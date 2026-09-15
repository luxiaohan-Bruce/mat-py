---
name: castelli-2024-three-approaches
description: >-
  对支持 lazy-constraint 回调的固定拓扑 DC-SCUC，使用 Castelli M3 在整数候选解上检查单回线 N-1 并加入新违反的热稳约束；保持同一棵搜索树，结束时验证全部原安全约束。
---

# Castelli 2024：在 MIP incumbent 上 lazy 加入违反热稳

A. F. Castelli, I. Harjunkoski, J. Poland, M. Giuntoli, E. Martelli, I. E. Grossmann. *Solving the security constrained unit commitment problem: Three novel approaches.* Int. J. Electr. Power Energy Syst., 162, 110213, 2024.

## 算法解读

外循环（解完一个 MIP 再扫流、加割、重解）每次都会丢掉当前 B&B 树。本文比较四条路径，本 skill 默认 **M3**。

| 代号 | 做法 | 最优性 |
|------|------|--------|
| M1 | Xavier 式外循环：松弛 MIP → 扫流 → 加割 → 再 `optimize` | 保 |
| M2 | M1 + 每轮后对当前整数解做 QP 邻域滤子，把邻域里还过载的割一并加上 | 保 |
| M3 | **solver callback**：铜板/松弛 MIP 只建一次；B&B 每出现新 incumbent，在 callback 里算直流 N-1，lazy 加入违反的安全约束 | 保 |
| M4 | shrinking horizon + 非均匀时段 + callback | **不保**（文中约 1% 次优） |

M3 的含义：安全约束作为 lazy 约束交给求解器。`LazyConstraints=1`。只在 `MIPSOL`（整数可行解）上取 $P_g$ 做 SFT，不要在 `MIPNODE` 对 LP 松弛加点——松弛过载不代表整数解过载，乱加点会切掉合法区域或白加。论文演示可配合 top-k；为保持「扫完无违反 ⇒ 原问题可行」，默认 **全部新违反** 都 lazy 进去。

结束时 incumbent 必须无违反。时限到仍有违反视为失败，不要把带过载的 incumbent 当可行解。`MIPGap` 一次就用最终间隙，不要外循环改 gap。

M4 用缩短时域换时间，不保证原 24h 问题最优，**默认禁止**。求解器没有 callback 时不要调用 M3，退回 M1/M2（外循环 + 全量加违反）；M2 的 QP 滤子不是默认路径，不必实现。

**整段算法（M3）：**

1. 建铜板 UC + 系统平衡，无热稳变量。打开 lazy。
2. `optimize(callback)`。callback 仅处理 `MIPSOL`：取 $P_g$ → SFT → 对未加过的违反 `cbLazy` 两侧 PTDF 割。
3. 求解结束检查：若仍能扫到违反，失败。

SFT 必须快（每个 incumbent 都要扫），用基态 $B$ 一次 + LODF，不要每个事故再分解。

---

## 1. 技能元数据 (Skill Metadata)

- **Tool Name**: `lazy_thermal_from_incumbent_castelli`
- **Description**: Castelli M3：在同一棵 B&B 树里，每当求解器给出新的整数可行解（incumbent），对当前 $P_g$ 做直流 N-1 SFT，把尚未加入的违反热稳作为 lazy 约束加进去。保最优。默认加 **全部** 新违反（不要默认 top-k）。不要在 LP 松弛节点（MIPNODE）加点。不要默认 M4 shrinking-horizon（不保最优）。求解器不能 callback 时不要调用本工具，改外循环 TSR/Xavier。结束时 incumbent 必须无违反。

---

## 2. 输入参数定义 (Parameter Schema)

```json
{
  "type": "object",
  "required": ["violations"],
  "properties": {
    "violations": {
      "type": "array",
      "description": "当前 incumbent 上 SFT 的违反（含 alpha/beta/F，便于直接 cbLazy）。",
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
    "allow_m4": {
      "type": "boolean",
      "default": false,
      "description": "必须保持 false。true 表示用户明确允许 shrinking-horizon 次优，本工具仍拒绝并报错。"
    }
  }
}
```

---

## 3. 核心代码实现 (Python Implementation)

默认路径是 M3。M1 是外循环对照，M2 是外循环后再做 QP 邻域滤子，M4 不保最优。

