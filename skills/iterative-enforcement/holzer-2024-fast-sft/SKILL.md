# Holzer 2024：基态 B 分解一次，事故用 LODF/SMW 求流

J. T. Holzer, Y. Chen, Z. Wu, C. Pan, A. Veeramany. *Fast Simultaneous Feasibility Test for Security Constrained Unit Commitment.* IEEE Trans. Power Syst., 2024.

## 算法解读

SFT（Simultaneous Feasibility Test）本身不是机组组合：给定一个 SCUC 解（各时段注入），算基态和事故潮流、过载量，以及把违反热稳写回主问题所需的灵敏度行。迭代加割、lazy callback、Benders 子问题检查，都要反复做这件事。慢的做法是每个事故重装 `B_c` 再分解。

本文用 **Sherman-Morrison-Woodbury** 处理「基态 `B` 与事故拓扑只差低秩」。单回线开断是 rank-1：`B_c = B − b_k e eᵀ`（`e` 是开断线两端的关联向量），

```
B_c^{-1} = B^{-1} + (b_k / (1 − b_k eᵀ B^{-1} e)) B^{-1} e eᵀ B^{-1}
```

这与 LODF 完全等价。于是启动阶段只分解一次基态去参考母线后的 `B_red`；每次注入只解一次基态 `θ`，事故流用乘法：

```
ψ_bus = B_red^{-1} e_bus
PTDF_{ℓ,bus} = b_ℓ (ψ_f − ψ_t)          // b = 1/x，忽略 tap
LODF_{ℓk} = PTDF_{ℓk} / (1 − PTDF_{kk})
f^0 = PTDF · p
f^c_ℓ = f^0_ℓ + LODF_{ℓk} f^0_k          // 开断线本身 f=0
```

`|1−PTDF_{kk}|` 过小表示开断后解列，该事故跳过，不要崩溃。过载

```
γ = max(f − F, −f − F, 0)
```

`γ` 超过容差则报违反，并给出割行：基态 `α = PTDF_ℓ[gen_bus]`，`β = −PTDF_ℓ·Pd[:,t]`；事故 `α^c = α_ℓ + LODF_{ℓk} α_k`（`β` 同样线性组合）。

拓扑不随时段变化时一套 `B` 即可（文中 SFT0）。多小时拓扑不同才要 SFT1；本仓库预防性 SCUC 拓扑不随 `t` 变，不做。多回线同时开断才需要多列 Woodbury；`contingencies` 是单回线，不必做。

**整段算法：**

1. 用在役支路组 `B`，去参考行/列，分解 `B_red`。
2. 预计算基态 PTDF 行；对每个开断 `k` 预计算 LODF 列。
3. 每次拿到 `Pg`：注入 `p = inj(Pg) − Pd`，`f^0 = PTDF p`，事故 `f^c = f^0 + LODF·f^0_k`。
4. 返回违反列表（含 `alpha, beta, F, gamma`）。选中后再 `addConstr`；未违反的行不要物化。

这是求流引擎。不要当另一套 UC 求解器调用，也不要对每个事故再 `inv(B)`。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `sft_lodf_holzer`
- **Description**: 给定预防性直流注入，计算基态与单回线 N-1 潮流、过载量 γ，以及违反行对应的 PTDF/LODF 割系数。基态 `B` 只分解一次，事故用 rank-1 LODF（SMW 的单回线特例）。这是求流引擎，不是机组组合求解器。拓扑不随时段变化时一套 `B` 即可。`|1−PTDF_{kk}|` 过小则跳过该事故。直流 `b=1/x`，忽略 tap/相移。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["branches", "pg", "pd", "gen_bus"],
  "properties": {
    "branches": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "fbus", "tbus", "x", "rate"],
        "properties": {
          "id": { "type": "integer" },
          "fbus": { "type": "integer", "description": "从母线，0-based。" },
          "tbus": { "type": "integer" },
          "x": { "type": "number", "description": "电抗；b=1/max(x,1e-10)。" },
          "rate": { "type": "number", "description": "热稳限，与 pg/pd 同单位。" },
          "status": { "type": "integer", "default": 1 }
        }
      }
    },
    "pg": { "type": "array", "items": { "type": "array", "items": { "type": "number" } }, "description": "(nG, T)。" },
    "pd": { "type": "array", "items": { "type": "array", "items": { "type": "number" } }, "description": "(nB, T)。" },
    "gen_bus": { "type": "array", "items": { "type": "integer" } },
    "ref_bus": { "type": "integer", "default": 0 },
    "outages": {
      "type": "array",
      "items": { "type": "integer" },
      "description": "开断支路 id。0 表示基态。缺省为基态 + 全部在役支路。"
    },
    "emergency_factor": { "type": "number", "default": 1.0, "description": "事故限 = rate × 该因子。" },
    "viol_tol": { "type": "number", "default": 1e-4, "description": "γ > viol_tol 记为违反。" }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

