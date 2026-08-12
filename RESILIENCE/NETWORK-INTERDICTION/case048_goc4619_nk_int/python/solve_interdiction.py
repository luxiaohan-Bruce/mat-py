#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from interdiction_model_py import run_case  # noqa: E402
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)
    e = r["interdiction"]
    print(
        f"[{r['case']}] status={e['status']} method={e['method']} "
        f"obj={e['obj']} atk={e['attacked_lines_idx']} "
        f"bal={e['max_power_balance_MW']:.3e}"
    )
