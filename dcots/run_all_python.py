#!/usr/bin/env python3
"""Discover and solve every DC-OTS case with Python/gurobipy."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))

from dcots_model_py import discover_cases, run_case  # noqa: E402


def main() -> None:
    for name in discover_cases(ROOT):
        r = run_case(ROOT / name, quiet=True)
        d, o = r["dcopf"], r["ots"]
        dobj = "None" if d["obj"] is None else f"{d['obj']:.6f}"
        oobj = "None" if o["obj"] is None else f"{o['obj']:.6f}"
        sav = "None" if r["savings"] is None else f"{r['savings']:.6f}"
        print(
            f"[{name}] DCOPF={dobj}  DC-OTS={oobj}  "
            f"savings={sav}  opened={o['opened_lines']}  "
            f"status={o['status']}  t={o['runtime']:.3f}s"
        )


if __name__ == "__main__":
    main()