```
ψ_bus = B_red^{-1} e_bus
PTDF_{ℓ,bus} = b_ℓ (ψ_f − ψ_t)
LODF_{ℓk} = PTDF_{ℓk} / (1 − PTDF_{kk})
f^0 = row0 · p,    f^c = f^0 + LODF_{·k} f^0_k
```

开断线本身 `f=0`，不报违反、不给割。

```python
from __future__ import annotations

from typing import Any

import numpy as np

_DENOM_EPS = 1e-10


def sft_lodf_holzer(
    branches: list[dict],
    pg: list[list[float]],
    pd: list[list[float]],
    gen_bus: list[int],
    ref_bus: int = 0,
    outages: list[int] | None = None,
    emergency_factor: float = 1.0,
    viol_tol: float = 1e-4,
) -> dict[str, Any]:
    Pg = np.asarray(pg, float)
    Pd = np.asarray(pd, float)
    if Pg.ndim != 2 or Pd.ndim != 2 or Pd.shape[1] != Pg.shape[1]:
        return {"ok": False, "error": "Error: pg 必须是 (nG, T)，pd 必须是 (nB, T)，时段维相同。"}
    nG, T = Pg.shape
    nB = Pd.shape[0]
    gb = np.asarray(gen_bus, int).ravel()
    if gb.size != nG or np.any(gb < 0) or np.any(gb >= nB):
        return {"ok": False, "error": "Error: gen_bus 长度须等于 nG，取值须在母线范围内。"}
    if not (0 <= ref_bus < nB):
        return {"ok": False, "error": "Error: ref_bus 必须是合法母线下标。"}
    if viol_tol < 0 or emergency_factor <= 0:
        return {"ok": False, "error": "Error: viol_tol ≥ 0 且 emergency_factor > 0。"}

    nL = len(branches)
    ff = np.zeros(nL, int)
    tt = np.zeros(nL, int)
    bsus = np.zeros(nL)
    rate = np.zeros(nL)
    status = np.ones(nL, int)
    ids = np.zeros(nL, int)
    id_to_ell: dict[int, int] = {}
    for ell, br in enumerate(branches):
        ids[ell] = int(br["id"])
        id_to_ell[ids[ell]] = ell
        ff[ell], tt[ell] = int(br["fbus"]), int(br["tbus"])
        bsus[ell] = 1.0 / max(float(br["x"]), 1e-10)
        rate[ell] = float(br["rate"])
        status[ell] = int(br.get("status", 1))
        if min(ff[ell], tt[ell]) < 0 or max(ff[ell], tt[ell]) >= nB:
            return {"ok": False, "error": f"Error: branches[{ell}] 母线越界。"}
        if rate[ell] <= 0:
            return {"ok": False, "error": f"Error: branches[{ell}] id={ids[ell]} 的 rate 必须 > 0。"}

    keep = [i for i in range(nB) if i != ref_bus]
    if not keep:
        return {"ok": False, "error": "Error: 去掉参考母线后没有剩余母线，无法分解 B。"}
    B = np.zeros((nB, nB))
    for ell in range(nL):
        if status[ell] == 0:
            continue
        i, j, b = int(ff[ell]), int(tt[ell]), float(bsus[ell])
        B[i, i] += b
        B[j, j] += b
        B[i, j] -= b
        B[j, i] -= b
    Bred = B[np.ix_(keep, keep)]
    sgn, _ = np.linalg.slogdet(Bred)
    if sgn == 0:
        return {"ok": False, "error": "Error: 基态 B_red 奇异（可能解列）。请检查在役拓扑后重试。"}
    invB = np.linalg.inv(Bred)

    psi = np.zeros((nB, nB))
    psi[np.ix_(keep, keep)] = invB
    row0 = np.zeros((nL, nB))
    for ell in range(nL):
        if status[ell] == 0:
            continue
        row0[ell] = bsus[ell] * (psi[int(ff[ell])] - psi[int(tt[ell])])

    if outages is None:
        out_ids = [0] + [int(i) for i in ids[status == 1]]
    else:
        out_ids = list(outages)

    violations: list[dict[str, Any]] = []
    skipped_outages: list[dict[str, Any]] = []

    def injection(tau: int) -> np.ndarray:
        p = -Pd[:, tau].copy()
        for g in range(nG):
            p[int(gb[g])] += Pg[g, tau]
        return p

    for out_id in out_ids:
        k_ell = None
        lodf = None
        if out_id != 0:
            if out_id not in id_to_ell:
                return {"ok": False, "error": f"Error: outages 含未知支路 id={out_id}。"}
            k_ell = id_to_ell[out_id]
            if status[k_ell] == 0:
                skipped_outages.append({"id": out_id, "reason": "offline"})
                continue
            ptdf_k = row0[:, int(ff[k_ell])] - row0[:, int(tt[k_ell])]
            denom = 1.0 - float(ptdf_k[k_ell])
            if abs(denom) < _DENOM_EPS:
                skipped_outages.append({"id": out_id, "reason": "islanding"})
                continue
            lodf = ptdf_k / denom

        for tau in range(T):
            p = injection(tau)
            f0 = row0 @ p
            if k_ell is None:
                fc, Fscale = f0, 1.0
            else:
                fc = f0 + lodf * f0[k_ell]
                fc[k_ell] = 0.0
                Fscale = float(emergency_factor)
            for ell in range(nL):
                if status[ell] == 0 or ell == k_ell:
                    continue
                F = rate[ell] * Fscale
                gma = max(float(fc[ell] - F), float(-fc[ell] - F), 0.0)
                if gma <= viol_tol:
                    continue
                alpha = row0[ell, gb].copy()
                beta = float(-row0[ell] @ Pd[:, tau])
                if k_ell is not None:
                    alpha = alpha + lodf[ell] * row0[k_ell, gb]
                    beta = beta + lodf[ell] * float(-row0[k_ell] @ Pd[:, tau])
                violations.append(
                    {
                        "gamma": gma,
                        "t": tau,
                        "out_id": int(out_id),
                        "ell": ell,
                        "branch_id": int(ids[ell]),
                        "alpha": alpha.tolist(),
                        "beta": beta,
                        "F": float(F),
                    }
                )

    return {"ok": True, "violations": violations, "skipped_outages": skipped_outages}
```

