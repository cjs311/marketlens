"""Tests for MarketLens portfolio-composition calculations."""

import numpy as np
import pandas as pd
import pytest

from src.composition import (
    CompositionCalculationError,
    calculate_asset_statistics,
    calculate_composition_analytics,
    calculate_concentration_metrics,
    calculate_correlation_matrix,
    calculate_volatility_contribution,
)


def make_asset_returns() -> pd.DataFrame:
    """Create deterministic multi-asset returns for testing."""
    return pd.DataFrame(
        {
            "SPY": [
                0.010,
                -0.005,
                0.008,
                0.003,
                -0.002,
            ],
            "QQQ": [
                0.015,
                -0.010,
                0.012,
                0.004,
                -0.006,
            ],
            "GLD": [
                -0.002,
                0.004,
                -0.001,
                0.005,
                0.003,
            ],
        },
        index=pd.bdate_range(
            "2026-01-02",
            periods=5,
        ),
        dtype="float64",
    )


def make_weights() -> pd.Series:
    """Create labeled portfolio weights."""
    return pd.Series(
        {
            "SPY": 0.50,
            "QQQ": 0.30,
            "GLD": 0.20,
        },
        dtype="float64",
        name="weight",
    )


def test_equal_weights_have_expected_concentration() -> None:
    """Three equal assets should have an effective count of three."""
    weights = pd.Series(
        {
            "SPY": 1.0 / 3.0,
            "QQQ": 1.0 / 3.0,
            "GLD": 1.0 / 3.0,
        }
    )

    metrics = calculate_concentration_metrics(
        weights
    )

    assert metrics["hhi"] == pytest.approx(
        1.0 / 3.0
    )

    assert metrics[
        "effective_assets"
    ] == pytest.approx(3.0)


def test_top_two_concentration_is_calculated() -> None:
    """Top-two weight should sum the two largest positions."""
    metrics = calculate_concentration_metrics(
        make_weights()
    )

    assert metrics["largest_ticker"] == "SPY"

    assert metrics[
        "largest_weight"
    ] == pytest.approx(0.50)

    assert metrics[
        "top_two_weight"
    ] == pytest.approx(0.80)


def test_asset_statistics_calculate_total_return() -> None:
    """Asset total return should equal compounded daily growth."""
    returns = make_asset_returns()

    statistics = calculate_asset_statistics(
        returns
    )

    expected = (
        (
            1.0
            + returns["SPY"]
        ).prod()
        - 1.0
    )

    assert statistics.loc[
        "SPY",
        "total_return",
    ] == pytest.approx(expected)


def test_asset_statistics_annualize_volatility() -> None:
    """Standalone volatility should use 252 trading days."""
    returns = make_asset_returns()

    statistics = calculate_asset_statistics(
        returns
    )

    expected = (
        returns["QQQ"].std(ddof=1)
        * np.sqrt(252)
    )

    assert statistics.loc[
        "QQQ",
        "annualized_volatility",
    ] == pytest.approx(expected)


def test_correlation_matrix_is_symmetric() -> None:
    """Asset correlations should form a symmetric matrix."""
    correlation = calculate_correlation_matrix(
        make_asset_returns()
    )

    assert correlation.equals(
        correlation.transpose()
    )

    assert np.diag(
        correlation
    ).tolist() == pytest.approx(
        [
            1.0,
            1.0,
            1.0,
        ]
    )


def test_volatility_contributions_sum_to_one() -> None:
    """Component contribution percentages should reconcile to 100%."""
    contribution = (
        calculate_volatility_contribution(
            make_asset_returns(),
            make_weights(),
        )
    )

    assert contribution[
        "contribution_percentage"
    ].sum() == pytest.approx(1.0)


def test_annualized_contributions_reconcile() -> None:
    """Component volatilities should sum to portfolio volatility."""
    returns = make_asset_returns()
    weights = make_weights()

    contribution = (
        calculate_volatility_contribution(
            returns,
            weights,
        )
    )

    covariance = returns.cov()

    expected_portfolio_volatility = (
        np.sqrt(
            weights.to_numpy()
            @ covariance.to_numpy()
            @ weights.to_numpy()
        )
        * np.sqrt(252)
    )

    assert contribution[
        "annualized_volatility_contribution"
    ].sum() == pytest.approx(
        expected_portfolio_volatility
    )


def test_zero_weight_has_zero_component_contribution() -> None:
    """An unallocated asset should contribute zero volatility."""
    weights = pd.Series(
        {
            "SPY": 0.70,
            "QQQ": 0.30,
            "GLD": 0.00,
        }
    )

    contribution = (
        calculate_volatility_contribution(
            make_asset_returns(),
            weights,
        )
    )

    assert contribution.loc[
        "GLD",
        "annualized_volatility_contribution",
    ] == pytest.approx(0.0)


def test_complete_analytics_build_expected_outputs() -> None:
    """Complete analysis should expose every chart-ready result."""
    analytics = calculate_composition_analytics(
        make_asset_returns(),
        make_weights(),
    )

    assert list(
        analytics.allocation.index
    ) == [
        "SPY",
        "QQQ",
        "GLD",
    ]

    assert analytics.correlation.shape == (
        3,
        3,
    )

    assert (
        "diversification_ratio"
        in analytics.metrics
    )

    assert list(
        analytics.volatility_contribution.index
    ) == [
        "SPY",
        "QQQ",
        "GLD",
    ]


def test_mismatched_tickers_are_rejected() -> None:
    """Weights must correspond exactly to the return columns."""
    weights = pd.Series(
        {
            "SPY": 0.50,
            "QQQ": 0.30,
            "BTC": 0.20,
        }
    )

    with pytest.raises(
        CompositionCalculationError,
        match="match the asset-return tickers",
    ):
        calculate_composition_analytics(
            make_asset_returns(),
            weights,
        )


def test_incorrect_weight_total_is_rejected() -> None:
    """Weights must total exactly 100% within tolerance."""
    weights = pd.Series(
        {
            "SPY": 0.50,
            "QQQ": 0.20,
            "GLD": 0.10,
        }
    )

    with pytest.raises(
        CompositionCalculationError,
        match="total 100%",
    ):
        calculate_concentration_metrics(
            weights
        )


def test_missing_asset_return_is_rejected() -> None:
    """Missing returns must not be silently removed."""
    returns = make_asset_returns()

    returns.loc[
        returns.index[1],
        "QQQ",
    ] = np.nan

    with pytest.raises(
        CompositionCalculationError,
        match="missing",
    ):
        calculate_asset_statistics(
            returns
        )