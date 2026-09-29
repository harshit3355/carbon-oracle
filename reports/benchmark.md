# CARBON ORACLE benchmark: Green Regret under forecast error

_Real GB regional carbon intensity; **synthetic** jobs, prices, queue waits and runtime errors. Every number below was produced by the command in the provenance section._

- 24 scenarios x 50 jobs (batch inference, embedding backfill, eval suites, fine-tuning), 7 illustrative regions mapped to GB grid regions, residency zones england / wales / gb / pinned-to-home.
- Realised carbon intensity differs from the forecast every policy sees by a factor of 0.792 (p5) / 1.034 (p50) / 1.649 (p95).
- Green Regret per job = normalised carbon+cost objective minus the hindsight oracle's, plus 10 per deadline miss or residency violation. The oracle knows realised carbon, queue waits and runtimes.
- Jobs no placement could finish on time in hindsight are excluded: 0.

## Nominal (queues and runtimes drawn from the schedulers' history) (16 scenarios)

| Policy | Green Regret / job | Objective gap / job | Deadline misses | Residency violations | Carbon kg | vs run-now | vs oracle | Cost $ |
|---|---|---|---|---|---|---|---|---|
| Run immediately, home region | 1.233 | 1.233 | 0/800 (0.0%) | 0 | 4561.0 | +0.0% | +433.5% | 102554 |
| Carbon-agnostic cheapest | 1.232 | 1.232 | 0/800 (0.0%) | 0 | 4713.9 | +3.4% | +451.4% | 97862 |
| Lowest-carbon-now | 0.442 | 0.392 | 4/800 (0.5%) | 0 | 2118.4 | -53.5% | +147.8% | 107156 |
| Deadline-first (shortest forecast queue) | 1.232 | 1.232 | 0/800 (0.0%) | 0 | 4713.9 | +3.4% | +451.4% | 97862 |
| Best window, home region (carbon-aware-sdk style) | 2.637 | 0.649 | 159/800 (19.9%) | 0 | 2820.7 | -38.2% | +230.0% | 102554 |
| Deterministic forecast optimizer = RGW without chance constraint (ablation) | 1.300 | 0.038 | 101/800 (12.6%) | 0 | 970.2 | -78.7% | +13.5% | 107409 |
| Deterministic + hand-tuned padding (2x queue, +25% runtime) | 0.451 | 0.064 | 31/800 (3.9%) | 0 | 1025.0 | -77.5% | +19.9% | 107401 |
| RGW, eps = 0.01 | 0.243 | 0.181 | 5/800 (0.6%) | 0 | 1316.1 | -71.1% | +53.9% | 106863 |
| **RGW, eps = 0.05 (mechanism)** | 0.189 | 0.089 | 8/800 (1.0%) | 0 | 1114.6 | -75.6% | +30.4% | 107344 |
| RGW, eps = 0.20 | 0.501 | 0.051 | 36/800 (4.5%) | 0 | 1014.4 | -77.8% | +18.7% | 107400 |

## Calm (queues and runtimes better than history): where the risk bound buys nothing (4 scenarios)

| Policy | Green Regret / job | Objective gap / job | Deadline misses | Residency violations | Carbon kg | vs run-now | vs oracle | Cost $ |
|---|---|---|---|---|---|---|---|---|
| Run immediately, home region | 1.131 | 1.131 | 0/200 (0.0%) | 0 | 906.8 | +0.0% | +806.3% | 20027 |
| Carbon-agnostic cheapest | 1.100 | 1.100 | 0/200 (0.0%) | 0 | 938.5 | +3.5% | +838.0% | 18942 |
| Lowest-carbon-now | 0.390 | 0.390 | 0/200 (0.0%) | 0 | 430.6 | -52.5% | +330.4% | 20860 |
| Deadline-first (shortest forecast queue) | 1.100 | 1.100 | 0/200 (0.0%) | 0 | 938.5 | +3.5% | +838.0% | 18942 |
| Best window, home region (carbon-aware-sdk style) | 1.318 | 0.418 | 18/200 (9.0%) | 0 | 387.3 | -57.3% | +287.1% | 20027 |
| Deterministic forecast optimizer = RGW without chance constraint (ablation) | 0.071 | 0.021 | 1/200 (0.5%) | 0 | 117.8 | -87.0% | +17.8% | 20929 |
| Deterministic + hand-tuned padding (2x queue, +25% runtime) | 0.042 | 0.042 | 0/200 (0.0%) | 0 | 131.3 | -85.5% | +31.3% | 20933 |
| RGW, eps = 0.01 | 0.157 | 0.157 | 0/200 (0.0%) | 0 | 186.3 | -79.5% | +86.2% | 20821 |
| **RGW, eps = 0.05 (mechanism)** | 0.064 | 0.064 | 0/200 (0.0%) | 0 | 143.2 | -84.2% | +43.1% | 20893 |
| RGW, eps = 0.20 | 0.035 | 0.035 | 0/200 (0.0%) | 0 | 129.4 | -85.7% | +29.3% | 20930 |

## Tail shift (wider errors, 10% congestion events): the risk bound is miscalibrated (4 scenarios)

