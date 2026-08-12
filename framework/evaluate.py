"""Unified evaluate() over results/python_result.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Constraint residuals only. Estimation error vs synthetic truth (e.g. SE
# max_theta_error_rad) is not a feasibility violation.
POWER_KEYS = (
    "max_power_balance_MW",
    "max_flow_equation_MW",
    "max_thermal_violation_MW",
    "max_generator_bound_MW",
    "max_balance_MW",
    "max_thermal_MW",
)
INT_KEYS = ("max_integer_violation", "max_integrality")

DEFAULT_POWER_TOL = 1e-4
DEFAULT_INT_TOL = 1e-6

_BLOCK_KEYS = (
    "ots",
    "ed",
    "mld",
    "scuc",
    "uc",
    "dnr",
    "smartds",
    "scacopf",
    "pmu",
    "se",
    "tep",
    "cem",
    "ht",
    "maint",
    "market",
    "bid",
    "restore",
    "island",
    "ops",
    "interdiction",
    "ieg",
    "rts_scuc",
    "dcopf",
)


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def primary_block(result: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    for key in _BLOCK_KEYS:
        block = result.get(key)
        if isinstance(block, dict) and ("status" in block or "obj" in block):
            if key == "dcopf" and isinstance(result.get("ots"), dict):
                continue
            return key, block
    for key, block in result.items():
        if isinstance(block, dict) and "status" in block:
            return str(key), block
    return None, {}


def evaluate(case_dir: str | Path, result_path: str | Path | None = None) -> dict[str, Any]:
    """Score an existing result. Does not re-solve.

    Returns passed / status / obj / residuals / violations.
    """
    case = Path(case_dir).resolve()
    cfg_path = case / "data" / "config.json"
    config = _load_json(cfg_path) or {}
    rpath = Path(result_path) if result_path else case / "results" / "python_result.json"
    result = _load_json(rpath)
    out: dict[str, Any] = {
        "case": case.name,
        "path": str(case),
        "result_path": str(rpath),
        "passed": False,
        "status": None,
        "obj": None,
        "block": None,
        "residuals": {},
        "violations": [],
        "reason": None,
        "solve_tier": config.get("solve_tier"),
        "base_problem": config.get("base_problem"),
    }
    if result is None:
        if config.get("solve_tier") == "skip" or config.get("problem") == "meta":
            out["status"] = "SKIP"
            out["passed"] = True
            out["reason"] = "skip_or_meta_no_result"
            return out
        out["reason"] = "missing_result"
        return out

    name, block = primary_block(result)
    out["block"] = name
    status = block.get("status") or result.get("status")
    obj = block.get("obj") if "obj" in block else result.get("obj")
    out["status"] = status
    out["obj"] = obj

    residuals: dict[str, float] = {}
    extra_keys = ("max_theta_error_rad", "max_angle_error_rad")
    for key in POWER_KEYS + INT_KEYS + extra_keys:
        if key in block and isinstance(block[key], (int, float)):
            residuals[key] = float(block[key])
        elif key in result and isinstance(result[key], (int, float)):
            residuals[key] = float(result[key])
    out["residuals"] = residuals

    violations: list[str] = []
    for key, val in residuals.items():
        if key in POWER_KEYS and abs(val) > DEFAULT_POWER_TOL:
            violations.append(f"{key}={val}")
        if key in INT_KEYS and abs(val) > DEFAULT_INT_TOL:
            violations.append(f"{key}={val}")

    explicit = block.get("validation_passed")
    if explicit is None and isinstance(result.get("validation"), dict):
        explicit = result["validation"].get("passed")

    ok_status = status in {None, "OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT", "SKIP", "SKIPPED"}
    if status in {"INFEASIBLE", "INF_OR_UNBD", "NUMERIC", "ERROR"}:
        ok_status = False
        violations.append(f"status={status}")

    if explicit is False:
        violations.append("validation_passed=false")

    if obj is None and status not in {"SKIP", "SKIPPED"} and config.get("solve_tier") != "skip":
        violations.append("obj=None")

    out["violations"] = violations
    out["passed"] = ok_status and not violations
    if not out["passed"]:
        out["reason"] = ";".join(violations) or "failed"
    else:
        out["reason"] = "ok"
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        sys.stderr.write("usage: evaluate.py <case_dir> [<case_dir> ...]\n")
        return 2
    fail = 0
    for arg in args:
        ev = evaluate(arg)
        flag = "PASS" if ev["passed"] else "FAIL"
        print(
            f"[{ev['case']}] {flag} status={ev['status']} obj={ev['obj']} "
            f"reason={ev['reason']}"
        )
        if not ev["passed"]:
            fail += 1
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
