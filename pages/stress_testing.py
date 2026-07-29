"""Portfolio stress-testing page for MarketLens."""

import pandas as pd
import plotly.express as px
import streamlit as st

from src.stress import (
    SCENARIOS,
    StressCalculationError,
    calculate_scenario_comparison,
    calculate_stress_test,
)
from src.ui import page_header

def format_percentage(
    value: float,
) -> str:
    """Format a decimal percentage."""
    return f"{value:.2%}"


def format_currency(
    value: float,
) -> str:
    """Format a dollar value."""
    return f"${value:,.2f}"


page_header(
    eyebrow="SCENARIO LAB",
    title="Pressure-test the portfolio.",
    description=(
        "Model historical-inspired and custom market shocks, adjust asset "
        "sensitivities, and estimate losses before they happen."
    ),
    badge="INTERACTIVE MODEL",
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
        "Stress Testing."
    )
    st.stop()

weights = portfolio_analytics.weights
benchmark_symbol = market_data_config["benchmark"]

st.info(
    "Stress Testing uses the active portfolio weights from Overview. "
    "Sensitivity and asset-specific shock values are modeling assumptions "
    "that you can edit below."
)

summary_values = (
    (
        "Portfolio assets",
        f"{len(weights):,}",
    ),
    (
        "Benchmark reference",
        benchmark_symbol,
    ),
    (
        "Analysis start",
        f"{market_data_result.actual_start:%b %d, %Y}",
    ),
    (
        "Analysis end",
        f"{market_data_result.actual_end:%b %d, %Y}",
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
st.subheader("Scenario configuration")

configuration_columns = st.columns(
    [
        1.5,
        1.0,
    ]
)

scenario_options = [
    *SCENARIOS.keys(),
    "Custom shock",
]

with configuration_columns[0]:
    selected_scenario = st.selectbox(
        "Stress scenario",
        options=scenario_options,
        help=(
            "Historical-style scenarios are simplified assumptions, "
            "not exact historical replays."
        ),
    )

    if selected_scenario == "Custom shock":
        custom_shock_percent = st.number_input(
            "Custom broad-market shock",
            min_value=-100.0,
            max_value=50.0,
            value=-15.0,
            step=1.0,
            format="%.1f",
            help=(
                "Enter -15 for a hypothetical 15% broad-market decline."
            ),
        )

        market_shock = (
            float(custom_shock_percent)
            / 100.0
        )

        scenario_description = (
            "A user-defined broad-market shock."
        )
    else:
        scenario = SCENARIOS[
            selected_scenario
        ]

        market_shock = scenario.market_shock
        scenario_description = (
            scenario.description
        )

        st.metric(
            "Modeled broad-market shock",
            format_percentage(
                market_shock
            ),
        )

    st.caption(
        scenario_description
    )

with configuration_columns[1]:
    initial_portfolio_value = st.number_input(
        "Starting portfolio value",
        min_value=1.0,
        value=10_000.0,
        step=1_000.0,
        format="%.2f",
        help=(
            "Used to estimate dollar profit, loss, and ending value."
        ),
    )

st.divider()
st.subheader("Asset-level assumptions")

st.markdown(
    """
    **Sensitivity** estimates how strongly an asset reacts to the broad-market
    shock. A value of `1.00` matches the market, `1.25` reacts 25% more, and a
    negative value moves in the opposite direction.

    **Specific shock** adds an extra asset-level adjustment after the market
    sensitivity is applied.
    """
)

allocation_signature = tuple(
    (
        str(ticker),
        round(
            float(weight),
            8,
        ),
    )
    for ticker, weight in weights.items()
)

if (
    st.session_state.get(
        "stress_allocation_signature"
    )
    != allocation_signature
):
    st.session_state[
        "stress_allocation_signature"
    ] = allocation_signature

    st.session_state.pop(
        "stress_assumptions_editor",
        None,
    )

assumption_input = pd.DataFrame(
    {
        "Ticker": [
            str(ticker)
            for ticker in weights.index
        ],
        "Weight (%)": (
            weights.to_numpy(
                dtype="float64"
            )
            * 100.0
        ),
        "Sensitivity": 1.0,
        "Specific shock (%)": 0.0,
    }
)

edited_assumptions = st.data_editor(
    assumption_input,
    hide_index=True,
    use_container_width=True,
    disabled=[
        "Ticker",
        "Weight (%)",
    ],
    num_rows="fixed",
    key="stress_assumptions_editor",
    column_config={
        "Ticker": st.column_config.TextColumn(
            "Ticker"
        ),
        "Weight (%)": st.column_config.NumberColumn(
            "Weight (%)",
            format="%.2f%%",
        ),
        "Sensitivity": st.column_config.NumberColumn(
            "Sensitivity",
            min_value=-3.0,
            max_value=5.0,
            step=0.05,
            format="%.2f",
        ),
        "Specific shock (%)": st.column_config.NumberColumn(
            "Specific shock (%)",
            min_value=-100.0,
            max_value=100.0,
            step=1.0,
            format="%.1f%%",
        ),
    },
)

sensitivities = pd.Series(
    edited_assumptions[
        "Sensitivity"
    ].to_numpy(),
    index=edited_assumptions[
        "Ticker"
    ].tolist(),
    dtype="float64",
)

specific_shocks = pd.Series(
    (
        edited_assumptions[
            "Specific shock (%)"
        ].to_numpy()
        / 100.0
    ),
    index=edited_assumptions[
        "Ticker"
    ].tolist(),
    dtype="float64",
)

try:
    stress_result = calculate_stress_test(
        weights=weights,
        market_shock=market_shock,
        sensitivities=sensitivities,
        specific_shocks=specific_shocks,
        initial_portfolio_value=(
            initial_portfolio_value
        ),
    )
except StressCalculationError as error:
    st.error(str(error))
    st.stop()

metrics = stress_result.metrics

st.divider()
st.subheader("Estimated portfolio impact")

impact_cards = (
    (
        "Portfolio stressed return",
        format_percentage(
            float(
                metrics[
                    "portfolio_stressed_return"
                ]
            )
        ),
        "Weighted result of all modeled asset shocks.",
    ),
    (
        "Estimated profit / loss",
        format_currency(
            float(
                metrics[
                    "portfolio_profit_loss"
                ]
            )
        ),
        "Estimated dollar change under the selected scenario.",
    ),
    (
        "Estimated loss",
        format_currency(
            float(
                metrics[
                    "estimated_loss"
                ]
            )
        ),
        "Displayed as zero when the modeled result is a gain.",
    ),
    (
        "Ending portfolio value",
        format_currency(
            float(
                metrics[
                    "ending_portfolio_value"
                ]
            )
        ),
        "Starting value plus the modeled portfolio profit or loss.",
    ),
)

for column, (
    label,
    value,
    help_text,
) in zip(
    st.columns(4),
    impact_cards,
):
    column.metric(
        label,
        value,
        help=help_text,
    )

detail_columns = st.columns(3)

detail_columns[0].metric(
    "Largest detractor",
    str(
        metrics[
            "largest_detractor"
        ]
    ),
)

detail_columns[1].metric(
    "Worst stressed asset",
    str(
        metrics[
            "worst_asset"
        ]
    ),
)

detail_columns[2].metric(
    "Loss floors applied",
    f"{int(metrics['floor_count']):,}",
    help=(
        "An asset's modeled loss is capped at 100% to reflect "
        "limited liability for a long-only position."
    ),
)

if int(
    metrics["floor_count"]
) > 0:
    st.warning(
        "At least one raw asset shock was below -100%. MarketLens capped "
        "that asset's modeled loss at -100%."
    )

portfolio_return = float(
    metrics[
        "portfolio_stressed_return"
    ]
)

if portfolio_return <= -0.25:
    st.error(
        "Severe modeled portfolio loss: the selected assumptions produce "
        f"an estimated decline of {abs(portfolio_return):.1%}."
    )
elif portfolio_return < 0.0:
    st.warning(
        "The selected scenario produces a modeled portfolio loss of "
        f"{abs(portfolio_return):.1%}."
    )
else:
    st.success(
        "The selected assumptions produce a non-negative modeled "
        "portfolio result."
    )

st.divider()
st.subheader("Asset-level impact")

asset_results = (
    stress_result
    .asset_results
    .rename_axis("Ticker")
    .reset_index()
)

chart_columns = st.columns(2)

asset_shock_figure = px.bar(
    asset_results.sort_values(
        "stressed_return",
        ascending=True,
    ),
    x="stressed_return",
    y="Ticker",
    orientation="h",
    color="Ticker",
    text="stressed_return",
    custom_data=[
        "weight",
        "sensitivity",
        "market_component",
        "specific_shock",
    ],
)

asset_shock_figure.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Weight: %{customdata[0]:.2%}<br>"
        "Sensitivity: %{customdata[1]:.2f}<br>"
        "Market component: %{customdata[2]:.2%}<br>"
        "Specific shock: %{customdata[3]:.2%}<br>"
        "Final asset shock: %{x:.2%}"
        "<extra></extra>"
    ),
)

