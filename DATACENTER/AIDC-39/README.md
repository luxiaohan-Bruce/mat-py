# AIDC-39：三个全新的电网—算力协同调度基准

三个独立构造的 MILP 问题，使用同一份公开 PGLib 39 节点网架，分别研究训练作业的时间调度、推理请求的空间分配、日前承诺与随机场景追补。所有 AIDC、工作负载、UC 运行参数和场景均为新生成的合成数据，未复用本仓库此前的数据中心或机组组合业务参数。原始电源的线性能量成本来自 PGLib。

| 案例 | 业务及电网模型 | 正式规模 | 文档 |
|---|---|---|---|
| case001_training_uc | 不可抢占并行训练 + 机组组合 | 1 站、240 作业、64 算力块、3 档位；约 100 秒难度档 | [数学模型](case001_training_uc/README.md) |
| case002_inference_n1 | 模型副本启停 + 请求路由 + 预防性线路 N-1 | 3 站、6 模型、6 区域、35 事故 | [数学模型](case002_inference_n1/README.md) |
| case003_stochastic_ups | 日前 UC/备用/算力 + 风光和需求随机追补 | 3 站、3 电池、20 场景、CVaR | [数学模型](case003_stochastic_ups/README.md) |

三例均为 39 节点、46 支路、96 个 15 分钟时段。前两例包含 10 个原有电源；第三例在现有母线上额外接入风光，目录中的总电源数为 12，母线数仍为 39。

三个案例的完整变量、参数、目标函数、约束、对照和生成公式统一整理于 [MATHEMATICAL_FORMULATION.md](MATHEMATICAL_FORMULATION.md)，包含当前 240 作业训练版本，并与现有实现逐项对应。

训练案例已按约 100 秒求解目标重新标定：任务数从 160 增至 240，任务完成时间成本调整为原来的 4.5 倍。标定与重复计时见 [calibration/README.md](calibration/README.md)，原始 160 作业输入及结果保存在 `calibration/original_160_jobs/`。其他两例的数据与正式结果保持原样。

## 使用

以下命令在仓库根目录运行。需要 Python 3.10+、NumPy、Gurobi 11+ 和能够求解相应规模的许可证。

```bash
python3 solve.py DATACENTER/AIDC-39/case001_training_uc
python3 solve.py DATACENTER/AIDC-39/case002_inference_n1
python3 solve.py DATACENTER/AIDC-39/case003_stochastic_ups
python3 DATACENTER/AIDC-39/run_all_python.py --with-baselines
python3 evaluate.py DATACENTER/AIDC-39/case001_training_uc
python3 evaluate.py DATACENTER/AIDC-39/case002_inference_n1
python3 evaluate.py DATACENTER/AIDC-39/case003_stochastic_ups
python3 DATACENTER/AIDC-39/test_aidc39.py
```

单例还支持 `python3 <case>/solve.py --mode baseline`、`--time-limit 60` 和 `--validate-only`。缩短时限适用于调试；正式结果统一使用 Seed=1、Threads=4、TimeLimit=600 秒、MIPGap=0.001。求解时限只包括求解器时间，构模和独立校验时间另行报告。

完整重建输入使用 `python3 DATACENTER/AIDC-39/generate.py`。该命令会覆盖本包的输入和配置、重新构模统计规模并更新目录；不自动重新求解。旧结果在输入哈希不一致时会被验收拒绝。重新运行求解后，使用 `python3 DATACENTER/AIDC-39/refresh_metadata.py --catalog` 更新元数据。

## 输出和比较

- `results/python_result.json`：正式解，包含全部调度变量、成本分项、最优界、间隙、首次可行解时间和独立校验证书。
- `results/baseline_result.json`：对照方案；随机案例另保存 `mean_policy_result.json`。
- `results/*_gurobi.log`、`*_model_stats.json`、`*_progress.json`：原始日志、实际构模规模和最近一次求解中进度。最终状态以结果 JSON 为准。
- [BENCHMARK.md](BENCHMARK.md)：实际运行结果、对照可行性和改善幅度；由结果文件生成。
- `python3 DATACENTER/AIDC-39/report.py`：重新独立校验保存的解，刷新报告和 `benchmark_results.json`，不重新求解。
- [GRID_MODEL.md](GRID_MODEL.md)、[DATA_SCHEMA.md](DATA_SCHEMA.md)：公共电网/UC 方程、字段、单位与边界约定。
- [VERIFICATION.md](VERIFICATION.md)：18 项新模型测试、20 项框架回归及正式验收记录，也记录全库旧包的清单不一致问题。

验收会重新读取完整解并复算约束，修改 `validation_passed` 不能绕过检查。校验器不导入 Gurobi，线路事故通过重新建立网络方程验证，独立于优化模型使用的 LODF 约束。

“OPTIMAL”表示 Gurobi 达到配置的终止间隙，不代表浮点意义下零间隙。时限内有效解与已证明达到终止标准的解分别报告。对照不可行时保留不可行状态，不计算改善百分比。三例验证的是明确定义的 DC 与业务模型，没有交流电压、无功或暂态认证含义。

## 来源与合成规则

原始网架：[PGLib 官方文件](https://github.com/power-grid-lib/pglib-opf/blob/dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3/pglib_opf_case39_epri.m)，PGLib-OPF v23.07；原始文件和归属声明保存在 `source/`。

- 固定提交：`dc6be4b2f85ca0e776952ec22cbd4c22396ea5a3`。
- 原始文件 SHA-256：`83a1a6ec49c9a0533b51e928f6bd95b93aea745a620e5123bedcd88f716c286b`。
- 新数据种子：训练 101、推理 202、随机追补 303；使用 NumPy PCG64。
- 基础负荷倍率为 \(a_t=a_{max}[0.8+0.2\sin^2(\pi(t/T-0.25))]\)。第一、三例 \(a_{max}=0.85\)，第二例为 0.68。
- 0.68 是线路安全算例的明确负荷设置。在本包合成最小出力约束下，三站各取电 200 MW、全部原有电源在线时，35 个非孤岛事故的静态预防性筛查得到基础负荷倍率上限约为 0.7099；0.85 不可行。该筛查不替代多时段正式验收。使用 `python3 DATACENTER/AIDC-39/screen_security.py` 可复现，结果和数值证书保存于 `source/static_security_screen.json`。
- 工作量、吞吐率、功率、时延和成本均是公开写出的基准假设，不对应某种商业 GPU 或真实站点报价。算力块是聚合资源单位。
