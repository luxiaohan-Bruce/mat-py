# Security-Constrained Optimal Transmission Switching (SC-OTS)

**base_problem**: OTS
**variant**: power_flow=dc, security=none / n-1 / sampled_n-1, topology_control=preventive_shared, generation_recourse=corrective_bounded, recourse=corrective_limited

基态与配置列出的事故态共享同一线路拓扑，所以线路开断是预防性决策；事故后允许机组在
`redispatch_frac` 给定的出力带内校正再调度。基态使用 `rateA`，事故态使用 `rateC`。

事故覆盖按案例如实标注：case02、case04–06 枚举全部可信非孤岛单线路事故，标为
`security=n-1`；case03、case07–66 只选择事故子集，标为 `sampled_n-1`；case01
没有可保持连通的单线路事故，标为 `security=none`。不要把抽样案例解释为完整 N-1。

```bash
python3 run_all_python.py
```