asset_shock_figure.add_vline(
    x=0.0,
    line_color="#64748B",
    line_width=1,
)

asset_shock_figure.update_layout(
    title="Modeled Return by Asset",
    xaxis_title="Stressed asset return",
    yaxis_title="",
    xaxis_tickformat=".0%",
    showlegend=False,
    height=440,
    margin={
        "l": 20,
        "r": 40,
        "t": 65,
        "b": 20,
    },
)

chart_columns[0].plotly_chart(
    asset_shock_figure,
    use_container_width=True,
)

contribution_figure = px.bar(
    asset_results.sort_values(
        "portfolio_contribution",
        ascending=True,
    ),
    x="portfolio_contribution",
    y="Ticker",
    orientation="h",
    color="Ticker",
    text="portfolio_contribution",
    custom_data=[
        "weight",
        "stressed_return",
        "asset_profit_loss",
    ],
)

contribution_figure.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
    hovertemplate=(
        "<b>%{y}</b><br>"
        "Weight: %{customdata[0]:.2%}<br>"
        "Asset shock: %{customdata[1]:.2%}<br>"
        "Dollar P/L: $%{customdata[2]:,.2f}<br>"
        "Portfolio contribution: %{x:.2%}"
        "<extra></extra>"
    ),
)

contribution_figure.add_vline(
    x=0.0,
    line_color="#64748B",
    line_width=1,
)

