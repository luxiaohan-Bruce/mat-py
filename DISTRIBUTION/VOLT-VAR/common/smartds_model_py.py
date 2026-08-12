"""SMART-DS aggregated linear DNR-like models (minimal feasible formulation)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path):
    case_dir = Path(case_dir)
    net = json.loads((case_dir / "data" / "network.json").read_text())
    cfg = json.loads((case_dir / "data" / "config.json").read_text())
    return net, cfg


def solve(net: dict, cfg: dict, quiet: bool = True) -> dict[str, Any]:
    mode = cfg.get("mode", "dnr")
    buses = net["buses"]
    branches = net["branches"]
    root = int(net.get("root_bus", 1)) - 1
    nB, nL = len(buses), len(branches)
    ders = net.get("der") or []
    shunts = net.get("shunts") or []

    m = gp.Model("smartds")
    m.Params.OutputFlag = 0 if quiet else 1
    m.Params.MIPGap = float(cfg.get("mip_gap", 0.01))
    m.Params.TimeLimit = float(cfg.get("time_limit", 120))
    m.Params.Seed = 1
    m.Params.Threads = 0

    z = m.addVars(nL, vtype=GRB.BINARY, name="z")
    P = m.addVars(nL, lb=-GRB.INFINITY, name="P")
    shed = m.addVars(nB, lb=0.0, name="shed")
    sP = m.addVars(nL, lb=0.0, name="sP")
    Pder = m.addVars(len(ders), lb=0.0, name="Pder") if mode == "hosting" else {}
    Qsh = m.addVars(len(shunts), lb=0.0, name="Qsh") if mode == "voltvar" else {}

    for ell, br in enumerate(branches):
        if not br.get("switchable"):
            m.addConstr(z[ell] == 1)
        rate = max(float(br["rate"]), 1.0)
        m.addConstr(sP[ell] >= P[ell])
        m.addConstr(sP[ell] >= -P[ell])
        m.addConstr(P[ell] <= rate * z[ell])
        m.addConstr(P[ell] >= -rate * z[ell])

    sw = [ell for ell, br in enumerate(branches) if br.get("switchable")]
    if sw:
        m.addConstr(gp.quicksum(1 - z[ell] for ell in sw) <= int(cfg.get("max_switch_actions", 4)))

    for b in range(nB):
        if b == root:
            continue
        pd = float(buses[b]["Pd"])
        bal = gp.LinExpr()
        for ell, br in enumerate(branches):
            i = int(br["fbus"]) - 1
            j = int(br["tbus"]) - 1
            if i == b:
                bal -= P[ell]
            if j == b:
                bal += P[ell]
        inj = -pd + shed[b]
        if mode == "hosting":
            for i, d in enumerate(ders):
                if int(d["bus"]) - 1 == b:
                    inj += Pder[i]
                    m.addConstr(Pder[i] <= float(d["Pmax"]))
        if mode == "voltvar":
            for i, sh in enumerate(shunts):
                if int(sh["bus"]) - 1 == b:
                    m.addConstr(Qsh[i] <= float(sh["Qmax"]))
        m.addConstr(bal == inj)
        m.addConstr(shed[b] <= max(pd, 0.0) + 1e-6)

    # Common transport+loss objective for dual MATLAB match; variant extras as constraints only.
    obj = gp.quicksum(float(br.get("r", 0.05)) * sP[ell] for ell, br in enumerate(branches))
    obj += 1e4 * gp.quicksum(shed[b] for b in range(nB))
    if mode == "hosting" and ders:
        # encourage DER: small secondary term kept tiny vs loss scale
        obj -= 0.01 * gp.quicksum(Pder[i] for i in range(len(ders)))
    if mode == "voltvar" and shunts:
        obj -= 0.01 * gp.quicksum(Qsh[i] for i in range(len(shunts)))
    m.setObjective(obj, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }.get(m.Status, str(m.Status))
    if m.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "mode": mode, "n_bus": nB}
    return {
        "status": status,
        "obj": float(m.ObjVal),
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "mode": mode,
        "n_bus": nB,
        "n_branch": nL,
        "opened": [int(branches[ell]["id"]) for ell in range(nL) if z[ell].X < 0.5],
        "load_shed": float(sum(shed[b].X for b in range(nB))),
        "der_total": float(sum(Pder[i].X for i in range(len(ders)))) if mode == "hosting" else 0.0,
        "note": "linear aggregated feeder model",
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    net, cfg = load_case(case_dir)
    sol = solve(net, cfg, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": cfg.get("problem"),
        "smartds": sol,
    }
    (case_dir / "results").mkdir(exist_ok=True)
    (case_dir / "results" / "python_result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
