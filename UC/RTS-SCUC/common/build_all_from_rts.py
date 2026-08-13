#!/usr/bin/env python3
"""Build network-constrained SCUC cases: RTS-GMLC topology + PGLib-UC day instances."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parent
RTS = WS / "数据集" / "RTS-GMLC-master" / "RTS_Data" / "SourceData"
UC_DIR = WS / "数据集" / "pglib-uc-master" / "rts_gmlc"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bus_from_uid(uid: str) -> int:
    m = re.match(r"(\d+)_", uid)
    if not m:
        raise ValueError(uid)
    return int(m.group(1))


def is_bridge(n_bus: int, edges: list[tuple[int, int]], drop: int) -> bool:
    """Undirected connectivity after dropping edge index drop."""
    adj: dict[int, list[int]] = defaultdict(list)
    for i, (a, b) in enumerate(edges):
        if i == drop:
            continue
        adj[a].append(b)
        adj[b].append(a)
    if not edges:
        return False
    start = edges[0][0] if drop != 0 else edges[min(1, len(edges) - 1)][0]
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) < n_bus


def build_network_skeleton() -> dict:
    buses_raw = _read_csv(RTS / "bus.csv")
    branches_raw = _read_csv(RTS / "branch.csv")
    gens_raw = _read_csv(RTS / "gen.csv")
    storage_raw = _read_csv(RTS / "storage.csv")

    buses = []
    for b in buses_raw:
        bid = int(b["Bus ID"])
        btype = 2 if b["Bus Type"] in ("PV", "REF") else 1
        if b["Bus Type"] == "Ref" or float(b.get("V Angle", "0")) == 0.0 and bid in (113, 213, 313):
            # RTS uses area refs; mark bus 113 as system ref later
            pass
        buses.append(
            {
                "bus_i": bid,
                "type": 3 if bid == 113 else (2 if b["Bus Type"] in ("PV", "Ref", "REF") else 1),
                "Pd": float(b["MW Load"]),
                "Qd": float(b["MVAR Load"]),
                "area": int(float(b["Area"])),
                "baseKV": float(b["BaseKV"]),
                "Vm": float(b["V Mag"]),
                "Va": float(b["V Angle"]),
            }
        )
    # ensure one type-3
    if not any(int(b["type"]) == 3 for b in buses):
        buses[0]["type"] = 3

    branches = []
    edge_pairs = []
    for i, br in enumerate(branches_raw, 1):
        f = int(br["From Bus"])
        t = int(br["To Bus"])
        x = float(br["X"])
        if abs(x) < 1e-6:
            x = 1e-5
        rateA = float(br["Cont Rating"]) or 9999.0
        rateC = float(br["STE Rating"]) or rateA * 1.1
        branches.append(
            {
                "id": i,
                "uid": br["UID"],
                "fbus": f,
                "tbus": t,
                "r": float(br["R"]),
                "x": x,
                "b": float(br["B"]),
                "rateA": rateA,
                "rateB": float(br["LTE Rating"]) or rateA,
                "rateC": rateC,
                "ratio": float(br["Tr Ratio"] or 0.0),
                "status": 1,
            }
        )
        edge_pairs.append((f, t))

    gen_bus = {row["GEN UID"]: int(row["Bus ID"]) for row in gens_raw}
    # storage: unique head reservoirs as ESS proxies
    storage = []
    seen = set()
    for row in storage_raw:
        if row.get("position", "").lower() != "head":
            continue
        name = row["Storage"]
        if name in seen:
            continue
        seen.add(name)
        emax = float(row["Max Volume GWh"] or 0.0) * 1000.0  # MWh
        pmax = float(row["Rating MVA"] or 0.0)
        if emax <= 0 or pmax <= 0:
            continue
        e0 = float(row["Initial Volume GWh"] or 0.0) * 1000.0
        storage.append(
            {
                "name": name,
                "bus": bus_from_uid(row["GEN UID"]),
                "Pmax_MW": pmax,
                "Emax_MWh": emax,
                "E0_MWh": min(max(e0, 0.0), emax),
                "eta_c": 0.95,
                "eta_d": 0.95,
            }
        )

    # contingencies: first 6 non-bridge AC branches with highest rateA
    n_bus = len(buses)
    ranked = sorted(range(len(branches)), key=lambda i: -branches[i]["rateA"])
    cont = []
    for i in ranked:
        if is_bridge(n_bus, edge_pairs, i):
            continue
        cont.append(branches[i]["id"])
        if len(cont) >= 6:
            break

    return {
        "baseMVA": 100.0,
        "buses": buses,
        "branches": branches,
        "gen_bus": gen_bus,
        "storage": storage,
        "contingencies": cont,
        "Pd_total": sum(b["Pd"] for b in buses),
    }


def linear_cost_from_pwl(gen: dict) -> tuple[float, float]:
    """Return (no_load_or_base_cost, slope $/MWh) from PWL points."""
    pts = gen["piecewise_production"]
    p0 = float(pts[0]["mw"])
    c0 = float(pts[0]["cost"])
    p1 = float(pts[-1]["mw"])
    c1 = float(pts[-1]["cost"])
    width = max(p1 - p0, 1e-6)
    slope = (c1 - c0) / width
    return c0, slope


def startup_cost(gen: dict) -> float:
    starts = gen.get("startup") or []
    if not starts:
        return 0.0
    return float(starts[-1]["cost"])


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    skel = build_network_skeleton()
    files = sorted(UC_DIR.glob("*.json"))
    manifest = []
    for n, src in enumerate(files, 1):
        uc = json.loads(src.read_text(encoding="utf-8"))
        T_full = int(uc["time_periods"])
        # use 24h for network SCUC tractability (first day half of 48h instances)
        T = min(24, T_full)
        demand = [float(x) for x in uc["demand"][:T]]
        reserves = [float(x) for x in uc["reserves"][:T]]
        Pd_total = max(skel["Pd_total"], 1.0)
        # bus load fractions from static RTS Pd
        bus_frac = {int(b["bus_i"]): float(b["Pd"]) / Pd_total for b in skel["buses"]}

        thermal = []
        for name, g in uc["thermal_generators"].items():
            bus = skel["gen_bus"].get(name, bus_from_uid(name))
            base_cost, slope = linear_cost_from_pwl(g)
            thermal.append(
                {
                    "name": name,
                    "bus": bus,
                    "Pmin": float(g["power_output_minimum"]),
                    "Pmax": float(g["power_output_maximum"]),
                    "RU": float(g["ramp_up_limit"]),
                    "RD": float(g["ramp_down_limit"]),
                    "UT": int(g["time_up_minimum"]),
                    "DT": int(g["time_down_minimum"]),
                    "u0": int(g["unit_on_t0"]),
                    "p0": float(g["power_output_t0"]),
                    "must_run": int(g.get("must_run", 0)),
                    "base_cost": base_cost,
                    "slope": slope,
                    "startup": startup_cost(g),
                    "shutdown": 0.0,
                }
            )

        renewable = []
        for name, g in uc.get("renewable_generators", {}).items():
            bus = skel["gen_bus"].get(name)
            if bus is None:
                try:
                    bus = bus_from_uid(name)
                except ValueError:
                    bus = int(skel["buses"][0]["bus_i"])
            renewable.append(
                {
                    "name": name,
                    "bus": bus,
                    "pmin": [float(x) for x in g["power_output_minimum"][:T]],
                    "pmax": [float(x) for x in g["power_output_maximum"][:T]],
                }
            )

        # store base fraction only; model multiplies demand[t]*frac[bus]
        # list form for MATLAB-friendly JSON (avoid numeric object keys)
        bus_frac_list = [
            {"bus": int(b["bus_i"]), "frac": float(bus_frac[int(b["bus_i"])])}
            for b in skel["buses"]
        ]
        network = {
            "name": f"rts_gmlc_{src.stem}",
            "source": {
                "network": "RTS-GMLC",
                "uc": str(src.relative_to(WS)),
            },
            "baseMVA": skel["baseMVA"],
            "buses": skel["buses"],
            "branches": skel["branches"],
            "thermal": thermal,
            "renewable": renewable,
            "storage": skel["storage"],
            "bus_load_fraction": bus_frac_list,
            "demand_MW": demand,
            "reserve_MW": reserves,
        }
        payload = json.dumps(network, indent=2).encode()
        case = f"case{n:02d}_rts_gmlc_{src.stem.replace('-', '_')}_rts_scuc"
        case_dir = ROOT / case
        (case_dir / "data").mkdir(parents=True, exist_ok=True)
        (case_dir / "results").mkdir(exist_ok=True)
        (case_dir / "data" / "network.json").write_bytes(payload)
        config = {
            "schema_version": 1,
            "case": case,
            "problem": "rts_scuc",
            "source": network["source"],
            "T": T,
            "contingencies": skel["contingencies"],
            "emergency_rate_factor": 1.0,
            "load_shed_penalty": 5000.0,
            "mip_gap": 0.01,
            "time_limit": 300.0,
            "seed": 1,
            "threads": 0,
            "solve_tier": "full",
            "base_problem": "uc",
            "variant": {
                "power_flow": "dc",
                "security": "sampled_n-1",
                "contingency_scope": "selected_subset",
                "uncertainty": "deterministic",
                "horizon": "multi_period",
                "recourse": "preventive",
                "storage": "yes",
            },
            "construction": [
                "Topology/storage from RTS-GMLC SourceData; thermal/renewable/demand/reserve from PGLib-UC rts_gmlc day file.",
                "Horizon = first 24 periods of the 48h UC instance.",
                "Preventive DC-SCUC with system reserve, ESS, optional load shed, and a selected subset of six non-bridge line contingencies.",
                "Thermal production cost: linear envelope of PWL endpoints + startup of longest-lag category.",
            ],
        }
        (case_dir / "data" / "config.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8"
        )
        write_text(
            case_dir / "python" / "solve_rts_scuc.py",
            """#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from rts_scuc_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)["scuc"]
    obj = "None" if r.get("obj") is None else f"{r['obj']:.6f}"
    print(f"[{CASE_DIR.name}] status={r.get('status')} obj={obj} t={r.get('runtime',0):.2f}s")
