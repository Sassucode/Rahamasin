# Pipeline correction decisions, before v2.1 evaluation

The user window is 2026-03-22 to 2026-09-22 UTC. 1604 downloaded bars comprise 500 warmup + 1104 evaluated bars. Exact v2.0 instrumentation: 1334 current-candle zone overlaps, 168 freshness survivors, 102 quality survivors; original nearest-zone selection tried 1444 directional candidates (including distant ones), only 7 confirmations passed, 5 then failed the one-bar episode-age timer and 2 exceeded proximity. No stop/target/R:R evaluation was reached. These are two connected inventories, not falsely presented as one monotonic old funnel.

Corrections, not a profit search:
- Current retest subtracted BEFORE freshness tests; creation never counts as retest. Current-role age follows an explicit break, while old quality/history is retained and still decays.
- A single failed close is not a permanently failed role: a one-close breach can reclaim; two consecutive qualifying closes still flip the role causally. Historical failure counts remain in the score.
- Rejection OR reclaim OR explicit first breakout-retest. Wick path reclaims midpoint, not necessarily far edge; reclaim and breakout-retetst use directional closing displacement without simultaneously requiring a long wick.
- Allow a bounded confirmation sequence; measure actual consecutive overlap (max pivot_span+1 bars), not elapsed time since a whole multi-candle touch episode began.
- Examine interacting zones, not just nearest already-filtered zone regardless of interaction.
- Keep zone width 0.45 ATR, displacement 1.5 ATR, efficiency 0.6, max previous role tests 2, proximity 1 ATR, stop floor 0.75 ATR, stop buffer 0.25 ATR, default gross/net R:R 1.8, fees and slippage unchanged.
- Context ranks candidates; countertrend still needs >=3 ATR and >=0.8-efficiency creation, but no contradictory simultaneous first-touch/sweep/double-wick checklist. Ranges allow both directions.
- Execute next OPEN with adverse entry slippage, using confirmation close only as projected entry. At the actual open recheck proximity, invalidation, structural minimum risk and R:R against the original frozen target. Cancel bad gaps; never substitute a farther target or inspect the opening bar's future high/low/close.
- Targets remain the nearest meaningful opposing role; an old, previously recovered zone is not discarded just because of age or a historical failed close.
- Require a full 14-bar ATR history at seed creation. This prevents creation widths drifting as a pivot approaches the truncated left edge of the rolling window. It is availability protection, not extra right-side pivot delay.

Measure R:R values 1.2/1.5/1.8/2.0 for survival counts only. Do not pick a value by P&L. Report all periods, including losses. Freeze the code/config before outcome evaluation. Stored per-candle funnel and last 50 rejected candidates are part of each backtest result. No new UI layout; append diagnostics to the existing backtest tab.
