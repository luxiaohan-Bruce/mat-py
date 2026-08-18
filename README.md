# 电力系统难优化算例（Python + Gurobi）

基于 **Python + Gurobi（gurobipy）** 的电网优化算例集：统一 JSON 数据、统一 `solve.py` 入口、`evaluate()` 验收、五档规模分级（`full` / `relaxed` / `large` / `xlarge` / `skip`）。

一级目录是便于浏览的 **`navigation_domain`**，不是互斥的数学基础问题分类。规范分类以每个案例 `config.json` 的 `base_problem` 为准；AC/DC、N-1、多时段、随机性、追补决策等属于 `variant` 轴。

机器可读定义与索引：[`BASE_PROBLEM_REGISTRY.json`](BASE_PROBLEM_REGISTRY.json)（分类契约）、[`CATALOG.json`](CATALOG.json)（1199 例）、[`NETWORK_INDEX.json`](NETWORK_INDEX.json)（同一张网跨问题）、[`framework/`](framework/)（生成、校验与验收工具）。

---

## 目录总览

```text
github_cases/
  OTS/                 # 输电拓扑切换
  OPF/                 # 最优潮流（DC、精确 AC、精确 SC-AC、线性化安全约束）
  UC/                  # 机组组合族
  DISTRIBUTION/        # 配网重构 / Volt-VAR / DER hosting / 微网 / 三相 DOPF
  DATACENTER/          # 多园区分流 / Green-LLM / 柔性数据中心负荷
  DISPATCH/            # 经济调度 / 需求响应
  MONITORING/          # PMU 布点 / 状态估计
  PLANNING/            # 输电扩展 / 容量扩展 / 配网扩展
  SCHEDULING/          # 水火调度 / 检修计划 / 储能调度
  MARKET/              # 市场出清 / 策略报价
  RESILIENCE/          # 切负荷 / 恢复 / 孤岛 / 主动停电 / 拦截
  MULTI-ENERGY/        # 电–气综合
  framework/           # 统一入口、特征、evaluate、目录生成
  CATALOG.json
  NETWORK_INDEX.json
  solve.py             # python3 solve.py <case_dir>
  evaluate.py          # python3 evaluate.py <case_dir>
  README.md
  requirements.txt
```

