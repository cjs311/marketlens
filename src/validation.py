"""Input-validation utilities for MarketLens."""

from __future__ import annotations

from datetime import date
import re


MAX_TICKERS = 10

TICKER_PATTERN = re.compile(
    r"^[A-Z0-9^][A-Z0-9.\-=^]{0,19}$"
)


class InputValidationError(ValueError):
    """Raised when a user-provided analysis input is invalid."""


def parse_ticker_input(
    raw_value: str,
    max_tickers: int = MAX_TICKERS,
) -> tuple[str, ...]:
    """Convert comma, semicolon, or whitespace-separated input into tickers.

    Symbols are converted to uppercase. Duplicate symbols and unsupported
    characters are rejected so that the user receives a clear explanation
    before a market-data request is attempted.
    """
    if not raw_value or not raw_value.strip():
        raise InputValidationError(
            "Enter at least one ticker symbol."
        )

    tokens = [
        token
        for token in re.split(r"[\s,;]+", raw_value.upper().strip())
        if token
    ]

    if len(tokens) > max_tickers:
        ticker_word = "ticker" if max_tickers == 1 else "tickers"

        raise InputValidationError(
            f"Enter no more than {max_tickers} {ticker_word}."
        )

    duplicates: list[str] = []
    seen: set[str] = set()

    for ticker in tokens:
        if ticker in seen and ticker not in duplicates:
            duplicates.append(ticker)

        seen.add(ticker)

    if duplicates:
        duplicate_text = ", ".join(duplicates)

        raise InputValidationError(
            f"Remove duplicate ticker symbols: {duplicate_text}."
        )

    invalid_tickers = [
        ticker
        for ticker in tokens
        if not TICKER_PATTERN.fullmatch(ticker)
    ]

    if invalid_tickers:
        invalid_text = ", ".join(invalid_tickers)

        raise InputValidationError(
            "These ticker symbols contain unsupported characters or have an "
            f"invalid format: {invalid_text}."
        )

    return tuple(tokens)


def parse_benchmark(raw_value: str) -> str:
    """Validate and return exactly one benchmark ticker."""
    tickers = parse_ticker_input(raw_value, max_tickers=1)

    if len(tickers) != 1:
        raise InputValidationError(
            "Enter exactly one benchmark ticker."
        )

    return tickers[0]


def validate_date_range(
    start_date: date,
    end_date: date,
    *,
    today: date | None = None,
) -> None:
    """Validate an inclusive historical analysis period."""
    if start_date >= end_date:
        raise InputValidationError(
            "The start date must be earlier than the end date."
        )

    comparison_date = today or date.today()

    if end_date > comparison_date:
        raise InputValidationError(
            "The end date cannot be in the future."
        )