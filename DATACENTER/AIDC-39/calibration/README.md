# 训练案例：约 100 秒难度标定

用户目标为将约 10 秒的训练与机组组合案例提高到约 100 秒。本次采用 80～120 秒作为“约 100 秒”的标定区间，以相同输入重复运行的中位数判断。

当前版本：**240 个作业，完成时间成本系数为原版的 4.5 倍**；保留 39 节点、46 支路、10 电源、96 时段、64 算力块、3 档位和 300 MW 接入上限。所有优化均用 Gurobi 13.0.2、Apple M5、Seed=1、Threads=4、TimeLimit=600 秒、MIPGap=0.1%，顺序执行。

## 原版与当前版

| 项目 | 原版 | 当前版 |
|---|---:|---:|
| 作业数 | 160 | 240 |
| 总训练工作量，标准块小时 | 1159.0 | 1368.5 |
| 最快档工作量 / 全天可用算力 | 75.5% | 89.1% |
| 完成时间成本，美元/小时 | 3～12 | 13.5～54 |
| 合法开始时间与档位组合 | 7241 | 11095 |
| 全部变量 | 19337 | 23191 |
| 二元变量 | 10121 | 13975 |
| 线性约束行 | 25004 | 25084 |
| 正式求解时间，秒 | 9.625 | 95.543 |

更多任务提高连续区间内的算力竞争；更高的流转时间成本强化尽早完成与低功率档位之间的取舍。时间窗口扩展规则、计算速度、功率和 UC 参数保留原值。小规模正确性测试仍使用短时域参数。

## 相同最终输入的重复运行

| 运行 | 时间，秒 | 最优间隙 | 独立验收 |
|---|---:|---:|---|
| [jobs240_cost4p5](../calibration/jobs240_cost4p5/run_1/python_result.json) | 92.002 | 0.09999% | 通过 |
| [jobs240_cost4p5_confirmation](../calibration/jobs240_cost4p5_confirmation/run_1/python_result.json) | 105.213 | 0.09999% | 通过 |
| [正式入口 solve.py](../case001_training_uc/results/python_result.json) | 95.543 | 0.09999% | 通过 |

中位数 **95.543 秒**，均值 **97.586 秒**，范围 **92.002～105.213 秒**。标定通过。所有结果以实际间隙条件正常结束。

计时是求解器报告的 Runtime，构模与文件写入另计。目标 100 秒是数据选择标准；正式求解器的时间上限仍为 600 秒。不同机器、软件版本及系统负载会影响秒数。

## 全部候选试验

下列记录保留全部已完成的标定候选。MILP 的搜索复杂度对数据变化不单调，因此在选定输入后进行重复验证。

| 候选 | 作业数 | 时间成本倍数 | 求解秒 | 间隙 | 独立验收 |
|---|---:|---:|---:|---:|---|
| [jobs200_margin19](../calibration/jobs200_margin19/run_1/python_result.json) | 200 | 1 | 13.693 | 0.09563% | 通过 |
| [jobs200_cost5](../calibration/jobs200_cost5/run_1/python_result.json) | 200 | 5 | 28.003 | 0.09627% | 通过 |
| [jobs240_cost5](../calibration/jobs240_cost5/run_1/python_result.json) | 240 | 5 | 69.524 | 0.09952% | 通过 |
| [jobs250_cost5](../calibration/jobs250_cost5/run_1/python_result.json) | 250 | 5 | 37.842 | 0.09807% | 通过 |
| [jobs240_cost6](../calibration/jobs240_cost6/run_1/python_result.json) | 240 | 6 | 28.279 | 0.09950% | 通过 |
| [jobs240_cost4](../calibration/jobs240_cost4/run_1/python_result.json) | 240 | 4 | 134.808 | 0.09884% | 通过 |
| [jobs240_cost4p5](../calibration/jobs240_cost4p5/run_1/python_result.json) | 240 | 4.5 | 92.002 | 0.09999% | 通过 |
| [jobs240_cost4p5_confirmation](../calibration/jobs240_cost4p5_confirmation/run_1/python_result.json) | 240 | 4.5 | 105.213 | 0.09999% | 通过 |

## 复现与文件

正式案例默认已切换到选定难度。使用仓库统一入口：

```bash
python3 solve.py DATACENTER/AIDC-39/case001_training_uc
python3 DATACENTER/AIDC-39/case001_training_uc/solve.py --mode baseline
python3 evaluate.py DATACENTER/AIDC-39/case001_training_uc
```

新建一个标定记录目录可复现相同工作负载的多次测量：

```bash
python3 DATACENTER/AIDC-39/calibration/calibrate_training.py --label fresh_240_cost4p5 --jobs 240 --wait-cost-scale 4.5 --repeats 3
python3 DATACENTER/AIDC-39/calibration/report_calibration.py
```

标签目录已存在时程序拒绝覆盖，避免丢失旧计时。原版输入、主问题及对照完整结果位于 `original_160_jobs/`；所有候选保留独立输入、结果、日志和摘要。当前输入可由种子 101 的数据生成器完整重建。

正式对照已在当前 240 个作业与相同成本参数下重新求解，比较见 [BENCHMARK.md](../BENCHMARK.md)。其他两个正式案例的输入与原有主问题/对照结果按 SHA-256 核对保持一致。
