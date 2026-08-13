# Linearized Security-Constrained OTS verification

This package contains **158** OTS-mode cases from GO Challenge 1.

- Model: linearized DC security-constrained OTS, not exact AC-OTS.
- Contingency coverage: sampled `case.con` subset, not exhaustive N-1.

- Stored Python results: **38/38 valid** in the `relaxed` tier; **120** size-based `skip` cases.
- Twelve Network-03 cases formerly marked infeasible are now `OPTIMAL` after fixing negative-`Pd`
  fixed-injection handling. This package is Python-only; `comparison.json` validates the stored
  Python result and does not claim a MATLAB cross-solver comparison.
