---
name: zhang-representative-scheduling-points
description: >-
  根据需求极值、爬坡压力、小规模 m-point UC 和启停变化选择代表性调度点，重构高分辨率 UC 并逐步释放候选二进制变量修复可行性；用于保留原网格约束的时间缩减，不应只实现抽样和状态插值。
---

# Zhang：代表性调度点与原分辨率修复

Menghan Zhang, Zhifang Yang, Wei Lin, Juan Yu, Wei Dai, Ershun Du. *Enhancing economics of power systems through fast unit commitment with high time resolution.* Applied Energy, 281, 116051, 2021.

## 算法解读

先按需求极值、爬坡和小型 UC 的启停变化评分选出 RSP，再解代表点 UC。非 RSP 状态仅允许从左端状态向右端状态切换一次；最后在原网格逐步释放二进制变量修复。诊断用松弛只定位违反，最终解必须通过原硬约束。

先读 [关键建模关系](#关键建模关系)。

**整段算法：**

1. 从需求曲线给局部极值高分，按全日最大上升/下降需求归一化相邻变化。分别处理无上升、无下降及端点，避免除零；平坦连续区间用两端代表是工程约定。
2. 将原网格顺序分组，解 m-point UC：保留容量、网络平衡与爬坡，忽略启停费用和最小开停时间。末组不足 $m$ 时用实际长度；组边界条件须记录，不能把独立小问题拼成可行调度。
3. 由小问题出力计算最大逐机爬坡占比，由其状态变化给相邻两点加启停分数。总分按下文评分公式组合，降序选 RSP，再补首末点与超过最大间距的中间点。补点后报告实际 RSP 数。
4. 以真实 RSP 时间间隔重建缩减 UC，取得 RSP 处状态；不得将不等间隔按统一 $24/K$ 缩放。根据相邻 RSP 的负荷差分配非 RSP，仅允许从左状态向右状态切换一次。
5. 在原时间网格建立完整修复模型，初始释放状态发生变化的机组在变化两侧的 $u$，其余状态固定；出力及网络变量保持可调。
6. 原文用正罚系数松弛爬坡、网络上下限和节点平衡以定位违反。只有所有松弛为零（数值上小于基线容差）且原约束检查通过才接受。诊断松弛不能出现在最终可行性验收中。
7. 若有违反：扩展已释放变量到相邻时段；爬坡违反仅释放对应机组，网络或平衡违反释放该时段全部机组，再解修复模型。每轮集合必须扩大；最坏回到全部二进制自由的原 UC。
8. 所有求解共享总预算。全部自由后仍失败时返回原问题实际状态；有限罚系数没有保证“总能找到零松弛”，最终应以硬约束原模型校验/回退。

### 关键建模关系

#### 评分公式

已从 PDF 第 4 页恢复 MinerU 缺失的式 (16)：$S_{1,t}=a$ 当点为需求极值，否则 0。

对相邻需求增量，正增量除以全时域最大正增量 $\Delta L^{\uparrow}$，负增量绝对值除以最大下降量 $\Delta L^{\downarrow}$，得到 $F_t^{t\pm1}$。式 (19) 为 $S_{2,\mathrm{load}}=\frac{a}{2}(F_{\mathrm{forward}}+F_{\mathrm{backward}})$。

m-point UC 为式 (20)–(25)，不含启动/停机费用和最小开停约束，但含 DC 网络。由其逐机出力得到上升量/RU 或下降量/RD，式 (28) 是 $S_{2,\mathrm{unit}}=\frac{a}{2}(\max_i E_{i,\mathrm{forward}}+\max_i E_{i,\mathrm{backward}})$。式 (29) 取 $S_2=\max(S_{2,\mathrm{load}},S_{2,\mathrm{unit}})$，并非相加。任何机组相邻两点启停变化时，两侧点给 $S_3=a$。最终 $S_{\mathrm{total}}=S_1+S_2+S_3$。

论文未把全部边界、平坦极值、评分同分、最大补点间隔、组间初值写成唯一算法；入口给出的固定端点、稳定时间排序和显式配置属于工程补全。零爬坡机组有非零变化时标记违反/强制保留相关点，不以零比值掩盖异常。

#### 非 RSP 分配及已核对疑点

式 (33) 是 $x_j\le x_{j+1},\quad x_j\in\{0,1\}$，所以所有可行分配都是一段 0 接一段 1，可线性扫描切点。

PDF 第 7 页的式 (32) 确实印为

$$
\sum_j(1-x_j)(D_j-D_L)+x_j(D_j-D_R),
$$

**没有绝对值**。当端点负荷不同时，各点的右减左代价恒为 $D_L-D_R$，故字面优化会偏向全部分给同一端；这与“按负荷差分成两部分”的解释存在歧义。本方法保留 `paper-signed` 字面复现，同时提供明确命名的 `l1-adaptation`，使用 $\lvert D_j-D_L\rvert$ 与 $\lvert D_j-D_R\rvert$，不把工程修正写成论文定论。

#### 原网格修复

论文式 (34) 加运行费用与五组松弛罚项，式 (35) 保持容量、最小开停与启停费用等约束；式 (36)–(39) 分别定位上下爬坡、线路上下限、节点平衡违反。状态释放集合单调扩大：已有候选扩到前后原时段；局部爬坡只加对应机组；网络/平衡则加对应时段所有机组。

PDF 第 7 页式 (37) 的降坡项写成 $\mathrm{RD}\,u_{t-1}$，与式 (4) 的 $\mathrm{RD}\,u_t$ 不同，入口要求沿用原模型正确降坡约束。式 (39) 的单个非负平衡松弛只能覆盖一个失衡方向；诊断模型若需要双向失衡，应使用有明确符号的正负两变量并记录为工程适配。有限的大罚数不能替代最终硬约束可行性检查。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `monotone_assignment`
- **Description**: 根据需求极值、爬坡压力、小规模 m-point UC 和启停变化选择代表性调度点，重构高分辨率 UC 并逐步释放候选二进制变量修复可行性；用于保留原网格约束的时间缩减，不应只实现抽样和状态插值。
- **实现范围**: 给定左右分配代价后求一次切换的最优分组；不包含评分、RSP UC 或可行性修复。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 `(assignment,cost)`，0 表示分给左端、1 表示分给右端；列表不会从 1 反向切回 0。

**完整流程输出与保证：**

输出 RSP 集、各点分项评分、非 RSP 到端点映射、展开状态、历轮释放变量集合、原网格完整调度、残差/目标/有效界及分阶段耗时。方法覆盖网络 UC；原文未建立储能、备用的完整扩展，实际基线包含这些约束时恢复阶段必须保留。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入原高分辨率节点需求 MW、网络、机组成本/爬坡/最小开停与初始条件，目标 RSP 数、最大 RSP 间距、m-point 长度（论文 $m=6$）、总预算和基线容差。评分幅度 $a$ 可统一设 1（共同正比例缩放不改变排名）；最大间距、端点策略和同分规则须记录为实验设置。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "left_cost",
    "right_cost"
  ],
  "properties": {
    "left_cost": {
      "type": "array",
      "items": {
        "type": "number",
        "description": "分配给左端的代价；原式允许有符号值。"
      }
    },
    "right_cost": {
      "type": "array",
      "items": {
        "type": "number",
        "description": "分配给右端的代价；长度与 left_cost 相等。"
      }
    }
  },
  "additionalProperties": false
}
```

调用方必须记录 `paper-signed` 或 `l1-adaptation`。该函数只接收已算好的代价，两种代价定义不能混用。

---

## 3. 核心代码实现 (Python Implementation)

```python
from math import isfinite

