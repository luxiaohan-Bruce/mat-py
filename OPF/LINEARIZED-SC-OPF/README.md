# Linearized Security-Constrained OPF (GO Challenge 1)

**base_problem**: OPF
**variant**: power_flow=dc_linearized, security=sampled_n-1, contingency_scope=sampled_subset,
recourse=corrective_limited, generation_recourse=corrective_within_generator_bounds, enable_ots=false

这些算例使用线性化 DC 有功潮流，**不是**精确 AC-OPF。每个场景只从
`case.con` 选取部分支路与机组事故，因此也不表示完整的 N-1 事故集。
事故态允许机组在 `0 <= Pg <= Pmax` 内重新调度，故元数据标为
`recourse=corrective_limited`、`generation_recourse=corrective_within_generator_bounds`；
这不是带爬坡或参与因子带宽的再调度模型。

```bash
python3 run_all_python.py --tier full,relaxed
python3 case001_t1s3_offline_network_01o_3_scenario_1_scacopf/python/solve_scacopf.py
```
