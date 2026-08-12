#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"common"))
from scacopf_model_py import run_case
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="full,relaxed")
    args = ap.parse_args()
    tiers = set(args.tier.split(","))
    manifest = json.loads((ROOT/"MANIFEST.json").read_text())
    fail=0
    for item in manifest:
        if item.get("solve_tier") not in tiers and "all" not in tiers:
            continue
        try:
            r = run_case(ROOT/item["case"], quiet=True)["scacopf"]
            obj = "None" if r.get("obj") is None else f"{r['obj']:.4f}"
            print(f"[{item['case']}] status={r.get('status')} obj={obj} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get("obj") is None: fail += 1
        except Exception as e:
            fail += 1
            print(f"[{item['case']}] ERROR {e}", flush=True)
            traceback.print_exc()
    print(f"done; failures={fail}")
    return 1 if fail else 0
if __name__ == "__main__":
    raise SystemExit(main())
