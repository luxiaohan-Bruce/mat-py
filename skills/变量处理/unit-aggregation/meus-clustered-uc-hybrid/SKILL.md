---
name: meus-clustered-uc-hybrid
description: >-
  当大量相似机组导致 UC 整数规模过大、且需要最终逐机调度时，先解 CUC，再以簇在线数量约束原逐机 UC；适用于可承担恢复求解的优化加速试验。
---

# Meus：聚合 UC 与逐机 UC 的两阶段混合求解

Jelle Meus, Kris Poncelet, Erik Delarue. Applicability of a Clustered Unit Commitment Model in Power System Modeling. IEEE Transactions on Power Systems, 2018.

## 算法解读

第一阶段 CUC 用簇在线整数数量 $U_{c,t}$ 替代逐机开停。第二阶段回到原逐机 UC，用 $\sum_{i\in c}u_{i,t}=U_{c,t}$ 连接簇数量，重新决定机组身份与出力；快启机不固定。即使参数相同，普通 CUC 也可能借用单机无法交付的爬坡，第二阶段是方法本身的一部分。

用于包含大量相似热机的 UC/规划运行子问题。相同参数也不能保证普通 CUC 的动态可行性。读取[关键建模关系](#关键建模关系)后实施。

**整段算法：**

1. 按技术和运行参数分簇；本仓库适配优先要求同一节点、兼容初始状态，快启机独立分组。保存逐机参数，簇参数采用论文均值近似时明确记录误差来源。
2. 用整数在线、启动、停机数量替代簇内二元变量，保留累计最小开停时间、启停出力、簇功率及爬坡约束，求解 CUC。总功率和在线数量是不同量，容量不能重复乘簇大小。
3. 取得整数簇在线轨迹后，在完整原逐机 UC 中加入 $\sum_{i\in c}u_{i,t}=U_{c,t}$。论文不固定快启机的状态；恢复问题仍决定机组身份、启动/停机和逐机出力。
4. 求解恢复问题并在原机组、原时段和原网络上检查功率、备用、爬坡、最小开停时间、初值以及原目标。仅验证通过的结果作为可行上界。
5. 恢复不可行时按诊断释放相关簇/时段的数量等式，再逐步释放到完整 UC；超时且无可行解时返回未恢复，不把超时标成不可行。此释放流程是工程适配，计入同一预算。

### 关键建模关系

#### 原方法与两种误差

§II–III 的 BUC 使用逐机二元变量，CUC 使用 $0\le U,V,W\le N_c$ 的整数数量及均值参数。本文事件记号为 $U_{t+1}=U_t+V_t-W_t$，成本为能量与空载费用乘时长，加启动/停机次数费用。

簇模型包括 $N_c-U_t\ge\sum_zW_{t-z}$（式16，过去 MDT 个时段）以及：

- 式17：$P_{t+1}-P_t\le(U_t-W_t)\mathrm{RU}-P^{\min}W_t+\mathrm{SU}\,V_t$。
- 式18：$P_t-P_{t+1}\le(U_t-W_t)\mathrm{RD}-P^{\min}V_t+\mathrm{SD}\,W_t$。
- 启动和停机能力分别约束 $P_t\le P^{\max}U_t-(P^{\max}-\mathrm{SU})V_{t-1}$ 与 $P_t\le P^{\max}U_t-(P^{\max}-\mathrm{SD})W_t$。

这里的 SU/SD 为启动/停机允许出力，不是正常爬坡。对每小时数据改变分辨率时须重新定义这些量及最小开停机窗口。

§V.B 用三种模型区分误差：真实逐机 BUC；先把每簇参数替换为均值、仍逐机建模的“虚构同质 BUC”；最终 CUC。前两者差异是异质聚类误差，后两者差异是聚合公式误差。不能把所有偏差都解释成求解器 gap。

#### 聚合可行但逐机不可行的明确反例

§IV.A 表I–II：两台相同机组，$P^{\min}=200$ MW，$P^{\max}=350$ MW，$\mathrm{RU}=\mathrm{RD}=50$ MW/时段，$\mathrm{SU}=\mathrm{SD}=250$ MW，$\mathrm{MUT}=\mathrm{MDT}=1$；需求依次 700、700、600、350 MW。普通 CUC 接受在线数量 2、2、2、1。

要在时段3后停一台，该机时段3须不超过250 MW，因 $\mathrm{RD}=50$，其时段2不超过300 MW，另一台不超过350 MW，所以时段2最多650 MW。需求700 MW无法满足，论文 BUC 通过50 MW失负荷得到解。禁止失负荷的原模型应报告该轨迹不可恢复。把时段3两机均分成300 MW不能修复停机限制。

§IV.B 表III–IV还说明最小开机时间会锁定究竟哪一台可停机：需求400、400、650、650、650、400、400、400 MW，$\mathrm{MUT}=4$。计数模型丢失身份后可能高估最大可发出力。表III MinerU 把 SD 和 MUT 的列粘连；已对照原 PDF 第5页确认 $P^{\min}=200$、$P^{\max}=400$ MW，$\mathrm{RU}=35$、$\mathrm{RD}=30$ MW/时段，$\mathrm{SU}=250$、$\mathrm{SD}=290$ MW，$\mathrm{MUT}=\mathrm{MDT}=4$时段，不能采用“2904”作为功率。本 skill 的确定性验证使用第一反例。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `count_couplings`
- **Description**: 当大量相似机组导致 UC 整数规模过大、且需要最终逐机调度时，先解 CUC，再以簇在线数量约束原逐机 UC；适用于可承担恢复求解的优化加速试验。
- **实现范围**: 生成第二阶段数量耦合行描述；不创建或求解 CUC/逐机 UC。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回 `(ids,t,n)` 列表；建模器据此在原 UC 中增加数量等式。

**完整流程输出与保证：**

输出簇映射、近似参数、CUC 解、数量耦合与释放日志、恢复后的逐机解和残差、原目标及原模型有效下界。普通 CUC 的界在使用异质均值后未必是原问题下界；恢复子问题的求解器 gap 也不是原 UC gap。混合流程是启发式，完整恢复的可行性不等于原问题全局最优性。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

输入原逐机模型、簇到机组的映射、初始状态与持续时间、功率上下限 MW、爬坡 MW/时段、启停功率 MW、最小开停机时段数、边际成本 货币/MWh、空载成本 货币/h、启停成本 货币/次及每时段小时数。标明允许的失负荷及惩罚，不能在恢复时自行引入。

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "groups",
    "counts"
  ],
  "properties": {
    "groups": {
      "type": "object",
      "description": "簇 id 到原机组 id 的不重叠映射。",
      "additionalProperties": {
        "type": "array",
        "items": {
          "type": "string",
          "description": "机组 id。"
        },
        "minItems": 1,
        "uniqueItems": true
      }
    },
    "counts": {
      "type": "object",
      "description": "同名簇的在线数量序列，时域应一致；值须在 1e-6 内接近合法整数。",
      "additionalProperties": {
        "type": "array",
        "items": {
          "type": "number",
          "description": "簇在线数量，范围 0 到簇大小。",
          "minimum": 0
        }
      }
    },
    "exempt": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "快启机 id；必须单独分组。"
      },
      "default": []
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

