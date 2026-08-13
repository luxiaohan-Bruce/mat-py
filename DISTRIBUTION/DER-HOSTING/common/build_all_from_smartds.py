#!/usr/bin/env python3
"""Build the experimental SMART-DS DER-hosting placeholder."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parents[2]
SRC = WS / "数据集" / "SMART-DS" / "GSO-rural-base_peak-rhs1_1247--rdt137"


def parse_buses(path: Path) -> list[str]:
    names = []
    for line in path.read_text(errors="replace").splitlines():
        m = re.search(r"Bus\s*=\s*([^\s,!]+)", line, re.I)
        if m:
            names.append(m.group(1).strip())
    # unique preserve order
    seen = set()
    out = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def parse_lines(path: Path) -> list[tuple[str, str]]:
    edges = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip().lower().startswith("new line"):
            continue
        b1 = re.search(r"Bus1\s*=\s*([^\s.]+)", line, re.I)
        b2 = re.search(r"Bus2\s*=\s*([^\s.]+)", line, re.I)
        if b1 and b2:
            edges.append((b1.group(1), b2.group(1)))
    return edges


def parse_loads(path: Path) -> dict[str, float]:
    loads = {}
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip().lower().startswith("new load"):
            continue
        bus = re.search(r"Bus1\s*=\s*([^\s.]+)", line, re.I)
        kw = re.search(r"kW\s*=\s*([0-9.eE+-]+)", line, re.I)
        if bus and kw:
            b = bus.group(1)
            loads[b] = loads.get(b, 0.0) + float(kw.group(1)) / 1000.0  # MW
    return loads


def aggregate(max_nodes: int = 80) -> dict:
    """Coarsen large OpenDSS feeder to ~max_nodes for full dual solves."""
    buses = parse_buses(SRC / "Buscoords.dss")
    if not buses:
        # fallback from lines
        edges = parse_lines(SRC / "Lines.dss")
        nodes = []
        seen = set()
        for a, b in edges:
            for x in (a, b):
                if x not in seen:
                    seen.add(x)
                    nodes.append(x)
        buses = nodes
    edges = parse_lines(SRC / "Lines.dss")
    loads = parse_loads(SRC / "Loads.dss")
    # Stable, order-preserving selection: feeder-front buses plus high-load buses.
    load_buses = sorted(loads, key=lambda b: (-loads[b], b))[: max_nodes // 2]
    keep = []
    seen = set()
    for name in buses[: max_nodes // 2] + load_buses + buses:
        if name not in seen:
            seen.add(name)
            keep.append(name)
        if len(keep) == max_nodes:
            break
    keep_set = set(keep)
    bus_index = {n: i + 1 for i, n in enumerate(keep)}
    bus_list = [
        {"bus_i": i + 1, "name": n, "Pd": float(loads.get(n, 0.0)), "Qd": 0.0, "Vm_min": 0.95, "Vm_max": 1.05}
        for i, n in enumerate(keep)
    ]
    # root = first
    branches = []
    bid = 0
    # Keep the checked-in 80-bus/90-branch aggregate contract deterministic.
    target_branches = len(keep) + len(keep) // 8
    induced_limit = max(0, target_branches - max(0, len(keep) - 1))
    for a, b in edges:
        if a in keep_set and b in keep_set:
            bid += 1
            branches.append(
                {
                    "id": bid,
                    "fbus": bus_index[a],
                    "tbus": bus_index[b],
                    "r": 0.05,
                    "x": 0.05,
                    "rate": 5.0,
                    "switchable": bid % 7 == 0,
                }
            )
            if len(branches) >= induced_limit:
                break
    # if graph sparse, connect path
    if len(branches) < len(keep) - 1:
        for i in range(1, len(keep)):
            bid += 1
            branches.append(
                {
                    "id": bid,
                    "fbus": 1,
                    "tbus": i + 1,
                    "r": 0.08,
                    "x": 0.08,
                    "rate": 8.0,
                    "switchable": i % 5 == 0,
                }
            )
    if max_nodes == 80 and (len(bus_list) != 80 or len(branches) != 90):
        raise RuntimeError(
            f"SMART-DS aggregate contract changed: buses={len(bus_list)}, branches={len(branches)}"
        )
    return {
        "name": "smartds_gso_rural_agg",
        "baseMVA": 1.0,
        "root_bus": 1,
        "buses": bus_list,
        "branches": branches,
        "source": str(SRC.relative_to(WS)),
        "aggregation": f"first/top-load {len(keep)} buses from OpenDSS feeder",
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    net = aggregate(80)
    variants = [(3, "hosting", {"problem": "smartds_experimental_der_hosting_proxy", "mode": "hosting", "der_candidates": 10})]
    manifest = []
    for i, slug, extra in variants:
        case = f"case{i:02d}_gso_rural_{slug}"
        case_dir = ROOT / case
        (case_dir / "data").mkdir(parents=True, exist_ok=True)
        (case_dir / "results").mkdir(exist_ok=True)
        payload = dict(net)
        payload["load_mult"] = [1.0]
        if slug == "voltvar":
            # shunt caps at high Pd buses
            top = sorted(payload["buses"], key=lambda b: -b["Pd"])[:5]
            payload["shunts"] = [{"bus": b["bus_i"], "Qmax": 0.2} for b in top]
        if slug == "hosting":
            top = sorted(payload["buses"], key=lambda b: b["Pd"])[:10]
            payload["der"] = [{"bus": b["bus_i"], "Pmax": 0.3} for b in top]
        (case_dir / "data" / "network.json").write_text(json.dumps(payload, indent=2) + "\n")
        config = {
            "schema_version": 1,
            "case": case,
            "problem": extra["problem"],
            "mode": slug,
            "source": {"dataset": "SMART-DS", "feeder": "GSO-rural-base_peak-rhs1_1247--rdt137"},
            "T": 1,
            "mip_gap": 0.01,
            "time_limit": 120.0,
            "seed": 1,
            "threads": 0,
            "solve_tier": "full",
            "maturity": "experimental",
            "validation_scope": "structural_only",
            "physics_validated": False,
            "max_switch_actions": 4,
            "construction": [
                "Aggregated OpenDSS feeder (~80 nodes) for dual solvability.",
                "Active-power transport proxy; not LinDistFlow or exact three-phase AC.",
                f"variant={slug}",
            ],
            "known_limitations": [
                "No voltage-magnitude variables, voltage-drop equations, or reactive-power balance.",
                "DER injection is only a secondary objective term; the model does not maximize or certify hosting capacity.",
                "No radiality or energized-connectivity constraints.",
            ],
            "base_problem": "der_hosting",
            "variant": {
                "power_flow": "active_power_transport",
                "reactive_power": "not_modeled",
                "voltage_magnitude": "not_modeled",
                "radiality": "not_enforced",
                "formulation": "experimental_der_injection_proxy",
                "security": "none",
                "uncertainty": "deterministic",
                "horizon": "single_period",
                "recourse": "none",
            },
            "source_network": "smartds:GSO-rural-base_peak-rhs1_1247--rdt137",
            "features": {
                "n_bus": len(payload["buses"]),
                "n_branch": len(payload["branches"]),
                "n_gen": 0,
                "n_storage": 0,
                "n_candidate_branch": 0,
                "T": 1,
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
        (case_dir / "data" / "config.json").write_text(json.dumps(config, indent=2) + "\n")
        write_text(
            case_dir / "python" / "solve_smartds.py",
            """#!/usr/bin/env python3
