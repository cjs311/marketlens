# MarketLens

MarketLens is a production-ready Streamlit dashboard for historical portfolio
performance, risk, composition, and stress analysis. It turns adjusted market
prices into an interactive research workflow that is understandable to
students, junior analysts, and investment-operations teams.

## What MarketLens does

- Loads and validates one to ten portfolio assets through `yfinance`
- Aligns adjusted prices to common trading dates
- Supports custom long-only weights with optional normalization
- Compares portfolio and benchmark performance
- Calculates volatility, drawdown, Sharpe, Sortino, VaR, CVaR, and beta
- Measures concentration, correlation, diversification, and risk contribution
- Models historical-inspired and custom stress scenarios
- Saves exact analysis snapshots to SQLite
- Reloads saved prices and weights without a new market-data request
- Exports adjusted prices, daily returns, stress results, and HTML summaries

## Application workflow

1. **Overview** — choose tickers, benchmark, dates, and portfolio weights.
2. **Risk Analysis** — inspect downside risk and benchmark sensitivity.
3. **Portfolio Composition** — review concentration and diversification.
4. **Stress Testing** — model scenario losses and asset sensitivities.
5. **Saved Analyses** — save, reload, report, or delete research snapshots.
6. **Methodology** — review formulas, assumptions, and limitations.

## Technology stack

- Python 3.12
- Streamlit
- pandas and NumPy
- Plotly
- yfinance
- SQLite
- pytest

## Local installation

From PowerShell:

```powershell
git clone https://github.com/cjs311/marketlens.git
cd marketlens

py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501` if Streamlit does not open automatically.

## Saved-analysis persistence

The application creates `data/marketlens.db` on first use. The database stores:

- Analysis name and creation timestamp
- Asset symbols and benchmark
- Requested and usable date ranges
- Validated portfolio weights
- Exact adjusted-price snapshot
- Data-quality metadata
- Headline performance metrics

Local database files are intentionally excluded from Git. Set
`MARKETLENS_DB_PATH` to use a different writable database location:

```powershell
$env:MARKETLENS_DB_PATH = "C:\marketlens-data\marketlens.db"
python -m streamlit run app.py
```

## Testing

Run the full automated suite:

```powershell
python -m pytest
```

Then run the compile and whitespace checks:

```powershell
python -m compileall app.py pages src tests
git diff --check
```

The tests cover input validation, data preparation, portfolio calculations,
risk metrics, composition analytics, stress scenarios, SQLite round trips,
record deletion, duplicate handling, and HTML report generation.

## Deployment

MarketLens is ready for Streamlit Community Cloud:

1. Push the latest `main` branch to GitHub.
2. In Streamlit Community Cloud, create an app from
   `cjs311/marketlens`.
3. Select branch `main` and entry point `app.py`.
4. Select Python 3.12 in advanced settings.
5. Deploy and run one portfolio through every page.

Streamlit Community Cloud uses ephemeral local storage. Saved analyses can
reset when the app restarts or is redeployed. That is acceptable for the public
portfolio demo; durable multi-user production storage would require a hosted
database or persistent volume.

## Calculation assumptions

- Returns use consecutive adjusted closing prices.
- Annualized calculations assume 252 trading days.
- Portfolio weights are applied to each daily return, representing daily
  rebalancing.
- The default annual risk-free rate is 0%.
- Historical VaR and CVaR are sample-based and do not represent maximum loss.
- Stress tests are simplified static-shock models, not historical replays.
- Taxes, fees, transaction costs, slippage, and liquidity are not modeled.

## Project structure

```text
marketlens/
├── app.py
├── pages/
│   ├── overview.py
│   ├── portfolio.py
│   ├── risk_analysis.py
│   ├── saved_analyses.py
│   ├── stress_testing.py
│   └── methodology.py
├── src/
│   ├── composition.py
│   ├── data_loader.py
│   ├── persistence.py
│   ├── portfolio.py
│   ├── reporting.py
│   ├── risk.py
│   ├── stress.py
│   ├── ui.py
│   └── validation.py
└── tests/
```

## Disclaimer

MarketLens is an educational analytics project. It does not place trades,
guarantee results, or provide personalized investment advice. Historical
performance does not guarantee future results.
