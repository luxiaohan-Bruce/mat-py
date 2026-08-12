#!/usr/bin/env python3
"""Evaluate saved results.

    python3 evaluate.py OTS/DC-OTS/case01_pjm5_dcots
    python3 evaluate.py --network pglib_opf_case14_ieee
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from framework.catalog import cases_on_network  # noqa: E402
from framework.evaluate import evaluate, main as eval_main  # noqa: E402


def main() -> int:
    if "--network" in sys.argv:
        i = sys.argv.index("--network")
        name = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        ids = cases_on_network(name)
        if not ids:
            print(f"no cases for network {name!r}")
            return 1
        fail = 0
        for cid in ids:
            path = ROOT / cid
            ev = evaluate(path)
            flag = "PASS" if ev["passed"] else "FAIL"
            print(f"[{cid}] {flag} status={ev['status']} obj={ev['obj']} reason={ev['reason']}")
            if not ev["passed"]:
                fail += 1
        return 1 if fail else 0
    return eval_main()


if __name__ == "__main__":
    raise SystemExit(main())
