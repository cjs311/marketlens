"""Tests for MarketLens portfolio-performance calculations."""

from datetime import date

import pandas as pd
import pytest

from src.portfolio import (
    PortfolioCalculationError,
    calculate_portfolio_analytics,
    create_equal_weights,
    create_portfolio_signature,
    validate_weights,
)


@pytest.fixture
def known_prices() -> pd.DataFrame:
    """Return prices with manually verifiable daily returns."""
    return pd.DataFrame(
        {
            "AAA": [
                100.0,
                110.0,
                99.0,
                108.9,
            ],
            "BBB": [
                100.0,
                100.0,
                110.0,
                110.0,
            ],
            "SPY": [
                100.0,
                105.0,
                105.0,
                110.25,
            ],
        },
        index=pd.bdate_range(
            "2026-01-02",
            periods=4,
        ),
    )


def test_create_equal_weights() -> None:
    """Equal weights should preserve ticker order and total one."""
    weights = create_equal_weights(
        ("AAA", "BBB", "CCC")
    )

    assert list(weights.index) == [
        "AAA",
        "BBB",
        "CCC",
    ]
    assert weights.sum() == pytest.approx(1.0)
    assert weights["AAA"] == pytest.approx(
        1.0 / 3.0
    )


def test_create_portfolio_signature() -> None:
    """Session signatures should normalize symbols and preserve dates."""
    signature = create_portfolio_signature(
        asset_tickers=(
            "spy",
            "qqq",
        ),
        benchmark="spy",
        actual_start=date(
            2025,
            7,
            29,
        ),
        actual_end=date(
            2026,
            7,
            28,
        ),
    )

    assert signature == (
        "SPY|QQQ|benchmark=SPY|"
        "start=2025-07-29|end=2026-07-28"
    )


def test_validate_weights_accepts_valid_weights() -> None:
    """A correctly weighted long-only portfolio should pass."""
    weights = validate_weights(
        {
            "AAA": 0.60,
            "BBB": 0.40,
        },
        ("AAA", "BBB"),
    )

    assert weights.to_dict() == pytest.approx(
        {
            "AAA": 0.60,
            "BBB": 0.40,
        }
    )


def test_validate_weights_normalizes_values() -> None:
    """Optional normalization should proportionally total one."""
    weights = validate_weights(
        {
            "AAA": 60.0,
            "BBB": 20.0,
        },
        ("AAA", "BBB"),
        normalize=True,
    )

    assert weights["AAA"] == pytest.approx(0.75)
    assert weights["BBB"] == pytest.approx(0.25)
    assert weights.sum() == pytest.approx(1.0)


def test_validate_weights_rejects_incorrect_total() -> None:
    """Weights must total one if normalization is disabled."""
    with pytest.raises(
        PortfolioCalculationError,
        match="total 100%",
    ):
        validate_weights(
            {
                "AAA": 0.60,
                "BBB": 0.20,
            },
            ("AAA", "BBB"),
        )


def test_validate_weights_rejects_negative_values() -> None:
    """The MVP should reject short positions."""
    with pytest.raises(
        PortfolioCalculationError,
        match="Negative",
    ):
        validate_weights(
            {
                "AAA": 1.10,
                "BBB": -0.10,
            },
            ("AAA", "BBB"),
        )


def test_validate_weights_rejects_missing_asset() -> None:
    """Every selected asset must receive a weight."""
    with pytest.raises(
        PortfolioCalculationError,
        match="missing",
    ):
        validate_weights(
            {
                "AAA": 1.0,
            },
            ("AAA", "BBB"),
        )


def test_calculate_portfolio_daily_returns(
    known_prices: pd.DataFrame,
) -> None:
    """Weighted daily returns should match manual calculations."""
    analytics = calculate_portfolio_analytics(
        prices=known_prices,
        asset_tickers=("AAA", "BBB"),
        benchmark="SPY",
        weights={
            "AAA": 0.60,
            "BBB": 0.40,
        },
    )

    assert analytics.portfolio_returns.tolist() == pytest.approx(
        [
            0.06,
            -0.02,
            0.06,
        ]
    )

    assert analytics.benchmark_returns.tolist() == pytest.approx(
        [
            0.05,
            0.00,
            0.05,
        ]
    )


def test_performance_index_starts_at_one_hundred(
    known_prices: pd.DataFrame,
) -> None:
    """Cumulative comparison should include a common starting value."""
    analytics = calculate_portfolio_analytics(
        prices=known_prices,
        asset_tickers=("AAA", "BBB"),
        benchmark="SPY",
        weights={
            "AAA": 0.60,
            "BBB": 0.40,
        },
    )

    assert analytics.performance_index.iloc[0].to_dict() == pytest.approx(
        {
            "Portfolio": 100.0,
            "Benchmark": 100.0,
        }
    )

    assert (
        analytics.performance_index["Portfolio"].iloc[-1]
        == pytest.approx(110.1128)
    )

    assert (
        analytics.performance_index["Benchmark"].iloc[-1]
        == pytest.approx(110.25)
    )


def test_performance_metrics_match_compounded_returns(
    known_prices: pd.DataFrame,
) -> None:
    """Reported total return should equal compounded daily returns."""
    analytics = calculate_portfolio_analytics(
        prices=known_prices,
        asset_tickers=("AAA", "BBB"),
        benchmark="SPY",
        weights={
            "AAA": 0.60,
            "BBB": 0.40,
        },
    )

    assert (
        analytics.metrics.loc[
            "Portfolio",
            "total_return",
        ]
        == pytest.approx(0.101128)
    )

    assert (
        analytics.metrics.loc[
            "Benchmark",
            "total_return",
        ]
        == pytest.approx(0.1025)
    )

    assert (
        analytics.metrics.loc[
            "Portfolio",
            "observations",
        ]
        == 3
    )


def test_calculation_rejects_nonpositive_prices(
    known_prices: pd.DataFrame,
) -> None:
    """Zero or negative adjusted prices must not produce returns."""
    invalid_prices = known_prices.copy()
    invalid_prices.loc[
        invalid_prices.index[1],
        "AAA",
    ] = 0.0

    with pytest.raises(
        PortfolioCalculationError,
        match="greater than zero",
    ):
        calculate_portfolio_analytics(
            prices=invalid_prices,
            asset_tickers=("AAA", "BBB"),
            benchmark="SPY",
            weights={
                "AAA": 0.60,
                "BBB": 0.40,
            },
        )
