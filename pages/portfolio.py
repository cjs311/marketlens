"""Portfolio-composition analysis page for MarketLens."""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.composition import (
    CompositionCalculationError,
    calculate_composition_analytics,
)


def format_percentage(value: float) -> str:
    """Format a decimal percentage or return N/A."""
    return (
        "N/A"
        if pd.isna(value)
        else f"{value:.2%}"
    )


def format_ratio(value: float) -> str:
    """Format a numeric ratio or return N/A."""
    return (
        "N/A"
        if pd.isna(value)
        else f"{value:.2f}"
    )


st.title("🧩 Portfolio Composition")
st.caption(
    "Allocation, concentration, correlation, and asset-level risk contribution"
)

portfolio_analytics = st.session_state.get(
    "portfolio_analytics"
)

market_data_config = st.session_state.get(
    "market_data_config"
)

market_data_result = st.session_state.get(
    "market_data_result"
)

if (
    portfolio_analytics is None
    or market_data_config is None
    or market_data_result is None
):
    st.info(
        "No portfolio analysis is loaded yet. Open the Overview page, "
        "load market data, and apply portfolio weights before using "
        "Portfolio Composition."
    )
    st.stop()

asset_returns = portfolio_analytics.asset_returns
weights = portfolio_analytics.weights
asset_tickers = market_data_config["asset_tickers"]
benchmark_symbol = market_data_config["benchmark"]

try:
    composition = calculate_composition_analytics(
        asset_returns=asset_returns,
        weights=weights,
    )
except CompositionCalculationError as error:
    st.error(str(error))
    st.stop()

metrics = composition.metrics

st.info(
    "This page uses the active allocation from Overview. Return to "
    "Overview and apply new weights to analyze another portfolio."
)

summary_values = (
    (
        "Portfolio assets",
        f"{len(asset_tickers):,}",
    ),
    (
        "Benchmark",
        benchmark_symbol,
    ),
    (
        "Return observations",
        f"{len(asset_returns):,}",
    ),
    (
        "Analysis period",
        (
            f"{market_data_result.actual_start:%b %d, %Y} – "
            f"{market_data_result.actual_end:%b %d, %Y}"
        ),
    ),
)

for column, (label, value) in zip(
    st.columns(4),
    summary_values,
):
    column.metric(
        label,
        value,
    )

st.divider()
st.subheader("Concentration summary")

concentration_cards = (
    (
        "Largest position",
        (
            f"{metrics['largest_ticker']} · "
            f"{float(metrics['largest_weight']):.2%}"
        ),
        "The asset with the largest portfolio allocation.",
    ),
    (
        "Top two concentration",
        format_percentage(
            float(
                metrics["top_two_weight"]
            )
        ),
        "The combined allocation of the two largest positions.",
    ),
    (
        "Effective number of assets",
        format_ratio(
            float(
                metrics["effective_assets"]
            )
        ),
        "The reciprocal of HHI. Higher values indicate more even allocation.",
    ),
    (
        "Diversification ratio",
        format_ratio(
            float(
                metrics["diversification_ratio"]
            )
        ),
        (
            "Weighted standalone volatility divided by portfolio "
            "volatility. Values above 1 indicate a diversification benefit."
        ),
    ),
)

for column, (
    label,
    value,
    help_text,
) in zip(
    st.columns(4),
    concentration_cards,
):
    column.metric(
        label,
        value,
        help=help_text,
    )

detail_columns = st.columns(2)

detail_columns[0].metric(
    "Concentration index (HHI)",
    f"{float(metrics['hhi']):.3f}",
    help=(
        "The sum of squared portfolio weights. Lower values indicate "
        "a more evenly distributed allocation."
    ),
)

average_correlation = float(
    metrics[
        "average_pairwise_correlation"
    ]
)

detail_columns[1].metric(
    "Average pairwise correlation",
    format_ratio(
        average_correlation
    ),
    help=(
        "The average historical correlation between each distinct "
        "pair of assets."
    ),
)

largest_weight = float(
    metrics["largest_weight"]
)

effective_assets = float(
    metrics["effective_assets"]
)

asset_count = int(
    metrics["asset_count"]
)

if largest_weight >= 0.50:
    st.warning(
        f"High single-position concentration: "
        f"{metrics['largest_ticker']} represents "
        f"{largest_weight:.1%} of the portfolio."
    )
elif largest_weight >= 0.35:
    st.warning(
        f"Moderate single-position concentration: "
        f"{metrics['largest_ticker']} represents "
        f"{largest_weight:.1%} of the portfolio."
    )
