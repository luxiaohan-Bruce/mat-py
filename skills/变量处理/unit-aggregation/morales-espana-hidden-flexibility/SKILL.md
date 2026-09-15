---
name: morales-espana-hidden-flexibility
description: >-
  当普通 CUC 高估同质机组的爬坡、备用或启停能力时，加入有序簇内状态与逐槽出力约束以收紧模型，并恢复核验真实机组轨迹。
---

# Morales-España：保留簇内爬坡与备用的隐含灵活性约束

Germán Morales-España, Diego A. Tejada-Arango. Modeling the Hidden Flexibility of Clustered Unit Commitment. IEEE Transactions on Power Systems 34(4), 2019, 3294–3296.

## 算法解读

普通 CUC 的“在线数量×单机爬坡”可能把满发机组的爬坡额度借给其他机组。PCUC 加入有序槽位状态、逐槽出力及备用，分别限制每槽容量、启停与爬坡，再与簇总量相连。局部凸包性质不能替代真实机组的跨时段身份和最小开停历史。

先读[关键建模关系](#关键建模关系)。论文证明的局部凸包和案例目标一致，不代表任意逐机最小开停时间与初态下的完整等价定理。

**整段算法：**

1. 保留传统簇整数 $u,y,z\in\{0,\ldots,G\}$、状态转换、累计最小开停时间及总功率关系 $P_{\mathrm{total}}=P^{\min}u+p$，其中 $p$ 是超过最低出力的部分。
2. 为每簇引入有序二元槽位状态 $\widetilde u_{g+1,t}\le\widetilde u_{g,t}$ 和连续 $\widetilde p,\widetilde r^+,\widetilde r^-$；用和等式连接簇状态、超最小出力与备用。不要因局部凸包描述就将所有二元槽位随意改为连续变量。
3. 为每槽加入容量、启停能力式15–17与爬坡式18–19。按最小开机时间分别选择 $\mathrm{TU}\ge2$ 或 $\mathrm{TU}=1$ 公式，逐项核验原模型假设；保留基本容量上界与非负限制。
4. 求解后把槽位调度映射或作为建议输入完整逐机 UC。检查每台真实机组的初始历史、最小开停时间、启停/爬坡及备用可交付性。槽位在相邻时段的排序不能替代真实机组身份历史。
5. 恢复不通过时释放槽位/计数建议，求解原 UC；可保留修复后的可行解作为热启动。恢复及回退是仓库适配，不是本文新增证明。

### 关键建模关系

#### 模型细节

§II.A 式1–3：$u_t-u_{t-1}=y_t-z_t$，$\sum_{i=t-\mathrm{TU}+1}^{t}y_i\le u_t$，$\sum_{i=t-\mathrm{TD}+1}^{t}z_i\le G-u_t$，初始窗口需带历史。原文文字的取值集合漏了0，按逻辑应包括关闭所有机组。

$\mathrm{TU}\ge2$ 时式4：$p_t+r_t^+\le(P^{\max}-P^{\min})u_t-(P^{\max}-\mathrm{SU})y_t-(P^{\max}-\mathrm{SD})z_{t+1}$；$\mathrm{TU}=1$时用式5–6分别限制，以避免重复扣减启停能力。$p-r^-\ge0$，总功率 $P^{\min}u+p$。

§II.B 式10–14：有序槽位二元 $\widetilde u_{g+1,t}\le\widetilde u_{g,t}$，$\widetilde p-\widetilde r^-\ge0$，$\widetilde p+\widetilde r^+\le(P^{\max}-P^{\min})\widetilde u$，并有 $u_t=\sum_g\widetilde u_{g,t},\quad p_t=\sum_g\widetilde p_{g,t},\quad r_t^{\pm}=\sum_g\widetilde r_{g,t}^{\pm}$。

$\mathrm{TU}\ge2$ 的逐槽式15–16：

- $\widetilde p_{g,t}+\widetilde r_{g,t}^+\le(\mathrm{SU}-P^{\min})\widetilde u_{g,t}+(P^{\max}-\mathrm{SU})\widetilde u_{g,t-1}$。
- $\widetilde p_{g,t}+\widetilde r_{g,t}^+\le(\mathrm{SD}-P^{\min})\widetilde u_{g,t}+(P^{\max}-\mathrm{SD})\widetilde u_{g,t+1}$。

$\mathrm{TU}=1$ 的原式17：

$$
\widetilde p_t+\widetilde r_t^+\le(\mathrm{SU}-P^{\max}+\mathrm{SD}-P^{\min})\widetilde u_t+(P^{\max}-\mathrm{SU})\widetilde u_{t-1}+(P^{\max}-\mathrm{SD})\widetilde u_{t+1}
$$

已对照 PDF 第2页确认该印刷式。它对单时段开机(0,1,0)给出的上界可能比 $\min(\mathrm{SU},\mathrm{SD})-P^{\min}$ 更紧，参数不满足时甚至为负。因此不要将这一式子称为所有 SU/SD 参数下的精确描述；本仓库测试需比较原逐机能力，对不匹配的 $\mathrm{TU}=1$ 机组保留原逐机约束或使用经过验证的原模型表示，并明确标为适配。

式18–19的爬坡与备用共同计入：$\widetilde p_t+\widetilde r_t^+-\widetilde p_{t-1}\le\mathrm{RU}\,\widetilde u_t$，$\widetilde p_{t-1}-\widetilde p_t+\widetilde r_t^-\le\mathrm{RD}\,\widetilde u_{t-1}$。量是超过 Pmin 的出力，不能把总功率直接塞入相同式子。

#### 精确性与来源边界

局部式10–14的凸包说明针对特定约束集合；加上全时域耦合后，不能据此删除二元性或宣布整体 LP 精确。结论§IV明确将逐机最小开停时间的改进列为未来工作。各槽位按在线数量排序可能与固定真实机组身份的持续运行时间不一致，因此 skill 要求独立恢复/核验。

符号表把功率标 MWh、爬坡标 MW/h，因一小时网格数值相同，适配时按物理 MW、MWh 分开；不会直接沿用单位混写。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `available_upward`
- **Description**: 当普通 CUC 高估同质机组的爬坡、备用或启停能力时，加入有序簇内状态与逐槽出力约束以收紧模型，并恢复核验真实机组轨迹。
- **实现范围**: 无启停、已知逐机当前出力时的向上调节量诊断；不等于完整 PCUC。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回一个响应时段内的可用向上调节量，MW：$\sum_i\min\{\mathrm{RU}_i,P_i^{\max}-p_i\}$。

**完整流程输出与保证：**

输出完整 PCUC 约束配置、簇/槽位解、逐机恢复结果、目标与原模型有效界/gap、备用及动态约束残差。该方法增加簇内连续变量及有序二元变量，优势来自对称性减少与约束加强，不能宣称全部变量数与机组数无关。不得把模型目标更低直接当成改进；必须排除灵活性高估。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

用于同质、网络位置兼容的机组簇，尤其备用和爬坡较紧时。输入簇大小、Pmin/Pmax MW、RU/RD MW/时段、启停允许出力 SU/SD MW、最小开停时间、初态、成本和系统负荷/网络/备用。原文为小时网格，改网格时须显式换算。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "powers",
    "pmax",
    "ramp_per_step"
  ],
  "properties": {
    "powers": {
      "type": "array",
      "items": {
        "type": "number",
        "description": "已知单机当前出力，MW，须不超过 pmax。",
        "minimum": 0
      }
    },
    "pmax": {
      "type": "number",
      "description": "相同单机最高出力，MW。",
      "minimum": 0
    },
    "ramp_per_step": {
      "type": "number",
      "description": "所检查响应时间内的单机爬坡能力，MW。",
      "minimum": 0
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

此例计算无启停、当前出力已确定情况下，一个响应时段内可用的向上调节量；用于识别“簇数量乘单机爬坡”的高估，不代替整个 PCUC 建模。

```python
from math import isfinite

def available_upward(powers, pmax, ramp_per_step):
    if not all(isfinite(x) for x in [pmax, ramp_per_step] + list(powers)):
        raise ValueError("finite powers and limits required")
    if pmax < 0 or ramp_per_step < 0:
        raise ValueError("nonnegative limits required")
    if any(p < 0 or p > pmax for p in powers):
        raise ValueError("individual power out of bounds")
    return sum(min(ramp_per_step, pmax - p) for p in powers)
```

十台 $P^{\max}=100$、$\mathrm{RU}=10$，九台出力100、一台0时，真正可上调10 MW，而 $10\,\mathrm{RU}$ 给出100 MW。备用响应时间如果短于调度时段，需要使用该响应时间的爬坡能力。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 出力越界、负限制或非有限值 | 抛出 ValueError。 |
| 响应时间与调度时段不同 | 先按真实响应时间换算单机爬坡；不得直接沿用小时额度。 |
| 槽位解无法满足真实历史或最小开停 | 释放槽位/计数建议，回退完整逐机 UC。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 九台机组已满发 100 MW，一台为 0 MW；每台在响应时段最多升 10 MW，诊断总向上能力。

**调用说明**: 使用 `available_upward` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "available_upward",
  "powers": [
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    100,
    0
  ],
  "pmax": 100,
  "ramp_per_step": 10
}
```

**Observation**: 返回 10 MW，而在线数量乘爬坡给出 100 MW。这里采用最低出力为零且不发生启停的诊断例子；有正 Pmin 的实际机组需要另行核验在线状态。

### 验证与后续对照实验

先验证上面的10 MW反例，再测试启停功率与最小开机时间交互；恢复阶段必须检查真实身份。对比 IUC、普通 CUC、完整 PCUC，使用相同实例、硬件、总预算及停止标准。报告预处理+建模+求解+恢复+验证总耗时、原目标、有效界/gap、原问题可行性与变量数；可单独消融启停/爬坡约束，但不可把消融解当成原问题可行解。本次未运行全库加速实验。
