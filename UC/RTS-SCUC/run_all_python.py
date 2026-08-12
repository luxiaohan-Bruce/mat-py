#!/usr/bin/env python3
from __future__ import annotations
import json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from rts_scuc_model_py import run_case
def main():
    manifest = json.loads((ROOT/"MANIFEST.json").read_text())
    fail=0
    for item in manifest:
        try:
            r = run_case(ROOT/item["case"], quiet=True)["scuc"]
            obj = "None" if r.get("obj") is None else f"{r['obj']:.4f}"
            print(f"[{item['case']}] status={r.get('status')} obj={obj} gap={r.get('mip_gap')} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get("obj") is None: fail += 1
        except Exception as e:
            fail += 1
            print(f"[{item['case']}] ERROR {e}", flush=True)
            traceback.print_exc()
    print(f"done; failures={fail}")
    return 1 if fail else 0
if __name__ == "__main__":
    raise SystemExit(main())
