# Planned trades — structure-v2.2

Implemented in the shared Strategy engine, MARKET card/chart, SETTINGS, and chronological backtester. No external execution or account connection was added.

## What the user sees

- **ACTIVE LONG / SHORT**: a historical-level interaction has passed the existing confirmation engine. Confirmation Entry uses next open with geometry revalidation.
- **PLANNED LONG / SHORT**: an unconfirmed hypothetical plan with entry zone, deterministic midpoint, structural stop, opposing historical target, gross R:R, distance %, distance ATR, zone quality, confirmation status and invalidation conditions. Existing chart draws entry band and entry/stop/target lines.
- **NO VALID SETUP**: neither a confirmed setup nor a nearby valid plan. If proposed geometry fails, show its actual rejection and values, rather than an incomplete “nearest area” hint.

Default entry mode remains **Confirmation Entry**. **Planned Limit Entry** explicitly permits unconfirmed resting-limit execution in backtesting. MARKET first shows a confirmed active setup if one exists, otherwise the nearest valid hypothetical plan. The market card explains the selected mode; it is not tracking an externally placed order.

## Deterministic planning rules

Evaluate all available historical zones before choosing the nearest surviving plan (then strength and R:R tie-breakers). Buy support below current close / sell resistance above current close. Fixed zone midpoint is the preferred entry; no fitted offset or optimally selected reaction price. Maximum current-price-to-midpoint distance defaults to **3 ATR**, configurable.

Keep existing creation displacement >=1.5 ATR, efficiency >=0.6, width/freshness/previous-test/role-flip filters. Countertrend retains stronger >=3 ATR, >=0.8 efficiency creation; RANGE permits both directions. A numerical strength is displayed and used for ranking, while these explicit quality criteria determine eligibility. Creation reaction is labeled as one formation observation, not a fabricated median across repeated profitable trades.

The stop is beyond the zone boundary and relevant confirmed same-role swings within one current ATR of the zone, plus the configured **0.25 ATR** buffer. This may be wider than a boundary-only stop; the actual confirmed swing is respected. Retain minimum structural risk **0.75 ATR**. Target is the nearest meaningful opposing historical zone; do not skip an intermediate blocker to obtain a better ratio. Both gross and estimated cost-adjusted R:R must meet **1.8** by default. Current price must not already have passed the target. Confirmation is not required to generate this geometry.

## Frozen limit lifecycle and ordering

A plan is created only from a closed historical prefix and a previously available historical zone. The pending order is first executable at the following bar's open. Entry, stop, target, source zones, creation timestamp, expiry and context are frozen in the saved order. Default expiry is **6 executable candles**, configurable 1–100. One pending order and one position maximum; later candidate calculations do not reprice a pending order.

At each subsequent bar:

1. Cancel if its opening timestamp has reached the fixed expiry.
2. Cancel an opening gap through stop, or an opening price already beyond the target.
3. A marketable opening fills at the improved open, otherwise a subsequent limit touch fills at the frozen preferred entry.
4. If target is reached without an opening fill and the ordering relative to an intrabar entry is unknowable, cancel rather than invent a profitable round trip. **If entry and stop are also touched, retain the conservative filled stop loss**, including when target was touched too.
5. No touch and no cancellation means the same order remains pending. Pending orders are canceled at test end.

Cancellation events, submissions and fills are stored in `pipeline.order_events` with original geometry. After termination, a new close may produce a new separately timestamped order; this is explicit replacement, not a historical modification. A stop crossed after a limit fill exits the position, rather than erasing the trade as “invalidated before entry.” Existing stop-first exits, fees, holding limits and marked-equity accounting remain. Target/entry limits receive no market slippage; stop/time exits do. No queue priority, liquidity, partial-fill, intrabar drawdown, borrow or funding simulation is claimed.

## Exact current example verified

The cached **2026-09-23 04:00 UTC** ONDO 4h candle closes at **0.43500**. The identified resistance is exactly **0.439726–0.447074**.

| Candidate | Value |
|---|---:|
| Preferred midpoint entry | 0.443400 |
| Structural stop | 0.468225 |
| Nearest meaningful historical support target | 0.4208825 |
| Gross R:R | **0.9070** |
| Required R:R | **1.8** |

