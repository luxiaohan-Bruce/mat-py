#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / 'common'))
from green_llm_model_py import run_case  # noqa: E402
if __name__ == '__main__':
    r = run_case(CASE_DIR, quiet=True)
    e = r['green_llm']
    print(
        f"[{r['case']}] status={e['status']} obj={e['obj']} "
        f"E={e.get('energy_cost')} C={e.get('carbon_cost')} "
        f"D={e.get('delay_cost')} valid={e.get('validation_passed')}"
    )
