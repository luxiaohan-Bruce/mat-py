"""Generator Maintenance Scheduling + multi-period copperplate ED (gurobipy).

MILP:
  binary s[k,t]  : task k starts at period t (exactly once in window)
  binary m[k,t]  : task k is on maintenance at period t (D consecutive after start)
  continuous Pg[g,t], load_shed[t]

  sum_t s[k,t] = 1  (window-restricted)
  m[k,t] = sum_{tau in [t-D+1, t]} s[k,tau]
  sum_k m[k,t] <= crew_limit
  Pg[g,t] <= Pmax_g * (1 - sum_{k on g} m[k,t])
  sum_g Pg[g,t] + shed[t] = demand[t]
  min sum c1*Pg + c0*available + maint_cost*s + penalty*shed
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
from tolerances import solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def solve_maint(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    gens = network["generators"]
    tasks = network["maintenance_tasks"]
    demand = [float(x) for x in network["demand"]]
    T = int(network["time_periods"])
    assert len(demand) == T
    nG = len(gens)
    nK = len(tasks)
    crew_limit = int(network.get("crew_limit", 2))
    shed_pen = float(network.get("load_shed_penalty", 1.0e5))
    period_h = float(network.get("period_hours", 1.0))
    params = solver_params_from_config(config)

    # map gen name / index -> list of task indices
    tasks_on_gen: list[list[int]] = [[] for _ in range(nG)]
    for k, task in enumerate(tasks):
        gi = int(task["gen_index"])
        tasks_on_gen[gi].append(k)

    m = gp.Model("maint_ed")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    # start binaries only on feasible start slots
    s: dict[tuple[int, int], gp.Var] = {}
    for k, task in enumerate(tasks):
        D = int(task["duration"])
        ws = int(task["window_start"])
        we = int(task["window_end"])  # inclusive last start
        we = min(we, T - D)
        for t in range(T):
            if ws <= t <= we and t + D <= T:
                s[k, t] = m.addVar(vtype=GRB.BINARY, name=f"s[{k},{t}]")

    m_bin = m.addVars(nK, T, vtype=GRB.BINARY, name="m")
    Pg = m.addVars(nG, T, lb=0.0, name="Pg")
    shed = m.addVars(T, lb=0.0, name="shed")

    # unique start
    for k, task in enumerate(tasks):
        starts = [s[k, t] for t in range(T) if (k, t) in s]
        if not starts:
            raise ValueError(f"task {k} has empty start window")
        m.addConstr(gp.quicksum(starts) == 1, name=f"start_once[{k}]")

    # consecutive maintenance coverage
    for k, task in enumerate(tasks):
        D = int(task["duration"])
        for t in range(T):
            covering = [
                s[k, tau]
                for tau in range(max(0, t - D + 1), t + 1)
                if (k, tau) in s
            ]
            if covering:
                m.addConstr(m_bin[k, t] == gp.quicksum(covering), name=f"cover[{k},{t}]")
            else:
                m.addConstr(m_bin[k, t] == 0, name=f"cover0[{k},{t}]")

    # crew limit
    for t in range(T):
        m.addConstr(
            gp.quicksum(m_bin[k, t] for k in range(nK)) <= crew_limit,
            name=f"crew[{t}]",
        )

    # generation bounds with maintenance outage
    for g, gen in enumerate(gens):
        pmax = float(gen["Pmax"])
        pmin = float(gen.get("Pmin", 0.0))
        status = int(gen.get("status", 1))
        for t in range(T):
            if status == 0 or pmax <= 0:
                Pg[g, t].UB = 0.0
                continue
            if tasks_on_gen[g]:
                # Pg <= pmax * (1 - sum m on this gen); at most one task per gen in our data
                out = gp.quicksum(m_bin[k, t] for k in tasks_on_gen[g])
                m.addConstr(Pg[g, t] <= pmax * (1.0 - out), name=f"pmax_m[{g},{t}]")
                # when online, allow down to 0 (copperplate ED, no UC)
                # optional soft pmin when online: skip for tractability
            else:
                Pg[g, t].UB = pmax
            # keep pmin unused (ED relax)

    # demand balance
    for t in range(T):
        m.addConstr(
            gp.quicksum(Pg[g, t] for g in range(nG)) + shed[t] == demand[t],
            name=f"bal[{t}]",
        )

    # objective: production + optional maint cost + shed
    obj = gp.LinExpr()
    for g, gen in enumerate(gens):
        c1 = float(gen.get("c1", 0.0))
        c0 = float(gen.get("c0", 0.0))
        c2 = float(gen.get("c2", 0.0))
        for t in range(T):
            obj += period_h * c1 * Pg[g, t]
            if abs(c2) > 1e-14:
                obj += period_h * c2 * Pg[g, t] * Pg[g, t]
            # no-load only when not on maintenance and status=1: approximate with c0 * (1-m)
            # skip c0 for parity simplicity unless c0 set and unit has no tasks
            if abs(c0) > 1e-14:
                if tasks_on_gen[g]:
                    out = gp.quicksum(m_bin[k, t] for k in tasks_on_gen[g])
                    obj += period_h * c0 * (1.0 - out)
                else:
                    obj += period_h * c0
    for k, task in enumerate(tasks):
        mc = float(task.get("maint_cost", 0.0))
        if abs(mc) > 1e-14:
            for t in range(T):
                if (k, t) in s:
                    obj += mc * s[k, t]
    for t in range(T):
        obj += period_h * shed_pen * shed[t]
    m.setObjective(obj, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    Pg_out = [[0.0] * T for _ in range(nG)]
    m_out = [[0.0] * T for _ in range(nK)]
    s_out = [[0.0] * T for _ in range(nK)]
    shed_out = [0.0] * T
    start_period = [-1] * nK
    obj_val = None
    obj_bound = None
    mip_gap = 0.0

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
            for t in range(T):
                Pg_out[g][t] = float(Pg[g, t].X)
        for k in range(nK):
            for t in range(T):
                m_out[k][t] = float(m_bin[k, t].X)
                if (k, t) in s:
                    sv = float(s[k, t].X)
                    s_out[k][t] = sv
                    if sv > 0.5:
                        start_period[k] = t
        for t in range(T):
            shed_out[t] = float(shed[t].X)

    residual = validate_maint_solution(
        network, Pg_out, m_out, s_out, shed_out, start_period, obj_val
    )
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "start_period": start_period,
        "m": m_out,
        "s": s_out,
        "Pg_MW": Pg_out,
        "shed_MW": shed_out,
        "crew_limit": crew_limit,
        "time_periods": T,
        **residual,
    }


def validate_maint_solution(
    network: dict,
    Pg: list[list[float]],
    m_state: list[list[float]],
    s_state: list[list[float]],
    shed: list[float],
    start_period: list[int],
    obj_val: float | None,
) -> dict[str, Any]:
    gens = network["generators"]
    tasks = network["maintenance_tasks"]
    demand = [float(x) for x in network["demand"]]
    T = int(network["time_periods"])
    nG = len(gens)
    nK = len(tasks)
    crew_limit = int(network.get("crew_limit", 2))
    tol_int = 1e-6
    tol_mw = 1e-4

    max_start_once = 0.0
    max_duration = 0.0
    max_crew = 0.0
    max_bal = 0.0
    max_pmax = 0.0
    max_outage = 0.0

    for k, task in enumerate(tasks):
        D = int(task["duration"])
        ws = int(task["window_start"])
        we = min(int(task["window_end"]), T - D)
        start_sum = sum(s_state[k][t] for t in range(T) if ws <= t <= we and t + D <= T)
        max_start_once = max(max_start_once, abs(start_sum - 1.0))
        # outside window starts should be ~0
        for t in range(T):
            if not (ws <= t <= we and t + D <= T):
                max_start_once = max(max_start_once, abs(s_state[k][t]))
        # consecutive: m[t] should equal sum of starts covering t
        for t in range(T):
            cover = sum(
                s_state[k][tau]
                for tau in range(max(0, t - D + 1), t + 1)
                if ws <= tau <= we and tau + D <= T
            )
            max_duration = max(max_duration, abs(m_state[k][t] - cover))
        # total on-maint periods ≈ D
        m_sum = sum(m_state[k][t] for t in range(T))
        max_duration = max(max_duration, abs(m_sum - D))

    for t in range(T):
        crew = sum(m_state[k][t] for k in range(nK))
        max_crew = max(max_crew, max(0.0, crew - crew_limit))
        gen_sum = sum(Pg[g][t] for g in range(nG)) + shed[t]
        max_bal = max(max_bal, abs(gen_sum - demand[t]))

    for g, gen in enumerate(gens):
        pmax = float(gen["Pmax"])
        status = int(gen.get("status", 1))
        k_list = [k for k, task in enumerate(tasks) if int(task["gen_index"]) == g]
        for t in range(T):
            if status == 0:
                max_pmax = max(max_pmax, abs(Pg[g][t]))
                continue
            out = sum(m_state[k][t] for k in k_list)
            if out > 0.5:
                max_outage = max(max_outage, abs(Pg[g][t]))
            max_pmax = max(max_pmax, max(0.0, Pg[g][t] - pmax * (1.0 - out) - 1e-9))

    validation_passed = (
        max_start_once <= tol_int
        and max_duration <= tol_int
        and max_crew <= tol_int
        and max_bal <= tol_mw
        and max_pmax <= tol_mw
        and max_outage <= tol_mw
        and obj_val is not None
    )
    return {
        "max_start_once_violation": max_start_once,
        "max_duration_violation": max_duration,
        "max_crew_violation": max_crew,
        "max_power_balance_MW": max_bal,
        "max_pmax_violation_MW": max_pmax,
        "max_outage_generation_MW": max_outage,
        "total_shed_MW": sum(shed),
        "validation_passed": validation_passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_maint(network, config, quiet=quiet)
    case_name = config.get("case", case_dir.name)
    payload = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobipy",
        "problem": "maintenance_scheduling",
        "base_problem": config.get("base_problem", "maintenance_scheduling"),
        "maint": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", payload)
    return payload


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    r = run_case(args.case_dir, quiet=not args.verbose)
    e = r["maint"]
    print(
        f"[{r['case']}] {e['status']} obj={e['obj']} "
        f"starts={e['start_period']} valid={e['validation_passed']} t={e['runtime']:.2f}s"
    )
