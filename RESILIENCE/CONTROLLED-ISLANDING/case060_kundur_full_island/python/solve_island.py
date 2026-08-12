#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from island_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    e = r["island"]
    print(f"[{r['case']}] {e.get('status')} obj={e.get('obj')} shed={e.get('total_shed_MW')} open={e.get('n_open_lines')} valid={e.get('validation_passed')}")
