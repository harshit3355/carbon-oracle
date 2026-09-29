"""Placement policies. Each sees carbon forecasts, queue forecasts and history, never the realised world.

A policy returns (region, submit time). Submission is final: no re-planning, no preemption.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import partial

from .data import SLOT_H, Trace, integral, prefix
from .model import CLASSES, PRICE, PUE, QUEUE, Job, objective, queue_forecast, queue_ratio, runtime_ratio, starts


@dataclass(frozen=True)
class View:
    forecast: dict[str, list[float]]  # prefix sums of forecast intensity
    q_hist: dict[str, list[float]]    # past realised/forecast queue-wait ratios per region
    r_hist: dict[str, list[float]]    # past realised/nominal runtime ratios per job class


def view(trace: Trace, seed: int, n: int = 1000) -> View:
    """History is drawn from the nominal regime with its own seed: what an operator's logs would show."""
    rng = random.Random(seed)
    return View({r: prefix(v) for r, v in trace.forecast.items()},
                {r: [queue_ratio(rng, r, "nominal") for _ in range(n)] for r in QUEUE},
                {c: [runtime_ratio(rng, c, "nominal") for _ in range(n)] for c in CLASSES})


def _est(job: Job, v: View, r: str, s: float) -> float:
    """Point-estimate objective: forecast carbon, median queue wait, nominal runtime."""
    begin = s + queue_forecast(r, s)
    carbon = job.power_kw * PUE * integral(v.forecast[r], begin, begin + job.runtime) / 1000
    return objective(job, carbon, PRICE[r] * job.runtime)


def _optimize(job: Job, v: View, need) -> tuple[str, float]:
    """Min estimated objective over feasible (region, submit) pairs; `need(r, s)` = hours from submit to finish."""
    feasible = [(r, s) for r in job.allowed for s in starts(job) if s + need(r, s) <= job.deadline]
    if not feasible:  # nothing passes the bound: take the earliest-finishing option now
        return min(((r, job.release) for r in job.allowed), key=lambda x: need(*x))
    return min(feasible, key=lambda x: _est(job, v, *x))


def deterministic(job: Job, v: View) -> tuple[str, float]:
    return _optimize(job, v, lambda r, s: queue_forecast(r, s) + job.runtime)


def padded(job: Job, v: View) -> tuple[str, float]:
    """Deterministic plus a hand-tuned safety margin (2x queue, +25% runtime): the obvious heuristic."""
    return _optimize(job, v, lambda r, s: 2 * queue_forecast(r, s) + 1.25 * job.runtime)


def rgw(job: Job, v: View, eps: float = 0.05) -> tuple[str, float]:
    """Risk-Bounded Green Window: P(wait + runtime <= deadline - submit) >= 1 - eps under the empirical
    history of queue and runtime errors. Queue and runtime draws are independent, so pairing by index is valid."""
    k = math.ceil((1 - eps) * len(v.r_hist[job.cls])) - 1
    cache: dict[tuple[str, float], float] = {}

    def need(r: str, s: float) -> float:
        w = queue_forecast(r, s)
        if (r, w) not in cache:
            cache[(r, w)] = sorted(w * q + job.runtime * p for q, p in zip(v.q_hist[r], v.r_hist[job.cls]))[k]
        return cache[(r, w)]
    return _optimize(job, v, need)


def run_now_home(job: Job, v: View) -> tuple[str, float]:
    return job.home, job.release


def cheapest(job: Job, v: View) -> tuple[str, float]:
    return min(job.allowed, key=PRICE.get), job.release


def lowest_carbon_now(job: Job, v: View) -> tuple[str, float]:
    return min(job.allowed, key=lambda r: integral(v.forecast[r], job.release, job.release + SLOT_H)), job.release


def deadline_first(job: Job, v: View) -> tuple[str, float]:
    """Run now where the forecast queue is shortest: earliest expected completion."""
    return min(job.allowed, key=lambda r: (queue_forecast(r, job.release), PRICE[r])), job.release


def best_window_home(job: Job, v: View) -> tuple[str, float]:
    """carbon-aware-sdk style: lowest-forecast window of the job's length before the deadline, one location,
    no queue or runtime uncertainty."""
    ok = [s for s in starts(job) if s + job.runtime <= job.deadline] or [job.release]
    return job.home, min(ok, key=lambda s: integral(v.forecast[job.home], s, s + job.runtime))


POLICIES = {
    "run_now_home": run_now_home,
    "cheapest": cheapest,
    "lowest_carbon_now": lowest_carbon_now,
    "deadline_first": deadline_first,
    "best_window_home": best_window_home,
    "deterministic": deterministic,
    "padded": padded,
    "rgw_eps0.01": partial(rgw, eps=0.01),
    "rgw": rgw,
    "rgw_eps0.20": partial(rgw, eps=0.20),
}
