"""Build and query CATALOG.json / NETWORK_INDEX.json."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from .evaluate import evaluate
from .features import extract_features, source_network
from .runner import find_solver
from .taxonomy import spec_for

ROOT = Path(__file__).resolve().parents[1]


def iter_cases(root: Path | None = None) -> list[Path]:
    root = root or ROOT
    cases: list[Path] = []
    for cfg in root.glob("*/*/case*/data/config.json"):
        cases.append(cfg.parent.parent)
    return sorted(cases, key=lambda p: str(p.relative_to(root)))


def pack_of(case_dir: Path, root: Path | None = None) -> str:
    root = root or ROOT
    rel = case_dir.resolve().relative_to(root.resolve())
    return "/".join(rel.parts[:2])


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def case_record(case_dir: Path, root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    pack = pack_of(case_dir, root)
    cfg = _load(case_dir / "data" / "config.json")
    net = _load(case_dir / "data" / "network.json")
    spec = spec_for(pack, cfg)
    feats = extract_features(cfg, net, pack=pack)
    configured_features = cfg.get("features")
    if not isinstance(configured_features, dict):
        configured_features = {}
    math_class = configured_features.get("math_class") or spec["math_class"]
    solver_family = configured_features.get("solver_family") or spec["solver_family"]
    solver = find_solver(case_dir)
    rel = case_dir.resolve().relative_to(root.resolve())
    entry = None
    if solver is not None:
        try:
            entry = str(solver.resolve().relative_to(root.resolve()))
        except ValueError:
            entry = str(solver)
    sn = cfg.get("source_network") or source_network(cfg, net)
    return {
        "id": f"{pack}/{case_dir.name}",
        "path": str(rel).replace("\\", "/"),
        "pack": pack,
        "case": case_dir.name,
        "base_problem": spec["base_problem"],
        "variant": spec["variant"],
        "math_class": math_class,
        "solver_family": solver_family,
        "solve_tier": cfg.get("solve_tier") or "full",
        "source_network": sn,
        "features": feats,
        "entrypoint": entry,
        "seed": cfg.get("seed", 1),
        "time_limit": cfg.get("time_limit"),
        "mip_gap": cfg.get("mip_gap"),
        "maturity": cfg.get("maturity"),
        "validation_scope": cfg.get("validation_scope"),
        "physics_validated": cfg.get("physics_validated"),
        "known_limitations": cfg.get("known_limitations"),
        "classification_note": cfg.get("classification_note"),
    }


def build_catalog(root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    cases = [case_record(c, root) for c in iter_cases(root)]
    by_net: dict[str, list[str]] = defaultdict(list)
    for rec in cases:
        by_net[str(rec["source_network"])].append(rec["id"])
    catalog = {
        "schema_version": 1,
        "n_cases": len(cases),
        "cases": cases,
    }
    index = {
        "schema_version": 1,
        "n_networks": len(by_net),
        "networks": {k: sorted(v) for k, v in sorted(by_net.items())},
    }
    return {"catalog": catalog, "network_index": index}


def write_catalog(root: Path | None = None) -> tuple[Path, Path]:
    root = root or ROOT
    built = build_catalog(root)
    cat_path = root / "CATALOG.json"
    idx_path = root / "NETWORK_INDEX.json"
    cat_path.write_text(json.dumps(built["catalog"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    idx_path.write_text(json.dumps(built["network_index"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return cat_path, idx_path


def load_catalog(root: Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    return _load(root / "CATALOG.json")


def cases_on_network(name: str, root: Path | None = None) -> list[str]:
    root = root or ROOT
    idx = _load(root / "NETWORK_INDEX.json")
    nets = idx.get("networks") or {}
    if name in nets:
        return list(nets[name])
    hits = []
    for key, ids in nets.items():
        if name in key:
            hits.extend(ids)
    return hits


def backfill_config(case_dir: Path, root: Path | None = None) -> dict[str, Any]:
    """Write canonical fields into data/config.json. Returns updated config."""
    root = root or ROOT
    cfg_path = case_dir / "data" / "config.json"
    cfg = _load(cfg_path)
    if not cfg:
        return cfg
    pack = pack_of(case_dir, root)
    net = _load(case_dir / "data" / "network.json")
    spec = spec_for(pack, cfg)
    feats = extract_features(cfg, net, pack=pack)
    variant = dict(spec["variant"])
    configured_features = cfg.get("features")
    if not isinstance(configured_features, dict):
        configured_features = {}
    math_class = configured_features.get("math_class") or spec["math_class"]
    solver_family = configured_features.get("solver_family") or spec["solver_family"]
    cfg["base_problem"] = spec["base_problem"]
    cfg["variant"] = variant
    cfg["source_network"] = source_network(cfg, net)
    cfg["features"] = {
        **feats,
        "math_class": math_class,
        "solver_family": solver_family,
    }
    if not cfg.get("solve_tier"):
        bucket = str(cfg.get("size_bucket") or "").upper()
        if bucket in {"XL", "XXL"}:
            cfg["solve_tier"] = "skip"
        elif bucket in {"L", "M"}:
            cfg["solve_tier"] = "relaxed"
        else:
            cfg["solve_tier"] = "full"
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return cfg


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--rebuild" in args or not args:
        cat, idx = write_catalog()
        data = json.loads(cat.read_text(encoding="utf-8"))
        print(f"wrote {cat} ({data.get('n_cases')} cases)")
        print(f"wrote {idx}")
        return 0
    if "--by-network" in args:
        i = args.index("--by-network")
        name = args[i + 1] if i + 1 < len(args) else ""
        hits = cases_on_network(name)
        print(f"{name}: {len(hits)}")
        for h in hits:
            print(f"  {h}")
        return 0
    if "--evaluate-all" in args:
        fail = 0
        n = 0
        skipped = 0
        for case in iter_cases():
            ev = evaluate(case)
            n += 1
            if ev["status"] == "SKIP":
                skipped += 1
            if not ev["passed"]:
                fail += 1
                print(f"FAIL {ev['path']} {ev['reason']}")
        print(f"evaluated={n} skipped={skipped} failed={fail}")
        return 1 if fail else 0
    print("usage: python3 -m framework.catalog [--rebuild|--by-network NAME|--evaluate-all]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
