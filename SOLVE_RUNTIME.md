# 求解时间

共 1162 例。小于 600s 写实测时间，超过 600s 记为**难求解**。

| 分类 | 案例数 | < 600s | 难求解 |
|---|---:|---:|---:|
| `DATACENTER/FLEXIBLE-DC-LOAD` | 6 | 6 | 0 |
| `DATACENTER/GEOGRAPHIC-LOAD-BALANCING` | 6 | 6 | 0 |
| `DATACENTER/GREEN-LLM` | 6 | 6 | 0 |
| `DISPATCH/DEMAND-RESPONSE` | 3 | 3 | 0 |
| `DISPATCH/ECONOMIC-DISPATCH` | 3 | 3 | 0 |
| `DISTRIBUTION/DER-HOSTING` | 1 | 1 | 0 |
| `DISTRIBUTION/DISTRIBUTION-OPF` | 2 | 2 | 0 |
| `DISTRIBUTION/DNR` | 5 | 5 | 0 |
| `DISTRIBUTION/MICROGRID` | 3 | 3 | 0 |
| `DISTRIBUTION/UNBALANCED-DOPF` | 2 | 2 | 0 |
| `DISTRIBUTION/VOLT-VAR` | 1 | 1 | 0 |
| `MARKET/MARKET-CLEARING` | 56 | 56 | 0 |
| `MARKET/STRATEGIC-BIDDING` | 8 | 8 | 0 |
| `MONITORING/PMU-PLACEMENT` | 66 | 61 | 5 |
| `MONITORING/STATE-ESTIMATION` | 12 | 12 | 0 |
| `MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS` | 14 | 14 | 0 |
| `OPF/AC-OPF` | 4 | 3 | 1 |
| `OPF/DC-OPF` | 71 | 66 | 5 |
| `OPF/LINEARIZED-SC-OPF` | 158 | 158 | 0 |
| `OPF/SC-AC-OPF` | 2 | 1 | 1 |
| `OTS/DC-OTS` | 65 | 59 | 6 |
| `OTS/LINEARIZED-SC-OTS` | 158 | 148 | 10 |
| `OTS/SC-OTS` | 51 | 34 | 17 |
| `PLANNING/DISTRIBUTION-EXPANSION` | 2 | 2 | 0 |
| `PLANNING/GCEP-DC` | 3 | 3 | 0 |
| `PLANNING/RESOURCE-CAPACITY-EXPANSION` | 10 | 10 | 0 |
| `PLANNING/TRANSMISSION-EXPANSION` | 67 | 62 | 5 |
| `RESILIENCE/CONTROLLED-ISLANDING` | 82 | 79 | 3 |
| `RESILIENCE/DISTRIBUTION-RESTORATION` | 3 | 3 | 0 |
| `RESILIENCE/MAXIMUM-LOAD-DELIVERY` | 18 | 18 | 0 |
| `RESILIENCE/NETWORK-INTERDICTION` | 68 | 21 | 47 |
| `RESILIENCE/OPTIMAL-POWER-SHUTOFF` | 35 | 35 | 0 |
| `RESILIENCE/POWER-RESTORATION` | 13 | 11 | 2 |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | 32 | 28 | 4 |
| `SCHEDULING/MAINTENANCE-SCHEDULING` | 5 | 5 | 0 |
| `SCHEDULING/STORAGE-SCHEDULING` | 3 | 3 | 0 |
| `UC/RTS-SCUC` | 12 | 12 | 0 |
| `UC/SCUC` | 50 | 27 | 23 |
| `UC/SYSTEM-UC` | 56 | 56 | 0 |
| **合计** | **1162** | **1033** | **129** |

## DATACENTER/FLEXIBLE-DC-LOAD

| 案例 | 时间 (s) |
|---|---:|
| `case001_ieee14_opf_inflexible` | 0.001 |
| `case002_ieee14_opf_temporal` | 0.002 |
| `case003_ieee14_opf_spatial` | 0.001 |
| `case004_ieee24_scuc_temporal` | 1.854 |
| `case005_ieee24_scuc_spatial_temporal` | 8.746 |
| `case006_ieee24_scuc_interruptible` | 1.587 |

## DATACENTER/GEOGRAPHIC-LOAD-BALANCING

| 案例 | 时间 (s) |
|---|---:|
| `case001_eeai10_24h_equity_full` | 0.007 |
| `case002_eeai10_24h_cost_full` | 0.002 |
| `case003_eeai10_457h_equity_full` | 0.079 |
| `case004_eeai10_457h_equity_partial` | 0.388 |
| `case005_eeai10_457h_cost_full` | 0.044 |
| `case006_eeai10_457h_local` | 0.003 |

## DATACENTER/GREEN-LLM

| 案例 | 时间 (s) |
|---|---:|
| `case001_9dc_24h_weighted` | 0.022 |
| `case002_9dc_24h_energy` | 0.025 |
| `case003_9dc_24h_carbon` | 0.025 |
| `case004_9dc_24h_lex_cde` | 0.091 |
| `case005_9dc_24h_place_milp` | 0.649 |
| `case006_4dc_6h_smoke` | 0.001 |

## DISPATCH/DEMAND-RESPONSE

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_dr` | 0.003 |
| `case002_pjm5_dr` | 0.001 |
| `case003_ieee14_dr` | 0.000 |

## DISPATCH/ECONOMIC-DISPATCH

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_copperplate_ed` | 0.003 |
| `case002_pjm5_copperplate_ed` | 0.001 |
| `case003_ieee14_copperplate_ed` | 0.000 |

## DISTRIBUTION/DER-HOSTING

| 案例 | 时间 (s) |
|---|---:|
| `case03_gso_rural_hosting` | 0.001 |

## DISTRIBUTION/DISTRIBUTION-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case02_mv_rural_dopf` | 0.028 |
| `case05_lv_rural2_dopf` | 0.014 |

## DISTRIBUTION/DNR

| 案例 | 时间 (s) |
|---|---:|
| `case01_gso_rural_dnr` | 0.001 |
| `case01_mv_rural_dnr` | 0.005 |
| `case03_mv_rural_dnr_ess` | 0.019 |
| `case04_lv_rural2_dnr` | 0.004 |
| `case06_lv_rural2_dnr_ess` | 0.013 |

## DISTRIBUTION/MICROGRID

| 案例 | 时间 (s) |
|---|---:|
| `case001_pjm5_microgrid_grid` | 0.000 |
| `case002_pjm5_microgrid_island` | 0.000 |
| `case003_pjm5_vpp` | 0.000 |

## DISTRIBUTION/UNBALANCED-DOPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_ieee4_unbalanced` | 0.000 |
| `case002_smartds_6bus_unbalanced` | 0.000 |

## DISTRIBUTION/VOLT-VAR

| 案例 | 时间 (s) |
|---|---:|
| `case02_gso_rural_voltvar` | 0.001 |

