---
name: xavier-2019-filter
description: >-
  当固定拓扑单回线 N-1 DC-SCUC 需要控制每轮安全约束增长时，对 SFT 违反先按监测线保留最严重事故，再按时段选择 top-k 加入主问题；配合外循环和最终全量安全检查。
---

# Xavier 2019：每时段只加 $\gamma$ 最大的 $k$ 条热稳割

Alinson S. Xavier, Feng Qiu, Fengyu Wang, Prakash R. Thimmapuram. *Transmission Constraint Filtering in Large-Scale Security-Constrained Unit Commitment.* IEEE PES Letters, 2019.

## 算法解读

全量基态 + N-1 热稳会让 SCUC 的 MIP 大到难以直接求解，但「只需强制其中很小一个子集，其余会自动满足」。前人（Tejada 的 TSR、Chen/MISO 的 SFT 回环）做法是：先解一个不含（或只含部分）热稳的松弛，再用 ISF/LODF 扫流，把**所有**违反的事故热稳加回去，直到扫不到违反。

本文 Algorithm 1 在「加违反」之上加两层过滤，减少每轮写入 MIP 的割：

1. 同一监测线 $m$ 若在多个事故 $v$ 下都过载，只留 $\gamma$ 最大的那个 `(v,m)`。直觉：最狠的那条事故割通常会把它余较轻的过载一并压下去。
2. 再只留 $\gamma$ 最大的 $k$ 条。论文实验 $5\le k\le15$ 最好，默认 $k=10$。

过载量

$$
\gamma_m^v=\max\{-f_m^v-F_m,0,f_m^v-F_m\}
$$

$f^0$ 用 ISF（基态 PTDF），$f^v$ 用 LODF，**未选中的热稳不要写成约束**（ISF 行很密，物化会撑爆模型）。作者在最多数千母线的系统上做到与 TSR 相同的最终解（$\Gamma=\varnothing$ 且达到最终 gap），因为循环会一直加到没有违反。

多时段：论文 Algorithm 1 无时段下标，正文写 constraints added per time period。实现上每个 $t$ 单独做「每线留最大事故 + top-k」。

早迭代用较松的 MIP gap（文中 5%），扫不到违反后再收到最终 gap（如 0.1%），避免在仍大量缺割时把树搜完。`TimeLimit` 是全局预算。同一模型 `addConstr` 后热启动，不要每轮重建 UC。

**整段算法（Algorithm 1）：**

1. 建一个 MIP：与原问题相同的 UC（开机、$P^{\min}u\le P_g\le P^{\max}u$、爬坡、最小开停、目标）+ 每时段 $\sum_gP_{g,t}=\sum_bP_{d,b,t}$。不要 $\theta$/$f$/热稳。
2. $\mathtt{MIPGap}\leftarrow\max(0.05,\mathrm{gap}_{\mathrm{final}})$，`optimize`。无解则停。
3. 用当前 $P_g$ 算全部在役非开断线的直流流（ISF + LODF）。$\gamma$ 超容差记入 $\Gamma$。
4. $\Gamma=\varnothing$：若当前 gap 仍大于最终 gap，收紧再解；否则结束。
5. 否则：每个 `(t, ℓ)` 只留 $\gamma$ 最大的事故；每个 $t$ 再留最多 $k$ 条。对选中键加两侧 PTDF 割，已加过的跳过。回到步骤 2。上限约 50 轮。

$k$ 过小可能来回加很久，加大 $k$，不要改成一次加全部违反（那是 TSR）。多回线同时开断不要用 LODF 这套。拓扑可变的 OTS 也不要。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `filter_transmission_constraints_xavier`
- **Description**: 对一次 SFT 扫到的热稳违反做 Xavier 2019 Algorithm 1 过滤：同一监测线若在多个事故下过载，只留 $\gamma$ 最大的那个事故；再在每个时段只留 $\gamma$ 最大的 $k$ 条（默认 $k=10$）。输出本轮应加入松弛 MIP 的键。铜板/无热稳 UC 先解、用 ISF/LODF 算流，本工具不管求流。不要把未选中的热稳物化。多回线同时开断不要用。k 过小导致循环不收敛时加大 k，不要改成「一次加全部违反」（那是 TSR）。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["violations", "n_periods"],
  "properties": {
    "violations": {
      "type": "array",
      "description": "本轮 SFT 的违反记录，γ>0。",
      "items": {
        "type": "object",
        "required": ["gamma", "t", "out_id", "ell"],
        "properties": {
          "gamma": { "type": "number", "description": "过载量 max(f−F, −f−F, 0)。" },
          "t": { "type": "integer", "description": "时段。" },
          "out_id": { "type": "integer", "description": "开断支路 id；基态为 0。" },
          "ell": { "type": "integer", "description": "过载监测线索引。" }
        }
      }
    },
    "n_periods": { "type": "integer", "description": "时段数 T≥1。" },
    "k": { "type": "integer", "default": 10, "description": "每个时段最多加入的割条数。论文实验 5–15，默认 10。" },
    "already_added": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "integer" },
        "minItems": 3,
        "maxItems": 3
      },
      "description": "已经加过的 (t, out_id, ell) 列表。这些不再选出。"
    }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

