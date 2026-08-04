#!/usr/bin/env python3
"""Solve this preventive N-1 SC-OTS case with gurobipy."""

from __future__ import annotations

import sys
from pathlib import Path


CASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE_DIR.parent))

from dcots_model import run_case  # noqa: E402


if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    baseline, optimized = result["dcopf"], result["ots"]
    print(
        f"[{result['case']}] SCOPF={baseline['obj']:.6f}  "
        f"SC-OTS={optimized['obj']:.6f}  savings={result['savings']:.6f}  "
        f"opened={optimized['opened_lines']}  status={optimized['status']}"
    )
