"""Load case JSON and write solver results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_case(case_dir: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    case_dir = Path(case_dir)
    network = json.loads((case_dir / "data" / "network.json").read_text(encoding="utf-8"))
    config = json.loads((case_dir / "data" / "config.json").read_text(encoding="utf-8"))
    return network, config


def write_result(case_dir: str | Path, name: str, payload: dict[str, Any]) -> Path:
    out_dir = Path(case_dir) / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
