"""Tests for MarketLens portfolio stress testing."""

import pandas as pd
import pytest

from src.stress import (
    SCENARIOS,
    StressCalculationError,
    calculate_scenario_comparison,
    calculate_stress_test,
)


def make_weights() -> pd.Series:
    """Create deterministic portfolio weights."""
    return pd.Series(
        {
            "SPY": 0.50,
            "QQQ": 0.30,
            "GLD": 0.20,
        },
        dtype="float64",
    )


def make_sensitivities() -> pd.Series:
    """Create asset-level market sensitivities."""
    return pd.Series(
        {
            "SPY": 1.00,
            "QQQ": 1.50,
            "GLD": -0.25,
        },
        dtype="float64",
    )


def test_builtin_scenarios_are_available() -> None:
    """MarketLens should expose several negative stress scenarios."""
    assert len(SCENARIOS) >= 5

    assert all(
        scenario.market_shock < 0.0
        for scenario in SCENARIOS.values()
    )


def test_default_sensitivity_matches_market_shock() -> None:
    """Default sensitivity of one should copy the market shock."""
    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.10,
    )

    assert result.asset_results[
        "stressed_return"
    ].tolist() == pytest.approx(
        [
            -0.10,
            -0.10,
            -0.10,
        ]
    )

    assert result.metrics[
        "portfolio_stressed_return"
    ] == pytest.approx(-0.10)


def test_asset_sensitivities_change_stressed_returns() -> None:
    """Each asset should react according to its sensitivity."""
    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.20,
        sensitivities=make_sensitivities(),
    )

    assert result.asset_results.loc[
        "SPY",
        "stressed_return",
    ] == pytest.approx(-0.20)

    assert result.asset_results.loc[
        "QQQ",
        "stressed_return",
    ] == pytest.approx(-0.30)

    assert result.asset_results.loc[
        "GLD",
        "stressed_return",
    ] == pytest.approx(0.05)

    assert result.metrics[
        "portfolio_stressed_return"
    ] == pytest.approx(-0.18)


def test_specific_shocks_are_added_to_market_component() -> None:
    """Asset-specific shocks should modify factor-driven returns."""
    specific_shocks = pd.Series(
        {
            "SPY": 0.00,
            "QQQ": 0.00,
            "GLD": 0.05,
        }
    )

    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.10,
        specific_shocks=specific_shocks,
    )

    assert result.asset_results.loc[
        "GLD",
        "stressed_return",
    ] == pytest.approx(-0.05)

    assert result.metrics[
        "portfolio_stressed_return"
    ] == pytest.approx(-0.09)


def test_asset_loss_is_floored_at_negative_one() -> None:
    """No long asset should lose more than 100%."""
    sensitivities = pd.Series(
        {
            "SPY": 6.00,
            "QQQ": 1.00,
            "GLD": 1.00,
        }
    )

    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.20,
        sensitivities=sensitivities,
    )

    assert result.asset_results.loc[
        "SPY",
        "raw_stressed_return",
    ] == pytest.approx(-1.20)

    assert result.asset_results.loc[
        "SPY",
        "stressed_return",
    ] == pytest.approx(-1.00)

    assert result.metrics[
        "floor_count"
    ] == 1


def test_asset_contributions_reconcile() -> None:
    """Asset contributions should sum to portfolio return."""
    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.20,
        sensitivities=make_sensitivities(),
    )

    assert result.asset_results[
        "portfolio_contribution"
    ].sum() == pytest.approx(
        result.metrics[
            "portfolio_stressed_return"
        ]
    )


def test_portfolio_value_estimates_are_calculated() -> None:
    """Starting value should produce P/L and ending value."""
    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.10,
        initial_portfolio_value=25_000.0,
    )

    assert result.metrics[
        "portfolio_profit_loss"
    ] == pytest.approx(-2_500.0)

    assert result.metrics[
        "estimated_loss"
    ] == pytest.approx(2_500.0)

    assert result.metrics[
        "ending_portfolio_value"
    ] == pytest.approx(22_500.0)


def test_largest_detractor_is_identified() -> None:
    """The most-negative weighted contribution should be identified."""
    sensitivities = pd.Series(
        {
            "SPY": 1.00,
            "QQQ": 2.00,
            "GLD": 1.00,
        }
    )

    result = calculate_stress_test(
        weights=make_weights(),
        market_shock=-0.10,
        sensitivities=sensitivities,
    )

    assert result.metrics[
        "largest_detractor"
    ] == "QQQ"


def test_mismatched_sensitivity_tickers_are_rejected() -> None:
    """Sensitivity labels must match portfolio tickers."""
    sensitivities = pd.Series(
        {
            "SPY": 1.00,
            "QQQ": 1.20,
            "BTC": 2.00,
        }
    )

    with pytest.raises(
        StressCalculationError,
        match="match the portfolio-weight tickers",
    ):
        calculate_stress_test(
            weights=make_weights(),
            market_shock=-0.10,
            sensitivities=sensitivities,
        )


def test_incorrect_weight_total_is_rejected() -> None:
    """Portfolio weights must total 100%."""
    weights = pd.Series(
        {
            "SPY": 0.50,
            "QQQ": 0.20,
            "GLD": 0.10,
        }
    )

    with pytest.raises(
        StressCalculationError,
        match="total 100%",
    ):
        calculate_stress_test(
            weights=weights,
            market_shock=-0.10,
        )


def test_market_loss_below_negative_one_is_rejected() -> None:
    """The broad market cannot lose more than 100%."""
    with pytest.raises(
        StressCalculationError,
        match="less than -100%",
    ):
        calculate_stress_test(
            weights=make_weights(),
            market_shock=-1.01,
        )


def test_scenario_comparison_builds_expected_results() -> None:
    """Scenario comparison should retain supplied scenario names."""
    comparison = calculate_scenario_comparison(
        weights=make_weights(),
        scenarios={
            "Small decline": -0.05,
            "Large decline": -0.20,
        },
    )

    assert list(
        comparison.index
    ) == [
        "Small decline",
        "Large decline",
    ]

    assert comparison.loc[
        "Small decline",
        "portfolio_stressed_return",
    ] == pytest.approx(-0.05)

    assert comparison.loc[
        "Large decline",
        "ending_portfolio_value",
    ] == pytest.approx(8_000.0)