def monotone_assignment(left_cost, right_cost):
    # 非 RSP 的左/右分配代价；允许原文有符号成本。
    if len(left_cost) != len(right_cost):
        raise ValueError("cost lengths differ")
    if any(not isfinite(v) for v in left_cost + right_cost):
        raise ValueError("non-finite cost")
    k = len(left_cost)
    value = sum(right_cost)  # 切点=0，全归右
    best, split = value, 0
    for j in range(k):
        value += left_cost[j] - right_cost[j]
        if value < best:
            best, split = value, j + 1
    return [0] * split + [1] * (k - split), best
```

入口必须记录代价模式：`paper-signed` 使用印刷式 (32) 的有符号差；`l1-adaptation` 使用绝对差，是工程变体。两者不能在实验中混名。这个枚举片段等价于单调二进制分组子问题，不含 UC 和修复求解。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 左右代价长度不同或有非有限值 | 抛出 ValueError。 |
| 评分分母为零或末尾小组不足 m 点 | 按实际数据处理零变化与短组，记录端点和同分规则。 |
| 修复仍有正松弛或原约束违反 | 扩大自由变量集合；最终回到完整硬约束 UC，不能用有限罚系数代替可行性证明。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 按 L1 工程变体，把需求 110、190 MW 分配给 100、200 MW 两个端点，状态至多切换一次。

**调用说明**: 使用 `monotone_assignment` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "monotone_assignment",
  "left_cost": [
    10,
    90
  ],
  "right_cost": [
    90,
    10
  ]
}
```

**Observation**: 返回 ([0,1],20)。这是明确标记的 L1 分组例子；恢复调度后仍需验证真实机组最小开停时间与爬坡。

### 验证与后续对照实验

小型验证：单调分组对照枚举；极值/零分母评分；原网格转移点两侧释放；机组爬坡违反只释放对应机组；平衡/线路违反释放全机组；无可行修复时逐步扩大到原 UC。检查原文与工程代价模式分别记录。

后续对照固定实例、硬件、线程、种子、总预算和停止标准，报告 $t_{\mathrm{selection}}+t_{\mathrm{RSP}}+t_{\mathrm{repair}}+t_{\mathrm{validation}}$、原问题目标/有效 gap、原约束残差、实际 RSP 数及每轮释放数。缩减 UC 的 gap 与罚函数目标不作为原 UC 最优性证明。价格指标仅在任务明确要求并完成原模型固定状态 ED 后计算。
