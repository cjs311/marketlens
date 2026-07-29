"""Portfolio stress-testing calculations for MarketLens."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd


LabeledValues = pd.Series | Mapping[str, float]


class StressCalculationError(ValueError):
    """Raised when a stress test cannot be calculated."""


@dataclass(frozen=True)
class StressScenario:
    """A modeled market-shock scenario."""

    name: str
    market_shock: float
    description: str


@dataclass(frozen=True)
class StressTestResult:
    """Complete output from one portfolio stress test."""

    asset_results: pd.DataFrame
    metrics: dict[str, float | int | str]


SCENARIOS: dict[str, StressScenario] = {
    "Market correction": StressScenario(
        name="Market correction",
        market_shock=-0.10,
        description=(
            "A hypothetical 10% broad-market decline."
        ),
    ),
    "2022 rate-shock style": StressScenario(
        name="2022 rate-shock style",
        market_shock=-0.25,
        description=(
            "A simplified 25% broad-market decline inspired by a "
            "rapidly tightening interest-rate environment."
        ),
    ),
    "2020 pandemic-crash style": StressScenario(
        name="2020 pandemic-crash style",
        market_shock=-0.34,
        description=(
            "A simplified 34% broad-market decline inspired by the "
            "early-2020 market shock."
        ),
    ),
    "2008 financial-crisis style": StressScenario(
        name="2008 financial-crisis style",
        market_shock=-0.37,
        description=(
            "A simplified 37% broad-market decline inspired by a "
            "severe financial-system crisis."
        ),
    ),
    "Technology-bust style": StressScenario(
        name="Technology-bust style",
        market_shock=-0.49,
        description=(
            "A simplified 49% broad-market decline representing an "
            "extended technology-led market contraction."
        ),
    ),
}


def _prepare_weights(
    weights: LabeledValues,
) -> pd.Series:
    """Validate and return decimal portfolio weights."""
    if isinstance(weights, pd.Series):
        weight_series = weights.copy()
    elif isinstance(weights, Mapping):
        weight_series = pd.Series(
            dict(weights),
            dtype="float64",
        )
    else:
        raise StressCalculationError(
            "Portfolio weights must be a labeled series or mapping."
        )

    if weight_series.empty:
        raise StressCalculationError(
            "Portfolio weights cannot be empty."
        )

    if weight_series.index.has_duplicates:
        raise StressCalculationError(
            "Portfolio-weight tickers must be unique."
        )

    weight_series = pd.to_numeric(
        weight_series,
        errors="coerce",
    ).astype("float64")

    if weight_series.isna().any():
        raise StressCalculationError(
            "Portfolio weights must be numeric."
        )

    if not np.isfinite(
        weight_series.to_numpy(dtype="float64")
    ).all():
        raise StressCalculationError(
            "Portfolio weights must be finite."
        )

    if (weight_series < 0.0).any():
        raise StressCalculationError(
            "Portfolio weights cannot be negative."
        )

    if not np.isclose(
        float(weight_series.sum()),
        1.0,
        atol=1e-8,
        rtol=0.0,
    ):
        raise StressCalculationError(
            "Portfolio weights must total 100%."
        )

    return weight_series.rename("weight")


def _prepare_assumption(
    values: LabeledValues | None,
    tickers: pd.Index,
    default_value: float,
    label: str,
) -> pd.Series:
    """Validate and align a labeled asset assumption."""
    if values is None:
        series = pd.Series(
            default_value,
            index=tickers,
            dtype="float64",
        )
    elif isinstance(values, pd.Series):
        series = values.copy()
    elif isinstance(values, Mapping):
        series = pd.Series(
            dict(values),
            dtype="float64",
        )
    else:
        raise StressCalculationError(
            f"{label} must be a labeled series or mapping."
        )

    if series.index.has_duplicates:
        raise StressCalculationError(
            f"{label} tickers must be unique."
        )

    expected_tickers = set(tickers)
    provided_tickers = set(series.index)

    if expected_tickers != provided_tickers:
        raise StressCalculationError(
            f"{label} must match the portfolio-weight tickers."
        )

    series = (
        pd.to_numeric(
            series,
            errors="coerce",
        )
        .reindex(tickers)
        .astype("float64")
    )

    if series.isna().any():
        raise StressCalculationError(
            f"{label} must contain numeric values."
        )

    if not np.isfinite(
        series.to_numpy(dtype="float64")
    ).all():
        raise StressCalculationError(
            f"{label} must contain finite values."
        )

    return series


def _prepare_market_shock(
    market_shock: float,
) -> float:
    """Validate a decimal market shock."""
    try:
        shock = float(market_shock)
    except (TypeError, ValueError) as error:
        raise StressCalculationError(
            "The market shock must be numeric."
        ) from error

    if not np.isfinite(shock):
        raise StressCalculationError(
            "The market shock must be finite."
        )

    if shock < -1.0:
        raise StressCalculationError(
            "The market shock cannot be less than -100%."
        )

    return shock


def _prepare_portfolio_value(
    initial_portfolio_value: float,
) -> float:
    """Validate the starting portfolio value."""
    try:
        portfolio_value = float(
            initial_portfolio_value
        )
    except (TypeError, ValueError) as error:
        raise StressCalculationError(
            "The starting portfolio value must be numeric."
        ) from error

    if (
        not np.isfinite(portfolio_value)
        or portfolio_value <= 0.0
    ):
        raise StressCalculationError(
            "The starting portfolio value must be greater than zero."
        )

    return portfolio_value


def calculate_stress_test(
    weights: LabeledValues,
    market_shock: float,
    sensitivities: LabeledValues | None = None,
    specific_shocks: LabeledValues | None = None,
    initial_portfolio_value: float = 10_000.0,
) -> StressTestResult:
    """Estimate portfolio results under a modeled market shock."""
    weight_series = _prepare_weights(
        weights
    )

    shock = _prepare_market_shock(
        market_shock
    )

    portfolio_value = _prepare_portfolio_value(
        initial_portfolio_value
    )

    sensitivity_series = _prepare_assumption(
        values=sensitivities,
        tickers=weight_series.index,
        default_value=1.0,
        label="Asset sensitivities",
    )

    specific_shock_series = _prepare_assumption(
        values=specific_shocks,
        tickers=weight_series.index,
        default_value=0.0,
        label="Asset-specific shocks",
    )

    market_component = (
        sensitivity_series
        * shock
    )

    raw_stressed_return = (
        market_component
        + specific_shock_series
    )

    floor_applied = (
        raw_stressed_return < -1.0
    )

    stressed_return = (
        raw_stressed_return
        .clip(lower=-1.0)
    )

    starting_value = (
        weight_series
        * portfolio_value
    )

    stressed_value = (
        starting_value
        * (
            1.0
            + stressed_return
        )
    )

    portfolio_contribution = (
        weight_series
        * stressed_return
    )

    asset_profit_loss = (
        stressed_value
        - starting_value
    )

    asset_results = pd.DataFrame(
        {
            "weight": weight_series,
            "sensitivity": sensitivity_series,
            "market_component": market_component,
            "specific_shock": specific_shock_series,
            "raw_stressed_return": raw_stressed_return,
            "stressed_return": stressed_return,
            "portfolio_contribution": portfolio_contribution,
            "starting_value": starting_value,
            "stressed_value": stressed_value,
            "asset_profit_loss": asset_profit_loss,
            "loss_floor_applied": floor_applied,
        }
    )

    asset_results.index.name = "Ticker"

    portfolio_stressed_return = float(
        portfolio_contribution.sum()
    )

    portfolio_profit_loss = float(
        portfolio_value
        * portfolio_stressed_return
    )

    ending_portfolio_value = float(
        portfolio_value
        + portfolio_profit_loss
    )

    estimated_loss = float(
        max(
            -portfolio_profit_loss,
            0.0,
        )
    )

    estimated_gain = float(
        max(
            portfolio_profit_loss,
            0.0,
        )
    )

    smallest_contribution = float(
        portfolio_contribution.min()
    )

    largest_contribution = float(
        portfolio_contribution.max()
    )

    largest_detractor = (
        str(
            portfolio_contribution.idxmin()
        )
        if smallest_contribution < 0.0
        else "None"
    )

    largest_contributor = (
        str(
            portfolio_contribution.idxmax()
        )
        if largest_contribution > 0.0
        else "None"
    )

    worst_asset = str(
        stressed_return.idxmin()
    )

    metrics: dict[str, float | int | str] = {
        "market_shock": shock,
        "initial_portfolio_value": portfolio_value,
        "portfolio_stressed_return": (
            portfolio_stressed_return
        ),
        "portfolio_profit_loss": (
            portfolio_profit_loss
        ),
        "estimated_loss": estimated_loss,
        "estimated_gain": estimated_gain,
        "ending_portfolio_value": (
            ending_portfolio_value
        ),
        "largest_detractor": largest_detractor,
        "largest_detractor_contribution": (
            min(
                smallest_contribution,
                0.0,
            )
        ),
        "largest_contributor": largest_contributor,
        "largest_contributor_contribution": (
            max(
                largest_contribution,
                0.0,
            )
        ),
        "worst_asset": worst_asset,
        "floor_count": int(
            floor_applied.sum()
        ),
    }

    return StressTestResult(
        asset_results=asset_results,
        metrics=metrics,
    )


def calculate_scenario_comparison(
    weights: LabeledValues,
    sensitivities: LabeledValues | None = None,
    specific_shocks: LabeledValues | None = None,
    initial_portfolio_value: float = 10_000.0,
    scenarios: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Compare portfolio results across multiple scenarios."""
    if scenarios is None:
        scenario_values = {
            name: scenario.market_shock
            for name, scenario in SCENARIOS.items()
        }
    elif not isinstance(scenarios, Mapping):
        raise StressCalculationError(
            "Scenarios must be supplied as a mapping."
        )
    elif len(scenarios) == 0:
        raise StressCalculationError(
            "At least one scenario is required."
        )
    else:
        scenario_values = dict(
            scenarios
        )

    comparison_rows: list[dict[str, float | str]] = []

    for name, scenario_shock in scenario_values.items():
        result = calculate_stress_test(
            weights=weights,
            market_shock=scenario_shock,
            sensitivities=sensitivities,
            specific_shocks=specific_shocks,
            initial_portfolio_value=(
                initial_portfolio_value
            ),
        )

        comparison_rows.append(
            {
                "Scenario": str(name),
                "market_shock": float(
                    result.metrics[
                        "market_shock"
                    ]
                ),
                "portfolio_stressed_return": float(
                    result.metrics[
                        "portfolio_stressed_return"
                    ]
                ),
                "portfolio_profit_loss": float(
                    result.metrics[
                        "portfolio_profit_loss"
                    ]
                ),
                "estimated_loss": float(
                    result.metrics[
                        "estimated_loss"
                    ]
                ),
                "ending_portfolio_value": float(
                    result.metrics[
                        "ending_portfolio_value"
                    ]
                ),
                "largest_detractor": str(
                    result.metrics[
                        "largest_detractor"
                    ]
                ),
            }
        )

    comparison = (
        pd.DataFrame(
            comparison_rows
        )
        .set_index("Scenario")
    )

    return comparison