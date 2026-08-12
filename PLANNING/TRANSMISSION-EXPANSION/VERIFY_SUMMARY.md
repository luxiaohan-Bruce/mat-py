# VERIFY_SUMMARY — transmission_expansion_cases

**68/68 PASS**（2026-08-12）

| 分层 | 数量 | 说明 |
|------|------|------|
| full | 20 | 双端 OPTIMAL + 残差 + 目标对齐（含 2 个原生 TNEP） |
| relaxed | 3 | 双端 OPTIMAL（n_bus 500–793） |
| skip | 45 | 仅数据构建（n_bus>1000） |

## 原生 TNEP

| case | obj (py≈mat) | built | bal |
|------|-------------:|------:|-----|
| case001_case3_tnep | 5639.9679 | 1 | ~1e-14 |
| case002_case5_tnep | 17972.7898 | 2 | ~1e-14 |

目标双端 abs 差 ≤ 0.01 / rel ≤ 1e-7；功率平衡 / 潮流 / 热稳残差 ~1e-4 MW 量级（实测远更小）。

## 合成候选（PGLib）

- 仅沿现有走廊并联；`provenance=synthetic`
- 费用：`construction_cost = 1e6 * abs(x_existing)`
- 多数小网最优 `built=0`（投资成本相对运行成本偏高，属固定公式、非调参）
- `case013_pegase89_tep_syn` 建设 1 条并联回路，双端一致

## 模型要点

- Gurobi indicator：候选 z=1 潮流物理 / z=0 潮流为 0
- MATLAB `Q_ii=c2` 与 gurobipy 对齐
- Seed=1, Threads=1, MIPGap=1e-6
