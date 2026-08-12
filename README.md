# 电力系统难优化算例（Python + Gurobi）

基于 **Python + Gurobi（gurobipy）** 的电网优化算例集：统一 JSON 数据、`solve_*.py` 入口、规模分级（`full` / `relaxed` / `skip`），便于复现与对照。

| 目录 | 问题 | 案例数 | 数据来源 |
|------|------|------:|----------|
| [`dcots/`](dcots/) | **DC-OTS** — 直流最优网络重构 | 66 | [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) |
| [`scots/`](scots/) | **SC-OTS** — 预防性安全约束 OTS（基态 + N-1） | 66 | PGLib-OPF |
| [`scuc/`](scuc/) | **SCUC** — 预防性多时段 UC + 直流潮流 + N-1 | 66 | PGLib-OPF（合成 UC 时序） |
| [`uc/`](uc/) | **UC** — 系统级机组组合（无网架潮流） | 56 | [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) |
| [`rts_scuc/`](rts_scuc/) | **RTS-SCUC** — 网络 SCUC + 储能 + 可再生 + N-1 | 12 | [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) + PGLib-UC `rts_gmlc` |
| [`scacopf/`](scacopf/) | **SC-AC-OPF / SC-AC-OTS**（线性化） | 316 | [GO Competition Challenge 1](https://gocompetition.energy.gov/) |
| [`dnr/`](dnr/) | **DNR / DOPF / DNR+ESS**（LinDistFlow） | 7 | [SimBench](https://simbench.de/) |
| [`smartds/`](smartds/) | **聚合馈线 DNR / Volt-VAR / DER hosting** | 3 | [SMART-DS](https://data.openei.org/submissions/2981) |

> **说明**：`scacopf` / `dnr` / `smartds` 均为**线性化近似**（DC 或 LinDistFlow），**不是**精确非凸 AC / 三相潮流。

单案例典型结构：

```text
caseXX_*/
  data/network.json   # 网络 / 机组 / 时序等
  data/config.json    # 事故集、可切换支路、求解参数、solve_tier、来源说明
  solve_*.py          # Python 入口
  results/            # 运行后写入 python_result.json 等
```

共享模型在各目录 `common/`；批量入口为 `run_all_python.py`。完整列表见各包 `MANIFEST.json`。

---

## 环境要求

- Python 3.10+
- Gurobi（建议 11+）及有效许可证
- `gurobipy`（见 `requirements.txt`）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 快速运行

```bash
# 输电侧 PGLib 三类（各 66 例）
python3 dcots/run_all_python.py
python3 scots/run_all_python.py
python3 scuc/run_all_python.py

# 系统 UC / RTS 网络 SCUC
python3 uc/run_all_python.py
python3 rts_scuc/run_all_python.py

# GO C1 线性化 SC-AC-OPF/OTS（建议先只跑可解档）
python3 scacopf/run_all_python.py --tier full,relaxed

# 配网 LinDistFlow
python3 dnr/run_all_python.py
python3 smartds/run_all_python.py
```

单案例示例：

```bash
python3 dcots/case01_pjm5_dcots/solve_dcots.py
python3 scots/case04_ieee24_scots/solve_scots.py
python3 scuc/case01_ieee39_scuc/solve_scuc.py
python3 uc/case01_rts_gmlc_2020_01_27_uc/solve_uc.py
python3 rts_scuc/case01_rts_gmlc_2020_01_27_rts_scuc/solve_rts_scuc.py
```

结果写入对应案例 `results/`。大网 `solve_tier=skip` 仅建议作数据/建模参考，完整 MIP 可能超时或内存不足；请优先从 `full` / `relaxed` 小中型案例开始。

---

## 算例与规模分级

按节点 / 组合规模写入 `config.solve_tier`：

| `solve_tier` | 含义 |
|--------------|------|
| `full` / `relaxed` | 中小规模，适合完整 MIP 求解与核对 |
| `skip` | 大规模（数据与脚本齐全；全量 MIP 可能极慢） |

### 输电：DC-OTS / SC-OTS / SCUC（PGLib-OPF，各 66）

可切换线路、N-1 预想事故与机组组合参数为确定性构造。部分代表例如下：

| 文件夹 | 问题 | 典型规模 | 说明 |
|--------|------|----------|------|
| `dcots/case01_pjm5_dcots` | DC-OTS | 5 节点 | 全线可切换，教学向 |
| `dcots/case03_ieee118_dcots` | DC-OTS | 118 节点 | 按 DCOPF 利用率选可切换线 |
| `scots/case04_ieee24_scots` | SC-OTS | 24 节点 | 预防性 N-1 + 可切换 |
| `scots/case06_activs200_scots` | SC-OTS | 200 节点 | 更大网 SC-OTS |
| `scuc/case01_ieee39_scuc` | SCUC | 39 节点 / 24h | 多时段 UC + N-1 |
| `scuc/case03_case60_scuc` | SCUC | 60 节点 | 更大规模机组组合 |

### UC（PGLib-UC，56）

系统级机组组合：启停、最小开停机、爬坡、旋转备用、可再生、分段成本与启动费用。无网架潮流约束。含 `rts_gmlc`、CA、FERC 等子集。

### RTS-SCUC（12）

RTS-GMLC 73 母线网架 + 储能；时序来自 PGLib-UC `rts_gmlc` 全部 12 个运行日。预防性 DC-SCUC：备用、可再生、储能、N-1。

### SC-AC-OPF / SC-AC-OTS（GO Challenge 1，316）

由 GO C1 场景解析得到；每个场景生成 `scacopf` 与 `scacots` 两套。模型为**线性化（直流）安全约束 OPF/OTS**，非官方精确 AC。当前分级约 **52** 个 `relaxed`（可解核对）+ **264** 个 `skip`（大网）。

### DNR（SimBench，7）+ SMART-DS（3）

- `dnr/`：MV/LV 可切换馈线 LinDistFlow 重构 / DOPF / 带储能；1 个 complete mixed 作 meta
- `smartds/`：GSO rural 聚合馈线 — DNR、Volt/VAR 电容器、DER hosting capacity

---

## 模型要点

### 共同约定（输电 DC 支路）

- MATPOWER 变比/移相：\(f = b\,(\theta_f - \theta_t - \varphi)\)，\(b = 1/(x\cdot\mathrm{tap})\)（`ratio=0` 时 tap 视为 1）
- 仅 `status=1` 的在线机组参与出力与费用
- 默认 `Seed=1`，线程数见各 `config.json`

### DC-OTS

- 目标：最小化发电费用（可含二次成本）
- 可切换线路用 Gurobi **indicator** 处理开断
- 基数约束限制最多打开 `max_open` 条；基态热稳 `rateA`

### SC-OTS（预防性）

- 同一拓扑满足基态与全部给定 N-1
- 事故后有限再调度（默认约 \(\pm 20\%(P_{\max}-P_{\min})\)）
- 基态 `rateA`，事故态可用 `rateC`

### SCUC（预防性，PGLib 合成时序）

- 多时段启停、最小开停机、爬坡、启停费用
- 预防性：出力在基态与 N-1 下一致
- 负荷曲线与 UT/DT 等为合成设计（PGLib-OPF 本身不含 UC 字段）

### UC（PGLib-UC）

- 系统功率平衡 + 备用；可再生注入；无支路潮流
- 参数直接来自 PGLib-UC JSON

### RTS-SCUC

- 网络 DC 潮流 + UC 逻辑 + 储能 + 可再生 + N-1
- 网架 RTS-GMLC，日时序对齐 PGLib-UC `rts_gmlc`

### SC-AC-OPF/OTS（线性化）

- GO C1 网络/成本/事故；直流潮流与热稳
- OTS 变体含线路开断决策

### DNR / SMART-DS（LinDistFlow）

- 径向近似潮流、开关/重构；部分案例含储能或电容器 / DER 容量

---

## 参考结果（节选）

下列由 **Python + gurobipy** 得到，参数以各 `config.json` 为准。完整结果见各案例 `results/`。

### DC-OTS（示例）

| 案例 | 基态 DCOPF | DC-OTS | 节约 | 打开线路（id） |
|------|----------:|-------:|-----:|----------------|
| case01_pjm5_dcots | 23092.09 | 18290.00 | 4802.09 | `4, 6` |
| case02_ieee14_dcots | 2799.99 | 2461.83 | 338.16 | `2, 17` |
| case03_ieee118_dcots | 99172.90 | 98631.58 | 541.32 | `31, 66, 67` |

### 扩展包核对（本地双端对照摘要）

| 包 | 状态 |
|----|------|
| `uc/` | 56/56 PASS（允许 MIP gap 容差） |
| `rts_scuc/` | 12/12 PASS |
| `scacopf/` | 可解档 52 例双端 PASS；其余 skip |
| `dnr/` | 6 求解 PASS + 1 meta |
| `smartds/` | 3/3 PASS |

SC-OTS / SCUC 中小规模 `full`/`relaxed` 档可稳定求得 `OPTIMAL`（或时限内可行解）。SCUC 多时段目标为全时段费用之和。

---

## 仓库结构

```text
README.md
requirements.txt
.gitignore
dcots/          # 66  DC-OTS
scots/          # 66  SC-OTS
scuc/           # 66  SCUC
uc/             # 56  PGLib-UC
rts_scuc/       # 12  RTS-GMLC SCUC+ESS
scacopf/        # 316 linearized SC-AC-OPF/OTS
dnr/            # 7   SimBench DNR family
smartds/        # 3   SMART-DS aggregated feeder
```

每个问题目录含 `common/`、`run_all_python.py`、`MANIFEST.json` 及若干 `case*/`。

---

## 数据来源与许可

| 来源 | 用途 | 许可提示 |
|------|------|----------|
| [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) | dcots / scots / scuc 网络 | 遵循项目许可并引用 |
| [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) | uc、rts_scuc 时序 | CC BY 等，见上游 |
| [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) | rts_scuc 网架与机组 | 开放数据，需署名 |
| [GO Competition Challenge 1](https://gocompetition.energy.gov/) | scacopf | 官方竞赛数据与说明 |
| [SimBench](https://simbench.de/) | dnr | ODbL 等，见上游 |
| [SMART-DS](https://data.openei.org/submissions/2981) | smartds | OpenEI 数据集条款 |

- 本仓库中的构造说明与求解脚本供**科研与教学**使用，使用风险自负。
- 使用 Gurobi 报告结果时请遵守其许可协议。
- 案例 `config.json` 的 `source` / `notes` 中记有更细的来源与 SHA 等信息（若有）。

---

## 免责声明

线性化模型与官方 AC / 三相仿真结果**不可直接等同**。大规模 MIP 的最优性证明取决于 Gurobi 时限与 gap；`skip` 档不保证可求最优。