| `navigation_domain` | 子包 | `base_problem` / 含义 | 案例数 | 数据来源 |
|---------------------|------|------------------------|------:|----------|
| [`OTS/`](OTS/) | [`DC-OTS/`](OTS/DC-OTS/) | OTS（直流） | 66 | [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) |
| | [`SC-OTS/`](OTS/SC-OTS/) | `ots`：完整或抽样 N-1、共享预防性拓扑、事故后有界再调度 | 66 | PGLib-OPF |
| | [`LINEARIZED-SC-OTS/`](OTS/LINEARIZED-SC-OTS/) | `ots`：GO C1 线性化、抽样 N-1 | 158 | [GO Competition C1](https://gocompetition.energy.gov/) |
| [`OPF/`](OPF/) | [`DC-OPF/`](OPF/DC-OPF/) | `opf`：网络约束 DC-OPF | 71 | PGLib-OPF |
| | [`AC-OPF/`](OPF/AC-OPF/) | `opf`：精确非凸极坐标 AC-OPF | 4 | PGLib-OPF |
| | [`SC-AC-OPF/`](OPF/SC-AC-OPF/) | `opf`：精确极坐标预防性 N-1 | 2 | PGLib-OPF |
| | [`LINEARIZED-SC-OPF/`](OPF/LINEARIZED-SC-OPF/) | `opf`：GO C1 线性化、抽样 N-1 | 158 | GO Competition C1 |
| [`UC/`](UC/) | [`SYSTEM-UC/`](UC/SYSTEM-UC/) | 系统级 UC（无网架） | 56 | [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) |
| | [`SCUC/`](UC/SCUC/) | 网络 SCUC + N-1 | 66 | PGLib-OPF 合成时序 |
| | [`RTS-SCUC/`](UC/RTS-SCUC/) | RTS 网络 SCUC+储能+RE | 12 | [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) |
| [`DISTRIBUTION/`](DISTRIBUTION/) | [`DNR/`](DISTRIBUTION/DNR/) | `dnr`：配网重构（实验模型） | 6 | [SimBench](https://simbench.de/) + [SMART-DS](https://data.openei.org/submissions/2981) |
| | [`DISTRIBUTION-OPF/`](DISTRIBUTION/DISTRIBUTION-OPF/) | `distribution_opf`（实验模型） | 2 | SimBench |
| | [`VOLT-VAR/`](DISTRIBUTION/VOLT-VAR/) | `volt_var`（实验模型） | 1 | SMART-DS |
| | [`DER-HOSTING/`](DISTRIBUTION/DER-HOSTING/) | `der_hosting`（实验模型） | 1 | SMART-DS |
| | [`MICROGRID/`](DISTRIBUTION/MICROGRID/) | `microgrid`：并网/孤岛 EMS 与 VPP | 3 | PGLib-OPF + 光伏/储能 |
| | [`UNBALANCED-DOPF/`](DISTRIBUTION/UNBALANCED-DOPF/) | `distribution_opf`：三相 LinDistFlow | 2 | IEEE 4-node / SMART-DS linecode |
| [`DATACENTER/`](DATACENTER/) | [`GEOGRAPHIC-LOAD-BALANCING/`](DATACENTER/GEOGRAPHIC-LOAD-BALANCING/) | `datacenter_glb`：多园区推理分流 + 水/碳公平 | 6 | [Environmentally-Equitable-AI](https://github.com/Ren-Research/Environmentally-Equitable-AI) |
| | [`GREEN-LLM/`](DATACENTER/GREEN-LLM/) | `green_llm`：LLM 推理分配 + 电/碳/水/时延 | 6 | [Green_LLM](https://github.com/JJmingcc/Green_LLM) |
| | [`FLEXIBLE-DC-LOAD/`](DATACENTER/FLEXIBLE-DC-LOAD/) | `datacenter_flex`：DC-OPF / SCUC 上的时空柔性负荷 | 6 | PGLib-OPF + Wan–Li |
| [`DISPATCH/`](DISPATCH/) | [`ECONOMIC-DISPATCH/`](DISPATCH/ECONOMIC-DISPATCH/) | `economic_dispatch`：无网架铜板 ED | 3 | PGLib-OPF |
| | [`DEMAND-RESPONSE/`](DISPATCH/DEMAND-RESPONSE/) | `demand_response`：可中断+可转移负荷 | 3 | PGLib-OPF |
| [`MONITORING/`](MONITORING/) | [`PMU-PLACEMENT/`](MONITORING/PMU-PLACEMENT/) | 最优 PMU 布点 | 66 | PGLib-OPF |
| | [`STATE-ESTIMATION/`](MONITORING/STATE-ESTIMATION/) | DC WLS / L1 状态估计 | 12 | PGLib + 合成测量 |
| [`PLANNING/`](PLANNING/) | [`TRANSMISSION-EXPANSION/`](PLANNING/TRANSMISSION-EXPANSION/) | TEP / TNEP | 68 | PowerModels TNEP + PGLib |
| | [`RESOURCE-CAPACITY-EXPANSION/`](PLANNING/RESOURCE-CAPACITY-EXPANSION/) | 资源容量扩展 CEM | 10 | GenX 示例 |
| | [`GCEP-DC/`](PLANNING/GCEP-DC/) | `resource_capacity_expansion`：Texas 123-BT + DC/EOR | 3 | [PSE-Lab GCEP](https://github.com/PSE-Lab/Grid-Capacity-Expansion-under-Data-Center-and-Electrified-Manufacturing-Loads) |
| | [`DISTRIBUTION-EXPANSION/`](PLANNING/DISTRIBUTION-EXPANSION/) | `distribution_expansion`：径向 LinDistFlow | 2 | SimBench 线型构造馈线 |
| [`SCHEDULING/`](SCHEDULING/) | [`HYDROTHERMAL-SCHEDULING/`](SCHEDULING/HYDROTHERMAL-SCHEDULING/) | 水火联合调度 | 32 | CommaLAB HT-Ramp / 46-bus |
| | [`MAINTENANCE-SCHEDULING/`](SCHEDULING/MAINTENANCE-SCHEDULING/) | 机组检修计划 | 5 | RTS-GMLC / PGLib-UC |
| | [`STORAGE-SCHEDULING/`](SCHEDULING/STORAGE-SCHEDULING/) | `storage_scheduling`：循环 SOC | 3 | PGLib-OPF |
| [`MARKET/`](MARKET/) | [`MARKET-CLEARING/`](MARKET/MARKET-CLEARING/) | 福利最大化能量出清 | 56 | PGLib-UC |
| | [`STRATEGIC-BIDDING/`](MARKET/STRATEGIC-BIDDING/) | 策略性报价 | 8 | Toy / PGLib |
| [`RESILIENCE/`](RESILIENCE/) | [`MAXIMUM-LOAD-DELIVERY/`](RESILIENCE/MAXIMUM-LOAD-DELIVERY/) | 最大供电 / 切负荷 | 18 | PowerModelsRestoration + PGLib |
| | [`POWER-RESTORATION/`](RESILIENCE/POWER-RESTORATION/) | 输电恢复 | 13 | PowerModelsRestoration + ACTIVSg200 |
| | [`DISTRIBUTION-RESTORATION/`](RESILIENCE/DISTRIBUTION-RESTORATION/) | 配网服务恢复 | 4 | SimBench + SMART-DS |
| | [`CONTROLLED-ISLANDING/`](RESILIENCE/CONTROLLED-ISLANDING/) | 主动解列 / 受控孤岛 | 82 | ANDES + PGLib |
| | [`OPTIMAL-POWER-SHUTOFF/`](RESILIENCE/OPTIMAL-POWER-SHUTOFF/) | 最优主动停电（野火） | 35 | PowerModelsWildfire |
| | [`NETWORK-INTERDICTION/`](RESILIENCE/NETWORK-INTERDICTION/) | N-k 网络拦截 | 69 | PGLib-OPF |
| [`MULTI-ENERGY/`](MULTI-ENERGY/) | [`INTEGRATED-ELECTRIC-GAS/`](MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS/) | 电–气综合优化 | 15 | Travis 150 + GasLib |

**合计 1199 个案例**（含子包内 `skip` 数据档）。

> **说明**
> - 子包目录名：**大写 + 连字符**。
> - GO C1 已按基础问题拆开并如实命名为 `OPF/LINEARIZED-SC-OPF` 与 `OTS/LINEARIZED-SC-OTS`；当前事故集是抽样子集，不代表完整 N-1。
> - 原“网络化经济调度”71 例实际包含节点平衡、相角、支路潮流和热稳约束，现归入 `OPF/DC-OPF`；`DISPATCH/ECONOMIC-DISPATCH` 新增 3 个真正的铜板 ED 基准。
> - 配网已拆分为 DNR 6 例、Distribution OPF 2 例、Volt-VAR 1 例、DER hosting 1 例。其中 9 个可执行案例是 **experimental 的 active-power transport 近似**，另有 1 个 DNR 数据汇总案为 `data_only`；均不能视为已通过 AC、三相或 LinDistFlow 物理验证。
> - `DISTRIBUTION/UNBALANCED-DOPF` 是三相 LinDistFlow（线性化），不是精确三相 AC 潮流。
> - `OPF/SC-AC-OPF` 是精确极坐标预防性 N-1，与 GO 线性化 `LINEARIZED-SC-OPF` 不是同一模型。
> - 最大供电（MLD）已从 `DISPATCH/` 挪到 `RESILIENCE/`（损坏网络上的供电，不是经济调度）。
> - 每个案例目录都有 `solve.py`；`config.json` 含统一 `base_problem` / `variant` / `source_network` / `features`。

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
python3 OTS/LINEARIZED-SC-OTS/run_all_python.py --tier relaxed
python3 OPF/DC-OPF/run_all_python.py --full-only
python3 OPF/AC-OPF/run_all_python.py
python3 OPF/SC-AC-OPF/run_all_python.py
python3 OPF/LINEARIZED-SC-OPF/run_all_python.py --tier relaxed

# —— UC ——
python3 UC/SYSTEM-UC/run_all_python.py
python3 UC/SCUC/run_all_python.py
python3 UC/RTS-SCUC/run_all_python.py

# —— 配网 ——
python3 DISTRIBUTION/DNR/run_all_python.py
python3 DISTRIBUTION/DISTRIBUTION-OPF/run_all_python.py
python3 DISTRIBUTION/VOLT-VAR/run_all_python.py
python3 DISTRIBUTION/DER-HOSTING/run_all_python.py
python3 DISTRIBUTION/MICROGRID/run_all_python.py
python3 DISTRIBUTION/UNBALANCED-DOPF/run_all_python.py

# —— 数据中心 ——
python3 DATACENTER/GEOGRAPHIC-LOAD-BALANCING/run_all_python.py
python3 DATACENTER/GREEN-LLM/run_all_python.py
python3 DATACENTER/FLEXIBLE-DC-LOAD/run_all_python.py

# —— 调度 / 监测 ——
python3 DISPATCH/ECONOMIC-DISPATCH/run_all_python.py
python3 DISPATCH/DEMAND-RESPONSE/run_all_python.py
python3 MONITORING/PMU-PLACEMENT/run_all_python.py
python3 MONITORING/STATE-ESTIMATION/run_all_python.py

# —— 规划 / 时序 / 市场 ——
python3 PLANNING/TRANSMISSION-EXPANSION/run_all_python.py --full-only
python3 PLANNING/RESOURCE-CAPACITY-EXPANSION/run_all_python.py
python3 PLANNING/GCEP-DC/run_all_python.py --full-only
python3 PLANNING/DISTRIBUTION-EXPANSION/run_all_python.py
python3 SCHEDULING/HYDROTHERMAL-SCHEDULING/run_all_python.py --full-only
python3 SCHEDULING/MAINTENANCE-SCHEDULING/run_all_python.py
python3 SCHEDULING/STORAGE-SCHEDULING/run_all_python.py
python3 MARKET/MARKET-CLEARING/run_all_python.py --full-only
python3 MARKET/STRATEGIC-BIDDING/run_all_python.py

# —— 韧性 / 综合能源 ——
python3 RESILIENCE/MAXIMUM-LOAD-DELIVERY/run_all_python.py
python3 RESILIENCE/POWER-RESTORATION/run_all_python.py --full-only
python3 RESILIENCE/DISTRIBUTION-RESTORATION/run_all_python.py
python3 RESILIENCE/CONTROLLED-ISLANDING/run_all_python.py --full-only
python3 RESILIENCE/OPTIMAL-POWER-SHUTOFF/run_all_python.py
python3 RESILIENCE/NETWORK-INTERDICTION/run_all_python.py --full-only
python3 MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS/run_all_python.py --full-only
```

### 单案例（统一入口）

每个案例目录都有 `solve.py`。两条命令等价：

```bash
python3 solve.py OTS/DC-OTS/case01_pjm5_dcots
python3 OTS/DC-OTS/case01_pjm5_dcots/solve.py

python3 solve.py OPF/DC-OPF/case001_lmbd3_dc_ed
python3 solve.py DISPATCH/ECONOMIC-DISPATCH/case001_lmbd3_copperplate_ed
python3 solve.py UC/SCUC/case01_ieee39_scuc
python3 solve.py RESILIENCE/MAXIMUM-LOAD-DELIVERY/case001_case3_mld_mld
python3 solve.py DISTRIBUTION/VOLT-VAR/case02_gso_rural_voltvar
```

```bash
# 验收已有 results/python_result.json（不重新求解）
python3 evaluate.py OTS/DC-OTS/case01_pjm5_dcots

# 同一张网、跨问题
python3 evaluate.py --network pglib_opf_case14_ieee
python3 -m framework.catalog --by-network pglib_opf_case118_ieee
```

结果写入对应案例 `results/`。建议优先从 `full` / `relaxed` 开始；`large` / `xlarge` 需要更长时限，`skip` 主要用于数据与建模检查。

---

## 单案例结构

```text
<NAVIGATION_DOMAIN>/<PACK>/
  common/              # 模型与共享工具
  run_all_python.py
  MANIFEST.json        # 若有
  caseXX_*/
    data/network.json
    data/config.json   # base_problem, variant, source_network, features
    python/solve_*.py  # 包内求解器
    solve.py           # 统一入口（转调 python/solve_*.py）
    results/
```

`config.features` 含 `n_bus` / `n_branch` / `n_gen` / `T` / `n_contingency` / `n_bin`。  
`config.source_network` 把同一张物理网（如 `pglib_opf_case14_ieee`）上的 OPF / ED / OTS / UC / PMU / TEP / 拦截等串起来。目录名提供浏览入口，不代替 `base_problem` 与 `variant` 的机器可读分类。

---

## 规模分级

| `solve_tier` | 当前案例数 | 含义 |
|--------------|--------------:|------|
| `full` | 427 | 默认完整求解与验收 |
| `relaxed` | 182 | 可求解，通常需更宽的时限或 gap |
| `large` | 23 | 大规模档 |
| `xlarge` | 24 | 超大规模档 |
| `skip` | 543 | 数据与建模参考，不承诺在常规时限内求优 |

机器规则见 [`BASE_PROBLEM_REGISTRY.json`](BASE_PROBLEM_REGISTRY.json)；修改目录、`config.json` 或分类后，运行 `python3 framework/validate_taxonomy.py` 检查路径、基础问题、变体轴、规模档与特征字段的一致性。

---

## 导航域、基础问题与变体轴

| `navigation_domain` | 当前 `base_problem` | 变体轴示例 |
|---------------------|--------------------------|------------|
| OTS | `ots` | `power_flow=dc/dc_linearized`；`security=none/n-1/sampled_n-1` |
| OPF | `opf` | `power_flow=dc/ac_exact/dc_linearized`；`security=none/n-1/sampled_n-1` |
| UC | `uc` | copperplate / network；storage；security |
| DISTRIBUTION | `dnr`、`distribution_opf`、`volt_var`、`der_hosting`、`microgrid` | 旧配网包为 `active_power_transport`；新包含铜板微网与三相 LinDistFlow |
| DATACENTER | `datacenter_glb`、`green_llm`、`datacenter_flex` | 多园区分流；LLM 分配；网架上的 DC 柔性 |
| DISPATCH | `economic_dispatch`、`demand_response` | `power_flow=copperplate`；可中断/可转移负荷 |
| MONITORING | `pmu_placement`、`state_estimation` | WLS / L1 |
| PLANNING | `transmission_expansion`、`resource_capacity_expansion`、`distribution_expansion` | candidate type；径向 LinDistFlow；Texas 123-BT GCEP |
| SCHEDULING | `hydrothermal_scheduling`、`maintenance_scheduling`、`storage_scheduling` | multi-period；循环 SOC |
| MARKET | `market_clearing`、`strategic_bidding` | welfare LP；bid ladder |
| RESILIENCE | `maximum_load_delivery`、`power_restoration`、`distribution_restoration`、`controlled_islanding`、`optimal_power_shutoff`、`network_interdiction` | damaged network；temporal restoration；N-k |
| MULTI-ENERGY | `integrated_electric_gas` | gas relaxation；coupling |

### 当前缺口 / coverage roadmap

已补齐并可验收的 pilot：

- 精确 AC-OPF：3/5/14/30-bus。
- 精确预防性 SC-AC-OPF：3-bus 选定 N-1、5-bus 抽样 N-1。
- Demand Response、Storage Scheduling、Distribution Expansion、Microgrid/VPP。
- 三相 LinDistFlow DOPF（IEEE 4-node 风格 + SMART-DS 线型 6 节点）。
- 数据中心：EE-AI 多园区分流、Green-LLM 推理分配、IEEE 网架柔性 DC 负荷、Texas 123-BT GCEP。

仍缺、且不会用不完整模型冒充的部分：

1. 中大规模与完整 N-1 的精确 AC-OPF / SC-AC-OPF。
2. 用精确三相 AC 交叉验证的 DNR / Volt-VAR / DER hosting。
3. 非平衡三相配网扩展与三相微网。

`stochastic`、`robust`、`reserve` 是叠加在 ED / OPF / UC / scheduling / planning 等基础问题上的变体轴，不单独新建一级分类。

---

## 模型要点（摘要）

### 共同约定（输电 DC 支路）

- MATPOWER：\(f = b(\theta_f-\theta_t-\varphi)\)，\(b=1/(x\cdot\mathrm{tap})\)（`ratio=0` 时 tap=1）
- 仅 `status=1` 在线机组参与出力与费用
- 默认 `Seed=1`；线程/时限见各 `config.json`
- 拓扑二进制优先 **Gurobi indicator**

### OTS / OPF

- **DC-OTS**：费用最小 + 可切换线路 + `max_open`
- **SC-OTS**：`topology_control=preventive_shared`，基态与配置事故共享拓扑；`generation_recourse=corrective_bounded`，事故后允许有界再调度。仅 case02、case04–06 覆盖全部可信非孤岛单线路事故，其余按配置标为 `sampled_n-1` 或 `none`
- **DC-OPF**：节点平衡 + 相角/支路潮流 + 热稳约束，无线路开断
- **AC-OPF**：精确极坐标 P/Q 平衡、电压/相角、tap/移相与支路两端 MVA 限制；Gurobi `NonConvex=2` 全局求解 pilot
- **LINEARIZED-SC-OPF / LINEARIZED-SC-OTS**：GO C1 的 DC 线性化安全约束，仅用配置中的抽样事故子集；事故态发电可在机组 `0/Pmax` 上下界内校正重调度（`corrective_within_generator_bounds`），且 OTS 的开断拓扑由基态与事故态共享（`preventive_shared`）；勿与精确 AC 或完整 N-1 等同

### UC

- **SYSTEM-UC**：系统平衡 + 备用 + 可再生，无支路潮流
- **SCUC / RTS-SCUC**：网络 DC + 多时段 UC；RTS 含储能

### DISPATCH / MONITORING

- **ED**：\(\min\sum c_2P^2+c_1P+c_0\)，单系统铜板平衡，无网架约束、无启停
- **PMU**：0-1 可观测覆盖
- **SE**：合成测量下 WLS / L1

### PLANNING / SCHEDULING / MARKET

- **TEP**：建设二进制 + DC 运行；合成并联候选沿既有走廊
- **CEM**：容量投资 + 代表时段运行（GenX 解析）
- **GCEP-DC**：Texas 123-BT 多年度 DC-OPF 扩容 + 县内 DC/EOR 负荷分配
- **HT**：库容平衡 + 水火出力；随机场景二阶段
- **Maint**：唯一开工、连续工期、crew、检修不可用
- **Market**：福利最大 LP；truthful 分段报价
- **Bidding**：离散报价档枚举 + 下层出清

### RESILIENCE / MULTI-ENERGY

- **MLD**：\(\max\sum w_i P_{d,i}x_i\)，损坏元件离线（静态，不是恢复时序）
- **Restoration**：带电单调、修复/启动顺序
- **Islanding**：岛归属、相干组、岛内连通
- **OPS**：风险预算与切负荷权衡（原生火险字段）
- **Interdiction**：攻击–运行 max-min / 枚举 oracle
- **IEG**：电力 DC + 气网 PWL Weymouth + heat-rate 耦合

---

## 参考结果与验收

| 子包路径 | 验收摘要 |
|----------|----------|
| `OTS/DC-OTS` | 26 个 full/relaxed 案例已有 OPTIMAL 结果，40 个 `skip` |
| `OTS/SC-OTS` | 19 个 full/relaxed 案例已有 OPTIMAL 结果，47 个 `skip` |
| `UC/SYSTEM-UC` | 56/56 PASS |
| `UC/RTS-SCUC` | 12/12 PASS |
| `UC/SCUC` | 18 个 full/relaxed 案例有可行结果（17 OPTIMAL、1 TIME_LIMIT），48 个 `skip` |
| `OPF/DC-OPF` | 42 例已有 OPTIMAL 结果，29 例 `skip` |
| `OPF/AC-OPF` | 3/3 OPTIMAL + 独立 AC 残差重算 PASS |
| `DATACENTER/GEOGRAPHIC-LOAD-BALANCING` | 6/6 OPTIMAL，Python/MATLAB 目标与分流约束对照 PASS |
| `DATACENTER/GREEN-LLM` | 6/6 OPTIMAL，含 1 个落地 MILP |
| `DATACENTER/FLEXIBLE-DC-LOAD` | 6/6 OPTIMAL；IEEE 24 时空柔性相对时移约降本 6.3% |
| `DISPATCH/ECONOMIC-DISPATCH` | 3/3 OPTIMAL，平衡/边界/费用重算验收通过 |
| `OPF/LINEARIZED-SC-OPF` + `OTS/LINEARIZED-SC-OTS` | 各 158 例；各 38 例 `relaxed` 已有 OPTIMAL 结果，各 120 例 `skip`；仅抽样 N-1 |
| `DISTRIBUTION/*` | DNR 6、Distribution OPF 2、Volt-VAR 1、DER hosting 1；9 个可执行案为 experimental，1 个汇总案为 data-only，均不声明 physics-validated / PASS |
| `RESILIENCE/MAXIMUM-LOAD-DELIVERY` | 18/18 PASS |
| `MONITORING/PMU-PLACEMENT` | 37 个 full/relaxed PASS，29 个 `skip` |
| `MONITORING/STATE-ESTIMATION` | 12/12 PASS |
| `PLANNING/*` | TEP 23 个 full/relaxed PASS + 45 `skip`；CEM 10/10 PASS；GCEP-DC 3/3 OPTIMAL |
| `SCHEDULING/*` | HT 29 个 validated feasible + 3 `skip`；Maint 5/5 PASS |
| `MARKET/*` | Market 56、Bid 8 PASS |
| `RESILIENCE/*` | Power restoration 9+4 skip；Distribution restoration 3+1 skip；Islanding 75+7 skip；OPS 35/35；Interdiction 21+48 skip |
| `MULTI-ENERGY/*` | IEG 14 个 full/relaxed PASS，1 个 `skip` |

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
| [PGLib-OPF](https://github.com/power-grid-lib/pglib-opf) | OTS / OPF / SCUC / ED / PMU / SE / TEP / Interdiction 等 |
| [PGLib-UC](https://github.com/power-grid-lib/pglib-uc) | SYSTEM-UC、市场、检修教学 |
| [RTS-GMLC](https://github.com/GridMod/RTS-GMLC) | RTS-SCUC、检修 |
| [GO Competition C1](https://gocompetition.energy.gov/) | LINEARIZED-SC-OPF 与 LINEARIZED-SC-OTS（抽样事故子集） |
| [SimBench](https://simbench.de/) / [SMART-DS](https://data.openei.org/submissions/2981) | 配网 |
| PowerModels TNEP / Restoration / Wildfire | 规划、恢复、OPS |
| GenX / GasLib / ANDES / CommaLAB / ACTIVSg200 | CEM、电–气、孤岛、水火、黑启动 |
| Environmentally-Equitable-AI / Green_LLM / PSE-Lab GCEP | 数据中心分流、LLM 分配、Texas 123-BT 扩容 |

- 构造说明与求解脚本供**科研与教学**；使用风险自负。
- 遵守 Gurobi 与各上游数据许可；`config.json` 的 `source` 中可有更细来源与 SHA。

---

## 免责声明

线性化输电模型与官方 AC 模型**不可直接等同**；当前实验性配网模型也不等同于经验证的非平衡三相潮流。大规模 MIP 最优性取决于时限与 gap；`skip` 档不保证可求最优。
