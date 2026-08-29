"""Sync point 6 tests: kernel-vocabulary registry coverage gate.

Reverse-direction counterpart of the SP5 suite: while SP5 verifies the
ontology points at existing kernel declarations, SP6 verifies every kernel
declaration carries an explicit classification (``ontology`` or
``kernel-internal``) in its file's ``kernel-vocabulary`` registry, and that
``ontology`` classifications are actually backed by the ontology YAML.

Written as unittest.TestCase because CI runs
``python -m unittest discover -s tests``.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_model_sync  # noqa: E402

KERNEL_DIR = check_model_sync.KERNEL_DIR
ONTOLOGY_YAML = check_model_sync.ONTOLOGY_YAML


def _load_ontology() -> dict:
    return yaml.safe_load(ONTOLOGY_YAML.read_text(encoding="utf-8"))


def _ontology_covered_names() -> set[str]:
    doc = _load_ontology()
    return {
        spec["kernel"]["declaration"].split()[-1]
        for spec in doc["classes"].values()
        if isinstance(spec, dict) and "declaration" in spec.get("kernel", {})
    }


class KernelRegistryCleanRepo(unittest.TestCase):
    """The registry gate and the kernel files must be consistent."""

    def test_registry_gate_passes_on_clean_repo(self):
        errors: list[str] = []
        check_model_sync.check_kernel_vocabulary_registry(errors)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_every_kernel_file_has_a_registry(self):
        for path in KERNEL_DIR.glob("*.sysml"):
            registry = check_model_sync._extract_kernel_registry(
                path.read_text(encoding="utf-8")
            )
            self.assertIsNotNone(
                registry, f"{path.name}: no kernel-vocabulary registry block"
            )

    def test_every_kernel_declaration_is_classified(self):
        for path in KERNEL_DIR.glob("*.sysml"):
            text = path.read_text(encoding="utf-8")
            registry = check_model_sync._extract_kernel_registry(text)
            self.assertIsNotNone(registry, path.name)
            code = check_model_sync._strip_comments(text)
            for _, name in check_model_sync._DECLARATION_RE.findall(code):
                self.assertIsNotNone(registry, path.name)
                self.assertIn(
                    name, registry or {}, f"{path.name}: '{name}' not classified"
                )

    def test_run_all_checks_includes_sync_point_six(self):
        errors = check_model_sync.run_all_checks()
        self.assertFalse(
            any(e.startswith("[SP6]") for e in errors), "\n".join(errors)
        )


class RegistryExtractionProbing(unittest.TestCase):
    """Function-level probing of the registry parser."""

    def test_parses_registry_with_comment_leaders(self):
        text = (
            "/*\n"
            " * kernel-vocabulary:\n"
            " * - Widget: ontology\n"
            " * - Gadget: kernel-internal (framing helper)\n"
            " */\n"
            "package P { part def Widget {} part def Gadget {} }"
        )
        registry = check_model_sync._extract_kernel_registry(text)
        self.assertEqual(
            registry, {"Widget": "ontology", "Gadget": "kernel-internal"}
        )

    def test_returns_none_without_registry(self):
        self.assertIsNone(
            check_model_sync._extract_kernel_registry("/* plain header */")
        )

    def test_reason_text_after_status_is_tolerated(self):
        text = "/* kernel-vocabulary:\n * - Gadget: kernel-internal (because it is a framing helper)\n */"
        registry = check_model_sync._extract_kernel_registry(text)
        self.assertEqual(registry, {"Gadget": "kernel-internal"})

    def test_unknown_status_is_not_silently_accepted(self):
        text = "/* kernel-vocabulary:\n * - Gadget: sometimes\n */"
        registry = check_model_sync._extract_kernel_registry(text)
        self.assertEqual(registry, {})  # entry does not parse as a valid status

    def test_declaration_scan_covers_multiple_kinds(self):
        code = (
            "part def A {} requirement def B {} enum def C {} "
            "item def D {} concern def E {} viewpoint def F {} "
            "allocation def G {}"
        )
        names = [n for _, n in check_model_sync._DECLARATION_RE.findall(code)]
        self.assertEqual(names, ["A", "B", "C", "D", "E", "F", "G"])

    def test_declaration_scan_ignores_comments(self):
        code = "/* part def FakeInComment {} */ part def Real {}"
        names = [
            n
            for _, n in check_model_sync._DECLARATION_RE.findall(
                check_model_sync._strip_comments(code)
            )
        ]
        self.assertEqual(names, ["Real"])


def _run_gate_with_tampered_file(mutate) -> list[str]:
    """Run the SP6 gate with one kernel file's text replaced."""
    texts = {
        p: mutate(p.name, p.read_text(encoding="utf-8"))
        for p in KERNEL_DIR.glob("*.sysml")
    }

    def fake_read(path):
        key = Path(path)
        if key in texts:
            return texts[key]
        # Fall through to the real reader for any other path (e.g. the
        # ontology YAML), so cross-file checks stay intact.
        return Path(path).read_text(encoding="utf-8")

    errors: list[str] = []
    with mock.patch.object(check_model_sync, "_read", fake_read):
        check_model_sync.check_kernel_vocabulary_registry(errors)
    return errors


