#!/usr/bin/env python3
"""Solve SCUC case with gurobipy."""
from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
ROOT = CASE_DIR.parent
sys.path.insert(0, str(ROOT / "common"))

from scuc_model_py import run_case  # noqa: E402


def main() -> None:
    r = run_case(CASE_DIR, quiet=True)
    sol = r.get("scuc") or {}
    obj = sol.get("obj")
    o = "None" if obj is None else f"{obj:.6f}"
    print(
        f"[{r.get('case', CASE_DIR.name)}] obj={o}  status={sol.get('status')}  "
        f"starts={sol.get('n_starts')}  t={sol.get('runtime')}"
    )


if __name__ == "__main__":
    main()
