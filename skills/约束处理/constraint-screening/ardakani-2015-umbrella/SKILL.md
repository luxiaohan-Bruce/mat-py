---
name: ardakani-2015-umbrella
description: >-
  在固定拓扑 DC 发电调度、SCOPF 或 SCUC 的求解前，使用 P-UCD 在机组容量盒与功率平衡上判定冗余线路热稳约束；用于保留可行域的约束筛选，不筛最小开停机逻辑。
---

# Ardakani 2015：Partial UCD 判定非 umbrella 热稳

Ali Jahanbani Ardakani, François Bouffard. *Acceleration of Umbrella Constraint Discovery in Generation Scheduling Problems.* IEEE Trans. Power Syst., 30(4), 2015.

## 算法解读

**Umbrella constraint**（Definition 1）：删掉会改变可行域的行。Binding（最优处积极）一定是 umbrella，但 umbrella 不一定在最优处 binding——还取决于目标函数。UCD 的目标是找出支撑可行域的那一小撮行，而不是找出某个最优解的积极集。

全文 UCD：对每一行找一个落在该超平面上、且满足其余约束的点；找不到就对该行加松弛 $s_j$，$s_j>0$ 说明它不是 umbrella。对偶形式的规模随原问题行数平方增长，本 skill **不要建这个巨型对偶**。

本文提出 **partial UCD (P-UCD)**：把约束分成

- $J_v$：经验上几乎都是 umbrella 的子集——机组容量 + 系统功率平衡
- $J_n$：潜在非 umbrella——线路热稳

**Lemma 1**：一条约束相对某个约束子集已经是非 umbrella，相对全集也是非 umbrella。因此只需在 $J_v$ 上判定 $J_n$ 里的每一行。IEEE 118 的 SCOPF 上作者观察到绝大多数线路限相对这个 $J_v$ 都不是 umbrella。作者也指出：这个松弛与 Zhai Theorem 3 同一结构，这里用的是 LP / umbrella 语言。

筛 LP（二进制已松成容量盒，筛程里没有 $u$）：

$$
\begin{aligned}
\max/\min\quad & f=\alpha^{\mathsf T}p+\beta\\
\text{s.t.}\quad &0\le p\le P^{\max},\\
&\mathbf1^{\mathsf T}p=D_t.
\end{aligned}
$$

$\max f\le F$ → 上侧非 umbrella，可删；$\min f\ge-F$ → 下侧可删。这条 LP 可用 Zhai 的贪心闭式解，不必调求解器。不要把其它线路限放进筛 LP——那是更紧的 UCD，不再是本文的 P-UCD。也不要用本方法去筛最小开停等 UC 逻辑行，那些几乎都是 umbrella。

**整段算法：**

1. 构造 $J_v$：在役机 $\overline P$ 与该时段 $D_t$（须 $0\le D_t\le\sum_g\overline P_g$，否则 $J_v$ 本身不可行，热稳全留）。
2. $J_n$ 里每一条热稳两侧解上述 max/min。
3. 非 umbrella 的一侧不写进模型。
4. 最终 MIP：UC + 系统平衡 + 留下的 PTDF 割。

这是「可行域支撑」口径。若还想删「可行域用得着、但最优费用下用不到」的行，那是 Porras 的费用上界，不是 umbrella。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_umbrella_pucd`
- **Description**: 用 Ardakani 2015 的 partial UCD（P-UCD）判定直流热稳是否为非 umbrella：相对子集 $J_v$ = {机组容量盒, 系统平衡} 已非 umbrella，则相对全集也非 umbrella（Lemma 1）。对每条热稳解 $\max/\min\;f=\alpha^{\mathsf T}p+\beta$ 于该子集；碰不到限则可删。不要建全文 UCD 的巨型对偶，不要把其它线路限放进筛 LP，不要指望用本工具删最小开停等 UC 逻辑行。筛程里二进制松成容量盒 $0\le p\le P^{\max}$，没有 $u$。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["pmax", "demand", "constraints"],
  "properties": {
    "pmax": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 1,
      "description": "在役机组容量上界。J_v 中的盒子。关机机关不要放入。"
    },
    "demand": {
      "type": "number",
      "description": "该时段系统负荷 D_t。必须 0 ≤ D_t ≤ sum(pmax)。"
    },
    "constraints": {
      "type": "array",
      "minItems": 1,
      "description": "潜在非 umbrella 集 J_n：待判定的线路限。",
      "items": {
        "type": "object",
        "required": ["id", "alpha", "F"],
        "properties": {
          "id": { "type": "string" },
          "alpha": { "type": "array", "items": { "type": "number" }, "description": "长度等于 pmax。" },
          "beta": { "type": "number", "default": 0 },
          "F": { "type": "number", "description": "F > 0。" }
        }
      }
    },
    "tolerance": { "type": "number", "default": 1e-6 }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

P-UCD 筛 LP（与 Zhai Theorem 3 同一结构，可用闭式代替求解器）：

$$
\begin{aligned}
\max/\min\quad & f=\alpha^{\mathsf T}p+\beta\\
\text{s.t.}\quad &0\le p\le P^{\max},\\
&\mathbf1^{\mathsf T}p=D_t.
\end{aligned}
$$

$\max f\le F$ → 删上侧；$\min f\ge-F$ → 删下侧。这是相对 $J_v$ 的非 umbrella，不是「某最优处 binding」。

```python
from __future__ import annotations

