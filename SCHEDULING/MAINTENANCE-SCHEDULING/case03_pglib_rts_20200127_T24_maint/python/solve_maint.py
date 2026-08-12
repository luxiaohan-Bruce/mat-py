#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from maint_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    e = r["maint"]
    print(f"[{r['case']}] status={e['status']} obj={e['obj']} starts={e['start_period']} "
          f"valid={e['validation_passed']} t={e['runtime']:.2f}s")
