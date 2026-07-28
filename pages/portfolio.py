"""Portfolio-composition page for MarketLens."""

import pandas as pd
import plotly.express as px
import streamlit as st


st.title("🧩 Portfolio Composition")
st.caption("Review allocation, exposure, concentration, and asset relationships")

st.info(
    "This page uses a static development portfolio to preview the interface. "
    "Editable tickers and weights will be connected to the analysis engine later."
)

sample_portfolio = pd.DataFrame(
    {
        "Ticker": ["QQQ", "AAPL", "MSFT", "NVDA"],
        "Weight": [40.0, 20.0, 20.0, 20.0],
        "Role": [
            "Technology ETF",
            "Technology equity",
            "Technology equity",
            "Semiconductor equity",
        ],
    }
)

table_column, chart_column = st.columns([1, 1.25])

with table_column:
    st.subheader("Example weights")
    st.dataframe(
        sample_portfolio,
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Weights shown as percentages.")

with chart_column:
    st.subheader("Example allocation")

    allocation_figure = px.pie(
        sample_portfolio,
        names="Ticker",
        values="Weight",
        hole=0.55,
        color_discrete_sequence=[
            "#34D399",
            "#60A5FA",
            "#A78BFA",
            "#F59E0B",
        ],
    )

    allocation_figure.update_traces(
        textposition="inside",
        textinfo="label+percent",
        hovertemplate="%{label}<br>Weight: %{value:.1f}%<extra></extra>",
    )

    allocation_figure.update_layout(
        showlegend=True,
        height=390,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
    )

    st.plotly_chart(allocation_figure, use_container_width=True)

st.warning(
    "This sample portfolio is for software testing only and is not an "
    "investment recommendation."
)

correlation_tab, risk_contribution_tab = st.tabs(
    ["Correlation Matrix", "Risk Contribution"]
)

with correlation_tab:
    st.write(
        "The correlation heatmap will appear here after historical asset "
        "returns are available."
    )

with risk_contribution_tab:
    st.write(
        "Asset contributions to portfolio volatility will appear here after "
        "the covariance engine is implemented."
    )