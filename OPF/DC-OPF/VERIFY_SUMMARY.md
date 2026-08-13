# VERIFY_SUMMARY — dc_opf_cases

**42 个已求解案例通过历史双端验收；29 个大网为仅数据 `skip`**（2026-08-12）

| 分层 | 数量 | 说明 |
|------|------|------|
| full | 23 | 双端 OPTIMAL + 残差 + 目标对齐 |
| relaxed | 19 | 双端求解通过 |
| skip | 29 | 仅数据构建（n_bus>3000） |

修复记录：MATLAB QP 的 `Q_ii=c2`（与 gurobipy 对齐）；零电抗支路用相角耦合。
