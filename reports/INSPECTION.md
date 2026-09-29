# Individual trade inspection

Random seed: `20260921`. Five winners and five losers were sampled independently from the original 37-trade, 4h, 2026-03-21–2026-09-21 run. Selection was made before visual review. All ten were rendered and visually reviewed in the existing desktop inspector, both at the signal and with subsequent outcome candles. The PNGs and sample metadata are in `inspection/`.

Signal-only charts end at the confirmation candle. They use the zone snapshot saved by that signal and never recompute a zone using later candles. The outcome view adds subsequent candles and entry/exit markers. Results remain visible in the trade table, so this is an information-cutoff audit, **not a blinded human forecasting experiment**. A zone overlay can extend across the display horizontally; its stored bounds do not incorporate those later bars.

| Original trade | Direction | Net R | Visual observation |
|---|---|---:|---|
| 3 | SHORT | +1.982 | A break back below the repeatedly crossed 0.255 area; continuation reaches the nearby prior low. Little upper-wick rejection on the signal. A profitable v1 example that stronger wick criteria would exclude. |
| 6 | LONG | +1.594 | Bounce from the old 0.255 area after a pullback; zone has been traded through repeatedly. The target is nearby and costs reduce a roughly minimum-R:R winner. Tightness/old age alone do not distinguish this winner from losses. |
| 12 | SHORT | +6.460 | Continuation after a large downside displacement, followed by consolidation beneath the zone. Large R comes partly from a very small 0.33 ATR stop. A favorable outlier, not evidence that all similarly tight shorts are good. |
| 16 | LONG | +1.726 | Sharp recovery into/through an old band, followed by a small continuation candle. The target is reached before the subsequent decline. Signal is momentum-like rather than a clean fresh support rejection. |
| 37 | LONG | +2.212 | Strong recent upward sequence with an upward reclaim of the area. Confirmed broad swings still classify this as countertrend. Clear illustration of pivot-context lag, despite the winning outcome. |
| 2 | SHORT | −1.335 | Small candle after an extended fall, with a nearby prior low target. Reversal stops it. Zone is old and repeatedly visited; stop is only 0.57 ATR. |
| 8 | SHORT | −1.337 | Choppy range and repeated crossing of the 0.268 band; the signal is followed by a stop sweep. Price later moves toward the target, which must not erase the stopped result. |
| 20 | SHORT | −1.316 | Attempts to fade a rebound into a prior area with a stop close to the entry band. The rebound accelerates sharply. Confirmed swing context still says aligned: another lag limitation. |
| 21 | SHORT | −1.137 | Signal follows a large upward repricing and short consolidation. A local retest hits the stop before a later decline. The earlier confirmed bearish regime does not describe the immediate impulse well. |
| 32 | LONG | −1.140 | Repeated overlap of the 0.382 region after a volatile decline; a bounce signal fails on the next downswing. No clean fresh departure/retest sequence is visible. |

Systematic findings: current-bar wick quality is weak in several **winners as well as losers**; old levels are heavily crossed; stops often lie inside normal candle ranges; broad confirmed pivots lag sudden regime changes. These observations support explainable restrictions, but do not prove those restrictions improve expectancy. The frozen v2 sample is too sparse to validate that hypothesis.

No favorable hindsight exits were substituted. Stop-first ambiguity and the recorded entry/exit candle timing were preserved. Five new winners and five new losers do not exist: v2 generated only one trade across the tested datasets. That limitation is explicitly reported rather than fabricating a new-strategy sample.
