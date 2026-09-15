---
name: pineda-time-adaptive-uc
description: >-
  使用相邻 Ward 聚类为 UC 生成不等长连续时段，并按真实时长重建成本、爬坡和最小开停约束；用于高分辨率调度的时间聚合及后续原时间网格验证。论文基础模型为单节点，不自动赋予网络或 N-1 可行性。
---

# Pineda：保持时序的时间自适应 UC

Salvador Pineda, Ricardo Fernández-Blanco, Juan Miguel Morales. *Time-Adaptive Unit Commitment.* 2019.

## 算法解读

每个原时段先是一簇，只允许合并相邻簇。对样本数 $n_i,n_j$ 和均值 $x_i,x_j$，使用 $\frac{2n_i n_j}{n_i+n_j}\lVert x_i-x_j\rVert^2$ 比较 Ward 合并代价。最后按真实时长重建 UC；聚类特征和物理 MW 数据分别保存。

把平稳区间合并、把快速变化区间保留为短时段，以有限的开停机决策数量描述负荷变化。论文固定为 24 个自适应时段，主要比较同规模下的运行经济性；在本仓库将高分辨率 $T_0$ 减到 $K$ 属于可测试的近似加速用法。

使用前阅读 [关键建模关系](#关键建模关系)。它不是随机打乱时间的普通聚类，也不是保留任意 24 个代表日。

**整段算法：**

1. 保存原网格和原始物理数据；特征归一化只用于计算距离，不能覆盖负荷 MW。记录多维特征权重及归一化参数。
2. 将每个原时段初始化为一簇，反复只合并相邻簇中 Ward 距离最小的一对，直到剩 $K$ 簇。同分固定选择最左一对，保留可重复性。
3. 计算 $h_t=(b_t-a_t)\,\Delta t$、负荷/预测的均值。非等间隔数据应另行使用时长加权 Ward 并标为扩展，不能直接用下方等间隔实现。
4. 以每段小时数乘运行费用；启动费用按开机事件记一次。用真实累计时长构造最小开停窗口、初始剩余开停要求和期末延续条件。爬坡按原文中点间距规则及下文所列限制处理。
5. 求聚合 UC 后，将开停状态逐段展开；在原网格上解调度/修复模型，恢复真实爬坡、需求、网络、备用和初始状态约束。原基线若禁止失负荷，不得添加软失负荷使验证通过。
6. 验证失败时，在出错区间增加边界并重解；仍失败或预算不足则回退原模型。任何修复改变开停状态都要记录，不能把展开操作本身当成可行性证明。
7. 需要原问题最优性证明时，把已验证解作为原模型热启动，取消聚合限制继续求解。

### 关键建模关系

#### 变长 UC

原文式 (3) 的成本是 $\sum_t(C_m p_t h_t+C_t^{\mathrm{start}})$，还包括失负荷成本。网络与备用未纳入论文基础模型；迁移到仓库时保留原模型的已有约束和硬失负荷政策。

式 (21)–(24) 将 $\mathrm{RU},\mathrm{RD},\mathrm{SU},\mathrm{SD}$ 各自乘以中点距离 $\widehat d_t=\frac{h_{t-1}+h_t}{2}$，再截到 $[P^{\min},P^{\max}]$。这是论文选定的平均功率模型，不是任意细网格的精确等价变换。尤其 $\max(P^{\min},\mathrm{RU}\,\widehat d_t)$ 可能比物理爬坡宽松；在严格原问题上不能据此给原约束放宽。首段与初始功率的时间间距由原网格确定，不能默认补一个一小时的虚构前段。

最小开机时间为 $\mathrm{UT}$ 小时时，从段 $t$ 起取最小 $\omega$ 使

$$
\sum_{j=t}^{t+\omega-1}h_j\ge\mathrm{UT}.
$$

启动时要求这些段全部在线；停机要求用 $\mathrm{DT}$ 类似构造。若剩余时域不足，则按基线的期末延续/滚动窗口约定处理。初始剩余时间使用 $\max(0,\mathrm{UT}-h_{\mathrm{on}})$ 或 $\max(0,\mathrm{DT}-h_{\mathrm{off}})$，只激活与初始状态对应的一种。

**PDF 核对**：第 4 页式 (14)、(15)、(18)、(27)、(30) 修复 MinerU 丢失的求和上界 $t+\omega-1$；式 (14) 的上界为初始强制在线段数，并非机组索引。该页在 $\mathrm{DT}_{\mathrm{initial}}$ 说明中也写了 $U_0$，与初始关机语义不一致，且将小时需求与 $N_T$ 混用。入口按物理含义使用关机指示与真实小时数，标为工程纠正，不宣称原文无此问题。

#### 从聚合解到可执行计划

论文 §IV 将机组分为基荷、中荷、峰荷：日前固定基荷状态与出力、中荷状态，实时允许中荷出力与峰荷启停调整。它不是“所有机组按聚合平均值重复”这一评价流程。

仓库加速测试应明示两种任务的区别：复现论文时执行该日前/实时政策；加速原 UC 时先展开状态，再在完整原问题恢复出力，失败则修复状态或作为 warm start。聚合最优值一般不是原 UC 的有效下界；修复成功只证明已得到原问题可行解。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `ward_blocks`
- **Description**: 使用相邻 Ward 聚类为 UC 生成不等长连续时段，并按真实时长重建成本、爬坡和最小开停约束；用于高分辨率调度的时间聚合及后续原时间网格验证。论文基础模型为单节点，不自动赋予网络或 N-1 可行性。
- **实现范围**: 等间隔输入的相邻 Ward 分段；不包含变时长 UC 建模或原网格恢复。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回按时间排序的半开区间列表 $[a_t,b_t)$，每个原时段恰好属于一段。

**完整流程输出与保证：**

输出：有序半开区间 $[a_t,b_t)$、原到聚合的映射、各段小时数和原单位均值、聚合模型解、恢复到原网格的完整调度、验证残差及总耗时。所有时段必须恰好覆盖一次。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入：连续且等间隔的原时间网格 `delta_hours`、原始负荷及可再生预测（MW）、用于聚类的归一化特征、目标时段数 $1\le K\le T_0$、机组成本与开停/爬坡/初始条件。最小开停时间以小时、爬坡以 MW/h、启动成本以每次事件计。不得从粗分辨率输入虚构细粒度数据。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "features",
    "k"
  ],
  "properties": {
    "features": {
      "type": "array",
      "items": {
        "type": "array",
        "items": {
          "type": "number",
          "description": "已归一化的特征值；维度和权重全时域一致。"
        },
        "minItems": 1
      },
      "description": "按原时间顺序排列的等间隔特征矩阵。",
      "minItems": 1
    },
    "k": {
      "type": "integer",
      "description": "目标时段数，不能超过原时段数。",
      "minimum": 1
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

```python
from math import isfinite

def ward_blocks(features, k):
    # features[t][j] 已归一化，等时间步；返回 [a,b)。
    n = len(features)
    if type(k) is not int or not 1 <= k <= n:
        raise ValueError("invalid number of blocks")
    dim = len(features[0])
    if not dim or any(len(x) != dim for x in features):
        raise ValueError("inconsistent feature dimension")
    if any(not isfinite(v) for x in features for v in x):
        raise ValueError("non-finite feature")
    blocks = [(i, i + 1, list(x)) for i, x in enumerate(features)]
    while len(blocks) > k:
        def distance(i):
            a, b, x = blocks[i]
            _, c, y = blocks[i + 1]
            ni, nj = b - a, c - b
            return 2 * ni * nj / (ni + nj) * sum(
                (u - v) ** 2 for u, v in zip(x, y))
        i = min(range(len(blocks) - 1), key=lambda j: (distance(j), j))
        a, b, x = blocks[i]
        _, c, y = blocks[i + 1]
        mean = [((b-a)*u + (c-b)*v)/(c-a) for u, v in zip(x, y)]
        blocks[i:i+2] = [(a, c, mean)]
    return [(a, b) for a, b, _ in blocks]
```

这是聚类核心，未包含 UC 求解器。输出边界必须用于原单位数据的聚合，不能把归一化质心直接填入 MW 平衡约束。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| k 越界、空特征维度、非有限值或维度不一致 | 抛出 ValueError；不生成聚合时段。 |
| 原网格不是等间隔 | 此片段不适用；使用显式时长加权扩展并记录方法变化。 |
| 展开后爬坡、最小开停或网络不可行 | 在违反区间增加边界并重求解，必要时在同一预算内回退原模型。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 把六个半小时时段的负荷 200、200、200、200、450、850 MW 合并为三段。

**调用说明**: 使用 `ward_blocks` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "ward_blocks",
  "features": [
    [
      200
    ],
    [
      200
    ],
    [
      200
    ],
    [
      200
    ],
    [
      450
    ],
    [
      850
    ]
  ],
  "k": 3
}
```

**Observation**: 得到 [0,4)、[4,5)、[5,6)，时长 2、0.5、0.5 h，物理均值 200、450、850 MW。总电量仍为 1050 MWh；能量守恒不证明原爬坡和网络可行。单特征例子使用统一原始尺度，不与其他单位特征混合。

### 验证与后续对照实验

另测 $K=T_0$、$K=1$、全常数、多维节点净负荷与最小开机时间跨段边界；测试平均负荷相同但内部有尖峰、使展开调度不可行的例子。连续窗口覆盖与能量守恒通过，并不代表爬坡和网络约束通过。

后续采用相同实例、硬件、线程、种子、预算和停止标准；报告聚类、模型建立、求解、全部修复及原网格验证的总耗时、原问题目标值/有效界、残差与变量数。分别列出聚合 UC 成本和真实网格成本，不将降低分辨率的近似目标与基线直接比较。
