"""N-k Network Interdiction (attacker–operator max–min).

Attacker disables up to k online lines (and optionally gens).
Operator solves DC load-shedding LP (min unserved MW) on the residual network.

Methods:
  enumeration — exact: all attack sets of size ≤k (practical for k=1 or small C(n,k))
  bilevel_milp — single-level MILP via operator dual + indicators / strong duality
  heuristic   — ranked single-line + top-pair / seeded random pairs (documented)
  auto        — enum; also milp when n_bus<=14 and k=1 for oracle match check
"""

from __future__ import annotations

import itertools
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

import gurobipy as gp
from gurobipy import GRB

# common_protocol helpers vendored in this common/ directory
from dc_network import (  # noqa: E402
    bus_maps,
    branch_susceptance,
    is_zero_x,
    thermal_rate_mw,
)
from result_io import load_case, write_result  # noqa: E402
from tolerances import DEFAULT_TOLERANCES, solver_params_from_config  # noqa: E402


def _status_name(m: gp.Model) -> str:
    return {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }.get(m.Status, str(m.Status))


def _online_lines(network: dict) -> list[int]:
    return [
        ell
        for ell, br in enumerate(network["branches"])
        if int(br.get("status", 1)) == 1
    ]


def _online_gens(network: dict) -> list[int]:
    return [
        g
        for g, gen in enumerate(network["gens"])
        if int(gen.get("status", 1)) == 1
    ]


