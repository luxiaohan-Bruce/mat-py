---
name: he-2025-vertex-guided
description: >-
  当 DC-UC 或 SCUC 的线路安全约束数量远多于连续出力变量时，在有效外包出力盒上用顶点引导公式批量筛选冗余热稳约束；可使用 LP 收紧界或保守容量界，无需枚举顶点。
---

# He 2025：顶点引导批量判定冗余热稳

Xuan He, Yuxin Pan, Yize Chen, Danny H.K. Tsang. *Vertex-Guided Redundant Constraints Identification for Unit Commitment.* 预印本， 2025.

## 算法解读

经典 LFGS（line-flow-guided screening）对每条热稳解一次 $\max/\min\;f$，LP 次数跟「线路 × 事故 × 时段 × 两侧」走。当热稳行数远大于机组变量数时，重复解这些只差目标行的 LP 很浪费。

本文把锚点改到 **变量顶点**。先对每个连续变量 $y_p=P_{g,t}$（筛程里 $u$ 已松弛）在 UC-LP 可行域上解 $\max y_p$ 和 $\min y_p$，得到外包超矩形 $[\underline y,\overline y]$。LP 次数跟 $\lvert G\rvert T$ 走，与线路数无关。某个界 LP 非最优，该坐标保持 $[0,P^{\max}]$。

**Theorem 1**：线性不等式 $a^{\mathsf T}y\le b$ 若被这个超矩形的全部顶点满足，则相对盒子冗余，因而相对原 UC 可行域也冗余。

不必枚举 $2^{\lvert P\rvert}$ 个顶点。**Theorem 2** 一次矩阵运算：盒子上 $a^{\mathsf T}y$ 的最大值是正系数走上界、负系数走下界，

$$
\begin{aligned}
\omega_j&=\sum_p\left[\max(a_{jp},0)\overline y_p+\min(a_{jp},0)\underline y_p\right]-b_j,\\
\omega_j&<0\quad\Longrightarrow\quad\text{删除约束 }j.
\end{aligned}
$$

热稳上侧：$a=\alpha$，$b=F-\beta$（判定 $\alpha^{\mathsf T}p+\beta\le F$）。下侧：$a=-\alpha$，$b=F+\beta$。事故场景用去掉开断列的 PTDF，限额乘紧急因子。

这是充分条件：$\omega\ge0$ 只说明盒子碰得到，不说明真 UC 碰得到，该侧必须留。可选第二遍 LFGS（EOVL）把 VGS 的子集补全到与逐线筛相同；本 skill 默认只做 Theorem 2。文中 S5–S7 的 NN/KNN **不要实现**。

**整段算法：**

1. （可选）在 UC-LP 松弛上对每个 $P_{g,t}$ 解界 LP，得到 `y_lo, y_hi`。
2. 对每条热稳两侧算 $\omega$，$\omega<0$ 则删。
3. 最终 MIP：UC + 系统平衡 + 留下的 PTDF 割。

没有界 LP 时用 $[0,P^{\max}]$，更保守、少删，算法仍正确。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_vertex_guided_he2025`
- **Description**: 先得到机组出力外包超矩形 $[\underline y,\overline y]$，再用 He 2025 Theorem 2 一次矩阵运算判定线性热稳相对该盒子是否冗余：$\omega_j<0$ 则删。不要枚举 $2^{\lvert P\rvert}$ 个顶点。不要实现文中 S5–S7 的 NN/KNN。界向量可由界 LP 得到；没有界 LP 时用 $[0,P^{\max}]$（更保守，少删）。在写热稳进 UC 之前调用。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["y_lo", "y_hi", "constraints"],
  "properties": {
    "y_lo": {
      "type": "array",
      "items": { "type": "number" },
      "description": "各机组（当前时段）出力下界。与 alpha 对齐。"
    },
    "y_hi": {
      "type": "array",
      "items": { "type": "number" },
      "description": "各机组出力上界。必须逐元素 ≥ y_lo。"
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
    "tolerance": { "type": "number", "default": 0, "description": "ω<0 的判定可写成 ω < -tolerance。" }
  }
}
```

界 LP（可选，调用方预先算好 `y_lo/y_hi`）：对每个 $P_{g,t}$ 在 UC-LP 松弛（平衡、容量、爬坡）上 $\max/\min$；非最优则该坐标保持 $[0,P^{\max}]$。

