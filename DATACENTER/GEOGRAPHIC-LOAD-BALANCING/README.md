# GEOGRAPHIC-LOAD-BALANCING — Environmentally Equitable AI

多园区推理负荷的地理分流 LP（Python + Gurobi）。官方 notebook 用 CVXPY；这里按 `offline_solver` 写成 gurobipy。

- **案例数**: 6
- **base_problem**: `datacenter_glb`

决策 \(x_{i,j,t}\)：时刻 \(t\) 把网关 \(j\) 的负荷放到园区 \(i\)。容量 `max_cap=1`，目标为电价成本加可选的水/碳峰值公平项。

```bash
python3 run_all_python.py
python3 case001_eeai10_24h_equity_full/solve.py
```

共享模型：`common/glb_model_py.py`（及 vendored `result_io.py`, `tolerances.py`）。
