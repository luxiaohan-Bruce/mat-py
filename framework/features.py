"""Standard size features and source_network identity."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_PGLIB_OPF = re.compile(r"(pglib_opf_case[A-Za-z0-9_]+)")
_GO_NET = re.compile(r"(Network_[^/]+)")


def _len(x: Any) -> int:
    if x is None:
        return 0
    if isinstance(x, dict):
        return len(x)
    if isinstance(x, (list, tuple, set)):
        return len(x)
    return 0


def _count_switchable(branches: Any) -> int:
    if isinstance(branches, dict):
        values = branches.values()
    elif isinstance(branches, (list, tuple)):
        values = branches
    else:
        return 0
    return sum(
        1
        for branch in values
        if isinstance(branch, dict) and bool(branch.get("switchable"))
    )


def source_network(config: dict[str, Any], network: dict[str, Any] | None = None) -> str:
    """Stable id for the underlying grid, shared across problem types."""
    src = config.get("source")
    net = network or {}
    if isinstance(src, str) and src.strip():
        m = _PGLIB_OPF.search(src)
        if m:
            return m.group(1)
        stem = Path(src).stem
        if stem.startswith("pglib"):
            return stem
        return src.strip()
    if isinstance(src, dict):
        for key in ("pglib_stem", "pglib_file"):
            val = src.get(key)
            if val:
                m = _PGLIB_OPF.search(str(val))
                return m.group(1) if m else Path(str(val)).stem
        rel = str(src.get("relative_path") or src.get("raw") or src.get("path_relative") or "")
        m = _PGLIB_OPF.search(rel)
        if m:
            return m.group(1)
        dataset = str(src.get("dataset") or "")
        if "PGLib-UC" in dataset or "pglib-uc" in rel:
            group = src.get("group") or (Path(rel).parent.name if rel else "")
            stem = Path(rel).stem if rel else str(config.get("case") or "")
            return f"pglib_uc:{group}:{stem}"
        if "GO Competition" in dataset or "Challenge_1" in rel:
            gm = _GO_NET.search(rel)
            if gm:
                return f"go_c1:{gm.group(1)}"
            return "go_c1"
        if dataset == "SimBench" or src.get("folder"):
            return f"simbench:{src.get('folder') or Path(rel).name}"
        if dataset == "SMART-DS" or src.get("feeder"):
            return f"smartds:{src.get('feeder') or src.get('folder') or 'gso_rural'}"
        if dataset == "RTS-GMLC" or "RTS-GMLC" in dataset or "RTS_GMLC" in rel:
            extra = src.get("load_slice") or src.get("system") or ""
            return f"rts_gmlc:{extra}".rstrip(":") if extra else "rts_gmlc"
        if "GenX" in dataset:
            return f"genx:{src.get('system') or 'unknown'}"
        if "GasLib" in dataset or "gaslib" in rel.lower():
            gas = src.get("gaslib_dir") or src.get("scenario") or "gaslib"
            pglib = src.get("pglib") or ""
            pm = _PGLIB_OPF.search(str(pglib))
            tail = pm.group(1) if pm else Path(str(pglib)).stem
            return f"gaslib:{gas}:{tail}".rstrip(":")
        if "ANDES" in dataset:
            return f"andes:{Path(rel).stem or config.get('case')}"
        if "CommaLAB" in dataset:
            return f"commalab:{src.get('system') or Path(rel).name}"
        if "PowerModelsWildfire" in dataset or "wildfire" in rel.lower():
            return f"wildfire:{Path(rel).stem or 'unknown'}"
        if "PowerModelsRestoration" in dataset or "restoration" in rel.lower():
            m2 = _PGLIB_OPF.search(rel)
            if m2:
                return m2.group(1)
            return f"restoration:{Path(rel).stem or 'unknown'}"
        if "IEEE PES 4 Node" in dataset:
            return f"ieee_pes_4_node_test_feeder:{src.get('system') or 'ieee4'}"
        if dataset == "SimBench LineType":
            return f"simbench_linetype:{src.get('system') or 'unknown'}"
        if "ACTIVSg200" in dataset:
            return "pglib_opf_case200_activ"
        if dataset:
            return f"{dataset.lower().replace(' ', '_')}:{Path(rel).stem or src.get('system') or 'unknown'}"
    net_src = net.get("source") or net.get("source_file")
    if isinstance(net_src, str) and net_src:
        m = _PGLIB_OPF.search(net_src)
        if m:
            return m.group(1)
        return Path(net_src).stem
    name = str(net.get("name") or config.get("case") or "unknown")
    return name


def extract_features(
    config: dict[str, Any],
    network: dict[str, Any] | None,
    *,
    pack: str = "",
) -> dict[str, Any]:
    cfg = config or {}
    net = network or {}

    n_bus = _len(net.get("buses") or net.get("bus") or net.get("zones"))
    branches = net.get("branches") or net.get("branch") or net.get("network_lines")
    n_branch = _len(branches)
    gens = (
        net.get("gens")
        or net.get("generators")
        or net.get("gen")
        or net.get("thermal")
        or net.get("thermal_units")
        or net.get("thermal_generators")
    )
    n_gen = _len(gens)
    n_gen += _len(net.get("renewable") or net.get("renewable_generators"))
    n_storage = _len(net.get("storage"))
    n_ne = _len(net.get("ne_branches"))

    T = cfg.get("T") or cfg.get("horizon_T") or cfg.get("time_periods")
    if T is None:
        T = net.get("time_periods") or net.get("n_time") or 1
    try:
        T = int(T)
    except (TypeError, ValueError):
        T = 1
    if T <= 0:
        T = 1

    ctg = cfg.get("contingencies")
    if ctg is None:
        ctg = net.get("contingencies")
    n_ctg = _len(ctg)

    n_scen = cfg.get("n_scenarios") or net.get("n_scenarios") or 1
    try:
        n_scen = int(n_scen)
    except (TypeError, ValueError):
        n_scen = 1

    if "switchable_idx" in cfg:
        n_switch = _len(cfg.get("switchable_idx"))
    elif "switchable_branches" in cfg:
        n_switch = _len(cfg.get("switchable_branches"))
    else:
        n_switch = _count_switchable(branches)
    max_open = cfg.get("max_open")
    k_attack = cfg.get("k")

    n_bin = _estimate_n_bin(
        pack,
        cfg,
        n_bus=n_bus,
        n_branch=n_branch,
        n_gen=n_gen,
        T=T,
        n_switch=n_switch,
        n_ne=n_ne,
        n_storage=n_storage,
        net=net,
    )

    return {
        "n_bus": int(n_bus),
        "n_branch": int(n_branch),
        "n_gen": int(n_gen),
        "n_storage": int(n_storage),
        "n_candidate_branch": int(n_ne),
        "T": int(T),
        "n_contingency": int(n_ctg),
        "n_scenario": int(n_scen),
        "n_switchable": int(n_switch),
        "max_open": max_open,
        "k": k_attack,
        "n_bin": int(n_bin),
    }


def _estimate_n_bin(
    pack: str,
    cfg: dict[str, Any],
    *,
    n_bus: int,
    n_branch: int,
    n_gen: int,
    T: int,
    n_switch: int,
    n_ne: int,
    n_storage: int,
    net: dict[str, Any],
) -> int:
    p = pack
    if "DC-OTS" in p or "SC-OTS" in p or "LINEARIZED-SC-OTS" in p:
        return n_switch
    if "LINEARIZED-SC-OPF" in p:
        return 0
    if "SYSTEM-UC" in p or p.endswith("SCUC") or "RTS-SCUC" in p:
        return n_gen * max(T, 1)
    if "PMU-PLACEMENT" in p:
        return n_bus
    if "DISTRIBUTION-EXPANSION" in p:
        return n_ne
    if "DEMAND-RESPONSE" in p or "STORAGE-SCHEDULING" in p or "MICROGRID" in p or "UNBALANCED-DOPF" in p or "SC-AC-OPF" in p or "AC-OPF" in p:
        return 0
    if "TRANSMISSION-EXPANSION" in p:
        return n_ne or n_branch
    if "NETWORK-INTERDICTION" in p:
        return n_branch
    if "CONTROLLED-ISLANDING" in p:
        return n_bus
    if "OPTIMAL-POWER-SHUTOFF" in p:
        return n_branch
    if "POWER-RESTORATION" in p or "DISTRIBUTION-RESTORATION" in p:
        return max(n_branch, n_bus) * max(T, 1)
    if "MAXIMUM-LOAD-DELIVERY" in p:
        return n_bus
    if (
        "DNR" in p
        or "DISTRIBUTION-OPF" in p
        or "VOLT-VAR" in p
        or "DER-HOSTING" in p
    ):
        return n_branch
    if "MAINTENANCE-SCHEDULING" in p:
        return _len(net.get("maintenance_tasks") or net.get("generators")) * max(T, 1)
    if "HYDROTHERMAL" in p:
        return n_gen * max(T, 1)
    if "STRATEGIC-BIDDING" in p:
        return 8
    if "INTEGRATED-ELECTRIC-GAS" in p:
        return max(8 * _len((net.get("gas") or {}).get("pipes")), 0)
    if cfg.get("se_method") == "l1":
        return 0
    return 0
