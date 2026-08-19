# 求解时间汇总

删除无入口与 INFEASIBLE 案例之后，剩余 **1162** 例。`TimeLimit` 已统一为 **600 s**。
本表是历史求解记录，不是在 600 s 时限下重跑。

数据来源：

- skip 档：`mat-py-main-skip-run-1000s-t8-copt-20260817/results.jsonl`（COPT 8.0.4 via Gurobi compat，当时 TimeLimit=1000 s，进程墙钟上限 1500 s）
- 非 skip：各案例 `results/python_result.json` 的 `runtime` / `runtime_seconds`（本地 Gurobi，当时用各案自己的 TimeLimit）
- 主问题 runtime：OTS 取 `ots` 而非全闭 DCOPF；`process_timeout` 用 `wall_seconds`

**难求解**：该次记录 runtime **> 600 s**（含 1500 s 进程超时）。

## 总览

| 指标 | 值 |
|---|---:|
| 剩余案例 | 1162 |
| 有 runtime | 1154 |
| 无 runtime | 8 |
| median (s) | 0.833 |
| mean (s) | 177.9 |
| p95 (s) | 1500.0 |
| max (s) | 1500.8 |
| 难求解（runtime>600s） | 129 |

记录来源计数：`python_result`=656, `skip_jsonl`=506

## 按子包（navigation pack）

| pack | 案例数 | 有 runtime | 缺失 | median (s) | mean (s) | p95 (s) | max (s) | runtime>600s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `DATACENTER/FLEXIBLE-DC-LOAD` | 6 | 6 | 0 | 0.794 | 2.032 | 8.746 | 8.746 | 0 |
| `DATACENTER/GEOGRAPHIC-LOAD-BALANCING` | 6 | 6 | 0 | 0.026 | 0.087 | 0.388 | 0.388 | 0 |
| `DATACENTER/GREEN-LLM` | 6 | 6 | 0 | 0.025 | 0.135 | 0.649 | 0.649 | 0 |
| `DISPATCH/DEMAND-RESPONSE` | 3 | 3 | 0 | 0.001 | 0.001 | 0.003 | 0.003 | 0 |
| `DISPATCH/ECONOMIC-DISPATCH` | 3 | 3 | 0 | 0.001 | 0.001 | 0.003 | 0.003 | 0 |
| `DISTRIBUTION/DER-HOSTING` | 1 | 1 | 0 | 0.001 | 0.001 | 0.001 | 0.001 | 0 |
| `DISTRIBUTION/DISTRIBUTION-OPF` | 2 | 2 | 0 | 0.021 | 0.021 | 0.028 | 0.028 | 0 |
| `DISTRIBUTION/DNR` | 5 | 5 | 0 | 0.005 | 0.008 | 0.019 | 0.019 | 0 |
| `DISTRIBUTION/MICROGRID` | 3 | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `DISTRIBUTION/UNBALANCED-DOPF` | 2 | 2 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `DISTRIBUTION/VOLT-VAR` | 1 | 1 | 0 | 0.001 | 0.001 | 0.001 | 0.001 | 0 |
| `MARKET/MARKET-CLEARING` | 56 | 56 | 0 | 0.143 | 0.160 | 0.335 | 0.523 | 0 |
| `MARKET/STRATEGIC-BIDDING` | 8 | 8 | 0 | 0.002 | 0.002 | 0.003 | 0.003 | 0 |
| `MONITORING/PMU-PLACEMENT` | 66 | 66 | 0 | 0.007 | 97.04 | 1000.4 | 1500.1 | 5 |
| `MONITORING/STATE-ESTIMATION` | 12 | 12 | 0 | 0.001 | 0.002 | 0.005 | 0.015 | 0 |
| `MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS` | 14 | 14 | 0 | 0.006 | 0.011 | 0.015 | 0.052 | 0 |
| `OPF/AC-OPF` | 4 | 4 | 0 | 78.65 | 264.4 | 900.0 | 900.0 | 1 |
| `OPF/DC-OPF` | 71 | 71 | 0 | 0.042 | 106.3 | 1500.1 | 1500.2 | 5 |
| `OPF/LINEARIZED-SC-OPF` | 158 | 158 | 0 | 9.102 | 54.67 | 398.0 | 440.8 | 0 |
| `OPF/SC-AC-OPF` | 2 | 2 | 0 | 300.3 | 300.3 | 600.0 | 600.0 | 1 |
| `OTS/DC-OTS` | 65 | 65 | 0 | 1.093 | 144.4 | 1500.0 | 1500.2 | 6 |
| `OTS/LINEARIZED-SC-OTS` | 158 | 150 | 8 | 23.06 | 135.9 | 1500.2 | 1500.4 | 10 |
| `OTS/SC-OTS` | 51 | 51 | 0 | 11.90 | 509.0 | 1500.2 | 1500.3 | 17 |
| `PLANNING/DISTRIBUTION-EXPANSION` | 2 | 2 | 0 | 0.002 | 0.002 | 0.003 | 0.003 | 0 |
| `PLANNING/GCEP-DC` | 3 | 3 | 0 | 10.45 | 148.8 | 435.1 | 435.1 | 0 |
| `PLANNING/RESOURCE-CAPACITY-EXPANSION` | 10 | 10 | 0 | 0.005 | 0.005 | 0.010 | 0.010 | 0 |
| `PLANNING/TRANSMISSION-EXPANSION` | 67 | 67 | 0 | 0.439 | 114.6 | 1500.2 | 1500.4 | 5 |
| `RESILIENCE/CONTROLLED-ISLANDING` | 82 | 82 | 0 | 0.007 | 37.24 | 22.41 | 1000.4 | 3 |
| `RESILIENCE/DISTRIBUTION-RESTORATION` | 3 | 3 | 0 | 0.040 | 0.054 | 0.122 | 0.122 | 0 |
| `RESILIENCE/MAXIMUM-LOAD-DELIVERY` | 18 | 18 | 0 | 0.000 | 0.000 | 0.001 | 0.002 | 0 |
| `RESILIENCE/NETWORK-INTERDICTION` | 68 | 68 | 0 | 1500.0 | 1038.9 | 1500.1 | 1500.1 | 47 |
| `RESILIENCE/OPTIMAL-POWER-SHUTOFF` | 35 | 35 | 0 | 0.001 | 0.194 | 0.043 | 5.335 | 0 |
| `RESILIENCE/POWER-RESTORATION` | 13 | 13 | 0 | 0.099 | 155.1 | 1000.3 | 1000.3 | 2 |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | 32 | 32 | 0 | 8.969 | 159.2 | 1000.7 | 1001.6 | 4 |
| `SCHEDULING/MAINTENANCE-SCHEDULING` | 5 | 5 | 0 | 0.014 | 0.046 | 0.190 | 0.190 | 0 |
| `SCHEDULING/STORAGE-SCHEDULING` | 3 | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `UC/RTS-SCUC` | 12 | 12 | 0 | 0.823 | 0.830 | 1.011 | 1.136 | 0 |
| `UC/SCUC` | 50 | 50 | 0 | 437.1 | 705.9 | 1500.5 | 1500.8 | 23 |
| `UC/SYSTEM-UC` | 56 | 56 | 0 | 6.033 | 17.79 | 50.62 | 61.40 | 0 |