from pathlib import Path
import sys
CASE_DIR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE_DIR.parent/'common'))
from smartds_model_py import run_case
if __name__=='__main__':
    r=run_case(CASE_DIR,quiet=True)['smartds']
    print(f"[{CASE_DIR.name}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s")
""",
        )
        write_text(
            case_dir / "README.md",
            f"# {case}\n\nSMART-DS aggregated-feeder `{slug}` placeholder. "
            "**Experimental / structural-only; not physics validated.**\n\n"
            "The objective does not maximize hosting capacity, and voltage/reactive-power equations are absent.\n",
        )
        manifest.append(
            {
                "case": case,
                "mode": slug,
                "solve_tier": "full",
                "maturity": "experimental",
                "validation_scope": "structural_only",
                "physics_validated": False,
                "base_problem": "der_hosting",
                "problem": config["problem"],
                "variant": config["variant"],
            }
        )
    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    write_text(
        ROOT / "run_all_python.py",
        """#!/usr/bin/env python3
import json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'common'))
from smartds_model_py import run_case
def main():
    man=json.loads((ROOT/'MANIFEST.json').read_text()); fail=0
    for item in man:
        try:
            r=run_case(ROOT/item['case'],quiet=True)['smartds']
            print(f"[{item['case']}] status={r.get('status')} obj={r.get('obj')} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get('obj') is None: fail+=1
        except Exception as e:
            fail+=1; print(f"[{item['case']}] ERROR {e}"); traceback.print_exc()
    print(f'done; failures={fail}'); return 1 if fail else 0
if __name__=='__main__':
    raise SystemExit(main())
""",
    )
    write_text(
        ROOT / "README.md",
        """# DER-HOSTING

> **Maturity:** experimental · **validation:** structural only · **physics validated:** no

SMART-DS active-power transport placeholder. The objective does not maximize hosting capacity and voltage/reactive-power equations are absent, so this is not physics-validated DER-hosting coverage.

```bash
python3 common/build_all_from_smartds.py
python3 run_all_python.py
```
""",
    )
    print("generated", len(manifest), "smartds cases; n_bus", len(net["buses"]))


if __name__ == "__main__":
    main()
