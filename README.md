# MarketLens

MarketLens is a Python and Streamlit market-risk and portfolio-analytics
dashboard. It is designed to transform historical market data into readable
portfolio performance, exposure, and risk information.

## Project status

MarketLens is currently under active development.

Day 1 includes:

- Python project setup
- Streamlit multipage navigation
- Temporary dashboard layout
- Dependency smoke tests
- Git initialization

The displayed portfolio data is currently illustrative. Live market data and
financial calculations will be added in later phases.

## Problem being solved

Historical market data is often difficult for nontechnical users to interpret.
MarketLens will organize raw adjusted prices into portfolio returns, benchmark
comparisons, risk metrics, interactive charts, stress scenarios, and
downloadable reports.

## Target users

- Finance and investment students
- Junior risk and portfolio analysts
- Investment-operations teams
- Trade-support analysts
- Users learning portfolio-risk concepts

## Planned features

- One-to-ten asset portfolios
- Custom portfolio weights
- Historical adjusted prices
- Portfolio and benchmark returns
- Volatility and drawdown analysis
- Sharpe and Sortino ratios
- Historical Value at Risk
- Historical Conditional Value at Risk
- Beta and asset correlations
- Contribution to portfolio volatility
- Static stress scenarios
- SQLite saved analyses
- CSV and HTML reports

## Technology stack

- Python
- Streamlit
- pandas
- NumPy
- Plotly
- yfinance
- SQLite
- pytest
- Git and GitHub

## Local installation

From PowerShell:

```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt