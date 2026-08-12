"""Independent numerical validation for DC-OTS and preventive SC-OTS results."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from validate_data import angle_limit_rad, branch_susceptance


DEFAULT_TOLERANCES = {
    "power_balance_mw": 1e-4,
    "flow_equation_mw": 1e-4,
    "open_flow_mw": 1e-4,
    "thermal_mw": 1e-4,
    "generator_bound_mw": 1e-4,
    "redispatch_mw": 1e-4,
    "angle_rad": 1e-7,
    "integrality": 1e-6,
}


def _as_float_list(value: Any) -> list[float]:
    if value is None:
        return []
    if isinstance(value, list):
        return [float(v) for v in value]
    return [float(value)]


def _z_values(solution: dict) -> dict[int, float]:
    out: dict[int, float] = {}
    for key, value in (solution.get("z") or {}).items():
        digits = "".join(ch for ch in str(key) if ch.isdigit())
        if digits:
            out[int(digits)] = float(value)
    return out


def _opened_ids(solution: dict) -> set[int]:
    raw = solution.get("opened_lines") or []
    if not isinstance(raw, list):
        raw = [raw]
    opened = {int(v) for v in raw}
    opened.update(bid for bid, value in _z_values(solution).items() if value < 0.5)
    return opened


def _connected(bus_ids: list[int], branches: list[dict], closed_ids: set[int]) -> bool:
    if not bus_ids:
        return False
    adjacency = {bid: [] for bid in bus_ids}
    for br in branches:
        if int(br["id"]) not in closed_ids:
            continue
        fbus, tbus = int(br["fbus"]), int(br["tbus"])
        adjacency[fbus].append(tbus)
        adjacency[tbus].append(fbus)
    seen = {bus_ids[0]}
    queue = deque([bus_ids[0]])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(bus_ids)


def _state_metrics(
    network: dict,
    config: dict,
    solution: dict,
    state_solution: dict,
    *,
    outaged_branch: int | None,
    base_dispatch: list[float],
) -> dict[str, Any]:
    base = float(network["baseMVA"])
    buses = network["buses"]
    gens = network["gens"]
    branches = network["branches"]
    bus_ids = [int(bus["bus_i"]) for bus in buses]
    bus_pos = {bid: pos for pos, bid in enumerate(bus_ids)}

    pg = _as_float_list(state_solution.get("Pg_MW"))
    theta_deg = _as_float_list(state_solution.get("theta_deg"))
    flow = _as_float_list(state_solution.get("flow_MW"))
    expected = (len(gens), len(buses), len(branches))
    actual = (len(pg), len(theta_deg), len(flow))
    if actual != expected:
        return {
            "valid_shape": False,
            "expected_shape": list(expected),
            "actual_shape": list(actual),
            "connected": False,
            "passed": False,
        }

    theta = [math.radians(value) for value in theta_deg]
    opened = _opened_ids(solution)
    closed_ids = {
        int(br["id"])
        for br in branches
        if int(br["status"]) == 1
        and int(br["id"]) not in opened
        and int(br["id"]) != outaged_branch
    }

    max_flow_eq = 0.0
    max_open_flow = 0.0
    max_thermal = 0.0
    max_angle = 0.0
    max_util = 0.0
    for ell, br in enumerate(branches):
        bid = int(br["id"])
        is_closed = bid in closed_ids
        fval = float(flow[ell])
        if not is_closed:
            max_open_flow = max(max_open_flow, abs(fval))
            continue

        i = bus_pos[int(br["fbus"])]
        j = bus_pos[int(br["tbus"])]
        bsus, shift = branch_susceptance(br)
        expected_flow = base * bsus * (theta[i] - theta[j] - shift)
        max_flow_eq = max(max_flow_eq, abs(fval - expected_flow))

        if outaged_branch is None:
            rate = float(br.get("rateA", 0.0))
        else:
            rate = float(br.get("rateC", 0.0))
            if rate <= 0.0:
                rate = float(br.get("rateA", 0.0))
        if rate > 0.0:
            max_thermal = max(max_thermal, max(0.0, abs(fval) - rate))
            max_util = max(max_util, abs(fval) / rate)

        amin, amax = angle_limit_rad(br)
        delta = theta[i] - theta[j]
        if amin is not None:
            max_angle = max(max_angle, max(0.0, amin - delta))
        if amax is not None:
            max_angle = max(max_angle, max(0.0, delta - amax))

    max_balance = 0.0
    for bus in buses:
        bid = int(bus["bus_i"])
        generation = sum(pg[g] for g, gen in enumerate(gens) if int(gen["bus"]) == bid)
        outflow = sum(
            flow[ell] for ell, br in enumerate(branches) if int(br["fbus"]) == bid
        )
        inflow = sum(
            flow[ell] for ell, br in enumerate(branches) if int(br["tbus"]) == bid
        )
        residual = generation - float(bus["Pd"]) - outflow + inflow
        max_balance = max(max_balance, abs(residual))

    max_gen_bound = 0.0
    for g, gen in enumerate(gens):
        if int(gen["status"]) == 0:
            max_gen_bound = max(max_gen_bound, abs(pg[g]))
        else:
            max_gen_bound = max(
                max_gen_bound,
                max(0.0, float(gen["Pmin"]) - pg[g]),
                max(0.0, pg[g] - float(gen["Pmax"])),
            )

    max_redispatch = 0.0
    max_dispatch_change = 0.0
    if outaged_branch is not None and len(base_dispatch) == len(gens):
        fraction = float(config.get("redispatch_frac", 0.2))
        for g, gen in enumerate(gens):
            change = abs(pg[g] - base_dispatch[g])
            max_dispatch_change = max(max_dispatch_change, change)
            band = fraction * (float(gen["Pmax"]) - float(gen["Pmin"]))
            if int(gen["status"]) == 0:
                band = 0.0
            max_redispatch = max(max_redispatch, max(0.0, change - band))

    return {
        "valid_shape": True,
        "outaged_branch": outaged_branch,
        "connected": _connected(bus_ids, branches, closed_ids),
        "max_power_balance_mw": max_balance,
        "max_flow_equation_mw": max_flow_eq,
        "max_open_flow_mw": max_open_flow,
        "max_thermal_violation_mw": max_thermal,
        "max_generator_bound_violation_mw": max_gen_bound,
        "max_angle_violation_rad": max_angle,
        "max_redispatch_violation_mw": max_redispatch,
        "max_utilization": max_util,
        "max_dispatch_change_mw": max_dispatch_change,
    }


def validate_solution_bundle(
    network: dict,
    config: dict,
    solution: dict,
    *,
    state: str,
    contingencies: dict | None = None,
    tolerances: dict | None = None,
) -> dict[str, Any]:
    """Recompute all model residuals without consulting the Gurobi model."""
    tol = dict(DEFAULT_TOLERANCES)
    if tolerances:
        tol.update(tolerances)

    zvals = _z_values(solution)
    max_integer = max((abs(value - round(value)) for value in zvals.values()), default=0.0)
    base_dispatch = _as_float_list(solution.get("Pg_MW"))
    base_metrics = _state_metrics(
        network,
        config,
        solution,
        solution,
        outaged_branch=None,
        base_dispatch=base_dispatch,
    )

    scenario_metrics: list[dict[str, Any]] = []
    for key, scenario in sorted(
        (contingencies or {}).items(), key=lambda item: int(item[0])
    ):
        outage = int(scenario.get("outaged_branch", key))
        metrics = _state_metrics(
            network,
            config,
            solution,
            scenario,
            outaged_branch=outage,
            base_dispatch=base_dispatch,
        )
        metrics["scenario"] = f"outage_{outage}"
        scenario_metrics.append(metrics)

    all_metrics = [base_metrics, *scenario_metrics]

    def maximum(name: str) -> float:
        return max((float(m.get(name, math.inf)) for m in all_metrics), default=math.inf)

    maxima = {
        "max_power_balance_mw": maximum("max_power_balance_mw"),
        "max_flow_equation_mw": maximum("max_flow_equation_mw"),
        "max_open_flow_mw": maximum("max_open_flow_mw"),
        "max_thermal_violation_mw": maximum("max_thermal_violation_mw"),
        "max_generator_bound_violation_mw": maximum(
            "max_generator_bound_violation_mw"
        ),
        "max_angle_violation_rad": maximum("max_angle_violation_rad"),
        "max_redispatch_violation_mw": maximum("max_redispatch_violation_mw"),
        "max_integrality_violation": max_integer,
    }
    connected = all(bool(m.get("connected", False)) for m in all_metrics)
    valid_shapes = all(bool(m.get("valid_shape", False)) for m in all_metrics)
    passed = (
        solution.get("status") == "OPTIMAL"
        and valid_shapes
        and connected
        and maxima["max_power_balance_mw"] <= tol["power_balance_mw"]
        and maxima["max_flow_equation_mw"] <= tol["flow_equation_mw"]
        and maxima["max_open_flow_mw"] <= tol["open_flow_mw"]
        and maxima["max_thermal_violation_mw"] <= tol["thermal_mw"]
        and maxima["max_generator_bound_violation_mw"] <= tol["generator_bound_mw"]
        and maxima["max_redispatch_violation_mw"] <= tol["redispatch_mw"]
        and maxima["max_angle_violation_rad"] <= tol["angle_rad"]
        and max_integer <= tol["integrality"]
    )
    return {
        "state": state,
        "passed": passed,
        "connected_all_states": connected,
        "valid_shapes": valid_shapes,
        "tolerances": tol,
        **maxima,
        "base": base_metrics,
        "scenarios": scenario_metrics,
    }
