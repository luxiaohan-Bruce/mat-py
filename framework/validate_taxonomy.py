"""Validate registry, case metadata, features, entrypoints, and catalog."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from framework.catalog import iter_cases, pack_of
    from framework.features import extract_features, source_network
    from framework.runner import find_solver
    from framework.taxonomy import load_registry
else:
    from .catalog import iter_cases, pack_of
    from .features import extract_features, source_network
    from .runner import find_solver
    from .taxonomy import load_registry

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


def _issue(code: str, path: str | Path, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=str(path), message=message)


def _load_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, str(exc)
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
    if not isinstance(data, dict):
        return None, "top-level JSON value must be an object"
    return data, None


def _duplicates(values: Iterable[Any]) -> set[Any]:
    seen: set[Any] = set()
    repeated: set[Any] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def validate_registry(registry: dict[str, Any]) -> list[ValidationIssue]:
    """Validate the registry itself before using it to validate cases."""
    issues: list[ValidationIssue] = []
    here = "BASE_PROBLEM_REGISTRY.json"

    domains = registry.get("navigation_domains")
    bases = registry.get("base_problems")
    packs = registry.get("packs")
    variants = registry.get("variant_dimensions")
    math_classes = registry.get("math_classes")
    solver_families = registry.get("solver_families")
    solve_tiers = registry.get("solve_tiers")
    contract = registry.get("contract")

    for name, value, expected in (
        ("navigation_domains", domains, dict),
        ("base_problems", bases, dict),
        ("packs", packs, dict),
        ("variant_dimensions", variants, dict),
        ("math_classes", math_classes, list),
        ("solver_families", solver_families, list),
        ("solve_tiers", solve_tiers, list),
        ("contract", contract, dict),
    ):
        if not isinstance(value, expected) or not value:
            issues.append(_issue("registry_shape", here, f"{name} must be a non-empty {expected.__name__}"))

    if issues:
        return issues

    base_ids: list[str] = []
    for base_problem, metadata in bases.items():
        if not isinstance(metadata, dict):
            issues.append(_issue("base_problem", here, f"base problem {base_problem!r} metadata must be an object"))
            continue
        stable_id = metadata.get("id")
        if not isinstance(stable_id, str) or not stable_id.startswith("B") or not stable_id[1:].isdigit():
            issues.append(_issue("base_problem_id", here, f"base problem {base_problem!r} needs a B<number> id"))
        else:
            base_ids.append(stable_id)
    duplicate_ids = _duplicates(base_ids)
    if duplicate_ids:
        issues.append(_issue("base_problem_id", here, f"duplicate base problem ids: {sorted(duplicate_ids)}"))
    expected_ids = {f"B{i:02d}" for i in range(1, len(bases) + 1)}
    if set(base_ids) != expected_ids:
        issues.append(
            _issue(
                "base_problem_id",
                here,
                f"base problem ids must be contiguous; expected={sorted(expected_ids)}, actual={sorted(base_ids)}",
            )
        )

    for field, values in (
        ("math_classes", math_classes),
        ("solver_families", solver_families),
        ("solve_tiers", solve_tiers),
    ):
        if any(not isinstance(value, str) or not value for value in values):
            issues.append(_issue("registry_enum", here, f"{field} must contain non-empty strings"))
        duplicates = _duplicates(values)
        if duplicates:
            issues.append(_issue("registry_enum", here, f"{field} contains duplicates: {sorted(duplicates)}"))

    required_variant = contract.get("required_variant_fields")
    required_features = contract.get("required_feature_fields")
    trust_metadata = contract.get("trust_metadata")
    if not isinstance(required_variant, list) or not required_variant:
        issues.append(_issue("registry_contract", here, "required_variant_fields must be a non-empty list"))
        required_variant = []
    if not isinstance(required_features, list) or not required_features:
        issues.append(_issue("registry_contract", here, "required_feature_fields must be a non-empty list"))
    if not isinstance(trust_metadata, dict):
        issues.append(_issue("registry_contract", here, "trust_metadata must be an object"))
    else:
        required_packs = trust_metadata.get("required_packs")
        maturity_values = trust_metadata.get("maturity_values")
        scope_values = trust_metadata.get("validation_scope_values")
        if not isinstance(required_packs, list) or not required_packs:
            issues.append(_issue("registry_contract", here, "trust_metadata.required_packs must be non-empty"))
        elif unknown := sorted(set(required_packs) - set(packs)):
            issues.append(_issue("registry_contract", here, f"unknown trust-metadata packs: {unknown}"))
        if not isinstance(maturity_values, list) or not maturity_values:
            issues.append(_issue("registry_contract", here, "trust_metadata.maturity_values must be non-empty"))
        if not isinstance(scope_values, list) or not scope_values:
            issues.append(
                _issue("registry_contract", here, "trust_metadata.validation_scope_values must be non-empty")
            )

    for dimension, allowed in variants.items():
        if not isinstance(allowed, list) or not allowed:
            issues.append(_issue("variant_dimension", here, f"variant dimension {dimension!r} needs allowed values"))
        elif any(not isinstance(value, str) or not value for value in allowed):
            issues.append(_issue("variant_dimension", here, f"variant dimension {dimension!r} has a non-string value"))

    for pack, spec in packs.items():
        path = f"{here}:packs.{pack}"
        if not isinstance(spec, dict):
            issues.append(_issue("pack_spec", path, "pack specification must be an object"))
            continue
        parts = str(pack).split("/")
        if len(parts) != 2 or not all(parts):
            issues.append(_issue("pack_path", path, "pack key must be NAVIGATION-DOMAIN/PACK"))
            continue
        domain = spec.get("navigation_domain")
        if domain != parts[0]:
            issues.append(_issue("navigation_domain", path, f"navigation_domain must equal path domain {parts[0]!r}"))
        if domain not in domains:
            issues.append(_issue("navigation_domain", path, f"unknown navigation domain {domain!r}"))
        base_problem = spec.get("base_problem")
        if base_problem not in bases:
            issues.append(_issue("base_problem", path, f"unknown base_problem {base_problem!r}"))

        default_math = spec.get("default_math_class")
        allowed_math = spec.get("allowed_math_classes")
        if not isinstance(allowed_math, list) or not allowed_math:
            issues.append(_issue("math_class", path, "allowed_math_classes must be a non-empty list"))
        else:
            if default_math not in allowed_math:
                issues.append(_issue("math_class", path, "default_math_class must be allowed"))
            unknown = sorted(set(allowed_math) - set(math_classes))
            if unknown:
                issues.append(_issue("math_class", path, f"unknown allowed math classes: {unknown}"))

        default_solver = spec.get("default_solver_family")
        allowed_solver = spec.get("allowed_solver_families")
        if not isinstance(allowed_solver, list) or not allowed_solver:
            issues.append(_issue("solver_family", path, "allowed_solver_families must be a non-empty list"))
        else:
            if default_solver not in allowed_solver:
                issues.append(_issue("solver_family", path, "default_solver_family must be allowed"))
            unknown = sorted(set(allowed_solver) - set(solver_families))
            if unknown:
                issues.append(_issue("solver_family", path, f"unknown allowed solver families: {unknown}"))

        default_variant = spec.get("default_variant")
        if not isinstance(default_variant, dict):
            issues.append(_issue("variant", path, "default_variant must be an object"))
            continue
        missing = sorted(set(required_variant) - set(default_variant))
        if missing:
            issues.append(_issue("variant", path, f"default_variant is missing {missing}"))
        issues.extend(_validate_variant(default_variant, variants, path))
    return issues


def _validate_variant(
    variant: dict[str, Any],
    dimensions: dict[str, Any],
    path: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for key, value in variant.items():
        allowed = dimensions.get(key)
        if allowed is None:
            issues.append(_issue("variant_dimension", path, f"unregistered variant dimension {key!r}"))
        elif value not in allowed:
            issues.append(_issue("variant_value", path, f"{key}={value!r} is not in {allowed!r}"))
    return issues


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _is_meta(config: dict[str, Any]) -> bool:
    problem = str(config.get("problem") or "")
    return problem == "meta" or problem.endswith("_meta")


def _validate_case(
    case_dir: Path,
    root: Path,
    registry: dict[str, Any],
) -> tuple[list[ValidationIssue], dict[str, Any] | None]:
    issues: list[ValidationIssue] = []
    rel = _relative(case_dir, root)
    cfg_path = case_dir / "data" / "config.json"
    net_path = case_dir / "data" / "network.json"
    config, error = _load_object(cfg_path)
    if config is None:
        return [_issue("config_json", _relative(cfg_path, root), error or "cannot load")], None
    network, error = _load_object(net_path)
    if network is None:
        return [_issue("network_json", _relative(net_path, root), error or "cannot load")], None

    pack = pack_of(case_dir, root)
    pack_spec = registry["packs"].get(pack)
    if not isinstance(pack_spec, dict):
        return [_issue("unregistered_pack", rel, f"pack {pack!r} is absent from registry")], None

    contract = registry["contract"]
    for field in contract.get("required_config_fields") or []:
        if field not in config:
            issues.append(_issue("config_field", rel, f"missing required config field {field!r}"))
    if config.get("case") != case_dir.name:
        issues.append(_issue("case_id", rel, f"config.case={config.get('case')!r}; expected {case_dir.name!r}"))
    if config.get("base_problem") != pack_spec.get("base_problem"):
        issues.append(
            _issue(
                "base_problem",
                rel,
                f"config={config.get('base_problem')!r}; registry={pack_spec.get('base_problem')!r}",
            )
        )

    tier = config.get("solve_tier")
    if tier not in registry["solve_tiers"]:
        issues.append(_issue("solve_tier", rel, f"unsupported solve_tier {tier!r}"))

    trust_metadata = contract.get("trust_metadata") or {}
    if pack in (trust_metadata.get("required_packs") or []):
        maturity = config.get("maturity")
        validation_scope = config.get("validation_scope")
        physics_validated = config.get("physics_validated")
        if maturity not in (trust_metadata.get("maturity_values") or []):
            issues.append(_issue("trust_metadata", rel, f"unsupported maturity {maturity!r}"))
        if validation_scope not in (trust_metadata.get("validation_scope_values") or []):
            issues.append(
                _issue("trust_metadata", rel, f"unsupported validation_scope {validation_scope!r}")
            )
        if not isinstance(physics_validated, bool):
            issues.append(_issue("trust_metadata", rel, "physics_validated must be boolean"))
        if maturity == "experimental" and physics_validated:
            issues.append(_issue("trust_metadata", rel, "experimental case cannot be physics_validated=true"))

    default_variant = dict(pack_spec.get("default_variant") or {})
    configured_variant = config.get("variant")
    if not isinstance(configured_variant, dict):
        issues.append(_issue("variant", rel, "config.variant must be an object"))
        configured_variant = {}
    effective_variant = dict(default_variant)
    effective_variant.update(configured_variant)
    missing_variant = sorted(
        set(contract.get("required_variant_fields") or []) - set(configured_variant)
    )
    if missing_variant:
        issues.append(_issue("variant", rel, f"config.variant is missing {missing_variant}"))
    issues.extend(_validate_variant(configured_variant, registry["variant_dimensions"], rel))
    configured_features = config.get("features")
    if not isinstance(configured_features, dict):
        issues.append(_issue("features", rel, "config.features must be an object"))
        configured_features = {}
    for field in contract.get("required_feature_fields") or []:
        if field not in configured_features:
            issues.append(_issue("feature_field", rel, f"missing feature {field!r}"))

    math_class = configured_features.get("math_class")
    if math_class not in (pack_spec.get("allowed_math_classes") or []):
        issues.append(
            _issue(
                "math_class",
                rel,
                f"features.math_class={math_class!r}; allowed={pack_spec.get('allowed_math_classes')!r}",
            )
        )
    solver_family = configured_features.get("solver_family")
    if solver_family not in (pack_spec.get("allowed_solver_families") or []):
        issues.append(
            _issue(
                "solver_family",
                rel,
                f"features.solver_family={solver_family!r}; allowed={pack_spec.get('allowed_solver_families')!r}",
            )
        )

    computed_features = extract_features(config, network, pack=pack)
    for key, expected in computed_features.items():
        actual = configured_features.get(key)
        if actual != expected:
            issues.append(_issue("feature_mismatch", rel, f"features.{key}={actual!r}; computed={expected!r}"))

    expected_source = source_network(config, network)
    if config.get("source_network") != expected_source:
        issues.append(
            _issue(
                "source_network",
                rel,
                f"config={config.get('source_network')!r}; computed={expected_source!r}",
            )
        )

    case_entry = case_dir / str(contract.get("case_entrypoint") or "solve.py")
    if not case_entry.is_file():
        issues.append(_issue("entrypoint", rel, f"missing {_relative(case_entry, root)}"))
    solver = find_solver(case_dir)
    skip_or_meta = tier == "skip" or _is_meta(config)
    if solver is None and not skip_or_meta:
        issues.append(_issue("entrypoint", rel, "non-skip case has no discoverable solver entrypoint"))

    solver_rel = _relative(solver, root) if solver is not None else None
    expected_record = {
        "id": f"{pack}/{case_dir.name}",
        "path": rel,
        "pack": pack,
        "case": case_dir.name,
        "base_problem": pack_spec["base_problem"],
        "variant": effective_variant,
        "math_class": math_class or pack_spec["default_math_class"],
        "solver_family": solver_family or pack_spec["default_solver_family"],
        "solve_tier": tier or "full",
        "source_network": config.get("source_network") or expected_source,
        "features": computed_features,
        "entrypoint": solver_rel,
        "maturity": config.get("maturity"),
        "validation_scope": config.get("validation_scope"),
        "physics_validated": config.get("physics_validated"),
        "known_limitations": config.get("known_limitations"),
        "classification_note": config.get("classification_note"),
        "_config": config,
    }
    return issues, expected_record


def _validate_catalog(
    root: Path,
    expected_records: dict[str, dict[str, Any]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    catalog_path = root / "CATALOG.json"
    catalog, error = _load_object(catalog_path)
    if catalog is None:
        return [_issue("catalog_json", _relative(catalog_path, root), error or "cannot load")]
    records = catalog.get("cases")
    if not isinstance(records, list):
        return [_issue("catalog_shape", "CATALOG.json", "cases must be a list")]
    if catalog.get("n_cases") != len(records):
        issues.append(
            _issue(
                "catalog_count",
                "CATALOG.json",
                f"n_cases={catalog.get('n_cases')!r}; actual records={len(records)}",
            )
        )

    by_id: dict[str, dict[str, Any]] = {}
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(_issue("catalog_record", "CATALOG.json", f"cases[{i}] is not an object"))
            continue
        case_id = record.get("id")
        if not isinstance(case_id, str):
            issues.append(_issue("catalog_record", "CATALOG.json", f"cases[{i}] has no string id"))
            continue
        if case_id in by_id:
            issues.append(_issue("catalog_duplicate", case_id, "duplicate catalog id"))
        by_id[case_id] = record

    missing = sorted(set(expected_records) - set(by_id))
    stale = sorted(set(by_id) - set(expected_records))
    for case_id in missing:
        issues.append(_issue("catalog_missing", case_id, "case is absent from CATALOG.json"))
    for case_id in stale:
        issues.append(_issue("catalog_stale", case_id, "catalog entry has no case directory"))

    fields = (
        "path",
        "pack",
        "case",
        "base_problem",
        "variant",
        "math_class",
        "solver_family",
        "solve_tier",
        "source_network",
        "features",
        "entrypoint",
        "maturity",
        "validation_scope",
        "physics_validated",
        "known_limitations",
        "classification_note",
    )
    for case_id in sorted(set(expected_records) & set(by_id)):
        expected = expected_records[case_id]
        actual = by_id[case_id]
        for field in fields:
            if actual.get(field) != expected.get(field):
                issues.append(
                    _issue(
                        "catalog_mismatch",
                        case_id,
                        f"{field}: catalog={actual.get(field)!r}; expected={expected.get(field)!r}",
                    )
                )
    return issues


def _validate_manifests(
    root: Path,
    expected_records: dict[str, dict[str, Any]],
) -> list[ValidationIssue]:
    """Keep duplicated manifest classification fields aligned with configs."""
    issues: list[ValidationIssue] = []
    feature_fields = {
        "n_bus",
        "n_branch",
        "n_gen",
        "n_storage",
        "n_candidate_branch",
        "T",
        "n_contingency",
        "n_scenario",
        "n_switchable",
        "max_open",
        "n_bin",
    }
    for manifest_path in sorted(root.glob("*/*/MANIFEST.json")):
        rel = _relative(manifest_path, root)
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(_issue("manifest_json", rel, str(exc)))
            continue
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and isinstance(data.get("cases"), list):
            rows = data["cases"]
            if "n_total" in data and data["n_total"] != len(rows):
                issues.append(
                    _issue("manifest_count", rel, f"n_total={data['n_total']!r}; rows={len(rows)}")
                )
        else:
            issues.append(_issue("manifest_shape", rel, "expected a list or an object with cases[]"))
            continue

        pack = str(manifest_path.parent.relative_to(root)).replace("\\", "/")
        expected_for_pack = {
            record["case"]: record
            for record in expected_records.values()
            if record["pack"] == pack
        }
        by_case: dict[str, dict[str, Any]] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not isinstance(row.get("case"), str):
                issues.append(_issue("manifest_record", rel, f"row {index} has no string case"))
                continue
            case_name = row["case"]
            if case_name in by_case:
                issues.append(_issue("manifest_duplicate", rel, f"duplicate case {case_name!r}"))
            by_case[case_name] = row

        for case_name in sorted(set(expected_for_pack) - set(by_case)):
            issues.append(_issue("manifest_missing", rel, f"missing case {case_name!r}"))
        for case_name in sorted(set(by_case) - set(expected_for_pack)):
            issues.append(_issue("manifest_stale", rel, f"unknown case {case_name!r}"))

        for case_name in sorted(set(expected_for_pack) & set(by_case)):
            expected = expected_for_pack[case_name]
            config = expected["_config"]
            row = by_case[case_name]
            for field in (
                "problem",
                "mode",
                "maturity",
                "validation_scope",
                "physics_validated",
                "base_problem",
                "solve_tier",
            ):
                if field in row and field in config and row[field] != config[field]:
                    issues.append(
                        _issue(
                            "manifest_mismatch",
                            f"{rel}:{case_name}",
                            f"{field}: manifest={row[field]!r}; config={config[field]!r}",
                        )
                    )
            for field in feature_fields:
                if field in row and row[field] != expected["features"].get(field):
                    issues.append(
                        _issue(
                            "manifest_mismatch",
                            f"{rel}:{case_name}",
                            f"{field}: manifest={row[field]!r}; config={expected['features'].get(field)!r}",
                        )
                    )
            if "n_cont" in row and row["n_cont"] != expected["features"].get("n_contingency"):
                issues.append(
                    _issue(
                        "manifest_mismatch",
                        f"{rel}:{case_name}",
                        f"n_cont: manifest={row['n_cont']!r}; config={expected['features'].get('n_contingency')!r}",
                    )
                )
            row_variant = row.get("variant")
            if isinstance(row_variant, dict):
                for field, value in row_variant.items():
                    if field in expected["variant"] and value != expected["variant"][field]:
                        issues.append(
                            _issue(
                                "manifest_mismatch",
                                f"{rel}:{case_name}",
                                f"variant.{field}: manifest={value!r}; config={expected['variant'][field]!r}",
                            )
                        )
    return issues


def validate_repository(
    root: str | Path = ROOT,
    *,
    registry_path: str | Path | None = None,
    check_catalog: bool = True,
) -> list[ValidationIssue]:
    """Return every taxonomy contract violation found under ``root``."""
    root_path = Path(root).resolve()
    resolved_registry = Path(registry_path) if registry_path else root_path / "BASE_PROBLEM_REGISTRY.json"
    try:
        registry = load_registry(resolved_registry)
    except ValueError as exc:
        return [_issue("registry_json", _relative(resolved_registry, root_path), str(exc))]

    issues = validate_registry(registry)
    if issues:
        return issues

    expected_records: dict[str, dict[str, Any]] = {}
    for case_dir in iter_cases(root_path):
        case_issues, expected = _validate_case(case_dir, root_path, registry)
        issues.extend(case_issues)
        if expected is not None:
            expected_records[expected["id"]] = expected

    issues.extend(_validate_manifests(root_path, expected_records))

    if check_catalog:
        issues.extend(_validate_catalog(root_path, expected_records))
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--no-catalog", action="store_true", help="skip CATALOG.json comparison")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)

    issues = validate_repository(
        args.root,
        registry_path=args.registry,
        check_catalog=not args.no_catalog,
    )
    case_count = len(iter_cases(args.root.resolve()))
    if args.json:
        print(
            json.dumps(
                {
                    "passed": not issues,
                    "n_cases": case_count,
                    "n_issues": len(issues),
                    "issues": [asdict(issue) for issue in issues],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for issue in issues:
            print(f"{issue.code}: {issue.path}: {issue.message}")
        state = "PASS" if not issues else "FAIL"
        print(f"{state} cases={case_count} issues={len(issues)}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
