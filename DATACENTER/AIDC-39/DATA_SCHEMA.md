# AIDC-39 数据字段、单位与生成规则

每例的输入由 `data/network.json`、`data/aidc.json` 和 `data/config.json` 组成。JSON 是完整数值输入，不依赖旧算例、外部请求轨迹或在线下载。运行求解器需要 Python、NumPy、Gurobi 与有效许可证；仅复算已有结果需要 Python 和 NumPy。

## 索引和时间约定

正式时域为 `T=96`、`dt_hours=0.25`，总长 24 小时。时段编号为 0～95；第 t 个时段对应 `[t/4,(t+1)/4)` 小时。到达/截止用时段边界表示，截止值 96 表示当日末尾。工作窗口为 `[release,deadline)`，不是闭区间。

母线编号沿用原文件的 1～39；支路 `id`、工作 `id`、区域、模型、站点和场景下标从零开始。所有数值调度数组的**第一维为时间**，与 Gurobi 内部变量索引顺序无关。电量使用 MW×小时，不能直接把 15 分钟功率相加当作 MWh。

## `network.json`

| 字段 | 含义、单位及约定 |
|---|---|
| `name, source, source_commit, source_sha256` | 原始网架名称、固定版本 URL、提交和文件 SHA-256 |
| `baseMVA` | 100 MVA |
| `buses[39]` | MATPOWER 顺序；`bus_i` 编号，`Pd` MW、`Qd` Mvar、`baseKV` kV，其余源数据原样保留 |
| `gens[10]` | 原有电源，`bus` 接入母线、`Pmax/Pmin/Pg` MW，`c1` 美元/MWh；`c2=0`、`c0` 为原成本数据 |
| `branches[46]` | `fbus/tbus` 母线、`r/x/b` 标幺值，`ratio` 变比，`angle/angmin/angmax` 度；`ratio=0` 解释为 1 |
| `branches[].rateA/rateB/rateC` | 原始 MVA 额定值；本 DC 模型使用 `rateA` 的数值作为 MW 限制 |
| `status` | 在线标记；本包固定网架的原始设备全部在线 |
| `renewable[2]` | 仅第三例，另加的合成风光电源描述，350 MW 风电在 21 号、250 MW 光伏在 26 号 |
| `storage[3]` | 仅第三例，三站储能 40 MW/100 MWh 的目录元数据；运行参数以 `aidc.sites` 为准 |

源文件保留于 `source/pglib_opf_case39_epri.m`，每次生成先核对 SHA-256。DC 模型没有使用原始 AC 电压/无功/电阻损耗方程；UC 最小出力使用下述合成参数覆盖原 `Pmin`。目录第三例的 `n_gen=12` 包括新增风光，**原有电源始终为 10 个**，母线与支路没有增加。

## `aidc.json` 的公共字段

| 字段 | 单位/含义 |
|---|---|
| `schema_version, kind` | 版本 1；`training / inference / stochastic` |
| `seed` | 数据种子 101 / 202 / 303；与求解器种子区分 |
| `T, dt_hours` | 时段数、小时/时段 |
| `background_multiplier[T]` | 无量纲，乘原始 `Pd`；`peak*(0.8+0.2*sin(pi*(t/T-0.25))²)`，peak 为 .85/.68/.85 |
| `uc[10].bus, must_run` | 对应电源母线、固定在线标记；30、39 固定在线 |
| `uc[].pmin_mw` | MW；39 号为零，其余为 `0.2*Pmax` |
| `uc[].ramp_mw_per_hour` | MW/h；`0.6*Pmax`，实际时段爬坡乘 .25 |
| `uc[].min_up_slots, min_down_slots` | 均 8 时段；最后无法完成保持期的启停被禁止 |
| `uc[].initial_on, initial_status_age_slots` | 均为 1、16；不指定日初出力，第二时段起检查爬坡 |
| `uc[].startup_cost, shutdown_cost` | 美元/次；分别 `.25*Pmax*c1`、0 |
| `uc[].no_load_cost_per_hour` | 美元/h；`.04*Pmax*c1`，39 号为零 |
| `provenance` | 公共电网来源、合成字段类别及 `previous_aidc_data_used=false` |

## 训练例

| 字段 | 单位/含义 |
|---|---|
| `site` | `bus=16, pcc_max_mw=300, blocks=64, idle_it_mw=16, pue=1.25` |
| `modes[3].name, speed, mw_per_block` | eco/balanced/fast；速度 .70/.85/1.00 标准块小时/(块·小时)，IT 功率 2/2.7/3.5 MW/块 |
| `n_jobs, jobs[240].id` | 当前难度档的作业数量及标识；原版 160 作业已归档 |
| `jobs[].blocks` | 固定并行规模，取 2/4/8 个聚合块 |
| `jobs[].work_block_hours` | 标准块小时；连续执行时间为 `ceil(work/(blocks*speed*dt))` |
| `jobs[].release, deadline` | 时段边界，执行区间必须完全落在窗口内 |
| `jobs[].wait_cost_per_hour` | 美元/h，整数 3～12 乘 4.5，即 13.5～54；乘完成时间减到达时间，包含排队和执行时间 |
| `jobs[].witness_start, witness_mode` | 生成时的最快档可行装箱见证，用于初始解；不是固定决策或最优标签 |

