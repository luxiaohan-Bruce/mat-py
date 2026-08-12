# Linearized SC-AC-OPF (GO Challenge 1)

**base_problem**: OPF（安全约束，线性化 DC，**不是**精确 AC）  
**variant**: security=n-1, enable_ots=false

从原混合包 `SC-AC-OPF-OTS` 拆出，仅含 `*_scacopf` 案例（每场景 OPF 侧）。

```bash
python3 run_all_python.py --tier full,relaxed
python3 case001_t1s3_offline_network_01o_3_scenario_1_scacopf/python/solve_scacopf.py
```
