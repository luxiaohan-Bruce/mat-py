---
name: koller-shifting-generation-levels
description: >-
  当同质机组具有对称爬坡、在最低出力启停且只含一种启动成本时，使用发电水平与运行年龄分层压缩 UC；非整除水平采用近似或与完整逐机模型耦合。
---

# Koller：发电水平移位 SGLM 与混合模型

Martin Koller, René Hofmann. Efficient clustering of identical generating units for the MILP-UC with a shifting generation level method. Computers & Chemical Engineering 125 (2019), 415–426.

## 算法解读

把超过最低出力的运行区间 $Q$ 按单步爬坡 $R\tau$ 分成发电水平，并按运行年龄跟踪数量的移动。$Q/(R\tau)$ 为整数时只用一套 Y 水平；存在余数比例 $\lambda$ 时增加 Z 水平和末端修正，但仍是近似。需要可靠逐机结果时使用保留完整逐机约束的 Hybrid。

本方法原版要求同质机组、上/下爬坡相同、启动/停机时超过最低出力的增量 $S=0$、单一启动费用；论文未实现旋转备用、冷热启动和不对称爬坡的完整推广。不要为套用方法而删除原问题中的这些约束。

**整段算法：**

1. 令 $Q=P^{\max}-P^{\min}$，计算 $I=\left\lceil\frac{Q}{R\tau}\right\rceil+1$ 与余数比例 $\lambda$。$\lambda=0$时只建 Y 分层；$\lambda\ne0$时同时建 Y、Z 两套分层。用数值容差处理接近整除，不能随意舍弃非零余数。
2. 建立连续 $y_{i,t,k}$（必要时 z），描述各出力水平和累计运行年龄层的数量；簇在线数为整数。总出力是 $P^{\min}U_t+\sum_{i,k}Y_i y_{i,t,k}$，不是将 y 当作某台机组的二元身份。
3. 新启机进入最低出力/年龄1层，停机只能从最低出力/年龄 $K$ 层移出。按附录A累计移位不等式限制每步最多移动一个正常出力层及增长一层年龄，年龄在 $K$ 饱和；最低停机时间继续用累计停机数约束。
4. $\lambda\ne0$时保持 Y/Z 的在线数量和总功率相同，并添加不等距末端修正及式55–56的启停到满发最短时间约束。仍需标记近似。要求严格逐机结果时使用 Hybrid：保留完整逐机3-bin，并用式57–58连接总功率与在线数。
5. 恢复真实机组轨迹，逐机核对初态、爬坡、最小开停、启停出力以及原系统约束。不能逐时段任意均分 y 对应的总出力。近似 SGLM 无法恢复时用 Hybrid 或原 UC 在同一预算内重求解。

### 关键建模关系

#### 分层与移位公式

§2.3、附录A：$I=\left\lceil\frac{Q}{R\tau}\right\rceil+1$，$\lambda=\frac{Q\bmod(R\tau)}{R\tau}$。整除时 $Y=R\tau[0,1,\ldots,I-1]$；非整除时 $Y=R\tau[0,1,\ldots,I-2,I-2+\lambda]$，$Z=R\tau[0,\lambda,1+\lambda,\ldots,I-2+\lambda]$。

$\sum_{i,k}y_{i,t,k}=U_t$，$\left(P^{\min}U_t+\sum_{i,k}Y_i y_{i,t,k}\right)\tau=D_t$。$w_t^*=w_{t+1}$ 是提前一格的停机量，故 $U_{t+1}-U_t=v_{t+1}-w_t^*$；最小停机累计的索引也必须用 $w_{\ell-1}^*$。$\tau$ 乘完整总功率，正文式34解析括号缺失，附录A.1b可确认。

新启机 $y_{1,t,1}=v_t$（$K>1$），$K=1$ 时改为 $y_{1,t,1}\ge v_t$；停机 $y_{1,t,K}\ge w_t^*$；未达到的高水平/低年龄组合置零（式40）。

整除时式42（附录A.2b），使用1起始索引：

$$
(1-2\delta_3)\left[\sum_{\ell=1}^{i+\delta_3}y_{\ell,t+1,k+1-\delta_1}-\sum_{\ell=1}^{i+1-\delta_3}\sum_{m=k}^{k+\delta_2}y_{\ell,t,m}-\delta_1v_{t+1}+(\delta_1+\delta_2)w_t^*\right]\le0
$$

其中 $i=1,\ldots,I-1$，$k=1,\ldots,\max(1,K-1)$，$\delta_1$为$K=1$指示，$\delta_2$为$K>1$且$k=K-1$指示，$\delta_3$分别取0/1。$K=1$、向上移位简化为 $\sum_{\ell\le i}y_{\ell,t}+v_{t+1}-w_t^*\le\sum_{\ell\le i+1}y_{\ell,t+1}$；这限制低层质量不能跨两层。

非整除式A.3需完整包括 z数量和功率匹配、低龄可达性、Y顶层与Z底层移位修正：Y额外项在$i=I-2$激活，系数$1-\lambda$，使用 $y_{I,\ldots}$（正文式53解析为小写l，附录A.3k明确为大写I）；Z修正在$i=1$激活，系数$1/\lambda-1$，使用$z_{2,\ldots}$。另外式55–56（A.3m–n）限制满发数量与最近启动、未来停机的关系；$\lambda=0$不可计算$1/\lambda$。

#### 近似性质和恢复

附录B在$Q=2.5$、$R\tau=1$、$\lambda=0.5$时用双重表示说明不同机组可在特定情形“借用”爬坡。B.1–B.4未加入式55–56，不能据此声称已证明含全部加强式也产生同一反例；但作者仍明确将 $\lambda\ne0$ 归为非精确，未给出其普遍等价证明。最大相关偏移量以 $\lambda R\tau$ 描述，不是目标值误差界。

