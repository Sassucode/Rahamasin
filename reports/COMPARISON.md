# Fixed-rule multi-period comparison

No periods or losing trades were discarded. Each segment starts flat, is independently risk-sized, and force-closes at its end; segment totals need not sum to full-run totals. Forty initial bars warm up each timeframe; subsequent prefixes expand to 500. First listing candle omitted as potentially partial.

## 4h · 3164 candles · 2025-04-11T16:00:00+00:00 to 2026-09-20T20:00:00+00:00

| Model | Period | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|
| original | Full | 87 | 25.3 | -0.195 | -16.99 | 0.78 | 20.04 |
| original | Development 70% | 55 | 21.8 | -0.292 | -16.07 | 0.69 | 16.39 |
| original | Evaluation 30% | 32 | 31.2 | -0.029 | -0.92 | 0.97 | 15.96 |
| original | First third | 31 | 22.6 | -0.205 | -6.35 | 0.78 | 12.90 |
| original | Middle third | 20 | 20.0 | -0.394 | -7.88 | 0.58 | 11.02 |
| original | Latest third | 36 | 30.6 | -0.077 | -2.76 | 0.91 | 15.96 |
| original | User six months | 37 | 29.7 | -0.105 | -3.90 | 0.88 | 15.96 |
| execution_fixed | Full | 87 | 25.3 | -0.195 | -16.99 | 0.78 | 20.04 |
| execution_fixed | Development 70% | 55 | 21.8 | -0.292 | -16.07 | 0.69 | 16.39 |
| execution_fixed | Evaluation 30% | 32 | 31.2 | -0.029 | -0.92 | 0.97 | 15.96 |
| execution_fixed | First third | 31 | 22.6 | -0.205 | -6.35 | 0.78 | 12.90 |
| execution_fixed | Middle third | 20 | 20.0 | -0.394 | -7.88 | 0.58 | 11.02 |
| execution_fixed | Latest third | 36 | 30.6 | -0.077 | -2.76 | 0.91 | 15.96 |
| execution_fixed | User six months | 37 | 29.7 | -0.105 | -3.90 | 0.88 | 15.96 |
| v2 | Full | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Development 70% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Evaluation 30% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | First third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Middle third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Latest third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | User six months | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |

## 1h · 12657 candles · 2025-04-11T15:00:00+00:00 to 2026-09-20T23:00:00+00:00

| Model | Period | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|
| original | Full | 394 | 25.1 | -0.405 | -159.52 | 0.62 | 82.15 |
| original | Development 70% | 281 | 24.9 | -0.391 | -109.81 | 0.63 | 70.16 |
| original | Evaluation 30% | 113 | 25.7 | -0.440 | -49.71 | 0.57 | 41.42 |
| original | First third | 137 | 27.7 | -0.310 | -42.43 | 0.70 | 43.98 |
| original | Middle third | 126 | 22.2 | -0.422 | -53.15 | 0.61 | 54.03 |
| original | Latest third | 130 | 25.4 | -0.481 | -62.49 | 0.54 | 48.94 |
| original | User six months | 134 | 26.1 | -0.455 | -60.91 | 0.56 | 48.94 |
| execution_fixed | Full | 394 | 25.1 | -0.405 | -159.52 | 0.62 | 82.15 |
| execution_fixed | Development 70% | 281 | 24.9 | -0.391 | -109.81 | 0.63 | 70.16 |
| execution_fixed | Evaluation 30% | 113 | 25.7 | -0.440 | -49.71 | 0.57 | 41.42 |
| execution_fixed | First third | 137 | 27.7 | -0.310 | -42.43 | 0.70 | 43.98 |
| execution_fixed | Middle third | 126 | 22.2 | -0.422 | -53.15 | 0.61 | 54.03 |
| execution_fixed | Latest third | 130 | 25.4 | -0.481 | -62.49 | 0.54 | 48.94 |
| execution_fixed | User six months | 134 | 26.1 | -0.455 | -60.91 | 0.56 | 48.94 |
| v2 | Full | 1 | 100.0 | 2.426 | 2.43 | ∞ | 0.71 |
| v2 | Development 70% | 1 | 100.0 | 2.426 | 2.43 | ∞ | 0.71 |
| v2 | Evaluation 30% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | First third | 1 | 100.0 | 2.426 | 2.43 | ∞ | 0.71 |
| v2 | Middle third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Latest third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | User six months | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |

## 1d · 527 candles · 2025-04-12T00:00:00+00:00 to 2026-09-20T00:00:00+00:00

| Model | Period | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|
| original | Full | 16 | 25.0 | -0.168 | -2.68 | 0.77 | 5.91 |
| original | Development 70% | 11 | 36.4 | 0.204 | 2.25 | 1.33 | 5.91 |
| original | Evaluation 30% | 5 | 0.0 | -0.986 | -4.93 | 0.00 | 4.84 |
| original | First third | 6 | 33.3 | -0.138 | -0.83 | 0.81 | 5.26 |
| original | Middle third | 4 | 25.0 | 0.252 | 1.01 | 1.41 | 2.92 |
| original | Latest third | 6 | 16.7 | -0.478 | -2.87 | 0.42 | 4.84 |
| original | User six months | 7 | 28.6 | 0.090 | 0.63 | 1.13 | 4.84 |
| execution_fixed | Full | 16 | 25.0 | -0.168 | -2.68 | 0.77 | 5.91 |
| execution_fixed | Development 70% | 11 | 36.4 | 0.204 | 2.25 | 1.33 | 5.91 |
| execution_fixed | Evaluation 30% | 5 | 0.0 | -0.986 | -4.93 | 0.00 | 4.84 |
| execution_fixed | First third | 6 | 33.3 | -0.138 | -0.83 | 0.81 | 5.26 |
| execution_fixed | Middle third | 4 | 25.0 | 0.252 | 1.01 | 1.41 | 2.92 |
| execution_fixed | Latest third | 6 | 16.7 | -0.478 | -2.87 | 0.42 | 4.84 |
| execution_fixed | User six months | 7 | 28.6 | 0.090 | 0.63 | 1.13 | 4.84 |
| v2 | Full | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Development 70% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Evaluation 30% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | First third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Middle third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Latest third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | User six months | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |

