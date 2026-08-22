# 求解时间

共 790 例。小于 600s 写实测时间，超过 600s 记为**难求解**。

| 分类 | 案例数 | < 600s | 难求解 |
|---|---:|---:|---:|
| `DATACENTER/FLEXIBLE-DC-LOAD` | 3 | 3 | 0 |
| `DISTRIBUTION/DNR` | 2 | 2 | 0 |
| `MARKET/MARKET-CLEARING` | 56 | 56 | 0 |
| `MONITORING/PMU-PLACEMENT` | 18 | 10 | 8 |
| `OPF/AC-OPF` | 3 | 2 | 1 |
| `OPF/DC-OPF` | 54 | 44 | 10 |
| `OPF/LINEARIZED-SC-OPF` | 158 | 158 | 0 |
| `OPF/SC-AC-OPF` | 1 | 0 | 1 |
| `OTS/DC-OTS` | 44 | 37 | 7 |
| `OTS/LINEARIZED-SC-OTS` | 158 | 148 | 10 |
| `OTS/SC-OTS` | 35 | 18 | 17 |
| `PLANNING/GCEP-DC` | 2 | 2 | 0 |
| `PLANNING/RESOURCE-CAPACITY-EXPANSION` | 10 | 10 | 0 |
| `PLANNING/TRANSMISSION-EXPANSION` | 26 | 21 | 5 |
| `RESILIENCE/CONTROLLED-ISLANDING` | 6 | 3 | 3 |
| `RESILIENCE/NETWORK-INTERDICTION` | 63 | 16 | 47 |
| `RESILIENCE/OPTIMAL-POWER-SHUTOFF` | 2 | 2 | 0 |
| `RESILIENCE/POWER-RESTORATION` | 4 | 2 | 2 |
| `SCHEDULING/HYDROTHERMAL-SCHEDULING` | 32 | 27 | 5 |
| `UC/RTS-SCUC` | 12 | 12 | 0 |
| `UC/SCUC` | 45 | 22 | 23 |
| `UC/SYSTEM-UC` | 56 | 56 | 0 |
| **合计** | **790** | **651** | **139** |

## DATACENTER/FLEXIBLE-DC-LOAD

| 案例 | 时间 (s) |
|---|---:|
| `case004_ieee24_scuc_temporal` | 6.293 |
| `case005_ieee24_scuc_spatial_temporal` | 8.746 |
| `case006_ieee24_scuc_interruptible` | 1.587 |

## DISTRIBUTION/DNR

| 案例 | 时间 (s) |
|---|---:|
| `case03_mv_rural_dnr_ess` | 10.71 |
| `case06_lv_rural2_dnr_ess` | 7.822 |

## MARKET/MARKET-CLEARING

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_2020_01_27_market` | 6.192 |
| `case02_rts_gmlc_2020_02_09_market` | 6.516 |
| `case03_rts_gmlc_2020_03_05_market` | 6.978 |
| `case04_rts_gmlc_2020_04_03_market` | 6.557 |
| `case05_rts_gmlc_2020_05_05_market` | 6.297 |
| `case06_rts_gmlc_2020_06_09_market` | 6.534 |
| `case07_rts_gmlc_2020_07_06_market` | 6.477 |
| `case08_rts_gmlc_2020_08_12_market` | 6.447 |
| `case09_rts_gmlc_2020_09_20_market` | 6.408 |
| `case10_rts_gmlc_2020_10_27_market` | 6.525 |
| `case11_rts_gmlc_2020_11_25_market` | 6.117 |
| `case12_rts_gmlc_2020_12_23_market` | 6.571 |
| `case13_ca_2014_09_01_reserves_0_market` | 16.39 |
| `case14_ca_2014_09_01_reserves_1_market` | 16.04 |
| `case15_ca_2014_09_01_reserves_3_market` | 16.74 |
| `case16_ca_2014_09_01_reserves_5_market` | 16.48 |
| `case17_ca_2014_12_01_reserves_0_market` | 24.51 |
| `case18_ca_2014_12_01_reserves_1_market` | 16.15 |
| `case19_ca_2014_12_01_reserves_3_market` | 24.86 |
| `case20_ca_2014_12_01_reserves_5_market` | 16.46 |
| `case21_ca_2015_03_01_reserves_0_market` | 15.83 |
| `case22_ca_2015_03_01_reserves_1_market` | 16.45 |
| `case23_ca_2015_03_01_reserves_3_market` | 16.64 |
| `case24_ca_2015_03_01_reserves_5_market` | 16.20 |
| `case25_ca_2015_06_01_reserves_0_market` | 16.19 |
| `case26_ca_2015_06_01_reserves_1_market` | 15.62 |
| `case27_ca_2015_06_01_reserves_3_market` | 5.129 |
| `case28_ca_2015_06_01_reserves_5_market` | 5.151 |
| `case29_ca_scenario400_reserves_0_market` | 6.226 |
| `case30_ca_scenario400_reserves_1_market` | 6.096 |
| `case31_ca_scenario400_reserves_3_market` | 6.198 |
| `case32_ca_scenario400_reserves_5_market` | 6.099 |
| `case33_ferc_2015_01_01_hw_market` | 9.152 |
| `case34_ferc_2015_01_01_lw_market` | 5.954 |
| `case35_ferc_2015_02_01_hw_market` | 5.601 |
| `case36_ferc_2015_02_01_lw_market` | 6.034 |
| `case37_ferc_2015_03_01_hw_market` | 5.453 |
| `case38_ferc_2015_03_01_lw_market` | 5.442 |
| `case39_ferc_2015_04_01_hw_market` | 13.81 |
| `case40_ferc_2015_04_01_lw_market` | 12.99 |
| `case41_ferc_2015_05_01_hw_market` | 12.86 |
| `case42_ferc_2015_05_01_lw_market` | 21.66 |
| `case43_ferc_2015_06_01_hw_market` | 12.95 |
| `case44_ferc_2015_06_01_lw_market` | 12.87 |
| `case45_ferc_2015_07_01_hw_market` | 6.860 |
| `case46_ferc_2015_07_01_lw_market` | 13.11 |
| `case47_ferc_2015_08_01_hw_market` | 13.49 |
| `case48_ferc_2015_08_01_lw_market` | 13.30 |
| `case49_ferc_2015_09_01_hw_market` | 5.136 |
| `case50_ferc_2015_09_01_lw_market` | 5.918 |
| `case51_ferc_2015_10_01_hw_market` | 5.720 |
| `case52_ferc_2015_10_01_lw_market` | 5.322 |
| `case53_ferc_2015_11_02_hw_market` | 5.695 |
| `case54_ferc_2015_11_02_lw_market` | 5.920 |
| `case55_ferc_2015_12_01_hw_market` | 6.185 |
| `case56_ferc_2015_12_01_lw_market` | 5.606 |

## MONITORING/PMU-PLACEMENT

| 案例 | 时间 (s) |
|---|---:|
| `case026_case2000_goc_pmu` | 6.265 |
| `case031_case2742_goc_pmu` | 难求解 |
| `case037_case2869_pegase_pmu` | 8.357 |
| `case042_case3970_goc_pmu` | 难求解 |
| `case043_case4020_goc_pmu` | 221.5 |
| `case044_case4601_goc_pmu` | 96.88 |
| `case045_case4619_goc_pmu` | 213.9 |
| `case047_case4837_goc_pmu` | 难求解 |
| `case049_case5658_epigrids_pmu` | 难求解 |
| `case054_case7336_epigrids_pmu` | 10.42 |
| `case056_case9241_pegase_pmu` | 1.123 |
| `case057_case9591_goc_pmu` | 308.3 |
| `case059_case10192_epigrids_pmu` | 111.7 |
| `case060_case10480_goc_pmu` | 难求解 |
| `case062_case19402_goc_pmu` | 难求解 |
| `case063_case20758_epigrids_pmu` | 18.07 |
| `case064_case24464_goc_pmu` | 难求解 |
| `case066_case78484_epigrids_pmu` | 难求解 |

## OPF/AC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case002_pjm5_acopf` | 99.91 |
| `case003_ieee14_acopf` | 57.39 |
| `case004_ieee30_acopf` | 难求解 |

