# iterative-enforcement

不要事先枚举全部 `(线路, 时段, 事故)` 热稳。先解铜板或仅基态，SFT 扫违反，再把选中的割加回同一个 MIP。

1. `sft_lodf_holzer` — 求流引擎（基态 B 一次，事故 LODF）
2. `select_all_violations_tejada` — 违反全部加回（TSR）
3. `filter_transmission_constraints_xavier` — 每时段最多 k 条（默认 k=10）
4. `select_watchlist_then_sft_chen` — 第一轮强制全部基态
5. `lazy_thermal_from_incumbent_castelli` — lazy callback（默认 M3）
