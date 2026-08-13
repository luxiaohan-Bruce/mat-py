#!/usr/bin/env python3
"""Create the missing-taxonomy pilot packs and refresh the registry."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "common_protocol"))
from parse_pglib import parse_pglib_m  # noqa: E402

PROFILE = [0.72, 0.68, 0.70, 0.85, 1.00, 0.95, 0.88, 0.80]
SOLVE_SHIM = '''#!/usr/bin/env python3
from pathlib import Path
import sys

CASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from {module} import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    block = result["{block}"]
    print(
        f"[{{CASE_DIR.name}}] status={{block.get('status')}} obj={{block.get('obj', block.get('objective'))}}"
    )
'''
RUN_ALL = '''#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from {module} import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest:
        result = run_case(ROOT / item["case"], quiet=True)
        block = result["{block}"]
        print(f"[{{item['case']}}] status={{block.get('status')}} obj={{block.get('obj', block.get('objective'))}}")
        if block.get("status") != "OPTIMAL" or not block.get("validation_passed"):
            failures += 1
    print(f"done; failures={{failures}}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pglib_source(stem: str) -> dict[str, Any]:
    path = REPO / "数据集" / "pglib-opf-master" / f"{stem}.m"
    return {
        "dataset": "PGLib-OPF",
        "relative_path": f"数据集/pglib-opf-master/{stem}.m",
        "sha256": _sha256(path),
    }


def _features(
    *,
    n_bus: int,
    n_branch: int,
    n_gen: int,
    n_storage: int = 0,
    n_candidate_branch: int = 0,
    T: int = 1,
    n_contingency: int = 0,
    n_bin: int = 0,
    math_class: str,
    solver_family: str,
) -> dict[str, Any]:
    return {
        "n_bus": n_bus,
        "n_branch": n_branch,
        "n_gen": n_gen,
        "n_storage": n_storage,
        "n_candidate_branch": n_candidate_branch,
        "T": T,
        "n_contingency": n_contingency,
        "n_scenario": 1,
        "n_switchable": 0,
        "max_open": None,
        "k": None,
        "n_bin": n_bin,
        "math_class": math_class,
        "solver_family": solver_family,
    }


def _write_case(
    pack_dir: Path,
    name: str,
    *,
    network: dict[str, Any],
    config: dict[str, Any],
    module: str,
    block: str,
    readme: str,
) -> dict[str, Any]:
    case_dir = pack_dir / name
    _dump(case_dir / "data" / "network.json", network)
    _dump(case_dir / "data" / "config.json", config)
    _write_text(case_dir / "solve.py", SOLVE_SHIM.format(module=module, block=block))
    _write_text(case_dir / "README.md", readme)
    return {
        "case": name,
        "source": config.get("source_network"),
        "n_bus": config["features"]["n_bus"],
        "n_gen": config["features"]["n_gen"],
        "n_branch": config["features"]["n_branch"],
        "n_storage": config["features"]["n_storage"],
        "n_candidate_branch": config["features"]["n_candidate_branch"],
        "T": config["features"]["T"],
        "n_contingency": config["features"]["n_contingency"],
        "n_bin": config["features"]["n_bin"],
        "solve_tier": config["solve_tier"],
        "base_problem": config["base_problem"],
        "problem": config["problem"],
        "variant": config["variant"],
    }


def _write_pack(pack_dir: Path, module: str, block: str, title: str, body: str, rows: list[dict[str, Any]]) -> None:
    _dump(pack_dir / "MANIFEST.json", rows)
    _write_text(pack_dir / "run_all_python.py", RUN_ALL.format(module=module, block=block))
    _write_text(pack_dir / "README.md", f"# {title}\n\n{body}\n")


_ED_NETWORKS = {
    "pglib_opf_case3_lmbd": "DISPATCH/ECONOMIC-DISPATCH/case001_lmbd3_copperplate_ed/data/network.json",
    "pglib_opf_case5_pjm": "DISPATCH/ECONOMIC-DISPATCH/case002_pjm5_copperplate_ed/data/network.json",
    "pglib_opf_case14_ieee": "DISPATCH/ECONOMIC-DISPATCH/case003_ieee14_copperplate_ed/data/network.json",
}


def copperplate_from(stem: str, case_name: str) -> dict[str, Any]:
    src = _load_json(ROOT / _ED_NETWORKS[stem])
    return {
        "name": case_name,
        "source": stem,
        "baseMVA": src["baseMVA"],
        "time_periods": 8,
        "dt_hour": 1.0,
        "demand_profile": PROFILE,
        "buses": src["buses"],
        "gens": src["gens"],
    }


def build_demand_response() -> None:
    pack = ROOT / "DISPATCH" / "DEMAND-RESPONSE"
    rows = []
    mapping = [
        ("case001_lmbd3_dr", "pglib_opf_case3_lmbd", "lmbd3"),
        ("case002_pjm5_dr", "pglib_opf_case5_pjm", "pjm5"),
        ("case003_ieee14_dr", "pglib_opf_case14_ieee", "ieee14"),
    ]
    for name, stem, _label in mapping:
        net = copperplate_from(stem, name)
        net["demand_response"] = {
            "interruptible_frac": 0.15,
            "shiftable_frac": 0.10,
            "voll_per_MWh": 500.0,
        }
        config = {
            "schema_version": 1,
            "case": name,
            "base_problem": "demand_response",
            "problem": "demand_response",
            "variant": {
                "power_flow": "copperplate",
                "security": "none",
                "uncertainty": "deterministic",
                "horizon": "multi_period",
                "recourse": "none",
                "demand_flexibility": "interruptible_and_shiftable",
                "formulation": "interruptible_and_shiftable_demand",
                "network_constraints": "none",
            },
            "classification_note": "Copperplate multi-period dispatch with interruptible shed and energy-neutral load shifting.",
            "source": _pglib_source(stem),
            "construction": {
                "builder_version": 1,
                "seed": 1,
                "transformations": ["reuse_copperplate_ed_units", "add_8h_demand_profile_and_dr_offers"],
            },
            "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 1e-6, "TimeLimit": 120.0},
            "solve_tier": "full",
            "mip_gap": 1e-6,
            "time_limit": 120.0,
            "seed": 1,
            "threads": 1,
            "T": 8,
            "source_network": stem,
            "features": _features(
                n_bus=len(net["buses"]),
                n_branch=0,
                n_gen=len(net["gens"]),
                T=8,
                math_class="qp",
                solver_family="convex_dispatch",
            ),
        }
        rows.append(
            _write_case(
                pack,
                name,
                network=net,
                config=config,
                module="demand_response_model_py",
                block="demand_response",
                readme=f"# {name}\n\n8-hour copperplate demand-response dispatch on `{stem}`.\n",
            )
        )
    _write_pack(
        pack,
        "demand_response_model_py",
        "demand_response",
        "DEMAND-RESPONSE — interruptible and shiftable load",
        "真正的需求响应：机组费用 + 可中断负荷 VOLL + 跨时段能量守恒的可转移负荷。无网架。",
        rows,
    )


def build_storage() -> None:
    pack = ROOT / "SCHEDULING" / "STORAGE-SCHEDULING"
    specs = [
        (
            "case001_lmbd3_storage",
            "pglib_opf_case3_lmbd",
            [{"name": "ess1", "bus": 2, "Pmax_MW": 40.0, "Emax_MWh": 80.0, "E0_MWh": 40.0, "eta_c": 0.95, "eta_d": 0.95}],
        ),
        (
            "case002_pjm5_storage",
            "pglib_opf_case5_pjm",
            [
                {"name": "ess1", "bus": 1, "Pmax_MW": 50.0, "Emax_MWh": 100.0, "E0_MWh": 50.0, "eta_c": 0.95, "eta_d": 0.95},
                {"name": "ess2", "bus": 3, "Pmax_MW": 30.0, "Emax_MWh": 60.0, "E0_MWh": 30.0, "eta_c": 0.95, "eta_d": 0.95},
            ],
        ),
        (
            "case003_ieee14_storage",
            "pglib_opf_case14_ieee",
            [{"name": "ess1", "bus": 6, "Pmax_MW": 40.0, "Emax_MWh": 120.0, "E0_MWh": 60.0, "eta_c": 0.95, "eta_d": 0.95}],
        ),
    ]
    rows = []
    for name, stem, storage in specs:
        net = copperplate_from(stem, name)
        net["storage"] = storage
        config = {
            "schema_version": 1,
            "case": name,
            "base_problem": "storage_scheduling",
            "problem": "storage_scheduling",
            "variant": {
                "power_flow": "copperplate",
                "security": "none",
                "uncertainty": "deterministic",
                "horizon": "multi_period",
                "recourse": "none",
                "storage": "simple_energy_balance",
                "formulation": "storage_soc_energy_balance",
                "network_constraints": "none",
            },
            "classification_note": "Copperplate multi-period storage scheduling with cyclic SOC and charge/discharge efficiencies.",
            "source": _pglib_source(stem),
            "construction": {
                "builder_version": 1,
                "seed": 1,
                "transformations": ["reuse_copperplate_ed_units", "add_8h_profile_and_explicit_storage"],
            },
            "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 1e-6, "TimeLimit": 120.0},
            "solve_tier": "full",
            "mip_gap": 1e-6,
            "time_limit": 120.0,
            "seed": 1,
            "threads": 1,
            "T": 8,
            "source_network": stem,
            "features": _features(
                n_bus=len(net["buses"]),
                n_branch=0,
                n_gen=len(net["gens"]),
                n_storage=len(storage),
                T=8,
                math_class="qp",
                solver_family="temporal_mip" if False else "convex_dispatch",
            ),
        }
        rows.append(
            _write_case(
                pack,
                name,
                network=net,
                config=config,
                module="storage_scheduling_model_py",
                block="storage_scheduling",
                readme=f"# {name}\n\n8-hour copperplate storage scheduling on `{stem}`.\n",
            )
        )
    _write_pack(
        pack,
        "storage_scheduling_model_py",
        "storage_scheduling",
        "STORAGE-SCHEDULING — cyclic SOC energy inventory",
        "独立储能调度：SOC 动态、充放电效率、周期末回到初值。无网架。",
        rows,
    )


def build_microgrid() -> None:
    pack = ROOT / "DISTRIBUTION" / "MICROGRID"
    base = copperplate_from("pglib_opf_case5_pjm", "pjm5_microgrid")
    storage = [
        {"name": "ess1", "bus": 2, "Pmax_MW": 40.0, "Emax_MWh": 80.0, "E0_MWh": 40.0, "eta_c": 0.95, "eta_d": 0.95}
    ]
    renewable = [
        {
            "name": "pv1",
            "bus": 4,
            "Pmax_MW": 80.0,
            "profile": [0.00, 0.05, 0.20, 0.55, 0.85, 0.70, 0.25, 0.00],
        }
    ]
    cases = [
        (
            "case001_pjm5_microgrid_grid",
            False,
            "grid_connected",
            "microgrid_energy_management",
            {"import_max_MW": 200.0, "export_max_MW": 50.0, "import_price_per_MWh": 45.0, "export_price_per_MWh": 20.0, "islanded": False},
        ),
        (
            "case002_pjm5_microgrid_island",
            True,
            "islanded",
            "microgrid_energy_management",
            {"import_max_MW": 0.0, "export_max_MW": 0.0, "import_price_per_MWh": 45.0, "export_price_per_MWh": 20.0, "islanded": True},
        ),
        (
            "case003_pjm5_vpp",
            False,
            "grid_connected",
            "vpp_aggregation",
            {"import_max_MW": 250.0, "export_max_MW": 120.0, "import_price_per_MWh": 42.0, "export_price_per_MWh": 28.0, "islanded": False},
        ),
    ]
    rows = []
    for name, _island, island_mode, formulation, grid in cases:
        net = dict(base)
        net["name"] = name
        net["storage"] = storage
        net["renewable"] = renewable
        net["grid"] = grid
        config = {
            "schema_version": 1,
            "case": name,
            "base_problem": "microgrid",
            "problem": "microgrid" if formulation != "vpp_aggregation" else "vpp",
            "variant": {
                "power_flow": "copperplate",
                "security": "none",
                "uncertainty": "deterministic",
                "horizon": "multi_period",
                "recourse": "none",
                "storage": "simple_energy_balance",
                "island_mode": island_mode,
                "formulation": formulation,
                "network_constraints": "none",
            },
            "classification_note": "Copperplate microgrid/VPP energy management with thermal units, PV, storage and optional grid exchange.",
            "source": _pglib_source("pglib_opf_case5_pjm"),
            "construction": {
                "builder_version": 1,
                "seed": 1,
                "transformations": ["reuse_pjm5_units", "add_pv_storage_and_pcc_limits"],
            },
            "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 1e-6, "TimeLimit": 120.0},
            "solve_tier": "full",
            "mip_gap": 1e-6,
            "time_limit": 120.0,
            "seed": 1,
            "threads": 1,
            "T": 8,
            "source_network": "pglib_opf_case5_pjm",
            "features": _features(
                n_bus=len(net["buses"]),
                n_branch=0,
                n_gen=len(net["gens"]) + len(renewable),
                n_storage=len(storage),
                T=8,
                math_class="qp",
                solver_family="convex_dispatch",
            ),
        }
        rows.append(
            _write_case(
                pack,
                name,
                network=net,
                config=config,
                module="microgrid_model_py",
                block="microgrid",
                readme=f"# {name}\n\nCopperplate microgrid/VPP on PJM 5-bus, island_mode={island_mode}.\n",
            )
        )
    _write_pack(
        pack,
        "microgrid_model_py",
        "microgrid",
        "MICROGRID — islanded EMS and VPP aggregation",
        "并网微网、孤岛微网和 VPP 聚合三个铜板时序能量管理算例。含光伏可弃、储能 SOC 与联络线买卖电。",
        rows,
    )


def _radial_branch(fid: int, fbus: int, tbus: int, r_ohm: float, x_ohm: float, smax: float, vbase: float, base: float, invest: float | None = None) -> dict[str, Any]:
    zbase = vbase * vbase / base
    item = {
        "id": fid,
        "fbus": fbus,
        "tbus": tbus,
        "r_ohm": r_ohm,
        "x_ohm": x_ohm,
        "r_pu": r_ohm / zbase,
        "x_pu": x_ohm / zbase,
        "smax_MVA": smax,
    }
    if invest is not None:
        item["invest_cost"] = invest
    return item


def build_distribution_expansion() -> None:
    pack = ROOT / "PLANNING" / "DISTRIBUTION-EXPANSION"
    rows = []
    # 5-bus radial planning feeder. r/x from SimBench 15-AL1/3-ST1A 20 kV, 1 km class.
    vbase = 20.0
    base = 1.0
    buses5 = [
        {"bus_i": 1, "Pd": 0.0, "Qd": 0.0, "Vmin": 0.95, "Vmax": 1.05, "is_root": True},
        {"bus_i": 2, "Pd": 1.2, "Qd": 0.4, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 3, "Pd": 0.9, "Qd": 0.3, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 4, "Pd": 1.1, "Qd": 0.35, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 5, "Pd": 0.8, "Qd": 0.25, "Vmin": 0.95, "Vmax": 1.05},
    ]
    net5 = {
        "name": "case001_radial5_distexp",
        "baseMVA": base,
        "baseKV": vbase,
        "root_bus": 1,
        "substation_price_per_MWh": 40.0,
        "buses": buses5,
        "branches": [
            _radial_branch(1, 1, 2, 1.8769, 0.409, 4.0, vbase, base),
            _radial_branch(2, 2, 3, 1.8769, 0.409, 4.0, vbase, base),
        ],
        "ne_branches": [
            _radial_branch(3, 1, 4, 1.2012, 0.394, 4.0, vbase, base, 120.0),
            _radial_branch(4, 2, 4, 1.2012, 0.394, 3.0, vbase, base, 80.0),
            _radial_branch(5, 3, 5, 1.8769, 0.409, 3.0, vbase, base, 90.0),
            _radial_branch(6, 2, 5, 1.2012, 0.394, 3.0, vbase, base, 110.0),
            _radial_branch(7, 1, 5, 0.64, 0.145, 4.0, vbase, base, 160.0),
        ],
    }
    config5 = {
        "schema_version": 1,
        "case": "case001_radial5_distexp",
        "base_problem": "distribution_expansion",
        "problem": "distribution_expansion",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
            "radiality": "spanning_tree",
            "voltage_magnitude": "lindistflow_v_squared",
            "reactive_power": "lindistflow",
            "formulation": "lindistflow_candidate_feeders",
            "network_constraints": "radial_lindistflow_and_candidate_investment",
        },
        "classification_note": "Radial feeder expansion with LinDistFlow voltage drop, Q balance and spanning-tree radiality.",
        "source": {"dataset": "SimBench LineType", "system": "radial5_expansion", "note": "r/x from 15-AL1/3-ST1A 20.0 and 24-AL1/4-ST1A 20.0"},
        "construction": {"builder_version": 1, "seed": 1, "transformations": ["constructed_radial_feeder", "simbench_line_types"]},
        "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 1e-6, "TimeLimit": 120.0},
        "solve_tier": "full",
        "mip_gap": 1e-6,
        "time_limit": 120.0,
        "seed": 1,
        "threads": 1,
        "source_network": "simbench_linetype:radial5_expansion",
        "features": _features(
            n_bus=5,
            n_branch=2,
            n_gen=0,
            n_candidate_branch=5,
            n_bin=5,
            math_class="milp",
            solver_family="topology_mip",
        ),
    }
    rows.append(
        _write_case(
            pack,
            "case001_radial5_distexp",
            network=net5,
            config=config5,
            module="distribution_expansion_model_py",
            block="dist_exp",
            readme="# case001_radial5_distexp\n\n5-bus radial feeder expansion with LinDistFlow.\n",
        )
    )

    buses8 = [
        {"bus_i": 1, "Pd": 0.0, "Qd": 0.0, "Vmin": 0.95, "Vmax": 1.05, "is_root": True},
        {"bus_i": 2, "Pd": 0.7, "Qd": 0.2, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 3, "Pd": 0.6, "Qd": 0.18, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 4, "Pd": 0.5, "Qd": 0.15, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 5, "Pd": 0.8, "Qd": 0.25, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 6, "Pd": 0.4, "Qd": 0.12, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 7, "Pd": 0.55, "Qd": 0.16, "Vmin": 0.95, "Vmax": 1.05},
        {"bus_i": 8, "Pd": 0.45, "Qd": 0.14, "Vmin": 0.95, "Vmax": 1.05},
    ]
    net8 = {
        "name": "case002_radial8_distexp",
        "baseMVA": base,
        "baseKV": vbase,
        "root_bus": 1,
        "substation_price_per_MWh": 40.0,
        "buses": buses8,
        "branches": [
            _radial_branch(1, 1, 2, 1.2012, 0.394, 5.0, vbase, base),
            _radial_branch(2, 2, 3, 1.8769, 0.409, 4.0, vbase, base),
            _radial_branch(3, 3, 4, 1.8769, 0.409, 3.0, vbase, base),
        ],
        "ne_branches": [
            _radial_branch(4, 2, 5, 1.2012, 0.394, 3.0, vbase, base, 95.0),
            _radial_branch(5, 3, 5, 1.8769, 0.409, 3.0, vbase, base, 70.0),
            _radial_branch(6, 3, 6, 1.8769, 0.409, 2.5, vbase, base, 85.0),
            _radial_branch(7, 4, 6, 1.2012, 0.394, 2.5, vbase, base, 75.0),
            _radial_branch(8, 4, 7, 1.8769, 0.409, 2.5, vbase, base, 88.0),
            _radial_branch(9, 5, 8, 1.2012, 0.394, 2.5, vbase, base, 92.0),
            _radial_branch(10, 7, 8, 1.8769, 0.409, 2.5, vbase, base, 65.0),
            _radial_branch(11, 1, 8, 0.64, 0.145, 4.0, vbase, base, 180.0),
        ],
    }
    config8 = dict(config5)
    config8["case"] = "case002_radial8_distexp"
    config8["source"] = {"dataset": "SimBench LineType", "system": "radial8_expansion"}
    config8["source_network"] = "simbench_linetype:radial8_expansion"
    config8["features"] = _features(
        n_bus=8,
        n_branch=3,
        n_gen=0,
        n_candidate_branch=8,
        n_bin=8,
        math_class="milp",
        solver_family="topology_mip",
    )
    rows.append(
        _write_case(
            pack,
            "case002_radial8_distexp",
            network=net8,
            config=config8,
            module="distribution_expansion_model_py",
            block="dist_exp",
            readme="# case002_radial8_distexp\n\n8-bus radial feeder expansion with LinDistFlow.\n",
        )
    )
    _write_pack(
        pack,
        "distribution_expansion_model_py",
        "dist_exp",
        "DISTRIBUTION-EXPANSION — radial LinDistFlow TEP",
        "配网扩展：候选馈线投资 + LinDistFlow 电压降落/无功平衡 + 生成树径向性。阻抗取自 SimBench 线型。",
        rows,
    )


def _z_to_pu(r_ohm: list[list[float]], x_ohm: list[list[float]], vbase: float, base: float) -> tuple[list[list[float]], list[list[float]]]:
    zbase = vbase * vbase / base
    r_pu = [[val / zbase for val in row] for row in r_ohm]
    x_pu = [[val / zbase for val in row] for row in x_ohm]
    return r_pu, x_pu


def build_unbalanced() -> None:
    pack = ROOT / "DISTRIBUTION" / "UNBALANCED-DOPF"
    rows = []
    # IEEE PES 4-node style spot load, 12.47 kV, 2000 ft of 336 ACSR.
    miles = 2000.0 / 5280.0
    r_mile = [
        [0.4013, 0.0953, 0.0953],
        [0.0953, 0.4013, 0.0953],
        [0.0953, 0.0953, 0.4013],
    ]
    x_mile = [
        [1.4133, 0.8515, 0.7266],
        [0.8515, 1.4133, 0.7802],
        [0.7266, 0.7802, 1.4133],
    ]
    r_ohm = [[val * miles for val in row] for row in r_mile]
    x_ohm = [[val * miles for val in row] for row in x_mile]
    vbase = 12.47
    base = 6.0
    r_pu, x_pu = _z_to_pu(r_ohm, x_ohm, vbase, base)
    net4 = {
        "name": "case001_ieee4_unbalanced",
        "baseMVA": base,
        "baseKV": vbase,
        "root_bus": 1,
        "substation_price_per_MWh": 40.0,
        "buses": [
            {"bus_i": 1, "Pd_phase": [0.0, 0.0, 0.0], "Qd_phase": [0.0, 0.0, 0.0], "Vmin": 0.95, "Vmax": 1.05, "is_root": True},
            {"bus_i": 2, "Pd_phase": [0.0, 0.0, 0.0], "Qd_phase": [0.0, 0.0, 0.0], "Vmin": 0.95, "Vmax": 1.05},
            {"bus_i": 3, "Pd_phase": [0.0, 0.0, 0.0], "Qd_phase": [0.0, 0.0, 0.0], "Vmin": 0.95, "Vmax": 1.05},
            {
                "bus_i": 4,
                "Pd_phase": [1.275, 1.800, 2.375],
                "Qd_phase": [0.790, 0.872, 0.781],
                "Vmin": 0.95,
                "Vmax": 1.05,
            },
        ],
        "branches": [
            {
                "id": 1,
                "fbus": 1,
                "tbus": 2,
                "r_pu": r_pu,
                "x_pu": x_pu,
                "smax_MVA": 3.0,
            },
            {
                "id": 2,
                "fbus": 2,
                "tbus": 3,
                "r_pu": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                "x_pu": [[0.01, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.01]],
                "smax_MVA": 6.0,
                "note": "idealized transformer series reactance placeholder between IEEE 4-node buses 2-3",
            },
            {
                "id": 3,
                "fbus": 3,
                "tbus": 4,
                "r_pu": r_pu,
                "x_pu": x_pu,
                "smax_MVA": 3.0,
            },
        ],
    }
    config4 = {
        "schema_version": 1,
        "case": "case001_ieee4_unbalanced",
        "base_problem": "distribution_opf",
        "problem": "unbalanced_lindistflow_dopf",
        "variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
            "phases": "three",
            "voltage_magnitude": "three_phase_lindistflow",
            "reactive_power": "three_phase",
            "formulation": "three_phase_lindistflow",
            "network_constraints": "per_phase_pq_balance_and_3x3_voltage_drop",
        },
        "classification_note": "Unbalanced three-phase LinDistFlow OPF on an IEEE 4-node-style feeder. Linearized, not exact AC.",
        "source": {
            "dataset": "IEEE PES 4 Node Test Feeder",
            "system": "ieee4",
            "note": "336 ACSR 2000 ft Z-matrix and spot load from the IEEE PES test feeder documentation",
        },
        "construction": {"builder_version": 1, "seed": 1, "transformations": ["ieee4_spot_load", "lindistflow_3x3"]},
        "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 1e-6, "TimeLimit": 120.0},
        "solve_tier": "full",
        "mip_gap": 1e-6,
        "time_limit": 120.0,
        "seed": 1,
        "threads": 1,
        "source_network": "ieee_pes_4_node_test_feeder:ieee4",
        "features": _features(
            n_bus=4,
            n_branch=3,
            n_gen=0,
            math_class="lp",
            solver_family="convex_dispatch",
        ),
    }
    rows.append(
        _write_case(
            pack,
            "case001_ieee4_unbalanced",
            network=net4,
            config=config4,
            module="unbalanced_dopf_model_py",
            block="unbalanced_dopf",
            readme="# case001_ieee4_unbalanced\n\nIEEE 4-node-style unbalanced LinDistFlow OPF.\n",
        )
    )

    # Second feeder uses SMART-DS 3-phase 336 ACSR linecode, 0.4 km sections.
    r_km = [
        [0.2377333, 0.06463333, 0.06463333],
        [0.06463333, 0.2377333, 0.06463333],
        [0.06463333, 0.06463333, 0.2377333],
    ]
    x_km = [
        [0.6083333, 0.2055333, 0.2055333],
        [0.2055333, 0.6083333, 0.2055333],
        [0.2055333, 0.2055333, 0.6083333],
    ]
    length = 0.4
    r_ohm2 = [[val * length for val in row] for row in r_km]
    x_ohm2 = [[val * length for val in row] for row in x_km]
    vbase2 = 12.47
    base2 = 1.0
    r_pu2, x_pu2 = _z_to_pu(r_ohm2, x_ohm2, vbase2, base2)
    net6 = {
        "name": "case002_smartds_6bus_unbalanced",
        "baseMVA": base2,
        "baseKV": vbase2,
        "root_bus": 1,
        "substation_price_per_MWh": 40.0,
        "buses": [
            {"bus_i": 1, "Pd_phase": [0.0, 0.0, 0.0], "Qd_phase": [0.0, 0.0, 0.0], "Vmin": 0.95, "Vmax": 1.05, "is_root": True},
            {"bus_i": 2, "Pd_phase": [0.12, 0.08, 0.15], "Qd_phase": [0.04, 0.03, 0.05], "Vmin": 0.95, "Vmax": 1.05},
            {"bus_i": 3, "Pd_phase": [0.09, 0.14, 0.07], "Qd_phase": [0.03, 0.05, 0.02], "Vmin": 0.95, "Vmax": 1.05},
            {"bus_i": 4, "Pd_phase": [0.16, 0.05, 0.11], "Qd_phase": [0.05, 0.02, 0.04], "Vmin": 0.95, "Vmax": 1.05},
            {"bus_i": 5, "Pd_phase": [0.07, 0.13, 0.18], "Qd_phase": [0.02, 0.04, 0.06], "Vmin": 0.95, "Vmax": 1.05},
            {"bus_i": 6, "Pd_phase": [0.11, 0.10, 0.09], "Qd_phase": [0.03, 0.03, 0.03], "Vmin": 0.95, "Vmax": 1.05},
        ],
        "branches": [
            {"id": 1, "fbus": 1, "tbus": 2, "r_pu": r_pu2, "x_pu": x_pu2, "smax_MVA": 1.0},
            {"id": 2, "fbus": 2, "tbus": 3, "r_pu": r_pu2, "x_pu": x_pu2, "smax_MVA": 1.0},
            {"id": 3, "fbus": 3, "tbus": 4, "r_pu": r_pu2, "x_pu": x_pu2, "smax_MVA": 0.8},
            {"id": 4, "fbus": 3, "tbus": 5, "r_pu": r_pu2, "x_pu": x_pu2, "smax_MVA": 0.8},
            {"id": 5, "fbus": 5, "tbus": 6, "r_pu": r_pu2, "x_pu": x_pu2, "smax_MVA": 0.6},
        ],
    }
    config6 = dict(config4)
    config6["case"] = "case002_smartds_6bus_unbalanced"
    config6["source"] = {
        "dataset": "Constructed",
        "system": "smartds_336acsr_6bus",
        "linecode": "3P_OH_AL_ACSR_336kcmil_Merlin_3",
        "linecode_dataset": "SMART-DS",
    }
    config6["source_network"] = "constructed:smartds_336acsr_6bus"
    config6["classification_note"] = (
        "Unbalanced three-phase LinDistFlow on a 6-bus radial feeder using the SMART-DS 336 kcmil 3-phase linecode."
    )
    config6["features"] = _features(
        n_bus=6,
        n_branch=5,
        n_gen=0,
        math_class="lp",
        solver_family="convex_dispatch",
    )
    rows.append(
        _write_case(
            pack,
            "case002_smartds_6bus_unbalanced",
            network=net6,
            config=config6,
            module="unbalanced_dopf_model_py",
            block="unbalanced_dopf",
            readme="# case002_smartds_6bus_unbalanced\n\nSMART-DS linecode 6-bus unbalanced LinDistFlow OPF.\n",
        )
    )
    _write_pack(
        pack,
        "unbalanced_dopf_model_py",
        "unbalanced_dopf",
        "UNBALANCED-DOPF — three-phase LinDistFlow",
        "非平衡三相 LinDistFlow：每相 P/Q 平衡与 3×3 阻抗电压降落。这是线性化模型，不是精确三相 AC-PF。",
        rows,
    )


def build_scacopf() -> None:
    pack = ROOT / "OPF" / "SC-AC-OPF"
    rows = []
    cases = [
        (
            "case001_lmbd3_scacopf",
            ROOT / "OPF" / "AC-OPF" / "case001_lmbd3_acopf" / "data" / "network.json",
            "pglib_opf_case3_lmbd",
            [{"id": 1, "outaged_branches": [2], "label": "outage_br2"}, {"id": 2, "outaged_branches": [3], "label": "outage_br3"}],
            "selected_subset",
            1e-7,
            300.0,
        ),
        (
            "case002_pjm5_scacopf",
            ROOT / "OPF" / "AC-OPF" / "case002_pjm5_acopf" / "data" / "network.json",
            "pglib_opf_case5_pjm",
            [{"id": 1, "outaged_branches": [1], "label": "outage_br1"}, {"id": 2, "outaged_branches": [4], "label": "outage_br4"}],
            "sampled_subset",
            1e-6,
            600.0,
        ),
    ]
    for name, net_path, stem, ctgs, scope, gap, tlim in cases:
        net = _load_json(net_path)
        net["name"] = name
        net["contingencies"] = ctgs
        config = {
            "schema_version": 1,
            "case": name,
            "base_problem": "opf",
            "problem": "sc_ac_opf",
            "variant": {
                "power_flow": "ac_exact",
                "security": "n-1" if scope == "selected_subset" else "sampled_n-1",
                "uncertainty": "deterministic",
                "horizon": "single_period",
                "recourse": "preventive",
                "generation_recourse": "corrective_within_generator_bounds",
                "contingency_scope": scope,
                "formulation": "polar_ac_preventive_n1",
                "network_constraints": "nodal_pq_balance_voltage_angle_and_two_end_mva_limits",
            },
            "classification_note": "Exact polar AC-OPF with shared preventive Pg and per-state voltage/reactive redispatch after selected line outages.",
            "source": _pglib_source(stem),
            "construction": {
                "builder_version": 1,
                "seed": 1,
                "transformations": ["reuse_ac_opf_network", "add_selected_line_contingencies"],
            },
            "gurobi_parameters": {
                "Seed": 1,
                "Threads": 1,
                "MIPGap": gap,
                "TimeLimit": tlim,
                "NonConvex": 2,
            },
            "solve_tier": "full",
            "mip_gap": gap,
            "time_limit": tlim,
            "seed": 1,
            "threads": 1,
            "source_network": stem,
            "features": _features(
                n_bus=len(net["buses"]),
                n_branch=len(net["branches"]),
                n_gen=len(net["gens"]),
                n_contingency=len(ctgs),
                math_class="nlp",
                solver_family="nonconvex_ac",
            ),
        }
        case_dir = pack / name
        _dump(case_dir / "data" / "network.json", net)
        _dump(case_dir / "data" / "config.json", config)
        _write_text(
            case_dir / "python" / "solve_scacopf.py",
            """#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from scacopf_model import run_case  # noqa: E402

