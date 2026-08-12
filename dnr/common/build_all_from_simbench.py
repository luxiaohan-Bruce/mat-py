#!/usr/bin/env python3
"""Build LinDistFlow-DNR cases from SimBench MV/LV switchable feeders."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parent
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
    manifest = []
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
            case_dir = ROOT / case
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
                "problem": f"lindistflow_{mode}",
                "source": {"dataset": "SimBench", "folder": folder},
                "T": T,
                "mip_gap": 0.01,
                "time_limit": 120.0,
                "seed": 1,
                "threads": 0,
                "solve_tier": "full",
                "max_switch_actions": 5,
                "construction": [
                    "LinDistFlow radial DNR / multiperiod DOPF (linear approx).",
                    "Switchable = Switch.csv edges (+ subset of lines if needed).",
                    "ESS only in dnr_ess variants.",
                ],
            }
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
                case_dir / "matlab" / "run_case.m",
                """function run_case()
here=fileparts(mfilename('fullpath')); case_dir=fileparts(here);
addpath(fullfile(fileparts(case_dir),'common')); run_case_mat(case_dir);
end
""",
            )
            write_text(case_dir / "README.md", f"# {case}\n\nSimBench `{folder}` LinDistFlow `{mode}` T={T}\n")
            manifest.append({"case": case, "folder": folder, "mode": mode, "T": T, "solve_tier": "full"})

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
                "solve_tier": "skip",
                "source": {"dataset": "SimBench", "folder": "1-complete_data-mixed-all-2-sw"},
            },
            indent=2,
        )
        + "\n"
    )
    write_text(case_dir / "README.md", "# complete mixed meta\n\nProfile source only (skip solve).\n")
    manifest.append({"case": case, "folder": "1-complete_data-mixed-all-2-sw", "mode": "meta", "solve_tier": "skip"})

    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    cases = "\n".join(f"    '{m['case']}'" for m in manifest if m["solve_tier"] != "skip")
    write_text(
        ROOT / "run_all_matlab.m",
        f"""function run_all_matlab()
here=fileparts(mfilename('fullpath')); addpath(fullfile(here,'common'));
cases={{
{cases}
}};
for i=1:numel(cases), try, run_case_mat(fullfile(here,cases{{i}})); catch ME, fprintf('[%s] ERROR %s\\n',cases{{i}},ME.message); end; end
end
""",
    )
    write_text(
        ROOT / "run_all_python.py",
        """#!/usr/bin/env python3
import json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'common'))
from dnr_model_py import run_case
def main():
    man=json.loads((ROOT/'MANIFEST.json').read_text()); fail=0
    for item in man:
        if item.get('solve_tier')=='skip':
            print(f"[{item['case']}] SKIP"); continue
        try:
            r=run_case(ROOT/item['case'],quiet=True)['dnr']
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
        """# SimBench LinDistFlow DNR / DOPF / DNR+ESS

Linear distribution network reconfiguration (not exact AC). Built from SimBench MV/LV switchable feeders; complete mixed dataset kept as meta/profile source.

```bash
python3 common/build_all_from_simbench.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
""",
    )
    print(f"generated {len(manifest)} dnr cases")


if __name__ == "__main__":
    main()