## OPF/DC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case005_ieee24_dc_ed` | 7.288 |
| `case006_ieee24_lp_ed` | 9.507 |
| `case007_as30_dc_ed` | 12.17 |
| `case008_as30_lp_ed` | 20.44 |
| `case009_ieee30_dc_ed` | 14.98 |
| `case010_epri39_dc_ed` | 6.954 |
| `case011_ieee57_dc_ed` | 9.321 |
| `case012_c60_dc_ed` | 12.21 |
| `case013_ieee73_dc_ed` | 8.635 |
| `case014_ieee73_lp_ed` | 11.61 |
| `case015_pegase89_dc_ed` | 21.65 |
| `case016_ieee118_dc_ed` | 12.32 |
| `case017_ieeedtc162_dc_ed` | 9.401 |
| `case019_snem197_dc_ed` | 7.426 |
| `case022_pserc240_dc_ed` | 17.40 |
| `case023_ieee300_dc_ed` | 13.48 |
| `case024_goc500_dc_ed` | 11.31 |
| `case027_goc793_dc_ed` | 5.418 |
| `case029_pegase1354_dc_ed` | 11.54 |
| `case030_snem1803_dc_ed` | 13.03 |
| `case031_rte1888_dc_ed` | 5.926 |
| `case032_rte1951_dc_ed` | 7.769 |
| `case033_goc2000_dc_ed` | 6.836 |
| `case035_goc2312_dc_ed` | 11.13 |
| `case037_2383wpk_dc_ed` | 5.235 |
| `case044_rte2848_dc_ed` | 10.57 |
| `case046_rte2868_dc_ed` | 12.07 |
| `case047_pegase2869_dc_ed` | 6.125 |
| `case049_goc3022_dc_ed` | 10.67 |
| `case053_goc3970_dc_ed` | 6.919 |
| `case055_goc4020_dc_ed` | 6.697 |
| `case057_goc4601_dc_ed` | 5.046 |
| `case059_goc4619_dc_ed` | 6.673 |
| `case061_sdet4661_dc_ed` | 1.086 |
| `case062_goc4837_dc_ed` | 8.226 |
| `case064_goc4917_dc_ed` | 9.754 |
| `case066_epigrids5658_dc_ed` | 2.443 |
| `case067_rte6468_dc_ed` | 8.555 |
| `case068_rte6470_dc_ed` | 12.44 |
| `case069_rte6495_dc_ed` | 12.13 |
| `case070_rte6515_dc_ed` | 11.71 |
| `case071_epigrids7336_dc_ed` | 难求解 |
| `case072_pegase8387_dc_ed` | 5.817 |
| `case073_pegase9241_dc_ed` | 12.86 |
| `case074_goc9591_dc_ed` | 难求解 |
| `case076_goc10000_dc_ed` | 难求解 |
| `case078_epigrids10192_dc_ed` | 难求解 |
| `case080_goc10480_dc_ed` | 难求解 |
| `case082_pegase13659_dc_ed` | 6.403 |
| `case083_goc19402_dc_ed` | 难求解 |
| `case085_epigrids20758_dc_ed` | 难求解 |
| `case087_goc24464_dc_ed` | 难求解 |
| `case089_goc30000_dc_ed` | 难求解 |
| `case091_epigrids78484_dc_ed` | 难求解 |