if __name__ == "__main__":
    result = run_case(CASE_DIR, quiet=True)
    solution = result["scacopf"]
    print(f"[{result['case']}] status={solution['status']} obj={solution.get('obj')} n_cont={solution.get('n_cont')}")
""",
        )
        _write_text(
            case_dir / "solve.py",
            """#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "python" / "solve_scacopf.py"), run_name="__main__")
""",
        )
        _write_text(case_dir / "README.md", f"# {name}\n\nPreventive exact SC-AC-OPF on `{stem}`.\n")
        rows.append(
            {
                "case": name,
                "path": name,
                "source": stem,
                "n_bus": config["features"]["n_bus"],
                "n_gen": config["features"]["n_gen"],
                "n_branch": config["features"]["n_branch"],
                "n_contingency": config["features"]["n_contingency"],
                "solve_tier": "full",
                "base_problem": "opf",
                "problem": "sc_ac_opf",
                "variant": config["variant"],
            }
        )
    _write_pack(
        pack,
        "scacopf_model",
        "scacopf",
        "SC-AC-OPF — preventive exact polar N-1",
        "精确极坐标预防性 SC-AC-OPF。基态与事故态共享 Pg；电压、无功和潮流按状态重解。不是 GO 线性化模型。",
        rows,
    )
    # overwrite run_all because pack uses path-style AC-OPF cases
    _write_text(
        pack / "run_all_python.py",
        """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from scacopf_model import run_case  # noqa: E402


