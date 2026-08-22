# Ding 2020：不确定净负荷下判定冗余热稳

Tao Ding, Cheng Li, Fangxing Li, Tianen Chen, Rui Bo. *Fast identifying redundant security constraints in SCUC in the presence of uncertainties.* IET Gener. Transm. Distrib., 14(20), 2020.

## 算法解读

Zhai 的解析条件默认净负荷是一个点。风电/负荷不确定时，净负荷落在盒子 `[Dmin, Dmax]` 里，潮流跟着盒子动。直接套 Zhai 会出现两种错：盒子被忽略而过松（该留的行被删），或把区间最坏情况当成点负荷而过紧（能删的删不掉）。

本文 **Corollary 1**：一条热稳对区间内**任意实现**都碰不到限，才叫不确定下的冗余。几何上：无不确定时冗余 = 超平面与可行域不相交；有区间时要对整个不确定盒子都不相交。充要条件是双层 MILP，不实用。

于是分两步，都是充分条件：

1. **FBBT**（feasible-based bound tightening）：机组出力先放在 `L=0, U=Pmax`，用
   - 功率平衡：`ΣP ∈ [ΣDmin, ΣDmax]` → 每个分量 `U_g ≤ Dmax_tot − Σ_{j≠g} L_j`，`L_g ≥ Dmin_tot − Σ_{j≠g} U_j`
   - 爬坡：`−RD ≤ P_t − P_{t−1} ≤ RU` 正向、反向推界
   迭代到相对改进很小。某分量出现 `L>U` 说明松弛已空，**全部热稳保留**。FBBT 是区间传播，不要为它解 LP。
2. **Corollary 3 连续背包**：可行域再松成收紧后的盒子 + 平衡。把 `P = L + ΔP`、`D = Dmax − ΔD` 代入潮流行，重量
   ```
   Λ = Σ Dmax − Σ L
   ```
   物品 = 机组（容量 `U−L`，价值 = 转移因子 `H_g`）+ 负荷母线（容量 `Dmax−Dmin`，价值 = `H_b`）。按价值降序填到 `Λ`，得到增量最优 `z_inc`。常数项
   ```
   Q = H_g·L − H_b·Dmax
   ```
   （上侧；下侧把 `H` 变号）。`Q + z_inc ≤ F` 则该侧对整个区间冗余。

区间从哪来：配置里的 `net_load_interval`；否则 `uncertainty_level=α` 给出 `[(1−α)Pd, (1+α)Pd]`；再否则 `Dmin=Dmax=Pd`，算法退化为「点负荷 + FBBT」，不要为此去编风电场景。

**整段算法：**

1. 读出 `Dmin, Dmax`（p.u.，与出力同单位）。
2. FBBT 得到 `L,U`；失败则停止筛选。
3. 对每个 `(t, 事故, 线路)` 两侧做一次背包。`H` 是该场景 PTDF 行（开断列已去掉）。
4. 最终 MIP：UC + 系统平衡 + 未删 PTDF 割，一次 `optimize`。

不要把 FBBT 的 `L,U` 当成开机决策；二进制仍只在最终 MIP 里。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_redundant_thermal_ding`
- **Description**: 净负荷落在区间时，用 Ding 2020 的 FBBT + 连续背包判定热稳对区间内任意实现是否冗余（Corollary 3，充分条件）。机组与负荷母线都是背包物品。无区间时区间退化为点负荷，判定仍可调用，但与 Zhai 同类。不要编造风电场景；FBBT 某分量 `L>U` 则全部保留。在把热稳写进 UC 之前调用。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["pmax", "dmin", "dmax", "h_gen", "h_bus", "F"],
  "properties": {
    "pmax": {
      "type": "array",
      "items": { "type": "number" },
      "description": "在役机组容量上界。只放 status=1 且 Pmax>0 的机。"
    },
    "ru": { "type": "array", "items": { "type": "number" }, "description": "机组向上爬坡。长度等于 pmax。缺省则 FBBT 不打爬坡。" },
    "rd": { "type": "array", "items": { "type": "number" }, "description": "机组向下爬坡。长度等于 pmax。" },
    "dmin": {
      "type": "array",
      "items": { "type": "array", "items": { "type": "number" } },
      "description": "净负荷下界，形状 (n_bus, T)。来自 net_load_interval，或 (1-α)Pd。"
    },
    "dmax": {
      "type": "array",
      "items": { "type": "array", "items": { "type": "number" } },
      "description": "净负荷上界，形状与 dmin 相同。必须逐元素 ≥ dmin。"
    },
    "h_gen": {
      "type": "array",
      "items": { "type": "number" },
      "description": "该热稳对机组的转移因子 H_g，长度等于 pmax。"
    },
    "h_bus": {
      "type": "array",
      "items": { "type": "number" },
      "description": "该热稳对负荷母线的转移因子 H_b，长度等于 dmin 的母线维。"
    },
    "F": { "type": "number", "description": "热稳限 F > 0。" },
    "id": { "type": "string", "description": "调用方键，原样返回。" },
    "t": { "type": "integer", "description": "要判定的时段，0 ≤ t < T。默认 0。" },
    "tolerance": { "type": "number", "default": 1e-6, "description": "与 F 比较的容差，必须 ≥ 0。" },
    "fbbt_iters": { "type": "integer", "default": 20, "description": "FBBT 最大轮数。" }
  }
}
```

