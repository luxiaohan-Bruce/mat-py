#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from pmu_model_py import run_case

def main():
    for item in json.loads((ROOT/"MANIFEST.json").read_text()):
        if item.get("solve_tier")=="skip":
            print(f"[{item['case']}] SKIP"); continue
        r = run_case(ROOT/item["case"], quiet=True)
        e=r["pmu"]
        print(f"[{r['case']}] {e['status']} n={e['n_pmu']} obj={e['obj']} obs={e['all_observable']}")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
