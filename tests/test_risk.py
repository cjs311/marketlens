"""Tests for MarketLens downside-risk calculations."""

import numpy as np
import pandas as pd
import pytest

from src.risk import (
    RiskCalculationError,
    calculate_beta,
    calculate_drawdown,
    calculate_historical_cvar,
    calculate_historical_var,
    calculate_risk_comparison,
    calculate_rolling_volatility,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
)


def make_returns(
    values: list[float],
    name: str = "Returns",
) -> pd.Series:
    """Create a dated return series for a test."""
    return pd.Series(
        values,
        index=pd.bdate_range(
            "2026-01-02",
            periods=len(values),
        ),
        name=name,
        dtype="float64",
    )


def test_drawdown_tracks_peak_to_trough() -> None:
    """Drawdown should measure declines from the running wealth peak."""
    returns = make_returns(
        [
            0.10,
            -0.10,
            -0.20,
            0.25,
        ]
    )

    drawdown = calculate_drawdown(
        returns
    )

    assert drawdown.tolist() == pytest.approx(
        [
            0.00,
            -0.10,
            -0.28,
            -0.10,
        ]
    )


def test_drawdown_captures_first_negative_return() -> None:
    """Initial wealth should count as the first running peak."""
    returns = make_returns(
        [
            -0.10,
            0.10,
        ]
    )

    drawdown = calculate_drawdown(
        returns
    )

    assert drawdown.tolist() == pytest.approx(
        [
            -0.10,
            -0.01,
        ]
    )


def test_sharpe_ratio_matches_known_formula() -> None:
    """Sharpe should annualize mean return and sample volatility."""
    returns = make_returns(
        [
            0.010,
            -0.005,
            0.015,
            0.000,
            0.020,
        ]
    )

    expected = (
        returns.mean()
        / returns.std(ddof=1)
        * np.sqrt(252)
    )

    result = calculate_sharpe_ratio(
        returns,
        annual_risk_free_rate=0.0,
    )

    assert result == pytest.approx(
        expected
    )


def test_sortino_ratio_matches_known_formula() -> None:
    """Sortino should penalize only returns below the target."""
    returns = make_returns(
        [
            0.010,
            -0.005,
            0.015,
            0.000,
            0.020,
        ]
    )

    downside_returns = np.minimum(
        returns.to_numpy(),
        0.0,
    )

    downside_deviation = (
        np.sqrt(
            np.mean(
                np.square(
                    downside_returns
                )
            )
        )
        * np.sqrt(252)
    )

    expected = (
        returns.mean()
        * 252
        / downside_deviation
    )

    result = calculate_sortino_ratio(
        returns,
        annual_risk_free_rate=0.0,
    )

    assert result == pytest.approx(
        expected
    )


def test_historical_var_and_cvar_match_tail_losses() -> None:
    """Historical VaR and CVaR should use the lower-return tail."""
    returns = make_returns(
        [
            -0.10,
            -0.05,
            -0.02,
            0.00,
            0.01,
            0.02,
            0.03,
            0.04,
            0.05,
            0.06,
        ]
    )

    value_at_risk = calculate_historical_var(
        returns,
        confidence_level=0.80,
    )

    conditional_value_at_risk = calculate_historical_cvar(
        returns,
        confidence_level=0.80,
    )

    assert value_at_risk == pytest.approx(
        0.026
    )

    assert conditional_value_at_risk == pytest.approx(
        0.075
    )


def test_beta_matches_known_relationship() -> None:
    """Twice each benchmark return should produce beta two."""
    benchmark = make_returns(
        [
            -0.02,
            -0.01,
            0.00,
            0.01,
            0.02,
        ],
        name="Benchmark",
    )

    asset = (
        benchmark
        .multiply(2.0)
        .rename("Asset")
    )

    assert calculate_beta(
        asset,
        benchmark,
    ) == pytest.approx(2.0)


def test_flat_returns_produce_undefined_ratios() -> None:
    """Zero variability should not produce an infinite ratio."""
    returns = make_returns(
        [
            0.001,
            0.001,
            0.001,
            0.001,
        ]
    )

    assert np.isnan(
        calculate_sharpe_ratio(
            returns
        )
    )

    assert np.isnan(
        calculate_sortino_ratio(
            returns
        )
    )


def test_rolling_volatility_uses_requested_window() -> None:
    """Rolling volatility should begin after a complete window."""
    returns = make_returns(
        [
            0.01,
            -0.01,
            0.01,
            -0.01,
        ]
    )

    result = calculate_rolling_volatility(
        returns,
        window=3,
    )

    expected_third_value = (
        returns.iloc[:3].std(ddof=1)
        * np.sqrt(252)
    )

    assert result.iloc[:2].isna().all()

    assert result.iloc[2] == pytest.approx(
        expected_third_value
    )


def test_invalid_confidence_level_is_rejected() -> None:
    """Confidence must be between zero and one."""
    returns = make_returns(
        [
            0.01,
            -0.01,
        ]
    )

    with pytest.raises(
        RiskCalculationError,
        match="confidence level",
    ):
        calculate_historical_var(
            returns,
            confidence_level=1.0,
        )


def test_missing_returns_are_rejected() -> None:
    """Missing observations must not be silently removed."""
    returns = make_returns(
        [
            0.01,
            -0.01,
            0.02,
        ]
    )

    returns.iloc[1] = np.nan

    with pytest.raises(
        RiskCalculationError,
        match="missing",
    ):
        calculate_drawdown(
            returns
        )


def test_risk_comparison_builds_aligned_outputs() -> None:
    """Comparison should expose portfolio and benchmark results."""
    portfolio = make_returns(
        [
            0.010,
            -0.020,
            0.015,
            0.005,
        ],
        name="Portfolio",
    )

    benchmark = make_returns(
        [
            0.005,
            -0.010,
            0.010,
            0.002,
        ],
        name="Benchmark",
    )

    comparison = calculate_risk_comparison(
        portfolio,
        benchmark,
        confidence_level=0.95,
        rolling_window=2,
    )

    assert list(
        comparison.metrics.index
    ) == [
        "Portfolio",
        "Benchmark",
    ]

    assert "beta" in (
        comparison.metrics.columns
    )

    assert list(
        comparison.drawdown.columns
    ) == [
        "Portfolio",
        "Benchmark",
    ]

    assert len(
        comparison.drawdown
    ) == len(
        portfolio
    )


def test_beta_rejects_misaligned_dates() -> None:
    """Beta must not combine returns from different dates."""
    asset = make_returns(
        [
            0.01,
            -0.01,
            0.02,
        ],
        name="Asset",
    )

    benchmark = make_returns(
        [
            0.01,
            -0.01,
            0.02,
        ],
        name="Benchmark",
    )

    benchmark.index = (
        benchmark.index
        + pd.Timedelta(days=1)
    )

    with pytest.raises(
        RiskCalculationError,
        match="same aligned dates",
    ):
        calculate_beta(
            asset,
            benchmark,
        )