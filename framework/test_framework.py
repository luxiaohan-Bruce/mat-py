"""Lightweight regression tests for shared framework governance."""

from __future__ import annotations

import json
import io
import importlib.util
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from . import catalog
from .catalog import case_record
from .evaluate import evaluate
from .features import extract_features
from .runner import find_solver
from .taxonomy import load_registry
from .validate_taxonomy import _validate_manifests, validate_registry


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class CatalogTests(unittest.TestCase):
    def test_case_record_merges_variant_and_trusts_feature_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "OTS" / "DC-OTS" / "case01_demo"
            _write_json(
                case / "data" / "config.json",
                {
                    "case": case.name,
                    "variant": {"security": "custom", "case_axis": "kept"},
                    "maturity": "experimental",
                    "validation_scope": "structural_only",
                    "physics_validated": False,
                    "features": {
                        "math_class": "trusted_math",
                        "solver_family": "trusted_solver",
                    },
                },
            )
            _write_json(case / "data" / "network.json", {})
            solver = case / "python" / "solve_demo.py"
            solver.parent.mkdir(parents=True)
            solver.write_text("pass\n", encoding="utf-8")

            record = case_record(case, root)

            self.assertEqual(record["variant"]["power_flow"], "dc")
            self.assertEqual(record["variant"]["security"], "custom")
            self.assertEqual(record["variant"]["case_axis"], "kept")
            self.assertEqual(record["math_class"], "trusted_math")
            self.assertEqual(record["solver_family"], "trusted_solver")
            self.assertEqual(record["maturity"], "experimental")
            self.assertEqual(record["validation_scope"], "structural_only")
            self.assertFalse(record["physics_validated"])

    def test_evaluate_all_fails_for_missing_non_skip_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_missing"
            _write_json(case / "data" / "config.json", {"solve_tier": "full"})
            with patch.object(catalog, "iter_cases", return_value=[case]):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(catalog.main(["--evaluate-all"]), 1)


