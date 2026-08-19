# DC-OPF — Network-constrained DC Optimal Power Flow

Python-only 包（gurobipy），自 `*_cases` 双端验收通过后同步（PLAM §11）。

单时段 DC-OPF（无 UC 二进制）。
目标：最小化二次/线性发电费用；约束：节点功率平衡、DC 支路潮流方程、线路热限和机组出力上下界。因显式包含网络约束，本包归类为 `opf/dc_opf`，而非铜板 Economic Dispatch。
数据：PGLib-OPF 全网 + 小网线性成本教学变体（`*_lp_ed`）。

- **案例数**: 71（<600s=66，难求解=5）

## 环境

- Python 3.10+
- Gurobi + `gurobipy`（见上级 `../requirements.txt`）

## 运行

```bash
# 批量
python3 run_all_python.py

# 单案例
python3 case001_lmbd3_dc_ed/python/solve_ed.py
```

共享模型：`common/ed_model_py.py`（为保持历史路径和最小 diff 保留文件名；其实际求解 DC-OPF），以及 vendored `dc_network.py` / `result_io.py` / `tolerances.py`。
完整列表见 `MANIFEST.json`。
