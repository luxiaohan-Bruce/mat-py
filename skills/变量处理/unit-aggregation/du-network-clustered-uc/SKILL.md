---
name: du-network-clustered-uc
description: >-
  当长期运行或规划中需压缩 UC 整数变量、同时保留每台机组所在节点的 DC 潮流时，使用 DO 与 CUC 的功率耦合；可选择连续容量松弛，但最终调度必须恢复逐机 UC。
---

# Du：逐机潮流与簇启停耦合的 NC-CUC

Ershun Du, Ning Zhang, Chongqing Kang, Qing Xia. A High-Efficiency Network-Constrained Clustered Unit Commitment Model for Power System Planning Studies. IEEE Transactions on Power Systems 34(4), 2019.

## 算法解读

NC-CUC 同时保留两个层次：DO 层在每台机组真实节点设置连续出力并建立网络；CUC 层管理簇的整数启停数量和运行约束。以 $P_{c,t}=\sum_{g\in c}p_{g,t}$ 耦合两层。NC-RCUC 进一步用连续 MW 容量替代整数数量；两种模型均需恢复逐机身份。

适用于允许近似的长期运行子问题或规划筛选。NC-CUC 保留整数簇数量，NC-RCUC 将其松弛为连续在线容量；二者均不自动提供逐机整数可行解。先阅读[关键建模关系](#关键建模关系)。

**整段算法：**

1. 根据技术及参数相似性分簇，保存逐机节点和参数；簇平均容量为算术均值，最小出力比例、爬坡比例与最小开停时间按容量加权。若最小开停时间加权后非整数，优先细分簇；向上取整等选择须标成适配并在原模型验证。
2. 建立 DO 层：逐机连续出力 $0\le p_{g,t}\le\mathrm{Cap}_g$，逐机连续爬坡、节点平衡、参考相角、DC 潮流、全线路限额。
3. 建立 CUC 层：整数在线/启停数量、簇出力范围、簇爬坡、启停转换、累计开停时间与备用。以 $P_{c,t}=\sum_{g\in c}p_{g,t}$ 耦合两层。变量成本只按逐机出力记一次，启动成本按簇启停记一次。
4. 若选 NC-RCUC，用 MW 单位的 $O,\mathrm{SU},\mathrm{SD}$ 代替在线/启停数量乘代表容量。明确标记连续松弛；外层投资若为整数，整个规划问题仍是 MILP。
5. 将聚合结果作为原逐机 UC 的初始建议。先用整数簇数量约束恢复；连续容量轨迹用偏差罚项引导，不可直接四舍五入后当作可行解。完整逐机模型重新分配身份和出力，保留原网络/备用/启停/爬坡等约束。恢复失败则释放建议或回退原 UC，此为工程适配。

### 关键建模关系

#### 公式与结构

§III.D 式35是核心：$\sum_{g\in c}P_{g,t}=P_{c,t}$。DO 层式19–20控制逐机出力及连续爬坡，式13–16控制节点平衡与 DC 网络。CUC 层式23–29处理簇在线数量、爬坡、启停和最小开停时间；式32是簇备用。目标式33按逐机成本计算变动费用。

式36 $\mathrm{Cap}_c=\frac{\sum_{g\in c}\mathrm{Cap}_g}{N_c}$；式37–41对 $\alpha_{\mathrm{RU}},\alpha_{\mathrm{RD}},\lambda_{\min},T_{\mathrm{on}},T_{\mathrm{off}}$ 用 $\mathrm{Cap}_g/\sum_{j\in c}\mathrm{Cap}_j$ 加权。跨节点聚类仍保留逐机 DO 出力，故网络功率约束可保留，但 DO 层没有逐机整数状态，这一缺口不能靠功率和等式补足。

NC-RCUC 式42–48：$\lambda_{\min}O_t\le P_t\le O_t$，$-\alpha_{\mathrm{RD}}O_t\le P_t-P_{t-1}\le\alpha_{\mathrm{RU}}O_t$，$O_t=O_{t-1}+\mathrm{SU}_t-\mathrm{SD}_t$；启动容量和停机容量均以 MW 计量。在线容量及其变化可为分数，不能解释为已经选定真实机组。对固定同一 NC-CUC 模型，去整数性是其松弛；对异质原 UC 是否有效下界，必须另证可行域包含关系。

#### 原文核对和实施限制

- PDF 第5页确认 MinerU 丢了式34最后一行 Linking Constraints；式35不可省略。式34把目标式33列作约束且仍引用含逐机状态的式12，实际接入应明确使用簇备用式32，记录为符号清理。
- 式46的最小停机时间求和在原文写成 SU；与式27的 SD、停机窗口含义不一致。实现时采用 SD 并注明这一修正，不直接复制。
- 式5定义启动进入当前时段，但式6–7、26–27累加 $t-\tau$，未含当前启动。按原模型的事件定义统一窗口和初始历史，不能混用两套约定。
- 表II给启动成本为货币/MW，式9/29却直接乘次数。实施时把启动单价先乘机组容量得到货币/次；连续容量模型式47则用货币/MW乘启动 MW。
- 原文按小时求和所以没有显式 $\Delta t$；其它分辨率的能量费用必须乘小时数。DC 的电纳 pu 与功率 MW 需统一基准，固定每个连通分量的参考相角。
- 异质均值最小开停时间可能非整数，原文没有完整离散化规则；不要静默截断。NC-RCUC 也不提供逐机整数恢复定理。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `du_cluster_parameters`
- **Description**: 当长期运行或规划中需压缩 UC 整数变量、同时保留每台机组所在节点的 DC 潮流时，使用 DO 与 CUC 的功率耦合；可选择连续容量松弛，但最终调度必须恢复逐机 UC。
- **实现范围**: 计算代表容量与容量加权运行参数；不构建两层模型或恢复逐机状态。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 size、平均 cap 与加权 min_ratio、ru_ratio、rd_ratio、up_hours、down_hours。

**完整流程输出与保证：**

输出模型类型、簇映射、容量加权参数、逐机 DO 出力、簇数量/连续容量、恢复后的原模型解、目标、有效界/gap及验证残差。DO 出力可能在多台机组上分别低于最小稳定出力，即使簇整数数量合法也不能推出逐机可行。异质平均、简化动态及跨节点状态不一致使其一般只是近似；不得把 NC-RCUC 或受限恢复的 gap 当成原 UC gap。

原文只测试正常拓扑 DC 安全。用于 SCUC 时须在原模型保留全部既有安全约束，恢复验证也包含这些约束。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入逐机容量 MW、节点、成本 货币/MWh、启动费 货币/次或货币/MW、最小出力比例、每小时爬坡比例、最小开停机小时数、初态、节点需求/风光 MW、DC 网络与线路限额 MW、时长 h、备用规则及簇映射。区分启动费的两种单位，不能混乘容量。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "units"
  ],
  "properties": {
    "units": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "cap",
          "min_ratio",
          "ru_ratio",
          "rd_ratio",
          "up_hours",
          "down_hours"
        ],
        "properties": {
          "cap": {
            "type": "number",
            "description": "单机容量，MW。",
            "exclusiveMinimum": 0
          },
          "min_ratio": {
            "type": "number",
            "description": "最低出力/容量比例。",
            "minimum": 0,
            "maximum": 1
          },
          "ru_ratio": {
            "type": "number",
            "description": "每小时上爬坡/容量比例，h^-1。",
            "minimum": 0
          },
          "rd_ratio": {
            "type": "number",
            "description": "每小时下爬坡/容量比例，h^-1。",
            "minimum": 0
          },
          "up_hours": {
            "type": "number",
            "description": "最小开机时间，h。",
            "minimum": 0
          },
          "down_hours": {
            "type": "number",
            "description": "最小停机时间，h。",
            "minimum": 0
          }
        }
      },
      "minItems": 1
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

