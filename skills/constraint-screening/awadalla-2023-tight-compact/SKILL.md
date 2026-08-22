# Awadalla 2023：历史净负荷多面体上筛热稳

Mohamed Awadalla, François Bouffard. *Tight and Compact Data-Driven Linear Relaxations for Constraint Screening in Unit Commitment.* IEEE Trans. Energy Markets, Policy and Regulation, 2024 (online 2023).

## 算法解读

坐标盒子把各母线净负荷当成独立区间，忽略空间相关，筛可行域过松、少删。作者用历史净负荷构造一个更紧的多面体 **DPUS**，再在这个多面体上做潮流 `max/min`。

历史矩阵 `W ∈ R^{n_hist × n_bus}`（`n_hist≥2`，母线维与当前系统相同）。预报误差 `W_c = W − μ`，协方差特征分解得主成分 `V`，得分 `Z = W_c V`，`s̄_k = max_t |z_{tk}|`。当前预报 `d⁰` 上：

```
d = d⁰ + V z ,    |z_k| ≤ s̄_k
```

这就是 **P1**：每个主成分方向独立地在 `d⁰ ± s̄_k V_{:,k}` 之间插值。P1 覆盖更稳，是默认。**P2** 是历史极值点的凸包，更紧但怕离群，不要当默认。

筛 LP：

```
max / min  H · (p_inj − d)
s.t.       d ∈ P1
           0 ≤ p ≤ Pmax
           1ᵀp = 1ᵀd
```

碰不到 `±F` 则该侧可删。可选再加一条基于历史 UC 费用的线性不等式（带保守因子），避免 predict-then-optimize 误删；没有历史费用就不要捏造，退回铜板费用上界那一套。

**门控：** 找不到形状匹配的历史矩阵 → 不要调用，不要用一条负荷曲线冒充 ensemble，不要用坐标 box 假装 DPUS。

**整段算法：**

1. 确认 `W` 存在且母线维一致。
2. PCA 得 `V, s̄`，在当前 `d⁰` 上形成 P1。
3. 对每条热稳（`H` 为母线转移因子）解上述 max/min。
4. 最终 MIP 只写留下的 PTDF 割。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `screen_tight_compact_awadalla`
- **Description**: 有历史净负荷矩阵时，用 Awadalla 2023 的 DPUS 多面体 P1（各主成分极值的凸组合）代替坐标盒子，再在 `d ∈ P1`、容量盒、系统平衡上 `max/min` 潮流，碰不到限则删。没有形状 `(n_hist, n_bus)` 的历史样本时必须跳过，不要用单条负荷曲线冒充 ensemble，不要用坐标 box 假装 DPUS。可选的历史 UC 费用不等式没有历史费用就不要捏造。默认 P1；P2（极值点凸包）更紧但怕离群，不要当默认。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["historical_netload", "forecast", "pmax", "gen_bus", "constraints"],
  "properties": {
    "historical_netload": {
      "type": "array",
      "items": { "type": "array", "items": { "type": "number" } },
      "description": "历史净负荷 W，形状 (n_hist, n_bus)。n_hist ≥ 2。缺失则不要调用。"
    },
    "forecast": {
      "type": "array",
      "items": { "type": "number" },
      "description": "当前时段预报 d⁰，长度 n_bus。"
    },
    "pmax": { "type": "array", "items": { "type": "number" }, "description": "在役机组容量。" },
    "gen_bus": {
      "type": "array",
      "items": { "type": "integer" },
      "description": "机组所在母线下标，长度等于 pmax，取值 0..n_bus-1。"
    },
    "constraints": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "h_bus", "F"],
        "properties": {
          "id": { "type": "string" },
          "h_bus": { "type": "array", "items": { "type": "number" }, "description": "母线转移因子，长度 n_bus。" },
          "F": { "type": "number" }
        }
      }
    },
    "n_components": {
      "type": "integer",
      "default": 0,
      "description": "保留的主成分个数。0 表示用全部正特征根。"
    },
    "tolerance": { "type": "number", "default": 1e-6 }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

预报误差 `W_c = W − μ`，特征分解得 `V`，得分 `Z = W_c V`，`s̄_k = max |z_{tk}|`。P1 为

```
d = d⁰ + V z,    |z_k| ≤ s̄_k
```

即各主成分方向独立插值 `d⁰ ± s̄_k V_{:,k}`。筛：`max/min H·(p_inj − d)` s.t. `d∈P1`，`0≤p≤Pmax`，`1ᵀp = 1ᵀd`。碰不到 `±F` 则删。

