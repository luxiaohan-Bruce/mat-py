# Linearized SC-AC-OPF / SC-AC-OTS (GO Challenge 1)

**Approximation notice:** models are **DC security-constrained OPF** (linear), not exact nonconvex AC.
Each GO C1 scenario yields two cases: `scacopf` and `scacots`.

```bash
python3 common/build_all_from_go_c1.py
python3 run_all_python.py --tier full,relaxed
matlab -batch "run_all_matlab"
python3 common/compare_results.py
```
