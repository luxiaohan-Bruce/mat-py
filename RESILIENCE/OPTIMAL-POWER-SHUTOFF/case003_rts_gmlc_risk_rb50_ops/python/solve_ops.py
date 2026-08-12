#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from ops_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    e = r["ops"]
    print(f"[{r['case']}] {e['status']} shed={e['load_shed_MW']:.3f} risk={e['risk_exposure']:.3f} deen={e['n_deenergized']}")
