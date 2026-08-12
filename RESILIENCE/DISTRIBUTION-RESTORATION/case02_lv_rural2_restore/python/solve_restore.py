#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from dist_restore_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)["restore"]
    print(
        f"[{CASE_DIR.name}] status={r.get('status')} obj={r.get('obj')} "
        f"valid={r.get('validation_passed')} served={r.get('served_MW')} "
        f"t={r.get('runtime', 0):.2f}s"
    )
