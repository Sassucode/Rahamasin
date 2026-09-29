# STRATEGY AUDIT — RAHAMASIN structure-v2.0

**Outcome: implementation and audit completed, but a profitable, sufficiently active strategy has NOT been established.** The frozen revised rules produced one 1-hour winner and no 4-hour/daily trades. All chronological evaluation segments had zero trades. It would be misleading to claim the flat equity curves or the one-trade infinite profit factor as success. No performance-driven parameter sweep or post-evaluation loosening was performed.

## 1. Original strategy: exact audit and what was wrong

- **Swings:** strict extrema with three candles on each side. Equal extrema omitted. A pivot was visible only after the right-hand three candles closed.
- **Zones/clustering:** last 500 bars; sort confirmed pivot prices and group within a bounded diameter of 0.45 *current* ATR. Add 15% of that diameter beyond the extreme prices. Pivot events separated by at most three bars count as one touch. Overlapping zones retain the higher score; display at most 24. Bounds and memberships could change with available volatility/history, though saved historical setups were not retroactively rewritten. Total width could reach 0.585 current ATR.
- **Reaction stats:** maximum favorable high/low move during the three right-hand confirmation bars; normalize by ATR available at the pivot. A success was >=1 ATR. These already-observed reactions were not future leakage.
- **Strength:** `5×min(touches,8) + 20×success_fraction + 10×min(median_reaction_ATR,3) + 10/(1+recency_bars/50)`. Repeated tests were rewarded. Failed holds, penetrations and departure cleanliness were absent. Switching pivot side labels was only a flip proxy, not a confirmed breakout/retest.
- **Direction/entry:** nearest >=2-touch zone below close for LONG, above for SHORT. Signal candle overlaps the zone, closes beyond its far edge, has the corresponding bullish/bearish body, and closes in the outer 40% of its range. Within 1.5 ATR of midpoint. This did **not** require a significant rejection wick. Preferred entry was the zone midpoint, a next-bar-only limit.
- **Stop:** outside zone and previous/current candle extreme, plus 0.2 ATR. No confirmed local swing requirement or minimum volatility-sized risk. Many stops were far below one ATR.
- **Target/R:R:** nearest >=2-touch opposing price zone wholly beyond the close. No explicit role/impulse quality requirement. Gross R:R >=1.8; costs could materially reduce that ratio. No farther target was deliberately substituted to pass.
- **Exposure:** backtester passed only each closed prefix, truncated to 500. Levels were computed from the prefix excluding the signal candle. No full-series centered pivots, duplicated live/backtest decision code, obvious lookahead, future leakage or short-sign error was found. The archived v1 implementation remains audit-only; live and current backtests share one v2 engine.

The exact user sample was reproduced: 37 trades, 11 wins, 26 losses, −3.902978 net R, 0.878965 PF, 15.9574% marked-equity drawdown. That agreement establishes the baseline before changing decisions.

### Execution correctness and the −1.24 R losses

Two fill issues were corrected: a limit executable at the opening price could be missed if the candle never traded back to the limit; and v1 discarded *all* entry-bar targets even when entry at the open or a closing price beyond target establishes ordering. V2 fills marketable limits at the open, handles known ordering, and remains stop-first when ambiguous. Invalidating opening gaps cancel pending setups; existing positions gap through their stops at the worse open. No optimistic arbitrary ordering is introduced.

R sign and denominator were correct. Every one of the sample's 26 losers was a normal nongapping stop. Average decomposition is **−1.000000 gross R −0.192101 fee R −0.048152 slippage R = −1.240253 net R**. Average stop size was only **0.518 ATR**. Raw stop-fill discrepancy after reversing modeled slippage was exactly zero. The new Trade record stores gross R, fee R and slippage R separately. Corrected execution alone left the measured metrics unchanged on all tested samples; those defects do not explain away the negative performance.

Sizing is still risk-normalized research, not an exchange margin simulator. Fees are on both entry and exit notionals. Targets are limits; stop/time exits receive adverse slippage. Equity is marked at candle close. Partial fills, market impact, borrow/funding, and intrabar drawdown remain unmodeled.

## 2. What changed and which setups are restricted

Zones now require a clean, meaningful creation departure and keep fixed creation-time bounds. A chronological ledger tracks actual test episodes (not just pivots), penetrations, failed holds, age and explicit polarity flips. Touch accumulation lowers quality. Wider current-volatility zones, old zones, repeatedly failed/overused levels, late confirmations, prolonged chop, insignificant wicks, too-tight structural stops, blocked targets and insufficient net R:R are rejected.

