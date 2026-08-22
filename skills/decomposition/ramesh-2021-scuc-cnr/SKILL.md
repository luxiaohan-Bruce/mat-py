# Ramesh 2021：主问题 UC + 事故可行割（无开关则不要 CNR）

Arun Ramamurthy Ramesh, Xingpeng Li, Kory W. Hedman. *An Accelerated-Decomposition Approach for Security-Constrained Unit Commitment With Corrective Network Reconfiguration.* IEEE Trans. Power Syst., 2021.

## 算法解读

完整 SCUC-CNR 允许事故后用开关把系统从紧急态拉回（corrective network reconfiguration），引入二进制 `z_k`，子问题变成 MILP。作者用 Benders 拆开：

- **MUC**（master unit commitment）：基态约束的松弛 MILP，给出开机与出力。
- **PCFC**（post-contingency feasibility check）：把 master 的 `Pg` 钉住，检查事故直流是否可行。
- **CSPS**：先用代数潮流筛掉明显可行的 `(t, 事故)`，只对可能不可行的场景做检查，少解 LP。
- **NR-PCFC / CNR**：仅当 PCFC 不可行时，按「离事故元件最近的可开关支路」一次断一条再查可行。这是启发式，不保证 CNR 最优。

本仓库预防性 SCUC **没有开关、事故后不另设 `Pg^{c,t}`**。可执行的是 **A-SCUC**：CSPS + 把违反的热稳作为可行割加回 master。禁止发明 `z_k`。论文 PCFC 允许事故后 10 min 再调度；预防性模型禁止那样做，割必须写在同一套 `Pg` 上（PTDF 热稳）。

CSPS 的代数规则：当前 `Pg` → 基态流 → LODF 事故流。任一在役监测线 `γ` 超容差 → 该 `(t, 事故)` 为 **critical**。`B` 奇异 / 解列也视为 critical。然后只对 critical 场景里**已经违反的监测线**加两侧 PTDF 割，不要把该场景全部线路一次倒进 master。

**整段算法（A-SCUC）：**

1. Master：UC + 每时段系统平衡。可选加基态热稳。无全套事故 `theta/f`，无开关变量。
2. 解 master，得 `Pg`。
3. CSPS / SFT 列出违反。无新违反且已到最终 gap → 停。
4. 把新违反加成可行割，热启动 master，回到 2。上限约 50 轮。早迭代可用较松 gap。

