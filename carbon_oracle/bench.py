"""Benchmark: Green Regret of every policy against the hindsight oracle, per scenario and per queue regime."""
from __future__ import annotations

import datetime
import platform
import statistics
import subprocess
import sys

from . import data
from .model import PENALTY, REGIMES, oracle, outcome, scenario
from .policies import POLICIES, view

# 16 nominal days, plus 4 "calm" (queues and runtimes better than history: the negative case) and
# 4 "tail_shift" (worse than history: the failure case)
SCENARIOS = ([(f"nominal-d{d:02d}", d, "nominal") for d in range(16)]
             + [(f"calm-d{d:02d}", d, "calm") for d in (1, 5, 9, 13)]
             + [(f"tail-d{d:02d}", d, "tail_shift") for d in (3, 7, 11, 15)])
MECHANISM, ABLATION = "rgw", "deterministic"  # the ablation is RGW with its chance constraint removed

LABELS = {"run_now_home": "Run immediately, home region", "cheapest": "Carbon-agnostic cheapest",
          "lowest_carbon_now": "Lowest-carbon-now", "deadline_first": "Deadline-first (shortest forecast queue)",
          "best_window_home": "Best window, home region (carbon-aware-sdk style)",
          "deterministic": "Deterministic forecast optimizer = RGW without chance constraint (ablation)",
          "padded": "Deterministic + hand-tuned padding (2x queue, +25% runtime)",
          "rgw_eps0.01": "RGW, eps = 0.01", "rgw": "**RGW, eps = 0.05 (mechanism)**", "rgw_eps0.20": "RGW, eps = 0.20"}


def run_scenario(trace, v, name: str, day: int, regime: str, seed: int) -> dict:
    jobs, world = scenario(trace, day, regime, seed)
    rows, infeasible = {p: [] for p in POLICIES}, 0
    for job in jobs:
        best = oracle(job, world)
        if best is None:
            infeasible += 1
            continue
        for p, f in POLICIES.items():
            o = outcome(job, world, *f(job, v))
            o["gap"] = o["J"] - best["J"]
            o["violation"] = o["missed"] or o["residency_violation"]
            o["regret"] = o["gap"] + PENALTY * o["violation"]
            o["oracle_carbon_kg"] = best["carbon_kg"]
            rows[p].append(o)
    return {"scenario": name, "day": day, "regime": regime, "seed": seed, "jobs": len(jobs),
            "infeasible_in_hindsight": infeasible, "policies": {p: _agg(r) for p, r in rows.items()}}


def _agg(rows: list[dict]) -> dict:
    n = len(rows)
    carbon, oc = sum(r["carbon_kg"] for r in rows), sum(r["oracle_carbon_kg"] for r in rows)
    return {"jobs": n, "green_regret": round(sum(r["regret"] for r in rows) / n, 4),
            "objective_gap": round(sum(r["gap"] for r in rows) / n, 4),
            "deadline_misses": sum(r["missed"] for r in rows),
            "residency_violations": sum(r["residency_violation"] for r in rows),
            "carbon_kg": round(carbon, 2), "oracle_carbon_kg": round(oc, 2), "cost_usd": round(sum(r["cost"] for r in rows), 2)}


def _ratio(a: float, b: float) -> float:
    return round(a / b - 1, 4)


def _summary(scen: list[dict], regime: str) -> dict:
    s = [x for x in scen if x["regime"] == regime]
    out = {}
    for p in POLICIES:
        a = [x["policies"][p] for x in s]
        n = sum(x["jobs"] for x in a)
        base = sum(x["policies"]["run_now_home"]["carbon_kg"] for x in s)
        carbon = sum(x["carbon_kg"] for x in a)
        out[p] = {"scenarios": len(s), "jobs": n,
                  "green_regret": round(sum(x["green_regret"] * x["jobs"] for x in a) / n, 4),
                  "objective_gap": round(sum(x["objective_gap"] * x["jobs"] for x in a) / n, 4),
                  "deadline_misses": sum(x["deadline_misses"] for x in a),
                  "miss_rate": round(sum(x["deadline_misses"] for x in a) / n, 4),
                  "residency_violations": sum(x["residency_violations"] for x in a),
                  "carbon_kg": round(carbon, 1), "carbon_vs_run_now": round(carbon / base - 1, 4),
                  "carbon_vs_oracle": round(carbon / sum(x["oracle_carbon_kg"] for x in a) - 1, 4),
                  "cost_usd": round(sum(x["cost_usd"] for x in a), 0)}
    return out


