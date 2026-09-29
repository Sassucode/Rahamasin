# Fixed-rule multi-period comparison

No periods or losing trades were discarded. Each segment starts flat, is independently risk-sized, and force-closes at its end; segment totals need not sum to full-run totals. Forty initial bars warm up each timeframe; subsequent prefixes expand to 500. First listing candle omitted as potentially partial.

## 1d · 972 candles · 2024-01-23T00:00:00+00:00 to 2026-09-20T00:00:00+00:00

| Model | Period | Trades | Win % | Expectancy R | Total R | PF | Max DD % |
|---|---|---:|---:|---:|---:|---:|---:|
| original | Full | 26 | 26.9 | -0.210 | -5.46 | 0.72 | 11.31 |
| original | Development 70% | 20 | 30.0 | -0.144 | -2.88 | 0.80 | 11.31 |
| original | Evaluation 30% | 6 | 16.7 | -0.430 | -2.58 | 0.47 | 4.10 |
| original | First third | 8 | 0.0 | -1.045 | -8.36 | 0.00 | 8.47 |
| original | Middle third | 12 | 50.0 | 0.457 | 5.49 | 1.86 | 4.05 |
| original | Latest third | 6 | 16.7 | -0.430 | -2.58 | 0.47 | 4.10 |
| original | User six months | 4 | 25.0 | -0.111 | -0.44 | 0.84 | 4.10 |
| execution_fixed | Full | 26 | 26.9 | -0.210 | -5.46 | 0.72 | 11.31 |
| execution_fixed | Development 70% | 20 | 30.0 | -0.144 | -2.88 | 0.80 | 11.31 |
| execution_fixed | Evaluation 30% | 6 | 16.7 | -0.430 | -2.58 | 0.47 | 4.10 |
| execution_fixed | First third | 8 | 0.0 | -1.045 | -8.36 | 0.00 | 8.47 |
| execution_fixed | Middle third | 12 | 50.0 | 0.457 | 5.49 | 1.86 | 4.05 |
| execution_fixed | Latest third | 6 | 16.7 | -0.430 | -2.58 | 0.47 | 4.10 |
| execution_fixed | User six months | 4 | 25.0 | -0.111 | -0.44 | 0.84 | 4.10 |
| v2 | Full | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Development 70% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Evaluation 30% | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | First third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Middle third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | Latest third | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |
| v2 | User six months | 0 | 0.0 | 0.000 | 0.00 | — | 0.00 |