## MARKET/MARKET-CLEARING

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_2020_01_27_market` | 0.014 |
| `case02_rts_gmlc_2020_02_09_market` | 0.015 |
| `case03_rts_gmlc_2020_03_05_market` | 0.015 |
| `case04_rts_gmlc_2020_04_03_market` | 0.015 |
| `case05_rts_gmlc_2020_05_05_market` | 0.015 |
| `case06_rts_gmlc_2020_06_09_market` | 0.017 |
| `case07_rts_gmlc_2020_07_06_market` | 0.017 |
| `case08_rts_gmlc_2020_08_12_market` | 0.019 |
| `case09_rts_gmlc_2020_09_20_market` | 0.016 |
| `case10_rts_gmlc_2020_10_27_market` | 0.017 |
| `case11_rts_gmlc_2020_11_25_market` | 0.015 |
| `case12_rts_gmlc_2020_12_23_market` | 0.015 |
| `case13_ca_2014_09_01_reserves_0_market` | 0.153 |
| `case14_ca_2014_09_01_reserves_1_market` | 0.155 |
| `case15_ca_2014_09_01_reserves_3_market` | 0.153 |
| `case16_ca_2014_09_01_reserves_5_market` | 0.157 |
| `case17_ca_2014_12_01_reserves_0_market` | 0.103 |
| `case18_ca_2014_12_01_reserves_1_market` | 0.107 |
| `case19_ca_2014_12_01_reserves_3_market` | 0.104 |
| `case20_ca_2014_12_01_reserves_5_market` | 0.106 |
| `case21_ca_2015_03_01_reserves_0_market` | 0.087 |
| `case22_ca_2015_03_01_reserves_1_market` | 0.090 |
| `case23_ca_2015_03_01_reserves_3_market` | 0.088 |
| `case24_ca_2015_03_01_reserves_5_market` | 0.092 |
| `case25_ca_2015_06_01_reserves_0_market` | 0.106 |
| `case26_ca_2015_06_01_reserves_1_market` | 0.108 |
| `case27_ca_2015_06_01_reserves_3_market` | 0.107 |
| `case28_ca_2015_06_01_reserves_5_market` | 0.107 |
| `case29_ca_scenario400_reserves_0_market` | 0.130 |
| `case30_ca_scenario400_reserves_1_market` | 0.134 |
| `case31_ca_scenario400_reserves_3_market` | 0.130 |
| `case32_ca_scenario400_reserves_5_market` | 0.131 |
| `case33_ferc_2015_01_01_hw_market` | 0.299 |
| `case34_ferc_2015_01_01_lw_market` | 0.288 |
| `case35_ferc_2015_02_01_hw_market` | 0.291 |
| `case36_ferc_2015_02_01_lw_market` | 0.293 |
| `case37_ferc_2015_03_01_hw_market` | 0.263 |
| `case38_ferc_2015_03_01_lw_market` | 0.314 |
| `case39_ferc_2015_04_01_hw_market` | 0.251 |
| `case40_ferc_2015_04_01_lw_market` | 0.176 |
| `case41_ferc_2015_05_01_hw_market` | 0.194 |
| `case42_ferc_2015_05_01_lw_market` | 0.185 |
| `case43_ferc_2015_06_01_hw_market` | 0.184 |
| `case44_ferc_2015_06_01_lw_market` | 0.182 |
| `case45_ferc_2015_07_01_hw_market` | 0.221 |
| `case46_ferc_2015_07_01_lw_market` | 0.233 |
| `case47_ferc_2015_08_01_hw_market` | 0.219 |
| `case48_ferc_2015_08_01_lw_market` | 0.224 |
| `case49_ferc_2015_09_01_hw_market` | 0.264 |
| `case50_ferc_2015_09_01_lw_market` | 0.290 |
| `case51_ferc_2015_10_01_hw_market` | 0.523 |
| `case52_ferc_2015_10_01_lw_market` | 0.244 |
| `case53_ferc_2015_11_02_hw_market` | 0.335 |
| `case54_ferc_2015_11_02_lw_market` | 0.239 |
| `case55_ferc_2015_12_01_hw_market` | 0.338 |
| `case56_ferc_2015_12_01_lw_market` | 0.351 |

## MARKET/STRATEGIC-BIDDING

| 案例 | 时间 (s) |
|---|---:|
| `case01_toy3_copperplate_price` | 0.003 |
| `case02_toy3_dc_price` | 0.002 |
| `case03_pjm5_dc_price` | 0.003 |
| `case04_pjm5_dc_withhold` | 0.001 |
| `case05_ieee14_dc_price` | 0.003 |
| `case06_rts_uc_t1_copperplate_price` | 0.001 |
| `case07_ferc_uc_t1_copperplate_price` | 0.001 |
| `case08_pjm5_binary_ladder` | 0.001 |

## MONITORING/PMU-PLACEMENT

| 案例 | 时间 (s) |
|---|---:|
| `case001_case3_lmbd_pmu` | 0.002 |
| `case002_case5_pjm_pmu` | 0.000 |
| `case003_case14_ieee_pmu` | 0.002 |
| `case004_case24_ieee_rts_pmu` | 0.001 |
| `case005_case30_as_pmu` | 0.000 |
| `case006_case30_ieee_pmu` | 0.000 |
| `case007_case39_epri_pmu` | 0.000 |
| `case008_case57_ieee_pmu` | 0.001 |
| `case009_case60_c_pmu` | 0.000 |
| `case010_case73_ieee_rts_pmu` | 0.001 |
| `case011_case89_pegase_pmu` | 0.000 |
| `case012_case118_ieee_pmu` | 0.002 |
| `case013_case162_ieee_dtc_pmu` | 0.002 |
| `case014_case179_goc_pmu` | 0.002 |
| `case015_case197_snem_pmu` | 0.001 |
| `case016_case200_activ_pmu` | 0.001 |
| `case017_case240_pserc_pmu` | 0.001 |
| `case018_case300_ieee_pmu` | 0.001 |
| `case019_case500_goc_pmu` | 0.007 |
| `case020_case588_sdet_pmu` | 0.002 |
| `case021_case793_goc_pmu` | 0.001 |
| `case022_case1354_pegase_pmu` | 0.002 |
| `case023_case1803_snem_pmu` | 0.008 |
| `case024_case1888_rte_pmu` | 0.003 |
| `case025_case1951_rte_pmu` | 0.003 |
| `case026_case2000_goc_pmu` | 0.005 |
| `case027_case2312_goc_pmu` | 0.005 |
| `case028_case2383wp_k_pmu` | 0.006 |
| `case029_case2736sp_k_pmu` | 0.006 |
| `case030_case2737sop_k_pmu` | 0.006 |
| `case031_case2742_goc_pmu` | 4.052 |
| `case032_case2746wop_k_pmu` | 0.007 |
| `case033_case2746wp_k_pmu` | 0.007 |
| `case034_case2848_rte_pmu` | 0.004 |
| `case035_case2853_sdet_pmu` | 0.006 |
| `case036_case2868_rte_pmu` | 0.005 |
| `case037_case2869_pegase_pmu` | 0.016 |
| `case038_case3012wp_k_pmu` | 0.025 |
| `case039_case3022_goc_pmu` | 0.167 |
| `case040_case3120sp_k_pmu` | 0.083 |
| `case041_case3375wp_k_pmu` | 0.078 |
| `case042_case3970_goc_pmu` | 难求解 |
| `case043_case4020_goc_pmu` | 221.5 |
| `case044_case4601_goc_pmu` | 2.523 |
| `case045_case4619_goc_pmu` | 213.9 |
| `case046_case4661_sdet_pmu` | 0.193 |
| `case047_case4837_goc_pmu` | 4.045 |
| `case048_case4917_goc_pmu` | 0.255 |
| `case049_case5658_epigrids_pmu` | 3.683 |
| `case050_case6468_rte_pmu` | 0.193 |
| `case051_case6470_rte_pmu` | 0.103 |
| `case052_case6495_rte_pmu` | 0.108 |
| `case053_case6515_rte_pmu` | 0.105 |
| `case054_case7336_epigrids_pmu` | 10.42 |
| `case055_case8387_pegase_pmu` | 0.879 |
| `case056_case9241_pegase_pmu` | 1.123 |
| `case057_case9591_goc_pmu` | 308.3 |
| `case058_case10000_goc_pmu` | 0.121 |
| `case059_case10192_epigrids_pmu` | 111.7 |
| `case060_case10480_goc_pmu` | 难求解 |
| `case061_case13659_pegase_pmu` | 0.648 |
| `case062_case19402_goc_pmu` | 难求解 |
| `case063_case20758_epigrids_pmu` | 18.07 |
| `case064_case24464_goc_pmu` | 难求解 |
| `case065_case30000_goc_pmu` | 0.396 |
| `case066_case78484_epigrids_pmu` | 难求解 |

## MONITORING/STATE-ESTIMATION

| 案例 | 时间 (s) |
|---|---:|
| `case001_case5_pjm_wls_se` | 0.000 |
| `case002_case5_pjm_l1_se` | 0.000 |
| `case003_case14_ieee_wls_se` | 0.000 |
| `case004_case14_ieee_l1_se` | 0.001 |
| `case005_case30_ieee_wls_se` | 0.000 |
| `case006_case30_ieee_l1_se` | 0.001 |
| `case007_case57_ieee_wls_se` | 0.001 |
| `case008_case57_ieee_l1_se` | 0.002 |
| `case009_case118_ieee_wls_se` | 0.001 |
| `case010_case118_ieee_l1_se` | 0.005 |
| `case011_case300_ieee_wls_se` | 0.003 |
| `case012_case300_ieee_l1_se` | 0.015 |

## MULTI-ENERGY/INTEGRATED-ELECTRIC-GAS

| 案例 | 时间 (s) |
|---|---:|
| `case01_travis150_ieg` | 0.052 |
| `case02_gaslib11_14_ieee_ieg` | 0.002 |
| `case03_gaslib24_24_ieee_rts_ieg` | 0.014 |
| `case04_gaslib39_scen01_39_epri_ieg` | 0.007 |
| `case05_gaslib39_scen02_39_epri_ieg` | 0.008 |
| `case06_gaslib39_scen03_39_epri_ieg` | 0.002 |
| `case07_gaslib39_scen04_39_epri_ieg` | 0.005 |
| `case08_gaslib39_scen05_39_epri_ieg` | 0.013 |
| `case09_gaslib39_scen06_39_epri_ieg` | 0.013 |
| `case10_gaslib39_scen07_39_epri_ieg` | 0.004 |
| `case11_gaslib39_scen08_39_epri_ieg` | 0.015 |
| `case12_gaslib39_scen09_39_epri_ieg` | 0.005 |
| `case13_gaslib39_scen10_39_epri_ieg` | 0.005 |
| `case14_gaslib40_57_ieee_ieg` | 0.002 |

## OPF/AC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_acopf` | 0.110 |
| `case002_pjm5_acopf` | 99.91 |
| `case003_ieee14_acopf` | 57.39 |
| `case004_ieee30_acopf` | 难求解 |

## OPF/DC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_dc_ed` | 0.000 |
| `case002_lmbd3_lp_ed` | 0.001 |
| `case003_pjm5_dc_ed` | 0.000 |
| `case004_ieee14_dc_ed` | 0.000 |
| `case005_ieee24_dc_ed` | 0.001 |
| `case006_ieee24_lp_ed` | 0.000 |
| `case007_as30_dc_ed` | 0.000 |
| `case008_as30_lp_ed` | 0.000 |
| `case009_ieee30_dc_ed` | 0.000 |
| `case010_epri39_dc_ed` | 0.000 |
| `case011_ieee57_dc_ed` | 0.000 |
| `case012_c60_dc_ed` | 0.000 |
| `case013_ieee73_dc_ed` | 0.001 |
| `case014_ieee73_lp_ed` | 0.001 |
| `case015_pegase89_dc_ed` | 0.002 |
| `case016_ieee118_dc_ed` | 0.001 |
| `case017_ieeedtc162_dc_ed` | 0.003 |
| `case018_goc179_dc_ed` | 0.001 |
| `case019_snem197_dc_ed` | 0.001 |
| `case020_activ200_dc_ed` | 0.001 |
| `case021_activ200_lp_ed` | 0.001 |
| `case022_pserc240_dc_ed` | 0.004 |
| `case023_ieee300_dc_ed` | 0.003 |
| `case024_goc500_dc_ed` | 0.004 |
| `case026_sdet588_dc_ed` | 0.004 |
| `case027_goc793_dc_ed` | 0.003 |
| `case029_pegase1354_dc_ed` | 0.018 |
| `case030_snem1803_dc_ed` | 0.024 |
| `case031_rte1888_dc_ed` | 0.021 |
| `case032_rte1951_dc_ed` | 0.020 |
| `case033_goc2000_dc_ed` | 0.029 |
| `case035_goc2312_dc_ed` | 0.018 |
| `case037_2383wpk_dc_ed` | 0.042 |
| `case038_2736spk_dc_ed` | 0.047 |
| `case039_2737sopk_dc_ed` | 0.042 |
| `case040_goc2742_dc_ed` | 0.053 |
| `case042_2746wopk_dc_ed` | 0.042 |
| `case043_2746wpk_dc_ed` | 0.045 |
| `case044_rte2848_dc_ed` | 0.033 |
| `case045_sdet2853_dc_ed` | 0.058 |
| `case046_rte2868_dc_ed` | 0.035 |
| `case047_pegase2869_dc_ed` | 0.084 |
| `case048_3012wpk_dc_ed` | 0.165 |
| `case049_goc3022_dc_ed` | 0.113 |
| `case051_3120spk_dc_ed` | 0.206 |
| `case052_3375wpk_dc_ed` | 0.281 |
| `case053_goc3970_dc_ed` | 0.366 |
| `case055_goc4020_dc_ed` | 0.526 |
| `case057_goc4601_dc_ed` | 0.221 |
| `case059_goc4619_dc_ed` | 0.460 |
| `case061_sdet4661_dc_ed` | 1.086 |
| `case062_goc4837_dc_ed` | 0.372 |
| `case064_goc4917_dc_ed` | 0.274 |
| `case066_epigrids5658_dc_ed` | 2.443 |
| `case067_rte6468_dc_ed` | 0.607 |
| `case068_rte6470_dc_ed` | 0.866 |
| `case069_rte6495_dc_ed` | 1.100 |
| `case070_rte6515_dc_ed` | 0.694 |
| `case071_epigrids7336_dc_ed` | 3.479 |
| `case072_pegase8387_dc_ed` | 5.817 |
| `case073_pegase9241_dc_ed` | 12.86 |
| `case074_goc9591_dc_ed` | 1.352 |
| `case076_goc10000_dc_ed` | 0.723 |
| `case078_epigrids10192_dc_ed` | 3.425 |
| `case080_goc10480_dc_ed` | 1.249 |
| `case082_pegase13659_dc_ed` | 6.403 |
| `case083_goc19402_dc_ed` | 难求解 |
| `case085_epigrids20758_dc_ed` | 难求解 |
| `case087_goc24464_dc_ed` | 难求解 |
| `case089_goc30000_dc_ed` | 难求解 |
| `case091_epigrids78484_dc_ed` | 难求解 |

