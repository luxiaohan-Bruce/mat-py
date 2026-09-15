# 优化求解加速 Skills

本目录收录 27 个论文方法 skill，分为约束处理 14 个、变量处理 13 个，主要面向电力系统机组组合（UC）、网络约束机组组合（NCUC）与安全约束机组组合（SCUC）。每个 skill 给出算法、适用条件、输入参数、核心代码、异常处理和调用示例；论文书目见 [PAPERS.md](PAPERS.md)。

## 目录结构

```text
skills/
  README.md
  PAPERS.md
  约束处理/
    constraint-screening/                 # 8 个
    iterative-enforcement/                # 5 个
    decomposition/                        # 1 个
  变量处理/
    variable-fixing-and-identification/    # 2 个
    time-aggregation/                     # 4 个
    unit-aggregation/                     # 7 个
```

每个方法以 `<分类>/<方法目录>/SKILL.md` 为入口，必要公式和实施条件集中在该文件中。代码可能只实现评分、分段、分簇或安全检查等局部步骤，完整接入范围以各 skill 的说明为准。

## 按问题类型选择

| 问题类型或主要瓶颈 | 对应方法 | 使用前提 |
|--------------------|----------|----------|
| 系统级确定性 UC，无网架 | Li 变量缩减、Pineda/Tao 时段方法、满足条件的机组聚合 | 原时间网格、运行成本、初始状态和机组动态约束明确。无线路模型时不使用热稳筛选。 |
| 固定拓扑的 DC-NCUC / 预防性 N-1 SCUC，线路约束很多 | 求解前约束筛选、迭代补约束、Ramesh 分解 | PTDF/LODF 与目标拓扑、事故集和出力政策一致；常规单线 LODF 不覆盖解列或多线同时开断。 |
| 鲁棒、机会约束或其他不确定性 UC | Ding、Awadalla、He 2026；多场景聚合可考虑 Yin | 区间、历史样本、高斯协方差或场景概率必须真实提供，且与待求解模型一致。 |
| 高时间分辨率 UC，时段数量大 | Pineda、Yu、Zhang、Tao | 需要完整细网格数据；Yu/Zhang 包含网络场景，聚合结果须恢复到原时段。 |
| 机组数量大、存在相同或相似机组 | Meus、Du、Knueven、Koller、Morales-España、Palmintier、Yin | 按物理参数、成本、网络位置和初始历史判断是否可聚合；精确与近似条件不同。 |
| UC 的分支搜索耗时高 | Li UPHB | 后端支持内部候选、伪成本、可靠性计数、全局界与强分支接入。 |
| 长期容量规划或热水风调度中的运行子问题 | Palmintier、Du、Meus、Yin，以及满足前提的其他 UC 方法 | 方法作用于 UC/调度部分，不自动处理投资、库容、排放或多阶段信息约束。 |

交流非线性 OPF、拓扑作为决策变量的 OTS、配网重构、PMU 布点等不能仅因属于电力优化就直接套用这些方法。部分线性热稳筛选可用于固定拓扑 DC-OPF/SCOPF 的对应子模型，但不能据此宣称覆盖完整 AC 或可变拓扑问题。

## 约束处理

### 求解前约束筛选（8 个）

