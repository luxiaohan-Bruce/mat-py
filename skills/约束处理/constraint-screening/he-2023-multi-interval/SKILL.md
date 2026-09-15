---
name: he-2023-multi-interval
description: >-
  在负荷已知、至少两个时段且具有爬坡耦合的 DC-UC 或 SCUC 中，用覆盖全时域的连续松弛 LP 筛选冗余热稳约束；要求筛选中的爬坡关系是原模型的有效松弛，不使用预测开机分支。
---

# He 2023：带跨时段爬坡的热稳筛选 LP

Xuan He, Jiayu Tian, Yufan Zhang, Honglin Wen, Yize Chen. *Fast Constraint Screening for Multi-Interval Unit Commitment.* 预印本， 2023.

## 算法解读

单时段筛（Zhai / Porras）把每个 $t$ 的出力盒子当成独立的。多时段 UC 有爬坡：负荷从 $t$ 降到 $t+1$ 时，机组来不及把出力全部打到某条灵敏线上，该时段线路限在真可行域上已经 inactive，但单时段筛仍认为满容量可以堵。文 Fig. 2 三节点例子就是这种情况。

**Corollary 1**（本 skill 实现的部分）：负荷 $P_{d,t}$ 已知，把开机松成 $u\in[0,1]$，筛 LP 覆盖整条时间轴：

$$
\begin{aligned}
\max/\min\quad & f_{\ell,t}=\alpha^{\mathsf T}P_{:,t}+\beta\\
\text{s.t.}\quad &P_g^{\min}u_{g,\tau}\le P_{g,\tau}\le P_g^{\max}u_{g,\tau} &&\forall g,\tau,\\
&0\le u_{g,\tau}\le1 &&\forall g,\tau,\\
&P_{g,\tau}-P_{g,\tau-1}\le\mathrm{RU}_g &&\forall g,\tau,\\
&P_{g,\tau-1}-P_{g,\tau}\le\mathrm{RD}_g &&\forall g,\tau,\\
&\sum_gP_{g,\tau}=D_\tau &&\forall\tau.
\end{aligned}
$$

$\max f\le F$ 删上侧，$\min f\ge-F$ 删下侧。这是 sample-aware、二进制松弛后的多时段充分条件：删掉的行对原可行域仍安全。爬坡链必须覆盖全部时段，禁止退回「只对时段 $t$ 做无爬坡盒子」。爬坡用问题里的 $\mathrm{RU},\mathrm{RD}$，不要发明单独的启停爬坡（本仓库基线 UC 也没有 $R^{\mathrm{su}},R^{\mathrm{sd}}$）。

**Corollary 2–3** 用预测开机 $\widehat u$ 再收紧盒子。那是文中的 ML 分支，**不要实现**；也不要把一次全模型求得的真实开机当成「预测」塞回来。

筛 LP 非最优 → 该侧保留。$T=1$ 或没有爬坡数据时不要走本算法。

**整段算法：**

1. 确认 $T\ge2$，准备 $P^{\min},P^{\max},\mathrm{RU},\mathrm{RD},(D_t)_{t=0}^{T-1}$。
2. 对每个热稳键的两侧各解一个上述 LP（被筛的是时段 $t$ 的潮流，约束仍含所有 $\tau$）。
3. 最终 MIP：带完整 UC 逻辑的原问题 + 留下的 PTDF 割。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_multi_interval_he2023`
- **Description**: 多时段、负荷已知时，用 He 2023 Corollary 1 的筛 LP：二进制松成 $u\in[0,1]$，约束含 $P^{\min}u\le P_g\le P^{\max}u$、系统平衡、以及时段间爬坡，对指定时段的 $f=\alpha^{\mathsf T}P_{:,t}+\beta$ 做 $\max/\min$。碰不到限则该侧可删。不要实现 Corollary 2–3 的预测开机 $\widehat u$（文中 ML）。单时段或没有爬坡数据时不要调用，改用 `screen_inactive_thermal_zhai`。筛 LP 非最优则保留。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["pmin", "pmax", "ru", "rd", "demand", "t", "constraints"],
  "properties": {
    "pmin": { "type": "array", "items": { "type": "number" }, "description": "机组 Pmin，长度 nG。" },
    "pmax": { "type": "array", "items": { "type": "number" }, "description": "机组 Pmax，长度 nG。" },
    "ru": { "type": "array", "items": { "type": "number" }, "description": "向上爬坡 RU。" },
    "rd": { "type": "array", "items": { "type": "number" }, "description": "向下爬坡 RD。" },
    "demand": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 2,
      "description": "各时段系统负荷，长度 T≥2。"
    },
    "t": { "type": "integer", "description": "被筛热稳所在时段，0 ≤ t < T。" },
    "constraints": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "alpha", "F"],
        "properties": {
          "id": { "type": "string" },
          "alpha": { "type": "array", "items": { "type": "number" }, "description": "对 nG 台机的灵敏度。" },
          "beta": { "type": "number", "default": 0 },
          "F": { "type": "number" }
        }
      }
    },
    "tolerance": { "type": "number", "default": 1e-6 }
  }
}
```

