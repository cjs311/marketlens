"""Stress-testing page for MarketLens."""

import pandas as pd
import streamlit as st


st.title("🧪 Stress Testing")
st.caption("Estimate portfolio impact under simplified hypothetical shocks")

st.info(
    "The interface below previews the stress-testing workflow. Scenario "
    "calculations will be implemented during the stress-testing phase."
)

st.number_input(
    "Hypothetical portfolio value",
    min_value=1_000.0,
    value=100_000.0,
    step=1_000.0,
    format="%.2f",
    disabled=True,
)

example_scenario = pd.DataFrame(
    {
        "Ticker": ["SPY", "QQQ", "GLD"],
        "Portfolio weight": ["50%", "30%", "20%"],
        "Example shock": ["-10%", "-15%", "+4%"],
        "Estimated contribution": ["Pending", "Pending", "Pending"],
    }
)

st.subheader("Example static-shock scenario")

st.dataframe(
    example_scenario,
    hide_index=True,
    use_container_width=True,
)

summary_columns = st.columns(2)

with summary_columns[0]:
    st.metric("Estimated portfolio impact", "Pending")

with summary_columns[1]:
    st.metric("Estimated dollar impact", "Pending")

st.warning(
    "Static shock analysis applies immediate percentage changes while holding "
    "other assumptions constant. It is not a complete market-risk model."
)