# AC-OPF Formulation Notes

> Phase 1 working notes. Fill objective values after Matlab smoke runs.

## Problem statement

**AC Optimal Power Flow (AC-OPF)**  
Minimize generation cost (or losses) subject to AC power flow equations and engineering limits.

- **Type:** nonconvex nonlinear program (NLP)  
- **Hardness:** AC power flow feasibility is strongly NP-hard (Bienstock & Verma, 2019)  
- **Why hard:** nonconvex feasible set, multiple local minima, scale  

## Decision variables (typical polar form)

| Symbol | Meaning |
|--------|---------|
| \(V_i, \theta_i\) | Voltage magnitude and angle at bus \(i\) |
| \(P_g, Q_g\) | Active/reactive generation |
| (optional) transformer taps, shunts | discrete or continuous |

## Constraints (standard)

1. **Power balance** (Kirchhoff + AC injection equations) at each bus  
2. **Generator limits** \(P^{\min}_g \le P_g \le P^{\max}_g\), same for \(Q\)  
3. **Voltage limits** \(V^{\min}_i \le V_i \le V^{\max}_i\)  
4. **Thermal / apparent power limits** on branches  
5. **Reference angle** at slack bus  

## Objective

Usually quadratic (or piecewise-linear) generation cost:

\[
\min \sum_g \left( a_g P_g^2 + b_g P_g + c_g \right)
\]

## Matlab entry points

```matlab
% After install_matpower and path setup:
runopf('case14')                    % MATPOWER classic case
runopf('case118')

% PGLib (add matlab/pglib-opf to path):
runopf('pglib_opf_case14_ieee')
runopf('pglib_opf_case30_ieee')
runopf('pglib_opf_case118_ieee')
```

Options: `mpoption('opf.ac.solver', ...)` — MIPS (default pure Matlab), IPOPT, etc.

## Code map (MATPOWER)

| Item | Location |
|------|----------|
| OPF driver | `matlab/matpower/lib/` (`runopf`, `opf`, …) |
| Built-in cases | `matlab/matpower/data/` |
| PGLib cases | `matlab/pglib-opf/*.m` |
| Baseline costs | `matlab/pglib-opf/BASELINE.md` |

## Run log (fill in)

| Case | Solver | Objective | Success? | Time (s) | Notes |
|------|--------|-----------|----------|----------|-------|
| case14 | | | | | |
| pglib_opf_case14_ieee | | | | | baseline AC ≈ 2178 |
| pglib_opf_case30_ieee | | | | | baseline AC ≈ 8209 |
| pglib_opf_case118_ieee | | | | | baseline AC ≈ 97214 |
| (hard PGLib pick) | | | | | |

## Python port boundary (later)

- Port **model + selected cases**, not entire MATPOWER.  
- Compare: objective, feasibility (max violation), wall time.  
- Candidates: PYPOWER / pandapower / Pyomo+IPOPT.  