爬坡链至少覆盖全部 $T$ 个时段，不要退回单时段无爬坡 LP。不要发明单独的启停爬坡。

---

## 3. 核心代码实现 (Python Implementation)

$$
\begin{aligned}
\max/\min\quad & f_{\ell,t}=\alpha^{\mathsf T}P_{:,t}+\beta\\
\text{s.t.}\quad &P_g^{\min}u_{g,\tau}\le P_{g,\tau}\le P_g^{\max}u_{g,\tau} &&\forall g,\tau,\\
&0\le u_{g,\tau}\le1 &&\forall g,\tau,\\
&P_{g,\tau}-P_{g,\tau-1}\le\mathrm{RU}_g &&\forall g,\tau,\\
&P_{g,\tau-1}-P_{g,\tau}\le\mathrm{RD}_g &&\forall g,\tau,\\
&\sum_gP_{g,\tau}=D_\tau &&\forall\tau.
\end{aligned}
$$

$S^*\le F$（上侧）或 $S^*\ge-F$（下侧）则删。

```python
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linprog


def _solve_lp(
    alpha: np.ndarray,
    beta: float,
    maximize: bool,
    pmin: np.ndarray,
    pmax: np.ndarray,
    ru: np.ndarray,
    rd: np.ndarray,
    demand: np.ndarray,
    t: int,
) -> float | None:
    nG, T = pmax.size, demand.size
    # 变量布局: Pg[g,τ] 共 nG*T，u[g,τ] 共 nG*T
    n_p, n_u = nG * T, nG * T
    n = n_p + n_u

    def pg(g: int, tau: int) -> int:
        return g * T + tau

    def uu(g: int, tau: int) -> int:
        return n_p + g * T + tau

    c = np.zeros(n)
    sign = -1.0 if maximize else 1.0
    for g in range(nG):
        c[pg(g, t)] = sign * alpha[g]

    bounds = [(0.0, None)] * n
    A_ub, b_ub, A_eq, b_eq = [], [], [], []

    for g in range(nG):
        for tau in range(T):
            bounds[pg(g, tau)] = (0.0, float(pmax[g]))
            bounds[uu(g, tau)] = (0.0, 1.0)
            row = np.zeros(n)  # Pg - Pmax u ≤ 0
            row[pg(g, tau)] = 1.0
            row[uu(g, tau)] = -float(pmax[g])
            A_ub.append(row)
            b_ub.append(0.0)
            row = np.zeros(n)  # Pmin u - Pg ≤ 0
            row[pg(g, tau)] = -1.0
            row[uu(g, tau)] = float(pmin[g])
            A_ub.append(row)
            b_ub.append(0.0)
        for tau in range(1, T):
            row = np.zeros(n)  # Pg_τ - Pg_{τ-1} ≤ RU
            row[pg(g, tau)] = 1.0
            row[pg(g, tau - 1)] = -1.0
            A_ub.append(row)
            b_ub.append(float(ru[g]))
            row = np.zeros(n)  # Pg_{τ-1} - Pg_τ ≤ RD
            row[pg(g, tau - 1)] = 1.0
            row[pg(g, tau)] = -1.0
            A_ub.append(row)
            b_ub.append(float(rd[g]))

    for tau in range(T):
        row = np.zeros(n)
        for g in range(nG):
            row[pg(g, tau)] = 1.0
        A_eq.append(row)
        b_eq.append(float(demand[tau]))

    res = linprog(
        c,
        A_ub=np.asarray(A_ub),
        b_ub=np.asarray(b_ub),
        A_eq=np.asarray(A_eq),
        b_eq=np.asarray(b_eq),
        bounds=bounds,
        method="highs",
    )
    if not res.success:
        return None
    val = float(res.fun)
    flow = -(val) + beta if maximize else val + beta
    return flow


def screen_multi_interval_he2023(
    pmin: list[float],
    pmax: list[float],
    ru: list[float],
    rd: list[float],
    demand: list[float],
    t: int,
    constraints: list[dict],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    pmn = np.asarray(pmin, float).ravel()
    pmx = np.asarray(pmax, float).ravel()
    ru_a = np.asarray(ru, float).ravel()
    rd_a = np.asarray(rd, float).ravel()
    D = np.asarray(demand, float).ravel()
    nG, T = pmx.size, D.size
    if T < 2:
        return {"ok": False, "error": "Error: demand 长度必须 ≥ 2。单时段请改用 screen_inactive_thermal_zhai。"}
    if not (pmn.size == ru_a.size == rd_a.size == nG):
        return {"ok": False, "error": "Error: pmin/pmax/ru/rd 必须等长。"}
    if np.any(pmn < -1e-12) or np.any(pmn > pmx + 1e-12):
        return {"ok": False, "error": "Error: 需要 0 ≤ pmin ≤ pmax。"}
    if not (0 <= t < T):
        return {"ok": False, "error": f"Error: t={t} 超出 [0, {T})。"}
    if not constraints:
        return {"ok": False, "error": "Error: constraints 为空。"}

    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        alpha = np.asarray(row.get("alpha", []), float).ravel()
        if alpha.size != nG:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 alpha 长度必须等于机组数。"}
        beta = float(row.get("beta", 0.0))
        F = float(row.get("F", float("nan")))
        if not np.isfinite(F) or F <= 0:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 F 必须为正。"}
        mx = _solve_lp(alpha, beta, True, pmn, pmx, ru_a, rd_a, D, t)
        mn = _solve_lp(alpha, beta, False, pmn, pmx, ru_a, rd_a, D, t)
        results.append(
            {
                "id": cid,
                "upper": {"drop": mx is not None and mx <= F + tolerance, "max_f": mx, "F": F},
                "lower": {"drop": mn is not None and mn >= -F - tolerance, "min_f": mn, "F": -F},
            }
        )
    return {"ok": True, "t": t, "results": results}
```

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| $T<2$ | `Error: demand 长度必须 ≥ 2。单时段请改用 screen_inactive_thermal_zhai。` |
| 数组不等长 | `Error: pmin/pmax/ru/rd 必须等长。` |
| $t$ 越界 | `Error: t=… 超出 [0, T)。` |
| 筛 LP 非最优 | 该侧 `drop=false` |
| 想用预测开机 $\widehat u$ | 不要实现。本工具只做 $u\in[0,1]$ 松弛。 |

不要把真实 UC 的开机解当「预测」再塞回来收紧。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两时段负荷 100→40。两机 $P^{\max}=[80,80]$，$P^{\min}=0$，$\mathrm{RU}=\mathrm{RD}=20$。$t=1$ 某线 $\alpha=[0.5,0.4]$，$\beta=0$，$F=50$。单时段看 $t=1$ 似乎可能堵，带爬坡呢？

**Thought**: $T=2$ 且有爬坡，走多时段筛 LP，不要退化成 $t=1$ 的容量盒。

**Action**:

```json
{
  "tool": "screen_multi_interval_he2023",
  "pmin": [0, 0],
  "pmax": [80, 80],
  "ru": [20, 20],
  "rd": [20, 20],
  "demand": [100, 40],
  "t": 1,
  "constraints": [{"id": "t=1,ell=2", "alpha": [0.5, 0.4], "beta": 0.0, "F": 50.0}]
}
```

**Observation**: `drop=true` 则该侧不写进模型；LP 失败则保留。
