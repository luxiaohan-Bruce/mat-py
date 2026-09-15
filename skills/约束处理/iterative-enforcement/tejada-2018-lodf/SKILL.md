---
name: tejada-2018-lodf
description: >-
  对固定拓扑、单回线 N-1 的预防性 DC-SCUC，采用 ISF/LODF 安全检查与 TSR 外循环，每轮加入全部尚未加入的违反热稳约束；用于无需求解器回调的迭代约束生成。
---

# Tejada 2018：LODF 写 N-1，违反全部加回（TSR）

Diego A. Tejada-Arango, Pedro Sánchez-Martín, Andres Ramos. *Security Constrained Unit Commitment Using Line Outage Distribution Factors.* IEEE Trans. Power Syst., 33(1), 2018.

## 算法解读

预防性 N-1 SCUC 若给每个事故各建一套相角 / 潮流变量，模型按事故数复制。本文两点：

**紧凑潮流。** 基态用 ISF（文 Eq. 25）：$f^0=\mathrm{PTDF}\,p$。事故不用每套拓扑再求 ISF，而用 LODF（Eq. 29）

$$
\begin{aligned}\mathrm{LODF}_{\ell k}=\frac{\mathrm{PTDF}_{\ell k}}{1-\mathrm{PTDF}_{kk}},\\f_\ell^c=f_\ell^0+\mathrm{LODF}_{\ell k}f_k^0.\end{aligned}
$$

开断线本身 $f=0$。$\lvert1-\mathrm{PTDF}_{kk}\rvert$ 过小（解列）则跳过该事故。非零系数大约少一个「母线 × 机组」因子。只对单回线开断成立；多回线同时开断不要套这个公式。直流 $b=1/x$，忽略 tap。

**§IV 迭代过滤（后称 TSR）。** 不要为每个事故解 Benders 子问题。先解**网络约束 UC**（只有基态 ISF 热稳，或更松的铜板：只有系统平衡），用 Eq. 30 扫全部事故流，把每一个过载的 `(开断线, 过载线, 时段)` 加回主问题，直到全部低于限。与 Xavier 的差别只有一条：TSR **全量加违反**，没有「每线留最大事故」也没有 top-k。

割在选中后才写，展开成 $P_g$ 的线性行：

$$
\begin{aligned}
\alpha&=\alpha_\ell+\mathrm{LODF}_{\ell k}\alpha_k,\\
\beta&=\beta_\ell+\mathrm{LODF}_{\ell k}\beta_k,\\
\alpha^{\mathsf T}P_{:,t}+\beta&\le F,\\
-\alpha^{\mathsf T}P_{:,t}-\beta&\le F.
\end{aligned}
$$

基态 $k$ 不存在，$\mathrm{LODF}=0$。求流时基态 $B_{\mathrm{red}}$ 只分解一次，禁止对每个事故再 `inv(B)`。

**整段算法：**

1. 建铜板（或仅基态热稳）MIP：UC + 系统平衡，无事故 `theta/f`。
2. 早迭代可用较松 MIP gap；`optimize`。
3. 一次基态流 + LODF 扫全部事故。$\gamma$ 超容差且未加过的键全部选中。
4. 无新违反：收到最终 gap 或停。否则加两侧割、热启动，回到 2。上限约 50 轮。

Xavier 把 TSR 当对照，再做 top-k。本 skill 实现 TSR 本身。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `select_all_violations_tejada`
- **Description**: TSR 过滤：把 SFT 扫到的每一条未加入的热稳违反都选中（不做 top-k、不按监测线去重事故）。基态用 ISF，事故用 LODF $f_\ell^c=f_\ell^0+\mathrm{LODF}_{\ell k}f_k^0$，不要为每个事故再求 $B^{-1}$。本工具只做「全量加违反」的键选择；求流用 `sft_lodf_holzer`。只要少割，改用 `filter_transmission_constraints_xavier`。不要为每个事故解 Benders 子问题。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["violations"],
  "properties": {
    "violations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["gamma", "t", "out_id", "ell"],
        "properties": {
          "gamma": { "type": "number" },
          "t": { "type": "integer" },
          "out_id": { "type": "integer" },
          "ell": { "type": "integer" }
        }
      }
    },
    "already_added": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "integer" },
        "minItems": 3,
        "maxItems": 3
      },
      "description": "已加过的 (t, out_id, ell)。"
    },
    "viol_tol": { "type": "number", "default": 0, "description": "只选 gamma > viol_tol 的记录。" }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

