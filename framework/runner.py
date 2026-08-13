"""Unified case entry: find python/solve_*.py and run it."""

from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path


def find_solver(case_dir: str | Path) -> Path | None:
    case = Path(case_dir).resolve()
    py = case / "python"
    cands: list[Path] = []
    if py.is_dir():
        cands.extend(sorted(p for p in py.glob("solve_*.py") if p.name != "solve.py"))
        if (py / "solve.py").is_file() and not cands:
            cands.append(py / "solve.py")
    cands.extend(sorted(p for p in case.glob("solve_*.py") if p.name != "solve.py"))
    # A case may implement its model directly in the canonical root entrypoint
    # instead of delegating to python/solve_*.py.
    root_solver = case / "solve.py"
    if not cands and root_solver.is_file():
        try:
            source = root_solver.read_text(encoding="utf-8")
        except OSError:
            source = ""
        shim_marker = 'cands = sorted(p for p in PY.glob("solve_*.py")'
        if shim_marker not in source:
            cands.append(root_solver)
    return cands[0] if cands else None


def run_case(case_dir: str | Path, *, capture: bool = False) -> int:
    """Execute the case solver as __main__. Returns process exit code."""
    case = Path(case_dir).resolve()
    solver = find_solver(case)
    if solver is None:
        sys.stderr.write(f"no solver found in {case}\n")
        return 2
    if capture:
        proc = subprocess.run([sys.executable, str(solver)], cwd=str(case))
        return int(proc.returncode)
    runpy.run_path(str(solver), run_name="__main__")
    return 0


def run_case_cli(case_dir: str | Path | None = None) -> int:
    if case_dir is None:
        argv = [a for a in sys.argv[1:] if not a.startswith("-")]
        if not argv:
            sys.stderr.write("usage: solve.py <case_dir>\n")
            return 2
        case_dir = argv[0]
    return run_case(case_dir, capture=True)


SOLVE_SHIM = '''#!/usr/bin/env python3
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
    sys.stderr.write(f"no solver in {CASE_DIR}\\n")
    raise SystemExit(2)
runpy.run_path(str(cands[0]), run_name="__main__")
'''
