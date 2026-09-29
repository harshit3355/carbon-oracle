"""Refresh the cached carbon trace from the GB Carbon Intensity API (keyless, CC BY 4.0).

The only module that touches the network. Tests and the benchmark read the committed CSV.
Usage: python -m carbon_oracle.fetch --start 2026-09-01 --days 21
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import urllib.request

from .data import CSV, META, REGIONS

API = "https://api.carbonintensity.org.uk"


def _get(path: str) -> dict:
    req = urllib.request.Request(API + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:  # fixed https host, no user-supplied URL
        return json.load(r)


def fetch(start: dt.datetime, days: int) -> list[dict]:
    rows: dict[str, dict] = {}
    for k in range(0, days, 7):
        a, b = start + dt.timedelta(days=k), start + dt.timedelta(days=min(k + 7, days))
        fa, fb = a.strftime("%Y-%m-%dT%H:%MZ"), b.strftime("%Y-%m-%dT%H:%MZ")
        for x in _get(f"/intensity/{fa}/{fb}")["data"]:
            rows.setdefault(x["from"], {})["national_forecast"] = x["intensity"]["forecast"]
            rows[x["from"]]["national_actual"] = x["intensity"]["actual"]
        for x in _get(f"/regional/intensity/{fa}/{fb}")["data"]:
            by_id = {r["regionid"]: r["intensity"]["forecast"] for r in x["regions"]}
            rows.setdefault(x["from"], {}).update({name: by_id[rid] for name, (rid, _, _) in REGIONS.items()})
    end = start + dt.timedelta(days=days)
    keep = sorted(t for t in rows if start <= dt.datetime.strptime(t, "%Y-%m-%dT%H:%MZ") < end)
    out = [{"from": t, **rows[t]} for t in keep]
    missing = [r["from"] for r in out if any(v is None for v in r.values()) or len(r) != 3 + len(REGIONS)]
    if missing:
        raise RuntimeError(f"incomplete half-hours from the API: {missing[:5]} ({len(missing)} total)")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2026-09-01")
    ap.add_argument("--days", type=int, default=21)
    a = ap.parse_args()
    start = dt.datetime.strptime(a.start, "%Y-%m-%d")
    rows = fetch(start, a.days)
    cols = ["from", "national_forecast", "national_actual", *REGIONS]
    with CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    META.write_text(json.dumps({
        "source": API, "endpoints": ["/intensity/{from}/{to}", "/regional/intensity/{from}/{to}"],
        "publisher": "National Energy System Operator (NESO) Carbon Intensity API",
        "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "window": {"start": rows[0]["from"], "end": rows[-1]["from"], "half_hours": len(rows)},
        "columns": {"national_forecast": "GB forecast gCO2/kWh", "national_actual": "GB actual gCO2/kWh",
                    **{k: f"regional forecast gCO2/kWh, {v[1]} (API regionid {v[0]})" for k, v in REGIONS.items()}},
        "sha256": hashlib.sha256(CSV.read_bytes()).hexdigest()}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} half-hours to {CSV}")


if __name__ == "__main__":
    main()
