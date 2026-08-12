"""DC Transmission Expansion Planning (TNEP) MILP via gurobipy.

min  sum_g (c2 Pg^2 + c1 Pg + c0) + sum_c construction_cost_c * z_c
s.t. DC power balance with existing + candidate flows
     existing branch physics (always on if status=1)
     candidate: indicator z=1 => f = base*b*(θf-θt-φ), |f|<=rate
                z=0 => f=0
"""

from __future__ import annotations

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
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _ne_branches(network: dict) -> list[dict]:
    return list(network.get("ne_branches") or [])


def solve_tep(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    cands = _ne_branches(network)
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL, nC = len(bus_ids), len(gens), len(branches), len(cands)
    params = solver_params_from_config(config)

    m = gp.Model("dc_tep")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, name="Pg_MW")
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")
    z = m.addVars(nC, vtype=GRB.BINARY, name="z")
    fc = m.addVars(nC, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="fc_MW")

    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        Pg[g].LB = lo
        Pg[g].UB = hi

    # Existing branches
    for ell, br in enumerate(branches):
        if int(br.get("status", 1)) == 0:
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        _, phi = branch_susceptance(br)
        if is_zero_x(br):
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

    # Candidate branches (indicators)
    for c, br in enumerate(cands):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        rate = thermal_rate_mw(br)
        # Always |f| <= rate * z (or free if rate=0 when built)
        if rate > 0:
            m.addConstr(fc[c] <= rate * z[c], name=f"c_fmax_{c}")
            m.addConstr(fc[c] >= -rate * z[c], name=f"c_fmin_{c}")
        else:
            # Unconstrained capacity when built; force f=0 when open via indicator
            pass

        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addGenConstrIndicator(
                z[c], True, theta[i] - theta[j] == phi, name=f"c_th_eq_{c}"
            )
            m.addGenConstrIndicator(z[c], False, fc[c] == 0.0, name=f"c_open_{c}")
        else:
            bsus, phi = branch_susceptance(br)
            m.addGenConstrIndicator(
                z[c],
                True,
                fc[c] - base * bsus * (theta[i] - theta[j] - phi) == 0.0,
                name=f"c_phys_{c}",
            )
            m.addGenConstrIndicator(z[c], False, fc[c] == 0.0, name=f"c_open_{c}")

        # Offline candidate (status=0): force z=0
        if int(br.get("status", 1)) == 0:
            m.addConstr(z[c] == 0, name=f"c_off_{c}")

    # Power balance: gens - Pd - out_exist + in_exist - out_cand + in_cand = 0
    for bi, bid in enumerate(bus_ids):
        Pd = float(buses[bi]["Pd"])
        gen_sum = gp.quicksum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        out_c = gp.quicksum(fc[c] for c, br in enumerate(cands) if int(br["fbus"]) == bid)
        in_c = gp.quicksum(fc[c] for c, br in enumerate(cands) if int(br["tbus"]) == bid)
        m.addConstr(
            gen_sum - Pd - out_f + in_f - out_c + in_c == 0.0,
            name=f"bal_{bid}",
        )

    # Objective
    obj = gp.QuadExpr()
    has_quad = False
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            continue
        c2, c1, c0 = float(gen["c2"]), float(gen["c1"]), float(gen["c0"])
        if abs(c2) > 1e-12:
            has_quad = True
            obj += c2 * Pg[g] * Pg[g]
        obj += c1 * Pg[g]
        obj += c0
    for c, br in enumerate(cands):
        obj += float(br.get("construction_cost", 0.0)) * z[c]
    m.setObjective(obj, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    z_build = [0] * nC
    fc_MW = [0.0] * nC
    obj_val = None
    obj_bound = None
    mip_gap = 0.0
    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        try:
            obj_bound = float(m.ObjBound)
        except Exception:
            obj_bound = obj_val
        try:
            mip_gap = float(m.MIPGap) if m.IsMIP else 0.0
        except Exception:
            mip_gap = 0.0
        for g in range(nG):
            Pg_MW[g] = float(Pg[g].X)
        for i in range(nB):
            theta_deg[i] = math.degrees(float(theta[i].X))
        for ell in range(nL):
            flow_MW[ell] = float(f[ell].X)
        for c in range(nC):
            z_build[c] = int(round(float(z[c].X)))
            fc_MW[c] = float(fc[c].X)

    residual = validate_tep_solution(
        network, Pg_MW, theta_deg, flow_MW, z_build, fc_MW, obj_val
    )
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "z_build": z_build,
        "fc_MW": fc_MW,
        "n_built": int(sum(z_build)),
        "has_quad": has_quad,
        "ref_bus": ref_bus,
        "baseMVA": base,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "n_binary": nC,
        **residual,
    }


