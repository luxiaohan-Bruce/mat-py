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
python3 evaluate.py DISPATCH/ECONOMIC-DISPATCH/case001_lmbd3_dc_ed
python3 evaluate.py --network pglib_opf_case14_ieee

# catalog
python3 -m framework.catalog --rebuild
python3 -m framework.catalog --by-network pglib_opf_case118_ieee
```

`CATALOG.json` lists every case. `NETWORK_INDEX.json` groups cases that share the same `source_network`.
