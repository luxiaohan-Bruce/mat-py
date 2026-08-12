#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from uc_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)["uc"]
    obj = "None" if r["obj"] is None else f"{r['obj']:.6f}"
    print(f"[{CASE_DIR.name}] status={r['status']} obj={obj} gap={r.get('mip_gap')} t={r['runtime']:.2f}s")
