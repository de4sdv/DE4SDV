"""Ontology ↔ method-kernel contract tests.

The contract (``kernel_sync`` in ``approach/framework/ontology/de4sdv-basic-ontology.yaml``)
is complete in both directions:

- every ontology class maps to exactly one kernel target (declaration,
  native construct, or external artifact), and mapped declarations exist;
- every SysML declaration in the governed method-kernel directory is either
  mapped by a class or explicitly excluded with a reason;
- mappings, exclusions, and actual declarations are compared as exact
  ``(file, declaration)`` pairs — no name-only shortcuts;
- feature slices may not re-declare mapped kernel names.

Adversarial probing per the declarative-artifact-testing skill: every failure
mode is induced on a live copy and attributed to a specific ``[ONTOLOGY-KERNEL]``
error. Written as ``unittest.TestCase`` and collected by the repository pytest
suite.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_model_sync  # noqa: E402

ONTOLOGY_YAML = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
CONTRACT_TAG = "[ONTOLOGY-KERNEL]"
GOVERNED_DIR = (
    "textual-notation-of-model/packages/methods/de4sdv"
)


def _load_ontology() -> dict:
    return yaml.safe_load(ONTOLOGY_YAML.read_text(encoding="utf-8"))


def _kernel_path(name: str) -> Path:
    return ROOT / GOVERNED_DIR / name


@contextmanager
def _contract_environment(tampered_yaml: Path, tampered_texts: dict[str, str]):
    """Serve a tampered YAML and tampered kernel/slice texts to the gate."""
    original_yaml = check_model_sync.ONTOLOGY_YAML
    original_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        if str(self) in tampered_texts:
            return tampered_texts[str(self)]
        return original_read(self, *args, **kwargs)

    check_model_sync.ONTOLOGY_YAML = tampered_yaml
    Path.read_text = fake_read
    try:
        yield
    finally:
        Path.read_text = original_read
        check_model_sync.ONTOLOGY_YAML = original_yaml


def _run_contract(doc: dict | None = None, tampered_texts: dict[str, str] | None = None):
    """Run the contract gate with an optional mutated YAML and tampered files."""
    if doc is None:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write(ONTOLOGY_YAML.read_text(encoding="utf-8"))
            tampered_yaml = Path(handle.name)
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            yaml.safe_dump(doc, handle)
            tampered_yaml = Path(handle.name)
    errors: list[str] = []
    try:
        with _contract_environment(tampered_yaml, tampered_texts or {}):
            check_model_sync.check_ontology_kernel_contract(errors)
    finally:
        tampered_yaml.unlink()
    return errors


class ContractCleanRepo(unittest.TestCase):
    """The contract must hold on the real repository state."""

    def test_contract_passes_on_clean_repo(self):
        self.assertEqual(_run_contract(), [])

    def test_contract_is_part_of_the_aggregate_gate(self):
        errors = check_model_sync.run_all_checks()
        self.assertFalse(
            any(e.startswith(CONTRACT_TAG) for e in errors), "\n".join(errors)
        )

    def test_governed_directory_is_declared_in_yaml(self):
        contract = _load_ontology()["kernel_sync"]
        self.assertEqual(contract["governed_directory"], GOVERNED_DIR)

    def test_every_kernel_declaration_is_mapped_or_excluded(self):
        """The bidirectional set equation holds on the live tree."""
        doc = _load_ontology()
        mapped = {
            (spec["kernel"]["file"], spec["kernel"]["declaration"])
            for spec in doc["classes"].values()
            if isinstance(spec.get("kernel"), dict) and "file" in spec["kernel"]
        }
        excluded = {
            (rel_file, declaration)
            for rel_file, declarations in doc["kernel_sync"]["exclusions"].items()
            for declaration in declarations
        }
        actual = set()
        for path in (ROOT / GOVERNED_DIR).rglob("*.sysml"):
            rel = str(path.relative_to(ROOT))
            for declaration in check_model_sync._sysml_definitions(
                path.read_text(encoding="utf-8")
            ):
                actual.add((rel, declaration))
        self.assertEqual(actual - mapped - excluded, set())
        self.assertEqual(excluded - actual, set())
        self.assertEqual(mapped & excluded, set())

    def test_exclusions_carry_reasons(self):
        for rel_file, declarations in _load_ontology()["kernel_sync"][
            "exclusions"
        ].items():
            self.assertTrue(declarations, f"{rel_file}: empty exclusion block")
            for declaration, reason in declarations.items():
                self.assertIsInstance(reason, str)
                self.assertTrue(
                    reason.strip(),
                    f"{rel_file}: '{declaration}' has no reason",
                )

    def test_scan_breadth_covers_two_word_kinds(self):
        """The scanner must inventory forms like 'variation part def'."""
        found = check_model_sync._sysml_definitions(
            _kernel_path("de4sdv_product_line.sysml").read_text(encoding="utf-8")
        )
        self.assertTrue(
            any(declaration.startswith("variation part def ") for declaration in found)
        )


class ContractMappingDirection(unittest.TestCase):
    """Ontology → kernel direction: mappings must resolve, exactly."""

    def test_every_class_has_exactly_one_mapping_style(self):
        for name, spec in _load_ontology()["classes"].items():
            kernel = spec.get("kernel")
            self.assertIsInstance(kernel, dict, f"{name}: no kernel mapping")
            styles = sum(
                (
                    "file" in kernel and "declaration" in kernel,
                    "native" in kernel,
                    "external" in kernel,
                )
            )
            self.assertEqual(
                styles, 1, f"{name}: {styles} mapping styles in one kernel block"
            )

    def test_catches_renamed_kernel_declaration(self):
        def mutate(doc):
            doc["classes"]["EngineeringIncrement"]["kernel"]["declaration"] = (
                "part def NoLongerExists"
            )

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any("part def NoLongerExists" in e for e in errors), errors
        )

    def test_catches_mapping_to_same_name_in_wrong_file(self):
        """Name-only matching is banned: the pair must be file-scoped."""
        doc = _load_ontology()
        doc["classes"]["ProductLine"]["kernel"]["file"] = (
            GOVERNED_DIR + "/de4sdv_method_context.sysml"
        )
        errors = _run_contract(doc)
        self.assertTrue(
            any(
                "'part def ProductLine'" in e and "not" in e for e in errors
            ),
            errors,
        )

    def test_catches_missing_kernel_file(self):
        def mutate(doc):
            doc["classes"]["EngineeringIncrement"]["kernel"]["file"] = (
                "no/such/file.sysml"
            )

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(any("kernel file not found" in e for e in errors), errors)

    def test_catches_half_specified_kernel_mapping(self):
        def mutate(doc):
            del doc["classes"]["EngineeringIncrement"]["kernel"]["declaration"]

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any("file: and declaration:" in e for e in errors), errors
        )

    def test_catches_ambiguous_kernel_mapping(self):
        def mutate(doc):
            doc["classes"]["EngineeringIncrement"]["kernel"]["native"] = (
                "SysML v2 part"
            )

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any("exactly one of file+declaration" in e for e in errors), errors
        )

    def test_catches_invalid_yaml(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("classes: [unclosed\n  broken")
            bad = Path(handle.name)
        errors: list[str] = []
        try:
            with mock.patch.object(check_model_sync, "ONTOLOGY_YAML", bad):
                check_model_sync.check_ontology_kernel_contract(errors)
        finally:
            bad.unlink()
        self.assertTrue(any("invalid YAML" in e for e in errors), errors)

    def test_catches_missing_yaml_file(self):
        errors: list[str] = []
        with mock.patch.object(
            check_model_sync,
            "ONTOLOGY_YAML",
            Path(tempfile.gettempdir()) / "absent-ontology.yaml",
        ):
            check_model_sync.check_ontology_kernel_contract(errors)
        self.assertTrue(any("ontology YAML not found" in e for e in errors), errors)


class ContractInventoryDirection(unittest.TestCase):
    """Kernel → ontology direction: every declaration needs a decision."""

    def test_catches_unclassified_new_kernel_declaration(self):
        process = _kernel_path("de4sdv_method_process.sysml")
        original = process.read_text(encoding="utf-8")
        tampered = original.replace(
            "enum def IncrementSize {",
            "part def BrandNewConcept {\n  }\n\n  enum def IncrementSize {",
        )
        errors = _run_contract(tampered_texts={str(process): tampered})
        self.assertTrue(
            any("BrandNewConcept" in e and "unclassified" in e for e in errors),
            errors,
        )

    def test_catches_stale_exclusion_after_rename(self):
        doc = _load_ontology()
        exclusions = doc["kernel_sync"]["exclusions"]
        rel_file = next(iter(exclusions))
        first = next(iter(exclusions[rel_file]))
        del exclusions[rel_file][first]
        exclusions[rel_file]["part def Ghost"] = "stale"
        errors = _run_contract(doc)
        self.assertTrue(
            any("Ghost" in e and "stale exclusion" in e for e in errors), errors
        )

    def test_catches_exclusion_with_empty_reason(self):
        def mutate(doc):
            exclusions = doc["kernel_sync"]["exclusions"]
            rel_file = next(iter(exclusions))
            first = next(iter(exclusions[rel_file]))
            exclusions[rel_file][first] = ""

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any("non-empty reason" in e for e in errors), errors
        )

    def test_catches_mapping_and_exclusion_overlap(self):
        def mutate(doc):
            doc["kernel_sync"]["exclusions"][
                GOVERNED_DIR + "/de4sdv_method_context.sysml"
            ]["part def EngineeringIncrement"] = "double bookkeeping"

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any(
                "both ontology-mapped and excluded" in e for e in errors
            ),
            errors,
        )

    def test_catches_exclusion_outside_governed_directory(self):
        def mutate(doc):
            doc["kernel_sync"]["exclusions"]["somewhere/else.sysml"] = {
                "part def Thing": "not governed"
            }

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(
            any("outside the governed directory" in e for e in errors), errors
        )

    def test_catches_missing_kernel_sync_block(self):
        def mutate(doc):
            del doc["kernel_sync"]

        doc = _load_ontology()
        mutate(doc)
        errors = _run_contract(doc)
        self.assertTrue(any("no kernel_sync contract" in e for e in errors), errors)


class ContractSliceGuard(unittest.TestCase):
    """Feature slices must not re-declare mapped kernel names."""

    def test_catches_slice_redeclaration_of_mapped_kernel_name(self):
        slice_path = ROOT / (
            "textual-notation-of-model/packages/features/aebs/"
            "aebs_needs_requirements.sysml"
        )
        original = slice_path.read_text(encoding="utf-8")
        tampered = original + "\npart def RequirementCandidate {}\n"
        errors = _run_contract(tampered_texts={str(slice_path): tampered})
        self.assertTrue(
            any(
                "re-declares mapped kernel name 'RequirementCandidate'" in e
                for e in errors
            ),
            errors,
        )

    def test_slice_guard_derives_names_from_mappings_not_a_list(self):
        """The guard must derive from the YAML, not a hand-kept name list."""
        import inspect

        source = inspect.getsource(check_model_sync.check_ontology_kernel_contract)
        self.assertNotIn("_PROTECTED_CONCEPTS", source)


class ContractSemanticsPins(unittest.TestCase):
    """Content pins tying the YAML to semantics the gate alone cannot see."""

    def test_feature_common_capability_disjointness_is_symmetric(self):
        doc = _load_ontology()
        feature = doc["classes"]["Feature"]
        common = doc["classes"]["CommonCapability"]
        self.assertEqual(feature["disjointWith"], ["CommonCapability"])
        self.assertEqual(common["disjointWith"], ["Feature"])
        kernel_text = check_model_sync._read(ROOT / feature["kernel"]["file"])
        self.assertIn(
            "ProductLineFeatureCandidate", feature["kernel"]["declaration"]
        )
        self.assertIn(
            "CommonProductLineCapability", common["kernel"]["declaration"]
        )
        self.assertEqual(feature["kernel"]["file"], common["kernel"]["file"])
        for declaration in (
            feature["kernel"]["declaration"],
            common["kernel"]["declaration"],
        ):
            self.assertTrue(
                check_model_sync._declaration_exists(kernel_text, declaration),
                declaration,
            )

    def test_status_vocabulary_comes_from_upstream_not_local(self):
        """ADR 0009: no parallel local status enums in the ontology."""
        evidence_status = _load_ontology()["classes"]["EvidenceStatus"]
        self.assertIn("external", evidence_status["kernel"])
        self.assertIn("VVStatus", evidence_status["kernel"]["external"])

    def test_schema_bumped_past_v0(self):
        self.assertEqual(
            _load_ontology()["schema"], "de4sdv.basic-ontology.v0.1"
        )

    def test_method_context_kernel_declares_pinned_declarations(self):
        doc = _load_ontology()
        context_file = GOVERNED_DIR + "/de4sdv_method_context.sysml"
        kernel_text = check_model_sync._read(ROOT / context_file)
        mapped = [
            spec["kernel"]["declaration"]
            for spec in doc["classes"].values()
            if spec.get("kernel", {}).get("file") == context_file
        ]
        self.assertGreaterEqual(len(mapped), 5)
        for declaration in mapped:
            self.assertTrue(
                check_model_sync._declaration_exists(kernel_text, declaration),
                declaration,
            )

    def test_governed_inventory_is_not_empty(self):
        """Meta-check: the scanner must actually find kernel declarations."""
        doc = _load_ontology()
        mapped = sum(
            1
            for spec in doc["classes"].values()
            if isinstance(spec.get("kernel"), dict)
            and "file" in spec["kernel"]
        )
        excluded = sum(
            len(declarations)
            for declarations in doc["kernel_sync"]["exclusions"].values()
        )
        self.assertGreaterEqual(mapped, 20)
        self.assertGreaterEqual(excluded, 50)


if __name__ == "__main__":
    unittest.main()
