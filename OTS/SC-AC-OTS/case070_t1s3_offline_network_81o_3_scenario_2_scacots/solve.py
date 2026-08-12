#!/usr/bin/env python3
"""Unified case entry — runs python/solve_*.py for this case."""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
CASE_DIR = HERE.parent.parent if HERE.parent.name == "python" else HERE.parent
PY = CASE_DIR / "python"
cands = []
if PY.is_dir():
    cands = sorted(p for p in PY.glob("solve_*.py") if p.name != "solve.py")
if not cands:
    cands = sorted(p for p in CASE_DIR.glob("solve_*.py") if p.resolve() != HERE)
if not cands:
    sys.stderr.write(f"no solver in {CASE_DIR}\n")
    raise SystemExit(2)
runpy.run_path(str(cands[0]), run_name="__main__")
