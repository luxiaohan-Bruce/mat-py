"""Experimental multiperiod active-power transport model for distribution examples."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path):
    case_dir = Path(case_dir)
    net = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    cfg = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    return net, cfg


def solve_dnr(net: dict, cfg: dict, quiet: bool = True) -> dict[str, Any]:
    buses = net["buses"]
    branches = net["branches"]
    storage = net.get("storage") or []
    mults = [float(x) for x in (net.get("load_mult") or [1.0])]
    T = int(cfg.get("T", len(mults)))
    mults = mults[:T]
    root = int(net.get("root_bus", 1)) - 1
    nB, nL, nS = len(buses), len(branches), len(storage)
    max_act = int(cfg.get("max_switch_actions", 5))

    m = gp.Model("dnr")
    m.Params.OutputFlag = 0 if quiet else 1
    m.Params.MIPGap = float(cfg.get("mip_gap", 0.01))
    m.Params.TimeLimit = float(cfg.get("time_limit", 120))
    m.Params.Seed = int(cfg.get("seed", 1))
    m.Params.Threads = int(cfg.get("threads", 0))

    z = m.addVars(nL, vtype=GRB.BINARY, name="z")
    P = m.addVars(nL, T, lb=-GRB.INFINITY, name="P")
    shed = m.addVars(nB, T, lb=0.0, name="shed")
    sP = m.addVars(nL, T, lb=0.0, name="sP")
    Pc = m.addVars(nS, T, lb=0.0, name="Pc")
    Pd = m.addVars(nS, T, lb=0.0, name="Pd")
    E = m.addVars(nS, T, lb=0.0, name="E")

    for ell, br in enumerate(branches):
        if not br.get("switchable", False):
            m.addConstr(z[ell] == 1)
    sw = [ell for ell, br in enumerate(branches) if br.get("switchable")]
    if sw:
        m.addConstr(gp.quicksum(1 - z[ell] for ell in sw) <= max_act)

    pen = 1e4
    obj = gp.quicksum(float(branches[ell]["r"]) * sP[ell, t] for ell in range(nL) for t in range(T))
    obj += pen * gp.quicksum(shed[b, t] for b in range(nB) for t in range(T))
    m.setObjective(obj, GRB.MINIMIZE)

    for t, mult in enumerate(mults):
        for ell, br in enumerate(branches):
            rate = max(float(br["rate"]), 1.0)
            m.addConstr(sP[ell, t] >= P[ell, t])
            m.addConstr(sP[ell, t] >= -P[ell, t])
            m.addConstr(P[ell, t] <= rate * z[ell])
            m.addConstr(P[ell, t] >= -rate * z[ell])
        for b in range(nB):
            if b == root:
                continue
            pd = float(buses[b]["Pd"]) * mult
            bal = gp.LinExpr()
            for ell, br in enumerate(branches):
                i = int(br["fbus"]) - 1
                j = int(br["tbus"]) - 1
                if i == b:
                    bal -= P[ell, t]
                if j == b:
                    bal += P[ell, t]
            inj = -pd + shed[b, t]
            for s, st in enumerate(storage):
                if int(st["bus"]) - 1 == b:
                    inj += Pd[s, t] - Pc[s, t]
            m.addConstr(bal == inj)
            m.addConstr(shed[b, t] <= max(pd, 0.0) + 1e-6)
        for s, st in enumerate(storage):
            pmax = float(st["Pmax"])
            emax = float(st["Emax"])
            e0 = float(st["E0"])
            eta_c = float(st["eta_c"])
            eta_d = max(float(st["eta_d"]), 1e-6)
            m.addConstr(Pc[s, t] <= pmax)
            m.addConstr(Pd[s, t] <= pmax)
            m.addConstr(E[s, t] <= emax)
            if t == 0:
                m.addConstr(E[s, t] == e0 + eta_c * Pc[s, t] - Pd[s, t] / eta_d)
            else:
                m.addConstr(E[s, t] == E[s, t - 1] + eta_c * Pc[s, t] - Pd[s, t] / eta_d)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }.get(m.Status, str(m.Status))
    if m.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "T": T, "n_bus": nB, "n_branch": nL}
    opened = [int(branches[ell]["id"]) for ell in range(nL) if z[ell].X < 0.5]
    return {
        "status": status,
        "obj": float(m.ObjVal),
        "obj_bound": float(m.ObjBound) if m.IsMIP else float(m.ObjVal),
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "T": T,
        "n_bus": nB,
        "n_branch": nL,
        "n_storage": nS,
        "opened_branches": opened,
        "load_shed": float(sum(shed[b, t].X for b in range(nB) for t in range(T))),
        "n_binary": int(m.NumBinVars),
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    net, cfg = load_case(case_dir)
    sol = solve_dnr(net, cfg, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": cfg.get("problem", "dnr"),
        "base_problem": cfg.get("base_problem", "distribution_opf"),
        "dnr": sol,
    }
    (case_dir / "results").mkdir(exist_ok=True)
    (case_dir / "results" / "python_result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
