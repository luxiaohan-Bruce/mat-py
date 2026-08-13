#!/usr/bin/env python3
from pathlib import Path
import sys

CASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from distribution_expansion_model_py import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    block = result["dist_exp"]
    print(
        f"[{CASE_DIR.name}] status={block.get('status')} obj={block.get('obj', block.get('objective'))}"
    )