| Policy | Green Regret / job | Objective gap / job | Deadline misses | Residency violations | Carbon kg | vs run-now | vs oracle | Cost $ |
|---|---|---|---|---|---|---|---|---|
| Run immediately, home region | 1.344 | 1.144 | 4/200 (2.0%) | 0 | 836.2 | +0.0% | +615.3% | 24308 |
| Carbon-agnostic cheapest | 1.109 | 1.109 | 0/200 (0.0%) | 0 | 886.5 | +6.0% | +658.3% | 23180 |
| Lowest-carbon-now | 0.834 | 0.284 | 11/200 (5.5%) | 0 | 294.6 | -64.8% | +152.0% | 25434 |
| Deadline-first (shortest forecast queue) | 1.109 | 1.109 | 0/200 (0.0%) | 0 | 886.5 | +6.0% | +658.3% | 23180 |
| Best window, home region (carbon-aware-sdk style) | 2.925 | 0.625 | 46/200 (23.0%) | 0 | 570.3 | -31.8% | +387.9% | 24308 |
| Deterministic forecast optimizer = RGW without chance constraint (ablation) | 1.774 | 0.074 | 34/200 (17.0%) | 0 | 173.1 | -79.3% | +48.0% | 25474 |
| Deterministic + hand-tuned padding (2x queue, +25% runtime) | 1.186 | 0.086 | 22/200 (11.0%) | 0 | 177.3 | -78.8% | +51.7% | 25466 |
| RGW, eps = 0.01 | 0.761 | 0.211 | 11/200 (5.5%) | 0 | 209.7 | -74.9% | +79.4% | 25289 |
| **RGW, eps = 0.05 (mechanism)** | 1.182 | 0.132 | 21/200 (10.5%) | 0 | 194.5 | -76.7% | +66.4% | 25439 |
| RGW, eps = 0.20 | 1.383 | 0.083 | 26/200 (13.0%) | 0 | 176.8 | -78.8% | +51.3% | 25466 |

## Mechanism vs its ablation (same objective, chance constraint removed)

| Regime | RGW Green Regret | Ablation Green Regret | RGW miss rate | Ablation miss rate | RGW carbon vs ablation |
|---|---|---|---|---|---|
| nominal | 0.189 | 1.300 | 1.0% | 12.6% | +14.9% |
| calm | 0.064 | 0.071 | 0.0% | 0.5% | +21.6% |
| tail_shift | 1.182 | 1.774 | 10.5% | 17.0% | +12.4% |

## Scenarios where RGW did worse than its ablation

| Scenario | RGW regret | Deterministic regret | RGW carbon kg | Deterministic carbon kg | RGW carbon vs deterministic | RGW misses | Deterministic misses |
|---|---|---|---|---|---|---|---|
| calm-d01 | 0.094 | 0.031 | 69.2 | 53.3 | +29.7% | 0 | 0 |
| calm-d05 | 0.037 | 0.026 | 25.8 | 25.8 | +0.1% | 0 | 0 |
| calm-d09 | 0.035 | 0.006 | 23.4 | 21.1 | +11.1% | 0 | 0 |
| tail-d11 | 1.244 | 1.000 | 67.9 | 65.2 | +4.1% | 5 | 4 |

## Per scenario (Green Regret / job; deadline misses in brackets)

