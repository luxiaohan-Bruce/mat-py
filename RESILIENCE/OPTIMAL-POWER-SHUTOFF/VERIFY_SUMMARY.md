# VERIFY_SUMMARY — optimal_power_shutoff_cases (PLAM B19)

## Counts

| Item | Value |
|------|-------|
| Risk-native networks eligible | **7 / 7** |
| Pareto budget fractions | 5 (`0, 0.25, 0.5, 0.75, 1.0`) |
| Cases constructed | **35** |
| Cases PASS | **35 / 35** |
| Python Gurobi results | 35 (all OPTIMAL, residual OK) |
| MATLAB Gurobi results | 30 (n_bus ≤ 30) |
| Dual objective compared | 30 / 30 PASS |
| RTS-GMLC (73-bus) | Python-only (5 cases) |

## Networks (native `power_risk` / `base_risk` only)

| Group | n_bus | n_branch | total_risk | cases |
|-------|------:|---------:|-----------:|------:|
| case3 | 3 | 3 | 12 | 5 |
| case5_risk_mops | 5 | 5 | 50 | 5 |
| case5_risk_sys1 | 5 | 6 | 22 | 5 |
| case5_risk_sys2 | 5 | 6 | 22 | 5 |
| case5_strg | 5 | 6 | 67 | 5 |
| case14_risk | 14 | 20 | 52 | 5 |
| rts_gmlc_risk | 73 | 120 | 152.97 | 5 |

**No synthetic wildfire risk on PGLib.**

## Residual checks (Python)

- De-energized branch flow = 0
- Risk budget satisfied
- Power balance / flow physics / thermal ~ 1e-4 MW
- Load served only if bus energized

## Pareto monotonicity (load_shed vs budget fraction)

- case3: OK
- case5_risk_mops: OK
- case5_risk_sys1: OK
- case5_risk_sys2: OK
- case5_strg: OK
- case14_risk: OK
- rts_gmlc_risk: OK

## Dual (Python ↔ MATLAB)

Small cases (nB ≤ 30): objective `load_shed` matched within package tolerances.
De-energized sets may differ under alternate optima when shed=0; residual checks still pass.