目录：[constraint-screening/](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Zhai：解析筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/zhai-2010-inactive/SKILL.md) | 确定性 DC-UC / SCUC；点负荷、固定拓扑 | 容量盒与功率平衡的解析充分条件；不处理区间负荷。 |
| [Ardakani：P-UCD](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/ardakani-2015-umbrella/SKILL.md) | DC 发电调度、DC-SCOPF / SCUC 的线性热稳约束 | 判定相对容量盒与平衡已冗余的线路侧；不筛 UC 逻辑。 |
| [Ding：区间净负荷筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/ding-2020-redundant-uncertainty/SKILL.md) | 有净负荷上下界的多时段 DC-UC / SCUC | 用 FBBT 与连续背包覆盖给定区间；依赖有效出力/爬坡界。 |
| [Porras：费用驱动筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/porras-2021-cost-driven/SKILL.md) | 线性运行费用的确定性 DC-UC / SCUC | 需要可证明有效的费用上界；经验费用裕量本身不提供保证。 |
| [Awadalla：数据驱动多面体](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/awadalla-2023-tight-compact/SKILL.md) | 有多条同维历史节点净负荷样本的 DC-UC | 用 PCA 保留空间相关；保证仅针对构造的负荷集合。 |
| [He：多时段筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/he-2023-multi-interval/SKILL.md) | 至少两个时段、具有爬坡耦合的 DC-UC / SCUC | 全时域 LP 收紧线路范围；须与原模型启停/爬坡语义兼容。 |
| [He：顶点引导筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/he-2025-vertex-guided/SKILL.md) | 线路安全约束数量远多于连续出力变量的 DC-UC | 有效外包出力盒上批量判定；缺少收紧界时使用保守容量盒。 |
| [He：不确定性筛选](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/constraint-screening/he-2026-screening-uncertainty/SKILL.md) | 盒不确定集的鲁棒 UC，或高斯机会约束 UC | 必须提供对应扰动模型；机会约束模式需要协方差与风险水平。 |

### 迭代补充安全约束（5 个）

目录：[iterative-enforcement/](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Holzer：快速 SFT](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/holzer-2024-fast-sft/SKILL.md) | 需要反复检查单回线 N-1 的固定拓扑 DC-SCUC | 潮流与违反检测模块，可配合外循环或回调；解列事故需另行处理。 |
| [Tejada：全量加入违反](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/tejada-2018-lodf/SKILL.md) | 单回线 N-1 的预防性 DC-SCUC | LODF 扫描后加入全部新违反；最终仍需完整安全检查。 |
| [Xavier：每时段 top-k 过滤](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/xavier-2019-filter/SKILL.md) | 大规模单回线 N-1 DC-SCUC，需控制每轮约束增长 | 每线保留最严重事故，再选 top-k；循环至全量扫描无违反。 |
| [Chen：基态清单与 SFT](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/chen-2016-miso/SKILL.md) | 第一轮能容纳全部基态热稳的预防性 DC-SCUC | 先强制基态，后续加入事故违反；清单是当前实现的工程取法。 |
| [Castelli：整数解回调](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/iterative-enforcement/castelli-2024-three-approaches/SKILL.md) | 支持 lazy-constraint 回调的 DC-SCUC MIP | 当前入口是 M3：在整数候选上检查并补安全约束；不是缩短时域的 M4。 |

### 主问题与事故检查分解（1 个）

目录：[decomposition/](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/decomposition/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Ramesh：加速分解](%E7%BA%A6%E6%9D%9F%E5%A4%84%E7%90%86/decomposition/ramesh-2021-scuc-cnr/SKILL.md) | 可分离事故检查的 DC-SCUC；扩展场景为事故后网络重构 | 预防性版本保持同一套出力；CNR 仅适用于确有可开关支路与相应决策的模型。 |

## 变量处理

### 变量固定与变量辨识（2 个）

目录：[variable-fixing-and-identification/](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/variable-fixing-and-identification/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Li：对偶阈值变量缩减](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/variable-fixing-and-identification/li-variable-reduction/SKILL.md) | 二进制规模大的确定性 UC / DC-SCUC；线性或凸分段成本 | 启发式固定开停机，可能不可行或损失最优解；需保留撤回与原模型验证。 |
| [Li：定制混合分支 UPHB](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/variable-fixing-and-identification/li-hybrid-branching/SKILL.md) | 搜索节点或强分支开销大的 SCUC MIP | 需要修改 HiGHS 内部分支实现；普通参数设置不能复现完整策略。 |

### 时段聚合（4 个）

