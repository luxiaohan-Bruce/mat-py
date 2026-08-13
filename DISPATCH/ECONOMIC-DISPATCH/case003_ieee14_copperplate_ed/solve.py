#!/usr/bin/env python3
from pathlib import Path
import sys

CASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from economic_dispatch_model_py import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)["economic_dispatch"]
    print(f"[{CASE_DIR.name}] status={result['status']} obj={result['obj']} bal={result['max_balance_violation_MW']:.3e}")
