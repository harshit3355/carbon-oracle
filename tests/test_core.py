import hashlib

import pytest

from carbon_oracle import data
from carbon_oracle.bench import run_scenario
from carbon_oracle.model import oracle, outcome, scenario
from carbon_oracle.policies import POLICIES, deterministic, rgw, view

TRACE = data.load()
VIEW = view(TRACE, seed=1)


def test_integral_handles_partial_slots():
    p = data.prefix([10.0, 20.0])  # two half-hour slots
    assert data.integral(p, 0.25, 0.75) == pytest.approx(10 * 0.25 + 20 * 0.25)
    assert data.integral(p, 0.0, 5.0) == pytest.approx(15.0)  # clamped to the trace


def test_cached_data_matches_its_metadata():
    m = data.meta()
    assert hashlib.sha256(data.CSV.read_bytes()).hexdigest() == m["sha256"]
    assert len(TRACE) == m["window"]["half_hours"] == 21 * 48
    assert set(TRACE.forecast) == set(data.REGIONS)
    assert all(x >= 0 for r in data.REGIONS for x in TRACE.actual[r])


def test_oracle_is_a_lower_bound_and_residency_holds():
    jobs, world = scenario(TRACE, day=2, regime="nominal", seed=11)
    for job in jobs:
        best = oracle(job, world)
        for f in POLICIES.values():
            o = outcome(job, world, *f(job, VIEW))
            assert not o["residency_violation"]
            if best and not o["missed"]:
                assert o["J"] >= best["J"] - 1e-9


def test_residency_violation_is_flagged():
    jobs, world = scenario(TRACE, day=0, regime="nominal", seed=3)
    job = next(j for j in jobs if j.residency == "wales")
    assert outcome(job, world, "uk-lon", job.release)["residency_violation"]


def test_chance_constraint_bounds_deadline_misses():
    """Fails if the risk bound is removed or broken: RGW must keep misses under eps where the
    deterministic optimizer, with the same objective, does not."""
    missed = {"rgw": 0, "det": 0}
    n = 0
    for day in (0, 4, 8):
        jobs, world = scenario(TRACE, day=day, regime="nominal", seed=100 + day)
        for job in jobs:
            if oracle(job, world) is None:
                continue
            n += 1
            missed["rgw"] += outcome(job, world, *rgw(job, VIEW))["missed"]
            missed["det"] += outcome(job, world, *deterministic(job, VIEW))["missed"]
    assert missed["rgw"] <= 0.05 * n
    assert missed["det"] >= 3 * max(missed["rgw"], 1)


def test_scenarios_are_reproducible():
    a = run_scenario(TRACE, VIEW, "x", 1, "calm", 5)
    b = run_scenario(TRACE, VIEW, "x", 1, "calm", 5)
    assert a == b
