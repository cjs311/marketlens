"""Risk-analysis page for MarketLens."""

import streamlit as st


st.title("⚠️ Risk Analysis")
st.caption("Measure portfolio volatility and downside behavior")

st.info(
    "Risk calculations will be added after the portfolio-return engine is "
    "complete. This page currently previews the planned layout."
)

metric_names = [
    "Annualized Volatility",
    "Maximum Drawdown",
    "Sharpe Ratio",
    "Sortino Ratio",
    "Historical VaR",
    "Historical CVaR",
]

for starting_index in range(0, len(metric_names), 3):
    metric_columns = st.columns(3)

    for column, metric_name in zip(
        metric_columns,
        metric_names[starting_index : starting_index + 3],
    ):
        with column:
            st.metric(metric_name, "Pending")

drawdown_tab, volatility_tab, distribution_tab = st.tabs(
    [
        "Drawdown",
        "Rolling Volatility",
        "Return Distribution",
    ]
)

with drawdown_tab:
    st.subheader("Portfolio drawdown")
    st.write(
        "This chart will show each decline from a previous portfolio peak."
    )

with volatility_tab:
    st.subheader("Rolling annualized volatility")
    st.write(
        "This chart will show how portfolio volatility changes over time."
    )

with distribution_tab:
    st.subheader("Daily-return distribution")
    st.write(
        "This chart will show the range and frequency of historical daily returns."
    )

st.warning(
    "Historical risk metrics describe past observations. They cannot determine "
    "the maximum possible future loss."
)