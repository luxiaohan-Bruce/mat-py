#!/usr/bin/env python3
"""Build experimental active-power transport cases from SimBench feeders."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOPF_ROOT = ROOT.parent / "DISTRIBUTION-OPF"
WS = ROOT.parents[2]
SB = WS / "数据集" / "SimBench"

# small/medium feeders fully modeled; complete_data used only for profiles
SOURCES = [
    ("1-MV-rural--0-sw", "mv_rural"),
    ("1-LV-rural2--0-sw", "lv_rural2"),
]


def read_semi(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def build_network(folder: str) -> dict:
    base = SB / folder
    nodes = read_semi(base / "Node.csv")
    lines = read_semi(base / "Line.csv")
    loads = read_semi(base / "Load.csv")
    switches = read_semi(base / "Switch.csv") if (base / "Switch.csv").exists() else []
    ltypes = {}
    if (base / "LineType.csv").exists():
        for r in read_semi(base / "LineType.csv"):
            ltypes[r["id"]] = r

    bus_ids = []
    bus_index = {}
    buses = []
    for i, n in enumerate(nodes):
        name = n["id"]
        bus_ids.append(name)
        bus_index[name] = i
        buses.append(
            {
                "bus_i": i + 1,
                "name": name,
                "Vm_min": float(n.get("vmMin") or 0.9),
                "Vm_max": float(n.get("vmMax") or 1.1),
                "Pd": 0.0,
                "Qd": 0.0,
                "is_root": n.get("type") == "busbar" and "HV" in name,
            }
        )
    # root: first busbar or first node
    # choose root as node with maximum degree in line graph for connectivity
    from collections import Counter

    deg = Counter()
    for ln in lines:
        deg[ln["nodeA"]] += 1
        deg[ln["nodeB"]] += 1
    if deg:
        root_name = max(deg, key=lambda k: deg[k])
        root = bus_index.get(root_name, 0)
    else:
        root = next((i for i, b in enumerate(buses) if b["is_root"]), 0)
    for b in buses:
        b["is_root"] = False
    buses[root]["is_root"] = True

    # loads in MW (SimBench pLoad already MW-ish; keep as is)
    for ld in loads:
        node = ld["node"]
        # attach to node or node without _suffix
        key = node if node in bus_index else None
        if key is None:
            for name in bus_index:
                if name.startswith(node):
                    key = name
                    break
        if key is None:
            continue
        bi = bus_index[key]
        buses[bi]["Pd"] += float(ld.get("pLoad") or 0.0)
        buses[bi]["Qd"] += float(ld.get("qLoad") or 0.0)

    branches = []
    bid = 0
    for ln in lines:
        a, b = ln["nodeA"], ln["nodeB"]
        if a not in bus_index or b not in bus_index:
            continue
        length_km = float(ln.get("length") or 0.1)
        typ = ltypes.get(ln.get("type") or "", {})
        # r,x ohm/km -> pu-like scaled later as absolute ohms; use simple r,x proportional to length
        r_ohm = float(typ.get("r") or 0.2) * length_km
        x_ohm = float(typ.get("x") or 0.2) * length_km
        if r_ohm < 1e-6:
            r_ohm = 1e-4
        if x_ohm < 1e-6:
            x_ohm = 1e-4
        rate = float(ln.get("loadingMax") or 100.0)
        # convert loadingMax percent placeholder to MW capacity synthetic
        pmax = max(rate / 100.0 * 5.0, 0.5)  # heuristic MW capacity
        bid += 1
        branches.append(
            {
                "id": bid,
                "fbus": bus_index[a] + 1,
                "tbus": bus_index[b] + 1,
                "r": r_ohm,
                "x": x_ohm,
                "rate": pmax,
                "switchable": False,
                "name": ln["id"],
            }
        )

    # switches as additional candidate edges (closed=cond 1)
    for sw in switches:
        a, b = sw["nodeA"], sw["nodeB"]
        if a not in bus_index or b not in bus_index:
            continue
        if bus_index[a] == bus_index[b]:
            continue
        bid += 1
        branches.append(
            {
                "id": bid,
                "fbus": bus_index[a] + 1,
                "tbus": bus_index[b] + 1,
                "r": 0.05,
                "x": 0.05,
                "rate": 5.0,
                "switchable": True,
                "name": sw["id"],
                "init_closed": int(float(sw.get("cond") or 1)),
            }
        )

    # mark a subset of lines switchable if few switches
    if sum(1 for b in branches if b.get("switchable")) < 5:
        for br in branches[:: max(1, len(branches) // 10)][:10]:
            br["switchable"] = True

    return {
        "name": folder,
        "baseMVA": 1.0,
        "root_bus": root + 1,
        "buses": buses,
        "branches": branches,
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    dnr_manifest = []
    dopf_manifest = []
    n = 0
    for folder, slug in SOURCES:
        net = build_network(folder)
        # peak DNR + multiperiod DOPF (T=4 using synthetic mult)
        for mode, T, mults in [
            ("dnr", 1, [1.0]),
            ("dopf", 4, [0.6, 0.8, 1.0, 0.9]),
            ("dnr_ess", 4, [0.6, 0.8, 1.0, 0.9]),
        ]:
            n += 1
            case = f"case{n:02d}_{slug}_{mode}"
            package_root = DOPF_ROOT if mode == "dopf" else ROOT
            case_dir = package_root / case
            (case_dir / "data").mkdir(parents=True, exist_ok=True)
            (case_dir / "results").mkdir(exist_ok=True)
            storage = []
            if mode == "dnr_ess":
                # place ESS at highest load bus
                top = max(net["buses"], key=lambda b: b["Pd"])
                storage = [
                    {
                        "bus": top["bus_i"],
                        "Pmax": 0.5,
                        "Emax": 2.0,
                        "E0": 1.0,
                        "eta_c": 0.95,
                        "eta_d": 0.95,
                    }
                ]
            payload = dict(net)
            payload["storage"] = storage
            payload["load_mult"] = mults
            (case_dir / "data" / "network.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            config = {
                "schema_version": 1,
                "case": case,
                "problem": f"active_power_transport_{mode}",
                "mode": mode,
                "source": {"dataset": "SimBench", "folder": folder},
                "T": T,
                "mip_gap": 0.01,
                "time_limit": 120.0,
                "seed": 1,
                "threads": 0,
                "solve_tier": "full",
                "maturity": "experimental",
                "validation_scope": "structural_only",
                "physics_validated": False,
                "max_switch_actions": 5,
                "construction": [
                    "Active-power transport proxy for exploratory distribution studies.",
                    "Switchable = Switch.csv edges (+ subset of lines if needed).",
                    "ESS only in dnr_ess variants.",
                ],
                "known_limitations": [
                    "No voltage-magnitude variables or voltage-drop equations.",
                    "No reactive-power balance or reactive-device coupling.",
                    "No radiality or energized-connectivity constraints.",
                ],
                "base_problem": "distribution_opf" if mode == "dopf" else "dnr",
                "variant": {
                    "power_flow": "active_power_transport",
                    "reactive_power": "not_modeled",
                    "voltage_magnitude": "not_modeled",
                    "radiality": "not_enforced",
                    "security": "none",
                    "uncertainty": "deterministic",
                    "horizon": "single_period" if T == 1 else "multi_period",
                    "recourse": "none",
                },
                "source_network": f"simbench:{folder}",
                "features": {
                    "n_bus": len(payload["buses"]),
                    "n_branch": len(payload["branches"]),
                    "n_gen": 0,
                    "n_storage": len(storage),
                    "n_candidate_branch": 0,
                    "T": T,
                    "n_contingency": 0,
                    "n_scenario": 1,
                    "n_switchable": sum(bool(br.get("switchable")) for br in payload["branches"]),
                    "max_open": None,
                    "k": None,
                    "n_bin": len(payload["branches"]),
                    "math_class": "milp",
                    "solver_family": "topology_mip",
                },
            }
            if mode == "dopf":
                config["variant"].update(
                    {
                        "formulation": "multiperiod_active_power_transport_proxy",
                        "network_constraints": "active_power_nodal_balance_and_branch_limits",
                    }
                )
            if mode == "dnr_ess":
                config["variant"]["storage"] = "yes"
            (case_dir / "data" / "config.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
            write_text(
                case_dir / "python" / "solve_dnr.py",
                """#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE_DIR.parent/'common'))
