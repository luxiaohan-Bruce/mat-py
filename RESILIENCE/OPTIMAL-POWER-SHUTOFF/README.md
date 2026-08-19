# OPTIMAL-POWER-SHUTOFF — Optimal Power Shutoff (wildfire risk)

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11，B19）。

- **案例数**: 35
- **验收**: | Cases PASS | **35 / 35** |

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py --full-only   # 默认只跑 full

# 单案例（示例见 MANIFEST 首案）
python3 <case>/python/solve_*.py
```

共享模型：`common/ops_model_py.py`（及 vendored `dc_network.py`, `result_io.py`, `tolerances.py`）。
完整列表见 `MANIFEST.json`。
