#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from microgrid_model_py import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest:
        result = run_case(ROOT / item["case"], quiet=True)
        block = result["microgrid"]
        print(f"[{item['case']}] status={block.get('status')} obj={block.get('obj', block.get('objective'))}")
        if block.get("status") != "OPTIMAL" or not block.get("validation_passed"):
            failures += 1
    print(f"done; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
