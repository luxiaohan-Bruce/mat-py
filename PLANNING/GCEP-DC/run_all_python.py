#!/usr/bin/env python3
"""Solve all cases in this pack with gurobipy (respect solve_tier)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from gcep_model_py import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    if isinstance(manifest, dict) and "cases" in manifest:
        items = manifest["cases"]
    else:
        items = manifest
    only_full = "--full-only" in sys.argv
    include_skip = "--include-skip" in sys.argv
    summary = []
    for item in items:
        name = item.get("case") or item.get("name") or item.get("path")
        tier = item.get("solve_tier", "full")
        if only_full and tier != "full":
            continue
        if tier == "skip" and not include_skip:
            summary.append({"case": name, "status": "SKIPPED", "obj": None})
            print(f"[{name}] SKIP (tier=skip)")
            continue
        case_dir = ROOT / name
        try:
            r = run_case(case_dir, quiet=True)
            e = None
            for k, v in r.items():
                if isinstance(v, dict) and "status" in v:
                    e = v
                    break
            if e is None:
                e = r
            summary.append(
                {
                    "case": name,
                    "status": e.get("status"),
                    "obj": e.get("obj", e.get("profit")),
                    "validation_passed": e.get("validation_passed"),
                    "runtime": e.get("runtime"),
                }
            )
            print(
                f"[{name}] {e.get('status')} obj={e.get('obj', e.get('profit'))} "
                f"valid={e.get('validation_passed')} t={e.get('runtime')}"
            )
        except Exception as ex:
            summary.append({"case": name, "status": "ERROR", "error": str(ex)})
            print(f"[{name}] ERROR {ex}")
    out = ROOT / "PYTHON_SOLVE_SUMMARY.json"
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    n_ok = sum(
        1
        for s in summary
        if s.get("status") in ("OPTIMAL", "SUBOPTIMAL")
        and (s.get("validation_passed") in (True, None))
    )
    print(f"summary: ok-ish={n_ok}/{len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