from dnr_model_py import run_case
if __name__=='__main__':
    r=run_case(CASE_DIR,quiet=True)['dnr']
    print(f"[{CASE_DIR.name}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s")
""",
            )
            write_text(
                case_dir / "README.md",
                f"# {case}\n\nSimBench `{folder}` active-power transport `{mode}`, T={T}. "
                "**Experimental / structural-only; not physics validated.**\n\n"
                "No voltage/drop equations, reactive-power balance, or radiality/connectivity constraints are enforced.\n",
            )
            item = {
                "case": case,
                "folder": folder,
                "mode": mode,
                "T": T,
                "solve_tier": "full",
                "maturity": "experimental",
                "validation_scope": "structural_only",
                "physics_validated": False,
                "base_problem": config["base_problem"],
                "problem": config["problem"],
                "variant": config["variant"],
            }
            (dopf_manifest if mode == "dopf" else dnr_manifest).append(item)

    # complete_data profiles note case (data-only)
    n += 1
    case = f"case{n:02d}_complete_mixed_profile_meta"
    case_dir = ROOT / case
    (case_dir / "data").mkdir(parents=True, exist_ok=True)
    (case_dir / "results").mkdir(exist_ok=True)
    meta = {
        "name": case,
        "source": "1-complete_data-mixed-all-2-sw",
        "note": "Large mixed network retained as profile/meta reference; not solved as full MIP.",
        "files": ["Line.csv", "Node.csv", "LoadProfile.csv"],
    }
    (case_dir / "data" / "network.json").write_text(json.dumps(meta, indent=2) + "\n")
    (case_dir / "data" / "config.json").write_text(
        json.dumps(
            {
                "case": case,
                "problem": "meta",
                "mode": "meta",
                "solve_tier": "skip",
                "maturity": "data_only",
                "validation_scope": "not_solved",
                "physics_validated": False,
                "source": {"dataset": "SimBench", "folder": "1-complete_data-mixed-all-2-sw"},
                "base_problem": "dnr",
                "variant": {"power_flow": "none"},
                "source_network": "simbench:1-complete_data-mixed-all-2-sw",
                "features": {
                    "n_bus": 0,
                    "n_branch": 0,
                    "n_gen": 0,
                    "n_storage": 0,
                    "n_candidate_branch": 0,
                    "T": 1,
                    "n_contingency": 0,
                    "n_scenario": 1,
                    "n_switchable": 0,
                    "max_open": None,
                    "k": None,
                    "n_bin": 0,
                    "math_class": "none",
                    "solver_family": "none",
                },
            },
            indent=2,
        )
        + "\n"
    )
    write_text(
        case_dir / "README.md",
        "# complete mixed meta\n\nProfile source only (`solve_tier=skip`). **Data-only; no model or physics-validation claim.**\n",
    )
    dnr_manifest.append(
        {
            "case": case,
            "folder": "1-complete_data-mixed-all-2-sw",
            "mode": "meta",
            "solve_tier": "skip",
            "maturity": "data_only",
            "validation_scope": "not_solved",
            "physics_validated": False,
            "base_problem": "dnr",
            "problem": "meta",
            "variant": {"power_flow": "none"},
        }
    )

    manifest_path = ROOT / "MANIFEST.json"
    existing = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    replacements = {item["case"]: item for item in dnr_manifest}
    merged = [replacements.pop(item["case"], item) for item in existing]
    merged.extend(replacements.values())
    manifest_path.write_text(json.dumps(merged, indent=2) + "\n")
    DOPF_ROOT.mkdir(parents=True, exist_ok=True)
    (DOPF_ROOT / "MANIFEST.json").write_text(json.dumps(dopf_manifest, indent=2) + "\n")
    write_text(
        ROOT / "run_all_python.py",
        """#!/usr/bin/env python3
