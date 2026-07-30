"""Portable report generation for MarketLens analyses."""

from __future__ import annotations

from html import escape
import re

from src.persistence import SavedAnalysisSummary


def analysis_report_filename(
    analysis_name: str,
) -> str:
    """Return a filesystem-safe HTML report filename."""
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        analysis_name.lower(),
    ).strip("-")

    return f"marketlens-{slug or 'analysis'}.html"


def generate_analysis_report(
    analysis: SavedAnalysisSummary,
) -> str:
    """Return a standalone HTML summary for a saved analysis."""
    allocation_rows = "".join(
        (
            "<tr>"
            f"<td>{escape(ticker)}</td>"
            f"<td>{weight:.2%}</td>"
            "</tr>"
        )
        for ticker, weight in analysis.weights.items()
    )
    assets = ", ".join(
        escape(ticker)
        for ticker in analysis.asset_tickers
    )
    created_at = analysis.created_at.astimezone().strftime(
        "%b %d, %Y %H:%M %Z"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MarketLens — {escape(analysis.name)}</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: Inter, "Segoe UI", system-ui, sans-serif;
      background: #070b14;
      color: #eef6ff;
    }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at 10% 0%, #17345f 0, transparent 32rem),
        #070b14;
    }}
    main {{
      width: min(960px, calc(100% - 40px));
      margin: 0 auto;
      padding: 64px 0;
    }}
    .eyebrow {{
      color: #5aa9ff;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: .16em;
    }}
    h1 {{
      margin: 10px 0 8px;
      font-size: clamp(34px, 6vw, 58px);
      letter-spacing: -.04em;
    }}
    .muted {{ color: #8fa3bf; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin: 28px 0;
    }}
    .card {{
      padding: 18px;
      border: 1px solid #22304a;
      border-radius: 16px;
      background: rgba(17, 28, 45, .86);
    }}
    .label {{
      color: #8fa3bf;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    .value {{
      margin-top: 8px;
      font-size: 24px;
      font-weight: 750;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border: 1px solid #22304a;
      border-radius: 14px;
    }}
    th, td {{
      padding: 13px 16px;
      border-bottom: 1px solid #22304a;
      text-align: left;
    }}
    th {{ color: #8fa3bf; }}
    footer {{
      margin-top: 36px;
      color: #8fa3bf;
      font-size: 13px;
    }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">MARKETLENS ANALYSIS REPORT</div>
    <h1>{escape(analysis.name)}</h1>
    <p class="muted">
      Created {escape(created_at)} · {assets} vs
      {escape(analysis.benchmark)}
    </p>

    <section class="grid">
      <div class="card">
        <div class="label">Total return</div>
        <div class="value">{analysis.portfolio_total_return:.2%}</div>
      </div>
      <div class="card">
        <div class="label">Annualized return</div>
        <div class="value">{analysis.portfolio_annualized_return:.2%}</div>
      </div>
      <div class="card">
        <div class="label">Annualized volatility</div>
        <div class="value">{analysis.portfolio_annualized_volatility:.2%}</div>
      </div>
      <div class="card">
        <div class="label">Analysis period</div>
        <div class="value">
          {analysis.actual_start:%m/%d/%y} – {analysis.actual_end:%m/%d/%y}
        </div>
      </div>
    </section>

    <h2>Portfolio allocation</h2>
    <table>
      <thead><tr><th>Ticker</th><th>Weight</th></tr></thead>
      <tbody>{allocation_rows}</tbody>
    </table>

    <footer>
      Educational analytics only. Historical performance does not guarantee
      future results, and this report is not personalized investment advice.
    </footer>
  </main>
</body>
</html>
"""
