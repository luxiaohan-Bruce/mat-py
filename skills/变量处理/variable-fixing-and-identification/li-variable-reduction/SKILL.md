---
name: li-variable-reduction
description: >-
  依据 Li 等人的 d-UC-LP 与阈值距离对 UC/SCUC 开停机变量排序和启发式固定，用于减少原多时段 MIP 的二进制变量；需要保持原问题全部约束并验证解，不适用于声称固定必然保留全局最优解。
---

# Li：基于单时段拉格朗日对偶的变量缩减

Xuan Li, Qiaozhu Zhai, Jingxuan Zhou, Xiaohong Guan. *A Variable Reduction Method for Large-Scale Unit Commitment.* IEEE Transactions on Power Systems, 35(1), 2020.

## 算法解读

对偶 LP 给出每台机组的有效经济系数 $\beta$。在线成本为 $ap+b$ 时，比较关机的零成本与最小、最大出力处成本，得到 $y=\min\{0,(a+\beta)P^{\min}+b,(a+\beta)P^{\max}+b\}$；$y<0$ 对应开机候选。阈值 $\beta^0=\max\{-a-b/P^{\max},-a-b/P^{\min}\}$ 到 $\beta$ 的距离只用于固定优先级，不能证明跨时段固定正确。

对二进制开停机变量很多的线性或凸分段线性 UC/SCUC，先解各时段的对偶 LP，按经济阈值距离固定部分 $u_{g,t}$，再求解保留全部时间耦合约束的原模型副本。固定是启发式；单时段解本身不是可行调度。

