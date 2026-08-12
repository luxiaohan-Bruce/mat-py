#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE_DIR.parent/"common"))
from pmu_model_py import run_case
r=run_case(CASE_DIR,quiet=True); e=r["pmu"]
print(f"[{r['case']}] {e['status']} n_pmu={e['n_pmu']} obj={e['obj']}")
