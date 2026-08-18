"""Green-LLM geographically distributed inference allocation (gurobipy).

Mirrors JJmingcc/Green_LLM model/lexicographic_model.py (the working experiment
model). Official Green_LLM.py references delay vars before they are created.

Decision x[i,j,k,t] = fraction of type-k queries from user region i served at DC j
in hour t.

  P_c[j,t] = sum_{i,k} (tau_in[k] h[k] + tau_out[k] f[k]) lambda[i,k,t] x
  P_d[j,t] = PUE[j] P_c[j,t]
  P_d[j,t] <= P_g[j,t] + P_w[j,t]
  P_g[j,t] <= P_max[j,t]
  woc[j,t] = (WUE[j,t]/PUE[j] + EWIF[j,t]) P_d[j,t]
  sum woc <= Z
  sum_{i,k} alpha[k,r] (h[k]+f[k]) lambda x <= C[r,j]
  sum_j x[i,j,k,t] == 1
  delays: transmission / propagation / processing <= Delta[i,k]

Objectives (energy / carbon / delay) are either weighted or lexicographic.
Optional binaries z[j,k]: x <= z and a one-shot download cost.
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
from tolerances import solver_params_from_config  # noqa: E402

ALLOC_TOL = 1e-6
CAP_TOL = 1e-5
WATER_TOL = 1e-4
COST_TOL = 1e-6


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(m.Status, str(m.Status))


def _solve_one(
    network: dict,
    config: dict,
    *,
    primary: str,
    hold: dict[str, float],
    quiet: bool,
) -> dict[str, Any]:
    nI = int(network["n_user"])
    nJ = int(network["n_dc"])
    nK = int(network["n_query"])
    nR = int(network["n_resource"])
    T = int(network["horizon"])
    lam = network["lambda"]
    h = [float(v) for v in network["h"]]
    ftok = [float(v) for v in network["f"]]
    tau_in = [float(v) for v in network["tau_in"]]
    tau_out = [float(v) for v in network["tau_out"]]
    c = network["c"]
    theta = network["theta"]
    delta = [float(v) for v in network["delta"]]
    P_w = network["P_w"]
    P_max = network["P_max"]
    PUE = [float(v) for v in network["PUE"]]
    Cap = network["C"]
    alpha = network["alpha"]
    rho = [float(v) for v in network["rho"]]
    beta = network["beta"]
    B = network["B"]
    dly = network["d"]
    vproc = network["v"]
    Delta = network["Delta"]
    WUE = network["WUE"]
    EWIF = network["EWIF"]
    Z = float(network["Z"])
    we = float(network.get("w_energy", 1.0))
    wc = float(network.get("w_carbon", 1.0))
    wd = float(network.get("w_delay", 1.0))
    place = bool(network.get("place_models", False))
    z_prev = network.get("z_prev") or [[0] * nK for _ in range(nJ)]
    f_dl = network.get("f_download") or [[0.0] * nK for _ in range(nJ)]
    params = solver_params_from_config(config)

    m = gp.Model("green_llm")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]
    m.Params.FeasibilityTol = 1e-6

    x = m.addVars(nI, nJ, nK, T, lb=0.0, ub=1.0, name="x")
    P_g = m.addVars(nJ, T, lb=0.0, name="Pg")
    P_c = m.addVars(nJ, T, lb=0.0, name="Pc")
    P_d = m.addVars(nJ, T, lb=0.0, name="Pd")
    D_tran = m.addVars(nI, nK, T, lb=0.0, name="Dtr")
    D_prop = m.addVars(nI, nK, T, lb=0.0, name="Dpr")
    D_proc = m.addVars(nI, nK, T, lb=0.0, name="Dpc")
    woc = m.addVars(nJ, T, lb=0.0, name="woc")
    z = None
    if place:
        z = m.addVars(nJ, nK, vtype=GRB.BINARY, name="z")

    e_tok = [tau_in[k] * h[k] + tau_out[k] * ftok[k] for k in range(nK)]
    tok = [h[k] + ftok[k] for k in range(nK)]

    for j in range(nJ):
        for t in range(T):
            m.addConstr(
                P_c[j, t]
                == gp.quicksum(
                    e_tok[k] * lam[i][k][t] * x[i, j, k, t]
                    for i in range(nI)
                    for k in range(nK)
                ),
                name=f"pc_{j}_{t}",
            )
            m.addConstr(P_d[j, t] == PUE[j] * P_c[j, t], name=f"pd_{j}_{t}")
            m.addConstr(P_d[j, t] <= P_g[j, t] + float(P_w[j][t]), name=f"bal_{j}_{t}")
            m.addConstr(P_g[j, t] <= float(P_max[j][t]), name=f"gmax_{j}_{t}")
            m.addConstr(
                woc[j, t]
                == (float(WUE[j][t]) / PUE[j] + float(EWIF[j][t])) * P_d[j, t],
                name=f"woc_{j}_{t}",
            )
            for r in range(nR):
                m.addConstr(
                    gp.quicksum(
                        float(alpha[k][r]) * tok[k] * lam[i][k][t] * x[i, j, k, t]
                        for i in range(nI)
                        for k in range(nK)
                    )
                    <= float(Cap[r][j]),
                    name=f"res_{r}_{j}_{t}",
                )

    m.addConstr(gp.quicksum(woc[j, t] for j in range(nJ) for t in range(T)) <= Z, name="Z")

    for i in range(nI):
        for k in range(nK):
            for t in range(T):
                m.addConstr(
                    gp.quicksum(x[i, j, k, t] for j in range(nJ)) == 1.0,
                    name=f"alloc_{i}_{k}_{t}",
                )
                m.addConstr(
                    D_tran[i, k, t]
                    == gp.quicksum(
                        float(beta[i][k][t])
                        * lam[i][k][t]
                        * x[i, j, k, t]
                        * tok[k]
                        / max(0.001, float(B[i][j]))
                        for j in range(nJ)
                    ),
                    name=f"dtr_{i}_{k}_{t}",
                )
                m.addConstr(
                    D_prop[i, k, t]
                    == gp.quicksum(float(dly[i][j]) * x[i, j, k, t] for j in range(nJ)),
                    name=f"dpr_{i}_{k}_{t}",
                )
                m.addConstr(
                    D_proc[i, k, t]
                    == gp.quicksum(
                        float(vproc[j][k]) * tok[k] * lam[i][k][t] * x[i, j, k, t]
                        for j in range(nJ)
                    ),
                    name=f"dpc_{i}_{k}_{t}",
                )
                m.addConstr(
                    D_tran[i, k, t] + D_prop[i, k, t] + D_proc[i, k, t]
                    <= float(Delta[i][k]),
                    name=f"dmax_{i}_{k}_{t}",
                )
                if place:
                    for j in range(nJ):
                        m.addConstr(x[i, j, k, t] <= z[j, k], name=f"pl_{i}_{j}_{k}_{t}")

    C_energy = gp.quicksum(float(c[j][t]) * P_g[j, t] for j in range(nJ) for t in range(T))
    C_carbon = gp.quicksum(
        delta[j] * float(theta[j][t]) * P_g[j, t] for j in range(nJ) for t in range(T)
    )
    C_delay = gp.quicksum(
        rho[k] * (D_tran[i, k, t] + D_prop[i, k, t] + D_proc[i, k, t])
        for i in range(nI)
        for k in range(nK)
        for t in range(T)
    )
    C_place = 0.0
    if place:
        C_place = gp.quicksum(
            float(f_dl[j][k]) * (1 - int(z_prev[j][k])) * z[j, k]
            for j in range(nJ)
            for k in range(nK)
        )

    if primary == "energy":
        m.setObjective(C_energy + C_place, GRB.MINIMIZE)
    elif primary == "carbon":
        m.setObjective(C_carbon + C_place, GRB.MINIMIZE)
    elif primary == "delay":
        m.setObjective(C_delay + C_place, GRB.MINIMIZE)
    else:
        m.setObjective(we * C_energy + wc * C_carbon + wd * C_delay + C_place, GRB.MINIMIZE)

    if "energy" in hold:
        m.addConstr(C_energy <= hold["energy"], name="hold_energy")
    if "carbon" in hold:
        m.addConstr(C_carbon <= hold["carbon"], name="hold_carbon")
    if "delay" in hold:
        m.addConstr(C_delay <= hold["delay"], name="hold_delay")

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
            "primary": primary,
        }

    energy = float(C_energy.getValue())
    carbon = float(C_carbon.getValue())
    delay = float(C_delay.getValue())
    place_cost = float(C_place.getValue()) if place else 0.0
    load_dc = [[0.0] * T for _ in range(nJ)]
    pg = [[0.0] * T for _ in range(nJ)]
    for j in range(nJ):
        for t in range(T):
            pg[j][t] = float(P_g[j, t].X)
            for i in range(nI):
                for k in range(nK):
                    load_dc[j][t] += float(x[i, j, k, t].X) * lam[i][k][t]
    z_sol = None
    if place:
        z_sol = [[int(round(z[j, k].X)) for k in range(nK)] for j in range(nJ)]

    obj_val = float(m.ObjVal)
    try:
        obj_bound = float(m.ObjBound)
    except Exception:
        obj_bound = obj_val
    return {
        "status": status,
        "obj": obj_val,
        "obj_bound": obj_bound,
        "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        "runtime": runtime,
        "n_var": m.NumVars,
        "n_constr": m.NumConstrs,
        "primary": primary,
        "energy_cost": energy,
        "carbon_cost": carbon,
        "delay_cost": delay,
        "place_cost": place_cost,
        "total_cost": energy + carbon + delay + place_cost,
        "load_dc_t": load_dc,
        "P_g": pg,
        "z": z_sol,
        "water_used": float(sum(woc[j, t].X for j in range(nJ) for t in range(T))),
    }


def solve_green_llm(network: dict, config: dict, *, quiet: bool = True) -> dict[str, Any]:
    mode = str(network.get("mode", "weighted")).lower()
    if mode == "lex":
        order = [str(s) for s in network.get("priority", ["carbon", "delay", "energy"])]
        tol = float(network.get("lex_tolerance", 0.001))
        hold: dict[str, float] = {}
        phases = []
        last: dict[str, Any] = {}
        total_rt = 0.0
        for name in order:
            last = _solve_one(network, config, primary=name, hold=hold, quiet=quiet)
            total_rt += float(last.get("runtime") or 0.0)
            phases.append(
                {
                    "objective": name,
                    "status": last.get("status"),
                    "energy_cost": last.get("energy_cost"),
                    "carbon_cost": last.get("carbon_cost"),
                    "delay_cost": last.get("delay_cost"),
                }
            )
            if last.get("status") not in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT"):
                last["lex_phases"] = phases
                last["runtime"] = total_rt
                last["mode"] = mode
                last.update(validate_green_llm(network, last))
                return last
            key = {"energy": "energy_cost", "carbon": "carbon_cost", "delay": "delay_cost"}[name]
            hold[name] = float(last[key]) * (1.0 + tol)
        last["lex_phases"] = phases
        last["runtime"] = total_rt
        last["mode"] = mode
        last.update(validate_green_llm(network, last))
        return last

    sol = _solve_one(network, config, primary="weighted", hold={}, quiet=quiet)
    sol["mode"] = mode
    sol.update(validate_green_llm(network, sol))
    return sol


def validate_green_llm(network: dict, sol: dict[str, Any]) -> dict[str, Any]:
    nI = int(network["n_user"])
    nJ = int(network["n_dc"])
    nK = int(network["n_query"])
    nR = int(network["n_resource"])
    T = int(network["horizon"])
    status = str(sol.get("status") or "")
    obj = sol.get("obj")
    if obj is None:
        return {"validation_passed": False, "max_alloc_violation": 1.0}

    lam = network["lambda"]
    h = [float(v) for v in network["h"]]
    ftok = [float(v) for v in network["f"]]
    tau_in = [float(v) for v in network["tau_in"]]
    tau_out = [float(v) for v in network["tau_out"]]
    PUE = [float(v) for v in network["PUE"]]
    Cap = network["C"]
    alpha = network["alpha"]
    P_w = network["P_w"]
    P_max = network["P_max"]
    WUE = network["WUE"]
    EWIF = network["EWIF"]
    Z = float(network["Z"])
    we = float(network.get("w_energy", 1.0))
    wc = float(network.get("w_carbon", 1.0))
    wd = float(network.get("w_delay", 1.0))
    place = bool(network.get("place_models", False))

    # Rebuild allocation from load is insufficient; re-check reported costs vs power.
    pg = sol.get("P_g") or [[0.0] * T for _ in range(nJ)]
    energy = 0.0
    carbon = 0.0
    water = 0.0
    max_grid = 0.0
    for j in range(nJ):
        for t in range(T):
            p = float(pg[j][t])
            energy += float(network["c"][j][t]) * p
            carbon += float(network["delta"][j]) * float(network["theta"][j][t]) * p
            max_grid = max(max_grid, max(0.0, p - float(P_max[j][t])))
    water = float(sol.get("water_used") or 0.0)
    water_vio = max(0.0, water - Z)
    delay = float(sol.get("delay_cost") or 0.0)
    place_cost = float(sol.get("place_cost") or 0.0)
    mode = str(network.get("mode", "weighted")).lower()
    primary = str(sol.get("primary") or "weighted")
    if mode == "lex":
        if primary == "energy":
            recomputed = energy + place_cost
        elif primary == "carbon":
            recomputed = carbon + place_cost
        else:
            recomputed = delay + place_cost
    else:
        recomputed = we * energy + wc * carbon + wd * delay + place_cost
    cost_gap = abs(recomputed - float(obj))
    passed = (
        status in ("OPTIMAL", "SUBOPTIMAL", "TIME_LIMIT")
        and max_grid <= CAP_TOL
        and water_vio <= WATER_TOL
        and cost_gap <= max(0.01, COST_TOL * max(1.0, abs(float(obj))))
    )
    # silence unused
    _ = (nI, nK, nR, h, ftok, tau_in, tau_out, PUE, Cap, alpha, P_w, lam)
    return {
        "energy_recomputed": energy,
        "carbon_recomputed": carbon,
        "cost_recomputed": recomputed,
        "max_grid_violation": max_grid,
        "water_violation": water_vio,
        "cost_gap": cost_gap,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_green_llm(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "green_llm",
        "base_problem": "green_llm",
        "green_llm": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    d = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "case006_4dc_6h_smoke"
    )
    r = run_case(d, quiet=True)
    e = r["green_llm"]
    print(
        f"[{r['case']}] status={e['status']} obj={e['obj']} "
        f"E={e.get('energy_cost')} C={e.get('carbon_cost')} "
        f"D={e.get('delay_cost')} valid={e.get('validation_passed')}"
    )
