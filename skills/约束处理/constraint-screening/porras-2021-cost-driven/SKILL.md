---
name: porras-2021-cost-driven
description: >-
  在具有线性生产费用的确定性 DC-UC 或 SCUC 中，向筛选 LP 加入有效费用上界，识别最优性意义下可省略的热稳约束；需要可证明有效的费用上界，经验费用裕量本身不提供保证。
---

# Porras 2021：费用上界下筛非积极热稳

Álvaro Porras, Salvador Pineda, Juan M. Morales, Asunción Jiménez-Cordero. *Cost-driven Screening of Network Constraints for the Unit Commitment Problem.* IEEE Trans. Power Syst., 2023.

## 算法解读

技术可行域上的 $\max/\min$ 潮流（文中方法 (2)，也就是 Zhai/P-UCD 那类）只能删 **冗余** 行：删了可行域不变。还有一类约束：可行域用得着，但在最优费用附近用不到，作者叫 **inactive**（与 Zhai 的 inactive 用词不同，这里强调目标）。文 Fig. 1 两节点例子：贵机与负荷不在同一侧，费用最优时线路永远不会堵，但纯技术 LP 仍认为贵机可以满发、线路可能堵。

**方法 UB**（文 (3)）在筛 LP 里加一条费用上界：

$$
\begin{aligned}
\max/\min\quad &\alpha^{\mathsf T}p+\beta\\
\text{s.t.}\quad &\mathbf1^{\mathsf T}p=D_t,\\
&0\le p\le P^{\max},\\
&c^{\mathsf T}p\le\overline C.
\end{aligned}
$$

$\overline C$ 必须是 UC 最优费用的 valid 上界。文中用历史 1-quantile 回归 $C(D)$；没有历史 UC 费用序列时，用铜板 UC（只含开机逻辑 + 系统平衡）的最优费用乘 $(1+\epsilon)$，默认 $\epsilon=0.05$。$\epsilon$ 保证 $\overline C$ 仍是上界：太小可能误删，最终 MIP 出现热稳违反时加大 $\epsilon$ 再筛。

$\max f\le F$ 删上侧，$\min f\ge-F$ 删下侧。筛 LP 不要放开机变量 $u$（与 Zhai 一样松成容量盒）。线性费用用 $c_g$；二次项不要塞进这个筛 LP。

**方法 CC** 把净负荷限制在历史样本的凸组合里，抓住空间相关。没有历史净负荷矩阵时不要实现 CC，也不要用单条 `load_mult` 假装凸包。

**整段算法：**

1. 解铜板 UC，得每时段费用 $C_{\mathrm{cp},t}$，令 $\overline C_t=(1+\epsilon)C_{\mathrm{cp},t}$。
2. 对每个 `(t, 事故, 线路)` 两侧解 UB 筛 LP（事故用对应 PTDF 行）。
3. 非最优 / 不可行 → 该侧保留。
4. 最终 MIP：UC + 系统平衡 + 留下的 PTDF 割。若留下的热稳仍被违反，加大 $\epsilon$ 从步骤 1 重来，不要在筛 LP 里加 $u$。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_cost_driven_porras`
- **Description**: 用 Porras 2021 方法 UB：在「容量盒 + 系统平衡 + 线性生产费用 $\le\overline C$」上对 $\max/\min\;(\alpha^{\mathsf T}p+\beta)$ 做筛 LP。碰不到限的一侧是费用意义下的 inactive（可行域可能用得着，最优费用下用不到）。$\overline C$ 必须是 UC 最优费用的 valid 上界；没有历史费用时用铜板 UC 费用 × $(1+\epsilon)$，默认 $\epsilon=0.05$。不要实现文中的方法 CC / 分位回归（需要历史净负荷凸组合）。筛 LP 不要放开机变量 $u$。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["pmax", "demand", "cost", "cost_ub", "constraints"],
  "properties": {
    "pmax": { "type": "array", "items": { "type": "number" }, "description": "在役机组容量上界。" },
    "demand": { "type": "number", "description": "该时段负荷 D_t，0 ≤ D_t ≤ sum(pmax)。" },
    "cost": {
      "type": "array",
      "items": { "type": "number" },
      "description": "线性生产费用系数 c_g，长度等于 pmax。二次项不要塞进本筛 LP。"
    },
    "cost_ub": {
      "type": "number",
      "description": "该时段费用上界 C̄。必须 ≥ 铜板最优费用。典型取 (1+ε)·C_copperplate，ε=0.05。"
    },
    "constraints": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "alpha", "F"],
        "properties": {
          "id": { "type": "string" },
          "alpha": { "type": "array", "items": { "type": "number" } },
          "beta": { "type": "number", "default": 0 },
          "F": { "type": "number" }
        }
      }
    },
    "tolerance": { "type": "number", "default": 1e-6 }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

方法 UB（文 (3)）：

$$
\begin{aligned}
\max/\min\quad &\alpha^{\mathsf T}p+\beta\\
\text{s.t.}\quad &\mathbf1^{\mathsf T}p=D_t,\\
&0\le p\le P^{\max},\\
&c^{\mathsf T}p\le\overline C.
\end{aligned}
$$

$\max f\le F$ 删上侧；$\min f\ge-F$ 删下侧。筛 LP 非最优 → 保留。

```python
from __future__ import annotations

