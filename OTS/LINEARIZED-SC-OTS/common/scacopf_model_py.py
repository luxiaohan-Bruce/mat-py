"""Linearized security-constrained DC OPF with optional topology switching."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path) -> tuple[dict, dict]:
    case_dir = Path(case_dir)
    with (case_dir / "data" / "network.json").open(encoding="utf-8") as f:
        network = json.load(f)
    with (case_dir / "data" / "config.json").open(encoding="utf-8") as f:
        config = json.load(f)
    return network, config


def _status_name(s: int) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
    }.get(s, str(s))


def solve_scacopf(network: dict, config: dict, quiet: bool = True) -> dict[str, Any]:
    return _solve_scacopf_core(network, config, quiet=quiet)


def _solve_scacopf_core(network: dict, config: dict, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = [g for g in network["gens"] if int(g.get("status", 1)) == 1]
    branches = [b for b in network["branches"] if int(b.get("status", 1)) == 1]
    cont_list = network.get("contingencies", [])  # selected subset
    switchable = set(int(x) for x in config.get("switchable_branches", []))
    max_open = int(config.get("max_open", 0))
    do_ots = bool(config.get("enable_ots", False)) and max_open > 0 and switchable

    bus_ids = [int(b["bus_i"]) for b in buses]
    bus_pos = {b: i for i, b in enumerate(bus_ids)}
    gens_at: dict[int, list[int]] = {bid: [] for bid in bus_ids}
    from_bus: dict[int, list[int]] = {bid: [] for bid in bus_ids}
    to_bus: dict[int, list[int]] = {bid: [] for bid in bus_ids}
    for g, gen in enumerate(gens):
        gens_at.setdefault(int(gen["bus"]), []).append(g)
    for ell, br in enumerate(branches):
        from_bus.setdefault(int(br["fbus"]), []).append(ell)
        to_bus.setdefault(int(br["tbus"]), []).append(ell)
    load_mw_of = {int(b["bus_i"]): float(b["Pd"]) for b in buses}
    ref = next((int(b["bus_i"]) for b in buses if int(b["type"]) == 3), bus_ids[0])
    ref_pos = bus_pos[ref]
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    # contingencies: 0=base + selected
    nC = 1 + len(cont_list)

    m = gp.Model(config.get("case", "scacopf"))
    m.Params.OutputFlag = 0 if quiet else 1
    m.Params.MIPGap = float(config.get("mip_gap", 0.01))
    m.Params.TimeLimit = float(config.get("time_limit", 120))
    m.Params.Seed = int(config.get("seed", 1))
    m.Params.Threads = int(config.get("threads", 0))

    Pg0 = m.addVars(nG, lb=0.0, name="Pg0")
    delta = m.addVars(nG, nC, lb=-GRB.INFINITY, name="dPg")  # redispatch; c=0 fixed 0
    shed = m.addVars(nB, nC, lb=0.0, name="shed")
    theta = m.addVars(nB, nC, lb=-math.pi, ub=math.pi, name="th")
    f = m.addVars(nL, nC, lb=-GRB.INFINITY, name="f")
    flow_slack = m.addVars(nL, nC, lb=0.0, name="fslk")  # thermal soft limit
    z = {}
    if do_ots:
        for ell, br in enumerate(branches):
            if int(br["id"]) in switchable:
                z[ell] = m.addVar(vtype=GRB.BINARY, name=f"z[{ell}]")
        if z:
            m.addConstr(gp.quicksum(z.values()) >= len(z) - max_open)

    # gen bounds base (relax Pmin to 0 for linearized feasibility)
    for g, gen in enumerate(gens):
        pmax = max(float(gen["Pmax"]), 0.0)
        m.addConstr(Pg0[g] >= 0.0)
        m.addConstr(Pg0[g] <= max(pmax, 1e-6))
        m.addConstr(delta[g, 0] == 0)

    # objective: base generation cost + shed + flow soft limit
    pen = float(config.get("load_shed_penalty", 1e4))
    flow_pen = float(config.get("flow_slack_penalty", 5e3))
    rate_scale = float(config.get("rate_scale", 1.2))
    obj = gp.quicksum(float(gen["c1"]) * Pg0[g] + float(gen.get("c0", 0.0)) for g, gen in enumerate(gens))
    obj += pen * gp.quicksum(shed[b, c] for b in range(nB) for c in range(nC))
    obj += flow_pen * gp.quicksum(flow_slack[ell, c] for ell in range(nL) for c in range(nC))
    m.setObjective(obj, GRB.MINIMIZE)

    bsus = []
    for br in branches:
        x = float(br["x"])
        tap = float(br.get("ratio") or 0.0) or 1.0
        bsus.append(1.0 / (x * tap * base) * base)  # 1/(x*tap) in p.u. with theta
        # flow in p.u. = b*(th_i-th_j); b=1/(x*tap)

    # map contingency outages
    branch_out = {c: set() for c in range(nC)}
    gen_out = {c: set() for c in range(nC)}
    for c, ct in enumerate(cont_list, start=1):
        if ct.get("branch"):
            brinfo = ct["branch"]
            for ell, br in enumerate(branches):
                if (
                    int(br["fbus"]) == int(brinfo["fbus"])
                    and int(br["tbus"]) == int(brinfo["tbus"])
                ) or (
                    int(br["fbus"]) == int(brinfo["tbus"])
                    and int(br["tbus"]) == int(brinfo["fbus"])
                ):
                    branch_out[c].add(ell)
        if ct.get("gen_bus") is not None:
            for g, gen in enumerate(gens):
                if int(gen["bus"]) == int(ct["gen_bus"]):
                    if ct.get("gen_id") is None or str(gen["id"]).strip() == str(ct["gen_id"]).strip():
                        gen_out[c].add(g)

    for c in range(nC):
        m.addConstr(theta[ref_pos, c] == 0)
        # participation / redispatch for c>0
        if c > 0:
            # outaged gens fixed delta = -Pg0 (offline)
            for g in gen_out[c]:
                m.addConstr(Pg0[g] + delta[g, c] == 0)
            # remaining gens: free within bounds, soft participation optional
            for g, gen in enumerate(gens):
                if g in gen_out[c]:
                    continue
                pmax = max(float(gen["Pmax"]), 0.0)
                m.addConstr(Pg0[g] + delta[g, c] >= 0.0)
                m.addConstr(Pg0[g] + delta[g, c] <= max(pmax, 1e-6))
        else:
            for g in range(nG):
                m.addConstr(delta[g, c] == 0)

        # flows
        for ell, br in enumerate(branches):
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            rate = (
                float(br["rateA"] if c == 0 else br.get("rateC", br["rateA"]))
                * rate_scale
                / base
            )
            out = ell in branch_out[c]
            bigM = 2 * math.pi * abs(bsus[ell]) + 10
            if out:
                m.addConstr(f[ell, c] == 0)
            elif do_ots and ell in z:
                m.addConstr(
                    f[ell, c]
                    <= bsus[ell] * (theta[i, c] - theta[j, c]) + bigM * (1 - z[ell])
                )
                m.addConstr(
                    f[ell, c]
                    >= bsus[ell] * (theta[i, c] - theta[j, c]) - bigM * (1 - z[ell])
                )
                m.addConstr(f[ell, c] <= rate * z[ell] + flow_slack[ell, c])
                m.addConstr(f[ell, c] >= -rate * z[ell] - flow_slack[ell, c])
            else:
                m.addConstr(f[ell, c] == bsus[ell] * (theta[i, c] - theta[j, c]))
                m.addConstr(f[ell, c] <= rate + flow_slack[ell, c])
                m.addConstr(f[ell, c] >= -rate - flow_slack[ell, c])

        # nodal balance p.u.
        for bi, bid in enumerate(bus_ids):
            load_mw = load_mw_of[bid]
            load = load_mw / base
            inj = -load + shed[bi, c] / base
            for g in gens_at.get(bid, []):
                inj += (Pg0[g] + delta[g, c]) / base
            flow = gp.LinExpr()
            for ell in from_bus.get(bid, []):
                flow += f[ell, c]
            for ell in to_bus.get(bid, []):
                flow -= f[ell, c]
            m.addConstr(flow == inj)
            # GO C1 uses negative Pd for fixed injections.  Those buses cannot
            # shed load; using Pd directly as a nonnegative variable's upper
            # bound made every such case infeasible before optimization.
            m.addConstr(shed[bi, c] <= max(load_mw, 0.0))

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m.Status)
    if m.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "n_bus": nB, "n_gen": nG, "n_branch": nL, "n_cont": nC - 1}

    opened: list[int] = []
    if do_ots:
        for ell, var in z.items():
            if var.X < 0.5:
                opened.append(int(branches[ell]["id"]))
    return {
        "status": status,
        "obj": float(m.ObjVal),
        "obj_bound": float(m.ObjBound) if m.IsMIP else float(m.ObjVal),
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "n_bus": nB,
        "n_gen": nG,
        "n_branch": nL,
        "n_cont": nC - 1,
        "load_shed_MW": float(sum(shed[b, c].X for b in range(nB) for c in range(nC))),
        "flow_slack_pu": float(sum(flow_slack[ell, c].X for ell in range(nL) for c in range(nC))),
        "opened_branches": opened,
        "enable_ots": bool(do_ots),
        "n_binary": int(m.NumBinVars),
        "n_variables": int(m.NumVars),
        "n_constraints": int(m.NumConstrs),
        "note": "linearized DC SC-OPF (not exact AC); documented approximation",
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_scacopf(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": config.get("problem", "linearized_sc_acopf"),
        "source": config.get("source", {}),
        "scacopf": sol,
    }
    out = case_dir / "results" / "python_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
