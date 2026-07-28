"""Smoke tests for the initial MarketLens development environment."""

from importlib.util import find_spec

import pytest


REQUIRED_PACKAGES = [
    "streamlit",
    "pandas",
    "numpy",
    "plotly",
    "yfinance",
]


@pytest.mark.parametrize("package_name", REQUIRED_PACKAGES)
def test_required_package_is_available(package_name: str) -> None:
    """Confirm that each required third-party package can be located."""
    assert find_spec(package_name) is not None, (
        f"Required package '{package_name}' is not installed."
    )


def test_marketlens_source_package_imports() -> None:
    """Confirm that the MarketLens source package can be imported."""
    import src

    assert src.__doc__
    assert "MarketLens" in src.__doc__