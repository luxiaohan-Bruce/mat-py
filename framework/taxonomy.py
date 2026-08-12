"""Canonical base_problem / variant / solver_family for each pack."""

from __future__ import annotations

from typing import Any

# Canonical PLAM names (not formulation aliases like dcots/scots).
PACK_SPEC: dict[str, dict[str, Any]] = {
    "OTS/DC-OTS": {
        "base_problem": "ots",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "OTS/SC-OTS": {
        "base_problem": "ots",
        "math_class": "milp",
        "solver_family": "security_mip",
        "variant": {
            "power_flow": "dc",
            "security": "n-1",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "preventive",
        },
    },
    "OTS/SC-AC-OTS": {
        "base_problem": "ots",
        "math_class": "milp",
        "solver_family": "security_mip",
        "variant": {
            "power_flow": "linearized_sc",
            "security": "n-1",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "preventive",
        },
    },
    "OPF/SC-AC-OPF": {
        "base_problem": "opf",
        "math_class": "lp",
        "solver_family": "security_mip",
        "variant": {
            "power_flow": "linearized_sc",
            "security": "n-1",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "preventive",
        },
    },
    "UC/SYSTEM-UC": {
        "base_problem": "uc",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    },
    "UC/SCUC": {
        "base_problem": "uc",
        "math_class": "milp",
        "solver_family": "security_mip",
        "variant": {
            "power_flow": "dc",
            "security": "n-1",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "preventive",
        },
    },
    "UC/RTS-SCUC": {
        "base_problem": "uc",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "dc",
            "security": "n-1",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "preventive",
            "storage": "yes",
        },
    },
    "DISTRIBUTION/DNR": {
        "base_problem": "dnr",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "DISTRIBUTION/VOLT-VAR": {
        "base_problem": "volt_var",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "DISTRIBUTION/DER-HOSTING": {
        "base_problem": "der_hosting",
        "math_class": "lp",
        "solver_family": "convex_dispatch",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "DISPATCH/ECONOMIC-DISPATCH": {
        "base_problem": "economic_dispatch",
        "math_class": "qp",
        "solver_family": "convex_dispatch",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/MAXIMUM-LOAD-DELIVERY": {
        "base_problem": "maximum_load_delivery",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "MONITORING/PMU-PLACEMENT": {
        "base_problem": "pmu_placement",
        "math_class": "milp",
        "solver_family": "covering_mip",
        "variant": {
            "power_flow": "topological",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "MONITORING/STATE-ESTIMATION": {
        "base_problem": "state_estimation",
        "math_class": "qp",
        "solver_family": "convex_dispatch",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "PLANNING/TRANSMISSION-EXPANSION": {
        "base_problem": "transmission_expansion",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "PLANNING/RESOURCE-CAPACITY-EXPANSION": {
        "base_problem": "resource_capacity_expansion",
        "math_class": "lp",
        "solver_family": "convex_dispatch",
        "variant": {
            "power_flow": "copperplate_multizone",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_stage_multi_period",
            "recourse": "none",
        },
    },
    "SCHEDULING/HYDROTHERMAL-SCHEDULING": {
        "base_problem": "hydrothermal_scheduling",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "two_stage_stochastic",
            "horizon": "multi_period",
            "recourse": "dispatch",
        },
    },
    "SCHEDULING/MAINTENANCE-SCHEDULING": {
        "base_problem": "maintenance_scheduling",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    },
    "MARKET/MARKET-CLEARING": {
        "base_problem": "market_clearing",
        "math_class": "lp",
        "solver_family": "convex_dispatch",
        "variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    },
    "MARKET/STRATEGIC-BIDDING": {
        "base_problem": "strategic_bidding",
        "math_class": "bilevel",
        "solver_family": "bilevel",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/POWER-RESTORATION": {
        "base_problem": "power_restoration",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/DISTRIBUTION-RESTORATION": {
        "base_problem": "distribution_restoration",
        "math_class": "milp",
        "solver_family": "temporal_mip",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/CONTROLLED-ISLANDING": {
        "base_problem": "controlled_islanding",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/OPTIMAL-POWER-SHUTOFF": {
        "base_problem": "optimal_power_shutoff",
        "math_class": "milp",
        "solver_family": "topology_mip",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
    "RESILIENCE/NETWORK-INTERDICTION": {
        "base_problem": "network_interdiction",
        "math_class": "bilevel",
        "solver_family": "bilevel",
        "variant": {
            "power_flow": "dc",
            "security": "n-k",
            "uncertainty": "worst_case_attack",
            "horizon": "single_period",
            "recourse": "operator_load_shed_lp",
        },
    },
    "MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS": {
        "base_problem": "integrated_electric_gas",
        "math_class": "milp",
        "solver_family": "coupled",
        "variant": {
            "power_flow": "dc",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    },
}

# Per-case overrides when a pack still mixes modes (DNR contains DOPF variants).
PROBLEM_OVERRIDE: dict[str, dict[str, Any]] = {
    "lindistflow_dopf": {
        "base_problem": "distribution_opf",
        "math_class": "lp",
        "solver_family": "convex_dispatch",
        "variant_extra": {"horizon": "multi_period"},
    },
    "lindistflow_dnr_ess": {
        "base_problem": "dnr",
        "variant_extra": {"storage": "yes", "horizon": "multi_period"},
    },
    "meta": {
        "base_problem": "dnr",
        "math_class": "none",
        "solver_family": "none",
    },
    "smartds_voltvar": {"base_problem": "volt_var"},
    "smartds_hosting": {"base_problem": "der_hosting", "math_class": "lp"},
    "smartds_lindistflow_dnr": {"base_problem": "dnr"},
    "l1": {"math_class": "lp", "variant_extra": {"estimator": "l1"}},
}


def spec_for(pack: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    spec = dict(PACK_SPEC.get(pack) or {
        "base_problem": "unknown",
        "math_class": "unknown",
        "solver_family": "unknown",
        "variant": {},
    })
    spec["variant"] = dict(spec.get("variant") or {})
    cfg = config or {}
    key = str(cfg.get("problem") or "")
    if cfg.get("se_method") == "l1":
        key = "l1"
    ov = PROBLEM_OVERRIDE.get(key)
    if ov:
        if "base_problem" in ov:
            spec["base_problem"] = ov["base_problem"]
        if "math_class" in ov:
            spec["math_class"] = ov["math_class"]
        if "solver_family" in ov:
            spec["solver_family"] = ov["solver_family"]
        spec["variant"].update(ov.get("variant_extra") or {})
    return spec