## 按 `base_problem`

| base_problem | 案例数 | 有 runtime | 缺失 | median (s) | mean (s) | p95 (s) | max (s) | runtime>600s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `controlled_islanding` | 82 | 82 | 0 | 0.007 | 37.24 | 22.41 | 1000.4 | 3 |
| `datacenter_flex` | 6 | 6 | 0 | 0.794 | 2.032 | 8.746 | 8.746 | 0 |
| `datacenter_glb` | 6 | 6 | 0 | 0.026 | 0.087 | 0.388 | 0.388 | 0 |
| `demand_response` | 3 | 3 | 0 | 0.001 | 0.001 | 0.003 | 0.003 | 0 |
| `der_hosting` | 1 | 1 | 0 | 0.001 | 0.001 | 0.001 | 0.001 | 0 |
| `distribution_expansion` | 2 | 2 | 0 | 0.002 | 0.002 | 0.003 | 0.003 | 0 |
| `distribution_opf` | 4 | 4 | 0 | 0.007 | 0.011 | 0.028 | 0.028 | 0 |
| `distribution_restoration` | 3 | 3 | 0 | 0.040 | 0.054 | 0.122 | 0.122 | 0 |
| `dnr` | 5 | 5 | 0 | 0.005 | 0.008 | 0.019 | 0.019 | 0 |
| `economic_dispatch` | 3 | 3 | 0 | 0.001 | 0.001 | 0.003 | 0.003 | 0 |
| `green_llm` | 6 | 6 | 0 | 0.025 | 0.135 | 0.649 | 0.649 | 0 |
| `hydrothermal_scheduling` | 32 | 32 | 0 | 8.969 | 159.2 | 1000.7 | 1001.6 | 4 |
| `integrated_electric_gas` | 14 | 14 | 0 | 0.006 | 0.011 | 0.015 | 0.052 | 0 |
| `maintenance_scheduling` | 5 | 5 | 0 | 0.014 | 0.046 | 0.190 | 0.190 | 0 |
| `market_clearing` | 56 | 56 | 0 | 0.143 | 0.160 | 0.335 | 0.523 | 0 |
| `maximum_load_delivery` | 18 | 18 | 0 | 0.000 | 0.000 | 0.001 | 0.002 | 0 |
| `microgrid` | 3 | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `network_interdiction` | 68 | 68 | 0 | 1500.0 | 1038.9 | 1500.1 | 1500.1 | 47 |
| `opf` | 235 | 235 | 0 | 6.127 | 75.93 | 415.0 | 1500.2 | 7 |
| `optimal_power_shutoff` | 35 | 35 | 0 | 0.001 | 0.194 | 0.043 | 5.335 | 0 |
| `ots` | 274 | 266 | 8 | 17.45 | 209.5 | 1500.2 | 1500.4 | 33 |
| `pmu_placement` | 66 | 66 | 0 | 0.007 | 97.04 | 1000.4 | 1500.1 | 5 |
| `power_restoration` | 13 | 13 | 0 | 0.099 | 155.1 | 1000.3 | 1000.3 | 2 |
| `resource_capacity_expansion` | 13 | 13 | 0 | 0.005 | 34.34 | 10.45 | 435.1 | 0 |
| `state_estimation` | 12 | 12 | 0 | 0.001 | 0.002 | 0.005 | 0.015 | 0 |
| `storage_scheduling` | 3 | 3 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |
| `strategic_bidding` | 8 | 8 | 0 | 0.002 | 0.002 | 0.003 | 0.003 | 0 |
| `transmission_expansion` | 67 | 67 | 0 | 0.439 | 114.6 | 1500.2 | 1500.4 | 5 |
| `uc` | 118 | 118 | 0 | 12.15 | 307.6 | 1500.3 | 1500.8 | 23 |
| `volt_var` | 1 | 1 | 0 | 0.001 | 0.001 | 0.001 | 0.001 | 0 |