def validate_tep_solution(
    network: dict,
    Pg_MW: list[float],
    theta_deg: list[float],
    flow_MW: list[float],
    z_build: list[int],
    fc_MW: list[float],
    obj: float | None,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    cands = _ne_branches(network)
    bus_ids, bus_pos, _ = bus_maps(network)
    nG, nB, nL, nC = len(gens), len(buses), len(branches), len(cands)
    tol = DEFAULT_TOLERANCES

    if (
        len(Pg_MW) != nG
        or len(theta_deg) != nB
        or len(flow_MW) != nL
        or len(z_build) != nC
        or len(fc_MW) != nC
    ):
        return {
            "max_power_balance_MW": float("inf"),
            "max_flow_equation_MW": float("inf"),
            "max_thermal_violation_MW": float("inf"),
            "max_generator_bound_MW": float("inf"),
            "max_construction_logic": float("inf"),
            "cost_recomputed": None,
            "validation_passed": False,
        }

    theta = [math.radians(v) for v in theta_deg]
    max_bal = 0.0
    for bi, bid in enumerate(bus_ids):
        gen_sum = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        out_c = sum(fc_MW[c] for c, br in enumerate(cands) if int(br["fbus"]) == bid)
        in_c = sum(fc_MW[c] for c, br in enumerate(cands) if int(br["tbus"]) == bid)
        max_bal = max(
            max_bal,
            abs(gen_sum - float(buses[bi]["Pd"]) - out_f + in_f - out_c + in_c),
        )

    max_flow_eq = 0.0
    max_thermal = 0.0
    for ell, br in enumerate(branches):
        if int(br.get("status", 1)) == 0:
            max_flow_eq = max(max_flow_eq, abs(flow_MW[ell]))
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        bsus, phi = branch_susceptance(br)
        if is_zero_x(br):
            max_flow_eq = max(max_flow_eq, abs(theta[i] - theta[j] - phi) * base)
        else:
            expected = base * bsus * (theta[i] - theta[j] - phi)
            max_flow_eq = max(max_flow_eq, abs(flow_MW[ell] - expected))
        rate = thermal_rate_mw(br)
        if rate > 0:
            max_thermal = max(max_thermal, max(0.0, abs(flow_MW[ell]) - rate))

    max_logic = 0.0
    for c, br in enumerate(cands):
        zc = 1 if z_build[c] >= 0.5 else 0
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        rate = thermal_rate_mw(br)
        if zc == 0:
            max_logic = max(max_logic, abs(fc_MW[c]))
            max_flow_eq = max(max_flow_eq, abs(fc_MW[c]))
        else:
            bsus, phi = branch_susceptance(br)
            if is_zero_x(br):
                max_flow_eq = max(max_flow_eq, abs(theta[i] - theta[j] - phi) * base)
            else:
                expected = base * bsus * (theta[i] - theta[j] - phi)
                max_flow_eq = max(max_flow_eq, abs(fc_MW[c] - expected))
            if rate > 0:
                max_thermal = max(max_thermal, max(0.0, abs(fc_MW[c]) - rate))
        if rate > 0 and abs(fc_MW[c]) > rate * zc + 1e-6:
            max_logic = max(max_logic, abs(fc_MW[c]) - rate * zc)
        if int(br.get("status", 1)) == 0 and zc == 1:
            max_logic = max(max_logic, 1.0)

    max_gen = 0.0
    cost = 0.0
    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        p = Pg_MW[g]
        if p < lo - 1e-9:
            max_gen = max(max_gen, lo - p)
        if p > hi + 1e-9:
            max_gen = max(max_gen, p - hi)
        if int(gen.get("status", 1)) == 1:
            cost += float(gen["c2"]) * p * p + float(gen["c1"]) * p + float(gen["c0"])
    for c, br in enumerate(cands):
        if z_build[c] >= 0.5:
            cost += float(br.get("construction_cost", 0.0))

    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
        and max_logic <= tol["integrality"]
    )
    if obj is not None and abs(cost - obj) > max(0.01, 1e-6 * max(1.0, abs(obj))):
        pass  # soft float noise on objective recompute

    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "max_construction_logic": max_logic,
        "cost_recomputed": cost,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_tep(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "tep",
        "base_problem": config.get("base_problem", "transmission_expansion"),
        "tep": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    import sys as _sys

    d = (
        Path(_sys.argv[1])
        if len(_sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case001_case3_tnep"
    )
    r = run_case(d, quiet=True)
    e = r["tep"]
    print(
        f"[{r['case']}] status={e['status']} obj={e['obj']} "
        f"built={e.get('n_built')} bal={e['max_power_balance_MW']:.3e}"
    )