生成顺序：从 PCG64(101) 抽取并行块数、最快档长度 2～12 时段和开始位置，在同时占用不超过 60 块的装箱中接受作业；向前/后扩大窗口，再抽取成本。正式版共生成 240 个作业，前后窗口扩展量独立均匀取 0～18 时段，成本抽取后乘 4.5。每个作业最多尝试 2000 次；失败会报错而非悄悄删减工作量。较慢档向上取整到整个时段，整段占用和用电。短时域单元测试保留较少作业和未缩放成本，正式输入默认参数在 `common/data.py` 中固定。

## 推理例

| 字段 | 单位/含义 |
|---|---|
| `sites[3]` | 顺序为母线 4、16、27；各 48 块、200 MW、3200 GB 模型内存；PUE 1.20/1.25/1.30 |
| `sites[].idle_it_mw, boot_mw_per_block` | 8 MW 固定 IT 功率、2 MW/正在启动块 |
| `sites[].startup_cost_per_block, deploy_cost_per_replica` | 18、12 美元/次 |
| `sites[].bandwidth_gbps` | 150 Gbps 站点总接入容量 |
| `services[6].capacity_rps` | 单副本安全服务上限，依次 900/800/700/600/500/400 requests/s |
| `services[].processing_ms` | 与上述上限配套的合成固定处理时延 8/12/18/25/32/40 ms |
| `services[].slo_ms` | 端到端上限 40/50/55/70/80/90 ms |
| `services[].memory_gb` | 每副本 40/48/60/72/90/110 GB，启动期也占用 |
| `services[].active_idle_mw, dynamic_mw_at_capacity` | 活跃空载 `1.1+.08*m` MW/副本，满服务量动态增加 1.75 MW/副本 |
| `services[].megabits_per_request` | 每请求 1/1.5/2/3/4/6 Mbit |
| `n_regions, demand_rps[T][6][6]` | 6 个区域；按时间、区域、模型保存当期请求速率 |
| `latency_ms[6][3]` | 区域到站点通信时延 ms；就近为 8，其余 `22+9*abs(d-r//2)+2*(r%2)` |
| `link_gbps[6][3]` | 各区域到站点 50 Gbps |
| `route_cost_per_million_requests[6][3]` | `.6+.08*latency_ms` 美元/百万请求；请求总量为 rps×3600×.25 |
| `initial_replicas[3][6], baseline_replicas[3][6]` | 本地两区域全日峰值/单副本能力向上取整；初始已满足最短在线期 |
| `boot_slots, minimum_active_slots` | 1、4；本版本启动耗时固定一时段 |
| `contingencies[35]` | 删除一条支路后仍连通的全部支路 id；对应 MATPOWER 行号为 id+1 |

请求生成式为 `capacity_m*(1.05+.045*r)*(.85+.65*sin(pi*(t/T-.23-.018*r))²)*(1+.10*sin(2*pi*t/T+m))*(1+epsilon)`，`epsilon` 由 PCG64(202) 均匀抽取于 [-.025,.025]，最终保留 5 位小数。模型时延与服务能力是合成表，不表示排队模型、商业硬件测量或真实 SLA 保证。

## 随机例

| 字段 | 单位/含义 |
|---|---|
| `sites[3]` | 母线 4/16/27，200 MW、48 块、PUE=1.25；固定 IT 8 MW |
| `idle_mw_per_block, dynamic_mw_per_busy_block` | 每可用块空载 1 MW，每忙碌块动态再增加 2 MW |
| `block_start_cost, initial_blocks` | 25 美元/新增块、32 个初始可用块 |
| `battery_power_mw, battery_energy_mwh, initial_energy_mwh` | 40 MW、100 MWh、80 MWh；日初和日末严格相等 |
| `eta_charge, eta_discharge` | .95、.95；无量纲 |
| `ups_hours, critical_inference_fraction` | .25 h、.25；关键负荷含固定负荷及 25% 推理，正常运行仍完成全部推理 |
| `battery_throughput_cost_per_mwh` | 2 美元/(MWh 充电量+MWh 放电量) |
| `cohorts[18]` | 依站点再依到达排序；`site` 为 0/1/2，`release/deadline` 为边界、`work_block_hours` 为标准块小时 |
| `renewables[2]` | `bus/kind/pmax_mw`：母线、wind/solar、MW 额定值 |
| `scenarios[20].id, probability` | id 0～19、等概率 .05 |
| `scenarios[].renewable_mw[T][2]` | 当期可用风电/光伏 MW 上限 |
| `scenarios[].inference_blocks[T][3]` | 当期推理所需等效忙碌块数，可以为连续值；容量决策仍为整数 |
| `nominal` | 上述两个数组的逐元素场景均值，`id="nominal"` |
| `cvar_alpha, risk_weight` | .9、.2；作用于场景运行成本 CVaR |
| `reserve_fraction` | .05，分别约束上调和下调备用总量 |
| `reserve_up_cost_per_mw_hour, reserve_down_cost_per_mw_hour` | 1、.3 美元/(MW·h) |
| `reserve_response_hours, curtailment_cost_per_mwh` | .25 h、1 美元/MWh |
| `information_structure` | 两阶段，追补时已知该场景整个轨迹 |

