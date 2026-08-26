# skills 所用论文

本目录每条 `SKILL.md` 对应一篇论文：文首题录即算法来源。下表按文件夹列出，共 **14** 篇。

题录以各 `SKILL.md` 文首为准；作者名、期刊、卷期、DOI 在文首不完整或与正式发表不一致时，按正式发表信息补全。

---

## constraint-screening（求解前筛热稳）

| # | Skill | 工具 | 论文 |
|---|-------|------|------|
| 1 | [`zhai-2010-inactive`](constraint-screening/zhai-2010-inactive/SKILL.md) | `screen_inactive_thermal_zhai` | Qiaozhu Zhai, Xiaohong Guan, Jinghui Cheng, Hongyu Wu. *Fast Identification of Inactive Security Constraints in SCUC Problems.* IEEE Trans. Power Syst., 25(2), 2010. |
| 2 | [`ding-2020-redundant-uncertainty`](constraint-screening/ding-2020-redundant-uncertainty/SKILL.md) | `screen_redundant_thermal_ding` | Tao Ding, Cheng Li, Fangxing Li, Tianen Chen, Rui Bo. *Fast identifying redundant security constraints in SCUC in the presence of uncertainties.* IET Gener. Transm. Distrib., 14(20), 2020. |
| 3 | [`ardakani-2015-umbrella`](constraint-screening/ardakani-2015-umbrella/SKILL.md) | `screen_umbrella_pucd` | Ali Jahanbani Ardakani, François Bouffard. *Acceleration of Umbrella Constraint Discovery in Generation Scheduling Problems.* IEEE Trans. Power Syst., 30(4), 2015. |
| 4 | [`porras-2021-cost-driven`](constraint-screening/porras-2021-cost-driven/SKILL.md) | `screen_cost_driven_porras` | Álvaro Porras, Salvador Pineda, Juan M. Morales, Asunción Jiménez-Cordero. *Cost-driven Screening of Network Constraints for the Unit Commitment Problem.* IEEE Trans. Power Syst., 2023. [arXiv:2104.05746](https://arxiv.org/abs/2104.05746) |
| 5 | [`awadalla-2023-tight-compact`](constraint-screening/awadalla-2023-tight-compact/SKILL.md) | `screen_tight_compact_awadalla` | Mohamed Awadalla, François Bouffard. *Tight and Compact Data-Driven Linear Relaxations for Constraint Screening in Unit Commitment.* IEEE Trans. Energy Markets, Policy and Regulation, 2024 (online 2023). |
| 6 | [`he-2025-vertex-guided`](constraint-screening/he-2025-vertex-guided/SKILL.md) | `screen_vertex_guided_he2025` | Xuan He, Yuxin Pan, Yize Chen, Danny H.K. Tsang. *Vertex-Guided Redundant Constraints Identification for Unit Commitment.* [arXiv:2507.09280](https://arxiv.org/abs/2507.09280), 2025. |
| 7 | [`he-2023-multi-interval`](constraint-screening/he-2023-multi-interval/SKILL.md) | `screen_multi_interval_he2023` | Xuan He, Jiayu Tian, Yufan Zhang, Honglin Wen, Yize Chen. *Fast Constraint Screening for Multi-Interval Unit Commitment.* [arXiv:2309.05894](https://arxiv.org/abs/2309.05894), 2023. |
| 8 | [`he-2026-screening-uncertainty`](constraint-screening/he-2026-screening-uncertainty/SKILL.md) | `screen_uncertainty_he2026` | Xuan He, Honglin Wen, Yufan Zhang, Yize Chen, Danny H.K. Tsang. *Modeling and tackling unit commitment constraint screening under uncertainty.* Applied Energy, 2026. Preprint [arXiv:2408.05185](https://arxiv.org/abs/2408.05185). |

## iterative-enforcement（松弛先解，SFT 再加割）

| # | Skill | 工具 | 论文 |
|---|-------|------|------|
| 9 | [`holzer-2024-fast-sft`](iterative-enforcement/holzer-2024-fast-sft/SKILL.md) | `sft_lodf_holzer` | J. T. Holzer, Y. Chen, Z. Wu, C. Pan, A. Veeramany. *Fast Simultaneous Feasibility Test for Security Constrained Unit Commitment.* IEEE Trans. Power Syst., 39(1), 1068–1078, 2024. [doi:10.1109/TPWRS.2023.3265269](https://doi.org/10.1109/TPWRS.2023.3265269) |
| 10 | [`tejada-2018-lodf`](iterative-enforcement/tejada-2018-lodf/SKILL.md) | `select_all_violations_tejada` | Diego A. Tejada-Arango, Pedro Sánchez-Martín, Andres Ramos. *Security Constrained Unit Commitment Using Line Outage Distribution Factors.* IEEE Trans. Power Syst., 33(1), 2018. |
| 11 | [`xavier-2019-filter`](iterative-enforcement/xavier-2019-filter/SKILL.md) | `filter_transmission_constraints_xavier` | Alinson S. Xavier, Feng Qiu, Fengyu Wang, Prakash R. Thimmapuram. *Transmission Constraint Filtering in Large-Scale Security-Constrained Unit Commitment.* IEEE Trans. Power Syst., 34(3), 2457–2460, 2019 (PES Letters). [doi:10.1109/TPWRS.2019.2892620](https://doi.org/10.1109/TPWRS.2019.2892620) |
| 12 | [`chen-2016-miso`](iterative-enforcement/chen-2016-miso/SKILL.md) | `select_watchlist_then_sft_chen` | Yonghong Chen, Aaron Casto, Fengyu Wang, Qun Zhou Wang, Xing Wang, Jie Wan. *Improving Large-Scale Day-Ahead Security Constrained Unit Commitment Performance.* IEEE Trans. Power Syst., 31(6), 2016. |
| 13 | [`castelli-2024-three-approaches`](iterative-enforcement/castelli-2024-three-approaches/SKILL.md) | `lazy_thermal_from_incumbent_castelli` | A. F. Castelli, I. Harjunkoski, J. Poland, M. Giuntoli, E. Martelli, I. E. Grossmann. *Solving the security constrained unit commitment problem: Three novel approaches.* Int. J. Electr. Power Energy Syst., 162, 110213, 2024. [doi:10.1016/j.ijepes.2024.110213](https://doi.org/10.1016/j.ijepes.2024.110213) |

## decomposition（主问题 UC + 事故可行割）

| # | Skill | 工具 | 论文 |
|---|-------|------|------|
| 14 | [`ramesh-2021-scuc-cnr`](decomposition/ramesh-2021-scuc-cnr/SKILL.md) | `benders_critical_cuts_ramesh` | Arun Venkatesh Ramesh, Xingpeng Li, Kory W. Hedman. *An Accelerated-Decomposition Approach for Security-Constrained Unit Commitment With Corrective Network Reconfiguration.* IEEE Trans. Power Syst., 37(2), 887–900, 2022 (online 2021). [doi:10.1109/TPWRS.2021.3098771](https://doi.org/10.1109/TPWRS.2021.3098771) · [arXiv:1912.01764](https://arxiv.org/abs/1912.01764) |

---

## 按年份

| 年 | 论文 | Skill |
|----|------|-------|
| 2010 | Zhai et al., IEEE TPWRS | `zhai-2010-inactive` |
| 2015 | Ardakani & Bouffard, IEEE TPWRS | `ardakani-2015-umbrella` |
| 2016 | Chen et al., IEEE TPWRS | `chen-2016-miso` |
| 2018 | Tejada-Arango et al., IEEE TPWRS | `tejada-2018-lodf` |
| 2019 | Xavier et al., IEEE TPWRS (PES Letters) | `xavier-2019-filter` |
| 2020 | Ding et al., IET GTD | `ding-2020-redundant-uncertainty` |
| 2021 | Ramesh, Li & Hedman, IEEE TPWRS（正式刊 2022） | `ramesh-2021-scuc-cnr` |
| 2023 | Porras et al., IEEE TPWRS | `porras-2021-cost-driven` |
| 2023 | He et al., arXiv:2309.05894 | `he-2023-multi-interval` |
| 2023/24 | Awadalla & Bouffard, IEEE TEMPR | `awadalla-2023-tight-compact` |
| 2024 | Holzer et al., IEEE TPWRS | `holzer-2024-fast-sft` |
| 2024 | Castelli et al., IJEPES | `castelli-2024-three-approaches` |
| 2025 | He et al., arXiv:2507.09280 | `he-2025-vertex-guided` |
| 2026 | He et al., Applied Energy | `he-2026-screening-uncertainty` |
