"""Portfolio-composition calculations for MarketLens."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
WeightInput = pd.Series | Mapping[str, float]


class CompositionCalculationError(ValueError):
    """Raised when composition analytics cannot be calculated."""


@dataclass(frozen=True)
class CompositionAnalytics:
    """Composition statistics and chart-ready portfolio data."""

    allocation: pd.DataFrame
    asset_metrics: pd.DataFrame
    correlation: pd.DataFrame
    covariance: pd.DataFrame
    volatility_contribution: pd.DataFrame
    metrics: dict[str, float | int | str]


def _prepare_asset_returns(
    asset_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and return numeric asset returns."""
    if (
        not isinstance(asset_returns, pd.DataFrame)
        or asset_returns.empty
        or asset_returns.shape[1] == 0
    ):
        raise CompositionCalculationError(
            "Asset returns must contain at least one asset."
        )

    if len(asset_returns) < 2:
        raise CompositionCalculationError(
            "Asset returns must contain at least two observations."
        )

    if asset_returns.columns.has_duplicates:
        raise CompositionCalculationError(
            "Asset-return tickers must be unique."
        )

    returns = (
        asset_returns
        .copy()
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
        .astype("float64")
    )

    if returns.isna().any().any():
        raise CompositionCalculationError(
            "Asset returns cannot contain missing values."
        )

    if not np.isfinite(
        returns.to_numpy(dtype="float64")
    ).all():
        raise CompositionCalculationError(
            "Asset returns cannot contain infinite values."
        )

    if (returns <= -1.0).any().any():
        raise CompositionCalculationError(
            "Asset returns cannot contain a loss of 100% or more."
        )

    return returns