LODF（文 Eq. 3，求流侧）：

$$
\mathrm{LODF}_{\ell k}=\frac{\mathrm{PTDF}_{\ell k}}{1-\mathrm{PTDF}_{kk}}
$$

割（选中后才写）：

$$
\begin{aligned}
\alpha&=\alpha_\ell+\mathrm{LODF}_{\ell k}\alpha_k,\\
\beta&=\beta_\ell+\mathrm{LODF}_{\ell k}\beta_k,\\
\alpha^{\mathsf T}P_{:,t}+\beta&\le F,\\
-\alpha^{\mathsf T}P_{:,t}-\beta&\le F.
\end{aligned}
$$

基态 `out_id=0` 时 $\mathrm{LODF}=0$。开断线本身 $f=0$，SFT 不应把它放进 `violations`。

```python
from __future__ import annotations

from typing import Any


def select_all_violations_tejada(
    violations: list[dict],
    already_added: list[list[int]] | None = None,
    viol_tol: float = 0.0,
) -> dict[str, Any]:
    if viol_tol < 0:
        return {"ok": False, "error": "Error: viol_tol 必须 ≥ 0。"}
    added = {tuple(x) for x in (already_added or [])}
    if any(len(x) != 3 for x in (already_added or [])):
        return {"ok": False, "error": "Error: already_added 的每个元素必须是 [t, out_id, ell]。"}

    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int]] = set()
    for i, rec in enumerate(violations):
        try:
            gma = float(rec["gamma"])
            t = int(rec["t"])
            c = int(rec["out_id"])
            ell = int(rec["ell"])
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": f"Error: violations[{i}] 需要 gamma/t/out_id/ell。"}
        if t < 0:
            return {"ok": False, "error": f"Error: violations[{i}].t={t} 不能为负。"}
        if gma <= viol_tol:
            continue
        key = (t, c, ell)
        if key in added or key in seen:
            continue
        seen.add(key)
        selected.append({"gamma": gma, "t": t, "out_id": c, "ell": ell})

    return {
        "ok": True,
        "selected": selected,
        "n_selected": len(selected),
        "converged": len(selected) == 0,
    }
```

外循环：铜板 MIP → optimize → `sft_lodf_holzer` → 本工具 → 对 `selected` 加两侧割并热启动，直到 `converged`。不要每个事故一套 ISF。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| 缺字段 | `Error: violations[i] 需要 gamma/t/out_id/ell。` |
| 本轮无新违反 | `converged=true`，停止加割 |
| 割太多想过滤 | 改用 `filter_transmission_constraints_xavier`，不要在本工具里加 k |
| 多回线同时开断 | 不要调用；本 LODF 公式只对单回线 |

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: SFT 给出三条违反，其中一条已经加过。TSR 本轮加哪些？

**Thought**: 全量加未加入的违反，不去重事故、不做 top-k。

**Action**:

```json
{
  "tool": "select_all_violations_tejada",
  "already_added": [[0, 3, 1]],
  "violations": [
    {"gamma": 5.0, "t": 0, "out_id": 3, "ell": 1},
    {"gamma": 4.0, "t": 0, "out_id": 7, "ell": 1},
    {"gamma": 3.0, "t": 0, "out_id": 2, "ell": 8}
  ]
}
```

**Observation**: 选出 `(0,7,1)` 与 `(0,2,8)`。已加的 `(0,3,1)` 跳过。
