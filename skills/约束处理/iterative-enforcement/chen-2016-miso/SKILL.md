---
name: chen-2016-miso
description: >-
  对第一轮能够容纳全部基态热稳约束的预防性 DC-SCUC，先强制基态安全，再用 SFT 检查事故并逐轮加入全部新违反约束；适用于固定拓扑单回线 N-1 的外循环求解。
---

# Chen 2016：第一轮强制基态 watch-list，事故交给 SFT

Yonghong Chen, Aaron Casto, Fengyu Wang, Qun Zhou Wang, Xing Wang, Jie Wan. *Improving Large-Scale Day-Ahead Security Constrained Unit Commitment Performance.* IEEE Trans. Power Syst., 31(6), 2016.

## 算法解读

MISO 日前 SCUC 并不一次塞进全部 N-1。实际流程是：

1. 主问题 MIP 只含一份经验/例行的 **watch-list**（文中 routinely binding/critical 的线路，约数百条），用节点注入灵敏度写成线性热稳。
2. 解完后把解交给网络应用做 **SFT**，新发现的过载约束再送回 SCUC，热启动再解。
3. §III.C 也可把二进制钉死做子问题，把绑定或近绑定的行交回主问题。文中提到可用 solver lazy constraints 减轻「主问题越撑越大」。

本仓库没有 MISO 的虚增、RSG、IBM LR、Binary Reduction，那些不要实现。从论文抽出可执行的核心：

**第一轮强制全部基态热稳**（watch-list := 全体在役监测线的基态），事故热稳为零。这样第一解已经满足 N 热稳，迭代只处理 N-1。之后 SFT **只扫事故态**，新违反的事故键 **全部** 加回（事故侧是 TSR，不是 Xavier top-k）。热稳保持硬约束，不要改成带惩罚的软约束。

若连基态热稳都装不进第一轮 MIP，不要用本算法，改铜板起步的 Tejada/Xavier。

**整段算法：**

