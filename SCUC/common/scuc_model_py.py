"""Preventive DC-SCUC model (gurobipy). Shared by all scuc cases."""

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
    with open(case_dir / "data" / "network.json", encoding="utf-8") as f:
        network = json.load(f)
    with open(case_dir / "data" / "config.json", encoding="utf-8") as f:
        config = json.load(f)
    return network, config


def _bus_maps(network: dict) -> tuple[list[int], dict[int, int], int]:
    bus_ids = [int(b["bus_i"]) for b in network["buses"]]
    bus_pos = {bid: i for i, bid in enumerate(bus_ids)}
    ref = bus_ids[0]
    for b in network["buses"]:
        if int(b["type"]) == 3:
            ref = int(b["bus_i"])
            break
    return bus_ids, bus_pos, ref


def solve_scuc(
    network: dict,
    config: dict,
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    """Solve preventive DC-SCUC. Powers in p.u. internally; costs in $ over horizon."""
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]

    T = int(config["T"])
    load_mult = [float(x) for x in config["load_mult"]]  # length T
    assert len(load_mult) == T

    # contingencies: list of branch ids (1-based); 0 = base (no outage)
    cont_ids = [0] + [int(x) for x in config.get("contingencies", [])]
    nC = len(cont_ids)

    bus_ids, bus_pos, ref_bus = _bus_maps(network)
    nB = len(bus_ids)
    nG = len(gens)
    nL = len(branches)
    ref_pos = bus_pos[ref_bus]

    # base Pd per bus (MW) before multiplier
    Pd0 = {int(b["bus_i"]): float(b["Pd"]) for b in buses}
    load_scale = float(config.get("load_scale", 1.0))

    m = gp.Model("scuc")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.MIPGap = float(config.get("mip_gap", 1e-4))
    m.Params.TimeLimit = float(config.get("time_limit", 300))
    m.Params.Seed = int(config.get("seed", 1))
    m.Params.Threads = int(config.get("threads", 1))

    # --- UC / dispatch vars (t = 0..T-1) ---
    u = m.addVars(nG, T, vtype=GRB.BINARY, name="u")
    v = m.addVars(nG, T, vtype=GRB.BINARY, name="v")  # startup
    w = m.addVars(nG, T, vtype=GRB.BINARY, name="w")  # shutdown
    Pg = m.addVars(nG, T, lb=0.0, name="Pg")  # p.u.

    # network vars per (t, c)
    theta = m.addVars(nB, T, nC, lb=-math.pi, ub=math.pi, name="theta")
    f = m.addVars(nL, T, nC, lb=-GRB.INFINITY, name="f")

    # initial commitment u_{-1}
    u0 = [int(g.get("u0", 0)) for g in gens]

    # gen parameters
    pmin = []
    pmax = []
    ru = []
    rd = []
    ut = []
    dt = []
    c1 = []
    c2 = []
    c0 = []
    sup = []
    sdn = []
    active = []  # can commit
    for g, gen in enumerate(gens):
        status = int(gen.get("status", 1))
        pmx = float(gen["Pmax"]) / base
        pmn = float(gen["Pmin"]) / base
        if status == 0 or pmx <= 1e-12:
            active.append(False)
            pmin.append(0.0)
            pmax.append(0.0)
            ru.append(0.0)
            rd.append(0.0)
            ut.append(1)
            dt.append(1)
            c1.append(0.0)
            c2.append(0.0)
            c0.append(0.0)
            sup.append(0.0)
            sdn.append(0.0)
            for t in range(T):
                m.addConstr(u[g, t] == 0)
                m.addConstr(v[g, t] == 0)
                m.addConstr(w[g, t] == 0)
                m.addConstr(Pg[g, t] == 0)
        else:
            active.append(True)
            pmin.append(pmn)
            pmax.append(pmx)
            ru.append(float(gen["RU"]) / base)
            rd.append(float(gen["RD"]) / base)
            ut.append(int(gen["UT"]))
            dt.append(int(gen["DT"]))
            c1.append(float(gen["c1"]))
            c2.append(float(gen["c2"]))
            c0.append(float(gen.get("c0_nl", 0.0)))
            sup.append(float(gen["startup_cost"]))
            sdn.append(float(gen["shutdown_cost"]))

    # objective
    obj = gp.LinExpr()
    has_quad = any(abs(c2[g]) > 1e-12 for g in range(nG))
    qobj = gp.QuadExpr() if has_quad else None
    for t in range(T):
        for g in range(nG):
            if not active[g]:
                continue
            # cost on MW: c1 * (Pg*base) + c2 * (Pg*base)^2 + no-load * u + startup/shutdown
            obj += c1[g] * base * Pg[g, t]
            obj += c0[g] * u[g, t]
            obj += sup[g] * v[g, t]
            obj += sdn[g] * w[g, t]
            if has_quad and abs(c2[g]) > 1e-12:
                qobj += c2[g] * (base * base) * Pg[g, t] * Pg[g, t]
    if has_quad:
        m.setObjective(qobj + obj, GRB.MINIMIZE)
    else:
        m.setObjective(obj, GRB.MINIMIZE)

    # commitment logic & limits & ramps
    for g in range(nG):
        if not active[g]:
            continue
        for t in range(T):
            u_prev = u0[g] if t == 0 else u[g, t - 1]
            m.addConstr(u[g, t] - u_prev == v[g, t] - w[g, t], name=f"ulog_{g}_{t}")
            m.addConstr(v[g, t] + w[g, t] <= 1)
            m.addConstr(Pg[g, t] <= pmax[g] * u[g, t])
            m.addConstr(Pg[g, t] >= pmin[g] * u[g, t])

            # ramp
            if t == 0:
                # from assumed P=0 if off, or free-ish if on: use pmin/pmax band
                P_prev = 0.0  # cold start reference at t=0 boundary
                # if initially on, allow up to pmax from 0 within ramp (startup)
                m.addConstr(Pg[g, t] - P_prev <= ru[g])
                m.addConstr(P_prev - Pg[g, t] <= rd[g])
            else:
                m.addConstr(Pg[g, t] - Pg[g, t - 1] <= ru[g])
                m.addConstr(Pg[g, t - 1] - Pg[g, t] <= rd[g])

        # min up: if start at t, stay on for UT periods (including t)
        UT = ut[g]
        for t in range(T):
            for k in range(UT):
                if t + k < T:
                    m.addConstr(u[g, t + k] >= v[g, t], name=f"minup_{g}_{t}_{k}")

        # min down: if shut down at t, stay off for DT periods (including t)
        DT = dt[g]
        for t in range(T):
            for k in range(DT):
                if t + k < T:
                    m.addConstr(u[g, t + k] <= 1 - w[g, t], name=f"mindn_{g}_{t}_{k}")

    # branch meta
    br_bsus = []
    br_rate = []
    br_status = []
    br_id = []
    br_f = []
    br_t = []
    ang_dmax = []
    for br in branches:
        x = float(br["x"])
        if abs(x) < 1e-10:
            x = 1e-10
        br_bsus.append(1.0 / x)
        rate = float(br["rateA"]) / base
        if rate <= 0:
            rate = 1e3
        br_rate.append(rate)
        br_status.append(int(br["status"]))
        br_id.append(int(br["id"]))
        br_f.append(bus_pos[int(br["fbus"])])
        br_t.append(bus_pos[int(br["tbus"])])
        angmax = abs(float(br.get("angmax", 30.0)))
        angmin = abs(float(br.get("angmin", -30.0)))
        ang_dmax.append(math.radians(max(angmax, angmin, 30.0)))

    emerg = float(config.get("emergency_rate_factor", 1.0))

    # network constraints for each t, c
    for t in range(T):
        mult = load_scale * load_mult[t]
        Pd_t = {bid: (Pd0.get(bid, 0.0) * mult) / base for bid in bus_ids}

        for ci, out_id in enumerate(cont_ids):
            m.addConstr(theta[ref_pos, t, ci] == 0.0)

            for ell in range(nL):
                i = br_f[ell]
                j = br_t[ell]
                bsus = br_bsus[ell]
                rate = br_rate[ell] * (emerg if out_id != 0 else 1.0)
                # if this line is the contingency outage or offline in data
                if br_status[ell] == 0 or br_id[ell] == out_id:
                    m.addConstr(f[ell, t, ci] == 0.0)
                else:
                    m.addConstr(f[ell, t, ci] == bsus * (theta[i, t, ci] - theta[j, t, ci]))
                    m.addConstr(f[ell, t, ci] <= rate)
                    m.addConstr(f[ell, t, ci] >= -rate)
                m.addConstr(theta[i, t, ci] - theta[j, t, ci] <= ang_dmax[ell])
                m.addConstr(theta[j, t, ci] - theta[i, t, ci] <= ang_dmax[ell])

            # power balance
            for bi, bid in enumerate(bus_ids):
                inj = gp.quicksum(
                    Pg[g, t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
                )
                outf = gp.quicksum(
                    f[ell, t, ci] for ell in range(nL) if int(branches[ell]["fbus"]) == bid
                )
                inf = gp.quicksum(
                    f[ell, t, ci] for ell in range(nL) if int(branches[ell]["tbus"]) == bid
                )
                m.addConstr(inj - Pd_t[bid] == outf - inf, name=f"bal_{t}_{ci}_{bid}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status = status_map.get(m.Status, str(m.Status))

    if m.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "T": T,
            "n_contingencies": nC - 1,
            "u": [],
            "Pg_MW": [],
            "startups": 0,
            "shutdowns": 0,
        }

    U = [[int(round(u[g, t].X)) for t in range(T)] for g in range(nG)]
    P = [[float(Pg[g, t].X) * base for t in range(T)] for g in range(nG)]
    startups = sum(int(round(v[g, t].X)) for g in range(nG) for t in range(T))
    shutdowns = sum(int(round(w[g, t].X)) for g in range(nG) for t in range(T))

    return {
        "status": status,
        "obj": float(m.ObjVal),
        "obj_bound": float(m.ObjBound) if m.IsMIP else float(m.ObjVal),
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "T": T,
        "n_contingencies": nC - 1,
        "contingencies": cont_ids[1:],
        "u": U,
        "Pg_MW": P,
        "startups": startups,
        "shutdowns": shutdowns,
        "ref_bus": ref_bus,
        "baseMVA": base,
        "n_binary": 3 * sum(1 for a in active if a) * T,
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_scuc(network, config, quiet=quiet)
    result = {
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "network_name": network.get("name", case_dir.name),
        "problem": "scuc",
        "scuc": sol,
        "T": config["T"],
        "load_scale": config.get("load_scale", 1.0),
        "contingencies": config.get("contingencies", []),
        "notes": config.get("notes", []),
    }
    out = case_dir / "results" / "python_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result
