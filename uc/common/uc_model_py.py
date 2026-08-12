"""PGLib-UC formulation implemented directly with gurobipy."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


def load_case(case_dir: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    case_dir = Path(case_dir)
    with (case_dir / "data" / "network.json").open(encoding="utf-8") as f:
        data = json.load(f)
    with (case_dir / "data" / "config.json").open(encoding="utf-8") as f:
        config = json.load(f)
    return data, config


def _status_name(status: int) -> str:
    names = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.INTERRUPTED: "INTERRUPTED",
    }
    return names.get(status, str(status))


def solve_uc(
    data: dict[str, Any], config: dict[str, Any], quiet: bool = True
) -> dict[str, Any]:
    """Solve the deterministic PGLib-UC MILP.

    Production cost is the convex piecewise-linear envelope of the supplied
    points. Startup categories follow the lag logic in the official PGLib-UC
    reference formulation.
    """

    thermal = list(data["thermal_generators"].items())
    renewable = list(data.get("renewable_generators", {}).items())
    T = int(data["time_periods"])
    G = range(len(thermal))
    TT = range(T)
    W = range(len(renewable))

    model = gp.Model(config.get("case", "pglib_uc"))
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.MIPGap = float(config.get("mip_gap", 0.01))
    model.Params.TimeLimit = float(config.get("time_limit", 120.0))
    model.Params.Seed = int(config.get("seed", 1))
    model.Params.Threads = int(config.get("threads", 1))

    u = model.addVars(G, TT, vtype=GRB.BINARY, name="u")
    start = model.addVars(G, TT, vtype=GRB.BINARY, name="start")
    stop = model.addVars(G, TT, vtype=GRB.BINARY, name="stop")
    p = model.addVars(G, TT, lb=0.0, name="p_above_min")
    reserve = model.addVars(G, TT, lb=0.0, name="reserve")

    renew = {}
    for w, (_, gen) in enumerate(renewable):
        for t in TT:
            renew[w, t] = model.addVar(
                lb=float(gen["power_output_minimum"][t]),
                ub=float(gen["power_output_maximum"][t]),
                name=f"renew[{w},{t}]",
            )

    startup_type = {}
    segment = {}
    objective = gp.LinExpr()

    for g, (_, gen) in enumerate(thermal):
        points = gen["piecewise_production"]
        pmin = float(gen["power_output_minimum"])
        if abs(float(points[0]["mw"]) - pmin) > 1e-6:
            raise ValueError(f"generator {thermal[g][0]}: first PWL point is not Pmin")
        base_cost = float(points[0]["cost"])
        starts = gen["startup"]
        for t in TT:
            objective += base_cost * u[g, t]
            for s, category in enumerate(starts):
                var = model.addVar(vtype=GRB.BINARY, name=f"startup_type[{g},{s},{t}]")
                startup_type[g, s, t] = var
                objective += float(category["cost"]) * var
            for s in range(len(points) - 1):
                left, right = points[s], points[s + 1]
                width = float(right["mw"]) - float(left["mw"])
                slope = (float(right["cost"]) - float(left["cost"])) / width
                var = model.addVar(lb=0.0, name=f"segment[{g},{s},{t}]")
                segment[g, s, t] = var
                objective += slope * var

    model.update()
    model.setObjective(objective, GRB.MINIMIZE)

    for t in TT:
        model.addConstr(
            gp.quicksum(
                p[g, t] + float(gen["power_output_minimum"]) * u[g, t]
                for g, (_, gen) in enumerate(thermal)
            )
            + gp.quicksum(renew[w, t] for w in W)
            == float(data["demand"][t]),
            name=f"demand[{t}]",
        )
        model.addConstr(
            gp.quicksum(reserve[g, t] for g in G) >= float(data["reserves"][t]),
            name=f"system_reserve[{t}]",
        )

    for g, (name, gen) in enumerate(thermal):
        pmin = float(gen["power_output_minimum"])
        pmax = float(gen["power_output_maximum"])
        headroom = pmax - pmin
        ramp_up = float(gen["ramp_up_limit"])
        ramp_down = float(gen["ramp_down_limit"])
        ramp_start = float(gen["ramp_startup_limit"])
        ramp_stop = float(gen["ramp_shutdown_limit"])
        min_up = min(int(gen["time_up_minimum"]), T)
        min_down = min(int(gen["time_down_minimum"]), T)
        u0 = int(gen["unit_on_t0"])
        p0_above = max(0.0, float(gen["power_output_t0"]) - pmin)
        starts = gen["startup"]
        points = gen["piecewise_production"]

        residual_up = max(0, int(gen["time_up_minimum"]) - int(gen["time_up_t0"]))
        residual_down = max(
            0, int(gen["time_down_minimum"]) - int(gen["time_down_t0"])
        )
        if u0:
            for t in range(min(T, residual_up)):
                model.addConstr(u[g, t] == 1, name=f"initial_up[{g},{t}]")
        else:
            for t in range(min(T, residual_down)):
                model.addConstr(u[g, t] == 0, name=f"initial_down[{g},{t}]")

        for t in TT:
            previous = u0 if t == 0 else u[g, t - 1]
            model.addConstr(
                u[g, t] - previous == start[g, t] - stop[g, t],
                name=f"logic[{g},{t}]",
            )
            model.addConstr(start[g, t] + stop[g, t] <= 1)
            if int(gen["must_run"]):
                model.addConstr(u[g, t] == 1)

            model.addConstr(
                gp.quicksum(start[g, tau] for tau in range(max(0, t - min_up + 1), t + 1))
                <= u[g, t],
                name=f"min_up[{g},{t}]",
            )
            model.addConstr(
                gp.quicksum(stop[g, tau] for tau in range(max(0, t - min_down + 1), t + 1))
                <= 1 - u[g, t],
                name=f"min_down[{g},{t}]",
            )

            model.addConstr(
                start[g, t]
                == gp.quicksum(startup_type[g, s, t] for s in range(len(starts))),
                name=f"startup_select[{g},{t}]",
            )

            model.addConstr(
                p[g, t] + reserve[g, t]
                <= headroom * u[g, t] - max(pmax - ramp_start, 0.0) * start[g, t],
                name=f"capacity_start[{g},{t}]",
            )
            if t < T - 1:
                model.addConstr(
                    p[g, t] + reserve[g, t]
                    <= headroom * u[g, t]
                    - max(pmax - ramp_stop, 0.0) * stop[g, t + 1],
                    name=f"capacity_stop[{g},{t}]",
                )

            if t == 0:
                model.addConstr(
                    p[g, t] + reserve[g, t] - u0 * p0_above <= ramp_up,
                    name=f"ramp_up_initial[{g}]",
                )
                model.addConstr(
                    u0 * p0_above - p[g, t] <= ramp_down,
                    name=f"ramp_down_initial[{g}]",
                )
                model.addConstr(
                    u0 * p0_above
                    <= u0 * headroom - max(pmax - ramp_stop, 0.0) * stop[g, 0],
                    name=f"shutdown_initial[{g}]",
                )
            else:
                model.addConstr(
                    p[g, t] + reserve[g, t] - p[g, t - 1] <= ramp_up,
                    name=f"ramp_up[{g},{t}]",
                )
                model.addConstr(
                    p[g, t - 1] - p[g, t] <= ramp_down,
                    name=f"ramp_down[{g},{t}]",
                )

            seg_vars = []
            for s in range(len(points) - 1):
                width = float(points[s + 1]["mw"]) - float(points[s]["mw"])
                var = segment[g, s, t]
                model.addConstr(var <= width * u[g, t])
                seg_vars.append(var)
            model.addConstr(p[g, t] == gp.quicksum(seg_vars), name=f"pwl_power[{g},{t}]")

        for s in range(len(starts) - 1):
            lag = int(starts[s]["lag"])
            next_lag = int(starts[s + 1]["lag"])
            for t in TT:
                if t + 1 >= next_lag:
                    model.addConstr(
                        startup_type[g, s, t]
                        <= gp.quicksum(stop[g, t - i] for i in range(lag, next_lag)),
                        name=f"startup_lag[{g},{s},{t}]",
                    )

            first_forbidden = max(1, next_lag - int(gen["time_down_t0"]) + 1)
            last_forbidden = min(next_lag - 1, T)
            for one_based_t in range(first_forbidden, last_forbidden + 1):
                model.addConstr(startup_type[g, s, one_based_t - 1] == 0)

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model.Status)

    if model.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "runtime": runtime,
            "T": T,
            "n_thermal": len(thermal),
            "n_renewable": len(renewable),
            "commitment": [],
            "dispatch_MW": [],
            "renewable_MW": [],
            "startups": 0,
            "shutdowns": 0,
        }

    commitment = [[int(round(u[g, t].X)) for t in TT] for g in G]
    dispatch = [
        [
            float(p[g, t].X) + float(thermal[g][1]["power_output_minimum"]) * commitment[g][t]
            for t in TT
        ]
        for g in G
    ]
    renewable_dispatch = [[float(renew[w, t].X) for t in TT] for w in W]
    max_demand_residual = max(
        abs(
            sum(dispatch[g][t] for g in G)
            + sum(renewable_dispatch[w][t] for w in W)
            - float(data["demand"][t])
        )
        for t in TT
    )
    reserve_margin = [sum(float(reserve[g, t].X) for g in G) - float(data["reserves"][t]) for t in TT]

    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap),
        "runtime": runtime,
        "T": T,
        "n_thermal": len(thermal),
        "n_renewable": len(renewable),
        "thermal_names": [name for name, _ in thermal],
        "renewable_names": [name for name, _ in renewable],
        "commitment": commitment,
        "dispatch_MW": dispatch,
        "renewable_MW": renewable_dispatch,
        "startups": sum(int(round(start[g, t].X)) for g in G for t in TT),
        "shutdowns": sum(int(round(stop[g, t].X)) for g in G for t in TT),
        "max_demand_residual_MW": max_demand_residual,
        "min_reserve_margin_MW": min(reserve_margin),
        "n_binary": model.NumBinVars,
        "n_variables": model.NumVars,
        "n_constraints": model.NumConstrs,
    }


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    data, config = load_case(case_dir)
    solution = solve_uc(data, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": "uc",
        "source": config.get("source", {}),
        "uc": solution,
    }
    output = case_dir / "results" / "python_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result

