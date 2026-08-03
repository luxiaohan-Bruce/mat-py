# UC / SCUC Formulation Notes

> Phase 2 working notes. MOST = MATPOWER Optimal Scheduling Tool.

## Problem statement

**Unit Commitment (UC)**  
Decide which generators are on/off over a horizon and how much they produce, minimizing cost subject to demand, reserves, min up/down time, ramp rates, startup costs, etc.

**Security-Constrained UC (SCUC)**  
UC plus post-contingency (N-1, …) feasibility of network/dispatch.

- **Type:** large-scale MILP / MIQP (with DC network); MINLP if coupled with AC  
- **Why hard:** combinatorial on/off × multiperiod × contingencies/scenarios  

## MOST scope (important)

| Feature | MOST support |
|---------|----------------|
| Multi-period dispatch | Yes |
| Unit commitment (binary) | Yes |
| DC network model | Yes (primary) |
| Full AC network in scheduling | Not in current release (formulation general, implementation DC) |
| Contingencies / security | Yes (`contab`) |
| Stochastic / renewable scenarios | Yes (transition matrices, wind profiles) |
| Storage, ramp reserves | Yes |

Use **Gurobi or CPLEX** for MILP (recommended in MOST manual).

## Decision variables (typical)

| Symbol | Meaning |
|--------|---------|
| \(u_{i,t}\) | Commitment (on/off) of unit \(i\) in period \(t\) |
| \(v_{i,t}, w_{i,t}\) | Startup / shutdown indicators |
| \(p_{i,t}\) | Active power dispatch |
| (network) \(\theta\), line flows | DC power flow |
| reserves, storage SoC | if enabled |

## Constraint families

1. Power balance (zonal or DC OPF)  
2. Generation limits linked to \(u_{i,t}\)  
3. Logical: startup/shutdown vs commitment  
4. Min up / min down time  
5. Ramp up / ramp down  
6. Reserves (spinning, load-following, contingency)  
7. Contingency network constraints (SCUC)  
8. Scenario coupling / transition probabilities (stochastic UC)  

## Matlab entry points (MOST examples)

Path: `matlab/most/examples/`

```matlab
most_ex1_ed          % deterministic economic dispatch
most_ex2_dcopf       % DC OPF
most_ex3_dcopf_w_uc  % DC OPF + binary commitment
most_ex4_dcopf_ss    % secure / stochastic DC OPF
most_ex5_mpopf       % multiperiod OPF
most_ex6_uc          % deterministic multiperiod UC  ★
most_ex7_suc         % secure stochastic UC          ★★
```

Core API: `most(mdi)` after building MOST data struct via `loadmd`, profiles, `xgd`, `contab`, etc.

## Code map

| Item | Location |
|------|----------|
| Solver | `matlab/most/lib/most.m` |
| Tutorials | `matlab/most/examples/most_ex*.m` |
| Extra gen / storage data helpers | `matlab/most/lib/loadxgendata.m`, `addstorage.m`, … |
| Manual | online MOST-manual PDF; also `matlab/most/docs/` |

## Recommended learning ladder

1. Ex1 → Ex2 (continuous, single period)  
2. Ex3 (first binaries)  
3. Ex5 → Ex6 (multiperiod + full UC constraints)  
4. Ex7 (security + stochastic)  

## Run log (fill in)

| Example | Solver | Objective | Success? | Time (s) | Notes |
|---------|--------|-----------|----------|----------|-------|
| most_ex1_ed | | | | | |
| most_ex3_dcopf_w_uc | | | | | |
| most_ex6_uc | Gurobi/CPLEX | | | | |
| most_ex7_suc | Gurobi/CPLEX | | | | |

## Python port boundary (later)

- Recreate **MILP of Ex6/Ex7** (or a reduced SCUC), not full MOST framework.  
- Stack: Pyomo + Gurobi/CPLEX, or gurobipy directly.  
- Data: reuse MOST example tables / MATPOWER `mpc` structs via a small parser.  