目录：[time-aggregation/](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/time-aggregation/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Pineda：时间自适应 UC](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/time-aggregation/pineda-time-adaptive-uc/SKILL.md) | 有连续高分辨率负荷/可再生预测的系统级 UC | 相邻 Ward 合并；原基础模型为单节点，网络和备用需要额外建模与恢复。 |
| [Yu：网络感知时间分辨率](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/time-aggregation/yu-network-flexible-time/SKILL.md) | 节点负荷变化与拥塞重要的高分辨率 DC-NCUC | 拥塞感知评分与动态规划；需要 PTDF、线路限额和原网格恢复。 |
| [Zhang：代表性调度点](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/time-aggregation/zhang-representative-scheduling-points/SKILL.md) | 希望减少开停机决策点、最终仍按原分辨率运行的 UC / DC-NCUC | 评分选点、单调状态分配、逐步释放原网格变量；修复不可省略。 |
| [Tao：成本导向时间划分](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/time-aggregation/tao-cost-oriented-time/SKILL.md) | 可重复调用日前 UC 与细网格调度的经济性优化 | 以成本反馈搜索边界；需要明确的日前/实时政策，搜索开销可能超过单次求解收益。 |

### 机组聚合（7 个）

目录：[unit-aggregation/](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/)

| Skill | 适用问题类型 | 方法与关键条件 |
|-------|--------------|----------------|
| [Meus：CUC 与逐机恢复](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/meus-clustered-uc-hybrid/SKILL.md) | 含大量相似热机、最终需要逐机调度的 UC / 规划运行子问题 | 先求簇在线数量，再解原逐机 UC；恢复可能失败，快启机保留自由。 |
| [Du：网络约束聚合 UC](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/du-network-clustered-uc/SKILL.md) | 必须保留真实机组节点的 DC-NCUC / 长期规划运行子问题 | 逐机连续潮流与簇启停耦合；NC-RCUC 是容量松弛，均需逐机恢复。 |
| [Knueven：相同机组精确聚合](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/knueven-identical-generators/SKILL.md) | 参数、成本和系统耦合系数相同的 UC 机组群 | 正常爬坡冗余时用紧 3-bin，否则用区间 EF；完整条件满足才有精确保证。 |
| [Koller：发电水平移位](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/koller-shifting-generation-levels/SKILL.md) | 同质机组、对称爬坡、最低出力启停、单一启动费用的 UC | 整除水平在论文条件下等价；非整除情况为近似，严格调度可用 Hybrid。 |
| [Morales-España：隐含灵活性](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/morales-espana-hidden-flexibility/SKILL.md) | 同质机组簇的爬坡、启停能力或备用较紧的 CUC | 有序槽位与逐槽约束抑制灵活性高估；不提供任意初态/最小开停的整体等价保证。 |
| [Palmintier：异质机组分层](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/palmintier-heterogeneous-clustering/SKILL.md) | 大量相似但参数不同的机组；长期规划与运行灵活性仿真 | 技术/热耗等分层与代表参数近似；原研究输电充分，网络调度需适配。 |
| [Yin：潮流驱动拆簇](%E5%8F%98%E9%87%8F%E5%A4%84%E7%90%86/unit-aggregation/yin-power-flow-clustering/SKILL.md) | 跨节点聚合误差明显的 DC-NCUC，含热水风与多场景调度 | 需电气距离和代表工况原 NCUC；随机模型恢复跨场景共同逐机启停。 |

## 适用性与结果含义

- 冗余筛选的保证建立在有效松弛、正确数据范围和数值判定上；费用驱动筛选还需要有效费用上界。
- 迭代加割和整数解回调需检查全部原安全约束，未出现于当前模型中的线路也不能漏检。
- 启发式固定、时间聚合和异质机组聚合可能损失可行性或最优性；只有恢复并通过原约束的调度才是原问题可行解。
- 精确聚合仅在相应 skill 列出的参数、动态约束、成本及身份恢复条件满足时成立。固定或近似子问题的 gap 不能直接当作原问题 gap。
