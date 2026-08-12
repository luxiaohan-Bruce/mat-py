"""Preventive DC-SCUC + ESS + renewables + reserve (gurobipy)."""

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


def _status_name(status: int) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }.get(status, str(status))


def solve_rts_scuc(network: dict, config: dict, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    branches = network["branches"]
    thermal = network["thermal"]
    renewable = network.get("renewable", [])
    storage = network.get("storage", [])
    raw_frac = network["bus_load_fraction"]
    if isinstance(raw_frac, dict):
        frac = {int(k): float(v) for k, v in raw_frac.items()}
    else:
        frac = {int(item["bus"]): float(item["frac"]) for item in raw_frac}
    demand = [float(x) for x in network["demand_MW"]]
    reserve_req = [float(x) for x in network["reserve_MW"]]

    T = int(config["T"])
    assert T == len(demand)
    cont_ids = [0] + [int(x) for x in config.get("contingencies", [])]
    nC = len(cont_ids)
    shed_pen = float(config.get("load_shed_penalty", 5000.0))

    bus_ids = [int(b["bus_i"]) for b in buses]
    bus_pos = {b: i for i, b in enumerate(bus_ids)}
    ref = next((int(b["bus_i"]) for b in buses if int(b["type"]) == 3), bus_ids[0])
    ref_pos = bus_pos[ref]
    nB, nG, nL = len(bus_ids), len(thermal), len(branches)
    nW, nS = len(renewable), len(storage)

    m = gp.Model("rts_scuc")
    m.Params.OutputFlag = 0 if quiet else 1
    m.Params.MIPGap = float(config.get("mip_gap", 0.01))
    m.Params.TimeLimit = float(config.get("time_limit", 300))
    m.Params.Seed = int(config.get("seed", 1))
    threads = int(config.get("threads", 0))
    m.Params.Threads = threads

    u = m.addVars(nG, T, vtype=GRB.BINARY, name="u")
    v = m.addVars(nG, T, vtype=GRB.BINARY, name="v")
    w = m.addVars(nG, T, vtype=GRB.BINARY, name="w")
    Pg = m.addVars(nG, T, lb=0.0, name="Pg")  # MW
    Rspin = m.addVars(nG, T, lb=0.0, name="R")
    Pw = m.addVars(nW, T, lb=0.0, name="Pw")
    Pc = m.addVars(nS, T, lb=0.0, name="Pc")
    Pd_ess = m.addVars(nS, T, lb=0.0, name="Pd")
    E = m.addVars(nS, T, lb=0.0, name="E")
    shed = m.addVars(nB, T, lb=0.0, name="shed")
    theta = m.addVars(nB, T, nC, lb=-math.pi, ub=math.pi, name="th")
    f = m.addVars(nL, T, nC, lb=-GRB.INFINITY, name="f")

    obj = gp.LinExpr()
    for g, gen in enumerate(thermal):
        for t in range(T):
            obj += float(gen["base_cost"]) * u[g, t]
            obj += float(gen["slope"]) * (Pg[g, t] - float(gen["Pmin"]) * u[g, t])
            obj += float(gen["startup"]) * v[g, t]
            obj += float(gen["shutdown"]) * w[g, t]
    for b in range(nB):
        for t in range(T):
            obj += shed_pen * shed[b, t]
    m.setObjective(obj, GRB.MINIMIZE)

    # UC logic
    for g, gen in enumerate(thermal):
        pmin, pmax = float(gen["Pmin"]), float(gen["Pmax"])
        ru, rd = float(gen["RU"]), float(gen["RD"])
        ut, dt = int(gen["UT"]), int(gen["DT"])
        u0 = int(gen["u0"])
        p0 = float(gen["p0"])
        for t in range(T):
            prev = u0 if t == 0 else u[g, t - 1]
            m.addConstr(u[g, t] - prev == v[g, t] - w[g, t])
            m.addConstr(v[g, t] + w[g, t] <= 1)
            if int(gen.get("must_run", 0)):
                m.addConstr(u[g, t] == 1)
            m.addConstr(Pg[g, t] >= pmin * u[g, t])
            m.addConstr(Pg[g, t] + Rspin[g, t] <= pmax * u[g, t])
            if t == 0:
                m.addConstr(Pg[g, t] - p0 <= ru)
                m.addConstr(p0 - Pg[g, t] <= rd)
            else:
                m.addConstr(Pg[g, t] - Pg[g, t - 1] <= ru)
                m.addConstr(Pg[g, t - 1] - Pg[g, t] <= rd)
            # min up/down (standard)
            if t >= ut - 1:
                m.addConstr(
                    gp.quicksum(v[g, k] for k in range(t - ut + 1, t + 1)) <= u[g, t]
                )
            if t >= dt - 1:
                m.addConstr(
                    gp.quicksum(w[g, k] for k in range(t - dt + 1, t + 1)) <= 1 - u[g, t]
                )

    # renewables
    for w_i, ren in enumerate(renewable):
        for t in range(T):
            m.addConstr(Pw[w_i, t] >= float(ren["pmin"][t]))
            m.addConstr(Pw[w_i, t] <= float(ren["pmax"][t]))

    # storage SOC (hourly)
    for s, st in enumerate(storage):
        pmax = float(st["Pmax_MW"])
        emax = float(st["Emax_MWh"])
        e0 = float(st["E0_MWh"])
        eta_c, eta_d = float(st["eta_c"]), float(st["eta_d"])
        for t in range(T):
            m.addConstr(Pc[s, t] <= pmax)
            m.addConstr(Pd_ess[s, t] <= pmax)
            m.addConstr(E[s, t] <= emax)
            if t == 0:
                m.addConstr(E[s, t] == e0 + eta_c * Pc[s, t] - Pd_ess[s, t] / max(eta_d, 1e-6))
            else:
                m.addConstr(
                    E[s, t]
                    == E[s, t - 1] + eta_c * Pc[s, t] - Pd_ess[s, t] / max(eta_d, 1e-6)
                )

    # system reserve
    for t in range(T):
        m.addConstr(gp.quicksum(Rspin[g, t] for g in range(nG)) >= reserve_req[t])

    # branch susceptance
    bsus = []
    for br in branches:
        x = float(br["x"])
        tap = float(br.get("ratio") or 0.0) or 1.0
        bsus.append(1.0 / (x * tap))

    outaged = set()
    for c, cid in enumerate(cont_ids):
        if cid != 0:
            outaged.add((c, cid))

    for t in range(T):
        for c, cid in enumerate(cont_ids):
            m.addConstr(theta[ref_pos, t, c] == 0)
            # flows
            for ell, br in enumerate(branches):
                i = bus_pos[int(br["fbus"])]
                j = bus_pos[int(br["tbus"])]
                rate = float(br["rateA"] if c == 0 else br.get("rateC", br["rateA"]))
                rate *= float(config.get("emergency_rate_factor", 1.0)) if c > 0 else 1.0
                if cid != 0 and int(br["id"]) == cid:
                    m.addConstr(f[ell, t, c] == 0)
                else:
                    m.addConstr(f[ell, t, c] == bsus[ell] * (theta[i, t, c] - theta[j, t, c]))
                    m.addConstr(f[ell, t, c] <= rate / base)
                    m.addConstr(f[ell, t, c] >= -rate / base)
            # nodal balance in p.u.
            for bi, bid in enumerate(bus_ids):
                load_mw = demand[t] * frac.get(bid, 0.0)
                inj = -load_mw / base + shed[bi, t] / base
                for g, gen in enumerate(thermal):
                    if int(gen["bus"]) == bid:
                        # preventive: same Pg in all contingencies
                        inj += Pg[g, t] / base
                for w_i, ren in enumerate(renewable):
                    if int(ren["bus"]) == bid:
                        inj += Pw[w_i, t] / base
                for s, st in enumerate(storage):
                    if int(st["bus"]) == bid:
                        inj += (Pd_ess[s, t] - Pc[s, t]) / base
                flow_terms = gp.LinExpr()
                for ell, br in enumerate(branches):
                    if int(br["fbus"]) == bid:
                        flow_terms += f[ell, t, c]
                    if int(br["tbus"]) == bid:
                        flow_terms -= f[ell, t, c]
                m.addConstr(flow_terms == inj, name=f"bal[{bi},{t},{c}]")
            # shed only on base for simplicity bound
            if c == 0:
                for bi, bid in enumerate(bus_ids):
                    m.addConstr(shed[bi, t] <= demand[t] * frac.get(bid, 0.0))

    # preventives: shed independent of c already; Pg independent of c

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m.Status)
    if m.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "T": T,
            "n_thermal": nG,
            "n_renewable": nW,
            "n_storage": nS,
            "n_contingencies": nC - 1,
        }

    max_bal = 0.0
    # residual check on base case
    for t in range(T):
        gen_sum = sum(Pg[g, t].X for g in range(nG))
        ren_sum = sum(Pw[w, t].X for w in range(nW))
        ess = sum(Pd_ess[s, t].X - Pc[s, t].X for s in range(nS))
        sh = sum(shed[b, t].X for b in range(nB))
        max_bal = max(max_bal, abs(gen_sum + ren_sum + ess + sh - demand[t]))

    return {
        "status": status,
        "obj": float(m.ObjVal),
        "obj_bound": float(m.ObjBound),
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "T": T,
        "n_thermal": nG,
        "n_renewable": nW,
        "n_storage": nS,
        "n_contingencies": nC - 1,
        "load_shed_MW_total": float(sum(shed[b, t].X for b in range(nB) for t in range(T))),
        "max_balance_residual_MW": max_bal,
        "startups": int(round(sum(v[g, t].X for g in range(nG) for t in range(T)))),
        "n_binary": m.NumBinVars,
        "n_variables": m.NumVars,
        "n_constraints": m.NumConstrs,
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_rts_scuc(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": "rts_scuc",
        "source": config.get("source", {}),
        "scuc": sol,
    }
    out = case_dir / "results" / "python_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
