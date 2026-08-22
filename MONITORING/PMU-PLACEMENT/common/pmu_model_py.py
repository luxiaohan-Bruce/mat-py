"""Optimal PMU Placement — bus observability 0-1 MILP (gurobipy).

min  sum_i cost_i * y_i
s.t. for each bus j: y_j + sum_{i neighbor j} y_i >= 1
A PMU at bus i observes i and all adjacent buses (via online branches).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from dc_network import bus_maps  # noqa: E402
from result_io import load_case, write_result  # noqa: E402
from tolerances import solver_params_from_config  # noqa: E402


def adjacency(network: dict) -> dict[int, set[int]]:
    bus_ids, _, _ = bus_maps(network)
    adj = {b: {b} for b in bus_ids}
    for br in network["branches"]:
        if int(br.get("status", 1)) != 1:
            continue
        f, t = int(br["fbus"]), int(br["tbus"])
        adj[f].add(t)
        adj[t].add(f)
    return adj


def solve_pmu(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    bus_ids, bus_pos, _ = bus_maps(network)
    nB = len(bus_ids)
    adj = adjacency(network)
    params = solver_params_from_config(config)
    costs = config.get("pmu_cost") or {}
    cost = [float(costs.get(str(b), costs.get(b, 1.0))) for b in bus_ids]

    m = gp.Model("pmu")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    y = m.addVars(nB, vtype=GRB.BINARY, name="y")
    m.setObjective(gp.quicksum(cost[i] * y[i] for i in range(nB)), GRB.MINIMIZE)

    # observability: for bus j, some PMU that covers j.
    # n1_observability: every bus remains covered after loss of any one PMU,
    # i.e. double coverage except buses whose covering set has size 1.
    # pmu_channels: each PMU observes its own bus plus at most K neighbors
    # (assignment binaries x[i,j]); classic channel-limited OPP.
    n1 = bool(config.get("n1_observability"))
    channels = config.get("pmu_channels")
    K = int(channels) if channels not in (None, "", 0, "0") else 0
    covering_of: list[list[int]] = []
    idx = {b: i for i, b in enumerate(bus_ids)}
    if K > 0:
        neighbors: list[list[int]] = []
        for bi in bus_ids:
            nbs = [idx[n] for n in adj[bi] if n != bi]
            neighbors.append(nbs)
        x = {}
        for i in range(nB):
            for j in neighbors[i]:
                x[i, j] = m.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")
            m.addConstr(
                gp.quicksum(x[i, j] for j in neighbors[i]) <= K * y[i],
                name=f"chan_{i}",
            )
            for j in neighbors[i]:
                m.addConstr(x[i, j] <= y[i], name=f"link_{i}_{j}")
        for j, bid in enumerate(bus_ids):
            covering_of.append([j] + neighbors[j])
            terms = [y[j]] + [x[i, j] for i in neighbors[j]]
            rhs = 2 if n1 and len(terms) >= 2 else 1
            m.addConstr(gp.quicksum(terms) >= rhs, name=f"obs_{bid}")
    else:
        for j, bid in enumerate(bus_ids):
            covering = [
                i
                for i, bi in enumerate(bus_ids)
                if bid in adj[bi]
            ]
            covering_of.append(covering)
            rhs = 2 if n1 and len(covering) >= 2 else 1
            m.addConstr(gp.quicksum(y[i] for i in covering) >= rhs, name=f"obs_{bid}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
    }.get(m.Status, str(m.Status))

    y_val = [0.0] * nB
    placed = []
    obj = None
    if m.SolCount > 0:
        obj = float(m.ObjVal)
        for i in range(nB):
            y_val[i] = float(y[i].X)
            if y_val[i] > 0.5:
                placed.append(bus_ids[i])
    # check observability (N-1 / channel-limited when requested)
    if K > 0 and m.SolCount > 0:
        cover_count = {b: 0 for b in bus_ids}
        for i, bi in enumerate(bus_ids):
            if y_val[i] <= 0.5:
                continue
            cover_count[bi] += 1
            for j in neighbors[i]:
                if float(x[i, j].X) > 0.5:
                    cover_count[bus_ids[j]] += 1
    else:
        cover_count = {b: 0 for b in bus_ids}
        for bi in placed:
            for nb in adj[bi]:
                cover_count[nb] += 1
    all_obs = True
    for j, bid in enumerate(bus_ids):
        covering = covering_of[j] if j < len(covering_of) else []
        need = 2 if n1 and len(covering) >= 2 else 1
        if cover_count[bid] < need:
            all_obs = False
            break
    n_pmu = len(placed)
    return {
        "status": status,
        "obj": obj,
        "obj_bound": float(m.ObjBound) if m.SolCount else None,
        "mip_gap": float(m.MIPGap) if m.IsMIP and m.SolCount else 0.0,
        "runtime": runtime,
        "y": {str(bus_ids[i]): y_val[i] for i in range(nB)},
        "placed_buses": sorted(placed),
        "n_pmu": n_pmu,
        "all_observable": all_obs,
        "n1_observability": n1,
        "pmu_channels": K or None,
        "validation_passed": bool(all_obs and status in ("OPTIMAL", "TIME_LIMIT") and obj is not None),
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_pmu(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "pmu",
        "base_problem": "pmu_placement",
        "pmu": sol,
        "validation": {"passed": sol["validation_passed"]},
    }
    write_result(case_dir, "python_result.json", result)
    return result
