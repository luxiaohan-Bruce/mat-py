"""Distribution service restoration MILP (v1).

Fault isolation + switch reconfiguration + critical load restoration.

max  sum_i w_i * Pd_i * x_i
s.t. binary switch status z
     single-root radial tree on energized set (commodity + cardinality)
     faulted branches forced open
     capacity-constrained transport power balance
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path):
    case_dir = Path(case_dir)
    net = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    cfg = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    return net, cfg


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }.get(m.Status, str(m.Status))


def solve_restore(net: dict, cfg: dict, quiet: bool = True) -> dict[str, Any]:
    buses = net["buses"]
    branches = net["branches"]
    sources = list(net.get("sources") or [])
    nB, nL = len(buses), len(branches)
    if not sources:
        root = int(net.get("root_bus", 1))
        sources = [{"bus": root, "Pmax": float(net.get("root_Pmax", 1e4)), "name": "root"}]
    nS = len(sources)

    faulted = set(int(x) for x in (cfg.get("faulted_branches") or net.get("faulted_branches") or []))
    weights = cfg.get("load_weights") or net.get("load_weights") or {}
    w = []
    for b in buses:
        bid = int(b["bus_i"])
        w.append(float(weights.get(str(bid), weights.get(bid, b.get("weight", 1.0)))))

    bus_pos = {int(buses[b]["bus_i"]): b for b in range(nB)}
    # Primary radiality root = first source (substation); extra sources are DG injections.
    root_bus = int(sources[0]["bus"])
    root_idx = bus_pos[root_bus]
    M_comm = float(nB)

    m = gp.Model("dist_restore")
    m.Params.OutputFlag = 0 if quiet else 1
    m.Params.MIPGap = float(cfg.get("mip_gap", 0.01))
    m.Params.TimeLimit = float(cfg.get("time_limit", 180))
    m.Params.Seed = int(cfg.get("seed", 1))
    m.Params.Threads = int(cfg.get("threads", 0))

    z = m.addVars(nL, vtype=GRB.BINARY, name="z")
    y = m.addVars(nB, vtype=GRB.BINARY, name="y")
    x = m.addVars(nB, lb=0.0, ub=1.0, name="x")
    P = m.addVars(nL, lb=-GRB.INFINITY, name="P")
    f = m.addVars(nL, lb=-GRB.INFINITY, name="f")
    Pg = m.addVars(nS, lb=0.0, name="Pg")

    obj = gp.quicksum(w[b] * float(buses[b]["Pd"]) * x[b] for b in range(nB))
    m.setObjective(obj, GRB.MAXIMIZE)

    m.addConstr(y[root_idx] == 1, name="root_on")

    for ell, br in enumerate(branches):
        bid = int(br["id"])
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        rate = max(float(br.get("rate", 1.0)), 1e-3)
        m.addConstr(z[ell] <= y[i], name=f"zyi_{ell}")
        m.addConstr(z[ell] <= y[j], name=f"zyj_{ell}")
        if bid in faulted or int(br.get("status", 1)) == 0 or br.get("faulted", False):
            m.addConstr(z[ell] == 0, name=f"fault_{ell}")
        elif not br.get("switchable", True):
            m.addConstr(z[ell] >= y[i] + y[j] - 1, name=f"fixed_{ell}")
        m.addConstr(P[ell] <= rate * z[ell], name=f"Pmax_{ell}")
        m.addConstr(P[ell] >= -rate * z[ell], name=f"Pmin_{ell}")
        m.addConstr(f[ell] <= M_comm * z[ell], name=f"fmax_{ell}")
        m.addConstr(f[ell] >= -M_comm * z[ell], name=f"fmin_{ell}")

    for s, src in enumerate(sources):
        pmax = float(src["Pmax"])
        bi = bus_pos[int(src["bus"])]
        m.addConstr(Pg[s] <= pmax, name=f"Pgmax_{s}")
        m.addConstr(Pg[s] <= pmax * y[bi], name=f"Pg_y_{s}")

    for b in range(nB):
        m.addConstr(x[b] <= y[b], name=f"xy_{b}")

    for b in range(nB):
        bid = int(buses[b]["bus_i"])
        pd = float(buses[b]["Pd"])
        bal = gp.LinExpr()
        for ell, br in enumerate(branches):
            i = int(br["fbus"])
            j = int(br["tbus"])
            if i == bid:
                bal -= P[ell]
            if j == bid:
                bal += P[ell]
        inj = -pd * x[b]
        for s, src in enumerate(sources):
            if int(src["bus"]) == bid:
                inj += Pg[s]
        m.addConstr(bal + inj == 0.0, name=f"bal_{b}")

    # Single-root commodity connectivity
    for b in range(nB):
        bid = int(buses[b]["bus_i"])
        cbal = gp.LinExpr()
        for ell, br in enumerate(branches):
            i = int(br["fbus"])
            j = int(br["tbus"])
            if i == bid:
                cbal -= f[ell]
            if j == bid:
                cbal += f[ell]
        if bid != root_bus:
            m.addConstr(cbal == y[b], name=f"comm_{b}")

    # Spanning tree on energized set: |E| = |V| - 1
    m.addConstr(
        gp.quicksum(z[ell] for ell in range(nL)) == gp.quicksum(y[b] for b in range(nB)) - 1,
        name="radial_card",
    )

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    if m.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "n_bus": nB,
            "n_branch": nL,
            "n_source": nS,
            "root_bus": root_bus,
            "faulted_branches": sorted(faulted),
            "validation_passed": False,
        }

    z_val = [float(z[ell].X) for ell in range(nL)]
    y_val = [float(y[b].X) for b in range(nB)]
    x_val = [float(x[b].X) for b in range(nB)]
    P_val = [float(P[ell].X) for ell in range(nL)]
    Pg_val = [float(Pg[s].X) for s in range(nS)]
    obj_val = float(m.ObjVal)

    closed = [int(branches[ell]["id"]) for ell in range(nL) if z_val[ell] >= 0.5]
    opened = [int(branches[ell]["id"]) for ell in range(nL) if z_val[ell] < 0.5]
    energized = [int(buses[b]["bus_i"]) for b in range(nB) if y_val[b] >= 0.5]
    served = sum(float(buses[b]["Pd"]) * x_val[b] for b in range(nB))
    total_pd = sum(float(b["Pd"]) for b in buses)
    weighted_served = sum(w[b] * float(buses[b]["Pd"]) * x_val[b] for b in range(nB))

    residual = _validate(
        net, sources, root_bus, faulted, z_val, y_val, x_val, P_val, Pg_val
    )

    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": float(m.ObjBound) if m.IsMIP else obj_val,
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "n_bus": nB,
        "n_branch": nL,
        "n_source": nS,
        "n_binary": int(m.NumBinVars),
        "root_bus": root_bus,
        "faulted_branches": sorted(faulted),
        "closed_branches": closed,
        "opened_branches": opened,
        "energized_buses": energized,
        "z": z_val,
        "y": y_val,
        "x": x_val,
        "P": P_val,
        "Pg": Pg_val,
        "served_MW": served,
        "total_demand_MW": total_pd,
        "unserved_MW": total_pd - served,
        "weighted_served": weighted_served,
        "n_closed": sum(1 for v in z_val if v >= 0.5),
        "n_energized": sum(1 for v in y_val if v >= 0.5),
        **residual,
    }


def _validate(net, sources, root_bus, faulted, z_val, y_val, x_val, P_val, Pg_val) -> dict[str, Any]:
    buses = net["buses"]
    branches = net["branches"]
    nB, nL = len(buses), len(branches)
    tol_bal = 1e-4
    tol_th = 1e-4
    tol_int = 1e-6

    max_int = 0.0
    for v in z_val + y_val:
        max_int = max(max_int, min(abs(v - 0.0), abs(v - 1.0)))

    max_fault_z = 0.0
    max_fault_flow = 0.0
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        if bid in faulted or br.get("faulted", False) or int(br.get("status", 1)) == 0:
            max_fault_z = max(max_fault_z, z_val[ell])
            max_fault_flow = max(max_fault_flow, abs(P_val[ell]))

    max_thermal = 0.0
    for ell, br in enumerate(branches):
        rate = max(float(br.get("rate", 1.0)), 1e-3)
        max_thermal = max(
            max_thermal, max(0.0, abs(P_val[ell]) - rate * max(z_val[ell], 0.0) - 1e-9)
        )

    source_inj = defaultdict(float)
    for s, src in enumerate(sources):
        source_inj[int(src["bus"])] += Pg_val[s]

    max_bal = 0.0
    for b in range(nB):
        bid = int(buses[b]["bus_i"])
        pd = float(buses[b]["Pd"]) * x_val[b]
        flow = 0.0
        for ell, br in enumerate(branches):
            if int(br["fbus"]) == bid:
                flow -= P_val[ell]
            if int(br["tbus"]) == bid:
                flow += P_val[ell]
        max_bal = max(max_bal, abs(flow + source_inj.get(bid, 0.0) - pd))

    max_xy = 0.0
    for b in range(nB):
        max_xy = max(max_xy, max(0.0, x_val[b] - y_val[b] - 1e-9))

    parent = list(range(nB))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    bus_pos = {int(buses[b]["bus_i"]): b for b in range(nB)}
    n_closed_energized = 0
    for ell, br in enumerate(branches):
        if z_val[ell] < 0.5:
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if y_val[i] >= 0.5 and y_val[j] >= 0.5:
            n_closed_energized += 1
            union(i, j)

    comps = defaultdict(list)
    for b in range(nB):
        if y_val[b] >= 0.5:
            comps[find(b)].append(b)
    n_islands = len(comps)
    n_energized = sum(1 for b in range(nB) if y_val[b] >= 0.5)
    root_idx = bus_pos[int(root_bus)]

    islands_without_source = 0
    for members in comps.values():
        # v1: single root must be in the only energized component(s)
        if root_idx not in members:
            islands_without_source += 1

    radial_violation = max(0, n_closed_energized - max(n_energized - n_islands, 0))
    # tree: one component containing root, edges = nodes - 1
    tree_ok = (
        n_islands == 1
        and n_energized >= 1
        and n_closed_energized == n_energized - 1
        and root_idx in next(iter(comps.values()))
    ) or (n_energized == 1 and n_closed_energized == 0 and y_val[root_idx] >= 0.5)

    isolation_ok = max_fault_z <= 0.5 + tol_int and max_fault_flow <= tol_bal
    radial_ok = tree_ok and radial_violation == 0 and islands_without_source == 0
    bal_ok = max_bal <= tol_bal
    thermal_ok = max_thermal <= tol_th
    xy_ok = max_xy <= tol_int
    int_ok = max_int <= 1e-4

    return {
        "max_power_balance_MW": max_bal,
        "max_thermal_viol_MW": max_thermal,
        "max_fault_z": max_fault_z,
        "max_fault_flow_MW": max_fault_flow,
        "max_xy_viol": max_xy,
        "max_int_resid": max_int,
        "n_islands": n_islands,
        "n_closed_energized": n_closed_energized,
        "radial_edge_excess": radial_violation,
        "islands_without_source": islands_without_source,
        "isolation_ok": isolation_ok,
        "radiality_ok": radial_ok,
        "validation_passed": isolation_ok and radial_ok and bal_ok and thermal_ok and xy_ok and int_ok,
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    net, cfg = load_case(case_dir)
    if cfg.get("solve_tier") == "skip" or cfg.get("problem") == "profile_meta":
        result = {
            "schema_version": 1,
            "case": case_dir.name,
            "solver": "python-gurobipy",
            "problem": cfg.get("problem"),
            "restore": {"status": "SKIPPED", "obj": None, "note": "meta/profile only"},
        }
        (case_dir / "results").mkdir(exist_ok=True)
        (case_dir / "results" / "python_result.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        return result
    sol = solve_restore(net, cfg, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": cfg.get("problem", "dist_restore"),
        "restore": sol,
    }
    (case_dir / "results").mkdir(exist_ok=True)
    (case_dir / "results" / "python_result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
