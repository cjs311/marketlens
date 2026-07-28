"""Tests for MarketLens user-input validation."""

from datetime import date

import pytest

from src.validation import (
    InputValidationError,
    parse_benchmark,
    parse_ticker_input,
    validate_date_range,
)


def test_parse_ticker_input_normalizes_symbols() -> None:
    """Ticker input should be trimmed and converted to uppercase."""
    result = parse_ticker_input(" spy, qqq, gld ")

    assert result == ("SPY", "QQQ", "GLD")


def test_parse_ticker_input_supports_common_yahoo_formats() -> None:
    """Common separators and Yahoo-style ticker characters should work."""
    result = parse_ticker_input(
        "BRK-B BTC-USD;EURUSD=X ^GSPC"
    )

    assert result == (
        "BRK-B",
        "BTC-USD",
        "EURUSD=X",
        "^GSPC",
    )


def test_parse_ticker_input_rejects_empty_input() -> None:
    """At least one ticker must be supplied."""
    with pytest.raises(
        InputValidationError,
        match="at least one",
    ):
        parse_ticker_input("   ")


def test_parse_ticker_input_rejects_duplicates() -> None:
    """Duplicate ticker symbols should be reported."""
    with pytest.raises(
        InputValidationError,
        match="duplicate",
    ):
        parse_ticker_input("SPY, QQQ, spy")


def test_parse_ticker_input_rejects_more_than_ten() -> None:
    """The MVP must support no more than ten portfolio assets."""
    raw_value = ", ".join(
        f"TEST{number}"
        for number in range(11)
    )

    with pytest.raises(
        InputValidationError,
        match="no more than 10",
    ):
        parse_ticker_input(raw_value)


def test_parse_ticker_input_rejects_invalid_characters() -> None:
    """Unsupported characters should fail before a provider request."""
    with pytest.raises(
        InputValidationError,
        match="unsupported",
    ):
        parse_ticker_input("SPY, AAPL$")


def test_parse_benchmark_accepts_one_symbol() -> None:
    """A single valid benchmark should be returned."""
    assert parse_benchmark(" spy ") == "SPY"


def test_parse_benchmark_rejects_multiple_symbols() -> None:
    """Only one benchmark may be selected."""
    with pytest.raises(InputValidationError):
        parse_benchmark("SPY, QQQ")


def test_validate_date_range_accepts_valid_dates() -> None:
    """A historical start date before the end date should pass."""
    validate_date_range(
        date(2025, 1, 1),
        date(2026, 1, 1),
        today=date(2026, 7, 28),
    )


def test_validate_date_range_requires_start_before_end() -> None:
    """Equal and reversed date ranges should both be rejected."""
    invalid_ranges = [
        (
            date(2026, 1, 1),
            date(2026, 1, 1),
        ),
        (
            date(2026, 2, 1),
            date(2026, 1, 1),
        ),
    ]

    for start_date, end_date in invalid_ranges:
        with pytest.raises(
            InputValidationError,
            match="earlier",
        ):
            validate_date_range(
                start_date,
                end_date,
                today=date(2026, 7, 28),
            )


def test_validate_date_range_rejects_future_end_date() -> None:
    """The selected analysis must not end in the future."""
    with pytest.raises(
        InputValidationError,
        match="future",
    ):
        validate_date_range(
            date(2026, 1, 1),
            date(2026, 7, 29),
            today=date(2026, 7, 28),
        )