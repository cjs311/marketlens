"""SQLite persistence for MarketLens portfolio analyses."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Iterator, Mapping

import numpy as np
import pandas as pd

from src.data_loader import MarketDataResult
from src.portfolio import (
    PortfolioCalculationError,
    PortfolioAnalytics,
    calculate_portfolio_analytics,
    validate_weights,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "marketlens.db"
MAX_ANALYSIS_NAME_LENGTH = 80


class PersistenceError(RuntimeError):
    """Raised when a saved analysis cannot be stored or restored."""


class DuplicateAnalysisNameError(PersistenceError):
    """Raised when an analysis name already exists."""


class SavedAnalysisNotFoundError(PersistenceError):
    """Raised when a requested saved analysis no longer exists."""


@dataclass(frozen=True)
class SavedAnalysisSummary:
    """Metadata and headline metrics for one saved analysis."""

    id: int
    name: str
    created_at: datetime
    asset_tickers: tuple[str, ...]
    benchmark: str
    requested_start: date
    requested_end: date
    actual_start: date
    actual_end: date
    weights: dict[str, float]
    portfolio_total_return: float
    portfolio_annualized_return: float
    portfolio_annualized_volatility: float


@dataclass(frozen=True)
class SavedAnalysis(SavedAnalysisSummary):
    """Complete saved analysis, including its historical adjusted prices."""

    prices: pd.DataFrame
    missing_values: dict[str, int]
    rows_before_alignment: int
    rows_after_alignment: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    created_at TEXT NOT NULL,
    asset_tickers_json TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    requested_start TEXT NOT NULL,
    requested_end TEXT NOT NULL,
    actual_start TEXT NOT NULL,
    actual_end TEXT NOT NULL,
    weights_json TEXT NOT NULL,
    prices_json TEXT NOT NULL,
    missing_values_json TEXT NOT NULL,
    rows_before_alignment INTEGER NOT NULL,
    rows_after_alignment INTEGER NOT NULL,
    portfolio_total_return REAL NOT NULL,
    portfolio_annualized_return REAL NOT NULL,
    portfolio_annualized_volatility REAL NOT NULL,
    CHECK(length(trim(name)) BETWEEN 1 AND 80)
);
"""


_SUMMARY_COLUMNS = """
id,
name,
created_at,
asset_tickers_json,
benchmark,
requested_start,
requested_end,
actual_start,
actual_end,
weights_json,
portfolio_total_return,
portfolio_annualized_return,
portfolio_annualized_volatility
"""


def get_database_path(
    database_path: str | Path | None = None,
) -> Path:
    """Return the configured SQLite path."""
    if database_path is not None:
        return Path(database_path).expanduser().resolve()

    configured_path = os.environ.get("MARKETLENS_DB_PATH")

    if configured_path:
        return Path(configured_path).expanduser().resolve()

    return DEFAULT_DATABASE_PATH


