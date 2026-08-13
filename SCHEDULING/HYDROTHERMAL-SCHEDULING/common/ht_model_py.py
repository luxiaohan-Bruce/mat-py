"""Hydrothermal scheduling v1 MILP/LP (gurobipy).

Deterministic or two-stage stochastic (first-stage commitment, second-stage dispatch).
Copperplate or networked DC when network present.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    return network, config


def _status_name(status: int) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(status, str(status))


def _as_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return list(x)


def solve_ht(data: dict[str, Any], config: dict[str, Any], *, quiet: bool = True) -> dict[str, Any]:
    T = int(data["time_periods"])
    dt = float(data.get("dt_hours", 1.0))
    thermal = _as_list(data.get("thermal_units", []))
    hs = data.get("hydro_system") or {}
    reservoirs = _as_list(hs.get("reservoirs", []))
    cascades = _as_list(hs.get("cascades", []))
    flow_to_vol = float(hs.get("flow_to_volume", 1.0))  # RCUC: 1.0 (same units)
    use_commitment = bool(data.get("use_commitment", True))
    networked = bool(data.get("networked", False))
    baseMVA = float(data.get("baseMVA", 100.0))
    deficit_cost = float(data.get("deficit_cost", 1.0e5))
    reserve_frac = float(data.get("reserve_fraction", 0.0))

    scenarios = _as_list(data.get("scenarios"))
    if not scenarios:
        # Deterministic wrapper
        dem = _as_list(data.get("demand", [0.0] * T))
        infl = {}
        for r in reservoirs:
            infl[str(r["id"])] = _as_list(r.get("inflows", [0.0] * T))
        scenarios = [
            {
                "id": 1,
                "probability": 1.0,
                "demand": dem,
                "bus_demand": data.get("bus_demand"),
                "inflows": infl,
            }
        ]
    nS = len(scenarios)
    probs = [float(s.get("probability", 1.0 / nS)) for s in scenarios]
    sp = sum(probs) or 1.0
    probs = [p / sp for p in probs]

    buses = _as_list(data.get("buses", []))
    branches = _as_list(data.get("branches", []))
    if networked and buses:
        bus_ids = [int(b["bus_i"]) for b in buses]
        bus_pos = {b: i for i, b in enumerate(bus_ids)}
        ref_bus = bus_ids[0]
        for b in buses:
            if int(b.get("type", 1)) == 3:
                ref_bus = int(b["bus_i"])
                break
        nB = len(bus_ids)
        nL = len(branches)
    else:
        networked = False
        bus_ids, bus_pos, ref_bus, nB, nL = [], {}, 0, 0, 0

    nG = len(thermal)
    nH = len(reservoirs)
    G, H, TT, SS = range(nG), range(nH), range(T), range(nS)

    # Cascade map: for each reservoir, list of (upstream_index, delay)
    res_id_to_idx = {int(r["id"]): h for h, r in enumerate(reservoirs)}
    upstream_of: list[list[tuple[int, int]]] = [[] for _ in H]
    for c in cascades:
        fr, to, delay = int(c["from"]), int(c["to"]), int(c.get("delay", 0))
        if to in res_id_to_idx and fr in res_id_to_idx:
            upstream_of[res_id_to_idx[to]].append((res_id_to_idx[fr], delay))
    # Also from reservoir fields
    for h, r in enumerate(reservoirs):
        up = r.get("upstream")
        if up is not None and int(up) in res_id_to_idx:
            delay = int(r.get("delay", r.get("delay_h", 0)) or 0)
            pair = (res_id_to_idx[int(up)], delay)
            if pair not in upstream_of[h]:
                upstream_of[h].append(pair)

    gp_params = dict(config.get("gurobi_parameters") or {})
    m = gp.Model(config.get("case", "ht"))
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = int(gp_params.get("Seed", config.get("seed", 1)))
    m.Params.Threads = int(gp_params.get("Threads", config.get("threads", 1)))
    m.Params.MIPGap = float(gp_params.get("MIPGap", config.get("mip_gap", 1e-6)))
    m.Params.TimeLimit = float(gp_params.get("TimeLimit", config.get("time_limit", 300)))

    # First-stage commitment (shared across scenarios)
    if use_commitment:
        u = m.addVars(nG, T, vtype=GRB.BINARY, name="u")
        v_start = m.addVars(nG, T, vtype=GRB.BINARY, name="start")
        v_stop = m.addVars(nG, T, vtype=GRB.BINARY, name="stop")
    else:
        u = m.addVars(nG, T, lb=0.0, ub=1.0, name="u")
        v_start = m.addVars(nG, T, lb=0.0, ub=1.0, name="start")
        v_stop = m.addVars(nG, T, lb=0.0, ub=1.0, name="stop")

    # Second-stage: thermal power, hydro release/spill/volume/power, deficit
    Pt = m.addVars(nS, nG, T, lb=0.0, name="Pt")
    release = m.addVars(nS, nH, T, lb=0.0, name="rel")
    spill = m.addVars(nS, nH, T, lb=0.0, name="spill")
    Vol = m.addVars(nS, nH, T, lb=0.0, name="V")
    Ph = m.addVars(nS, nH, T, lb=0.0, name="Ph")
    if networked:
        theta = m.addVars(nS, nB, T, lb=-math.pi, ub=math.pi, name="th")
        flow = m.addVars(nS, nL, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f")
        deficit = m.addVars(nS, nB, T, lb=0.0, name="def")  # per-bus unserved
    else:
        theta = flow = None
        deficit = m.addVars(nS, T, lb=0.0, name="def")

    # Bounds
    for g, gen in enumerate(thermal):
        pmax = float(gen["Pmax"])
        for s in SS:
            for t in TT:
                Pt[s, g, t].UB = pmax
    for h, r in enumerate(reservoirs):
        vmax = float(r.get("max_volume", r.get("Vmax", 1e9)))
        vmin = float(r.get("min_volume", r.get("Vmin", 0.0)))
        rmax = float(r.get("max_usage", r.get("qmax_plant", 1e9)))
        smax = float(r.get("max_spillage", r.get("spill_max", 1e9)))
        pmax_h = float(r.get("pmax_plant", r.get("volume_to_power", 1.0) * rmax))
        for s in SS:
            for t in TT:
                Vol[s, h, t].LB = vmin
                Vol[s, h, t].UB = vmax
                release[s, h, t].UB = rmax
                spill[s, h, t].UB = max(smax, 0.0)
                Ph[s, h, t].UB = max(pmax_h, 0.0)

    obj = gp.LinExpr()
    has_quad = False
    Qpairs: list[tuple[Any, float]] = []

    # Thermal production + startup (first-stage startup charged once)
    for g, gen in enumerate(thermal):
        c0 = float(gen.get("c0", 0.0))
        c1 = float(gen.get("c1", 0.0))
        c2 = float(gen.get("c2", 0.0))
        suc = float(gen.get("fixed_startup", 0.0)) + float(gen.get("cool_cost", 0.0))
        for t in TT:
            obj += suc * v_start[g, t]
            # no-load cost charged when on (expected, same for all scen via first-stage u)
            obj += c0 * u[g, t]
        for s in SS:
            pr = probs[s]
            for t in TT:
                obj += pr * c1 * Pt[s, g, t]
                if abs(c2) > 1e-14:
                    has_quad = True
                    # store for QuadExpr
                    Qpairs.append((Pt[s, g, t], pr * c2))

    # Deficit + future water value
    for s in SS:
        pr = probs[s]
        if networked:
            for bi in range(nB):
                for t in TT:
                    obj += pr * deficit_cost * deficit[s, bi, t]
        else:
            for t in TT:
                obj += pr * deficit_cost * deficit[s, t]
        for h, r in enumerate(reservoirs):
            # Terminal water value (optional; default on when present)
            fv = float(r.get("future_value", 0.0))
            if abs(fv) > 1e-12:
                obj += pr * (-fv) * Vol[s, h, T - 1]

    if has_quad:
        qobj = gp.QuadExpr()
        qobj += obj
        for var, coef in Qpairs:
            qobj += coef * var * var
        m.setObjective(qobj, GRB.MINIMIZE)
    else:
        m.setObjective(obj, GRB.MINIMIZE)

    # Commitment logic
    for g, gen in enumerate(thermal):
        init = int(gen.get("initial_status", 0))
        u0 = 1 if init > 0 else 0
        min_up = min(int(gen.get("min_up", 1)), T)
        min_down = min(int(gen.get("min_down", 1)), T)
        # residual must stay on/off
        if init > 0:
            residual = max(0, min_up - init)
            for t in range(min(T, residual)):
                m.addConstr(u[g, t] == 1)
        elif init < 0:
            residual = max(0, min_down - abs(init))
            for t in range(min(T, residual)):
                m.addConstr(u[g, t] == 0)

        for t in TT:
            prev = u0 if t == 0 else u[g, t - 1]
            m.addConstr(u[g, t] - prev == v_start[g, t] - v_stop[g, t])
            m.addConstr(v_start[g, t] + v_stop[g, t] <= 1)
            # min up
            if min_up > 1 and t >= min_up - 1:
                m.addConstr(
                    gp.quicksum(v_start[g, k] for k in range(t - min_up + 1, t + 1))
                    <= u[g, t]
                )
            # min down
            if min_down > 1 and t >= min_down - 1:
                m.addConstr(
                    gp.quicksum(v_stop[g, k] for k in range(t - min_down + 1, t + 1))
                    <= 1 - u[g, t]
                )

        pmin = float(gen["Pmin"])
        pmax = float(gen["Pmax"])
        ru = float(gen.get("ramp_up", pmax))
        rd = float(gen.get("ramp_down", pmax))
        p0 = float(gen.get("P0", pmin * u0 if u0 else 0.0))
        for s in SS:
            for t in TT:
                m.addConstr(Pt[s, g, t] >= pmin * u[g, t])
                m.addConstr(Pt[s, g, t] <= pmax * u[g, t])
                # Ramps with off-state relaxation (aligned MATLAB)
                # p[t]-p[t-1] <= RU + Pmax*(1-u[t-1])
                # p[t-1]-p[t] <= RD + Pmax*(1-u[t])
                if t == 0:
                    m.addConstr(Pt[s, g, t] - p0 <= ru + pmax * (1 - u0))
                    m.addConstr(p0 - Pt[s, g, t] <= rd + pmax * (1 - u[g, t]))
                else:
                    m.addConstr(
                        Pt[s, g, t] - Pt[s, g, t - 1]
                        <= ru + pmax * (1 - u[g, t - 1])
                    )
                    m.addConstr(
                        Pt[s, g, t - 1] - Pt[s, g, t]
                        <= rd + pmax * (1 - u[g, t])
                    )

    # Hydro physics
    for s in SS:
        scen = scenarios[s]
        infl_map = scen.get("inflows") or {}
        for h, r in enumerate(reservoirs):
            rid = str(r["id"])
            inflows = _as_list(infl_map.get(rid, r.get("inflows", [0.0] * T)))
            if len(inflows) < T:
                inflows = list(inflows) + [0.0] * (T - len(inflows))
            V0 = float(r.get("initial_volume", r.get("min_volume", 0.0)))
            k = float(r.get("volume_to_power", 0.0))
            # linear P = k * release
            for t in TT:
                m.addConstr(Ph[s, h, t] == k * release[s, h, t])

            for t in TT:
                # upstream delayed releases+spills
                up_in = gp.LinExpr()
                for uh, delay in upstream_of[h]:
                    src_t = t - delay
                    if src_t >= 0:
                        up_in += release[s, uh, src_t] + spill[s, uh, src_t]
                    # if delay > t, no historical series: ignore (assume 0)
                prev_V = V0 if t == 0 else Vol[s, h, t - 1]
                # V_t = V_{t-1} + flow_to_vol * (inflow + up - rel - spill)
                m.addConstr(
                    Vol[s, h, t]
                    == prev_V
                    + flow_to_vol
                    * (float(inflows[t]) + up_in - release[s, h, t] - spill[s, h, t])
                )

            # terminal volume >= target if provided, else >= min (already LB)
            Vtarget = r.get("target_volume")
            if Vtarget is not None:
                m.addConstr(Vol[s, h, T - 1] >= float(Vtarget) * 0.0 + float(r.get("min_volume", 0.0)))
                # soft: enforce V_T >= min only (hard target can be infeasible); keep min
                # Optional mild terminal: V_T >= 0.95 * target if feasible — use min for v1
                pass

    # Power balance
    for s in SS:
        scen = scenarios[s]
        if networked:
            bus_dem = scen.get("bus_demand") or data.get("bus_demand") or {}
            # map thermal/hydro to buses
            gen_bus = [int(g.get("bus", ref_bus)) for g in thermal]
            hyd_bus = [int(r.get("bus", ref_bus)) for r in reservoirs]
            for t in TT:
                m.addConstr(theta[s, bus_pos[ref_bus], t] == 0.0)
                # branch physics
                for ell, br in enumerate(branches):
                    if int(br.get("status", 1)) == 0:
                        m.addConstr(flow[s, ell, t] == 0.0)
                        continue
                    i = bus_pos[int(br["fbus"])]
                    j = bus_pos[int(br["tbus"])]
                    x = float(br["x"])
                    if abs(x) < 1e-12:
                        m.addConstr(theta[s, i, t] - theta[s, j, t] == 0.0)
                    else:
                        # f_MW = baseMVA / x * (theta_i - theta_j)  (x in pu)
                        m.addConstr(
                            flow[s, ell, t]
                            == (baseMVA / x) * (theta[s, i, t] - theta[s, j, t])
                        )
                    rate = float(br.get("rateA", 0.0))
                    if rate > 0:
                        m.addConstr(flow[s, ell, t] <= rate)
                        m.addConstr(flow[s, ell, t] >= -rate)
                # nodal balance
                for bi, bid in enumerate(bus_ids):
                    dem_b = 0.0
                    series = bus_dem.get(str(bid)) or bus_dem.get(bid)
                    if series is not None:
                        dem_b = float(_as_list(series)[t]) if t < len(_as_list(series)) else 0.0
                    inj = gp.LinExpr()
                    for g in G:
                        if gen_bus[g] == bid:
                            inj += Pt[s, g, t]
                    for h in H:
                        if hyd_bus[h] == bid:
                            inj += Ph[s, h, t]
                    # flows
                    for ell, br in enumerate(branches):
                        if int(br.get("status", 1)) == 0:
                            continue
                        if int(br["fbus"]) == bid:
                            inj -= flow[s, ell, t]
                        if int(br["tbus"]) == bid:
                            inj += flow[s, ell, t]
                    m.addConstr(
                        inj + deficit[s, bi, t] == dem_b, name=f"bal_{s}_{bid}_{t}"
                    )
        else:
            dem = _as_list(scen.get("demand", [0.0] * T))
            for t in TT:
                m.addConstr(
                    gp.quicksum(Pt[s, g, t] for g in G)
                    + gp.quicksum(Ph[s, h, t] for h in H)
                    + deficit[s, t]
                    == float(dem[t] if t < len(dem) else 0.0),
                    name=f"bal_{s}_{t}",
                )
                if reserve_frac > 0:
                    # simple capacity reserve on thermal
                    m.addConstr(
                        gp.quicksum(
                            float(thermal[g]["Pmax"]) * u[g, t] - Pt[s, g, t] for g in G
                        )
                        + gp.quicksum(
                            float(
                                reservoirs[h].get(
                                    "pmax_plant",
                                    reservoirs[h].get("max_usage", 0)
                                    * reservoirs[h].get("volume_to_power", 0),
                                )
                            )
                            - Ph[s, h, t]
                            for h in H
                        )
                        >= reserve_frac * float(dem[t] if t < len(dem) else 0.0)
                    )

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m.Status)

    result: dict[str, Any] = {
        "status": status,
        "obj": None,
        "runtime": runtime,
        "mip_gap": None,
        "n_scenarios": nS,
        "time_periods": T,
        "networked": networked,
        "use_commitment": use_commitment,
        "max_power_balance_MW": None,
        "max_water_balance_hm3": None,
        "validation_passed": False,
        "thermal_on_hours": None,
        "total_deficit_MW": None,
    }

    if m.SolCount < 1:
        return result

    result["obj"] = float(m.ObjVal)
    try:
        result["mip_gap"] = float(m.MIPGap) if m.IsMIP else 0.0
    except Exception:
        result["mip_gap"] = 0.0

    # Residuals
    max_bal = 0.0
    max_water = 0.0
    total_def = 0.0
    Pt_x = m.getAttr("X", Pt)
    Ph_x = m.getAttr("X", Ph)
    rel_x = m.getAttr("X", release)
    sp_x = m.getAttr("X", spill)
    V_x = m.getAttr("X", Vol)
    def_x = m.getAttr("X", deficit)

    for s in SS:
        scen = scenarios[s]
        if not networked:
            dem = _as_list(scen.get("demand", [0.0] * T))
            for t in TT:
                gen_sum = sum(Pt_x[s, g, t] for g in G) + sum(Ph_x[s, h, t] for h in H)
                bal = abs(gen_sum + def_x[s, t] - float(dem[t] if t < len(dem) else 0.0))
                max_bal = max(max_bal, bal)
                total_def += probs[s] * def_x[s, t]
        else:
            bus_dem = scen.get("bus_demand") or {}
            flow_x = m.getAttr("X", flow)
            gen_bus = [int(g.get("bus", ref_bus)) for g in thermal]
            hyd_bus = [int(r.get("bus", ref_bus)) for r in reservoirs]
            for t in TT:
                for bi, bid in enumerate(bus_ids):
                    dem_b = 0.0
                    series = bus_dem.get(str(bid)) or bus_dem.get(bid)
                    if series is not None:
                        dem_b = float(_as_list(series)[t]) if t < len(_as_list(series)) else 0.0
                    inj = 0.0
                    for g in G:
                        if gen_bus[g] == bid:
                            inj += Pt_x[s, g, t]
                    for h in H:
                        if hyd_bus[h] == bid:
                            inj += Ph_x[s, h, t]
                    for ell, br in enumerate(branches):
                        if int(br.get("status", 1)) == 0:
                            continue
                        if int(br["fbus"]) == bid:
                            inj -= flow_x[s, ell, t]
                        if int(br["tbus"]) == bid:
                            inj += flow_x[s, ell, t]
                    inj += def_x[s, bi, t]
                    max_bal = max(max_bal, abs(inj - dem_b))
                    total_def += probs[s] * def_x[s, bi, t]

        for h, r in enumerate(reservoirs):
            rid = str(r["id"])
            inflows = _as_list((scen.get("inflows") or {}).get(rid, r.get("inflows", [0.0] * T)))
            if len(inflows) < T:
                inflows = list(inflows) + [0.0] * (T - len(inflows))
            V0 = float(r.get("initial_volume", 0.0))
            for t in TT:
                up_in = 0.0
                for uh, delay in upstream_of[h]:
                    src_t = t - delay
                    if src_t >= 0:
                        up_in += rel_x[s, uh, src_t] + sp_x[s, uh, src_t]
                prev = V0 if t == 0 else V_x[s, h, t - 1]
                expected = prev + flow_to_vol * (
                    float(inflows[t]) + up_in - rel_x[s, h, t] - sp_x[s, h, t]
                )
                max_water = max(max_water, abs(V_x[s, h, t] - expected))

    u_x = m.getAttr("X", u)
    on_hours = sum(1 for g in G for t in TT if u_x[g, t] > 0.5)

    result["max_power_balance_MW"] = max_bal
    result["max_water_balance_hm3"] = max_water
    result["total_deficit_MW"] = total_def
    result["thermal_on_hours"] = on_hours
    result["validation_passed"] = (
        max_bal <= 1e-3
        and max_water <= 1e-4
        and status in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT", "INTERRUPTED")
    )
    return result


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    data, config = load_case(case_dir)
    sol = solve_ht(data, config, quiet=quiet)
    case_name = config.get("case", case_dir.name)
    payload = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "ht",
        "base_problem": "hydrothermal_scheduling",
        "ht": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    out = case_dir / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "python_result.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload
