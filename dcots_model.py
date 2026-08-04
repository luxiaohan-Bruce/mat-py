"""Shared DC-OTS and preventive SC-OTS implementation using gurobipy.

Formulation highlights:
  - DC branch: f = b (θ_f - θ_t - φ), b = 1/(x·tap), tap=1 if ratio==0
  - Switching via Gurobi indicator constraints (no big-M / global Δθ boxes)
  - Conditional MATPOWER angle limits only when a branch is effectively closed
  - Signed single-commodity connectivity in every operating state
  - Objective costs only for online generators (status==1)
  - SC-OTS: shared z, rateA base / rateC contingency, redispatch band, no load shed
  - Optional post-optimal strictly-convex tie-break for deterministic contingency states
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from validate_data import (
    DataValidationError,
    angle_limit_rad,
    branch_susceptance,
    thermal_rate_pu,
    validate_network,
)
from validate_residuals import validate_solution_bundle


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_case(case_dir: str | Path) -> tuple[dict, dict]:
    case_dir = Path(case_dir)
    with open(case_dir / "network.json", encoding="utf-8") as f:
        network = json.load(f)
    with open(case_dir / "config.json", encoding="utf-8") as f:
        config = json.load(f)
    validate_network(network, config)
    return network, config


def _bus_maps(network: dict) -> tuple[list[int], dict[int, int], int]:
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


def _switchable_set(config: dict, force_all_closed: bool) -> set[int]:
    if force_all_closed:
        return set()
    return set(int(i) for i in config.get("switchable_idx", []) or [])


def _contingency_list(network: dict, config: dict) -> list[int]:
    """Return list of single-branch contingency branch ids (1-based)."""
    raw = config.get("contingencies", [])
    branches = network["branches"]
    online_ids = [int(br["id"]) for br in branches if int(br["status"]) == 1]
    if raw is None or raw == [] or raw == "none":
        return []
    if isinstance(raw, str) and raw.lower() in ("n1_all", "n-1", "n1"):
        return online_ids
    return [int(c) for c in raw]


def _solver_params(m: gp.Model, config: dict, quiet: bool) -> None:
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.MIPGap = float(config.get("mip_gap", 1e-6))
    m.Params.TimeLimit = float(config.get("time_limit", 120))
    m.Params.Seed = int(config.get("seed", 1))
    m.Params.Threads = int(config.get("threads", 1))


def _status_name(m: gp.Model) -> str:
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
    }
    return status_map.get(m.Status, str(m.Status))


def _gen_bounds_pu(gen: dict, base: float) -> tuple[float, float]:
    if int(gen["status"]) == 0:
        return 0.0, 0.0
    pmin = float(gen["Pmin"]) / base
    pmax = float(gen["Pmax"]) / base
    return pmin, pmax


def _add_objective(m: gp.Model, Pg: gp.tupledict, gens: list, base: float) -> bool:
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


# ---------------------------------------------------------------------------
# Branch / connectivity building blocks (indicator-based)
# ---------------------------------------------------------------------------

def _add_branch_state(
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

    # Offline or contingency outage: force flow 0, no physics
    if status == 0 or outaged:
        m.addConstr(f == 0.0, name=f"{state}_f0_{ell}")
        return

    if z is None:
        # Always closed
        m.addConstr(f == bsus * (theta_i - theta_j - phi), name=f"{state}_phys_{ell}")
        m.addConstr(f <= rate, name=f"{state}_fmax_{ell}")
        m.addConstr(f >= -rate, name=f"{state}_fmin_{ell}")
        if amax is not None:
            m.addConstr(theta_i - theta_j <= amax, name=f"{state}_angmax_{ell}")
        if amin is not None:
            m.addConstr(theta_i - theta_j >= amin, name=f"{state}_angmin_{ell}")
        return

    # Switchable: indicators on z
    # z=1 => physics; z=0 => f=0
    m.addGenConstrIndicator(
        z, True, f - bsus * (theta_i - theta_j - phi) == 0.0, name=f"{state}_ind_phys_{ell}"
    )
    m.addGenConstrIndicator(z, False, f == 0.0, name=f"{state}_ind_open_{ell}")
    # Thermal: |f| <= rate * z  (linear, tight when z∈{0,1})
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


def _add_connectivity(
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
    """Signed single-commodity flow: root at ref supplies 1 unit to every other bus.

    Edge capacity linked to effective closed status (z and not outaged / online).
    """
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
        # net supply = outflow - inflow
        if bid == ref_bus:
            m.addConstr(outflow - inflow == cap, name=f"{state}_conn_ref")
        else:
            m.addConstr(outflow - inflow == -1.0, name=f"{state}_conn_{bid}")


def _add_power_balance(
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


def _pack_solution(
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
    status = str(reported_metrics.get("status", _status_name(m)))
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


# ---------------------------------------------------------------------------
# solve_dcots
# ---------------------------------------------------------------------------

def solve_dcots(
    network: dict,
    config: dict,
    *,
    force_all_closed: bool = False,
    quiet: bool = True,
) -> dict[str, Any]:
    """Solve DC-OTS (or DCOPF if force_all_closed). Powers in p.u.; cost in $/h."""
    validate_network(network, config)

    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = _bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)

    switchable = _switchable_set(config, force_all_closed)
    max_open = 0 if force_all_closed else int(config.get("max_open", 0))
    Pd = {int(b["bus_i"]): float(b["Pd"]) / base for b in buses}

    m = gp.Model("dcots")
    _solver_params(m, config, quiet)

    # Free angles (ref fixed); no global angle box
    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, name="Pg")
    f = m.addVars(nL, lb=-GRB.INFINITY, name="f")

    z_vars: dict[int, gp.Var] = {}
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        if bid in switchable and int(br["status"]) == 1:
            z_vars[ell] = m.addVar(vtype=GRB.BINARY, name=f"z_{bid}")

    fixed_open = {int(i) for i in config.get("fixed_open_idx", []) or []}
    for ell, z in z_vars.items():
        if int(branches[ell]["id"]) in fixed_open:
            m.addConstr(z == 0.0, name=f"fixed_open_{int(branches[ell]['id'])}")

    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    for g, gen in enumerate(gens):
        pmin, pmax = _gen_bounds_pu(gen, base)
        Pg[g].LB = pmin
        Pg[g].UB = pmax

    has_quad = _add_objective(m, Pg, gens, base)

    for ell, br in enumerate(branches):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        _add_branch_state(
            m,
            state="base",
            ell=ell,
            br=br,
            theta_i=theta[i],
            theta_j=theta[j],
            f=f[ell],
            z=z_vars.get(ell),
            outaged=False,
            base=base,
            contingency=False,
        )

    if z_vars and max_open < len(z_vars):
        m.addConstr(
            gp.quicksum(1 - z for z in z_vars.values()) <= max_open, name="max_open"
        )

    _add_power_balance(
        m, state="base", bus_ids=bus_ids, gens=gens, branches=branches, Pg=Pg, f=f, Pd=Pd
    )
    _add_connectivity(
        m,
        state="base",
        nB=nB,
        nL=nL,
        branches=branches,
        bus_ids=bus_ids,
        bus_pos=bus_pos,
        ref_bus=ref_bus,
        z_vars=z_vars,
        outaged_ids=set(),
    )

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0

    return _pack_solution(
        m=m,
        runtime=runtime,
        branches=branches,
        gens=gens,
        bus_ids=bus_ids,
        base=base,
        ref_bus=ref_bus,
        z_vars=z_vars,
        max_open=max_open,
        force_all_closed=force_all_closed,
        has_quad=has_quad,
        theta=theta,
        Pg=Pg,
        f=f,
        extra={"problem": "dcopf" if force_all_closed else "dcots"},
    )


# ---------------------------------------------------------------------------
# solve_scots (preventive N-1 SC-OTS)
# ---------------------------------------------------------------------------

def solve_scots(
    network: dict,
    config: dict,
    *,
    force_all_closed: bool = False,
    quiet: bool = True,
) -> dict[str, Any]:
    """Preventive SC-OTS: shared topology z, base rateA, contingency rateC.

    Redispatch: |Pg_c - Pg_0| <= redispatch_frac * (Pmax - Pmin) for online gens.
    No load shedding. Connectivity enforced in every state.
    force_all_closed=True yields all-lines-closed SCOPF (same contingencies).
    """
    validate_network(network, config)

    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = _bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)

    switchable = _switchable_set(config, force_all_closed)
    max_open = 0 if force_all_closed else int(config.get("max_open", 0))
    redispatch_frac = float(config.get("redispatch_frac", 0.2))
    cont_ids = _contingency_list(network, config)
    Pd = {int(b["bus_i"]): float(b["Pd"]) / base for b in buses}

    m = gp.Model("scopf" if force_all_closed else "scots")
    _solver_params(m, config, quiet)

    # Shared topology
    z_vars: dict[int, gp.Var] = {}
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        if bid in switchable and int(br["status"]) == 1:
            z_vars[ell] = m.addVar(vtype=GRB.BINARY, name=f"z_{bid}")

    fixed_open = {int(i) for i in config.get("fixed_open_idx", []) or []}
    for ell, z in z_vars.items():
        if int(branches[ell]["id"]) in fixed_open:
            m.addConstr(z == 0.0, name=f"fixed_open_{int(branches[ell]['id'])}")

    if z_vars and max_open < len(z_vars):
        m.addConstr(
            gp.quicksum(1 - z for z in z_vars.values()) <= max_open, name="max_open"
        )

    # ---- base state ----
    theta0 = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta0")
    Pg0 = m.addVars(nG, name="Pg0")
    f0 = m.addVars(nL, lb=-GRB.INFINITY, name="f0")
    m.addConstr(theta0[bus_pos[ref_bus]] == 0.0, name="ref0")

    for g, gen in enumerate(gens):
        pmin, pmax = _gen_bounds_pu(gen, base)
        Pg0[g].LB = pmin
        Pg0[g].UB = pmax

    has_quad = _add_objective(m, Pg0, gens, base)

    for ell, br in enumerate(branches):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        _add_branch_state(
            m,
            state="base",
            ell=ell,
            br=br,
            theta_i=theta0[i],
            theta_j=theta0[j],
            f=f0[ell],
            z=z_vars.get(ell),
            outaged=False,
            base=base,
            contingency=False,
        )
    _add_power_balance(
        m, state="base", bus_ids=bus_ids, gens=gens, branches=branches, Pg=Pg0, f=f0, Pd=Pd
    )
    _add_connectivity(
        m,
        state="base",
        nB=nB,
        nL=nL,
        branches=branches,
        bus_ids=bus_ids,
        bus_pos=bus_pos,
        ref_bus=ref_bus,
        z_vars=z_vars,
        outaged_ids=set(),
    )

    # ---- contingency states ----
    cont_Pg: dict[int, gp.tupledict] = {}
    cont_theta: dict[int, gp.tupledict] = {}
    cont_f: dict[int, gp.tupledict] = {}

    for cid in cont_ids:
        tag = f"c{cid}"
        theta_c = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f"theta_{tag}")
        Pg_c = m.addVars(nG, name=f"Pg_{tag}")
        f_c = m.addVars(nL, lb=-GRB.INFINITY, name=f"f_{tag}")
        cont_theta[cid] = theta_c
        cont_Pg[cid] = Pg_c
        cont_f[cid] = f_c

        m.addConstr(theta_c[bus_pos[ref_bus]] == 0.0, name=f"ref_{tag}")

        for g, gen in enumerate(gens):
            pmin, pmax = _gen_bounds_pu(gen, base)
            Pg_c[g].LB = pmin
            Pg_c[g].UB = pmax
            # redispatch band around base dispatch
            span = pmax - pmin
            band = redispatch_frac * span
            m.addConstr(Pg_c[g] - Pg0[g] <= band, name=f"rd_up_{tag}_{g}")
            m.addConstr(Pg0[g] - Pg_c[g] <= band, name=f"rd_dn_{tag}_{g}")

        outaged = {int(cid)}
        for ell, br in enumerate(branches):
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            _add_branch_state(
                m,
                state=tag,
                ell=ell,
                br=br,
                theta_i=theta_c[i],
                theta_j=theta_c[j],
                f=f_c[ell],
                z=z_vars.get(ell),
                outaged=(int(br["id"]) in outaged),
                base=base,
                contingency=True,
            )
        _add_power_balance(
            m,
            state=tag,
            bus_ids=bus_ids,
            gens=gens,
            branches=branches,
            Pg=Pg_c,
            f=f_c,
            Pd=Pd,
        )
        _add_connectivity(
            m,
            state=tag,
            nB=nB,
            nL=nL,
            branches=branches,
            bus_ids=bus_ids,
            bus_pos=bus_pos,
            ref_bus=ref_bus,
            z_vars=z_vars,
            outaged_ids=outaged,
        )

    t0 = time.time()
    m.optimize()

    reported_metrics: dict[str, Any] | None = None
    canonicalize = bool(config.get("canonicalize_contingencies", False)) and bool(cont_ids)
    tie_break_status = "NOT_REQUESTED"
    if canonicalize and m.Status == GRB.OPTIMAL and m.SolCount > 0:
        reported_metrics = {
            "status": _status_name(m),
            "obj": float(m.ObjVal),
            "obj_bound": float(m.ObjBound) if hasattr(m, "ObjBound") else float(m.ObjVal),
            "mip_gap": float(m.MIPGap) if m.IsMIP else 0.0,
        }
        primary_pg = [float(Pg0[g].X) for g in range(nG)]
        primary_z = {ell: int(round(float(z.X))) for ell, z in z_vars.items()}
        for g, value in enumerate(primary_pg):
            m.addConstr(Pg0[g] == value, name=f"canonical_fix_Pg0_{g}")
        for ell, value in primary_z.items():
            m.addConstr(z_vars[ell] == value, name=f"canonical_fix_z_{ell}")

        secondary = gp.QuadExpr()
        for cid in cont_ids:
            for g in range(nG):
                secondary += cont_Pg[cid][g] * cont_Pg[cid][g]
        m.setObjective(secondary, GRB.MINIMIZE)
        m.Params.FeasibilityTol = 1e-9
        m.Params.OptimalityTol = 1e-9
        m.Params.BarConvTol = 1e-10
        m.optimize()
        tie_break_status = _status_name(m)
        if m.Status != GRB.OPTIMAL or m.SolCount == 0:
            raise RuntimeError(
                "post-optimal contingency tie-break failed: "
                f"status={tie_break_status}"
            )

    runtime = time.time() - t0

    sol = _pack_solution(
        m=m,
        runtime=runtime,
        branches=branches,
        gens=gens,
        bus_ids=bus_ids,
        base=base,
        ref_bus=ref_bus,
        z_vars=z_vars,
        max_open=max_open,
        force_all_closed=force_all_closed,
        has_quad=has_quad,
        theta=theta0,
        Pg=Pg0,
        f=f0,
        extra={
            "problem": "scopf" if force_all_closed else "scots",
            "redispatch_frac": redispatch_frac,
            "contingency_ids": cont_ids,
            "contingency_solution_selection": (
                "post_optimal_min_sum_squared_dispatch"
                if canonicalize
                else "primary_solver_solution"
            ),
            "tie_break_status": tie_break_status,
        },
        reported_metrics=reported_metrics,
    )

    # Attach per-contingency dispatches when solved
    if m.SolCount > 0:
        cont_out = {}
        for cid in cont_ids:
            cont_out[str(cid)] = {
                "outaged_branch": cid,
                "Pg_MW": [float(cont_Pg[cid][g].X) * base for g in range(nG)],
                "theta_deg": [
                    math.degrees(float(cont_theta[cid][i].X)) for i in range(nB)
                ],
                "flow_MW": [float(cont_f[cid][ell].X) * base for ell in range(nL)],
            }
        sol["contingency_solutions"] = cont_out
    else:
        sol["contingency_solutions"] = {}

    return sol


# ---------------------------------------------------------------------------
# run_case + schema v2
# ---------------------------------------------------------------------------

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


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    """Load case, solve baseline + OTS/SC-OTS, validate residuals, write schema v2 JSON.

    For problem=scots the baseline is all-lines-closed SCOPF with the same
    contingencies (not ordinary DCOPF). Stored under the historical key 'dcopf'.
    """
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    problem = str(config.get("problem", "dcots")).lower()
    if problem == "dcopf":
        problem = "dcots"

    if problem == "scots":
        dcopf = solve_scots(network, config, force_all_closed=True, quiet=quiet)
        ots = solve_scots(network, config, force_all_closed=False, quiet=quiet)
    else:
        dcopf = solve_dcots(network, config, force_all_closed=True, quiet=quiet)
        ots = solve_dcots(network, config, force_all_closed=False, quiet=quiet)

    result = build_result_v2(
        case_dir=case_dir,
        network=network,
        config=config,
        dcopf=dcopf,
        ots=ots,
        problem=problem,
    )

    # Independent residual validation on both solutions
    result["validation"] = {
        "dcopf": validate_solution_bundle(
            network,
            config,
            dcopf,
            state="scopf" if problem == "scots" else "dcopf",
            contingencies=dcopf.get("contingency_solutions"),
        ),
        "ots": validate_solution_bundle(
            network,
            config,
            ots,
            state=problem,
            contingencies=ots.get("contingency_solutions"),
        ),
    }

    out = case_dir / "results" / "python_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


def discover_cases(root: str | Path | None = None) -> list[str]:
    """Discover case directories containing network.json and config.json."""
    root = Path(root) if root else Path(__file__).resolve().parent
    names = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "network.json").is_file() and (p / "config.json").is_file():
            names.append(p.name)
    return names
