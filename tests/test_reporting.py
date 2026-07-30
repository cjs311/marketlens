"""Tests for MarketLens standalone analysis reports."""

from datetime import UTC, date, datetime

from src.persistence import SavedAnalysisSummary
from src.reporting import (
    analysis_report_filename,
    generate_analysis_report,
)


def test_report_escapes_user_supplied_name() -> None:
    """Report HTML must escape the saved analysis name."""
    summary = SavedAnalysisSummary(
        id=1,
        name="<Core & Growth>",
        created_at=datetime(
            2026,
            7,
            29,
            tzinfo=UTC,
        ),
        asset_tickers=(
            "SPY",
            "QQQ",
        ),
        benchmark="SPY",
        requested_start=date(
            2025,
            7,
            29,
        ),
        requested_end=date(
            2026,
            7,
            29,
        ),
        actual_start=date(
            2025,
            7,
            29,
        ),
        actual_end=date(
            2026,
            7,
            28,
        ),
        weights={
            "SPY": 0.55,
            "QQQ": 0.45,
        },
        portfolio_total_return=0.18,
        portfolio_annualized_return=0.17,
        portfolio_annualized_volatility=0.13,
    )

    report = generate_analysis_report(
        summary
    )

    assert "<Core & Growth>" not in report
    assert "&lt;Core &amp; Growth&gt;" in report
    assert "55.00%" in report
    assert "Educational analytics only" in report


def test_report_filename_is_safe() -> None:
    """Generated filenames should contain a stable readable slug."""
    assert (
        analysis_report_filename(
            "Core / Growth Portfolio!"
        )
        == "marketlens-core-growth-portfolio.html"
    )
