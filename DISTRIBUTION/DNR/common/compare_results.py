#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    man = json.loads((ROOT / "MANIFEST.json").read_text())
    ok = chk = 0
    for item in man:
        if item.get("solve_tier") == "skip":
            continue
        chk += 1
        cdir = ROOT / item["case"]
        py = cdir / "results" / "python_result.json"
        mat = cdir / "results" / "matlab_result.json"
        report = {
            "case": item["case"],
            "solver_consistency_ok": False,
            "comparison_issues": [],
            "validation_status": "structural_only",
            "physics_validated": False,
            "notes": [
                "Numerical solver agreement is not a physics-validation PASS.",
                "Voltage, reactive-power, radiality, and energized-connectivity constraints are not modeled.",
            ],
        }
        if not py.exists() or not mat.exists():
            report["comparison_issues"].append("missing")
        else:
            po = json.loads(py.read_text())["dnr"].get("obj")
            mo = json.loads(mat.read_text())["dnr"].get("obj")
            if po is None or mo is None:
                report["comparison_issues"].append("no obj")
            else:
                rel = abs(po - mo) / max(1.0, abs(po), abs(mo))
                if rel > 0.05:
                    report["comparison_issues"].append(f"rel {rel}")
            report["solver_consistency_ok"] = not report["comparison_issues"]
        (cdir / "results" / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
        ok += int(report["solver_consistency_ok"])
        print(f"{item['case']}: {'CONSISTENT' if report['solver_consistency_ok'] else 'INCONSISTENT'}")
    print(f"summary {ok}/{chk}")
    return 0 if ok == chk else 1

if __name__ == "__main__":
    raise SystemExit(main())
