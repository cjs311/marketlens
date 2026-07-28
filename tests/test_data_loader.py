"""Tests for MarketLens historical-price preparation."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.data_loader import (
    InsufficientDataError,
    UnavailableTickerError,
    extract_adjusted_close,
    prepare_price_data,
)


def test_extract_adjusted_close_from_multiindex() -> None:
    """The normal multi-ticker yfinance response should be supported."""
    columns = pd.MultiIndex.from_tuples(
        [
            ("Close", "SPY"),
            ("Close", "QQQ"),
            ("Open", "SPY"),
            ("Open", "QQQ"),
        ],
        names=["Price", "Ticker"],
    )

    raw_data = pd.DataFrame(
        [
            [100.0, 200.0, 99.0, 198.0],
            [101.0, 202.0, 100.0, 200.0],
        ],
        index=pd.bdate_range("2026-01-02", periods=2),
        columns=columns,
    )

    result = extract_adjusted_close(
        raw_data,
        ("SPY", "QQQ"),
    )

    assert list(result.columns) == ["SPY", "QQQ"]
    assert result.iloc[0].to_dict() == {
        "SPY": 100.0,
        "QQQ": 200.0,
    }


def test_extract_adjusted_close_from_single_level() -> None:
    """A single-ticker, single-level response should be normalized."""
    raw_data = pd.DataFrame(
        {
            "Open": [99.0, 100.0],
            "Close": [100.0, 101.0],
        },
        index=pd.bdate_range("2026-01-02", periods=2),
    )

    result = extract_adjusted_close(
        raw_data,
        ("SPY",),
    )

    assert list(result.columns) == ["SPY"]
    assert result["SPY"].tolist() == [100.0, 101.0]


def test_prepare_price_data_aligns_missing_dates() -> None:
    """Dates with a missing price should be removed transparently."""
    dates = pd.bdate_range(
        "2026-01-02",
        periods=25,
    )

    prices = pd.DataFrame(
        {
            "SPY": np.linspace(100.0, 124.0, 25),
            "QQQ": np.linspace(200.0, 248.0, 25),
        },
        index=dates,
    )

    prices.loc[dates[0], "QQQ"] = np.nan

    result = prepare_price_data(
        close_prices=prices,
        requested_symbols=("SPY", "QQQ"),
        requested_start=dates[0].date(),
        requested_end=dates[-1].date(),
        minimum_observations=20,
    )

    assert result.rows_before_alignment == 25
    assert result.rows_after_alignment == 24
    assert result.dropped_rows == 1
    assert result.missing_values == {
        "SPY": 0,
        "QQQ": 1,
    }
    assert not result.prices.isna().any().any()
    assert result.actual_start == dates[1].date()


def test_prepare_price_data_rejects_unavailable_ticker() -> None:
    """An all-missing ticker must not be silently excluded."""
    dates = pd.bdate_range(
        "2026-01-02",
        periods=25,
    )

    prices = pd.DataFrame(
        {
            "SPY": np.linspace(100.0, 124.0, 25),
            "GLD": np.nan,
        },
        index=dates,
    )

    with pytest.raises(
        UnavailableTickerError,
        match="GLD",
    ):
        prepare_price_data(
            close_prices=prices,
            requested_symbols=("SPY", "GLD"),
            requested_start=dates[0].date(),
            requested_end=dates[-1].date(),
            minimum_observations=20,
        )


def test_prepare_price_data_rejects_short_history() -> None:
    """Too few observations should produce an explicit error."""
    dates = pd.bdate_range(
        "2026-01-02",
        periods=5,
    )

    prices = pd.DataFrame(
        {
            "SPY": np.linspace(100.0, 104.0, 5),
            "QQQ": np.linspace(200.0, 208.0, 5),
        },
        index=dates,
    )

    with pytest.raises(
        InsufficientDataError,
        match="At least 20",
    ):
        prepare_price_data(
            close_prices=prices,
            requested_symbols=("SPY", "QQQ"),
            requested_start=dates[0].date(),
            requested_end=dates[-1].date(),
            minimum_observations=20,
        )