"""Main entry point and navigation configuration for MarketLens."""

from pathlib import Path

import streamlit as st
from src.ui import (
    inject_styles,
    install_plotly_theme,
    render_sidebar_brand,
)


PROJECT_ROOT = Path(__file__).resolve().parent
PAGES_DIRECTORY = PROJECT_ROOT / "pages"


st.set_page_config(
    page_title="MarketLens",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
install_plotly_theme()
inject_styles()
render_sidebar_brand()


pages = {
    "Portfolio Analytics": [
        st.Page(
            PAGES_DIRECTORY / "overview.py",
            title="Overview",
            icon="📊",
            default=True,
        ),
        st.Page(
            PAGES_DIRECTORY / "risk_analysis.py",
            title="Risk Analysis",
            icon="⚠️",
        ),
        st.Page(
            PAGES_DIRECTORY / "portfolio.py",
            title="Portfolio Composition",
            icon="🧩",
        ),
        st.Page(
            PAGES_DIRECTORY / "stress_testing.py",
            title="Stress Testing",
            icon="🧪",
        ),
        st.Page(
            PAGES_DIRECTORY / "saved_analyses.py",
            title="Saved Analyses",
            icon="💾",
        ),
    ],
    "Project Information": [
        st.Page(
            PAGES_DIRECTORY / "methodology.py",
            title="Methodology",
            icon="📘",
        ),
    ],
}


navigation = st.navigation(pages)

with st.sidebar:
    st.divider()
    st.caption("MarketLens MVP")
    st.caption("Educational analytics — not financial advice")

navigation.run()