---
name: yu-network-flexible-time
description: >-
  利用负荷变化、机组出力范围与 PTDF 拥塞影响构造区间代价，以动态规划选择连续聚合时段，并重建变时长 NCUC、恢复原网格调度；用于网络约束 UC 的近似加速，不能用区间平均潮流代替原网格可行性验证。
---

# Yu：考虑拥塞的灵活时间分辨率 NCUC

Zekuan Yu, Haiwang Zhong, Guangchun Ruan, Xinfei Yan. *Network-Constrained Unit Commitment With Flexible Temporal Resolution.* IEEE Transactions on Power Systems, 40(1), 2025.

## 算法解读

区间代价 $\lambda$ 结合总负荷变化、PTDF 正负机组组的可调范围与潜在拥塞。令 $\lambda_{a,b}$ 表示半开区间 $[a,b)$ 的代价，动态规划保持边界顺序，将前 $b$ 个原时段划成 $q$ 段：

$$
V(q,b)=\min_{q-1\le a<b}\left\{V(q-1,a)+\lambda_{a,b}\right\},\qquad V(0,0)=0.
$$

只使用负荷范围属于无拥塞评分示例，完整网络方法须按下文公式构造区间代价。当系统净负荷曲线相近而节点负荷分布变化会引发拥塞时，使用拥塞感知评分、动态规划分段、变时长模型及原时段恢复这四个步骤。具体公式见[关键建模关系](#关键建模关系)。

**整段算法：**

1. 解论文指定的辅助模型：将 UC 整数变量连续化、忽略网络约束，以所得发电计算线路潮流，识别各原时段潜在拥塞线。记录辅助 LP 耗时。预测拥塞集合只用于评分，不授权删除原网络约束。
2. 对每个候选连续区间计算下文给出的论文式 (6)–(8) 的 $\lambda$：总负荷范围、按 PTDF 正负分组的机组可调范围、拥塞引起的额外调节需求。仅用系统负荷范围是论文 M2 消融，不是完整 M1。
3. 用动态规划把 $T_0$ 个原时段划成恰好 $K$ 段，最小化 $\sum_t\lambda_t$。单点区间代价为零，所有边界保持顺序。
4. 构建变长 NCUC：平衡和网络用平均节点负荷；容量与上下备用考虑区间最大/最小负荷；保留区间内部最大相邻负荷增减量对应的爬坡备用要求。
5. 用原步长推导相邻段平均出力爬坡上限，以及启动/停机过程的平均出力上界；按累计小时确定最小开停窗口。不要只按聚合段数替换原 $T$。
6. 展开 $u$ 到原网格，再在完整原约束下求 ED。不可行时解允许调整相关开停状态的原网格修复 MIP；可使用原模型 warm start 回退。论文引用的纠正方法未在本文完整给出，不能捏造其代码；本步骤的修复 MIP 标为工程适配。
7. 只有通过原网格验证后才能比较成本。需证明最优性时解除聚合/固定，在原模型继续求解。

### 关键建模关系

#### 拥塞感知区间代价

固定一条上限方向拥塞线 $\ell$。按 PTDF 的正负划分机组为 $G_+$、$G_-$，以 $P^{\max}-P^{\min}$ 加权计算平均 PTDF $T_+$,$T_-$；同样的可调范围占比为 $\eta_+$,$\eta_-$（式 (4)、(8)）。对区间内所有有序时间对 $s<f$，计算

$$
\Delta D=D^f-D^s,\qquad
\Delta PF_l=-\sum_j PTDF_{lj}(D_j^f-D_j^s).
$$

式 (6) 的两个需求下界为

$$
A_+=\max_{s<f}\frac{T_-\Delta D+\Delta PF_l}{T_+-T_-},\quad
A_-=\max_{s<f}\frac{T_+\Delta D+\Delta PF_l}{T_+-T_-}.
$$

式 (7)：对所有候选拥塞线取最大，

$$
\lambda(S,F)=\frac{\max\{\max_{s<f}|\Delta D|,
\max_l A_+/\eta_+,\max_l A_-/\eta_-\}}{\max_{S\le\tau\le F}D^\tau}.
$$

无拥塞时仅保留第一项。方向必须按原式一致；下限方向先取负 PTDF，不能把上下两侧的符号混在一个评分中。正负组、分母退化在原文未给通用处理，入口将其列为不适用而非伪造公式。

附录式 (17)–(18) 将二维方框、平衡直线与拥塞半平面的交集化为条件 (6)。这些条件属于平均 PTDF 的两组简化模型，**不是逐机逐时段 NCUC 可行性的充分条件**。PDF 第 5 页已核对分式的正负号及归一化分母。

#### 变长约束的具体转换

正文 $d_t$ 是原时间步的数量，不是小时；真实长度为 $h_t=d_t\Delta t$。

- 运行费用乘 $h_t$，启停费用按事件计；平衡和 PTDF 行用区间均值。
- 式 (9c)/(9d) 用区间最大负荷、最小负荷检查在线容量范围；式 (9e)/(9f) 用区间内**相邻原时段**最大上升/下降需求检查在线爬坡能力。不能用总能量替代这些 MW 值。
- 式 (13)：$\overline{\mathrm{RU}}_t=\frac{d_{t-1}+d_t}{2}\mathrm{RU}\,\Delta t$；下降同理。
- 论文假设启动后的第一个原时段出力为 $P^{\min}$。式 (14)–(16) 可无歧义地计算为 $\overline{\mathrm{SU}}_t=\frac{1}{d_t}\sum_{j=0}^{d_t-1}\min(P^{\max},P^{\min}+j\,\mathrm{RU}\,\Delta t)$；$\overline{\mathrm{SD}}_t$ 用 $\mathrm{RD}$ 对称构造，并在停机约束中使用**前一段**的系数。若原模型启动界不同，重新由原界推导，不擅改为 $P^{\min}$。
- 式 (10) 的最小开停窗口是从当前段开始累计小时首次达到要求的段号；若时域不足，延续到末段，同时遵从基线跨日边界政策。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `optimal_blocks`
- **Description**: 利用负荷变化、机组出力范围与 PTDF 拥塞影响构造区间代价，以动态规划选择连续聚合时段，并重建变时长 NCUC、恢复原网格调度；用于网络约束 UC 的近似加速，不能用区间平均潮流代替原网格可行性验证。
- **实现范围**: 给定区间代价函数后求最优连续分段；不包含拥塞评分辅助 LP 或 NCUC。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 `(blocks,total_cost)`；没有合法的 K 段划分时抛出 ValueError。

**完整流程输出与保证：**

输出：区间代价、分段映射、聚合状态、原网格完整调度、修复情况、原问题残差/目标/有效界及耗时。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入：原网格节点负荷 MW、等间隔步长小时、机组母线与 $P^{\min},P^{\max}$、PTDF 和热稳限值、原 UC 约束与初始状态、目标段数 $K$、有效容差及总预算。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "n",
    "k",
    "segment_cost"
  ],
  "properties": {
    "n": {
      "type": "integer",
      "description": "原时段数。",
      "minimum": 1
    },
    "k": {
      "type": "integer",
      "description": "目标段数，1≤k≤n。",
      "minimum": 1
    },
    "segment_cost": {
      "description": "Python 可调用对象 segment_cost(a,b)，返回半开区间 [a,b) 的非负代价；正无穷表示禁用。不接受函数名称字符串替代真实函数。",
      "x-python-type": "Callable[[int, int], float]"
    }
  },
  "additionalProperties": false
}
```

`segment_cost` 是运行时绑定的 Python 函数，上述 `x-python-type` 是接口注解；普通 JSON 不能序列化函数。其返回值、时段边界及评分单位由调用方检查。

---

## 3. 核心代码实现 (Python Implementation)

```python
from math import inf, isnan