## OPF/LINEARIZED-SC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case001_t1s3_offline_network_01o_3_scenario_1_scacopf` | 5.604 |
| `case003_t1s3_offline_network_01o_3_scenario_2_scacopf` | 6.964 |
| `case005_t1s3_offline_network_01o_3_scenario_3_scacopf` | 6.451 |
| `case007_t1s3_offline_network_02o_3_scenario_1_scacopf` | 6.971 |
| `case009_t1s3_offline_network_02o_3_scenario_2_scacopf` | 6.675 |
| `case011_t1s3_offline_network_02o_3_scenario_3_scacopf` | 6.872 |
| `case013_t1s3_offline_network_03o_3_scenario_1_scacopf` | 11.36 |
| `case015_t1s3_offline_network_03o_3_scenario_2_scacopf` | 6.871 |
| `case017_t1s3_offline_network_03o_3_scenario_3_scacopf` | 7.269 |
| `case019_t1s3_offline_network_05o_3_scenario_1_scacopf` | 11.62 |
| `case021_t1s3_offline_network_05o_3_scenario_2_scacopf` | 8.896 |
| `case023_t1s3_offline_network_05o_3_scenario_3_scacopf` | 7.830 |
| `case025_t1s3_offline_network_06o_3_scenario_1_scacopf` | 6.212 |
| `case027_t1s3_offline_network_06o_3_scenario_2_scacopf` | 5.321 |
| `case029_t1s3_offline_network_06o_3_scenario_3_scacopf` | 5.636 |
| `case031_t1s3_offline_network_07o_3_scenario_1_scacopf` | 28.65 |
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
| `case079_t1s3_real_time_network_01r_3_scenario_1_scacopf` | 6.447 |
| `case081_t1s3_real_time_network_01r_3_scenario_2_scacopf` | 7.073 |
| `case083_t1s3_real_time_network_01r_3_scenario_3_scacopf` | 6.271 |
| `case085_t1s3_real_time_network_02r_3_scenario_1_scacopf` | 6.872 |
| `case087_t1s3_real_time_network_02r_3_scenario_2_scacopf` | 6.904 |
| `case089_network_02r_3_scenario_2_scenario_30_scacopf` | 6.793 |
| `case091_t1s3_real_time_network_02r_3_scenario_3_scacopf` | 7.180 |
| `case093_t1s3_real_time_network_03r_3_scenario_1_scacopf` | 7.026 |
| `case095_t1s3_real_time_network_03r_3_scenario_2_scacopf` | 7.598 |
| `case097_t1s3_real_time_network_03r_3_scenario_3_scacopf` | 12.17 |
| `case099_t1s3_real_time_network_05r_3_scenario_1_scacopf` | 10.70 |
| `case101_t1s3_real_time_network_05r_3_scenario_2_scacopf` | 7.605 |
| `case103_t1s3_real_time_network_05r_3_scenario_3_scacopf` | 11.00 |
| `case105_t1s3_real_time_network_06r_3_scenario_1_scacopf` | 5.246 |
| `case107_t1s3_real_time_network_06r_3_scenario_2_scacopf` | 6.943 |
| `case109_t1s3_real_time_network_06r_3_scenario_3_scacopf` | 5.964 |
| `case111_t1s3_real_time_network_07r_3_scenario_1_scacopf` | 30.21 |
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
| `case159_t1s3_offline_network_01o_3_scenario_1_scacopf` | 6.270 |
| `case161_t1s3_offline_network_01o_3_scenario_2_scacopf` | 6.922 |
| `case163_t1s3_offline_network_01o_3_scenario_3_scacopf` | 6.468 |
| `case165_t1s3_offline_network_02o_3_scenario_1_scacopf` | 6.678 |
| `case167_t1s3_offline_network_02o_3_scenario_2_scacopf` | 6.820 |
| `case169_t1s3_offline_network_02o_3_scenario_3_scacopf` | 12.33 |
| `case171_t1s3_offline_network_03o_3_scenario_1_scacopf` | 7.006 |
| `case173_t1s3_offline_network_03o_3_scenario_2_scacopf` | 6.845 |
| `case175_t1s3_offline_network_03o_3_scenario_3_scacopf` | 7.614 |
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
| `case237_t1s3_real_time_network_01r_3_scenario_1_scacopf` | 6.102 |
| `case239_t1s3_real_time_network_01r_3_scenario_2_scacopf` | 11.73 |
| `case241_t1s3_real_time_network_01r_3_scenario_3_scacopf` | 6.313 |
| `case243_t1s3_real_time_network_02r_3_scenario_1_scacopf` | 5.690 |
| `case245_t1s3_real_time_network_02r_3_scenario_2_scacopf` | 7.118 |
| `case247_network_02r_3_scenario_2_scenario_30_scacopf` | 7.082 |
| `case249_t1s3_real_time_network_02r_3_scenario_3_scacopf` | 7.396 |
| `case251_t1s3_real_time_network_03r_3_scenario_1_scacopf` | 7.085 |
| `case253_t1s3_real_time_network_03r_3_scenario_2_scacopf` | 7.032 |
| `case255_t1s3_real_time_network_03r_3_scenario_3_scacopf` | 10.99 |
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
| `case303_t1s3_real_time_network_70r_3_scenario_3_scacopf` | 34.09 |
| `case305_t1s3_real_time_network_81r_3_scenario_1_scacopf` | 20.00 |
| `case307_t1s3_real_time_network_81r_3_scenario_2_scacopf` | 22.95 |
| `case309_t1s3_real_time_network_81r_3_scenario_3_scacopf` | 30.10 |
| `case311_t1s3_real_time_network_84r_3_scenario_1_scacopf` | 58.29 |
| `case313_t1s3_real_time_network_84r_3_scenario_2_scacopf` | 53.97 |
| `case315_t1s3_real_time_network_84r_3_scenario_3_scacopf` | 56.95 |

