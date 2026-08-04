#!/usr/bin/env python3
"""Discover and solve all six DC-OTS/SC-OTS cases."""

from __future__ import annotations

from pathlib import Path

from dcots_model import discover_cases, run_case


ROOT = Path(__file__).resolve().parent


def main() -> None:
    for name in discover_cases(ROOT):
        result = run_case(ROOT / name, quiet=True)
        baseline = result["dcopf"]
        optimized = result["ots"]
        baseline_label = "SCOPF" if result["problem"] == "scots" else "DCOPF"
        optimized_label = "SC-OTS" if result["problem"] == "scots" else "DC-OTS"
        print(
            f"[{name}] {baseline_label}={baseline['obj']:.6f}  "
            f"{optimized_label}={optimized['obj']:.6f}  "
            f"savings={result['savings']:.6f}  "
            f"opened={optimized['opened_lines']}  status={optimized['status']}"
        )


if __name__ == "__main__":
    main()
