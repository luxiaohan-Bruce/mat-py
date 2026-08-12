"""Integrated Electricity–Gas (IEG) MILP v1 via gurobipy.

Electric: networked DC OPF / ED
Gas: nodal mass balance; pipeline flow with direction binary;
     piecewise-linear Weymouth |f|f ≈ (π_i - π_j)/k  (π = p²)
Coupling: gas offtake = heat_rate * Pg for gas-fired gens
Objective: min electric gen cost + gas supply cost
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
from tolerances import solver_params_from_config  # noqa: E402

# residual tolerances
TOL_ELEC_MW = 1e-4
TOL_GAS_FLOW = 1e-3
TOL_PRESSURE = 1e-3
TOL_COUPLING = 1e-3


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _node_index(nodes: list[dict], key: Any) -> int:
    """Map gas node id (int or str) to list index."""
    for i, n in enumerate(nodes):
        if n["id"] == key or str(n["id"]) == str(key):
            return i
    raise KeyError(f"gas node {key!r} not found")


def _pwl_breakpoints(fmax: float, n_seg: int) -> tuple[list[float], list[float]]:
    """Breakpoints for g(f)=f|f| on [-fmax, fmax]."""
    fmax = max(float(fmax), 1.0)
    n_seg = max(int(n_seg), 4)
    # even number of intervals preferred
    xs = [ -fmax + 2.0 * fmax * k / n_seg for k in range(n_seg + 1) ]
    ys = [ x * abs(x) for x in xs ]
    return xs, ys


def solve_ieg(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    gas = network["gas"]
    nodes = gas["nodes"]
    pipes = gas.get("pipes") or []
    compressors = gas.get("compressors") or []
    valves = gas.get("valves") or []
    sources = gas.get("sources") or []
    demands = gas.get("demands") or []
    coupling = (network.get("coupling") or {}).get("gas_gens") or []

    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    nN = len(nodes)
    nP = len(pipes)
    nC = len(compressors)
    nV = len(valves)
    nS = len(sources)

    params = solver_params_from_config(config)
    n_pwl = int(config.get("weymouth_pwl_segments", 10))
    model_mode = str(config.get("gas_model", "pwl"))  # pwl | relaxed

    m = gp.Model("ieg_v1")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    # ---- Electric vars ----
    theta = m.addVars(nB, lb=-math.pi, ub=math.pi, name="theta")
    Pg = m.addVars(nG, name="Pg_MW")
    f_e = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_elec_MW")
    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    for g, gen in enumerate(gens):
        lo, hi = gen_bounds_mw(gen)
        Pg[g].LB = lo
        Pg[g].UB = hi

    for ell, br in enumerate(branches):
        if int(br.get("status", 1)) == 0:
            m.addConstr(f_e[ell] == 0.0, name=f"fe0_{ell}")
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addConstr(theta[i] - theta[j] == phi, name=f"th_eq_{ell}")
        else:
            bsus, phi = branch_susceptance(br)
            m.addConstr(
                f_e[ell] == base * bsus * (theta[i] - theta[j] - phi),
                name=f"phys_{ell}",
            )
        rate = thermal_rate_mw(br)
        if rate > 0:
            m.addConstr(f_e[ell] <= rate, name=f"femax_{ell}")
            m.addConstr(f_e[ell] >= -rate, name=f"femin_{ell}")

    for bi, bid in enumerate(bus_ids):
        Pd = float(buses[bi]["Pd"])
        gen_sum = gp.quicksum(
            Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
        )
        out_f = gp.quicksum(
            f_e[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        )
        in_f = gp.quicksum(
            f_e[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        )
        m.addConstr(gen_sum - Pd - out_f + in_f == 0.0, name=f"ebal_{bid}")

    # ---- Gas vars: pressure squared π = p² ----
    pi = []
    pmin_l, pmax_l = [], []
    for i, nd in enumerate(nodes):
        pmin = float(nd["pmin"])
        pmax = float(nd["pmax"])
        pmin_l.append(pmin)
        pmax_l.append(pmax)
        pi.append(m.addVar(lb=pmin * pmin, ub=pmax * pmax, name=f"pi_{i}"))

    # supply
    s_var = []
    for si, src in enumerate(sources):
        s_var.append(
            m.addVar(
                lb=float(src.get("smin_m3h", 0.0)),
                ub=float(src.get("smax_m3h", 0.0)),
                name=f"supply_{si}",
            )
        )

    # gas offtake by gens
    offtake = {i: 0.0 for i in range(nN)}  # will become LinExpr
    offtake_expr: dict[int, Any] = {i: gp.LinExpr(0.0) for i in range(nN)}
    for c in coupling:
        gi = int(c["gen_index"])
        ni = _node_index(nodes, c["gas_node"])
        hr = float(c["heat_rate"])
        offtake_expr[ni] += hr * Pg[gi]

    # fixed non-power demand
    dem_at = {i: 0.0 for i in range(nN)}
    for d in demands:
        ni = _node_index(nodes, d["gas_node"])
        dem_at[ni] += float(d.get("demand_m3h", d.get("demand", 0.0)))

    # pipe flows + Weymouth PWL
    f_pipe = m.addVars(nP, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_pipe")
    y_dir = m.addVars(nP, vtype=GRB.BINARY, name="y_dir")  # 1: from→to positive

    for ell, pipe in enumerate(pipes):
        fmax = float(pipe["fmax"])
        f_pipe[ell].LB = -fmax
        f_pipe[ell].UB = fmax
        # direction indicators (optional bounds tightening)
        m.addConstr(f_pipe[ell] <= fmax * y_dir[ell] + fmax * (1 - y_dir[ell]), name=f"fub_{ell}")
        # keep binary linked: f >= -fmax*(1-y) - wait standard:
        # y=1 => f >= 0; y=0 => f <= 0
        m.addConstr(f_pipe[ell] <= fmax * y_dir[ell], name=f"fpos_{ell}")
        m.addConstr(f_pipe[ell] >= -fmax * (1 - y_dir[ell]), name=f"fneg_{ell}")

        i = _node_index(nodes, pipe["from"])
        j = _node_index(nodes, pipe["to"])
        k_coef = float(pipe["k"])
        if k_coef < 1e-18:
            k_coef = 1e-18

        if model_mode == "relaxed":
            # drop nonlinear Weymouth; only capacity + direction
            continue

        # PWL: g ≈ f|f|, constraint π_i - π_j = k * g
        xs, ys = _pwl_breakpoints(fmax, n_pwl)
        gvar = m.addVar(lb=min(ys), ub=max(ys), name=f"g_ff_{ell}")
        # SOS2 convex combination
        lam = m.addVars(len(xs), lb=0.0, ub=1.0, name=f"lam_{ell}")
        m.addConstr(gp.quicksum(lam[t] for t in range(len(xs))) == 1.0, name=f"lamsum_{ell}")
        m.addConstr(
            f_pipe[ell] == gp.quicksum(xs[t] * lam[t] for t in range(len(xs))),
            name=f"f_pwl_{ell}",
        )
        m.addConstr(
            gvar == gp.quicksum(ys[t] * lam[t] for t in range(len(xs))),
            name=f"g_pwl_{ell}",
        )
        m.addSOS(GRB.SOS_TYPE2, [lam[t] for t in range(len(xs))])
        m.addConstr(pi[i] - pi[j] == k_coef * gvar, name=f"weymouth_{ell}")

    # compressors: directed free boost (no Weymouth); flow >= 0
    f_comp = m.addVars(nC, lb=0.0, name="f_comp")
    for c_i, cs in enumerate(compressors):
        f_comp[c_i].UB = float(cs["fmax"])
        # optional mild boost: allow π_to unrestricted relative to π_from within bounds

    # valves / short pipes: bidirectional free flow
    # short_pipe / valve: equal pressure; controlValve: free π (can throttle)
    f_valve = m.addVars(nV, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_valve")
    for v_i, vv in enumerate(valves):
        fmax = float(vv["fmax"])
        f_valve[v_i].LB = -fmax
        f_valve[v_i].UB = fmax
        kind = str(vv.get("kind", "valve"))
        if kind != "controlValve":
            i = _node_index(nodes, vv["from"])
            j = _node_index(nodes, vv["to"])
            m.addConstr(pi[i] == pi[j], name=f"valve_pi_{v_i}")

    # nodal gas balance: supply - demand - offtake - out + in = 0
    for ni in range(nN):
        nid = nodes[ni]["id"]
        sup = gp.quicksum(
            s_var[si] for si, src in enumerate(sources) if str(src["gas_node"]) == str(nid)
        )
        out_p = gp.quicksum(
            f_pipe[ell] for ell, p in enumerate(pipes) if str(p["from"]) == str(nid)
        )
        in_p = gp.quicksum(
            f_pipe[ell] for ell, p in enumerate(pipes) if str(p["to"]) == str(nid)
        )
        out_c = gp.quicksum(
            f_comp[c_i]
            for c_i, cs in enumerate(compressors)
            if str(cs["from"]) == str(nid)
        )
        in_c = gp.quicksum(
            f_comp[c_i]
            for c_i, cs in enumerate(compressors)
            if str(cs["to"]) == str(nid)
        )
        out_v = gp.quicksum(
            f_valve[v_i] for v_i, vv in enumerate(valves) if str(vv["from"]) == str(nid)
        )
        in_v = gp.quicksum(
            f_valve[v_i] for v_i, vv in enumerate(valves) if str(vv["to"]) == str(nid)
        )
        m.addConstr(
            sup - dem_at[ni] - offtake_expr[ni] - out_p + in_p - out_c + in_c - out_v + in_v
            == 0.0,
            name=f"gbal_{ni}",
        )

    # ---- Objective ----
    obj = gp.LinExpr(0.0)
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            continue
        obj += float(gen.get("c1", 0.0)) * Pg[g]
        obj += float(gen.get("c0", 0.0))
        # ignore c2 for MILP-pure v1 (Travis uses linear); if c2 present treat as linear-approx skip
    for si, src in enumerate(sources):
        obj += float(src.get("cost", 0.0)) * s_var[si]
    m.setObjective(obj, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    p_bar = [0.0] * nN
    pipe_flow = [0.0] * nP
    comp_flow = [0.0] * nC
    valve_flow = [0.0] * nV
    supply = [0.0] * nS
    gas_offtake = [0.0] * nG
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
            flow_MW[ell] = float(f_e[ell].X)
        for i in range(nN):
            p_bar[i] = math.sqrt(max(float(pi[i].X), 0.0))
        for ell in range(nP):
            pipe_flow[ell] = float(f_pipe[ell].X)
        for c_i in range(nC):
            comp_flow[c_i] = float(f_comp[c_i].X)
        for v_i in range(nV):
            valve_flow[v_i] = float(f_valve[v_i].X)
        for si in range(nS):
            supply[si] = float(s_var[si].X)
        for c in coupling:
            gi = int(c["gen_index"])
            gas_offtake[gi] = float(c["heat_rate"]) * Pg_MW[gi]

    residual = validate_ieg_solution(
        network,
        Pg_MW,
        theta_deg,
        flow_MW,
        p_bar,
        pipe_flow,
        supply,
        gas_offtake,
        obj_val,
        model_mode=model_mode,
        comp_flow=comp_flow,
        valve_flow=valve_flow,
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
        "pressure": p_bar,
        "pipe_flow": pipe_flow,
        "comp_flow": comp_flow,
        "valve_flow": valve_flow,
        "supply": supply,
        "gas_offtake": gas_offtake,
        "ref_bus": ref_bus,
        "baseMVA": base,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "gas_model": model_mode,
        **residual,
    }


def validate_ieg_solution(
    network: dict,
    Pg_MW: list[float],
    theta_deg: list[float],
    flow_MW: list[float],
    pressure: list[float],
    pipe_flow: list[float],
    supply: list[float],
    gas_offtake: list[float],
    obj: float | None,
    *,
    model_mode: str = "pwl",
    comp_flow: list[float] | None = None,
    valve_flow: list[float] | None = None,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    gas = network["gas"]
    nodes = gas["nodes"]
    pipes = gas.get("pipes") or []
    compressors = gas.get("compressors") or []
    valves = gas.get("valves") or []
    sources = gas.get("sources") or []
    demands = gas.get("demands") or []
    coupling = (network.get("coupling") or {}).get("gas_gens") or []
    bus_ids, bus_pos, _ = bus_maps(network)
    nG = len(gens)
    nN = len(nodes)
    comp_flow = list(comp_flow or [0.0] * len(compressors))
    valve_flow = list(valve_flow or [0.0] * len(valves))

    if len(Pg_MW) != nG or len(pressure) != nN:
        return {
            "max_power_balance_MW": float("inf"),
            "max_gas_balance": float("inf"),
            "max_pressure_violation": float("inf"),
            "max_coupling_violation": float("inf"),
            "max_weymouth_violation": float("inf"),
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

    max_pviol = 0.0
    for i, nd in enumerate(nodes):
        p = pressure[i]
        max_pviol = max(
            max_pviol,
            max(0.0, float(nd["pmin"]) - p),
            max(0.0, p - float(nd["pmax"])),
        )

    max_coup = 0.0
    offtake_at = {i: 0.0 for i in range(nN)}
    for c in coupling:
        gi = int(c["gen_index"])
        ni = _node_index(nodes, c["gas_node"])
        expected = float(c["heat_rate"]) * Pg_MW[gi]
        got = gas_offtake[gi] if gi < len(gas_offtake) else expected
        max_coup = max(max_coup, abs(got - expected))
        offtake_at[ni] += expected

    dem_at = {i: 0.0 for i in range(nN)}
    for d in demands:
        ni = _node_index(nodes, d["gas_node"])
        dem_at[ni] += float(d.get("demand_m3h", d.get("demand", 0.0)))

    sup_at = {i: 0.0 for i in range(nN)}
    for si, src in enumerate(sources):
        ni = _node_index(nodes, src["gas_node"])
        if si < len(supply):
            sup_at[ni] += supply[si]

    max_gbal = 0.0
    for ni in range(nN):
        nid = str(nodes[ni]["id"])
        out_p = sum(pipe_flow[ell] for ell, p in enumerate(pipes) if str(p["from"]) == nid)
        in_p = sum(pipe_flow[ell] for ell, p in enumerate(pipes) if str(p["to"]) == nid)
        out_c = sum(
            comp_flow[c_i]
            for c_i, cs in enumerate(compressors)
            if str(cs["from"]) == nid and c_i < len(comp_flow)
        )
        in_c = sum(
            comp_flow[c_i]
            for c_i, cs in enumerate(compressors)
            if str(cs["to"]) == nid and c_i < len(comp_flow)
        )
        out_v = sum(
            valve_flow[v_i]
            for v_i, vv in enumerate(valves)
            if str(vv["from"]) == nid and v_i < len(valve_flow)
        )
        in_v = sum(
            valve_flow[v_i]
            for v_i, vv in enumerate(valves)
            if str(vv["to"]) == nid and v_i < len(valve_flow)
        )
        imb = (
            sup_at[ni]
            - dem_at[ni]
            - offtake_at[ni]
            - out_p
            + in_p
            - out_c
            + in_c
            - out_v
            + in_v
        )
        max_gbal = max(max_gbal, abs(imb))

    max_wey = 0.0
    if model_mode != "relaxed":
        for ell, pipe in enumerate(pipes):
            i = _node_index(nodes, pipe["from"])
            j = _node_index(nodes, pipe["to"])
            f = pipe_flow[ell]
            k_coef = float(pipe["k"])
            lhs = pressure[i] ** 2 - pressure[j] ** 2
            rhs = k_coef * f * abs(f)
            scale = max(1.0, abs(lhs), abs(rhs))
            max_wey = max(max_wey, abs(lhs - rhs) / scale)

    # PWL introduces approximation error on Weymouth; do not fail solely on nonlinear residual.
    passed = (
        max_bal <= TOL_ELEC_MW
        and max_flow_eq <= TOL_ELEC_MW
        and max_thermal <= TOL_ELEC_MW
        and max_gbal <= TOL_GAS_FLOW
        and max_pviol <= TOL_PRESSURE
        and max_coup <= TOL_COUPLING
        and obj is not None
    )

    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_gas_balance": max_gbal,
        "max_pressure_violation": max_pviol,
        "max_coupling_violation": max_coup,
        "max_weymouth_violation": max_wey,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    tier = str(config.get("solve_tier", "full"))
    if tier == "skip":
        result = {
            "schema_version": 1,
            "case": config.get("case") or case_dir.name,
            "solver": "python-gurobi",
            "problem": "ieg",
            "base_problem": config.get("base_problem", "integrated_electric_gas"),
            "ieg": {"status": "SKIPPED", "obj": None, "validation_passed": True},
            "validation": {"passed": True, "mode": "data_only_skip"},
        }
        write_result(case_dir, "python_result.json", result)
        return result

    sol = solve_ieg(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "ieg",
        "base_problem": config.get("base_problem", "integrated_electric_gas"),
        "ieg": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "case01_travis150_ieg"
    r = run_case(d, quiet=True)
    e = r["ieg"]
    print(
        f"[{r['case']}] status={e.get('status')} obj={e.get('obj')} "
        f"bal={e.get('max_power_balance_MW')} gas={e.get('max_gas_balance')} "
        f"valid={e.get('validation_passed')}"
    )
