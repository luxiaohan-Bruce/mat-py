---
name: he-2026-screening-uncertainty
description: >-
  对固定拓扑 DC 模型中的盒不确定集鲁棒 UC 或高斯机会约束 UC，按对应扰动模型筛选冗余热稳约束；需要真实负荷区间，或协方差与风险水平，不将筛选结果跨模型直接复用。
---

# He 2026：不确定 UC 的热稳筛选

Xuan He, Honglin Wen, Yufan Zhang, Yize Chen, Danny H.K. Tsang. *Modeling and tackling unit commitment constraint screening under uncertainty.* Applied Energy, 2026.

## 算法解读

确定性筛法（Zhai 等）假定净负荷是点。鲁棒 UC / 机会约束 UC 里扰动 $\omega$ 会扩大潮流范围，把确定性删除集直接套上去可能误删。本文分别给两种筛法，都保证：筛掉的行对**对应的不确定 UC** 仍冗余。

**RO-screening。** 净负荷 $\ell=\widehat\ell+\omega$ 落在盒子上（文中常用相对盒 $\omega\in[-\beta\circ\lvert\widehat\ell\rvert,\beta\circ\lvert\widehat\ell\rvert]$，或直接给每母线半宽）。筛 LP 在这个盒子 + 容量盒 + 功率平衡上 $\max/\min$ 潮流（可带仿射再调度 $x_i(\omega)=x_i+\alpha_i\Omega$，那是不确定 UC 自己的变量）。碰不到限则相对鲁棒 UC 冗余（Lemma 1：筛保留集包含鲁棒 UC 的非冗余集）。

**CC-screening。** $\omega\sim\mathcal N(0,\Sigma)$，机会热稳

$$
\mathbb P\!\left(H_g^{\mathsf T}p-H_b^{\mathsf T}(\widehat\ell+\omega)\le F\right)\ge1-\epsilon
$$

在高斯下改写成确定性分位数：

$$
H_g^{\mathsf T}p-H_b^{\mathsf T}\widehat\ell+\Phi^{-1}(1-\epsilon)\lVert\Sigma^{1/2}H_b\rVert\le F
$$

即有效限变成 $F_{\mathrm{cc}}=F-z_{1-\epsilon}\sqrt{H_b^{\mathsf T}\Sigma H_b}$，再对名义点做容量盒筛。Lemma 2 保证对 CC-UC 可行。$\epsilon\in(0,0.5]$，$F_{\mathrm{cc}}\le0$ 则两侧都留。

可选 MPP 把筛最优值做成分区仿射，本 skill 不做。

**门控（必须先做）：** 数据里要有场景、区间、`chance_epsilon` 或鲁棒盒，且问题声明是不确定 UC。确定性 SCUC 不要调用，不要用 `load_mult` 冒充扰动，不要编 $\Sigma$ 或 $\beta$。不要把 CC 删除集套到确定性 MIP 上。仿射再调度只存在于不确定 UC，不要改预防性「一套 $P_g$」语义。

**整段算法：**