A confirmed HH/HL or LH/LL regime is a filter. Countertrend trades require exceptional fresh departure quality and a strong failed-break rejection; direction is not disabled based on the known six-month result. Breakout-retest requires a two-close break and the first held retest. Rejection and breakout-retest are separate diagnostic labels.

The BACKTEST tab adds full/70% development/30% evaluation tables and group diagnostics without redesigning the application. Each saved run retains its configuration, strategy version and split results. The inspector can hide all post-signal candles and retains entry/target zone snapshots. Legacy runs remain readable.

## 3. Full-period results before vs after

All periods use 10bps/side fees, 5bps market-exit slippage, 1% risk and seven-day maximum hold. Before = frozen v1; the corrected-execution-only comparator is also retained in the linked full tables. Each provider is independent; USD and USDT candles are never spliced. Start-up bars are warmup, not silently dropped losing trades. The first potentially partial listing candle is excluded, followed by 40 warmup candles; information windows then expand to 500.

| Dataset | Model | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|
| Binance 1h | original | 394 | 25.127 | -0.405 | -159.518 | 0.617 | 82.15 |
| Binance 1h | v2 | 1 | 100.000 | 2.426 | 2.426 | ∞ | 0.71 |
| Binance 4h | original | 87 | 25.287 | -0.195 | -16.988 | 0.784 | 20.04 |
| Binance 4h | v2 | 0 | — | unestimable | 0.000 | — | 0.00 |
| Binance 1d | original | 16 | 25.000 | -0.168 | -2.683 | 0.772 | 5.91 |
| Binance 1d | v2 | 0 | — | unestimable | 0.000 | — | 0.00 |
| Coinbase 1d | original | 26 | 26.923 | -0.210 | -5.459 | 0.721 | 11.31 |
| Coinbase 1d | v2 | 0 | — | unestimable | 0.000 | — | 0.00 |

Binance coverage begins 2025-04-11; complete audited 4h trading evaluation begins 2025-04-18 08:00 UTC. Coinbase daily data extends coverage to 2024-01-22; its audited trading interval begins 2024-03-03 after warmup. All end at 2026-09-21 00:00 UTC (exclusive). Every first/middle/latest third and the user's exact six-month period is retained in [COMPARISON.md](COMPARISON.md) and [Coinbase comparison](coinbase/COMPARISON.md), with precise dates and metrics in the corresponding JSON.

For the user's exact six months: v1 remains 37 trades, −3.90 R, PF 0.88; v2 has zero trades. This is abstention, not a demonstrated profitable replacement.

## 4. Development and chronological out-of-sample evaluation

Rules/configuration were frozen before running v2 on market data; see [RULES_FROZEN.md](RULES_FROZEN.md) and the SHA-256 manifests. The latest 30% was not used to revise parameters. However, it overlaps the user's already-seen v1 six-month sample, so it is a **retrospective chronological holdout, not pristine unseen or forward evidence**. The UI says evaluation and warns about this distinction.

Each split is an independent flat-start simulation. Earlier closed bars may warm up levels; no position or pending order crosses the boundary. Trades are forced closed at each segment's end. Thus independent segment totals need not sum to the uninterrupted full run.

| Dataset | Model | Development trades | Development R | Development PF | Evaluation trades | Evaluation R | Evaluation PF |
|---|---|---:|---:|---:|---:|---:|---:|
| Binance 1h | original | 281 | -109.811 | 0.634 | 113 | -49.707 | 0.572 |
| Binance 1h | v2 | 1 | 2.426 | ∞ | 0 | 0.000 | — |
| Binance 4h | original | 55 | -16.068 | 0.688 | 32 | -0.919 | 0.966 |
| Binance 4h | v2 | 0 | 0.000 | — | 0 | 0.000 | — |
| Binance 1d | original | 11 | 2.248 | 1.329 | 5 | -4.931 | 0.000 |
| Binance 1d | v2 | 0 | 0.000 | — | 0 | 0.000 | — |
| Coinbase 1d | original | 20 | -2.879 | 0.804 | 6 | -2.581 | 0.471 |
| Coinbase 1d | v2 | 0 | 0.000 | — | 0 | 0.000 | — |

