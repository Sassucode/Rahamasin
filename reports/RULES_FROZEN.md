# Structure v2 rules frozen before evaluation

This specification was written after reproducing the user-reported six-month v1 result, but before running v2 on any market history. No grid search or performance-driven parameter sweep will be used. The last 30% is a chronological evaluation holdout from this implementation exercise; it is **not pristine unseen data**, because the user's six-month report and v1 diagnostics overlap it. A forward test is still needed.

Symmetric LONG/SHORT logic; neither direction is removed based on the known sample.

- Confirm pivots with 3 neighbors on each side. Keep a 500-bar information horizon.
- A new zone must depart >=1.5 ATR in closed prices within its 3-bar confirmation window and have >=0.6 net/path departure efficiency. Freeze width at 0.45 creation ATR. Overlapping seeds never expand or rejuvenate the zone.
- Track actual overlap episodes separated by 2 outside candles, penetrations, failed closes, and 2 consecutive closes beyond the zone by 0.25 creation ATR for polarity reversal. Require at most one reversal; break itself is not a retest.
- Decay score with every retest, penetration, failed hold and age; do not reward touch accumulation. Score impulse through 6 ATR.
- Entry zones: <=2 role retests and <=3 total retests, no failed holds of current role, age <=250 bars, width <=0.675 current ATR, clean departure.
- Broader context uses the last 2 confirmed highs and lows with span 6; HH/HL = bullish, LH/LL = bearish, else range, with 0.1 ATR structural tolerance.
- Directional rejection must overlap the zone, close beyond it in the correct candle direction, have a wick >=35% of its range and >=0.25 ATR, and close in outer 35%. Confirmation more than 1 ATR from midpoint or more than one earlier bar into a touch episode is rejected.
- Countertrend: only a first retest of a >=3 ATR, >=0.8-efficiency departure, a sweep of the zone's far edge, and >=0.5 ATR wick. Range setups use the same clean rejection rules at opposing historical boundaries.
- Explicit breakout-retest: only first held retest following the two-close role reversal. Repeated flipped retests rejected.
- Next-bar midpoint limit, then expiry. Structural stop beyond zone, rejection, previous candle, and most recent confirmed same-side local swing in 13 bars, plus 0.25 ATR. Reject a structural stop <0.75 ATR, never widen merely to pass.
- Target nearest meaningful unbroken opposing impulse zone, including intermediate aged/retested blockers. Require >=1 ATR reward and gross AND estimated net R:R >=1.8. Never skip a nearer target to pass R:R.
- 1% risk, 7-day maximum hold, 10bps fee per side, 5bps market exit slippage. R denominator remains actual entry-to-structural-stop distance; fees/slippage are separately recorded.

Corrected execution is compared separately against frozen original execution. Full, thirds and 70/30 segments restart positions independently and force-close at their boundary. Earlier prices may warm up each segment; no earlier open trade is carried across the split. No performance-based changes after evaluation are permitted in this run. Correctness fixes must be documented and all affected results recomputed.
