# ECONOMIC-DISPATCH — Copperplate pilots

真正的单时段铜板经济调度（Python + Gurobi）。

模型只包含机组出力上下界和全系统供需平衡 `sum(Pg) = sum(Pd)`，不建立相角、支路潮流或线路热限约束。`buses` 仅保留负荷来源，机组的 `bus` 字段仅用于数据溯源。这与 `OPF/DC-OPF` 中显式考虑网络的 71 个案例有本质区别。

- **案例数**: 3
- **数据来源**: `OPF/DC-OPF` 的 PGLib 3/5/14-bus 案例（只复用 buses/gens）
- **网络假设**: `power_flow=copperplate`，无 branches

```bash
python3 run_all_python.py
python3 case001_lmbd3_copperplate_ed/solve.py
```

共享模型：`common/economic_dispatch_model_py.py`。
