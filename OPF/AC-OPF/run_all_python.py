#!/usr/bin/env python3
"""Solve and independently validate all exact AC-OPF pilots."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from acopf_model import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    summary = []
    for item in manifest:
        case_dir = ROOT / item["path"]
        try:
            result = run_case(case_dir, quiet="--verbose" not in sys.argv)
            solution = result["acopf"]
            passed = bool(result["validation"]["passed"])
            summary.append(
                {
                    "case": item["case"],
                    "status": solution["status"],
                    "objective": solution["objective"],
                    "objective_bound": solution["objective_bound"],
                    "optimality_gap": solution["optimality_gap"],
                    "runtime_seconds": solution["runtime_seconds"],
                    "validation_passed": passed,
                    "max_p_balance_MW": solution.get("max_p_balance_MW"),
                    "max_q_balance_MVAr": solution.get("max_q_balance_MVAr"),
                }
            )
            print(
                f"[{item['case']}] {solution['status']} obj={solution['objective']} "
                f"valid={passed} t={solution['runtime_seconds']:.3f}s"
            )
        except Exception as error:
            summary.append({"case": item["case"], "status": "ERROR", "error": str(error)})
            print(f"[{item['case']}] ERROR {error}")
    (ROOT / "PYTHON_SOLVE_SUMMARY.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    passed_count = sum(
        item.get("status") == "OPTIMAL" and item.get("validation_passed") for item in summary
    )
    print(f"summary: OPTIMAL+valid={passed_count}/{len(summary)}")
    return 0 if passed_count == len(summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
