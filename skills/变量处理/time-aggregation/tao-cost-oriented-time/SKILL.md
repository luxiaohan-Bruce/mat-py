---
name: tao-cost-oriented-time
description: >-
  以日前 UC 加原细网格实时调度的成本反馈搜索固定数量的时间边界，使用相邻边界局部搜索、离散 Adam 和离线热启动减少搜索开销；用于时间聚合策略研究，需要真实预测与明确的日前/实时决策政策。
---

# Tao：成本导向时间边界搜索与离散 Adam

Junyi Tao, Ran Li, Salvador Pineda. *Unit Commitment with Cost-Oriented Temporal Resolution.* 预印本，2025.

## 算法解读

在细时间格上固定首末边界，移动内部边界，评价每个划分对应的日前 UC 与原细网格实时调度总成本。离散 Adam 用相邻边界候选费用估计方向；多个独立提案必须合成为绝对边界并重新评价，局部改善不能相加成为整体改善。

当负荷变化无法反映启动成本跳变或爬坡引起的昂贵调度时，用真实调度成本评价时间划分。它优化“分段方式”，不是降低一次 UC 的目标后就结束；边界搜索要重复求 UC 和 ED，可能比普通聚类慢。

先读 [关键建模关系](#关键建模关系)。使用已有原模型作为求解适配器；不把含整数下层问题用 KKT 直接替换。

**整段算法：**

1. 在整数细时间步上表示边界 $0=b_0<b_1<\cdots<b_K=T_0$。起止固定，每段至少一步。初始化用均匀划分；离线/在线模式按下文调度政策改用相邻聚类与离线最终划分。
2. 定义 `evaluate_partition`：先按时长构建日前 UC，再按原文政策展开承诺并求细网格实时调度，校验原约束后返回总费用及状态。这里的 ED 对峰荷启停仍可能含整数变量。
3. 贪婪模式在原文的邻接允许范围内逐步枚举一个内部边界的合法位置；移动只改变相邻两段、两段总长不变，其余边界固定。保留重复候选缓存，缓存键包括预测、初始状态、政策与求解设置。
4. Adam 模式以左右各一个细时间步的候选成本估计方向，更新每个边界的一、二阶矩及偏差修正，将步长量化回整数格，再限制在本轮合法范围内。
5. 若各边界从同一个旧划分独立生成提案，用绝对边界位置统一合成，再差分成时长。必须再次求完整 UC/实时调度；独立局部改善不保证组合后改善。
6. **工程保护**：只保留成本有可确认改善的已验证完整方案，拒绝交叉/零长/不可行提案；离散状态重复、没有改善或预算到达时停止，返回最好已验证方案。边界停动不是双层全局最优证明。
7. 使用离线结果作当天热启动时，替换为当天可用预测后重新评价；保留离线耗时及数据时间戳。历史回测使用实现时点之后的真实负荷选边界，应明确标为理想信息实验。

### 关键建模关系

#### 优化对象与调度政策

§III.A 式 (4)–(12) 的上层调整时间长度，以细网格调度成本为目标；下层在该划分上优化日前 UC。运行成本乘实际小时，启停成本按事件计。式 (8) 固定基荷出力，式 (9) 固定基荷与中荷状态；峰荷保留实时调整能力，因此不能简单称为纯连续 ED。

确定性研究假设日前和实时净需求相同；概率模式使用提前 48 小时预测。将方法用于原 UC 加速时必须定义原问题允许的调整范围，不增加未经授权的失负荷、网络松弛或其他自由度。

#### 贪婪边界搜索

每轮基于旧划分，边界 $q$ 的内部允许区域由左右相邻区间各一半形成；首个、末个内部边界向外可用范围按正文例外处理。只能落在细网格上，严格边界约束与最短一格同时检查。

对每个合法候选位置求一次日前 UC 和细网格调度。论文式 (17) 保持相邻两段总长，式 (19) 固定其他段。固定 $K$ 不代表固定全部变量数量：实时调度及重复搜索仍消耗大量计算。

#### 已核对的公式问题

对照 PDF 第 5–6 页：

- 式 (21) 将独立提案合并时使用 $\sum_q x_{q,\mathrm{alter}}$；这些量是在不同旧左边界下定义的局部左段长度，直接作为累计新时长不一定保持一致。入口改用 $b'_q=b_{q-1}+x_{q,\mathrm{alter}}$ 后差分，这是标明的工程合成规则。
- 式 (29) 将右邻长度写为 $x_{q,\mathrm{left}}$，与式 (26) 的守恒配对矛盾；按式 (26) 应为 $x_{q+1,\mathrm{left}}$。
- MinerU 式 (38) 丢失量化前除以 $L_{\min}$ 的部分；PDF 是先将连续步长除以 $L_{\min}$ 再取整乘回 $L_{\min}$。入口不照抄缺失版本。
- 概率式 (23)–(25) 的部分出力没有情景下标，而文字讨论情景相关实际调度；不能仅凭此认定完整随机模型的非预见性结构。若接入随机版，明确共享日前承诺及按情景的可调决策，并标为建模补全。

#### 离散 Adam 方向

论文式 (35) 采用 $g=\frac{C_{\mathrm{left}}-C_{\mathrm{right}}}{2L_{\min}}$，是对向右移动坐标的负梯度。式 (36)/(37) 用它更新并修正 $m,v$。与式 (39) 联用时可清楚写为

$$
b'_q=b_q+\operatorname{round}\left(
\frac{\alpha\hat m_q}{\sqrt{\hat v_q+\epsilon}\,L_{min}}
\right)L_{min}.
$$

