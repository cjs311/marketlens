"""Tests for MarketLens SQLite saved-analysis persistence."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import MarketDataResult
from src.persistence import (
    DuplicateAnalysisNameError,
    PersistenceError,
    SavedAnalysisNotFoundError,
    delete_saved_analysis,
    get_saved_analysis,
    initialize_database,
    list_saved_analyses,
    restore_saved_analysis,
    save_analysis,
)
from src.portfolio import (
    calculate_portfolio_analytics,
)


@pytest.fixture
def database_path(
    tmp_path: Path,
) -> Path:
    """Return an isolated SQLite path."""
    return tmp_path / "marketlens-test.db"


@pytest.fixture
def analysis_inputs() -> tuple[
    MarketDataResult,
    dict[str, object],
    object,
]:
    """Return one complete, manually verifiable analysis."""
    prices = pd.DataFrame(
        {
            "AAA": [
                100.0,
                104.0,
                102.0,
                108.0,
            ],
            "BBB": [
                50.0,
                51.0,
                54.0,
                53.0,
            ],
            "SPY": [
                400.0,
                404.0,
                408.0,
                412.0,
            ],
        },
        index=pd.bdate_range(
            "2026-01-05",
            periods=4,
            name="Date",
        ),
    )
    market_data_result = MarketDataResult(
        prices=prices,
        requested_symbols=(
            "AAA",
            "BBB",
            "SPY",
        ),
        requested_start=date(
            2026,
            1,
            1,
        ),
        requested_end=date(
            2026,
            1,
            31,
        ),
        actual_start=date(
            2026,
            1,
            5,
        ),
        actual_end=date(
            2026,
            1,
            8,
        ),
        missing_values={
            "AAA": 0,
            "BBB": 0,
            "SPY": 0,
        },
        rows_before_alignment=4,
        rows_after_alignment=4,
    )
    config: dict[str, object] = {
        "asset_tickers": (
            "AAA",
            "BBB",
        ),
        "benchmark": "SPY",
        "start_date": date(
            2026,
            1,
            1,
        ),
        "end_date": date(
            2026,
            1,
            31,
        ),
    }
    analytics = calculate_portfolio_analytics(
        prices=prices,
        asset_tickers=(
            "AAA",
            "BBB",
        ),
        benchmark="SPY",
        weights={
            "AAA": 0.65,
            "BBB": 0.35,
        },
    )

    return (
        market_data_result,
        config,
        analytics,
    )


def test_initialize_database_creates_schema(
    database_path: Path,
) -> None:
    """Initialization should create the configured database file."""
    initialize_database(database_path)

    assert database_path.exists()
    assert list_saved_analyses(
        database_path
    ) == []


def test_saved_analysis_round_trip(
    database_path: Path,
    analysis_inputs: tuple[
        MarketDataResult,
        dict[str, object],
        object,
    ],
) -> None:
    """A save and reload should preserve data, weights, and metrics."""
    (
        market_data_result,
        config,
        analytics,
    ) = analysis_inputs

    saved_summary = save_analysis(
        name="  Core   ETF Test  ",
        market_data_result=market_data_result,
        market_data_config=config,
        portfolio_analytics=analytics,
        database_path=database_path,
    )

    assert saved_summary.name == "Core ETF Test"
    assert saved_summary.weights == pytest.approx(
        {
            "AAA": 0.65,
            "BBB": 0.35,
        }
    )

    summaries = list_saved_analyses(
        database_path
    )

    assert len(summaries) == 1
    assert summaries[0] == saved_summary

    saved_analysis = get_saved_analysis(
        saved_summary.id,
        database_path,
    )

    pd.testing.assert_frame_equal(
        saved_analysis.prices,
        market_data_result.prices,
        check_freq=False,
    )

    (
        restored_market_data,
        restored_config,
        restored_analytics,
    ) = restore_saved_analysis(
        saved_analysis
    )

    pd.testing.assert_frame_equal(
        restored_market_data.prices,
        market_data_result.prices,
        check_freq=False,
    )
    assert restored_config == config
    pd.testing.assert_series_equal(
        restored_analytics.weights,
        analytics.weights,
    )
    pd.testing.assert_frame_equal(
        restored_analytics.metrics,
        analytics.metrics,
    )


def test_saved_names_are_unique_case_insensitively(
    database_path: Path,
    analysis_inputs: tuple[
        MarketDataResult,
        dict[str, object],
        object,
    ],
) -> None:
    """Duplicate names should receive a clear domain error."""
    (
        market_data_result,
        config,
        analytics,
    ) = analysis_inputs

    save_analysis(
        name="Long-Term Portfolio",
        market_data_result=market_data_result,
        market_data_config=config,
        portfolio_analytics=analytics,
        database_path=database_path,
    )

    with pytest.raises(
        DuplicateAnalysisNameError,
        match="already exists",
    ):
        save_analysis(
            name="long-term portfolio",
            market_data_result=market_data_result,
            market_data_config=config,
            portfolio_analytics=analytics,
            database_path=database_path,
        )


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "   ",
        "x" * 81,
    ],
)
def test_invalid_analysis_names_are_rejected(
    invalid_name: str,
    database_path: Path,
    analysis_inputs: tuple[
        MarketDataResult,
        dict[str, object],
        object,
    ],
) -> None:
    """Empty and oversized names should not reach SQLite."""
    (
        market_data_result,
        config,
        analytics,
    ) = analysis_inputs

    with pytest.raises(PersistenceError):
        save_analysis(
            name=invalid_name,
            market_data_result=market_data_result,
            market_data_config=config,
            portfolio_analytics=analytics,
            database_path=database_path,
        )


def test_delete_saved_analysis(
    database_path: Path,
    analysis_inputs: tuple[
        MarketDataResult,
        dict[str, object],
        object,
    ],
) -> None:
    """Deleting a record should remove only the selected analysis."""
    (
        market_data_result,
        config,
        analytics,
    ) = analysis_inputs
    saved_summary = save_analysis(
        name="Delete Me",
        market_data_result=market_data_result,
        market_data_config=config,
        portfolio_analytics=analytics,
        database_path=database_path,
    )

    delete_saved_analysis(
        saved_summary.id,
        database_path,
    )

    assert list_saved_analyses(
        database_path
    ) == []

    with pytest.raises(
        SavedAnalysisNotFoundError,
    ):
        get_saved_analysis(
            saved_summary.id,
            database_path,
        )


def test_delete_missing_analysis_raises_error(
    database_path: Path,
) -> None:
    """Deleting a stale selection should report that it is gone."""
    with pytest.raises(
        SavedAnalysisNotFoundError,
        match="no longer exists",
    ):
        delete_saved_analysis(
            404,
            database_path,
        )
