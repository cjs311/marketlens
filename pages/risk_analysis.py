"""Dedicated portfolio-risk analysis page for MarketLens."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.risk import RiskCalculationError, calculate_risk_comparison


def format_percentage(value: float) -> str:
    """Format a decimal percentage or return N/A."""
    return "N/A" if pd.isna(value) else f"{value:.2%}"


def format_ratio(value: float) -> str:
    """Format a unitless ratio or return N/A."""
    return "N/A" if pd.isna(value) else f"{value:.2f}"


def format_integer(value: float) -> str:
    """Format a whole-number metric."""
    return f"{int(value):,}"


st.title("⚠️ Risk Analysis")
st.caption(
    "Downside risk, benchmark sensitivity, and historical tail-loss analysis"
)

portfolio_analytics = st.session_state.get("portfolio_analytics")
market_data_config = st.session_state.get("market_data_config")
market_data_result = st.session_state.get("market_data_result")

if (
    portfolio_analytics is None
    or market_data_config is None
    or market_data_result is None
):
    st.info(
        "No portfolio analysis is loaded yet. Open the Overview page, load "
        "market data, and apply portfolio weights before using Risk Analysis."
    )
    st.stop()

portfolio_returns = portfolio_analytics.portfolio_returns
benchmark_returns = portfolio_analytics.benchmark_returns
benchmark_symbol = market_data_config["benchmark"]
asset_tickers = market_data_config["asset_tickers"]
benchmark_label = f"Benchmark ({benchmark_symbol})"

st.info(
    "Risk calculations reuse the active portfolio from Overview. Return there "
    "and apply new weights whenever you want to analyze a different allocation."
)

summary_values = (
    ("Portfolio assets", len(asset_tickers)),
    ("Benchmark", benchmark_symbol),
    ("Daily returns", f"{len(portfolio_returns):,}"),
    (
        "Analysis period",
        f"{market_data_result.actual_start:%b %d, %Y} – "
        f"{market_data_result.actual_end:%b %d, %Y}",
    ),
)

for column, (label, value) in zip(
    st.columns(4),
    summary_values,
):
    column.metric(label, value)

st.divider()
st.subheader("Risk assumptions")

available_return_count = len(portfolio_returns)

standard_windows = [
    window
    for window in (21, 63, 126, 252)
    if window <= available_return_count
]

if not standard_windows:
    standard_windows = [
        max(
            2,
            available_return_count,
        )
    ]

assumption_columns = st.columns(3)

annual_risk_free_rate_percent = assumption_columns[0].number_input(
    "Annual risk-free rate (%)",
    min_value=0.0,
    max_value=25.0,
    value=0.0,
    step=0.25,
    format="%.2f",
    help=(
        "Used in Sharpe, Sortino, and downside-deviation calculations. "
        "The documented MarketLens default is 0%."
    ),
)

confidence_percent = assumption_columns[1].selectbox(
    "Historical loss confidence",
    options=[
        95,
        99,
    ],
    index=0,
    help="Used for one-day historical VaR and CVaR.",
)

rolling_window = assumption_columns[2].selectbox(
    "Rolling volatility window",
    options=standard_windows,
    index=0,
    format_func=lambda value: f"{value} trading days",
)

try:
    risk_comparison = calculate_risk_comparison(
        portfolio_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
        annual_risk_free_rate=(
            annual_risk_free_rate_percent
            / 100.0
        ),
        confidence_level=(
            confidence_percent
            / 100.0
        ),
        rolling_window=rolling_window,
    )
except RiskCalculationError as error:
    st.error(str(error))
    st.stop()

metrics = risk_comparison.metrics

st.divider()
st.subheader("Portfolio risk summary")

primary_cards = (
    (
        "Maximum drawdown",
        "max_drawdown",
        format_percentage,
        "Largest peak-to-trough decline in the analyzed period.",
    ),
    (
        "Annualized volatility",
        "annualized_volatility",
        format_percentage,
        "Daily sample volatility annualized using 252 trading days.",
    ),
    (
        "Sharpe ratio",
        "sharpe_ratio",
        format_ratio,
        "Annualized excess return divided by annualized volatility.",
    ),
    (
        "Sortino ratio",
        "sortino_ratio",
        format_ratio,
        "Annualized excess return divided by downside deviation.",
    ),
)

secondary_cards = (
    (
        f"{confidence_percent}% one-day VaR",
        "historical_var",
        format_percentage,
        "Historical loss threshold shown as a positive loss magnitude.",
    ),
    (
        f"{confidence_percent}% one-day CVaR",
        "historical_cvar",
        format_percentage,
        "Average loss at or beyond the historical VaR threshold.",
    ),
    (
        "Beta vs benchmark",
        "beta",
        format_ratio,
        "Historical sensitivity to benchmark returns.",
    ),
    (
        "Downside deviation",
        "downside_deviation",
        format_percentage,
        "Annualized variability below the daily risk-free threshold.",
    ),
)

for card_row in (
    primary_cards,
    secondary_cards,
):
    for column, (
        label,
        key,
        formatter,
        help_text,
    ) in zip(
        st.columns(4),
        card_row,
    ):
        column.metric(
            label,
            formatter(
                float(
                    metrics.loc[
                        "Portfolio",
                        key,
                    ]
                )
            ),
            help=help_text,
        )

st.caption(
    "Risk ratios can appear as N/A when the selected history has zero total "
    "or downside variability."
)

st.divider()
st.subheader("Drawdown history")

drawdown_chart_data = (
    risk_comparison
    .drawdown
    .rename(
        columns={
            "Benchmark": benchmark_label,
        }
    )
)

drawdown_figure = go.Figure()

drawdown_styles = (
    (
        "Portfolio",
        "#F87171",
        "rgba(248, 113, 113, 0.18)",
        2.4,
    ),
    (
        benchmark_label,
        "#94A3B8",
        "rgba(148, 163, 184, 0.10)",
        2.0,
    ),
)

for (
    series_name,
    color,
    fill_color,
    width,
) in drawdown_styles:
    drawdown_figure.add_trace(
        go.Scatter(
            x=drawdown_chart_data.index,
            y=drawdown_chart_data[
                series_name
            ],
            name=series_name,
            mode="lines",
            line={
                "color": color,
                "width": width,
            },
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate=(
                "%{x|%b %d, %Y}<br>"
                "Drawdown: %{y:.2%}"
                f"<extra>{series_name}</extra>"
            ),
        )
    )

drawdown_figure.add_hline(
    y=0.0,
    line_color="#64748B",
    line_width=1,
)

drawdown_figure.update_layout(
    title=(
        "Peak-to-Trough Drawdown: "
        f"{market_data_result.actual_start:%b %d, %Y} – "
        f"{market_data_result.actual_end:%b %d, %Y}"
    ),
    xaxis_title="Date",
    yaxis_title="Drawdown",
    yaxis_tickformat=".1%",
    hovermode="x unified",
    height=465,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
    legend_title_text="",
)

st.plotly_chart(
    drawdown_figure,
    use_container_width=True,
)

st.caption(
    "Drawdown measures the decline from each series’ previous wealth peak. "
    "A value of -20% means the series was 20% below its prior high."
)

st.divider()
st.subheader("Rolling volatility")

rolling_chart_data = (
    risk_comparison
    .rolling_volatility
    .rename_axis("Date")
    .rename(
        columns={
            "Benchmark": benchmark_label,
        }
    )
    .reset_index()
    .melt(
        id_vars="Date",
        var_name="Series",
        value_name="Annualized volatility",
    )
    .dropna(
        subset=[
            "Annualized volatility",
        ]
    )
)

rolling_figure = px.line(
    rolling_chart_data,
    x="Date",
    y="Annualized volatility",
    color="Series",
    color_discrete_map={
        "Portfolio": "#F59E0B",
        benchmark_label: "#94A3B8",
    },
)

rolling_figure.update_traces(
    line={
        "width": 2.4,
    },
    hovertemplate=(
        "%{x|%b %d, %Y}<br>"
        "Volatility: %{y:.2%}"
        "<extra>%{fullData.name}</extra>"
    ),
)

rolling_figure.update_layout(
    title=(
        f"{rolling_window}-Trading-Day "
        "Rolling Annualized Volatility"
    ),
    xaxis_title="Date",
    yaxis_title="Annualized volatility",
    yaxis_tickformat=".1%",
    hovermode="x unified",
    height=430,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
    legend_title_text="",
)

st.plotly_chart(
    rolling_figure,
    use_container_width=True,
)

st.caption(
    "Rolling volatility shows how recent return variability changed through "
    "time. It describes historical variability, not direction."
)

st.divider()
st.subheader("Daily return distribution")

distribution_data = pd.concat(
    [
        portfolio_returns.rename(
            "Portfolio"
        ),
        benchmark_returns.rename(
            benchmark_label
        ),
    ],
    axis="columns",
).melt(
    var_name="Series",
    value_name="Daily return",
)

distribution_figure = px.histogram(
    distribution_data,
    x="Daily return",
    color="Series",
    nbins=50,
    barmode="overlay",
    opacity=0.62,
    histnorm="probability",
    color_discrete_map={
        "Portfolio": "#60A5FA",
        benchmark_label: "#94A3B8",
    },
)

portfolio_var = float(
    metrics.loc[
        "Portfolio",
        "historical_var",
    ]
)

portfolio_cvar = float(
    metrics.loc[
        "Portfolio",
        "historical_cvar",
    ]
)

distribution_figure.add_vline(
    x=-portfolio_var,
    line_color="#F59E0B",
    line_dash="dash",
    line_width=2,
    annotation_text=(
        f"{confidence_percent}% VaR"
    ),
    annotation_position="top left",
)

distribution_figure.add_vline(
    x=-portfolio_cvar,
    line_color="#EF4444",
    line_dash="dot",
    line_width=2,
    annotation_text=(
        f"{confidence_percent}% CVaR"
    ),
    annotation_position="top right",
)

distribution_figure.update_layout(
    title="Observed Daily Return Distribution",
    xaxis_title="Daily return",
    yaxis_title="Share of observations",
    xaxis_tickformat=".1%",
    yaxis_tickformat=".1%",
    height=450,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
    legend_title_text="",
)

st.plotly_chart(
    distribution_figure,
    use_container_width=True,
)

st.caption(
    "The vertical lines show the portfolio’s historical loss thresholds. "
    "VaR and CVaR use only returns observed in the selected period."
)

st.divider()
st.subheader("Detailed risk comparison")

risk_rows = (
    (
        "Annualized volatility",
        "annualized_volatility",
        format_percentage,
    ),
    (
        "Downside deviation",
        "downside_deviation",
        format_percentage,
    ),
    (
        "Sharpe ratio",
        "sharpe_ratio",
        format_ratio,
    ),
    (
        "Sortino ratio",
        "sortino_ratio",
        format_ratio,
    ),
    (
        "Beta",
        "beta",
        format_ratio,
    ),
    (
        "Maximum drawdown",
        "max_drawdown",
        format_percentage,
    ),
    (
        "Current drawdown",
        "current_drawdown",
        format_percentage,
    ),
    (
        "Longest drawdown (trading days)",
        "max_drawdown_duration",
        format_integer,
    ),
    (
        f"Historical VaR ({confidence_percent}%)",
        "historical_var",
        format_percentage,
    ),
    (
        f"Historical CVaR ({confidence_percent}%)",
        "historical_cvar",
        format_percentage,
    ),
    (
        "Worst day",
        "worst_day",
        format_percentage,
    ),
    (
        "Positive-day percentage",
        "positive_day_ratio",
        format_percentage,
    ),
    (
        "Return observations",
        "observations",
        format_integer,
    ),
)

risk_comparison_table = pd.DataFrame(
    {
        "Metric": [
            label
            for label, _, _ in risk_rows
        ],
        "Portfolio": [
            formatter(
                float(
                    metrics.loc[
                        "Portfolio",
                        key,
                    ]
                )
            )
            for _, key, formatter in risk_rows
        ],
        benchmark_label: [
            formatter(
                float(
                    metrics.loc[
                        "Benchmark",
                        key,
                    ]
                )
            )
            for _, key, formatter in risk_rows
        ],
    }
)

st.dataframe(
    risk_comparison_table,
    hide_index=True,
    use_container_width=True,
)

with st.expander(
    "Risk time series and CSV export"
):
    export_data = pd.concat(
        [
            portfolio_returns.rename(
                "Portfolio return"
            ),
            benchmark_returns.rename(
                f"{benchmark_symbol} benchmark return"
            ),
            risk_comparison.portfolio.drawdown.rename(
                "Portfolio drawdown"
            ),
            risk_comparison.benchmark.drawdown.rename(
                f"{benchmark_symbol} benchmark drawdown"
            ),
            risk_comparison.portfolio.rolling_volatility.rename(
                (
                    "Portfolio "
                    f"{rolling_window}-day annualized volatility"
                )
            ),
            risk_comparison.benchmark.rolling_volatility.rename(
                (
                    f"{benchmark_symbol} benchmark "
                    f"{rolling_window}-day annualized volatility"
                )
            ),
        ],
        axis="columns",
    )

    st.dataframe(
        export_data.sort_index(
            ascending=False
        ),
        use_container_width=True,
        height=420,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                format="%.4f",
            )
            for column in export_data.columns
        },
    )

    risk_csv = (
        export_data
        .rename_axis("Date")
        .to_csv()
        .encode("utf-8")
    )

    st.download_button(
        label="Download risk time series as CSV",
        data=risk_csv,
        file_name=(
            "marketlens_risk_analysis_"
            f"{market_data_result.actual_start}_"
            f"{market_data_result.actual_end}.csv"
        ),
        mime="text/csv",
    )

with st.expander(
    "How MarketLens calculates these metrics"
):
    st.markdown(
        f"""
        - **Annualization:** MarketLens assumes 252 trading days per year.
        - **Risk-free rate:** The selected annual rate is converted to an
          effective daily rate before excess returns are calculated.
        - **Sharpe ratio:** Annualized average excess return divided by
          annualized sample volatility.
        - **Sortino ratio:** Annualized average excess return divided by
          annualized downside deviation.
        - **Drawdown:** Percentage decline from the previous running wealth peak.
        - **Beta:** Covariance between portfolio and {benchmark_symbol} returns
          divided by the variance of {benchmark_symbol} returns.
        - **Historical VaR:** Observed lower-tail return threshold, shown as a
          positive one-day loss.
        - **Historical CVaR:** Average observed one-day loss at or beyond VaR.
        """
    )

st.warning(
    "Historical VaR and CVaR are estimates based on the selected sample. They "
    "do not represent the maximum possible loss and can understate risk during "
    "new or unusually severe market conditions."
)

st.caption(
    "MarketLens is an educational analytics project. Historical results do not "
    "guarantee future performance and are not personalized investment advice."
)