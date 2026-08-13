"""Preventive security-constrained exact polar AC-OPF.

Base-case and post-contingency states share active-power setpoints. Each state
keeps its own voltages, angles, reactive dispatch and branch flows. Outaged
branches are removed from that state's AC equations rather than relaxed.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB, nlfunc

ACOPF_COMMON = Path(__file__).resolve().parents[2] / "AC-OPF" / "common"
sys.path.insert(0, str(ACOPF_COMMON))
from acopf_model import (  # noqa: E402
    _branch_coefficients,
    _status_name,
    validate_acopf_solution,
)


def _masked_network(network: dict[str, Any], outaged: set[int]) -> dict[str, Any]:
    clone = dict(network)
    clone["branches"] = []
    for branch in network["branches"]:
        item = dict(branch)
        if int(item["id"]) in outaged:
            item["status"] = 0
        clone["branches"].append(item)
    return clone


def solve_scacopf(
    network: dict[str, Any], config: dict[str, Any], *, quiet: bool = True
) -> dict[str, Any]:
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    contingencies = [{"id": 0, "outaged_branches": [], "label": "base"}]
    for raw in network.get("contingencies") or []:
        contingencies.append(
            {
                "id": int(raw["id"]),
                "outaged_branches": [int(x) for x in raw["outaged_branches"]],
                "label": raw.get("label") or f"ctg_{raw['id']}",
            }
        )
    base = float(network["baseMVA"])
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    ref_candidates = [int(bus["bus_i"]) for bus in buses if int(bus.get("type", 1)) == 3]
    ref_bus = ref_candidates[0] if ref_candidates else bus_ids[0]
    params = config.get("gurobi_parameters", {})

    model = gp.Model("preventive_sc_acopf")
    model.Params.OutputFlag = 0 if quiet else 1
    model.Params.NonConvex = 2
    model.Params.FuncNonlinear = 1
    model.Params.Seed = int(params.get("Seed", config.get("seed", 1)))
    model.Params.Threads = int(params.get("Threads", config.get("threads", 1)))
    model.Params.MIPGap = float(params.get("MIPGap", config.get("mip_gap", 1e-4)))
    model.Params.TimeLimit = float(params.get("TimeLimit", config.get("time_limit", 600.0)))
    model.Params.FeasibilityTol = 1e-8
    model.Params.OptimalityTol = 1e-8
    model.Params.NumericFocus = 2

    states = list(range(len(contingencies)))
    vm = model.addVars(len(states), len(buses), lb=0.0, name="Vm_pu")
    va = model.addVars(len(states), len(buses), lb=-math.pi, ub=math.pi, name="Va_rad")
    pg = model.addVars(len(gens), lb=-GRB.INFINITY, name="Pg_MW")
    qg = model.addVars(len(states), len(gens), lb=-GRB.INFINITY, name="Qg_MVAr")
    p_from = model.addVars(len(states), len(branches), lb=-GRB.INFINITY, name="P_from_MW")
    q_from = model.addVars(len(states), len(branches), lb=-GRB.INFINITY, name="Q_from_MVAr")
    p_to = model.addVars(len(states), len(branches), lb=-GRB.INFINITY, name="P_to_MW")
    q_to = model.addVars(len(states), len(branches), lb=-GRB.INFINITY, name="Q_to_MVAr")

    for bi, bus in enumerate(buses):
        for s in states:
            vm[s, bi].LB = float(bus["Vmin"])
            vm[s, bi].UB = float(bus["Vmax"])
            vm[s, bi].Start = min(max(float(bus.get("Vm", 1.0)), float(bus["Vmin"])), float(bus["Vmax"]))
            va[s, bi].Start = math.radians(float(bus.get("Va", 0.0)))
    ref_pos = bus_pos[ref_bus]
    ref_angle = math.radians(float(buses[ref_pos].get("Va", 0.0)))
    for s in states:
        model.addConstr(va[s, ref_pos] == ref_angle, name=f"reference_angle_{s}")

    objective = gp.QuadExpr()
    for g, gen in enumerate(gens):
        online = int(gen.get("status", 1)) == 1
        p_min = float(gen["Pmin"]) if online else 0.0
        p_max = float(gen["Pmax"]) if online else 0.0
        pg[g].LB, pg[g].UB = p_min, p_max
        pg[g].Start = min(max(float(gen.get("Pg", 0.0)), p_min), p_max)
        if online:
            if int(gen.get("cost_model", 2)) != 2:
                raise ValueError("SC-AC-OPF requires polynomial P-cost (cost_model=2)")
            objective += float(gen.get("c2", 0.0)) * pg[g] * pg[g]
            objective += float(gen.get("c1", 0.0)) * pg[g]
            objective += float(gen.get("c0", 0.0))
        for s in states:
            q_min = float(gen["Qmin"]) if online else 0.0
            q_max = float(gen["Qmax"]) if online else 0.0
            qg[s, g].LB, qg[s, g].UB = q_min, q_max
    model.setObjective(objective, GRB.MINIMIZE)

    for s, ctg in enumerate(contingencies):
        outaged = {int(idx) for idx in ctg["outaged_branches"]}
        for ell, branch in enumerate(branches):
            offline = int(branch.get("status", 1)) == 0 or int(branch["id"]) in outaged
            if offline:
                model.addConstr(p_from[s, ell] == 0.0, name=f"p_from_off_{s}_{ell}")
                model.addConstr(q_from[s, ell] == 0.0, name=f"q_from_off_{s}_{ell}")
                model.addConstr(p_to[s, ell] == 0.0, name=f"p_to_off_{s}_{ell}")
                model.addConstr(q_to[s, ell] == 0.0, name=f"q_to_off_{s}_{ell}")
                continue
            i = bus_pos[int(branch["fbus"])]
            j = bus_pos[int(branch["tbus"])]
            g, b, charging, tap, shift = _branch_coefficients(branch)
            delta = va[s, i] - va[s, j] - shift
            cosine = nlfunc.cos(delta)
            sine = nlfunc.sin(delta)
            cross = vm[s, i] * vm[s, j] / tap
            model.addConstr(
                p_from[s, ell]
                == base * (g * vm[s, i] * vm[s, i] / (tap * tap) - cross * (g * cosine + b * sine)),
                name=f"p_from_eq_{s}_{ell}",
            )
            model.addConstr(
                q_from[s, ell]
                == base
                * (
                    -(b + charging / 2.0) * vm[s, i] * vm[s, i] / (tap * tap)
                    - cross * (g * sine - b * cosine)
                ),
                name=f"q_from_eq_{s}_{ell}",
            )
            model.addConstr(
                p_to[s, ell] == base * (g * vm[s, j] * vm[s, j] - cross * (g * cosine - b * sine)),
                name=f"p_to_eq_{s}_{ell}",
            )
            model.addConstr(
                q_to[s, ell]
                == base
                * (-(b + charging / 2.0) * vm[s, j] * vm[s, j] + cross * (g * sine + b * cosine)),
                name=f"q_to_eq_{s}_{ell}",
            )
            lower = float(branch.get("angmin", -360.0))
            upper = float(branch.get("angmax", 360.0))
            if lower > -360.0:
                model.addConstr(va[s, i] - va[s, j] >= math.radians(lower), name=f"angle_min_{s}_{ell}")
            if upper < 360.0:
                model.addConstr(va[s, i] - va[s, j] <= math.radians(upper), name=f"angle_max_{s}_{ell}")
            rate = float(branch.get("rateC" if s > 0 else "rateA", 0.0) or branch.get("rateA", 0.0))
            if rate > 0.0:
                model.addQConstr(
                    p_from[s, ell] * p_from[s, ell] + q_from[s, ell] * q_from[s, ell] <= rate * rate,
                    name=f"thermal_from_{s}_{ell}",
                )
                model.addQConstr(
                    p_to[s, ell] * p_to[s, ell] + q_to[s, ell] * q_to[s, ell] <= rate * rate,
                    name=f"thermal_to_{s}_{ell}",
                )
        for bi, bus in enumerate(buses):
            bus_id = int(bus["bus_i"])
            p_generation = gp.quicksum(pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id)
            q_generation = gp.quicksum(
                qg[s, g] for g, gen in enumerate(gens) if int(gen["bus"]) == bus_id
            )
            p_out = gp.quicksum(
                p_from[s, ell] if int(branch["fbus"]) == bus_id else p_to[s, ell]
                for ell, branch in enumerate(branches)
                if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
            )
            q_out = gp.quicksum(
                q_from[s, ell] if int(branch["fbus"]) == bus_id else q_to[s, ell]
                for ell, branch in enumerate(branches)
                if int(branch["fbus"]) == bus_id or int(branch["tbus"]) == bus_id
            )
            model.addConstr(
                p_generation - float(bus.get("Pd", 0.0))
                == p_out + float(bus.get("Gs", 0.0)) * vm[s, bi] * vm[s, bi],
                name=f"p_balance_{s}_{bus_id}",
            )
            model.addConstr(
                q_generation - float(bus.get("Qd", 0.0))
                == q_out - float(bus.get("Bs", 0.0)) * vm[s, bi] * vm[s, bi],
                name=f"q_balance_{s}_{bus_id}",
            )

    started = time.time()
    model.optimize()
    runtime = time.time() - started
    status = _status_name(model)
    if model.SolCount == 0:
        return {
            "status": status,
            "obj": None,
            "objective": None,
            "runtime_seconds": runtime,
            "n_cont": len(contingencies) - 1,
            "validation_passed": False,
        }

    pg_mw = [float(pg[g].X) for g in range(len(gens))]
    state_blocks = []
    max_p = 0.0
    max_q = 0.0
    max_thermal = 0.0
    all_valid = True
    for s, ctg in enumerate(contingencies):
        vm_s = [float(vm[s, i].X) for i in range(len(buses))]
        va_s = [math.degrees(float(va[s, i].X)) for i in range(len(buses))]
        qg_s = [float(qg[s, g].X) for g in range(len(gens))]
        pf_s = [float(p_from[s, ell].X) for ell in range(len(branches))]
        qf_s = [float(q_from[s, ell].X) for ell in range(len(branches))]
        pt_s = [float(p_to[s, ell].X) for ell in range(len(branches))]
        qt_s = [float(q_to[s, ell].X) for ell in range(len(branches))]
        masked = _masked_network(network, set(ctg["outaged_branches"]))
        validation = validate_acopf_solution(
            masked, vm_s, va_s, pg_mw, qg_s, pf_s, qf_s, pt_s, qt_s, float(model.ObjVal) if s == 0 else None
        )
        if s > 0:
            validation.pop("cost_recomputed", None)
            validation.pop("cost_recompute_error", None)
        all_valid = all_valid and bool(validation.get("validation_passed"))
        max_p = max(max_p, float(validation.get("max_p_balance_MW") or 0.0))
        max_q = max(max_q, float(validation.get("max_q_balance_MVAr") or 0.0))
        max_thermal = max(max_thermal, float(validation.get("max_thermal_violation_MVA") or 0.0))
        state_blocks.append(
            {
                "label": ctg["label"],
                "outaged_branches": ctg["outaged_branches"],
                "Vm_pu": vm_s,
                "Va_deg": va_s,
                "Qg_MVAr": qg_s,
                "P_from_MW": pf_s,
                "Q_from_MVAr": qf_s,
                "P_to_MW": pt_s,
                "Q_to_MVAr": qt_s,
                **validation,
            }
        )
    obj = float(model.ObjVal)
    return {
        "status": status,
        "obj": obj,
        "objective": obj,
        "obj_bound": float(model.ObjBound),
        "objective_bound": float(model.ObjBound),
        "optimality_gap": float(model.MIPGap) if model.IsMIP else 0.0,
        "runtime_seconds": runtime,
        "n_cont": len(contingencies) - 1,
        "Pg_MW": pg_mw,
        "states": state_blocks,
        "max_power_balance_MW": max(max_p, max_q),
        "max_thermal_violation_MW": max_thermal,
        "n_var": model.NumVars,
        "n_constr": model.NumConstrs,
        "globally_optimal": status == "OPTIMAL",
        "validation_passed": bool(all_valid),
    }


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    solution = solve_scacopf(network, config, quiet=quiet)
    result = {
        "schema_version": 1,
        "case": config.get("case", case_dir.name),
        "solver": "python-gurobi-13-global-nonlinear",
        "base_problem": "opf",
        "problem": "sc_ac_opf",
        "variant": config.get("variant"),
        "scacopf": solution,
        "validation": {"passed": bool(solution.get("validation_passed"))},
    }
    out_dir = case_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "python_result.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return result
