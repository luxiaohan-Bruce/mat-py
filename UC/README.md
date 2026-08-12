# PGLib-UC：MATLAB ↔ Python（Gurobi）

本目录将 `数据集/pglib-uc-master` 中全部 56 个公开实例转换成统一的双端案例。
Python 使用 `gurobipy`，MATLAB 使用 Gurobi MATLAB API，两端直接构造同一 MILP。

模型包含启停逻辑、初始状态、最小开停机时间、爬坡、旋转备用、可再生能源出力、
多档启动费用和凸分段线性生产成本。`MANIFEST.json` 记录全部来源与规模。

```bash
python3 common/build_all_from_pglib_uc.py
python3 run_all_python.py
/Applications/MATLAB_R2025a.app/bin/matlab -batch "cd(pwd); run_all_matlab"
python3 common/compare_results.py
```