```python
from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import linprog


def build_p1(
    W: np.ndarray,
    n_components: int = 0,
) -> tuple[np.ndarray, np.ndarray] | dict[str, Any]:
    """P1 的轴向：V 与 s̄。d = d0 + V z，|z_k| ≤ s̄_k。"""
    n_hist, _n_bus = W.shape
    if n_hist < 2:
        return {"ok": False, "error": "Error: historical_netload 至少需要 2 条样本才能做 PCA。"}
    Wc = W - W.mean(axis=0)
    cov = np.cov(Wc, rowvar=False)
    eigval, eigvec = np.linalg.eigh(np.atleast_2d(cov))
    order = np.argsort(eigval)[::-1]
    eigval, eigvec = eigval[order], eigvec[:, order]
    V = eigvec[:, eigval > 1e-12]
    if n_components > 0:
        V = V[:, :n_components]
    if V.size == 0:
        return {"ok": False, "error": "Error: 历史样本协方差秩为 0，无法构造 P1。请换样本或不要调用本工具。"}
    sbar = np.max(np.abs(Wc @ V), axis=0)
    return V, sbar


def _screen_one(
    h: np.ndarray,
    F: float,
    pmax: np.ndarray,
    gen_bus: np.ndarray,
    d0: np.ndarray,
    V: np.ndarray,
    sbar: np.ndarray,
    tolerance: float,
) -> dict[str, Any]:
    n_bus = d0.size
    nG, K = pmax.size, sbar.size
    n = nG + K
    # 变量 p, z；d = d0 + V z，|z| ≤ s̄
    A_eq = np.zeros((1, n))
    A_eq[0, :nG] = 1.0
    A_eq[0, nG:] = -(V.sum(axis=0))
    b_eq = np.array([float(d0.sum())])
    bounds = [(0.0, float(pmax[g])) for g in range(nG)] + [
        (-float(sbar[k]), float(sbar[k])) for k in range(K)
    ]

    def opt(maximize: bool) -> float | None:
        c = np.zeros(n)
        sign = -1.0 if maximize else 1.0
        for g in range(nG):
            c[g] = sign * h[int(gen_bus[g])]
        c[nG:] = -sign * (h @ V)
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        if not res.success:
            return None
        p, z = res.x[:nG], res.x[nG:]
        d = d0 + V @ z
        inj = np.zeros(n_bus)
        for g in range(nG):
            inj[int(gen_bus[g])] += p[g]
        return float(h @ (inj - d))

    mx, mn = opt(True), opt(False)
    return {
        "upper": {"drop": mx is not None and mx <= F + tolerance, "max_f": mx, "F": F},
        "lower": {"drop": mn is not None and mn >= -F - tolerance, "min_f": mn, "F": -F},
    }


def screen_tight_compact_awadalla(
    historical_netload: list[list[float]],
    forecast: list[float],
    pmax: list[float],
    gen_bus: list[int],
    constraints: list[dict],
    n_components: int = 0,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    if historical_netload is None:
        return {
            "ok": False,
            "skipped": True,
            "error": "Error: 没有 historical_netload。不要用单条负荷曲线冒充 ensemble。请改用 screen_cost_driven_porras。",
        }
    W = np.asarray(historical_netload, float)
    d0 = np.asarray(forecast, float).ravel()
    if W.ndim != 2:
        return {"ok": False, "error": "Error: historical_netload 必须是 (n_hist, n_bus) 二维数组。"}
    if d0.size != W.shape[1]:
        return {"ok": False, "error": "Error: forecast 长度必须等于历史样本的母线维。"}
    pbar = np.asarray(pmax, float).ravel()
    gb = np.asarray(gen_bus, int).ravel()
    if gb.size != pbar.size or np.any(gb < 0) or np.any(gb >= W.shape[1]):
        return {"ok": False, "error": "Error: gen_bus 长度须等于 pmax，取值须在母线下标范围内。"}
    built = build_p1(W, n_components)
    if isinstance(built, dict):
        return built
    V, sbar = built
    results = []
    for i, row in enumerate(constraints):
        cid = str(row.get("id", i))
        h = np.asarray(row.get("h_bus", []), float).ravel()
        F = float(row.get("F", float("nan")))
        if h.size != d0.size or not np.isfinite(F) or F <= 0:
            return {"ok": False, "error": f"Error: constraints[{i}] id={cid} 的 h_bus 长度或 F 非法。"}
        rec = _screen_one(h, F, pbar, gb, d0, V, sbar, tolerance)
        rec["id"] = cid
        results.append(rec)
    return {"ok": True, "results": results}
```

P1 写成 `d = d⁰ + Vz`、`|z_k|≤s̄_k`，与 `S_k^{±}=d⁰±s̄_k V_{:,k}` 的独立轴向插值等价。无历史费用时不要另加费用不等式。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| 无历史矩阵 | `Error: 没有 historical_netload。不要用单条负荷曲线冒充 ensemble。请改用 screen_cost_driven_porras。` |
| 样本 < 2 | `Error: historical_netload 至少需要 2 条样本才能做 PCA。` |
| 协方差秩 0 | `Error: 历史样本协方差秩为 0，无法构造 P1。` |
| 母线维不一致 | `Error: forecast 长度必须等于历史样本的母线维。` |

筛 LP 失败 → 该侧保留。无历史费用时不要加费用不等式。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 有 48 条历史 2 母线净负荷，当前预报 `[60, 40]`，两机都在母线 0，Pmax=80/80。线路 `H=[0.5,-0.4]`，F=25。

**Thought**: 有 ensemble，构造 P1 再筛。不要退化成坐标盒子。

**Action**:

```json
{
  "tool": "screen_tight_compact_awadalla",
  "historical_netload": [[58, 41], [62, 38], [55, 44]],
  "forecast": [60, 40],
  "pmax": [80, 80],
  "gen_bus": [0, 0],
  "constraints": [{"id": "ell=1", "h_bus": [0.5, -0.4], "F": 25}]
}
```

**Observation**: `skipped=true` 只有在没给历史矩阵时出现，然后改走 `screen_cost_driven_porras`。
