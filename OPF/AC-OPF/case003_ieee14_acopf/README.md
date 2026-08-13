# case003_ieee14_acopf

Exact polar AC-OPF pilot built from PGLib-OPF `pglib_opf_case14_ieee` (14
buses, 20 branches, 5 generators). This case exercises non-unity transformer
taps. Run `python3 solve.py`; the verified output is written to
`results/python_result.json`.

The global optimality certificate uses a `1e-3` relative gap; feasibility is
still independently checked at the package's `2e-4` MW/MVAr tolerance.

Classification: `base_problem=opf`, `problem=ac_opf`,
`power_flow=ac_exact`, `formulation=polar_ac_power_flow`, `security=none`.
