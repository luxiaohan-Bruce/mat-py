# Linearized SC-AC-OTS (GO Challenge 1)

**base_problem**: OTS（安全约束 + 线路开断，线性化 DC，**不是**精确 AC）  
**variant**: security=n-1, enable_ots=true

从原混合包 `SC-AC-OPF-OTS` 拆出，仅含 `*_scacots` 案例（每场景 OTS 侧）。

```bash
python3 run_all_python.py --tier full,relaxed
python3 case002_t1s3_offline_network_01o_3_scenario_1_scacots/python/solve_scacopf.py
```
