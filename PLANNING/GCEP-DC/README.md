# GCEP-DC — Texas 123-BT capacity expansion with DC / EOR loads

PSE-Lab 电网容量扩展（GCEP）的 Gurobi LP。官方脚本是 Pyomo `Case2_LP_multi-periods.py`；这里按同一套集合 / 约束 / 目标改写。

- **案例数**: 3（full=2，large=1）
- **base_problem**: `resource_capacity_expansion`
- **网架**: 合成 Texas 123-BT
- **数据来源**: [PSE-Lab/Grid-Capacity-Expansion-under-Data-Center-and-Electrified-Manufacturing-Loads](https://github.com/PSE-Lab/Grid-Capacity-Expansion-under-Data-Center-and-Electrified-Manufacturing-Loads)（arXiv:2605.29053）
- **不含** MATLAB；双端对照摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

多年度投资 + 代表日直流潮流；县内 DC / EOR 负荷可在该县母线间分配；含建设时滞与 2029 年前核电禁建。储能按小时更新 SoC（官方脚本在日/年边界少记 1 小时充放，这里按物理写全）。目标按官方缩放 \(1/10^5\)。

```bash
python3 run_all_python.py --full-only
python3 case001_tx123_y2_d1/solve.py
```

共享模型：`common/gcep_model_py.py`（及 vendored `result_io.py`, `tolerances.py`）。
