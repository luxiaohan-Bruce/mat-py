#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from mld_model_py import run_case  # noqa: E402


def main() -> int:
    for item in json.loads((ROOT / "MANIFEST.json").read_text()):
        r = run_case(ROOT / item["case"], quiet=True)
        e = r["mld"]
        print(f"[{r['case']}] {e['status']} obj={e['obj']} served={e['served_MW']:.3f} valid={e['validation_passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
