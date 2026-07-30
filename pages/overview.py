"""Market data and portfolio-performance overview for MarketLens."""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    MarketDataError,
    MarketDataResult,
    download_market_data,
)
from src.portfolio import (
    PortfolioCalculationError,
    calculate_portfolio_analytics,
    create_equal_weights,
    create_portfolio_signature,
    validate_weights,
)
from src.validation import (
    InputValidationError,
    parse_benchmark,
    parse_ticker_input,
    validate_date_range,
)
from src.ui import page_header


@st.cache_data(
    ttl="1h",
    max_entries=25,
    show_spinner=False,
)
def load_cached_market_data(
    asset_tickers: tuple[str, ...],
    benchmark: str,
    start_date: date,
    end_date: date,
) -> MarketDataResult:
    """Cache identical market-data requests for one hour."""
    return download_market_data(
        asset_tickers=asset_tickers,
        benchmark=benchmark,
        start_date=start_date,
        end_date=end_date,
    )


def format_percentage(value: float) -> str:
    """Format a decimal as a signed percentage."""
    return f"{value:+.2%}"


page_header(
    eyebrow="MARKET OVERVIEW",
    title="See the portfolio clearly.",
    description=(
        "Load historical market data, configure portfolio weights, "
        "and compare performance against your selected benchmark."
    ),
    badge="PRIMARY WORKSPACE",
)

overview_notice = st.session_state.pop(
    "overview_notice",
    None,
)

if overview_notice:
    st.success(overview_notice)

today = date.today()
default_start = today - timedelta(days=365)
active_config = st.session_state.get(
    "market_data_config"
)

if active_config is None:
    default_ticker_input = "SPY, QQQ, GLD"
    default_benchmark_input = "SPY"
    default_start_input = default_start
    default_end_input = today
else:
    default_ticker_input = ", ".join(
        active_config["asset_tickers"]
    )
    default_benchmark_input = active_config[
        "benchmark"
    ]
    default_start_input = active_config[
        "start_date"
    ]
    default_end_input = active_config[
        "end_date"
    ]

st.subheader("Historical analysis setup")

with st.form("market_data_form"):
    input_columns = st.columns([2, 1.2, 1.2, 1])

    with input_columns[0]:
        ticker_input = st.text_input(
            "Portfolio ticker symbols",
            value=default_ticker_input,
            help=(
                "Enter between one and ten symbols separated by commas, "
                "spaces, or semicolons."
            ),
        )

    with input_columns[1]:
        start_date = st.date_input(
            "Start date",
            value=default_start_input,
            max_value=today,
        )

    with input_columns[2]:
        end_date = st.date_input(
            "End date",
            value=default_end_input,
            max_value=today,
        )

    with input_columns[3]:
        benchmark_input = st.text_input(
            "Benchmark",
            value=default_benchmark_input,
            help=(
                "The benchmark is aligned to the same dates as the "
                "portfolio assets."
            ),
        )

    submitted = st.form_submit_button(
        "Load market data",
        type="primary",
        use_container_width=True,
    )

if submitted:
    for state_key in (
        "market_data_result",
        "market_data_config",
        "portfolio_signature",
        "portfolio_weights",
        "portfolio_analytics",
    ):
        st.session_state.pop(
            state_key,
            None,
        )

    try:
        asset_tickers = parse_ticker_input(
            ticker_input
        )
        benchmark = parse_benchmark(
            benchmark_input
        )

        validate_date_range(
            start_date,
            end_date,
        )

        with st.spinner(
            "Downloading and validating adjusted prices..."
        ):
            market_data_result = load_cached_market_data(
                asset_tickers=asset_tickers,
                benchmark=benchmark,
                start_date=start_date,
                end_date=end_date,
            )

    except (
        InputValidationError,
        MarketDataError,
    ) as error:
        st.error(str(error))
    else:
        st.session_state[
            "market_data_result"
        ] = market_data_result

        st.session_state[
            "market_data_config"
        ] = {
            "asset_tickers": asset_tickers,
            "benchmark": benchmark,
            "start_date": start_date,
            "end_date": end_date,
        }

        st.success(
            "Loaded "
            f"{market_data_result.rows_after_alignment:,} aligned trading "
            f"days from {market_data_result.actual_start:%b %d, %Y} through "
            f"{market_data_result.actual_end:%b %d, %Y}."
        )