## OPF/LINEARIZED-SC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_t1s3_offline_network_01o_3_scenario_1_scacopf` | 0.074 |
| `case003_t1s3_offline_network_01o_3_scenario_2_scacopf` | 0.072 |
| `case005_t1s3_offline_network_01o_3_scenario_3_scacopf` | 0.071 |
| `case007_t1s3_offline_network_02o_3_scenario_1_scacopf` | 0.099 |
| `case009_t1s3_offline_network_02o_3_scenario_2_scacopf` | 0.099 |
| `case011_t1s3_offline_network_02o_3_scenario_3_scacopf` | 0.103 |
| `case013_t1s3_offline_network_03o_3_scenario_1_scacopf` | 0.121 |
| `case015_t1s3_offline_network_03o_3_scenario_2_scacopf` | 0.115 |
| `case017_t1s3_offline_network_03o_3_scenario_3_scacopf` | 0.113 |
| `case019_t1s3_offline_network_05o_3_scenario_1_scacopf` | 11.62 |
| `case021_t1s3_offline_network_05o_3_scenario_2_scacopf` | 8.896 |
| `case023_t1s3_offline_network_05o_3_scenario_3_scacopf` | 7.830 |
| `case025_t1s3_offline_network_06o_3_scenario_1_scacopf` | 6.212 |
| `case027_t1s3_offline_network_06o_3_scenario_2_scacopf` | 5.321 |
| `case029_t1s3_offline_network_06o_3_scenario_3_scacopf` | 5.636 |
| `case031_t1s3_offline_network_07o_3_scenario_1_scacopf` | 4.600 |
| `case033_t1s3_offline_network_07o_3_scenario_2_scacopf` | 6.770 |
| `case035_t1s3_offline_network_07o_3_scenario_3_scacopf` | 9.419 |
| `case037_t1s3_offline_network_08o_3_scenario_1_scacopf` | 15.04 |
| `case039_t1s3_offline_network_08o_3_scenario_2_scacopf` | 14.69 |
| `case041_t1s3_offline_network_08o_3_scenario_3_scacopf` | 14.66 |
| `case043_t1s3_offline_network_09o_3_scenario_1_scacopf` | 31.96 |
| `case045_t1s3_offline_network_09o_3_scenario_2_scacopf` | 38.68 |
| `case047_t1s3_offline_network_09o_3_scenario_3_scacopf` | 31.64 |
| `case049_t1s3_offline_network_12o_3_scenario_1_scacopf` | 427.4 |
| `case051_t1s3_offline_network_12o_3_scenario_2_scacopf` | 373.5 |
| `case053_t1s3_offline_network_12o_3_scenario_3_scacopf` | 402.4 |
| `case055_t1s3_offline_network_13o_3_scenario_1_scacopf` | 98.11 |
| `case057_t1s3_offline_network_13o_3_scenario_2_scacopf` | 150.3 |
| `case059_t1s3_offline_network_13o_3_scenario_3_scacopf` | 150.2 |
| `case061_t1s3_offline_network_70o_3_scenario_1_scacopf` | 6.127 |
| `case063_t1s3_offline_network_70o_3_scenario_2_scacopf` | 5.852 |
| `case065_t1s3_offline_network_70o_3_scenario_3_scacopf` | 7.345 |
| `case067_t1s3_offline_network_81o_3_scenario_1_scacopf` | 21.51 |
| `case069_t1s3_offline_network_81o_3_scenario_2_scacopf` | 28.63 |
| `case071_t1s3_offline_network_81o_3_scenario_3_scacopf` | 24.87 |
| `case073_t1s3_offline_network_84o_3_scenario_1_scacopf` | 62.77 |
| `case075_t1s3_offline_network_84o_3_scenario_2_scacopf` | 62.92 |
| `case077_t1s3_offline_network_84o_3_scenario_3_scacopf` | 67.88 |
| `case079_t1s3_real_time_network_01r_3_scenario_1_scacopf` | 0.064 |
| `case081_t1s3_real_time_network_01r_3_scenario_2_scacopf` | 0.075 |
| `case083_t1s3_real_time_network_01r_3_scenario_3_scacopf` | 0.072 |
| `case085_t1s3_real_time_network_02r_3_scenario_1_scacopf` | 0.109 |
| `case087_t1s3_real_time_network_02r_3_scenario_2_scacopf` | 0.105 |
| `case089_network_02r_3_scenario_2_scenario_30_scacopf` | 0.110 |
| `case091_t1s3_real_time_network_02r_3_scenario_3_scacopf` | 0.103 |
| `case093_t1s3_real_time_network_03r_3_scenario_1_scacopf` | 0.115 |
| `case095_t1s3_real_time_network_03r_3_scenario_2_scacopf` | 0.114 |
| `case097_t1s3_real_time_network_03r_3_scenario_3_scacopf` | 0.116 |
| `case099_t1s3_real_time_network_05r_3_scenario_1_scacopf` | 10.70 |
| `case101_t1s3_real_time_network_05r_3_scenario_2_scacopf` | 7.605 |
| `case103_t1s3_real_time_network_05r_3_scenario_3_scacopf` | 11.00 |
| `case105_t1s3_real_time_network_06r_3_scenario_1_scacopf` | 5.246 |
| `case107_t1s3_real_time_network_06r_3_scenario_2_scacopf` | 6.943 |
| `case109_t1s3_real_time_network_06r_3_scenario_3_scacopf` | 5.964 |
| `case111_t1s3_real_time_network_07r_3_scenario_1_scacopf` | 4.547 |
| `case113_t1s3_real_time_network_07r_3_scenario_2_scacopf` | 6.086 |
| `case115_t1s3_real_time_network_07r_3_scenario_3_scacopf` | 8.999 |
| `case117_t1s3_real_time_network_08r_3_scenario_1_scacopf` | 16.72 |
| `case119_t1s3_real_time_network_08r_3_scenario_2_scacopf` | 17.16 |
| `case121_t1s3_real_time_network_08r_3_scenario_3_scacopf` | 12.04 |
| `case123_t1s3_real_time_network_09r_3_scenario_1_scacopf` | 38.26 |
| `case125_t1s3_real_time_network_09r_3_scenario_2_scacopf` | 39.60 |
| `case127_t1s3_real_time_network_09r_3_scenario_3_scacopf` | 46.95 |
| `case129_t1s3_real_time_network_12r_3_scenario_1_scacopf` | 421.4 |
| `case131_t1s3_real_time_network_12r_3_scenario_2_scacopf` | 395.8 |
| `case133_t1s3_real_time_network_12r_3_scenario_3_scacopf` | 418.3 |
| `case135_t1s3_real_time_network_13r_3_scenario_1_scacopf` | 109.6 |
| `case137_t1s3_real_time_network_13r_3_scenario_2_scacopf` | 172.5 |
| `case139_t1s3_real_time_network_13r_3_scenario_3_scacopf` | 154.3 |
| `case141_t1s3_real_time_network_70r_3_scenario_1_scacopf` | 7.542 |
| `case143_t1s3_real_time_network_70r_3_scenario_2_scacopf` | 7.545 |
| `case145_t1s3_real_time_network_70r_3_scenario_3_scacopf` | 6.181 |
| `case147_t1s3_real_time_network_81r_3_scenario_1_scacopf` | 23.88 |
| `case149_t1s3_real_time_network_81r_3_scenario_2_scacopf` | 21.80 |
| `case151_t1s3_real_time_network_81r_3_scenario_3_scacopf` | 24.22 |
| `case153_t1s3_real_time_network_84r_3_scenario_1_scacopf` | 63.31 |
| `case155_t1s3_real_time_network_84r_3_scenario_2_scacopf` | 59.94 |
| `case157_t1s3_real_time_network_84r_3_scenario_3_scacopf` | 66.64 |
| `case159_t1s3_offline_network_01o_3_scenario_1_scacopf` | 0.071 |
| `case161_t1s3_offline_network_01o_3_scenario_2_scacopf` | 0.085 |
| `case163_t1s3_offline_network_01o_3_scenario_3_scacopf` | 0.073 |
| `case165_t1s3_offline_network_02o_3_scenario_1_scacopf` | 0.101 |
| `case167_t1s3_offline_network_02o_3_scenario_2_scacopf` | 0.102 |
| `case169_t1s3_offline_network_02o_3_scenario_3_scacopf` | 0.101 |
| `case171_t1s3_offline_network_03o_3_scenario_1_scacopf` | 0.112 |
| `case173_t1s3_offline_network_03o_3_scenario_2_scacopf` | 0.114 |
| `case175_t1s3_offline_network_03o_3_scenario_3_scacopf` | 0.115 |
| `case177_t1s3_offline_network_05o_3_scenario_1_scacopf` | 10.24 |
| `case179_t1s3_offline_network_05o_3_scenario_2_scacopf` | 8.004 |
| `case181_t1s3_offline_network_05o_3_scenario_3_scacopf` | 11.74 |
| `case183_t1s3_offline_network_06o_3_scenario_1_scacopf` | 7.937 |
| `case185_t1s3_offline_network_06o_3_scenario_2_scacopf` | 7.933 |
| `case187_t1s3_offline_network_06o_3_scenario_3_scacopf` | 7.448 |
| `case189_t1s3_offline_network_07o_3_scenario_1_scacopf` | 5.434 |
| `case191_t1s3_offline_network_07o_3_scenario_2_scacopf` | 8.373 |
| `case193_t1s3_offline_network_07o_3_scenario_3_scacopf` | 9.205 |
| `case195_t1s3_offline_network_08o_3_scenario_1_scacopf` | 15.85 |
| `case197_t1s3_offline_network_08o_3_scenario_2_scacopf` | 15.24 |
| `case199_t1s3_offline_network_08o_3_scenario_3_scacopf` | 18.59 |
| `case201_t1s3_offline_network_09o_3_scenario_1_scacopf` | 38.73 |
| `case203_t1s3_offline_network_09o_3_scenario_2_scacopf` | 41.47 |
| `case205_t1s3_offline_network_09o_3_scenario_3_scacopf` | 47.05 |
| `case207_t1s3_offline_network_12o_3_scenario_1_scacopf` | 440.8 |
| `case209_t1s3_offline_network_12o_3_scenario_2_scacopf` | 423.3 |
| `case211_t1s3_offline_network_12o_3_scenario_3_scacopf` | 386.4 |
| `case213_t1s3_offline_network_13o_3_scenario_1_scacopf` | 95.72 |
| `case215_t1s3_offline_network_13o_3_scenario_2_scacopf` | 168.7 |
| `case217_t1s3_offline_network_13o_3_scenario_3_scacopf` | 151.6 |
| `case219_t1s3_offline_network_70o_3_scenario_1_scacopf` | 6.279 |
| `case221_t1s3_offline_network_70o_3_scenario_2_scacopf` | 7.699 |
| `case223_t1s3_offline_network_70o_3_scenario_3_scacopf` | 6.154 |
| `case225_t1s3_offline_network_81o_3_scenario_1_scacopf` | 28.77 |
| `case227_t1s3_offline_network_81o_3_scenario_2_scacopf` | 23.30 |
| `case229_t1s3_offline_network_81o_3_scenario_3_scacopf` | 24.70 |
| `case231_t1s3_offline_network_84o_3_scenario_1_scacopf` | 57.35 |
| `case233_t1s3_offline_network_84o_3_scenario_2_scacopf` | 60.62 |
| `case235_t1s3_offline_network_84o_3_scenario_3_scacopf` | 69.69 |
| `case237_t1s3_real_time_network_01r_3_scenario_1_scacopf` | 0.067 |
| `case239_t1s3_real_time_network_01r_3_scenario_2_scacopf` | 0.076 |
| `case241_t1s3_real_time_network_01r_3_scenario_3_scacopf` | 0.067 |
| `case243_t1s3_real_time_network_02r_3_scenario_1_scacopf` | 0.105 |
| `case245_t1s3_real_time_network_02r_3_scenario_2_scacopf` | 0.100 |
| `case247_network_02r_3_scenario_2_scenario_30_scacopf` | 0.103 |
| `case249_t1s3_real_time_network_02r_3_scenario_3_scacopf` | 0.100 |
| `case251_t1s3_real_time_network_03r_3_scenario_1_scacopf` | 0.116 |
| `case253_t1s3_real_time_network_03r_3_scenario_2_scacopf` | 0.112 |
| `case255_t1s3_real_time_network_03r_3_scenario_3_scacopf` | 0.161 |
| `case257_t1s3_real_time_network_05r_3_scenario_1_scacopf` | 8.767 |
| `case259_t1s3_real_time_network_05r_3_scenario_2_scacopf` | 8.396 |
| `case261_t1s3_real_time_network_05r_3_scenario_3_scacopf` | 8.798 |
| `case263_t1s3_real_time_network_06r_3_scenario_1_scacopf` | 5.852 |
| `case265_t1s3_real_time_network_06r_3_scenario_2_scacopf` | 6.841 |
| `case267_t1s3_real_time_network_06r_3_scenario_3_scacopf` | 8.127 |
| `case269_t1s3_real_time_network_07r_3_scenario_1_scacopf` | 5.915 |
| `case271_t1s3_real_time_network_07r_3_scenario_2_scacopf` | 7.821 |
| `case273_t1s3_real_time_network_07r_3_scenario_3_scacopf` | 8.747 |
| `case275_t1s3_real_time_network_08r_3_scenario_1_scacopf` | 16.28 |
| `case277_t1s3_real_time_network_08r_3_scenario_2_scacopf` | 16.03 |
| `case279_t1s3_real_time_network_08r_3_scenario_3_scacopf` | 17.51 |
| `case281_t1s3_real_time_network_09r_3_scenario_1_scacopf` | 33.10 |
| `case283_t1s3_real_time_network_09r_3_scenario_2_scacopf` | 45.60 |
| `case285_t1s3_real_time_network_09r_3_scenario_3_scacopf` | 48.96 |
| `case287_t1s3_real_time_network_12r_3_scenario_1_scacopf` | 415.0 |
| `case289_t1s3_real_time_network_12r_3_scenario_2_scacopf` | 400.8 |
| `case291_t1s3_real_time_network_12r_3_scenario_3_scacopf` | 398.0 |
| `case293_t1s3_real_time_network_13r_3_scenario_1_scacopf` | 105.4 |
| `case295_t1s3_real_time_network_13r_3_scenario_2_scacopf` | 163.4 |
| `case297_t1s3_real_time_network_13r_3_scenario_3_scacopf` | 147.1 |
| `case299_t1s3_real_time_network_70r_3_scenario_1_scacopf` | 7.345 |
| `case301_t1s3_real_time_network_70r_3_scenario_2_scacopf` | 5.656 |
| `case303_t1s3_real_time_network_70r_3_scenario_3_scacopf` | 4.940 |
| `case305_t1s3_real_time_network_81r_3_scenario_1_scacopf` | 20.00 |
| `case307_t1s3_real_time_network_81r_3_scenario_2_scacopf` | 22.95 |
| `case309_t1s3_real_time_network_81r_3_scenario_3_scacopf` | 30.10 |
| `case311_t1s3_real_time_network_84r_3_scenario_1_scacopf` | 58.29 |
| `case313_t1s3_real_time_network_84r_3_scenario_2_scacopf` | 53.97 |
| `case315_t1s3_real_time_network_84r_3_scenario_3_scacopf` | 56.95 |

