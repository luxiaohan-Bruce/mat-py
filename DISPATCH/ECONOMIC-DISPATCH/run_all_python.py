#!/usr/bin/env python3
"""Run all copperplate economic-dispatch pilot cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from economic_dispatch_model_py import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest:
        result = run_case(ROOT / item["case"], quiet=True)
        solution = result["economic_dispatch"]
        print(
            f"[{item['case']}] status={solution['status']} obj={solution['obj']} "
            f"bal={solution.get('max_balance_violation_MW', float('inf')):.3e}"
        )
        if solution["status"] != "OPTIMAL" or not solution.get("validation_passed"):
            failures += 1
    print(f"done; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
