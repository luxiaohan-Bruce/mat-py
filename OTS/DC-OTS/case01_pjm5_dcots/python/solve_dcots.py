#!/usr/bin/env python3
"""Solve Case 01 PJM5 DC-OTS with gurobipy."""
from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
ROOT = CASE_DIR.parent
sys.path.insert(0, str(ROOT / "common"))

from dcots_model_py import run_case  # noqa: E402


def main() -> None:
    r = run_case(CASE_DIR, quiet=True)
    d, o = r["dcopf"], r["ots"]
    dobj = "None" if d["obj"] is None else f"{d['obj']:.6f}"
    oobj = "None" if o["obj"] is None else f"{o['obj']:.6f}"
    sav = "None" if r["savings"] is None else f"{r['savings']:.6f}"
    print(
        f"[{r['case']}] DCOPF={dobj}  OTS={oobj}  "
        f"savings={sav}  opened={o['opened_lines']}  status={o['status']}"
    )


if __name__ == "__main__":
    main()
