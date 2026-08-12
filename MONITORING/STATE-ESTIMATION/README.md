# STATE-ESTIMATION — DC WLS / L1 State Estimation

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

直流状态估计：WLS（QP）与 L1 robust（LP）。
固定 seed=1 生成真值相角、测量与坏数据。双端验收：**12/12 PASS**。

- **案例数**: 12（full=12）
- **数据来源**: PGLib-OPF 拓扑 + 合成测量（seed=1）
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py

# 单案例
python3 case001_case5_pjm_wls_se/python/solve_se.py
```

共享模型：`common/se_model_py.py`（及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络构造得到；请遵循 PGLib / PowerModelsRestoration 等上游许可并引用。
本包供科研与教学使用。
