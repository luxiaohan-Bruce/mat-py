"""Three-phase linearized DistFlow OPF with a 3x3 impedance matrix."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB


PHASES = ("A", "B", "C")
POWER_TOL = 1e-4
VOLT_TOL = 1e-6


def _status_name(model: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }.get(model.Status, str(model.Status))


def solve_unbalanced_dopf(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    buses = network["buses"]
    branches = network["branches"]
    root = int(network["root_bus"])
    base = float(network.get("baseMVA", 1.0))
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    params = config.get("gurobi_parameters", {})

    model = gp.Model("unbalanced_lindistflow")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-6)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 120.0)))

    p_flow = model.addVars(len(branches), 3, lb=-GRB.INFINITY, name="P_MW")
    q_flow = model.addVars(len(branches), 3, lb=-GRB.INFINITY, name="Q_MVAr")
    v_sq = model.addVars(len(buses), 3, lb=0.0, name="Vsq_pu")
    p_sub = model.addVars(3, lb=-GRB.INFINITY, name="Psub_MW")
    q_sub = model.addVars(3, lb=-GRB.INFINITY, name="Qsub_MVAr")

    for bi, bus in enumerate(buses):
        vmin = float(bus.get("Vmin", 0.95)) ** 2
        vmax = float(bus.get("Vmax", 1.05)) ** 2
        for ph in range(3):
            v_sq[bi, ph].LB = vmin
            v_sq[bi, ph].UB = vmax
    root_pos = bus_pos[root]
    for ph in range(3):
        v_sq[root_pos, ph].LB = 1.0
        v_sq[root_pos, ph].UB = 1.0

    price = float(network.get("substation_price_per_MWh", 40.0))
    model.setObjective(price * gp.quicksum(p_sub[ph] for ph in range(3)), GRB.MINIMIZE)

    for ell, branch in enumerate(branches):
        smax = float(branch.get("smax_MVA", 5.0))
        r_mat = branch["r_pu"]
        x_mat = branch["x_pu"]
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        for ph in range(3):
            p_flow[ell, ph].LB = -smax
            p_flow[ell, ph].UB = smax
            q_flow[ell, ph].LB = -smax
            q_flow[ell, ph].UB = smax
            drop = gp.quicksum(
                2.0 * (float(r_mat[ph][psi]) * p_flow[ell, psi] + float(x_mat[ph][psi]) * q_flow[ell, psi]) / base
                for psi in range(3)
            )
            model.addConstr(v_sq[j, ph] == v_sq[i, ph] - drop, name=f"vdrop_{ell}_{ph}")

    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        pd = bus.get("Pd_phase") or [0.0, 0.0, 0.0]
        qd = bus.get("Qd_phase") or [0.0, 0.0, 0.0]
        for ph in range(3):
            p_out = gp.quicksum(
                p_flow[ell, ph] if int(branch["fbus"]) == bus_id else -p_flow[ell, ph]
                for ell, branch in enumerate(branches)
                if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
            )
            q_out = gp.quicksum(
                q_flow[ell, ph] if int(branch["fbus"]) == bus_id else -q_flow[ell, ph]
                for ell, branch in enumerate(branches)
                if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
            )
            inject_p = p_sub[ph] if bus_id == root else 0.0
            inject_q = q_sub[ph] if bus_id == root else 0.0
            model.addConstr(inject_p - float(pd[ph]) == p_out, name=f"p_bal_{bus_id}_{ph}")
            model.addConstr(inject_q - float(qd[ph]) == q_out, name=f"q_bal_{bus_id}_{ph}")

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    if model.SolCount == 0:
        return {"status": status, "obj": None, "runtime": runtime, "validation_passed": False}

    p_mw = [[float(p_flow[ell, ph].X) for ph in range(3)] for ell in range(len(branches))]
    q_mvar = [[float(q_flow[ell, ph].X) for ph in range(3)] for ell in range(len(branches))]
    vsq = [[float(v_sq[bi, ph].X) for ph in range(3)] for bi in range(len(buses))]
    psub = [float(p_sub[ph].X) for ph in range(3)]
    qsub = [float(q_sub[ph].X) for ph in range(3)]
    max_balance = 0.0
    max_volt = 0.0
    max_thermal = 0.0
    for bi, bus in enumerate(buses):
        bus_id = int(bus["bus_i"])
        pd = bus.get("Pd_phase") or [0.0, 0.0, 0.0]
        qd = bus.get("Qd_phase") or [0.0, 0.0, 0.0]
        for ph in range(3):
            p_out = 0.0
            q_out = 0.0
            for ell, branch in enumerate(branches):
                if int(branch["fbus"]) == bus_id:
                    p_out += p_mw[ell][ph]
                    q_out += q_mvar[ell][ph]
                elif int(branch["tbus"]) == bus_id:
                    p_out -= p_mw[ell][ph]
                    q_out -= q_mvar[ell][ph]
            inject_p = psub[ph] if bus_id == root else 0.0
            inject_q = qsub[ph] if bus_id == root else 0.0
            max_balance = max(
                max_balance,
                abs(inject_p - float(pd[ph]) - p_out),
                abs(inject_q - float(qd[ph]) - q_out),
            )
    for ell, branch in enumerate(branches):
        i = bus_pos[int(branch["fbus"])]
        j = bus_pos[int(branch["tbus"])]
        r_mat = branch["r_pu"]
        x_mat = branch["x_pu"]
        smax = float(branch.get("smax_MVA", 5.0))
        for ph in range(3):
            expected = vsq[i][ph] - 2.0 * sum(
                (float(r_mat[ph][psi]) * p_mw[ell][psi] + float(x_mat[ph][psi]) * q_mvar[ell][psi]) / base
                for psi in range(3)
            )
            max_volt = max(max_volt, abs(vsq[j][ph] - expected))
            max_thermal = max(max_thermal, max(0.0, (p_mw[ell][ph] ** 2 + q_mvar[ell][ph] ** 2) ** 0.5 - smax))
    recomputed = price * sum(psub)
    passed = status == "OPTIMAL" and max_balance <= POWER_TOL and max_volt <= VOLT_TOL and max_thermal <= POWER_TOL
    return {
        "status": status,
        "obj": float(model.ObjVal),
        "obj_bound": float(model.ObjBound),
        "mip_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime": runtime,
        "phases": list(PHASES),
        "Psub_MW": psub,
        "Qsub_MVAr": qsub,
        "P_MW": p_mw,
        "Q_MVAr": q_mvar,
        "Vsq_pu": vsq,
        "cost_recomputed": recomputed,
        "max_power_balance_MW": max_balance,
        "max_voltage_equation_pu": max_volt,
        "max_thermal_violation_MW": max_thermal,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "validation_passed": passed,
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_unbalanced_dopf(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi",
        "base_problem": "distribution_opf",
        "problem": "unbalanced_lindistflow_dopf",
        "unbalanced_dopf": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result