```python
from __future__ import annotations

from typing import Any


def lazy_thermal_from_incumbent_castelli(
    violations: list[dict],
    already_added: list[list[int]] | None = None,
    allow_m4: bool = False,
) -> dict[str, Any]:
    if allow_m4:
        return {
            "ok": False,
            "error": "Error: M4 shrinking-horizon 不保最优，本工具拒绝。请保持 allow_m4=false，使用 M3 lazy callback。",
        }
    added = {tuple(x) for x in (already_added or [])}
    if any(len(x) != 3 for x in (already_added or [])):
        return {"ok": False, "error": "Error: already_added 的每个元素必须是 [t, out_id, ell]。"}

    lazy_cuts: list[dict[str, Any]] = []
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
                "error": f"Error: violations[{i}] 需要 t/out_id/ell/alpha/beta/F。请先对 incumbent 的 Pg 调用 sft_lodf_holzer。",
            }
        if F <= 0:
            return {"ok": False, "error": f"Error: violations[{i}] 的 F 必须 > 0。"}
        if not alpha:
            return {"ok": False, "error": f"Error: violations[{i}] 的 alpha 为空。"}
        key = (t, c, ell)
        if key in added or key in seen:
            continue
        seen.add(key)
        lazy_cuts.append(
            {
                "t": t,
                "out_id": c,
                "ell": ell,
                "alpha": alpha,
                "beta": beta,
                "F": F,
                "sense": "both",
            }
        )
    return {
        "ok": True,
        "lazy_cuts": lazy_cuts,
        "n_new": len(lazy_cuts),
        "incumbent_feasible": len(lazy_cuts) == 0,
    }
```

Gurobi 接线（调用方）：铜板 UC，`LazyConstraints=1`，只在 `where == GRB.Callback.MIPSOL` 时取 $P_g$、SFT、本工具、用 `cbLazy` 加入 $\alpha^{\mathsf T}P_{:,t}+\beta\le F$ 与对侧。`MIPGap` 用最终间隙，不要外循环改 gap。

```python
def cb(model, where):
    if where != GRB.Callback.MIPSOL:
        return
    Pg_hat = ...  # cbGetSolution
    sft = sft_lodf_holzer(..., pg=Pg_hat.tolist(), ...)
    out = lazy_thermal_from_incumbent_castelli(sft["violations"], already_added=list(added))
    for cut in out["lazy_cuts"]:
        expr = gp.LinExpr(cut["alpha"], pg_by_t[cut["t"]])
        model.cbLazy(expr + cut["beta"] <= cut["F"])
        model.cbLazy(-expr - cut["beta"] <= cut["F"])
        added.add((cut["t"], cut["out_id"], cut["ell"]))
```

不能 callback 时：退回外循环 + 全量加违反，不要偷偷开 M4。

---

## 4. 异常处理与降级策略 (Error Handling)

| 情况 | 返回 |
|------|------|
| `allow_m4=true` | `Error: M4 shrinking-horizon 不保最优，本工具拒绝。请保持 allow_m4=false，使用 M3 lazy callback。` |
| 缺割系数 | `Error: violations[i] 需要 t/out_id/ell/alpha/beta/F。请先对 incumbent 的 Pg 调用 sft_lodf_holzer。` |
| 本 incumbent 无新违反 | `incumbent_feasible=true` |
| 无 callback 接口 | 不要调用；改 Tejada/Xavier 外循环 |
| 在 MIPNODE 加点 | 不要做 |

时限到仍有违反 → 求解失败，不要把带违反的 incumbent 当可行。

---

## 5. Agent 调用示例 (Few-Shot Example)

**User Prompt**: Gurobi 刚找到一个整数解，SFT 报两条违反，其中一条已经 lazy 过。本节点加什么？

**Thought**: M3，只在 MIPSOL 上把新违反做成 lazy 两侧割。

**Action**:

```json
{
  "tool": "lazy_thermal_from_incumbent_castelli",
  "already_added": [[0, 3, 1]],
  "violations": [
    {"t": 0, "out_id": 3, "ell": 1, "alpha": [0.2, -0.1], "beta": 1.0, "F": 20, "gamma": 4.0},
    {"t": 0, "out_id": 5, "ell": 2, "alpha": [0.4, 0.0], "beta": 0.0, "F": 15, "gamma": 2.0}
  ]
}
```

**Observation**: 只返回第二条的两侧 lazy 割。`cbLazy` 后继续同一棵树。
