# GREEN-LLM — multi-campus LLM inference allocation

跨园区 LLM 推理分流（Python + Gurobi）。对照官方实验用的 `lexicographic_model.py`（仓库里的 `Green_LLM.py` 在定义时延变量之前就引用了它们，不能直接跑）。

- **案例数**: 6（full=6）
- **base_problem**: `green_llm`
- **数据来源**: [JJmingcc/Green_LLM](https://github.com/JJmingcc/Green_LLM)（arXiv:2507.09942）
- **不含** MATLAB；双端对照摘要见 `VERIFY_SUMMARY.md` 与各案 `results/comparison.json`

决策 \(x_{i,j,k,t}\)：把区域 \(i\) 的 \(k\) 类查询分到园区 \(j\)。含 PUE、可再生/购电、水量、资源容量、时延与可选的模型落地二进制。

```bash
python3 run_all_python.py
python3 case001_9dc_24h_weighted/solve.py
```

共享模型：`common/green_llm_model_py.py`（及 vendored `result_io.py`, `tolerances.py`）。
