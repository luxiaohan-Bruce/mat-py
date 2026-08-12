#!/usr/bin/env python3
"""Run every generated PGLib-UC case with gurobipy."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from uc_model_py import run_case  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tier",
        default="all",
        help="Comma-separated tiers to run, or 'all' (default)",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated case folder names to run",
    )
    args = parser.parse_args()
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    tiers = {x.strip() for x in args.tier.split(",") if x.strip()}
    failed = 0
    for item in manifest:
        if only and item["case"] not in only:
            continue
        if "all" not in tiers and item.get("solve_tier") not in tiers:
            continue
        try:
            result = run_case(ROOT / item["case"], quiet=True)["uc"]
            obj = "None" if result["obj"] is None else f"{result['obj']:.4f}"
            print(
                f"[{item['case']}] status={result['status']} obj={obj} "
                f"gap={result.get('mip_gap')} t={result['runtime']:.2f}s",
                flush=True,
            )
            if result["obj"] is None:
                failed += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[{item['case']}] ERROR {exc}", flush=True)
            traceback.print_exc()
    print(f"done; failures={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
