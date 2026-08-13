"""Single-period copperplate economic dispatch with Gurobi."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def _status_name(model: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(model.Status, str(model.Status))


def _bounds(gen: dict[str, Any]) -> tuple[float, float]:
    if int(gen.get("status", 1)) == 0:
        return 0.0, 0.0
    return float(gen["Pmin"]), float(gen["Pmax"])


def solve_economic_dispatch(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    buses = network["buses"]
    gens = network["gens"]
    demand_mw = sum(float(bus.get("Pd", 0.0)) for bus in buses)
    params = config.get("gurobi_parameters", {})

    model = gp.Model("copperplate_economic_dispatch")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-6)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 120.0)))

    pg = model.addVars(len(gens), lb=-GRB.INFINITY, name="Pg_MW")
    objective = gp.QuadExpr()
    has_quadratic_cost = False
    for idx, gen in enumerate(gens):
        lower, upper = _bounds(gen)
        pg[idx].LB = lower
        pg[idx].UB = upper
        if int(gen.get("status", 1)) == 0:
            continue
        c2 = float(gen.get("c2", 0.0))
        c1 = float(gen.get("c1", 0.0))
        c0 = float(gen.get("c0", 0.0))
        if abs(c2) > 1e-12:
            objective += c2 * pg[idx] * pg[idx]
            has_quadratic_cost = True
        objective += c1 * pg[idx] + c0
    model.setObjective(objective, GRB.MINIMIZE)
    balance = model.addConstr(
        gp.quicksum(pg[idx] for idx in range(len(gens))) == demand_mw,
        name="copperplate_balance",
    )

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    if model.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "demand_MW": demand_mw,
            "validation_passed": False,
        }

    pg_mw = [float(pg[idx].X) for idx in range(len(gens))]
    balance_residual = abs(sum(pg_mw) - demand_mw)
    bound_violation = 0.0
    recomputed_cost = 0.0
    for value, gen in zip(pg_mw, gens):
        lower, upper = _bounds(gen)
        bound_violation = max(bound_violation, lower - value, value - upper, 0.0)
        if int(gen.get("status", 1)) == 1:
            recomputed_cost += (
                float(gen.get("c2", 0.0)) * value * value
                + float(gen.get("c1", 0.0)) * value
                + float(gen.get("c0", 0.0))
            )
    try:
        system_lambda = float(balance.Pi)
    except (AttributeError, gp.GurobiError):
        system_lambda = None

    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime": runtime,
        "demand_MW": demand_mw,
        "Pg_MW": pg_mw,
        "system_lambda_per_MWh": system_lambda,
        "has_quadratic_cost": has_quadratic_cost,
        "max_balance_violation_MW": balance_residual,
        "max_generator_bound_violation_MW": bound_violation,
        "cost_recomputed": recomputed_cost,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "validation_passed": balance_residual <= 1e-4 and bound_violation <= 1e-6,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_economic_dispatch(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "base_problem": "economic_dispatch",
        "problem": "economic_dispatch",
        "economic_dispatch": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
