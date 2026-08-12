"""DC Maximum Load Delivery (gurobipy).

max  sum_i weight_i * Pd_i * x_i
s.t. 0 <= x_i <= 1 (load served fraction)
     DC balance with served load, DC flow, thermal, gen bounds
     Damaged branches/gens forced offline (status=0 or damage lists).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from dc_network import (  # noqa: E402
    bus_maps,
    branch_susceptance,
    gen_bounds_mw,
    is_zero_x,
    thermal_rate_mw,
)
from result_io import load_case, write_result  # noqa: E402
from tolerances import DEFAULT_TOLERANCES, solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
    }.get(m.Status, str(m.Status))


def solve_mld(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    params = solver_params_from_config(config)

    dmg_br = set(int(i) for i in (config.get("damaged_branches") or []))
    dmg_gen = set(int(i) for i in (config.get("damaged_gens") or []))  # 0-based

    m = gp.Model("dc_mld")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, name="Pg_MW")
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")
    x = m.addVars(nB, lb=0.0, ub=1.0, name="load_frac")  # served fraction

    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    # load weights (default 1.0)
    weights = config.get("load_weights") or {}
    w = [float(weights.get(str(bid), weights.get(bid, 1.0))) for bid in bus_ids]

    obj = gp.quicksum(
        w[bi] * float(buses[bi]["Pd"]) * x[bi] for bi in range(nB) if float(buses[bi]["Pd"]) > 0
    )
    m.setObjective(obj, GRB.MAXIMIZE)

    # MLD: allow offline dispatch (Pmin relaxed to 0) so pure load-shedding remains feasible.
    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        if g in dmg_gen or int(gen.get("status", 1)) == 0:
            lo, hi = 0.0, 0.0
        else:
            lo = 0.0  # relax Pmin
        Pg[g].LB = lo
        Pg[g].UB = hi

    for ell, br in enumerate(branches):
        bid = int(br["id"])
        offline = int(br.get("status", 1)) == 0 or bid in dmg_br
        if offline:
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addConstr(theta[i] - theta[j] == phi, name=f"th_eq_{ell}")
        else:
            bsus, phi = branch_susceptance(br)
            m.addConstr(
                f[ell] == base * bsus * (theta[i] - theta[j] - phi),
                name=f"phys_{ell}",
            )
        rate = thermal_rate_mw(br)
        if rate > 0:
            m.addConstr(f[ell] <= rate, name=f"fmax_{ell}")
            m.addConstr(f[ell] >= -rate, name=f"fmin_{ell}")

    for bi, bid in enumerate(bus_ids):
        Pd = float(buses[bi]["Pd"])
        gen_sum = gp.quicksum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        m.addConstr(gen_sum - Pd * x[bi] - out_f + in_f == 0.0, name=f"bal_{bid}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    load_frac = [0.0] * nB
    obj_val = None
    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        for g in range(nG):
            Pg_MW[g] = float(Pg[g].X)
        for i in range(nB):
            theta_deg[i] = math.degrees(float(theta[i].X))
            load_frac[i] = float(x[i].X)
        for ell in range(nL):
            flow_MW[ell] = float(f[ell].X)

    served = sum(float(buses[bi]["Pd"]) * load_frac[bi] for bi in range(nB))
    total_pd = sum(float(b["Pd"]) for b in buses)
    residual = _validate(network, config, Pg_MW, theta_deg, flow_MW, load_frac)
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": float(m.ObjBound) if m.SolCount > 0 else None,
        "mip_gap": 0.0,
        "runtime": runtime,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "load_frac": load_frac,
        "served_MW": served,
        "total_demand_MW": total_pd,
        "unserved_MW": total_pd - served,
        "damaged_branches": sorted(dmg_br),
        "damaged_gens": sorted(dmg_gen),
        "ref_bus": ref_bus,
        "baseMVA": base,
        **residual,
    }


def _validate(network, config, Pg_MW, theta_deg, flow_MW, load_frac) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    dmg_br = set(int(i) for i in (config.get("damaged_branches") or []))
    dmg_gen = set(int(i) for i in (config.get("damaged_gens") or []))
    tol = DEFAULT_TOLERANCES

    max_bal = 0.0
    for bi, bid in enumerate(bus_ids):
        gen_sum = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        served = float(buses[bi]["Pd"]) * load_frac[bi]
        max_bal = max(max_bal, abs(gen_sum - served - out_f + in_f))

    max_flow_eq = 0.0
    max_thermal = 0.0
    max_dmg_flow = 0.0
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        offline = int(br.get("status", 1)) == 0 or bid in dmg_br
        if offline:
            max_dmg_flow = max(max_dmg_flow, abs(flow_MW[ell]))
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        th = [math.radians(v) for v in theta_deg]
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            max_flow_eq = max(max_flow_eq, abs(th[i] - th[j] - phi) * base)
        else:
            bsus, phi = branch_susceptance(br)
            exp = base * bsus * (th[i] - th[j] - phi)
            max_flow_eq = max(max_flow_eq, abs(flow_MW[ell] - exp))
        rate = thermal_rate_mw(br)
        if rate > 0:
            max_thermal = max(max_thermal, max(0.0, abs(flow_MW[ell]) - rate))

    max_gen = 0.0
    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        if g in dmg_gen or int(gen.get("status", 1)) == 0:
            lo, hi = 0.0, 0.0
        else:
            lo = 0.0
        p = Pg_MW[g]
        max_gen = max(max_gen, max(0.0, lo - p), max(0.0, p - hi))

    max_x = max(max(0.0, -lf) for lf in load_frac) + max(max(0.0, lf - 1.0) for lf in load_frac)
    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
        and max_dmg_flow <= tol["power_balance_mw"]
        and max_x <= 1e-6
    )
    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "max_damaged_flow_MW": max_dmg_flow,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_mld(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "mld",
        "base_problem": "maximum_load_delivery",
        "mld": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result
