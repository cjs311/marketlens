"""Historical market-data retrieval and preparation for MarketLens."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf


DEFAULT_MINIMUM_OBSERVATIONS = 20


class MarketDataError(RuntimeError):
    """Base exception for market-data retrieval and preparation errors."""


class UnavailableTickerError(MarketDataError):
    """Raised when one or more requested tickers have no usable data."""

    def __init__(self, symbols: Sequence[str]) -> None:
        """Create an error containing the unavailable ticker symbols."""
        self.symbols = tuple(symbols)
        symbol_text = ", ".join(self.symbols)

        super().__init__(
            "No usable adjusted-price history was returned for: "
            f"{symbol_text}. Check the ticker spelling, selected date range, "
            "internet connection, and data-source availability."
        )


class InsufficientDataError(MarketDataError):
    """Raised when too few aligned observations are available."""


@dataclass(frozen=True)
class MarketDataResult:
    """Cleaned price history and its associated data-quality information."""

    prices: pd.DataFrame
    requested_symbols: tuple[str, ...]
    requested_start: date
    requested_end: date
    actual_start: date
    actual_end: date
    missing_values: dict[str, int]
    rows_before_alignment: int
    rows_after_alignment: int

    @property
    def dropped_rows(self) -> int:
        """Return the number of dates removed during cross-asset alignment."""
        return self.rows_before_alignment - self.rows_after_alignment


def extract_adjusted_close(
    raw_data: pd.DataFrame | None,
    requested_symbols: Sequence[str],
) -> pd.DataFrame:
    """Extract auto-adjusted closing prices from a yfinance response.

    yfinance normally returns MultiIndex columns for downloads. This function
    also handles the single-level response shape so that the rest of the
    application receives one consistent ticker-column format.
    """
    if raw_data is None or raw_data.empty:
        raise MarketDataError(
            "The market-data provider returned an empty response."
        )

    if isinstance(raw_data.columns, pd.MultiIndex):
        first_level = raw_data.columns.get_level_values(0)
        second_level = raw_data.columns.get_level_values(1)

        if "Close" in first_level:
            close_prices = raw_data.xs(
                "Close",
                axis=1,
                level=0,
                drop_level=True,
            )
        elif "Close" in second_level:
            close_prices = raw_data.xs(
                "Close",
                axis=1,
                level=1,
                drop_level=True,
            )
        else:
            raise MarketDataError(
                "The response did not contain adjusted closing prices."
            )
    else:
        if "Close" not in raw_data.columns:
            raise MarketDataError(
                "The response did not contain adjusted closing prices."
            )

        if len(requested_symbols) != 1:
            raise MarketDataError(
                "The market-data response did not match the requested tickers."
            )

        close_prices = raw_data.loc[:, ["Close"]].rename(
            columns={"Close": requested_symbols[0]}
        )

    if isinstance(close_prices, pd.Series):
        close_prices = close_prices.to_frame()

    close_prices = close_prices.copy()
    close_prices.columns = [
        str(column).upper()
        for column in close_prices.columns
    ]

    return close_prices.apply(
        pd.to_numeric,
        errors="coerce",
    )


def prepare_price_data(
    close_prices: pd.DataFrame,
    requested_symbols: Sequence[str],
    requested_start: date,
    requested_end: date,
    *,
    minimum_observations: int = DEFAULT_MINIMUM_OBSERVATIONS,
) -> MarketDataResult:
    """Clean, validate, and align adjusted prices to common trading dates."""
    symbols = tuple(
        dict.fromkeys(
            symbol.upper()
            for symbol in requested_symbols
        )
    )

    if not symbols:
        raise MarketDataError(
            "At least one requested symbol is required."
        )

    prices = close_prices.copy()
    prices.columns = [
        str(column).upper()
        for column in prices.columns
    ]

    prices.index = pd.to_datetime(
        prices.index,
        errors="coerce",
    )
    prices = prices.loc[~prices.index.isna()]

    if (
        isinstance(prices.index, pd.DatetimeIndex)
        and prices.index.tz is not None
    ):
        prices.index = prices.index.tz_localize(None)

    prices = (
        prices.loc[~prices.index.duplicated(keep="last")]
        .sort_index()
        .replace([np.inf, -np.inf], np.nan)
    )

    unavailable_symbols = [
        symbol
        for symbol in symbols
        if (
            symbol not in prices.columns
            or not prices[symbol].notna().any()
        )
    ]

    if unavailable_symbols:
        raise UnavailableTickerError(unavailable_symbols)

    prices = prices.loc[:, list(symbols)]
    prices = prices.dropna(how="all")

    if prices.empty:
        raise UnavailableTickerError(symbols)

    rows_before_alignment = len(prices)

    missing_values = {
        symbol: int(prices[symbol].isna().sum())
        for symbol in symbols
    }

    aligned_prices = prices.dropna(how="any")
    rows_after_alignment = len(aligned_prices)

    if rows_after_alignment < minimum_observations:
        raise InsufficientDataError(
            "Only "
            f"{rows_after_alignment} aligned trading-day observations were "
            f"available. At least {minimum_observations} are required. "
            "Choose an earlier start date or different ticker symbols."
        )

    actual_start = aligned_prices.index[0].date()
    actual_end = aligned_prices.index[-1].date()

    return MarketDataResult(
        prices=aligned_prices,
        requested_symbols=symbols,
        requested_start=requested_start,
        requested_end=requested_end,
        actual_start=actual_start,
        actual_end=actual_end,
        missing_values=missing_values,
        rows_before_alignment=rows_before_alignment,
        rows_after_alignment=rows_after_alignment,
    )


def download_market_data(
    asset_tickers: tuple[str, ...],
    benchmark: str,
    start_date: date,
    end_date: date,
) -> MarketDataResult:
    """Download and prepare adjusted daily prices for assets and benchmark."""
    requested_symbols = tuple(
        dict.fromkeys(
            (*asset_tickers, benchmark.upper())
        )
    )

    # yfinance treats its end date as exclusive. Adding one day makes the
    # user's selected end date inclusive.
    provider_end_date = end_date + timedelta(days=1)

    try:
        raw_data = yf.download(
            tickers=list(requested_symbols),
            start=start_date.isoformat(),
            end=provider_end_date.isoformat(),
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=True,
            group_by="column",
            keepna=False,
            repair=False,
            timeout=15,
            multi_level_index=True,
        )
    except Exception as error:
        raise MarketDataError(
            "Market data could not be downloaded. Check your internet "
            "connection and try again."
        ) from error

    if raw_data is None or raw_data.empty:
        raise UnavailableTickerError(requested_symbols)

    close_prices = extract_adjusted_close(
        raw_data,
        requested_symbols,
    )

    return prepare_price_data(
        close_prices=close_prices,
        requested_symbols=requested_symbols,
        requested_start=start_date,
        requested_end=end_date,
    )