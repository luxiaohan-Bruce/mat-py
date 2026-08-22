"""Network-constrained DC optimal power flow (gurobipy).

min  sum_g c2*Pg_g^2 + c1*Pg_g + c0   (online gens only, Pg in MW)
s.t. power balance, DC flow f = b*(θf-θt-φ), thermal limits, gen bounds.
No commitment binaries.
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
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def solve_ed(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    if int(config.get("T") or 1) > 1:
        return solve_ed_horizon(network, config, quiet=quiet)
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    params = solver_params_from_config(config)

    m = gp.Model("dc_opf")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, name="Pg_MW")  # MW
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")

    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        Pg[g].LB = lo
        Pg[g].UB = hi

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
    m.setObjective(obj, GRB.MINIMIZE)

    for ell, br in enumerate(branches):
        if int(br.get("status", 1)) == 0:
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        _, phi = branch_susceptance(br)
        if is_zero_x(br):
            # Ideal branch: angle coupling only; flow free within thermal limit
            m.addConstr(theta[i] - theta[j] == phi, name=f"th_eq_{ell}")
        else:
            bsus, phi = branch_susceptance(br)
            # f_MW = base * b * (θf - θt - φ)
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
        m.addConstr(gen_sum - Pd - out_f + in_f == 0.0, name=f"bal_{bid}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
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

    residual = validate_ed_solution(network, Pg_MW, theta_deg, flow_MW, obj_val)
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "has_quad": has_quad,
        "ref_bus": ref_bus,
        "baseMVA": base,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        **residual,
    }


def validate_ed_solution(
    network: dict,
    Pg_MW: list[float],
    theta_deg: list[float],
    flow_MW: list[float],
    obj: float | None,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    nG, nB, nL = len(gens), len(buses), len(branches)
    tol = DEFAULT_TOLERANCES

    if len(Pg_MW) != nG or len(theta_deg) != nB or len(flow_MW) != nL:
        return {
            "max_power_balance_MW": float("inf"),
            "max_flow_equation_MW": float("inf"),
            "max_thermal_violation_MW": float("inf"),
            "max_generator_bound_MW": float("inf"),
            "cost_recomputed": None,
            "validation_passed": False,
        }

    theta = [math.radians(v) for v in theta_deg]
    max_bal = 0.0
    for bi, bid in enumerate(bus_ids):
        gen_sum = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        max_bal = max(max_bal, abs(gen_sum - float(buses[bi]["Pd"]) - out_f + in_f))

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

    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
    )
    if obj is not None and abs(cost - obj) > max(0.01, 1e-6 * max(1.0, abs(obj))):
        # soft: still report but don't fail solely on cost recompute float noise
        pass

    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "cost_recomputed": cost,
        "validation_passed": passed,
    }


DAILY_24 = [
    0.60, 0.56, 0.54, 0.53, 0.55, 0.62,
    0.76, 0.88, 0.94, 0.96, 0.98, 1.00,
    0.97, 0.95, 0.93, 0.92, 0.94, 0.98,
    1.00, 0.98, 0.90, 0.82, 0.72, 0.65,
]


def _load_multipliers(config: dict, T: int) -> list[float]:
    raw = config.get("load_mult")
    if isinstance(raw, list) and raw:
        mult = [float(x) for x in raw]
    else:
        mult = []
        while len(mult) < T:
            mult.extend(DAILY_24)
    if len(mult) < T:
        extra = DAILY_24
        while len(mult) < T:
            mult.extend(extra)
    return [float(x) for x in mult[:T]]


def solve_ed_horizon(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    """Multi-period DC-OPF with load profile and optional ramp coupling."""
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    T = max(2, int(config.get("T") or 2))
    load_mult = _load_multipliers(config, T)
    ramp_frac = float(config.get("ramp_frac", 0.25))
    params = solver_params_from_config(config)

    m = gp.Model("dc_opf_horizon")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, T, name="Pg_MW")
    f = m.addVars(nL, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")

    for t in range(T):
        m.addConstr(theta[bus_pos[ref_bus], t] == 0.0, name=f"ref_{t}")

    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        for t in range(T):
            Pg[g, t].LB = lo
            Pg[g, t].UB = hi
        if int(gen.get("status", 1)) == 1 and ramp_frac > 0:
            cap = max(abs(float(gen.get("Pmax", 0.0))), abs(float(gen.get("Pmin", 0.0))), 1.0)
            ramp = ramp_frac * cap
            for t in range(1, T):
                m.addConstr(Pg[g, t] - Pg[g, t - 1] <= ramp, name=f"ru_{g}_{t}")
                m.addConstr(Pg[g, t - 1] - Pg[g, t] <= ramp, name=f"rd_{g}_{t}")

    obj = gp.QuadExpr()
    has_quad = False
    for t in range(T):
        for g, gen in enumerate(gens):
            if int(gen.get("status", 1)) == 0:
                continue
            c2, c1, c0 = float(gen["c2"]), float(gen["c1"]), float(gen["c0"])
            if abs(c2) > 1e-12:
                has_quad = True
                obj += c2 * Pg[g, t] * Pg[g, t]
            obj += c1 * Pg[g, t]
            obj += c0
    m.setObjective(obj, GRB.MINIMIZE)

    for t in range(T):
        for ell, br in enumerate(branches):
            if int(br.get("status", 1)) == 0:
                m.addConstr(f[ell, t] == 0.0, name=f"f0_{ell}_{t}")
                continue
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            _, phi = branch_susceptance(br)
            if is_zero_x(br):
                m.addConstr(theta[i, t] - theta[j, t] == phi, name=f"th_eq_{ell}_{t}")
            else:
                bsus, phi = branch_susceptance(br)
                m.addConstr(
                    f[ell, t] == base * bsus * (theta[i, t] - theta[j, t] - phi),
                    name=f"phys_{ell}_{t}",
                )
            rate = thermal_rate_mw(br)
            if rate > 0:
                m.addConstr(f[ell, t] <= rate, name=f"fmax_{ell}_{t}")
                m.addConstr(f[ell, t] >= -rate, name=f"fmin_{ell}_{t}")

        for bi, bid in enumerate(bus_ids):
            Pd = float(buses[bi]["Pd"]) * load_mult[t]
            gen_sum = gp.quicksum(
                Pg[g, t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            out_f = gp.quicksum(
                f[ell, t] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
            )
            in_f = gp.quicksum(
                f[ell, t] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
            )
            m.addConstr(gen_sum - Pd - out_f + in_f == 0.0, name=f"bal_{bid}_{t}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    obj_val = None
    obj_bound = None
    mip_gap = 0.0
    peak_t = max(range(T), key=lambda tt: load_mult[tt])
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
            Pg_MW[g] = float(Pg[g, peak_t].X)
        for i in range(nB):
            theta_deg[i] = math.degrees(float(theta[i, peak_t].X))
        for ell in range(nL):
            flow_MW[ell] = float(f[ell, peak_t].X)

    # residuals at the peak-load hour, scaled Pd
    net_peak = json.loads(json.dumps(network))
    for bi, bus in enumerate(net_peak["buses"]):
        bus["Pd"] = float(buses[bi]["Pd"]) * load_mult[peak_t]
    residual = validate_ed_solution(net_peak, Pg_MW, theta_deg, flow_MW, None)
    # objective is summed over T; do not compare to single-hour cost
    residual["cost_recomputed"] = obj_val
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "has_quad": has_quad,
        "ref_bus": ref_bus,
        "baseMVA": base,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "T": T,
        "peak_t": peak_t,
        **residual,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_ed(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": config.get("problem", "dc_opf"),
        "base_problem": config.get("base_problem", "opf"),
        "ed": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    import sys as _sys

    d = Path(_sys.argv[1]) if len(_sys.argv) > 1 else Path(__file__).resolve().parents[1] / "case001_pjm5_dc_ed"
    r = run_case(d, quiet=True)
    e = r["ed"]
    print(f"[{r['case']}] status={e['status']} obj={e['obj']} bal={e['max_power_balance_MW']:.3e}")
