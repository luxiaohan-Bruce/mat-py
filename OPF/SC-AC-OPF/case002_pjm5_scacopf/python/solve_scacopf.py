#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from scacopf_model import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    solution = result["scacopf"]
    print(f"[{result['case']}] status={solution['status']} obj={solution.get('obj')} n_cont={solution.get('n_cont')}")
