#!/usr/bin/env python3
"""Solve all DC-OPF cases with gurobipy (respect solve_tier)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from ed_model_py import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    only_full = "--full-only" in sys.argv
    include_skip = "--include-skip" in sys.argv
    summary = []
    for item in manifest:
        tier = item.get("solve_tier", "full")
        if only_full and tier != "full":
            continue
        if tier == "skip" and not include_skip:
            summary.append({"case": item["case"], "status": "SKIPPED", "obj": None})
            print(f"[{item['case']}] SKIP (tier=skip)")
            continue
        case_dir = ROOT / item["case"]
        try:
            r = run_case(case_dir, quiet=True)
            e = r["ed"]
            summary.append(
                {
                    "case": item["case"],
                    "status": e["status"],
                    "obj": e["obj"],
                    "validation_passed": e.get("validation_passed"),
                    "runtime": e.get("runtime"),
                }
            )
            print(
                f"[{item['case']}] {e['status']} obj={e['obj']} "
                f"valid={e.get('validation_passed')} t={e.get('runtime'):.3f}s"
            )
        except Exception as ex:
            summary.append({"case": item["case"], "status": "ERROR", "error": str(ex)})
            print(f"[{item['case']}] ERROR {ex}")
    out = ROOT / "PYTHON_SOLVE_SUMMARY.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    n_ok = sum(1 for s in summary if s.get("status") == "OPTIMAL" and s.get("validation_passed"))
    print(f"summary: OPTIMAL+valid={n_ok}/{len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
