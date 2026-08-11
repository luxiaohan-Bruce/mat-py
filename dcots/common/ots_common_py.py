"""Shared building blocks for DC-OTS and preventive SC-OTS (gurobipy).

Used by dcots_model_py.py and scots_model_py.py. Matches MATLAB helpers in
dcots_model_mat.m for numerical parity.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from validate_data import (
    angle_limit_rad,
    branch_susceptance,
    thermal_rate_pu,
    validate_network,
)


def load_case(case_dir: str | Path) -> tuple[dict, dict]:
    case_dir = Path(case_dir)
    with open(case_dir / "data" / "network.json", encoding="utf-8") as f:
        network = json.load(f)
    with open(case_dir / "data" / "config.json", encoding="utf-8") as f:
        config = json.load(f)
    validate_network(network, config)
    return network, config


def bus_maps(network: dict) -> tuple[list[int], dict[int, int], int]:
    bus_ids = [int(b["bus_i"]) for b in network["buses"]]
    bus_pos = {bid: i for i, bid in enumerate(bus_ids)}
    ref = None
    for b in network["buses"]:
        if int(b["type"]) == 3:
            ref = int(b["bus_i"])
            break
    if ref is None:
        ref = bus_ids[0]
    return bus_ids, bus_pos, ref


def switchable_set(config: dict, force_all_closed: bool) -> set[int]:
    if force_all_closed:
        return set()
    return set(int(i) for i in config.get("switchable_idx", []) or [])


def contingency_list(network: dict, config: dict) -> list[int]:
    """Return list of single-branch contingency branch ids (1-based)."""
    raw = config.get("contingencies", [])
    branches = network["branches"]
    online_ids = [int(br["id"]) for br in branches if int(br["status"]) == 1]
    if raw is None or raw == [] or raw == "none":
        return []
    if isinstance(raw, str) and raw.lower() in ("n1_all", "n-1", "n1"):
        return online_ids
    return [int(c) for c in raw]


def solver_params(m: gp.Model, config: dict, quiet: bool) -> None:
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.MIPGap = float(config.get("mip_gap", 1e-6))
    m.Params.TimeLimit = float(config.get("time_limit", 120))
    m.Params.Seed = int(config.get("seed", 1))
    m.Params.Threads = int(config.get("threads", 1))


def status_name(m: gp.Model) -> str:
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }
    return status_map.get(m.Status, str(m.Status))


def gen_bounds_pu(gen: dict, base: float) -> tuple[float, float]:
    if int(gen["status"]) == 0:
        return 0.0, 0.0
    pmin = float(gen["Pmin"]) / base
    pmax = float(gen["Pmax"]) / base
    return pmin, pmax


def add_objective(m: gp.Model, Pg: gp.tupledict, gens: list, base: float) -> bool:
    """Minimize cost over online generators only. Returns has_quad."""
    obj = gp.QuadExpr()
    has_quad = False
    for g, gen in enumerate(gens):
        if int(gen["status"]) == 0:
            continue
        c2, c1, c0 = float(gen["c2"]), float(gen["c1"]), float(gen["c0"])
        if abs(c2) > 1e-12:
            has_quad = True
            obj += c2 * (base * base) * Pg[g] * Pg[g]
        obj += c1 * base * Pg[g]
        obj += c0
    m.setObjective(obj, GRB.MINIMIZE)
    return has_quad


def add_branch_state(
    m: gp.Model,
    *,
    state: str,
    ell: int,
    br: dict,
    theta_i: gp.Var,
    theta_j: gp.Var,
    f: gp.Var,
    z: gp.Var | None,
    outaged: bool,
    base: float,
    contingency: bool,
) -> None:
    """Physics + thermal + conditional angle limits for one branch in one state.

    z is the shared topology binary (None => fixed closed if status==1).
    outaged: N-1 outage forces open regardless of z.
    """
    bsus, phi = branch_susceptance(br)
    rate = thermal_rate_pu(br, base, contingency=contingency)
    amin, amax = angle_limit_rad(br)
    status = int(br["status"])

    if status == 0 or outaged:
        m.addConstr(f == 0.0, name=f"{state}_f0_{ell}")
        return

    if z is None:
        m.addConstr(f == bsus * (theta_i - theta_j - phi), name=f"{state}_phys_{ell}")
        m.addConstr(f <= rate, name=f"{state}_fmax_{ell}")
        m.addConstr(f >= -rate, name=f"{state}_fmin_{ell}")
        if amax is not None:
            m.addConstr(theta_i - theta_j <= amax, name=f"{state}_angmax_{ell}")
        if amin is not None:
            m.addConstr(theta_i - theta_j >= amin, name=f"{state}_angmin_{ell}")
        return

    m.addGenConstrIndicator(
        z, True, f - bsus * (theta_i - theta_j - phi) == 0.0, name=f"{state}_ind_phys_{ell}"
    )
    m.addGenConstrIndicator(z, False, f == 0.0, name=f"{state}_ind_open_{ell}")
    m.addConstr(f <= rate * z, name=f"{state}_fmax_{ell}")
    m.addConstr(f >= -rate * z, name=f"{state}_fmin_{ell}")
    if amax is not None:
        m.addGenConstrIndicator(
            z, True, theta_i - theta_j <= amax, name=f"{state}_ind_angmax_{ell}"
        )
    if amin is not None:
        m.addGenConstrIndicator(
            z, True, theta_i - theta_j >= amin, name=f"{state}_ind_angmin_{ell}"
        )


def add_connectivity(
    m: gp.Model,
    *,
    state: str,
    nB: int,
    nL: int,
    branches: list,
    bus_ids: list[int],
    bus_pos: dict[int, int],
    ref_bus: int,
    z_vars: dict[int, gp.Var],
    outaged_ids: set[int],
) -> None:
    """Signed single-commodity flow: root at ref supplies 1 unit to every other bus."""
    if nB <= 1:
        return
    y = m.addVars(nL, lb=-GRB.INFINITY, name=f"{state}_y")
    cap = float(nB - 1)
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        offline = int(br["status"]) == 0 or bid in outaged_ids
        if offline:
            m.addConstr(y[ell] == 0.0, name=f"{state}_y0_{ell}")
            continue
        if ell in z_vars:
            z = z_vars[ell]
            m.addConstr(y[ell] <= cap * z, name=f"{state}_yp_{ell}")
            m.addConstr(y[ell] >= -cap * z, name=f"{state}_ym_{ell}")
        else:
            m.addConstr(y[ell] <= cap, name=f"{state}_yp_{ell}")
            m.addConstr(y[ell] >= -cap, name=f"{state}_ym_{ell}")

    for bi, bid in enumerate(bus_ids):
        outflow = gp.quicksum(
            y[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        )
        inflow = gp.quicksum(
            y[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        )
        if bid == ref_bus:
            m.addConstr(outflow - inflow == cap, name=f"{state}_conn_ref")
        else:
            m.addConstr(outflow - inflow == -1.0, name=f"{state}_conn_{bid}")


def add_power_balance(
    m: gp.Model,
    *,
    state: str,
    bus_ids: list[int],
    gens: list,
    branches: list,
    Pg: gp.tupledict,
    f: gp.tupledict,
    Pd: dict[int, float],
) -> None:
    for bid in bus_ids:
        inj = gp.quicksum(
            Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid
        )
        outf = gp.quicksum(
            f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        )
        inf = gp.quicksum(
            f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        )
        m.addConstr(inj - Pd.get(bid, 0.0) == outf - inf, name=f"{state}_bal_{bid}")


def pack_solution(
    *,
    m: gp.Model,
    runtime: float,
    branches: list,
    gens: list,
    bus_ids: list[int],
    base: float,
    ref_bus: int,
    z_vars: dict[int, gp.Var],
    max_open: int,
    force_all_closed: bool,
    has_quad: bool,
    theta: gp.tupledict,
    Pg: gp.tupledict,
    f: gp.tupledict,
    extra: dict | None = None,
    reported_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reported_metrics = reported_metrics or {}
    status = str(reported_metrics.get("status", status_name(m)))
    if m.SolCount == 0:
        out = {
            "status": status,
            "obj": None,
            "obj_bound": None,
            "mip_gap": None,
            "runtime": runtime,
            "opened_lines": [],
            "z": {},
            "Pg_MW": [],
            "theta_deg": [],
            "flow_MW": [],
            "force_all_closed": force_all_closed,
            "has_quad": has_quad,
            "n_binary": len(z_vars),
            "max_open": max_open,
            "ref_bus": ref_bus,
            "baseMVA": base,
        }
        if extra:
            out.update(extra)
        return out

    opened = []
    z_sol: dict[str, float] = {}
    for ell, z in z_vars.items():
        bid = int(branches[ell]["id"])
        val = float(z.X)
        z_sol[str(bid)] = val
        if val < 0.5:
            opened.append(bid)
    opened.sort()

    out = {
        "status": status,
        "obj": float(reported_metrics.get("obj", m.ObjVal)),
        "obj_bound": float(
            reported_metrics.get(
                "obj_bound", m.ObjBound if hasattr(m, "ObjBound") else m.ObjVal
            )
        ),
        "mip_gap": float(
            reported_metrics.get("mip_gap", m.MIPGap if m.IsMIP else 0.0)
        ),
        "runtime": runtime,
        "opened_lines": opened,
        "z": z_sol,
        "Pg_MW": [float(Pg[g].X) * base for g in range(len(gens))],
        "theta_deg": [math.degrees(float(theta[i].X)) for i in range(len(bus_ids))],
        "flow_MW": [float(f[ell].X) * base for ell in range(len(branches))],
        "force_all_closed": force_all_closed,
        "has_quad": has_quad,
        "n_binary": len(z_vars),
        "max_open": max_open,
        "ref_bus": ref_bus,
        "baseMVA": base,
    }
    if extra:
        out.update(extra)
    return out


def build_result_v2(
    *,
    case_dir: Path,
    network: dict,
    config: dict,
    dcopf: dict,
    ots: dict,
    problem: str,
) -> dict[str, Any]:
    savings = None
    if dcopf.get("obj") is not None and ots.get("obj") is not None:
        savings = float(dcopf["obj"]) - float(ots["obj"])

    result: dict[str, Any] = {
        "schema_version": 2,
        "case": case_dir.name,
        "solver": "python-gurobipy",
        "problem": problem,
        "network_name": network.get("name", case_dir.name),
        "dcopf": dcopf,
        "ots": ots,
        "savings": savings,
        "switchable_idx": [int(i) for i in config.get("switchable_idx", []) or []],
        "max_open": int(config.get("max_open", 0)),
        "notes": config.get("notes", []),
        "formulation": {
            "branch_physics": "f = b*(theta_f - theta_t - phi), b=1/(x*tap), tap=1 if ratio==0",
            "switching": "gurobi_indicators",
            "angle_limits": "conditional_matpower",
            "connectivity": "signed_single_commodity_all_states",
            "cost": "online_generators_only",
            "load_shedding": False,
            "scots_rates": {"base": "rateA", "contingency": "rateC"},
            "redispatch_frac": float(config.get("redispatch_frac", 0.2))
            if problem == "scots"
            else None,
            "contingency_solution_selection": (
                "post_optimal_min_sum_squared_dispatch"
                if problem == "scots" and config.get("canonicalize_contingencies", False)
                else None
            ),
        },
    }
    return result


def discover_cases(root: str | Path | None = None) -> list[str]:
    """Dynamic case discovery: directories with data/network.json."""
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    names = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "data" / "network.json").is_file():
            names.append(p.name)
    return names
