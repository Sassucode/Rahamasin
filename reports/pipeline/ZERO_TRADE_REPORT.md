# Zero-trade diagnosis and correction — structure-v2.1

The exact reported Binance ONDO/USDT 4h window, **2026-03-22 through 2026-09-22 exclusive (UTC)**, now has **3 completed trades: 1 LONG and 2 SHORT**, versus zero in structure-v2.0. Default minimum gross and estimated net R:R remains **1.8**. The three-trade sample is below the aspirational 5–30 range; no threshold was reduced to meet a quota. Full available 4h history has 10 trades and PF 0.993, so profitability is **not established**.

## Exact zero-trade root cause

The loaded 1,604 bars contain **500 warmup bars and 1,104 evaluated bars**. The old implementation selected the nearest eligible zone per direction, even when it was not interacting with price: 1,444 selected candidates, 1,437 confirmation failures, only **7 confirmation passes**. This 99.5% rejection rate includes distant candidates, not just genuine interactions.

All seven remaining candidates then failed timing: **5 `rejected_prolonged_overlap` and 2 `rejected_entry_too_late`**. The old episode-age test rejected a confirmation more than one bar after the touch episode started, even when there was no sustained current overlap. **Zero candidates reached stop, target or R:R evaluation.** R:R 1.8 and order fills therefore did not cause this particular zero result.

Additional restrictive combinations: rejection required a wick plus a far-edge reclaim; breakout-retests also inherited wick requirements; current tests were counted against freshness before being subtracted; historical failed closes permanently excluded recoverable zones; countertrend combined strong creation with first-touch, sweep and extra wick requirements. All changes were written down before outcome evaluation in [DECISIONS.md](DECISIONS.md).

## Before/after stage counts

Counts describe zone-candle observations, except final signals/orders/trades. A zone can occur on many bars; counts are not unique zones or independent opportunities. Before uses current-bar overlaps; after uses current or preceding three-bar interactions to support causal reclaim sequences. The old nearest-selection branch is a different cohort from its overlap inventory and must not be read as a single monotonic funnel.

| Stage | v2.0 before | v2.1 after |
|---|---:|---:|
| Evaluated candles | 1104 | 1104 |
| Rolling swing observations | 100784 | 100784 |
| Rolling zone observations | 16329 | 16068 |
| Raw interactions (definitions above) | 1334 | 2163 |
| Fresh enough | 168 | 375 |
| Zone quality | 102 | 250 |
| Confirmation | 7 | 32 |
| Context | 0 | 29 |
| Timing | 0 | 22 |
| Valid stop | 0 | 22 |
| Valid target | 0 | 16 |
| Minimum gross/net R:R | 0 | 4 |
| Selected LONG | 0 | 1 |
| Selected SHORT | 0 | 2 |
| Submitted orders | 0 | 3 |
| Actual fills | 0 | 3 |
| Completed trades | 0 | 3 |

Four zone candidates pass R:R on three selected signal bars. One best setup is selected per bar. Signals while occupied are still counted but cannot submit another order. The final test bar is traced even though no following open is available. Every evaluated bar has a saved record.

## Primary rejection counts, descending

### Before

| Reason | Count |
|---|---:|
| rejected_confirmation | 1437 |
| rejected_zone_too_old | 768 |
| rejected_too_many_touches | 369 |
| rejected_zone_width | 66 |
| rejected_previous_failed_hold | 15 |
| rejected_repeated_flips | 14 |
| rejected_prolonged_overlap | 5 |
| rejected_entry_too_late | 2 |
### After

| Reason | Count |
|---|---:|
| rejected_repeated_flips | 1289 |
| rejected_too_many_touches | 379 |
| rejected_confirmation | 218 |
| rejected_zone_width | 125 |
| rejected_zone_too_old | 120 |
| rejected_rr | 12 |
| rejected_target_geometry | 6 |
| rejected_entry_too_late | 6 |
| rejected_market_structure | 3 |
| rejected_prolonged_overlap | 1 |

Absent rejection codes have count zero. In particular, weak displacement, no opposing target and invalid stop are zero in this window; six after candidates instead fail target distance/geometry. Counts use the **first failing condition**, not every possible failure.

## Swing/zone availability and contradiction audit

The exact 1,604-bar source has **144 confirmed swing highs and 150 confirmed swing lows**. Across evaluated rolling snapshots there are **93 distinct (seed time, original role) identities**: first-observed roles are **51 support / 42 resistance**, including **57 already flipped**. Identity counts are not the sum of rolling observations. Median creation width is **0.45 seed ATR**. At the last pre-confirmation snapshot: **14 support / 1 resistance / 12 flipped**, median age **335 bars**, median width **0.2044 current ATR**; current-role test distribution is **0:12, 1:2, 2:1**. Roles and touch counts evolve causally; the first-observed and latest-snapshot statistics deliberately use different clearly labeled cohorts. Zones are plentiful; failure to detect structure was not the cause.

