# AC-OPF — Exact nonconvex polar pilots

This package adds three small, reproducible PGLib AC optimal-power-flow pilots.
They are intentionally separate from `../DC-OPF`: every case enforces the full
nonlinear polar P/Q network equations and is classified as
`opf/ac_opf`, `power_flow=ac_exact`, `formulation=polar_ac_power_flow`.

## Model

The shared Gurobi 13 model in `common/acopf_model.py` includes:

- explicit active and reactive nodal balance, including bus shunts;
- bus voltage-magnitude bounds and one reference angle;
- exact trigonometric branch flows with resistance, total line charging,
  off-nominal tap ratio, and phase shift;
- branch angle-difference bounds and `P² + Q² <= rateA²` at both ends;
- online generator P/Q bounds and polynomial active-power generation cost.

Gurobi uses `NonConvex=2` and nonlinear function constraints, so `OPTIMAL`
means a globally certified solution within the configured gap (1e-7 for the
3- and 5-bus pilots; 1e-3 for IEEE 14), not merely a local stationary point.
The result writer independently recomputes every
branch flow, both nodal balances, limits, and objective from serialized values.

## Run

```bash
python3 run_all_python.py
python3 case003_ieee14_acopf/solve.py
```

Gurobi 13+ and a valid `gurobipy` license are required. The three cases use one
thread and deterministic seed 1. See `VERIFY_SUMMARY.md` for measured results.

## Source

Network data are unchanged JSON conversions of PGLib-OPF
`case3_lmbd`, `case5_pjm`, and `case14_ieee`; source paths and SHA-256 values
are recorded in each `data/config.json`.