market_data_result = st.session_state.get(
    "market_data_result"
)
market_data_config = st.session_state.get(
    "market_data_config"
)

if (
    market_data_result is None
    or market_data_config is None
):
    st.divider()
    st.subheader("Ready to load market data")

    st.markdown(
        """
        Select the assets, benchmark, and analysis period. MarketLens will
        validate the inputs, download adjusted prices, and align every security
        to common trading dates.
        """
    )

    st.warning(
        "Historical data from yfinance may be delayed, incomplete, adjusted, "
        "or temporarily unavailable."
    )

    st.stop()

prices = market_data_result.prices
asset_tickers = market_data_config[
    "asset_tickers"
]
benchmark = market_data_config[
    "benchmark"
]

st.divider()
st.subheader("Loaded dataset")

dataset_columns = st.columns(4)

with dataset_columns[0]:
    st.metric(
        "Portfolio assets",
        len(asset_tickers),
    )

with dataset_columns[1]:
    st.metric(
        "Benchmark",
        benchmark,
    )

with dataset_columns[2]:
    st.metric(
        "Aligned trading days",
        f"{len(prices):,}",
    )

with dataset_columns[3]:
    st.metric(
        "Usable period",
        (
            f"{market_data_result.actual_start:%b %d, %Y} – "
            f"{market_data_result.actual_end:%b %d, %Y}"
        ),
    )

if market_data_result.dropped_rows > 0:
    st.warning(
        f"{market_data_result.dropped_rows:,} rows were removed because at "
        "least one requested security had a missing adjusted price."
    )
else:
    st.success(
        "No dates were removed during cross-asset alignment."
    )

portfolio_signature = create_portfolio_signature(
    asset_tickers=asset_tickers,
    benchmark=benchmark,
    actual_start=market_data_result.actual_start,
    actual_end=market_data_result.actual_end,
)

if (
    st.session_state.get(
        "portfolio_signature"
    )
    != portfolio_signature
):
    default_weights = create_equal_weights(
        asset_tickers
    )

    default_analytics = calculate_portfolio_analytics(
        prices=prices,
        asset_tickers=asset_tickers,
        benchmark=benchmark,
        weights=default_weights,
    )

    st.session_state[
        "portfolio_signature"
    ] = portfolio_signature

    st.session_state[
        "portfolio_weights"
    ] = default_weights

    st.session_state[
        "portfolio_analytics"
    ] = default_analytics

current_weights = st.session_state[
    "portfolio_weights"
]

st.divider()
st.subheader("Portfolio weights")

st.caption(
    "Enter target percentages for the selected portfolio assets. "
    "MarketLens currently supports long-only weights."
)

weight_editor_data = pd.DataFrame(
    {
        "Ticker": list(asset_tickers),
        "Weight (%)": [
            float(
                current_weights[ticker]
                * 100.0
            )
            for ticker in asset_tickers
        ],
    }
)

editor_key = (
    "weight_editor_"
    + portfolio_signature
)

with st.form(
    "portfolio_weight_form_"
    + portfolio_signature
):
    edited_weights = st.data_editor(
        weight_editor_data,
        hide_index=True,
        use_container_width=True,
        num_rows="fixed",
        disabled=["Ticker"],
        key=editor_key,
        column_config={
            "Ticker": st.column_config.TextColumn(
                "Ticker",
                help="Portfolio asset symbol",
            ),
            "Weight (%)": st.column_config.NumberColumn(
                "Weight (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                format="%.2f",
                help="Target percentage allocated to this asset",
            ),
        },
    )

    normalize_requested = st.checkbox(
        "Automatically normalize entered weights to 100%",
        value=True,
        help=(
            "For example, weights of 60 and 20 would be proportionally "
            "converted to 75% and 25%."
        ),
    )

    apply_weights = st.form_submit_button(
        "Apply portfolio weights",
        type="primary",
        use_container_width=True,
    )