contribution_figure.update_layout(
    title="Contribution to Portfolio Stress Result",
    xaxis_title="Contribution to total portfolio return",
    yaxis_title="",
    xaxis_tickformat=".0%",
    showlegend=False,
    height=440,
    margin={
        "l": 20,
        "r": 40,
        "t": 65,
        "b": 20,
    },
)

chart_columns[1].plotly_chart(
    contribution_figure,
    use_container_width=True,
)

display_results = (
    asset_results[
        [
            "Ticker",
            "weight",
            "sensitivity",
            "market_component",
            "specific_shock",
            "stressed_return",
            "portfolio_contribution",
            "starting_value",
            "asset_profit_loss",
            "stressed_value",
            "loss_floor_applied",
        ]
    ]
    .rename(
        columns={
            "weight": "Weight",
            "sensitivity": "Sensitivity",
            "market_component": "Market component",
            "specific_shock": "Specific shock",
            "stressed_return": "Stressed return",
            "portfolio_contribution": "Portfolio contribution",
            "starting_value": "Starting value",
            "asset_profit_loss": "Asset P/L",
            "stressed_value": "Stressed value",
            "loss_floor_applied": "Loss floor applied",
        }
    )
)

percentage_columns = [
    "Weight",
    "Market component",
    "Specific shock",
    "Stressed return",
    "Portfolio contribution",
]

display_results[
    percentage_columns
] = (
    display_results[
        percentage_columns
    ]
    * 100.0
)

st.dataframe(
    display_results,
    hide_index=True,
    use_container_width=True,
    column_config={
        **{
            column: st.column_config.NumberColumn(
                column,
                format="%.2f%%",
            )
            for column in percentage_columns
        },
        "Sensitivity": st.column_config.NumberColumn(
            "Sensitivity",
            format="%.2f",
        ),
        "Starting value": st.column_config.NumberColumn(
            "Starting value",
            format="$%.2f",
        ),
        "Asset P/L": st.column_config.NumberColumn(
            "Asset P/L",
            format="$%.2f",
        ),
        "Stressed value": st.column_config.NumberColumn(
            "Stressed value",
            format="$%.2f",
        ),
    },
)

st.divider()
st.subheader("Scenario comparison")

comparison_scenarios = {
    name: scenario.market_shock
    for name, scenario in SCENARIOS.items()
}

if selected_scenario == "Custom shock":
    comparison_scenarios[
        "Custom shock"
    ] = market_shock

try:
    comparison = calculate_scenario_comparison(
        weights=weights,
        sensitivities=sensitivities,
        specific_shocks=specific_shocks,
        initial_portfolio_value=(
            initial_portfolio_value
        ),
        scenarios=comparison_scenarios,
    )
except StressCalculationError as error:
    st.error(str(error))
    st.stop()

comparison_chart_data = (
    comparison
    .rename_axis("Scenario")
    .reset_index()
)

scenario_figure = px.bar(
    comparison_chart_data,
    x="Scenario",
    y="portfolio_stressed_return",
    color="Scenario",
    text="portfolio_stressed_return",
    custom_data=[
        "market_shock",
        "estimated_loss",
        "ending_portfolio_value",
        "largest_detractor",
    ],
)

