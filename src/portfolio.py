"""Portfolio-weight and performance calculations for MarketLens."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252
WEIGHT_TOLERANCE = 0.0001


class PortfolioCalculationError(ValueError):
    """Raised when portfolio inputs cannot produce valid analytics."""


@dataclass(frozen=True)
class PortfolioAnalytics:
    """Calculated portfolio and benchmark performance information."""

    weights: pd.Series
    asset_returns: pd.DataFrame
    portfolio_returns: pd.Series
    benchmark_returns: pd.Series
    comparison_returns: pd.DataFrame
    performance_index: pd.DataFrame
    metrics: pd.DataFrame


def create_equal_weights(
    asset_tickers: Sequence[str],
) -> pd.Series:
    """Return equal decimal weights for the supplied assets."""
    symbols = tuple(
        str(ticker).upper()
        for ticker in asset_tickers
    )

    if not symbols:
        raise PortfolioCalculationError(
            "At least one portfolio asset is required."
        )

    if len(set(symbols)) != len(symbols):
        raise PortfolioCalculationError(
            "Portfolio asset symbols must be unique."
        )

    equal_weight = 1.0 / len(symbols)

    return pd.Series(
        equal_weight,
        index=symbols,
        name="Weight",
        dtype="float64",
    )


def validate_weights(
    raw_weights: Mapping[str, float] | pd.Series,
    asset_tickers: Sequence[str],
    *,
    normalize: bool = False,
    tolerance: float = WEIGHT_TOLERANCE,
) -> pd.Series:
    """Validate and return ordered decimal portfolio weights.

    MarketLens initially supports long-only portfolios. When normalization is
    enabled, nonnegative weights are proportionally rescaled to total 100%.
    """
    symbols = tuple(
        str(ticker).upper()
        for ticker in asset_tickers
    )

    if not symbols:
        raise PortfolioCalculationError(
            "At least one portfolio asset is required."
        )

    if len(set(symbols)) != len(symbols):
        raise PortfolioCalculationError(
            "Portfolio asset symbols must be unique."
        )

    if isinstance(raw_weights, pd.Series):
        weights = raw_weights.copy()
    else:
        weights = pd.Series(
            raw_weights,
            dtype="object",
        )

    if weights.empty:
        raise PortfolioCalculationError(
            "Enter a weight for every portfolio asset."
        )

    weights.index = [
        str(index_value).upper()
        for index_value in weights.index
    ]

    duplicate_symbols = (
        weights.index[
            weights.index.duplicated()
        ]
        .unique()
        .tolist()
    )

    if duplicate_symbols:
        raise PortfolioCalculationError(
            "Duplicate portfolio weights were supplied for: "
            f"{', '.join(duplicate_symbols)}."
        )

    missing_symbols = [
        symbol
        for symbol in symbols
        if symbol not in weights.index
    ]

    unexpected_symbols = [
        symbol
        for symbol in weights.index
        if symbol not in symbols
    ]

    if missing_symbols:
        raise PortfolioCalculationError(
            "Weights are missing for: "
            f"{', '.join(missing_symbols)}."
        )

    if unexpected_symbols:
        raise PortfolioCalculationError(
            "Weights were supplied for unexpected assets: "
            f"{', '.join(unexpected_symbols)}."
        )

    weights = pd.to_numeric(
        weights.loc[list(symbols)],
        errors="coerce",
    ).astype("float64")

    invalid_symbols = weights.index[
        weights.isna() | ~np.isfinite(weights)
    ].tolist()

    if invalid_symbols:
        raise PortfolioCalculationError(
            "Enter valid numeric weights for: "
            f"{', '.join(invalid_symbols)}."
        )

    negative_symbols = weights.index[
        weights < 0.0
    ].tolist()

    if negative_symbols:
        raise PortfolioCalculationError(
            "Negative weights are not supported in the MarketLens MVP. "
            "Update these assets: "
            f"{', '.join(negative_symbols)}."
        )

    total_weight = float(weights.sum())

    if total_weight <= 0.0:
        raise PortfolioCalculationError(
            "Portfolio weights must total more than 0%."
        )

    if normalize:
        weights = weights / total_weight
    elif not np.isclose(
        total_weight,
        1.0,
        atol=tolerance,
        rtol=0.0,
    ):
        raise PortfolioCalculationError(
            "Portfolio weights currently total "
            f"{total_weight:.2%}. They must total 100%, or you can enable "
            "automatic normalization."
        )
    else:
        # Remove tiny rounding differences such as 33.33% entered three times.
        weights = weights / total_weight

    weights.name = "Weight"

    return weights


def _summarize_returns(
    daily_returns: pd.Series,
) -> dict[str, float | int]:
    """Calculate core performance measurements for one return series."""
    if daily_returns.empty:
        raise PortfolioCalculationError(
            "At least one daily return is required."
        )

    observations = len(daily_returns)
    ending_growth = float(
        (1.0 + daily_returns).prod()
    )
    total_return = ending_growth - 1.0

    if ending_growth <= 0.0:
        annualized_return = -1.0
    else:
        annualized_return = (
            ending_growth
            ** (
                TRADING_DAYS_PER_YEAR
                / observations
            )
            - 1.0
        )

    annualized_volatility = float(
        daily_returns.std(ddof=1)
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "average_daily_return": float(daily_returns.mean()),
        "best_day": float(daily_returns.max()),
        "worst_day": float(daily_returns.min()),
        "observations": observations,
    }


def calculate_portfolio_analytics(
    prices: pd.DataFrame,
    asset_tickers: Sequence[str],
    benchmark: str,
    weights: Mapping[str, float] | pd.Series,
) -> PortfolioAnalytics:
    """Calculate weighted portfolio and benchmark performance.

    The MVP applies the selected target weights to every daily return. This
    represents a constant-weight portfolio rebalanced daily and does not include
    transaction costs, taxes, slippage, or management fees.
    """
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise PortfolioCalculationError(
            "Adjusted price history is required."
        )

    symbols = tuple(
        str(ticker).upper()
        for ticker in asset_tickers
    )
    benchmark_symbol = str(benchmark).upper()

    validated_weights = validate_weights(
        raw_weights=weights,
        asset_tickers=symbols,
    )

    working_prices = prices.copy()
    working_prices.columns = [
        str(column).upper()
        for column in working_prices.columns
    ]

    required_symbols = tuple(
        dict.fromkeys(
            (*symbols, benchmark_symbol)
        )
    )

    missing_price_columns = [
        symbol
        for symbol in required_symbols
        if symbol not in working_prices.columns
    ]

    if missing_price_columns:
        raise PortfolioCalculationError(
            "Adjusted prices are missing for: "
            f"{', '.join(missing_price_columns)}."
        )

    selected_prices = (
        working_prices
        .loc[:, list(required_symbols)]
        .apply(
            pd.to_numeric,
            errors="coerce",
        )
    )

    if selected_prices.isna().any().any():
        raise PortfolioCalculationError(
            "Portfolio calculations cannot use missing adjusted prices."
        )

    if not np.isfinite(
        selected_prices.to_numpy(dtype="float64")
    ).all():
        raise PortfolioCalculationError(
            "Portfolio calculations cannot use infinite adjusted prices."
        )

    if (selected_prices <= 0.0).any().any():
        raise PortfolioCalculationError(
            "Adjusted prices must be greater than zero."
        )

    if len(selected_prices) < 2:
        raise PortfolioCalculationError(
            "At least two adjusted-price observations are required."
        )

    all_returns = (
        selected_prices
        .pct_change(fill_method=None)
        .iloc[1:]
    )

    if all_returns.empty:
        raise PortfolioCalculationError(
            "The selected prices did not produce daily returns."
        )

    if not np.isfinite(
        all_returns.to_numpy(dtype="float64")
    ).all():
        raise PortfolioCalculationError(
            "The selected prices produced invalid daily returns."
        )

    asset_returns = all_returns.loc[:, list(symbols)]

    portfolio_returns = (
        asset_returns
        .mul(
            validated_weights,
            axis="columns",
        )
        .sum(axis="columns")
        .rename("Portfolio")
    )

    benchmark_returns = (
        all_returns[benchmark_symbol]
        .rename("Benchmark")
    )

    comparison_returns = pd.concat(
        [
            portfolio_returns,
            benchmark_returns,
        ],
        axis="columns",
    )

    compounded_index = (
        (1.0 + comparison_returns)
        .cumprod()
        .multiply(100.0)
    )

    starting_index = pd.DataFrame(
        {
            "Portfolio": [100.0],
            "Benchmark": [100.0],
        },
        index=selected_prices.index[:1],
    )

    performance_index = pd.concat(
        [
            starting_index,
            compounded_index,
        ]
    )

    performance_index.index.name = selected_prices.index.name

    metrics = pd.DataFrame(
        {
            "Portfolio": _summarize_returns(
                portfolio_returns
            ),
            "Benchmark": _summarize_returns(
                benchmark_returns
            ),
        }
    ).transpose()

    metrics.index.name = "Series"

    return PortfolioAnalytics(
        weights=validated_weights,
        asset_returns=asset_returns,
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
        comparison_returns=comparison_returns,
        performance_index=performance_index,
        metrics=metrics,
    )