## OPF/SC-AC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_scacopf` | 0.525 |
| `case002_pjm5_scacopf` | 难求解 |

## OTS/DC-OTS

| 案例 | 时间 (s) |
|---|---:|
| `case01_pjm5_dcots` | 0.007 |
| `case02_ieee14_dcots` | 0.010 |
| `case03_ieee118_dcots` | 0.050 |
| `case04_lmbd3_dcots` | 0.003 |
| `case05_ieee24_dcots` | 0.003 |
| `case06_as30_dcots` | 0.012 |
| `case07_ieee30_dcots` | 0.022 |
| `case08_epri39_dcots` | 0.011 |
| `case09_ieee57_dcots` | 0.079 |
| `case10_c60_dcots` | 0.022 |
| `case11_ieee73_dcots` | 0.008 |
| `case12_pegase89_dcots` | 0.043 |
| `case13_ieeedtc162_dcots` | 0.114 |
| `case14_goc179_dcots` | 0.059 |
| `case15_snem197_dcots` | 0.005 |
| `case16_activ200_dcots` | 0.007 |
| `case17_pserc240_dcots` | 0.072 |
| `case18_ieee300_dcots` | 0.074 |
| `case19_goc500_dcots` | 0.161 |
| `case20_sdet588_dcots` | 0.053 |
| `case21_goc793_dcots` | 0.104 |
| `case22_pegase1354_dcots` | 0.098 |
| `case23_snem1803_dcots` | 0.064 |
| `case24_rte1888_dcots` | 0.054 |
| `case25_rte1951_dcots` | 0.053 |
| `case26_goc2000_dcots` | 1.010 |
| `case27_goc2312_dcots` | 1.093 |
| `case28_2383wpk_dcots` | 1.042 |
| `case29_2736spk_dcots` | 0.735 |
| `case30_2737sopk_dcots` | 0.744 |
| `case31_goc2742_dcots` | 8.480 |
| `case32_2746wopk_dcots` | 0.911 |
| `case33_2746wpk_dcots` | 0.916 |
| `case34_rte2848_dcots` | 0.878 |
| `case35_sdet2853_dcots` | 1.200 |
| `case36_rte2868_dcots` | 1.391 |
| `case37_pegase2869_dcots` | 1.706 |
| `case38_3012wpk_dcots` | 1.588 |
| `case39_goc3022_dcots` | 2.820 |
| `case40_3120spk_dcots` | 1.257 |
| `case41_3375wpk_dcots` | 1.482 |
| `case42_goc3970_dcots` | 10.95 |
| `case43_goc4020_dcots` | 7.257 |
| `case44_goc4601_dcots` | 9.701 |
| `case45_goc4619_dcots` | 15.79 |
| `case46_sdet4661_dcots` | 3.449 |
| `case47_goc4837_dcots` | 7.917 |
| `case48_goc4917_dcots` | 4.448 |
| `case49_epigrids5658_dcots` | 4.570 |
| `case50_rte6468_dcots` | 3.662 |
| `case51_rte6470_dcots` | 2.423 |
| `case52_rte6495_dcots` | 3.916 |
| `case53_rte6515_dcots` | 3.619 |
| `case54_epigrids7336_dcots` | 5.233 |
| `case55_pegase8387_dcots` | 8.388 |
| `case56_pegase9241_dcots` | 9.294 |
| `case57_goc9591_dcots` | 123.8 |
| `case58_goc10000_dcots` | 13.82 |
| `case60_goc10480_dcots` | 118.6 |
| `case61_pegase13659_dcots` | 难求解 |
| `case62_goc19402_dcots` | 难求解 |
| `case63_epigrids20758_dcots` | 难求解 |
| `case64_goc24464_dcots` | 难求解 |
| `case65_goc30000_dcots` | 难求解 |
| `case66_epigrids78484_dcots` | 难求解 |

## OTS/LINEARIZED-SC-OTS