## OPF/SC-AC-OPF

| 案例 | 时间 (s) |
|---|---:|
| `case002_pjm5_scacopf` | 难求解 |

## OTS/DC-OTS

| 案例 | 时间 (s) |
|---|---:|
| `case03_ieee118_dcots` | 6.717 |
| `case09_ieee57_dcots` | 16.70 |
| `case13_ieeedtc162_dcots` | 9.348 |
| `case14_goc179_dcots` | 难求解 |
| `case17_pserc240_dcots` | 108.2 |
| `case19_goc500_dcots` | 54.89 |
| `case20_sdet588_dcots` | 57.04 |
| `case21_goc793_dcots` | 26.79 |
| `case23_snem1803_dcots` | 44.82 |
| `case26_goc2000_dcots` | 7.282 |
| `case27_goc2312_dcots` | 7.614 |
| `case28_2383wpk_dcots` | 22.54 |
| `case31_goc2742_dcots` | 8.480 |
| `case35_sdet2853_dcots` | 98.85 |
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
| `case48_goc4917_dcots` | 5.804 |
| `case49_epigrids5658_dcots` | 8.023 |
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
| `case002_t1s3_offline_network_01o_3_scenario_1_scacots` | 50.06 |
| `case004_t1s3_offline_network_01o_3_scenario_2_scacots` | 5.029 |
| `case006_t1s3_offline_network_01o_3_scenario_3_scacots` | 6.718 |
| `case008_t1s3_offline_network_02o_3_scenario_1_scacots` | 10.53 |
| `case010_t1s3_offline_network_02o_3_scenario_2_scacots` | 6.700 |
| `case012_t1s3_offline_network_02o_3_scenario_3_scacots` | 8.463 |
| `case014_t1s3_offline_network_03o_3_scenario_1_scacots` | 40.39 |
| `case016_t1s3_offline_network_03o_3_scenario_2_scacots` | 32.94 |
| `case018_t1s3_offline_network_03o_3_scenario_3_scacots` | 31.96 |
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
| `case080_t1s3_real_time_network_01r_3_scenario_1_scacots` | 39.32 |
| `case082_t1s3_real_time_network_01r_3_scenario_2_scacots` | 39.30 |
| `case084_t1s3_real_time_network_01r_3_scenario_3_scacots` | 6.932 |
| `case086_t1s3_real_time_network_02r_3_scenario_1_scacots` | 10.68 |
| `case088_t1s3_real_time_network_02r_3_scenario_2_scacots` | 6.182 |
| `case090_network_02r_3_scenario_2_scenario_30_scacots` | 6.695 |
| `case092_t1s3_real_time_network_02r_3_scenario_3_scacots` | 9.151 |
| `case094_t1s3_real_time_network_03r_3_scenario_1_scacots` | 37.84 |
| `case096_t1s3_real_time_network_03r_3_scenario_2_scacots` | 29.66 |
| `case098_t1s3_real_time_network_03r_3_scenario_3_scacots` | 37.43 |
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
| `case160_t1s3_offline_network_01o_3_scenario_1_scacots` | 60.06 |
| `case162_t1s3_offline_network_01o_3_scenario_2_scacots` | 5.778 |
| `case164_t1s3_offline_network_01o_3_scenario_3_scacots` | 6.104 |
| `case166_t1s3_offline_network_02o_3_scenario_1_scacots` | 10.18 |
| `case168_t1s3_offline_network_02o_3_scenario_2_scacots` | 5.413 |
| `case170_t1s3_offline_network_02o_3_scenario_3_scacots` | 8.677 |
| `case172_t1s3_offline_network_03o_3_scenario_1_scacots` | 44.22 |
| `case174_t1s3_offline_network_03o_3_scenario_2_scacots` | 31.93 |
| `case176_t1s3_offline_network_03o_3_scenario_3_scacots` | 32.82 |
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
| `case238_t1s3_real_time_network_01r_3_scenario_1_scacots` | 37.19 |
| `case240_t1s3_real_time_network_01r_3_scenario_2_scacots` | 8.241 |
| `case242_t1s3_real_time_network_01r_3_scenario_3_scacots` | 6.718 |
| `case244_t1s3_real_time_network_02r_3_scenario_1_scacots` | 12.20 |
| `case246_t1s3_real_time_network_02r_3_scenario_2_scacots` | 7.991 |
| `case248_network_02r_3_scenario_2_scenario_30_scacots` | 7.154 |
| `case250_t1s3_real_time_network_02r_3_scenario_3_scacots` | 9.181 |
| `case252_t1s3_real_time_network_03r_3_scenario_1_scacots` | 50.12 |
| `case254_t1s3_real_time_network_03r_3_scenario_2_scacots` | 33.20 |
| `case256_t1s3_real_time_network_03r_3_scenario_3_scacots` | 30.96 |
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
| `case05_ieee73_scots` | 13.59 |
| `case06_activs200_scots` | 7.894 |
| `case11_c60_scots` | 12.52 |
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

