"""Shared visual design system for MarketLens."""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


MARKETLENS_COLORS = {
    "background": "#070B14",
    "surface": "#0D1421",
    "surface_raised": "#111C2D",
    "border": "#22304A",
    "border_bright": "#30496F",
    "text": "#EEF6FF",
    "text_muted": "#8FA3BF",
    "blue": "#5AA9FF",
    "cyan": "#38D9C5",
    "violet": "#9A7CFF",
    "green": "#39D98A",
    "red": "#FF6B7A",
    "amber": "#F5B84B",
}


CHART_COLORS = [
    "#5AA9FF",
    "#9A7CFF",
    "#38D9C5",
    "#F5B84B",
    "#FF6B7A",
    "#63E6BE",
    "#74C0FC",
    "#B197FC",
    "#FFA94D",
    "#F783AC",
]


def install_plotly_theme() -> None:
    """Install the shared MarketLens Plotly theme."""
    pio.templates["marketlens"] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plot_bgcolor="rgba(0, 0, 0, 0)",
            font={
                "family": (
                    "Inter, Segoe UI, system-ui, "
                    "-apple-system, sans-serif"
                ),
                "color": MARKETLENS_COLORS["text_muted"],
                "size": 13,
            },
            title={
                "font": {
                    "color": MARKETLENS_COLORS["text"],
                    "size": 18,
                },
                "x": 0.02,
                "xanchor": "left",
            },
            colorway=CHART_COLORS,
            piecolorway=CHART_COLORS,
            hoverlabel={
                "bgcolor": "#111C2D",
                "bordercolor": "#30496F",
                "font": {
                    "color": "#EEF6FF",
                    "family": (
                        "Inter, Segoe UI, system-ui, "
                        "-apple-system, sans-serif"
                    ),
                    "size": 13,
                },
            },
            legend={
                "bgcolor": "rgba(0, 0, 0, 0)",
                "font": {
                    "color": MARKETLENS_COLORS["text_muted"],
                },
            },
            xaxis={
                "gridcolor": "rgba(143, 163, 191, 0.12)",
                "linecolor": "rgba(143, 163, 191, 0.16)",
                "zerolinecolor": "rgba(143, 163, 191, 0.22)",
                "tickfont": {
                    "color": MARKETLENS_COLORS["text_muted"],
                },
                "title_font": {
                    "color": MARKETLENS_COLORS["text_muted"],
                },
                "automargin": True,
            },
            yaxis={
                "gridcolor": "rgba(143, 163, 191, 0.12)",
                "linecolor": "rgba(143, 163, 191, 0.16)",
                "zerolinecolor": "rgba(143, 163, 191, 0.22)",
                "tickfont": {
                    "color": MARKETLENS_COLORS["text_muted"],
                },
                "title_font": {
                    "color": MARKETLENS_COLORS["text_muted"],
                },
                "automargin": True,
            },
            margin={
                "l": 30,
                "r": 25,
                "t": 65,
                "b": 35,
            },
        )
    )

    pio.templates.default = "marketlens"