def optimal_blocks(n, k, segment_cost):
    # segment_cost(a,b): 0-based [a,b)，按论文构造；inf 表示不允许该段。
    if type(n) is not int or type(k) is not int or not 1 <= k <= n:
        raise ValueError("invalid horizon or number of blocks")
    costs = {}
    for a in range(n):
        for b in range(a + 1, n + 1):
            value = float(segment_cost(a, b))
            if isnan(value) or value < 0:
                raise ValueError("segment cost must be nonnegative")
            costs[a, b] = value
    dp = [[inf] * (n + 1) for _ in range(k + 1)]
    prev = [[None] * (n + 1) for _ in range(k + 1)]
    dp[0][0] = 0.0
    for q in range(1, k + 1):
        for b in range(q, n + 1):
            for a in range(q - 1, b):
                value = dp[q - 1][a] + costs[a, b]
                if value < dp[q][b]:
                    dp[q][b], prev[q][b] = value, a
    if dp[k][n] == inf:
        raise ValueError("no valid partition")
    blocks, b = [], n
    for q in range(k, 0, -1):
        a = prev[q][b]
        blocks.append((a, b))
        b = a
    return list(reversed(blocks)), dp[k][n]
```

该片段只求分段子问题，不求 NCUC。区间代价预计算后复杂度 $O(KT_0^2)$；实际评分可能更贵，计入预处理时间。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| n/k 非法或区间代价为 NaN/负值 | 抛出 ValueError。 |
| 所有候选路径都含禁用区间 | 返回 no valid partition；保留原分辨率。 |
| 拥塞评分公式分母无效或组为空 | 报告评分不适用；不要静默将拥塞项置零。 |

PTDF 正负组为空、分母近零或最大净需求非正时，式 (7) 不能直接计算。报告评分不适用；保留原分辨率，或明确采用不同评分的消融，不能静默把拥塞项置零。下限拥塞需反转该线路 PTDF 行与潮流方向再用同一推导。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 先用无拥塞的小型例子检验动态规划，再接入实际网络评分。

**调用说明**: 使用 `optimal_blocks` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```text
demand = [100, 1000, 1700, 2200, 2500]
cost = lambda a, b: (max(demand[a:b]) - min(demand[a:b])) / max(demand)
optimal_blocks(n=5, k=3, segment_cost=cost)
```

**Observation**: 返回区间 [0,1)、[1,2)、[2,5)，总代价 0.32。正式使用时替换为拥塞感知代价；保持总负荷不变但重新分配节点需求，应能改变网络评分。

### 验证与后续对照实验

验证 DP 与小规模枚举一致、时段覆盖与能量守恒、启动段平均功率上限、跨段最小开停及展开后的拥塞反例。基线与方法固定实例、硬件、线程、种子、预算及停止标准；记录辅助 LP、所有区间评分、DP、建模、求解、ED/修复和验证的总时间，报告目标、原问题有效界、残差、时段数与二进制数。受限/近似模型 gap 不代表原 NCUC gap。
