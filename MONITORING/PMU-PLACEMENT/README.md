# PMU-PLACEMENT — Optimal PMU Placement

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

最优 PMU 布点：0-1 MILP；PMU 观测本母线及邻接母线；单位成本最小化 PMU 数。
数据：PGLib-OPF 拓扑。

- **案例数**: 66（<600s=61，难求解=5）

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py

# 单案例
python3 case001_case3_lmbd_pmu/python/solve_pmu.py
```

共享模型：`common/pmu_model_py.py`（及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`）。
完整列表见 `MANIFEST.json`。
