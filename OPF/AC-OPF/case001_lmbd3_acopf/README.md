# case001_lmbd3_acopf

Exact polar AC-OPF pilot built from PGLib-OPF `pglib_opf_case3_lmbd` (3 buses,
3 branches, 3 generators). Run `python3 solve.py`; the verified output is
written to `results/python_result.json`.

Classification: `base_problem=opf`, `problem=ac_opf`,
`power_flow=ac_exact`, `formulation=polar_ac_power_flow`, `security=none`.
