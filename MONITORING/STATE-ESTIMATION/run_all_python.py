#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from se_model_py import run_case

def main():
    for item in json.loads((ROOT/"MANIFEST.json").read_text()):
        r = run_case(ROOT/item["case"], quiet=True)
        e = r["se"]
        print(f"[{r['case']}] {e['method']} {e['status']} obj={e['obj']} rmse={e['rmse_theta_rad']:.3e}")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
