#!/usr/bin/env python3
"""Build linearized security-constrained OPF and OTS cases from GO C1 scenarios."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parents[2]
sys.path.insert(0, str(ROOT / "common"))
from parse_go_c1 import load_scenario  # noqa: E402

GO = WS / "数据集" / "GO Competition Challenge 1"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def select_contingencies(net: dict, max_n: int) -> list[dict]:
    conts = net.get("contingencies_all") or []
    # prefer branch contingencies then gen
    branch = [c for c in conts if c.get("branch")]
    gen = [c for c in conts if c.get("gen_bus") is not None]
    chosen = branch[: max_n // 2] + gen[: max_n - max_n // 2]
    if len(chosen) < max_n:
        for c in conts:
            if c not in chosen:
                chosen.append(c)
            if len(chosen) >= max_n:
                break
    return chosen[:max_n]


def pick_switchable(net: dict, k: int = 8) -> list[int]:
    # highest rateA non-transformer lines
    lines = [b for b in net["branches"] if b.get("kind") == "line" and int(b.get("status", 1)) == 1]
    lines = sorted(lines, key=lambda b: -float(b["rateA"]))
    return [int(b["id"]) for b in lines[:k]]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    raws = sorted(GO.rglob("case.raw"))
    # only Trial_Event scenarios under Used_Scenarios
    raws = [p for p in raws if "Used_Scenarios" in str(p)]
    manifest = []
    case_no = 0
    for raw in raws:
        try:
            net = load_scenario(raw)
        except Exception as exc:  # noqa: BLE001
            print(f"SKIP {raw}: {exc}")
            continue
        nB = len(net["buses"])
        nG = len(net["gens"])
        nG_online = len([g for g in net["gens"] if int(g.get("status", 1)) == 1])
        nL = len(net["branches"])
        if nB <= 200:
            tier, nc, tl, gap = "full", 8, 120.0, 0.01
        elif nB <= 1000:
            tier, nc, tl, gap = "relaxed", 5, 180.0, 0.02
        else:
            tier, nc, tl, gap = "skip", 3, 60.0, 0.05

        rel = raw.relative_to(GO)
        parts = rel.parts
        # .../T1S3_Offline/Network_01O-3/scenario_1/case.raw
        tag = "_".join(slug(x) for x in parts[-4:-1]) if len(parts) >= 4 else slug(raw.parent.name)
        network_folder = next(
            (part for part in parts if part.lower().startswith("network_")),
            raw.parent.name,
        )

        for mode in ("scacopf", "scacots"):
            case_no += 1
            if mode != "scacopf":
                continue
            enable_ots = mode == "scacots"
            cont = select_contingencies(net, nc)
            sw = pick_switchable(net, 8 if enable_ots else 0)
            case = f"case{case_no:03d}_{tag}_{mode}"
            case_dir = ROOT / case
            (case_dir / "data").mkdir(parents=True, exist_ok=True)
            (case_dir / "results").mkdir(exist_ok=True)
            payload = {
                "name": case,
                "baseMVA": net["baseMVA"],
                "buses": net["buses"],
                "gens": net["gens"],
                "branches": net["branches"],
                "contingencies": cont,
                "source_files": net.get("source_files", {}),
            }
            (case_dir / "data" / "network.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            config = {
                "schema_version": 1,
                "case": case,
                "problem": f"linearized_{mode}",
                "mode": mode,
                "source": {
                    "dataset": "GO Competition Challenge 1",
                    "raw": str(raw.relative_to(WS)),
                },
                "enable_ots": enable_ots,
                "switchable_branches": sw,
                "max_open": 2 if enable_ots else 0,
                "mip_gap": gap,
                "time_limit": tl if tier != "skip" else 1.0,
                "seed": 1,
                "threads": 0,
                "solve_tier": tier,
                "load_shed_penalty": 10000.0,
                "base_problem": "ots" if enable_ots else "opf",
                "variant": {
                    "power_flow": "dc_linearized",
                    "security": "sampled_n-1",
                    "contingency_scope": "sampled_subset",
                    "uncertainty": "deterministic",
                    "horizon": "single_period",
                    "recourse": "corrective_limited",
                    "generation_recourse": "corrective_within_generator_bounds",
                },
                "construction": [
                    f"Linearized DC security-constrained {'OTS' if enable_ots else 'OPF'} (NOT exact AC).",
                    "Security constraints cover a sampled subset of case.con contingencies "
                    "(branch + generator), not the complete N-1 set.",
                    "OTS candidates = top rateA lines; max_open=2." if enable_ots else "OPF only.",
                    f"nB={nB}, nG={nG} ({nG_online} online), nL={nL}, Nc={len(cont)}, tier={tier}",
                ],
                "source_network": f"go_c1:{network_folder}",
                "features": {
                    "n_bus": nB,
                    "n_branch": nL,
                    "n_gen": nG,
                    "n_storage": 0,
                    "n_candidate_branch": 0,
                    "T": 1,
                    "n_contingency": len(cont),
                    "n_scenario": 1,
                    "n_switchable": len(sw),
                    "max_open": 2 if enable_ots else 0,
                    "k": None,
                    "n_bin": len(sw),
                    "math_class": "milp" if enable_ots else "lp",
                    "solver_family": "security_mip",
                },
            }
            (case_dir / "data" / "config.json").write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
            write_text(
                case_dir / "python" / "solve_scacopf.py",
                """#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from scacopf_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)["scacopf"]
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

