"""Multi-period copperplate dispatch with interruptible and shiftable demand."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


POWER_TOL = 1e-4
BOUND_TOL = 1e-6


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


def _cost(gen: dict[str, Any], pg: float) -> float:
    if int(gen.get("status", 1)) == 0:
        return 0.0
    return float(gen.get("c2", 0.0)) * pg * pg + float(gen.get("c1", 0.0)) * pg + float(gen.get("c0", 0.0))


def solve_demand_response(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    gens = network["gens"]
    profile = [float(x) for x in network["demand_profile"]]
    horizon = len(profile)
    dt = float(network.get("dt_hour", 1.0))
    base_demand = sum(float(bus.get("Pd", 0.0)) for bus in network["buses"])
    demand = [base_demand * multiplier for multiplier in profile]
    spec = network["demand_response"]
    interruptible = float(spec["interruptible_frac"])
    shiftable = float(spec["shiftable_frac"])
    voll = float(spec["voll_per_MWh"])
    params = config.get("gurobi_parameters", {})

    model = gp.Model("demand_response")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-6)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 120.0)))

    pg = model.addVars(len(gens), horizon, lb=-GRB.INFINITY, name="Pg_MW")
    shed = model.addVars(horizon, lb=0.0, name="P_shed_MW")
    shift_down = model.addVars(horizon, lb=0.0, name="P_shift_down_MW")
    shift_up = model.addVars(horizon, lb=0.0, name="P_shift_up_MW")
    objective = gp.QuadExpr()
    for t, load in enumerate(demand):
        shed[t].UB = interruptible * load
        shift_down[t].UB = shiftable * load
        shift_up[t].UB = shiftable * load
        for g, gen in enumerate(gens):
            lower, upper = _bounds(gen)
            pg[g, t].LB = lower
            pg[g, t].UB = upper
            if int(gen.get("status", 1)) == 0:
                continue
            c2 = float(gen.get("c2", 0.0))
            if abs(c2) > 1e-12:
                objective += dt * c2 * pg[g, t] * pg[g, t]
            objective += dt * (float(gen.get("c1", 0.0)) * pg[g, t] + float(gen.get("c0", 0.0)))
        objective += dt * voll * shed[t]
        model.addConstr(
            gp.quicksum(pg[g, t] for g in range(len(gens))) + shed[t] + shift_down[t]
            == load + shift_up[t],
            name=f"balance_{t}",
        )
    model.addConstr(
        gp.quicksum(dt * shift_down[t] for t in range(horizon))
        == gp.quicksum(dt * shift_up[t] for t in range(horizon)),
        name="shift_energy_balance",
    )
    model.setObjective(objective, GRB.MINIMIZE)

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    if model.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "validation_passed": False,
        }

    pg_mw = [[float(pg[g, t].X) for t in range(horizon)] for g in range(len(gens))]
    shed_mw = [float(shed[t].X) for t in range(horizon)]
    down_mw = [float(shift_down[t].X) for t in range(horizon)]
    up_mw = [float(shift_up[t].X) for t in range(horizon)]
    max_balance = 0.0
    max_bound = 0.0
    recomputed = 0.0
    for t, load in enumerate(demand):
        residual = abs(sum(pg_mw[g][t] for g in range(len(gens))) + shed_mw[t] + down_mw[t] - load - up_mw[t])
        max_balance = max(max_balance, residual)
        recomputed += dt * voll * shed_mw[t]
        for g, gen in enumerate(gens):
            lower, upper = _bounds(gen)
            value = pg_mw[g][t]
            max_bound = max(max_bound, lower - value, value - upper, 0.0)
            recomputed += dt * _cost(gen, value)
    shift_mismatch = abs(sum(down_mw) - sum(up_mw)) * dt
    max_balance = max(max_balance, shift_mismatch)
    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime": runtime,
        "T": horizon,
        "dt_hour": dt,
        "demand_MW": demand,
        "Pg_MW": pg_mw,
        "P_shed_MW": shed_mw,
        "P_shift_down_MW": down_mw,
        "P_shift_up_MW": up_mw,
        "cost_recomputed": recomputed,
        "max_power_balance_MW": max_balance,
        "max_generator_bound_MW": max_bound,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "validation_passed": max_balance <= POWER_TOL and max_bound <= BOUND_TOL,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_demand_response(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "base_problem": "demand_response",
        "problem": "demand_response",
        "demand_response": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
