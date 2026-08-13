# PMU-PLACEMENT — Optimal PMU Placement

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

最优 PMU 布点：0-1 MILP；PMU 观测本母线及邻接母线；单位成本最小化 PMU 数。
数据：PGLib-OPF 拓扑。37 个 full/relaxed 案例通过双端验收；29 个 `skip` 大网仅提供数据，不计作求解 PASS。

- **案例数**: 66（full=18, relaxed=19, skip=29）
- **数据来源**: PGLib-OPF (https://github.com/power-grid-lib/pglib-opf)
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py   # 默认跳过 solve_tier=skip

# 单案例
python3 case001_case3_lmbd_pmu/python/solve_pmu.py
```

共享模型：`common/pmu_model_py.py`（及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络构造得到；请遵循 PGLib / PowerModelsRestoration 等上游许可并引用。
本包供科研与教学使用。