| 案例 | 时间 (s) |
|---|---:|
| `case002_t1s3_offline_network_01o_3_scenario_1_scacots` | 0.172 |
| `case004_t1s3_offline_network_01o_3_scenario_2_scacots` | 0.162 |
| `case006_t1s3_offline_network_01o_3_scenario_3_scacots` | 0.156 |
| `case008_t1s3_offline_network_02o_3_scenario_1_scacots` | 0.346 |
| `case010_t1s3_offline_network_02o_3_scenario_2_scacots` | 0.391 |
| `case012_t1s3_offline_network_02o_3_scenario_3_scacots` | 0.414 |
| `case014_t1s3_offline_network_03o_3_scenario_1_scacots` | 0.488 |
| `case016_t1s3_offline_network_03o_3_scenario_2_scacots` | 0.654 |
| `case018_t1s3_offline_network_03o_3_scenario_3_scacots` | 0.643 |
| `case020_t1s3_offline_network_05o_3_scenario_1_scacots` | 16.96 |
| `case022_t1s3_offline_network_05o_3_scenario_2_scacots` | 13.55 |
| `case024_t1s3_offline_network_05o_3_scenario_3_scacots` | 18.18 |
| `case026_t1s3_offline_network_06o_3_scenario_1_scacots` | 21.07 |
| `case028_t1s3_offline_network_06o_3_scenario_2_scacots` | 22.52 |
| `case030_t1s3_offline_network_06o_3_scenario_3_scacots` | 20.34 |
| `case032_t1s3_offline_network_07o_3_scenario_1_scacots` | 16.59 |
| `case034_t1s3_offline_network_07o_3_scenario_2_scacots` | 21.23 |
| `case036_t1s3_offline_network_07o_3_scenario_3_scacots` | 20.51 |
| `case038_t1s3_offline_network_08o_3_scenario_1_scacots` | 26.99 |
| `case040_t1s3_offline_network_08o_3_scenario_2_scacots` | 35.81 |
| `case042_t1s3_offline_network_08o_3_scenario_3_scacots` | 28.68 |
| `case044_t1s3_offline_network_09o_3_scenario_1_scacots` | 63.18 |
| `case046_t1s3_offline_network_09o_3_scenario_2_scacots` | 48.45 |
| `case048_t1s3_offline_network_09o_3_scenario_3_scacots` | 54.49 |
| `case050_t1s3_offline_network_12o_3_scenario_1_scacots` | 191.4 |
| `case052_t1s3_offline_network_12o_3_scenario_2_scacots` | 203.0 |
| `case054_t1s3_offline_network_12o_3_scenario_3_scacots` | 415.3 |
| `case056_t1s3_offline_network_13o_3_scenario_1_scacots` | 难求解 |
| `case058_t1s3_offline_network_13o_3_scenario_2_scacots` | 难求解 |
| `case060_t1s3_offline_network_13o_3_scenario_3_scacots` | 难求解 |
| `case062_t1s3_offline_network_70o_3_scenario_1_scacots` | 17.45 |
| `case064_t1s3_offline_network_70o_3_scenario_2_scacots` | 17.10 |
| `case066_t1s3_offline_network_70o_3_scenario_3_scacots` | 17.98 |
| `case068_t1s3_offline_network_81o_3_scenario_1_scacots` | 45.05 |
| `case070_t1s3_offline_network_81o_3_scenario_2_scacots` | 46.53 |
| `case072_t1s3_offline_network_81o_3_scenario_3_scacots` | 45.88 |
| `case074_t1s3_offline_network_84o_3_scenario_1_scacots` | 87.27 |
| `case076_t1s3_offline_network_84o_3_scenario_2_scacots` | 95.86 |
| `case078_t1s3_offline_network_84o_3_scenario_3_scacots` | 66.43 |
| `case080_t1s3_real_time_network_01r_3_scenario_1_scacots` | 0.150 |
| `case082_t1s3_real_time_network_01r_3_scenario_2_scacots` | 0.151 |
| `case084_t1s3_real_time_network_01r_3_scenario_3_scacots` | 0.160 |
| `case086_t1s3_real_time_network_02r_3_scenario_1_scacots` | 0.371 |
| `case088_t1s3_real_time_network_02r_3_scenario_2_scacots` | 0.393 |
| `case090_network_02r_3_scenario_2_scenario_30_scacots` | 0.388 |
| `case092_t1s3_real_time_network_02r_3_scenario_3_scacots` | 0.435 |
| `case094_t1s3_real_time_network_03r_3_scenario_1_scacots` | 0.487 |
| `case096_t1s3_real_time_network_03r_3_scenario_2_scacots` | 0.664 |
| `case098_t1s3_real_time_network_03r_3_scenario_3_scacots` | 0.629 |
| `case100_t1s3_real_time_network_05r_3_scenario_1_scacots` | 16.93 |
| `case102_t1s3_real_time_network_05r_3_scenario_2_scacots` | 14.99 |
| `case104_t1s3_real_time_network_05r_3_scenario_3_scacots` | 21.06 |
| `case106_t1s3_real_time_network_06r_3_scenario_1_scacots` | 24.61 |
| `case108_t1s3_real_time_network_06r_3_scenario_2_scacots` | 28.85 |
| `case110_t1s3_real_time_network_06r_3_scenario_3_scacots` | 29.39 |
| `case112_t1s3_real_time_network_07r_3_scenario_1_scacots` | 20.88 |
| `case114_t1s3_real_time_network_07r_3_scenario_2_scacots` | 19.92 |
| `case116_t1s3_real_time_network_07r_3_scenario_3_scacots` | 20.62 |
| `case118_t1s3_real_time_network_08r_3_scenario_1_scacots` | 26.96 |
| `case120_t1s3_real_time_network_08r_3_scenario_2_scacots` | 40.73 |
| `case122_t1s3_real_time_network_08r_3_scenario_3_scacots` | 29.29 |
| `case124_t1s3_real_time_network_09r_3_scenario_1_scacots` | 63.42 |
| `case126_t1s3_real_time_network_09r_3_scenario_2_scacots` | 54.61 |
| `case128_t1s3_real_time_network_09r_3_scenario_3_scacots` | 62.67 |
| `case130_t1s3_real_time_network_12r_3_scenario_1_scacots` | 196.0 |
| `case132_t1s3_real_time_network_12r_3_scenario_2_scacots` | 195.6 |
| `case134_t1s3_real_time_network_12r_3_scenario_3_scacots` | 521.7 |
| `case136_t1s3_real_time_network_13r_3_scenario_1_scacots` | 123.5 |
| `case138_t1s3_real_time_network_13r_3_scenario_2_scacots` | 155.9 |
| `case140_t1s3_real_time_network_13r_3_scenario_3_scacots` | 166.7 |
| `case142_t1s3_real_time_network_70r_3_scenario_1_scacots` | 18.61 |
| `case144_t1s3_real_time_network_70r_3_scenario_2_scacots` | 18.00 |
| `case146_t1s3_real_time_network_70r_3_scenario_3_scacots` | 17.87 |
| `case148_t1s3_real_time_network_81r_3_scenario_1_scacots` | 50.77 |
| `case150_t1s3_real_time_network_81r_3_scenario_2_scacots` | 49.54 |
| `case152_t1s3_real_time_network_81r_3_scenario_3_scacots` | 54.25 |
| `case154_t1s3_real_time_network_84r_3_scenario_1_scacots` | 85.33 |
| `case156_t1s3_real_time_network_84r_3_scenario_2_scacots` | 95.29 |
| `case158_t1s3_real_time_network_84r_3_scenario_3_scacots` | 69.42 |
| `case160_t1s3_offline_network_01o_3_scenario_1_scacots` | 0.171 |
| `case162_t1s3_offline_network_01o_3_scenario_2_scacots` | 0.176 |
| `case164_t1s3_offline_network_01o_3_scenario_3_scacots` | 0.161 |
| `case166_t1s3_offline_network_02o_3_scenario_1_scacots` | 0.357 |
| `case168_t1s3_offline_network_02o_3_scenario_2_scacots` | 0.417 |
| `case170_t1s3_offline_network_02o_3_scenario_3_scacots` | 0.414 |
| `case172_t1s3_offline_network_03o_3_scenario_1_scacots` | 0.528 |
| `case174_t1s3_offline_network_03o_3_scenario_2_scacots` | 0.654 |
| `case176_t1s3_offline_network_03o_3_scenario_3_scacots` | 0.620 |
| `case178_t1s3_offline_network_05o_3_scenario_1_scacots` | 17.54 |
| `case180_t1s3_offline_network_05o_3_scenario_2_scacots` | 17.46 |
| `case182_t1s3_offline_network_05o_3_scenario_3_scacots` | 19.05 |
| `case184_t1s3_offline_network_06o_3_scenario_1_scacots` | 23.59 |
| `case186_t1s3_offline_network_06o_3_scenario_2_scacots` | 24.23 |
| `case188_t1s3_offline_network_06o_3_scenario_3_scacots` | 21.31 |
| `case190_t1s3_offline_network_07o_3_scenario_1_scacots` | 23.66 |
| `case192_t1s3_offline_network_07o_3_scenario_2_scacots` | 23.60 |
| `case194_t1s3_offline_network_07o_3_scenario_3_scacots` | 25.20 |
| `case196_t1s3_offline_network_08o_3_scenario_1_scacots` | 28.14 |
| `case198_t1s3_offline_network_08o_3_scenario_2_scacots` | 40.82 |
| `case200_t1s3_offline_network_08o_3_scenario_3_scacots` | 30.42 |
| `case202_t1s3_offline_network_09o_3_scenario_1_scacots` | 32.06 |
| `case204_t1s3_offline_network_09o_3_scenario_2_scacots` | 33.87 |
| `case206_t1s3_offline_network_09o_3_scenario_3_scacots` | 32.11 |
| `case208_t1s3_offline_network_12o_3_scenario_1_scacots` | 368.9 |
| `case210_t1s3_offline_network_12o_3_scenario_2_scacots` | 276.6 |
| `case212_t1s3_offline_network_12o_3_scenario_3_scacots` | 499.3 |
| `case214_t1s3_offline_network_13o_3_scenario_1_scacots` | 难求解 |
| `case216_t1s3_offline_network_13o_3_scenario_2_scacots` | 难求解 |
| `case218_t1s3_offline_network_13o_3_scenario_3_scacots` | 难求解 |
| `case220_t1s3_offline_network_70o_3_scenario_1_scacots` | 19.51 |
| `case222_t1s3_offline_network_70o_3_scenario_2_scacots` | 15.81 |
| `case224_t1s3_offline_network_70o_3_scenario_3_scacots` | 16.32 |
| `case226_t1s3_offline_network_81o_3_scenario_1_scacots` | 56.50 |
| `case228_t1s3_offline_network_81o_3_scenario_2_scacots` | 44.66 |
| `case230_t1s3_offline_network_81o_3_scenario_3_scacots` | 51.17 |
| `case232_t1s3_offline_network_84o_3_scenario_1_scacots` | 108.1 |
| `case234_t1s3_offline_network_84o_3_scenario_2_scacots` | 93.11 |
| `case236_t1s3_offline_network_84o_3_scenario_3_scacots` | 62.53 |
| `case238_t1s3_real_time_network_01r_3_scenario_1_scacots` | 0.153 |
| `case240_t1s3_real_time_network_01r_3_scenario_2_scacots` | 0.159 |
| `case242_t1s3_real_time_network_01r_3_scenario_3_scacots` | 0.150 |
| `case244_t1s3_real_time_network_02r_3_scenario_1_scacots` | 0.366 |
| `case246_t1s3_real_time_network_02r_3_scenario_2_scacots` | 0.397 |
| `case248_network_02r_3_scenario_2_scenario_30_scacots` | 0.399 |
| `case250_t1s3_real_time_network_02r_3_scenario_3_scacots` | 0.416 |
| `case252_t1s3_real_time_network_03r_3_scenario_1_scacots` | 0.492 |
| `case254_t1s3_real_time_network_03r_3_scenario_2_scacots` | 0.663 |
| `case256_t1s3_real_time_network_03r_3_scenario_3_scacots` | 0.627 |
| `case258_t1s3_real_time_network_05r_3_scenario_1_scacots` | 19.14 |
| `case260_t1s3_real_time_network_05r_3_scenario_2_scacots` | 14.71 |
| `case262_t1s3_real_time_network_05r_3_scenario_3_scacots` | 17.78 |
| `case264_t1s3_real_time_network_06r_3_scenario_1_scacots` | 20.58 |
| `case266_t1s3_real_time_network_06r_3_scenario_2_scacots` | 19.84 |
| `case268_t1s3_real_time_network_06r_3_scenario_3_scacots` | 20.97 |
| `case270_t1s3_real_time_network_07r_3_scenario_1_scacots` | 26.64 |
| `case272_t1s3_real_time_network_07r_3_scenario_2_scacots` | 22.46 |
| `case274_t1s3_real_time_network_07r_3_scenario_3_scacots` | 24.17 |
| `case276_t1s3_real_time_network_08r_3_scenario_1_scacots` | 36.94 |
| `case278_t1s3_real_time_network_08r_3_scenario_2_scacots` | 36.37 |
| `case280_t1s3_real_time_network_08r_3_scenario_3_scacots` | 29.55 |
| `case282_t1s3_real_time_network_09r_3_scenario_1_scacots` | 71.23 |
| `case284_t1s3_real_time_network_09r_3_scenario_2_scacots` | 58.60 |
| `case286_t1s3_real_time_network_09r_3_scenario_3_scacots` | 68.58 |
| `case288_t1s3_real_time_network_12r_3_scenario_1_scacots` | 189.0 |
| `case290_t1s3_real_time_network_12r_3_scenario_2_scacots` | 278.8 |
| `case292_t1s3_real_time_network_12r_3_scenario_3_scacots` | 难求解 |
| `case294_t1s3_real_time_network_13r_3_scenario_1_scacots` | 难求解 |
| `case296_t1s3_real_time_network_13r_3_scenario_2_scacots` | 难求解 |
| `case298_t1s3_real_time_network_13r_3_scenario_3_scacots` | 难求解 |
| `case300_t1s3_real_time_network_70r_3_scenario_1_scacots` | 18.96 |
| `case302_t1s3_real_time_network_70r_3_scenario_2_scacots` | 16.16 |
| `case304_t1s3_real_time_network_70r_3_scenario_3_scacots` | 24.56 |
| `case306_t1s3_real_time_network_81r_3_scenario_1_scacots` | 57.62 |
| `case308_t1s3_real_time_network_81r_3_scenario_2_scacots` | 39.24 |
| `case310_t1s3_real_time_network_81r_3_scenario_3_scacots` | 54.86 |
| `case312_t1s3_real_time_network_84r_3_scenario_1_scacots` | 117.3 |
| `case314_t1s3_real_time_network_84r_3_scenario_2_scacots` | 119.4 |
| `case316_t1s3_real_time_network_84r_3_scenario_3_scacots` | 71.81 |

