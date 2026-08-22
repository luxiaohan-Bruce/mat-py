# Zhai 2010 Theorem 5：解析判定 inactive 热稳

Qiaozhu Zhai, Xiaohong Guan, Jinghui Cheng, Hongyu Wu. *Fast Identification of Inactive Security Constraints in SCUC Problems.* IEEE Trans. Power Syst., 25(2), 2010.

## 算法解读

SCUC 里基态与 N-1 热稳行数按「线路 × 时段 × 事故」增长，但绝大多数行在整个可行域上永远碰不到限。作者把这种行叫 **inactive**：从约束集里删掉后，可行域不变（Definition 1/2）。这不是「某个最优解处互补松弛为 0」——那叫 binding，和 inactive 不是一回事。

充要判定（Theorem 1）要对每一行解一个 MILP，规模与原 SCUC 相当，本 skill 不做。作者把判定松成只保留「系统功率平衡 + 机组容量盒」的 LP（Theorem 3）：

```
(GLP)  max  α·p     s.t.  1ᵀp = D_t ,  0 ≤ p ≤ P̄
```

若 GLP 最优值不超过该侧热稳界，则原问题中该侧也碰不到限（充分条件）。盒子是论文 (19) 的 `0≤p≤P̄`：开机二进制已松弛，**不要用 Pmin**，也不要把爬坡、最小开停放进这个判定。负荷是一个点 `D_t`，不是区间。

Theorem 4–5 给出 GLP 的闭式。把 `α` 降序排列 `α_{i_1} ≥ α_{i_2} ≥ …`，找刚好装满负荷的边际机组下标 `k`（`Σ_{m<k} P̄_{i_m} < D_t ≤ Σ_{m≤k} P̄_{i_m}`）：

```
GLP2* = Σ_{m<k} (α_{i_m} − α_{i_k}) P̄_{i_m}  +  α_{i_k} D_t
```

`k=0`（第一台就装满）时就是 `α_{i_1} D_t`。下侧把 `α` 换成 `−α`。直流热稳写成 `f = α·p + β`（`β` 是负荷注入的截距）后：

- 上侧：`GLP2*(α) ≤ F − β` → 删 `α·p+β ≤ F`
- 下侧：`GLP2*(−α) ≤ F + β` → 删 `−(α·p+β) ≤ F`

`D_t ∉ [0, ΣP̄]` 时 GLP 不可行，该侧不删。判定充分非必要：爬坡等时序约束会让真可行域更小，所以 Theorem 5 删不掉的行必须留。IEEE 24-bus 上作者用 Theorem 5 解析标出绝大部分热稳，只剩少数线路需要进 SCUC。

**整段算法：**

1. 直流约定算 PTDF：`b=1/x`，忽略 tap/相移；`α_g = H_{bus[g]}`，`β = −H·Pd[:,t]`。事故场景把开断列从拓扑去掉，限额乘紧急因子。开断线、离线线 `f≡0`，不筛不加。
2. 只对 `status=1` 且 `Pmax>0` 的机构造 `P̄`。每个键 `(t, 事故, 线路)` 的两侧分别算 GLP2*。
3. 容差与功率残差同量级。`drop=true` 的一侧不要写进模型；两侧可只删一边。
4. 最终只建一次 MIP：原 UC（开机、爬坡、最小开停、目标）+ 每时段系统平衡 + 未删热稳的 PTDF 割。不要再为每个事故建 `theta`/`f`。

