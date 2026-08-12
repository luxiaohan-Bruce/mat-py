# ECONOMIC-DISPATCH — Networked DC Economic Dispatch

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

单时段网络化直流经济调度（无 UC 二进制）。
目标：最小化二次/线性发电费用；约束：节点功率平衡、DC 潮流、热稳、机组出力上下界。
数据：PGLib-OPF 全网 + 小网线性成本教学变体（`*_lp_ed`）。
双端验收：**71/71 PASS**（full 23 / relaxed 19 / skip 29 仅数据）。

- **案例数**: 71（full=23, relaxed=19, skip=29）
- **数据来源**: PGLib-OPF (https://github.com/power-grid-lib/pglib-opf)
- **不含** MATLAB 脚本；参考 dual-pass 摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py --full-only   # 默认跳过 solve_tier=skip

# 单案例
python3 case001_lmbd3_dc_ed/python/solve_ed.py
```

共享模型：`common/ed_model_py.py`（及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`）。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络构造得到；请遵循 PGLib / PowerModelsRestoration 等上游许可并引用。
本包供科研与教学使用。