---

## 3. 核心代码实现 (Python Implementation)

Theorem 1：线性不等式被超矩形全部顶点满足 ⇒ 相对盒子冗余 ⇒ 相对 UC 冗余。Theorem 2 不必枚举顶点：

$$
\begin{aligned}
\omega_j&=\sum_p\left[\max(a_{jp},0)\overline y_p+\min(a_{jp},0)\underline y_p\right]-b_j,\\
\omega_j&<0\quad\Longrightarrow\quad\text{删除约束 }j.
\end{aligned}
$$

上侧 $a=\alpha$，$b=F-\beta$；下侧 $a=-\alpha$，$b=F+\beta$。

```python
from __future__ import annotations

from typing import Any, TypedDict

import numpy as np


class ThermalRow(TypedDict, total=False):
    id: str
    alpha: list[float]
    beta: float
    F: float


def _omega(a: np.ndarray, y_lo: np.ndarray, y_hi: np.ndarray, b: float) -> float:
    a_pos = np.maximum(a, 0.0)
    a_neg = np.minimum(a, 0.0)
    return float(a_pos @ y_hi + a_neg @ y_lo) - b


def screen_vertex_guided_he2025(
    y_lo: list[float],
    y_hi: list[float],
    constraints: list[ThermalRow],
    tolerance: float = 0.0,
) -> dict[str, Any]:
    lo = np.asarray(y_lo, float).ravel()
    hi = np.asarray(y_hi, float).ravel()
    if lo.size == 0 or lo.size != hi.size:
        return {"ok": False, "error": "Error: y_lo 与 y_hi 必须非空且等长。"}
    if np.any(~np.isfinite(lo)) or np.any(~np.isfinite(hi)):
        return {"ok": False, "error": "Error: y_lo/y_hi 含 NaN/Inf。"}
    if np.any(lo > hi + 1e-12):
        return {"ok": False, "error": "Error: 存在 y_lo > y_hi。请先修正界 LP 结果或回退到 [0, Pmax] 后重试。"}
    if tolerance < 0:
        return {"ok": False, "error": "Error: tolerance 必须 ≥ 0。"}
    if not constraints:
        return {"ok": False, "error": "Error: constraints 为空。"}
    n = lo.size
    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        alpha = np.asarray(row.get("alpha", []), float).ravel()
        if alpha.size != n:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 alpha 长度与 y_lo 不一致。"}
        beta = float(row.get("beta", 0.0))
        F = float(row.get("F", float("nan")))
        if not np.isfinite(F) or F <= 0:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 F 必须为正。"}
        w_up = _omega(alpha, lo, hi, F - beta)
        w_dn = _omega(-alpha, lo, hi, F + beta)
        results.append(
            {
                "id": cid,
                "upper": {"drop": w_up < -tolerance, "omega": w_up},
                "lower": {"drop": w_dn < -tolerance, "omega": w_dn},
            }
        )
    return {"ok": True, "results": results}
```

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| $\mathtt{y\_lo}>\mathtt{y\_hi}$ | `Error: 存在 y_lo > y_hi。请先修正界 LP 结果或回退到 [0, Pmax] 后重试。` |
| 长度不一致 | `Error: y_lo 与 y_hi 必须非空且等长。` / alpha 对齐 |
| 界 LP 非最优 | 调用方把该坐标设为 $[0,P^{\max}]$，不要把失败界传进来 |
| 想用 NN 补全 | 不要调用；本工具只做 Theorem 2 |

$\omega\ge0$ 一律保留（充分条件）。不要枚举顶点。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两机当前时段界 `[0,80]` 与 `[10,50]`。线路 $\alpha=[0.2, -0.1]$，$\beta=5$，$F=40$。盒子顶点会不会碰到限？

**Thought**: 行数多于机组变量，用 Theorem 2 算 ω，不要对这条线再解 $\max f$ LP。

**Action**:

```json
{
  "tool": "screen_vertex_guided_he2025",
  "y_lo": [0, 10],
  "y_hi": [80, 50],
  "constraints": [{"id": "t=0,ell=3", "alpha": [0.2, -0.1], "beta": 5.0, "F": 40.0}]
}
```

**Observation**: 上侧盒子最大 $0.2\times80+(-0.1)\times10=15$，$\omega=15-(40-5)=-20<0$ → 可删。