不要用于交流潮流或拓扑可变的 OTS（PTDF 会变）。净负荷是区间时不要套本闭式，那是 Ding 2020 的问题。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_inactive_thermal_zhai`
- **Description**: 用 Zhai 2010 Theorem 5 判定直流热稳哪一侧 inactive（删掉后，在「系统功率平衡 + 机组容量盒」下可行域不变）。输入该时段负荷、在役机组容量、线性潮流行 `f = α·p + β` 与限值 `F`，输出每一行上/下侧是否可删。在把热稳写进 UC/SCUC 之前调用。不要用于交流潮流或拓扑可变的开关问题，也不要把 `Pmin`、爬坡、最小开停放进本判定。本判定充分非必要：判不掉的行必须保留。

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
      "description": "在役机组容量上界 P̄。只放 status=1 且 Pmax>0 的机。单位与 demand、F 一致。"
    },
    "demand": {
      "type": "number",
      "description": "该时段系统负荷 D_t。必须 0 ≤ D_t ≤ sum(pmax)，否则 Theorem 5 前提不成立。"
    },
    "constraints": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "alpha", "F"],
        "properties": {
          "id": { "type": "string", "description": "调用方键，原样返回。" },
          "alpha": {
            "type": "array",
            "items": { "type": "number" },
            "description": "对机组出力的灵敏度，长度等于 pmax。负荷贡献放进 beta。"
          },
          "beta": { "type": "number", "default": 0, "description": "截距，通常 β = −H·Pd。默认 0。" },
          "F": { "type": "number", "description": "热稳限 F > 0。上侧 α·p+β ≤ F，下侧 −(α·p+β) ≤ F。" }
        }
      }
    },
    "tolerance": {
      "type": "number",
      "default": 1e-6,
      "description": "GLP2* 与限值比较容差，必须 ≥ 0。"
    }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

「该侧 inactive」松成 Theorem 3：`max α·p  s.t. 1ᵀp = D_t,  0 ≤ p ≤ P̄`。若最优值 ≤ `F−β`，上侧碰不到限。Theorem 4–5：`α` 降序，边际机组 `k` 装满 `D_t`，

```
GLP2* = Σ_{m<k} (α_{i_m} − α_{i_k}) P̄_{i_m}  +  α_{i_k} D_t
```

下侧把 `α` 换成 `−α`，界换成 `F+β`。论文 (19) 是 `0≤p≤P̄`，不要用 `Pmin`。

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
    """Theorem 5：max a·p s.t. 1ᵀp = dt, 0 ≤ p ≤ pbar。不可行返回 None。"""
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


def screen_inactive_thermal_zhai(
    pmax: list[float],
    demand: float,
    constraints: list[ThermalRow],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    pbar = np.asarray(pmax, dtype=float).ravel()
    if pbar.size == 0:
        return {"ok": False, "error": "Error: pmax 为空。请至少提供一台在役机组后重试。"}
    if np.any(~np.isfinite(pbar)) or not np.isfinite(demand):
        return {"ok": False, "error": "Error: pmax 或 demand 含 NaN/Inf，请检查数据后重试。"}
    if np.any(pbar < -1e-12):
        return {"ok": False, "error": "Error: pmax 含负数，容量上界必须 ≥ 0。"}
    if tolerance < 0:
        return {"ok": False, "error": "Error: tolerance 必须 ≥ 0。"}
    if not constraints:
        return {"ok": False, "error": "Error: constraints 为空，没有需要判定的热稳。"}

    cap_sum = float(np.maximum(pbar, 0.0).sum())
    if demand < -1e-12 or demand > cap_sum + 1e-9:
        return {
            "ok": False,
            "error": (
                f"Error: demand 必须落在 [0, sum(pmax)] 内，当前 demand={demand}, "
                f"sum(pmax)={cap_sum}。请检查是否误删在役机组，或核对负荷单位后重试。"
            ),
        }

    pbar = np.maximum(pbar, 0.0)
    n = pbar.size
    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        alpha = np.asarray(row.get("alpha", []), dtype=float).ravel()
        if alpha.size != n:
            return {
                "ok": False,
                "error": (
                    f"Error: constraints[{i}] id={cid} 的 alpha 长度 {alpha.size} "
                    f"与 pmax 长度 {n} 不一致。每个机组必须有一个灵敏度。"
                ),
            }
        if np.any(~np.isfinite(alpha)):
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 alpha 含 NaN/Inf。"}
        beta = float(row.get("beta", 0.0))
        F = float(row.get("F", float("nan")))
        if not np.isfinite(beta) or not np.isfinite(F):
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 beta/F 含 NaN/Inf。"}
        if F <= 0:
            return {
                "ok": False,
                "error": (
                    f"Error: constraints[{i}] id={cid} 的 F={F} ≤ 0。"
                    "热稳限必须为正。无额定的线路请先填默认限值后再调用。"
                ),
            }
        up = _greedy_glp2(alpha, pbar, demand)
        dn = _greedy_glp2(-alpha, pbar, demand)
        bound_up, bound_dn = F - beta, F + beta
        results.append(
            {
                "id": cid,
                "upper": {"drop": up is not None and up <= bound_up + tolerance, "glp2": up, "bound": bound_up},
                "lower": {"drop": dn is not None and dn <= bound_dn + tolerance, "glp2": dn, "bound": bound_dn},
            }
        )
    return {"ok": True, "results": results}
```

`drop=true` 的一侧不要写进模型；`drop=false` 必须保留。两侧可只删一边。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `pmax` 空 | `Error: pmax 为空。请至少提供一台在役机组后重试。` |
| `demand` 不在 `[0, ΣP̄]` | `Error: demand 必须落在 [0, sum(pmax)] 内，当前 demand=…, sum(pmax)=…。请检查是否误删在役机组，或核对负荷单位后重试。` |
| `alpha` 长度 ≠ `pmax` | `Error: constraints[i] id=… 的 alpha 长度 … 与 pmax 长度 … 不一致。每个机组必须有一个灵敏度。` |
| `F ≤ 0` | `Error: constraints[i] id=… 的 F=… ≤ 0。热稳限必须为正。无额定的线路请先填默认限值后再调用。` |
| NaN/Inf / `tolerance<0` / 空 `constraints` | 对应 `Error: …` 字符串 |

`ok=false` 时一行都不删。擦边（`glp2` 略大于 `bound`）一律 `drop=false`。不要把 `u`、`Pmin`、爬坡放进本函数。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 三台在役机容量 100/80/50 MW，负荷 150 MW。线路灵敏度 `[0.3, 0.1, -0.2]`，β=5 MW，F=20 MW。哪些侧可以不写进 UC？

**Thought**: 线性热稳 + 容量盒 + 系统平衡，调用 `screen_inactive_thermal_zhai`。

**Action**:

```json
{
  "tool": "screen_inactive_thermal_zhai",
  "pmax": [100, 80, 50],
  "demand": 150,
  "constraints": [{"id": "t=0,c=base,ell=7", "alpha": [0.3, 0.1, -0.2], "beta": 5.0, "F": 20.0}]
}
```

**Observation**: 上侧 GLP2\*=35 > 15 → 保留；下侧 GLP2\*=−4 ≤ 25 → 可删。建模只加 `α·p + β ≤ F`。