class EvaluationTests(unittest.TestCase):
    def _write_linearized_sc_case(
        self,
        root: Path,
        *,
        problem: str = "linearized_scacopf",
        n_cont: object = 5,
        load_shed_MW: object = 0.0,
        flow_slack_pu: object = 0.0,
        variant: dict | None = None,
    ) -> Path:
        case = root / "case01_linearized_sc"
        config: dict = {
            "solve_tier": "relaxed",
            "problem": problem,
            "features": {"n_contingency": 5},
        }
        if variant is not None:
            config["variant"] = variant
        _write_json(case / "data" / "config.json", config)
        _write_json(
            case / "results" / "python_result.json",
            {
                "scacopf": {
                    "status": "OPTIMAL",
                    "obj": 12.5,
                    "n_cont": n_cont,
                    "load_shed_MW": load_shed_MW,
                    "flow_slack_pu": flow_slack_pu,
                }
            },
        )
        return case

    def test_linearized_sc_truth_gate_accepts_complete_unrelaxed_result(self) -> None:
        for problem in ("linearized_scacopf", "linearized_scacots"):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as tmp:
                result = evaluate(
                    self._write_linearized_sc_case(Path(tmp), problem=problem)
                )
                self.assertTrue(result["passed"])
                self.assertEqual(result["reason"], "ok")

    def test_linearized_sc_truth_gate_rejects_relaxed_or_incomplete_result(self) -> None:
        cases = (
            ({"n_cont": 0}, "n_cont=0 expected_n_contingency=5"),
            ({"n_cont": None}, "n_cont=None expected_n_contingency=5"),
            ({"load_shed_MW": 1.1e-4}, "load_shed_MW=0.00011"),
            ({"load_shed_MW": None}, "load_shed_MW=None"),
            ({"flow_slack_pu": 1.1e-6}, "flow_slack_pu=1.1e-06"),
            ({"flow_slack_pu": None}, "flow_slack_pu=None"),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as tmp:
                result = evaluate(
                    self._write_linearized_sc_case(Path(tmp), **overrides)
                )
                self.assertFalse(result["passed"])
                self.assertIn(expected, result["violations"])

    def test_linearized_sc_allows_load_shed_when_recourse_is_nse(self) -> None:
        variant = {"recourse": "corrective_limited_with_nse"}
        for problem in ("linearized_scacopf", "linearized_scacots"):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as tmp:
                result = evaluate(
                    self._write_linearized_sc_case(
                        Path(tmp),
                        problem=problem,
                        load_shed_MW=80.63,
                        variant=variant,
                    )
                )
                self.assertTrue(result["passed"])
                self.assertEqual(result["reason"], "ok")
                self.assertEqual(result["residuals"].get("load_shed_MW"), 80.63)

    def test_linearized_sc_nse_variant_still_rejects_flow_slack_and_missing_shed(self) -> None:
        variant = {"recourse": "corrective_limited_with_nse"}
        cases = (
            ({"load_shed_MW": None, "variant": variant}, "load_shed_MW=None"),
            ({"flow_slack_pu": 1.1e-6, "variant": variant}, "flow_slack_pu=1.1e-06"),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as tmp:
                result = evaluate(
                    self._write_linearized_sc_case(Path(tmp), **overrides)
                )
                self.assertFalse(result["passed"])
                self.assertIn(expected, result["violations"])

    def test_missing_non_skip_result_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_missing"
            _write_json(case / "data" / "config.json", {"solve_tier": "full"})
            result = evaluate(case)
            self.assertFalse(result["passed"])
            self.assertEqual(result["reason"], "missing_result")

    def test_skip_ignores_stale_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_skip"
            _write_json(case / "data" / "config.json", {"solve_tier": "skip"})
            _write_json(
                case / "results" / "python_result.json",
                {"ots": {"status": "INFEASIBLE", "obj": None}},
            )
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["status"], "SKIP")
            self.assertEqual(result["reason"], "configured_skip_or_meta")

    def test_meta_suffix_ignores_stale_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_meta"
            _write_json(
                case / "data" / "config.json",
                {"solve_tier": "full", "problem": "profile_meta"},
            )
            _write_json(case / "results" / "python_result.json", {"status": "ERROR"})
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["status"], "SKIP")

    def test_objective_alias_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_acopf"
            _write_json(case / "data" / "config.json", {"solve_tier": "full"})
            _write_json(
                case / "results" / "python_result.json",
                {
                    "acopf": {
                        "status": "OPTIMAL",
                        "objective": 12.5,
                        "validation_passed": True,
                    }
                },
            )
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["obj"], 12.5)

    def test_interrupted_valid_incumbent_is_accepted_without_claiming_optimality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_interrupted"
            _write_json(case / "data" / "config.json", {"solve_tier": "relaxed"})
            _write_json(
                case / "results" / "python_result.json",
                {
                    "ht": {
                        "status": "INTERRUPTED",
                        "obj": 12.5,
                        "mip_gap": 0.1,
                        "validation_passed": True,
                    }
                },
            )
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["status"], "INTERRUPTED")
            self.assertEqual(result["claim"], "validated_feasible_incumbent")

    def test_time_limit_without_residual_validation_is_solver_claim_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_time_limit"
            _write_json(case / "data" / "config.json", {"solve_tier": "full"})
            _write_json(
                case / "results" / "python_result.json",
                {"scuc": {"status": "TIME_LIMIT", "obj": 12.5}},
            )
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["claim"], "solver_feasible_incumbent")
            self.assertEqual(
                result["reason"],
                "solver_feasible_incumbent_not_independently_validated",
            )

    def test_experimental_result_is_only_a_structural_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "case01_experimental"
            _write_json(
                case / "data" / "config.json",
                {
                    "solve_tier": "full",
                    "maturity": "experimental",
                    "validation_scope": "structural_only",
                    "physics_validated": False,
                },
            )
            _write_json(
                case / "results" / "python_result.json",
                {"dnr": {"status": "OPTIMAL", "obj": 1.0, "validation_passed": True}},
            )
            result = evaluate(case)
            self.assertTrue(result["passed"])
            self.assertEqual(result["claim"], "structural_only")
            self.assertEqual(result["reason"], "structural_only_not_physics_validated")