因此 $C_{\mathrm{right}}<C_{\mathrm{left}}$ 时应趋向右移，不要将标准梯度下降的负号再叠加一次。边界范围需要上下两侧共同截断；原文式 (38) 的单侧 $\min$ 不能替代完整区间检查。均衡舍入规则须显式固定，参数 `alpha,beta1,beta2` 未从材料中获得统一数值，不虚构“论文默认”。原文给 $\epsilon=10^{-8}$。

不可微成本、整数最优解跳变、候选的不同 MIP gap 都会影响方向估计；所有候选采用一致求解设置。只要求方向提示，不宣称 Adam 收敛定理适用于本双层整数问题。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `combine_boundary_proposals`
- **Description**: 以日前 UC 加原细网格实时调度的成本反馈搜索固定数量的时间边界，使用相邻边界局部搜索、离散 Adam 和离线热启动减少搜索开销；用于时间聚合策略研究，需要真实预测与明确的日前/实时决策政策。
- **实现范围**: 把同一旧划分生成的内部边界提案合成为新段长；不包含 Adam 更新、合法邻域筛选或成本求解。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回新段长列表，段数和总细步数不变；所有新边界严格递增。

**完整流程输出与保证：**

输出：合法边界与长度、逐次候选成本和求解状态、最好已验证调度、模型调用数、离线与在线耗时、原问题目标/有效界、残差。默认确定性模式；没有情景数据不生成虚构样本，没有离线预测就从当天数据初始化。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入：高分辨率需求/可再生预测、细网格小时数（论文 10 分钟）、目标段数 $K$、原 UC/ED 构建与验证函数、基荷/中荷/峰荷的日前固定政策、初始状态、预算。Adam 模式另给 `alpha,beta1,beta2,eps`；离线模式需真实可用的提前 48 小时预测；随机模式需带权情景与共享决策定义。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "old_lengths",
    "proposed_left_lengths"
  ],
  "properties": {
    "old_lengths": {
      "type": "array",
      "items": {
        "type": "integer",
        "description": "旧段包含的细时间步数。",
        "minimum": 1
      },
      "minItems": 1
    },
    "proposed_left_lengths": {
      "type": "array",
      "items": {
        "type": "integer",
        "description": "第 q 项是以旧边界 b[q] 为起点的新左段长度；先量化为整数。"
      }
    }
  },
  "additionalProperties": false
}
```

提案数必须比旧段数少 1；调用前按原文邻域限制筛选合法提案，此函数只验证合成后的顺序与总长。

---

## 3. 核心代码实现 (Python Implementation)

```python
def combine_boundary_proposals(old_lengths, proposed_left_lengths):
    # 单位均为整数细时间步。第 q 个提案为保持旧 b[q] 时的新左段长度。
    if not old_lengths or any(type(x) is not int or x < 1 for x in old_lengths):
        raise ValueError("all periods must contain positive integer steps")
    if len(proposed_left_lengths) != len(old_lengths) - 1:
        raise ValueError("one proposal is required per internal boundary")
    if any(type(x) is not int for x in proposed_left_lengths):
        raise ValueError("proposals must be quantized first")
    boundaries, prefix = [0], 0
    for q, proposal in enumerate(proposed_left_lengths):
        boundaries.append(prefix + proposal)
        prefix += old_lengths[q]
    boundaries.append(sum(old_lengths))
    if any(a >= b for a, b in zip(boundaries, boundaries[1:])):
        raise ValueError("crossing, zero-length or out-of-range proposal")
    return [b - a for a, b in zip(boundaries, boundaries[1:])]
```

此片段检验守恒与顺序；合法移动范围由调用方按本轮旧边界先行检查。完整算法使用求解回调，不能拿一个人工成本函数的结果称为 UC 实测。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 段长不是正整数或提案数不匹配 | 抛出 ValueError。 |
| 新边界交叉、越界或形成零长段 | 拒绝该提案，保留最好已验证方案。 |
| 候选不可行、无 incumbent、重复或预算耗尽 | 不替换最好可行方案；记录实际终止状态和全部求解开销。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 旧划分为 6、6、6 个细时间步，两条内部边界独立给出新左长 7、5，合成新划分。

**调用说明**: 使用 `combine_boundary_proposals` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "combine_boundary_proposals",
  "old_lengths": [
    6,
    6,
    6
  ],
  "proposed_left_lengths": [
    7,
    5
  ]
}
```

**Observation**: 得到 [7,4,7]，对应绝对边界 [0,7,11,18]，总长仍是 18。下一步重新求完整 UC/实时调度；合法划分不代表成本改善。

### 验证与后续对照实验

测试总长度和段数不变、每段至少一步、首末固定、$K=1$ 无内部边界、量化后零移动、重复划分停止，以及候选求解无 incumbent/不可行时不替换最好解。无成本改善只表示本轮搜索停止。

后续固定实例、硬件、线程、种子、总预算和停止标准，分别与等长 UC、负荷聚类、贪婪枚举、Adam、离线热启动比较。报告全部 UC/实时调度调用和验证的总耗时，另列离线与在线时间、总 CPU 开销、原问题成本/有效界与可行性。节约运行费用与减少求解时间是两个指标；不把在线延迟下降写成含离线准备的总加速。
