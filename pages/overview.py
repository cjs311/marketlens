"""Overview dashboard page for MarketLens."""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.title("📈 MarketLens")
st.caption("Market-risk and portfolio-analytics dashboard")

st.info(
    "Day 1 dashboard preview: the controls and chart below use illustrative "
    "sample data. Live market data and real calculations will be added in "
    "the upcoming development phases."
)

st.subheader("Analysis setup preview")

today = date.today()
default_start = today - timedelta(days=365)

input_columns = st.columns(4)

with input_columns[0]:
    st.text_input(
        "Ticker symbols",
        value="SPY, QQQ, GLD",
        disabled=True,
        help="Live ticker validation will be implemented on Day 2.",
    )

with input_columns[1]:
    st.date_input(
        "Start date",
        value=default_start,
        disabled=True,
    )

with input_columns[2]:
    st.date_input(
        "End date",
        value=today,
        disabled=True,
    )

with input_columns[3]:
    st.text_input(
        "Benchmark",
        value="SPY",
        disabled=True,
    )

st.divider()
st.subheader("Portfolio summary")

first_metric_row = st.columns(3)

with first_metric_row[0]:
    st.metric("Total Return", "Pending")

with first_metric_row[1]:
    st.metric("Annualized Return", "Pending")

with first_metric_row[2]:
    st.metric("Annualized Volatility", "Pending")

second_metric_row = st.columns(3)

with second_metric_row[0]:
    st.metric("Sharpe Ratio", "Pending")

with second_metric_row[1]:
    st.metric("Maximum Drawdown", "Pending")

with second_metric_row[2]:
    st.metric("Historical VaR (95%)", "Pending")

st.caption(
    "Metric cards will activate after the market-data and calculation "
    "engines are implemented."
)

st.divider()
st.subheader("Portfolio vs. benchmark")

number_of_dates = 126
sample_dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=number_of_dates)

sample_portfolio = (
    100
    + np.linspace(0, 12, number_of_dates)
    + 2.4 * np.sin(np.linspace(0, 9, number_of_dates))
)

sample_benchmark = (
    100
    + np.linspace(0, 8, number_of_dates)
    + 1.8 * np.sin(np.linspace(0.5, 8.5, number_of_dates))
)

figure = go.Figure()

figure.add_trace(
    go.Scatter(
        x=sample_dates,
        y=sample_portfolio,
        mode="lines",
        name="Sample Portfolio",
        line={"color": "#34D399", "width": 3},
        hovertemplate="%{x|%b %d, %Y}<br>Index: %{y:.2f}<extra></extra>",
    )
)

figure.add_trace(
    go.Scatter(
        x=sample_dates,
        y=sample_benchmark,
        mode="lines",
        name="Sample Benchmark",
        line={"color": "#60A5FA", "width": 2},
        hovertemplate="%{x|%b %d, %Y}<br>Index: %{y:.2f}<extra></extra>",
    )
)

figure.update_layout(
    title="Illustrative Normalized Performance",
    xaxis_title="Date",
    yaxis_title="Normalized value",
    hovermode="x unified",
    height=430,
    margin={"l": 20, "r": 20, "t": 60, "b": 20},
    legend_title_text="",
)

st.plotly_chart(figure, use_container_width=True)

st.caption(
    "The displayed series are generated only to preview the dashboard layout. "
    "They are not actual prices, returns, or investment results."
)

st.subheader("Upcoming development")

roadmap_columns = st.columns(3)

with roadmap_columns[0]:
    st.markdown(
        """
        **Market data**

        - Ticker validation
        - Adjusted prices
        - Missing-data checks
        - Benchmark alignment
        """
    )

with roadmap_columns[1]:
    st.markdown(
        """
        **Portfolio analytics**

        - Weighted returns
        - Risk metrics
        - Correlations
        - Risk contributions
        """
    )

with roadmap_columns[2]:
    st.markdown(
        """
        **Reporting**

        - Saved analyses
        - Stress scenarios
        - CSV exports
        - HTML risk reports
        """
    )