首次接入前阅读 [关键建模关系](#关键建模关系)，特别是乘子符号、分段成本扩展和零阈值歧义。

**整段算法：**

1. 在副本上构造每个时段的 s-UC：去掉跨时段约束和非负启动费用，再按下文公式构造 d-UC-LP。启用其他放松前，核实它确实放宽原可行域且保持下界方向。
2. 求解 LP 并检查乘子、$y$ 的有效性；异常时保留该时段变量，不用失败结果进行固定或计算认证下界。
3. 用 $\beta=-\lambda_0\mathbf 1+\mathrm{PTDF}^{\mathsf T}(\lambda^+-\lambda^-)$、阈值 $\beta^0$ 与 $\lvert\beta-\beta^0\rvert$ 排序。状态从单机最小值 $y$ 读取；临界距离在容差内的变量保留自由。
4. 按全体原始 $GT$ 的 $\lfloor\mathrm{PDR}\,GT\rfloor$ 数量上限选变量。原有强制开停条件优先；与它冲突的候选不固定。保存原始上下界，只在副本增加固定。
5. 在完整原目标和全部约束下求解。只有恢复完整调度并通过原约束验证的 incumbent 才是结果。
6. **工程回退**：固定子问题不可行时撤回置信度最低的一半固定，直到零固定；单次无 incumbent 的超时不等于不可行。所有重试共享总预算，预算用尽就返回实际状态。可用已验证 incumbent 热启动未固定模型。
7. 需要原问题最优性证明时，使用原模型有效界，或取消固定继续完整搜索。固定子问题的 `ObjBound`/gap 只属于受限子问题。

### 关键建模关系

#### 数学机制

论文 §III.A 的 s-UC 去掉爬坡、最小开停等耦合约束并省略启动费用。对每个时段，令负荷总量为 $D$，负荷在第 $\ell$ 条安全约束的贡献为 $h_\ell=\sum_k\Gamma^D_{\ell k}d_k$。采用式 (14) 的乘子符号：

$$
\beta_i=-\lambda_0+\sum_l(\lambda_l^+-\lambda_l^-)\Gamma^U_{li},\quad
 g_l^+=-h_l-F_l,\quad g_l^-=h_l-F_l.
$$

$\lambda_0$ 自由，$\lambda^+$、$\lambda^-$ 非负；平衡项在拉格朗日函数中是 $\lambda_0(D-\sum_i p_i)$。不能直接把求解器原始行对偶不经符号核对代入。

单机在线成本 $a_i p_i+b_i$，关机成本为零。式 (29)–(30) 给出

$$
y_i=\min\{0,(a_i+\beta_i)\underline P_i+b_i,
(a_i+\beta_i)\overline P_i+b_i\}.
$$

因此式 (38)–(42) 是以下显式 LP：

$$
\max_{\lambda,y}\ \sum_i y_i+\lambda_0D+
\sum_l(\lambda_l^+g_l^++\lambda_l^-g_l^-),
$$

约束为 $\lambda^{\pm}\ge0$，$y_i\le0$，以及 $y_i$ 分别不超过两个在线端点表达式。$y_i$ 必须允许负值，不能沿用优化建模库的非负变量默认界。无需次梯度循环，也不能用“先解普通连续 LP 再四舍五入”代替该构造。

#### 固定判据和边界

式 (43)–(44)：

$$
\beta_i^0=\max\{-a_i-b_i/\overline P_i,-a_i-b_i/\underline P_i\},
\quad \Delta\beta_{it}=|\beta_{it}-\beta_i^0|.
$$

Algorithm 1 按全体 `(i,t)` 的距离降序取 PDR 比例，再求完整 UC。距离是启发式可信程度，不是安全变量固定的充分条件。

**原文歧义已对照 PDF 印刷页 265（文件第 5 页）**：式 (31) 与 Algorithm 1 将 $y=0$ 对应停机，而 §III.C 的文字用 $\beta\le\beta^0$ 对应开机，等号处不一致。入口采用 $y$ 规则，并把距离在容差内的变量留自由；这是明确的数值适配。

附录的凸分段线性成本可统一写为：对包含两端点的每个成本断点 $P_j$ 添加 $y_i\le C_i(P_j)+\beta_iP_j$，同时 $y_i\le0$。当所有 $P_j>0$ 时阈值是 $\max_j[-C_i(P_j)/P_j]$。$P_j=0$ 的在线截距项须单独处理；若它使在线/离线不能由有限阈值区分，就跳过距离固定，不进行除零。不能以一条平均线代替分段成本并仍宣称原方法的界。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `rank_fixings`
- **Description**: 依据 Li 等人的 d-UC-LP 与阈值距离对 UC/SCUC 开停机变量排序和启发式固定，用于减少原多时段 MIP 的二进制变量；需要保持原问题全部约束并验证解，不适用于声称固定必然保留全局最优解。
- **实现范围**: 线性成本候选评分与固定清单；不包含 d-UC-LP、受限 UC 或撤回固定后的求解。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回按阈值距离降序排列的 `{id,value,margin}` 列表；临界变量不固定，列表可能少于比例上限。

**完整流程输出与保证：**

输出固定映射、排序分数、实际固定数、未固定原模型上的有效下界、完整调度、原约束残差、求解状态与分阶段耗时。无可行调度时返回失败状态和已尝试比例，不能输出近似二进制向量冒充解。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

| 输入 | 含义 |
|---|---|
| 原 UC 构建器与变量映射 | 保留目标、初始状态、最小开停时间、爬坡、备用及全部网络约束；稳定标识 `(g,t)` |
| `pmin,pmax,cost` | MW；每时段费用的线性系数或凸分段成本断点。所有时段按各自时长换算成本 |
| `demand,PTDF,F` | 节点负荷 MW、相应网络与事故的灵敏度、线路界 MW |
| `pdr` | 要固定的比例 `[0,1]`，必须在实验配置中明确，不沿用论文 70% 为通用默认 |
| 容差与总时间预算 | 沿用基线的可行性/整数容差；经济阈值容差另记单位与数值 |

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "rows",
    "pdr"
  ],
  "properties": {
    "rows": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "a",
          "b",
          "pmin",
          "pmax",
          "beta"
        ],
        "properties": {
          "id": {
            "type": "string",
            "description": "唯一变量标识，JSON 调用使用字符串，如 u[0,0]。"
          },
          "a": {
            "type": "number",
            "description": "时段线性成本系数，货币/MW，已经乘该时段小时数。"
          },
          "b": {
            "type": "number",
            "description": "在线固定费用，货币/时段。"
          },
          "pmin": {
            "type": "number",
            "description": "最低稳定出力，MW；此片段要求大于零。",
            "exclusiveMinimum": 0
          },
          "pmax": {
            "type": "number",
            "description": "最大出力，MW，且不小于 pmin。",
            "exclusiveMinimum": 0
          },
          "beta": {
            "type": "number",
            "description": "对偶有效经济系数，单位与 a 相同。"
          }
        }
      }
    },
    "pdr": {
      "type": "number",
      "description": "按全部输入行数计算的固定比例。",
      "minimum": 0,
      "maximum": 1
    },
    "margin_tol": {
      "type": "number",
      "description": "阈值距离容差，单位与 beta 相同。",
      "minimum": 0,
      "default": 1e-08
    }
  },
  "additionalProperties": false
}
```

数值输入须有限；数组尺寸、单位和跨字段关系除 Schema 外，还须按代码与上文前提核验。

---

## 3. 核心代码实现 (Python Implementation)

以下是纯 Python 数学片段，不是已注册工具，也不包括 LP 或 UC 求解器。

```python
from math import isfinite, floor

