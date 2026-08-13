#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from acopf_model import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    solution = result["acopf"]
    print(
        f"[{result['case']}] status={solution['status']} obj={solution['objective']} "
        f"Pbal={solution.get('max_p_balance_MW', float('inf')):.3e} "
        f"Qbal={solution.get('max_q_balance_MVAr', float('inf')):.3e}"
    )
