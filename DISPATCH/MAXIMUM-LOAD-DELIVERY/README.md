# MAXIMUM-LOAD-DELIVERY — DC Maximum Load Delivery

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

直流最大供电（MLD）：最大化加权负荷供电比例；损坏支路/机组强制离线。
数据：PowerModelsRestoration 可解析算例 + PGLib 小网 synthetic damage。
v1 忽略储能/无功/三相。双端验收：**18/18 PASS**。

- **案例数**: 18（full=18）
- **数据来源**: PowerModelsRestoration + PGLib-OPF
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py

# 单案例
python3 case001_case3_mld_mld/python/solve_mld.py
```

共享模型：`common/mld_model_py.py`（及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络构造得到；请遵循 PGLib / PowerModelsRestoration 等上游许可并引用。
本包供科研与教学使用。