1. 建 MIP：UC + 系统平衡 + 全部基态 `(t, ℓ)` 两侧 PTDF 割（$F=\mathrm{rateA}$）。无事故 `theta/f`。
2. 早迭代可用较松 gap，`optimize`。
3. SFT 的开断集合不含基态。无事故违反：收紧到最终 gap 或停。
4. 否则把全部新违反事故键加成 PTDF 割，同一模型热启动。上限约 50 轮。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `select_watchlist_then_sft_chen`
- **Description**: MISO 两阶段思想：第一轮 MIP 必须含全部基态热稳（watch-list := 全部基态监测线），事故热稳不进第一轮；之后 SFT **只扫事故态**，把新违反的事故键全部加回（事故侧用 TSR，不用 Xavier top-k）。本工具分两步：`seed` 给出第一轮应强制的基态键；`iterate` 从事故违反里选出尚未加入的键。不要实现虚增、RSG、IBM LR、Binary Reduction。热稳不要改成带惩罚的软约束。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["phase"],
  "properties": {
    "phase": { "type": "string", "enum": ["seed", "iterate"], "description": "seed=第一轮基态 watch-list；iterate=从事故 SFT 选新割。" },
    "n_periods": { "type": "integer", "description": "seed 必填。时段数 T。" },
    "monitored_lines": {
      "type": "array",
      "items": { "type": "integer" },
      "description": "seed：在役监测线索引（不含离线）。"
    },
    "violations": {
      "type": "array",
      "description": "iterate：SFT 违反。必须已经排除基态（out_id=0）。",
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
      "items": { "type": "array", "items": { "type": "integer" }, "minItems": 3, "maxItems": 3 }
    }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

```python
from __future__ import annotations

from typing import Any


def select_watchlist_then_sft_chen(
    phase: str,
    n_periods: int | None = None,
    monitored_lines: list[int] | None = None,
    violations: list[dict] | None = None,
    already_added: list[list[int]] | None = None,
) -> dict[str, Any]:
    added = {tuple(x) for x in (already_added or [])}
    if any(len(x) != 3 for x in (already_added or [])):
        return {"ok": False, "error": "Error: already_added 的每个元素必须是 [t, out_id, ell]。"}

    if phase == "seed":
        if n_periods is None or n_periods < 1:
            return {"ok": False, "error": "Error: seed 需要 n_periods ≥ 1。"}
        if not monitored_lines:
            return {"ok": False, "error": "Error: seed 需要非空 monitored_lines（在役基态监测线）。"}
        selected = []
        for t in range(n_periods):
            for ell in monitored_lines:
                if int(ell) < 0:
                    return {"ok": False, "error": f"Error: monitored_lines 含负数 {ell}。"}
                key = (t, 0, int(ell))
                if key in added:
                    continue
                selected.append({"t": t, "out_id": 0, "ell": int(ell)})
        return {"ok": True, "phase": "seed", "selected": selected, "n_selected": len(selected)}

    if phase != "iterate":
        return {"ok": False, "error": "Error: phase 必须是 'seed' 或 'iterate'。"}
    if not violations:
        return {"ok": True, "phase": "iterate", "selected": [], "n_selected": 0, "converged": True}

    selected = []
    seen: set[tuple[int, int, int]] = set()
    for i, rec in enumerate(violations):
        try:
            t = int(rec["t"])
            c = int(rec["out_id"])
            ell = int(rec["ell"])
            gma = float(rec.get("gamma", 1.0))
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": f"Error: violations[{i}] 需要 t/out_id/ell。"}
        if c == 0:
            return {
                "ok": False,
                "error": (
                    "Error: iterate 阶段扫到基态违反 out_id=0。"
                    "第一轮应已强制全部基态热稳；请检查 seed 是否漏线，或 SFT 是否误扫基态。"
                ),
            }
        if gma <= 0:
            continue
        key = (t, c, ell)
        if key in added or key in seen:
            continue
        seen.add(key)
        selected.append({"gamma": gma, "t": t, "out_id": c, "ell": ell})
    return {
        "ok": True,
        "phase": "iterate",
        "selected": selected,
        "n_selected": len(selected),
        "converged": len(selected) == 0,
    }
```

建模：UC + 系统平衡，无全套事故 `theta/f`。`seed` 的键用基态 PTDF 割强制进去，再 `optimize`。之后 SFT 的 `outages` 不要含 0。事故违反用本工具 `iterate` 全量加回。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `phase` 非法 | `Error: phase 必须是 'seed' 或 'iterate'。` |
| seed 无线 | `Error: seed 需要非空 monitored_lines。` |
| iterate 出现基态违反 | `Error: iterate 阶段扫到基态违反 out_id=0。第一轮应已强制全部基态热稳；请检查 seed 是否漏线，或 SFT 是否误扫基态。` |
| 基态热稳已经装不下 | 不要用本工具，改铜板 + Xavier/Tejada |

不要做软约束惩罚。事故侧不要改成 top-k。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: $T=2$，在役监测线 0 和 1。先强制基态；再根据事故 SFT 加割。

**Thought**: 先 `seed` 把 `(t,0,ell)` 全加进去，再只扫事故。

**Action**（seed）:

```json
{
  "tool": "select_watchlist_then_sft_chen",
  "phase": "seed",
  "n_periods": 2,
  "monitored_lines": [0, 1]
}
```

**Action**（iterate）:

```json
{
  "tool": "select_watchlist_then_sft_chen",
  "phase": "iterate",
  "already_added": [[0, 0, 0], [0, 0, 1], [1, 0, 0], [1, 0, 1]],
  "violations": [{"gamma": 2.1, "t": 0, "out_id": 4, "ell": 1}]
}
```

**Observation**: seed 4 条基态键；iterate 选出 `(0,4,1)`。
