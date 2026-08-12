#!/usr/bin/env python3
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from scuc_model_py import run_case  # noqa: E402

if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    s = r["scuc"]
    print(f"[{r['case']}] {s['status']} obj={s['obj']} startups={s['startups']} t={s['runtime']:.2f}s")
