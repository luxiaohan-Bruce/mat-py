#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    passed = 0
    checked = 0
    for item in manifest:
        if item.get("solve_tier") == "skip":
            continue
        case_dir = ROOT / item["case"]
        py_path = case_dir / "results" / "python_result.json"
        mat_path = case_dir / "results" / "matlab_result.json"
        report = {"case": item["case"], "ok": False, "issues": [], "checks": {}}
        checked += 1
        if not py_path.exists() or not mat_path.exists():
            report["issues"].append("missing result")
        else:
            py = json.loads(py_path.read_text())["scacopf"]
            mat = json.loads(mat_path.read_text())["scacopf"]
            po, mo = py.get("obj"), mat.get("obj")
            report["checks"].update(obj_py=po, obj_mat=mo, status_py=py.get("status"), status_mat=mat.get("status"))
            if po is None or mo is None:
                report["issues"].append("no incumbent")
            else:
                rel = abs(float(po) - float(mo)) / max(1.0, abs(float(po)), abs(float(mo)))
                allowed = max(1e-5, 1.05 * max(float(py.get("mip_gap") or 0), float(mat.get("mip_gap") or 0)))
                report["checks"]["obj_rel_diff"] = rel
                report["checks"]["allowed"] = allowed
                if rel > allowed:
                    report["issues"].append(f"obj rel {rel:.3e} > {allowed:.3e}")
            report["ok"] = not report["issues"]
        (case_dir / "results" / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
        passed += int(report["ok"])
        print(f"{item['case']}: {'PASS' if report['ok'] else 'FAIL'}")
    print(f"summary: {passed}/{checked} PASS (skip excluded)")
    return 0 if passed == checked else 1


if __name__ == "__main__":
    raise SystemExit(main())
