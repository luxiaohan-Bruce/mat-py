"""Strict validation of network.json + config.json for DC-OTS / SC-OTS."""

from __future__ import annotations

from typing import Any


class DataValidationError(ValueError):
    """Raised when case data fails strict validation."""


def _req(d: dict, key: str, ctx: str) -> Any:
    if key not in d:
        raise DataValidationError(f"{ctx}: missing required field '{key}'")
    return d[key]


def validate_network(network: dict, config: dict | None = None) -> None:
    """Validate network (and optional config). Raises DataValidationError on failure."""
    errors: list[str] = []

    base = network.get("baseMVA")
    if base is None or float(base) <= 0:
        errors.append("baseMVA must be a positive number")

    buses = network.get("buses")
    gens = network.get("gens")
    branches = network.get("branches")
    if not isinstance(buses, list) or not buses:
        errors.append("buses must be a non-empty list")
    if not isinstance(gens, list) or not gens:
        errors.append("gens must be a non-empty list")
    if not isinstance(branches, list) or not branches:
        errors.append("branches must be a non-empty list")
    if errors:
        raise DataValidationError("; ".join(errors))

    bus_ids: list[int] = []
    refs = 0
    for i, b in enumerate(buses):
        ctx = f"buses[{i}]"
        try:
            bid = int(_req(b, "bus_i", ctx))
            btype = int(_req(b, "type", ctx))
            float(_req(b, "Pd", ctx))
        except (TypeError, ValueError, DataValidationError) as e:
            errors.append(str(e))
            continue
        bus_ids.append(bid)
        if btype == 3:
            refs += 1
        if btype not in (1, 2, 3, 4):
            errors.append(f"{ctx}: invalid bus type {btype}")

    if len(bus_ids) != len(set(bus_ids)):
        errors.append("bus_i values must be unique")
    if refs == 0:
        errors.append("network must have at least one reference bus (type==3)")
    if refs > 1:
        errors.append(f"network has {refs} reference buses; expected exactly one")

    bus_set = set(bus_ids)
    for i, g in enumerate(gens):
        ctx = f"gens[{i}]"
        try:
            gbus = int(_req(g, "bus", ctx))
            status = int(_req(g, "status", ctx))
            pmin = float(_req(g, "Pmin", ctx))
            pmax = float(_req(g, "Pmax", ctx))
            cost_model = int(g.get("cost_model", 2))
            float(_req(g, "c2", ctx))
            float(_req(g, "c1", ctx))
            float(_req(g, "c0", ctx))
        except (TypeError, ValueError, DataValidationError) as e:
            errors.append(str(e))
            continue
        if gbus not in bus_set:
            errors.append(f"{ctx}: gen bus {gbus} not in bus list")
        if status not in (0, 1):
            errors.append(f"{ctx}: status must be 0 or 1")
        if pmax < pmin - 1e-9:
            errors.append(f"{ctx}: Pmax ({pmax}) < Pmin ({pmin})")
        if cost_model != 2:
            errors.append(f"{ctx}: only polynomial cost_model=2 is supported")

    branch_ids: list[int] = []
    for i, br in enumerate(branches):
        ctx = f"branches[{i}]"
        try:
            bid = int(_req(br, "id", ctx))
            fbus = int(_req(br, "fbus", ctx))
            tbus = int(_req(br, "tbus", ctx))
            x = float(_req(br, "x", ctx))
            status = int(_req(br, "status", ctx))
            float(_req(br, "rateA", ctx))
            float(br.get("rateB", 0.0))
            float(br.get("rateC", 0.0))
            float(br.get("ratio", 0.0))
            float(br.get("angle", 0.0))
        except (TypeError, ValueError, DataValidationError) as e:
            errors.append(str(e))
            continue
        branch_ids.append(bid)
        if fbus not in bus_set or tbus not in bus_set:
            errors.append(f"{ctx}: fbus/tbus ({fbus},{tbus}) not in bus list")
        if fbus == tbus:
            errors.append(f"{ctx}: fbus == tbus ({fbus})")
        if status not in (0, 1):
            errors.append(f"{ctx}: status must be 0 or 1")
        if status == 1 and abs(x) < 1e-12:
            errors.append(f"{ctx}: in-service branch has near-zero reactance x={x}")
        amin = float(br.get("angmin", -360.0))
        amax = float(br.get("angmax", 360.0))
        if amin > -360.0 and amax < 360.0 and amin > amax + 1e-12:
            errors.append(f"{ctx}: active angmin ({amin}) exceeds angmax ({amax})")

    if len(branch_ids) != len(set(branch_ids)):
        errors.append("branch id values must be unique")

    if config is not None:
        sw = config.get("switchable_idx", [])
        if sw is None:
            sw = []
        if not isinstance(sw, (list, tuple)):
            errors.append("config.switchable_idx must be a list")
        else:
            id_set = set(branch_ids)
            branch_by_id = {int(br["id"]): br for br in branches}
            for s in sw:
                sid = int(s)
                if sid not in id_set:
                    errors.append(f"config.switchable_idx contains unknown branch id {s}")
                    continue
                br = branch_by_id[sid]
                if int(br["status"]) != 1:
                    errors.append(f"config.switchable_idx contains offline branch id {sid}")
                if abs(float(br.get("ratio", 0.0))) > 1e-12:
                    errors.append(f"config.switchable_idx contains transformer branch id {sid}")
                if abs(float(br.get("angle", 0.0))) > 1e-12:
                    errors.append(f"config.switchable_idx contains phase-shifter branch id {sid}")
        fixed_open = config.get("fixed_open_idx", []) or []
        if not isinstance(fixed_open, (list, tuple)):
            errors.append("config.fixed_open_idx must be a list")
        else:
            sw_ids = {int(s) for s in sw} if isinstance(sw, (list, tuple)) else set()
            for value in fixed_open:
                if int(value) not in sw_ids:
                    errors.append(
                        f"config.fixed_open_idx branch {value} is not in switchable_idx"
                    )
        max_open = config.get("max_open", 0)
        try:
            mo = int(max_open)
            if mo < 0:
                errors.append("config.max_open must be >= 0")
        except (TypeError, ValueError):
            errors.append("config.max_open must be an integer")

        problem = str(config.get("problem", "dcots")).lower()
        if problem not in ("dcots", "scots", "dcopf"):
            errors.append(f"config.problem must be dcots|scots|dcopf, got {problem!r}")

        if problem == "scots":
            rf = config.get("redispatch_frac", 0.2)
            try:
                rf = float(rf)
                if rf < 0 or rf > 1:
                    errors.append("config.redispatch_frac must be in [0, 1]")
            except (TypeError, ValueError):
                errors.append("config.redispatch_frac must be numeric")
            cont = config.get("contingencies", [])
            if cont is None:
                cont = []
            if isinstance(cont, str) and cont.lower() in ("n1_all", "n-1", "n1"):
                pass
            elif isinstance(cont, (list, tuple)):
                id_set = set(branch_ids)
                for c in cont:
                    cid = int(c)
                    if cid not in id_set:
                        errors.append(f"config.contingencies contains unknown branch id {c}")
                    elif int(branches[branch_ids.index(cid)]["status"]) != 1:
                        errors.append(f"config.contingencies contains offline branch id {cid}")
            else:
                errors.append("config.contingencies must be a list of branch ids or 'n1_all'")

    if errors:
        raise DataValidationError("; ".join(errors))


