"""Equity-aware geographical load balancing (gurobipy).

Mirrors Ren-Research/Environmentally-Equitable-AI utils/solve.py offline_solver.

Decision x[i,j,t] = workload from gateway j processed at DC i in hour t
(in official DC-capacity units, max_cap = 1).

min  l0 * sum price[i,t] x[i,j,t]
   + l1 * z_w + l2 * z_c          if equity_type == MAX
   + l1 * mean_i Water_i
   + l2 * mean_i Carbon_i         if equity_type == AVG

s.t. sum_j x[i,j,t] <= max_cap
     sum_i x[i,j,t] == workload[j,t]
     x[i,j,t] = 0 if mask[i,j] = 0
     x >= 0
     Water_i  = sum_{j,t} water[i,t] x[i,j,t]
     Carbon_i = sum_{j,t} carbon[i,t] x[i,j,t]
     MAX: z_w >= Water_i, z_c >= Carbon_i
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from result_io import load_case, write_result  # noqa: E402
from tolerances import solver_params_from_config  # noqa: E402

DEMAND_TOL = 1e-6
CAP_TOL = 1e-6
COST_TOL = 1e-6


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _mat(rows: Any) -> list[list[float]]:
    return [[float(v) for v in row] for row in rows]


def solve_glb(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    n_dc = int(network["n_dc"])
    n_gw = int(network["n_gateway"])
    T = int(network["horizon"])
    max_cap = float(network["max_cap"])
    l0 = float(network["l0_energy"])
    l1 = float(network["l1_water"])
    l2 = float(network["l2_carbon"])
    equity = str(network.get("equity_type", "MAX")).upper()
    price = _mat(network["price_usd_per_mwh"])
    carbon = _mat(network["carbon_kg_per_kwh"])
    water = _mat(network["water_l_per_kwh"])
    demand = _mat(network["workload"])
    mask = [[int(v) for v in row] for row in network["mask"]]
    locations = [str(s) for s in network["locations"]]
    params = solver_params_from_config(config)

    m = gp.Model("eeai_glb")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    x: dict[tuple[int, int, int], gp.Var] = {}
    for i in range(n_dc):
        for j in range(n_gw):
            if mask[i][j] == 0:
                continue
            for t in range(T):
                x[i, j, t] = m.addVar(lb=0.0, name=f"x_{i}_{j}_{t}")

    for i in range(n_dc):
        for t in range(T):
            m.addConstr(
                gp.quicksum(x[i, j, t] for j in range(n_gw) if (i, j, t) in x) <= max_cap,
                name=f"cap_{i}_{t}",
            )
    for j in range(n_gw):
        for t in range(T):
            m.addConstr(
                gp.quicksum(x[i, j, t] for i in range(n_dc) if (i, j, t) in x) == demand[j][t],
                name=f"dem_{j}_{t}",
            )

    energy = gp.quicksum(
        price[i][t] * x[i, j, t] for (i, j, t) in x
    )
    water_i = [
        gp.quicksum(water[i][t] * x[i, j, t] for j in range(n_gw) for t in range(T) if (i, j, t) in x)
        for i in range(n_dc)
    ]
    carbon_i = [
        gp.quicksum(carbon[i][t] * x[i, j, t] for j in range(n_gw) for t in range(T) if (i, j, t) in x)
        for i in range(n_dc)
    ]

    if equity == "MAX":
        z_w = m.addVar(lb=0.0, name="z_water")
        z_c = m.addVar(lb=0.0, name="z_carbon")
        for i in range(n_dc):
            m.addConstr(water_i[i] <= z_w, name=f"eq_w_{i}")
            m.addConstr(carbon_i[i] <= z_c, name=f"eq_c_{i}")
        m.setObjective(l0 * energy + l1 * z_w + l2 * z_c, GRB.MINIMIZE)
    elif equity == "AVG":
        m.setObjective(
            l0 * energy
            + (l1 / n_dc) * gp.quicksum(water_i)
            + (l2 / n_dc) * gp.quicksum(carbon_i),
            GRB.MINIMIZE,
        )
    else:
        raise ValueError(f"unknown equity_type {equity}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    load_dc_t = [[0.0] * T for _ in range(n_dc)]
    load_gw_t = [[0.0] * T for _ in range(n_gw)]
    obj_val = None
    obj_bound = None
    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        try:
            obj_bound = float(m.ObjBound)
        except Exception:
            obj_bound = obj_val
        for (i, j, t), var in x.items():
            v = float(var.X)
            load_dc_t[i][t] += v
            load_gw_t[j][t] += v

    residual = validate_glb(
        network,
        load_dc_t,
        load_gw_t,
        obj_val,
        status,
    )
    out = {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": 0.0,
        "runtime": runtime,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "equity_type": equity,
        "locations": locations,
        "load_dc_t": load_dc_t,
        "load_by_dc": [sum(row) for row in load_dc_t],
        **residual,
    }
    return out


def validate_glb(
    network: dict,
    load_dc_t: list[list[float]],
    load_gw_t: list[list[float]],
    obj: float | None,
    status: str,
) -> dict[str, Any]:
    n_dc = int(network["n_dc"])
    n_gw = int(network["n_gateway"])
    T = int(network["horizon"])
    max_cap = float(network["max_cap"])
    l0 = float(network["l0_energy"])
    l1 = float(network["l1_water"])
    l2 = float(network["l2_carbon"])
    equity = str(network.get("equity_type", "MAX")).upper()
    price = _mat(network["price_usd_per_mwh"])
    carbon = _mat(network["carbon_kg_per_kwh"])
    water = _mat(network["water_l_per_kwh"])
    demand = _mat(network["workload"])

    max_demand = 0.0
    for j in range(n_gw):
        for t in range(T):
            max_demand = max(max_demand, abs(load_gw_t[j][t] - demand[j][t]))

    max_cap_vio = 0.0
    energy_by_dc = [0.0] * n_dc
    water_by_dc = [0.0] * n_dc
    carbon_by_dc = [0.0] * n_dc
    for i in range(n_dc):
        for t in range(T):
            p = load_dc_t[i][t]
            max_cap_vio = max(max_cap_vio, max(0.0, p - max_cap))
            energy_by_dc[i] += price[i][t] * p
            water_by_dc[i] += water[i][t] * p
            carbon_by_dc[i] += carbon[i][t] * p

    energy_cost = sum(energy_by_dc)
    water_peak = max(water_by_dc) if water_by_dc else 0.0
    carbon_peak = max(carbon_by_dc) if carbon_by_dc else 0.0
    water_mean = sum(water_by_dc) / n_dc
    carbon_mean = sum(carbon_by_dc) / n_dc
    if equity == "MAX":
        cost = l0 * energy_cost + l1 * water_peak + l2 * carbon_peak
    else:
        cost = l0 * energy_cost + l1 * water_mean + l2 * carbon_mean

    cost_gap = None if obj is None else abs(cost - obj)
    passed = (
        status in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT")
        and obj is not None
        and max_demand <= DEMAND_TOL
        and max_cap_vio <= CAP_TOL
        and (cost_gap is None or cost_gap <= max(0.01, COST_TOL * max(1.0, abs(obj))))
    )
    water_par = water_peak / water_mean if water_mean > 1e-12 else None
    carbon_par = carbon_peak / carbon_mean if carbon_mean > 1e-12 else None
    return {
        "max_demand_violation": max_demand,
        "max_capacity_violation": max_cap_vio,
        "energy_cost": energy_cost,
        "water_peak": water_peak,
        "carbon_peak": carbon_peak,
        "water_mean": water_mean,
        "carbon_mean": carbon_mean,
        "water_par": water_par,
        "carbon_par": carbon_par,
        "energy_by_dc": energy_by_dc,
        "water_by_dc": water_by_dc,
        "carbon_by_dc": carbon_by_dc,
        "cost_recomputed": cost,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_glb(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": config.get("problem", "glb"),
        "base_problem": config.get("base_problem", "datacenter_glb"),
        "glb": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "case001_eeai10_24h_equity_full"
    r = run_case(d, quiet=True)
    e = r["glb"]
    print(
        f"[{r['case']}] status={e['status']} obj={e['obj']} "
        f"energy={e['energy_cost']:.4f} water_peak={e['water_peak']:.4f} "
        f"carbon_peak={e['carbon_peak']:.4f} valid={e['validation_passed']}"
    )