This specific short is **not structurally valid at the configured minimum**, so it correctly remains NO VALID SETUP with these numbers and the R:R rejection visible. It is not being rejected for absent confirmation. The illustrative 0.4548 stop / 0.4120 target supplied in the request are not substituted for the actual historical swing and nearer support. Even reducing the stop to the unchanged 0.75 ATR minimum does not make this nearest-target geometry meet 1.8. No false planned short was forced onto the screen.

A genuinely valid real historical **PLANNED SHORT** is also rendered and verified: entry zone **0.284139–0.287061**, preferred **0.285600**, stop **0.293880**, target **0.249643**, gross R:R **4.3425**. It exists before entry without confirmation. A real planned LONG is covered by a stored regression fixture. Screenshots: `ui/historical-short.png`, `ui/historical-plan.png`, `ui/current-example.png`.

## Independent real backtests

Same Binance ONDO/USDT 4h cached series, **2026-03-22 to 2026-09-22 exclusive UTC**, 500 warmup + 1,104 evaluated bars, no data gaps. Modes have separate pending orders, portfolios, metrics and saved runs; no pooled results. Each mode also runs independent flat-start chronological 70/30 segments of this six-month window. No settings were tuned by evaluation profitability.

| Mode / segment | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---:|---:|---:|---:|---:|---:|
| confirmation / Full | 3 | 66.67 | +1.0350 | +3.1051 | 3.898 | 1.072 |
| confirmation / Development 70% | 1 | 0.00 | -1.0716 | -1.0716 | 0.000 | 1.072 |
| confirmation / Evaluation 30% | 2 | 100.00 | +2.0883 | +4.1767 | ∞ | 0.146 |
| planned_limit / Full | 11 | 27.27 | +0.0112 | +0.1231 | 1.014 | 6.266 |
| planned_limit / Development 70% | 9 | 22.22 | -0.2144 | -1.9297 | 0.740 | 6.181 |
| planned_limit / Evaluation 30% | 2 | 50.00 | +1.0264 | +2.0528 | 2.876 | 1.094 |

Limit lifecycle totals: **60 submitted**, **30 target_before_entry**, **11 filled**, **19 expired**. Planned completed trades: **2 LONG / 9 SHORT**, **3 wins / 8 losses**. Confirmation results exactly preserve the prior three trades. The planned mode has more fills but only **+0.1231 R total**, PF **1.0145**; this is not robust evidence of profitability.

## UI and reproduction

SETTINGS: select Entry mode, maximum distance ATR, expiry candles; Save settings. MARKET refresh recomputes plans using those settings. For confirmation mode, the card says to wait for rejection/reclaim. For limit mode, it states the resting price and expiry. This application does not automatically cancel or update any manual order at an external exchange.

BACKTEST: choose **Both entry modes**, then Run chronological backtest. The comparison rows show both portfolios; the selected saved run supplies the displayed trade list and equity curve. Open the other mode's saved run for its detailed trades. The saved-run label and metrics identify the mode.

From `/Users/sassu/Documents/tradeo/rahamasin`:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m rahamasin.research.planned_run
.venv/bin/python -m tests.render_planned
./run.command --db reports/research.sqlite3
```

- Saved **confirmation** result: **#17**.
- Saved **planned_limit** result: **#18**.

**71 tests pass**, including planned LONG/SHORT geometry, minimum R:R and distance rejection, future-zone rejection, no-target and overtested rejection, expiry, multi-bar pending persistence, fill/no-fill, invalidating opening gap, target-before-entry cancellation, conservative ambiguous stop loss, independent mode persistence, market-card contents and settings, and a non-vacuous real historical plan unchanged by future data. Existing confirmation regressions remain passing. Actual populated card and mode-comparison screenshots were rendered and reviewed. Compile check passes.

`manifest.json` freezes the final evaluated code/config. `results.json` contains separate metrics, split results, diagnostic traces and frozen order events; per-mode CSV files contain actual completed trades. `current-example.json` stores the precise current rejection. Only the research database was written by verification; the normal user database is unchanged. Restart an already running app to load v2.2.
