"""Exact polar AC optimal power flow solved globally with Gurobi 13.

The model uses the MATPOWER/PGLib branch convention, including complex taps,
phase shifts, total line charging, shunts, voltage and angle bounds, and an
MVA limit at both ends of every in-service branch.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB, nlfunc


POWER_TOL_MW = 2e-4
FLOW_TOL_MVA = 2e-4
BOUND_TOL = 2e-6


def _status_name(model: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(model.Status, str(model.Status))


def _branch_coefficients(branch: dict[str, Any]) -> tuple[float, float, float, float, float]:
    """Return series g/b, total charging b, tap magnitude, phase shift radians."""
    r = float(branch.get("r", 0.0))
    x = float(branch.get("x", 0.0))
    denom = r * r + x * x
    if denom <= 1e-18:
        raise ValueError(f"in-service branch {branch.get('id')} has zero impedance")
    g = r / denom
    b = -x / denom
    charging = float(branch.get("b", 0.0))
    tap = float(branch.get("ratio", 0.0))
    if abs(tap) <= 1e-12:
        tap = 1.0
    shift = math.radians(float(branch.get("angle", 0.0)))
    return g, b, charging, tap, shift


def _branch_flows(
    branch: dict[str, Any], vm_f: float, va_f: float, vm_t: float, va_t: float, base: float
) -> tuple[float, float, float, float]:
    """Recompute MATPOWER branch flows (MW/MVAr) independently of Gurobi."""
    if int(branch.get("status", 1)) == 0:
        return 0.0, 0.0, 0.0, 0.0
    g, b, charging, tap, shift = _branch_coefficients(branch)
    delta = va_f - va_t - shift
    c = math.cos(delta)
    s = math.sin(delta)
    cross = vm_f * vm_t / tap
    p_from = base * (g * vm_f * vm_f / (tap * tap) - cross * (g * c + b * s))
    q_from = base * (
        -(b + charging / 2.0) * vm_f * vm_f / (tap * tap)
        - cross * (g * s - b * c)
    )
    p_to = base * (g * vm_t * vm_t - cross * (g * c - b * s))
    q_to = base * (
        -(b + charging / 2.0) * vm_t * vm_t
        + cross * (g * s + b * c)
    )
    return p_from, q_from, p_to, q_to


def _cost(gens: list[dict[str, Any]], pg_mw: list[float]) -> float:
    value = 0.0
    for idx, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            continue
        if int(gen.get("cost_model", 2)) != 2:
            raise ValueError("AC-OPF pilots require polynomial P-cost (cost_model=2)")
        p = pg_mw[idx]
        value += float(gen.get("c2", 0.0)) * p * p
        value += float(gen.get("c1", 0.0)) * p
        value += float(gen.get("c0", 0.0))
    return value


def validate_acopf_solution(
    network: dict[str, Any],
    vm_pu: list[float],
    va_deg: list[float],
    pg_mw: list[float],
    qg_mvar: list[float],
    p_from_mw: list[float],
    q_from_mvar: list[float],
    p_to_mw: list[float],
    q_to_mvar: list[float],
    objective: float | None,
) -> dict[str, Any]:
    """Independent numerical validation from the serialized primal solution."""
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    expected_lengths = (
        len(vm_pu) == len(buses),
        len(va_deg) == len(buses),
        len(pg_mw) == len(gens),
        len(qg_mvar) == len(gens),
        len(p_from_mw) == len(branches),
        len(q_from_mvar) == len(branches),
        len(p_to_mw) == len(branches),
        len(q_to_mvar) == len(branches),
    )
    if not all(expected_lengths):
        return {"validation_passed": False, "validation_error": "solution vector length mismatch"}

    va_rad = [math.radians(value) for value in va_deg]
    recomputed: list[tuple[float, float, float, float]] = []
    max_flow_eq = 0.0
    max_thermal = 0.0
    max_angle = 0.0
    for ell, branch in enumerate(branches):
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        flow = _branch_flows(branch, vm_pu[i], va_rad[i], vm_pu[j], va_rad[j], base)
        recomputed.append(flow)
        serialized = (p_from_mw[ell], q_from_mvar[ell], p_to_mw[ell], q_to_mvar[ell])
        max_flow_eq = max(max_flow_eq, *(abs(flow[k] - serialized[k]) for k in range(4)))
        if int(branch.get("status", 1)) == 0:
            continue
        rate = float(branch.get("rateA", 0.0))
        if rate > 0.0:
            max_thermal = max(
                max_thermal,
                max(0.0, math.hypot(flow[0], flow[1]) - rate),
                max(0.0, math.hypot(flow[2], flow[3]) - rate),
            )
        difference = va_deg[i] - va_deg[j]
        lower = float(branch.get("angmin", -360.0))
        upper = float(branch.get("angmax", 360.0))
        if lower > -360.0:
            max_angle = max(max_angle, max(0.0, lower - difference))
        if upper < 360.0:
            max_angle = max(max_angle, max(0.0, difference - upper))

    max_p_balance = 0.0
    max_q_balance = 0.0
    max_voltage = 0.0
    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        p_generation = sum(pg_mw[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id)
        q_generation = sum(qg_mvar[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id)
        p_out = 0.0
        q_out = 0.0
        for ell, branch in enumerate(branches):
            if int(branch["fbus"]) == bus_id:
                p_out += recomputed[ell][0]
                q_out += recomputed[ell][1]
            elif int(branch["tbus"]) == bus_id:
                p_out += recomputed[ell][2]
                q_out += recomputed[ell][3]
        v_squared = vm_pu[bi] * vm_pu[bi]
        p_residual = (
            p_generation - float(bus.get("Pd", 0.0)) - p_out - float(bus.get("Gs", 0.0)) * v_squared
        )
        q_residual = (
            q_generation - float(bus.get("Qd", 0.0)) - q_out + float(bus.get("Bs", 0.0)) * v_squared
        )
        max_p_balance = max(max_p_balance, abs(p_residual))
        max_q_balance = max(max_q_balance, abs(q_residual))
        max_voltage = max(
            max_voltage,
            max(0.0, float(bus["Vmin"]) - vm_pu[bi]),
            max(0.0, vm_pu[bi] - float(bus["Vmax"])),
        )

    max_p_bound = 0.0
    max_q_bound = 0.0
    for g, gen in enumerate(gens):
        status = int(gen.get("status", 1))
        p_min = float(gen["Pmin"]) if status else 0.0
        p_max = float(gen["Pmax"]) if status else 0.0
        q_min = float(gen["Qmin"]) if status else 0.0
        q_max = float(gen["Qmax"]) if status else 0.0
        max_p_bound = max(max_p_bound, max(0.0, p_min - pg_mw[g]), max(0.0, pg_mw[g] - p_max))
        max_q_bound = max(
            max_q_bound, max(0.0, q_min - qg_mvar[g]), max(0.0, qg_mvar[g] - q_max)
        )

    cost_recomputed = _cost(gens, pg_mw)
    cost_error = 0.0 if objective is None else abs(cost_recomputed - objective)
    passed = (
        max_p_balance <= POWER_TOL_MW
        and max_q_balance <= POWER_TOL_MW
        and max_flow_eq <= FLOW_TOL_MVA
        and max_thermal <= FLOW_TOL_MVA
        and max_voltage <= BOUND_TOL
        and max_angle <= BOUND_TOL
        and max_p_bound <= BOUND_TOL
        and max_q_bound <= BOUND_TOL
        and cost_error <= max(1e-4, 1e-8 * max(1.0, abs(cost_recomputed)))
    )
    return {
        "max_p_balance_MW": max_p_balance,
        "max_q_balance_MVAr": max_q_balance,
        "max_branch_flow_equation_MVA": max_flow_eq,
        "max_thermal_violation_MVA": max_thermal,
        "max_voltage_bound_violation_pu": max_voltage,
        "max_angle_bound_violation_deg": max_angle,
        "max_p_generator_bound_MW": max_p_bound,
        "max_q_generator_bound_MVAr": max_q_bound,
        "cost_recomputed": cost_recomputed,
        "cost_recompute_error": cost_error,
        "validation_passed": passed,
        "validation_tolerances": {
            "power_balance_MW_MVAr": POWER_TOL_MW,
            "branch_flow_and_thermal_MVA": FLOW_TOL_MVA,
            "variable_bounds": BOUND_TOL,
        },
    }


def solve_acopf(network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    ref_candidates = [int(bus["bus_i"]) for bus in buses if int(bus.get("type", 1)) == 3]
    ref_bus = ref_candidates[0] if ref_candidates else bus_ids[0]
    params = config.get("gurobi_parameters", {})

    model = gp.Model("polar_acopf")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.NonConvex = 2
    model.Params.FuncNonlinear = 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-7)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 300.0)))
    model.Params.FeasibilityTol = 1e-8
    model.Params.OptimalityTol = 1e-8
    model.Params.NumericFocus = 2

    vm = model.addVars(
        len(buses),
        lb=[float(bus["Vmin"]) for bus in buses],
        ub=[float(bus["Vmax"]) for bus in buses],
        name="Vm_pu",
    )
    va = model.addVars(len(buses), lb=-math.pi, ub=math.pi, name="Va_rad")
    pg = model.addVars(len(gens), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="Pg_MW")
    qg = model.addVars(len(gens), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="Qg_MVAr")
    p_from = model.addVars(len(branches), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="P_from_MW")
    q_from = model.addVars(len(branches), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="Q_from_MVAr")
    p_to = model.addVars(len(branches), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="P_to_MW")
    q_to = model.addVars(len(branches), lb=-GRB.INFINITY, ub=GRB.INFINITY, name="Q_to_MVAr")

    ref_pos = bus_pos[ref_bus]
    ref_angle = math.radians(float(buses[ref_pos].get("Va", 0.0)))
    model.addConstr(va[ref_pos] == ref_angle, name="reference_angle")
    vm_start = [
        min(max(float(bus.get("Vm", 1.0)), float(bus["Vmin"])), float(bus["Vmax"]))
        for bus in buses
    ]
    va_start = [math.radians(float(bus.get("Va", 0.0))) for bus in buses]
    for bi in range(len(buses)):
        vm[bi].Start = vm_start[bi]
        va[bi].Start = va_start[bi]

    objective = gp.QuadExpr()
    for g, gen in enumerate(gens):
        online = int(gen.get("status", 1)) == 1
        p_min = float(gen["Pmin"]) if online else 0.0
        p_max = float(gen["Pmax"]) if online else 0.0
        q_min = float(gen["Qmin"]) if online else 0.0
        q_max = float(gen["Qmax"]) if online else 0.0
        pg[g].LB, pg[g].UB = p_min, p_max
        qg[g].LB, qg[g].UB = q_min, q_max
        pg[g].Start = min(max(float(gen.get("Pg", 0.0)), p_min), p_max)
        qg[g].Start = min(max(float(gen.get("Qg", 0.0)), q_min), q_max)
        if online:
            if int(gen.get("cost_model", 2)) != 2:
                raise ValueError("AC-OPF pilots require polynomial P-cost (cost_model=2)")
            objective += float(gen.get("c2", 0.0)) * pg[g] * pg[g]
            objective += float(gen.get("c1", 0.0)) * pg[g]
            objective += float(gen.get("c0", 0.0))
    model.setObjective(objective, GRB.MINIMIZE)

    for ell, branch in enumerate(branches):
        if int(branch.get("status", 1)) == 0:
            model.addConstr(p_from[ell] == 0.0, name=f"p_from_off_{ell}")
            model.addConstr(q_from[ell] == 0.0, name=f"q_from_off_{ell}")
            model.addConstr(p_to[ell] == 0.0, name=f"p_to_off_{ell}")
            model.addConstr(q_to[ell] == 0.0, name=f"q_to_off_{ell}")
            continue
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        g, b, charging, tap, shift = _branch_coefficients(branch)
        delta = va[i] - va[j] - shift
        cosine = nlfunc.cos(delta)
        sine = nlfunc.sin(delta)
        cross = vm[i] * vm[j] / tap
        model.addConstr(
            p_from[ell]
            == base * (g * vm[i] * vm[i] / (tap * tap) - cross * (g * cosine + b * sine)),
            name=f"p_from_eq_{ell}",
        )
        model.addConstr(
            q_from[ell]
            == base
            * (
                -(b + charging / 2.0) * vm[i] * vm[i] / (tap * tap)
                - cross * (g * sine - b * cosine)
            ),
            name=f"q_from_eq_{ell}",
        )
        model.addConstr(
            p_to[ell] == base * (g * vm[j] * vm[j] - cross * (g * cosine - b * sine)),
            name=f"p_to_eq_{ell}",
        )
        model.addConstr(
            q_to[ell]
            == base
            * (-(b + charging / 2.0) * vm[j] * vm[j] + cross * (g * sine + b * cosine)),
            name=f"q_to_eq_{ell}",
        )
        lower = float(branch.get("angmin", -360.0))
        upper = float(branch.get("angmax", 360.0))
        if lower > -360.0:
            model.addConstr(va[i] - va[j] >= math.radians(lower), name=f"angle_min_{ell}")
        if upper < 360.0:
            model.addConstr(va[i] - va[j] <= math.radians(upper), name=f"angle_max_{ell}")
        rate = float(branch.get("rateA", 0.0))
        if rate > 0.0:
            p_from[ell].LB = p_to[ell].LB = -rate
            p_from[ell].UB = p_to[ell].UB = rate
            q_from[ell].LB = q_to[ell].LB = -rate
            q_from[ell].UB = q_to[ell].UB = rate
            model.addConstr(p_from[ell] * p_from[ell] + q_from[ell] * q_from[ell] <= rate * rate,
                            name=f"thermal_from_{ell}")
            model.addConstr(p_to[ell] * p_to[ell] + q_to[ell] * q_to[ell] <= rate * rate,
                            name=f"thermal_to_{ell}")

        initial = _branch_flows(
            branch,
            vm_start[i],
            va_start[i],
            vm_start[j],
            va_start[j],
            base,
        )
        p_from[ell].Start, q_from[ell].Start, p_to[ell].Start, q_to[ell].Start = initial

    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        p_generation = gp.quicksum(pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id)
        q_generation = gp.quicksum(qg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id)
        p_out = gp.quicksum(
            p_from[ell] if int(branch["fbus"]) == bus_id else p_to[ell]
            for ell, branch in enumerate(branches)
            if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
        )
        q_out = gp.quicksum(
            q_from[ell] if int(branch["fbus"]) == bus_id else q_to[ell]
            for ell, branch in enumerate(branches)
            if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
        )
        model.addConstr(
            p_generation - float(bus.get("Pd", 0.0))
            == p_out + float(bus.get("Gs", 0.0)) * vm[bi] * vm[bi],
            name=f"p_balance_{bus_id}",
        )
        model.addConstr(
            q_generation - float(bus.get("Qd", 0.0))
            == q_out - float(bus.get("Bs", 0.0)) * vm[bi] * vm[bi],
            name=f"q_balance_{bus_id}",
        )

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    has_solution = model.SolCount > 0

    vm_values = [float(vm[i].X) for i in range(len(buses))] if has_solution else []
    va_values = [math.degrees(float(va[i].X)) for i in range(len(buses))] if has_solution else []
    pg_values = [float(pg[g].X) for g in range(len(gens))] if has_solution else []
    qg_values = [float(qg[g].X) for g in range(len(gens))] if has_solution else []
    pf_values = [float(p_from[l].X) for l in range(len(branches))] if has_solution else []
    qf_values = [float(q_from[l].X) for l in range(len(branches))] if has_solution else []
    pt_values = [float(p_to[l].X) for l in range(len(branches))] if has_solution else []
    qt_values = [float(q_to[l].X) for l in range(len(branches))] if has_solution else []
    obj = float(model.ObjVal) if has_solution else None
    obj_bound = float(model.ObjBound) if has_solution else None
    try:
        gap = float(model.MIPGap) if has_solution else None
    except gp.GurobiError:
        gap = None
    validation = validate_acopf_solution(
        network,
        vm_values,
        va_values,
        pg_values,
        qg_values,
        pf_values,
        qf_values,
        pt_values,
        qt_values,
        obj,
    )
    validation["validation_passed"] = bool(validation.get("validation_passed") and status == "OPTIMAL")
    return {
        "status": status,
        "objective": obj,
        "objective_bound": obj_bound,
        "optimality_gap": gap,
        "runtime_seconds": runtime,
        "Vm_pu": vm_values,
        "Va_deg": va_values,
        "Pg_MW": pg_values,
        "Qg_MVAr": qg_values,
        "P_from_MW": pf_values,
        "Q_from_MVAr": qf_values,
        "P_to_MW": pt_values,
        "Q_to_MVAr": qt_values,
        "reference_bus": ref_bus,
        "baseMVA": base,
        "n_variables": model.NumVars,
        "n_constraints": model.NumConstrs,
        **validation,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_path = Path(case_dir)
    network = json.loads((case_path / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_path / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_acopf(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_path.name),
        "solver": "python-gurobi-13-global-nonlinear",
        "base_problem": "opf",
        "problem": "ac_opf",
        "variant": config["variant"],
        "acopf": solution,
        "validation": {
            "passed": bool(solution.get("validation_passed")),
            "method": "independent_polar_ac_recomputation",
        },
    }
    output = case_path / "results" / "python_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result
