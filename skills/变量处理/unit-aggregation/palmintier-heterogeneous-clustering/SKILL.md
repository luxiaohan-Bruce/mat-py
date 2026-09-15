---
name: palmintier-heterogeneous-clustering
description: >-
  当长期规划或运行仿真含大量相似但不完全相同的机组时，按技术与效率等分层形成代表机组，用整数数量近似 UC，并在原机组上恢复评估精度和总耗时。
---

# Palmintier：异质机组分簇与精度成本权衡

Bryan S. Palmintier, Mort D. Webster. Heterogeneous Unit Clustering for Efficient Operational Flexibility Modeling. IEEE Transactions on Power Systems 29(3), 2014, 1089–1098.

## 算法解读

先按燃料和技术分大类，再按热耗等特征近似等量细分，使用代表容量及加权运行参数建立整数数量 UC。异质参数会带来近似误差，簇数决定精度与计算开销的权衡；在调度任务中还需回到原逐机模型恢复。

原方法面向长期规划近似，假设输电充分、以备用表示安全；含网络的仓库实例优先限定同节点分簇并在恢复时保留全部原约束。这属于适配。先读[关键建模关系](#关键建模关系)。

**整段算法：**

1. 建立原逐机 UC 基线。按燃料与原动机类型分大类，再按效率/热耗、容量或厂址分层。论文比较手工近似等量分组，没有唯一通用 k-means 参数。选定分组规则并保存边界，避免用测试实例最优解事后挑簇。
2. 簇代表容量取算术均值，运行技术特征采用容量加权均值；保存原机组数据与簇内离散程度。偏差过大的类别细分；不要把代表参数当作真实机组参数。
3. 每簇以 $U\in\{0,\ldots,N\}$ 表示在线数量，出力、备用和费用按代表机组及数量建模。保留累计启停窗口、正常与启停贡献的簇爬坡修正、在线备用与离线快启备用资格。
4. 用多种簇数求解并记录近似结果。原论文同时研究的“合并备用”“放松小机整数性”“用启动次数替代最小开停”是独立消融，默认不叠加，以免混淆加速来源。
5. 对调度用途，在完整原逐机 UC 中依据计数/总出力建议恢复身份和出力；异质容量使固定等式可能不可行，先释放冲突簇或改用偏差目标，再必要时完全释放。此为工程恢复流程，保留原约束与费用。

### 关键建模关系

#### 聚合模型与分组

§III将逐机二元状态替换为簇整数在线数，启动/停机连续量经状态转换与成本共同处理。单个状态等式并不能单独保证连续事件量为整数；在存在额外奖励、负费用或恢复用途时应检查事件量，必要时改成整数并标注适配。

簇正常运转核心数量为 $U_t-S_t$。式8b–9b：

$$
P_{t-1}-P_t\le(U_t-S_t)\mathrm{RD}-P^{\min}S_t+\max(P^{\min},\mathrm{RD})D_t
$$

$$
P_t-P_{t-1}\le(U_t-S_t)\mathrm{RU}-P^{\min}D_t+\max(P^{\min},\mathrm{RU})S_t
$$

这些式子修正聚合瞬时爬坡，但不恢复逐机分配历史。最小停机式11b用 $N-U$ 替换 $1-U$；在线备用式17b按 $UaP^{\max}$ 缩放，离线快启备用式18b按 $(N-U)a_{\mathrm{quickstart}}P^{\max}$。各级上下备用与能量共享容量，不能分别满额重复申报。

§III.C 四种分组层次：逐机；仅技术；技术加容量/年代/效率；同厂同技术。代表容量为成员平均，热耗、爬坡、最低出力等用容量加权技术特征。该描述未全面区分绝对量与比例，实施必须记录采用的单位，避免二次加权造成总容量/爬坡放大。

#### 恢复与保证边界

原文以代表机组描述近似灵活性，不交付按真实异质机组逐台恢复的通用定理。两台容量100、200 MW，代表容量150 MW、在线数量1、总出力140 MW时，可能存在可恢复身份但不能任意选择第一台；若原节点/最低出力/爬坡继续限制，也可能完全不可恢复。簇数量可用作恢复约束，但不能平均摊到离线机组上。

论文§III.D描述同质、线性热耗下聚合精确，其动态公式仍存在后续文献讨论的灵活性高估问题；本 skill 不沿用为无条件等价保证。精确性需要额外可分解条件，否则当作近似并在原模型检验。

原文最小开停时间累加写 $t-m$ 到t，共m+1个点；在实现中根据事件进入当前时段的统一定义核对持续时长，不能机械复制偏移。原文功率/能量单位随一小时网格混写，非小时成本与能量平衡须显式乘 Δt。原文提及 k-means 只是可选分组方式；按手工分组思想实现的确定性分位分层是仓库适配。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `stratify_units`
- **Description**: 当长期规划或运行仿真含大量相似但不完全相同的机组时，按技术与效率等分层形成代表机组，用整数数量近似 UC，并在原机组上恢复评估精度和总耗时。
- **实现范围**: 同技术类别内按单一特征稳定排序并等量分层；属于论文分组思路的工程实现。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回各簇的原机组记录列表；不计算代表参数，不求解聚合或恢复模型。

**完整流程输出与保证：**

输出分簇规则、成员、代表参数/离散程度、聚合解、原机组恢复解、各指标误差和原约束残差。异质分簇属于近似；聚合目标或界没有自动的原问题上下界意义。原文对相同机组的等价论述不能覆盖任意紧爬坡情形，必要时用 Knueven 的条件另作检查。

若恢复费用明显变差、备用不可交付或动态不可行，细分相关簇并重试；将失败与耗时一并报告，不只统计成功且加速的实例。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入逐机技术/燃料/厂址、容量 MW、最低负荷比例、热耗和成本、爬坡 MW/h或标幺/h、最小开停小时数、启动成本、备用资格/响应能力、初始历史、原时序需求和风电。必须先统一特征单位，不能把绝对 MW 与标幺比例混合平均。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "units",
    "groups"
  ],
  "properties": {
    "units": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "fuel",
          "technology"
        ],
        "properties": {
          "id": {
            "type": "string",
            "description": "唯一原机组 id。"
          },
          "fuel": {
            "type": "string",
            "description": "燃料类型；一次调用必须相同。"
          },
          "technology": {
            "type": "string",
            "description": "机组技术类型；一次调用必须相同。"
          },
          "heat_rate": {
            "type": "number",
            "description": "热耗，采用全体一致的单位，如 GJ/MWh。",
            "exclusiveMinimum": 0
          }
        }
      },
      "minItems": 1
    },
    "groups": {
      "type": "integer",
      "description": "目标子簇数，不能超过机组数。",
      "minimum": 1
    },
    "feature": {
      "type": "string",
      "description": "排序字段，必须存在于每条机组记录且为有限可比较数值。",
      "default": "heat_rate"
    }
  },
  "additionalProperties": false
}
```

默认 `feature=heat_rate` 时，每条记录都必须含 heat_rate；使用其他特征时须提供同名字段并统一单位。这种字段依赖由调用方显式检查。

---

## 3. 核心代码实现 (Python Implementation)

```python
def stratify_units(units, groups, feature="heat_rate"):
    if not units or type(groups) is not int or not 1 <= groups <= len(units):
        raise ValueError("invalid number of subclusters")
    if len({u["id"] for u in units}) != len(units):
        raise ValueError("duplicate unit id")
    if len({(u["fuel"], u["technology"]) for u in units}) != 1:
        raise ValueError("partition fuel and technology first")
    ordered = sorted(units, key=lambda u: (u[feature], str(u["id"])))
    n = len(ordered)
    return [ordered[j*n//groups:(j+1)*n//groups] for j in range(groups)]
```

代码是论文“按额外特征近似等量分组”的确定性工程实现，不是作者发布代码。对所得簇取平均容量和容量加权特征；爬坡建议先化为标幺/h，平均后乘代表容量恢复 MW/h，并明确标记这一步单位适配。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 重复 id、簇数越界或混合技术/燃料 | 抛出 ValueError；先按技术与燃料分大类。 |
| 排序特征缺失、非有限或单位不一致 | 在排序前拒绝该输入，不用默认零值替代。 |
| 异质簇恢复失败或费用/备用偏差过大 | 细分相关簇并重新恢复；统计失败和全部重试开销。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 把同技术燃机按热耗分成两组，保持每台机组恰好出现一次。

**调用说明**: 使用 `stratify_units` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "stratify_units",
  "units": [
    {
      "id": "a",
      "fuel": "gas",
      "technology": "CCGT",
      "heat_rate": 8
    },
    {
      "id": "b",
      "fuel": "gas",
      "technology": "CCGT",
      "heat_rate": 9
    },
    {
      "id": "c",
      "fuel": "gas",
      "technology": "CCGT",
      "heat_rate": 7
    },
    {
      "id": "d",
      "fuel": "gas",
      "technology": "CCGT",
      "heat_rate": 10
    }
  ],
  "groups": 2,
  "feature": "heat_rate"
}
```

**Observation**: 返回成员 [c,a] 和 [b,d]。随后从保留的原参数计算代表容量与加权特征，并在原机组约束上恢复；特征排序本身没有逐机可行性保证。

### 验证与后续对照实验

小测分层无重复无丢失、总容量守恒，并构造同簇两台容量不同导致固定在线数与固定总功率不能恢复的例子。后续使用相同实例、硬件、总预算和停止标准，报告预处理+聚合求解+恢复/重试+验证总耗时、原目标、有效界/gap、原可行性及变量数；同时比较能量结构、在线数量和出力差异，原模型包含排放时再报告排放。论文速度仅是历史证据，本次未运行全库实验。