""",
        )
        write_text(
            case_dir / "matlab" / "run_case.m",
            """function run_case()
here = fileparts(mfilename('fullpath'));
case_dir = fileparts(here);
addpath(fullfile(fileparts(case_dir), 'common'));
run_case_mat(case_dir);
end
""",
        )
        write_text(
            case_dir / "README.md",
            f"""# {case}

- UC day: `{src.name}` (PGLib-UC)
- Network: RTS-GMLC (73 bus)
- T={T}, Nc={len(skel['contingencies'])}, thermal={len(thermal)}, renewable={len(renewable)}, storage={len(skel['storage'])}
- Preventive DC-SCUC + ESS + reserve + selected N-1 subset
""",
        )
        manifest.append(
            {
                "case": case,
                "uc_source": str(src.relative_to(WS)),
                "T": T,
                "n_thermal": len(thermal),
                "n_renewable": len(renewable),
                "n_storage": len(skel["storage"]),
                "n_contingencies": len(skel["contingencies"]),
                "solve_tier": "full",
            }
        )

    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    cases = "\n".join(f"    '{m['case']}'" for m in manifest)
    write_text(
        ROOT / "run_all_matlab.m",
        f"""function run_all_matlab()
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'common'));
cases = {{
{cases}
}};
for i=1:numel(cases)
    run_case_mat(fullfile(here,cases{{i}}));