def main() -> int:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = 0
    for item in manifest:
        result = run_case(ROOT / item["case"], quiet="--verbose" not in sys.argv)
        block = result["scacopf"]
        print(f"[{item['case']}] status={block.get('status')} obj={block.get('obj')} valid={block.get('validation_passed')}")
        if block.get("status") != "OPTIMAL" or not block.get("validation_passed"):
            failures += 1
    print(f"done; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
    )


def build_ieee30_acopf() -> None:
    stem = "pglib_opf_case30_ieee"
    raw = parse_pglib_m(REPO / "数据集" / "pglib-opf-master" / f"{stem}.m")
    name = "case004_ieee30_acopf"
    net = {
        "name": name,
        "source": stem,
        "baseMVA": raw["baseMVA"],
        "buses": raw["buses"],
        "gens": raw["gens"],
        "branches": raw["branches"],
    }
    pack = ROOT / "OPF" / "AC-OPF"
    case_dir = pack / name
    config = {
        "schema_version": 1,
        "case": name,
        "base_problem": "opf",
        "problem": "ac_opf",
        "variant": {
            "power_flow": "ac_exact",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
            "cost_model": "quadratic_if_present",
            "formulation": "polar_ac_power_flow",
            "network_constraints": "nodal_pq_balance_voltage_angle_and_two_end_mva_limits",
        },
        "source": _pglib_source(stem),
        "construction": {"builder_version": 1, "seed": 1, "transformations": ["exact_ac_opf_pilot_from_pglib"]},
        "gurobi_parameters": {"Seed": 1, "Threads": 1, "MIPGap": 0.001, "TimeLimit": 900.0, "NonConvex": 2},
        "solve_tier": "full",
        "mip_gap": 0.001,
        "time_limit": 900.0,
        "seed": 1,
        "threads": 1,
        "source_network": stem,
        "features": _features(
            n_bus=len(net["buses"]),
            n_branch=len(net["branches"]),
            n_gen=len(net["gens"]),
            math_class="nlp",
            solver_family="nonconvex_ac",
        ),
        "classification_note": "Exact nonconvex polar AC-OPF with explicit P/Q balance and two-end MVA limits.",
    }
    _dump(case_dir / "data" / "network.json", net)
    _dump(case_dir / "data" / "config.json", config)
    (case_dir / "python").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pack / "case003_ieee14_acopf" / "python" / "solve_acopf.py", case_dir / "python" / "solve_acopf.py")
    shutil.copyfile(pack / "case003_ieee14_acopf" / "solve.py", case_dir / "solve.py")
    _write_text(case_dir / "README.md", f"# {name}\n\nExact polar AC-OPF on IEEE 30-bus PGLib.\n")
    manifest = _load_json(pack / "MANIFEST.json")
    if not any(row.get("case") == name for row in manifest):
        manifest.append(
            {
                "case": name,
                "source": stem,
                "n_bus": config["features"]["n_bus"],
                "n_gen": config["features"]["n_gen"],
                "n_branch": config["features"]["n_branch"],
                "solve_tier": "full",
                "base_problem": "opf",
                "problem": "ac_opf",
                "variant": config["variant"],
                "path": name,
            }
        )
        _dump(pack / "MANIFEST.json", manifest)