## OTS/SC-OTS

| 案例 | 时间 (s) |
|---|---:|
| `case01_lmbd3_scots` | 0.000 |
| `case02_pjm5_scots` | 0.004 |
| `case03_ieee14_scots` | 0.020 |
| `case04_ieee24_scots` | 0.287 |
| `case05_ieee73_scots` | 13.59 |
| `case06_activs200_scots` | 7.894 |
| `case07_as30_scots` | 0.034 |
| `case08_ieee30_scots` | 0.095 |
| `case09_epri39_scots` | 0.059 |
| `case10_ieee57_scots` | 0.096 |
| `case11_c60_scots` | 0.111 |
| `case12_pegase89_scots` | 0.058 |
| `case13_ieee118_scots` | 0.195 |
| `case14_ieeedtc162_scots` | 0.403 |
| `case15_goc179_scots` | 0.077 |
| `case16_snem197_scots` | 0.061 |
| `case17_pserc240_scots` | 0.646 |
| `case18_ieee300_scots` | 0.463 |
| `case19_goc500_scots` | 0.725 |
| `case20_sdet588_scots` | 1.038 |
| `case21_goc793_scots` | 1.796 |
| `case24_rte1888_scots` | 3.603 |
| `case25_rte1951_scots` | 3.758 |
| `case26_goc2000_scots` | 22.76 |
| `case28_2383wpk_scots` | 5.249 |
| `case31_goc2742_scots` | 57.35 |
| `case34_rte2848_scots` | 5.460 |
| `case36_rte2868_scots` | 6.658 |
| `case37_pegase2869_scots` | 11.90 |
| `case42_goc3970_scots` | 65.10 |
| `case43_goc4020_scots` | 31.40 |
| `case44_goc4601_scots` | 75.53 |
| `case45_goc4619_scots` | 91.35 |
| `case47_goc4837_scots` | 48.89 |
| `case49_epigrids5658_scots` | 难求解 |
| `case50_rte6468_scots` | 难求解 |
| `case51_rte6470_scots` | 难求解 |
| `case52_rte6495_scots` | 难求解 |
| `case53_rte6515_scots` | 难求解 |
| `case54_epigrids7336_scots` | 难求解 |
| `case55_pegase8387_scots` | 难求解 |
| `case56_pegase9241_scots` | 难求解 |
| `case57_goc9591_scots` | 难求解 |
| `case58_goc10000_scots` | 难求解 |
| `case60_goc10480_scots` | 难求解 |
| `case61_pegase13659_scots` | 难求解 |
| `case62_goc19402_scots` | 难求解 |
| `case63_epigrids20758_scots` | 难求解 |
| `case64_goc24464_scots` | 难求解 |
| `case65_goc30000_scots` | 难求解 |
| `case66_epigrids78484_scots` | 难求解 |

## PLANNING/DISTRIBUTION-EXPANSION

| 案例 | 时间 (s) |
|---|---:|
| `case001_radial5_distexp` | 0.003 |
| `case002_radial8_distexp` | 0.001 |

## PLANNING/GCEP-DC

| 案例 | 时间 (s) |
|---|---:|
| `case001_tx123_y2_d1` | 0.770 |
| `case002_tx123_y3_d2` | 10.45 |
| `case003_tx123_y7_d5` | 435.1 |

## PLANNING/RESOURCE-CAPACITY-EXPANSION

| 案例 | 时间 (s) |
|---|---:|
| `case01_1_three_zones_cem` | 0.004 |
| `case02_2_three_zones_w_electrolyzer_cem` | 0.010 |
| `case03_3_three_zones_w_co2_capture_cem` | 0.004 |
| `case04_4_three_zones_w_policies_slack_cem` | 0.003 |
| `case05_5_three_zones_w_piecewise_fuel_cem` | 0.005 |
| `case06_6_three_zones_w_multistage_cem` | 0.003 |
| `case07_7_three_zones_w_colocated_vre_storage_cem` | 0.005 |
| `case08_8_three_zones_w_colocated_vre_storage_electrolyzers_cem` | 0.008 |
| `case09_9_three_zones_w_retrofit_cem` | 0.006 |
| `case10_11_three_zones_w_allam_cycle_lox_cem` | 0.005 |

## PLANNING/TRANSMISSION-EXPANSION

| 案例 | 时间 (s) |
|---|---:|
| `case001_case3_tnep` | 0.010 |
| `case002_case5_tnep` | 0.001 |
| `case003_lmbd3_tep_syn` | 0.001 |
| `case004_pjm5_tep_syn` | 0.001 |
| `case005_ieee14_tep_syn` | 0.001 |
| `case006_ieee24_tep_syn` | 0.002 |
| `case007_as30_tep_syn` | 0.004 |
| `case008_ieee30_tep_syn` | 0.001 |
| `case009_epri39_tep_syn` | 0.005 |
| `case010_ieee57_tep_syn` | 0.003 |
| `case011_c60_tep_syn` | 0.002 |
| `case012_ieee73_tep_syn` | 0.009 |
| `case013_pegase89_tep_syn` | 0.012 |
| `case014_ieee118_tep_syn` | 0.011 |
| `case015_ieeedtc162_tep_syn` | 0.011 |
| `case016_goc179_tep_syn` | 0.004 |
| `case017_snem197_tep_syn` | 0.008 |
| `case018_activ200_tep_syn` | 0.008 |
| `case019_pserc240_tep_syn` | 0.018 |
| `case020_ieee300_tep_syn` | 0.011 |
| `case021_goc500_tep_syn` | 0.134 |
| `case022_sdet588_tep_syn` | 0.017 |
| `case023_goc793_tep_syn` | 0.035 |
| `case024_pegase1354_tep_syn` | 0.232 |
| `case025_snem1803_tep_syn` | 0.317 |
| `case026_rte1888_tep_syn` | 0.275 |
| `case027_rte1951_tep_syn` | 0.240 |
| `case028_goc2000_tep_syn` | 0.672 |
| `case029_goc2312_tep_syn` | 0.915 |
| `case030_2383wpk_tep_syn` | 0.325 |
| `case031_2736spk_tep_syn` | 0.327 |
| `case032_2737sopk_tep_syn` | 0.509 |
| `case033_goc2742_tep_syn` | 1.692 |
| `case034_2746wopk_tep_syn` | 0.289 |
| `case035_2746wpk_tep_syn` | 0.322 |
| `case036_rte2848_tep_syn` | 0.439 |
| `case037_sdet2853_tep_syn` | 0.456 |
| `case038_rte2868_tep_syn` | 0.456 |
| `case039_pegase2869_tep_syn` | 0.509 |
| `case040_3012wpk_tep_syn` | 0.363 |
| `case041_goc3022_tep_syn` | 1.314 |
| `case042_3120spk_tep_syn` | 0.381 |
| `case043_3375wpk_tep_syn` | 0.471 |
| `case044_goc3970_tep_syn` | 3.960 |
| `case045_goc4020_tep_syn` | 2.548 |
| `case046_goc4601_tep_syn` | 2.204 |
| `case047_goc4619_tep_syn` | 2.552 |
| `case048_sdet4661_tep_syn` | 1.076 |
| `case049_goc4837_tep_syn` | 2.630 |
| `case050_goc4917_tep_syn` | 2.315 |
| `case051_epigrids5658_tep_syn` | 1.308 |
| `case052_rte6468_tep_syn` | 1.094 |
| `case053_rte6470_tep_syn` | 1.149 |
| `case054_rte6495_tep_syn` | 1.113 |
| `case055_rte6515_tep_syn` | 1.240 |
| `case056_epigrids7336_tep_syn` | 2.613 |
| `case057_pegase8387_tep_syn` | 3.238 |
| `case058_pegase9241_tep_syn` | 7.321 |
| `case059_goc9591_tep_syn` | 93.80 |
| `case060_goc10000_tep_syn` | 17.07 |
| `case062_goc10480_tep_syn` | 11.80 |
| `case063_pegase13659_tep_syn` | 5.820 |
| `case064_goc19402_tep_syn` | 难求解 |
| `case065_epigrids20758_tep_syn` | 难求解 |
| `case066_goc24464_tep_syn` | 难求解 |
| `case067_goc30000_tep_syn` | 难求解 |
| `case068_epigrids78484_tep_syn` | 难求解 |

## RESILIENCE/CONTROLLED-ISLANDING

| 案例 | 时间 (s) |
|---|---:|
| `case001_pjm5bus_island` | 0.001 |
| `case002_GBnetwork_island` | 难求解 |
| `case003_EI_33_island` | 难求解 |
| `case004_ieee14_island` | 0.008 |
| `case005_ieee14_ac8b_island` | 0.007 |
| `case006_ieee14_ace_island` | 0.007 |
| `case007_ieee14_alter_island` | 0.007 |
| `case008_ieee14_conn_island` | 0.014 |
| `case009_ieee14_dgprct1_island` | 0.008 |
| `case010_ieee14_dgprctext_island` | 0.008 |
| `case011_ieee14_esac1a_island` | 0.007 |
| `case012_ieee14_esd1_island` | 0.008 |
| `case013_ieee14_esd1u_island` | 0.008 |
| `case014_ieee14_esdc1a_island` | 0.007 |
| `case015_ieee14_esst1a_island` | 0.007 |
| `case016_ieee14_esst3a_island` | 0.007 |
| `case017_ieee14_esst4b_island` | 0.007 |
| `case018_ieee14_exac1_island` | 0.007 |
| `case019_ieee14_exac4_island` | 0.007 |
| `case020_ieee14_fault_island` | 0.007 |
| `case021_ieee14_fload_island` | 0.007 |
| `case022_ieee14_freqdiv_island` | 0.007 |
| `case023_ieee14_full_island` | 0.007 |
| `case024_ieee14_gast_island` | 0.007 |
| `case025_ieee14_gentrip_island` | 0.007 |
| `case026_ieee14_hygov_island` | 0.007 |
| `case027_ieee14_hygov4_island` | 0.007 |
| `case028_ieee14_hygovdb_island` | 0.007 |
| `case029_ieee14_ieeet1_island` | 0.007 |
| `case030_ieee14_ieeet3_island` | 0.007 |
| `case031_ieee14_ieeevc2_island` | 0.007 |
| `case032_ieee14_ieesgo_island` | 0.007 |
| `case033_ieee14_island_island` | 0.007 |
| `case034_ieee14_linetrip_island` | 0.007 |
| `case035_ieee14_plbvfu1_island` | 0.007 |
| `case036_ieee14_pll1_island` | 0.007 |
| `case037_ieee14_pvd1_island` | 0.008 |
| `case038_ieee14_pvd1u_island` | 0.008 |
| `case039_ieee14_reecb1_island` | 0.007 |
| `case040_ieee14_regcp1_island` | 0.007 |
| `case041_ieee14_regcp1_nopll_island` | 0.007 |
| `case042_ieee14_shaft5_island` | 0.007 |
| `case043_ieee14_shuntsw_island` | 0.007 |
| `case044_ieee14_solar_island` | 0.007 |
| `case045_ieee14_solar_abn_island` | 0.007 |
| `case046_ieee14_timeseries_island` | 0.007 |
| `case047_ieee14_wt3_island` | 0.007 |
| `case048_ieee14_wt3n_island` | 0.007 |
| `case049_ieee14_zip_island` | 0.007 |
| `case050_ieee39_full_island` | 0.038 |
| `case051_kundur_aw_island` | 0.010 |
| `case052_kundur_coi_island` | 0.010 |
| `case053_kundur_coi_empty_island` | 0.009 |
| `case054_kundur_coi_partial_island` | 0.010 |
| `case055_kundur_esdc2a_island` | 0.010 |
| `case056_kundur_esst3a_island` | 0.010 |
| `case057_kundur_exdc2_zero_tb_island` | 0.010 |
| `case058_kundur_exst1_island` | 0.010 |
| `case059_kundur_freq_island` | 0.010 |
| `case060_kundur_full_island` | 0.010 |
| `case061_kundur_gentrip_island` | 0.010 |
| `case062_kundur_ieeeg1_island` | 0.010 |
| `case063_kundur_ieeest_island` | 0.010 |
| `case064_kundur_islands_island` | 0.012 |
| `case065_kundur_motor_island` | 0.010 |
| `case066_kundur_pmu_island` | 0.010 |
| `case067_kundur_reg_island` | 0.010 |
| `case068_kundur_sexs_island` | 0.010 |
| `case069_kundur_st2cut_island` | 0.010 |
| `case070_kundur_vsc_island` | 0.010 |
| `case071_kundur_wtds_island` | 0.009 |
| `case072_kundur_wtdta1_island` | 0.010 |
| `case073_npcc_island` | 难求解 |
| `case074_SMIB_island` | 0.001 |
| `case075_wecc_full_island` | 22.41 |
| `case076_wecc_gencls_island` | 24.33 |
| `case077_case5_pjm_island` | 0.001 |
| `case078_case14_ieee_island` | 0.010 |
| `case079_case30_ieee_island` | 0.008 |
| `case080_case39_epri_island` | 0.130 |
| `case081_case57_ieee_island` | 0.995 |
| `case082_case118_ieee_island` | 4.754 |