def bench(seed: int) -> dict:
    trace = data.load()
    v = view(trace, seed=seed * 1000 + 999)
    scen = [run_scenario(trace, v, name, d, reg, seed * 1000 + i) for i, (name, d, reg) in enumerate(SCENARIOS)]
    ratio = sorted(a / f for r in trace.forecast for a, f in zip(trace.actual[r], trace.forecast[r]) if f)
    # negative case: scenarios where the mechanism did worse than its own ablation
    worse = [{"scenario": x["scenario"], "regime": x["regime"],
              **{f"{p}_{k}": x["policies"][p][k] for p in (MECHANISM, ABLATION)
                 for k in ("green_regret", "carbon_kg", "deadline_misses")},
              "extra_carbon": _ratio(x["policies"][MECHANISM]["carbon_kg"], x["policies"][ABLATION]["carbon_kg"])}
             for x in scen if x["policies"][MECHANISM]["green_regret"] > x["policies"][ABLATION]["green_regret"]]
    summary = {reg: _summary(scen, reg) for reg in REGIMES}
    vs = {reg: {"extra_carbon": _ratio(s[MECHANISM]["carbon_kg"], s[ABLATION]["carbon_kg"]),
                "miss_rate": s[MECHANISM]["miss_rate"], "ablation_miss_rate": s[ABLATION]["miss_rate"],
                "green_regret": s[MECHANISM]["green_regret"], "ablation_green_regret": s[ABLATION]["green_regret"]}
          for reg, s in summary.items()}
    return {"seed": seed, "scenarios": len(scen), "jobs_per_scenario": scen[0]["jobs"],
            "infeasible_in_hindsight": sum(x["infeasible_in_hindsight"] for x in scen),
            "carbon_forecast_error": {"actual_over_forecast_p5": round(ratio[len(ratio) // 20], 3),
                                      "p50": round(statistics.median(ratio), 3),
                                      "p95": round(ratio[19 * len(ratio) // 20], 3)},
            "summary": summary, "mechanism_vs_ablation": vs, "mechanism_worse_than_ablation": worse, "per_scenario": scen}


def provenance(**extra) -> dict:
    def git(*args):
        r = subprocess.run(["git", *args], cwd=data.ROOT, capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    sha = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--", "carbon_oracle", "data"))
    m = data.meta()
    return {"commit": (sha or "unknown") + ("-dirty" if dirty else ""),
            "command": "python -m carbon_oracle " + " ".join(sys.argv[1:]),
            "python": platform.python_version(), "platform": platform.platform(),
            "data_sha256": data.load().sha256[:16], "data_source": m["source"], "data_license": m["license"],
            "data_window": f"{m['window']['start']} .. {m['window']['end']}", "data_fetched_at": m["fetched_at"],
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), **extra}


def _pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def _table(summ: dict) -> list[str]:
    L = ["| Policy | Green Regret / job | Objective gap / job | Deadline misses | Residency violations "
         "| Carbon kg | vs run-now | vs oracle | Cost $ |", "|---|---|---|---|---|---|---|---|---|"]
    for p, x in summ.items():
        L.append(f"| {LABELS[p]} | {x['green_regret']:.3f} | {x['objective_gap']:.3f} | "
                 f"{x['deadline_misses']}/{x['jobs']} ({100 * x['miss_rate']:.1f}%) | {x['residency_violations']} | "
                 f"{x['carbon_kg']:.1f} | {_pct(x['carbon_vs_run_now'])} | {_pct(x['carbon_vs_oracle'])} | "
                 f"{x['cost_usd']:.0f} |")
    return L


def markdown(rep: dict) -> str:
    e = rep["carbon_forecast_error"]
    L = ["# CARBON ORACLE benchmark: Green Regret under forecast error", "",
         "_Real GB regional carbon intensity; **synthetic** jobs, prices, queue waits and runtime errors. "
         "Every number below was produced by the command in the provenance section._", "",
         f"- {rep['scenarios']} scenarios x {rep['jobs_per_scenario']} jobs (batch inference, embedding backfill, "
         "eval suites, fine-tuning), 7 illustrative regions mapped to GB grid regions, residency zones "
         "england / wales / gb / pinned-to-home.",
         f"- Realised carbon intensity differs from the forecast every policy sees by a factor of "
         f"{e['actual_over_forecast_p5']} (p5) / {e['p50']} (p50) / {e['p95']} (p95).",
         f"- Green Regret per job = normalised carbon+cost objective minus the hindsight oracle's, plus {PENALTY:g} "
         "per deadline miss or residency violation. The oracle knows realised carbon, queue waits and runtimes.",
         f"- Jobs no placement could finish on time in hindsight are excluded: {rep['infeasible_in_hindsight']}.", ""]
    titles = {"nominal": "Nominal (queues and runtimes drawn from the schedulers' history)",
              "calm": "Calm (queues and runtimes better than history): where the risk bound buys nothing",
              "tail_shift": "Tail shift (wider errors, 10% congestion events): the risk bound is miscalibrated"}
    for reg, summ in rep["summary"].items():
        n = next(iter(summ.values()))["scenarios"]
        L += [f"## {titles[reg]} ({n} scenarios)", "", *_table(summ), ""]
    L += ["## Mechanism vs its ablation (same objective, chance constraint removed)", "",
          "| Regime | RGW Green Regret | Ablation Green Regret | RGW miss rate | Ablation miss rate "
          "| RGW carbon vs ablation |", "|---|---|---|---|---|---|"]
    for reg, x in rep["mechanism_vs_ablation"].items():
        L.append(f"| {reg} | {x['green_regret']:.3f} | {x['ablation_green_regret']:.3f} | "
                 f"{100 * x['miss_rate']:.1f}% | {100 * x['ablation_miss_rate']:.1f}% | {_pct(x['extra_carbon'])} |")
    L += ["", "## Scenarios where RGW did worse than its ablation", ""]
    if rep["mechanism_worse_than_ablation"]:
        L += ["| Scenario | RGW regret | Deterministic regret | RGW carbon kg | Deterministic carbon kg "
              "| RGW carbon vs deterministic | RGW misses | Deterministic misses |", "|---|---|---|---|---|---|---|---|"]
        for x in rep["mechanism_worse_than_ablation"]:
            L.append(f"| {x['scenario']} | {x['rgw_green_regret']:.3f} | {x['deterministic_green_regret']:.3f} | "
                     f"{x['rgw_carbon_kg']:.1f} | {x['deterministic_carbon_kg']:.1f} | {_pct(x['extra_carbon'])} | "
                     f"{x['rgw_deadline_misses']} | "
                     f"{x['deterministic_deadline_misses']} |")
    else:
        L.append("None.")
    L += ["", "## Per scenario (Green Regret / job; deadline misses in brackets)", "",
          "| Scenario | " + " | ".join(POLICIES) + " |", "|---|" + "---|" * len(POLICIES)]
    for x in rep["per_scenario"]:
        L.append(f"| {x['scenario']} | " + " | ".join(
            f"{x['policies'][p]['green_regret']:.2f} ({x['policies'][p]['deadline_misses']})" for p in POLICIES) + " |")
    L += ["", "## Provenance", "", *(f"- {k}: `{v}`" for k, v in rep["provenance"].items()), ""]
    return "\n".join(L)