def solve_operator_lp(
    network: dict,
    *,
    disabled_lines: set[int] | list[int] | None = None,
    disabled_gens: set[int] | list[int] | None = None,
    quiet: bool = True,
    params: dict | None = None,
) -> dict[str, Any]:
    """Min load-shed DC LP on residual network. Lines/gens by 0-based index."""
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    dL = set(int(x) for x in (disabled_lines or []))
    dG = set(int(x) for x in (disabled_gens or []))

    m = gp.Model("op_load_shed")
    if quiet:
        m.Params.OutputFlag = 0
    if params:
        m.Params.Seed = int(params.get("Seed", 1))
        m.Params.Threads = int(params.get("Threads", 1))
        m.Params.TimeLimit = float(params.get("TimeLimit", 300))

    theta = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="theta")
    Pg = m.addVars(nG, lb=0.0, name="Pg")
    f = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="f")
    s = m.addVars(nB, lb=0.0, name="shed")

    m.addConstr(theta[bus_pos[ref_bus]] == 0.0, name="ref")

    for g, gen in enumerate(gens):
        if g in dG or int(gen.get("status", 1)) == 0:
            Pg[g].UB = 0.0
        else:
            Pg[g].UB = float(gen["Pmax"])

    for bi in range(nB):
        s[bi].UB = max(0.0, float(buses[bi]["Pd"]))

    for ell, br in enumerate(branches):
        offline = int(br.get("status", 1)) == 0 or ell in dL
        if offline:
            m.addConstr(f[ell] == 0.0, name=f"f0_{ell}")
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            m.addConstr(theta[i] - theta[j] == phi, name=f"th_{ell}")
        else:
            bsus, phi = branch_susceptance(br)
            m.addConstr(
                f[ell] == base * bsus * (theta[i] - theta[j] - phi),
                name=f"phys_{ell}",
            )
        rate = thermal_rate_mw(br)
        if rate > 0:
            m.addConstr(f[ell] <= rate, name=f"fmax_{ell}")
            m.addConstr(f[ell] >= -rate, name=f"fmin_{ell}")

    for bi, bid in enumerate(bus_ids):
        Pd = float(buses[bi]["Pd"])
        gen_sum = gp.quicksum(Pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        out_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        in_f = gp.quicksum(f[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        m.addConstr(gen_sum - out_f + in_f + s[bi] == Pd, name=f"bal_{bid}")

    m.setObjective(gp.quicksum(s[bi] for bi in range(nB)), GRB.MINIMIZE)
    m.optimize()

    shed = 0.0
    Pg_MW = [0.0] * nG
    theta_deg = [0.0] * nB
    flow_MW = [0.0] * nL
    s_MW = [0.0] * nB
    status = _status_name(m)
    if m.SolCount > 0:
        shed = float(m.ObjVal)
        for g in range(nG):
            Pg_MW[g] = float(Pg[g].X)
        for i in range(nB):
            theta_deg[i] = math.degrees(float(theta[i].X))
            s_MW[i] = float(s[i].X)
        for ell in range(nL):
            flow_MW[ell] = float(f[ell].X)

    residual = _validate_operator(network, dL, dG, Pg_MW, theta_deg, flow_MW, s_MW)
    return {
        "status": status,
        "shed_MW": shed,
        "Pg_MW": Pg_MW,
        "theta_deg": theta_deg,
        "flow_MW": flow_MW,
        "shed_bus_MW": s_MW,
        **residual,
    }


def _validate_operator(
    network: dict,
    dL: set[int],
    dG: set[int],
    Pg_MW: list[float],
    theta_deg: list[float],
    flow_MW: list[float],
    s_MW: list[float],
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, _ = bus_maps(network)
    tol = DEFAULT_TOLERANCES
    th = [math.radians(v) for v in theta_deg]

    max_bal = 0.0
    for bi, bid in enumerate(bus_ids):
        gs = sum(Pg_MW[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        of = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid)
        inf = sum(flow_MW[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid)
        max_bal = max(max_bal, abs(gs - of + inf + s_MW[bi] - float(buses[bi]["Pd"])))

    max_flow_eq = 0.0
    max_thermal = 0.0
    max_atk_flow = 0.0
    for ell, br in enumerate(branches):
        offline = int(br.get("status", 1)) == 0 or ell in dL
        if offline:
            max_atk_flow = max(max_atk_flow, abs(flow_MW[ell]))
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        if is_zero_x(br):
            _, phi = branch_susceptance(br)
            max_flow_eq = max(max_flow_eq, abs(th[i] - th[j] - phi) * base)
        else:
            bsus, phi = branch_susceptance(br)
            exp = base * bsus * (th[i] - th[j] - phi)
            max_flow_eq = max(max_flow_eq, abs(flow_MW[ell] - exp))
        rate = thermal_rate_mw(br)
        if rate > 0:
            max_thermal = max(max_thermal, max(0.0, abs(flow_MW[ell]) - rate))

    max_gen = 0.0
    for g, gen in enumerate(gens):
        offline = g in dG or int(gen.get("status", 1)) == 0
        p = Pg_MW[g]
        if offline:
            max_gen = max(max_gen, abs(p))
        else:
            max_gen = max(max_gen, max(0.0, -p), max(0.0, p - float(gen["Pmax"])))

    for bi in range(len(buses)):
        max_gen = max(max_gen, max(0.0, -s_MW[bi]), max(0.0, s_MW[bi] - max(0.0, float(buses[bi]["Pd"]))))

    passed = (
        max_bal <= tol["power_balance_mw"]
        and max_flow_eq <= tol["flow_equation_mw"]
        and max_thermal <= tol["thermal_mw"]
        and max_atk_flow <= tol["thermal_mw"]
        and max_gen <= tol["generator_bound_mw"]
    )
    return {
        "max_power_balance_MW": max_bal,
        "max_flow_equation_MW": max_flow_eq,
        "max_thermal_violation_MW": max_thermal,
        "max_attacked_flow_MW": max_atk_flow,
        "max_generator_bound_MW": max_gen,
        "operator_validation_passed": passed,
    }


def solve_enumeration(
    network: dict,
    config: dict,
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    """Exact max load-shed over all attack combinations of size 1..k (default exact size k)."""
    params = solver_params_from_config(config)
    k = int(config.get("k", 1))
    attack_target = str(config.get("attack_target", "lines"))
    # attack_size_mode: "exact" (size=k) or "upto" (size<=k)
    size_mode = str(config.get("attack_size_mode", "exact"))

    lines = _online_lines(network)
    gens = _online_gens(network)
    if attack_target == "gens":
        candidates = [("g", g) for g in gens]
    elif attack_target == "lines_and_gens":
        candidates = [("l", ell) for ell in lines] + [("g", g) for g in gens]
    else:
        candidates = [("l", ell) for ell in lines]

    n_cand = len(candidates)
    if n_cand == 0:
        op0 = solve_operator_lp(network, quiet=quiet, params=params)
        return _pack_result(
            network,
            config,
            method="enumeration",
            status="OPTIMAL",
            obj=op0["shed_MW"],
            attacked_lines=[],
            attacked_gens=[],
            op=op0,
            n_enum=1,
            runtime=0.0,
            notes="no attack candidates",
        )

    sizes = range(1, k + 1) if size_mode == "upto" else [k]
    t0 = time.time()
    best_shed = -1.0
    best_lines: list[int] = []
    best_gens: list[int] = []
    best_op: dict[str, Any] | None = None
    n_enum = 0
    # baseline (no attack) for reporting
    op_base = solve_operator_lp(network, quiet=quiet, params=params)
    baseline = float(op_base["shed_MW"])

    for sz in sizes:
        if sz > n_cand:
            continue
        for combo in itertools.combinations(candidates, sz):
            dL: set[int] = set()
            dG: set[int] = set()
            for kind, idx in combo:
                if kind == "l":
                    dL.add(idx)
                else:
                    dG.add(idx)
            op = solve_operator_lp(
                network, disabled_lines=dL, disabled_gens=dG, quiet=quiet, params=params
            )
            n_enum += 1
            sh = float(op["shed_MW"])
            if sh > best_shed + 1e-9:
                best_shed = sh
                best_lines = sorted(dL)
                best_gens = sorted(dG)
                best_op = op
            elif abs(sh - best_shed) <= 1e-9:
                # tie-break: lexicographically smallest attack (reproducible)
                key = (tuple(sorted(dL)), tuple(sorted(dG)))
                cur = (tuple(best_lines), tuple(best_gens))
                if key < cur:
                    best_lines = sorted(dL)
                    best_gens = sorted(dG)
                    best_op = op

    runtime = time.time() - t0
    if best_op is None:
        best_shed = baseline
        best_op = op_base

    return _pack_result(
        network,
        config,
        method="enumeration",
        status="OPTIMAL" if best_op.get("status") == "OPTIMAL" else best_op.get("status", "OPTIMAL"),
        obj=best_shed,
        attacked_lines=best_lines,
        attacked_gens=best_gens,
        op=best_op,
        n_enum=n_enum,
        runtime=runtime,
        baseline_shed_MW=baseline,
        notes=f"enumerated {n_enum} attacks, k={k}, target={attack_target}",
    )


def solve_bilevel_milp(
    network: dict,
    config: dict,
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    """Single-level MILP: max dual of operator LP with attack binaries (lines).

    Uses Gurobi indicator constraints for attack-dependent dual feasibility.
    Gen attacks not included in MILP v1 (use enumeration).
    """
    params = solver_params_from_config(config)
    k = int(config.get("k", 1))
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids, bus_pos, ref_bus = bus_maps(network)
    nB, nG, nL = len(bus_ids), len(gens), len(branches)
    online = _online_lines(network)
    offline0 = [ell for ell in range(nL) if ell not in set(online)]

    # Skip zero-x lines as attack candidates in MILP (rare); still force offline status
    attackable = [ell for ell in online if not is_zero_x(branches[ell])]
    zero_online = [ell for ell in online if is_zero_x(branches[ell])]

    m = gp.Model("interdiction_dual_milp")
    if quiet:
        m.Params.OutputFlag = 0
    m.Params.Seed = params["Seed"]
    m.Params.Threads = params["Threads"]
    m.Params.MIPGap = params["MIPGap"]
    m.Params.TimeLimit = params["TimeLimit"]

    # Attack binaries
    delta = m.addVars(attackable, vtype=GRB.BINARY, name="delta")
    m.addConstr(gp.quicksum(delta[ell] for ell in attackable) <= k, name="budget")

    # Dual vars
    lam = m.addVars(nB, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="lam")  # balance
    mu = m.addVars(nL, lb=-GRB.INFINITY, ub=GRB.INFINITY, name="mu")  # physics
    ap = m.addVars(nL, lb=0.0, name="ap")  # thermal +
    am = m.addVars(nL, lb=0.0, name="am")  # thermal -
    u = m.addVars(nG, lb=0.0, name="u")  # gen upper
    v = m.addVars(nB, lb=0.0, name="v")  # shed upper

    # Bound dual vars mildly for numerics (load-shed dual typically O(1))
    LAM_M = 1e3
    for i in range(nB):
        lam[i].LB = -LAM_M
        lam[i].UB = LAM_M
    for ell in range(nL):
        mu[ell].LB = -LAM_M
        mu[ell].UB = LAM_M
        ap[ell].UB = LAM_M
        am[ell].UB = LAM_M

    # Dual of s_i: λ_i - v_i ≤ 1
    for i in range(nB):
        m.addConstr(lam[i] - v[i] <= 1.0, name=f"ds_{i}")

    # Dual of Pg_g: λ_bus - u_g ≤ 0 (online gens only; offline Pmax=0 → drop)
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 0:
            m.addConstr(u[g] == 0.0, name=f"u0_{g}")
            continue
        bi = bus_pos[int(gen["bus"])]
        m.addConstr(lam[bi] - u[g] <= 0.0, name=f"dPg_{g}")

    # Dual of θ: for i ≠ ref, sum incidence * β * μ = 0
    # When line attacked, μ=0 so it drops out.
    beta = [0.0] * nL
    phi = [0.0] * nL
    rate = [0.0] * nL
    for ell, br in enumerate(branches):
        if is_zero_x(br):
            _, phi[ell] = branch_susceptance(br)
            beta[ell] = 0.0
        else:
            bsus, phi[ell] = branch_susceptance(br)
            beta[ell] = base * bsus
        rate[ell] = thermal_rate_mw(br)

    for bi, bid in enumerate(bus_ids):
        if bid == ref_bus:
            continue
        expr = gp.LinExpr()
        for ell, br in enumerate(branches):
            if ell in offline0:
                continue
            if is_zero_x(br):
                continue
            if int(br["fbus"]) == bid:
                expr += -beta[ell] * mu[ell]
            if int(br["tbus"]) == bid:
                expr += beta[ell] * mu[ell]
        m.addConstr(expr == 0.0, name=f"dth_{bid}")

    # Dual of f and attack-dependent activation via indicators
    for ell, br in enumerate(branches):
        if ell in offline0:
            m.addConstr(mu[ell] == 0.0)
            m.addConstr(ap[ell] == 0.0)
            m.addConstr(am[ell] == 0.0)
            continue
        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        # dual of f when line online: -λ_i + λ_j + μ + ap - am = 0
        # (balance contributes -λ_fbus + λ_tbus; physics contributes μ; thermal ap-am)
        df = -lam[i] + lam[j] + mu[ell] + ap[ell] - am[ell]
        if ell in zero_online:
            # never attacked in MILP; always online; zero-x: no μ physics on f
            # dual of f: -λ_i + λ_j + ap - am = 0, mu free unused → set mu=0
            m.addConstr(mu[ell] == 0.0)
            m.addConstr(-lam[i] + lam[j] + ap[ell] - am[ell] == 0.0, name=f"df_{ell}")
            if rate[ell] <= 0:
                m.addConstr(ap[ell] == 0.0)
                m.addConstr(am[ell] == 0.0)
            continue
        # attackable
        # When delta=0 (online): enforce dual-f and allow mu,ap,am
        # When delta=1 (attacked): force mu=ap=am=0 (no dual-f needed)
        m.addGenConstrIndicator(delta[ell], False, df == 0.0, name=f"ind_df_{ell}")
        m.addGenConstrIndicator(delta[ell], True, mu[ell] == 0.0, name=f"ind_mu0_{ell}")
        m.addGenConstrIndicator(delta[ell], True, ap[ell] == 0.0, name=f"ind_ap0_{ell}")
        m.addGenConstrIndicator(delta[ell], True, am[ell] == 0.0, name=f"ind_am0_{ell}")
        if rate[ell] <= 0:
            # no thermal dual when unconstrained; still need dual-f with ap=am=0 when online
            m.addGenConstrIndicator(delta[ell], False, ap[ell] == 0.0)
            m.addGenConstrIndicator(delta[ell], False, am[ell] == 0.0)

    # Dual objective: max ∑ Pd λ - ∑ Pmax u - ∑ Pd v - ∑ R(ap+am) - ∑ β φ μ
    # Primal physics: f - β(θf-θt-φ)=0 ⇒ f - βθf + βθt = -βφ, dual μ, rhs contrib μ*(-βφ)?
    # Constraint written as f - β(θf-θt-φ) = 0 ⇒ rhs=0, no phi in dual obj from that form.
    # Use: f - β(θf-θt) + βφ = 0, dual μ, rhs=0 still if absorbed in const...
    # Primal in solve_operator: f = β(θf-θt-φ) ⇒ f - βθf + βθt + βφ = 0
    # dual obj contribution from equality Ax=0 is 0. Phi is in matrix not rhs.
    # Dual of θ already uses β μ; dual of f uses μ. No explicit phi dual obj term if rhs=0.
    # BUT: constraint f - βθf + βθt = -βφ has rhs=-βφ → dual obj += μ*(-βφ)
    dual_obj = gp.LinExpr()
    for bi in range(nB):
        Pd = float(buses[bi]["Pd"])
        dual_obj += Pd * lam[bi]
        dual_obj -= Pd * v[bi]
    for g, gen in enumerate(gens):
        if int(gen.get("status", 1)) == 1:
            dual_obj -= float(gen["Pmax"]) * u[g]
    for ell in attackable:
        if rate[ell] > 0:
            dual_obj -= rate[ell] * (ap[ell] + am[ell])
        # rhs of physics f-β(θf-θt)=-βφ → contrib μ * (-βφ)
        dual_obj += mu[ell] * (-beta[ell] * phi[ell])
    for ell in zero_online:
        if rate[ell] > 0:
            dual_obj -= rate[ell] * (ap[ell] + am[ell])

    m.setObjective(dual_obj, GRB.MAXIMIZE)

    t0 = time.time()
    m.optimize()
    runtime = time.time() - t0
    status = _status_name(m)

    attacked_lines: list[int] = []
    obj = None
    obj_bound = None
    mip_gap = 0.0
    if m.SolCount > 0:
        obj = float(m.ObjVal)
        try:
            obj_bound = float(m.ObjBound)
        except Exception:
            obj_bound = obj
        try:
            mip_gap = float(m.MIPGap)
        except Exception:
            mip_gap = 0.0
        for ell in attackable:
            if float(delta[ell].X) > 0.5:
                attacked_lines.append(ell)
        attacked_lines.sort()

    # Re-solve operator on attack for primal residual / exact shed
    op = solve_operator_lp(
        network,
        disabled_lines=attacked_lines,
        quiet=quiet,
        params=params,
    )
    # Prefer operator shed as reported obj when dual/primal match; keep dual_obj too
    dual_obj_val = obj
    primal_shed = float(op["shed_MW"])
    if dual_obj_val is not None and abs(dual_obj_val - primal_shed) > max(0.01, 1e-4 * max(1.0, abs(primal_shed))):
        # dual gap / formulation residual — still report both
        pass

    return _pack_result(
        network,
        config,
        method="bilevel_milp",
        status=status,
        obj=primal_shed if op.get("status") == "OPTIMAL" else dual_obj_val,
        attacked_lines=attacked_lines,
        attacked_gens=[],
        op=op,
        n_enum=0,
        runtime=runtime,
        dual_obj=dual_obj_val,
        obj_bound=obj_bound,
        mip_gap=mip_gap,
        notes="single-level dual MILP (line attacks); obj=operator re-eval shed",
    )


def solve_heuristic(
    network: dict,
    config: dict,
    *,
    quiet: bool = True,
) -> dict[str, Any]:
    """Heuristic worst attack for larger k: rank single-line, then top pairs / random pairs."""
    params = solver_params_from_config(config)
    k = int(config.get("k", 2))
    seed = int(config.get("seed", params.get("Seed", 1)))
    top_m = int(config.get("heuristic_top", 25))
    n_random = int(config.get("heuristic_random_pairs", 200))
    lines = _online_lines(network)
    t0 = time.time()

    # rank single-line
    scores: list[tuple[float, int]] = []
    for ell in lines:
        op = solve_operator_lp(network, disabled_lines={ell}, quiet=quiet, params=params)
        scores.append((float(op["shed_MW"]), ell))
    scores.sort(key=lambda t: (-t[0], t[1]))

    best_shed = scores[0][0] if scores else 0.0
    best_lines = [scores[0][1]] if scores else []
    best_op = solve_operator_lp(
        network, disabled_lines=set(best_lines), quiet=quiet, params=params
    ) if best_lines else solve_operator_lp(network, quiet=quiet, params=params)
    n_eval = len(lines)

    if k >= 2 and len(lines) >= 2:
        top = [ell for _, ell in scores[: min(top_m, len(scores))]]
        # all pairs in top
        for a, b in itertools.combinations(top, 2):
            op = solve_operator_lp(
                network, disabled_lines={a, b}, quiet=quiet, params=params
            )
            n_eval += 1
            sh = float(op["shed_MW"])
            if sh > best_shed + 1e-9 or (
                abs(sh - best_shed) <= 1e-9 and tuple(sorted([a, b])) < tuple(best_lines)
            ):
                best_shed = sh
                best_lines = sorted([a, b])
                best_op = op
        # seeded random pairs outside pure top-only if needed
        rng = random.Random(seed)
        if len(lines) > 2:
            for _ in range(n_random):
                a, b = rng.sample(lines, 2)
                if a > b:
                    a, b = b, a
                op = solve_operator_lp(
                    network, disabled_lines={a, b}, quiet=quiet, params=params
                )
                n_eval += 1
                sh = float(op["shed_MW"])
                if sh > best_shed + 1e-9 or (
                    abs(sh - best_shed) <= 1e-9
                    and tuple(sorted([a, b])) < tuple(best_lines)
                ):
                    best_shed = sh
                    best_lines = sorted([a, b])
                    best_op = op

    # if k==1 only top single
    if k == 1 and scores:
        best_shed = scores[0][0]
        best_lines = [scores[0][1]]
        best_op = solve_operator_lp(
            network, disabled_lines=set(best_lines), quiet=quiet, params=params
        )

    runtime = time.time() - t0
    return _pack_result(
        network,
        config,
        method="heuristic",
        status="OPTIMAL" if best_op.get("status") == "OPTIMAL" else best_op.get("status"),
        obj=best_shed,
        attacked_lines=best_lines,
        attacked_gens=[],
        op=best_op,
        n_enum=n_eval,
        runtime=runtime,
        notes=f"heuristic top_m={top_m} random_pairs={n_random} seed={seed}; not exact",
    )


def _pack_result(
    network: dict,
    config: dict,
    *,
    method: str,
    status: str,
    obj: float | None,
    attacked_lines: list[int],
    attacked_gens: list[int],
    op: dict[str, Any],
    n_enum: int,
    runtime: float,
    notes: str = "",
    dual_obj: float | None = None,
    obj_bound: float | None = None,
    mip_gap: float = 0.0,
    baseline_shed_MW: float | None = None,
) -> dict[str, Any]:
    total_pd = sum(float(b["Pd"]) for b in network["buses"])
    # branch ids for human-readable attack list
    br_ids = []
    for ell in attacked_lines:
        br = network["branches"][ell]
        br_ids.append(int(br.get("id", ell + 1)))

    val_ok = bool(op.get("operator_validation_passed", False))
    if status not in ("OPTIMAL", "TIME_LIMIT", "SUBOPTIMAL") and obj is None:
        val_ok = False

    return {
        "status": status,
        "obj": obj,
        "obj_bound": obj_bound if obj_bound is not None else obj,
        "mip_gap": mip_gap,
        "runtime": runtime,
        "method": method,
        "k": int(config.get("k", 1)),
        "attack_target": str(config.get("attack_target", "lines")),
        "attacked_lines_idx": list(attacked_lines),
        "attacked_branch_ids": br_ids,
        "attacked_gens": list(attacked_gens),
        "n_attacks_evaluated": n_enum,
        "shed_MW": obj,
        "total_demand_MW": total_pd,
        "baseline_shed_MW": baseline_shed_MW,
        "dual_obj": dual_obj,
        "Pg_MW": op.get("Pg_MW"),
        "theta_deg": op.get("theta_deg"),
        "flow_MW": op.get("flow_MW"),
        "shed_bus_MW": op.get("shed_bus_MW"),
        "max_power_balance_MW": op.get("max_power_balance_MW", 0.0),
        "max_flow_equation_MW": op.get("max_flow_equation_MW", 0.0),
        "max_thermal_violation_MW": op.get("max_thermal_violation_MW", 0.0),
        "max_attacked_flow_MW": op.get("max_attacked_flow_MW", 0.0),
        "max_generator_bound_MW": op.get("max_generator_bound_MW", 0.0),
        "notes": notes,
        "validation_passed": val_ok and obj is not None,
    }


def solve_interdiction(
    network: dict, config: dict, *, quiet: bool = True
) -> dict[str, Any]:
    method = str(config.get("method", "enumeration")).lower()
    k = int(config.get("k", 1))
    n_bus = len(network["buses"])

    if method == "auto":
        # small: enum + milp cross-check
        en = solve_enumeration(network, config, quiet=quiet)
        if n_bus <= 14 and k == 1 and str(config.get("attack_target", "lines")) == "lines":
            milp = solve_bilevel_milp(network, config, quiet=quiet)
            en["milp_obj"] = milp.get("obj")
            en["milp_attacked_lines_idx"] = milp.get("attacked_lines_idx")
            en["milp_dual_obj"] = milp.get("dual_obj")
            en["milp_status"] = milp.get("status")
            if (
                en.get("obj") is not None
                and milp.get("obj") is not None
                and abs(float(en["obj"]) - float(milp["obj"]))
                <= max(0.01, 1e-5 * max(1.0, abs(float(en["obj"]))))
            ):
                en["oracle_milp_match"] = True
            else:
                en["oracle_milp_match"] = False
            en["notes"] = (en.get("notes") or "") + f"; milp_match={en['oracle_milp_match']}"
            en["method"] = "auto"
            en["runtime"] = float(en.get("runtime") or 0) + float(milp.get("runtime") or 0)
        return en
    if method == "enumeration":
        return solve_enumeration(network, config, quiet=quiet)
    if method in ("bilevel_milp", "milp", "dual_milp"):
        return solve_bilevel_milp(network, config, quiet=quiet)
    if method == "heuristic":
        return solve_heuristic(network, config, quiet=quiet)
    raise ValueError(f"unknown method {method}")


def run_case(case_dir: str | Path, *, quiet: bool = True) -> dict[str, Any]:
    case_dir = Path(case_dir)
    network, config = load_case(case_dir)
    sol = solve_interdiction(network, config, quiet=quiet)
    case_name = config.get("case") or case_dir.name
    result = {
        "schema_version": 1,
        "case": case_name,
        "solver": "python-gurobi",
        "problem": "interdiction",
        "base_problem": config.get("base_problem", "network_interdiction"),
        "interdiction": sol,
        "validation": {"passed": bool(sol.get("validation_passed"))},
    }
    write_result(case_dir, "python_result.json", result)
    return result


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    args = ap.parse_args()
    r = run_case(args.case_dir, quiet=True)
    e = r["interdiction"]
    print(
        f"[{r['case']}] {e['status']} method={e['method']} obj={e['obj']} "
        f"atk_lines={e['attacked_lines_idx']} valid={e['validation_passed']}"
    )
