"""CLI: run the offline benchmark. `python -m carbon_oracle.fetch` refreshes data."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bench as bench_mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m carbon_oracle", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench", help="run every policy on every scenario and write reports/benchmark.{json,md}")
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--out", default="reports")
    a = ap.parse_args(argv)

    rep = bench_mod.bench(a.seed)
    rep["provenance"] = bench_mod.provenance(seed=a.seed)
    for reg, summ in rep["summary"].items():
        print(f"[{reg}]")
        for p, x in summ.items():
            print(f"  {p:18s} regret {x['green_regret']:7.3f}  misses {x['deadline_misses']:3d}/{x['jobs']}"
                  f"  carbon {x['carbon_kg']:8.1f} kg ({100 * x['carbon_vs_run_now']:+.1f}% vs run-now)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "benchmark.json").write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8", newline="\n")
    (out / "benchmark.md").write_text(bench_mod.markdown(rep), encoding="utf-8", newline="\n")
    print(f"wrote {out / 'benchmark.json'} and {out / 'benchmark.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
