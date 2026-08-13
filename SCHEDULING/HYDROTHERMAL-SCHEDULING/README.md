# HYDROTHERMAL-SCHEDULING — Hydrothermal Scheduling

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11，B13）。

- **案例数**: 32（full=9, relaxed=20, skip=3）
- **数据来源**: RCUC/HT-Ramp + System_46buses
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`
- **验收**: 29 个 full/relaxed 案例具有残差合格的可行结果（其中 3 个明确标为 interrupted incumbent）；3 个 16-scenario 案例为 `skip`

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py --full-only   # 默认跳过 solve_tier=skip

# 单案例（示例见 MANIFEST 首案）
python3 <case>/python/solve_*.py
```

共享模型：`common/ht_model_py.py`（及 vendored (none)）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络/算例构造得到；请遵循上游许可并引用。
本包供科研与教学使用。