end
end
""",
    )
    write_text(
        ROOT / "run_all_python.py",
        """#!/usr/bin/env python3
from __future__ import annotations
import json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "common"))
from rts_scuc_model_py import run_case
def main():
    manifest = json.loads((ROOT/"MANIFEST.json").read_text())
    fail=0
    for item in manifest:
        try:
            r = run_case(ROOT/item["case"], quiet=True)["scuc"]
            obj = "None" if r.get("obj") is None else f"{r['obj']:.4f}"
            print(f"[{item['case']}] status={r.get('status')} obj={obj} gap={r.get('mip_gap')} t={r.get('runtime',0):.2f}s", flush=True)
            if r.get("obj") is None: fail += 1
        except Exception as e:
            fail += 1
            print(f"[{item['case']}] ERROR {e}", flush=True)
            traceback.print_exc()
    print(f"done; failures={fail}")
    return 1 if fail else 0
if __name__ == "__main__":
    raise SystemExit(main())
""",
    )
    write_text(
        ROOT / "README.md",
        """# RTS-GMLC network SCUC (MATLAB ↔ Python / Gurobi)

Combines **RTS-GMLC** transmission topology (and ESS proxies) with all **12** PGLib-UC `rts_gmlc` day instances.

**base_problem**: UC
**variant**: power_flow=dc, security=sampled_n-1, contingency_scope=selected_subset, horizon=multi_period, recourse=preventive

Model: preventive DC-SCUC, system spinning reserve, renewable bounds, storage SOC, optional load-shed, and a selected subset of six non-bridge line contingencies. The package does not claim exhaustive N-1 coverage.

```bash
python3 common/build_all_from_rts.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
""",
    )
    print(f"generated {len(manifest)} rts_scuc cases; contingencies={skel['contingencies']}")


if __name__ == "__main__":
    main()
