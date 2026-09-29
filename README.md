# RAHAMASIN

A standalone Python desktop application for ONDO swing-trading research. It identifies historical support/resistance zones, produces one deterministic LONG / SHORT / NO TRADE state, explains structural entry/stop/target levels, and tests the same strategy chronologically. No execution, account connection, wallet, paid API, LLM, or paper trading is included.

## Install and run

Python 3.12+ is required. Tested on macOS with Python 3.14 and PySide6 6.11. Qt needs a graphical desktop for normal use.

```bash
cd rahamasin
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m rahamasin
```

On Windows activate with `.venv\Scripts\activate`. On Linux, install your distribution's Qt/XCB runtime libraries if Qt reports a missing platform plugin. The project is independent of its parent directory's existing applications.

The default database is `~/.rahamasin/rahamasin.sqlite3`. Override it with `python -m rahamasin --db ./local.sqlite3`. The database is created on first launch. The app loads data automatically on normal startup; **Refresh ONDO** also forces a history refresh. There are no invented/demo market prices. A new installation is intentionally empty until public data has been fetched.

## Workflow

- **MARKET**: choose 1h, 4h, or 1d, refresh, inspect the latest closed candle and its setup. Drag/scroll the chart to pan/zoom. Entry, stop, and one target appear for valid setups. NO TRADE shows nearby qualifying areas and confirmation requirements. The large price is the exchange last-trade quote polled every 5 seconds, with source, bid/ask, receipt time and age. Closed-candle prices are labeled separately. At startup analysis loads automatically; while MARKET is visible, closed history is checked every minute and refreshed after a new candle closes.
- **BACKTEST**: select UTC dates (end is exclusive), timeframe, minimum gross R:R, and risk per trade. The app downloads a preceding warmup window and evaluates signals only in the selected period. Downloads/backtests run on a worker thread. Metrics and the equity curve include modeled costs. Saved runs can be reopened, with independent development/evaluation results and diagnostics for newly computed runs.
- **TRADES**: click a row to see candles around the signal, original zone snapshot, entry/stop/target, entry/exit markers, factual reasons and net outcome.
- **LEVELS**: inspect the zone statistics from the last market refresh. In v2, reaction statistics describe the completed creation departure; retests/penetrations/failed holds are separate fields in saved zone snapshots and diagnostic exports. They are not expected returns.
- **SETTINGS**: save strategy parameters, fees, and slippage. Changes apply to subsequent refreshes/runs; existing results keep their own configuration. Defaults aim at swing setups, with a seven-day maximum hold. Stops/targets may exit sooner than two days. Daily candles naturally give less precise execution estimates.

## Data and provenance

The replaceable `Provider` protocol returns immutable OHLCV candles. Binance ONDO/USDT is tried first, then Coinbase ONDO/USD. These are separate datasets and are never mixed. The UI and each run record their source and timeframe. Only completed UTC candles are accepted. Quote units are USDT on Binance and USD on Coinbase; they are not converted.

Binance is paginated at 1,000 bars. Coinbase is paginated below its 300-bar maximum. Coinbase has no native 4h interval, so complete groups of four UTC hourly candles are aggregated; incomplete groups are discarded. HTTP rate limits/transient server errors receive bounded retries. Provider availability and historical coverage can vary by location and listing date.

SQLite caches each source/timeframe/timestamp independently. Downloads fill missing intervals; cached complete ranges need no network request. Offline mode uses existing candles and labels them as cached. A failed refresh can fall back to cached history with a prominent status note. Backtesting refuses internal gaps and incomplete requested endings; missing periods are never silently filled with synthetic candles. Inspect coverage notes, especially for dates preceding the ONDO listing. Do not interpret a historical cached setup as a current signal.