## PLANNING/GCEP-DC

| 案例 | 时间 (s) |
|---|---:|
| `case002_tx123_y3_d2` | 10.45 |
| `case003_tx123_y7_d5` | 435.1 |

## PLANNING/RESOURCE-CAPACITY-EXPANSION

| 案例 | 时间 (s) |
|---|---:|
| `case01_1_three_zones_cem` | 17.17 |
| `case02_2_three_zones_w_electrolyzer_cem` | 79.71 |
| `case03_3_three_zones_w_co2_capture_cem` | 37.72 |
| `case04_4_three_zones_w_policies_slack_cem` | 31.28 |
| `case05_5_three_zones_w_piecewise_fuel_cem` | 17.92 |
| `case06_6_three_zones_w_multistage_cem` | 23.41 |
| `case07_7_three_zones_w_colocated_vre_storage_cem` | 5.240 |
| `case08_8_three_zones_w_colocated_vre_storage_electrolyzers_cem` | 7.021 |
| `case09_9_three_zones_w_retrofit_cem` | 42.10 |
| `case10_11_three_zones_w_allam_cycle_lox_cem` | 342.7 |

## PLANNING/TRANSMISSION-EXPANSION

| 案例 | 时间 (s) |
|---|---:|
| `case033_goc2742_tep_syn` | 6.883 |
| `case041_goc3022_tep_syn` | 1.314 |
| `case044_goc3970_tep_syn` | 9.482 |
| `case045_goc4020_tep_syn` | 13.88 |
| `case046_goc4601_tep_syn` | 6.382 |
| `case047_goc4619_tep_syn` | 27.30 |
| `case048_sdet4661_tep_syn` | 1.076 |
| `case049_goc4837_tep_syn` | 5.506 |
| `case050_goc4917_tep_syn` | 5.330 |
| `case051_epigrids5658_tep_syn` | 1.308 |
| `case052_rte6468_tep_syn` | 1.094 |
| `case053_rte6470_tep_syn` | 1.149 |
| `case054_rte6495_tep_syn` | 1.113 |
| `case055_rte6515_tep_syn` | 1.240 |
| `case056_epigrids7336_tep_syn` | 5.027 |
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
| `case002_GBnetwork_island` | 难求解 |
| `case003_EI_33_island` | 难求解 |
| `case073_npcc_island` | 难求解 |
| `case075_wecc_full_island` | 22.41 |
| `case076_wecc_gencls_island` | 24.33 |
| `case082_case118_ieee_island` | 4.754 |