elif (
    asset_count > 1
    and effective_assets
    < asset_count * 0.60
):
    st.warning(
        "The portfolio contains several assets, but its effective number "
        "of assets is low because the allocation is uneven."
    )
else:
    st.success(
        "No major allocation-concentration warning was triggered by "
        "MarketLens' current composition rules."
    )

st.caption(
    "These warnings describe allocation concentration only. They are "
    "educational indicators, not recommendations to buy or sell."
)

st.divider()
st.subheader("Portfolio allocation")

allocation_data = (
    composition
    .allocation
    .rename_axis("Ticker")
    .reset_index()
)

allocation_columns = st.columns(2)

allocation_figure = px.pie(
    allocation_data,
    names="Ticker",
    values="weight",
    hole=0.42,
    color="Ticker",
)

allocation_figure.update_traces(
    textposition="inside",
    texttemplate=(
        "%{label}<br>%{percent:.1%}"
    ),
    hovertemplate=(
        "<b>%{label}</b><br>"
        "Weight: %{percent:.2%}"
        "<extra></extra>"
    ),
)

allocation_figure.update_layout(
    title="Current Portfolio Allocation",
    height=430,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
    legend_title_text="",
)

allocation_columns[0].plotly_chart(
    allocation_figure,
    use_container_width=True,
)

allocation_bar = px.bar(
    allocation_data.sort_values(
        "weight",
        ascending=True,
    ),
    x="weight",
    y="Ticker",
    orientation="h",
    color="Ticker",
    text="weight",
)

allocation_bar.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Weight: %{x:.2%}"
        "<extra></extra>"
    ),
)

allocation_bar.update_layout(
    title="Allocation by Asset",
    xaxis_title="Portfolio weight",
    yaxis_title="",
    xaxis_tickformat=".0%",
    showlegend=False,
    height=430,
    margin={
        "l": 20,
        "r": 45,
        "t": 65,
        "b": 20,
    },
)

allocation_columns[1].plotly_chart(
    allocation_bar,
    use_container_width=True,
)

st.divider()
st.subheader("Individual asset statistics")

asset_table = (
    composition
    .asset_metrics
    .join(
        composition
        .volatility_contribution[
            [
                "weight",
                "contribution_percentage",
            ]
        ]
    )
    [
        [
            "weight",
            "total_return",
            "annualized_return",
            "annualized_volatility",
            "best_day",
            "worst_day",
            "positive_day_ratio",
            "contribution_percentage",
            "observations",
        ]
    ]
    .rename(
        columns={
            "weight": "Weight",
            "total_return": "Total return",
            "annualized_return": "Annualized return",
            "annualized_volatility": "Annualized volatility",
            "best_day": "Best day",
            "worst_day": "Worst day",
            "positive_day_ratio": "Positive-day percentage",
            "contribution_percentage": (
                "Volatility contribution"
            ),
            "observations": "Observations",
        }
    )
)

display_asset_table = (
    asset_table
    .reset_index()
)

percentage_columns = [
    "Weight",
    "Total return",
    "Annualized return",
    "Annualized volatility",
    "Best day",
    "Worst day",
    "Positive-day percentage",
    "Volatility contribution",
]

display_asset_table[
    percentage_columns
] = (
    display_asset_table[
        percentage_columns
    ]
    * 100.0
)

st.dataframe(
    display_asset_table,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Ticker": st.column_config.TextColumn(
            "Ticker"
        ),
        **{
            column: st.column_config.NumberColumn(
                column,
                format="%.2f%%",
            )
            for column in percentage_columns
        },
        "Observations": st.column_config.NumberColumn(
            "Observations",
            format="%d",
        ),
    },
)

st.caption(
    "Annualized returns are compounded from the selected sample. "
    "Annualized volatility uses 252 trading days."
)

st.divider()
st.subheader("Asset correlation")

correlation = composition.correlation

correlation_figure = go.Figure(
    data=go.Heatmap(
        z=correlation.to_numpy(
            dtype="float64"
        ),
        x=correlation.columns.tolist(),
        y=correlation.index.tolist(),
        zmin=-1.0,
        zmax=1.0,
        zmid=0.0,
        colorscale="RdBu_r",
        text=correlation.round(2).to_numpy(),
        texttemplate="%{text}",
        colorbar={
            "title": "Correlation",
            "tickformat": ".1f",
        },
        hovertemplate=(
            "%{y} vs %{x}<br>"
            "Correlation: %{z:.3f}"
            "<extra></extra>"
        ),
    )
)

