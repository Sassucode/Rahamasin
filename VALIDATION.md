# Validation record — fresh market price, 2026-09-28

- Main displayed price now comes from a separate asynchronous exchange ticker polled every 5 seconds; the last closed-candle price is explicitly separate.
- Automatic startup history load and one-minute checks for newly closed candles on MARKET. Strategy/backtest inputs remain closed OHLCV; no numerical strategy changes.
- Source matching, 20-second freshness limit, request-error/offline labels, request cancellation on source change and nonoverlapping requests verified. Live price never rewrites candles.
- 75 offline tests pass. Real production Binance Qt polling returned two successive valid fresh quotes (0.5213, 0.5212 in the first integration run). Timestamped final verification is in `reports/live/network-check.json`.
- Normal startup enables polling; smoke/test windows stay network-free unless explicitly started. User's normal database was not used by verification.

---

# Validation record — planned trades, 2026-09-23

- Live version `structure-v2.2`: shared deterministic planned geometry, separate confirmation/limit entry modes, frozen pending-order lifecycle and existing-chart overlays.
- 71 tests pass, including real planned-prefix future independence, both directions, geometry/filtering, expiry, fill/no-fill/invalidation, conservative ambiguous-bar stop handling, mode separation and UI/storage.
- Real 4h six-month confirmation mode preserves 3 trades / +3.105079 R. Planned limit mode produces 11 trades / +0.123116 R / PF 1.014478 / max marked DD 6.266395%. Independent 70/30 results retained for each.
- 60 submitted limit orders: 11 filled, 19 expired, 30 canceled for target-before-entry. Original snapshots retained for every event.
- Exact user example (0.435 close, 0.43973–0.44707 resistance) correctly fails actual R:R 0.907 against default 1.8; card explains the geometry. Valid real historical planned LONG and SHORT were displayed and verified.
- Compile passes; real MARKET and separate-mode BACKTEST screens rendered and visually inspected. Research-only database writes; restart app for new version.

Primary report: [PLANNED_TRADES.md](reports/planned/PLANNED_TRADES.md).

---

# Validation record — pipeline correction, 2026-09-22

- Exact reported 1,604-bar dataset traced: 500 warmup + 1,104 evaluated candles. Archived v2.0: seven confirmations; five rejected by episode timing, two by distance; zero reached stop/target/R:R.
- Live `structure-v2.1` uses independent rejection/reclaim/breakout-retest paths, corrected prior-test and timing semantics, and next-open execution with frozen-geometry revalidation. Default R:R remains 1.8.
- Real 4h six-month outcome: 3 trades, 2 wins / 1 loss, +3.105079 R, PF 3.897575, max marked drawdown 1.071613%. Full available 4h: 10 trades, −0.043595 R, PF 0.992737. No profitability claim.
- Full, independent 70/30 and current six-month periods run for both 4h and 1h. Diagnostic R:R 1.2 / 1.5 / 1.8 / 2.0 gives 6 / 3 / 3 / 1 completed 4h six-month trades. No profit-based threshold selection.
- 60 tests pass: prior regressions, all new confirmation paths, causal pivot/ATR timing, corrected touches, stop/target geometry, next-open execution, persisted funnel, a real active signal tested with altered future data, exact trade replay and rejection UI cutoff protection.
- Actual populated diagnostic and inspector screens rendered. Reviewed all three current 4h trades and actual old/new rejected examples. Last 50 rejected candidates are inspectable without future chart candles.
- Strategy/levels hashes match the manifest frozen before evaluation. Final hashes also record later compatibility-only backtester getters, UI and export metadata changes; metrics were not changed.
- Research uses `reports/research.sqlite3`; the user's normal database is unchanged. Restart the app to load v2.1.

Primary deliverable: [ZERO_TRADE_REPORT.md](reports/pipeline/ZERO_TRADE_REPORT.md). Machine-readable metrics, funnel data, CSVs and UI images are in `reports/pipeline/`.

---

# Validation record — strategy audit, 2026-09-21

- Exact reproduction of the user's 4h 2026-03-21–2026-09-21 v1 result: 37 trades, 11 wins, 26 losses, −3.902978 R, PF 0.878965, max marked drawdown 15.9574%.
- Frozen original strategy and execution retained under `research/v1/` for audit only. Live and current backtest decisions share `strategy/engine.py`.
- Real public Binance data downloaded across 1h, 4h and 1d (12,658 / 3,165 / 528 closed candles before omission of the first possibly partial listing candle). No internal gaps. Separate Coinbase daily data: 973 candles, no gaps, extending to January 2024.
- Before, execution-only correction, and v2 each tested over full, first/middle/latest thirds, independent 70/30 segments, and the user's six months. All outcomes retained. No parameter search.
- V2 produced one 1h winner (+2.426075 R) and no 4h/daily trades. All evaluation segments empty. This does NOT establish profitable or stable behavior; the filters are too restrictive to assess an edge.
- All strategy/execution SHA-256 hashes verified unchanged against the manifest written before v2 evaluation.
- 44 tests pass, covering archived v1, major v2 rules, causal/event-ledger behavior, both-side execution, R decomposition, independent splits, persistence, legacy migration, UI diagnostics and an actual active v2 signal with altered future candles.
- Compilation, offscreen application launch and dependency consistency check pass.
- Updated desktop backtest, market, levels, settings and inspector tabs rendered against real cached research data. Backtest and inspector images visually reviewed. Evaluation rows and zero-sample warnings are visible.
- Seeded random sample of five original winners and five losers visually reviewed at signal time and with outcome candles. The only v2 trade reviewed in both modes. There are not five new winners/losers to inspect, and none were fabricated.
- Current UI results were tested offscreen, including saved-run restoration; an already-running desktop process must be restarted to load changed Python modules.
- User's normal database was read only; research data/results are isolated in `reports/research.sqlite3`.

Primary deliverable: [STRATEGY AUDIT](reports/STRATEGY_AUDIT.md). Full result tables: [Binance](reports/COMPARISON.md), [Coinbase daily](reports/coinbase/COMPARISON.md). Visual audit: [inspection notes](reports/INSPECTION.md).

Reproduce tests with `python -m pytest -q` from the project root. Reproduction commands and execution assumptions are documented in README.md. Open the completed research runs with `python -m rahamasin --db reports/research.sqlite3`.