from typing import Any, TypedDict

import numpy as np
from scipy.optimize import linprog


class ThermalRow(TypedDict, total=False):
    id: str
    alpha: list[float]
    beta: float
    F: float


def _opt_flow(
    alpha: np.ndarray,
    pmax: np.ndarray,
    cost: np.ndarray,
    demand: float,
    cost_ub: float,
    maximize: bool,
) -> float | None:
    """线性筛 LP；失败返回 None（调用方保留该侧）。"""
    n = alpha.size
    c = -alpha if maximize else alpha
    A_eq = np.ones((1, n))
    A_ub = cost.reshape(1, -1)
    bounds = [(0.0, float(pmax[i])) for i in range(n)]
    res = linprog(
        c,
        A_ub=A_ub,
        b_ub=[cost_ub],
        A_eq=A_eq,
        b_eq=[demand],
        bounds=bounds,
        method="highs",
    )
    if not res.success:
        return None
    val = float(res.fun)
    return -val if maximize else val


def screen_cost_driven_porras(
    pmax: list[float],
    demand: float,
    cost: list[float],
    cost_ub: float,
    constraints: list[ThermalRow],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    pbar = np.asarray(pmax, float).ravel()
    cvec = np.asarray(cost, float).ravel()
    if pbar.size == 0 or cvec.size != pbar.size:
        return {"ok": False, "error": "Error: cost 长度必须等于 pmax，且 pmax 非空。"}
    if np.any(pbar < -1e-12) or np.any(cvec < -1e-12):
        return {"ok": False, "error": "Error: pmax 与 cost 必须 ≥ 0。"}
    if not np.isfinite(demand) or not np.isfinite(cost_ub) or tolerance < 0:
        return {"ok": False, "error": "Error: demand / cost_ub / tolerance 非法。"}
    cap_sum = float(np.maximum(pbar, 0.0).sum())
    if demand < -1e-12 or demand > cap_sum + 1e-9:
        return {
            "ok": False,
            "error": (
                f"Error: demand 必须落在 [0, sum(pmax)] 内，当前 demand={demand}, "
                f"sum(pmax)={cap_sum}。"
            ),
        }
    cmin = float(np.min(cvec) * demand)
    if cost_ub + 1e-9 < cmin:
        return {
            "ok": False,
            "error": (
                f"Error: cost_ub={cost_ub} 小于可能的最低线性费用 {cmin}。"
                "请改用铜板 UC 费用×(1+ε) 或加大 ε 后重试。"
            ),
        }
    if not constraints:
        return {"ok": False, "error": "Error: constraints 为空。"}

    pbar = np.maximum(pbar, 0.0)
    n = pbar.size
    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        alpha = np.asarray(row.get("alpha", []), float).ravel()
        if alpha.size != n:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 alpha 长度与 pmax 不一致。"}
        beta = float(row.get("beta", 0.0))
        F = float(row.get("F", float("nan")))
        if not np.isfinite(F) or F <= 0:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 F 必须为正。"}
        mx = _opt_flow(alpha, pbar, cvec, demand, cost_ub, True)
        mn = _opt_flow(alpha, pbar, cvec, demand, cost_ub, False)
        max_f = None if mx is None else mx + beta
        min_f = None if mn is None else mn + beta
        results.append(
            {
                "id": cid,
                "upper": {"drop": max_f is not None and max_f <= F + tolerance, "max_f": max_f, "F": F},
                "lower": {"drop": min_f is not None and min_f >= -F - tolerance, "min_f": min_f, "F": -F},
            }
        )
    return {"ok": True, "results": results}
```

$\overline C$ 由调用方提供：先解铜板 UC（只含开机逻辑 + 系统平衡），$\overline C_t=(1+\epsilon)C_{\mathrm{cp},t}$。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `cost` 长度不对 | `Error: cost 长度必须等于 pmax，且 pmax 非空。` |
| `cost_ub` 过小 | `Error: cost_ub=… 小于可能的最低线性费用 …。请改用铜板 UC 费用×(1+ε) 或加大 ε 后重试。` |
| 筛 LP 非最优 | 该侧 `drop=false`（不是整次调用失败） |
| 想做方法 CC | `Error: 本工具不实现历史凸组合 CC。没有历史净负荷时不要调用 CC。`（不要伪造样本） |

$\epsilon$ 过小导致可行解违反热稳：加大 $\epsilon$ 再筛，不要在筛 LP 里放 $u$。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两机 $P^{\max}=[100,100]$，线性费用 10 与 100，$D=80$。铜板最优费用 800，取 $\epsilon=0.05$ 故 $\overline C=840$。线路几乎只对贵机灵敏 $\alpha=[0, 0.9]$，$\beta=0$，$F=50$。费用最优下会堵吗？

**Thought**: 技术可行域上贵机可以满发，费用上界会把它压住。走方法 UB。

**Action**:

```json
{
  "tool": "screen_cost_driven_porras",
  "pmax": [100, 100],
  "demand": 80,
  "cost": [10, 100],
  "cost_ub": 840,
  "constraints": [{"id": "ell=1", "alpha": [0.0, 0.9], "beta": 0.0, "F": 50.0}]
}
```

**Observation**: 费用约束下 $p_2\le0.444$，$\max f\approx0.4\le50$ → 上侧可删。