下面返回求解器无关的行描述；建模器据此建立等式。它不能代替第二阶段 UC。

```python
def count_couplings(groups, counts, exempt=()):
    exempt = set(exempt)
    seen, rows = set(), []
    for c, ids in groups.items():
        ids = tuple(ids)
        if not ids or len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("clusters must form disjoint nonempty groups")
        seen.update(ids)
        if exempt.intersection(ids):
            if not set(ids) <= exempt:
                raise ValueError("split fast-starting and other units first")
            continue
        for t, value in enumerate(counts[c]):
            n = round(value)
            if abs(value - n) > 1e-6 or not 0 <= n <= len(ids):
                raise ValueError("invalid integer cluster count")
            rows.append((ids, t, n))
    return rows
```

接入伪代码：`for ids,t,n in rows: original.add(sum(u[i,t] for i in ids)==n)`；调用前统一事件索引，本论文启动/停机发生在 $t\to t+1$。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 簇为空、成员重复或跨簇重叠 | 抛出 ValueError。 |
| 快启机与其他机组混在一簇 | 先拆簇；不能只跳过该簇中的一部分机组。 |
| 数量非整数、越界或恢复不可行 | 拒绝无效数量；恢复失败时释放相关数量等式，必要时回退完整原 UC。 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两台普通机组的簇在线数量为 2、1，生成逐机 UC 的数量耦合。

**调用说明**: 使用 `count_couplings` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "count_couplings",
  "groups": {
    "c": [
      "a",
      "b"
    ]
  },
  "counts": {
    "c": [
      2,
      1
    ]
  },
  "exempt": []
}
```

**Observation**: 返回 ((a,b),0,2) 与 ((a,b),1,1)，对应 $u_{a,0}+u_{b,0}=2$、$u_{a,1}+u_{b,1}=1$。恢复求解还需确定第二时段是哪台开机，并验证停机与爬坡。

### 验证与后续对照实验

先用下文的两机四时段反例检查：簇调度可行但逐机受停机功率与下降爬坡限制，不能直接输出。再做原 UC、CUC+恢复对照，使用相同实例、硬件、求解预算和停止标准；计时包含分簇、两次求解、释放重试、恢复和验证。报告原目标、有效下界/gap、原问题可行性、失负荷及变量数变化。论文案例的速度不代表本仓库结果，本次未运行全库实验。