import json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from dnr_model_py import run_case as run_dnr
from smartds_model_py import run_case as run_smartds
def main():
    man = json.loads((ROOT / "MANIFEST.json").read_text()); fail = 0
    for item in man:
        if item.get("solve_tier") == "skip":
            print(f"[{item['case']}] SKIP"); continue
        try:
            case_dir = ROOT / item["case"]
            cfg = json.loads((case_dir / "data" / "config.json").read_text())
            if "smartds" in str(cfg.get("problem") or ""):
                r = run_smartds(case_dir, quiet=True)["smartds"]
            else:
                r = run_dnr(case_dir, quiet=True)["dnr"]
            print(f"[{item['case']}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get("obj") is None: fail += 1
        except Exception as e:
            fail += 1; print(f"[{item['case']}] ERROR {e}"); traceback.print_exc()
    print(f"done; failures={fail}"); return 1 if fail else 0
if __name__ == "__main__":
    raise SystemExit(main())
""",
    )
    write_text(
        ROOT / "README.md",
        """# Experimental active-power transport DNR / DNR+ESS

Structural-only examples built from SimBench MV/LV switchable feeders. They omit voltage/drop equations, reactive-power balance, and radiality/connectivity constraints, and are not physics-validated DNR coverage. The complete mixed dataset is kept as a data/profile source.

```bash
python3 common/build_all_from_simbench.py
python3 run_all_python.py
python3 common/compare_results.py
```
""",
    )
    print(f"generated {len(dnr_manifest)} dnr cases and {len(dopf_manifest)} distribution-opf cases")


if __name__ == "__main__":
    main()