| Check | Finding / correction |
|---|---|
| Pivot delay | A pivot is confirmed after exactly N right bars (default 3), with no second N-bar delay. A historical setup requires creation before its confirmation candle. |
| ATR | Finite after warmup. Creation now requires the full 14-bar left-side ATR history to prevent seed width drift near a truncated window edge. This adds no right-side pivot delay. |
| Freshness vs retest | Creation is not a retest. Current touch is subtracted before the maximum **2 previous tests** check. Current-role age starts at an explicit breakout. |
| Polarity | Two qualifying closes assign a causal role flip; the observed flipped zones prove it is reachable. More than one flip remains rejected. |
| Failed hold | A single historical close through an edge does not permanently invalidate a recovered role. Failure statistics still reduce quality; confirmed role changes are retained. |
| Confirmation threshold | Wick rejection can close beyond the midpoint rather than requiring an additional far-edge reclaim. SHORT is mirrored. |
| OR vs AND | Rejection, reclaim and first breakout-retest are independent alternatives; the latter two need directional close displacement, not an extra rejection wick. |
| RANGE / countertrend | RANGE permits both sides. Alignment ranks candidates. Countertrend still requires creation >=3 ATR and efficiency >=0.8; the additional simultaneous sweep/first-touch/double-wick checklist is removed. |
| Timing | Recent interaction window is four bars; prolonged chop measures actual consecutive overlaps, not elapsed touch-episode age. Proximity stays <=1 ATR. |
| Width / strength | Width 0.45 seed ATR, displacement >=1.5 ATR and efficiency >=0.6 unchanged. |
| Stops | Structural zone/rejection/local-swing invalidation plus 0.25 ATR buffer; minimum risk 0.75 ATR unchanged. Stop geometry was never reached in the baseline. |
| Targets | Nearest meaningful opposing historical role above/below entry. Creation displacement/efficiency qualify meaningful structure; old age or recovered historical breach alone does not discard a target. Never skip a nearer blocker to manufacture R:R. |
| Entry | Old code used a historical-zone midpoint limit, **not the future candle midpoint**. No order was proposed in the zero run. New execution is next open with adverse slippage and frozen-geometry revalidation. |

## Entry and costs

Confirmation close is the projected entry reference. Entry occurs at the **next candle open plus 5 bps adverse slippage**. Only the opening price is consulted for entry; that candle's later high/low/close cannot decide whether an opening entry exists. Proximity, stop validity, target geometry, and gross/net R:R are rechecked at the actual slipped opening price. A bad gap cancels the order; stops and targets are never moved to rescue it. Historical inspection retains the reference line; trade tables show actual entry.

Default fees are 10 bps each side. Stops/time exits have adverse 5 bps slippage; target limits do not. Ambiguous stop/target candles are stop-first. R uses actual filled entry-to-stop distance. Entry slippage is already embedded in that fill and is not subtracted twice; the separate slippage-R component describes the exit. No liquidity, partial fills, funding or borrow model is claimed. There is one position at a time and a seven-day maximum hold.

## Fixed-rule real backtests

Binance series through 2026-09-22, starting in April 2025. First potentially partial listing bar is excluded; full runs use 40 initial warmup bars and expand causal history to 500. The selected six-month run uses its preceding history. Downloaded coverage: 3,171 4h and 12,682 1h bars before first-bar exclusion, with no internal gaps. Full means **all locally available downloaded Binance history**, not a claim about every possible external historical source.

Independent 70/30 segments restart flat and use earlier bars only for warmup. Same default configuration for both timeframes and all segments; no evaluation-specific fit. The evaluation interval overlaps the inspected six-month period and is not pristine unseen data.

| Timeframe / period | Trades | Wins / losses | Win % | Average R = expectancy | Total R | PF | Max DD % |
|---|---:|---:|---:|---:|---:|---:|---:|
| 4h Full | 10 | 3 / 7 | 30.00 | -0.0044 | -0.0436 | 0.9927 | 7.0271 |
| 4h Development 70% | 7 | 1 / 6 | 14.29 | -0.4498 | -3.1487 | 0.3614 | 6.0200 |
| 4h Evaluation 30% | 3 | 2 / 1 | 66.67 | +1.0350 | +3.1051 | 3.8976 | 1.0716 |
| 4h Current six months | 3 | 2 / 1 | 66.67 | +1.0350 | +3.1051 | 3.8976 | 1.0716 |
| 1h Full | 17 | 5 / 12 | 29.41 | -0.0748 | -1.2711 | 0.9107 | 9.8124 |
| 1h Development 70% | 11 | 3 / 8 | 27.27 | -0.1142 | -1.2561 | 0.8677 | 9.8124 |
| 1h Evaluation 30% | 6 | 2 / 4 | 33.33 | -0.0025 | -0.0149 | 0.9969 | 2.8943 |
| 1h Current six months | 6 | 2 / 4 | 33.33 | -0.0025 | -0.0149 | 0.9969 | 2.8943 |

Full 4h LONG/SHORT: **3 / 7**; current six months: **1 / 2**. Current average winner **+2.0883 R**, average loser **−1.0716 R**, longest losing streak **1**. Full 4h losing streak **7**. Full and 1h losses are retained and reported. Drawdown is candle-close marked equity at 1% risk, not intrabar drawdown.