def du_cluster_parameters(units):
    if not units or any(u["cap"] <= 0 for u in units):
        raise ValueError("positive MW capacities required")
    keys = ("cap", "min_ratio", "ru_ratio", "rd_ratio", "up_hours", "down_hours")
    if any(not isfinite(u[k]) for u in units for k in keys):
        raise ValueError("finite cluster parameters required")
    total = sum(u["cap"] for u in units)
    result = {"size": len(units), "cap": total / len(units)}
    for key in ("min_ratio", "ru_ratio", "rd_ratio", "up_hours", "down_hours"):
        result[key] = sum(u["cap"] * u[key] for u in units) / total
    return result
```

关键接入伪代码：`cluster_power[c,t] == sum(unit_power[g,t] for g in members[c])`；网络始终使用 `unit_power[g,t]` 和真实节点，不能把簇总功率任意放到一个虚构节点。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 容量不为正或参数非有限 | 抛出 ValueError；物理比例范围由输入校验一并检查。 |
| 加权最小开停时间不落在原时间格上 | 优先细分簇；若取整，标为适配并在原逐机模型验证。 |
| DO 出力低于真实单机最小稳定出力 | 不能直接输出；完整恢复失败时释放簇建议或回退原 UC。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 合并两台容量 100、200 MW 的机组，最低出力比例分别为 0.4、0.5。

**调用说明**: 使用 `du_cluster_parameters` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "du_cluster_parameters",
  "units": [
    {
      "cap": 100,
      "min_ratio": 0.4,
      "ru_ratio": 0.5,
      "rd_ratio": 0.5,
      "up_hours": 2,
      "down_hours": 2
    },
    {
      "cap": 200,
      "min_ratio": 0.5,
      "ru_ratio": 0.5,
      "rd_ratio": 0.5,
      "up_hours": 2,
      "down_hours": 2
    }
  ]
}
```

**Observation**: 返回 `size=2`、`cap=150` MW、$\mathtt{min\_ratio}=7/15$，其余参数保持 0.5、0.5、2、2。两台代表容量合计 300 MW；容量守恒不证明逐机整数可行性。

### 验证与后续对照实验

先验证两台容量100/200 MW的簇均值150 MW、最小出力比例0.4/0.5的加权值7/15，以及所有逐机出力之和等于簇出力。再构造两台 $P^{\min}=40$、$P^{\max}=100$ 的机组、簇在线数1且 DO 出力各25的反例，确认恢复检查拒绝直接输出该轨迹。对照原 UC 使用相同实例、硬件、总预算与停止标准，计入预处理、建模、求解、恢复重试和原约束验证；报告总耗时、原目标、有效界/gap、可行性和变量规模。本次仅验证文档与片段，不声称取得加速。
