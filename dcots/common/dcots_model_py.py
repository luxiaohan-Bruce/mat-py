"""DC-OTS MILP (gurobipy).

Formulation highlights (matched in MATLAB dcots_model_mat.m):
  - DC branch: f = b (θ_f - θ_t - φ), b = 1/(x·tap), tap=1 if ratio==0
  - Switching via Gurobi indicator constraints (no big-M / global Δθ boxes)
  - Conditional MATPOWER angle limits only when a branch is effectively closed
  - Signed single-commodity connectivity
  - Objective costs only for online generators (status==1)

SC-OTS lives in scots_model_py.py (separate package under scots_cases/).
"""

from __future__ import annotations

import json
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
    discover_cases,
    gen_bounds_pu,
    load_case,
    pack_solution,
    solver_params,
    switchable_set,
)
from validate_data import validate_network
from validate_residuals import validate_solution_bundle

# Re-export for callers / builders that import from this module
__all__ = [
    "discover_cases",
    "load_case",
    "run_case",
    "solve_dcots",
]


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
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)

    switchable = switchable_set(config, force_all_closed)
    max_open = 0 if force_all_closed else int(config.get("max_open", 0))
    Pd = {int(b["bus_i"]): float(b["Pd"]) / base for b in buses}

    m = gp.Model("dcots")
    solver_params(m, config, quiet)

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
        pmin, pmax = gen_bounds_pu(gen, base)
        Pg[g].LB = pmin
        Pg[g].UB = pmax

    has_quad = add_objective(m, Pg, gens, base)

    for ell, br in enumerate(branches):
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        add_branch_state(
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

    add_power_balance(
        m, state="base", bus_ids=bus_ids, gens=gens, branches=branches, Pg=Pg, f=f, Pd=Pd
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

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0

    return pack_solution(
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


def run_case(case_dir: str | Path, quiet: bool = True) -> dict[str, Any]:
    """Load DC-OTS case, solve DCOPF baseline + OTS, validate, write JSON."""
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    problem = str(config.get("problem", "dcots")).lower()
    if problem == "dcopf":
        problem = "dcots"
    if problem == "scots":
        raise ValueError(
            f"{case_dir.name}: problem=scots belongs in scots_cases "
            "(use scots_model_py.run_case)"
        )

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

    result["validation"] = {
        "dcopf": validate_solution_bundle(
            network,
            config,
            dcopf,
            state="dcopf",
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