## RESILIENCE/DISTRIBUTION-RESTORATION

| 案例 | 时间 (s) |
|---|---:|
| `case01_mv_rural_restore` | 0.122 |
| `case02_lv_rural2_restore` | 0.040 |
| `case03_gso_rural_restore` | 0.001 |

## RESILIENCE/MAXIMUM-LOAD-DELIVERY

| 案例 | 时间 (s) |
|---|---:|
| `case001_case3_mld_mld` | 0.001 |
| `case002_case3_mld_lc_mld` | 0.000 |
| `case003_case3_mld_s_mld` | 0.000 |
| `case004_case3_mld_uc_mld` | 0.000 |
| `case005_case3_restoration_total_dmg_mld` | 0.000 |
| `case006_case5_mld_ft_mld` | 0.000 |
| `case007_case5_mld_strg_mld` | 0.000 |
| `case008_case5_mld_strg_only_mld` | 0.000 |
| `case009_case5_mld_strg_uc_mld` | 0.000 |
| `case010_case5_restoration_mld` | 0.000 |
| `case011_case5_restoration_shunt_mld` | 0.000 |
| `case012_case5_restoration_strg_mld` | 0.000 |
| `case013_case5_restoration_total_dmg_mld` | 0.000 |
| `case014_case5_pjm_dmg_mld` | 0.000 |
| `case015_case14_ieee_dmg_mld` | 0.000 |
| `case016_case30_ieee_dmg_mld` | 0.000 |
| `case017_case57_ieee_dmg_mld` | 0.001 |
| `case018_case118_ieee_dmg_mld` | 0.002 |

## RESILIENCE/NETWORK-INTERDICTION

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_nk_int` | 0.004 |
| `case002_lmbd3_gen_nk_int` | 0.001 |
| `case003_pjm5_nk_int` | 0.017 |
| `case004_pjm5_gen_nk_int` | 0.002 |
| `case005_ieee14_nk_int` | 0.042 |
| `case006_ieee14_gen_nk_int` | 0.004 |
| `case007_ieee24_nk_int` | 0.092 |
| `case008_as30_nk_int` | 0.146 |
| `case009_ieee30_nk_int` | 0.133 |
| `case010_epri39_nk_int` | 0.187 |
| `case011_ieee57_nk_int` | 0.839 |
| `case012_c60_nk_int` | 1.071 |
| `case013_ieee73_nk_int` | 2.101 |
| `case014_pegase89_nk_int` | 4.752 |
| `case015_ieee118_nk_int` | 4.152 |
| `case016_ieeedtc162_nk_int` | 21.39 |
| `case017_goc179_nk_int` | 11.70 |
| `case018_snem197_nk_int` | 13.74 |
| `case019_activ200_nk_int` | 12.90 |
| `case020_pserc240_nk_int` | 33.03 |
| `case021_ieee300_nk_int` | 34.69 |
| `case022_goc500_nk_int` | 难求解 |
| `case023_sdet588_nk_int` | 难求解 |
| `case024_goc793_nk_int` | 难求解 |
| `case025_pegase1354_nk_int` | 难求解 |
| `case026_snem1803_nk_int` | 难求解 |
| `case027_rte1888_nk_int` | 难求解 |
| `case028_rte1951_nk_int` | 难求解 |
| `case029_goc2000_nk_int` | 难求解 |
| `case030_goc2312_nk_int` | 难求解 |
| `case031_2383wpk_nk_int` | 难求解 |
| `case032_2736spk_nk_int` | 难求解 |
| `case033_2737sopk_nk_int` | 难求解 |
| `case034_goc2742_nk_int` | 难求解 |
| `case035_2746wopk_nk_int` | 难求解 |
| `case036_2746wpk_nk_int` | 难求解 |
| `case037_rte2848_nk_int` | 难求解 |
| `case038_sdet2853_nk_int` | 难求解 |
| `case039_rte2868_nk_int` | 难求解 |
| `case040_pegase2869_nk_int` | 难求解 |
| `case041_3012wpk_nk_int` | 难求解 |
| `case042_goc3022_nk_int` | 难求解 |
| `case043_3120spk_nk_int` | 难求解 |
| `case044_3375wpk_nk_int` | 难求解 |
| `case045_goc3970_nk_int` | 难求解 |
| `case046_goc4020_nk_int` | 难求解 |
| `case047_goc4601_nk_int` | 难求解 |
| `case048_goc4619_nk_int` | 难求解 |
| `case049_sdet4661_nk_int` | 难求解 |
| `case050_goc4837_nk_int` | 难求解 |
| `case051_goc4917_nk_int` | 难求解 |
| `case052_epigrids5658_nk_int` | 难求解 |
| `case053_rte6468_nk_int` | 难求解 |
| `case054_rte6470_nk_int` | 难求解 |
| `case055_rte6495_nk_int` | 难求解 |
| `case056_rte6515_nk_int` | 难求解 |
| `case057_epigrids7336_nk_int` | 难求解 |
| `case059_pegase9241_nk_int` | 难求解 |
| `case060_goc9591_nk_int` | 难求解 |
| `case061_goc10000_nk_int` | 难求解 |
| `case062_epigrids10192_nk_int` | 难求解 |
| `case063_goc10480_nk_int` | 难求解 |
| `case064_pegase13659_nk_int` | 难求解 |
| `case065_goc19402_nk_int` | 难求解 |
| `case066_epigrids20758_nk_int` | 难求解 |
| `case067_goc24464_nk_int` | 难求解 |
| `case068_goc30000_nk_int` | 难求解 |
| `case069_epigrids78484_nk_int` | 难求解 |

## RESILIENCE/OPTIMAL-POWER-SHUTOFF

| 案例 | 时间 (s) |
|---|---:|
| `case001_rts_gmlc_risk_rb00_ops` | 0.006 |
| `case002_rts_gmlc_risk_rb25_ops` | 1.310 |
| `case003_rts_gmlc_risk_rb50_ops` | 5.335 |
| `case004_rts_gmlc_risk_rb75_ops` | 0.034 |
| `case005_rts_gmlc_risk_rb100_ops` | 0.026 |
| `case006_case14_risk_rb00_ops` | 0.000 |
| `case007_case14_risk_rb25_ops` | 0.043 |
| `case008_case14_risk_rb50_ops` | 0.006 |
| `case009_case14_risk_rb75_ops` | 0.006 |
| `case010_case14_risk_rb100_ops` | 0.006 |
| `case011_case3_rb00_ops` | 0.000 |
| `case012_case3_rb25_ops` | 0.001 |
| `case013_case3_rb50_ops` | 0.001 |
| `case014_case3_rb75_ops` | 0.002 |
| `case015_case3_rb100_ops` | 0.001 |
| `case016_case5_risk_mops_rb00_ops` | 0.000 |
| `case017_case5_risk_mops_rb25_ops` | 0.001 |
| `case018_case5_risk_mops_rb50_ops` | 0.002 |
| `case019_case5_risk_mops_rb75_ops` | 0.001 |
| `case020_case5_risk_mops_rb100_ops` | 0.000 |
| `case021_case5_risk_sys1_rb00_ops` | 0.000 |
| `case022_case5_risk_sys1_rb25_ops` | 0.001 |
| `case023_case5_risk_sys1_rb50_ops` | 0.001 |
| `case024_case5_risk_sys1_rb75_ops` | 0.001 |
| `case025_case5_risk_sys1_rb100_ops` | 0.001 |
| `case026_case5_risk_sys2_rb00_ops` | 0.000 |
| `case027_case5_risk_sys2_rb25_ops` | 0.002 |
| `case028_case5_risk_sys2_rb50_ops` | 0.003 |
| `case029_case5_risk_sys2_rb75_ops` | 0.004 |
| `case030_case5_risk_sys2_rb100_ops` | 0.001 |
| `case031_case5_strg_rb00_ops` | 0.000 |
| `case032_case5_strg_rb25_ops` | 0.002 |
| `case033_case5_strg_rb50_ops` | 0.003 |
| `case034_case5_strg_rb75_ops` | 0.001 |
| `case035_case5_strg_rb100_ops` | 0.001 |

## RESILIENCE/POWER-RESTORATION

| 案例 | 时间 (s) |
|---|---:|
| `case001_case3_restoration_total_dmg_restore` | 0.007 |
| `case002_case5_restoration_restore` | 0.009 |
| `case003_case5_restoration_shunt_restore` | 0.005 |
| `case004_case5_restoration_strg_restore` | 0.013 |
| `case005_case5_restoration_total_dmg_restore` | 0.071 |
| `case006_activsg200_scenario1_restore` | 0.098 |
| `case007_activsg200_scenario2_restore` | 0.668 |
| `case008_activsg200_scenario3_restore` | 7.382 |
| `case009_activsg200_scenario4_restore` | 难求解 |
| `case010_activsg200_scenario5_restore` | 0.099 |
| `case011_activsg200_scenario6_restore` | 0.577 |
| `case012_activsg200_scenario7_restore` | 6.638 |
| `case013_activsg200_scenario8_restore` | 难求解 |

## SCHEDULING/HYDROTHERMAL-SCHEDULING

| 案例 | 时间 (s) |
|---|---:|
| `case01_rcuc_100_50_1_w_ht` | 0.942 |
| `case02_rcuc_100_50_2_w_ht` | 1.496 |
| `case03_rcuc_150_75_1_w_ht` | 6.525 |
| `case04_rcuc_150_75_2_w_ht` | 4.445 |
| `case05_rcuc_200_100_1_w_ht` | 2.897 |
| `case06_rcuc_200_100_2_w_ht` | 6.597 |
| `case07_rcuc_20_10_1_w_ht` | 3.077 |
| `case08_rcuc_20_10_2_w_ht` | 0.423 |
| `case09_rcuc_50_20_1_w_ht` | 1.644 |
| `case10_rcuc_50_20_2_w_ht` | 8.632 |
| `case11_rcuc_75_35_1_w_ht` | 2.052 |
| `case12_rcuc_75_35_2_w_ht` | 9.271 |
| `case13_s46a_scen1_ht` | 27.24 |
| `case14_s46a_scen4_ht` | 120.0 |
| `case15_s46a_scen9_ht` | 难求解 |
| `case16_s46a_scen16_ht` | 难求解 |
| `case17_s46b_scen1_ht` | 1.288 |
| `case18_s46b_scen4_ht` | 11.80 |
| `case19_s46b_scen9_ht` | 56.15 |
| `case20_s46b_scen16_ht` | 187.3 |
| `case21_s46c_scen1_ht` | 5.151 |
| `case22_s46c_scen4_ht` | 49.47 |
| `case23_s46c_scen9_ht` | 305.9 |
| `case24_s46c_scen16_ht` | 难求解 |
| `case25_s46d_scen1_ht` | 1.043 |
| `case26_s46d_scen4_ht` | 8.666 |
| `case27_s46d_scen9_ht` | 46.45 |
| `case28_s46d_scen16_ht` | 217.6 |
| `case29_s46e_scen1_ht` | 3.594 |
| `case30_s46e_scen4_ht` | 54.94 |
| `case31_s46e_scen9_ht` | 306.3 |
| `case32_s46e_scen16_ht` | 难求解 |

## SCHEDULING/MAINTENANCE-SCHEDULING

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_week168_maint` | 0.190 |
| `case02_rts_gmlc_4week_daily_maint` | 0.016 |
| `case03_pglib_rts_20200127_T24_maint` | 0.003 |
| `case04_pglib_rts_20200706_T48_maint` | 0.014 |
| `case05_pglib_ca_top40_T24_maint` | 0.004 |

