# AC-OPF verification summary

Verified with Gurobi 13.0.2 (`NonConvex=2`, seed 1, one thread). Each result was
independently recomputed by `common/acopf_model.py::validate_acopf_solution`.

| Case | Status | Objective | Global gap | Max P residual | Max Q residual | Validation |
|---|---:|---:|---:|---:|---:|---:|
| `case001_lmbd3_acopf` | OPTIMAL | 5812.642974239 | 4.06e-08 | 3.75e-10 MW | 1.24e-10 MVAr | PASS |
| `case002_pjm5_acopf` | OPTIMAL | 17551.890920868 | 1.34e-07 | 1.88e-12 MW | 3.89e-12 MVAr | PASS |
| `case003_ieee14_acopf` | OPTIMAL | 2178.080428182 | 9.99e-04 | 3.09e-09 MW | 2.82e-09 MVAr | PASS |
| `case004_ieee30_acopf` | TIME_LIMIT | 8208.515471729 | 7.43e-01 | 4.62e-09 MW | 9.40e-09 MVAr | VALIDATED_INCUMBENT |

The first three also have zero recomputed MVA thermal, voltage, angle-difference,
P-generator-bound, and Q-generator-bound violations. Maximum serialized versus
recomputed branch-flow error is below `3.1e-9` MVA. IEEE 14 uses an explicitly
documented `1e-3` global gap; its exact AC feasibility tolerances are unchanged.
IEEE 30 is a physics-validated incumbent after 900 s (`solve_tier=large`); the
dual bound is not tight enough to certify global optimality.
