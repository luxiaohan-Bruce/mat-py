"""Copperplate microgrid / VPP energy management with optional grid exchange."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


POWER_TOL = 1e-4
BOUND_TOL = 1e-6
ENERGY_TOL = 1e-4


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


def solve_microgrid(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    gens = network["gens"]
    storage = network.get("storage") or []
    renewable = network.get("renewable") or []
    profile = [float(x) for x in network["demand_profile"]]
    horizon = len(profile)
    dt = float(network.get("dt_hour", 1.0))
    base_demand = sum(float(bus.get("Pd", 0.0)) for bus in network["buses"])
    demand = [base_demand * multiplier for multiplier in profile]
    grid = network.get("grid") or {}
    islanded = bool(grid.get("islanded", False))
    import_max = 0.0 if islanded else float(grid.get("import_max_MW", 0.0))
    export_max = 0.0 if islanded else float(grid.get("export_max_MW", 0.0))
    import_price = float(grid.get("import_price_per_MWh", 0.0))
    export_price = float(grid.get("export_price_per_MWh", 0.0))
    params = config.get("gurobi_parameters", {})

    model = gp.Model("microgrid")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-6)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 120.0)))

    pg = model.addVars(len(gens), horizon, lb=-GRB.INFINITY, name="Pg_MW")
    p_ren = model.addVars(len(renewable), horizon, lb=0.0, name="Pren_MW")
    pch = model.addVars(len(storage), horizon, lb=0.0, name="Pch_MW")
    pdis = model.addVars(len(storage), horizon, lb=0.0, name="Pdis_MW")
    soc = model.addVars(len(storage), horizon, lb=0.0, name="SOC_MWh")
    p_imp = model.addVars(horizon, lb=0.0, ub=import_max, name="P_import_MW")
    p_exp = model.addVars(horizon, lb=0.0, ub=export_max, name="P_export_MW")
    objective = gp.QuadExpr()

    for s, unit in enumerate(storage):
        pmax = float(unit["Pmax_MW"])
        emax = float(unit["Emax_MWh"])
        emin = float(unit.get("Emin_MWh", 0.0))
        for t in range(horizon):
            pch[s, t].UB = pmax
            pdis[s, t].UB = pmax
            soc[s, t].LB = emin
            soc[s, t].UB = emax

    for t, load in enumerate(demand):
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
        for r, unit in enumerate(renewable):
            available = float(unit["Pmax_MW"]) * float(unit["profile"][t])
            p_ren[r, t].UB = available
        objective += dt * (import_price * p_imp[t] - export_price * p_exp[t])
        model.addConstr(
            gp.quicksum(pg[g, t] for g in range(len(gens)))
            + gp.quicksum(p_ren[r, t] for r in range(len(renewable)))
            + gp.quicksum(pdis[s, t] - pch[s, t] for s in range(len(storage)))
            + p_imp[t]
            - p_exp[t]
            == load,
            name=f"balance_{t}",
        )
    for s, unit in enumerate(storage):
        eta_c = float(unit["eta_c"])
        eta_d = float(unit["eta_d"])
        energy0 = float(unit["E0_MWh"])
        for t in range(horizon):
            previous = energy0 if t == 0 else soc[s, t - 1]
            model.addConstr(
                soc[s, t] == previous + dt * (eta_c * pch[s, t] - pdis[s, t] / eta_d),
                name=f"soc_{s}_{t}",
            )
        model.addConstr(soc[s, horizon - 1] == energy0, name=f"cyclic_soc_{s}")
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
            "islanded": islanded,
            "validation_passed": False,
        }

    pg_mw = [[float(pg[g, t].X) for t in range(horizon)] for g in range(len(gens))]
    pren_mw = [[float(p_ren[r, t].X) for t in range(horizon)] for r in range(len(renewable))]
    pch_mw = [[float(pch[s, t].X) for t in range(horizon)] for s in range(len(storage))]
    pdis_mw = [[float(pdis[s, t].X) for t in range(horizon)] for s in range(len(storage))]
    soc_mwh = [[float(soc[s, t].X) for t in range(horizon)] for s in range(len(storage))]
    imp_mw = [float(p_imp[t].X) for t in range(horizon)]
    exp_mw = [float(p_exp[t].X) for t in range(horizon)]
    max_balance = 0.0
    max_bound = 0.0
    max_energy = 0.0
    recomputed = 0.0
    for t, load in enumerate(demand):
        residual = abs(
            sum(pg_mw[g][t] for g in range(len(gens)))
            + sum(pren_mw[r][t] for r in range(len(renewable)))
            + sum(pdis_mw[s][t] - pch_mw[s][t] for s in range(len(storage)))
            + imp_mw[t]
            - exp_mw[t]
            - load
        )
        max_balance = max(max_balance, residual)
        recomputed += dt * (import_price * imp_mw[t] - export_price * exp_mw[t])
        for g, gen in enumerate(gens):
            lower, upper = _bounds(gen)
            value = pg_mw[g][t]
            max_bound = max(max_bound, lower - value, value - upper, 0.0)
            recomputed += dt * _cost(gen, value)
    for s, unit in enumerate(storage):
        eta_c = float(unit["eta_c"])
        eta_d = float(unit["eta_d"])
        previous = float(unit["E0_MWh"])
        for t in range(horizon):
            expected = previous + dt * (eta_c * pch_mw[s][t] - pdis_mw[s][t] / eta_d)
            max_energy = max(max_energy, abs(soc_mwh[s][t] - expected))
            previous = soc_mwh[s][t]
        max_energy = max(max_energy, abs(soc_mwh[s][-1] - float(unit["E0_MWh"])))
    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime": runtime,
        "islanded": islanded,
        "T": horizon,
        "dt_hour": dt,
        "demand_MW": demand,
        "Pg_MW": pg_mw,
        "Pren_MW": pren_mw,
        "Pch_MW": pch_mw,
        "Pdis_MW": pdis_mw,
        "SOC_MWh": soc_mwh,
        "P_import_MW": imp_mw,
        "P_export_MW": exp_mw,
        "cost_recomputed": recomputed,
        "max_power_balance_MW": max_balance,
        "max_generator_bound_MW": max_bound,
        "max_storage_energy_MWh": max_energy,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "validation_passed": (
            max_balance <= POWER_TOL and max_bound <= BOUND_TOL and max_energy <= ENERGY_TOL
        ),
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_microgrid(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "base_problem": "microgrid",
        "problem": "microgrid",
        "microgrid": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