| Scenario | run_now_home | cheapest | lowest_carbon_now | deadline_first | best_window_home | deterministic | padded | rgw_eps0.01 | rgw | rgw_eps0.20 |
|---|---|---|---|---|---|---|---|---|---|---|
| nominal-d00 | 1.23 (0) | 1.18 (0) | 0.22 (0) | 1.18 (0) | 2.12 (7) | 0.83 (4) | 0.26 (1) | 0.12 (0) | 0.06 (0) | 0.45 (2) |
| nominal-d01 | 1.39 (0) | 1.39 (0) | 0.90 (0) | 1.39 (0) | 2.63 (11) | 2.21 (11) | 0.45 (2) | 0.40 (0) | 0.10 (0) | 0.26 (1) |
| nominal-d02 | 0.91 (0) | 1.00 (0) | 0.63 (2) | 1.00 (0) | 2.00 (8) | 1.06 (5) | 0.68 (3) | 0.56 (2) | 0.49 (2) | 0.66 (3) |
| nominal-d03 | 1.05 (0) | 1.04 (0) | 0.27 (0) | 1.04 (0) | 2.08 (8) | 0.82 (4) | 0.22 (1) | 0.15 (0) | 0.07 (0) | 0.42 (2) |
| nominal-d04 | 0.90 (0) | 1.08 (0) | 0.37 (0) | 1.08 (0) | 2.19 (9) | 1.08 (5) | 0.09 (0) | 0.12 (0) | 0.10 (0) | 0.09 (0) |
| nominal-d05 | 1.34 (0) | 1.37 (0) | 0.35 (0) | 1.37 (0) | 3.15 (12) | 1.11 (5) | 0.12 (0) | 0.20 (0) | 0.13 (0) | 0.12 (0) |
| nominal-d06 | 0.97 (0) | 1.02 (0) | 0.18 (0) | 1.02 (0) | 1.89 (6) | 1.07 (5) | 0.27 (1) | 0.32 (1) | 0.28 (1) | 0.27 (1) |
| nominal-d07 | 0.88 (0) | 1.00 (0) | 0.15 (0) | 1.00 (0) | 1.38 (4) | 0.23 (1) | 0.04 (0) | 0.10 (0) | 0.04 (0) | 0.03 (0) |
| nominal-d08 | 1.19 (0) | 1.05 (0) | 0.48 (0) | 1.05 (0) | 2.24 (8) | 1.03 (5) | 0.64 (3) | 0.20 (0) | 0.29 (1) | 0.63 (3) |
| nominal-d09 | 1.23 (0) | 1.35 (0) | 0.23 (0) | 1.35 (0) | 1.98 (6) | 0.22 (1) | 0.24 (1) | 0.11 (0) | 0.04 (0) | 0.03 (0) |
| nominal-d10 | 1.89 (0) | 2.07 (0) | 0.83 (1) | 2.07 (0) | 4.87 (21) | 2.61 (13) | 1.48 (7) | 0.44 (1) | 0.33 (1) | 1.82 (9) |
| nominal-d11 | 0.94 (0) | 0.79 (0) | 0.16 (0) | 0.79 (0) | 1.44 (4) | 0.44 (2) | 0.05 (0) | 0.13 (0) | 0.07 (0) | 0.25 (1) |
| nominal-d12 | 1.47 (0) | 1.42 (0) | 1.12 (1) | 1.42 (0) | 4.30 (18) | 2.61 (13) | 0.63 (3) | 0.47 (1) | 0.54 (2) | 0.63 (3) |
| nominal-d13 | 1.78 (0) | 1.58 (0) | 0.47 (0) | 1.58 (0) | 4.76 (19) | 3.81 (19) | 0.87 (4) | 0.29 (0) | 0.12 (0) | 1.06 (5) |
| nominal-d14 | 1.20 (0) | 1.15 (0) | 0.23 (0) | 1.15 (0) | 2.19 (6) | 0.44 (2) | 0.52 (2) | 0.08 (0) | 0.26 (1) | 0.25 (1) |
| nominal-d15 | 1.35 (0) | 1.22 (0) | 0.48 (0) | 1.22 (0) | 2.96 (12) | 1.24 (6) | 0.66 (3) | 0.20 (0) | 0.09 (0) | 1.05 (5) |
| calm-d01 | 1.34 (0) | 1.08 (0) | 0.64 (0) | 1.08 (0) | 1.01 (3) | 0.03 (0) | 0.08 (0) | 0.18 (0) | 0.09 (0) | 0.07 (0) |
| calm-d05 | 1.06 (0) | 1.03 (0) | 0.36 (0) | 1.03 (0) | 0.90 (3) | 0.03 (0) | 0.03 (0) | 0.07 (0) | 0.04 (0) | 0.03 (0) |
| calm-d09 | 1.02 (0) | 1.13 (0) | 0.18 (0) | 1.13 (0) | 1.31 (4) | 0.01 (0) | 0.02 (0) | 0.15 (0) | 0.04 (0) | 0.02 (0) |
| calm-d13 | 1.09 (0) | 1.16 (0) | 0.38 (0) | 1.16 (0) | 2.05 (8) | 0.22 (1) | 0.05 (0) | 0.22 (0) | 0.09 (0) | 0.03 (0) |
| tail-d03 | 1.02 (1) | 0.97 (0) | 0.86 (3) | 0.97 (0) | 2.16 (9) | 1.45 (7) | 1.05 (5) | 0.54 (2) | 1.10 (5) | 1.25 (6) |
| tail-d07 | 1.45 (1) | 1.13 (0) | 0.97 (4) | 1.13 (0) | 3.78 (15) | 1.62 (8) | 0.63 (3) | 0.55 (2) | 0.87 (4) | 0.83 (4) |
| tail-d11 | 1.42 (2) | 0.83 (0) | 0.86 (3) | 0.83 (0) | 1.33 (4) | 1.00 (4) | 1.00 (4) | 1.53 (6) | 1.24 (5) | 1.00 (4) |
| tail-d15 | 1.48 (0) | 1.51 (0) | 0.65 (1) | 1.51 (0) | 4.43 (18) | 3.03 (15) | 2.06 (10) | 0.43 (1) | 1.52 (7) | 2.45 (12) |

## Provenance

- commit: `05c296bdda6ebce91f397add682e6ac56bcb2238`
- command: `python -m carbon_oracle bench --out reports`
- python: `3.10.6`
- platform: `Windows-10-10.0.26200-SP0`
- data_sha256: `f985a61551f70caa`
- data_source: `https://api.carbonintensity.org.uk`
- data_license: `CC BY 4.0`
- data_window: `2026-09-01T00:00Z .. 2026-09-21T23:30Z`
- data_fetched_at: `2026-09-29T09:05:37+00:00`
- generated_at: `2026-09-29T09:14:46+00:00`
- seed: `7`
