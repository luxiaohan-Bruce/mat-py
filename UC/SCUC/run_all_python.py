#!/usr/bin/env python3
"""Run all SCUC cases with Python/gurobipy."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))

from scuc_model_py import run_case  # noqa: E402

CASES = [
    "case01_ieee39_scuc",
    "case02_ieee57_scuc",
    "case03_case60_scuc",
]


def main() -> None:
    for name in CASES:
        r = run_case(ROOT / name, quiet=True)
        s = r["scuc"]
        obj = "None" if s["obj"] is None else f"{s['obj']:.4f}"
        print(
            f"[{name}] status={s['status']} obj={obj} "
            f"startups={s.get('startups')} shutdowns={s.get('shutdowns')} "
            f"t={s['runtime']:.2f}s gap={s.get('mip_gap')}"
        )


if __name__ == "__main__":
    main()
