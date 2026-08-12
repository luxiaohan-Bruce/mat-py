"""Copperplate multi-period energy market clearing (LP welfare max).

max  sum_t  utility_t * served_t  -  sum_{b,t}  price_b * accept_{b,t}
s.t. sum_b accept_{b,t} = served_t          (power balance, each period)
     0 <= accept_{b,t} <= qty_{b,t}
     0 <= served_t <= Pd_t

Truthful supply blocks from PGLib-UC piecewise production cost;
renewables offer at 0 $/MWh with period-varying qty.
Demand utility = VOLL * served (synthetic VOLL default 10000 $/MWh).

LP dual of balance is the energy price LMP_t.
If a future MILP with UC binaries is used, fix binaries and re-solve this LP
for economically meaningful prices (documented in package README).
"""

from __future__ import annotations

import json
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


def _block_qty(block: dict, t: int) -> float:
    if "period_qty_mw" in block and block["period_qty_mw"] is not None:
        return float(block["period_qty_mw"][t])
    return float(block.get("qty_mw", 0.0))


def solve_market(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    T = int(network["time_periods"])
    demand = [float(x) for x in network["demand_mw"]]
    assert len(demand) == T
    blocks = network["supply_blocks"]
    nB = len(blocks)
    voll = float(network.get("voll_usd_per_mwh", 10000.0))
    params = solver_params_from_config(config)

    m = gp.Model("market_clearing")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]
    m.Params.Method = 2  # barrier
    m.Params.Crossover = 1  # need duals (LMP)

    # accept[b,t], served[t]
    accept = m.addVars(nB, T, lb=0.0, name="accept")
    served = m.addVars(T, lb=0.0, name="served")

    for t in range(T):
        served[t].UB = demand[t]
        for b in range(nB):
            accept[b, t].UB = _block_qty(blocks[b], t)

    bal = []
    for t in range(T):
        c = m.addConstr(
            gp.quicksum(accept[b, t] for b in range(nB)) == served[t],
            name=f"bal_{t}",
        )
        bal.append(c)

    welfare = gp.quicksum(voll * served[t] for t in range(T)) - gp.quicksum(
        float(blocks[b]["price_usd_per_mwh"]) * accept[b, t]
        for b in range(nB)
        for t in range(T)
    )
    m.setObjective(welfare, GRB.MAXIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    accept_mw: list[list[float]] = [[0.0] * T for _ in range(nB)]
    served_mw = [0.0] * T
    lmp = [0.0] * T
    obj_val = None
    gen_cost = None
    demand_utility = None
    if m.SolCount > 0:
        obj_val = float(m.ObjVal)
        for t in range(T):
            served_mw[t] = float(served[t].X)
            try:
                # Gurobi Pi for maximization: negate so LMP ≈ marginal offer cost ≥ 0
                lmp[t] = -float(bal[t].Pi)
            except Exception:
                lmp[t] = 0.0
            for b in range(nB):
                accept_mw[b][t] = float(accept[b, t].X)
        demand_utility = sum(voll * served_mw[t] for t in range(T))
        gen_cost = sum(
            float(blocks[b]["price_usd_per_mwh"]) * accept_mw[b][t]
            for b in range(nB)
            for t in range(T)
        )

    residual = validate_market_solution(
        network, accept_mw, served_mw, obj_val, lmp=lmp
    )
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_val,
        "mip_gap": 0.0,
        "runtime": runtime,
        "welfare": obj_val,
        "demand_utility": demand_utility,
        "generation_cost": gen_cost,
        "served_mw": served_mw,
        "accept_mw": accept_mw,
        "lmp_usd_per_mwh": lmp,
        "voll_usd_per_mwh": voll,
        "T": T,
        "n_blocks": nB,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "model_type": "lp",
        **residual,
    }


def validate_market_solution(
    network: dict,
    accept_mw: list[list[float]],
    served_mw: list[float],
    obj: float | None,
    *,
    lmp: list[float] | None = None,
) -> dict[str, Any]:
    T = int(network["time_periods"])
    demand = [float(x) for x in network["demand_mw"]]
    blocks = network["supply_blocks"]
    nB = len(blocks)
    voll = float(network.get("voll_usd_per_mwh", 10000.0))
    tol = DEFAULT_TOLERANCES

    if (
        len(served_mw) != T
        or len(accept_mw) != nB
        or any(len(row) != T for row in accept_mw)
    ):
        return {
            "max_power_balance_MW": float("inf"),
            "max_offer_bound_MW": float("inf"),
            "max_served_bound_MW": float("inf"),
            "welfare_recomputed": None,
            "validation_passed": False,
        }

    max_bal = 0.0
    max_offer = 0.0
    max_served = 0.0
    gen_cost = 0.0
    utility = 0.0
    for t in range(T):
        gen_sum = sum(accept_mw[b][t] for b in range(nB))
        max_bal = max(max_bal, abs(gen_sum - served_mw[t]))
        if served_mw[t] < -1e-9:
            max_served = max(max_served, -served_mw[t])
        if served_mw[t] > demand[t] + 1e-9:
            max_served = max(max_served, served_mw[t] - demand[t])
        utility += voll * served_mw[t]
        for b in range(nB):
            q = _block_qty(blocks[b], t)
            a = accept_mw[b][t]
            if a < -1e-9:
                max_offer = max(max_offer, -a)
            if a > q + 1e-9:
                max_offer = max(max_offer, a - q)
            gen_cost += float(blocks[b]["price_usd_per_mwh"]) * a

    welfare = utility - gen_cost
    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_offer <= tol["generator_bound_mw"]
        and max_served <= tol["generator_bound_mw"]
    )
    if obj is not None and abs(welfare - obj) > max(0.01, 1e-6 * max(1.0, abs(obj))):
        # welfare recompute mismatch is a hard residual for this LP
        passed = False

    return {
        "max_power_balance_MW": max_bal,
        "max_offer_bound_MW": max_offer,
        "max_served_bound_MW": max_served,
        "welfare_recomputed": welfare,
        "demand_utility_recomputed": utility,
        "generation_cost_recomputed": gen_cost,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_market(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "market_clearing",
        "base_problem": config.get("base_problem", "market_clearing"),
        "market": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case01_rts_gmlc_2020_01_27_market"
    )
    r = run_case(d, quiet=True)
    e = r["market"]
    print(
        f"[{r['case']}] status={e['status']} welfare={e['obj']} "
        f"bal={e['max_power_balance_MW']:.3e} valid={e['validation_passed']}"
    )
