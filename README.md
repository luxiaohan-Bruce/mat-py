# DC-OTS / SC-OTS Python Cases

Six reproducible optimal transmission switching examples implemented in Python
with `gurobipy`. The repository contains three DC-OTS cases and three preventive
N-1 SC-OTS cases derived from PGLib-OPF data.

## Cases

| Folder | Problem | Buses | Branches | N-1 contingencies | Switchable lines | Max open |
|---|---|---:|---:|---:|---:|---:|
| `case01_pjm5_dcots` | DC-OTS | 5 | 6 | — | 6 | 2 |
| `case02_ieee14_dcots` | DC-OTS | 14 | 20 | — | 8 | 2 |
| `case03_ieee118_dcots` | DC-OTS | 118 | 186 | — | 20 | 3 |
| `case04_ieee24_scots` | SC-OTS | 24 | 38 | 37 | 8 | 1 |
| `case05_ieee73_scots` | SC-OTS | 73 | 120 | 118 | 12 | 2 |
| `case06_activs200_scots` | SC-OTS | 200 | 245 | 173 | 20 | 3 |

Each case directory contains only:

- `network.json`: buses, generators, branches, costs, ratings, taps, and shifts.
- `config.json`: switchable branches, cardinality, contingencies, solver settings,
  and data provenance.
- `solve.py`: the Python entry point for that case.

## Formulation

- DC branch flow follows the MATPOWER tap/phase-shift convention:
  `f = b * (theta_from - theta_to - shift)`, with `b = 1 / (x * tap)`.
- Gurobi indicator constraints decouple flow physics and angle limits when a
  switchable line is open; no global angle box or legacy big-M is used.
- A signed single-commodity flow keeps the base state and every contingency
  state connected.
- Only online generators contribute generation cost; invalid bounds are rejected.
- Preventive SC-OTS shares one topology across the base state and all N-1 states.
  Post-contingency actions are limited to generator redispatch within
  `±20% * (Pmax - Pmin)`; load shedding and post-contingency switching are disabled.
- Base-state limits use `rateA`; contingency limits use the original `rateC`.
- After the primary SC-OTS optimum, a strictly convex secondary objective selects
  a deterministic representative contingency dispatch without changing the
  reported primary objective, bound, or MIP gap.

## Requirements

- Python 3.10 or newer
- Gurobi 13.x and a valid Gurobi license

Install the Python package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

Solve all cases:

```bash
python run_all.py
```

Solve one case:

```bash
python case04_ieee24_scots/solve.py
```

Each run writes a detailed result to `<case>/results/python_result.json`.
Generated result directories are ignored by Git.

## Reference results

Results below were obtained with Python, gurobipy 13.0.2, one solver thread, and
the parameters recorded in each `config.json`.

| Case | Baseline objective | OTS objective | Savings | Opened lines |
|---|---:|---:|---:|---|
| case01 | 23092.091473 | 18290.000000 | 4802.091473 | `4, 6` |
| case02 | 2799.992284 | 2461.831571 | 338.160714 | `2, 17` |
| case03 | 99172.899106 | 98631.580859 | 541.318247 | `31, 66, 67` |
| case04 | 61001.240313 | 61001.240312 | 0.000001 | none |
| case05 | 183003.720937 | 183003.720937 | 0.000000 | `19, 100` |
| case06 | 27479.643306 | 27479.643306 | 0.000000 | `73` |

The three SC-OTS cases tested load multipliers from 1.000 through 1.150. None met
the configured economic-improvement threshold, so their published networks keep
the original 1.000 load scale and unmodified branch ratings.

## Repository layout

```text
README.md
requirements.txt
run_all.py
dcots_model.py
validate_data.py
validate_residuals.py
case01_pjm5_dcots/
case02_ieee14_dcots/
case03_ieee118_dcots/
case04_ieee24_scots/
case05_ieee73_scots/
case06_activs200_scots/
```

The source cases and SHA-256 hashes are recorded in each configuration file.
PGLib-OPF project: <https://github.com/power-grid-lib/pglib-opf>.
