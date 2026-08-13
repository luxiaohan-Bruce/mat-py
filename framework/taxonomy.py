"""Load canonical pack taxonomy from ``BASE_PROBLEM_REGISTRY.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "BASE_PROBLEM_REGISTRY.json"


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    """Read the machine-readable taxonomy registry.

    The file is intentionally read on demand instead of being duplicated in
    Python.  This keeps catalog generation and taxonomy validation on the same
    source of truth when packs are added or moved.
    """
    registry_path = Path(path) if path is not None else REGISTRY_PATH
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read taxonomy registry {registry_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"taxonomy registry {registry_path} must contain an object")
    return data


def _pack_spec(pack: str, registry: dict[str, Any]) -> dict[str, Any]:
    packs = registry.get("packs")
    raw = packs.get(pack) if isinstance(packs, dict) else None
    if not isinstance(raw, dict):
        return {
            "base_problem": "unknown",
            "math_class": "unknown",
            "solver_family": "unknown",
            "variant": {},
        }
    return {
        "base_problem": raw.get("base_problem", "unknown"),
        "math_class": raw.get("default_math_class", "unknown"),
        "solver_family": raw.get("default_solver_family", "unknown"),
        "variant": dict(raw.get("default_variant") or {}),
    }


def pack_specs(registry: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Return the legacy ``PACK_SPEC`` view derived from the registry."""
    data = registry or load_registry()
    packs = data.get("packs") or {}
    return {str(pack): _pack_spec(str(pack), data) for pack in packs}


def spec_for(
    pack: str,
    config: dict[str, Any] | None = None,
    *,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return pack defaults with case ``variant`` values merged on top."""
    spec = _pack_spec(pack, registry or load_registry())
    cfg = config or {}
    variant = cfg.get("variant")
    if isinstance(variant, dict):
        spec["variant"].update(variant)
    return spec


# Compatibility for callers that inspect this name.  Runtime lookups use
# ``spec_for`` and therefore always read the registry supplied for that run.
PACK_SPEC = pack_specs()
