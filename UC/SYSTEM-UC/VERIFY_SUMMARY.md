# PGLib-UC verify summary

- Date: 2026-08-12
- Cases: **56 / 56 PASS** (MATLAB Gurobi ↔ Python gurobipy)
- Compare rule: relative objective difference ≤ `max(1e-6, 1.05 × max(mip_gap_py, mip_gap_mat))`; demand residual ≤ `1e-4` MW

## Tiers

| Tier | Count | Sources | MIPGap (config) | TimeLimit |
|------|-------|---------|-----------------|-----------|
| full | 12 | rts_gmlc | 0.01 | 180 s |
| large | 20 | ca | 0.01 | 300 s |
| xlarge | 24 | ferc | 0.02 | 600 s |

## Notes

- Data: `数据集/pglib-uc-master` (all JSON instances).
- Model: deterministic system-level UC with reserves, ramping, min up/down, startup categories, convex PWL production cost (aligned with official PGLib-UC formulation).
- Alternate MIP incumbents within the gap tolerance are accepted.
- Commands:

```bash
python3 common/build_all_from_pglib_uc.py
python3 run_all_python.py
# MATLAB
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