@contextmanager
def _connect(
    database_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    """Open a configured SQLite connection."""
    path = get_database_path(database_path)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        connection = sqlite3.connect(
            path,
            timeout=10.0,
        )
    except (OSError, sqlite3.Error) as error:
        raise PersistenceError(
            "MarketLens could not open its saved-analysis database."
        ) from error

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")

    try:
        yield connection
    finally:
        connection.close()


def initialize_database(
    database_path: str | Path | None = None,
) -> None:
    """Create the saved-analysis table when it does not exist."""
    try:
        with _connect(database_path) as connection:
            connection.execute(_SCHEMA)
            connection.commit()
    except sqlite3.Error as error:
        raise PersistenceError(
            "MarketLens could not initialize saved-analysis storage."
        ) from error


def _clean_name(name: str) -> str:
    """Validate and normalize a user-supplied analysis name."""
    cleaned_name = " ".join(str(name).split())

    if not cleaned_name:
        raise PersistenceError(
            "Enter a name before saving the analysis."
        )

    if len(cleaned_name) > MAX_ANALYSIS_NAME_LENGTH:
        raise PersistenceError(
            "Analysis names must contain 80 characters or fewer."
        )

    return cleaned_name


def _serialize_prices(prices: pd.DataFrame) -> str:
    """Serialize a price frame without losing ticker order or dates."""
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise PersistenceError(
            "Adjusted price history is required before saving."
        )

    numeric_prices = prices.apply(
        pd.to_numeric,
        errors="coerce",
    ).astype("float64")

    if (
        numeric_prices.isna().any().any()
        or not np.isfinite(
            numeric_prices.to_numpy(dtype="float64")
        ).all()
    ):
        raise PersistenceError(
            "Adjusted price history contains invalid values."
        )

    timestamps = pd.to_datetime(
        numeric_prices.index,
        errors="coerce",
    )

    if timestamps.isna().any():
        raise PersistenceError(
            "Adjusted price history contains invalid dates."
        )

    payload = {
        "columns": [
            str(column).upper()
            for column in numeric_prices.columns
        ],
        "index": [
            timestamp.isoformat()
            for timestamp in timestamps
        ],
        "data": numeric_prices.to_numpy(
            dtype="float64"
        ).tolist(),
    }

    return json.dumps(
        payload,
        separators=(",", ":"),
        allow_nan=False,
    )


def _deserialize_prices(prices_json: str) -> pd.DataFrame:
    """Restore a serialized adjusted-price frame."""
    try:
        payload = json.loads(prices_json)
        prices = pd.DataFrame(
            payload["data"],
            columns=payload["columns"],
            index=pd.to_datetime(
                payload["index"],
                errors="raise",
            ),
            dtype="float64",
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        raise PersistenceError(
            "A saved analysis contains invalid price history."
        ) from error

    prices.index.name = "Date"

    return prices


def _parse_json(
    raw_value: str,
    *,
    field_name: str,
) -> Any:
    """Parse one JSON database field with a user-safe error."""
    try:
        return json.loads(raw_value)
    except (TypeError, json.JSONDecodeError) as error:
        raise PersistenceError(
            f"A saved analysis contains invalid {field_name} data."
        ) from error


def _parse_date(
    raw_value: str,
    *,
    field_name: str,
) -> date:
    """Parse one ISO date database field."""
    try:
        return date.fromisoformat(raw_value)
    except (TypeError, ValueError) as error:
        raise PersistenceError(
            f"A saved analysis contains an invalid {field_name} date."
        ) from error


def _parse_datetime(raw_value: str) -> datetime:
    """Parse one ISO timestamp database field."""
    try:
        return datetime.fromisoformat(raw_value)
    except (TypeError, ValueError) as error:
        raise PersistenceError(
            "A saved analysis contains an invalid creation timestamp."
        ) from error


def _row_to_summary(
    row: sqlite3.Row,
) -> SavedAnalysisSummary:
    """Convert a SQLite row into summary metadata."""
    raw_asset_tickers = _parse_json(
        row["asset_tickers_json"],
        field_name="ticker",
    )

    if not isinstance(
        raw_asset_tickers,
        list,
    ):
        raise PersistenceError(
            "A saved analysis contains invalid ticker data."
        )

    asset_tickers = tuple(
        str(ticker).upper()
        for ticker in raw_asset_tickers
    )
    raw_weights = _parse_json(
        row["weights_json"],
        field_name="portfolio-weight",
    )

    if not isinstance(raw_weights, dict):
        raise PersistenceError(
            "A saved analysis contains invalid portfolio-weight data."
        )

    try:
        weights = {
            str(ticker).upper(): float(weight)
            for ticker, weight in raw_weights.items()
        }
    except (TypeError, ValueError) as error:
        raise PersistenceError(
            "A saved analysis contains invalid portfolio-weight data."
        ) from error

    return SavedAnalysisSummary(
        id=int(row["id"]),
        name=str(row["name"]),
        created_at=_parse_datetime(row["created_at"]),
        asset_tickers=asset_tickers,
        benchmark=str(row["benchmark"]).upper(),
        requested_start=_parse_date(
            row["requested_start"],
            field_name="requested-start",
        ),
        requested_end=_parse_date(
            row["requested_end"],
            field_name="requested-end",
        ),
        actual_start=_parse_date(
            row["actual_start"],
            field_name="actual-start",
        ),
        actual_end=_parse_date(
            row["actual_end"],
            field_name="actual-end",
        ),
        weights=weights,
        portfolio_total_return=float(
            row["portfolio_total_return"]
        ),
        portfolio_annualized_return=float(
            row["portfolio_annualized_return"]
        ),
        portfolio_annualized_volatility=float(
            row["portfolio_annualized_volatility"]
        ),
    )


def save_analysis(
    *,
    name: str,
    market_data_result: MarketDataResult,
    market_data_config: Mapping[str, Any],
    portfolio_analytics: PortfolioAnalytics,
    database_path: str | Path | None = None,
) -> SavedAnalysisSummary:
    """Persist the active analysis and return its saved metadata."""
    initialize_database(database_path)
    cleaned_name = _clean_name(name)

    try:
        asset_tickers = tuple(
            str(ticker).upper()
            for ticker in market_data_config[
                "asset_tickers"
            ]
        )
        benchmark = str(
            market_data_config["benchmark"]
        ).upper()
        requested_start = market_data_config[
            "start_date"
        ]
        requested_end = market_data_config[
            "end_date"
        ]
    except (KeyError, TypeError) as error:
        raise PersistenceError(
            "The active market-data configuration is incomplete."
        ) from error

    if not asset_tickers:
        raise PersistenceError(
            "At least one portfolio asset is required before saving."
        )

    if not isinstance(requested_start, date) or not isinstance(
        requested_end,
        date,
    ):
        raise PersistenceError(
            "The active analysis contains an invalid requested date range."
        )

    try:
        weights = validate_weights(
            portfolio_analytics.weights,
            asset_tickers,
        )
    except PortfolioCalculationError as error:
        raise PersistenceError(
            "The active portfolio weights are invalid."
        ) from error
    prices_json = _serialize_prices(
        market_data_result.prices
    )
    metrics = portfolio_analytics.metrics

    try:
        portfolio_total_return = float(
            metrics.loc[
                "Portfolio",
                "total_return",
            ]
        )
        portfolio_annualized_return = float(
            metrics.loc[
                "Portfolio",
                "annualized_return",
            ]
        )
        portfolio_annualized_volatility = float(
            metrics.loc[
                "Portfolio",
                "annualized_volatility",
            ]
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PersistenceError(
            "The active portfolio metrics are incomplete."
        ) from error

    created_at = datetime.now(UTC).replace(
        microsecond=0
    )
    parameters = (
        cleaned_name,
        created_at.isoformat(),
        json.dumps(asset_tickers),
        benchmark,
        requested_start.isoformat(),
        requested_end.isoformat(),
        market_data_result.actual_start.isoformat(),
        market_data_result.actual_end.isoformat(),
        json.dumps(
            {
                ticker: float(weights[ticker])
                for ticker in asset_tickers
            }
        ),
        prices_json,
        json.dumps(
            market_data_result.missing_values
        ),
        int(
            market_data_result.rows_before_alignment
        ),
        int(
            market_data_result.rows_after_alignment
        ),
        portfolio_total_return,
        portfolio_annualized_return,
        portfolio_annualized_volatility,
    )

    try:
        with _connect(database_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO saved_analyses (
                    name,
                    created_at,
                    asset_tickers_json,
                    benchmark,
                    requested_start,
                    requested_end,
                    actual_start,
                    actual_end,
                    weights_json,
                    prices_json,
                    missing_values_json,
                    rows_before_alignment,
                    rows_after_alignment,
                    portfolio_total_return,
                    portfolio_annualized_return,
                    portfolio_annualized_volatility
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                parameters,
            )
            saved_id = int(cursor.lastrowid)
            connection.commit()
    except sqlite3.IntegrityError as error:
        raise DuplicateAnalysisNameError(
            "An analysis with that name already exists. "
            "Choose a different name."
        ) from error
    except sqlite3.Error as error:
        raise PersistenceError(
            "MarketLens could not save the current analysis."
        ) from error

    return SavedAnalysisSummary(
        id=saved_id,
        name=cleaned_name,
        created_at=created_at,
        asset_tickers=asset_tickers,
        benchmark=benchmark,
        requested_start=requested_start,
        requested_end=requested_end,
        actual_start=market_data_result.actual_start,
        actual_end=market_data_result.actual_end,
        weights={
            ticker: float(weights[ticker])
            for ticker in asset_tickers
        },
        portfolio_total_return=portfolio_total_return,
        portfolio_annualized_return=portfolio_annualized_return,
        portfolio_annualized_volatility=(
            portfolio_annualized_volatility
        ),
    )


def list_saved_analyses(
    database_path: str | Path | None = None,
) -> list[SavedAnalysisSummary]:
    """Return saved analyses in newest-first order."""
    initialize_database(database_path)

    try:
        with _connect(database_path) as connection:
            rows = connection.execute(
                f"""
                SELECT {_SUMMARY_COLUMNS}
                FROM saved_analyses
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()
    except sqlite3.Error as error:
        raise PersistenceError(
            "MarketLens could not load saved analyses."
        ) from error

    return [
        _row_to_summary(row)
        for row in rows
    ]


def get_saved_analysis(
    analysis_id: int,
    database_path: str | Path | None = None,
) -> SavedAnalysis:
    """Return one complete saved analysis."""
    initialize_database(database_path)

    try:
        resolved_id = int(analysis_id)
    except (TypeError, ValueError) as error:
        raise SavedAnalysisNotFoundError(
            "The selected saved analysis is invalid."
        ) from error

    try:
        with _connect(database_path) as connection:
            row = connection.execute(
                """
                SELECT *
                FROM saved_analyses
                WHERE id = ?
                """,
                (resolved_id,),
            ).fetchone()
    except sqlite3.Error as error:
        raise PersistenceError(
            "MarketLens could not load the selected analysis."
        ) from error

    if row is None:
        raise SavedAnalysisNotFoundError(
            "The selected saved analysis no longer exists."
        )

    summary = _row_to_summary(row)
    raw_missing_values = _parse_json(
        row["missing_values_json"],
        field_name="missing-value",
    )

    return SavedAnalysis(
        **summary.__dict__,
        prices=_deserialize_prices(
            row["prices_json"]
        ),
        missing_values={
            str(ticker).upper(): int(count)
            for ticker, count in raw_missing_values.items()
        },
        rows_before_alignment=int(
            row["rows_before_alignment"]
        ),
        rows_after_alignment=int(
            row["rows_after_alignment"]
        ),
    )


def delete_saved_analysis(
    analysis_id: int,
    database_path: str | Path | None = None,
) -> None:
    """Permanently delete one saved analysis."""
    initialize_database(database_path)

    try:
        resolved_id = int(analysis_id)
    except (TypeError, ValueError) as error:
        raise SavedAnalysisNotFoundError(
            "The selected saved analysis is invalid."
        ) from error

    try:
        with _connect(database_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM saved_analyses
                WHERE id = ?
                """,
                (resolved_id,),
            )
            connection.commit()
    except sqlite3.Error as error:
        raise PersistenceError(
            "MarketLens could not delete the selected analysis."
        ) from error

    if cursor.rowcount == 0:
        raise SavedAnalysisNotFoundError(
            "The selected saved analysis no longer exists."
        )


def restore_saved_analysis(
    saved_analysis: SavedAnalysis,
) -> tuple[
    MarketDataResult,
    dict[str, Any],
    PortfolioAnalytics,
]:
    """Rebuild application state from a complete saved analysis."""
    market_data_result = MarketDataResult(
        prices=saved_analysis.prices.copy(),
        requested_symbols=tuple(
            dict.fromkeys(
                (
                    *saved_analysis.asset_tickers,
                    saved_analysis.benchmark,
                )
            )
        ),
        requested_start=saved_analysis.requested_start,
        requested_end=saved_analysis.requested_end,
        actual_start=saved_analysis.actual_start,
        actual_end=saved_analysis.actual_end,
        missing_values=saved_analysis.missing_values.copy(),
        rows_before_alignment=(
            saved_analysis.rows_before_alignment
        ),
        rows_after_alignment=(
            saved_analysis.rows_after_alignment
        ),
    )
    market_data_config = {
        "asset_tickers": saved_analysis.asset_tickers,
        "benchmark": saved_analysis.benchmark,
        "start_date": saved_analysis.requested_start,
        "end_date": saved_analysis.requested_end,
    }
    try:
        portfolio_analytics = calculate_portfolio_analytics(
            prices=market_data_result.prices,
            asset_tickers=saved_analysis.asset_tickers,
            benchmark=saved_analysis.benchmark,
            weights=saved_analysis.weights,
        )
    except PortfolioCalculationError as error:
        raise PersistenceError(
            "The saved analysis could not be reconstructed."
        ) from error

    return (
        market_data_result,
        market_data_config,
        portfolio_analytics,
    )
