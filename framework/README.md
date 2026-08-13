# Case framework

Every case uses the same layout:

```text
<CATEGORY>/<PACK>/caseXX_*/
  data/config.json      # base_problem, variant, source_network, features
  data/network.json
  python/solve_*.py     # pack-specific solver
  solve.py              # unified entry (delegates to python/solve_*.py)
  results/
```

## Commands

```bash
# one case, two equivalent entries
python3 solve.py OTS/DC-OTS/case01_pjm5_dcots
python3 OTS/DC-OTS/case01_pjm5_dcots/solve.py

# score saved results (does not re-solve)
python3 evaluate.py OPF/DC-OPF/case001_lmbd3_dc_ed
python3 evaluate.py --network pglib_opf_case14_ieee

# catalog
python3 -m framework.catalog --rebuild
python3 -m framework.catalog --by-network pglib_opf_case118_ieee
```

`CATALOG.json` lists every case. `NETWORK_INDEX.json` groups cases that share the same `source_network`.
Catalog records also preserve optional trust metadata (`maturity`, `validation_scope`,
`physics_validated`, `known_limitations`). Unified evaluation prints `STRUCTURAL_ONLY` for
experimental models and `SKIP` for configured data-only cases; neither label is a physics PASS.
Time-limited or interrupted solutions are reported as `VALIDATED_INCUMBENT` when an explicit
residual check passed, otherwise as `FEASIBLE_INCUMBENT` (solver feasibility only); neither
label claims optimality.