4h split boundary is **2026-04-17 16:00 UTC**. Every v2 evaluation sample is empty. No stability, positive expectancy, or PF>1 claim is warranted. The one v2 1h trade occurred in development: a fresh countertrend LONG rejection with a 5.98 ATR creation impulse, +2.426 net R. It is also used as a non-vacuous causal regression fixture; changing later candles must not alter its signal.

## 5. LONG vs SHORT statistics

| Period/model | Direction | Trades | Win % | Expectancy R | PF |
|---|---|---:|---:|---:|---:|
| 4h original full | LONG | 41 | 34.1 | 0.163 | 1.209 |
| 4h original full | SHORT | 46 | 17.4 | -0.515 | 0.493 |
| 4h original user six months | LONG | 13 | 53.8 | 0.589 | 2.079 |
| 4h original user six months | SHORT | 24 | 16.7 | -0.482 | 0.540 |
| 4h v2 full | LONG | 0 | 0.0 | 0.000 | — |
| 4h v2 full | SHORT | 0 | 0.0 | 0.000 | — |
| 1h v2 full | LONG | 1 | 100.0 | 2.426 | ∞ |
| 1h v2 full | SHORT | 0 | 0.0 | 0.000 | — |

Zero-count expectancy cells above are implementation placeholders, not statistical estimates. The one-trade 1h figure and infinite PF are likewise not persuasive evidence. Full diagnostics for every timeframe, variant and split remain in JSON; no losses or adverse periods are hidden.

## 6. Which level characteristics correlate with results?

On the **full original 4h** sample:

- LONG: 41 trades, +0.163 R expectancy, PF 1.21; SHORT: 46 trades, −0.515 R, PF 0.49. This is descriptive, not proof that long-only will generalize.
- Old strength >=65: 33 trades, −0.458 R; below 65: 54 trades, −0.034 R. Rewarding accumulated touches produced a poor quality ranking.
- No reconstructed failed holds: only 4 trades, +0.624 R, PF 2.06; previously failed: 83 trades, −0.235 R, PF 0.75. Small clean-level sample limits confidence.
- Wider-than-0.5-ATR zones: 28 trades, +0.110 R; narrower: 59 trades, −0.340 R. This does **not** justify a claim that narrow zones are inherently superior.
- The freshness/recency hypothesis is **not consistently supported**: recent zones did better in the known six-month sample, but <=100-bar zones lost −0.378 R/trade over the full sample versus −0.141 R for older zones. No fresh first-retest v1 trades existed under the reconstructed definition.
- Trend-aligned original setups lost −0.382 R/trade; countertrend ones averaged +0.075 R. A broad context filter is structurally explainable, but these results do **not** validate it as an edge. Confirmed context lag is visible in individual examples.
- Stops under 0.75 ATR averaged −0.175 R; the 12 trades with 0.75–1.5 ATR stops averaged −0.247 R. The new floor is a volatility/cost control, not a data-proven profit improvement.

These are overlapping observational groups, with no causality claim, significance test or independence assumption. V1 did not store an event ledger: its retests/penetrations/failed holds were reconstructed against the **signal-time zone bounds** from pre-signal candles. They are explicitly marked as retrospective diagnostic features, not perfectly stable historical zone identities. V2 stores its causal ledger at the signal.

Every trade has direction, strength, age, touches, retest ordinal, entry-center distance, entry-available ATR, stop/target/width in ATR, R:R, confirmation, context/alignment, weakening flags, outcome, gross R, fees and slippage. CSV files include every trade and separate every losing trade. [Original six-month diagnostics](ORIGINAL_DIAGNOSTICS.md), [full 4h diagnostics](4h-original-diagnostics.md), and [inspection report](INSPECTION.md) explain the principal evidence.

## 7. Exact deterministic rules now used

