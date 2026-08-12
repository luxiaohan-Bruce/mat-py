#!/usr/bin/env python3
"""Generate one MATLAB/Python UC case for every PGLib-UC JSON instance."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
SOURCE = WORKSPACE / "数据集" / "pglib-uc-master"
GROUP_ORDER = {"rts_gmlc": 0, "ca": 1, "ferc": 2}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def validate(data: dict, source: Path) -> None:
    T = int(data["time_periods"])
    if len(data["demand"]) != T or len(data["reserves"]) != T:
        raise ValueError(f"{source}: time-series length mismatch")
    for name, gen in data["thermal_generators"].items():
        points = gen["piecewise_production"]
        if not points:
            raise ValueError(f"{source}: {name} has no production-cost points")
        if abs(float(points[0]["mw"]) - float(gen["power_output_minimum"])) > 1e-6:
            raise ValueError(f"{source}: {name} first cost point != Pmin")
        last_slope = float("-inf")
        for left, right in zip(points, points[1:]):
            width = float(right["mw"]) - float(left["mw"])
            if width <= 0:
                raise ValueError(f"{source}: {name} non-increasing PWL MW points")
            slope = (float(right["cost"]) - float(left["cost"])) / width
            if slope + 1e-7 < last_slope:
                raise ValueError(f"{source}: {name} non-convex PWL cost")
            last_slope = slope
        lags = [int(item["lag"]) for item in gen["startup"]]
        if not lags or lags != sorted(lags):
            raise ValueError(f"{source}: {name} invalid startup lags")
    for name, gen in data.get("renewable_generators", {}).items():
        if len(gen["power_output_minimum"]) != T or len(gen["power_output_maximum"]) != T:
            raise ValueError(f"{source}: {name} renewable time-series length mismatch")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    files = sorted(
        SOURCE.glob("*/*.json"),
        key=lambda p: (GROUP_ORDER.get(p.parent.name, 99), p.name),
    )
    manifest = []
    matlab_names = []
    for number, source in enumerate(files, 1):
        data = json.loads(source.read_text(encoding="utf-8"))
        validate(data, source)
        case_name = f"case{number:02d}_{source.parent.name}_{slug(source.stem)}_uc"
        case_dir = ROOT / case_name
        data_dir = case_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "results").mkdir(exist_ok=True)
        payload = source.read_bytes()
        (data_dir / "network.json").write_bytes(payload)

        n_thermal = len(data["thermal_generators"])
        if n_thermal <= 100:
            tier = "full"
            mip_gap = 0.01  # matches official PGLib-UC reference default
            time_limit = 180.0
            threads = 1
        elif n_thermal <= 700:
            tier = "large"
            mip_gap = 0.01
            time_limit = 300.0
            threads = 0  # all cores; dual compare uses gap-based tolerance
        else:
            tier = "xlarge"
            mip_gap = 0.02
            time_limit = 600.0
            threads = 0
        config = {
            "schema_version": 1,
            "case": case_name,
            "problem": "uc",
            "source": {
                "dataset": "PGLib-UC",
                "relative_path": str(source.relative_to(WORKSPACE)),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            "solve_tier": tier,
            "mip_gap": mip_gap,
            "time_limit": time_limit,
            "seed": 1,
            "threads": threads,
            "construction": [
                "All thermal, renewable, demand, reserve, initial-state, ramp, minimum up/down, startup-lag and PWL-cost data are preserved.",
                "The mathematical model follows the official PGLib-UC reference equations and uses gurobipy/Gurobi in Python.",
                "Solver tolerances follow PGLib-UC practice (MIPGap≈1%) with tiered time limits for large instances.",
            ],
        }
        (data_dir / "config.json").write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        write_text(
            case_dir / "python" / "solve_uc.py",
            """#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
CASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CASE_DIR.parent / "common"))
from uc_model_py import run_case
if __name__ == "__main__":
    r = run_case(CASE_DIR, quiet=True)["uc"]
    obj = "None" if r["obj"] is None else f"{r['obj']:.6f}"
    print(f"[{CASE_DIR.name}] status={r['status']} obj={obj} gap={r.get('mip_gap')} t={r['runtime']:.2f}s")
""",
        )
        write_text(
            case_dir / "matlab" / "run_case.m",
            f"""function run_case()
here = fileparts(mfilename('fullpath'));
case_dir = fileparts(here);
addpath(fullfile(fileparts(case_dir), 'common'));
run_case_mat(case_dir);
end
""",
        )
        write_text(
            case_dir / "README.md",
            f"""# {case_name}

- Source: `数据集/pglib-uc-master/{source.parent.name}/{source.name}`
- Horizon: {data['time_periods']} periods
- Thermal generators: {n_thermal}
- Renewable generators: {len(data.get('renewable_generators', {}))}
- Model: deterministic UC with reserve, ramping, minimum up/down time, startup categories and convex PWL production cost
- Solvers: MATLAB Gurobi API and Python `gurobipy`
""",
        )
        matlab_names.append(case_name)
        manifest.append(
            {
                "case": case_name,
                "source": str(source.relative_to(WORKSPACE)),
                "T": data["time_periods"],
                "n_thermal": n_thermal,
                "n_renewable": len(data.get("renewable_generators", {})),
                "solve_tier": tier,
            }
        )

    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    matlab_lines = "\n".join(f"    '{name}'" for name in matlab_names)
    write_text(
        ROOT / "run_all_matlab.m",
        f"""function run_all_matlab()
here = fileparts(mfilename('fullpath'));
addpath(fullfile(here, 'common'));
cases = {{
{matlab_lines}
}};
for i = 1:numel(cases)
    run_case_mat(fullfile(here, cases{{i}}));
end
end
""",
    )
    print(f"generated {len(manifest)} cases under {ROOT}")


if __name__ == "__main__":
    main()