论文 Algorithm 1：

1. 求解不含热稳约束的 SCUC 松弛。
2. 用 ISF 和 LODF 分别计算 $f^0$ 与 $f^v$，并计算 $\gamma_m^v=\max\{-f_m^v-F_m,0,f_m^v-F_m\}$。
3. 构造 $\Gamma=\{(v,m):\gamma_m^v>0\}$；若为空则返回。
4. 对每个 $m$ 只留 $\gamma_m^v$ 最大的 $(v,m)$，再选取其中最大的 $k$ 个。
5. 将对应约束加入松弛模型，返回求解步骤。

多时段：论文写 “constraints added per time period”，每个 $t$ 单独做 top-k。

```python
from __future__ import annotations

from typing import Any


def filter_transmission_constraints_xavier(
    violations: list[dict],
    n_periods: int,
    k: int = 10,
    already_added: list[list[int]] | None = None,
) -> dict[str, Any]:
    if n_periods < 1:
        return {"ok": False, "error": "Error: n_periods 必须 ≥ 1。"}
    if k < 1:
        return {"ok": False, "error": "Error: k 必须 ≥ 1。论文默认 10；不要传 0。"}
    added = {tuple(x) for x in (already_added or [])}
    if any(len(x) != 3 for x in (already_added or [])):
        return {"ok": False, "error": "Error: already_added 的每个元素必须是长度为 3 的 [t, out_id, ell]。"}

    best: dict[tuple[int, int], tuple[float, int, int, int]] = {}
    for i, rec in enumerate(violations):
        try:
            gma = float(rec["gamma"])
            t = int(rec["t"])
            c = int(rec["out_id"])
            ell = int(rec["ell"])
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": f"Error: violations[{i}] 需要 gamma/t/out_id/ell。"}
        if not (0 <= t < n_periods):
            return {"ok": False, "error": f"Error: violations[{i}].t={t} 超出 [0, {n_periods})。"}
        if gma <= 0:
            continue
        if (t, c, ell) in added:
            continue
        prev = best.get((t, ell))
        if prev is None or gma > prev[0]:
            best[(t, ell)] = (gma, t, c, ell)

    by_t: list[list[tuple[float, int, int, int]]] = [[] for _ in range(n_periods)]
    for rec in best.values():
        by_t[rec[1]].append(rec)

    selected: list[dict[str, Any]] = []
    for t in range(n_periods):
        recs_t = sorted(by_t[t], key=lambda r: r[0], reverse=True)
        for gma, tt, c, ell in recs_t[:k]:
            selected.append({"gamma": gma, "t": tt, "out_id": c, "ell": ell})

    return {
        "ok": True,
        "selected": selected,
        "n_raw": len(violations),
        "n_after_per_line": len(best),
        "n_selected": len(selected),
        "converged": len(selected) == 0,
    }
```

外循环（调用方）：铜板 MIP（UC + 每时段系统平衡，无 $\theta$/$f$）→ `optimize` → SFT 得 `violations` → 本工具 → 对 `selected` 加两侧 PTDF 割并热启动。无违反后若还在宽松 MIP gap，收到最终 gap 再解一轮。上限约 50 轮。早迭代可用 5% gap，无违反后再收到最终 gap。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| $k<1$ | `Error: k 必须 ≥ 1。论文默认 10；不要传 0。` |
| $t$ 越界 | `Error: violations[i].t=… 超出 [0, T)。` |
| 缺字段 | `Error: violations[i] 需要 gamma/t/out_id/ell。` |
| 本轮 `selected` 空 | `converged=true`，不是错误：停止加割 |
| 想一次加全部违反 | 不要把 k 设成无穷；那是 `select_all_violations_tejada` |

未选中的割不要 `addConstr`。已加过的键必须放进 `already_added`。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: $T=1$。SFT 扫到：线 1 在事故 3 过载 5、事故 7 过载 4；线 8 在事故 2 过载 3。$k=1$。本轮加哪条？

**Thought**: 先按监测线去重（线 1 留事故 3），再 top-k。

**Action**:

```json
{
  "tool": "filter_transmission_constraints_xavier",
  "n_periods": 1,
  "k": 1,
  "already_added": [],
  "violations": [
    {"gamma": 5.0, "t": 0, "out_id": 3, "ell": 1},
    {"gamma": 4.0, "t": 0, "out_id": 7, "ell": 1},
    {"gamma": 3.0, "t": 0, "out_id": 2, "ell": 8}
  ]
}
```

**Observation**: 选出 `[(t=0, out_id=3, ell=1)]`。只对这一条加两侧割，不要加 `ell=8`。