## R:R sensitivity — survival only

| Threshold | Candidate passes | LONG / SHORT signals | Submitted | Filled / completed |
|---|---:|---:|---:|---:|
| 1.2 | 10 | 3 / 6 | 7 | 6 / 6 |
| 1.5 | 6 | 1 / 4 | 4 | 3 / 3 |
| 1.8 | 4 | 1 / 2 | 3 | 3 / 3 |
| 2.0 | 2 | 0 / 1 | 1 | 1 / 1 |

Position occupancy and next-open geometry explain signals > submissions > fills. This comparison was not ranked by profit; **1.8 remains the default**. R:R now removes 12 of 16 valid-target candidates, but was not the original zero-trade cause.

## Actual inspected cases

All seven late-stage old rejections are in `before.json` and rendered under `ui/before-rejected-*.png`. At-signal images contain no later candles. Old records legitimately have no stop/target because those stages were not reached.

| Old signal UTC | Direction / zone | Actual final rejection |
|---|---|---|
| 2026-05-24 16:00 | SHORT 0.44357–0.45163 | rejected_prolonged_overlap |
| 2026-05-25 00:00 | SHORT 0.44357–0.45163 | rejected_prolonged_overlap |
| 2026-05-25 20:00 | SHORT 0.44357–0.45163 | rejected_entry_too_late |
| 2026-06-03 00:00 | SHORT 0.38696–0.39304 | rejected_prolonged_overlap |
| 2026-08-05 12:00 | SHORT 0.38164–0.38696 | rejected_prolonged_overlap |
| 2026-08-05 16:00 | SHORT 0.38164–0.38696 | rejected_prolonged_overlap |
| 2026-08-09 20:00 | SHORT 0.35775–0.36085 | rejected_entry_too_late |

Visual review of May 24 and August 5 confirms the price interacts with historical zones; the old episode clock rejects those confirmations. August 5 becomes a valid bearish first breakout-retest in v2.1. This is a rule-based admission, not an admission based on its later win. The latest stored v2.1 rejected SHORT (September 21 20:00) has attractive projected R:R (~4.04) but no valid bearish confirmation and remains rejected.

The three actual 4h trades were reviewed with the signal cutoff and/or outcome chart:

| Signal UTC | Direction / confirmation | Net outcome |
|---|---|---:|
| 2026-05-20 16:00 | SHORT / rejection, range | −1.0716 R |
| 2026-08-05 12:00 | SHORT / first breakout-retest, bearish | +2.0199 R |
| 2026-09-04 20:00 | LONG / rejection, range | +2.1568 R |

The first short fails at its structural stop, the second reaches the historical support target, and the long reaches resistance. Screenshots are in `ui/`; full planned/actual entry, stop, target and executed R:R are in `4h-current-six-months-trades.csv`.

## Delivered diagnostics and verification

Existing BACKTEST diagnostics contain **Signal pipeline** and **Rejected** sub-tabs. Last 50 rejected candidates retain timestamp, direction, frozen zone, midpoint, confirmation close, projected entry/distance ATR, stop/target, R:R, context, confirmation type and primary reason. Double-click a rejection to use the existing TRADES chart; the chart is always cutoff-safe and explicitly labels it **not a trade**. `None` means a field is unavailable/not reached, not zero. Main tabs/layout are retained.

**60 offline tests pass**, including causal pivot availability, ATR seed stability, both directions and all three confirmation paths, touch/freshness semantics, recovered targets, unchanged stop/R:R floors, next-open cancellation, per-candle persistence, legacy strategy regression, real active v2.1 signal with altered future candles, exact real trade replay, UI rejection inspection and cutoff protection. Actual populated UI screenshots were rendered and visually reviewed.

`manifest.json` was written before evaluation. `final-code-hashes.json` records final code after compatibility-only backtester getters and diagnostics/UI/export changes; live strategy and levels decisions were unchanged after evaluation. Non-Full saved runs' diagnostic metadata was corrected to avoid displaying Full-period counters for a six-month run. All trade outcomes and metrics were preserved. The normal user database was not modified.

## Reproduce and open

From `/Users/sassu/Documents/tradeo/rahamasin`:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m rahamasin.research.pipeline_run --download
.venv/bin/python -m rahamasin.research.pipeline_before
.venv/bin/python -m rahamasin.research.pipeline_run
.venv/bin/python -m tests.render_pipeline
./run.command --db reports/research.sqlite3
```

Restart an already running application to load v2.1. Research saved-run IDs:
- 4h Full: **#6**
- 4h Development 70%: **#7**
- 4h Evaluation 30%: **#8**
- 4h Current six months: **#9**
- 1h Full: **#10**
- 1h Development 70%: **#11**
- 1h Evaluation 30%: **#12**
- 1h Current six months: **#13**

Raw outputs: `before.json`, `results.json`, each `*-pipeline.json` (including every evaluated bar), each `*-trades.csv`, and `evaluation.log`. Earlier v1/v2.0 reports remain historical records.
