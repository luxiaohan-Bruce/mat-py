"""Preventive SC-OTS MILP (gurobipy).

Formulation highlights (matched in MATLAB dcots_model_mat.m solve_scots_mat):
  - Shared topology z across base and all N-1 contingency states
  - Base thermal limits rateA; contingency limits rateC
  - Post-contingency redispatch band; no load shedding
  - Connectivity in every operating state
  - Optional post-optimal strictly-convex tie-break for contingency dispatch

DC-OTS lives in dcots_model_py.py.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

from ots_common_py import (
    add_branch_state,
    add_connectivity,
    add_objective,
    add_power_balance,
    build_result_v2,
    bus_maps,
    contingency_list,
    discover_cases,
    gen_bounds_pu,
    load_case,
    pack_solution,
    solver_params,
    status_name,
    switchable_set,
)
from validate_data import validate_network
from validate_residuals import validate_solution_bundle

__all__ = [
    "discover_cases",
    "load_case",
    "run_case",
    "solve_scots",
]


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
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)

    switchable = switchable_set(config, force_all_closed)
    max_open = 0 if force_all_closed else int(config.get("max_open", 0))
    redispatch_frac = float(config.get("redispatch_frac", 0.2))
    cont_ids = contingency_list(network, config)
    Pd = {int(b["bus_i"]): float(b["Pd"]) / base for b in buses}

    m = gp.Model("scopf" if force_all_closed else "scots")
    solver_params(m, config, quiet)

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
        pmin, pmax = gen_bounds_pu(gen, base)
        Pg0[g].LB = pmin
        Pg0[g].UB = pmax

    has_quad = add_objective(m, Pg0, gens, base)

    for ell, br in enumerate(branches):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        add_branch_state(
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
    add_power_balance(
        m, state="base", bus_ids=bus_ids, gens=gens, branches=branches, Pg=Pg0, f=f0, Pd=Pd
    )
    add_connectivity(
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
            pmin, pmax = gen_bounds_pu(gen, base)
            Pg_c[g].LB = pmin
            Pg_c[g].UB = pmax
            span = pmax - pmin
            band = redispatch_frac * span
            m.addConstr(Pg_c[g] - Pg0[g] <= band, name=f"rd_up_{tag}_{g}")
            m.addConstr(Pg0[g] - Pg_c[g] <= band, name=f"rd_dn_{tag}_{g}")

        outaged = {int(cid)}
        for ell, br in enumerate(branches):
            i = bus_pos[int(br["fbus"])]
            j = bus_pos[int(br["tbus"])]
            add_branch_state(
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
        add_power_balance(
            m,
            state=tag,
            bus_ids=bus_ids,
            gens=gens,
            branches=branches,
            Pg=Pg_c,
            f=f_c,
            Pd=Pd,
        )
        add_connectivity(
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
            "status": status_name(m),
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
        tie_break_status = status_name(m)
        if m.Status != GRB.OPTIMAL or m.SolCount == 0:
            raise RuntimeError(
                "post-optimal contingency tie-break failed: "
                f"status={tie_break_status}"
            )

    runtime = time.time() - t0

    sol = pack_solution(
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


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    """Load SC-OTS case, solve SCOPF baseline + SC-OTS, validate, write JSON.

    Baseline is all-lines-closed SCOPF with the same contingencies (not DCOPF).
    Stored under the historical key 'dcopf'.
    """
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    problem = str(config.get("problem", "scots")).lower()
    if problem != "scots":
        raise ValueError(
            f"{case_dir.name}: expected problem=scots, got {problem!r} "
            "(use dcots_model_py.run_case for DC-OTS)"
        )

    dcopf = solve_scots(network, config, force_all_closed=True, quiet=quiet)
    ots = solve_scots(network, config, force_all_closed=False, quiet=quiet)

    result = build_result_v2(
        case_dir=case_dir,
        network=network,
        config=config,
        dcopf=dcopf,
        ots=ots,
        problem=problem,
    )

    result["validation"] = {
        "dcopf": validate_solution_bundle(
            network,
            config,
            dcopf,
            state="scopf",
            contingencies=dcopf.get("contingency_solutions"),
        ),
        "ots": validate_solution_bundle(
            network,
            config,
            ots,
            state="scots",
            contingencies=ots.get("contingency_solutions"),
        ),
    }

    out = case_dir / "results" / "python_result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result
