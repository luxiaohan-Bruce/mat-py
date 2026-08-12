"""Multi-period DC Power Restoration / Black Start (gurobipy) — PLAM B16 v1.

Horizon T. Binary: bus energized y[b,t], branch closed z[ell,t], gen online u[g,t]
(all monotonic nondecreasing in t). Continuous: Pg, f, theta, load fraction x.

Damaged components start unavailable; become available once "repaired" (monotonic
availability binary, repair lag 1 period by default). Undamaged start available.

Energization:
  - blackstart gens may online if available (self-start)
  - non-blackstart gens need bus energized
  - bus energized only if available and (has online gen OR path from energized
    neighbor via a closed branch) — linearized propagation

DC flow via Gurobi indicators on z. Objective: max sum_t w_t * weight_b * Pd * x.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from dc_network import (  # noqa: E402
    bus_maps,
    branch_susceptance,
    is_zero_x,
    thermal_rate_mw,
)
# common_protocol helpers vendored in this common/ directory
from result_io import load_case, write_result  # noqa: E402
from tolerances import DEFAULT_TOLERANCES, solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }.get(m.Status, str(m.Status))


def _as_set_int(vals) -> set[int]:
    return {int(v) for v in (vals or [])}


def solve_restore(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)

    T = int(config.get("horizon_T", 5))
    T = max(1, T)
    repair_lag = int(config.get("repair_lag", 1))  # periods after repair action
    repair_lag = max(0, repair_lag)
    repairs_per_period = config.get("repairs_per_period", None)
    if repairs_per_period is not None:
        repairs_per_period = int(repairs_per_period)

    dmg_br = _as_set_int(config.get("damaged_branches"))  # branch ids (1-based)
    dmg_gen = _as_set_int(config.get("damaged_gens"))  # 0-based gen indices
    dmg_bus = _as_set_int(config.get("damaged_buses"))  # bus_i ids

    # blackstart: list of 0-based gen indices; default = all gens (PMR ROP style)
    bs_cfg = config.get("blackstart_gens")
    if bs_cfg is None:
        blackstart = set(range(nG))
    else:
        blackstart = _as_set_int(bs_cfg)

    # gen capacity multipliers (renewable availability etc.), default 1.0
    # Prefer list aligned with gens; also accept dict keyed by index/bus.
    gen_avail = config.get("gen_availability")
    pmax_scale: list[float] = []
    for g, gen in enumerate(gens):
        sc = float(gen.get("availability", 1.0))
        if isinstance(gen_avail, list) and g < len(gen_avail):
            sc = float(gen_avail[g])
        elif isinstance(gen_avail, dict):
            key = str(g)
            bus_key = str(int(gen["bus"]))
            sc = float(gen_avail.get(key, gen_avail.get(bus_key, sc)))
        pmax_scale.append(max(0.0, sc))

    # load weights: list aligned with buses, or dict by bus_i
    weights = config.get("load_weights")
    w_bus: list[float] = []
    for bi, bid in enumerate(bus_ids):
        w = 1.0
        if isinstance(weights, list) and bi < len(weights):
            w = float(weights[bi])
        elif isinstance(weights, dict):
            w = float(weights.get(str(bid), weights.get(bid, 1.0)))
        w_bus.append(w)

    # time weights: earlier periods preferred
    tw_cfg = config.get("time_weights")
    if tw_cfg is not None and len(tw_cfg) >= T:
        time_w = [float(tw_cfg[t]) for t in range(T)]
    else:
        time_w = [float(T - t) for t in range(T)]  # T, T-1, ..., 1

    params = solver_params_from_config(config)

    m = gp.Model("dc_restore")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    # --- variables ---
    y = m.addVars(nB, T, vtype=GRB.BINARY, name="y")  # bus energized
    z = m.addVars(nL, T, vtype=GRB.BINARY, name="z")  # branch closed
    u = m.addVars(nG, T, vtype=GRB.BINARY, name="u")  # gen online
    # availability after repair (monotonic)
    a_br = m.addVars(nL, T, vtype=GRB.BINARY, name="a_br")
    a_gen = m.addVars(nG, T, vtype=GRB.BINARY, name="a_gen")
    a_bus = m.addVars(nB, T, vtype=GRB.BINARY, name="a_bus")

    theta = m.addVars(nB, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, T, lb=0.0, name="Pg_MW")
    f = m.addVars(nL, T, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f_MW")
    x = m.addVars(nB, T, lb=0.0, ub=1.0, name="load_frac")

    # propagation auxiliaries: prop[ell,t,dir] dir=0 from f->t, dir=1 from t->f
    prop = m.addVars(nL, T, 2, lb=0.0, ub=1.0, name="prop")

    # reference angle when ref bus energized (always fix ref theta = 0 for numerical stability)
    for t in range(T):
        m.addConstr(theta[bus_pos[ref_bus], t] == 0.0, name=f"ref_{t}")

    # --- availability initial + monotonic + repair lag ---
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        initially = 0 if (bid in dmg_br or int(br.get("status", 1)) == 0) else 1
        for t in range(T):
            if initially:
                m.addConstr(a_br[ell, t] == 1, name=f"abr_ok_{ell}_{t}")
            else:
                if t == 0:
                    # available at t=0 only if lag==0 and we "repair at 0" — keep offline at t=0
                    m.addConstr(a_br[ell, 0] == 0, name=f"abr0_{ell}")
                else:
                    m.addConstr(a_br[ell, t] >= a_br[ell, t - 1], name=f"abr_mono_{ell}_{t}")
        # lag: if lag>=1, a[t] <= a[t-1] + (implicit free jump); first increase is repair complete
        # With lag 1: damaged stays 0 at t=0; can jump to 1 from t=1 onward (already modeled)

    for g, gen in enumerate(gens):
        initially = 0 if (g in dmg_gen or int(gen.get("status", 1)) == 0) else 1
        if pmax_scale[g] <= 0.0:
            initially = 0  # fully unavailable
        for t in range(T):
            if initially and pmax_scale[g] > 0:
                m.addConstr(a_gen[g, t] == 1, name=f"agen_ok_{g}_{t}")
            else:
                if t == 0:
                    m.addConstr(a_gen[g, 0] == 0, name=f"agen0_{g}")
                else:
                    m.addConstr(a_gen[g, t] >= a_gen[g, t - 1], name=f"agen_mono_{g}_{t}")
                # if permanently unavailable (scale 0 and not damaged repairable), lock
                if pmax_scale[g] <= 0.0 and g not in dmg_gen and int(gen.get("status", 1)) != 0:
                    # renewable at 0 availability and not in damage list: stay offline
                    m.addConstr(a_gen[g, t] == 0, name=f"agen_lock_{g}_{t}")

    for bi, bid in enumerate(bus_ids):
        initially = 0 if bid in dmg_bus else 1
        for t in range(T):
            if initially:
                m.addConstr(a_bus[bi, t] == 1, name=f"abus_ok_{bi}_{t}")
            else:
                if t == 0:
                    m.addConstr(a_bus[bi, 0] == 0, name=f"abus0_{bi}")
                else:
                    m.addConstr(a_bus[bi, t] >= a_bus[bi, t - 1], name=f"abus_mono_{bi}_{t}")

    # repair budget per period (optional): count newly available components
    if repairs_per_period is not None:
        for t in range(T):
            terms = []
            for ell in range(nL):
                bid = int(branches[ell]["id"])
                if bid in dmg_br or int(branches[ell].get("status", 1)) == 0:
                    if t == 0:
                        terms.append(a_br[ell, 0])
                    else:
                        terms.append(a_br[ell, t] - a_br[ell, t - 1])
            for g in range(nG):
                if g in dmg_gen or int(gens[g].get("status", 1)) == 0:
                    if t == 0:
                        terms.append(a_gen[g, 0])
                    else:
                        terms.append(a_gen[g, t] - a_gen[g, t - 1])
            for bi, bid in enumerate(bus_ids):
                if bid in dmg_bus:
                    if t == 0:
                        terms.append(a_bus[bi, 0])
                    else:
                        terms.append(a_bus[bi, t] - a_bus[bi, t - 1])
            if terms:
                m.addConstr(
                    gp.quicksum(terms) <= repairs_per_period, name=f"repair_budget_{t}"
                )

    # --- topology / energization logic ---
    for t in range(T):
        # monotonic energization states
        if t > 0:
            for bi in range(nB):
                m.addConstr(y[bi, t] >= y[bi, t - 1], name=f"y_mono_{bi}_{t}")
            for ell in range(nL):
                m.addConstr(z[ell, t] >= z[ell, t - 1], name=f"z_mono_{ell}_{t}")
            for g in range(nG):
                m.addConstr(u[g, t] >= u[g, t - 1], name=f"u_mono_{g}_{t}")

        for ell in range(nL):
            i = bus_pos[int(branches[ell]["fbus"])]
            j = bus_pos[int(branches[ell]["tbus"])]
            m.addConstr(z[ell, t] <= a_br[ell, t], name=f"z_av_{ell}_{t}")
            m.addConstr(z[ell, t] <= y[i, t], name=f"z_yi_{ell}_{t}")
            m.addConstr(z[ell, t] <= y[j, t], name=f"z_yj_{ell}_{t}")
            # propagation
            m.addConstr(prop[ell, t, 0] <= z[ell, t], name=f"p0z_{ell}_{t}")
            m.addConstr(prop[ell, t, 0] <= y[i, t], name=f"p0y_{ell}_{t}")
            m.addConstr(prop[ell, t, 1] <= z[ell, t], name=f"p1z_{ell}_{t}")
            m.addConstr(prop[ell, t, 1] <= y[j, t], name=f"p1y_{ell}_{t}")

        for g, gen in enumerate(gens):
            bi = bus_pos[int(gen["bus"])]
            m.addConstr(u[g, t] <= a_gen[g, t], name=f"u_av_{g}_{t}")
            if g not in blackstart:
                m.addConstr(u[g, t] <= y[bi, t], name=f"u_y_{g}_{t}")
            # blackstart online implies bus energized
            if g in blackstart:
                m.addConstr(y[bi, t] >= u[g, t], name=f"bs_y_{g}_{t}")

        for bi, bid in enumerate(bus_ids):
            m.addConstr(y[bi, t] <= a_bus[bi, t], name=f"y_av_{bi}_{t}")
            # y <= sum online gens at bus + sum prop into bus
            gen_src = gp.quicksum(
                u[g, t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            prop_in = gp.LinExpr()
            for ell, br in enumerate(branches):
                if int(br["fbus"]) == bid:
                    # prop from tbus -> fbus is dir 1
                    prop_in += prop[ell, t, 1]
                if int(br["tbus"]) == bid:
                    prop_in += prop[ell, t, 0]
            m.addConstr(y[bi, t] <= gen_src + prop_in, name=f"y_src_{bi}_{t}")
            # load only on energized buses
            m.addConstr(x[bi, t] <= y[bi, t], name=f"x_y_{bi}_{t}")

        # gen bounds
        for g, gen in enumerate(gens):
            pmax = float(gen["Pmax"]) * pmax_scale[g]
            m.addConstr(Pg[g, t] <= pmax * u[g, t], name=f"pgmax_{g}_{t}")
            # Pmin relaxed to 0 in restoration

        # branch flow indicators
        for ell, br in enumerate(branches):
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            rate = thermal_rate_mw(br)
            if rate <= 0:
                rate = 1e4 * base  # loose

            if is_zero_x(br):
                _, phi = branch_susceptance(br)
                m.addGenConstrIndicator(
                    z[ell, t],
                    True,
                    theta[i, t] - theta[j, t] == phi,
                    name=f"ind_th_{ell}_{t}",
                )
                m.addGenConstrIndicator(
                    z[ell, t], False, f[ell, t] == 0.0, name=f"ind_f0_{ell}_{t}"
                )
            else:
                bsus, phi = branch_susceptance(br)
                m.addGenConstrIndicator(
                    z[ell, t],
                    True,
                    f[ell, t] - base * bsus * (theta[i, t] - theta[j, t] - phi) == 0.0,
                    name=f"ind_phys_{ell}_{t}",
                )
                m.addGenConstrIndicator(
                    z[ell, t], False, f[ell, t] == 0.0, name=f"ind_f0_{ell}_{t}"
                )

            m.addConstr(f[ell, t] <= rate * z[ell, t], name=f"fmax_{ell}_{t}")
            m.addConstr(f[ell, t] >= -rate * z[ell, t], name=f"fmin_{ell}_{t}")

        # power balance
        for bi, bid in enumerate(bus_ids):
            Pd = float(buses[bi]["Pd"])
            gen_sum = gp.quicksum(
                Pg[g, t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            out_f = gp.quicksum(
                f[ell, t] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
            )
            in_f = gp.quicksum(
                f[ell, t] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
            )
            m.addConstr(
                gen_sum - Pd * x[bi, t] - out_f + in_f == 0.0, name=f"bal_{bid}_{t}"
            )

    # objective: max weighted served energy-periods
    obj = gp.quicksum(
        time_w[t] * w_bus[bi] * float(buses[bi]["Pd"]) * x[bi, t]
        for t in range(T)
        for bi in range(nB)
        if float(buses[bi]["Pd"]) > 0
    )
    m.setObjective(obj, GRB.MAXIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    # extract
    y_val = [[0.0] * T for _ in range(nB)]
    z_val = [[0.0] * T for _ in range(nL)]
    u_val = [[0.0] * T for _ in range(nG)]
    Pg_MW = [[0.0] * T for _ in range(nG)]
    flow_MW = [[0.0] * T for _ in range(nL)]
    theta_deg = [[0.0] * T for _ in range(nB)]
    load_frac = [[0.0] * T for _ in range(nB)]
    a_br_v = [[0.0] * T for _ in range(nL)]
    a_gen_v = [[0.0] * T for _ in range(nG)]
    obj_val = None
    mip_gap = None
    obj_bound = None

    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        obj_bound = float(m.ObjBound)
        try:
            mip_gap = float(m.MIPGap)
        except Exception:
            mip_gap = 0.0
        for t in range(T):
            for bi in range(nB):
                y_val[bi][t] = float(y[bi, t].X)
                theta_deg[bi][t] = math.degrees(float(theta[bi, t].X))
                load_frac[bi][t] = float(x[bi, t].X)
            for ell in range(nL):
                z_val[ell][t] = float(z[ell, t].X)
                flow_MW[ell][t] = float(f[ell, t].X)
                a_br_v[ell][t] = float(a_br[ell, t].X)
            for g in range(nG):
                u_val[g][t] = float(u[g, t].X)
                Pg_MW[g][t] = float(Pg[g, t].X)
                a_gen_v[g][t] = float(a_gen[g, t].X)

    served_by_t = []
    for t in range(T):
        s = sum(float(buses[bi]["Pd"]) * load_frac[bi][t] for bi in range(nB))
        served_by_t.append(s)
    total_pd = sum(float(b["Pd"]) for b in buses)
    residual = _validate(
        network,
        config,
        T,
        y_val,
        z_val,
        u_val,
        Pg_MW,
        flow_MW,
        theta_deg,
        load_frac,
        a_br_v,
        a_gen_v,
        pmax_scale,
        blackstart,
    )

    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap if mip_gap is not None else 0.0,
        "runtime": runtime,
        "horizon_T": T,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "load_frac": load_frac,
        "y_bus": y_val,
        "z_branch": z_val,
        "u_gen": u_val,
        "a_branch": a_br_v,
        "a_gen": a_gen_v,
        "served_MW_by_t": served_by_t,
        "served_MW_final": served_by_t[-1] if served_by_t else 0.0,
        "total_demand_MW": total_pd,
        "unserved_MW_final": total_pd - (served_by_t[-1] if served_by_t else 0.0),
        "damaged_branches": sorted(dmg_br),
        "damaged_gens": sorted(dmg_gen),
        "damaged_buses": sorted(dmg_bus),
        "blackstart_gens": sorted(blackstart),
        "time_weights": time_w,
        "ref_bus": ref_bus,
        "baseMVA": base,
        **residual,
    }


def _validate(
    network,
    config,
    T,
    y_val,
    z_val,
    u_val,
    Pg_MW,
    flow_MW,
    theta_deg,
    load_frac,
    a_br_v,
    a_gen_v,
    pmax_scale,
    blackstart,
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    tol = DEFAULT_TOLERANCES
    int_tol = tol["integrality"]

    max_bal = 0.0
    max_flow_eq = 0.0
    max_thermal = 0.0
    max_open_flow = 0.0
    max_gen = 0.0
    max_mono = 0.0
    max_logic = 0.0

    for t in range(T):
        # monotonic
        if t > 0:
            for bi in range(nB):
                max_mono = max(max_mono, max(0.0, y_val[bi][t - 1] - y_val[bi][t] - int_tol))
            for ell in range(nL):
                max_mono = max(max_mono, max(0.0, z_val[ell][t - 1] - z_val[ell][t] - int_tol))
            for g in range(nG):
                max_mono = max(max_mono, max(0.0, u_val[g][t - 1] - u_val[g][t] - int_tol))

        for bi, bid in enumerate(bus_ids):
            gen_sum = sum(
                Pg_MW[g][t] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            out_f = sum(
                flow_MW[ell][t]
                for ell, br in enumerate(branches)
                if int(br["fbus"]) == bid
            )
            in_f = sum(
                flow_MW[ell][t]
                for ell, br in enumerate(branches)
                if int(br["tbus"]) == bid
            )
            served = float(buses[bi]["Pd"]) * load_frac[bi][t]
            max_bal = max(max_bal, abs(gen_sum - served - out_f + in_f))
            # load only if energized
            max_logic = max(
                max_logic, max(0.0, load_frac[bi][t] - y_val[bi][t] - int_tol)
            )

        for ell, br in enumerate(branches):
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            zv = z_val[ell][t]
            if zv < 0.5:
                max_open_flow = max(max_open_flow, abs(flow_MW[ell][t]))
            else:
                th_i = math.radians(theta_deg[i][t])
                th_j = math.radians(theta_deg[j][t])
                if is_zero_x(br):
                    _, phi = branch_susceptance(br)
                    max_flow_eq = max(max_flow_eq, abs(th_i - th_j - phi) * base)
                else:
                    bsus, phi = branch_susceptance(br)
                    exp = base * bsus * (th_i - th_j - phi)
                    max_flow_eq = max(max_flow_eq, abs(flow_MW[ell][t] - exp))
                rate = thermal_rate_mw(br)
                if rate > 0:
                    max_thermal = max(
                        max_thermal, max(0.0, abs(flow_MW[ell][t]) - rate)
                    )
            # z only if ends energized and available
            max_logic = max(
                max_logic,
                max(0.0, zv - y_val[i][t] - int_tol),
                max(0.0, zv - y_val[j][t] - int_tol),
                max(0.0, zv - a_br_v[ell][t] - int_tol),
            )

        for g, gen in enumerate(gens):
            bi = bus_pos[int(gen["bus"])]
            pmax = float(gen["Pmax"]) * pmax_scale[g]
            max_gen = max(
                max_gen,
                max(0.0, -Pg_MW[g][t]),
                max(0.0, Pg_MW[g][t] - pmax * max(u_val[g][t], 0) - 1e-6),
            )
            max_logic = max(
                max_logic,
                max(0.0, u_val[g][t] - a_gen_v[g][t] - int_tol),
            )
            if g not in blackstart:
                max_logic = max(
                    max_logic, max(0.0, u_val[g][t] - y_val[bi][t] - int_tol)
                )

    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
        and max_open_flow <= tol["power_balance_mw"]
        and max_mono <= 1e-5
        and max_logic <= 1e-5
    )
    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "max_open_line_flow_MW": max_open_flow,
        "max_monotonicity_violation": max_mono,
        "max_logic_violation": max_logic,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    tier = str(config.get("solve_tier", "full"))
    if tier == "skip":
        result = {
            "schema_version": 1,
            "case": config.get("case", case_dir.name),
            "solver": "python-gurobi",
            "problem": "restore",
            "base_problem": "power_restoration",
            "restore": {
                "status": "SKIPPED",
                "obj": None,
                "validation_passed": True,
                "note": "solve_tier=skip",
            },
            "validation": {"passed": True},
        }
        write_result(case_dir, "python_result.json", result)
        return result

    sol = solve_restore(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "restore",
        "base_problem": "power_restoration",
        "restore": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result
