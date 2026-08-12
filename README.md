# 电力系统难优化算例（Python + Gurobi）

基于 **Python + Gurobi（gurobipy）** 的电网优化算例集：统一 JSON 数据、`solve_*.py` 入口、规模分级（`full` / `relaxed` / `skip`）。

目录按 **基础问题分类** 组织（PLAM：一级 = 优化在决定什么；AC/DC、N-1、多时段等进入各包 `config.variant`，不是一级目录）。

---

## 目录总览

```text
github_cases/
  OTS/                 # 输电拓扑切换
  OPF/                 # 最优潮流（线性化安全约束）
  UC/                  # 机组组合族
  DISTRIBUTION/        # 配网重构 / Volt-VAR / DER
  DISPATCH/            # 经济调度 / 最大供电
  MONITORING/          # PMU 布点 / 状态估计
  PLANNING/            # 输电扩展 / 容量扩展
  SCHEDULING/          # 水火调度 / 检修计划
  MARKET/              # 市场出清 / 策略报价
  RESILIENCE/          # 恢复 / 孤岛 / 主动停电 / 拦截
  MULTI-ENERGY/        # 电–气综合
  README.md
  requirements.txt
```

| 分类目录 | 子包 | 基础问题 | 案例数 | 数据来源 |
|----------|------|----------|------:|----------|
| [`OTS/`](OTS/) | [`DC-OTS/`](OTS/DC-OTS/) | OTS（直流） | 66 | [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) |
| | [`SC-OTS/`](OTS/SC-OTS/) | OTS + N-1 预防性 | 66 | PGLib-OPF |
| [`OPF/`](OPF/) | [`SC-AC-OPF-OTS/`](OPF/SC-AC-OPF-OTS/) | 线性化 SC-OPF / SC-OTS | 316 | [GO Competition C1](https://gocompetition.energy.gov/) |
| [`UC/`](UC/) | [`SYSTEM-UC/`](UC/SYSTEM-UC/) | 系统级 UC（无网架） | 56 | [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) |
| | [`SCUC/`](UC/SCUC/) | 网络 SCUC + N-1 | 66 | PGLib-OPF 合成时序 |
| | [`RTS-SCUC/`](UC/RTS-SCUC/) | RTS 网络 SCUC+储能+RE | 12 | [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) |
| [`DISTRIBUTION/`](DISTRIBUTION/) | [`DNR/`](DISTRIBUTION/DNR/) | 配网重构 LinDistFlow | 7 | [SimBench](https://simbench.de/) |
| | [`SMART-DS/`](DISTRIBUTION/SMART-DS/) | DNR / Volt-VAR / DER hosting | 3 | [SMART-DS](https://data.openei.org/submissions/2981) |
| [`DISPATCH/`](DISPATCH/) | [`ECONOMIC-DISPATCH/`](DISPATCH/ECONOMIC-DISPATCH/) | 网络化 DC 经济调度 | 71 | PGLib-OPF |
| | [`MAXIMUM-LOAD-DELIVERY/`](DISPATCH/MAXIMUM-LOAD-DELIVERY/) | 最大供电 / 切负荷 | 18 | PowerModelsRestoration + PGLib |
| [`MONITORING/`](MONITORING/) | [`PMU-PLACEMENT/`](MONITORING/PMU-PLACEMENT/) | 最优 PMU 布点 | 66 | PGLib-OPF |
| | [`STATE-ESTIMATION/`](MONITORING/STATE-ESTIMATION/) | DC WLS / L1 状态估计 | 12 | PGLib + 合成测量 |
| [`PLANNING/`](PLANNING/) | [`TRANSMISSION-EXPANSION/`](PLANNING/TRANSMISSION-EXPANSION/) | TEP / TNEP | 68 | PowerModels TNEP + PGLib |
| | [`RESOURCE-CAPACITY-EXPANSION/`](PLANNING/RESOURCE-CAPACITY-EXPANSION/) | 资源容量扩展 CEM | 10 | GenX 示例 |
| [`SCHEDULING/`](SCHEDULING/) | [`HYDROTHERMAL-SCHEDULING/`](SCHEDULING/HYDROTHERMAL-SCHEDULING/) | 水火联合调度 | 32 | CommaLAB HT-Ramp / 46-bus |
| | [`MAINTENANCE-SCHEDULING/`](SCHEDULING/MAINTENANCE-SCHEDULING/) | 机组检修计划 | 5 | RTS-GMLC / PGLib-UC |
| [`MARKET/`](MARKET/) | [`MARKET-CLEARING/`](MARKET/MARKET-CLEARING/) | 福利最大化能量出清 | 56 | PGLib-UC |
| | [`STRATEGIC-BIDDING/`](MARKET/STRATEGIC-BIDDING/) | 策略性报价 | 8 | Toy / PGLib |
| [`RESILIENCE/`](RESILIENCE/) | [`POWER-RESTORATION/`](RESILIENCE/POWER-RESTORATION/) | 输电恢复 | 13 | PowerModelsRestoration + ACTIVSg200 |
| | [`DISTRIBUTION-RESTORATION/`](RESILIENCE/DISTRIBUTION-RESTORATION/) | 配网服务恢复 | 4 | SimBench + SMART-DS |
| | [`CONTROLLED-ISLANDING/`](RESILIENCE/CONTROLLED-ISLANDING/) | 主动解列 / 受控孤岛 | 82 | ANDES + PGLib |
| | [`OPTIMAL-POWER-SHUTOFF/`](RESILIENCE/OPTIMAL-POWER-SHUTOFF/) | 最优主动停电（野火） | 35 | PowerModelsWildfire |
| | [`NETWORK-INTERDICTION/`](RESILIENCE/NETWORK-INTERDICTION/) | N-k 网络拦截 | 69 | PGLib-OPF |
| [`MULTI-ENERGY/`](MULTI-ENERGY/) | [`INTEGRATED-ELECTRIC-GAS/`](MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS/) | 电–气综合优化 | 15 | Travis 150 + GasLib |

**合计约 1150+ 案例**（含子包内 `skip` 数据档）。

> **说明**
> - 子包目录名：**大写 + 连字符**（`SC-AC-OPF-OTS` 表示 SC-AC-OPF/OTS，文件系统不能含 `/`）。
> - `OPF/SC-AC-OPF-OTS`、`DISTRIBUTION/DNR`、`DISTRIBUTION/SMART-DS` 均为**线性化近似**，**不是**精确非凸 AC / 三相潮流。
> - `UC/SYSTEM-UC` 原公开目录名为 `UC/`，迁入 `UC/` 分类后改名为 `SYSTEM-UC`，避免与分类目录重名。

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

在仓库根目录（本 README 所在目录）执行。每个子包自带 `run_all_python.py` 与 `common/`。

```bash
# —— OTS / OPF ——
python3 OTS/DC-OTS/run_all_python.py
python3 OTS/SC-OTS/run_all_python.py
python3 OPF/SC-AC-OPF-OTS/run_all_python.py --tier full,relaxed

# —— UC ——
python3 UC/SYSTEM-UC/run_all_python.py
python3 UC/SCUC/run_all_python.py
python3 UC/RTS-SCUC/run_all_python.py

# —— 配网 ——
python3 DISTRIBUTION/DNR/run_all_python.py
python3 DISTRIBUTION/SMART-DS/run_all_python.py

# —— 调度 / 监测 ——
python3 DISPATCH/ECONOMIC-DISPATCH/run_all_python.py --full-only
python3 DISPATCH/MAXIMUM-LOAD-DELIVERY/run_all_python.py
python3 MONITORING/PMU-PLACEMENT/run_all_python.py
python3 MONITORING/STATE-ESTIMATION/run_all_python.py

# —— 规划 / 时序 / 市场 ——
python3 PLANNING/TRANSMISSION-EXPANSION/run_all_python.py --full-only
python3 PLANNING/RESOURCE-CAPACITY-EXPANSION/run_all_python.py
python3 SCHEDULING/HYDROTHERMAL-SCHEDULING/run_all_python.py --full-only
python3 SCHEDULING/MAINTENANCE-SCHEDULING/run_all_python.py
python3 MARKET/MARKET-CLEARING/run_all_python.py --full-only
python3 MARKET/STRATEGIC-BIDDING/run_all_python.py

# —— 韧性 / 综合能源 ——
python3 RESILIENCE/POWER-RESTORATION/run_all_python.py --full-only
python3 RESILIENCE/DISTRIBUTION-RESTORATION/run_all_python.py
python3 RESILIENCE/CONTROLLED-ISLANDING/run_all_python.py --full-only
python3 RESILIENCE/OPTIMAL-POWER-SHUTOFF/run_all_python.py
python3 RESILIENCE/NETWORK-INTERDICTION/run_all_python.py --full-only
python3 MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS/run_all_python.py --full-only
```

### 单案例示例

```bash
python3 OTS/DC-OTS/case01_pjm5_dcots/solve_dcots.py
python3 OTS/SC-OTS/case04_ieee24_scots/solve_scots.py
python3 UC/SCUC/case01_ieee39_scuc/solve_scuc.py
python3 UC/SYSTEM-UC/case01_rts_gmlc_2020_01_27_uc/python/solve_uc.py
python3 UC/RTS-SCUC/case01_rts_gmlc_2020_01_27_rts_scuc/python/solve_rts_scuc.py
python3 DISPATCH/ECONOMIC-DISPATCH/case001_lmbd3_dc_ed/python/solve_ed.py
python3 DISPATCH/MAXIMUM-LOAD-DELIVERY/case001_case3_mld_mld/python/solve_mld.py
python3 MONITORING/PMU-PLACEMENT/case001_case3_lmbd_pmu/python/solve_pmu.py
python3 MONITORING/STATE-ESTIMATION/case001_case5_pjm_wls_se/python/solve_se.py
python3 PLANNING/TRANSMISSION-EXPANSION/case001_case3_tnep/python/solve_tep.py
python3 PLANNING/RESOURCE-CAPACITY-EXPANSION/case01_1_three_zones_cem/python/solve_cem.py
python3 SCHEDULING/HYDROTHERMAL-SCHEDULING/case07_rcuc_20_10_1_w_ht/python/solve_ht.py
python3 SCHEDULING/MAINTENANCE-SCHEDULING/case01_rts_gmlc_week168_maint/python/solve_maint.py
python3 MARKET/MARKET-CLEARING/case01_rts_gmlc_2020_01_27_market/python/solve_market.py
python3 MARKET/STRATEGIC-BIDDING/case01_toy3_copperplate_price/python/solve_bid.py
python3 RESILIENCE/POWER-RESTORATION/case001_case3_restoration_total_dmg_restore/python/solve_restore.py
python3 RESILIENCE/DISTRIBUTION-RESTORATION/case01_mv_rural_restore/python/solve_restore.py
python3 RESILIENCE/CONTROLLED-ISLANDING/case001_pjm5bus_island/python/solve_island.py
python3 RESILIENCE/OPTIMAL-POWER-SHUTOFF/case011_case3_rb00_ops/python/solve_ops.py
python3 RESILIENCE/NETWORK-INTERDICTION/case001_lmbd3_nk_int/python/solve_interdiction.py
python3 MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS/case01_travis150_ieg/python/solve_ieg.py
```

结果写入对应案例 `results/`。大网 `solve_tier=skip` 仅建议作数据/建模参考；请优先从 `full` / `relaxed` 开始。

---

## 单案例结构

```text
<CATEGORY>/<PACK>/
  common/              # 模型与共享工具
  run_all_python.py
  MANIFEST.json        # 若有
  caseXX_*/
    data/network.json
    data/config.json
    solve_*.py  或  python/solve_*.py
    results/
```

---

## 规模分级

| `solve_tier` | 含义 |
|--------------|------|
| `full` / `relaxed` | 中小规模，适合完整 MIP 与核对 |
| `skip` | 大规模（数据齐全；全量 MIP 可能极慢） |

---

## 分类与基础问题对照

| 分类 | 对应基础问题（PLAM） | 变体轴示例 |
|------|----------------------|------------|
| OTS | Optimal Transmission Switching | security=none / n-1 |
| OPF | Optimal Power Flow（线性化 SC） | security=n-1；**非精确 AC** |
| UC | Unit Commitment | copperplate / network；storage；n-1 |
| DISTRIBUTION | DNR / Volt-VAR / DER Hosting | power_flow=lindistflow |
| DISPATCH | Economic Dispatch；Maximum Load Delivery | power_flow=dc |
| MONITORING | PMU Placement；State Estimation | WLS / L1 |
| PLANNING | Transmission Expansion；Capacity Expansion | synthetic candidates / GenX |
| SCHEDULING | Hydrothermal；Maintenance | multi_period；stochastic scenarios |
| MARKET | Market Clearing；Strategic Bidding | welfare LP；bid ladder |
| RESILIENCE | Restoration；Islanding；OPS；Interdiction | multi_period；risk budget；N-k |
| MULTI-ENERGY | Integrated Electricity–Gas | Weymouth PWL；coupling |

---

## 模型要点（摘要）

### 共同约定（输电 DC 支路）

- MATPOWER：\(f = b(\theta_f-\theta_t-\varphi)\)，\(b=1/(x\cdot\mathrm{tap})\)（`ratio=0` 时 tap=1）
- 仅 `status=1` 在线机组参与出力与费用
- 默认 `Seed=1`；线程/时限见各 `config.json`
- 拓扑二进制优先 **Gurobi indicator**

### OTS / OPF

- **DC-OTS**：费用最小 + 可切换线路 + `max_open`
- **SC-OTS**：基态与 N-1 共享拓扑；事故后有限再调度
- **SC-AC-OPF-OTS**：GO C1 线性化安全约束，勿与精确 AC 等同

### UC

- **SYSTEM-UC**：系统平衡 + 备用 + 可再生，无支路潮流
- **SCUC / RTS-SCUC**：网络 DC + 多时段 UC；RTS 含储能

### DISPATCH / MONITORING

- **ED**：\(\min\sum c_2P^2+c_1P+c_0\)，DC 潮流，无启停
- **MLD**：\(\max\sum w_i P_{d,i}x_i\)，损坏元件离线
- **PMU**：0-1 可观测覆盖
- **SE**：合成测量下 WLS / L1

### PLANNING / SCHEDULING / MARKET

- **TEP**：建设二进制 + DC 运行；合成并联候选沿既有走廊
- **CEM**：容量投资 + 代表时段运行（GenX 解析）
- **HT**：库容平衡 + 水火出力；随机场景二阶段
- **Maint**：唯一开工、连续工期、crew、检修不可用
- **Market**：福利最大 LP；truthful 分段报价
- **Bidding**：离散报价档枚举 + 下层出清

### RESILIENCE / MULTI-ENERGY

- **Restoration**：带电单调、修复/启动顺序
- **Islanding**：岛归属、相干组、岛内连通
- **OPS**：风险预算与切负荷权衡（原生火险字段）
- **Interdiction**：攻击–运行 max-min / 枚举 oracle
- **IEG**：电力 DC + 气网 PWL Weymouth + heat-rate 耦合

---

## 参考结果与验收

| 子包路径 | 验收摘要 |
|----------|----------|
| `OTS/DC-OTS` | PGLib 66 例可运行 |
| `OTS/SC-OTS` | 中小规模 full/relaxed 可 OPTIMAL |
| `UC/SYSTEM-UC` | 56/56 PASS |
| `UC/RTS-SCUC` | 12/12 PASS |
| `OPF/SC-AC-OPF-OTS` | 可解档约 52 例；其余 skip |
| `DISTRIBUTION/DNR` | 6 求解 + 1 meta |
| `DISTRIBUTION/SMART-DS` | 3/3 PASS |
| `DISPATCH/ECONOMIC-DISPATCH` | 71/71 双端 PASS |
| `DISPATCH/MAXIMUM-LOAD-DELIVERY` | 18/18 PASS |
| `MONITORING/PMU-PLACEMENT` | 66/66 PASS |
| `MONITORING/STATE-ESTIMATION` | 12/12 PASS |
| `PLANNING/*` | TEP 68、CEM 10 PASS |
| `SCHEDULING/*` | HT 32、Maint 5 PASS |
| `MARKET/*` | Market 56、Bid 8 PASS |
| `RESILIENCE/*` | 恢复/孤岛/OPS/拦截均 PASS |
| `MULTI-ENERGY/*` | IEG 15 PASS |

完整数值见各案例 `results/` 与各包 `VERIFY_SUMMARY.md`（若有）。

### DC-OTS 示例

| 案例 | 基态 DCOPF | DC-OTS | 节约 | 打开线路 |
|------|----------:|-------:|-----:|----------|
| case01_pjm5_dcots | 23092.09 | 18290.00 | 4802.09 | `4, 6` |
| case02_ieee14_dcots | 2799.99 | 2461.83 | 338.16 | `2, 17` |
| case03_ieee118_dcots | 99172.90 | 98631.58 | 541.32 | `31, 66, 67` |

---

## 数据来源与许可

| 来源 | 用途 |
|------|------|
| [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) | OTS / SCUC / ED / PMU / SE / TEP / Interdiction 等 |
| [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) | SYSTEM-UC、市场、检修教学 |
| [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) | RTS-SCUC、检修 |
| [GO Competition C1](https://gocompetition.energy.gov/) | 线性化 SC-AC-OPF/OTS |
| [SimBench](https://simbench.de/) / [SMART-DS](https://data.openei.org/submissions/2981) | 配网 |
| PowerModels TNEP / Restoration / Wildfire | 规划、恢复、OPS |
| GenX / GasLib / ANDES / CommaLAB / ACTIVSg200 | CEM、电–气、孤岛、水火、黑启动 |

- 构造说明与求解脚本供**科研与教学**；使用风险自负。
- 遵守 Gurobi 与各上游数据许可；`config.json` 的 `source` 中可有更细来源与 SHA。

---

## 免责声明

线性化模型与官方 AC / 三相仿真**不可直接等同**。大规模 MIP 最优性取决于时限与 gap；`skip` 档不保证可求最优。