一次只判定一条热稳的两侧；多条热稳对每条分别调用（FBBT 的 `L,U` 可在调用方缓存）。

---

## 3. 核心代码实现 (Python Implementation)

Corollary 1 的充要是双层 MILP，不用。Corollary 3：可行域松成容量盒 + 平衡，负荷也是背包物品。FBBT 用 `ΣP ∈ [ΣDmin, ΣDmax]` 和爬坡收紧 `L,U`，不解 LP。

代换 `P = L + ΔP`，`D = Dmax − ΔD`，重量 `Λ = ΣDmax − ΣL`。`Z⁺ = Q + greedy`，`Z⁺ ≤ F` 则该侧冗余。

```python
from __future__ import annotations

from typing import Any

import numpy as np


def _greedy_fill(values: np.ndarray, caps: np.ndarray, weight: float) -> float | None:
    """连续背包：max v·x s.t. 1ᵀx = weight, 0 ≤ x ≤ caps。"""
    values = np.asarray(values, float).ravel()
    caps = np.maximum(np.asarray(caps, float).ravel(), 0.0)
    if weight < -1e-12 or weight > float(caps.sum()) + 1e-9:
        return None
    if weight <= 1e-15:
        return 0.0
    order = np.argsort(-values, kind="mergesort")
    remaining, obj = float(weight), 0.0
    for idx in order:
        if remaining <= 1e-15:
            break
        take = caps[idx] if caps[idx] < remaining else remaining
        obj += values[idx] * take
        remaining -= take
    return float(obj)


def fbbt_bounds(
    pmax: np.ndarray,
    dmin: np.ndarray,
    dmax: np.ndarray,
    ru: np.ndarray | None,
    rd: np.ndarray | None,
    k_max: int = 20,
    eps: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """返回 (L, U, ok)。ok=False 表示某分量 L>U，不要删任何热稳。"""
    nG = pmax.size
    T = dmin.shape[1]
    Lg = np.zeros((nG, T))
    Ug = pmax[:, None] * np.ones((1, T))
    Dmin_tot, Dmax_tot = dmin.sum(axis=0), dmax.sum(axis=0)
    ru = np.asarray(ru if ru is not None else np.full(nG, np.inf), float)
    rd = np.asarray(rd if rd is not None else np.full(nG, np.inf), float)
    for _ in range(k_max):
        old_L, old_U = Lg.copy(), Ug.copy()
        for t in range(T):
            sl, su = float(Lg[:, t].sum()), float(Ug[:, t].sum())
            Ug[:, t] = np.minimum(Ug[:, t], Dmax_tot[t] - (sl - Lg[:, t]))
            Lg[:, t] = np.maximum(Lg[:, t], Dmin_tot[t] - (su - Ug[:, t]))
        Ug[:, 0] = np.minimum(Ug[:, 0], ru)
        for t in range(1, T):
            Ug[:, t] = np.minimum(Ug[:, t], Ug[:, t - 1] + ru)
            Lg[:, t] = np.maximum(Lg[:, t], Lg[:, t - 1] - rd)
        for t in range(T - 2, -1, -1):
            Ug[:, t] = np.minimum(Ug[:, t], Ug[:, t + 1] + rd)
            Lg[:, t] = np.maximum(Lg[:, t], Lg[:, t + 1] - ru)
        Lg = np.maximum(Lg, 0.0)
        Ug = np.minimum(Ug, pmax[:, None])
        if np.any(Lg > Ug + 1e-12):
            return Lg, Ug, False
        Lg = np.minimum(Lg, Ug)
        num = float(np.abs(Lg - old_L).sum() + np.abs(Ug - old_U).sum())
        den = float(np.abs(old_L).sum() + np.abs(old_U).sum()) + 1e-12
        if num / den < eps:
            break
    return Lg, Ug, True


def screen_redundant_thermal_ding(
    pmax: list[float],
    dmin: list[list[float]],
    dmax: list[list[float]],
    h_gen: list[float],
    h_bus: list[float],
    F: float,
    ru: list[float] | None = None,
    rd: list[float] | None = None,
    id: str = "row",
    t: int = 0,
    tolerance: float = 1e-6,
    fbbt_iters: int = 20,
) -> dict[str, Any]:
    pmax_a = np.asarray(pmax, float).ravel()
    Dmin = np.asarray(dmin, float)
    Dmax = np.asarray(dmax, float)
    Hg = np.asarray(h_gen, float).ravel()
    Hb = np.asarray(h_bus, float).ravel()
    if Dmin.ndim != 2 or Dmax.shape != Dmin.shape:
        return {"ok": False, "error": "Error: dmin/dmax 必须是形状相同的 (n_bus, T) 数组。"}
    if np.any(Dmin > Dmax + 1e-12):
        return {"ok": False, "error": "Error: 存在 dmin > dmax。请交换或修正区间后重试。"}
    if Hg.size != pmax_a.size:
        return {"ok": False, "error": "Error: h_gen 长度必须等于 pmax。"}
    if Hb.size != Dmin.shape[0]:
        return {"ok": False, "error": "Error: h_bus 长度必须等于 dmin 的母线维。"}
    if F <= 0 or tolerance < 0:
        return {"ok": False, "error": "Error: F 必须 > 0 且 tolerance ≥ 0。"}
    if not (0 <= t < Dmin.shape[1]):
        return {"ok": False, "error": f"Error: t={t} 超出时段范围 [0, {Dmin.shape[1]})。"}

    ru_a = np.asarray(ru, float).ravel() if ru is not None else None
    rd_a = np.asarray(rd, float).ravel() if rd is not None else None
    L, U, ok = fbbt_bounds(pmax_a, Dmin, Dmax, ru_a, rd_a, k_max=fbbt_iters)
    if not ok:
        return {
            "ok": True,
            "id": id,
            "fbbt_ok": False,
            "upper": {"drop": False},
            "lower": {"drop": False},
            "note": "FBBT 出现 L>U，按论文保留两侧。",
        }

    Lt, Ut = L[:, t], U[:, t]
    Dmx, Dmn = Dmax[:, t], Dmin[:, t]
    cap_p = np.maximum(Ut - Lt, 0.0)
    cap_d = np.maximum(Dmx - Dmn, 0.0)
    lam = float(Dmx.sum() - Lt.sum())
    sides = {}
    for name, sign in (("upper", 1.0), ("lower", -1.0)):
        Hg_s, Hb_s = sign * Hg, sign * Hb
        Q = float(np.dot(Hg_s, Lt) - np.dot(Hb_s, Dmx))
        zinc = _greedy_fill(np.concatenate([Hg_s, Hb_s]), np.concatenate([cap_p, cap_d]), lam)
        drop = zinc is not None and Q + zinc <= F + tolerance
        sides[name] = {"drop": drop, "Q": Q, "z_inc": zinc, "bound": F}
    return {"ok": True, "id": id, "t": t, "fbbt_ok": True, **sides}
```

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `dmin > dmax` | `Error: 存在 dmin > dmax。请交换或修正区间后重试。` |
| 维数不一致 | `Error: h_gen 长度必须等于 pmax。` / `h_bus` 对母线维 |
| `t` 越界 | `Error: t=… 超出时段范围 …` |
| FBBT `L>U` | `ok=true` 但两侧 `drop=false`（不是参数错误） |
| 无区间数据 | 令 `dmin=dmax=Pd` 再调用，或改用 `screen_inactive_thermal_zhai` |

`ok=false` 或 `fbbt_ok=false`：不要删行。不要为 FBBT 解 LP。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两机 Pmax=100/80，两母线负荷区间 t=0 为 `[40,50]` 与 `[30,45]`。线路 `H_g=[0.4,-0.1]`，`H_b=[0.3,0.2]`，F=60。这一侧能删吗？

**Thought**: 有净负荷区间，走 Ding，不要套点负荷 Zhai。

**Action**:

```json
{
  "tool": "screen_redundant_thermal_ding",
  "pmax": [100, 80],
  "dmin": [[40], [30]],
  "dmax": [[50], [45]],
  "h_gen": [0.4, -0.1],
  "h_bus": [0.3, 0.2],
  "F": 60,
  "t": 0
}
```

**Observation**: `drop=true` 的一侧不写进模型；`fbbt_ok=false` 则两侧都留。
