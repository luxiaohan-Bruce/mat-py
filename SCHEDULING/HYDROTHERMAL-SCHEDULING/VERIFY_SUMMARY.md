# VERIFY_SUMMARY hydrothermal_scheduling

**Dual full-tier compare**: 9/9 PASS

Stored Python coverage after the classification audit: 29 `full`/`relaxed` cases have
validated feasible results. Three interrupted `relaxed` solves retain explicitly labelled
feasible incumbents (optimality is not claimed). The three 16-scenario cases without a stored
validated result are now `solve_tier=skip`, rather than being counted as solved.

| case | tier | ok | obj_py | obj_mat | bal_py | water_py |
|------|------|----|--------|---------|--------|----------|
| case07_rcuc_20_10_1_w_ht | full | True | 2829775.9363737307 | 2829536.0164085873 | 1.1368683772161603e-12 | 1.1368683772161603e-13 |
| case08_rcuc_20_10_2_w_ht | full | True | 2942218.996338688 | 2941921.1162414844 | 1.1368683772161603e-12 | 5.4569682106375694e-12 |
| case09_rcuc_50_20_1_w_ht | full | True | 10122885.02652079 | 10126229.668931853 | 2.7284841053187847e-11 | 3.1036506698001176e-11 |
| case10_rcuc_50_20_2_w_ht | full | True | 7707496.221534907 | 7709126.872510174 | 1.8189894035458565e-12 | 2.8421709430404007e-13 |
| case13_s46a_scen1_ht | full | True | -16071816.923833558 | -16073927.04839345 | 8.864773803907156e-09 | 1.248281478183344e-10 |
| case17_s46b_scen1_ht | full | True | -421963038.15966225 | -421963038.15966314 | 1.202205557326863e-10 | 1.1368683772161603e-11 |
| case21_s46c_scen1_ht | full | True | -410709226.63494486 | -410720143.55961186 | 9.99378357846581e-10 | 3.4378899727016687e-10 |
| case25_s46d_scen1_ht | full | True | -547491436.5826464 | -547491436.582646 | 3.841236662083247e-09 | 6.043876510375412e-11 |
| case29_s46e_scen1_ht | full | True | 19882944.557075005 | 19882746.91491427 | 1.0438094832920797e-11 | 7.275957614183426e-12 |


## Construction counts

| metric | value |
|--------|------:|
| constructed HT cases | 32 |
| full tier | 9 |
| relaxed tier | 20 |
| skip tier | 3 |
| eligible sources | 32 |
| ineligible (T-Ramp pure thermal) | 42 |

### Sources
- RCUC/HT-Ramp: 12 deterministic hydrothermal
- System_46buses A–E × {1,4,9,16}: 20 networked (deterministic / multi-scenario)
- RCUC/T-Ramp: 42 marked ineligible (no hydro)

### Dual full-tier pilots
All 9 full-tier cases: Python + MATLAB OPTIMAL (or accepted), residual power/water balance PASS.

### Model v1 notes
- Thermal: quadratic cost + binary commitment + min up/down + ramps
- Hydro: volume balance with cascade delay, linear P=k*release, terminal min volume, optional future water value
- RCUC: copperplate; 46-bus: networked DC with per-bus unserved energy
- Stochastic (n_scen>1): first-stage commitment, second-stage dispatch (expectation)
