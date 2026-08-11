# DC-OTS / SC-OTS / SCUC Python 算例

基于 **Python + Gurobi（gurobipy）** 的电力系统难优化算例集。网络数据来自 [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) 全部 **66** 个基础算例；可切换线路、N-1 预想事故与机组组合参数为确定性构造，便于复现与对照。

| 目录 | 问题 | 案例数 |
|------|------|------:|
| [`dcots/`](dcots/) | **DC-OTS** — 直流最优网络重构 | 66 |
| [`scots/`](scots/) | **SC-OTS** — 预防性安全约束 OTS（基态 + N-1） | 66 |
| [`scuc/`](scuc/) | **SCUC** — 预防性多时段机组组合 + 直流潮流 + N-1 | 66 |

每个案例如下（以 DC-OTS 为例）：

- `data/network.json`：母线、机组、支路、成本、热稳限额、变比与移相角等
- `data/config.json`：可切换支路、开断数上限、预想事故、求解参数、`solve_tier` 与构造说明
- `solve_*.py`：该算例的 Python 入口

共享模型在对应目录的 `common/` 下；批量入口为 `run_all_python.py`。

---

## 算例与规模分级

全部 **66×3** 个案例均已生成数据与求解脚本。按节点规模写入 `config.solve_tier`：

| `solve_tier` | 含义 |
|--------------|------|
| `full` / `relaxed` | 中小规模，适合完整 MIP 求解与核对 |
| `skip` | 大规模网（数据与脚本齐全；全量 MIP 可能极慢或不切实际） |

部分代表性案例如下（完整列表见各目录 `MANIFEST.json`）：

| 文件夹 | 问题 | 典型规模 | 说明 |
|--------|------|----------|------|
| `dcots/case01_pjm5_dcots` | DC-OTS | 5 节点 | 全线可切换，教学向 |
| `dcots/case03_ieee118_dcots` | DC-OTS | 118 节点 | 按 DCOPF 利用率选可切换线 |
| `scots/case04_ieee24_scots` | SC-OTS | 24 节点 | 预防性 N-1 + 可切换 |
| `scots/case06_activs200_scots` | SC-OTS | 200 节点 | 更大网 SC-OTS |
| `scuc/case01_ieee39_scuc` | SCUC | 39 节点 / 24h | 多时段 UC + N-1 |
| `scuc/case03_case60_scuc` | SCUC | 60 节点 | 更大规模机组组合 |

---

## 模型要点

### 共同约定

- 直流支路潮流采用 MATPOWER 变比/移相约定：  
  \(f = b\,(\theta_f - \theta_t - \varphi)\)，\(b = 1/(x\cdot\mathrm{tap})\)（`ratio=0` 时 tap 视为 1）
- 仅 `status=1` 的在线机组参与出力与费用
- 求解默认 `Seed=1`，线程数见各 `config.json`

### DC-OTS

- 目标：最小化发电费用（可含二次成本）
- 可切换线路用 Gurobi **indicator** 约束处理开断（开断后潮流与角度约束解耦）
- 基数约束限制最多打开 `max_open` 条可切换线
- 基态热稳限额使用 `rateA`

### SC-OTS（预防性）

- 同一拓扑同时满足基态与全部给定 N-1 支路开断
- 事故后仅允许有限再调度（默认约 \(\pm 20\%(P_{\max}-P_{\min})\)），不含切负荷与事故后二次开断
- 基态限额 `rateA`，事故态可用 `rateC`（见模型与 `config`）

### SCUC（预防性）

- 多时段启停、最小开停机、爬坡、启动/停机费用
- 预防性：各时段出力在基态与 N-1 下一致（不按事故再调度机组组合）
- 负荷曲线与 UC 参数为合成设计（PGLib 本身不含 UT/DT 等字段）

---

## 环境要求

- Python 3.10+
- Gurobi（建议 11+ / 13.x）及有效许可证
- `gurobipy`（见 `requirements.txt`）

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 运行

求解某一类全部可发现案例：

```bash
python3 dcots/run_all_python.py
python3 scots/run_all_python.py
python3 scuc/run_all_python.py
```

求解单个案例：

```bash
python3 dcots/case01_pjm5_dcots/solve_dcots.py
python3 scots/case04_ieee24_scots/solve_scots.py
python3 scuc/case01_ieee39_scuc/solve_scuc.py
```

每次运行会在对应案例的 `results/python_result.json` 写入详细结果（若目录中已有缓存结果，重新运行会覆盖）。

> 大网 `solve_tier=skip` 的案例仅建议作数据/建模参考；完整 MIP 可能超时或内存不足。请优先从 `full`/`relaxed` 小中型案例开始。

---

## 参考结果（节选）

下列结果由 **Python + gurobipy** 得到，求解参数以各案例 `config.json` 为准（单线程、固定 Seed）。完整结果见各案例 `results/` 或本地工作包核对记录。

### DC-OTS（示例）

| 案例 | 基态 DCOPF | DC-OTS | 节约 | 打开线路（id） |
|------|----------:|-------:|-----:|----------------|
| case01_pjm5_dcots | 23092.09 | 18290.00 | 4802.09 | `4, 6` |
| case02_ieee14_dcots | 2799.99 | 2461.83 | 338.16 | `2, 17` |
| case03_ieee118_dcots | 99172.90 | 98631.58 | 541.32 | `31, 66, 67` |

### SC-OTS / SCUC

中小规模案例在 `full`/`relaxed` 档可稳定求得 `OPTIMAL`（或时限内可行解）。SCUC 多时段目标为全时段费用之和；具体数值因负荷缩放 \(\lambda\) 与事故集而异，以本机重跑 `solve_*.py` 为准。

---

## 仓库结构

```text
README.md
requirements.txt
.gitignore
dcots/
  common/                 # DC-OTS 模型与校验
  case01_pjm5_dcots/
  case02_ieee14_dcots/
  ...
  case66_..._dcots/
  run_all_python.py
  MANIFEST.json
scots/
  common/                 # SC-OTS 模型与校验
  case01_..._scots/
  ...
  run_all_python.py
  MANIFEST.json
scuc/
  common/                 # SCUC 模型
  case01_ieee39_scuc/
  ...
  run_all_python.py
  MANIFEST.json
```

数据来源与 SHA 等信息写在各 `config.json` 的 `source` / `notes` 中。  
PGLib-OPF 项目：<https://github.com/power-grid-lib/pglib-opf>。

---

## 许可与引用

- 本仓库中的构造说明、求解脚本：供科研与教学使用，使用风险自负。
- 网络原始数据请遵循 **PGLib-OPF** 许可证并引用该项目。
- 使用 Gurobi 报告结果时请遵守其许可协议。
