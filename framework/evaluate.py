"""Unified evaluate() over results/python_result.json."""

from __future__ import annotations

import json
import math
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
    "acopf",
    "economic_dispatch",
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
    "demand_response",
    "storage_scheduling",
    "dist_exp",
    "microgrid",
    "unbalanced_dopf",
    "glb",
    "green_llm",
    "dcflex",
    "gcep",
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
        "maturity": config.get("maturity"),
        "validation_scope": config.get("validation_scope"),
        "physics_validated": config.get("physics_validated"),
        "claim": "solver_and_residual_validation",
    }
    problem = str(config.get("problem") or "")
    is_meta = problem == "meta" or problem.endswith("_meta")
    if config.get("solve_tier") == "skip" or is_meta:
        out["status"] = "SKIP"
        out["passed"] = True
        out["claim"] = "data_only" if config.get("maturity") == "data_only" else "configured_skip"
        out["reason"] = "configured_skip_or_meta"
        return out
    result = _load_json(rpath)
    if result is None:
        out["reason"] = "missing_result"
        return out

    name, block = primary_block(result)
    out["block"] = name
    status = block.get("status") or result.get("status")
    if "obj" in block:
        obj = block.get("obj")
    elif "objective" in block:
        obj = block.get("objective")
    else:
        obj = result.get("obj", result.get("objective"))
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

    if problem == "aidc39":
        # Recompute from the saved full schedule; never trust a cached PASS.
        import importlib
        import importlib.util

        package_name = "_aidc39_verification"
        package_dir = Path(__file__).resolve().parents[1] / "DATACENTER" / "AIDC-39" / "common"
        try:
            if package_name not in sys.modules:
                spec = importlib.util.spec_from_file_location(
                    package_name, package_dir / "__init__.py", submodule_search_locations=[str(package_dir)]
                )
                if spec is None or spec.loader is None:
                    raise ImportError("AIDC verifier is unavailable")
                package = importlib.util.module_from_spec(spec)
                sys.modules[package_name] = package
                spec.loader.exec_module(package)
            verifier = importlib.import_module(package_name + ".verify")
            certificate = verifier.revalidate_saved(case, rpath)
            out["independent_validation"] = certificate
            if not certificate.get("passed"):
                violations.append("aidc39 independent validation failed: " + str(certificate.get("violations")))
            if block.get("validation_passed") is not True:
                violations.append("aidc39 missing successful original validation")
        except Exception as exc:
            violations.append(f"aidc39 verification error: {exc}")

    if problem in {"linearized_scacopf", "linearized_scacots"}:
        features = config.get("features")
        expected_n_cont = features.get("n_contingency") if isinstance(features, dict) else None
        actual_n_cont = block.get("n_cont")
        if (
            not isinstance(expected_n_cont, int)
            or isinstance(expected_n_cont, bool)
            or not isinstance(actual_n_cont, int)
            or isinstance(actual_n_cont, bool)
            or actual_n_cont != expected_n_cont
        ):
            violations.append(
                f"n_cont={actual_n_cont!r} expected_n_contingency={expected_n_cont!r}"
            )
        variant = config.get("variant") if isinstance(config.get("variant"), dict) else {}
        allow_nse = variant.get("recourse") == "corrective_limited_with_nse"
        for key, tolerance in (("load_shed_MW", 1e-4), ("flow_slack_pu", 1e-6)):
            value = block.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
                residuals[key] = float(value)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(float(value))
            ):
                violations.append(f"{key}={value!r}")
            elif abs(float(value)) > tolerance:
                if key == "load_shed_MW" and allow_nse:
                    continue
                violations.append(f"{key}={value}")
        out["residuals"] = residuals

    explicit = block.get("validation_passed")
    if explicit is None and isinstance(result.get("validation"), dict):
        explicit = result["validation"].get("passed")

    ok_status = status in {
        None,
        "OPTIMAL",
        "SUBOPTIMAL",
        "TIME_LIMIT",
        "INTERRUPTED",
        "SKIP",
        "SKIPPED",
    }
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
        if config.get("validation_scope") == "structural_only":
            out["claim"] = "structural_only"
            out["reason"] = "structural_only_not_physics_validated"
        elif status in {"SUBOPTIMAL", "TIME_LIMIT", "INTERRUPTED"}:
            if explicit is True:
                out["claim"] = "validated_feasible_incumbent"
                out["reason"] = "validated_feasible_incumbent_not_optimal"
            else:
                out["claim"] = "solver_feasible_incumbent"
                out["reason"] = "solver_feasible_incumbent_not_independently_validated"
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
        if ev["status"] == "SKIP":
            flag = "SKIP"
        elif ev["passed"] and ev.get("claim") == "structural_only":
            flag = "STRUCTURAL_ONLY"
        elif ev["passed"] and ev.get("claim") == "validated_feasible_incumbent":
            flag = "VALIDATED_INCUMBENT"
        elif ev["passed"] and ev.get("claim") == "solver_feasible_incumbent":
            flag = "FEASIBLE_INCUMBENT"
        else:
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