1. 读 `mode=ro` 或 `cc`。缺盒子 / 缺 $(\Sigma,\epsilon)$ → 跳过。
2. RO：在 $[\widehat\ell-r,\widehat\ell+r]$ 上 max/min 潮流。CC：先改写 $F_{\mathrm{cc}}$，再在名义负荷上筛。
3. 从对应的不确定 UC MIP 里删 `drop=true` 的一侧。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_uncertainty_he2026`
- **Description**: 仅当 UC 带显式不确定时调用。鲁棒（RO）：净负荷在盒 $\widehat\ell\pm\beta\circ\lvert\widehat\ell\rvert$（或给定盒子）上 $\max/\min$ 潮流，碰不到限则相对鲁棒 UC 冗余（Lemma 1）。机会约束（CC）：$\omega\sim\mathcal N(0,\Sigma)$ 时用 $\Phi^{-1}(1-\epsilon)$ 把机会热稳改成确定性分位数再筛（Lemma 2）。确定性 UC（无场景、无区间、无 `chance_epsilon`、无鲁棒盒）必须跳过，不要用负荷曲线冒充扰动，不要编造 $\Sigma$ 或 $\beta$。不要把 CC 删除集套到确定性 MIP 上。仿射再调度只存在于不确定 UC，不要改确定性预防性「一套 Pg」语义。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["mode", "pmax", "forecast", "h_gen", "h_bus", "F"],
  "properties": {
    "mode": {
      "type": "string",
      "enum": ["ro", "cc"],
      "description": "ro = 鲁棒盒；cc = 高斯机会约束。"
    },
    "pmax": { "type": "array", "items": { "type": "number" } },
    "forecast": {
      "type": "array",
      "items": { "type": "number" },
      "description": "名义净负荷 ℓ̂，长度 n_bus。"
    },
    "h_gen": { "type": "array", "items": { "type": "number" }, "description": "对机组的转移因子。" },
    "h_bus": { "type": "array", "items": { "type": "number" }, "description": "对母线的转移因子，长度 n_bus。" },
    "F": { "type": "number" },
    "id": { "type": "string" },
    "box_radius": {
      "type": "array",
      "items": { "type": "number" },
      "description": "RO：各母线半宽。缺省且给了 robust_beta 时用 β∘|ℓ̂|。"
    },
    "robust_beta": {
      "type": "number",
      "description": "RO：相对名义负荷的盒比例。box_radius 优先。"
    },
    "sigma": {
      "type": "array",
      "items": { "type": "array", "items": { "type": "number" } },
      "description": "CC：ω 的协方差 Σ，形状 (n_bus, n_bus)。必须由数据给出。"
    },
    "chance_epsilon": {
      "type": "number",
      "description": "CC：违反概率 ε ∈ (0, 0.5]。"
    },
    "tolerance": { "type": "number", "default": 1e-6 }
  }
}
```

确定性算例：直接不要调用；若调用则返回 `skipped`。

---

## 3. 核心代码实现 (Python Implementation)

RO：在 $d\in[\widehat\ell-r,\widehat\ell+r]$、$0\le p\le P^{\max}$、$\mathbf1^{\mathsf T}p=\mathbf1^{\mathsf T}d$ 上 $\max/\min\;(H_g^{\mathsf T}p-H_b^{\mathsf T}d)$。

CC：机会约束 $\mathbb P\!\left(H_g^{\mathsf T}p-H_b^{\mathsf T}(\widehat\ell+\omega)\le F\right)\ge1-\epsilon$ 在高斯下等价于

$$
H_g^{\mathsf T}p-H_b^{\mathsf T}\widehat\ell+\Phi^{-1}(1-\epsilon)\lVert\Sigma^{1/2}H_b\rVert\le F
$$

筛时把限值改成 $F-z_\epsilon\lVert\Sigma^{1/2}H_b\rVert$（上侧；下侧对称），再对名义点做容量盒筛。

