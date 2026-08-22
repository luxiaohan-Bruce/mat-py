# constraint-screening

第一次 `optimize` 前判定直流热稳哪一侧可删。`drop=true` 的一侧不要写进模型。

递进（越后越依赖额外假设）：

1. `screen_inactive_thermal_zhai` — 容量盒 + 平衡的解析充分条件
2. `screen_redundant_thermal_ding` — 净负荷区间 + FBBT
3. `screen_umbrella_pucd` — P-UCD / umbrella
4. `screen_cost_driven_porras` — 再加费用上界
5. `screen_tight_compact_awadalla` — 要历史净负荷；没有就不要用
6. `screen_vertex_guided_he2025` — 外包盒 + Theorem 2 的 ω
7. `screen_multi_interval_he2023` — 筛 LP 含爬坡
8. `screen_uncertainty_he2026` — 机会约束/鲁棒 UC；确定性不要用