def rank_fixings(rows, pdr, margin_tol=1e-8):
    # 每行: id=(g,t), a, b, pmin, pmax, beta。
    if not isfinite(pdr) or not 0 <= pdr <= 1:
        raise ValueError("pdr must be in [0,1]")
    if not isfinite(margin_tol) or margin_tol < 0:
        raise ValueError("invalid margin tolerance")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate variable id")
    ranked = []
    for r in rows:
        a, b, lo, hi, beta = (r[k] for k in
                              ("a", "b", "pmin", "pmax", "beta"))
        if not all(isfinite(x) for x in (a, b, lo, hi, beta)):
            raise ValueError("non-finite input")
        if not 0 < lo <= hi:
            raise ValueError("this threshold requires 0 < pmin <= pmax")
        beta0 = max(-a - b / hi, -a - b / lo)
        margin = abs(beta - beta0)
        y = min(0.0, (a + beta) * lo + b, (a + beta) * hi + b)
        if margin > margin_tol:
            ranked.append({"id": r["id"], "value": int(y < 0),
                           "margin": margin})
    # 同分时保持输入次序，输入应按(g,t)稳定排列。
    ranked.sort(key=lambda r: -r["margin"])
    return ranked[:floor(pdr * len(rows))]
```

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 参数非有限、重复 id 或比例越界 | 抛出 ValueError；本轮不应用固定。 |
| 阈值相等或距离在容差内 | 保留自由，不用任意破同分决定开停。 |
| 固定后的完整 UC 不可行 | 撤回低置信度固定并重试；全部重试共享原预算。受限问题的 gap 不能作为原问题 gap。 |

$P^{\min}=0$、非凸成本或未定义的分段断点不适用上述评分片段；按原单机子问题求值并重新推导阈值，无法完成则跳过该变量。候选冲突或验证失败时撤回固定，不改变原问题限制。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 给三台候选变量计算固定方向，第三台刚好位于阈值，保留它自由。

**调用说明**: 使用 `rank_fixings` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "rank_fixings",
  "rows": [
    {
      "id": "u[0,0]",
      "a": 10,
      "b": 20,
      "pmin": 10,
      "pmax": 100,
      "beta": -12
    },
    {
      "id": "u[0,1]",
      "a": 10,
      "b": 20,
      "pmin": 10,
      "pmax": 100,
      "beta": -9
    },
    {
      "id": "u[0,2]",
      "a": 10,
      "b": 20,
      "pmin": 10,
      "pmax": 100,
      "beta": -10.2
    }
  ],
  "pdr": 1.0
}
```

**Observation**: 返回 $u_{0,0}\to1$、$u_{0,1}\to0$，距离分别约为 1.8、1.2；$u_{0,2}$ 不在清单中。下一步在保留全部约束的原 UC 副本中验证这两个固定。

### 验证与后续对照实验

先测阈值两侧与相等、正负截距、$\mathrm{PDR}=0$、固定造成最小开机时间冲突及回退到零固定。基线与加速方法使用相同实例、硬件、线程、种子、总预算和停止标准。报告 LP 预处理、固定、全部重试、最终求解与验证的总耗时、目标值、原问题有效 gap、固定比例与模型规模；论文耗时仅作原文证据，不当作本仓库实测。