**CNR：** 仅当数据里真有 `switchable` 支路（或 `n_switchable>0`）且要做事故后开关时才启用。否则整段跳过。启用时仍是启发式：PCFC 不可行才试邻近开关，不保证开关方案最优。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `benders_critical_cuts_ramesh`
- **Description**: A-SCUC：主问题只有 UC + 系统平衡（可选基态热稳），事故不进主 MIP。对当前 master 的 `Pg` 做代数 CSPS：任一在役线过载则该 `(t, out_id)` 为 critical，把这些违反的 PTDF 热稳作为可行割加回 master。不要为非 critical 场景解事故 LP。预防性模型禁止另设事故后再调度 `Pg^{c,t}`。没有可开关支路时禁止发明开关二进制、禁止走 CNR。有 `switchable` 才允许在 PCFC 不可行时试邻近开关（启发式，不保证 CNR 最优）。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["violations"],
  "properties": {
    "violations": {
      "type": "array",
      "description": "对当前 master 的 Pg 做 SFT/CSPS 得到的违反（须带 alpha/beta/F）。",
      "items": {
        "type": "object",
        "required": ["t", "out_id", "ell", "alpha", "beta", "F"],
        "properties": {
          "t": { "type": "integer" },
          "out_id": { "type": "integer" },
          "ell": { "type": "integer" },
          "alpha": { "type": "array", "items": { "type": "number" } },
          "beta": { "type": "number" },
          "F": { "type": "number" },
          "gamma": { "type": "number" }
        }
      }
    },
    "already_added": {
      "type": "array",
      "items": { "type": "array", "items": { "type": "integer" }, "minItems": 3, "maxItems": 3 }
    },
    "n_switchable": {
      "type": "integer",
      "default": 0,
      "description": "可开关支路数。0 表示禁止 CNR。"
    },
    "enable_cnr": {
      "type": "boolean",
      "default": false,
      "description": "仅当 n_switchable>0 且用户明确要 CNR 时为 true。"
    }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

CSPS（代数，不解 LP）：当前 `Pg` → 基态流 → LODF 事故流。任一在役线 `γ>0` → `(t,c)` critical。岛解 / `B` 奇异视为该 `c` critical（SFT 的 `skipped_outages` 按 critical 处理，整场景保留到下一轮检查）。

割：只对 critical 场景里已经违反的监测线加两侧 PTDF，不要一次倒入该场景全部线路。

```python
from __future__ import annotations

from typing import Any


def benders_critical_cuts_ramesh(
    violations: list[dict],
    already_added: list[list[int]] | None = None,
    n_switchable: int = 0,
    enable_cnr: bool = False,
) -> dict[str, Any]:
    if enable_cnr and n_switchable <= 0:
        return {
            "ok": False,
            "error": (
                "Error: 没有可开关支路（n_switchable=0），禁止 CNR，也不要发明开关二进制。"
                "请令 enable_cnr=false，只加事故可行割。"
            ),
        }
    if n_switchable < 0:
        return {"ok": False, "error": "Error: n_switchable 不能为负。"}
    added = {tuple(x) for x in (already_added or [])}
    if any(len(x) != 3 for x in (already_added or [])):
        return {"ok": False, "error": "Error: already_added 的每个元素必须是 [t, out_id, ell]。"}

    cuts: list[dict[str, Any]] = []
    critical: set[tuple[int, int]] = set()
    seen: set[tuple[int, int, int]] = set()
    for i, rec in enumerate(violations):
        try:
            t = int(rec["t"])
            c = int(rec["out_id"])
            ell = int(rec["ell"])
            alpha = [float(x) for x in rec["alpha"]]
            beta = float(rec["beta"])
            F = float(rec["F"])
        except (KeyError, TypeError, ValueError):
            return {
                "ok": False,
                "error": f"Error: violations[{i}] 需要 t/out_id/ell/alpha/beta/F。请先对 master 的 Pg 做 SFT/CSPS。",
            }
        if F <= 0 or not alpha:
            return {"ok": False, "error": f"Error: violations[{i}] 的 alpha/F 非法。"}
        critical.add((t, c))
        key = (t, c, ell)
        if key in added or key in seen:
            continue
        seen.add(key)
        cuts.append({"t": t, "out_id": c, "ell": ell, "alpha": alpha, "beta": beta, "F": F})

    return {
        "ok": True,
        "critical_scenarios": [{"t": t, "out_id": c} for t, c in sorted(critical)],
        "cuts": cuts,
        "n_cuts": len(cuts),
        "converged": len(cuts) == 0,
        "cnr": False if n_switchable <= 0 else bool(enable_cnr),
    }
```

外循环：解 master → SFT/CSPS → 本工具 → 把 `cuts` 作为可行割加进 master 并热启动。无新割则停。主问题不要建全套事故 `theta/f`，不要另设 `Pg^{c,t}`。

CNR（仅 `cnr=true`）：PCFC 不可行时，按离事故元件最近的可开关支路一次断一条再查可行。这是启发式。预防性默认不走。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `enable_cnr` 且无开关 | `Error: 没有可开关支路（n_switchable=0），禁止 CNR，也不要发明开关二进制。请令 enable_cnr=false，只加事故可行割。` |
| 缺割系数 | `Error: violations[i] 需要 t/out_id/ell/alpha/beta/F。请先对 master 的 Pg 做 SFT/CSPS。` |
| 无新割 | `converged=true` |
| 想事故后再调度 | 不要调用本工具去加 `Pg^{c,t}`；预防性语义是一套 `Pg` |

不要一次把某事故的全部线路倒进 master，只加已经违反的行。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: 预防性 SCUC，无开关。Master 当前解在事故 4、时段 0 让线 1 过载。加什么割？

**Thought**: CSPS 标 `(0,4)` critical，只把这条违反加成可行割。`enable_cnr=false`。

**Action**:

```json
{
  "tool": "benders_critical_cuts_ramesh",
  "n_switchable": 0,
  "enable_cnr": false,
  "already_added": [],
  "violations": [
    {
      "t": 0, "out_id": 4, "ell": 1,
      "alpha": [0.25, -0.05], "beta": 2.0, "F": 30, "gamma": 1.2
    }
  ]
}
```

**Observation**: `critical_scenarios=[(0,4)]`，一条两侧 PTDF 可行割加进 master。不要引入 `z_k`。