1. Take at most the last 500 **closed** candles; require 40 and consistent spacing. Filter `as_of` before all analysis. Compute zones and context from candles strictly **before** the confirmation candle.
2. Strict pivots have three neighbors per side. At pivot confirmation, require maximum directional closing departure >=1.5 pivot ATR, and positive net directional close movement / sum of absolute close changes >=0.6 over those three right bars. ATR is mean true range over up to 14 preceding bars.
3. Freeze zone bounds at pivot price ±0.225 pivot ATR. Process seeds chronologically; a later overlapping seed cannot widen/reset an existing zone. The rolling information horizon can eventually expire an old seed; freshness is therefore bounded-history freshness, not all-time identity.
4. An overlap after two fully outside candles starts a new test episode. Track penetration once per episode and failed close >0.25 creation ATR beyond invalidation. Two consecutive such closes flip support/resistance, reset current-role retest/failure counters and timestamp the break; the breakout itself is not a retest. Historical failure/penetration counters remain.
5. Quality score: `(45×min(impulse/6,1)+25×efficiency+20+10 if exactly one flip)` multiplied by `1/(1+0.45×tests+0.25×penetrations+0.8×failed_holds)` and `max(0.25,1−age/(1.25×lookback))`, bounded 0–100. Parenthesization: the optional +10 is added to the whole quality sum. Creation reaction statistics are distinct from the test ledger.
6. Eligible entry zones have <=2 current-role tests, <=3 lifetime-within-window tests, no current-role failed holds, <=1 flip, age <=250 bars, and width <=0.675 current ATR. Choose nearest support below close for LONG or resistance above close for SHORT; do not search farther to manufacture a setup.
7. Context uses span-six confirmed swings: last two highs and lows both rising by >0.1 ATR = BULLISH; both falling = BEARISH; otherwise RANGE. No EMA/RSI/MACD rule exists.
8. Confirmation must overlap the zone, have a directional body, reclaim the far edge, close in the outer 35% of the candle range, and have a relevant wick >=35% of range and >=0.25 pre-signal ATR. Close must be within 1 ATR of zone center. Reject if an already-active overlap episode began more than one earlier candle ago.
9. Countertrend requires >=3 ATR impulse, >=0.8 departure efficiency, no prior role test (excluding the current episode), a sweep beyond the zone's far edge, and >=0.5 ATR wick. Range uses ordinary clean boundary rejection. A flipped zone is labeled Breakout-retest, and only its first held role retest is allowed.
10. Preferred entry is zone midpoint; limit lasts one subsequent candle. Stop goes beyond the zone, signal/previous candle extreme and latest confirmed same-side local swing in the most recent 13-bar window, plus 0.25 pre-signal ATR. Reject a planned structural stop <0.75 ATR or nonpositive stop; do not widen just to pass.
11. Target is the nearest unbroken meaningful opposing-role impulse zone's near edge, **including aged/retested intermediate blockers**. Reject if no target, reward <1 ATR, target already crossed by the confirmation close, gross R:R <1.8, or `(reward−entry/target fees)/(risk+estimated entry/stop fees+stop slippage)` <1.8. No target stretching.
12. At most one position. Entry, conservative stop-first execution, seven-day timeout, end-of-period exit and modeled costs follow the execution section. Signal time is the confirmation candle's opening timestamp; it is only actionable after that candle closes. Intrabar exits are timestamped at candle close because tick ordering is unavailable.

## 8. Remaining weaknesses and verification

**Over-filtering is the main new weakness.** In a full 4h signal scan, 4,131 directional candidates failed the wick/reclaim test; among those passing it, 13 failed prolonged-overlap, 7 failed the structural-stop floor, 5 failed proximity and 2 failed the countertrend exception. No 4h setup survived. These counts are per evaluated direction, not independent trades, and are not a profitability attribution. The joint criteria remove too many opportunities to assess quality.

Only the creation confirmation window measures impulse/cleanliness; longer later reactions do not improve the seed quality. Zone memory expires with the rolling lookback. Broader confirmed pivots lag fast reversals. Volatility and history horizons differ in elapsed time across 1h/4h/1d. Holding one week on daily bars offers coarse execution. Historical liquidity/fees are simplified, and short availability is not modeled. Coinbase's longer sample was evaluated at daily resolution; Binance supplied the primary hourly/four-hour samples. V2 has no losing sample from which to infer tail risk.

No rule was adjusted to recover the inspected winners or to obtain a requested profit figure. Any future redesign should predeclare a new development protocol and use genuinely new forward data for evaluation; the periods studied here are now researched data. This implementation should be treated as a conservative research candidate, **not a validated trading edge**.

Tests cover both archived v1 and every major v2 rule, causal level confirmation, level weakening, explicit flips, context, strong/countertrend rejection, no-chase/chop, stop/target/net-R:R rejection, both-side fills and R decomposition, independent split boundaries, immutable-history caching, legacy storage, UI population, and a real active v2 signal with altered future candles. See [VALIDATION.md](../VALIDATION.md) for the final verification record.
