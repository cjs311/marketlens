"""Downside-risk calculations for MarketLens."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 252


class RiskCalculationError(ValueError):
    """Raised when return data cannot produce valid risk analytics."""


@dataclass(frozen=True)
class RiskAnalytics:
    """Risk measurements and time series for one return stream."""

    daily_returns: pd.Series
    wealth_index: pd.Series
    drawdown: pd.Series
    rolling_volatility: pd.Series
    metrics: dict[str, float | int]


@dataclass(frozen=True)
class RiskComparison:
    """Portfolio and benchmark risk analytics on aligned dates."""

    portfolio: RiskAnalytics
    benchmark: RiskAnalytics
    metrics: pd.DataFrame
    drawdown: pd.DataFrame
    rolling_volatility: pd.DataFrame


def _prepare_returns(
    daily_returns: pd.Series,
    *,
    label: str = "Daily returns",
) -> pd.Series:
    """Validate and return a numeric daily-return series."""
    if not isinstance(daily_returns, pd.Series) or daily_returns.empty:
        raise RiskCalculationError(
            f"{label} must contain at least two observations."
        )

    returns = pd.to_numeric(
        daily_returns.copy(),
        errors="coerce",
    ).astype("float64")

    if len(returns) < 2:
        raise RiskCalculationError(
            f"{label} must contain at least two observations."
        )

    if returns.isna().any():
        raise RiskCalculationError(
            f"{label} cannot contain missing values."
        )

    if not np.isfinite(
        returns.to_numpy(dtype="float64")
    ).all():
        raise RiskCalculationError(
            f"{label} cannot contain infinite values."
        )

    if (returns <= -1.0).any():
        raise RiskCalculationError(
            f"{label} cannot contain a loss of 100% or more."
        )

    returns.name = daily_returns.name or label

    return returns


def _validate_annual_risk_free_rate(
    annual_risk_free_rate: float,
) -> float:
    """Validate an annual decimal risk-free rate."""
    try:
        rate = float(annual_risk_free_rate)
    except (TypeError, ValueError) as error:
        raise RiskCalculationError(
            "The annual risk-free rate must be numeric."
        ) from error

    if not np.isfinite(rate) or rate <= -1.0:
        raise RiskCalculationError(
            "The annual risk-free rate must be finite and greater than -100%."
        )

    return rate


def _validate_confidence_level(
    confidence_level: float,
) -> float:
    """Validate a decimal historical-risk confidence level."""
    try:
        confidence = float(confidence_level)
    except (TypeError, ValueError) as error:
        raise RiskCalculationError(
            "The confidence level must be numeric."
        ) from error

    if (
        not np.isfinite(confidence)
        or not 0.0 < confidence < 1.0
    ):
        raise RiskCalculationError(
            "The confidence level must be greater than 0% and less than 100%."
        )

    return confidence


def _daily_risk_free_rate(
    annual_risk_free_rate: float,
) -> float:
    """Convert an effective annual rate into an effective daily rate."""
    annual_rate = _validate_annual_risk_free_rate(
        annual_risk_free_rate
    )

    return (
        (1.0 + annual_rate)
        ** (1.0 / TRADING_DAYS_PER_YEAR)
        - 1.0
    )


def calculate_drawdown(
    daily_returns: pd.Series,
) -> pd.Series:
    """Return the percentage decline from the prior running wealth peak."""
    returns = _prepare_returns(daily_returns)

    wealth = (
        (1.0 + returns)
        .cumprod()
    )

    running_peak = (
        wealth
        .cummax()
        .clip(lower=1.0)
    )

    drawdown = (
        wealth
        .divide(running_peak)
        .subtract(1.0)
        .rename("Drawdown")
    )

    return drawdown.mask(
        np.isclose(
            drawdown,
            0.0,
            atol=1e-12,
            rtol=0.0,
        ),
        0.0,
    )


def calculate_annualized_volatility(
    daily_returns: pd.Series,
) -> float:
    """Return sample volatility annualized with 252 trading days."""
    returns = _prepare_returns(daily_returns)

    return float(
        returns.std(ddof=1)
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )


def calculate_downside_deviation(
    daily_returns: pd.Series,
    annual_risk_free_rate: float = 0.0,
) -> float:
    """Return annualized downside deviation below the daily risk-free rate."""
    returns = _prepare_returns(daily_returns)

    daily_risk_free_rate = _daily_risk_free_rate(
        annual_risk_free_rate
    )

    excess_returns = (
        returns
        - daily_risk_free_rate
    )

    downside_returns = np.minimum(
        excess_returns.to_numpy(dtype="float64"),
        0.0,
    )

    return float(
        np.sqrt(
            np.mean(
                np.square(downside_returns)
            )
        )
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )


def calculate_sharpe_ratio(
    daily_returns: pd.Series,
    annual_risk_free_rate: float = 0.0,
) -> float:
    """Return annualized excess return divided by annualized volatility."""
    returns = _prepare_returns(daily_returns)

    daily_risk_free_rate = _daily_risk_free_rate(
        annual_risk_free_rate
    )

    excess_returns = (
        returns
        - daily_risk_free_rate
    )

    annualized_excess_return = float(
        excess_returns.mean()
        * TRADING_DAYS_PER_YEAR
    )

    annualized_volatility = float(
        returns.std(ddof=1)
        * np.sqrt(TRADING_DAYS_PER_YEAR)
    )

    if np.isclose(
        annualized_volatility,
        0.0,
        atol=np.finfo("float64").eps,
        rtol=0.0,
    ):
        return float("nan")

    return (
        annualized_excess_return
        / annualized_volatility
    )


def calculate_sortino_ratio(
    daily_returns: pd.Series,
    annual_risk_free_rate: float = 0.0,
) -> float:
    """Return annualized excess return divided by downside deviation."""
    returns = _prepare_returns(daily_returns)

    daily_risk_free_rate = _daily_risk_free_rate(
        annual_risk_free_rate
    )

    excess_returns = (
        returns
        - daily_risk_free_rate
    )

    annualized_excess_return = float(
        excess_returns.mean()
        * TRADING_DAYS_PER_YEAR
    )

    downside_deviation = calculate_downside_deviation(
        returns,
        annual_risk_free_rate=annual_risk_free_rate,
    )

    if np.isclose(
        downside_deviation,
        0.0,
        atol=np.finfo("float64").eps,
        rtol=0.0,
    ):
        return float("nan")

    return (
        annualized_excess_return
        / downside_deviation
    )


def calculate_beta(
    asset_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """Return covariance with the benchmark divided by benchmark variance."""
    asset = _prepare_returns(
        asset_returns,
        label="Asset returns",
    )

    benchmark = _prepare_returns(
        benchmark_returns,
        label="Benchmark returns",
    )

    if not asset.index.equals(
        benchmark.index
    ):
        raise RiskCalculationError(
            "Asset and benchmark returns must use the same aligned dates."
        )

    benchmark_variance = float(
        benchmark.var(ddof=1)
    )

    if np.isclose(
        benchmark_variance,
        0.0,
        atol=np.finfo("float64").eps,
        rtol=0.0,
    ):
        return float("nan")

    covariance = float(
        asset.cov(benchmark)
    )

    return (
        covariance
        / benchmark_variance
    )


def calculate_historical_var(
    daily_returns: pd.Series,
    confidence_level: float = 0.95,
) -> float:
    """Return one-day historical VaR as a positive loss magnitude."""
    returns = _prepare_returns(daily_returns)

    confidence = _validate_confidence_level(
        confidence_level
    )

    return_threshold = float(
        returns.quantile(
            1.0 - confidence
        )
    )

    return max(
        0.0,
        -return_threshold,
    )


def calculate_historical_cvar(
    daily_returns: pd.Series,
    confidence_level: float = 0.95,
) -> float:
    """Return average loss at or beyond the historical VaR threshold."""
    returns = _prepare_returns(daily_returns)

    confidence = _validate_confidence_level(
        confidence_level
    )

    return_threshold = float(
        returns.quantile(
            1.0 - confidence
        )
    )

    tail_returns = returns[
        returns <= return_threshold
    ]

    if tail_returns.empty:
        return 0.0

    return max(
        0.0,
        -float(tail_returns.mean()),
    )


def calculate_rolling_volatility(
    daily_returns: pd.Series,
    window: int = 21,
) -> pd.Series:
    """Return rolling volatility annualized with 252 trading days."""
    returns = _prepare_returns(daily_returns)

    if (
        not isinstance(window, int)
        or window < 2
    ):
        raise RiskCalculationError(
            "The rolling-volatility window must be an integer of at least 2."
        )

    return (
        returns
        .rolling(
            window=window,
            min_periods=window,
        )
        .std(ddof=1)
        .multiply(
            np.sqrt(
                TRADING_DAYS_PER_YEAR
            )
        )
        .rename("Rolling volatility")
    )


def _maximum_drawdown_duration(
    drawdown: pd.Series,
) -> int:
    """Return the longest consecutive underwater period."""
    longest_duration = 0
    current_duration = 0

    for is_underwater in (
        drawdown < -1e-12
    ):
        if is_underwater:
            current_duration += 1

            longest_duration = max(
                longest_duration,
                current_duration,
            )
        else:
            current_duration = 0

    return longest_duration


def calculate_risk_analytics(
    daily_returns: pd.Series,
    *,
    annual_risk_free_rate: float = 0.0,
    confidence_level: float = 0.95,
    rolling_window: int = 21,
) -> RiskAnalytics:
    """Calculate risk metrics and chart-ready series."""
    returns = _prepare_returns(daily_returns)

    annual_rate = _validate_annual_risk_free_rate(
        annual_risk_free_rate
    )

    confidence = _validate_confidence_level(
        confidence_level
    )

    wealth_index = (
        (1.0 + returns)
        .cumprod()
        .multiply(100.0)
        .rename("Wealth index")
    )

    drawdown = calculate_drawdown(
        returns
    )

    rolling_volatility = calculate_rolling_volatility(
        returns,
        window=rolling_window,
    )

    metrics: dict[str, float | int] = {
        "annualized_volatility": (
            calculate_annualized_volatility(
                returns
            )
        ),
        "downside_deviation": (
            calculate_downside_deviation(
                returns,
                annual_risk_free_rate=annual_rate,
            )
        ),
        "sharpe_ratio": (
            calculate_sharpe_ratio(
                returns,
                annual_risk_free_rate=annual_rate,
            )
        ),
        "sortino_ratio": (
            calculate_sortino_ratio(
                returns,
                annual_risk_free_rate=annual_rate,
            )
        ),
        "max_drawdown": float(
            drawdown.min()
        ),
        "current_drawdown": float(
            drawdown.iloc[-1]
        ),
        "max_drawdown_duration": (
            _maximum_drawdown_duration(
                drawdown
            )
        ),
        "historical_var": (
            calculate_historical_var(
                returns,
                confidence_level=confidence,
            )
        ),
        "historical_cvar": (
            calculate_historical_cvar(
                returns,
                confidence_level=confidence,
            )
        ),
        "worst_day": float(
            returns.min()
        ),
        "positive_day_ratio": float(
            (returns > 0.0).mean()
        ),
        "observations": len(
            returns
        ),
    }

    return RiskAnalytics(
        daily_returns=returns,
        wealth_index=wealth_index,
        drawdown=drawdown,
        rolling_volatility=rolling_volatility,
        metrics=metrics,
    )


def calculate_risk_comparison(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    *,
    annual_risk_free_rate: float = 0.0,
    confidence_level: float = 0.95,
    rolling_window: int = 21,
) -> RiskComparison:
    """Calculate aligned portfolio-versus-benchmark risk analytics."""
    portfolio_series = _prepare_returns(
        portfolio_returns,
        label="Portfolio returns",
    )

    benchmark_series = _prepare_returns(
        benchmark_returns,
        label="Benchmark returns",
    )

    if not portfolio_series.index.equals(
        benchmark_series.index
    ):
        raise RiskCalculationError(
            "Portfolio and benchmark returns must use the same aligned dates."
        )

    portfolio = calculate_risk_analytics(
        portfolio_series,
        annual_risk_free_rate=annual_risk_free_rate,
        confidence_level=confidence_level,
        rolling_window=rolling_window,
    )

    benchmark = calculate_risk_analytics(
        benchmark_series,
        annual_risk_free_rate=annual_risk_free_rate,
        confidence_level=confidence_level,
        rolling_window=rolling_window,
    )

    portfolio_beta = calculate_beta(
        portfolio_series,
        benchmark_series,
    )

    benchmark_beta = calculate_beta(
        benchmark_series,
        benchmark_series,
    )

    metrics = pd.DataFrame(
        {
            "Portfolio": {
                **portfolio.metrics,
                "beta": portfolio_beta,
            },
            "Benchmark": {
                **benchmark.metrics,
                "beta": benchmark_beta,
            },
        }
    ).transpose()

    metrics.index.name = "Series"

    drawdown = pd.concat(
        [
            portfolio.drawdown.rename(
                "Portfolio"
            ),
            benchmark.drawdown.rename(
                "Benchmark"
            ),
        ],
        axis="columns",
    )

    rolling_volatility = pd.concat(
        [
            portfolio.rolling_volatility.rename(
                "Portfolio"
            ),
            benchmark.rolling_volatility.rename(
                "Benchmark"
            ),
        ],
        axis="columns",
    )

    return RiskComparison(
        portfolio=portfolio,
        benchmark=benchmark,
        metrics=metrics,
        drawdown=drawdown,
        rolling_volatility=rolling_volatility,
    )