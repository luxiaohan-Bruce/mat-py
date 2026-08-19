# TRANSMISSION-EXPANSION — Transmission Expansion Planning (TEP / TNEP)

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11，B11）。

- **案例数**: 67（full=20, relaxed=3, skip=44）
- **数据来源**: PowerModelsTNEP native + PGLib synthetic candidates
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`
- **验收**: 23 个 full/relaxed 案例通过双端验收；44 个 `skip` 大网仅提供数据（2026-08-12）

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

共享模型：`common/tep_model_py.py`（及 vendored `dc_network.py`, `result_io.py`, `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络/算例构造得到；请遵循上游许可并引用。
本包供科研与教学使用。
