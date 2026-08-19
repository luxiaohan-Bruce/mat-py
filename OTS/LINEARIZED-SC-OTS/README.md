# Linearized Security-Constrained OTS (GO Challenge 1)

**base_problem**: OTS
**variant**: power_flow=dc_linearized, security=sampled_n-1, contingency_scope=sampled_subset,
recourse=corrective_limited, generation_recourse=corrective_within_generator_bounds,
topology_control=preventive_shared, enable_ots=true

这些算例在线性化 DC 有功潮流下联合优化线路开断，**不是**精确 AC-OTS。
每个场景只从 `case.con` 选取部分支路与机组事故，因此也不表示完整的 N-1 事故集。
基态与所有事故态共享同一开断决策，故拓扑控制是
`topology_control=preventive_shared`；事故态机组可在 `0 <= Pg <= Pmax` 内重新调度，
对应 `recourse=corrective_limited`、
`generation_recourse=corrective_within_generator_bounds`，不包含额外爬坡或参与因子带宽。

```bash
python3 run_all_python.py
python3 case002_t1s3_offline_network_01o_3_scenario_1_scacots/python/solve_scacopf.py
```