scenario_figure.update_traces(
    texttemplate="%{text:.1%}",
    textposition="outside",
    hovertemplate=(
        "<b>%{x}</b><br>"
        "Market shock: %{customdata[0]:.1%}<br>"
        "Portfolio result: %{y:.2%}<br>"
        "Estimated loss: $%{customdata[1]:,.2f}<br>"
        "Ending value: $%{customdata[2]:,.2f}<br>"
        "Largest detractor: %{customdata[3]}"
        "<extra></extra>"
    ),
)

scenario_figure.add_hline(
    y=0.0,
    line_color="#64748B",
    line_width=1,
)

scenario_figure.update_layout(
    title="Portfolio Result Across Stress Scenarios",
    xaxis_title="",
    yaxis_title="Modeled portfolio return",
    yaxis_tickformat=".0%",
    showlegend=False,
    height=500,
    margin={
        "l": 20,
        "r": 20,
        "t": 65,
        "b": 90,
    },
)

st.plotly_chart(
    scenario_figure,
    use_container_width=True,
)

display_comparison = (
    comparison
    .reset_index()
    .rename(
        columns={
            "market_shock": "Market shock",
            "portfolio_stressed_return": "Portfolio result",
            "portfolio_profit_loss": "Portfolio P/L",
            "estimated_loss": "Estimated loss",
            "ending_portfolio_value": "Ending value",
            "largest_detractor": "Largest detractor",
        }
    )
)

display_comparison[
    [
        "Market shock",
        "Portfolio result",
    ]
] = (
    display_comparison[
        [
            "Market shock",
            "Portfolio result",
        ]
    ]
    * 100.0
)

st.dataframe(
    display_comparison,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Market shock": st.column_config.NumberColumn(
            "Market shock",
            format="%.2f%%",
        ),
        "Portfolio result": st.column_config.NumberColumn(
            "Portfolio result",
            format="%.2f%%",
        ),
        "Portfolio P/L": st.column_config.NumberColumn(
            "Portfolio P/L",
            format="$%.2f",
        ),
        "Estimated loss": st.column_config.NumberColumn(
            "Estimated loss",
            format="$%.2f",
        ),
        "Ending value": st.column_config.NumberColumn(
            "Ending value",
            format="$%.2f",
        ),
    },
)

st.divider()
st.subheader("Export stress-test data")

export_asset_results = (
    stress_result
    .asset_results
    .copy()
)

export_asset_results.insert(
    0,
    "scenario",
    selected_scenario,
)

export_asset_results.insert(
    1,
    "market_shock",
    market_shock,
)

asset_csv = (
    export_asset_results
    .rename_axis("Ticker")
    .to_csv()
    .encode("utf-8")
)

comparison_csv = (
    comparison
    .rename_axis("Scenario")
    .to_csv()
    .encode("utf-8")
)

download_columns = st.columns(2)

download_columns[0].download_button(
    label="Download selected stress test as CSV",
    data=asset_csv,
    file_name=(
        "marketlens_stress_test_"
        f"{market_data_result.actual_start}_"
        f"{market_data_result.actual_end}.csv"
    ),
    mime="text/csv",
)

download_columns[1].download_button(
    label="Download scenario comparison as CSV",
    data=comparison_csv,
    file_name=(
        "marketlens_stress_scenarios_"
        f"{market_data_result.actual_start}_"
        f"{market_data_result.actual_end}.csv"
    ),
    mime="text/csv",
)

with st.expander(
    "How MarketLens calculates stress results"
):
    st.markdown(
        """
        1. Each asset receives a user-defined **market sensitivity**.
        2. MarketLens multiplies the broad-market shock by that sensitivity.
        3. Any asset-specific shock is added to the market-driven result.
        4. Asset losses are floored at -100% for a long-only position.
        5. Each final asset shock is multiplied by its portfolio weight.
        6. Weighted contributions are added to estimate the total portfolio result.
        7. The portfolio result is applied to the entered starting value to estimate
           dollar profit or loss and ending value.

        This is a transparent linear sensitivity model. It does not model options,
        leverage, margin calls, changing correlations, liquidity problems, or
        nonlinear security behavior.
        """
    )

st.warning(
    "Stress scenarios are hypothetical estimates, not forecasts. Real market "
    "losses can differ because sensitivities and relationships may change "
    "during severe conditions."
)

st.caption(
    "MarketLens is an educational analytics project. Stress-test results "
    "are not personalized investment advice."
)