def _prepare_weights(
    weights: WeightInput,
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
        raise CompositionCalculationError(
            "Portfolio weights must be a labeled series or mapping."
        )

    if weight_series.empty:
        raise CompositionCalculationError(
            "Portfolio weights cannot be empty."
        )

    if weight_series.index.has_duplicates:
        raise CompositionCalculationError(
            "Portfolio-weight tickers must be unique."
        )

    weight_series = pd.to_numeric(
        weight_series,
        errors="coerce",
    ).astype("float64")

    if weight_series.isna().any():
        raise CompositionCalculationError(
            "Portfolio weights must be numeric."
        )

    if not np.isfinite(
        weight_series.to_numpy(dtype="float64")
    ).all():
        raise CompositionCalculationError(
            "Portfolio weights must be finite."
        )

    if (weight_series < 0.0).any():
        raise CompositionCalculationError(
            "Portfolio weights cannot be negative."
        )

    total_weight = float(
        weight_series.sum()
    )

    if not np.isclose(
        total_weight,
        1.0,
        atol=1e-8,
        rtol=0.0,
    ):
        raise CompositionCalculationError(
            "Portfolio weights must total 100%."
        )

    return weight_series.rename("weight")


def _prepare_inputs(
    asset_returns: pd.DataFrame,
    weights: WeightInput,
) -> tuple[pd.DataFrame, pd.Series]:
    """Validate and align asset returns with portfolio weights."""
    returns = _prepare_asset_returns(
        asset_returns
    )

    weight_series = _prepare_weights(
        weights
    )

    return_tickers = set(
        returns.columns
    )

    weight_tickers = set(
        weight_series.index
    )

    if return_tickers != weight_tickers:
        missing_weights = (
            return_tickers
            - weight_tickers
        )

        extra_weights = (
            weight_tickers
            - return_tickers
        )

        details: list[str] = []

        if missing_weights:
            details.append(
                "missing weights for "
                + ", ".join(
                    sorted(
                        map(
                            str,
                            missing_weights,
                        )
                    )
                )
            )

        if extra_weights:
            details.append(
                "weights without return data for "
                + ", ".join(
                    sorted(
                        map(
                            str,
                            extra_weights,
                        )
                    )
                )
            )

        raise CompositionCalculationError(
            "Portfolio weights must match the asset-return tickers: "
            + "; ".join(details)
            + "."
        )

    weight_series = (
        weight_series
        .reindex(
            returns.columns
        )
        .astype("float64")
    )

    return returns, weight_series


def calculate_concentration_metrics(
    weights: WeightInput,
) -> dict[str, float | int | str]:
    """Calculate portfolio concentration measurements."""
    weight_series = _prepare_weights(
        weights
    )

    sorted_weights = weight_series.sort_values(
        ascending=False
    )

    largest_ticker = str(
        sorted_weights.index[0]
    )

    largest_weight = float(
        sorted_weights.iloc[0]
    )

    top_two_weight = float(
        sorted_weights.iloc[:2].sum()
    )

    hhi = float(
        np.square(
            weight_series.to_numpy(
                dtype="float64"
            )
        ).sum()
    )

    effective_assets = (
        float(1.0 / hhi)
        if hhi > 0.0
        else float("nan")
    )

    return {
        "asset_count": len(
            weight_series
        ),
        "largest_ticker": largest_ticker,
        "largest_weight": largest_weight,
        "top_two_weight": top_two_weight,
        "hhi": hhi,
        "effective_assets": effective_assets,
    }


def calculate_asset_statistics(
    asset_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate performance statistics for each asset."""
    returns = _prepare_asset_returns(
        asset_returns
    )

    growth = (
        1.0
        + returns
    ).prod()

    total_return = (
        growth
        - 1.0
    )

    annualized_return = (
        growth.pow(
            TRADING_DAYS_PER_YEAR
            / len(returns)
        )
        - 1.0
    )

    annualized_volatility = (
        returns.std(ddof=1)
        * np.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )

    statistics = pd.DataFrame(
        {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "annualized_volatility": annualized_volatility,
            "average_daily_return": returns.mean(),
            "best_day": returns.max(),
            "worst_day": returns.min(),
            "positive_day_ratio": (
                returns > 0.0
            ).mean(),
            "observations": len(
                returns
            ),
        }
    )

    statistics.index.name = "Ticker"

    return statistics.astype(
        {
            "total_return": "float64",
            "annualized_return": "float64",
            "annualized_volatility": "float64",
            "average_daily_return": "float64",
            "best_day": "float64",
            "worst_day": "float64",
            "positive_day_ratio": "float64",
            "observations": "int64",
        }
    )


def calculate_correlation_matrix(
    asset_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Return the Pearson correlation matrix for asset returns."""
    returns = _prepare_asset_returns(
        asset_returns
    )

    correlation = returns.corr()

    correlation.index.name = "Ticker"
    correlation.columns.name = "Ticker"

    return correlation


def calculate_volatility_contribution(
    asset_returns: pd.DataFrame,
    weights: WeightInput,
) -> pd.DataFrame:
    """Calculate each asset's component contribution to portfolio volatility."""
    returns, weight_series = _prepare_inputs(
        asset_returns,
        weights,
    )

    covariance = returns.cov()

    weight_values = weight_series.to_numpy(
        dtype="float64"
    )

    covariance_values = covariance.to_numpy(
        dtype="float64"
    )

    portfolio_daily_variance = float(
        weight_values
        @ covariance_values
        @ weight_values
    )

    standalone_annualized_volatility = (
        returns.std(ddof=1)
        * np.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )

    if (
        portfolio_daily_variance <= 0.0
        or np.isclose(
            portfolio_daily_variance,
            0.0,
            atol=np.finfo("float64").eps,
            rtol=0.0,
        )
    ):
        marginal_annualized_volatility = pd.Series(
            np.nan,
            index=returns.columns,
            dtype="float64",
        )

        annualized_volatility_contribution = pd.Series(
            np.nan,
            index=returns.columns,
            dtype="float64",
        )

        contribution_percentage = pd.Series(
            np.nan,
            index=returns.columns,
            dtype="float64",
        )
    else:
        portfolio_daily_volatility = float(
            np.sqrt(
                portfolio_daily_variance
            )
        )

        marginal_daily_volatility = (
            covariance_values
            @ weight_values
            / portfolio_daily_volatility
        )

        component_daily_volatility = (
            weight_values
            * marginal_daily_volatility
        )

        marginal_annualized_volatility = pd.Series(
            marginal_daily_volatility
            * np.sqrt(
                TRADING_DAYS_PER_YEAR
            ),
            index=returns.columns,
            dtype="float64",
        )

        annualized_volatility_contribution = pd.Series(
            component_daily_volatility
            * np.sqrt(
                TRADING_DAYS_PER_YEAR
            ),
            index=returns.columns,
            dtype="float64",
        )

        contribution_percentage = pd.Series(
            component_daily_volatility
            / portfolio_daily_volatility,
            index=returns.columns,
            dtype="float64",
        )

    contribution = pd.DataFrame(
        {
            "weight": weight_series,
            "standalone_annualized_volatility": (
                standalone_annualized_volatility
            ),
            "marginal_annualized_volatility": (
                marginal_annualized_volatility
            ),
            "annualized_volatility_contribution": (
                annualized_volatility_contribution
            ),
            "contribution_percentage": (
                contribution_percentage
            ),
        }
    )

    contribution.index.name = "Ticker"

    return contribution


def calculate_composition_analytics(
    asset_returns: pd.DataFrame,
    weights: WeightInput,
) -> CompositionAnalytics:
    """Calculate complete portfolio-composition analytics."""
    returns, weight_series = _prepare_inputs(
        asset_returns,
        weights,
    )

    allocation = pd.DataFrame(
        {
            "weight": weight_series,
        }
    )

    allocation.index.name = "Ticker"

    asset_metrics = calculate_asset_statistics(
        returns
    )

    correlation = calculate_correlation_matrix(
        returns
    )

    covariance = returns.cov()

    covariance.index.name = "Ticker"
    covariance.columns.name = "Ticker"

    volatility_contribution = (
        calculate_volatility_contribution(
            returns,
            weight_series,
        )
    )

    metrics = calculate_concentration_metrics(
        weight_series
    )

    weighted_average_asset_volatility = float(
        (
            weight_series
            * asset_metrics[
                "annualized_volatility"
            ]
        ).sum()
    )

    weight_values = weight_series.to_numpy(
        dtype="float64"
    )

    portfolio_annualized_volatility = float(
        np.sqrt(
            weight_values
            @ covariance.to_numpy(
                dtype="float64"
            )
            @ weight_values
        )
        * np.sqrt(
            TRADING_DAYS_PER_YEAR
        )
    )

    if np.isclose(
        portfolio_annualized_volatility,
        0.0,
        atol=np.finfo("float64").eps,
        rtol=0.0,
    ):
        diversification_ratio = float(
            "nan"
        )
    else:
        diversification_ratio = (
            weighted_average_asset_volatility
            / portfolio_annualized_volatility
        )

    if len(correlation) > 1:
        upper_triangle = (
            correlation
            .to_numpy(
                dtype="float64"
            )[
                np.triu_indices(
                    len(correlation),
                    k=1,
                )
            ]
        )

        finite_correlations = upper_triangle[
            np.isfinite(
                upper_triangle
            )
        ]

        average_pairwise_correlation = (
            float(
                finite_correlations.mean()
            )
            if len(finite_correlations) > 0
            else float("nan")
        )
    else:
        average_pairwise_correlation = float(
            "nan"
        )

    metrics.update(
        {
            "weighted_average_asset_volatility": (
                weighted_average_asset_volatility
            ),
            "portfolio_annualized_volatility": (
                portfolio_annualized_volatility
            ),
            "diversification_ratio": (
                diversification_ratio
            ),
            "average_pairwise_correlation": (
                average_pairwise_correlation
            ),
        }
    )

    return CompositionAnalytics(
        allocation=allocation,
        asset_metrics=asset_metrics,
        correlation=correlation,
        covariance=covariance,
        volatility_contribution=(
            volatility_contribution
        ),
        metrics=metrics,
    )