## RESILIENCE/NETWORK-INTERDICTION

| 案例 | 时间 (s) |
|---|---:|
| `case005_ieee14_nk_int` | 11.92 |
| `case007_ieee24_nk_int` | 31.07 |
| `case008_as30_nk_int` | 65.32 |
| `case009_ieee30_nk_int` | 37.52 |
| `case010_epri39_nk_int` | 117.0 |
| `case011_ieee57_nk_int` | 25.48 |
| `case012_c60_nk_int` | 34.86 |
| `case013_ieee73_nk_int` | 99.48 |
| `case014_pegase89_nk_int` | 468.5 |
| `case015_ieee118_nk_int` | 450.6 |
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
| `case002_rts_gmlc_risk_rb25_ops` | 1.310 |
| `case003_rts_gmlc_risk_rb50_ops` | 5.335 |

## RESILIENCE/POWER-RESTORATION

| 案例 | 时间 (s) |
|---|---:|
| `case008_activsg200_scenario3_restore` | 7.382 |
| `case009_activsg200_scenario4_restore` | 难求解 |
| `case012_activsg200_scenario7_restore` | 6.638 |
| `case013_activsg200_scenario8_restore` | 难求解 |

## SCHEDULING/HYDROTHERMAL-SCHEDULING

| 案例 | 时间 (s) |
|---|---:|
| `case01_rcuc_100_50_1_w_ht` | 78.33 |
| `case02_rcuc_100_50_2_w_ht` | 67.97 |
| `case03_rcuc_150_75_1_w_ht` | 6.525 |
| `case04_rcuc_150_75_2_w_ht` | 160.9 |
| `case05_rcuc_200_100_1_w_ht` | 难求解 |
| `case06_rcuc_200_100_2_w_ht` | 6.597 |
| `case07_rcuc_20_10_1_w_ht` | 241.0 |
| `case08_rcuc_20_10_2_w_ht` | 5.855 |
| `case09_rcuc_50_20_1_w_ht` | 27.37 |
| `case10_rcuc_50_20_2_w_ht` | 8.632 |
| `case11_rcuc_75_35_1_w_ht` | 48.75 |
| `case12_rcuc_75_35_2_w_ht` | 9.271 |
| `case13_s46a_scen1_ht` | 27.24 |
| `case14_s46a_scen4_ht` | 120.0 |
| `case15_s46a_scen9_ht` | 难求解 |
| `case16_s46a_scen16_ht` | 难求解 |
| `case17_s46b_scen1_ht` | 13.39 |
| `case18_s46b_scen4_ht` | 11.80 |
| `case19_s46b_scen9_ht` | 56.15 |
| `case20_s46b_scen16_ht` | 187.3 |
| `case21_s46c_scen1_ht` | 5.151 |
| `case22_s46c_scen4_ht` | 49.47 |
| `case23_s46c_scen9_ht` | 305.9 |
| `case24_s46c_scen16_ht` | 难求解 |
| `case25_s46d_scen1_ht` | 12.72 |
| `case26_s46d_scen4_ht` | 8.666 |
| `case27_s46d_scen9_ht` | 46.45 |
| `case28_s46d_scen16_ht` | 217.6 |
| `case29_s46e_scen1_ht` | 14.53 |
| `case30_s46e_scen4_ht` | 54.94 |
| `case31_s46e_scen9_ht` | 306.3 |
| `case32_s46e_scen16_ht` | 难求解 |

## UC/RTS-SCUC

