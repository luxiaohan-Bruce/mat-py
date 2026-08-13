#!/usr/bin/env python3
"""Validate stored Python results for the Python-only GO C1 package."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    passed = 0
    checked = 0
    for item in manifest:
        if item.get("solve_tier") == "skip":
            continue
        case_dir = ROOT / item["case"]
        py_path = case_dir / "results" / "python_result.json"
        report = {
            "case": item["case"],
            "validation": "python_result",
            "ok": False,
            "issues": [],
            "checks": {},
        }
        checked += 1
        if not py_path.is_file():
            report["issues"].append("missing python_result.json")
        else:
            result = json.loads(py_path.read_text(encoding="utf-8")).get("scacopf", {})
            obj = result.get("obj")
            status = result.get("status")
            report["checks"].update(
                status=status,
                obj=obj,
                mip_gap=result.get("mip_gap"),
                load_shed_MW=result.get("load_shed_MW"),
                flow_slack_pu=result.get("flow_slack_pu"),
            )
            if status not in {"OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT"}:
                report["issues"].append(f"unusable solver status: {status}")
            if not isinstance(obj, (int, float)) or not math.isfinite(float(obj)):
                report["issues"].append("missing or non-finite objective")
            report["ok"] = not report["issues"]
        (case_dir / "results" / "comparison.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        passed += int(report["ok"])
        print(f"{item['case']}: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"summary: {passed}/{checked} Python results valid (skip excluded)")
    return 0 if passed == checked else 1


if __name__ == "__main__":
    raise SystemExit(main())
