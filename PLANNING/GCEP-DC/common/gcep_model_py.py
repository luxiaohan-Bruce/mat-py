"""Texas 123-BT multi-period GCEP with data-center and EOR loads (gurobipy).

Faithful to PSE-Lab Case2_LP_multi-periods.py:

  p_gen - curt_gen + stor_d - stor_c - sum_nbr (Sbase/x)(θ_n-θ_nbr)
      = D_base + p_DC + p_EOR - curt

  county DC/EOR: sum_{n in county} p = D_county(year)
  thermal CF band, solar/wind/hydro follow CF * available capacity
  construction lags, nuclear moratorium through 2029
  storage SoC with η=sqrt(0.85), 4 h duration
  objective: CAPEX + FOM + VOM/fuel + curtailment, / 1e5
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

BAL_TOL = 1e-2
ENERGY_TOL = 1e-2


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _df(ir: float, year: int, base: int) -> float:
    return 1.0 / (1.0 + ir) ** (year - base)


def solve_gcep(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    nN = int(network["n_bus"])
    nY = int(network["n_year"])
    nD = int(network["n_day"])
    nH = int(network["n_hour"])
    years = [int(y) for y in network["years"]]
    wday = [float(v) for v in network["weight_days"]]
    buses = network["buses"]
    gens = network["gens"]
    lines = network["lines"]
    bus_ids = [int(b["bus"]) for b in buses]
    bus_pos = {bid: i for i, bid in enumerate(bus_ids)}
    nG = len(gens)
    nL = len(lines)
    base = float(network["baseMVA"])
    construct = {str(k): int(v) for k, v in network["construct"].items()}
    trans_lag = int(network["trans_lag"])
    stor_lag = int(network["stor_lag"])
    cfmin = {str(k): float(v) for k, v in network["cf_th_min"].items()}
    cfmax = {str(k): float(v) for k, v in network["cf_th_max"].items()}
    cf_h = float(network["cf_hydro"])
    eta_c = float(network["eta_charge"])
    eta_d = float(network["eta_discharge"])
    hr_s = float(network["hr_stor"])
    Ir = float(network["Ir"])
    y0 = int(network["finance_base_year"])
    scale = float(network["obj_scale"])
    a_curt = float(network["alpha_curt"])
    a_curt_g = float(network["alpha_curt_gen"])
    a_tr = float(network["alpha_capex_trans"])
    P_peak = [float(v) for v in network["P_peak_total"]]
    D_base = network["D_base"]
    CF_s = network["CF_solar"]
    CF_w = network["CF_wind"]
    D_DC = network["D_DC"]
    D_EOR = network["D_EOR"]
    dc_counties = [str(c) for c in network["dc_counties"]]
    eor_counties = [str(c) for c in network["eor_counties"]]
    if network.get("county_buses"):
        bic = {
            str(item["county"]): [int(x) for x in item["buses"]]
            for item in network["county_buses"]
        }
    else:
        bic = {str(k): [int(x) for x in v] for k, v in network["buses_in_county"].items()}
    N_DC = set(int(x) for x in network["N_DC"])
    N_EOR = set(int(x) for x in network["N_EOR"])
    capex_gen = network["capex_gen"]
    vom = network["vom_gen"]
    fom = network["fom_gen"]
    fuel = network["cost_fuel"]
    hr = network["heat_rate"]
    capex_stor = [float(v) for v in network["capex_stor"]]
    fom_stor = [float(v) for v in network["fom_stor"]]
    params = solver_params_from_config(config)

    nbr: list[list[int]] = [[] for _ in range(nN)]
    line_x = []
    line_cap = []
    line_mile = []
    line_pair = []
    for ell, ln in enumerate(lines):
        i = bus_pos[int(ln["fbus"])]
        j = bus_pos[int(ln["tbus"])]
        line_pair.append((i, j))
        line_x.append(max(float(ln["x"]), 1e-8))
        line_cap.append(float(ln["cap0"]))
        line_mile.append(float(ln["mile"]))
        nbr[i].append(ell)
        nbr[j].append(ell)

    g_at = [[] for _ in range(nN)]
    g_fuel = [str(g["fuel"]) for g in gens]
    g_p0 = [float(g["pmax0"]) for g in gens]
    for gi, g in enumerate(gens):
        g_at[bus_pos[int(g["bus"])]].append(gi)

    dc_idx = {bid: k for k, bid in enumerate(sorted(N_DC))}
    eor_idx = {bid: k for k, bid in enumerate(sorted(N_EOR))}
    dc_buses = sorted(N_DC)
    eor_buses = sorted(N_EOR)

    m = gp.Model("gcep")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]
    m.Params.Method = 2
    m.Params.Crossover = 0

    p_gen = m.addVars(nG, nY, nD, nH, lb=0.0, name="pg")
    curt_g = m.addVars(nG, nY, nD, nH, lb=0.0, name="cg")
    p_ch = m.addVars(nN, nY, nD, nH, lb=0.0, name="ch")
    p_dis = m.addVars(nN, nY, nD, nH, lb=0.0, name="ds")
    e_st = m.addVars(nN, nY, nD, nH, lb=0.0, name="es")
    th = m.addVars(nN, nY, nD, nH, lb=-math.pi, ub=math.pi, name="th")
    curt = m.addVars(nN, nY, nD, nH, lb=0.0, name="cu")
    p_dc = m.addVars(len(dc_buses), nY, nD, nH, lb=0.0, name="pdc")
    p_eor = m.addVars(len(eor_buses), nY, nD, nH, lb=0.0, name="peor")
    c_gen = m.addVars(nG, nY, lb=0.0, name="cgen")
    c_tr = m.addVars(nL, nY, lb=0.0, name="ctr")
    c_st = m.addVars(nN, nY, lb=0.0, name="cst")

    def avail_gen(gi: int, t: int):
        lag = construct[g_fuel[gi]]
        extra = gp.quicksum(c_gen[gi, tp] for tp in range(t + 1 - lag)) if t + 1 > lag else 0.0
        return g_p0[gi] + extra

    def avail_tr(ell: int, t: int):
        extra = gp.quicksum(c_tr[ell, tp] for tp in range(t + 1 - trans_lag)) if t + 1 > trans_lag else 0.0
        return line_cap[ell] + extra

    def avail_st(n: int, t: int):
        extra = gp.quicksum(c_st[n, tp] for tp in range(t + 1 - stor_lag)) if t + 1 > stor_lag else 0.0
        return extra

    # energy balance + storage + gen limits
    for t in range(nY):
        for d in range(nD):
            for h in range(nH):
                m.addConstr(th[0, t, d, h] == 0.0)
                for n in range(nN):
                    flow = gp.LinExpr()
                    for ell in nbr[n]:
                        i, j = line_pair[ell]
                        other = j if i == n else i
                        flow += (base / line_x[ell]) * (th[n, t, d, h] - th[other, t, d, h])
                    pdc = p_dc[dc_idx[bus_ids[n]], t, d, h] if bus_ids[n] in dc_idx else 0.0
                    peor = p_eor[eor_idx[bus_ids[n]], t, d, h] if bus_ids[n] in eor_idx else 0.0
                    m.addConstr(
                        gp.quicksum(p_gen[gi, t, d, h] for gi in g_at[n])
                        - gp.quicksum(curt_g[gi, t, d, h] for gi in g_at[n])
                        + p_dis[n, t, d, h]
                        - p_ch[n, t, d, h]
                        - flow
                        == float(D_base[n][t][d][h]) + pdc + peor - curt[n, t, d, h],
                        name=f"bal_{n}_{t}_{d}_{h}",
                    )
                    cap_s = avail_st(n, t)
                    m.addConstr(p_ch[n, t, d, h] <= cap_s)
                    m.addConstr(p_dis[n, t, d, h] <= cap_s)
                    m.addConstr(e_st[n, t, d, h] <= cap_s * hr_s)
                    if t == 0 and d == 0 and h == 0:
                        m.addConstr(
                            e_st[n, t, d, h]
                            == eta_c * p_ch[n, t, d, h] - (1.0 / eta_d) * p_dis[n, t, d, h]
                        )
                    else:
                        if h > 0:
                            prev = e_st[n, t, d, h - 1]
                        elif d > 0:
                            prev = e_st[n, t, d - 1, nH - 1]
                        else:
                            prev = e_st[n, t - 1, nD - 1, nH - 1]
                        m.addConstr(
                            e_st[n, t, d, h]
                            == prev + eta_c * p_ch[n, t, d, h] - (1.0 / eta_d) * p_dis[n, t, d, h]
                        )
                for gi in range(nG):
                    fuel_i = g_fuel[gi]
                    cap = avail_gen(gi, t)
                    npos = bus_pos[int(gens[gi]["bus"])]
                    if fuel_i in cfmin:
                        m.addConstr(p_gen[gi, t, d, h] >= cfmin[fuel_i] * cap)
                        m.addConstr(p_gen[gi, t, d, h] <= cfmax[fuel_i] * cap)
                    elif fuel_i == "Solar":
                        m.addConstr(p_gen[gi, t, d, h] == float(CF_s[npos][d][h]) * cap)
                    elif fuel_i == "Wind":
                        m.addConstr(p_gen[gi, t, d, h] == float(CF_w[npos][d][h]) * cap)
                    elif fuel_i == "Hydro":
                        m.addConstr(p_gen[gi, t, d, h] == cf_h * cap)
                    m.addConstr(curt_g[gi, t, d, h] <= p_gen[gi, t, d, h])
                for ell, (i, j) in enumerate(line_pair):
                    pf = (base / line_x[ell]) * (th[i, t, d, h] - th[j, t, d, h])
                    capl = avail_tr(ell, t)
                    m.addConstr(pf <= capl)
                    m.addConstr(-pf <= capl)

        for ci, cty in enumerate(dc_counties):
            ids = [dc_idx[b] for b in bic.get(cty, []) if b in dc_idx]
            for d in range(nD):
                for h in range(nH):
                    m.addConstr(
                        gp.quicksum(p_dc[k, t, d, h] for k in ids) == float(D_DC[ci][t])
                    )
        for ei, cty in enumerate(eor_counties):
            ids = [eor_idx[b] for b in bic.get(cty, []) if b in eor_idx]
            for d in range(nD):
                for h in range(nH):
                    m.addConstr(
                        gp.quicksum(p_eor[k, t, d, h] for k in ids) == float(D_EOR[ei][t])
                    )

        if t + 1 > min(construct.values()):
            m.addConstr(
                P_peak[t]
                <= gp.quicksum(g_p0[gi] for gi in range(nG))
                + gp.quicksum(
                    c_gen[gi, tp]
                    for gi in range(nG)
                    for tp in range(t + 1 - construct[g_fuel[gi]])
                    if t + 1 > construct[g_fuel[gi]]
                )
            )

        for gi in range(nG):
            if g_fuel[gi] == "Nuclear" and years[t] <= 2029:
                m.addConstr(c_gen[gi, t] == 0)

    # objective
    obj = gp.LinExpr()
    for t in range(nY):
        y = years[t]
        df = _df(Ir, y, y0)
        capex_g = gp.quicksum(
            float(capex_gen[g_fuel[gi]][t]) * 1e3 * c_gen[gi, t] for gi in range(nG)
        )
        capex_t = gp.quicksum(a_tr * line_mile[ell] * 1e3 * c_tr[ell, t] for ell in range(nL))
        capex_s = gp.quicksum(capex_stor[t] * 1e3 * c_st[n, t] for n in range(nN))
        opex_v = gp.LinExpr()
        for gi in range(nG):
            fi = g_fuel[gi]
            coef = (float(vom[fi][t]) + float(fuel[fi][t]) * float(hr[fi][t]))
            opex_v += coef * gp.quicksum(
                wday[d] * p_gen[gi, t, d, h] for d in range(nD) for h in range(nH)
            )
        opex_f = gp.LinExpr()
        for gi in range(nG):
            opex_f += float(fom[g_fuel[gi]][t]) * 1e3 * avail_gen(gi, t)
        opex_s = gp.quicksum(fom_stor[t] * 1e3 * avail_st(n, t) for n in range(nN))
        cost_cu = a_curt * gp.quicksum(
            wday[d] * curt[n, t, d, h] for n in range(nN) for d in range(nD) for h in range(nH)
        )
        cost_cg = a_curt_g * gp.quicksum(
            wday[d] * curt_g[gi, t, d, h] for gi in range(nG) for d in range(nD) for h in range(nH)
        )
        obj += capex_g + df * capex_t + capex_s + opex_v + opex_f + opex_s + cost_cu + cost_cg
    m.setObjective(obj / scale, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)
    if m.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "n_var": m.NumVars,
            "n_constr": m.NumConstrs,
        }

    def xv(var):
        return float(var.X)

    new_gen = {f: 0.0 for f in network["fuels"]}
    for gi in range(nG):
        for t in range(nY):
            new_gen[g_fuel[gi]] += xv(c_gen[gi, t])
    new_tr = sum(xv(c_tr[ell, t]) for ell in range(nL) for t in range(nY))
    new_st = sum(xv(c_st[n, t]) for n in range(nN) for t in range(nY))
    dc_energy = 0.0
    for t in range(nY):
        for d in range(nD):
            for h in range(nH):
                dc_energy += wday[d] * sum(xv(p_dc[k, t, d, h]) for k in range(len(dc_buses)))
    eor_energy = 0.0
    for t in range(nY):
        for d in range(nD):
            for h in range(nH):
                eor_energy += wday[d] * sum(xv(p_eor[k, t, d, h]) for k in range(len(eor_buses)))
    curt_sum = sum(
        wday[d] * xv(curt[n, t, d, h])
        for n in range(nN)
        for t in range(nY)
        for d in range(nD)
        for h in range(nH)
    )
    obj_val = float(m.ObjVal)
    sol = {
        "status": status,
        "obj": obj_val,
        "obj_bound": float(m.ObjBoundC) if hasattr(m, "ObjBoundC") else obj_val,
        "mip_gap": 0.0,
        "runtime": runtime,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "new_gen_MW": new_gen,
        "new_trans_MW": new_tr,
        "new_stor_MW": new_st,
        "dc_energy_MWh": dc_energy,
        "eor_energy_MWh": eor_energy,
        "curt_MWh": curt_sum,
        "p_dc_sample": [
            [xv(p_dc[0, t, 0, h]) if dc_buses else 0.0 for h in range(nH)]
            for t in range(nY)
        ]
        if dc_buses
        else [],
    }
    # light residual: county DC and one-hour power balance using extracted flows
    max_dc = 0.0
    for t in range(nY):
        for ci, cty in enumerate(dc_counties):
            ids = [dc_idx[b] for b in bic.get(cty, []) if b in dc_idx]
            got = sum(xv(p_dc[k, t, 0, 0]) for k in ids)
            max_dc = max(max_dc, abs(got - float(D_DC[ci][t])))
    max_eor = 0.0
    for t in range(nY):
        for ei, cty in enumerate(eor_counties):
            ids = [eor_idx[b] for b in bic.get(cty, []) if b in eor_idx]
            got = sum(xv(p_eor[k, t, 0, 0]) for k in ids)
            max_eor = max(max_eor, abs(got - float(D_EOR[ei][t])))
    # sample energy balance at (t=last, d=0, h=12)
    t, d, h = nY - 1, 0, min(12, nH - 1)
    max_bal = 0.0
    for n in range(nN):
        flow = 0.0
        for ell in nbr[n]:
            i, j = line_pair[ell]
            other = j if i == n else i
            flow += (base / line_x[ell]) * (xv(th[n, t, d, h]) - xv(th[other, t, d, h]))
        pdc = xv(p_dc[dc_idx[bus_ids[n]], t, d, h]) if bus_ids[n] in dc_idx else 0.0
        peor = xv(p_eor[eor_idx[bus_ids[n]], t, d, h]) if bus_ids[n] in eor_idx else 0.0
        lhs = (
            sum(xv(p_gen[gi, t, d, h]) for gi in g_at[n])
            - sum(xv(curt_g[gi, t, d, h]) for gi in g_at[n])
            + xv(p_dis[n, t, d, h])
            - xv(p_ch[n, t, d, h])
            - flow
        )
        rhs = float(D_base[n][t][d][h]) + pdc + peor - xv(curt[n, t, d, h])
        max_bal = max(max_bal, abs(lhs - rhs))
    passed = (
        status in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT")
        and max_dc <= ENERGY_TOL
        and max_eor <= ENERGY_TOL
        and max_bal <= BAL_TOL
    )
    sol.update(
        {
            "max_dc_county_violation": max_dc,
            "max_eor_county_violation": max_eor,
            "max_balance_violation": max_bal,
            "validation_passed": passed,
        }
    )
    return sol


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_gcep(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case") or case_dir.name,
        "solver": "python-gurobi",
        "problem": "gcep",
        "base_problem": "gcep_dc",
        "gcep": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case001_tx123_y2_d1"
    )
    r = run_case(d, quiet=True)
    e = r["gcep"]
    print(f"[{r['case']}] status={e['status']} obj={e['obj']} valid={e.get('validation_passed')}")
