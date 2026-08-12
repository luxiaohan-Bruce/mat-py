#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    passed = 0
    for item in manifest:
        case_dir = ROOT / item["case"]
        py_path = case_dir / "results" / "python_result.json"
        mat_path = case_dir / "results" / "matlab_result.json"
        report = {"case": item["case"], "ok": False, "issues": [], "checks": {}}
        if not py_path.exists() or not mat_path.exists():
            report["issues"].append("missing Python or MATLAB result")
        else:
            py = json.loads(py_path.read_text(encoding="utf-8"))["scuc"]
            mat = json.loads(mat_path.read_text(encoding="utf-8"))["scuc"]
            po, mo = py.get("obj"), mat.get("obj")
            report["checks"].update(
                status_py=py.get("status"),
                status_mat=mat.get("status"),
                obj_py=po,
                obj_mat=mo,
            )
            if po is None or mo is None:
                report["issues"].append("one solver returned no incumbent")
            else:
                rel = abs(float(po) - float(mo)) / max(1.0, abs(float(po)), abs(float(mo)))
                allowed = max(
                    1e-6,
                    1.05 * max(float(py.get("mip_gap") or 0), float(mat.get("mip_gap") or 0)),
                )
                report["checks"]["obj_rel_diff"] = rel
                report["checks"]["allowed_obj_rel_diff"] = allowed
                if rel > allowed:
                    report["issues"].append(
                        f"objective relative difference {rel:.3e} exceeds {allowed:.3e}"
                    )
                bal = max(
                    float(py.get("max_balance_residual_MW") or 0),
                    float(mat.get("max_balance_residual_MW") or 0),
                )
                report["checks"]["max_balance_residual_MW"] = bal
                if bal > 1e-3:
                    report["issues"].append("balance residual exceeds 1e-3 MW")
            report["ok"] = not report["issues"]
        (case_dir / "results" / "comparison.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        passed += int(report["ok"])
        print(f"{item['case']}: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"summary: {passed}/{len(manifest)} PASS")
    return 0 if passed == len(manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