对返回的每一条违反加两侧割：`α·Pg[:,t]+β ≤ F` 与 `−α·Pg[:,t]−β ≤ F`。未违反的热稳不要写成约束。不要对每个事故再组装 `B` 再求逆。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| 形状不对 | `Error: pg 必须是 (nG, T)，pd 必须是 (nB, T)，时段维相同。` |
| `B_red` 奇异 | `Error: 基态 B_red 奇异（可能解列）。请检查在役拓扑后重试。` |
| 未知开断 id | `Error: outages 含未知支路 id=…。` |
| 解列 | 该事故进 `skipped_outages`，不崩溃 |

不要当 SCUC 求解器调用本工具。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 两母线一线，x=0.1，rate=50。机在母线 0 出力 80，负荷在母线 1 为 80。扫基态过载。

**Thought**: 只要潮流和割行，调用 `sft_lodf_holzer`。

**Action**:

```json
{
  "tool": "sft_lodf_holzer",
  "branches": [{"id": 1, "fbus": 0, "tbus": 1, "x": 0.1, "rate": 50}],
  "pg": [[80]],
  "pd": [[0], [80]],
  "gen_bus": [0],
  "outages": [0]
}
```

**Observation**: `f^0=80>50` → `violations` 一条，带 `alpha/beta/F`，据此加两侧热稳割。
