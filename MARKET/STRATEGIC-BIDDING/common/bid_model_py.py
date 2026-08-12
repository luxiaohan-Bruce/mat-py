"""Strategic bidding via discrete offer-ladder enumeration (PLAM B22).

Upper level: strategic firm chooses one ladder level to max profit
  profit = sum_{g in firm} LMP_bus(g) * Pg_g  -  true_cost_g(Pg_g)

Lower level: welfare-max / offer-cost-min market clearing LP
  min  sum_g offer_g * Pg_g  -  sum_i utility_i * d_i
  s.t. power balance, DC flow (or copperplate), thermal, gen/demand bounds

v1 dual-match method: enumerate bid ladder levels; solve lower LP each time;
pick max profit. Same algorithm in MATLAB (bid_model_mat.m).

Optional withhold mode: ladder is capacity fraction of Pmax; offer = true MC.

Big-M note (for future single-level KKT/MPEC): primal bounds
  0 <= Pg <= Pmax, 0 <= d <= Pd, |f| <= rate, |theta| <= pi
imply dual big-M from those bounds; this pack uses enumeration so no M needed.
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
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _topology(network: dict, config: dict) -> str:
    t = config.get("topology") or network.get("topology") or "dc"
    return str(t).lower()


def _demand_utility(buses: list[dict], config: dict) -> list[float]:
    """Synthetic utility $/MWh for elastic demand at each bus (default VOLL-like)."""
    du = config.get("demand_utility") or {}
    default_u = float(du.get("utility_per_mwh", 100.0))
    per_bus = du.get("per_bus") or {}
    out = []
    for b in buses:
        bid = int(b["bus_i"])
        out.append(float(per_bus.get(str(bid), per_bus.get(bid, default_u))))
    return out


def _true_cost(gen: dict, p: float) -> float:
    return float(gen.get("c2", 0.0)) * p * p + float(gen.get("c1", 0.0)) * p + float(
        gen.get("c0", 0.0)
    )


def _competitive_offer(gen: dict) -> float:
    """Linear competitive offer = true linear MC (c1)."""
    return float(gen.get("c1", 0.0))


def solve_market_clearing(
    network: dict,
    config: dict,
    offers: list[float],
    pmax_eff: list[float],
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    """Lower-level LP: min offer-cost - demand-utility subject to DC/copperplate."""
    base = float(network.get("baseMVA", 100.0))
    buses = network["buses"]
    gens = network["gens"]
    branches = network.get("branches") or []
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    topo = _topology(network, config)
    utils = _demand_utility(buses, config)
    params = solver_params_from_config(config)

    m = gp.Model("market_clearing")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.Method = 1  # dual simplex — stable duals
    m.Params.NumericFocus = 1

    Pg = m.addVars(nG, lb=0.0, name="Pg")
    d = m.addVars(nB, lb=0.0, name="d")

    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            Pg[g].UB = 0.0
        else:
            Pg[g].UB = max(0.0, float(pmax_eff[g]))

    for bi, bus in enumerate(buses):
        d[bi].UB = max(0.0, float(bus.get("Pd", 0.0)))

    # min sum offer*Pg - sum u*d
    obj = gp.quicksum(float(offers[g]) * Pg[g] for g in range(nG))
    obj -= gp.quicksum(utils[bi] * d[bi] for bi in range(nB))
    m.setObjective(obj, GRB.MINIMIZE)

    bal = {}
    if topo == "copperplate":
        bal[0] = m.addConstr(
            gp.quicksum(Pg[g] for g in range(nG)) - gp.quicksum(d[bi] for bi in range(nB))
            == 0.0,
            name="bal_sys",
        )
        theta = None
        f = None
    else:
        theta = m.addVars(nB, lb=-math.pi, ub=math.pi, name="theta")
        f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f")
        m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

        for ell, br in enumerate(branches):
            if int(br.get("status", 1)) == 0:
                m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
                continue
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            if is_zero_x(br):
                _, phi = branch_susceptance(br)
                m.addConstr(theta[i] - theta[j] == phi, name=f"th_eq_{ell}")
            else:
                bsus, phi = branch_susceptance(br)
                m.addConstr(
                    f[ell] == base * bsus * (theta[i] - theta[j] - phi),
                    name=f"phys_{ell}",
                )
            rate = thermal_rate_mw(br)
            if rate > 0:
                m.addConstr(f[ell] <= rate, name=f"fmax_{ell}")
                m.addConstr(f[ell] >= -rate, name=f"fmin_{ell}")

        for bi, bid in enumerate(bus_ids):
            gen_sum = gp.quicksum(
                Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
            )
            out_f = gp.quicksum(
                f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
            )
            in_f = gp.quicksum(
                f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
            )
            bal[bi] = m.addConstr(
                gen_sum - d[bi] - out_f + in_f == 0.0, name=f"bal_{bid}"
            )

    m.optimize()
    status = _status_name(m)
    if m.SolCount == 0:
        return {
            "status": status,
            "welfare_obj": None,
            "Pg_MW": [0.0] * nG,
            "d_MW": [0.0] * nB,
            "LMP": [0.0] * nB,
            "theta_deg": [0.0] * nB,
            "flow_MW": [0.0] * nL,
            "offers": list(offers),
            "pmax_eff": list(pmax_eff),
        }

    Pg_MW = [float(Pg[g].X) for g in range(nG)]
    d_MW = [float(d[bi].X) for bi in range(nB)]
    if topo == "copperplate":
        lmp0 = float(bal[0].Pi)
        LMP = [lmp0] * nB
        theta_deg = [0.0] * nB
        flow_MW = [0.0] * nL
    else:
        LMP = [float(bal[bi].Pi) for bi in range(nB)]
        theta_deg = [math.degrees(float(theta[bi].X)) for bi in range(nB)]  # type: ignore[index]
        flow_MW = [float(f[ell].X) for ell in range(nL)]  # type: ignore[index]

    return {
        "status": status,
        "welfare_obj": float(m.ObjVal),
        "Pg_MW": Pg_MW,
        "d_MW": d_MW,
        "LMP": LMP,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "offers": [float(x) for x in offers],
        "pmax_eff": [float(x) for x in pmax_eff],
    }


def firm_profit(network: dict, firm_gens: list[int], clearing: dict) -> dict[str, float]:
    gens = network["gens"]
    buses = network["buses"]
    bus_ids, bus_pos, _ = bus_maps(network)
    Pg = clearing["Pg_MW"]
    LMP = clearing["LMP"]
    revenue = 0.0
    cost = 0.0
    firm_mw = 0.0
    for g in firm_gens:
        gen = gens[g]
        p = float(Pg[g])
        firm_mw += p
        bi = bus_pos[int(gen["bus"])]
        # copperplate: LMP length may be 1 or nB (we broadcast)
        lmp = float(LMP[bi] if bi < len(LMP) else LMP[0])
        revenue += lmp * p
        cost += _true_cost(gen, p)
    return {
        "profit": revenue - cost,
        "revenue": revenue,
        "true_cost": cost,
        "firm_MW": firm_mw,
    }


def validate_clearing(network: dict, config: dict, clearing: dict) -> dict[str, Any]:
    buses = network["buses"]
    gens = network["gens"]
    branches = network.get("branches") or []
    bus_ids, bus_pos, _ = bus_maps(network)
    base = float(network.get("baseMVA", 100.0))
    topo = _topology(network, config)
    Pg = clearing["Pg_MW"]
    d = clearing["d_MW"]
    fl = clearing.get("flow_MW") or [0.0] * len(branches)
    th = [math.radians(v) for v in (clearing.get("theta_deg") or [0.0] * len(buses))]
    pmax_eff = clearing.get("pmax_eff") or [
        float(g["Pmax"]) if int(g.get("status", 1)) == 1 else 0.0 for g in gens
    ]

    max_bal = 0.0
    if topo == "copperplate":
        max_bal = abs(sum(Pg) - sum(d))
    else:
        for bi, bid in enumerate(bus_ids):
            gs = sum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
            of = sum(fl[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
            inf = sum(fl[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
            max_bal = max(max_bal, abs(gs - d[bi] - of + inf))

    max_flow_eq = 0.0
    max_thermal = 0.0
    if topo != "copperplate":
        for ell, br in enumerate(branches):
            if int(br.get("status", 1)) == 0:
                max_flow_eq = max(max_flow_eq, abs(fl[ell]))
                continue
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            if is_zero_x(br):
                _, phi = branch_susceptance(br)
                max_flow_eq = max(max_flow_eq, abs(th[i] - th[j] - phi) * base)
            else:
                bsus, phi = branch_susceptance(br)
                exp = base * bsus * (th[i] - th[j] - phi)
                max_flow_eq = max(max_flow_eq, abs(fl[ell] - exp))
            rate = thermal_rate_mw(br)
            if rate > 0:
                max_thermal = max(max_thermal, max(0.0, abs(fl[ell]) - rate - 1e-9))

    max_gen = 0.0
    for g, gen in enumerate(gens):
        p = Pg[g]
        hi = float(pmax_eff[g])
        if p < -1e-9:
            max_gen = max(max_gen, -p)
        if p > hi + 1e-6:
            max_gen = max(max_gen, p - hi)

    max_dem = 0.0
    for bi, bus in enumerate(buses):
        pd = float(bus.get("Pd", 0.0))
        if d[bi] < -1e-9:
            max_dem = max(max_dem, -d[bi])
        if d[bi] > pd + 1e-6:
            max_dem = max(max_dem, d[bi] - pd)

    tol = DEFAULT_TOLERANCES
    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
        and max_dem <= tol["generator_bound_mw"]
    )
    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_generator_bound_MW": max_gen,
        "max_demand_bound_MW": max_dem,
        "validation_passed": passed,
    }


def solve_strategic_bid(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    """Enumerate discrete offer ladder; return best-profit firm strategy + clearing."""
    gens = network["gens"]
    nG = len(gens)
    strat = config.get("strategic") or {}
    firm_gens = [int(g) for g in strat.get("firm_gens", [0])]
    mode = str(strat.get("mode", "price")).lower()
    ladder = [float(x) for x in strat.get("bid_ladder", [20.0, 30.0, 40.0, 50.0])]
    method = str(config.get("method", "enumeration")).lower()

    t0 = time.time()
    best: dict[str, Any] | None = None
    ladder_trace: list[dict[str, Any]] = []

    for k, level in enumerate(ladder):
        offers = [_competitive_offer(g) for g in gens]
        pmax_eff = [
            float(g["Pmax"]) if int(g.get("status", 1)) == 1 else 0.0 for g in gens
        ]
        if mode == "withhold":
            # level is capacity fraction in (0,1]
            frac = max(0.0, min(1.0, level))
            for g in firm_gens:
                if int(gens[g].get("status", 1)) == 1:
                    pmax_eff[g] = float(gens[g]["Pmax"]) * frac
                    offers[g] = _competitive_offer(gens[g])
        else:
            # price ladder: absolute $/MWh offer for firm gens
            for g in firm_gens:
                if int(gens[g].get("status", 1)) == 1:
                    offers[g] = level

        clearing = solve_market_clearing(
            network, config, offers, pmax_eff, quiet=quiet
        )
        if clearing["status"] not in ("OPTIMAL", "SUBOPTIMAL") or clearing["welfare_obj"] is None:
            ladder_trace.append(
                {
                    "level_index": k,
                    "level": level,
                    "status": clearing["status"],
                    "profit": None,
                }
            )
            continue
        prof = firm_profit(network, firm_gens, clearing)
        entry = {
            "level_index": k,
            "level": level,
            "status": clearing["status"],
            "profit": prof["profit"],
            "revenue": prof["revenue"],
            "true_cost": prof["true_cost"],
            "firm_MW": prof["firm_MW"],
            "welfare_obj": clearing["welfare_obj"],
            "mean_LMP": sum(clearing["LMP"]) / max(1, len(clearing["LMP"])),
        }
        ladder_trace.append(entry)
        if best is None or prof["profit"] > best["profit"] + 1e-9:
            best = {
                **entry,
                "clearing": clearing,
                "offers": offers,
                "pmax_eff": pmax_eff,
            }

    runtime = time.time() - t0
    if best is None:
        return {
            "status": "INFEASIBLE",
            "obj": None,
            "profit": None,
            "method": method,
            "mode": mode,
            "bid_ladder": ladder,
            "firm_gens": firm_gens,
            "best_level_index": None,
            "best_level": None,
            "runtime": runtime,
            "ladder_trace": ladder_trace,
            "validation_passed": False,
            "max_power_balance_MW": float("inf"),
            "max_flow_equation_MW": float("inf"),
            "max_thermal_violation_MW": float("inf"),
            "max_generator_bound_MW": float("inf"),
            "max_demand_bound_MW": float("inf"),
        }

    clearing = best["clearing"]
    residual = validate_clearing(network, config, clearing)
    # Recompute profit from residual solution for acceptance
    prof = firm_profit(network, firm_gens, clearing)

    return {
        "status": "OPTIMAL",
        "obj": prof["profit"],  # primary objective = firm profit
        "obj_bound": prof["profit"],
        "mip_gap": 0.0,
        "profit": prof["profit"],
        "revenue": prof["revenue"],
        "true_cost": prof["true_cost"],
        "firm_MW": prof["firm_MW"],
        "method": method,
        "mode": mode,
        "bid_ladder": ladder,
        "firm_gens": firm_gens,
        "best_level_index": best["level_index"],
        "best_level": best["level"],
        "offers": best["offers"],
        "pmax_eff": best["pmax_eff"],
        "Pg_MW": clearing["Pg_MW"],
        "d_MW": clearing["d_MW"],
        "LMP": clearing["LMP"],
        "theta_deg": clearing["theta_deg"],
        "flow_MW": clearing["flow_MW"],
        "welfare_obj": clearing["welfare_obj"],
        "clearing_status": clearing["status"],
        "ladder_trace": ladder_trace,
        "n_ladder": len(ladder),
        "runtime": runtime,
        "topology": _topology(network, config),
        **residual,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_strategic_bid(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "bid",
        "base_problem": config.get("base_problem", "strategic_bidding"),
        "bid": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case01_toy3_copperplate_price"
    )
    r = run_case(d, quiet=True)
    e = r["bid"]
    print(
        f"[{r['case']}] status={e['status']} profit={e.get('profit')} "
        f"level={e.get('best_level')} bal={e.get('max_power_balance_MW')}"
    )
