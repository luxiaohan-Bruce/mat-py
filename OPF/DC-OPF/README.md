# DC-OPF — Network-constrained DC Optimal Power Flow

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

单时段 DC-OPF（无 UC 二进制）。
目标：最小化二次/线性发电费用；约束：节点功率平衡、DC 支路潮流方程、线路热限和机组出力上下界。因显式包含网络约束，本包归类为 `opf/dc_opf`，而非铜板 Economic Dispatch。
数据：PGLib-OPF 全网 + 小网线性成本教学变体（`*_lp_ed`）。
结果覆盖：42 个可执行案例（full 23 / relaxed 19）保留已验证求解结果；29 个 `skip` 大网仅提供数据，不计作求解 PASS。

- **案例数**: 71（full=23, relaxed=19, skip=29）
- **数据来源**: PGLib-OPF (https://github.com/power-grid-lib/pglib-opf)
- **不含** MATLAB 脚本；已求解案例的历史双端对照见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

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

共享模型：`common/ed_model_py.py`（为保持历史路径和最小 diff 保留文件名；其实际求解 DC-OPF），以及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`。
完整列表见 `MANIFEST.json`。

## 许可与来源

JSON 案例数据由上游网络构造得到；请遵循 PGLib / PowerModelsRestoration 等上游许可并引用。
本包供科研与教学使用。