correlation_figure.update_layout(
    title="Daily Return Correlation Matrix",
    xaxis_title="Asset",
    yaxis_title="Asset",
    height=max(
        430,
        85 * len(correlation),
    ),
    margin={
        "l": 40,
        "r": 40,
        "t": 65,
        "b": 40,
    },
)

st.plotly_chart(
    correlation_figure,
    use_container_width=True,
)

st.caption(
    "Correlation ranges from -1 to +1. Lower correlations can improve "
    "diversification, but historical relationships can change."
)

st.divider()
st.subheader("Contribution to portfolio volatility")

contribution_data = (
    composition
    .volatility_contribution
    .rename_axis("Ticker")
    .reset_index()
)

contribution_figure = px.bar(
    contribution_data.sort_values(
        "contribution_percentage",
        ascending=False,
    ),
    x="Ticker",
    y="contribution_percentage",
    color="Ticker",
    text="contribution_percentage",
)

contribution_figure.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Weight: %{customdata[0]:.2%}<br>"
        "Standalone volatility: %{customdata[1]:.2%}<br>"
        "Volatility contribution: %{y:.2%}"
        "<extra></extra>"
    ),
    customdata=contribution_data[
        [
            "weight",
            "standalone_annualized_volatility",
        ]
    ].to_numpy(),
)

contribution_figure.add_hline(
    y=0.0,
    line_color="#64748B",
    line_width=1,
)

contribution_figure.update_layout(
    title="Share of Total Portfolio Volatility",
    xaxis_title="Asset",
    yaxis_title="Contribution to portfolio volatility",
    yaxis_tickformat=".1%",
    showlegend=False,
    height=450,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
)

st.plotly_chart(
    contribution_figure,
    use_container_width=True,
)

st.caption(
    "Volatility contribution considers portfolio weight, each asset's "
    "volatility, and its covariance with the other holdings. Therefore, "
    "an asset's risk contribution does not have to equal its allocation."
)

portfolio_volatility = float(
    metrics[
        "portfolio_annualized_volatility"
    ]
)

weighted_asset_volatility = float(
    metrics[
        "weighted_average_asset_volatility"
    ]
)

volatility_columns = st.columns(2)

volatility_columns[0].metric(
    "Portfolio annualized volatility",
    format_percentage(
        portfolio_volatility
    ),
)

volatility_columns[1].metric(
    "Weighted standalone volatility",
    format_percentage(
        weighted_asset_volatility
    ),
    help=(
        "Weighted average of each asset's standalone volatility before "
        "accounting for diversification."
    ),
)

with st.expander(
    "Composition data and CSV export"
):
    export_data = (
        composition
        .asset_metrics
        .join(
            composition.allocation
        )
        .join(
            composition
            .volatility_contribution
            .drop(
                columns=[
                    "weight",
                    "standalone_annualized_volatility",
                ]
            )
        )
    )

    export_data = export_data[
        [
            "weight",
            "total_return",
            "annualized_return",
            "annualized_volatility",
            "average_daily_return",
            "best_day",
            "worst_day",
            "positive_day_ratio",
            "marginal_annualized_volatility",
            "annualized_volatility_contribution",
            "contribution_percentage",
            "observations",
        ]
    ]

    st.dataframe(
        export_data,
        use_container_width=True,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                format="%.6f",
            )
            for column in export_data.columns
        },
    )

    composition_csv = (
        export_data
        .rename_axis("Ticker")
        .to_csv()
        .encode("utf-8")
    )

    st.download_button(
        label="Download composition analysis as CSV",
        data=composition_csv,
        file_name=(
            "marketlens_portfolio_composition_"
            f"{market_data_result.actual_start}_"
            f"{market_data_result.actual_end}.csv"
        ),
        mime="text/csv",
    )

with st.expander(
    "How MarketLens calculates composition metrics"
):
    st.markdown(
        """
        - **HHI:** Sum of each squared portfolio weight.
        - **Effective assets:** One divided by HHI. A perfectly equal
          three-asset portfolio has an effective count of three.
        - **Diversification ratio:** Weighted average standalone volatility
          divided by total portfolio volatility.
        - **Correlation:** Pearson correlation calculated from aligned daily
          asset returns.
        - **Marginal volatility:** The estimated change in portfolio
          volatility associated with increasing an asset's weight.
        - **Component volatility:** Asset weight multiplied by marginal
          volatility.
        - **Contribution percentage:** Component volatility divided by total
          portfolio volatility. Contributions reconcile to 100% when portfolio
          volatility is nonzero.
        """
    )

st.caption(
    "MarketLens is an educational analytics project. Historical results "
    "do not guarantee future performance and are not personalized "
    "investment advice."
)