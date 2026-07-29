"""Methodology and limitations page for MarketLens."""

import streamlit as st

from src.ui import page_header

page_header(
    eyebrow="MODEL DOCUMENTATION",
    title="Understand every calculation.",
    description=(
        "Review the assumptions, methods, data limitations, and risk-model "
        "boundaries behind MarketLens portfolio analytics."
    ),
    badge="METHODS & LIMITATIONS",
)
st.markdown(
    """
    MarketLens is an educational market-risk and portfolio-analytics tool.
    It will transform historical adjusted prices into returns, performance
    measurements, risk statistics, visualizations, and downloadable reports.
    """
)

with st.expander("Returns and annualization", expanded=True):
    st.markdown(
        """
        - Daily returns will be calculated from consecutive adjusted prices.
        - Portfolio returns will be calculated from validated asset weights.
        - Annualized calculations will assume **252 trading days per year**.
        - Cumulative performance will represent compounded historical returns.
        """
    )

with st.expander("Risk-adjusted performance"):
    st.markdown(
        """
        - The risk-free rate will be configurable.
        - The initial default will be **0.0% annually**.
        - This is a documented model assumption, not a claim about the
          current market risk-free rate.
        - Sharpe ratio will use total volatility.
        - Sortino ratio will use downside deviation.
        """
    )

with st.expander("Value at Risk and Conditional Value at Risk"):
    st.markdown(
        """
        MarketLens will initially use one-day historical Value at Risk at
        95% and 99% confidence levels. Conditional Value at Risk will estimate
        the average loss in observations beyond the selected VaR threshold.

        These measurements are based on the historical sample. They do not
        represent the maximum possible loss.
        """
    )

with st.expander("Stress-testing limitations"):
    st.markdown(
        """
        The MVP stress test will apply user-defined static percentage shocks
        to individual positions. It will not model changing correlations,
        liquidity, volatility, transaction costs, or second-order effects.
        """
    )

with st.expander("Data-source limitations"):
    st.markdown(
        """
        The initial version will retrieve historical information through
        yfinance for educational development. Market data may be delayed,
        incomplete, adjusted, or unavailable. MarketLens will surface missing
        data instead of silently treating it as complete.
        """
    )

st.warning(
    "MarketLens does not place trades, guarantee results, or provide "
    "personalized investment advice."
)