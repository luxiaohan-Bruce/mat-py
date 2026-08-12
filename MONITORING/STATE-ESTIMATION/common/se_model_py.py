"""DC State Estimation: WLS (QP) and L1 robust (LP).

Measurements and true state are written in network/config by the builder.
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
from dc_network import bus_maps, branch_susceptance, is_zero_x  # noqa: E402
from result_io import load_case, write_result  # noqa: E402
from tolerances import solver_params_from_config  # noqa: E402


def solve_se(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    method = str(config.get("se_method", "wls")).lower()  # wls | l1
    base = float(network["baseMVA"])
    buses = network["buses"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB = len(bus_ids)
    meas = config["measurements"]  # list of {type, ...}
    true_theta = config.get("true_theta_rad") or [0.0] * nB
    params = solver_params_from_config(config)

    m = gp.Model(f"se_{method}")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.TimeLimit = params["TimeLimit"]

    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    residuals = []
    weights = []
    for k, me in enumerate(meas):
        t = me["type"]
        z = float(me["z"])
        sigma = float(me.get("sigma", 0.01))
        w = 1.0 / max(sigma * sigma, 1e-12)
        if t == "theta":
            i = bus_pos[int(me["bus"])]
            r = theta[i] - z
        elif t == "pinj":
            expr = gp.LinExpr(0.0)
            bid = int(me["bus"])
            for br in branches:
                if int(br.get("status", 1)) != 1 or is_zero_x(br):
                    continue
                f, tb = int(br["fbus"]), int(br["tbus"])
                bsus, phi = branch_susceptance(br)
                flow = base * bsus * (theta[bus_pos[f]] - theta[bus_pos[tb]] - phi)
                if f == bid:
                    expr += flow
                if tb == bid:
                    expr -= flow
            r = expr - z
        elif t == "pflow":
            ell = int(me["branch_id"]) - 1
            br = branches[ell]
            f, tb = int(br["fbus"]), int(br["tbus"])
            if is_zero_x(br):
                r = 0.0 * theta[0] + (0.0 - z)  # zero-x: skip poorly defined
                w = 0.0
            else:
                bsus, phi = branch_susceptance(br)
                flow = base * bsus * (theta[bus_pos[f]] - theta[bus_pos[tb]] - phi)
                r = flow - z
        else:
            continue
        residuals.append(r)
        weights.append(w)

    if method == "l1":
        tvars = m.addVars(len(residuals), lb=0.0, name="t")
        for k, r in enumerate(residuals):
            m.addConstr(tvars[k] >= r, name=f"lp_{k}")
            m.addConstr(tvars[k] >= -r, name=f"ln_{k}")
        m.setObjective(
            gp.quicksum(math.sqrt(max(weights[k], 0.0)) * tvars[k] for k in range(len(residuals))),
            GRB.MINIMIZE,
        )
    else:
        # WLS QP
        obj = gp.QuadExpr()
        for k, r in enumerate(residuals):
            if weights[k] <= 0:
                continue
            obj += weights[k] * r * r
        m.setObjective(obj, GRB.MINIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
    }.get(m.Status, str(m.Status))

    theta_hat = [0.0] * nB
    obj = None
    if m.SolCount > 0:
        obj = float(m.ObjVal)
        for i in range(nB):
            theta_hat[i] = float(theta[i].X)

    # state error vs truth
    max_err = 0.0
    rmse = 0.0
    for i in range(nB):
        e = theta_hat[i] - float(true_theta[i])
        max_err = max(max_err, abs(e))
        rmse += e * e
    rmse = math.sqrt(rmse / max(nB, 1))

    return {
        "status": status,
        "obj": obj,
        "obj_bound": obj,
        "mip_gap": 0.0,
        "runtime": runtime,
        "method": method,
        "theta_rad": theta_hat,
        "theta_deg": [math.degrees(v) for v in theta_hat],
        "max_theta_error_rad": max_err,
        "rmse_theta_rad": rmse,
        "n_meas": len(meas),
        "validation_passed": status == "OPTIMAL" and obj is not None,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_se(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "problem": "se",
        "base_problem": "state_estimation",
        "se": sol,
        "validation": {"passed": sol["validation_passed"]},
    }
    write_result(case_dir, "python_result.json", result)
    return result