## SCHEDULING/STORAGE-SCHEDULING

| 案例 | 时间 (s) |
|---|---:|
| `case001_lmbd3_storage` | 0.000 |
| `case002_pjm5_storage` | 0.000 |
| `case003_ieee14_storage` | 0.000 |

## UC/RTS-SCUC

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_2020_01_27_rts_scuc` | 0.843 |
| `case02_rts_gmlc_2020_02_09_rts_scuc` | 1.011 |
| `case03_rts_gmlc_2020_03_05_rts_scuc` | 0.646 |
| `case04_rts_gmlc_2020_04_03_rts_scuc` | 0.818 |
| `case05_rts_gmlc_2020_05_05_rts_scuc` | 0.744 |
| `case06_rts_gmlc_2020_06_09_rts_scuc` | 0.828 |
| `case07_rts_gmlc_2020_07_06_rts_scuc` | 0.870 |
| `case08_rts_gmlc_2020_08_12_rts_scuc` | 1.136 |
| `case09_rts_gmlc_2020_09_20_rts_scuc` | 0.693 |
| `case10_rts_gmlc_2020_10_27_rts_scuc` | 0.703 |
| `case11_rts_gmlc_2020_11_25_rts_scuc` | 0.762 |
| `case12_rts_gmlc_2020_12_23_rts_scuc` | 0.908 |

## UC/SCUC

| 案例 | 时间 (s) |
|---|---:|
| `case01_ieee39_scuc` | 0.461 |
| `case02_ieee57_scuc` | 1.386 |
| `case03_case60_scuc` | 0.479 |
| `case04_lmbd3_scuc` | 0.009 |
| `case05_pjm5_scuc` | 0.030 |
| `case06_ieee14_scuc` | 0.024 |
| `case07_ieee24_scuc` | 5.035 |
| `case08_as30_scuc` | 0.282 |
| `case09_ieee30_scuc` | 0.064 |
| `case10_ieee73_scuc` | 400.0 |
| `case11_pegase89_scuc` | 9.116 |
| `case12_ieee118_scuc` | 1.034 |
| `case13_ieeedtc162_scuc` | 1.258 |
| `case14_goc179_scuc` | 0.442 |
| `case15_snem197_scuc` | 0.238 |
| `case16_activ200_scuc` | 2.388 |
| `case17_pserc240_scuc` | 42.18 |
| `case18_ieee300_scuc` | 5.535 |
| `case19_goc500_scuc` | 43.04 |
| `case20_sdet588_scuc` | 31.37 |
| `case21_goc793_scuc` | 543.4 |
| `case22_pegase1354_scuc` | 67.73 |
| `case23_snem1803_scuc` | 474.2 |
| `case24_rte1888_scuc` | 58.69 |
| `case26_goc2000_scuc` | 难求解 |
| `case34_rte2848_scuc` | 92.64 |
| `case36_rte2868_scuc` | 253.6 |
| `case37_pegase2869_scuc` | 250.7 |
| `case39_goc3022_scuc` | 难求解 |
| `case42_goc3970_scuc` | 难求解 |
| `case44_goc4601_scuc` | 难求解 |
| `case48_goc4917_scuc` | 难求解 |
| `case49_epigrids5658_scuc` | 难求解 |
| `case50_rte6468_scuc` | 难求解 |
| `case51_rte6470_scuc` | 难求解 |
| `case52_rte6495_scuc` | 难求解 |
| `case53_rte6515_scuc` | 难求解 |
| `case54_epigrids7336_scuc` | 难求解 |
| `case55_pegase8387_scuc` | 难求解 |
| `case56_pegase9241_scuc` | 难求解 |
| `case57_goc9591_scuc` | 难求解 |
| `case58_goc10000_scuc` | 难求解 |
| `case59_epigrids10192_scuc` | 难求解 |
| `case60_goc10480_scuc` | 难求解 |
| `case61_pegase13659_scuc` | 难求解 |
| `case62_goc19402_scuc` | 难求解 |
| `case63_epigrids20758_scuc` | 难求解 |
| `case64_goc24464_scuc` | 难求解 |
| `case65_goc30000_scuc` | 难求解 |
| `case66_epigrids78484_scuc` | 难求解 |

## UC/SYSTEM-UC

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_2020_01_27_uc` | 1.703 |
| `case02_rts_gmlc_2020_02_09_uc` | 4.482 |
| `case03_rts_gmlc_2020_03_05_uc` | 3.113 |
| `case04_rts_gmlc_2020_04_03_uc` | 3.146 |
| `case05_rts_gmlc_2020_05_05_uc` | 1.669 |
| `case06_rts_gmlc_2020_06_09_uc` | 0.897 |
| `case07_rts_gmlc_2020_07_06_uc` | 1.516 |
| `case08_rts_gmlc_2020_08_12_uc` | 1.490 |
| `case09_rts_gmlc_2020_09_20_uc` | 1.953 |
| `case10_rts_gmlc_2020_10_27_uc` | 2.222 |
| `case11_rts_gmlc_2020_11_25_uc` | 2.370 |
| `case12_rts_gmlc_2020_12_23_uc` | 2.255 |
| `case13_ca_2014_09_01_reserves_0_uc` | 2.509 |
| `case14_ca_2014_09_01_reserves_1_uc` | 4.366 |
| `case15_ca_2014_09_01_reserves_3_uc` | 12.55 |
| `case16_ca_2014_09_01_reserves_5_uc` | 11.09 |
| `case17_ca_2014_12_01_reserves_0_uc` | 3.323 |
| `case18_ca_2014_12_01_reserves_1_uc` | 5.817 |
| `case19_ca_2014_12_01_reserves_3_uc` | 4.425 |
| `case20_ca_2014_12_01_reserves_5_uc` | 3.558 |
| `case21_ca_2015_03_01_reserves_0_uc` | 3.475 |
| `case22_ca_2015_03_01_reserves_1_uc` | 3.961 |
| `case23_ca_2015_03_01_reserves_3_uc` | 4.315 |
| `case24_ca_2015_03_01_reserves_5_uc` | 4.258 |
| `case25_ca_2015_06_01_reserves_0_uc` | 3.337 |
| `case26_ca_2015_06_01_reserves_1_uc` | 6.249 |
| `case27_ca_2015_06_01_reserves_3_uc` | 3.280 |
| `case28_ca_2015_06_01_reserves_5_uc` | 3.431 |
| `case29_ca_scenario400_reserves_0_uc` | 3.894 |
| `case30_ca_scenario400_reserves_1_uc` | 3.473 |
| `case31_ca_scenario400_reserves_3_uc` | 11.74 |
| `case32_ca_scenario400_reserves_5_uc` | 5.462 |
| `case33_ferc_2015_01_01_hw_uc` | 50.28 |
| `case34_ferc_2015_01_01_lw_uc` | 61.40 |
| `case35_ferc_2015_02_01_hw_uc` | 46.18 |
| `case36_ferc_2015_02_01_lw_uc` | 53.06 |
| `case37_ferc_2015_03_01_hw_uc` | 26.20 |
| `case38_ferc_2015_03_01_lw_uc` | 24.71 |
| `case39_ferc_2015_04_01_hw_uc` | 54.39 |
| `case40_ferc_2015_04_01_lw_uc` | 24.41 |
| `case41_ferc_2015_05_01_hw_uc` | 24.08 |
| `case42_ferc_2015_05_01_lw_uc` | 25.41 |
| `case43_ferc_2015_06_01_hw_uc` | 23.85 |
| `case44_ferc_2015_06_01_lw_uc` | 49.80 |
| `case45_ferc_2015_07_01_hw_uc` | 50.62 |
| `case46_ferc_2015_07_01_lw_uc` | 22.39 |
| `case47_ferc_2015_08_01_hw_uc` | 23.73 |
| `case48_ferc_2015_08_01_lw_uc` | 26.90 |
| `case49_ferc_2015_09_01_hw_uc` | 45.12 |
| `case50_ferc_2015_09_01_lw_uc` | 47.41 |
| `case51_ferc_2015_10_01_hw_uc` | 23.01 |
| `case52_ferc_2015_10_01_lw_uc` | 22.04 |
| `case53_ferc_2015_11_02_hw_uc` | 31.97 |
| `case54_ferc_2015_11_02_lw_uc` | 26.66 |
| `case55_ferc_2015_12_01_hw_uc` | 38.05 |
| `case56_ferc_2015_12_01_lw_uc` | 43.13 |