def patch_registry() -> None:
    path = ROOT / "BASE_PROBLEM_REGISTRY.json"
    data = _load_json(path)
    bases = data["base_problems"]
    bases["demand_response"] = {"id": "B24", "label": "Demand response"}
    bases["storage_scheduling"] = {"id": "B25", "label": "Storage scheduling"}
    bases["distribution_expansion"] = {"id": "B26", "label": "Distribution expansion"}
    bases["microgrid"] = {"id": "B27", "label": "Microgrid and VPP"}
    variants = data["variant_dimensions"]
    extras = {
        "demand_flexibility": ["interruptible_and_shiftable"],
        "island_mode": ["grid_connected", "islanded"],
        "phases": ["one", "three"],
    }
    for key, values in extras.items():
        variants[key] = sorted(set(variants.get(key, []) + values))
    for key, values in {
        "formulation": [
            "interruptible_and_shiftable_demand",
            "storage_soc_energy_balance",
            "lindistflow_candidate_feeders",
            "microgrid_energy_management",
            "vpp_aggregation",
            "three_phase_lindistflow",
            "polar_ac_preventive_n1",
        ],
        "network_constraints": [
            "radial_lindistflow_and_candidate_investment",
            "per_phase_pq_balance_and_3x3_voltage_drop",
        ],
        "voltage_magnitude": ["lindistflow_v_squared", "three_phase_lindistflow"],
        "reactive_power": ["lindistflow", "three_phase"],
        "radiality": ["spanning_tree"],
    }.items():
        variants[key] = sorted(set(variants.get(key, []) + values))
    packs = data["packs"]
    packs["DISPATCH/DEMAND-RESPONSE"] = {
        "navigation_domain": "DISPATCH",
        "base_problem": "demand_response",
        "default_math_class": "qp",
        "allowed_math_classes": ["lp", "qp"],
        "default_solver_family": "convex_dispatch",
        "allowed_solver_families": ["convex_dispatch"],
        "default_variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    }
    packs["SCHEDULING/STORAGE-SCHEDULING"] = {
        "navigation_domain": "SCHEDULING",
        "base_problem": "storage_scheduling",
        "default_math_class": "qp",
        "allowed_math_classes": ["lp", "qp"],
        "default_solver_family": "convex_dispatch",
        "allowed_solver_families": ["convex_dispatch"],
        "default_variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    }
    packs["PLANNING/DISTRIBUTION-EXPANSION"] = {
        "navigation_domain": "PLANNING",
        "base_problem": "distribution_expansion",
        "default_math_class": "milp",
        "allowed_math_classes": ["milp"],
        "default_solver_family": "topology_mip",
        "allowed_solver_families": ["topology_mip"],
        "default_variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    }
    packs["DISTRIBUTION/MICROGRID"] = {
        "navigation_domain": "DISTRIBUTION",
        "base_problem": "microgrid",
        "default_math_class": "qp",
        "allowed_math_classes": ["lp", "qp"],
        "default_solver_family": "convex_dispatch",
        "allowed_solver_families": ["convex_dispatch"],
        "default_variant": {
            "power_flow": "copperplate",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "multi_period",
            "recourse": "none",
        },
    }
    packs["DISTRIBUTION/UNBALANCED-DOPF"] = {
        "navigation_domain": "DISTRIBUTION",
        "base_problem": "distribution_opf",
        "default_math_class": "lp",
        "allowed_math_classes": ["lp", "qp"],
        "default_solver_family": "convex_dispatch",
        "allowed_solver_families": ["convex_dispatch"],
        "default_variant": {
            "power_flow": "lindistflow",
            "security": "none",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "none",
        },
    }
    packs["OPF/SC-AC-OPF"] = {
        "navigation_domain": "OPF",
        "base_problem": "opf",
        "default_math_class": "nlp",
        "allowed_math_classes": ["nlp"],
        "default_solver_family": "nonconvex_ac",
        "allowed_solver_families": ["nonconvex_ac"],
        "default_variant": {
            "power_flow": "ac_exact",
            "security": "sampled_n-1",
            "uncertainty": "deterministic",
            "horizon": "single_period",
            "recourse": "preventive",
        },
    }
    _dump(path, data)


def patch_source_network_helpers() -> None:
    path = ROOT / "framework" / "features.py"
    text = path.read_text(encoding="utf-8")
    needle = '        if "ACTIVSg200" in dataset:\n            return "pglib_opf_case200_activ"'
    extra = '''        if "IEEE PES 4 Node" in dataset:
            return f"ieee_pes_4_node_test_feeder:{src.get('system') or 'ieee4'}"
        if dataset == "SimBench LineType":
            return f"simbench_linetype:{src.get('system') or 'unknown'}"'''
    if "ieee_pes_4_node_test_feeder" not in text:
        text = text.replace(needle, extra + "\n" + needle)
        path.write_text(text, encoding="utf-8")


def patch_evaluate_and_bins() -> None:
    ev = ROOT / "framework" / "evaluate.py"
    text = ev.read_text(encoding="utf-8")
    old = '''    "dcopf",
)'''
    new = '''    "dcopf",
    "demand_response",
    "storage_scheduling",
    "dist_exp",
    "microgrid",
    "unbalanced_dopf",
)'''
    if "demand_response" not in text:
        ev.write_text(text.replace(old, new), encoding="utf-8")
    feat = ROOT / "framework" / "features.py"
    text = feat.read_text(encoding="utf-8")
    needle = '''    if "TRANSMISSION-EXPANSION" in p:
        return n_ne or n_branch'''
    extra = '''    if "DISTRIBUTION-EXPANSION" in p:
        return n_ne
    if "DEMAND-RESPONSE" in p or "STORAGE-SCHEDULING" in p or "MICROGRID" in p or "UNBALANCED-DOPF" in p or "SC-AC-OPF" in p or "AC-OPF" in p:
        return 0'''
    if "DISTRIBUTION-EXPANSION" not in text:
        feat.write_text(text.replace(needle, extra + "\n" + needle), encoding="utf-8")


def main() -> int:
    patch_registry()
    patch_source_network_helpers()
    patch_evaluate_and_bins()
    build_demand_response()
    build_storage()
    build_microgrid()
    build_distribution_expansion()
    build_unbalanced()
    build_scacopf()
    build_ieee30_acopf()
    print("gap pilots written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
