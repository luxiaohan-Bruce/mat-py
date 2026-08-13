# DISTRIBUTION-OPF

> **成熟度：** experimental · **验证范围：** structural-only · **配电物理验证：** 否

SimBench MV/LV 多时段有功网络输运示例（Python + Gurobi），从 `DNR` 包中拆分，避免将 `distribution_opf` 与 `dnr` 混为同一基础问题。保留 `DISTRIBUTION-OPF` 类别用于分类占位与后续模型升级，但当前实现不计入 physics-validated distribution OPF coverage。

- **案例数**: 2
- **时域**: 4 periods
- **当前约束**: 有功节点平衡与支路容量限制
- **共享模型**: `common/dnr_model_py.py`（为保持案例入口兼容性保留历史文件名）
- **缺失物理**: 电压变量/压降方程、无功平衡、径向与带电连通性约束

因此 `OPTIMAL` 只表示该实验性代理模型被求解，不能作为 LinDistFlow、AC 配电 OPF 或可运行配电方案的验证结论。

```bash
python3 run_all_python.py
python3 case02_mv_rural_dopf/solve.py
python3 case05_lv_rural2_dopf/solve.py
```