MARKETLENS_CSS = """
<style>
:root {
    color-scheme: dark;
    --ml-background: #070B14;
    --ml-surface: #0D1421;
    --ml-surface-raised: #111C2D;
    --ml-border: #22304A;
    --ml-border-bright: #30496F;
    --ml-text: #EEF6FF;
    --ml-muted: #8FA3BF;
    --ml-blue: #5AA9FF;
    --ml-cyan: #38D9C5;
    --ml-violet: #9A7CFF;
    --ml-green: #39D98A;
    --ml-red: #FF6B7A;
    --ml-amber: #F5B84B;
}

html,
body,
[class*="css"] {
    font-family:
        Inter,
        "Segoe UI",
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 12% 0%,
            rgba(90, 169, 255, 0.10),
            transparent 26rem
        ),
        radial-gradient(
            circle at 88% 8%,
            rgba(154, 124, 255, 0.08),
            transparent 28rem
        ),
        linear-gradient(
            180deg,
            #070B14 0%,
            #080D17 46%,
            #070B14 100%
        );
    color: var(--ml-text);
}

header[data-testid="stHeader"] {
    background: rgba(7, 11, 20, 0.78);
    border-bottom: 1px solid rgba(48, 73, 111, 0.35);
    backdrop-filter: blur(18px);
}

div[data-testid="stToolbar"] {
    right: 1.2rem;
}

.block-container {
    width: 100%;
    max-width: 1480px;
    padding-top: 2rem;
    padding-bottom: 5rem;
}

h1,
h2,
h3 {
    color: var(--ml-text);
    letter-spacing: -0.025em;
}

h2 {
    margin-top: 0.35rem;
}

p,
label,
[data-testid="stCaptionContainer"] {
    color: var(--ml-muted);
}

hr {
    border-color: rgba(48, 73, 111, 0.42) !important;
    margin: 2.25rem 0 !important;
}

/* Sidebar */

section[data-testid="stSidebar"] {
    background:
        radial-gradient(
            circle at 15% 4%,
            rgba(90, 169, 255, 0.11),
            transparent 16rem
        ),
        linear-gradient(
            180deg,
            #0A111E 0%,
            #080D17 100%
        );
    border-right: 1px solid rgba(48, 73, 111, 0.48);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1rem;
}

div[data-testid="stSidebarNav"] a {
    border: 1px solid transparent;
    border-radius: 11px;
    color: var(--ml-muted);
    margin: 0.16rem 0.55rem;
    padding: 0.7rem 0.8rem;
    transition:
        background 160ms ease,
        border-color 160ms ease,
        color 160ms ease,
        transform 160ms ease;
}

div[data-testid="stSidebarNav"] a:hover {
    background: rgba(90, 169, 255, 0.08);
    border-color: rgba(90, 169, 255, 0.18);
    color: var(--ml-text);
    transform: translateX(2px);
}

div[data-testid="stSidebarNav"] a[aria-current="page"] {
    background:
        linear-gradient(
            120deg,
            rgba(90, 169, 255, 0.17),
            rgba(154, 124, 255, 0.10)
        );
    border-color: rgba(90, 169, 255, 0.30);
    color: #FFFFFF;
    box-shadow:
        inset 3px 0 0 var(--ml-blue),
        0 8px 24px rgba(0, 0, 0, 0.16);
}

.ml-sidebar-brand {
    margin: 1.2rem 0.55rem 0.6rem;
    padding: 1rem;
    background: rgba(17, 28, 45, 0.68);
    border: 1px solid rgba(48, 73, 111, 0.55);
    border-radius: 15px;
}

.ml-brand-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.ml-brand-mark {
    width: 2.65rem;
    height: 2.65rem;
    display: grid;
    place-items: center;
    color: #FFFFFF;
    font-size: 0.8rem;
    font-weight: 800;
    letter-spacing: -0.04em;
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 12px;
    background:
        linear-gradient(
            135deg,
            var(--ml-blue),
            var(--ml-violet)
        );
    box-shadow: 0 10px 26px rgba(90, 169, 255, 0.22);
}

.ml-brand-name {
    color: var(--ml-text);
    font-size: 1rem;
    font-weight: 750;
    letter-spacing: -0.02em;
}

.ml-brand-label {
    color: var(--ml-muted);
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    margin-top: 0.18rem;
}

.ml-sidebar-copy {
    color: var(--ml-muted);
    font-size: 0.72rem;
    line-height: 1.55;
    margin: 0.85rem 0 0;
}

/* Page hero */

.ml-page-hero {
    position: relative;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 2rem;
    overflow: hidden;
    margin: 0 0 1.8rem;
    padding: 1.8rem 1.9rem;
    background:
        linear-gradient(
            125deg,
            rgba(17, 28, 45, 0.96),
            rgba(11, 18, 31, 0.93)
        );
    border: 1px solid rgba(48, 73, 111, 0.64);
    border-radius: 22px;
    box-shadow:
        0 22px 60px rgba(0, 0, 0, 0.24),
        inset 0 1px 0 rgba(255, 255, 255, 0.035);
    animation: ml-fade-up 420ms ease both;
}

.ml-page-hero::after {
    content: "";
    position: absolute;
    width: 25rem;
    height: 25rem;
    right: -12rem;
    top: -17rem;
    pointer-events: none;
    border-radius: 50%;
    background: rgba(90, 169, 255, 0.19);
    filter: blur(22px);
}

.ml-page-hero-content {
    position: relative;
    z-index: 1;
    max-width: 55rem;
}

.ml-eyebrow {
    color: var(--ml-cyan);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.18em;
    margin: 0 0 0.6rem;
    text-transform: uppercase;
}

.ml-page-title {
    color: #FFFFFF;
    font-size: clamp(2rem, 4vw, 3.35rem);
    font-weight: 780;
    letter-spacing: -0.045em;
    line-height: 1.02;
    margin: 0;
}

.ml-page-description {
    color: #9FB2CB;
    font-size: 0.98rem;
    line-height: 1.7;
    margin: 0.8rem 0 0;
    max-width: 48rem;
}

.ml-live-badge {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    gap: 0.5rem;
    color: #B8C8DC;
    font-size: 0.65rem;
    font-weight: 750;
    letter-spacing: 0.10em;
    white-space: nowrap;
    padding: 0.55rem 0.72rem;
    border: 1px solid rgba(56, 217, 197, 0.27);
    border-radius: 999px;
    background: rgba(56, 217, 197, 0.07);
}

.ml-live-dot {
    width: 0.46rem;
    height: 0.46rem;
    border-radius: 50%;
    background: var(--ml-cyan);
    box-shadow: 0 0 0 4px rgba(56, 217, 197, 0.11);
}

/* Metrics */

div[data-testid="stMetric"] {
    min-height: 7.5rem;
    padding: 1.05rem 1.1rem;
    background:
        linear-gradient(
            145deg,
            rgba(17, 28, 45, 0.94),
            rgba(12, 20, 33, 0.94)
        );
    border: 1px solid rgba(48, 73, 111, 0.55);
    border-radius: 16px;
    box-shadow:
        0 14px 34px rgba(0, 0, 0, 0.17),
        inset 0 1px 0 rgba(255, 255, 255, 0.025);
    transition:
        border-color 180ms ease,
        transform 180ms ease,
        box-shadow 180ms ease;
}

div[data-testid="stMetric"]:hover {
    border-color: rgba(90, 169, 255, 0.44);
    box-shadow: 0 18px 42px rgba(0, 0, 0, 0.23);
    transform: translateY(-2px);
}

div[data-testid="stMetricLabel"] p {
    color: var(--ml-muted);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.055em;
    text-transform: uppercase;
}

div[data-testid="stMetricValue"] {
    color: var(--ml-text);
    font-size: clamp(1.35rem, 2.4vw, 2rem);
    font-weight: 740;
    letter-spacing: -0.035em;
}

div[data-testid="stMetricDelta"] {
    font-size: 0.75rem;
    font-weight: 650;
}

/* Charts and tables */

div[data-testid="stPlotlyChart"] {
    overflow: hidden;
    padding: 0.4rem;
    background:
        linear-gradient(
            145deg,
            rgba(17, 28, 45, 0.89),
            rgba(11, 18, 31, 0.89)
        );
    border: 1px solid rgba(48, 73, 111, 0.52);
    border-radius: 18px;
    box-shadow: 0 16px 38px rgba(0, 0, 0, 0.18);
}

.modebar {
    opacity: 0;
    transition: opacity 160ms ease;
}

div[data-testid="stPlotlyChart"]:hover .modebar {
    opacity: 0.76;
}

div[data-testid="stDataFrame"] {
    overflow: hidden;
    border: 1px solid rgba(48, 73, 111, 0.58);
    border-radius: 15px;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.15);
}

/* Inputs */

div[data-baseweb="input"],
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
div[data-baseweb="textarea"] {
    background: rgba(13, 20, 33, 0.92) !important;
    border-color: rgba(48, 73, 111, 0.70) !important;
    border-radius: 11px !important;
}

div[data-baseweb="input"]:focus-within,
div[data-baseweb="select"] > div:focus-within,
div[data-baseweb="base-input"]:focus-within,
div[data-baseweb="textarea"]:focus-within {
    border-color: rgba(90, 169, 255, 0.82) !important;
    box-shadow: 0 0 0 3px rgba(90, 169, 255, 0.11);
}

div[data-testid="stDateInput"],
div[data-testid="stNumberInput"],
div[data-testid="stTextInput"],
div[data-testid="stSelectbox"] {
    margin-bottom: 0.15rem;
}

/* Buttons */

div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
    min-height: 2.72rem;
    color: var(--ml-text);
    font-weight: 700;
    border: 1px solid rgba(90, 169, 255, 0.38);
    border-radius: 11px;
    background:
        linear-gradient(
            125deg,
            rgba(90, 169, 255, 0.16),
            rgba(154, 124, 255, 0.12)
        );
    transition:
        transform 160ms ease,
        border-color 160ms ease,
        box-shadow 160ms ease;
}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    color: #FFFFFF;
    border-color: rgba(90, 169, 255, 0.76);
    box-shadow: 0 10px 28px rgba(90, 169, 255, 0.13);
    transform: translateY(-1px);
}

button[kind="primary"] {
    color: #FFFFFF !important;
    border: none !important;
    background:
        linear-gradient(
            120deg,
            #377DFF,
            #6C63FF
        ) !important;
    box-shadow: 0 12px 30px rgba(55, 125, 255, 0.28);
}

/* Streamlit wraps button labels in child elements. */
button[kind="primary"] p,
button[kind="primary"] span {
    color: #FFFFFF !important;
    font-weight: 750 !important;
}

/* Tabs, alerts and expanders */

div[data-baseweb="tab-list"] {
    gap: 0.5rem;
    padding: 0.32rem;
    border: 1px solid rgba(48, 73, 111, 0.42);
    border-radius: 13px;
    background: rgba(13, 20, 33, 0.70);
}

button[data-baseweb="tab"] {
    border-radius: 9px;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(90, 169, 255, 0.12);
}

div[data-testid="stAlert"] {
    border: 1px solid rgba(48, 73, 111, 0.60);
    border-radius: 13px;
    background: rgba(17, 28, 45, 0.78);
}

details {
    overflow: hidden;
    background: rgba(13, 20, 33, 0.78);
    border: 1px solid rgba(48, 73, 111, 0.52) !important;
    border-radius: 13px !important;
}

code {
    color: #B6CFFF;
    background: rgba(90, 169, 255, 0.10);
    border-radius: 6px;
}

/* Scrollbars */

* {
    scrollbar-width: thin;
    scrollbar-color: #30496F #0A111E;
}

*::-webkit-scrollbar {
    width: 9px;
    height: 9px;
}

*::-webkit-scrollbar-track {
    background: #0A111E;
}

*::-webkit-scrollbar-thumb {
    background: #30496F;
    border: 2px solid #0A111E;
    border-radius: 999px;
}

/* Motion */

@keyframes ml-fade-up {
    from {
        opacity: 0;
        transform: translateY(8px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@media (max-width: 900px) {
    .block-container {
        padding-top: 1.25rem;
    }

    .ml-page-hero {
        flex-direction: column;
        gap: 1.15rem;
        padding: 1.35rem;
    }

    .ml-page-title {
        font-size: 2.15rem;
    }

    .ml-live-badge {
        align-self: flex-start;
    }

    div[data-testid="stMetric"] {
        min-height: 6.7rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }
}
/* Ensure primary and form-submit button labels remain visible. */
div[data-testid="stFormSubmitButton"] button,
div[data-testid="stFormSubmitButton"] button *,
button[kind="primary"],
button[kind="primary"] * {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 750 !important;
}

div[data-testid="stFormSubmitButton"] button {
    border: none !important;
    background: linear-gradient(
        120deg,
        #377DFF,
        #6C63FF
    ) !important;
    box-shadow: 0 12px 30px rgba(55, 125, 255, 0.28);
}
</style>
"""