```python
from __future__ import annotations

from math import sqrt
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.stats import norm


def _box_flow(
    h_gen: np.ndarray,
    h_bus: np.ndarray,
    pmax: np.ndarray,
    d_lo: np.ndarray,
    d_hi: np.ndarray,
    maximize: bool,
) -> float | None:
    nG, nB = h_gen.size, h_bus.size
    n = nG + nB
    sign = -1.0 if maximize else 1.0
    c = np.concatenate([sign * h_gen, -sign * h_bus])
    A_eq = np.zeros((1, n))
    A_eq[0, :nG] = 1.0
    A_eq[0, nG:] = -1.0
    b_eq = np.array([0.0])
    bounds = [(0.0, float(pmax[g])) for g in range(nG)] + [
        (float(d_lo[b]), float(d_hi[b])) for b in range(nB)
    ]
    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        return None
    val = float(res.fun)
    return -val if maximize else val


def screen_uncertainty_he2026(
    mode: str,
    pmax: list[float],
    forecast: list[float],
    h_gen: list[float],
    h_bus: list[float],
    F: float,
    id: str = "row",
    box_radius: list[float] | None = None,
    robust_beta: float | None = None,
    sigma: list[list[float]] | None = None,
    chance_epsilon: float | None = None,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    if mode not in {"ro", "cc"}:
        return {"ok": False, "error": "Error: mode 必须是 'ro' 或 'cc'。"}
    pbar = np.asarray(pmax, float).ravel()
    ell = np.asarray(forecast, float).ravel()
    Hg = np.asarray(h_gen, float).ravel()
    Hb = np.asarray(h_bus, float).ravel()
    if Hg.size != pbar.size or Hb.size != ell.size:
        return {"ok": False, "error": "Error: h_gen 对 pmax、h_bus 对 forecast 长度必须对齐。"}
    if F <= 0:
        return {"ok": False, "error": "Error: F 必须 > 0。"}

    if mode == "ro":
        if box_radius is not None:
            r = np.asarray(box_radius, float).ravel()
        elif robust_beta is not None:
            r = abs(float(robust_beta)) * np.abs(ell)
        else:
            return {
                "ok": False,
                "skipped": True,
                "error": "Error: RO 需要 box_radius 或 robust_beta。确定性算例不要编造盒子，请改用 screen_inactive_thermal_zhai。",
            }
        if r.size != ell.size or np.any(r < -1e-12):
            return {"ok": False, "error": "Error: box_radius 长度必须等于 forecast 且 ≥ 0。"}
        d_lo, d_hi = ell - r, ell + r
        mx = _box_flow(Hg, Hb, pbar, d_lo, d_hi, True)
        mn = _box_flow(Hg, Hb, pbar, d_lo, d_hi, False)
        return {
            "ok": True,
            "id": id,
            "mode": "ro",
            "upper": {"drop": mx is not None and mx <= F + tolerance, "max_f": mx, "F": F},
            "lower": {"drop": mn is not None and mn >= -F - tolerance, "min_f": mn, "F": -F},
        }

    if sigma is None or chance_epsilon is None:
        return {
            "ok": False,
            "skipped": True,
            "error": "Error: CC 需要 sigma 与 chance_epsilon。不要编造协方差。确定性算例请改用 screen_inactive_thermal_zhai。",
        }
    eps = float(chance_epsilon)
    if not (0.0 < eps <= 0.5):
        return {"ok": False, "error": "Error: chance_epsilon 必须落在 (0, 0.5]。"}
    Sig = np.asarray(sigma, float)
    if Sig.shape != (ell.size, ell.size):
        return {"ok": False, "error": "Error: sigma 必须是 (n_bus, n_bus)。"}
    try:
        z = float(norm.ppf(1.0 - eps))
        sd = float(sqrt(max(Hb @ Sig @ Hb, 0.0)))
    except Exception:
        return {"ok": False, "error": "Error: sigma 不是合法协方差，请检查半正定性后重试。"}
    F_cc = F - z * sd
    if F_cc <= 0:
        return {
            "ok": True,
            "id": id,
            "mode": "cc",
            "upper": {"drop": False, "note": "分位数改写后有效限 ≤ 0，两侧保留。"},
            "lower": {"drop": False},
        }
    d_lo = d_hi = ell
    mx = _box_flow(Hg, Hb, pbar, d_lo, d_hi, True)
    mn = _box_flow(Hg, Hb, pbar, d_lo, d_hi, False)
    return {
        "ok": True,
        "id": id,
        "mode": "cc",
        "F_cc": F_cc,
        "upper": {"drop": mx is not None and mx <= F_cc + tolerance, "max_f": mx, "F": F_cc},
        "lower": {"drop": mn is not None and mn >= -F_cc - tolerance, "min_f": mn, "F": -F_cc},
    }
```

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| 确定性、无盒/无 Σ | `skipped=true`，`Error: …确定性算例不要编造盒子/协方差，请改用 screen_inactive_thermal_zhai。` |
| `chance_epsilon` 非法 | `Error: chance_epsilon 必须落在 (0, 0.5]。` |
| `sigma` 维数不对 | `Error: sigma 必须是 (n_bus, n_bus)。` |
| 分位数后 $F_{\mathrm{cc}}\le0$ | 两侧 `drop=false` |

不要把 CC 删除集用到确定性 MIP。仿射再调度不要写进预防性「一套 Pg」。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 鲁棒 UC，名义负荷 `[50, 40]`，相对扰动 10%。两机 $P^{\max}=[80,80]$，$H_g=[0.3,0.1]$，$H_b=[0.2,0.1]$，$F=35$。

**Thought**: 有显式鲁棒盒，`mode=ro`。不要当确定性 Zhai 做。

**Action**:

```json
{
  "tool": "screen_uncertainty_he2026",
  "mode": "ro",
  "pmax": [80, 80],
  "forecast": [50, 40],
  "h_gen": [0.3, 0.1],
  "h_bus": [0.2, 0.1],
  "F": 35,
  "robust_beta": 0.1
}
```

**Observation**: `drop=true` 的一侧可从鲁棒 UC 去掉。若用户其实是确定性 SCUC，返回 `skipped`，改走 Zhai。
