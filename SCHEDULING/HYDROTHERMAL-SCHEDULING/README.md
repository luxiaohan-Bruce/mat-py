# HYDROTHERMAL-SCHEDULING — Hydrothermal Scheduling

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11，B13）。

- **案例数**: 32（<600s=27，难求解=5）

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py

# 单案例（示例见 MANIFEST 首案）
python3 <case>/python/solve_*.py
```

共享模型：`common/ht_model_py.py`（及 vendored (none)）。
完整列表见 `MANIFEST.json`。
