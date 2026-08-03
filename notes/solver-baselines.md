# Solver Baselines Log

Record reproducible runs here (Matlab first; Python later).

## Environment

| Item | Value |
|------|-------|
| Machine | |
| MATLAB version | *(not found on PATH in setup machine)* |
| MATPOWER path | `matlab/matpower` |
| MOST path | `matlab/most` |
| PGLib path | `matlab/pglib-opf` |
| MILP solver | Gurobi / CPLEX / other: |
| NLP solver | MIPS / IPOPT / other: |
| Date | |

## AC-OPF runs

| Timestamp | Case | Solver | Obj | Status | Time (s) | Max violation | Notes |
|-----------|------|--------|-----|--------|----------|---------------|-------|
| | | | | | | | |

## UC / MOST runs

| Timestamp | Example | Solver | Obj | Status | Time (s) | MIP gap | Notes |
|-----------|---------|--------|-----|--------|----------|---------|-------|
| | | | | | | | |

## PGLib reference (TYP, AC, from BASELINE.md)

| Case | AC ($/h) | QC gap % |
|------|----------|----------|
| pglib_opf_case14_ieee | 2.1781e+03 | 0.11 |
| pglib_opf_case30_ieee | 8.2085e+03 | 18.81 |
| pglib_opf_case118_ieee | 9.7214e+04 | 0.79 |
| pglib_opf_case5_pjm | 1.7552e+04 | 14.55 |

## Smoke-test snippets (Matlab)

```matlab
%% --- AC-OPF smoke ---
cd('/path/to/mat-py/matlab/matpower');
install_matpower;   % or add paths per README
addpath(genpath('../pglib-opf'));

r = runopf('case14');
r = runopf('pglib_opf_case14_ieee');
disp(r.f);          % objective

%% --- MOST smoke (needs MATPOWER on path + MILP solver) ---
cd('/path/to/mat-py/matlab/most/examples');
most_ex1_ed;
% most_ex6_uc;    % after Gurobi/CPLEX configured
```
