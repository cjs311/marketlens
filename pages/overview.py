"""Overview and historical-market-data page for MarketLens."""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    MarketDataError,
    MarketDataResult,
    download_market_data,
)
from src.validation import (
    InputValidationError,
    parse_benchmark,
    parse_ticker_input,
    validate_date_range,
)


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


st.title("📈 MarketLens")
st.caption("Market-risk and portfolio-analytics dashboard")

st.info(
    "Day 2 adds real adjusted historical prices and market-data validation. "
    "Portfolio returns, weights, and risk metrics begin on Day 3."
)

today = date.today()
default_start = today - timedelta(days=365)

st.subheader("Historical analysis setup")

with st.form("market_data_form"):
    input_columns = st.columns([2, 1.2, 1.2, 1])

    with input_columns[0]:
        ticker_input = st.text_input(
            "Portfolio ticker symbols",
            value="SPY, QQQ, GLD",
            help=(
                "Enter between one and ten symbols separated by commas, "
                "spaces, or semicolons."
            ),
        )

    with input_columns[1]:
        start_date = st.date_input(
            "Start date",
            value=default_start,
            max_value=today,
        )

    with input_columns[2]:
        end_date = st.date_input(
            "End date",
            value=today,
            max_value=today,
        )

    with input_columns[3]:
        benchmark_input = st.text_input(
            "Benchmark",
            value="SPY",
            help="The benchmark is downloaded and aligned with the portfolio assets.",
        )

    submitted = st.form_submit_button(
        "Load market data",
        type="primary",
        use_container_width=True,
    )

if submitted:
    st.session_state.pop("market_data_result", None)
    st.session_state.pop("market_data_config", None)

    try:
        asset_tickers = parse_ticker_input(ticker_input)
        benchmark = parse_benchmark(benchmark_input)

        validate_date_range(
            start_date,
            end_date,
        )

        with st.spinner("Downloading and validating adjusted prices..."):
            market_data_result = load_cached_market_data(
                asset_tickers=asset_tickers,
                benchmark=benchmark,
                start_date=start_date,
                end_date=end_date,
            )

    except (InputValidationError, MarketDataError) as error:
        st.error(str(error))
    else:
        st.session_state["market_data_result"] = market_data_result
        st.session_state["market_data_config"] = {
            "asset_tickers": asset_tickers,
            "benchmark": benchmark,
            "start_date": start_date,
            "end_date": end_date,
        }

        st.success(
            "Loaded "
            f"{market_data_result.rows_after_alignment:,} aligned trading days "
            f"from {market_data_result.actual_start:%b %d, %Y} through "
            f"{market_data_result.actual_end:%b %d, %Y}."
        )

market_data_result = st.session_state.get(
    "market_data_result"
)
market_data_config = st.session_state.get(
    "market_data_config"
)

if market_data_result is None or market_data_config is None:
    st.divider()
    st.subheader("Ready to load market data")

    st.markdown(
        """
        Select your assets, benchmark, and historical period, and then choose
        **Load market data**.

        MarketLens will:

        - Validate the ticker format.
        - Download adjusted daily closing prices.
        - Confirm that every ticker returned usable history.
        - Align all securities to common trading dates.
        - Report missing observations instead of hiding them.
        """
    )

    st.warning(
        "Historical data from yfinance may be delayed, incomplete, adjusted, "
        "or temporarily unavailable."
    )

    st.stop()

prices = market_data_result.prices
asset_tickers = market_data_config["asset_tickers"]
benchmark = market_data_config["benchmark"]

st.divider()
st.subheader("Loaded dataset")

summary_columns = st.columns(4)

with summary_columns[0]:
    st.metric(
        "Securities loaded",
        len(prices.columns),
    )

with summary_columns[1]:
    st.metric(
        "Aligned trading days",
        f"{len(prices):,}",
    )

with summary_columns[2]:
    st.metric(
        "First usable date",
        market_data_result.actual_start.strftime("%b %d, %Y"),
    )

with summary_columns[3]:
    st.metric(
        "Last usable date",
        market_data_result.actual_end.strftime("%b %d, %Y"),
    )

if market_data_result.dropped_rows > 0:
    st.warning(
        f"{market_data_result.dropped_rows:,} date rows were removed because "
        "at least one requested security had a missing adjusted price. "
        "Portfolio calculations require the assets to use common dates."
    )
else:
    st.success(
        "No date rows were removed during cross-asset alignment."
    )

st.subheader("Normalized security performance")

