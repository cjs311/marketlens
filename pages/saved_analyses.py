"""Saved-analysis management page for MarketLens."""

import pandas as pd
import streamlit as st

from src.persistence import (
    PersistenceError,
    delete_saved_analysis,
    get_saved_analysis,
    initialize_database,
    list_saved_analyses,
    restore_saved_analysis,
    save_analysis,
)
from src.portfolio import create_portfolio_signature
from src.reporting import (
    analysis_report_filename,
    generate_analysis_report,
)
from src.ui import page_header


page_header(
    eyebrow="ANALYSIS LIBRARY",
    title="Keep your portfolio research organized.",
    description=(
        "Save, reload, review, and manage portfolio analyses from one "
        "central research library."
    ),
    badge="SQLITE PERSISTENCE",
)

try:
    initialize_database()
except PersistenceError as error:
    st.error(str(error))
    st.stop()

notice = st.session_state.pop(
    "saved_analysis_notice",
    None,
)

if notice:
    st.success(notice)

market_data_result = st.session_state.get(
    "market_data_result"
)
market_data_config = st.session_state.get(
    "market_data_config"
)
portfolio_analytics = st.session_state.get(
    "portfolio_analytics"
)
active_analysis_available = all(
    value is not None
    for value in (
        market_data_result,
        market_data_config,
        portfolio_analytics,
    )
)

st.subheader("Save the active analysis")

if not active_analysis_available:
    st.info(
        "Load market data and apply portfolio weights on Overview before "
        "saving an analysis."
    )

with st.form("save_analysis_form"):
    analysis_name = st.text_input(
        "Analysis name",
        placeholder="Example: Diversified ETF Portfolio",
        max_chars=80,
        disabled=not active_analysis_available,
    )
    save_requested = st.form_submit_button(
        "Save current analysis",
        type="primary",
        use_container_width=True,
        disabled=not active_analysis_available,
    )

if save_requested:
    try:
        saved_summary = save_analysis(
            name=analysis_name,
            market_data_result=market_data_result,
            market_data_config=market_data_config,
            portfolio_analytics=portfolio_analytics,
        )
    except PersistenceError as error:
        st.error(str(error))
    else:
        st.session_state[
            "saved_analysis_notice"
        ] = (
            f'Saved "{saved_summary.name}" with its prices, '
            "weights, dates, and performance snapshot."
        )
        st.rerun()

st.divider()
st.subheader("Saved portfolio analyses")

try:
    saved_analyses = list_saved_analyses()
except PersistenceError as error:
    st.error(str(error))
    st.stop()

if not saved_analyses:
    st.info(
        "No analyses have been saved yet. Your first saved portfolio will "
        "appear here with its allocation, date range, and headline metrics."
    )
    st.stop()

summary_by_id = {
    summary.id: summary
    for summary in saved_analyses
}
selected_id = st.selectbox(
    "Select a saved analysis",
    options=list(summary_by_id),
    format_func=lambda analysis_id: (
        f"{summary_by_id[analysis_id].name} · "
        f"{summary_by_id[analysis_id].created_at:%b %d, %Y %H:%M} UTC"
    ),
)
selected_summary = summary_by_id[
    selected_id
]

summary_columns = st.columns(
    [1, 1, 1, 1.35],
)
summary_columns[0].metric(
    "Portfolio assets",
    f"{len(selected_summary.asset_tickers):,}",
)
summary_columns[1].metric(
    "Benchmark",
    selected_summary.benchmark,
)
summary_columns[2].metric(
    "Total return",
    f"{selected_summary.portfolio_total_return:.2%}",
)
summary_columns[3].metric(
    "Analysis period",
    (
        f"{selected_summary.actual_start:%m/%d/%y} – "
        f"{selected_summary.actual_end:%m/%d/%y}"
    ),
)

performance_columns = st.columns(2)
performance_columns[0].metric(
    "Annualized return",
    f"{selected_summary.portfolio_annualized_return:.2%}",
)
performance_columns[1].metric(
    "Annualized volatility",
    f"{selected_summary.portfolio_annualized_volatility:.2%}",
)

allocation_table = pd.DataFrame(
    {
        "Ticker": selected_summary.weights.keys(),
        "Weight": [
            f"{weight:.2%}"
            for weight in selected_summary.weights.values()
        ],
    }
)

with st.expander(
    "Saved allocation details",
    expanded=True,
):
    st.dataframe(
        allocation_table,
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "Saved analyses include the exact adjusted-price history used at "
        "save time, so reloading does not depend on a fresh data download."
    )

report_html = generate_analysis_report(
    selected_summary
)
action_columns = st.columns(3)

with action_columns[0]:
    reload_requested = st.button(
        "Reload selected analysis",
        type="primary",
        use_container_width=True,
    )

with action_columns[1]:
    st.download_button(
        "Download HTML report",
        data=report_html.encode("utf-8"),
        file_name=analysis_report_filename(
            selected_summary.name
        ),
        mime="text/html",
        use_container_width=True,
    )

with action_columns[2]:
    confirm_delete = st.checkbox(
        "Confirm permanent deletion",
        key=f"confirm_delete_{selected_id}",
    )
    delete_requested = st.button(
        "Delete selected analysis",
        use_container_width=True,
        disabled=not confirm_delete,
    )

if reload_requested:
    try:
        saved_analysis = get_saved_analysis(
            selected_id
        )
        (
            restored_market_data,
            restored_config,
            restored_analytics,
        ) = restore_saved_analysis(
            saved_analysis
        )
    except PersistenceError as error:
        st.error(str(error))
    else:
        portfolio_signature = create_portfolio_signature(
            asset_tickers=(
                restored_config[
                    "asset_tickers"
                ]
            ),
            benchmark=restored_config[
                "benchmark"
            ],
            actual_start=(
                restored_market_data.actual_start
            ),
            actual_end=(
                restored_market_data.actual_end
            ),
        )
        st.session_state[
            "market_data_result"
        ] = restored_market_data
        st.session_state[
            "market_data_config"
        ] = restored_config
        st.session_state[
            "portfolio_signature"
        ] = portfolio_signature
        st.session_state[
            "portfolio_weights"
        ] = restored_analytics.weights
        st.session_state[
            "portfolio_analytics"
        ] = restored_analytics
        st.session_state.pop(
            f"weight_editor_{portfolio_signature}",
            None,
        )
        st.session_state[
            "overview_notice"
        ] = (
            f'Loaded saved analysis "{saved_analysis.name}".'
        )
        st.switch_page("pages/overview.py")

if delete_requested:
    try:
        delete_saved_analysis(
            selected_id
        )
    except PersistenceError as error:
        st.error(str(error))
    else:
        st.session_state[
            "saved_analysis_notice"
        ] = (
            f'Deleted "{selected_summary.name}".'
        )
        st.rerun()

st.divider()
st.subheader("Library index")

library_table = pd.DataFrame(
    [
        {
            "Name": summary.name,
            "Created (UTC)": (
                summary.created_at.strftime(
                    "%Y-%m-%d %H:%M"
                )
            ),
            "Assets": ", ".join(
                summary.asset_tickers
            ),
            "Benchmark": summary.benchmark,
            "Total return": (
                f"{summary.portfolio_total_return:.2%}"
            ),
            "Period": (
                f"{summary.actual_start:%m/%d/%y} – "
                f"{summary.actual_end:%m/%d/%y}"
            ),
        }
        for summary in saved_analyses
    ]
)

st.dataframe(
    library_table,
    hide_index=True,
    use_container_width=True,
)
