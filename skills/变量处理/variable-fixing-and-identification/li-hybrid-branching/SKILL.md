---
name: li-hybrid-branching
description: >-
  按机组容量、时序、最低技术出力费用和可靠性信息设计 SCUC 的 UPHB 分支策略，用于可修改求解器内部的研究接入；需要动态候选、全局界和伪成本信息，普通静态分支优先级不等同于论文方法。
---

# Li：SCUC 定制化混合分支 UPHB

李佩杰、葛佳伟、袁沐琛、徐胜男。《求解安全约束机组组合的定制化混合分支方法》。电工技术学报，41(11)，2026.

## 算法解读

CHR 先比较容量加权的可靠性分数，再比较时段；ACR 先限制最早时段，再比较最低出力费用与分数解形成的双向分数。UPHB 在两条规则之间按全局 gap 改善情况切换，并仅对所选候选执行必要的强分支。候选评分是完整状态机的一部分。

该方法改变分支搜索顺序，论文在 HiGHS 1.6.0 内部实现。需要访问节点 LP 解、开停机变量身份、全局上下界、已探索节点数、伪成本/可靠性计数及强分支入口。首次接入阅读 [关键建模关系](#关键建模关系)。

本仓库默认使用 Gurobi；本 skill 提供算法设计与数学片段，不安装、编译或替换求解器。目标后端必须先确认上述能力，缺失则返回“不支持完整 UPHB”。静态 `BranchPriority` 或仅容量排序只能作为独立消融，不能标成论文复现。

**整段算法：**

1. 保留原模型，建立稳定的 $u_{g,t}$ 身份映射。论文只优先选择当前 LP 解为分数的开停机变量。
2. 主规则 CHR：按 $\frac{P^{\max}}{P_{\mathrm{base}}}\max(s^{\mathrm{RB}},\epsilon)$ 降序，再按时段升序选择。
3. 次规则 ACR：先限制在最早时段，再最大化 $\max(C^{p\min}x,\epsilon)\max(C^{p\min}(1-x),\epsilon)$。两条规则的排序顺序不同。
4. 按下文的 Algorithm 1 状态机切换：主规则在节点窗口内继续执行；窗口结束且 gap 未改善，短暂切到次规则；次规则窗口结束后回到主规则。
5. 选出候选后才检查其双向可靠性；若任一方向计数小于 $\eta_{\mathrm{rel}}$，对该变量执行强分支。不要先给所有启动/停机变量做强分支。
6. 分支仍创建完备的左右子域，保留求解器的传播、剪枝和界更新。**工程适配**：没有分数 $u$ 而其他整数变量仍分数时，回到后端合法默认分支，不能宣布节点整数可行。
7. 在相同后端比较默认可靠性分支、CHR 单规则、ACR 单规则及完整 UPHB，保存每种规则选择次数、强分支开销和切换记录。

### 关键建模关系

#### 完整切换伪代码

保存 `main=true`、节点锚点 $n_{\mathrm{anchor}}$、参考 gap $g_{\mathrm{old}}$。在分支开始且有有限正上界时初始化。

论文式 (34)–(35)：

$$
g=(UB-LB)/UB,\quad h=100g,\quad
N_1=wN_{bus}\exp(h-1),\quad 0<w<1.
$$

1. 更新 $N_1$，读取节点计数 $n$ 和全局 gap $g$。
2. 主规则状态下，若 $n_{\mathrm{anchor}}<n<n_{\mathrm{anchor}}+N_1$，使用 CHR。否则更新 $n_{\mathrm{anchor}}=n$；若 $g_{\mathrm{old}}>g$，令 $g_{\mathrm{old}}=g$ 并继续 CHR，否则切到次规则并使用 ACR。
3. 次规则状态下，若 $n_{\mathrm{anchor}}<n<n_{\mathrm{anchor}}+\alpha N_1$，继续 ACR；否则更新 $n_{\mathrm{anchor}}=n$、$g_{\mathrm{old}}=g$，切回主规则并使用 CHR。
4. 选出候选后检查 $\min(\eta_+,\eta_-)<\eta_{\mathrm{rel}}$；不可靠时仅对该候选执行强分支，再交还正常分支与传播流程。

节点计数是整数、窗口可为实数；复现保持原严格区间比较。工程上可以对窗口取整/设上限及 gap 改善容差，但必须记录规则变化并做单独消融。浮点指数溢出风险出现时降级，不能产生无效索引或无限循环。

**已核对 PDF 第 6–7 页**：图 1/2 的两个排序顺序、式 (33) 的乘积、Algorithm 1 的 ACR、式 (34) 指数 $h-1$。正文另用 AVR 表示平均费用规则，与算法 ACR 名称不一致；此 skill 统一称 ACR，算法含义不变。文中的“局部最优”是作者对搜索停滞的描述，不能解释为正确 B&C 已失去全局保证。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `choose_uphb`
- **Description**: 按机组容量、时序、最低技术出力费用和可靠性信息设计 SCUC 的 UPHB 分支策略，用于可修改求解器内部的研究接入；需要动态候选、全局界和伪成本信息，普通静态分支优先级不等同于论文方法。
- **实现范围**: CHR/ACR 候选选择；完整 UPHB 依赖 HiGHS 内部状态机、可靠性计数和强分支入口。 本文件中的 Tool Name 对应下方 Python 函数，尚未注册为仓库工具。
- **函数返回**: 返回候选变量 id；没有分数开停机候选时返回 None，由后端继续选择其他整数变量。

**完整流程输出与保证：**

输出本节点候选变量、使用的规则、是否需要强分支、更新后的切换状态与统计日志。最终调度和最优性结论仍由完整求解器及原约束验证产生。

---

## 2. 输入参数定义 (Parameter Schema)

**完整方法的输入与单位：**

| 输入 | 含义 |
|---|---|
| 候选变量映射 | 原变量到预处理后列的对应，类型、机组 $g$、时段 $t$、当前分数值 $x$ |
| `pmax,pbase` | 最大容量及公共基准，均为 MW |
| `cpmin` | 最低技术出力对应的时段费用，不是成本曲线斜率 |
| `rb` 与可靠性状态 | 来自求解器分支历史的可靠性分支评分与双向计数 |
| `UB,LB,nodes,nbus` | 全局界、已探索节点数、节点总数；另给 `w,alpha,eta_rel` 和容差 |

**核心函数参数：** 下述 Schema 描述局部计算输入；原 UC 构建器、求解器状态及恢复过程由完整流程接入。

```json
{
  "type": "object",
  "required": [
    "candidates",
    "rule",
    "pbase"
  ],
  "properties": {
    "candidates": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "kind",
          "g",
          "t",
          "x",
          "pmax",
          "rb",
          "cpmin"
        ],
        "properties": {
          "id": {
            "type": "string",
            "description": "稳定变量标识。"
          },
          "kind": {
            "type": "string",
            "description": "u 表示开停机变量；其他类型交给后端默认规则。"
          },
          "g": {
            "type": "integer",
            "description": "机组索引，同分时稳定排序。",
            "minimum": 0
          },
          "t": {
            "type": "integer",
            "description": "时段索引。",
            "minimum": 0
          },
          "x": {
            "type": "number",
            "description": "当前节点 LP 值；仅分数 u 参与选择。",
            "minimum": 0,
            "maximum": 1
          },
          "pmax": {
            "type": "number",
            "description": "容量，MW。",
            "exclusiveMinimum": 0
          },
          "rb": {
            "type": "number",
            "description": "求解器可靠性分支评分。"
          },
          "cpmin": {
            "type": "number",
            "description": "最低技术出力对应的时段费用。",
            "minimum": 0
          }
        }
      }
    },
    "rule": {
      "type": "string",
      "description": "当前选取规则，由完整状态机决定。",
      "enum": [
        "CHR",
        "ACR"
      ]
    },
    "pbase": {
      "type": "number",
      "description": "公共容量基准，MW。",
      "exclusiveMinimum": 0
    },
    "eps": {
      "type": "number",
      "description": "评分下限，按论文数值尺度使用。",
      "exclusiveMinimum": 0,
      "default": 1e-06
    },
    "int_tol": {
      "type": "number",
      "description": "整数容差。",
      "minimum": 0,
      "exclusiveMaximum": 0.5,
      "default": 1e-06
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

def choose_uphb(candidates, rule, pbase, eps=1e-6, int_tol=1e-6):
    if not isfinite(pbase) or pbase <= 0 or rule not in ("CHR", "ACR"):
        raise ValueError("invalid scale or rule")
    if not 0 < eps or not 0 <= int_tol < 0.5:
        raise ValueError("invalid tolerance")
    pool = []
    for c in candidates:
        if c["kind"] != "u":
            continue
        if not all(isfinite(c[k]) for k in ("x", "pmax", "rb", "cpmin")):
            raise ValueError("non-finite candidate")
        if c["pmax"] <= 0 or c["cpmin"] < 0:
            raise ValueError("unsupported capacity or cost")
        if int_tol < c["x"] < 1 - int_tol:
            pool.append(c)
    if not pool:
        return None  # 交还后端默认分支，不表示所有整数变量已整数化。
    if rule == "CHR":
        return min(pool, key=lambda c: (
            -(c["pmax"] / pbase) * max(c["rb"], eps), c["t"], c["g"]))["id"]
    return min(pool, key=lambda c: (
        c["t"], -max(c["cpmin"] * c["x"], eps)
        * max(c["cpmin"] * (1 - c["x"]), eps), c["g"]))["id"]
```

片段只验证候选选择，不实现求解器回调、规则切换或完整分支定界。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 处理 |
|------|------|
| 没有可选分数 u | 返回 None；不代表当前节点所有整数变量均已整数化。 |
| 缺少后端候选、强分支或状态访问能力 | 返回“不支持完整 UPHB”；普通参数或静态优先级仅可单列为消融。 |
| 变量身份映射或全局界不可靠 | 使用后端默认分支并记录降级，不猜变量身份或窗口。 |

`UB` 不存在、不为正或上下界非有限时，不计算论文指数窗口；使用后端默认策略并记录降级。原式适用于正目标值；负费用实例需要另行标注的归一化设计。预处理映射丢失时也降级，不能猜变量名。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 当前使用 CHR，在较晚的大容量机组与较早的小容量机组之间选择分支候选。

**调用说明**: 使用 `choose_uphb` 验证本例的局部计算；完整优化流程仍按“算法解读”执行。

**Action**:

```json
{
  "tool": "choose_uphb",
  "candidates": [
    {
      "id": "late",
      "kind": "u",
      "g": 0,
      "t": 2,
      "x": 0.5,
      "pmax": 500,
      "rb": 2,
      "cpmin": 10
    },
    {
      "id": "early",
      "kind": "u",
      "g": 1,
      "t": 1,
      "x": 0.4,
      "pmax": 100,
      "rb": 1,
      "cpmin": 5
    }
  ],
  "rule": "CHR",
  "pbase": 100
}
```

**Observation**: 返回 late。相同候选改用 ACR 时返回 early，因为 ACR 先限制最早时段。两种结果仅验证候选排序；完整策略还需状态切换和强分支接入。

### 验证与后续对照实验

同一 `rb` 下，大容量机组即使时段较晚也可被 CHR 先选；ACR 则必须先选最早时段，再比较费用评分。用这两种情况检查排序没有颠倒，并测试整数候选、非 $u$ 变量及空候选集。

后续以相同实例、硬件、线程、种子、预算和 gap 测试，报告含元数据建立、全部强分支、搜索及验证的总耗时、目标/有效界、节点数和原约束残差。分支不改变模型，整数变量总数通常不会减少。完整搜索的保证来自后端正确性，不来自经验评分；未完成搜索不能称为全局最优。
