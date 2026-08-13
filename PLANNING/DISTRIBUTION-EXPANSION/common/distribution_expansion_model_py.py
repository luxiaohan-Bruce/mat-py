"""Radial distribution expansion with LinDistFlow physics and spanning-tree radiality."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


POWER_TOL = 1e-4
VOLT_TOL = 1e-6
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


def _all_branches(network: dict[str, Any]) -> list[dict[str, Any]]:
    existing = [{**branch, "candidate": False} for branch in network.get("branches") or []]
    candidates = [{**branch, "candidate": True} for branch in network.get("ne_branches") or []]
    return existing + candidates


def solve_distribution_expansion(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    buses = network["buses"]
    branches = _all_branches(network)
    root = int(network["root_bus"])
    base = float(network.get("baseMVA", 1.0))
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    params = config.get("gurobi_parameters", {})

    model = gp.Model("distribution_expansion")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-6)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 120.0)))

    built = {}
    for ell, branch in enumerate(branches):
        if branch["candidate"]:
            built[ell] = model.addVar(vtype=GRB.BINARY, name=f"build_{ell}")
        else:
            built[ell] = model.addVar(lb=1.0, ub=1.0, name=f"existing_{ell}")
    p_flow = model.addVars(len(branches), lb=-GRB.INFINITY, name="P_MW")
    q_flow = model.addVars(len(branches), lb=-GRB.INFINITY, name="Q_MVAr")
    commodity = model.addVars(len(branches), lb=-GRB.INFINITY, name="radial_flow")
    v_sq = model.addVars(len(buses), lb=0.0, name="Vsq_pu")
    p_sub = model.addVar(lb=-GRB.INFINITY, name="Psub_MW")
    q_sub = model.addVar(lb=-GRB.INFINITY, name="Qsub_MVAr")

    for bi, bus in enumerate(buses):
        v_sq[bi].LB = float(bus.get("Vmin", 0.95)) ** 2
        v_sq[bi].UB = float(bus.get("Vmax", 1.05)) ** 2
    root_pos = bus_pos[root]
    v_sq[root_pos].LB = 1.0
    v_sq[root_pos].UB = 1.0

    substation_price = float(network.get("substation_price_per_MWh", 40.0))
    objective = substation_price * p_sub
    for ell, branch in enumerate(branches):
        if branch["candidate"]:
            objective += float(branch.get("invest_cost", 0.0)) * built[ell]
        smax = float(branch.get("smax_MVA", 10.0))
        p_flow[ell].LB = -smax
        p_flow[ell].UB = smax
        q_flow[ell].LB = -smax
        q_flow[ell].UB = smax
        model.addConstr(p_flow[ell] <= smax * built[ell], name=f"p_pos_{ell}")
        model.addConstr(p_flow[ell] >= -smax * built[ell], name=f"p_neg_{ell}")
        model.addConstr(q_flow[ell] <= smax * built[ell], name=f"q_pos_{ell}")
        model.addConstr(q_flow[ell] >= -smax * built[ell], name=f"q_neg_{ell}")
        model.addQConstr(
            p_flow[ell] * p_flow[ell] + q_flow[ell] * q_flow[ell] <= smax * smax * built[ell],
            name=f"smax_{ell}",
        )
        model.addConstr(commodity[ell] <= (len(buses) - 1) * built[ell], name=f"rad_pos_{ell}")
        model.addConstr(commodity[ell] >= -(len(buses) - 1) * built[ell], name=f"rad_neg_{ell}")
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        drop = 2.0 * (float(branch["r_pu"]) * p_flow[ell] + float(branch["x_pu"]) * q_flow[ell]) / base
        big_m = 4.0
        model.addConstr(v_sq[j] <= v_sq[i] - drop + big_m * (1.0 - built[ell]), name=f"vdrop_hi_{ell}")
        model.addConstr(v_sq[j] >= v_sq[i] - drop - big_m * (1.0 - built[ell]), name=f"vdrop_lo_{ell}")
    model.addConstr(gp.quicksum(built[ell] for ell in range(len(branches))) == len(buses) - 1, name="tree_cardinality")

    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        p_out = gp.quicksum(
            p_flow[ell] if int(branch["fbus"]) == bus_id else -p_flow[ell]
            for ell, branch in enumerate(branches)
            if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
        )
        q_out = gp.quicksum(
            q_flow[ell] if int(branch["fbus"]) == bus_id else -q_flow[ell]
            for ell, branch in enumerate(branches)
            if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
        )
        inject_p = p_sub if bus_id == root else 0.0
        inject_q = q_sub if bus_id == root else 0.0
        model.addConstr(inject_p - float(bus.get("Pd", 0.0)) == p_out, name=f"p_bal_{bus_id}")
        model.addConstr(inject_q - float(bus.get("Qd", 0.0)) == q_out, name=f"q_bal_{bus_id}")
        rad_out = gp.quicksum(
            commodity[ell] if int(branch["fbus"]) == bus_id else -commodity[ell]
            for ell, branch in enumerate(branches)
            if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
        )
        if bus_id == root:
            model.addConstr(rad_out == len(buses) - 1, name="radial_root")
        else:
            model.addConstr(rad_out == -1.0, name=f"radial_{bus_id}")
    model.setObjective(objective, GRB.MINIMIZE)

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    if model.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "validation_passed": False}

    built_x = [float(built[ell].X) for ell in range(len(branches))]
    p_mw = [float(p_flow[ell].X) for ell in range(len(branches))]
    q_mvar = [float(q_flow[ell].X) for ell in range(len(branches))]
    vsq = [float(v_sq[i].X) for i in range(len(buses))]
    psub = float(p_sub.X)
    qsub = float(q_sub.X)
    max_balance = 0.0
    max_volt = 0.0
    max_thermal = 0.0
    max_int = 0.0
    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        p_out = 0.0
        q_out = 0.0
        for ell, branch in enumerate(branches):
            if built_x[ell] < 0.5:
                continue
            if int(branch["fbus"]) == bus_id:
                p_out += p_mw[ell]
                q_out += q_mvar[ell]
            elif int(branch["tbus"]) == bus_id:
                p_out -= p_mw[ell]
                q_out -= q_mvar[ell]
        inject_p = psub if bus_id == root else 0.0
        inject_q = qsub if bus_id == root else 0.0
        max_balance = max(
            max_balance,
            abs(inject_p - float(bus.get("Pd", 0.0)) - p_out),
            abs(inject_q - float(bus.get("Qd", 0.0)) - q_out),
        )
    for ell, branch in enumerate(branches):
        max_int = max(max_int, min(abs(built_x[ell]), abs(built_x[ell] - 1.0)))
        smax = float(branch.get("smax_MVA", 10.0))
        if built_x[ell] < 0.5:
            max_thermal = max(max_thermal, abs(p_mw[ell]), abs(q_mvar[ell]))
            continue
        max_thermal = max(max_thermal, max(0.0, (p_mw[ell] ** 2 + q_mvar[ell] ** 2) ** 0.5 - smax))
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        expected = vsq[i] - 2.0 * (float(branch["r_pu"]) * p_mw[ell] + float(branch["x_pu"]) * q_mvar[ell]) / base
        max_volt = max(max_volt, abs(vsq[j] - expected))
    built_count = sum(1 for value in built_x if value > 0.5)
    tree_ok = built_count == len(buses) - 1
    recomputed = substation_price * psub + sum(
        float(branch.get("invest_cost", 0.0)) * built_x[ell]
        for ell, branch in enumerate(branches)
        if branch["candidate"]
    )
    passed = (
        status == "OPTIMAL"
        and max_balance <= POWER_TOL
        and max_volt <= VOLT_TOL
        and max_thermal <= POWER_TOL
        and max_int <= BOUND_TOL
        and tree_ok
    )
    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime": runtime,
        "Psub_MW": psub,
        "Qsub_MVAr": qsub,
        "build": built_x,
        "P_MW": p_mw,
        "Q_MVAr": q_mvar,
        "Vsq_pu": vsq,
        "n_built": built_count,
        "cost_recomputed": recomputed,
        "max_power_balance_MW": max_balance,
        "max_voltage_equation_pu": max_volt,
        "max_thermal_violation_MW": max_thermal,
        "max_integer_violation": max_int,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_distribution_expansion(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "base_problem": "distribution_expansion",
        "problem": "distribution_expansion",
        "dist_exp": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