Hybrid在同一个优化模型中加入完整逐机式4–14及 $\sum_g q_{g,t}=\sum_{i,k}Y_i y_{i,t,k}$、$\sum_g u_{g,t}=U_t$；它是同时耦合的混合模型，不是 Meus 的先后两次求解。原文只连接总功率和在线数，实施时还需核对启停成本与次数一致性，必要时显式连接事件和，并记录为适配。连续 $v,w$ 在正启动成本下的整性论述不应推广到负价/额外奖励或中间可行点；出现分数必须验证或改为整数并注明。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `shifting_levels`
- **Description**: 当同质机组具有对称爬坡、在最低出力启停且只含一种启动成本时，使用发电水平与运行年龄分层压缩 UC；非整除水平采用近似或与完整逐机模型耦合。
- **实现范围**: 生成 Y/Z 移位水平及余数比例；不构建年龄层、累计移位约束或 Hybrid。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 `(Y,Z,lambda)`，水平为超过 Pmin 的 MW 增量；整除时 `Z=None`、$\lambda=0$。

**完整流程输出与保证：**

输出适用条件检查、$\lambda$ 与水平、SGLM/Hybrid模式、聚合和恢复轨迹、原目标及有效界/gap、残差与变量数。论文在其假设下将 $\lambda=0$描述为等价；$\lambda\ne0$明确不是精确等价，即使试验未观察到偏差也不能推广。Hybrid保留逐机约束才可直接检查逐机可行性，其变量数重新随 G 增加；不要把 SGLM 的规模优势赋给 Hybrid。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入簇大小 G、最低/最高出力 MW、爬坡 MW/h、时长 $\tau$ h、最小开停时段数、初始功率/运行历史、线性费用（货币/MWh、货币/h、货币/次）、每时段需求 MWh。原文 $\tau=1\,\mathrm h$，$K$ 为最小开机小时数；非一小时网格须先转换时段数。读[关键建模关系](#关键建模关系)。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "pmin",
    "pmax",
    "ramp_per_hour"
  ],
  "properties": {
    "pmin": {
      "type": "number",
      "description": "最低出力，MW。",
      "minimum": 0
    },
    "pmax": {
      "type": "number",
      "description": "最高出力，MW，严格大于 pmin。",
      "exclusiveMinimum": 0
    },
    "ramp_per_hour": {
      "type": "number",
      "description": "对称正常爬坡，MW/h。",
      "exclusiveMinimum": 0
    },
    "hours": {
      "type": "number",
      "description": "一个调度时段，h。",
      "exclusiveMinimum": 0,
      "default": 1.0
    },
    "tol": {
      "type": "number",
      "description": "判断接近整除的无量纲相对容差。",
      "minimum": 0,
      "default": 1e-10
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

```python
import math

def shifting_levels(pmin, pmax, ramp_per_hour, hours=1.0, tol=1e-10):
    if not all(math.isfinite(x) for x in (pmin, pmax, ramp_per_hour, hours, tol)):
        raise ValueError("finite inputs required")
    if hours <= 0 or ramp_per_hour <= 0 or tol < 0:
        raise ValueError("positive time/ramp and nonnegative tolerance required")
    q = pmax - pmin
    step = ramp_per_hour * hours
    if q <= 0 or step <= 0:
        raise ValueError("positive operating range and ramp step required")
    ratio = q / step
    if round(ratio) >= 1 and abs(ratio - round(ratio)) <= tol * max(1.0, ratio):
        n = round(ratio)
        y = [j * step for j in range(n + 1)]
        y[-1] = q
        return y, None, 0.0
    n = math.floor(ratio)
    fraction = ratio - n
    y = [j * step for j in range(n + 1)] + [q]
    z = [0.0] + [(fraction + j) * step for j in range(n + 1)]
    z[-1] = q
    return y, z, fraction
```

例如 $Q=2.5$ MW、$R\tau=1$ MW 得 $Y=[0,1,2,2.5]$，$Z=[0,0.5,1.5,2.5]$，$\lambda=0.5$。若 $R\tau\ge Q$，优先检查能否使用快机聚合，避免不必要水平变量。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 运行范围、时长或爬坡不为正，或参数非有限 | 抛出 ValueError。 |
| 不对称爬坡、非最低出力启停或多种启动费 | 原版适用条件不成立；保留原约束并改用合适模型。 |
| 非整除 SGLM 无法逐机恢复 | 使用 Hybrid 或原 UC；不能因近似模型求解最优就声明原问题最优。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: $P^{\min}=10$、$P^{\max}=12.5$ MW，对称爬坡 1 MW/h，时长 1 h，计算移位水平。

**调用说明**: 使用 `shifting_levels` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "shifting_levels",
  "pmin": 10,
  "pmax": 12.5,
  "ramp_per_hour": 1,
  "hours": 1
}
```

**Observation**: 返回 $Y=[0,1,2,2.5]$、$Z=[0,0.5,1.5,2.5]$、$\lambda=0.5$。这些是超过 Pmin 的增量；该非整除情况按近似处理，需 Hybrid 或逐机恢复。

### 验证与后续对照实验

先检查水平端点、间隔及移位守恒；$Q=4$、$R\tau=1$的双机最大总增量轨迹应为2、4、6、7、8而非2、4、6、8。对 $\lambda\ne0$测试附录B借用爬坡的反例，验证原逐机限制能拒绝。对照固定相同实例、硬件、总预算和停止标准，计入预处理、建模、求解、恢复/Hybrid重试、验证；报告原目标、有效界/gap、可行性、变量数与总耗时。本次没有运行全库实验。
