---
name: knueven-identical-generators
description: >-
  当 UC 存在物理参数及成本相同的机组时，检查精确聚合条件；快爬坡机组使用聚合 3-bin，慢爬坡机组使用启停区间扩展形式，并分解恢复逐机解。
---

# Knueven：相同机组的精确聚合与解分解

Ben Knueven, Jim Ostrowski, Jean-Paul Watson. Exploiting Identical Generators in Unit Commitment. IEEE Transactions on Power Systems, 2018.

## 算法解读

快爬坡相同机组在正常爬坡冗余时可用紧聚合 3-bin。慢机需要按启停区间建立扩展形式 EF，每条区间弧携带整数数量及该弧专属出力，而不是只有逐时段总数。均分同一弧的功率并安排满足停机间隔的真实机组，才能使用论文的分解保证。

读取[关键建模关系](#关键建模关系)。精确性要求簇内相同物理参数与成本，并且系统耦合只依赖可加总量：仓库通常可先限制同节点、同备用资格、同故障/禁运规则。不同节点 PTDF、检修或机组专有约束破坏交换对称性时须拆簇。

**整段算法：**

1. 识别等价类；无重复者保留原 3-bin。初始历史不同可以按论文扩展初始区间处理，不能直接平均或删除初态；尚未实现这一步时按兼容历史再拆簇。
2. 若 $\mathrm{RU},\mathrm{RD}\ge P^{\max}-P^{\min}$ 且原模型中正常爬坡确实冗余，采用整数数量 $U,V,W\in\{0,\ldots,N\}$ 的紧 3-bin 式8–9。启停出力约束不能随正常爬坡一起删去；$\mathrm{UT}=1$与$\mathrm{UT}\ge2$使用不同容量公式。
3. 否则用 EF：对每个满足最小开机时间的半开区间 $[a,b)$，建立整数数量 $Y_{a,b}$、该区间专属总功率/备用向量，约束 $A_{a,b}P_{a,b}\le b_{a,b}Y_{a,b}$，并限制重叠运行加停机间隔的数量不超过簇大小。
4. 成本和备用按附录处理：分段容量随可用机组数量/区间数量缩放；冷/热启动保留停机区间匹配变量。不能简单把单机二次成本作用于簇总功率。
5. EF 用 Algorithm 1 逐个取出可行区间，区间内按该区间数量均分出力；快爬坡用 Algorithm 2 分解启停，再根据启动/停机上界分配功率。所有恢复解回到原模型验证，检查目标一致性及边界历史。
6. 任何不满足证明条件、无法恢复或目标不一致的情况，退回相应逐机模型或明确改为启发式；不要继续声称等价。EF 随时间维度可达 $O(T^3)$，建模成本过大时保持原模型可能更合适。

### 关键建模关系

#### 两条精确聚合路线

§II 式3反例：两台 $P^{\min}=\mathrm{SU}=\mathrm{SD}=100$、$P^{\max}=200$、$\mathrm{RU}=\mathrm{RD}=50$，数量 `[1,2,2,2,1]` 与总功率 `[200,300,400,300,200]` 满足朴素簇约束，但第二台在时段2启动后时段3最多150，不能与另一台共同发400 MW。正常爬坡不能靠数量缩放精确表达。

EF 式7：每个合法在线区间 $[a,b)$ 建立 $Y_{a,b}$ 和专属 $P_{a,b}$，$AP\le bY$；在所有 $t\in[a,b+\mathrm{DT})$ 覆盖的弧上 $\sum_{(a,b):\,t\in[a,b+\mathrm{DT})}Y_{a,b}\le N$，输出和为簇功率。区间运行域是凸多面体时，可把同弧总向量按 Y 均分；区间图整数分解性解决身份分配。对递增凸成本，相同区间的均分可以无损实现最优性，成本须使用相应透视/分段结构。初始不同出力的运行弧必要时要复制为不同边界多面体。

快爬坡式8：$U_t-U_{t-1}=V_t-W_t$，累计开停机窗口约束，整数计数上限 N。$\mathrm{UT}\ge2$ 时式9总出力为 $P^{\min}U_t\le P_t\le P^{\max}U_t+(\mathrm{SU}-P^{\max})V_t+(\mathrm{SD}-P^{\max})W_{t+1}$。须先验证正常爬坡冗余；$\mathrm{UT}=1$以分开的启停上界代替同时扣减。启动和停机功率均是绝对 MW，不是超过最低出力的增量。

#### 恢复算法与退化情况

Algorithm 1：选择最早可启动且最早结束的正数区间，取一个单机解 $P_{a,b}/Y_{a,b}$，从余量扣除，至少等 DT 后再取下个区间，重复剥离。本文代码用等价的区间着色思路演示无历史、常数启动费的特例。

Algorithm 2：从簇计数剥离单机状态，运行且已满足 UT 时尽早取可用停机，关闭且满足 DT 时尽早取启动。历史窗口必须与原初态一致，不能每次默认已经运行/停机足够长。

PDF第5页式10核对后应为同一分数：

$$
p_{\mathrm{stay}}=\frac{P-\min(\mathrm{SU},P/U)V-\min(\mathrm{SD},P/U)W_{\mathrm{next}}}{U-V-W_{\mathrm{next}}}
$$

正文针对 $\mathrm{SU}=\mathrm{SD}$、$\mathrm{UT}\ge2$。新启机/即将停机分别赋相应 $\min$ 值。当 $U=0$直接输出零；常开数量分母为0时只分配启停机并核对总功率，不执行除法。$\mathrm{SU}\ne\mathrm{SD}$、按停机时间变化的启动费需要更完整分类和匹配，不能照用这一特例。

#### 附录实现要点与解析修正

附录B式15给基准三二元模型；附录C式16目标、17系统平衡/备用、18未聚合机组、19快爬坡簇、20慢爬坡EF。附录功率改用“超过Pmin”口径，系统平衡须加 $P^{\min}U$，不能混用正文总功率记号。

- 式19e–h按分段位置相对 $\mathrm{SU}=\mathrm{SD}$ 划分容量缩放：低段按 U；高段对 $\mathrm{TU}=1$分别按 $U-V$、$U-W_{\mathrm{next}}$，对 $\mathrm{TU}>1$按 $U-V-W_{\mathrm{next}}$。只缩放总 Pmax 而不缩放分段成本会改变目标。
- 式20a–f在每条运行弧内施加容量、首尾启停出力、正常爬坡与分段容量。式20g–j求和连接簇量。
- 式20k–n连接在线/离线弧的流量，并以初末弧约束数量；离线弧 X 支持不同启动类别。不能删除初末弧，把滚动边界当作自由状态。
- MinerU 把第9–10页两栏公式交织，按公式编号而不是文本邻接重建；式19k印刷也用 $1-U$，与主文式8c及簇大小不符，应使用 $N-U$。这项修正已以主文和 PDF 核对记录。
- 式15d附近启动扣减以及求和上界在解析中有缺漏，以附录18/19对应完整容量式和 PDF 为准；本文不交付未经核验的全附录代码副本。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `split_interval_solution`
- **Description**: 当 UC 存在物理参数及成本相同的机组时，检查精确聚合条件；快爬坡机组使用聚合 3-bin，慢爬坡机组使用启停区间扩展形式，并分解恢复逐机解。
- **实现范围**: 同初始历史、固定启动费条件下的 EF 区间分解；上游必须已保证每条弧的功率多面体可行。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回每台机组的 `{时段索引:MW出力}` 字典；未出现的时段处于停机状态。

**完整流程输出与保证：**

输出等价类与匹配证据、每簇使用的模型、聚合解、分解后的原机组轨迹、原目标与有效界/gap、恢复残差。精确条件与完整模型均满足时，聚合最优解可恢复为原问题最优解；有限 gap 下只声明相应容差。近似分簇没有这一保证。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入每台机组的 Pmin/Pmax MW、RU/RD MW/时段、启动/停机允许出力 MW、最小开停时段数、初始出力与历史、凸且递增的分段成本、启动类别及冷却时间、备用和网络系数。分簇须完整比较模型系数，不能按“接近”或四舍五入替代相同。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "arcs",
    "units"
  ],
  "properties": {
    "arcs": {
      "type": "array",
      "items": {
        "type": "array",
        "minItems": 4,
        "maxItems": 4,
        "prefixItems": [
          {
            "type": "integer",
            "description": "开始时段 a。",
            "minimum": 0
          },
          {
            "type": "integer",
            "description": "结束时段 b，不包含 b。",
            "minimum": 1
          },
          {
            "type": "integer",
            "description": "该弧在线区间数量。",
            "minimum": 0
          },
          {
            "type": "array",
            "items": {
              "type": "number",
              "description": "该弧总功率，MW；长度 b-a。",
              "minimum": 0
            }
          }
        ],
        "description": "每项为 [a,b,count,power]。"
      }
    },
    "units": {
      "type": "integer",
      "description": "簇内相同机组数。",
      "minimum": 1
    },
    "min_up": {
      "type": "integer",
      "description": "最小开机细时段数。",
      "minimum": 1,
      "default": 1
    },
    "min_down": {
      "type": "integer",
      "description": "最小停机细时段数。",
      "minimum": 1,
      "default": 1
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

以下用按开始时间的区间着色实现同一分解思想，仅适用于初始均已停够时间、无按停机年龄变化的启动费用。每条弧包含开始、结束、整数数量和该弧的总功率序列；其功率多面体由上游 EF 保证。

```python
def split_interval_solution(arcs, units, min_up=1, min_down=1):
    if units < 1 or min_up < 1 or min_down < 1:
        raise ValueError("positive counts and dwell times required")
    ready = [0] * units
    schedules = [dict() for _ in range(units)]
    for a, b, count, power in sorted(arcs, key=lambda x: (x[0], x[1])):
        if a < 0 or b - a < min_up or len(power) != b - a:
            raise ValueError("invalid interval")
        if not isinstance(count, int) or not 0 <= count <= units:
            raise ValueError("integer arc multiplicity required")
        if count == 0:
            if any(abs(p) > 1e-8 for p in power):
                raise ValueError("zero-count arc carries power")
            continue
        for _ in range(count):
            g = next((g for g in range(units) if ready[g] <= a), None)
            if g is None:
                raise ValueError("interval count/downtime infeasible")
            schedules[g].update({t: power[t-a] / count for t in range(a, b)})
            ready[g] = b + min_down
    return schedules
```

这段代码只做 EF 区间分解，不能直接分解普通 CUC 总出力。调用者必须再检查逐台 MW 界、启停允许功率、爬坡、原始初态及成本。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 弧长度、数量或零数量弧出力不合法 | 抛出 ValueError。 |
| 运行/停机间隔使可用机组不足 | 拒绝分解；检查上游 EF 计数约束和初始历史。 |
| 原机组成本、物理参数或网络系数不相同 | 拆簇或回到逐机模型；不再声明精确等价。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 把数量为 2 的 [0,3) 区间弧，总出力 200、300、400 MW 分解给两台相同机组。

**调用说明**: 使用 `split_interval_solution` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "split_interval_solution",
  "arcs": [
    [
      0,
      3,
      2,
      [
        200,
        300,
        400
      ]
    ]
  ],
  "units": 2,
  "min_up": 1,
  "min_down": 1
}
```

**Observation**: 两台各得 [100,150,200] MW。若 $P^{\min}=100$、$P^{\max}=200$、$\mathrm{RU}=\mathrm{RD}=50$ MW/时段，正常爬坡通过；还须由上游 EF 与原模型检查启停功率、边界和初态。

### 验证与后续对照实验

小测两份相同 $[0,3)$ 弧总出力 `[200,300,400]`，分解成每台 `[100,150,200]` 并验证50 MW爬坡；再验证缺少足够停机间隔的弧被拒绝。用正文五时段反例确认错误的普通聚合不能冒充 EF。后续对照固定实例、硬件、总预算与停止标准，报告识别+建模+求解+分解+验证总耗时、原目标、有效界/gap、原可行性及变量数。本次不运行全库加速实验。
