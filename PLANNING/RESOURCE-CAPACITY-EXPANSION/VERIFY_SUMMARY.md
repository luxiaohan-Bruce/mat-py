# VERIFY_SUMMARY resource_capacity_expansion

**base_problem**: `resource_capacity_expansion`

## Counts

| Metric | Value |
|--------|------:|
| GenX systems scanned | 11 |
| Eligible CEM cases built | 10 |
| Ineligible (not CEM) | 1 |
| Dual OPTIMAL + residual PASS | 10/10 |

## Ineligible systems

- `10_IEEE_9_bus_DC_OPF`: Pure DC-OPF example (fixed existing generation, DC_OPF=1, New_Build=0); not a capacity-expansion / CEM investment instance

## Case results

| case | result | status_py | status_mat | obj_py | obj_mat | obj_rel |
|------|--------|-----------|------------|--------|---------|--------|
| case01_1_three_zones_cem | PASS | OPTIMAL | OPTIMAL | 7918406831.01922 | 7918406831.01922 | 0.0 |
| case02_2_three_zones_w_electrolyzer_cem | PASS | OPTIMAL | OPTIMAL | 4010277656.0173225 | 4010277656.0173216 | 2.3780755304443453e-16 |
| case03_3_three_zones_w_co2_capture_cem | PASS | OPTIMAL | OPTIMAL | 7804500273.654718 | 7804500273.654721 | 3.665863090397432e-16 |
| case04_4_three_zones_w_policies_slack_cem | PASS | OPTIMAL | OPTIMAL | 7792260273.654717 | 7792260273.654719 | 2.4477475929046666e-16 |
| case05_5_three_zones_w_piecewise_fuel_cem | PASS | OPTIMAL | OPTIMAL | 7918406831.01922 | 7918406831.01922 | 0.0 |
| case06_6_three_zones_w_multistage_cem | PASS | OPTIMAL | OPTIMAL | 7918406831.01922 | 7918406831.019219 | 1.204376507494371e-16 |
| case07_7_three_zones_w_colocated_vre_storage_cem | PASS | OPTIMAL | OPTIMAL | 359004491652.1617 | 359004491652.16174 | 1.7001223569407805e-16 |
| case08_8_three_zones_w_colocated_vre_storage_electrolyzers_cem | PASS | OPTIMAL | OPTIMAL | 22045052573280.78 | 22045052573280.78 | 0.0 |
| case09_9_three_zones_w_retrofit_cem | PASS | OPTIMAL | OPTIMAL | 8149800778.7518425 | 8149800778.7518425 | 0.0 |
| case10_11_three_zones_w_allam_cycle_lox_cem | PASS | OPTIMAL | OPTIMAL | 6891805665.237079 | 6891805665.23708 | 1.3837800465220218e-16 |

summary: 10/10 PASS
