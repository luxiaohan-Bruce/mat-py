# RTS-GMLC network SCUC (MATLAB ↔ Python / Gurobi)

Combines **RTS-GMLC** transmission topology (and ESS proxies) with all **12** PGLib-UC `rts_gmlc` day instances.

Model: preventive DC-SCUC, system spinning reserve, renewable bounds, storage SOC, optional load-shed, N-1 line contingencies.

```bash
python3 common/build_all_from_rts.py
python3 run_all_python.py
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
