# Security-Constrained Unit Commitment (SCUC)

**base_problem**: UC
**variant**: power_flow=dc, security=sampled_n-1, contingency_scope=selected_subset, horizon=multi_period, recourse=preventive

每个算例显式选择有限支路事故子集进行预防性 DC-SCUC 校验；`sampled_n-1` 不表示穷举
网络内全部单支路事故。模型同时包含启停、最小开停机时间、爬坡和旋转备用约束。

```bash
python3 run_all_python.py
```
