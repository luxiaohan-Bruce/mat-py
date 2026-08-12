"""Resource capacity expansion (CEM/GEP) LP — gurobipy.

min  investment + fixed_OM + sum_t w_t * (op_cost + NSE)
s.t. capacity bounds, energy balance per zone/t, gen dispatch limits,
     simple storage energy balance, optional transfer limits, optional CO2/min-cap.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from result_io import load_case, write_result  # noqa: E402
from tolerances import DEFAULT_TOLERANCES, solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _cap_bounds(existing: float, max_cap: float, min_cap: float, new_build: int, can_retire: int):
    """Return (lb, ub) for total installed capacity.

    v1: no economic retirement (keeps Cap >= existing when existing > 0) so
    inv_cost = Inv*(Cap-existing) stays linear and non-negative.
    """
    existing = max(0.0, float(existing))
    min_cap = max(0.0, float(min_cap))
    _ = can_retire  # recorded in data; ignored for bounds in v1
    if int(new_build) == 0:
        # Fixed at existing (cannot expand)
        return existing, existing
    lb = max(existing, min_cap)
    if max_cap is None or float(max_cap) < 0:
        ub = GRB.INFINITY
    else:
        ub = float(max_cap)
        if ub < lb:
            ub = max(lb, ub) if ub >= 0 else lb
            if float(max_cap) >= 0 and float(max_cap) < lb:
                # Data says max < existing: pin at existing
                return existing, existing
    return lb, ub


def solve_cem(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    zones = network["zones"]
    gens = network["generators"]
    storage = network.get("storage") or []
    demand = network["demand"]
    weights = network["time_weights"]
    lines = network.get("network_lines") or []
    policies = network.get("policies") or {}
    voll = float(network.get("voll") or 50000.0)
    T = int(network.get("n_time") or len(demand))
    nZ = len(zones)
    nG = len(gens)
    nS = len(storage)
    nL = len(lines)
    zone_ids = [int(z["id"]) for z in zones]
    zpos = {zid: i for i, zid in enumerate(zone_ids)}
    params = solver_params_from_config(config)

    m = gp.Model("cem")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    # Capacity variables
    Cap = []
    for g, gen in enumerate(gens):
        lb, ub = _cap_bounds(
            gen.get("existing_cap_MW", 0),
            gen.get("max_cap_MW", -1),
            gen.get("min_cap_MW", 0),
            gen.get("new_build", 1),
            gen.get("can_retire", 0),
        )
        Cap.append(m.addVar(lb=lb, ub=ub, name=f"Cap_g{g}"))

    CapP = []
    CapE = []
    for s, st in enumerate(storage):
        lb_p, ub_p = _cap_bounds(
            st.get("existing_cap_MW", 0),
            st.get("max_cap_MW", -1),
            st.get("min_cap_MW", 0),
            st.get("new_build", 1),
            st.get("can_retire", 0),
        )
        lb_e, ub_e = _cap_bounds(
            st.get("existing_cap_MWh", 0),
            st.get("max_cap_MWh", -1),
            st.get("min_cap_MWh", 0),
            st.get("new_build", 1),
            st.get("can_retire", 0),
        )
        CapP.append(m.addVar(lb=lb_p, ub=ub_p, name=f"CapP_s{s}"))
        CapE.append(m.addVar(lb=lb_e, ub=ub_e, name=f"CapE_s{s}"))
        # Duration coupling: min_duration * CapP <= CapE <= max_duration * CapP
        min_d = float(st.get("min_duration_h") or 1.0)
        max_d = float(st.get("max_duration_h") or 10.0)
        if max_d < min_d:
            max_d = min_d
        m.addConstr(CapE[s] >= min_d * CapP[s], name=f"smin_dur_{s}")
        m.addConstr(CapE[s] <= max_d * CapP[s], name=f"smax_dur_{s}")

    # Dispatch / storage ops / NSE / flows
    # p[g,t]: generation (or electrolyzer consumption as negative via separate)
    p = m.addVars(nG, T, lb=0.0, name="p")
    # Electrolyzer consumption
    pe = m.addVars(nG, T, lb=0.0, name="pe")  # only used for type=electrolyzer
    ch = m.addVars(nS, T, lb=0.0, name="ch")
    dis = m.addVars(nS, T, lb=0.0, name="dis")
    e = m.addVars(nS, T, lb=0.0, name="e")
    nse = m.addVars(nZ, T, lb=0.0, name="nse")
    # Directed flow on lines (can be negative)
    f = m.addVars(nL, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f")

    # Investment + fixed OM
    inv_expr = gp.LinExpr()
    for g, gen in enumerate(gens):
        exist = float(gen.get("existing_cap_MW") or 0)
        inv_c = float(gen.get("inv_cost_per_MWyr") or 0)
        fom = float(gen.get("fixed_om_per_MWyr") or 0)
        new_build = int(gen.get("new_build", 1))
        if new_build == 1 and inv_c > 0:
            # new capacity portion
            inv_expr += inv_c * (Cap[g] - exist)
        inv_expr += fom * Cap[g]

    for s, st in enumerate(storage):
        exist_p = float(st.get("existing_cap_MW") or 0)
        exist_e = float(st.get("existing_cap_MWh") or 0)
        if int(st.get("new_build", 1)) == 1:
            inv_expr += float(st.get("inv_cost_per_MWyr") or 0) * (CapP[s] - exist_p)
            inv_expr += float(st.get("inv_cost_per_MWhyr") or 0) * (CapE[s] - exist_e)
        inv_expr += float(st.get("fixed_om_per_MWyr") or 0) * CapP[s]
        inv_expr += float(st.get("fixed_om_per_MWhyr") or 0) * CapE[s]

    # Operating cost
    op_expr = gp.LinExpr()
    for t in range(T):
        w = float(weights[t])
        for g, gen in enumerate(gens):
            gtype = gen.get("type") or "thermal"
            costs = gen.get("op_cost_per_MWh") or [float(gen.get("var_om_per_MWh") or 0)] * T
            c = float(costs[t] if t < len(costs) else costs[-1])
            if gtype == "electrolyzer":
                # Consumption cost minus H2 revenue
                h2_mwh = float(gen.get("hydrogen_mwh_per_tonne") or 55.0) or 55.0
                h2_price = float(gen.get("hydrogen_price_per_tonne") or 0)
                revenue_per_mwh = h2_price / h2_mwh if h2_mwh > 0 else 0.0
                op_expr += w * (c - revenue_per_mwh) * pe[g, t]
            else:
                op_expr += w * c * p[g, t]
        for s, st in enumerate(storage):
            op_expr += w * float(st.get("var_om_per_MWh") or 0) * dis[s, t]
            op_expr += w * float(st.get("var_om_per_MWh_in") or 0) * ch[s, t]
        for zi in range(nZ):
            op_expr += w * voll * nse[zi, t]

    m.setObjective(inv_expr + op_expr, GRB.MINIMIZE)

    # Gen limits by capacity * availability
    for g, gen in enumerate(gens):
        gtype = gen.get("type") or "thermal"
        av = gen.get("availability") or [1.0] * T
        for t in range(T):
            a = float(av[t] if t < len(av) else 1.0)
            if gtype == "electrolyzer":
                m.addConstr(pe[g, t] <= Cap[g] * a, name=f"elz_{g}_{t}")
                m.addConstr(p[g, t] == 0.0, name=f"p0elz_{g}_{t}")
            else:
                m.addConstr(p[g, t] <= Cap[g] * a, name=f"pmax_{g}_{t}")
                m.addConstr(pe[g, t] == 0.0, name=f"pe0_{g}_{t}")

    # Storage ops
    for s, st in enumerate(storage):
        eff_up = float(st.get("eff_up") or 0.92)
        eff_dn = float(st.get("eff_down") or 0.92)
        if eff_up <= 0:
            eff_up = 0.92
        if eff_dn <= 0:
            eff_dn = 0.92
        sd = float(st.get("self_disch") or 0.0)
        av = st.get("availability") or [1.0] * T
        for t in range(T):
            a = float(av[t] if t < len(av) else 1.0)
            m.addConstr(ch[s, t] <= CapP[s] * a, name=f"chmax_{s}_{t}")
            m.addConstr(dis[s, t] <= CapP[s] * a, name=f"dismax_{s}_{t}")
            m.addConstr(e[s, t] <= CapE[s], name=f"emax_{s}_{t}")
            if t == 0:
                # Cyclic: e_0 = e_{T-1} * (1-sd) + ch*eff - dis/eff  (link at end)
                pass
            else:
                m.addConstr(
                    e[s, t]
                    == e[s, t - 1] * (1.0 - sd)
                    + ch[s, t] * eff_up
                    - dis[s, t] / eff_dn,
                    name=f"ebal_{s}_{t}",
                )
        # cyclic closure
        if T >= 1:
            m.addConstr(
                e[s, 0]
                == e[s, T - 1] * (1.0 - sd)
                + ch[s, 0] * eff_up
                - dis[s, 0] / eff_dn,
                name=f"ebal_cyc_{s}",
            )

    # Line limits
    for ell, ln in enumerate(lines):
        lim = float(ln.get("max_flow_MW") or 0)
        if lim <= 0:
            lim = 1e6
        for t in range(T):
            m.addConstr(f[ell, t] <= lim, name=f"fmax_{ell}_{t}")
            m.addConstr(f[ell, t] >= -lim, name=f"fmin_{ell}_{t}")

    # Zone energy balance
    for t in range(T):
        load_map = demand[t]["load_MW"] if t < len(demand) else {}
        for zi, zid in enumerate(zone_ids):
            load = float(load_map.get(str(zid), load_map.get(zid, 0.0)))
            gen_sum = gp.quicksum(
                p[g, t]
                for g, gen in enumerate(gens)
                if int(gen["zone"]) == zid and (gen.get("type") or "") != "electrolyzer"
            )
            elz_sum = gp.quicksum(
                pe[g, t]
                for g, gen in enumerate(gens)
                if int(gen["zone"]) == zid and (gen.get("type") or "") == "electrolyzer"
            )
            dis_sum = gp.quicksum(
                dis[s, t] for s, st in enumerate(storage) if int(st["zone"]) == zid
            )
            ch_sum = gp.quicksum(
                ch[s, t] for s, st in enumerate(storage) if int(st["zone"]) == zid
            )
            # net import: flow into zone - flow out
            net_imp = gp.LinExpr()
            for ell, ln in enumerate(lines):
                if int(ln["from_zone"]) == zid:
                    net_imp -= f[ell, t]
                if int(ln["to_zone"]) == zid:
                    net_imp += f[ell, t]
            # gen + dis + import + nse = load + ch + elz
            m.addConstr(
                gen_sum + dis_sum + net_imp + nse[zi, t] == load + ch_sum + elz_sum,
                name=f"bal_z{zid}_t{t}",
            )
            m.addConstr(nse[zi, t] <= load, name=f"nse_ub_z{zid}_t{t}")

    # Min capacity requirements
    min_reqs = policies.get("min_capacity_requirements") or []
    min_assign = policies.get("min_capacity_assignments") or {}
    name_to_g = {gen["name"]: g for g, gen in enumerate(gens)}
    name_to_s = {st["name"]: s for s, st in enumerate(storage)}
    for req in min_reqs:
        rid = int(req["id"])
        min_mw = float(req["min_MW"])
        terms = []
        for name, ids in min_assign.items():
            if rid in ids:
                if name in name_to_g:
                    terms.append(Cap[name_to_g[name]])
                if name in name_to_s:
                    terms.append(CapP[name_to_s[name]])
        if terms:
            m.addConstr(gp.quicksum(terms) >= min_mw, name=f"mincap_{rid}")

    # CO2 cap (mass system-wide, annualized via weights)
    if policies.get("co2_mode") == "mass_system" and policies.get("co2_cap_tons"):
        co2_cap = float(policies["co2_cap_tons"])
        co2_expr = gp.LinExpr()
        for g, gen in enumerate(gens):
            ef = float(gen.get("co2_tons_per_MWh") or 0)
            if ef <= 0:
                continue
            for t in range(T):
                co2_expr += float(weights[t]) * ef * p[g, t]
        m.addConstr(co2_expr <= co2_cap, name="co2_mass")
    elif policies.get("co2_mode") == "rate_demand" and policies.get("co2_rate_tons_per_MWh"):
        rate = float(policies["co2_rate_tons_per_MWh"])
        co2_expr = gp.LinExpr()
        dem_expr = gp.LinExpr()
        for g, gen in enumerate(gens):
            ef = float(gen.get("co2_tons_per_MWh") or 0)
            if ef <= 0:
                continue
            for t in range(T):
                co2_expr += float(weights[t]) * ef * p[g, t]
        for t in range(T):
            load_map = demand[t]["load_MW"]
            total_load = sum(float(v) for v in load_map.values())
            dem_expr += float(weights[t]) * total_load
        m.addConstr(co2_expr <= rate * dem_expr, name="co2_rate")

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Cap_g = [0.0] * nG
    Cap_s_p = [0.0] * nS
    Cap_s_e = [0.0] * nS
    p_gt = [[0.0] * T for _ in range(nG)]
    pe_gt = [[0.0] * T for _ in range(nG)]
    ch_st = [[0.0] * T for _ in range(nS)]
    dis_st = [[0.0] * T for _ in range(nS)]
    e_st = [[0.0] * T for _ in range(nS)]
    nse_zt = [[0.0] * T for _ in range(nZ)]
    f_lt = [[0.0] * T for _ in range(nL)]
    obj_val = None
    obj_bound = None
    mip_gap = 0.0
    inv_cost = None
    op_cost = None

    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        try:
            obj_bound = float(m.ObjBound)
        except Exception:
            obj_bound = obj_val
        try:
            mip_gap = float(m.MIPGap) if m.IsMIP else 0.0
        except Exception:
            mip_gap = 0.0
        for g in range(nG):
            Cap_g[g] = float(Cap[g].X)
            for t in range(T):
                p_gt[g][t] = float(p[g, t].X)
                pe_gt[g][t] = float(pe[g, t].X)
        for s in range(nS):
            Cap_s_p[s] = float(CapP[s].X)
            Cap_s_e[s] = float(CapE[s].X)
            for t in range(T):
                ch_st[s][t] = float(ch[s, t].X)
                dis_st[s][t] = float(dis[s, t].X)
                e_st[s][t] = float(e[s, t].X)
        for zi in range(nZ):
            for t in range(T):
                nse_zt[zi][t] = float(nse[zi, t].X)
        for ell in range(nL):
            for t in range(T):
                f_lt[ell][t] = float(f[ell, t].X)

        # Decompose costs from solution
        inv_cost = 0.0
        for g, gen in enumerate(gens):
            exist = float(gen.get("existing_cap_MW") or 0)
            if int(gen.get("new_build", 1)) == 1:
                inv_cost += float(gen.get("inv_cost_per_MWyr") or 0) * max(0.0, Cap_g[g] - exist)
            inv_cost += float(gen.get("fixed_om_per_MWyr") or 0) * Cap_g[g]
        for s, st in enumerate(storage):
            exist_p = float(st.get("existing_cap_MW") or 0)
            exist_e = float(st.get("existing_cap_MWh") or 0)
            if int(st.get("new_build", 1)) == 1:
                inv_cost += float(st.get("inv_cost_per_MWyr") or 0) * max(0.0, Cap_s_p[s] - exist_p)
                inv_cost += float(st.get("inv_cost_per_MWhyr") or 0) * max(0.0, Cap_s_e[s] - exist_e)
            inv_cost += float(st.get("fixed_om_per_MWyr") or 0) * Cap_s_p[s]
            inv_cost += float(st.get("fixed_om_per_MWhyr") or 0) * Cap_s_e[s]
        op_cost = float(obj_val - inv_cost)

    residual = validate_cem_solution(
        network,
        Cap_g,
        Cap_s_p,
        Cap_s_e,
        p_gt,
        pe_gt,
        ch_st,
        dis_st,
        e_st,
        nse_zt,
        f_lt,
        obj_val,
        inv_cost,
    )

    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "investment_cost": inv_cost,
        "operating_cost": op_cost,
        "Cap_MW": Cap_g,
        "CapP_MW": Cap_s_p,
        "CapE_MWh": Cap_s_e,
        "p_MW": p_gt,
        "pe_MW": pe_gt,
        "charge_MW": ch_st,
        "discharge_MW": dis_st,
        "energy_MWh": e_st,
        "nse_MW": nse_zt,
        "flow_MW": f_lt,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        **residual,
    }


def validate_cem_solution(
    network: dict,
    Cap_g: list[float],
    Cap_s_p: list[float],
    Cap_s_e: list[float],
    p_gt: list[list[float]],
    pe_gt: list[list[float]],
    ch_st: list[list[float]],
    dis_st: list[list[float]],
    e_st: list[list[float]],
    nse_zt: list[list[float]],
    f_lt: list[list[float]],
    obj: float | None,
    inv_cost: float | None,
) -> dict[str, Any]:
    gens = network["generators"]
    storage = network.get("storage") or []
    demand = network["demand"]
    weights = network["time_weights"]
    lines = network.get("network_lines") or []
    zones = network["zones"]
    voll = float(network.get("voll") or 50000.0)
    T = int(network.get("n_time") or len(demand))
    zone_ids = [int(z["id"]) for z in zones]
    nZ, nG, nS, nL = len(zone_ids), len(gens), len(storage), len(lines)
    tol = DEFAULT_TOLERANCES

    if obj is None:
        return {
            "max_energy_balance_MW": float("inf"),
            "max_capacity_bound_MW": float("inf"),
            "max_storage_balance_MWh": float("inf"),
            "max_flow_limit_MW": float("inf"),
            "cost_recomputed": None,
            "investment_cost_recomputed": None,
            "operating_cost_recomputed": None,
            "validation_passed": False,
        }

    max_bal = 0.0
    max_cap = 0.0
    max_stor = 0.0
    max_flow = 0.0

    # Capacity bounds & dispatch vs cap
    for g, gen in enumerate(gens):
        exist = float(gen.get("existing_cap_MW") or 0)
        maxc = float(gen.get("max_cap_MW", -1))
        minc = float(gen.get("min_cap_MW") or 0)
        c = Cap_g[g]
        nb = int(gen.get("new_build", 1))
        if nb == 0:
            # Fixed at existing; GenX Max_Cap_MW=0 means no expansion, not total max 0
            max_cap = max(max_cap, abs(c - exist))
        else:
            max_cap = max(max_cap, max(0.0, minc - c))
            max_cap = max(max_cap, max(0.0, exist - c))
            if maxc >= 0:
                max_cap = max(max_cap, max(0.0, c - maxc))
        av = gen.get("availability") or [1.0] * T
        gtype = gen.get("type") or "thermal"
        for t in range(T):
            a = float(av[t] if t < len(av) else 1.0)
            if gtype == "electrolyzer":
                max_cap = max(max_cap, max(0.0, pe_gt[g][t] - c * a - 1e-9))
            else:
                max_cap = max(max_cap, max(0.0, p_gt[g][t] - c * a - 1e-9))

    for s, st in enumerate(storage):
        min_d = float(st.get("min_duration_h") or 1.0)
        max_d = float(st.get("max_duration_h") or 10.0)
        max_cap = max(max_cap, max(0.0, min_d * Cap_s_p[s] - Cap_s_e[s]))
        max_cap = max(max_cap, max(0.0, Cap_s_e[s] - max_d * Cap_s_p[s]))
        eff_up = float(st.get("eff_up") or 0.92) or 0.92
        eff_dn = float(st.get("eff_down") or 0.92) or 0.92
        sd = float(st.get("self_disch") or 0.0)
        for t in range(T):
            max_cap = max(max_cap, max(0.0, ch_st[s][t] - Cap_s_p[s]))
            max_cap = max(max_cap, max(0.0, dis_st[s][t] - Cap_s_p[s]))
            max_cap = max(max_cap, max(0.0, e_st[s][t] - Cap_s_e[s]))
            prev = e_st[s][T - 1] if t == 0 else e_st[s][t - 1]
            expected = prev * (1.0 - sd) + ch_st[s][t] * eff_up - dis_st[s][t] / eff_dn
            max_stor = max(max_stor, abs(e_st[s][t] - expected))

    for t in range(T):
        load_map = demand[t]["load_MW"]
        for zi, zid in enumerate(zone_ids):
            load = float(load_map.get(str(zid), load_map.get(zid, 0.0)))
            gen_sum = sum(
                p_gt[g][t]
                for g, gen in enumerate(gens)
                if int(gen["zone"]) == zid and (gen.get("type") or "") != "electrolyzer"
            )
            elz_sum = sum(
                pe_gt[g][t]
                for g, gen in enumerate(gens)
                if int(gen["zone"]) == zid and (gen.get("type") or "") == "electrolyzer"
            )
            dis_sum = sum(dis_st[s][t] for s, st in enumerate(storage) if int(st["zone"]) == zid)
            ch_sum = sum(ch_st[s][t] for s, st in enumerate(storage) if int(st["zone"]) == zid)
            net_imp = 0.0
            for ell, ln in enumerate(lines):
                if int(ln["from_zone"]) == zid:
                    net_imp -= f_lt[ell][t]
                if int(ln["to_zone"]) == zid:
                    net_imp += f_lt[ell][t]
            bal = gen_sum + dis_sum + net_imp + nse_zt[zi][t] - load - ch_sum - elz_sum
            max_bal = max(max_bal, abs(bal))

    for ell, ln in enumerate(lines):
        lim = float(ln.get("max_flow_MW") or 0) or 1e6
        for t in range(T):
            max_flow = max(max_flow, max(0.0, abs(f_lt[ell][t]) - lim))

    # Recompute costs
    inv_r = 0.0
    for g, gen in enumerate(gens):
        exist = float(gen.get("existing_cap_MW") or 0)
        if int(gen.get("new_build", 1)) == 1:
            inv_r += float(gen.get("inv_cost_per_MWyr") or 0) * max(0.0, Cap_g[g] - exist)
        inv_r += float(gen.get("fixed_om_per_MWyr") or 0) * Cap_g[g]
    for s, st in enumerate(storage):
        exist_p = float(st.get("existing_cap_MW") or 0)
        exist_e = float(st.get("existing_cap_MWh") or 0)
        if int(st.get("new_build", 1)) == 1:
            inv_r += float(st.get("inv_cost_per_MWyr") or 0) * max(0.0, Cap_s_p[s] - exist_p)
            inv_r += float(st.get("inv_cost_per_MWhyr") or 0) * max(0.0, Cap_s_e[s] - exist_e)
        inv_r += float(st.get("fixed_om_per_MWyr") or 0) * Cap_s_p[s]
        inv_r += float(st.get("fixed_om_per_MWhyr") or 0) * Cap_s_e[s]

    op_r = 0.0
    for t in range(T):
        w = float(weights[t])
        for g, gen in enumerate(gens):
            gtype = gen.get("type") or "thermal"
            costs = gen.get("op_cost_per_MWh") or [0.0] * T
            c = float(costs[t] if t < len(costs) else 0.0)
            if gtype == "electrolyzer":
                h2_mwh = float(gen.get("hydrogen_mwh_per_tonne") or 55.0) or 55.0
                h2_price = float(gen.get("hydrogen_price_per_tonne") or 0)
                rev = h2_price / h2_mwh if h2_mwh > 0 else 0.0
                op_r += w * (c - rev) * pe_gt[g][t]
            else:
                op_r += w * c * p_gt[g][t]
        for s, st in enumerate(storage):
            op_r += w * float(st.get("var_om_per_MWh") or 0) * dis_st[s][t]
            op_r += w * float(st.get("var_om_per_MWh_in") or 0) * ch_st[s][t]
        for zi in range(nZ):
            op_r += w * voll * nse_zt[zi][t]

    cost_r = inv_r + op_r
    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_cap <= tol["generator_bound_mw"]
        and max_stor <= 1e-3
        and max_flow <= tol["thermal_mw"]
    )
    if obj is not None and abs(cost_r - obj) > max(1.0, 1e-5 * max(1.0, abs(obj))):
        # large cost mismatch flags failure
        if abs(cost_r - obj) > max(100.0, 1e-4 * max(1.0, abs(obj))):
            passed = False

    return {
        "max_energy_balance_MW": max_bal,
        "max_capacity_bound_MW": max_cap,
        "max_storage_balance_MWh": max_stor,
        "max_flow_limit_MW": max_flow,
        "cost_recomputed": cost_r,
        "investment_cost_recomputed": inv_r,
        "operating_cost_recomputed": op_r,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_cem(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "cem",
        "base_problem": config.get("base_problem", "resource_capacity_expansion"),
        "cem": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    import sys as _sys

    d = (
        Path(_sys.argv[1])
        if len(_sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case01_1_three_zones_cem"
    )
    r = run_case(d, quiet=True)
    e = r["cem"]
    print(
        f"[{r['case']}] status={e['status']} obj={e['obj']} "
        f"bal={e.get('max_energy_balance_MW')}"
    )