class KernelRegistryFailureAttribution(unittest.TestCase):
    """Each failure mode must surface as an [SP6] error, not a silent pass."""

    def test_catches_unclassified_new_declaration(self):
        def mutate(name, text):
            if name == "de4sdv_method_context.sysml":
                return text.replace(
                    "package DE4SDV_MethodContext {",
                    "package DE4SDV_MethodContext {\n"
                    "  part def BrandNewConcept {\n"
                    "  }\n",
                )
            return text

        errors = _run_gate_with_tampered_file(mutate)
        self.assertTrue(
            any("BrandNewConcept" in e and "not classified" in e for e in errors),
            errors,
        )

    def test_catches_missing_registry_block(self):
        def mutate(name, text):
            if name == "de4sdv_stakeholders.sysml":
                return text.replace("kernel-vocabulary:", "vocabulary-removed:")
            return text

        errors = _run_gate_with_tampered_file(mutate)
        self.assertTrue(
            any("no kernel-vocabulary registry" in e for e in errors), errors
        )

    def test_catches_stale_registry_entry(self):
        def mutate(name, text):
            if name == "de4sdv_stakeholders.sysml":
                return text.replace(
                    " * - Supplier: kernel-internal (concrete stakeholder role)",
                    " * - RenamedAway: kernel-internal (stale entry)",
                )
            return text

        errors = _run_gate_with_tampered_file(mutate)
        self.assertTrue(any("RenamedAway" in e and "stale" in e for e in errors), errors)

    def test_unknown_registry_status_is_rejected(self):
        """An invalid status does not parse as a registry entry, so the
        declaration surfaces as unclassified — conservative by design."""
        def mutate(name, text):
            if name == "de4sdv_stakeholders.sysml":
                return text.replace(
                    " * - Supplier: kernel-internal (concrete stakeholder role)",
                    " * - Supplier: maybe",
                )
            return text

        errors = _run_gate_with_tampered_file(mutate)
        self.assertTrue(
            any("Supplier" in e and "not classified" in e for e in errors), errors
        )

    def test_catches_ontology_status_without_yaml_mapping(self):
        def mutate(name, text):
            if name == "de4sdv_stakeholders.sysml":
                return text.replace(
                    " * - Supplier: kernel-internal (concrete stakeholder role)",
                    " * - Supplier: ontology",
                )
            return text

        errors = _run_gate_with_tampered_file(mutate)
        self.assertTrue(
            any(
                "Supplier" in e and "registered as 'ontology' but not mapped" in e
                for e in errors
            ),
            errors,
        )


class KernelRegistrySemanticsPins(unittest.TestCase):
    """Content pins tying the registries to the ontology contract."""

    def test_ontology_status_entries_all_mapped_in_yaml(self):
        """The cross-direction consistency the gate enforces, asserted directly."""
        covered = _ontology_covered_names()
        for path in KERNEL_DIR.glob("*.sysml"):
            registry = check_model_sync._extract_kernel_registry(
                path.read_text(encoding="utf-8")
            ) or {}
            for name, status in registry.items():
                if status == "ontology":
                    self.assertIn(
                        name, covered, f"{path.name}: '{name}' marked ontology "
                        f"but absent from the ontology YAML"
                    )

    def test_stakeholder_roles_are_kernel_internal(self):
        """Concrete roles must never be promoted to ontology vocabulary."""
        registry = check_model_sync._extract_kernel_registry(
            (KERNEL_DIR / "de4sdv_stakeholders.sysml").read_text(encoding="utf-8")
        ) or {}
        for role in ("RoadUser", "SystemsEngineer", "OpenSourceReviewer"):
            self.assertEqual(
                registry.get(role), "kernel-internal",
                f"{role}: concrete roles are kernel-internal, not ontology",
            )

    def test_core_vocabulary_is_registered_as_ontology(self):
        """The kernel's core semantic vocabulary must be ontology-classified."""
        registry = check_model_sync._extract_kernel_registry(
            (KERNEL_DIR / "de4sdv_method_context.sysml").read_text(encoding="utf-8")
        ) or {}
        for name in (
            "EngineeringIncrement",
            "StakeholderNeedCandidate",
            "RequirementCandidate",
            "IncrementGap",
            "IncrementAssumption",
        ):
            self.assertEqual(registry.get(name), "ontology", name)

    def test_ontology_yaml_covers_at_least_thirty_kernel_declarations(self):
        """Coverage floor: the ontology must keep mapping real kernel content."""
        self.assertGreaterEqual(len(_ontology_covered_names()), 30)


if __name__ == "__main__":
    unittest.main()