API references: [Binance spot market data](https://developers.binance.com/en/docs/binance-spot-api-docs/rest-api/market-data-endpoints), [Coinbase product candles](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles).

## Planned trades — structure-v2.2

MARKET distinguishes **ACTIVE LONG/SHORT**, **PLANNED LONG/SHORT**, and **NO VALID SETUP**. Active means confirmed interaction. Planned means hypothetical historical-zone geometry without confirmation: fixed midpoint entry, stop beyond a nearby confirmed swing/zone plus ATR buffer, nearest meaningful opposing target, gross/net R:R, distance, quality, confirmation status and invalidation rules. All levels are drawn on the existing chart. A plan is not a confirmed market-entry signal.

SETTINGS adds **Entry mode**, **Maximum plan distance (ATR)** (default 3) and **Limit expiry (candles)** (default 6). Confirmation entry remains the default. Existing zone freshness/quality, stronger countertrend requirements, 0.75 ATR minimum stop risk, and default minimum gross/net R:R 1.8 remain in force. One formation reaction is labeled as such, not presented as a multi-event statistical return estimate.

BACKTEST offers **Confirmation Entry**, **Planned Limit Entry**, or **Both entry modes**. Both computes independent portfolios and independent 70/30 splits, saves separate runs, and shows a comparison above the selected run's results. Open the corresponding saved run for its trades. Never combine the two modes' statistics.

Planned limits become available at the next bar after the plan was computed. One pending order at a time, with frozen entry/stop/target. No silent repricing while pending. Cancel on expiry, opening gap through stop, or target reached before entry. If an intrabar entry/target ordering is unknown, no profitable fill is assumed; if stop is also touched, retain the conservative filled stop loss. An order can be replaced only after the prior order has terminated, using a newly computed and separately recorded snapshot. Unfilled orders at the test end are canceled. A fresh MARKET refresh recomputes a hypothetical plan; it does not manage any manual external order.

See [PLANNED_TRADES.md](reports/planned/PLANNED_TRADES.md) for real separate-mode results, the exact user's current example, expiry events and verification. The original confirmation engine behavior is retained. Earlier reports below describe their archived versions.

## Strategy v2.1 and zero-trade diagnosis

The previous correction was `structure-v2.1`; current live strategy is `structure-v2.2`. Read [ZERO_TRADE_REPORT.md](reports/pipeline/ZERO_TRADE_REPORT.md) for the exact baseline bottleneck, corrected rules, per-filter counts, rejected examples, R:R sensitivity and real backtests. The original [STRATEGY_AUDIT.md](reports/STRATEGY_AUDIT.md) remains a historical v1/v2.0 audit.

On Binance ONDO/USDT 4h, 2026-03-22 through 2026-09-22 exclusive, v2.1 produces **3 trades (1 LONG / 2 SHORT), 66.67% wins, +1.035 R expectancy, PF 3.898, 1.072% maximum marked drawdown**, versus zero before. Full available 4h history has 10 trades, −0.0044 R expectancy and PF 0.993. This does **not** establish a profitable strategy. The default R:R remains 1.8; no trade quota is imposed.

Confirmed pivots seed historical zones after a meaningful departure. A causal ledger tracks tests, breaches and explicit role flips. Rejection, reclaim and first breakout-retest are independent confirmation paths. Current touches are excluded from previous-test counts; one historical breached close does not permanently ban a recovered zone. RANGE allows both directions and countertrend still requires stronger creation. Stops remain structural with an ATR buffer; targets remain the nearest meaningful opposing historical zones. Both gross and estimated net R:R must pass, including at the actual next open.

The current defaults are eight setup parameters (pivot span, lookback, zone width, displacement, maximum tests, wick threshold, stop buffer and minimum R:R) plus risk, holding period and two execution cost assumptions. Existing saved settings are preserved where applicable; the obsolete v1 minimum-touch setting is ignored. Saved legacy runs remain readable and are labeled v1. Audit results use the exact default configuration recorded in the manifest, which may differ from a user's saved overrides.

## Chronological evaluation and diagnostics

The BACKTEST tab retains its layout and adds full/development/evaluation summaries, grouped diagnostics, **Signal pipeline** counters and the last 50 **Rejected** candidates. Double-click a rejected candidate to inspect its frozen zone, projected geometry and primary rejection reason in the existing TRADES chart. Rejected charts always hide future candles. The first 70% and last 30% are independent flat-start runs; their totals need not sum to the full run. Earlier candles can warm up a later period, but no open position carries over the boundary. Hover period labels for exact UTC bounds. A repeatedly viewed evaluation period is not pristine out-of-sample evidence; this audit's original six-month sample already overlapped it.

The TRADES inspector has an **At signal** checkbox (on by default), which hides candles after confirmation. Turn it off to inspect outcomes. Both entry and target zone snapshots are frozen at signal time; no future levels are recalculated. Results remain visible, so this is not a blinded inspection mode.

`Strategy.analyze` is still the only current decision engine, used by both live analysis and backtesting. `research/v1/` and `research/v20/` are frozen audit-only references, never imported by the live strategy. Pivots require closed right-hand bars, levels exclude the confirmation candle, and `as_of` filters before all computation. A real active v2 signal is tested against appended/altered future data, in addition to general prefix tests.

## Confirmation execution and R accounting

V2.1 enters at the next candle open with adverse entry slippage. Confirmation close is only a projected reference; actual opening proximity, stop, target and gross/net R:R are rechecked against frozen levels. Invalid opening geometry cancels the order. Entry never uses that bar's future high/low/close. Ambiguous stop/target bars are stop-first. Existing positions gap through stops at the worse open. Stops/time exits receive adverse slippage; target limits do not. Saved legacy results retain their original execution model.

Structural R is based on actual entry-to-stop risk: `net R = gross price R − fees R − slippage R`. A normal nongapping stop is −1 gross R, not necessarily −1 net R. The original six-month loss average of −1.240 R was exactly −1 gross, −0.192 fees, −0.048 slippage; it was not a sign error. The inspector shows this decomposition. In v2.1, entry slippage is already embedded in the actual entry and is not subtracted twice; the separate slippage-R component is the exit cost.

Starting equity remains $10,000 with 1% risk-normalized sizing, no cash/margin constraints, one position at a time, 7-day maximum hold, 10bps fees per side and 5bps market entry/exit slippage by default. Candle-close marked equity includes modeled exit cost. There is no queue, partial-fill, liquidity, intrabar drawdown, funding or borrow model. Short returns are hypothetical spot-price research. Zero-trade statistics are displayed as lacking evidence.

## Reproduce the current zero-trade correction

```bash
.venv/bin/python -m rahamasin.research.pipeline_run --download
.venv/bin/python -m rahamasin.research.pipeline_before
.venv/bin/python -m rahamasin.research.pipeline_run
./run.command --db reports/research.sqlite3
```

These runs end at **2026-09-22 00:00 UTC**. The normal database is unchanged. Saved research runs and their IDs are listed in [the report](reports/pipeline/ZERO_TRADE_REPORT.md). Restart an already running app to load the new code. For normal use, double-click `run.command` in this project directory.

## Reproduce the earlier v1/v2.0 audit

From this project with the virtual environment active:

```bash
python -m rahamasin.research.download
python -m rahamasin.research.download --coinbase-daily
python -m rahamasin.research.audit
python -m rahamasin.research.audit --coinbase-daily
python -m rahamasin.research.inspect_trades
python -m rahamasin --db reports/research.sqlite3
```

These research scripts fix the ending boundary at **2026-09-21 00:00 UTC**, use a separate local research database, and do not overwrite the user's normal database. Binance's available series begins April 2025; separate Coinbase daily coverage starts January 2024. Each series omits its first possibly partial listing candle and uses 40 initial warmup bars, then expands the causal history up to 500 bars. Full, thirds, 70/30 and the user's six-month window are all retained. There is no parameter search. Multi-timeframe evaluation can take several minutes. CSVs contain every trade and separate losing-trade extracts; JSON retains every period's metrics and group statistics. `research.baseline` optionally reproduces the initial sample from the user's read-only default cache.

## Architecture

```
rahamasin/
  models.py          immutable candles/config; setup, zone, trade, result records
  storage.py         SQLite repository and JSON run/config snapshots
  data/providers.py  public provider protocol, pagination, validation, cache
  strategy/levels.py causal pivots, zones, transparent strength
  strategy/engine.py single deterministic setup engine
  backtest/engine.py chronological execution, equity and statistics
  ui/chart.py        pyqtgraph candlesticks and chart overlays
  ui/window.py       PySide6 tabs and background worker
  main.py            desktop entry point
 tests/              offline tests and optional network integration check
```

## Verification

From the project directory with the environment active:

```bash
python -m pytest -q
python -m rahamasin --smoke-test --db /tmp/rahamasin-smoke.sqlite3
python -m tests.live_check  # optional: downloads real public ONDO data
```

`--smoke-test --screenshot /tmp/rahamasin.png` also saves the desktop UI. Tests cover confirmed pivots, clustering, strength formula, LONG/SHORT rejection, structural stop and target, R:R rejection, prefix/future independence, next-bar execution, gap cancellation, same-bar stop/target ambiguity, missing data, cache fallback, storage round trips, and desktop rendering. Network tests are intentionally separate from the reproducible offline suite.

## Fresh market price

Public quotes are requested asynchronously from the same source/pair as the displayed history: Binance ONDO/USDT or Coinbase ONDO/USD. Quotes never overwrite OHLCV or enter historical strategy/backtest calculations. There is no silent cross-exchange quote fallback. Live distance to entry is displayed separately from the plan's creation distance; crossing a displayed stop/target prompts reassessment.

This is a **5-second HTTP snapshot**, not tick-by-tick streaming. The UI says so explicitly. A quote older than 20 seconds (receipt or provider timestamp), any current request error, or cache-only mode removes the live label and live chart line. The previous value may remain visible as stale, never as current. New requests have an 8-second timeout and cannot overlap. Switching sources aborts the prior request; switching to cache-only disables network polling. Shutdown stops polling safely.

API fields follow [Binance market-data documentation](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/market) and [Coinbase product ticker documentation](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-ticker). Coinbase's timestamp is the last trade timestamp; a quiet market can therefore correctly show an old last trade despite a successful request.

Optional real network check: `.venv/bin/python -m tests.live_quote_check`. It requests two production quotes through the actual Qt poller and saves the results and a populated screenshot to `reports/live/`.