| 案例 | 时间 (s) |
|---|---:|
| `case01_rts_gmlc_2020_01_27_rts_scuc` | 6.506 |
| `case02_rts_gmlc_2020_02_09_rts_scuc` | 6.233 |
| `case03_rts_gmlc_2020_03_05_rts_scuc` | 6.048 |
| `case04_rts_gmlc_2020_04_03_rts_scuc` | 6.790 |
| `case05_rts_gmlc_2020_05_05_rts_scuc` | 6.264 |
| `case06_rts_gmlc_2020_06_09_rts_scuc` | 7.946 |
| `case07_rts_gmlc_2020_07_06_rts_scuc` | 8.149 |
| `case08_rts_gmlc_2020_08_12_rts_scuc` | 19.54 |
| `case09_rts_gmlc_2020_09_20_rts_scuc` | 5.667 |
| `case10_rts_gmlc_2020_10_27_rts_scuc` | 6.337 |
| `case11_rts_gmlc_2020_11_25_rts_scuc` | 6.392 |
| `case12_rts_gmlc_2020_12_23_rts_scuc` | 9.404 |

## UC/SCUC

| 案例 | 时间 (s) |
|---|---:|
| `case01_ieee39_scuc` | 5.882 |
| `case02_ieee57_scuc` | 8.659 |
| `case03_case60_scuc` | 7.292 |
| `case07_ieee24_scuc` | 5.035 |
| `case08_as30_scuc` | 8.932 |
| `case10_ieee73_scuc` | 400.0 |
| `case11_pegase89_scuc` | 9.116 |
| `case12_ieee118_scuc` | 43.76 |
| `case13_ieeedtc162_scuc` | 135.5 |
| `case15_snem197_scuc` | 12.79 |
| `case16_activ200_scuc` | 110.0 |
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
| `case01_rts_gmlc_2020_01_27_uc` | 41.49 |
| `case02_rts_gmlc_2020_02_09_uc` | 62.37 |
| `case03_rts_gmlc_2020_03_05_uc` | 25.52 |
| `case04_rts_gmlc_2020_04_03_uc` | 19.65 |
| `case05_rts_gmlc_2020_05_05_uc` | 13.87 |
| `case06_rts_gmlc_2020_06_09_uc` | 6.621 |
| `case07_rts_gmlc_2020_07_06_uc` | 6.699 |
| `case08_rts_gmlc_2020_08_12_uc` | 6.869 |
| `case09_rts_gmlc_2020_09_20_uc` | 28.11 |
| `case10_rts_gmlc_2020_10_27_uc` | 62.95 |
| `case11_rts_gmlc_2020_11_25_uc` | 34.22 |
| `case12_rts_gmlc_2020_12_23_uc` | 31.32 |
| `case13_ca_2014_09_01_reserves_0_uc` | 34.74 |
| `case14_ca_2014_09_01_reserves_1_uc` | 34.10 |
| `case15_ca_2014_09_01_reserves_3_uc` | 12.55 |
| `case16_ca_2014_09_01_reserves_5_uc` | 11.09 |
| `case17_ca_2014_12_01_reserves_0_uc` | 30.12 |
| `case18_ca_2014_12_01_reserves_1_uc` | 5.817 |
| `case19_ca_2014_12_01_reserves_3_uc` | 105.8 |
| `case20_ca_2014_12_01_reserves_5_uc` | 38.21 |
| `case21_ca_2015_03_01_reserves_0_uc` | 55.61 |
| `case22_ca_2015_03_01_reserves_1_uc` | 36.29 |
| `case23_ca_2015_03_01_reserves_3_uc` | 43.28 |
| `case24_ca_2015_03_01_reserves_5_uc` | 29.06 |
| `case25_ca_2015_06_01_reserves_0_uc` | 30.00 |
| `case26_ca_2015_06_01_reserves_1_uc` | 6.249 |
| `case27_ca_2015_06_01_reserves_3_uc` | 35.00 |
| `case28_ca_2015_06_01_reserves_5_uc` | 39.07 |
| `case29_ca_scenario400_reserves_0_uc` | 32.44 |
| `case30_ca_scenario400_reserves_1_uc` | 67.10 |
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
