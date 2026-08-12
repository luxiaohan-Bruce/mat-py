#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from restore_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    e = r["restore"]
    print(f"[{r['case']}] {e.get('status')} obj={e.get('obj')} served_final={e.get('served_MW_final')}")
