# case002_pjm5_acopf

Exact polar AC-OPF pilot built from PGLib-OPF `pglib_opf_case5_pjm` (5 buses,
6 branches, 5 generators). Run `python3 solve.py`; the verified output is
written to `results/python_result.json`.

Classification: `base_problem=opf`, `problem=ac_opf`,
`power_flow=ac_exact`, `formulation=polar_ac_power_flow`, `security=none`.
