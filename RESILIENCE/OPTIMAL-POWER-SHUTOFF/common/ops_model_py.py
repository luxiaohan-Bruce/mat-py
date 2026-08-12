"""DC Optimal Power Shutoff (OPS / PSPS) MILP — gurobipy.

Binary z_ell = 1 keeps branch energized. Offline branch: flow = 0 (indicator).
Serve load only on energized buses; gens require bus on; branch requires both
buses on. DC physics via Gurobi indicators.

Modes (config["ops_mode"]):
  risk_budget — max served s.t. sum risk_ell * z_ell <= risk_budget
  risk_weight — min alpha*load_shed + (1-alpha)*risk_exposure
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
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }.get(m.Status, str(m.Status))


def _branch_risk(br: dict) -> float:
    return float(br.get("power_risk", 0.0) or 0.0) + float(br.get("base_risk", 0.0) or 0.0)


def _bus_power_risk(bus: dict) -> float:
    return float(bus.get("power_risk", 0.0) or 0.0)


def _gen_power_risk(gen: dict) -> float:
    return float(gen.get("power_risk", 0.0) or 0.0)


def solve_ops(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    params = solver_params_from_config(config)

    mode = str(config.get("ops_mode", "risk_budget")).lower()
    alpha = float(config.get("risk_weight", config.get("alpha", 0.5)))
    risk_budget = float(config.get("risk_budget", 1e18))

    br_risk = [_branch_risk(br) for br in branches]
    total_branch_risk = sum(br_risk[ell] for ell, br in enumerate(branches) if int(br.get("status", 1)) == 1)
    total_pd = sum(float(b["Pd"]) for b in buses)

    m = gp.Model("dc_ops")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, lb=-math.pi, ub=math.pi, name="theta")
    Pg = m.addVars(nG, lb=0.0, name="Pg_MW")
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")
    z_br = m.addVars(nL, vtype=GRB.BINARY, name="z_br")
    z_bus = m.addVars(nB, vtype=GRB.BINARY, name="z_bus")
    z_gen = m.addVars(nG, vtype=GRB.BINARY, name="z_gen")
    x = m.addVars(nB, lb=0.0, ub=1.0, name="load_frac")

    # Reference: if ref bus is energized, fix its angle to 0 (indicator)
    m.addGenConstrIndicator(
        z_bus[bus_pos[ref_bus]], True, theta[bus_pos[ref_bus]] == 0.0, name="ref_th"
    )

    # Generators: online only if status=1 and z_gen=1; z_gen <= z_bus
    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        if int(gen.get("status", 1)) == 0:
            m.addConstr(z_gen[g] == 0.0, name=f"gen_off_{g}")
            m.addConstr(Pg[g] == 0.0, name=f"Pg0_{g}")
            continue
        # Pmin relaxed to 0 for shutoff feasibility
        Pg[g].UB = hi
        m.addConstr(Pg[g] <= hi * z_gen[g], name=f"Pg_ub_{g}")
        m.addConstr(z_gen[g] <= z_bus[bus_pos[int(gen["bus"])]], name=f"gen_bus_{g}")

    # Loads: served only if bus energized
    for bi in range(nB):
        m.addConstr(x[bi] <= z_bus[bi], name=f"load_bus_{bi}")

    # Branches
    for ell, br in enumerate(branches):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if int(br.get("status", 1)) == 0:
            m.addConstr(z_br[ell] == 0.0, name=f"zbr0_{ell}")
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue

        # Branch energized only if both terminal buses on
        m.addConstr(z_br[ell] <= z_bus[i], name=f"zbr_f_{ell}")
        m.addConstr(z_br[ell] <= z_bus[j], name=f"zbr_t_{ell}")

        rate = thermal_rate_mw(br)
        if rate <= 0:
            rate = 1e4 * base  # loose thermal if rateA=0

        m.addConstr(f[ell] <= rate * z_br[ell], name=f"fmax_{ell}")
        m.addConstr(f[ell] >= -rate * z_br[ell], name=f"fmin_{ell}")
        m.addGenConstrIndicator(z_br[ell], False, f[ell] == 0.0, name=f"ind_off_{ell}")

        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addGenConstrIndicator(
                z_br[ell], True, theta[i] - theta[j] == phi, name=f"ind_th_{ell}"
            )
        else:
            bsus, phi = branch_susceptance(br)
            # f = base * b * (theta_i - theta_j - phi)
            m.addGenConstrIndicator(
                z_br[ell],
                True,
                f[ell] - base * bsus * (theta[i] - theta[j] - phi) == 0.0,
                name=f"ind_phys_{ell}",
            )

    # Power balance (MW)
    for bi, bid in enumerate(bus_ids):
        Pd = float(buses[bi]["Pd"])
        gen_sum = gp.quicksum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        m.addConstr(gen_sum - Pd * x[bi] - out_f + in_f == 0.0, name=f"bal_{bid}")

    # Risk exposure (branch-focused as sum risk_ell * z_ell; optional bus/gen power_risk)
    risk_expr = gp.quicksum(br_risk[ell] * z_br[ell] for ell in range(nL))
    # Include bus/gen power_risk when those components are on (PMW-compatible extra)
    risk_expr += gp.quicksum(_bus_power_risk(buses[bi]) * z_bus[bi] for bi in range(nB))
    risk_expr += gp.quicksum(
        _gen_power_risk(gens[g]) * z_gen[g]
        for g in range(nG)
        if int(gens[g].get("status", 1)) == 1
    )
    # load power_risk * served fraction
    risk_expr += gp.quicksum(
        float(buses[bi].get("load_power_risk", 0.0) or 0.0) * x[bi] for bi in range(nB)
    )

    served_expr = gp.quicksum(float(buses[bi]["Pd"]) * x[bi] for bi in range(nB))
    shed_expr = total_pd - served_expr

    if mode == "risk_weight":
        # min alpha * load_shed + (1-alpha) * risk_exposure
        m.setObjective(alpha * shed_expr + (1.0 - alpha) * risk_expr, GRB.MINIMIZE)
    else:
        # risk_budget: max served / min shed s.t. risk <= budget
        m.addConstr(risk_expr <= risk_budget, name="risk_budget")
        m.setObjective(shed_expr, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    load_frac = [0.0] * nB
    z_br_sol = [0.0] * nL
    z_bus_sol = [0.0] * nB
    z_gen_sol = [0.0] * nG
    obj_val = None
    mip_gap = None
    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        mip_gap = float(m.MIPGap) if m.IsMIP else 0.0
        for g in range(nG):
            Pg_MW[g] = float(Pg[g].X)
            z_gen_sol[g] = float(z_gen[g].X)
        for i in range(nB):
            theta_deg[i] = math.degrees(float(theta[i].X))
            load_frac[i] = float(x[i].X)
            z_bus_sol[i] = float(z_bus[i].X)
        for ell in range(nL):
            flow_MW[ell] = float(f[ell].X)
            z_br_sol[ell] = float(z_br[ell].X)

    served = sum(float(buses[bi]["Pd"]) * load_frac[bi] for bi in range(nB))
    risk_exposure = sum(br_risk[ell] * z_br_sol[ell] for ell in range(nL))
    risk_exposure += sum(_bus_power_risk(buses[bi]) * z_bus_sol[bi] for bi in range(nB))
    risk_exposure += sum(
        _gen_power_risk(gens[g]) * z_gen_sol[g]
        for g in range(nG)
        if int(gens[g].get("status", 1)) == 1
    )
    risk_exposure += sum(
        float(buses[bi].get("load_power_risk", 0.0) or 0.0) * load_frac[bi] for bi in range(nB)
    )
    deenergized = [int(branches[ell]["id"]) for ell in range(nL) if z_br_sol[ell] < 0.5]

    residual = _validate(
        network, config, Pg_MW, theta_deg, flow_MW, load_frac, z_br_sol, z_bus_sol, z_gen_sol,
        risk_exposure, risk_budget if mode != "risk_weight" else None,
    )

    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": float(m.ObjBound) if m.SolCount > 0 else None,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "ops_mode": mode,
        "risk_weight": alpha if mode == "risk_weight" else None,
        "risk_budget": risk_budget if mode != "risk_weight" else None,
        "total_branch_risk": total_branch_risk,
        "risk_exposure": risk_exposure,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "load_frac": load_frac,
        "z_branch": z_br_sol,
        "z_bus": z_bus_sol,
        "z_gen": z_gen_sol,
        "deenergized_branches": deenergized,
        "n_deenergized": len(deenergized),
        "served_MW": served,
        "total_demand_MW": total_pd,
        "load_shed_MW": total_pd - served,
        "ref_bus": ref_bus,
        "baseMVA": base,
        **residual,
    }


def _validate(
    network,
    config,
    Pg_MW,
    theta_deg,
    flow_MW,
    load_frac,
    z_br,
    z_bus,
    z_gen,
    risk_exposure,
    risk_budget,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    tol = DEFAULT_TOLERANCES
    th = [math.radians(v) for v in theta_deg]

    max_bal = 0.0
    for bi, bid in enumerate(bus_ids):
        gen_sum = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        served = float(buses[bi]["Pd"]) * load_frac[bi]
        max_bal = max(max_bal, abs(gen_sum - served - out_f + in_f))

    max_flow_eq = 0.0
    max_thermal = 0.0
    max_off_flow = 0.0
    max_int = 0.0
    for ell, br in enumerate(branches):
        z = z_br[ell]
        max_int = max(max_int, min(abs(z), abs(z - 1.0)))
        if z < 0.5 or int(br.get("status", 1)) == 0:
            max_off_flow = max(max_off_flow, abs(flow_MW[ell]))
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
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

    # load only if bus on
    max_load_bus = 0.0
    for bi in range(len(bus_ids)):
        if load_frac[bi] > z_bus[bi] + 1e-6:
            max_load_bus = max(max_load_bus, load_frac[bi] - z_bus[bi])

    max_risk_viol = 0.0
    if risk_budget is not None:
        max_risk_viol = max(0.0, risk_exposure - risk_budget - 1e-6)

    max_gen = 0.0
    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        if int(gen.get("status", 1)) == 0 or z_gen[g] < 0.5:
            max_gen = max(max_gen, abs(Pg_MW[g]))
        else:
            max_gen = max(max_gen, max(0.0, Pg_MW[g] - hi), max(0.0, -Pg_MW[g]))

    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
        and max_off_flow <= tol["power_balance_mw"]
        and max_load_bus <= 1e-5
        and max_risk_viol <= 1e-4
        and max_int <= tol["integrality"]
    )
    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "max_deenergized_flow_MW": max_off_flow,
        "max_load_without_bus": max_load_bus,
        "max_risk_budget_violation": max_risk_viol,
        "max_integrality": max_int,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_ops(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "ops",
        "base_problem": "optimal_power_shutoff",
        "ops": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result
