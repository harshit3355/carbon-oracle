# Threat model

CARBON ORACLE v0.1 is an offline simulator. It proposes placements; it never submits a job, calls a cloud
API or holds a credential. The only network access is the separate data refresh
(`python -m carbon_oracle.fetch`), which reads a public, keyless API.

## Assets

- **Residency guarantees**: a job placed outside its allowed zone is a compliance incident, not a
  performance bug.
- **Deadline (SLO) guarantees**: the chance constraint's `eps` is only as good as the history it is
  calibrated on.
- **Integrity of the evidence**: `reports/benchmark.*` and the cached trace in `data/`.

## Trust boundaries

| Input | Trust | Why |
|---|---|---|
| `REGIONS` mapping and residency zones (`carbon_oracle/data.py`) | trusted, code-reviewed | a wrong zone silently allows placements that violate residency for every policy |
| Cached carbon trace (`data/gb_carbon_intensity.csv`) | trusted after review | its SHA-256 is recorded in the metadata file and in every report |
| Carbon Intensity API responses (fetch only) | untrusted | third-party data; could be wrong, incomplete or changed |
| Carbon forecasts at decision time | untrusted signal | they steer where and when work runs |
| Queue-wait and runtime history | untrusted signal | it sets how much slack the chance constraint reserves |

## Threats and controls

| Threat | Control |
|---|---|
| A job is placed outside its residency zone | residency is a hard filter applied before optimisation, never a weighted cost; every policy is checked by `tests/test_core.py`, and a violation costs a fixed Green Regret penalty in the report |
| A wrong or tampered forecast steers jobs into a dirty window or region | not controlled for carbon: RGW optimises the forecast it is given. It does bound the deadline risk, which a forecast cannot move because feasibility depends only on queue and runtime estimates |
| Queue history under-reports waits (bad logging or poisoning), so the bound is too tight | not controlled: this is the measured `tail_shift` failure (miss rate above `eps`). Mitigation for a real deployment: recalibrate on recent data and alert when observed misses exceed `eps` |
| The data refresh writes an incomplete or malformed trace | `fetch` refuses to write if any half-hour or region is missing; values are parsed as numbers only; the new SHA-256 shows up in the diff and in report provenance |
| The fetch is redirected to another host | the host is a constant in `fetch.py`, HTTPS only, no user-supplied URL |
| A report is presented as evidence for code that did not produce it | reports record commit SHA (with `-dirty` if the code or data were modified), command, seed, Python version, data hash, data window and fetch date; regenerate from the commit to verify |
| Supply-chain compromise of CI | all actions pinned by commit SHA; workflow token is `contents: read`; no dependencies beyond pytest |

## Out of scope for v0.1

Live schedulers, cloud credentials, Kubernetes admission, multi-tenant fairness, and signing of reports.
If this is wired to a real queue (v0.2), placements should be proposals behind the platform's existing
authorisation, and residency must be enforced again at the execution point, not only in the planner.
