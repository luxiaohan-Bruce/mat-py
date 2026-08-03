# References — Power System Hard Optimization Problems

Local Matlab assets live under `../matlab/`. This file lists papers, manuals, and baselines for later Python conversion.

## Local code (cloned)

| Asset | Path | Git (approx) | Role |
|-------|------|--------------|------|
| MATPOWER | `matlab/matpower/` | 2026-07-31 | AC/DC PF & OPF |
| MOST | `matlab/most/` | 2026-07-23 | Multi-period UC / SCUC-style scheduling |
| PGLib-OPF | `matlab/pglib-opf/` | v23.07 (2023-07) | Hard AC-OPF benchmarks (MATPOWER format) |

Note: MATPOWER distribution also vendors a copy of MOST under `matlab/matpower/most/`. Prefer the standalone `matlab/most/` or follow MATPOWER install docs so versions stay consistent.

## Toolboxes & data

- MATPOWER: https://github.com/MATPOWER/matpower — https://matpower.org  
- MOST: https://github.com/MATPOWER/most  
- PGLib-OPF: https://github.com/power-grid-lib/pglib-opf  
- PSAT (optional): http://faraday1.ucd.ie/psat.html  

## Papers & reports

- Zimmerman, Murillo-Sánchez, Thomas. *MATPOWER: Steady-State Operations, Planning and Analysis Tools…* IEEE TPWRS, 2011.  
- Murillo-Sánchez et al. *Secure Planning and Operations…* (MOST) IEEE TSG, 2013.  
- PGLib-OPF Task Force report: https://arxiv.org/abs/1908.02788  
- Bienstock & Verma. *Strong NP-hardness of AC power flow feasibility*, 2019.  
- Tuncer & Kocuk. MISOCP / UC with AC power flows (research frontier).  

## Manuals

- MOST User’s Manual: https://matpower.org/docs/MOST-manual-1.3.1.pdf  
- MATPOWER docs: bundled under `matlab/matpower/docs/`  

## PGLib baseline (AC costs for small cases)

From `matlab/pglib-opf/BASELINE.md` (PowerModels.jl + IPOPT; TYP conditions):

| Case | AC cost ($/h) | Notes |
|------|---------------|--------|
| pglib_opf_case14_ieee | 2.1781e+03 | small, easy |
| pglib_opf_case30_ieee | 8.2085e+03 | larger QC/SOC gap (~18%) |
| pglib_opf_case118_ieee | 9.7214e+04 | medium standard |
| pglib_opf_case5_pjm | 1.7552e+04 | small but large relaxation gap |

Use these as order-of-magnitude checks when running MATPOWER (solver differences allowed).

## Future Python stack (not used yet)

- PYPOWER, pandapower, PyPSA  
- Pyomo / gurobipy / cplex for UC  
- PowerModels.jl (Julia) for OPF research baselines  
