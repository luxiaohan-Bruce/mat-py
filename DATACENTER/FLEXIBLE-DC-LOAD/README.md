# FLEXIBLE-DC-LOAD — Wan–Li datacenter flexibility on DC-OPF / SCUC

把数据中心柔性负荷接到已有 IEEE 网架上（Python + Gurobi）。支路用 MATPOWER 直流：\(f=b(\theta_f-\theta_t)\)，\(b=1/(x\cdot\mathrm{tap})\)。

- **案例数**: 6
- **base_problem**: `datacenter_flex`
- **网架**: PGLib IEEE 14 / IEEE 24（经仓库 `scuc_cases` 时序复用）
- **来源**: Wan–Li 时空柔性（arXiv:2605.18517）

柔性模式：刚性 / 时移 / 空间搬移 / 时空能量守恒 / 可中断。IEEE 14 为多时段 DC-OPF；IEEE 24 开机组组合、无 N-1。

```bash
python3 run_all_python.py
python3 case001_ieee14_opf_inflexible/solve.py
```

共享模型：`common/dcflex_model_py.py`（及 vendored `result_io.py`, `tolerances.py`）。