class FeatureAndRegistryTests(unittest.TestCase):
    def test_linearized_sc_solver_never_drops_contingencies(self) -> None:
        root = Path(__file__).resolve().parents[1]
        model_paths = (
            root / "OPF" / "LINEARIZED-SC-OPF" / "common" / "scacopf_model_py.py",
            root / "OTS" / "LINEARIZED-SC-OTS" / "common" / "scacopf_model_py.py",
        )
        for index, model_path in enumerate(model_paths):
            with self.subTest(model_path=model_path):
                spec = importlib.util.spec_from_file_location(
                    f"linearized_sc_model_{index}", model_path
                )
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                network = {"contingencies": [{"branch": {"id": 1}}]}
                failure = {"status": "INFEASIBLE", "obj": None, "n_cont": 1}
                with patch.object(
                    module, "_solve_scacopf_core", return_value=failure
                ) as solve_core:
                    result = module.solve_scacopf(network, {}, quiet=True)
                self.assertIs(result, failure)
                solve_core.assert_called_once_with(network, {}, quiet=True)

    def test_manifest_repeated_config_fields_must_match(self) -> None:
        config = {
            "problem": "demo_problem",
            "mode": "demo_mode",
            "maturity": "experimental",
            "validation_scope": "structural_only",
            "physics_validated": False,
            "base_problem": "opf",
            "solve_tier": "full",
        }
        expected = {
            "pack": "TEST/PACK",
            "case": "case01_demo",
            "features": {},
            "variant": {},
            "_config": config,
        }
        repeated_fields = (
            "problem",
            "mode",
            "maturity",
            "validation_scope",
            "physics_validated",
            "base_problem",
            "solve_tier",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "TEST" / "PACK" / "MANIFEST.json"
            matching = {"case": expected["case"]}
            matching.update({field: config[field] for field in repeated_fields})
            _write_json(manifest, [matching])
            records = {"TEST/PACK/case01_demo": expected}

            self.assertEqual(_validate_manifests(root, records), [])
            for field in repeated_fields:
                with self.subTest(field=field):
                    mismatched = dict(matching)
                    mismatched[field] = True if field == "physics_validated" else "different"
                    _write_json(manifest, [mismatched])
                    issues = _validate_manifests(root, records)
                    self.assertEqual(len(issues), 1)
                    self.assertEqual(issues[0].code, "manifest_mismatch")
                    self.assertTrue(issues[0].message.startswith(f"{field}:"))

            manifest_only_mode = dict(matching)
            config_without_mode = dict(config)
            del config_without_mode["mode"]
            expected_without_mode = dict(expected)
            expected_without_mode["_config"] = config_without_mode
            _write_json(manifest, [manifest_only_mode])
            self.assertEqual(
                _validate_manifests(root, {"TEST/PACK/case01_demo": expected_without_mode}),
                [],
            )

    def test_switchable_count_falls_back_to_network(self) -> None:
        network = {
            "branches": [
                {"switchable": True},
                {"switchable": False},
                {"switchable": 1},
            ]
        }
        features = extract_features({}, network, pack="DISTRIBUTION/DNR")
        self.assertEqual(features["n_switchable"], 2)

    def test_distribution_binary_counts_match_implemented_models(self) -> None:
        network = {"branches": [{"switchable": True}, {"switchable": False}]}
        hosting = extract_features({}, network, pack="DISTRIBUTION/DER-HOSTING")
        dopf = extract_features({}, network, pack="DISTRIBUTION/DISTRIBUTION-OPF")
        volt_var = extract_features({}, network, pack="DISTRIBUTION/VOLT-VAR")
        self.assertEqual(hosting["n_bin"], 2)
        self.assertEqual(dopf["n_bin"], 2)
        self.assertEqual(volt_var["n_bin"], 2)

    def test_registry_is_self_consistent(self) -> None:
        self.assertEqual(validate_registry(load_registry()), [])

    def test_direct_root_solver_is_discoverable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            solver = case / "solve.py"
            solver.write_text("pass\n", encoding="utf-8")
            self.assertEqual(find_solver(case), solver.resolve())

    def test_empty_delegating_shim_is_not_a_solver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp)
            (case / "solve.py").write_text(
                'cands = sorted(p for p in PY.glob("solve_*.py") if p.name != "solve.py")\n',
                encoding="utf-8",
            )
            self.assertIsNone(find_solver(case))


if __name__ == "__main__":
    unittest.main()