if apply_weights:
    raw_weight_percentages = pd.Series(
        edited_weights[
            "Weight (%)"
        ].to_numpy(),
        index=edited_weights[
            "Ticker"
        ].astype(str),
        dtype="float64",
    )

    raw_decimal_weights = (
        raw_weight_percentages
        / 100.0
    )

    try:
        validated_weights = validate_weights(
            raw_weights=raw_decimal_weights,
            asset_tickers=asset_tickers,
            normalize=normalize_requested,
        )

        portfolio_analytics = calculate_portfolio_analytics(
            prices=prices,
            asset_tickers=asset_tickers,
            benchmark=benchmark,
            weights=validated_weights,
        )

    except PortfolioCalculationError as error:
        st.error(str(error))
    else:
        st.session_state[
            "portfolio_weights"
        ] = validated_weights

        st.session_state[
            "portfolio_analytics"
        ] = portfolio_analytics

        current_weights = validated_weights


        st.success(
            "Portfolio weights applied. Final allocation totals 100%."
        )

portfolio_analytics = st.session_state[
    "portfolio_analytics"
]
current_weights = portfolio_analytics.weights
metrics = portfolio_analytics.metrics

allocation_table = pd.DataFrame(
    {
        "Ticker": current_weights.index,
        "Weight": [
            f"{value:.2%}"
            for value in current_weights
        ],
    }
)

st.dataframe(
    allocation_table,
    hide_index=True,
    use_container_width=True,
)

st.caption(
    "Calculation assumption: the selected target weights are applied to every "
    "daily return, representing daily rebalancing. Transaction costs, taxes, "
    "slippage, and management fees are not included."
)

st.divider()
st.subheader("Portfolio performance")

portfolio_total_return = float(
    metrics.loc[
        "Portfolio",
        "total_return",
    ]
)
benchmark_total_return = float(
    metrics.loc[
        "Benchmark",
        "total_return",
    ]
)

portfolio_annualized_return = float(
    metrics.loc[
        "Portfolio",
        "annualized_return",
    ]
)
benchmark_annualized_return = float(
    metrics.loc[
        "Benchmark",
        "annualized_return",
    ]
)

portfolio_volatility = float(
    metrics.loc[
        "Portfolio",
        "annualized_volatility",
    ]
)

metric_columns = st.columns(4)

with metric_columns[0]:
    st.metric(
        "Portfolio total return",
        f"{portfolio_total_return:.2%}",
        delta=(
            f"{portfolio_total_return - benchmark_total_return:+.2%} "
            "vs benchmark"
        ),
    )

with metric_columns[1]:
    st.metric(
        "Portfolio annualized return",
        f"{portfolio_annualized_return:.2%}",
        delta=(
            f"{portfolio_annualized_return - benchmark_annualized_return:+.2%} "
            "vs benchmark"
        ),
    )

with metric_columns[2]:
    st.metric(
        "Portfolio annualized volatility",
        f"{portfolio_volatility:.2%}",
    )

with metric_columns[3]:
    st.metric(
        f"{benchmark} total return",
        f"{benchmark_total_return:.2%}",
    )

performance_chart_data = (
    portfolio_analytics.performance_index
    .rename_axis("Date")
    .reset_index()
    .melt(
        id_vars="Date",
        var_name="Series",
        value_name="Growth of 100",
    )
)

performance_figure = px.line(
    performance_chart_data,
    x="Date",
    y="Growth of 100",
    color="Series",
    color_discrete_map={
        "Portfolio": "#34D399",
        "Benchmark": "#94A3B8",
    },
)

performance_figure.update_traces(
    line={"width": 2.6},
    hovertemplate=(
        "%{x|%b %d, %Y}<br>"
        "Value: %{y:.2f}"
        "<extra>%{fullData.name}</extra>"
    ),
)

performance_figure.update_layout(
    title=(
        "Growth of 100: Portfolio vs "
        f"{benchmark}"
    ),
    xaxis_title="Date",
    yaxis_title="Growth of 100",
    hovermode="x unified",
    height=475,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 20,
    },
    legend_title_text="",
)

st.plotly_chart(
    performance_figure,
    use_container_width=True,
)

st.caption(
    "Both series begin at 100. Portfolio performance compounds the selected "
    "weighted daily asset returns."
)