每站每 16 时段到达训练批次；工作量为 `(10+d)*window_hours*(1+epsilon)`，`epsilon` 均匀分布于 [-.08,.08]。PCG64(303) 接着生成 AR(1) 轨迹 `z[t]=.92*z[t-1]+sqrt(1-.92²)*N(0,1)`，输出截断至 [-2,2]。风电基准为 `350*(.55+.16*cos(2*pi*(h-3)/24))`，光伏基准为 `250*max(0,sin(pi*(h-6)/12))`，分别乘 `1+.16*z_w`、`1+.18*z_s` 后截断至额定值。推理为 `(13+5*sin(pi*(t/T-.2))²+d)*(1+.065*z_common+.025*z_local_d)`。风光时间轨迹分别采样，推理站点共享一项扰动；不声称拟合了真实气象与请求的横向相关系数。正式版 `h=t/4`。小规模测试把日曲线压缩到较短时域，但保持 15 分钟步长。

## `config.json` 与规模统计

求解设置 `seed=1, threads=4, time_limit=600, mip_gap=.001`；此外 `FeasibilityTol=IntFeasTol=1e-8`。时限仅累计求解器时间，不包括构模和写文件。若独立校验发现接近整数的数值误差，则在剩余时限内固定整数策略重新求解连续调度，保留原 MILP 的全局界并重新验收；结果记录 `integer_polish`。

`problem="aidc39"`、`base_problem="datacenter_flex"`，`variant` 描述 DC、多时段、UC、事故与不确定性。`model_size` 是构模后、预处理前的实际变量/线性行/非零元统计；`n_binary` 包括固定的二元变量，`n_general_integer` 不包括二元变量。变量上下界不计入线性约束行。`features` 将这些值映射到目录；`physics_validated` 表示已有正式解通过独立 DC 与业务验收。

训练例另保存 `difficulty_target_seconds=100` 与 `training_profile={n_jobs:240,wait_cost_scale:4.5}`。它们用于说明难度标定，不改变求解停止规则；正式时间上限仍为 600 秒。

## 结果格式与独立验收

`results/python_result.json`、`baseline_result.json`，以及第三例 `mean_policy_result.json` 使用相同顶层结构：

- `input_sha256`：合并电网与业务输入、按键排序规范化 JSON 的 SHA-256；不含配置和求解器参数，后者另存于 `metadata`。
- `aidc39`：状态、目标、全局界、相对间隙、求解时间、首次可行解时间、节点数、实际规模和验证标记。不可行/无解时目标与间隙为 null，验证失败。
- `cost_breakdown`：各项目成本，单位美元；系统发电成本只计一次。第三例另列期望运行成本、备用、算力启动和 `.2*CVaR`。
- `validation`：数值残差、各项容差、违规项、独立重算成本和业务指标。
- `metadata`：版本、机器架构、实际求解设置、构模/校验/墙钟时间，对照说明及可选数值修复信息；修复发生时 `validation_seconds` 包含修复阶段墙钟，不与 `runtime` 直接相加。

前两例 `schedule` 包含 `uc.on/start/stop[T][10]`、`pg_mw[T][10]`、`theta_rad[T][39]`、`flow_mw[T][46]`、`imports_mw[T][D]`。训练另保存每个作业的 `job/mode/start/duration`；推理另保存 `replicas/replica_boot/replica_stop[T][3][6]`、`routes_rps[T][6][6][3]` 和完整事故列表。事故潮流没有另存冗余副本，可由相同注入及退出拓扑唯一重建。

第三例 `first_stage` 保存 UC、`gpu_blocks/gpu_starts[T][3]`、`pg0_mw/reserve_up_mw/reserve_down_mw[T][10]`。`nominal` 与 20 个 `scenarios` 分别保存上述网络量，以及 `facility_mw/charge_mw/discharge_mw/charging[T][3]`、`energy_mwh[T+1][3]`、`renewable_mw[T][2]`、`training_blocks[T][18]` 和 `operating_cost`。另存 `cvar_eta`、`cvar_excess[20]`；固定均值计划的对照保存 `fixed_first_stage` 用于逐项比对。

功率和请求速率容差 1e-4（各自单位）、整数/块容量 1e-6、相角 1e-7 rad、SOC 1e-5 MWh、训练工作量 1e-5 块小时。证书包含完整逐类最大残差和容差。`evaluate.py` 从输入及保存的数值重新检查，拒绝丢失任务、丢失场景、非有限值、功率篡改和输入哈希不匹配等错误。保存的 PASS 不能代替复算。
