#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE_DIR.parent/"common"))
from se_model_py import run_case
r=run_case(CASE_DIR,quiet=True); e=r["se"]
print(f"[{r['case']}] {e['method']} {e['status']} obj={e['obj']} rmse={e['rmse_theta_rad']:.3e}")
