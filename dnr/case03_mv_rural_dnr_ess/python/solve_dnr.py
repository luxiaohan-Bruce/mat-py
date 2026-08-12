#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE_DIR.parent/'common'))
from dnr_model_py import run_case
if __name__=='__main__':
    r=run_case(CASE_DIR,quiet=True)['dnr']
    print(f"[{CASE_DIR.name}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s")
