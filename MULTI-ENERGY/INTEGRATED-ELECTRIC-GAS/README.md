# INTEGRATED-ELECTRIC-GAS — Integrated Electricity–Gas Optimization

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11，B20）。

- **案例数**: 14（full=13, relaxed=1）
- **数据来源**: GasLib + PGLib / Travis coupling
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`
- **验收**: 14 个 full/relaxed 案例通过验收

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

共享模型：`common/ieg_model_py.py`（及 vendored `dc_network.py`, `result_io.py`, `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络/算例构造得到；请遵循上游许可并引用。
本包供科研与教学使用。
