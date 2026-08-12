"""Controlled / intentional islanding MILP (gurobipy).

Decisions:
  z[i,k]   bus i assigned to island k
  closed[l] line l remains in service
  shed[i]  load shed (MW) at bus i
  Pg, f, theta  DC dispatch within islands
  root[i,k], commodity flows  connectivity of each non-empty island

Constraints:
  unique island assignment; line open across islands; DC balance/flow;
  coherency (same group → same island; different groups → different islands);
  commodity-flow connectivity with a generator root per used island.

Objective: min sum shed (+ optional open-line penalty).
"""

from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
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
# common_protocol helpers vendored in this common/ directory
from result_io import load_case, write_result  # noqa: E402
from tolerances import DEFAULT_TOLERANCES, solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }.get(m.Status, str(m.Status))


def _coherency_groups(config: dict) -> list[list[int]]:
    raw = config.get("coherency_groups") or []
    return [[int(g) for g in grp] for grp in raw if grp]


def solve_island(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    params = solver_params_from_config(config)

    groups = _coherency_groups(config)
    K = int(config.get("n_islands") or max(2, len(groups) if groups else 2))
    K = max(1, min(K, nB))
    switch_pen = float(config.get("switch_penalty", 1e-3))

    # gen capacity / load for big-M
    sum_pmax = sum(max(0.0, float(g.get("Pmax", 0.0))) for g in gens if int(g.get("status", 1)) == 1)
    sum_pd = sum(max(0.0, float(b.get("Pd", 0.0))) for b in buses)
    M_inj = max(sum_pmax + sum_pd, 1.0) * 2.0

    # buses with online gens
    has_gen = {bid: False for bid in bus_ids}
    online_gen_idx = []
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 1 and float(gen.get("Pmax", 0.0)) > 1e-9:
            has_gen[int(gen["bus"])] = True
            online_gen_idx.append(g)

    m = gp.Model("controlled_islanding")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    z = m.addVars(nB, K, vtype=GRB.BINARY, name="z")
    closed = m.addVars(nL, vtype=GRB.BINARY, name="closed")
    w = m.addVars(nL, K, lb=0.0, ub=1.0, name="w")
    theta = m.addVars(nB, lb=-2 * math.pi, ub=2 * math.pi, name="theta")
    Pg = m.addVars(nG, name="Pg")
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f")
    shed = m.addVars(nB, lb=0.0, name="shed")
    island_used = m.addVars(K, vtype=GRB.BINARY, name="island_used")
    root = m.addVars(nB, K, vtype=GRB.BINARY, name="root")
    cf_f = m.addVars(nL, lb=0.0, name="cf_f")  # commodity fbus -> tbus
    cf_t = m.addVars(nL, lb=0.0, name="cf_t")
    gen_c = m.addVars(nB, lb=0.0, name="gen_c")  # commodity injection at roots

    # unique assignment
    for i in range(nB):
        m.addConstr(gp.quicksum(z[i, k] for k in range(K)) == 1, name=f"assign_{i}")

    # island_used linking
    for k in range(K):
        for i in range(nB):
            m.addConstr(island_used[k] >= z[i, k], name=f"used_ge_{k}_{i}")
        m.addConstr(
            island_used[k] <= gp.quicksum(z[i, k] for i in range(nB)),
            name=f"used_le_{k}",
        )

    # line membership / open across islands
    for ell, br in enumerate(branches):
        fi = bus_pos[int(br["fbus"])]
        ti = bus_pos[int(br["tbus"])]
        offline = int(br.get("status", 1)) == 0
        if offline:
            m.addConstr(closed[ell] == 0, name=f"off_{ell}")
            for k in range(K):
                m.addConstr(w[ell, k] == 0, name=f"woff_{ell}_{k}")
            continue
        for k in range(K):
            m.addConstr(w[ell, k] <= z[fi, k], name=f"wf_{ell}_{k}")
            m.addConstr(w[ell, k] <= z[ti, k], name=f"wt_{ell}_{k}")
        m.addConstr(
            closed[ell] == gp.quicksum(w[ell, k] for k in range(K)),
            name=f"cl_{ell}",
        )

    # reference angle on global ref bus
    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    # generator bounds (Pmin relaxed to 0 for post-island redispatch)
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            Pg[g].LB = 0.0
            Pg[g].UB = 0.0
        else:
            Pg[g].LB = 0.0
            Pg[g].UB = max(0.0, float(gen["Pmax"]))

    # load shed bounds
    for i, b in enumerate(buses):
        Pd = max(0.0, float(b["Pd"]))
        shed[i].UB = Pd

    # DC flow with indicators on closed
    for ell, br in enumerate(branches):
        fi = bus_pos[int(br["fbus"])]
        ti = bus_pos[int(br["tbus"])]
        offline = int(br.get("status", 1)) == 0
        if offline:
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue
        # open => f = 0
        m.addGenConstrIndicator(closed[ell], False, f[ell] == 0.0, name=f"ind_f0_{ell}")
        rate = thermal_rate_mw(br)
        if rate > 0:
            m.addConstr(f[ell] <= rate, name=f"fmax_{ell}")
            m.addConstr(f[ell] >= -rate, name=f"fmin_{ell}")
        else:
            m.addConstr(f[ell] <= M_inj, name=f"fmax_{ell}")
            m.addConstr(f[ell] >= -M_inj, name=f"fmin_{ell}")
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addGenConstrIndicator(
                closed[ell], True, theta[fi] - theta[ti] == phi, name=f"ind_th_{ell}"
            )
        else:
            bsus, phi = branch_susceptance(br)
            # closed => f = base * b * (theta_f - theta_t - phi)
            m.addGenConstrIndicator(
                closed[ell],
                True,
                f[ell] == base * bsus * (theta[fi] - theta[ti] - phi),
                name=f"ind_phys_{ell}",
            )

    # nodal balance: gen - (Pd - shed) - out + in = 0
    for i, bid in enumerate(bus_ids):
        Pd = max(0.0, float(buses[i]["Pd"]))
        gen_sum = gp.quicksum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        m.addConstr(gen_sum - (Pd - shed[i]) - out_f + in_f == 0.0, name=f"bal_{bid}")

    # coherency: same group same island (skip pairs already on same bus)
    for gi, grp in enumerate(groups):
        if len(grp) < 2:
            continue
        g0 = grp[0]
        b0 = bus_pos[int(gens[g0]["bus"])]
        for g in grp[1:]:
            bi = bus_pos[int(gens[g]["bus"])]
            if bi == b0:
                continue
            for k in range(K):
                m.addConstr(z[b0, k] == z[bi, k], name=f"coh_{gi}_{g}_{k}")

    # different groups → different islands (pair group representatives)
    reps = []
    for grp in groups:
        if not grp:
            continue
        reps.append(bus_pos[int(gens[grp[0]]["bus"])])
    for a in range(len(reps)):
        for b in range(a + 1, len(reps)):
            for k in range(K):
                m.addConstr(z[reps[a], k] + z[reps[b], k] <= 1, name=f"sep_{a}_{b}_{k}")

    # force number of used islands when multiple coherency groups
    if len(groups) >= 2:
        m.addConstr(
            gp.quicksum(island_used[k] for k in range(K)) >= min(K, len(groups)),
            name="n_islands_min",
        )
    elif K >= 2:
        # free partition into up to K; still allow single island if no group split
        pass

    # connectivity: root only at gen buses in island; one root per used island
    for i, bid in enumerate(bus_ids):
        for k in range(K):
            m.addConstr(root[i, k] <= z[i, k], name=f"root_z_{i}_{k}")
            if not has_gen[bid]:
                m.addConstr(root[i, k] == 0, name=f"root_nogen_{i}_{k}")
    for k in range(K):
        m.addConstr(
            gp.quicksum(root[i, k] for i in range(nB)) == island_used[k],
            name=f"one_root_{k}",
        )

    # commodity capacity on closed lines
    cap_c = float(nB)
    for ell, br in enumerate(branches):
        if int(br.get("status", 1)) == 0:
            m.addConstr(cf_f[ell] == 0, name=f"cf0f_{ell}")
            m.addConstr(cf_t[ell] == 0, name=f"cf0t_{ell}")
        else:
            m.addConstr(cf_f[ell] + cf_t[ell] <= cap_c * closed[ell], name=f"cfc_{ell}")

    # commodity: every bus consumes 1; roots inject (connectivity within islands)
    for i, bid in enumerate(bus_ids):
        m.addConstr(
            gen_c[i] <= cap_c * gp.quicksum(root[i, k] for k in range(K)),
            name=f"gc_{bid}",
        )
        inflow = gp.quicksum(
            cf_f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        ) + gp.quicksum(
            cf_t[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        )
        outflow = gp.quicksum(
            cf_f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        ) + gp.quicksum(
            cf_t[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        )
        m.addConstr(inflow - outflow + gen_c[i] == 1.0, name=f"cmb_{bid}")

    # objective
    open_cost = gp.quicksum(
        switch_pen * (1 - closed[ell])
        for ell, br in enumerate(branches)
        if int(br.get("status", 1)) == 1
    )
    m.setObjective(gp.quicksum(shed[i] for i in range(nB)) + open_cost, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    island_of_bus = {str(bid): -1 for bid in bus_ids}
    closed_val = [0.0] * nL
    shed_val = [0.0] * nB
    Pg_MW = [0.0] * nG
    flow_MW = [0.0] * nL
    theta_deg = [0.0] * nB
    root_buses = []
    obj_val = None
    mip_gap = None
    obj_bound = None

    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        obj_bound = float(m.ObjBound)
        mip_gap = float(m.MIPGap) if m.IsMIP else 0.0
        for i, bid in enumerate(bus_ids):
            for k in range(K):
                if z[i, k].X > 0.5:
                    island_of_bus[str(bid)] = k
                    break
            shed_val[i] = float(shed[i].X)
            theta_deg[i] = math.degrees(float(theta[i].X))
        for ell in range(nL):
            closed_val[ell] = float(closed[ell].X)
            flow_MW[ell] = float(f[ell].X)
        for g in range(nG):
            Pg_MW[g] = float(Pg[g].X)
        for i, bid in enumerate(bus_ids):
            for k in range(K):
                if root[i, k].X > 0.5:
                    root_buses.append({"bus": bid, "island": k})

    open_lines = [
        int(branches[ell]["id"])
        for ell in range(nL)
        if closed_val[ell] < 0.5 and int(branches[ell].get("status", 1)) == 1
    ]
    total_shed = sum(shed_val)
    served = sum_pd - total_shed

    if m.SolCount > 0:
        residual = _validate(
            network,
            config,
            island_of_bus,
            closed_val,
            shed_val,
            Pg_MW,
            flow_MW,
            theta_deg,
            groups,
            K,
        )
    else:
        residual = {
            "unique_assignment": False,
            "coherency_ok": False,
            "group_separation_ok": False,
            "island_connected": False,
            "island_has_gen": False,
            "max_power_balance_MW": None,
            "max_flow_equation_MW": None,
            "max_thermal_violation_MW": None,
            "max_cross_island_flow_MW": None,
            "max_generator_bound_MW": None,
            "validation_passed": False,
        }

    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap if mip_gap is not None else 0.0,
        "runtime": runtime,
        "n_islands": K,
        "island_of_bus": island_of_bus,
        "closed": closed_val,
        "open_lines": open_lines,
        "n_open_lines": len(open_lines),
        "shed_MW": shed_val,
        "total_shed_MW": total_shed,
        "served_MW": served,
        "total_demand_MW": sum_pd,
        "Pg_MW": Pg_MW,
        "flow_MW": flow_MW,
        "theta_deg": theta_deg,
        "root_buses": root_buses,
        "coherency_groups": groups,
        "switch_penalty": switch_pen,
        "ref_bus": ref_bus,
        "baseMVA": base,
        **residual,
    }


def _validate(
    network,
    config,
    island_of_bus,
    closed_val,
    shed_val,
    Pg_MW,
    flow_MW,
    theta_deg,
    groups,
    K,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    tol = DEFAULT_TOLERANCES
    integ = tol["integrality"]

    # unique assignment
    assign_ok = True
    island_id = []
    for bid in bus_ids:
        k = int(island_of_bus[str(bid)])
        if k < 0 or k >= K:
            assign_ok = False
        island_id.append(k)

    max_bal = 0.0
    for i, bid in enumerate(bus_ids):
        Pd = max(0.0, float(buses[i]["Pd"]))
        sh = shed_val[i]
        gen_sum = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        max_bal = max(max_bal, abs(gen_sum - (Pd - sh) - out_f + in_f))
        if sh < -integ or sh > Pd + integ:
            assign_ok = False

    max_flow_eq = 0.0
    max_thermal = 0.0
    max_cross = 0.0  # flow on open or cross-island
    for ell, br in enumerate(branches):
        fi = int(br["fbus"])
        ti = int(br["tbus"])
        cl = closed_val[ell]
        same = island_of_bus[str(fi)] == island_of_bus[str(ti)] and island_of_bus[str(fi)] >= 0
        offline = int(br.get("status", 1)) == 0
        if offline or cl < 0.5:
            max_cross = max(max_cross, abs(flow_MW[ell]))
            continue
        if not same:
            max_cross = max(max_cross, abs(flow_MW[ell]) + 1.0)  # should not be closed
        i = bus_pos[fi]
        j = bus_pos[ti]
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
            max_thermal = max(max_thermal, max(0.0, abs(flow_MW[ell]) - rate - 1e-8))

    # coherency residual
    coh_ok = True
    for grp in groups:
        islands = set()
        for g in grp:
            if g < 0 or g >= len(gens):
                coh_ok = False
                continue
            bid = int(gens[g]["bus"])
            islands.add(int(island_of_bus[str(bid)]))
        if len(islands) > 1:
            coh_ok = False
    # inter-group separation
    rep_islands = []
    for grp in groups:
        if grp:
            bid = int(gens[grp[0]]["bus"])
            rep_islands.append(int(island_of_bus[str(bid)]))
    sep_ok = len(rep_islands) == len(set(rep_islands))

    # connectivity of each non-empty island via BFS on closed same-island edges
    island_buses: dict[int, list[int]] = defaultdict(list)
    for bid in bus_ids:
        island_buses[int(island_of_bus[str(bid)])].append(bid)
    adj: dict[int, set[int]] = {bid: set() for bid in bus_ids}
    for ell, br in enumerate(branches):
        if closed_val[ell] < 0.5 or int(br.get("status", 1)) == 0:
            continue
        f, t = int(br["fbus"]), int(br["tbus"])
        if island_of_bus[str(f)] != island_of_bus[str(t)]:
            continue
        adj[f].add(t)
        adj[t].add(f)
    conn_ok = True
    power_ok = True
    for k, members in island_buses.items():
        if k < 0 or not members:
            continue
        start = members[0]
        seen = {start}
        stack = [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v not in seen and v in members:
                    seen.add(v)
                    stack.append(v)
        if len(seen) != len(members):
            conn_ok = False
        # each non-empty island must contain at least one online gen
        if not any(has_gen_bus(gens, bid) for bid in members):
            power_ok = False

    max_gen = 0.0
    for g, gen in enumerate(gens):
        lo, hi = 0.0, 0.0
        if int(gen.get("status", 1)) == 1:
            hi = max(0.0, float(gen["Pmax"]))
        p = Pg_MW[g]
        max_gen = max(max_gen, max(0.0, lo - p), max(0.0, p - hi))

    passed = (
        assign_ok
        and coh_ok
        and sep_ok
        and conn_ok
        and power_ok
        and max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_cross <= tol["power_balance_mw"]
        and max_gen <= tol["generator_bound_mw"]
    )
    return {
        "unique_assignment": assign_ok,
        "coherency_ok": coh_ok,
        "group_separation_ok": sep_ok,
        "island_connected": conn_ok,
        "island_has_gen": power_ok,
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_cross_island_flow_MW": max_cross,
        "max_generator_bound_MW": max_gen,
        "validation_passed": bool(passed),
    }


def has_gen_bus(gens, bid: int) -> bool:
    for gen in gens:
        if int(gen.get("status", 1)) == 1 and int(gen["bus"]) == bid and float(gen.get("Pmax", 0)) > 1e-9:
            return True
    return False


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    tier = str(config.get("solve_tier", "full"))
    if tier == "skip":
        result = {
            "schema_version": 1,
            "case": config.get("case", case_dir.name),
            "solver": "python-gurobi",
            "problem": "controlled_islanding",
            "base_problem": "controlled_islanding",
            "island": {
                "status": "SKIPPED",
                "obj": None,
                "validation_passed": True,
                "note": "solve_tier=skip data-only",
                "n_bus": len(network["buses"]),
                "n_branch": len(network["branches"]),
                "n_gen": len(network["gens"]),
                "n_islands": config.get("n_islands"),
                "coherency_groups": config.get("coherency_groups"),
            },
            "validation": {"passed": True, "tier": "skip"},
        }
        write_result(case_dir, "python_result.json", result)
        return result

    sol = solve_island(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "controlled_islanding",
        "base_problem": "controlled_islanding",
        "island": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("-v", action="store_true")
    args = ap.parse_args()
    r = run_case(args.case_dir, quiet=not args.v)
    e = r["island"]
    print(f"[{r['case']}] {e.get('status')} obj={e.get('obj')} shed={e.get('total_shed_MW')} valid={e.get('validation_passed')}")