- Source: `{raw.relative_to(WS)}`
- Linearized DC security-constrained {'OTS' if enable_ots else 'OPF'} (approximation; not exact AC; sampled contingency subset)
- Buses={nB}, gens={nG} ({nG_online} online), branches={nL}, contingencies={len(cont)}, tier={tier}
""",
            )
            manifest.append(
                {
                    "case": case,
                    "mode": mode,
                    "raw": str(raw.relative_to(WS)),
                    "n_bus": nB,
                    "n_gen": nG,
                    "n_gen_online": nG_online,
                    "n_branch": nL,
                    "n_cont": len(cont),
                    "solve_tier": tier,
                }
            )
            print(f"built {case} nB={nB} tier={tier}")

    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    cases = "\n".join(f"    '{m['case']}'" for m in manifest if m["solve_tier"] != "skip")
    write_text(
        ROOT / "run_all_matlab.m",
        f"""function run_all_matlab()
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here,'common'));
cases = {{
{cases}
}};
for i=1:numel(cases)
    try
        run_case_mat(fullfile(here,cases{{i}}));
    catch ME
        fprintf('[%s] ERROR %s\\n', cases{{i}}, ME.message);
    end
end
end
""",
    )
    write_text(
        ROOT / "run_all_python.py",
        """#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/"common"))
from scacopf_model_py import run_case
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="full,relaxed")
    args = ap.parse_args()
    tiers = set(args.tier.split(","))
    manifest = json.loads((ROOT/"MANIFEST.json").read_text())
    fail=0
    for item in manifest:
        if item.get("solve_tier") not in tiers and "all" not in tiers:
            continue
        try:
            r = run_case(ROOT/item["case"], quiet=True)["scacopf"]
            obj = "None" if r.get("obj") is None else f"{r['obj']:.4f}"
            print(f"[{item['case']}] status={r.get('status')} obj={obj} t={r.get('runtime',0):.2f}s", flush=True)
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
        """# Linearized Security-Constrained OPF / OTS (GO Challenge 1)

**Approximation notice:** models are **DC security-constrained OPF** (linear), not exact nonconvex AC.
Each case covers a sampled subset of `case.con`, not the complete N-1 set.
This OPF builder emits only the `scacopf` case for each GO C1 scenario.
Contingency-state generation may redispatch anywhere within `0 <= Pg <= Pmax`:
`recourse=corrective_limited`,
`generation_recourse=corrective_within_generator_bounds`.

```bash
python3 common/build_all_from_go_c1.py
python3 run_all_python.py --tier full,relaxed
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
""",
    )
    print(f"TOTAL cases {len(manifest)} from {len(raws)} raw files")


if __name__ == "__main__":
    main()