from typing import Any, TypedDict

import numpy as np


class ThermalRow(TypedDict, total=False):
    id: str
    alpha: list[float]
    beta: float
    F: float


def _greedy_glp2(a: np.ndarray, pbar: np.ndarray, dt: float) -> float | None:
    """max a·p s.t. 1ᵀp = dt, 0 ≤ p ≤ pbar。"""
    if dt < -1e-12 or dt > float(pbar.sum()) + 1e-9:
        return None
    if a.size == 0:
        return 0.0 if abs(dt) <= 1e-12 else None
    order = np.argsort(-a, kind="mergesort")
    a_s, p_s = a[order], pbar[order]
    k = int(np.searchsorted(np.cumsum(p_s), dt, side="left"))
    k = min(k, len(a_s) - 1)
    if k == 0:
        return float(a_s[0] * dt)
    return float(np.dot(a_s[:k] - a_s[k], p_s[:k]) + a_s[k] * dt)


def screen_umbrella_pucd(
    pmax: list[float],
    demand: float,
    constraints: list[ThermalRow],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    pbar = np.asarray(pmax, float).ravel()
    if pbar.size == 0:
        return {"ok": False, "error": "Error: pmax 为空。J_v 至少要有一台在役机组。"}
    if not np.isfinite(demand) or np.any(~np.isfinite(pbar)):
        return {"ok": False, "error": "Error: pmax 或 demand 含 NaN/Inf。"}
    if np.any(pbar < -1e-12) or tolerance < 0:
        return {"ok": False, "error": "Error: pmax 必须 ≥ 0 且 tolerance ≥ 0。"}
    if not constraints:
        return {"ok": False, "error": "Error: constraints 为空，J_n 没有待判定的线路限。"}
    cap_sum = float(np.maximum(pbar, 0.0).sum())
    if demand < -1e-12 or demand > cap_sum + 1e-9:
        return {
            "ok": False,
            "error": (
                f"Error: demand 必须落在 [0, sum(pmax)] 内，当前 demand={demand}, "
                f"sum(pmax)={cap_sum}。J_v 的平衡约束不可行，请核对机组集合后重试。"
            ),
        }
    pbar = np.maximum(pbar, 0.0)
    n = pbar.size
    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        alpha = np.asarray(row.get("alpha", []), float).ravel()
        if alpha.size != n:
            return {
                "ok": False,
                "error": f"Error: constraints[{i}] id={cid} 的 alpha 长度 {alpha.size} 与 pmax 长度 {n} 不一致。",
            }
        beta = float(row.get("beta", 0.0))
        F = float(row.get("F", float("nan")))
        if not np.isfinite(beta) or not np.isfinite(F) or F <= 0:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 F 必须为正有限数。"}
        up = _greedy_glp2(alpha, pbar, demand)
        dn = _greedy_glp2(-alpha, pbar, demand)
        # max f = up + β ； min f = −dn + β
        results.append(
            {
                "id": cid,
                "upper": {
                    "drop": up is not None and up + beta <= F + tolerance,
                    "max_f": None if up is None else up + beta,
                    "F": F,
                },
                "lower": {
                    "drop": dn is not None and -dn + beta >= -F - tolerance,
                    "min_f": None if dn is None else -dn + beta,
                    "F": -F,
                },
            }
        )
    return {"ok": True, "results": results}
```

不要把其它线路限放进 $J_v$（那是更紧的 UCD，不是本工具的 P-UCD）。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `demand` 超出容量盒 | `Error: demand 必须落在 [0, sum(pmax)] 内… J_v 的平衡约束不可行，请核对机组集合后重试。` |
| `alpha` 长度不对 | `Error: constraints[i] id=… 的 alpha 长度 … 与 pmax 长度 … 不一致。` |
| $F\le0$ | `Error: … F 必须为正有限数。` |
| 想做全文 UCD | 不要对本工具加「把全部线路放进筛 LP」的参数；那不是 P-UCD。 |

`ok=false` 或 LP/闭式不可行：该行保留。不要用本工具筛 UC 逻辑约束。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 要找相对「容量盒 + 功率平衡」已经不可能支撑可行域的线路限。三机 100/80/50，$D=150$，某线 $\alpha=[0.3,0.1,-0.2]$，$\beta=5$，$F=20$。

**Thought**: 这是 P-UCD 的 $J_n$ 判定，调用 `screen_umbrella_pucd`。不要建全文对偶 UCD。

**Action**:

```json
{
  "tool": "screen_umbrella_pucd",
  "pmax": [100, 80, 50],
  "demand": 150,
  "constraints": [{"id": "ell=7", "alpha": [0.3, 0.1, -0.2], "beta": 5.0, "F": 20.0}]
}
```

**Observation**: $\max f=40>20$ → 上侧仍可能是 umbrella，保留；$\min f=1\ge-20$ → 下侧非 umbrella，可删。
