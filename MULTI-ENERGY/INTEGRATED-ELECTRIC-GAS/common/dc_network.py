"""Shared DC network helpers (branch b, bus maps) for new problem packs."""

from __future__ import annotations

import math
from typing import Any


def bus_maps(network: dict[str, Any]) -> tuple[list[int], dict[int, int], int]:
    bus_ids = [int(b["bus_i"]) for b in network["buses"]]
    bus_pos = {bid: i for i, bid in enumerate(bus_ids)}
    ref = next((int(b["bus_i"]) for b in network["buses"] if int(b["type"]) == 3), bus_ids[0])
    return bus_ids, bus_pos, ref


# Branches with |x| below this are treated as ideal (theta coupling, free flow physics).
ZERO_X_EPS = 1e-8


def branch_susceptance(br: dict[str, Any]) -> tuple[float, float]:
    """Return (b, phi_rad). MATPOWER: b = 1/(x*tap), tap=1 if ratio==0.

    If |x| < ZERO_X_EPS, returns (inf-like large sentinel via is_zero_x check).
    Prefer is_zero_x() + explicit theta equality in models.
    """
    x = float(br["x"])
    if abs(x) < ZERO_X_EPS:
        x = ZERO_X_EPS  # caller should use is_zero_x instead of huge b
    ratio = float(br.get("ratio", 0.0) or 0.0)
    tap = 1.0 if abs(ratio) < 1e-12 else ratio
    b = 1.0 / (x * tap)
    phi = math.radians(float(br.get("angle", 0.0) or 0.0))
    return b, phi


def is_zero_x(br: dict[str, Any]) -> bool:
    return abs(float(br.get("x", 0.0) or 0.0)) < ZERO_X_EPS


def thermal_rate_mw(br: dict[str, Any]) -> float:
    """rateA in MW; 0 means unconstrained in many PGLib cases."""
    return float(br.get("rateA", 0.0) or 0.0)


def gen_bounds_mw(gen: dict[str, Any]) -> tuple[float, float]:
    if int(gen.get("status", 1)) == 0:
        return 0.0, 0.0
    return float(gen["Pmin"]), float(gen["Pmax"])
