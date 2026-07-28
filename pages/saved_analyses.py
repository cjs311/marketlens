"""Saved-analysis management page for MarketLens."""

import streamlit as st


st.title("💾 Saved Analyses")
st.caption("Save, reload, review, and delete portfolio analyses")

st.info(
    "SQLite persistence will be implemented during the database phase. "
    "No analyses have been saved yet."
)

st.text_input(
    "Analysis name",
    placeholder="Example: Diversified ETF Portfolio",
    disabled=True,
)

action_columns = st.columns(3)

with action_columns[0]:
    st.button(
        "Save current analysis",
        disabled=True,
        use_container_width=True,
    )

with action_columns[1]:
    st.button(
        "Reload selected analysis",
        disabled=True,
        use_container_width=True,
    )

with action_columns[2]:
    st.button(
        "Delete selected analysis",
        disabled=True,
        use_container_width=True,
    )

st.subheader("Saved portfolio analyses")

st.write(
    "Saved analyses will display their creation date, benchmark, portfolio "
    "composition, analysis period, and major risk metrics here."
)