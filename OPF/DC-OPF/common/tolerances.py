"""Shared numerical tolerances for dual-ended acceptance (PLAM §9)."""

from __future__ import annotations

from typing import Any

DEFAULT_TOLERANCES: dict[str, float] = {
    "power_balance_mw": 1e-4,
    "flow_equation_mw": 1e-4,
    "thermal_mw": 1e-4,
    "generator_bound_mw": 1e-4,
    "angle_rad": 1e-7,
    "integrality": 1e-6,
    "obj_abs": 0.01,
    "obj_rel": 1e-7,
}


def objectives_close(
    a: float | None,
    b: float | None,
    *,
    abs_tol: float | None = None,
    rel_tol: float | None = None,
    mip_gap_a: float = 0.0,
    mip_gap_b: float = 0.0,
) -> tuple[bool, float]:
    """Return (ok, relative_diff). Allows gap-aware tolerance for MIP incumbents."""
    if a is None or b is None:
        return False, float("inf")
    fa, fb = float(a), float(b)
    abs_tol = DEFAULT_TOLERANCES["obj_abs"] if abs_tol is None else abs_tol
    rel_tol = DEFAULT_TOLERANCES["obj_rel"] if rel_tol is None else rel_tol
    denom = max(1.0, abs(fa), abs(fb))
    rel = abs(fa - fb) / denom
    allowed = max(rel_tol, 1.05 * max(float(mip_gap_a), float(mip_gap_b)))
    ok = abs(fa - fb) <= abs_tol or rel <= allowed
    return ok, rel


def solver_params_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Flatten gurobi_parameters + legacy flat keys."""
    gp = dict(config.get("gurobi_parameters") or {})
    return {
        "Seed": int(gp.get("Seed", config.get("seed", 1))),
        "Threads": int(gp.get("Threads", config.get("threads", 1))),
        "MIPGap": float(gp.get("MIPGap", config.get("mip_gap", 1e-6))),
        "TimeLimit": float(gp.get("TimeLimit", config.get("time_limit", 300))),
    }