def branch_susceptance(br: dict) -> tuple[float, float]:
    """Return (b, phi_rad) for DC branch flow f = b * (theta_f - theta_t - phi).

    MATPOWER makeBdc convention:
      tap = 1 if ratio==0 else ratio
      b = 1 / (x * tap)
      phi = angle_deg * pi/180
    """
    import math

    x = float(br["x"])
    if abs(x) < 1e-12:
        x = 1e-12
    ratio = float(br.get("ratio", 0.0))
    tap = 1.0 if abs(ratio) < 1e-12 else ratio
    b = 1.0 / (x * tap)
    phi = math.radians(float(br.get("angle", 0.0)))
    return b, phi


def angle_limit_rad(br: dict) -> tuple[float | None, float | None]:
    """MATPOWER one-sided angle limits in radians.

    Lower bound is active only if angmin > -360; upper only if angmax < 360.
    Sides are independent — a one-sided active bound is retained.
    Returns (amin_rad_or_None, amax_rad_or_None).
    """
    import math

    amin_deg = float(br.get("angmin", -360.0))
    amax_deg = float(br.get("angmax", 360.0))
    amin = math.radians(amin_deg) if amin_deg > -360.0 + 1e-12 else None
    amax = math.radians(amax_deg) if amax_deg < 360.0 - 1e-12 else None
    return amin, amax


def thermal_rate_pu(br: dict, base: float, *, contingency: bool = False) -> float:
    """Thermal limit in p.u. rateA for base, rateC for contingency (fallback rateA)."""
    if contingency:
        rate = float(br.get("rateC", 0.0))
        if rate <= 0:
            rate = float(br.get("rateA", 0.0))
    else:
        rate = float(br.get("rateA", 0.0))
    if rate <= 0:
        return 1e3  # effectively unconstrained
    return rate / base
