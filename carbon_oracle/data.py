"""Cached GB carbon trace and the (illustrative) cloud-region -> grid-region mapping."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "gb_carbon_intensity.csv"
META = ROOT / "data" / "gb_carbon_intensity.meta.json"
SLOT_H = 0.5  # the API reports half-hours

# Illustrative only: no cloud provider is implied. Each hypothetical region is placed in one GB
# distribution-network region so it inherits that region's published carbon intensity.
# Scottish regions are left out: the API reports ~0 gCO2/kWh for them throughout the cached window
# (generation-based regional accounting), which would make them trivially optimal.
# name: (API regionid, grid region, residency zone)
REGIONS = {
    "uk-lon": (13, "London", "england"),
    "uk-soe": (12, "South England", "england"),
    "uk-eae": (10, "East England", "england"),
    "uk-swe": (11, "South West England", "england"),
    "uk-wmd": (8, "West Midlands", "england"),
    "uk-swa": (7, "South Wales", "wales"),
    "uk-nwm": (6, "North Wales & Merseyside", "wales"),
}


@dataclass(frozen=True)
class Trace:
    times: list[str]
    forecast: dict[str, list[float]]  # what a scheduler sees: the API's regional forecast
    actual: dict[str, list[float]]    # what the job emits: regional forecast x national actual/forecast
    sha256: str

    def __len__(self) -> int:
        return len(self.times)


def load() -> Trace:
    raw = CSV.read_bytes()
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    # The API publishes no regional actuals, so realised regional intensity is derived: the regional
    # forecast rescaled by the same half-hour's national actual/forecast ratio (a real forecast error).
    ratio = [float(r["national_actual"]) / float(r["national_forecast"]) for r in rows]
    fc = {k: [float(r[k]) for r in rows] for k in REGIONS}
    act = {k: [v * q for v, q in zip(fc[k], ratio)] for k in REGIONS}
    return Trace([r["from"] for r in rows], fc, act, hashlib.sha256(raw).hexdigest())


def meta() -> dict:
    return json.loads(META.read_text(encoding="utf-8"))


def prefix(xs: list[float]) -> list[float]:
    out = [0.0]
    for x in xs:
        out.append(out[-1] + x * SLOT_H)
    return out


def integral(p: list[float], a: float, b: float) -> float:
    """Integral of the step function behind prefix sums `p` over [a, b] hours (clamped to the trace)."""
    def at(h: float) -> float:
        i = min(max(h / SLOT_H, 0.0), len(p) - 1.0)
        k = min(int(i), len(p) - 2)
        return p[k] + (p[k + 1] - p[k]) * (i - k)
    return at(b) - at(a)
