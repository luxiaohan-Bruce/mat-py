#!/usr/bin/env python3
"""Unified solver CLI.

    python3 solve.py OTS/DC-OTS/case01_pjm5_dcots
    python3 OTS/DC-OTS/case01_pjm5_dcots/solve.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from framework.runner import run_case_cli  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_case_cli())