def inject_styles() -> None:
    """Inject the shared MarketLens stylesheet."""
    st.html(MARKETLENS_CSS)


def render_sidebar_brand() -> None:
    """Render the compact sidebar identity card."""
    with st.sidebar:
        st.html(
            """
            <div class="ml-sidebar-brand">
                <div class="ml-brand-row">
                    <div class="ml-brand-mark">ML</div>
                    <div>
                        <div class="ml-brand-name">MarketLens</div>
                        <div class="ml-brand-label">
                            PORTFOLIO INTELLIGENCE
                        </div>
                    </div>
                </div>
                <p class="ml-sidebar-copy">
                    Performance, risk, composition, drawdown, and
                    stress analytics in one focused workspace.
                </p>
            </div>
            """
        )


def configure_page(
    title: str,
    icon: str = "◈",
) -> None:
    """Configure and style one MarketLens page."""
    st.set_page_config(
        page_title=f"{title} · MarketLens",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    install_plotly_theme()
    inject_styles()
    render_sidebar_brand()


def page_header(
    eyebrow: str,
    title: str,
    description: str,
    badge: str = "ANALYSIS WORKSPACE",
) -> None:
    """Render a polished MarketLens page header."""
    safe_eyebrow = escape(str(eyebrow))
    safe_title = escape(str(title))
    safe_description = escape(str(description))
    safe_badge = escape(str(badge))

    st.html(
        f"""
        <div class="ml-page-hero">
            <div class="ml-page-hero-content">
                <p class="ml-eyebrow">{safe_eyebrow}</p>
                <h1 class="ml-page-title">{safe_title}</h1>
                <p class="ml-page-description">
                    {safe_description}
                </p>
            </div>
            <div class="ml-live-badge">
                <span class="ml-live-dot"></span>
                {safe_badge}
            </div>
        </div>
        """
    )