comparison_table = pd.DataFrame(
    {
        "Series": [
            "Portfolio",
            f"Benchmark ({benchmark})",
        ],
        "Total return": [
            format_percentage(
                portfolio_total_return
            ),
            format_percentage(
                benchmark_total_return
            ),
        ],
        "Annualized return": [
            format_percentage(
                portfolio_annualized_return
            ),
            format_percentage(
                benchmark_annualized_return
            ),
        ],
        "Annualized volatility": [
            format_percentage(
                float(
                    metrics.loc[
                        "Portfolio",
                        "annualized_volatility",
                    ]
                )
            ),
            format_percentage(
                float(
                    metrics.loc[
                        "Benchmark",
                        "annualized_volatility",
                    ]
                )
            ),
        ],
        "Best day": [
            format_percentage(
                float(
                    metrics.loc[
                        "Portfolio",
                        "best_day",
                    ]
                )
            ),
            format_percentage(
                float(
                    metrics.loc[
                        "Benchmark",
                        "best_day",
                    ]
                )
            ),
        ],
        "Worst day": [
            format_percentage(
                float(
                    metrics.loc[
                        "Portfolio",
                        "worst_day",
                    ]
                )
            ),
            format_percentage(
                float(
                    metrics.loc[
                        "Benchmark",
                        "worst_day",
                    ]
                )
            ),
        ],
    }
)

st.dataframe(
    comparison_table,
    hide_index=True,
    use_container_width=True,
)

with st.expander(
    "Daily return history and export"
):
    daily_return_history = (
        portfolio_analytics.asset_returns
        .add_suffix(" asset return")
    )

    daily_return_history[
        "Portfolio return"
    ] = portfolio_analytics.portfolio_returns

    daily_return_history[
        f"{benchmark} benchmark return"
    ] = portfolio_analytics.benchmark_returns

    st.dataframe(
        daily_return_history
        .sort_index(ascending=False),
        use_container_width=True,
        height=420,
        column_config={
            column: st.column_config.NumberColumn(
                column,
                format="%.4f",
            )
            for column in daily_return_history.columns
        },
    )

    return_csv = (
        daily_return_history
        .rename_axis("Date")
        .to_csv()
        .encode("utf-8")
    )

    st.download_button(
        label="Download daily returns as CSV",
        data=return_csv,
        file_name=(
            "marketlens_daily_returns_"
            f"{market_data_result.actual_start}_"
            f"{market_data_result.actual_end}.csv"
        ),
        mime="text/csv",
    )

with st.expander(
    "Underlying security performance and data quality"
):
    normalized_prices = (
        prices
        .divide(prices.iloc[0])
        .multiply(100.0)
    )

    normalized_chart_data = (
        normalized_prices
        .rename_axis("Date")
        .reset_index()
        .melt(
            id_vars="Date",
            var_name="Security",
            value_name="Normalized value",
        )
    )

    normalized_figure = px.line(
        normalized_chart_data,
        x="Date",
        y="Normalized value",
        color="Security",
    )

    normalized_figure.update_layout(
        title="Individual Adjusted Prices Indexed to 100",
        xaxis_title="Date",
        yaxis_title="Normalized value",
        hovermode="x unified",
        height=425,
    )

    st.plotly_chart(
        normalized_figure,
        use_container_width=True,
    )

    quality_columns = st.columns(3)

    with quality_columns[0]:
        st.metric(
            "Rows before alignment",
            f"{market_data_result.rows_before_alignment:,}",
        )

    with quality_columns[1]:
        st.metric(
            "Rows after alignment",
            f"{market_data_result.rows_after_alignment:,}",
        )

    with quality_columns[2]:
        st.metric(
            "Rows removed",
            f"{market_data_result.dropped_rows:,}",
        )

    st.dataframe(
        prices.sort_index(
            ascending=False
        ),
        use_container_width=True,
        height=350,
        column_config={
            ticker: st.column_config.NumberColumn(
                ticker,
                format="%.2f",
            )
            for ticker in prices.columns
        },
    )

    price_csv = (
        prices
        .rename_axis("Date")
        .to_csv()
        .encode("utf-8")
    )

    st.download_button(
        label="Download adjusted prices as CSV",
        data=price_csv,
        file_name=(
            "marketlens_adjusted_prices_"
            f"{market_data_result.actual_start}_"
            f"{market_data_result.actual_end}.csv"
        ),
        mime="text/csv",
    )

st.warning(
    "MarketLens is an educational analytics project. Historical performance "
    "does not guarantee future results, and this dashboard does not provide "
    "personalized investment advice."
)
