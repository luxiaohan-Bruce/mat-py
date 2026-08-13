#!/usr/bin/env python3
"""Run all distribution-OPF cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from dnr_model_py import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest:
        result = run_case(ROOT / item["case"], quiet=True)["dnr"]
        print(
            f"[{item['case']}] status={result.get('status')} obj={result.get('obj')} "
            f"t={result.get('runtime', 0.0):.2f}s"
        )
        if result.get("status") != "OPTIMAL" or result.get("obj") is None:
            failures += 1
    print(f"done; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
