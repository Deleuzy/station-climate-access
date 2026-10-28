"""Command line: python -m sca run --city aarhus|copenhagen|all"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from .config import CITIES
from .pipeline import run_city

ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sca", description="Station climate-access screening")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fetch inputs if needed, then compute and write outputs")
    run.add_argument("--city", required=True, choices=[*CITIES, "all"])
    run.add_argument("--offline", action="store_true", help="use cached data only, no network")
    run.add_argument("--data-dir", type=Path, default=ROOT / "data")
    run.add_argument("--out-dir", type=Path, default=ROOT / "output")
    args = parser.parse_args(argv)

    keys = list(CITIES) if args.city == "all" else [args.city]
    tables = []
    for key in keys:
        table = run_city(CITIES[key], args.data_dir, args.out_dir, offline=args.offline)
        tables.append(table.assign(city=CITIES[key].label))
        print(
            f"{CITIES[key].label}: {len(table)} stations, "
            f"{int(table['high_exposure'].sum())} high exposure, "
            f"{int(table['high_exposure_and_access'].sum())} high exposure and access"
        )
    if len(tables) > 1:
        pd.concat(tables, ignore_index=True).to_csv(args.out_dir / "ranking_all_cities.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
