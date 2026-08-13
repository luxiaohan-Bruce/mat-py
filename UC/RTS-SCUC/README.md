# RTS-GMLC network SCUC (MATLAB ↔ Python / Gurobi)

Combines **RTS-GMLC** transmission topology (and ESS proxies) with all **12** PGLib-UC `rts_gmlc` day instances.

**base_problem**: UC
**variant**: power_flow=dc, security=sampled_n-1, contingency_scope=selected_subset, horizon=multi_period, recourse=preventive

Model: preventive DC-SCUC, system spinning reserve, renewable bounds, storage SOC, optional load-shed, and a selected subset of six non-bridge line contingencies. The package does not claim exhaustive N-1 coverage.

```bash
python3 common/build_all_from_rts.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
