"""Parse GO Competition Challenge 1 RAW/ROP/INL/CON into internal JSON network."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _split_csv_line(line: str) -> list[str]:
    # handle quoted fields
    out: list[str] = []
    cur = ""
    in_q = False
    for ch in line:
        if ch == "'":
            in_q = not in_q
            continue
        if ch == "," and not in_q:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _sections(raw_text: str) -> list[list[str]]:
    parts: list[list[str]] = []
    cur: list[str] = []
    for line in raw_text.splitlines():
        s = line.strip()
        if s == "0" or s.startswith("0 /") or s.startswith("0/"):
            parts.append(cur)
            cur = []
        else:
            if line.strip():
                cur.append(line.rstrip())
    if cur:
        parts.append(cur)
    return parts


def parse_raw(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    parts = _sections(text)
    if len(parts) < 5:
        raise ValueError(f"unexpected RAW structure in {path}: {len(parts)} sections")
    # system
    sys_fields = _split_csv_line(parts[0][0])
    baseMVA = float(sys_fields[1]) if len(sys_fields) > 1 else 100.0
    buses = []
    for line in parts[0][3:]:  # skip system + 2 comments
        f = _split_csv_line(line)
        if not f or not f[0]:
            continue
        buses.append(
            {
                "bus_i": int(float(f[0])),
                "baseKV": float(f[2]) if len(f) > 2 else 138.0,
                "type": int(float(f[3])) if len(f) > 3 else 1,
                "Vm": float(f[7]) if len(f) > 7 else 1.0,
                "Va": float(f[8]) if len(f) > 8 else 0.0,
                "Vmax": float(f[9]) if len(f) > 9 else 1.1,
                "Vmin": float(f[10]) if len(f) > 10 else 0.9,
                "Pd": 0.0,
                "Qd": 0.0,
            }
        )
    bus_map = {b["bus_i"]: b for b in buses}
    # loads
    for line in parts[1]:
        f = _split_csv_line(line)
        if len(f) < 6:
            continue
        bid = int(float(f[0]))
        status = int(float(f[2])) if len(f) > 2 else 1
        if status == 0:
            continue
        pd = float(f[5]); qd = float(f[6]) if len(f) > 6 else 0.0
        if bid in bus_map:
            bus_map[bid]["Pd"] += pd
            bus_map[bid]["Qd"] += qd
    # PSS/E v33 fixed section order after buses:
    # 1 load, 2 fixed shunt, 3 generator, 4 non-transformer branch, 5 transformer, ...
    gens = []
    gen_sec = parts[3] if len(parts) > 3 else []
    for line in gen_sec:
        f = _split_csv_line(line)
        if len(f) < 17:
            continue
        try:
            bus = int(float(f[0]))
            gid = f[1]
            pg = float(f[2])
            qg = float(f[3])
            qt = float(f[4])
            qb = float(f[5])
            status = int(float(f[14]))
            pmax = float(f[16])
            pmin = float(f[17]) if len(f) > 17 else 0.0
        except ValueError:
            continue
        gens.append(
            {
                "bus": bus,
                "id": gid,
                "Pg": pg,
                "Qg": qg,
                "Qmax": qt,
                "Qmin": qb,
                "status": status,
                "Pmax": pmax,
                "Pmin": pmin,
                "c1": 20.0,
                "c0": 0.0,
                "alpha": 0.0,
            }
        )

    branches = []
    bid = 0
    # non-transformer branches: fbus,tbus,ckt,r,x,b,rateA,rateB,rateC,...,status
    branch_sec = parts[4] if len(parts) > 4 else []
    for line in branch_sec:
        f = _split_csv_line(line)
        if len(f) < 14:
            continue
        try:
            fb, tb = int(float(f[0])), int(float(f[1]))
            r, x = float(f[3]), float(f[4])
            bch = float(f[5])
            rateA = float(f[6]) or 9999.0
            rateB = float(f[7]) or rateA
            rateC = float(f[8]) or rateA
            st = int(float(f[13]))
        except ValueError:
            continue
        if abs(x) < 1e-8:
            x = 1e-5
        bid += 1
        branches.append(
            {
                "id": bid,
                "fbus": fb,
                "tbus": tb,
                "ckt": f[2],
                "r": r,
                "x": x,
                "b": bch,
                "rateA": rateA,
                "rateB": rateB,
                "rateC": rateC,
                "ratio": 0.0,
                "status": st,
                "kind": "line",
            }
        )

    # transformers: 4-line records
    xf_sec = parts[5] if len(parts) > 5 else []
    i = 0
    while i + 3 < len(xf_sec):
        h = _split_csv_line(xf_sec[i])
        w1 = _split_csv_line(xf_sec[i + 1])
        w2 = _split_csv_line(xf_sec[i + 2])
        # fourth line skipped
        if len(h) < 12 or len(w1) < 2 or len(w2) < 3:
            i += 1
            continue
        try:
            fb, tb = int(float(h[0])), int(float(h[1]))
            r, x = float(w1[0]), float(w1[1])
            rateA = float(w2[2]) or 9999.0
            rateB = float(w2[3]) if len(w2) > 3 else rateA
            rateC = float(w2[4]) if len(w2) > 4 else rateA
            st = int(float(h[11]))
            ratio = float(w2[0]) if w2[0] else 1.0
        except ValueError:
            i += 1
            continue
        if abs(x) < 1e-8:
            x = 1e-5
        bid += 1
        branches.append(
            {
                "id": bid,
                "fbus": fb,
                "tbus": tb,
                "ckt": h[3] if len(h) > 3 else "1",
                "r": r,
                "x": x,
                "b": 0.0,
                "rateA": rateA,
                "rateB": rateB or rateA,
                "rateC": rateC or rateA,
                "ratio": ratio,
                "status": st,
                "kind": "xfmr",
            }
        )
        i += 4

    # ensure ref bus
    if not any(int(b["type"]) == 3 for b in buses):
        # choose first gen bus
        if gens:
            bus_map[int(gens[0]["bus"])]["type"] = 3
        else:
            buses[0]["type"] = 3

    return {
        "baseMVA": baseMVA,
        "buses": buses,
        "gens": gens,
        "branches": branches,
    }


def parse_rop(path: Path, gens: list[dict]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    # After "BEGIN ACTIVE POWER DISPATCH TABLES" there are tables; simplified:
    # look for lines with many numeric cost points: tbl,pmax,c0,c1,c2... or gen dispatch maps
    # GO ROP has generator dispatch data then cost curves.
    # Heuristic: find block "BEGIN GENERATOR DISPATCH DATA" ... map bus,genid -> table
    # then "BEGIN ACTIVE POWER DISPATCH TABLES" with cost coefficients.
    gen_table: dict[tuple[int, str], int] = {}
    in_disp = False
    in_tables = False
    tables: dict[int, list[float]] = {}
    cur_tbl = None
    for line in text.splitlines():
        s = line.strip().upper()
        if "BEGIN GENERATOR DISPATCH DATA" in s:
            in_disp = True
            in_tables = False
            continue
        if "END OF GENERATOR DISPATCH" in s:
            in_disp = False
            continue
        if "BEGIN ACTIVE POWER DISPATCH TABLES" in s:
            in_tables = True
            in_disp = False
            continue
        if "END OF ACTIVE POWER DISPATCH TABLES" in s:
            in_tables = False
            continue
        if in_disp and line.strip() and not line.strip().startswith("0"):
            f = _split_csv_line(line)
            if len(f) >= 4:
                try:
                    bus = int(float(f[0])); gid = f[1]; tbl = int(float(f[3]))
                    gen_table[(bus, gid)] = tbl
                except ValueError:
                    pass
        if in_tables and line.strip() and not line.strip().startswith("0"):
            f = _split_csv_line(line)
            # table records vary; common: table_num, pmax, c, c, c...
            if len(f) >= 3:
                try:
                    # first field table id if integer small
                    tid = int(float(f[0]))
                    # cost points often pairs; use linear c1 from last-first if possible
                    nums = [float(x) for x in f[1:] if x not in ("",)]
                    tables.setdefault(tid, []).extend(nums)
                except ValueError:
                    pass
    # apply: for each gen, set c1 from table if possible
    for g in gens:
        key = (int(g["bus"]), str(g["id"]))
        # id may be stored without quotes consistency
        tid = gen_table.get(key)
        if tid is None:
            # try strip
            for (b, i), t in gen_table.items():
                if b == int(g["bus"]) and i.strip() == str(g["id"]).strip():
                    tid = t
                    break
        if tid is not None and tid in tables and tables[tid]:
            nums = tables[tid]
            # heuristic linear cost: if >=2 numbers take last as $/MWh-ish or average positive
            pos = [x for x in nums if x > 0]
            g["c1"] = float(pos[0]) if pos else 20.0
            g["c0"] = 0.0


def parse_inl(path: Path, gens: list[dict]) -> None:
    if not path.exists():
        return
    # lines: bus, genid, H, Pmax?, ... participation related
    # GO INL: bus, id, response rate or alpha
    text = path.read_text(encoding="utf-8", errors="replace")
    alphas: dict[tuple[int, str], float] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("0"):
            continue
        f = _split_csv_line(s)
        if len(f) < 3:
            continue
        try:
            bus = int(float(f[0])); gid = f[1]
            # field 2 often participation-related constant; use abs and normalize later
            alpha = abs(float(f[2]))
            alphas[(bus, gid)] = alpha
        except ValueError:
            continue
    for g in gens:
        a = alphas.get((int(g["bus"]), str(g["id"])))
        if a is None:
            for (b, i), v in alphas.items():
                if b == int(g["bus"]) and i.strip() == str(g["id"]).strip():
                    a = v
                    break
        g["alpha"] = float(a or 0.0)
    # normalize among in-service gens
    total = sum(float(g["alpha"]) for g in gens if int(g.get("status", 1)) == 1 and float(g["alpha"]) > 0)
    if total <= 0:
        n = sum(1 for g in gens if int(g.get("status", 1)) == 1)
        for g in gens:
            g["alpha"] = 1.0 / n if int(g.get("status", 1)) == 1 and n else 0.0
    else:
        for g in gens:
            if int(g.get("status", 1)) == 1:
                g["alpha"] = float(g["alpha"]) / total
            else:
                g["alpha"] = 0.0


def parse_con(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    conts: list[dict[str, Any]] = []
    cur_name = None
    cur: dict[str, Any] | None = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        up = s.upper()
        if up.startswith("CONTINGENCY"):
            cur_name = s.split(None, 1)[1] if len(s.split(None, 1)) > 1 else f"c{len(conts)}"
            cur = {"name": cur_name, "branch": None, "gen_bus": None, "gen_id": None}
        elif cur is not None and up.startswith("OPEN BRANCH"):
            # OPEN BRANCH FROM BUS n TO BUS m CIRCUIT c
            m = re.search(r"FROM BUS\s+(\d+)\s+TO BUS\s+(\d+)", up)
            ckt = re.search(r"CIRCUIT\s+(\S+)", up)
            if m:
                cur["branch"] = {
                    "fbus": int(m.group(1)),
                    "tbus": int(m.group(2)),
                    "ckt": (ckt.group(1).strip("'") if ckt else "1"),
                }
        elif cur is not None and up.startswith("REMOVE UNIT"):
            m = re.search(r"REMOVE UNIT\s+(\S+)\s+FROM BUS\s+(\d+)", up)
            if m:
                cur["gen_id"] = m.group(1).strip("'")
                cur["gen_bus"] = int(m.group(2))
        elif up == "END" and cur is not None:
            conts.append(cur)
            cur = None
    return conts


def resolve_files(scenario_raw: Path) -> dict[str, Path]:
    """Locate rop/inl/con for a scenario raw path."""
    scen_dir = scenario_raw.parent
    net_dir = scen_dir.parent if scen_dir.name.startswith("scenario") else scen_dir
    def find(name: str) -> Path:
        for p in (scen_dir / name, net_dir / name):
            if p.exists():
                return p
        return net_dir / name
    return {
        "raw": scenario_raw,
        "rop": find("case.rop"),
        "inl": find("case.inl"),
        "con": find("case.con"),
    }


def load_scenario(raw_path: Path) -> dict[str, Any]:
    files = resolve_files(raw_path)
    net = parse_raw(files["raw"])
    parse_rop(files["rop"], net["gens"])
    parse_inl(files["inl"], net["gens"])
    conts = parse_con(files["con"])
    net["contingencies_all"] = conts
    net["source_files"] = {k: str(v) for k, v in files.items()}
    return net