## 按 `solve_tier`

| solve_tier | 案例数 | 有 runtime | 缺失 | median (s) | mean (s) | p95 (s) | max (s) | runtime>600s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `full` | 427 | 427 | 0 | 0.007 | 1.741 | 2.370 | 400.0 | 0 |
| `large` | 23 | 23 | 0 | 4.315 | 88.68 | 600.0 | 900.0 | 2 |
| `relaxed` | 182 | 182 | 0 | 0.158 | 12.34 | 46.45 | 638.8 | 1 |
| `skip` | 506 | 498 | 8 | 28.81 | 400.3 | 1500.2 | 1500.8 | 126 |
| `xlarge` | 24 | 24 | 0 | 29.43 | 36.03 | 54.39 | 61.40 | 0 |

## 难求解明细（runtime > 600 s）

共 129 例。

| pack | case | base_problem | tier | status | runtime (s) | source |
|---|---|---|---|---|---:|---|
| `UC/SCUC` | `case48_goc4917_scuc` | `uc` | `skip` | `process_timeout` | 1500.8 | `skip_jsonl` |
| `UC/SCUC` | `case44_goc4601_scuc` | `uc` | `skip` | `process_timeout` | 1500.6 | `skip_jsonl` |
| `UC/SCUC` | `case53_rte6515_scuc` | `uc` | `skip` | `process_timeout` | 1500.5 | `skip_jsonl` |
| `UC/SCUC` | `case51_rte6470_scuc` | `uc` | `skip` | `process_timeout` | 1500.4 | `skip_jsonl` |
| `UC/SCUC` | `case52_rte6495_scuc` | `uc` | `skip` | `process_timeout` | 1500.4 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case214_t1s3_offline_network_13o_3_scenario_1_scacots` | `ots` | `skip` | `process_timeout` | 1500.4 | `skip_jsonl` |
| `PLANNING/TRANSMISSION-EXPANSION` | `case064_goc19402_tep_syn` | `transmission_expansion` | `skip` | `process_timeout` | 1500.4 | `skip_jsonl` |
| `PLANNING/TRANSMISSION-EXPANSION` | `case066_goc24464_tep_syn` | `transmission_expansion` | `skip` | `process_timeout` | 1500.4 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case218_t1s3_offline_network_13o_3_scenario_3_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `UC/SCUC` | `case49_epigrids5658_scuc` | `uc` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case296_t1s3_real_time_network_13r_3_scenario_2_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case058_t1s3_offline_network_13o_3_scenario_2_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `PLANNING/TRANSMISSION-EXPANSION` | `case065_epigrids20758_tep_syn` | `transmission_expansion` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case056_t1s3_offline_network_13o_3_scenario_1_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case294_t1s3_real_time_network_13r_3_scenario_1_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/SC-OTS` | `case49_epigrids5658_scots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/SC-OTS` | `case51_rte6470_scots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `UC/SCUC` | `case66_epigrids78484_scuc` | `uc` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case060_t1s3_offline_network_13o_3_scenario_3_scacots` | `ots` | `skip` | `process_timeout` | 1500.3 | `skip_jsonl` |
| `UC/SCUC` | `case65_goc30000_scuc` | `uc` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `PLANNING/TRANSMISSION-EXPANSION` | `case067_goc30000_tep_syn` | `transmission_expansion` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/SC-OTS` | `case57_goc9591_scots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/SC-OTS` | `case52_rte6495_scots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case298_t1s3_real_time_network_13r_3_scenario_3_scacots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/SC-OTS` | `case50_rte6468_scots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OPF/DC-OPF` | `case089_goc30000_dc_ed` | `opf` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/SC-OTS` | `case53_rte6515_scots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OPF/DC-OPF` | `case083_goc19402_dc_ed` | `opf` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/SC-OTS` | `case58_goc10000_scots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OPF/DC-OPF` | `case085_epigrids20758_dc_ed` | `opf` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/DC-OTS` | `case61_pegase13659_dcots` | `ots` | `skip` | `process_timeout` | 1500.2 | `skip_jsonl` |
| `OTS/LINEARIZED-SC-OTS` | `case216_t1s3_offline_network_13o_3_scenario_2_scacots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case57_goc9591_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case55_pegase8387_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case60_goc10480_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case64_goc24464_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case62_goc19402_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case067_goc24464_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case63_epigrids20758_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case56_pegase9241_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case54_epigrids7336_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OTS/SC-OTS` | `case56_pegase9241_scots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OTS/SC-OTS` | `case66_epigrids78484_scots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OTS/SC-OTS` | `case61_pegase13659_scots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `MONITORING/PMU-PLACEMENT` | `case066_case78484_epigrids_pmu` | `pmu_placement` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case066_epigrids20758_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case50_rte6468_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `PLANNING/TRANSMISSION-EXPANSION` | `case068_epigrids78484_tep_syn` | `transmission_expansion` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case068_goc30000_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case065_goc19402_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case069_epigrids78484_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case58_goc10000_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OPF/DC-OPF` | `case091_epigrids78484_dc_ed` | `opf` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OTS/SC-OTS` | `case60_goc10480_scots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OPF/DC-OPF` | `case087_goc24464_dc_ed` | `opf` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case59_epigrids10192_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `OTS/DC-OTS` | `case66_epigrids78484_dcots` | `ots` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `UC/SCUC` | `case61_pegase13659_scuc` | `uc` | `skip` | `process_timeout` | 1500.1 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case060_goc9591_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case65_goc30000_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case54_epigrids7336_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case62_goc19402_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case063_goc10480_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case050_goc4837_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case63_epigrids20758_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case048_goc4619_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/DC-OTS` | `case65_goc30000_dcots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case55_pegase8387_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case059_pegase9241_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/SC-OTS` | `case64_goc24464_scots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case064_pegase13659_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case061_goc10000_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/DC-OTS` | `case63_epigrids20758_dcots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/DC-OTS` | `case62_goc19402_dcots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `OTS/DC-OTS` | `case64_goc24464_dcots` | `ots` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case046_goc4020_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case029_goc2000_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case038_sdet2853_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case054_rte6470_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case047_goc4601_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case035_2746wopk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case062_epigrids10192_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case055_rte6495_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case043_3120spk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case024_goc793_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case044_3375wpk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case032_2736spk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case034_goc2742_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case049_sdet4661_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case041_3012wpk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case039_rte2868_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case051_goc4917_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case028_rte1951_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case027_rte1888_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case052_epigrids5658_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case057_epigrids7336_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case025_pegase1354_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case045_goc3970_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case033_2737sopk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case036_2746wpk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case056_rte6515_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case037_rte2848_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case031_2383wpk_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case042_goc3022_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case040_pegase2869_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case053_rte6468_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case030_goc2312_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case022_goc500_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case023_sdet588_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `RESILIENCE/NETWORK-INTERDICTION` | `case026_snem1803_nk_int` | `network_interdiction` | `skip` | `process_timeout` | 1500.0 | `skip_jsonl` |
| `UC/SCUC` | `case26_goc2000_scuc` | `uc` | `skip` | `TIME_LIMIT` | 1003.4 | `skip_jsonl` |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | `case24_s46c_scen16_ht` | `hydrothermal_scheduling` | `skip` | `OPTIMAL` | 1001.6 | `skip_jsonl` |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | `case16_s46a_scen16_ht` | `hydrothermal_scheduling` | `skip` | `TIME_LIMIT` | 1001.4 | `skip_jsonl` |
| `UC/SCUC` | `case42_goc3970_scuc` | `uc` | `skip` | `TIME_LIMIT` | 1001.0 | `skip_jsonl` |
| `UC/SCUC` | `case39_goc3022_scuc` | `uc` | `skip` | `TIME_LIMIT` | 1000.9 | `skip_jsonl` |
| `MONITORING/PMU-PLACEMENT` | `case064_case24464_goc_pmu` | `pmu_placement` | `skip` | `TIME_LIMIT` | 1000.8 | `skip_jsonl` |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | `case32_s46e_scen16_ht` | `hydrothermal_scheduling` | `skip` | `TIME_LIMIT` | 1000.7 | `skip_jsonl` |
| `MONITORING/PMU-PLACEMENT` | `case062_case19402_goc_pmu` | `pmu_placement` | `skip` | `TIME_LIMIT` | 1000.4 | `skip_jsonl` |
| `RESILIENCE/CONTROLLED-ISLANDING` | `case002_GBnetwork_island` | `controlled_islanding` | `skip` | `TIME_LIMIT` | 1000.4 | `skip_jsonl` |
| `MONITORING/PMU-PLACEMENT` | `case060_case10480_goc_pmu` | `pmu_placement` | `skip` | `TIME_LIMIT` | 1000.4 | `skip_jsonl` |
| `MONITORING/PMU-PLACEMENT` | `case042_case3970_goc_pmu` | `pmu_placement` | `skip` | `TIME_LIMIT` | 1000.3 | `skip_jsonl` |
| `RESILIENCE/POWER-RESTORATION` | `case013_activsg200_scenario8_restore` | `power_restoration` | `skip` | `TIME_LIMIT` | 1000.3 | `skip_jsonl` |
| `RESILIENCE/POWER-RESTORATION` | `case009_activsg200_scenario4_restore` | `power_restoration` | `skip` | `TIME_LIMIT` | 1000.3 | `skip_jsonl` |
| `RESILIENCE/CONTROLLED-ISLANDING` | `case073_npcc_island` | `controlled_islanding` | `skip` | `TIME_LIMIT` | 1000.3 | `skip_jsonl` |
| `RESILIENCE/CONTROLLED-ISLANDING` | `case003_EI_33_island` | `controlled_islanding` | `skip` | `TIME_LIMIT` | 1000.2 | `skip_jsonl` |
| `OPF/AC-OPF` | `case004_ieee30_acopf` | `opf` | `large` | `TIME_LIMIT` | 900.0 | `python_result` |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | `case15_s46a_scen9_ht` | `hydrothermal_scheduling` | `relaxed` | `INTERRUPTED` | 638.8 | `python_result` |
| `OTS/LINEARIZED-SC-OTS` | `case292_t1s3_real_time_network_12r_3_scenario_3_scacots` | `ots` | `skip` | `OPTIMAL` | 612.4 | `skip_jsonl` |
| `OPF/SC-AC-OPF` | `case002_pjm5_scacopf` | `opf` | `large` | `TIME_LIMIT` | 600.0 | `python_result` |

## 无 runtime 记录

下列案例 skip 批次 `process_error` 且没有可用的 `python_result` runtime：

- `OTS/LINEARIZED-SC-OTS/case136_t1s3_real_time_network_13r_3_scenario_1_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case138_t1s3_real_time_network_13r_3_scenario_2_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case140_t1s3_real_time_network_13r_3_scenario_3_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case202_t1s3_offline_network_09o_3_scenario_1_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case204_t1s3_offline_network_09o_3_scenario_2_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case206_t1s3_offline_network_09o_3_scenario_3_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case208_t1s3_offline_network_12o_3_scenario_1_scacots` status=`None`
- `OTS/LINEARIZED-SC-OTS/case210_t1s3_offline_network_12o_3_scenario_2_scacots` status=`None`

## 已删除（不在本表）

无入口 2 例 + 主问题 INFEASIBLE 35 例，共 37 例，见仓库 `DELETE_LIST.json`。
