"""DC-flexible multi-period DC-OPF / SCUC (gurobipy).

Wan–Li style embedding of data-center load on an existing IEEE network:

  inflexible:        P_dc[d,t] = P_base[d,t]
  temporal:          sum_t P_dc[d,t] = sum_t P_base[d,t]
                     (1-α) P_base <= P_dc <= (1+α) P_base
  spatial:           sum_d P_dc[d,t] = sum_d P_base[d,t]  for each t
                     0 <= P_dc <= (1+α) max_t P_base
  spatial_temporal:  sum_{d,t} P_dc = sum_{d,t} P_base
                     0 <= P_dc <= (1+α) max_t P_base
  interruptible:     P_dc + shed = P_base,  0 <= shed <= β P_base

Power balance at bus b (p.u.):
  sum_g Pg - Pd0[b]*λ[t] - sum_{d at b} P_dc[d,t]/Sbase = outflow - inflow
  f = (1/x) (θ_f - θ_t)
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
from result_io import load_case, write_result  # noqa: E402
from tolerances import solver_params_from_config  # noqa: E402

BAL_TOL = 1e-4
THERM_TOL = 1e-4
ENERGY_TOL = 1e-3


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _bus_maps(network: dict) -> tuple[list[int], dict[int, int], int]:
    bus_ids = [int(b["bus_i"]) for b in network["buses"]]
    bus_pos = {bid: i for i, bid in enumerate(bus_ids)}
    ref = bus_ids[0]
    for b in network["buses"]:
        if int(b["type"]) == 3:
            ref = int(b["bus_i"])
            break
    return bus_ids, bus_pos, ref


def solve_dcflex(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    T = int(network["horizon"])
    load_mult = [float(x) for x in network["load_mult"]]
    load_scale = float(network.get("load_scale", 1.0))
    flex = str(network.get("flex_mode", "inflexible")).lower()
    alpha = float(network.get("flex_alpha", 0.25))
    shed_frac = float(network.get("shed_frac", 0.0))
    c_shed = float(network.get("c_shed", 0.0))
    use_uc = bool(network.get("use_uc", False))
    dcs = list(network.get("dcs") or [])
    nD = len(dcs)
    params = solver_params_from_config(config)

    bus_ids, bus_pos, ref_bus = _bus_maps(network)
    nB = len(bus_ids)
    nG = len(gens)
    nL = len(branches)
    ref_pos = bus_pos[ref_bus]
    Pd0 = {int(b["bus_i"]): float(b["Pd"]) for b in buses}

    p_base = [[float(d["p_base_mw"][t]) for t in range(T)] for d in dcs]
    dc_bus = [int(d["bus"]) for d in dcs]

    m = gp.Model("dcflex")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    u = v = w = None
    if use_uc:
        u = m.addVars(nG, T, vtype=GRB.BINARY, name="u")
        v = m.addVars(nG, T, vtype=GRB.BINARY, name="v")
        w = m.addVars(nG, T, vtype=GRB.BINARY, name="w")
    Pg = m.addVars(nG, T, lb=0.0, name="Pg")
    theta = m.addVars(nB, T, lb=-math.pi, ub=math.pi, name="theta")
    flow = m.addVars(nL, T, lb=-GRB.INFINITY, name="f")
    Pdc = m.addVars(nD, T, lb=0.0, name="Pdc")
    shed = m.addVars(nD, T, lb=0.0, name="shed") if flex == "interruptible" else None

    active = []
    pmin, pmax, ru, rd, ut, dt = [], [], [], [], [], []
    c1, c2, c0, sup, sdn, u0 = [], [], [], [], [], []
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
            u0.append(0)
            for t in range(T):
                m.addConstr(Pg[g, t] == 0)
                if use_uc:
                    m.addConstr(u[g, t] == 0)
                    m.addConstr(v[g, t] == 0)
                    m.addConstr(w[g, t] == 0)
        else:
            active.append(True)
            pmin.append(pmn)
            pmax.append(pmx)
            ru.append(float(gen.get("RU", gen["Pmax"] * 0.5)) / base)
            rd.append(float(gen.get("RD", gen["Pmax"] * 0.5)) / base)
            ut.append(int(gen.get("UT", 1)))
            dt.append(int(gen.get("DT", 1)))
            c1.append(float(gen.get("c1", 0.0)))
            c2.append(float(gen.get("c2", 0.0)))
            c0.append(float(gen.get("c0_nl", gen.get("c0", 0.0))))
            sup.append(float(gen.get("startup_cost", 0.0)))
            sdn.append(float(gen.get("shutdown_cost", 0.0)))
            u0.append(int(gen.get("u0", 0)))

    obj = gp.LinExpr()
    has_quad = any(abs(c2[g]) > 1e-12 for g in range(nG))
    qobj = gp.QuadExpr() if has_quad else None
    for t in range(T):
        for g in range(nG):
            if not active[g]:
                continue
            obj += c1[g] * base * Pg[g, t]
            if use_uc:
                obj += c0[g] * u[g, t] + sup[g] * v[g, t] + sdn[g] * w[g, t]
            if has_quad and abs(c2[g]) > 1e-12:
                qobj += c2[g] * (base * base) * Pg[g, t] * Pg[g, t]
        if shed is not None:
            for d in range(nD):
                obj += c_shed * shed[d, t]
    if has_quad:
        m.setObjective(qobj + obj, GRB.MINIMIZE)
    else:
        m.setObjective(obj, GRB.MINIMIZE)

    for g in range(nG):
        if not active[g]:
            continue
        for t in range(T):
            if use_uc:
                u_prev = u0[g] if t == 0 else u[g, t - 1]
                m.addConstr(u[g, t] - u_prev == v[g, t] - w[g, t])
                m.addConstr(v[g, t] + w[g, t] <= 1)
                m.addConstr(Pg[g, t] <= pmax[g] * u[g, t])
                m.addConstr(Pg[g, t] >= pmin[g] * u[g, t])
            else:
                m.addConstr(Pg[g, t] <= pmax[g])
                if pmin[g] > 1e-12:
                    m.addConstr(Pg[g, t] >= pmin[g])
            if t == 0:
                m.addConstr(Pg[g, t] <= ru[g] + pmax[g])
            else:
                m.addConstr(Pg[g, t] - Pg[g, t - 1] <= ru[g])
                m.addConstr(Pg[g, t - 1] - Pg[g, t] <= rd[g])
        if use_uc:
            for t in range(T):
                for k in range(ut[g]):
                    if t + k < T:
                        m.addConstr(u[g, t + k] >= v[g, t])
                for k in range(dt[g]):
                    if t + k < T:
                        m.addConstr(u[g, t + k] <= 1 - w[g, t])

    for d in range(nD):
        peak = max(p_base[d]) if p_base[d] else 0.0
        cap = (1.0 + alpha) * peak
        energy = sum(p_base[d])
        for t in range(T):
            if flex == "inflexible":
                m.addConstr(Pdc[d, t] == p_base[d][t])
            elif flex == "temporal":
                lo = max(0.0, (1.0 - alpha) * p_base[d][t])
                hi = (1.0 + alpha) * p_base[d][t]
                m.addConstr(Pdc[d, t] >= lo)
                m.addConstr(Pdc[d, t] <= hi)
            elif flex in ("spatial", "spatial_temporal"):
                m.addConstr(Pdc[d, t] <= cap)
            elif flex == "interruptible":
                m.addConstr(Pdc[d, t] + shed[d, t] == p_base[d][t])
                m.addConstr(shed[d, t] <= shed_frac * p_base[d][t])
            else:
                raise ValueError(f"unknown flex_mode {flex}")
        if flex == "temporal":
            m.addConstr(gp.quicksum(Pdc[d, t] for t in range(T)) == energy)
    if flex == "spatial":
        for t in range(T):
            m.addConstr(
                gp.quicksum(Pdc[d, t] for d in range(nD))
                == sum(p_base[d][t] for d in range(nD))
            )
    if flex == "spatial_temporal":
        m.addConstr(
            gp.quicksum(Pdc[d, t] for d in range(nD) for t in range(T))
            == sum(p_base[d][t] for d in range(nD) for t in range(T))
        )

    br_b, br_rate, br_status, br_f, br_t = [], [], [], [], []
    for br in branches:
        x = float(br["x"])
        if abs(x) < 1e-10:
            x = 1e-10
        tap = float(br.get("ratio", 0.0) or 0.0)
        if tap == 0.0:
            tap = 1.0
        br_b.append(1.0 / (x * tap))
        rate = float(br["rateA"]) / base
        br_rate.append(1e3 if rate <= 0 else rate)
        br_status.append(int(br.get("status", 1)))
        br_f.append(bus_pos[int(br["fbus"])])
        br_t.append(bus_pos[int(br["tbus"])])

    for t in range(T):
        m.addConstr(theta[ref_pos, t] == 0.0)
        for ell in range(nL):
            i, j = br_f[ell], br_t[ell]
            if br_status[ell] == 0:
                m.addConstr(flow[ell, t] == 0.0)
            else:
                m.addConstr(flow[ell, t] == br_b[ell] * (theta[i, t] - theta[j, t]))
                m.addConstr(flow[ell, t] <= br_rate[ell])
                m.addConstr(flow[ell, t] >= -br_rate[ell])
        Pd_t = {
            bid: (Pd0.get(bid, 0.0) * load_scale * load_mult[t]) / base for bid in bus_ids
        }
        for bi, bid in enumerate(bus_ids):
            inj = gp.quicksum(
                Pg[g, t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            outf = gp.quicksum(flow[ell, t] for ell in range(nL) if br_f[ell] == bi)
            inf = gp.quicksum(flow[ell, t] for ell in range(nL) if br_t[ell] == bi)
            pdc_b = gp.quicksum(
                Pdc[d, t] / base for d in range(nD) if dc_bus[d] == bid
            )
            m.addConstr(inj - Pd_t[bid] - pdc_b == outf - inf, name=f"bal_{t}_{bid}")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)
    if m.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "flex_mode": flex}

    P = [[float(Pg[g, t].X) * base for t in range(T)] for g in range(nG)]
    Pdc_mw = [[float(Pdc[d, t].X) for t in range(T)] for d in range(nD)]
    shed_mw = (
        [[float(shed[d, t].X) for t in range(T)] for d in range(nD)]
        if shed is not None
        else [[0.0] * T for _ in range(nD)]
    )
    th = [[float(theta[i, t].X) for t in range(T)] for i in range(nB)]
    fl = [[float(flow[ell, t].X) * base for t in range(T)] for ell in range(nL)]
    U = None
    if use_uc:
        U = [[int(round(u[g, t].X)) for t in range(T)] for g in range(nG)]
    obj_val = float(m.ObjVal)
    try:
        obj_bound = float(m.ObjBound)
    except Exception:
        obj_bound = obj_val
    sol = {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "flex_mode": flex,
        "use_uc": use_uc,
        "Pg_MW": P,
        "Pdc_MW": Pdc_mw,
        "shed_MW": shed_mw,
        "theta": th,
        "f_MW": fl,
        "u": U,
        "dc_energy": [sum(row) for row in Pdc_mw],
        "shed_energy": [sum(row) for row in shed_mw],
        "baseMVA": base,
        "ref_bus": ref_bus,
    }
    sol.update(validate_dcflex(network, sol))
    return sol


def validate_dcflex(network: dict, sol: dict[str, Any]) -> dict[str, Any]:
    if sol.get("obj") is None:
        return {"validation_passed": False}
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    T = int(network["horizon"])
    load_mult = [float(x) for x in network["load_mult"]]
    load_scale = float(network.get("load_scale", 1.0))
    flex = str(network.get("flex_mode", "inflexible")).lower()
    dcs = list(network.get("dcs") or [])
    bus_ids, bus_pos, _ref = _bus_maps(network)
    Pd0 = {int(b["bus_i"]): float(b["Pd"]) for b in buses}
    P = sol["Pg_MW"]
    Pdc = sol["Pdc_MW"]
    shed = sol.get("shed_MW") or [[0.0] * T for _ in dcs]
    th = sol["theta"]
    fl = sol["f_MW"]

    max_bal = 0.0
    max_flow_eq = 0.0
    max_therm = 0.0
    for t in range(T):
        inj = {bid: 0.0 for bid in bus_ids}
        for g, gen in enumerate(gens):
            inj[int(gen["bus"])] += P[g][t]
        for d, dc in enumerate(dcs):
            inj[int(dc["bus"])] -= Pdc[d][t]
        for bid in bus_ids:
            inj[bid] -= Pd0.get(bid, 0.0) * load_scale * load_mult[t]
        for ell, br in enumerate(branches):
            if int(br.get("status", 1)) == 0:
                continue
            fb, tb = int(br["fbus"]), int(br["tbus"])
            inj[fb] -= fl[ell][t]
            inj[tb] += fl[ell][t]
            x = float(br["x"]) or 1e-10
            tap = float(br.get("ratio", 0.0) or 0.0) or 1.0
            pred = base * (1.0 / (x * tap)) * (th[bus_pos[fb]][t] - th[bus_pos[tb]][t])
            max_flow_eq = max(max_flow_eq, abs(pred - fl[ell][t]))
            rate = float(br["rateA"])
            if rate > 0:
                max_therm = max(max_therm, max(0.0, abs(fl[ell][t]) - rate))
        for bid in bus_ids:
            max_bal = max(max_bal, abs(inj[bid]))

    energy_vio = 0.0
    for d, dc in enumerate(dcs):
        base_e = sum(float(v) for v in dc["p_base_mw"])
        if flex == "temporal":
            energy_vio = max(energy_vio, abs(sum(Pdc[d]) - base_e))
        if flex == "interruptible":
            for t in range(T):
                energy_vio = max(
                    energy_vio,
                    abs(Pdc[d][t] + shed[d][t] - float(dc["p_base_mw"][t])),
                )
    if flex == "spatial":
        for t in range(T):
            energy_vio = max(
                energy_vio,
                abs(sum(Pdc[d][t] for d in range(len(dcs))) - sum(float(dc["p_base_mw"][t]) for dc in dcs)),
            )
    if flex == "spatial_temporal":
        energy_vio = max(
            energy_vio,
            abs(
                sum(sum(row) for row in Pdc)
                - sum(sum(float(v) for v in dc["p_base_mw"]) for dc in dcs)
            ),
        )

    passed = (
        sol.get("status") in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT")
        and max_bal <= BAL_TOL
        and max_flow_eq <= BAL_TOL
        and max_therm <= THERM_TOL
        and energy_vio <= ENERGY_TOL
    )
    return {
        "max_balance_violation": max_bal,
        "max_flow_violation": max_flow_eq,
        "max_thermal_violation": max_therm,
        "max_energy_violation": energy_vio,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_dcflex(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case") or case_dir.name,
        "solver": "python-gurobi",
        "problem": "dcflex",
        "base_problem": "datacenter_flex",
        "dcflex": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case001_ieee14_opf_inflexible"
    )
    r = run_case(d, quiet=True)
    e = r["dcflex"]
    print(f"[{r['case']}] status={e['status']} obj={e['obj']} valid={e.get('validation_passed')}")