normalized_prices = (
    prices
    .divide(prices.iloc[0])
    .multiply(100.0)
)

display_names: dict[str, str] = {}

for ticker in normalized_prices.columns:
    if ticker == benchmark and ticker in asset_tickers:
        display_names[ticker] = f"{ticker} (asset and benchmark)"
    elif ticker == benchmark:
        display_names[ticker] = f"{ticker} (benchmark)"
    else:
        display_names[ticker] = ticker

chart_data = (
    normalized_prices
    .rename(columns=display_names)
    .rename_axis("Date")
    .reset_index()
    .melt(
        id_vars="Date",
        var_name="Security",
        value_name="Normalized value",
    )
)

performance_figure = px.line(
    chart_data,
    x="Date",
    y="Normalized value",
    color="Security",
    color_discrete_sequence=[
        "#34D399",
        "#60A5FA",
        "#A78BFA",
        "#F59E0B",
        "#F87171",
        "#22D3EE",
        "#FB7185",
        "#A3E635",
        "#C084FC",
        "#FBBF24",
        "#94A3B8",
    ],
)

performance_figure.update_traces(
    line={"width": 2.4},
    hovertemplate=(
        "%{x|%b %d, %Y}<br>"
        "Normalized value: %{y:.2f}"
        "<extra>%{fullData.name}</extra>"
    ),
)

performance_figure.update_layout(
    title=(
        "Adjusted Prices Indexed to 100 "
        f"({market_data_result.actual_start} to "
        f"{market_data_result.actual_end})"
    ),
    xaxis_title="Date",
    yaxis_title="Normalized value",
    hovermode="x unified",
    height=475,
    margin={"l": 20, "r": 20, "t": 65, "b": 20},
    legend_title_text="",
)

st.plotly_chart(
    performance_figure,
    use_container_width=True,
)

st.caption(
    "Each security begins at 100 so historical price movements can be compared "
    "on a common scale. This does not yet represent a weighted portfolio."
)

st.subheader("Security summary")

security_summary_rows: list[dict[str, object]] = []

for ticker in prices.columns:
    if ticker == benchmark and ticker in asset_tickers:
        role = "Portfolio asset and benchmark"
    elif ticker == benchmark:
        role = "Benchmark"
    else:
        role = "Portfolio asset"

    security_summary_rows.append(
        {
            "Ticker": ticker,
            "Role": role,
            "First adjusted close": prices[ticker].iloc[0],
            "Latest adjusted close": prices[ticker].iloc[-1],
            "Aligned observations": int(prices[ticker].count()),
            "Missing before alignment": (
                market_data_result.missing_values[ticker]
            ),
        }
    )

security_summary = pd.DataFrame(
    security_summary_rows
)

st.dataframe(
    security_summary,
    hide_index=True,
    use_container_width=True,
    column_config={
        "First adjusted close": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Latest adjusted close": st.column_config.NumberColumn(
            format="%.2f"
        ),
        "Aligned observations": st.column_config.NumberColumn(
            format="%d"
        ),
        "Missing before alignment": st.column_config.NumberColumn(
            format="%d"
        ),
    },
)

with st.expander("Data-quality details"):
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

    st.write(
        "**Requested period:** "
        f"{market_data_result.requested_start} through "
        f"{market_data_result.requested_end}"
    )

    st.write(
        "**Actual common-data period:** "
        f"{market_data_result.actual_start} through "
        f"{market_data_result.actual_end}"
    )

    st.caption(
        "The actual period can differ because weekends, exchange holidays, "
        "listing dates, and missing source observations do not produce usable "
        "daily prices."
    )

st.subheader("Adjusted closing-price history")

display_history = (
    prices
    .sort_index(ascending=False)
    .rename_axis("Date")
)

st.dataframe(
    display_history,
    use_container_width=True,
    height=420,
    column_config={
        ticker: st.column_config.NumberColumn(
            ticker,
            format="%.2f",
        )
        for ticker in display_history.columns
    },
)

csv_data = (
    prices
    .rename_axis("Date")
    .to_csv()
    .encode("utf-8")
)

st.download_button(
    label="Download adjusted prices as CSV",
    data=csv_data,
    file_name=(
        "marketlens_adjusted_prices_"
        f"{market_data_result.actual_start}_"
        f"{market_data_result.actual_end}.csv"
    ),
    mime="text/csv",
)

st.warning(
    "MarketLens currently uses yfinance for educational historical-data "
    "access. Data may be delayed, incomplete, adjusted, or unavailable. "
    "This page does not provide investment advice."
)