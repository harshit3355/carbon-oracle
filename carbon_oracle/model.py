"""Synthetic AI job sets, the realised world they run in, and hindsight evaluation.

Carbon intensity is real (cached GB data). Everything else here is synthetic and labelled as such:
job classes, prices, queue waits and runtime errors.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .data import REGIONS, SLOT_H, Trace, integral, prefix

# class: (nominal runtime range h, runtime log-sd, slack beyond nominal runtime h, node power kW)
CLASSES = {
    "batch_inference": ((1.0, 4.0), 0.10, (6.0, 24.0), 6.0),
    "embedding_backfill": ((2.0, 8.0), 0.15, (12.0, 36.0), 4.0),
    "eval_suite": ((0.5, 2.0), 0.25, (4.0, 12.0), 3.0),
    "fine_tune": ((4.0, 12.0), 0.30, (12.0, 36.0), 10.0),
}
PRICE = {"uk-lon": 28.0, "uk-soe": 29.0, "uk-eae": 29.0, "uk-swe": 30.0,  # $/node-hour
         "uk-wmd": 31.0, "uk-swa": 30.0, "uk-nwm": 32.0}
# (median queue wait h off-peak, log-sd). Assumption: the low-carbon regions are the small, congested ones.
QUEUE = {"uk-lon": (0.25, 0.3), "uk-soe": (0.25, 0.35), "uk-eae": (0.5, 0.4), "uk-swe": (0.5, 0.5),
         "uk-wmd": (0.75, 0.6), "uk-swa": (0.5, 0.5), "uk-nwm": (1.0, 0.7)}
RESIDENCY = {"gb": 0.40, "england": 0.35, "wales": 0.15, "pinned": 0.10}
# regime: (log-mean shift, log-sd multiplier) for queue waits and runtimes, probability of a 3-6x queue
# congestion event. Schedulers only ever see history from "nominal".
REGIMES = {"nominal": (0.0, 1.0, 0.03), "calm": (-0.25, 0.5, 0.0), "tail_shift": (0.0, 1.5, 0.10)}
PUE = 1.2
I_REF = 100.0     # gCO2/kWh, fixes the carbon/cost exchange rate in the objective
COST_WEIGHT = 1.0  # 1% of a job's reference cost weighs the same as 1% of its reference carbon
PENALTY = 10.0     # Green Regret added per deadline miss or residency violation


@dataclass(frozen=True)
class Job:
    id: int
    cls: str
    release: float   # hours from trace start, on a slot boundary
    runtime: float   # nominal (estimated) hours
    deadline: float
    power_kw: float
    home: str
    residency: str
    allowed: tuple[str, ...]


@dataclass(frozen=True)
class World:
    """Realised values, shared by every policy in a scenario (common random numbers)."""
    actual: dict[str, list[float]]   # prefix sums of realised intensity
    wait: dict[str, list[float]]     # realised queue wait for a submission in each slot
    runtime: dict[int, float]        # realised runtime per job


def allowed(residency: str, home: str) -> tuple[str, ...]:
    if residency == "pinned":
        return (home,)
    return tuple(r for r, (_, _, z) in REGIONS.items() if residency in ("gb", z))


def queue_forecast(region: str, h: float) -> float:
    return QUEUE[region][0] * (2.0 if 7 <= h % 24 < 18 else 1.0)


def queue_ratio(rng: random.Random, region: str, regime: str) -> float:
    mu, sd, p = REGIMES[regime]
    x = math.exp(rng.gauss(mu, QUEUE[region][1] * sd))
    return x * rng.uniform(3.0, 6.0) if rng.random() < p else x


def runtime_ratio(rng: random.Random, cls: str, regime: str) -> float:
    mu, sd, _ = REGIMES[regime]
    return math.exp(rng.gauss(mu, CLASSES[cls][1] * sd))


def scenario(trace: Trace, day: int, regime: str, seed: int, n_jobs: int = 50) -> tuple[list[Job], World]:
    rng = random.Random(seed)
    jobs = []
    for i in range(n_jobs):
        cls = rng.choice(list(CLASSES))
        (lo, hi), _, (slo, shi), kw = CLASSES[cls]
        res = rng.choices(list(RESIDENCY), weights=list(RESIDENCY.values()))[0]
        home = rng.choice(allowed(res, "") if res in ("england", "wales") else list(REGIONS))
        release = day * 24 + rng.randrange(48) * SLOT_H
        runtime = round(rng.uniform(lo, hi) * 4) / 4
        jobs.append(Job(i, cls, release, runtime, release + runtime + round(rng.uniform(slo, shi) * 2) / 2,
                        kw, home, res, allowed(res, home)))
    wait = {r: [queue_forecast(r, k * SLOT_H) * queue_ratio(rng, r, regime) for k in range(len(trace))]
            for r in REGIONS}
    runtime = {j.id: j.runtime * runtime_ratio(rng, j.cls, regime) for j in jobs}
    return jobs, World({r: prefix(v) for r, v in trace.actual.items()}, wait, runtime)


def objective(job: Job, carbon_kg: float, cost: float) -> float:
    cref = job.power_kw * PUE * job.runtime * I_REF / 1000
    kref = job.runtime * sum(PRICE.values()) / len(PRICE)
    return carbon_kg / cref + COST_WEIGHT * cost / kref


def starts(job: Job) -> list[float]:
    return [job.release + k * SLOT_H for k in range(int((job.deadline - job.release) / SLOT_H))]


def outcome(job: Job, world: World, region: str, s: float) -> dict:
    begin = s + world.wait[region][round(s / SLOT_H)]
    finish = begin + world.runtime[job.id]
    carbon = job.power_kw * PUE * integral(world.actual[region], begin, finish) / 1000
    cost = PRICE[region] * world.runtime[job.id]
    return {"region": region, "submit": s, "finish": round(finish, 3), "carbon_kg": carbon, "cost": cost,
            "missed": finish > job.deadline + 1e-9, "residency_violation": region not in job.allowed,
            "J": objective(job, carbon, cost)}


def oracle(job: Job, world: World) -> dict | None:
    """Hindsight optimum: realised carbon, queue waits and runtime. None if nothing meets the deadline."""
    best = None
    for r in job.allowed:
        for s in starts(job):
            o = outcome(job, world, r, s)
            if not o["missed"] and (best is None or o["J"] < best["J"]):
                best = o
    return best
