"""Model-built kernel contract <-> method-kernel contract tests.

O4 Wave C2 deleted the authored ontology (and its ``kernel_sync`` block). The
contract is complete in both directions:

- every class of the model-built kernel contract
  (``KernelContract.from_layers``) maps to exactly one kernel target (file
  declaration, native construct, or external artifact), and mapped
  declarations exist in the named file (``scripts/check_model_sync.py`` sync
  point 5);
- every SysML declaration in the governed method-kernel directory is either
  projected by a model-generated layer or listed in
  ``docs/method-conformance/o4/kernel-internal-declarations.yaml`` with a
  reason, as a disjoint union (the model-projection coverage gate, owner
  decision D3);
- mappings, listed declarations and actual declarations are compared as exact
  ``(file, declaration)`` pairs — no name-only shortcuts;
- feature slices may not re-declare mapped kernel names.

Replaced in Wave C2 (YAML-mutation tests -> model-contract / D3-manifest
mutations): ``test_governed_directory_is_declared_in_yaml``,
``test_every_kernel_declaration_is_mapped_or_excluded``,
``test_exclusions_carry_reasons``, ``test_every_class_has_exactly_one_mapping_style``,
``test_catches_ambiguous_kernel_mapping`` (a typed model mapping cannot carry
two styles; replaced by ``test_catches_unrecognized_kernel_mapping``),
``test_catches_invalid_yaml`` / ``test_catches_missing_yaml_file`` (replaced
by ``test_catches_unbuildable_model_contract`` /
``test_catches_corrupt_model_layer``), the inventory-direction tests (now
mutate the D3 manifest instead of breaking the retired C1 transition lock),
``test_catches_missing_kernel_sync_block`` (-> ``test_catches_missing_manifest_declarations``),
``test_schema_bumped_past_v0`` (-> ``test_semantic_authority_identity_is_model_built``)
and the content pins (now read the model contract and the batch-2 projection).

Adversarial probing per the declarative-artifact-testing skill: every failure
mode is induced and attributed to a specific error.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from scripts import check_model_sync  # noqa: E402
from model_contract_fixtures import model_contract  # noqa: E402

CONTRACT_TAG = "[ONTOLOGY-KERNEL]"
GOVERNED_DIR = "textual-notation-of-model/packages/methods/de4sdv"
MANIFEST = "docs/method-conformance/o4/kernel-internal-declarations.yaml"
BATCH2 = "docs/method-conformance/o4/definition-batch2-projection.json"


def _kernel_path(name: str) -> Path:
    return ROOT / GOVERNED_DIR / name


def _manifest() -> dict:
    return yaml.safe_load((ROOT / MANIFEST).read_text(encoding="utf-8"))


class _MappingContract:
    """A contract view whose class mappings can be replaced per test."""

    def __init__(self, overrides: dict) -> None:
        real = model_contract()
        self.classes = dict(real.classes)
        self._real = real
        self._overrides = overrides

    def mapping(self, name):
        if name in self._overrides:
            value = self._overrides[name]
            if isinstance(value, Exception):
                raise value
            return value
        return self._real.mapping(name)


def _run_contract(overrides: dict | None = None):
    """Run sync point 5 over the real contract with replaced class mappings."""
    errors: list[str] = []
    if overrides is None:
        check_model_sync.check_ontology_kernel_contract(errors)
        return errors
    with mock.patch.object(check_model_sync, "_load_model_contract",
                           return_value=_MappingContract(overrides)):
        check_model_sync.check_ontology_kernel_contract(errors)
    return errors


def _run_coverage(manifest: dict | None = None, tampered_texts: dict[str, str] | None = None):
    """Kernel-accounting errors of the model-projection coverage gate, with an
    optionally mutated D3 manifest and tampered kernel/slice texts."""
    from de4sdv.semantic import model_projection_coverage as coverage

    texts = {Path(path): text for path, text in (tampered_texts or {}).items()}
    if manifest is not None:
        texts[ROOT / MANIFEST] = yaml.safe_dump(manifest)
    original_read = Path.read_text

    def fake_read(self, *args, **kwargs):
        if self in texts:
            return texts[self]
        return original_read(self, *args, **kwargs)

    with mock.patch.object(Path, "read_text", fake_read):
        return list(coverage.build_report(ROOT)["kernel_accounting_errors"])


class ContractCleanRepo(unittest.TestCase):
    """The contract must hold on the real repository state."""

    def test_contract_passes_on_clean_repo(self):
        self.assertEqual(_run_contract(), [])

    def test_contract_is_part_of_the_aggregate_gate(self):
        errors = check_model_sync.run_all_checks()
        self.assertFalse(
            any(e.startswith(CONTRACT_TAG) for e in errors), "\n".join(errors)
        )

    def test_governed_directory_is_declared_in_the_manifest(self):
        self.assertEqual(_manifest()["governed_directory"], GOVERNED_DIR)

    def test_every_kernel_declaration_is_projected_or_listed(self):
        """The bidirectional set equation holds on the live tree."""
        from de4sdv.semantic import model_projection_coverage as coverage

        report = coverage.build_report(ROOT)
        self.assertEqual(report["kernel_accounting_errors"], [])
        listed = {(rel_file, declaration)
                  for rel_file, declarations in _manifest()["declarations"].items()
                  for declaration in declarations}
        mapped = {(m.file, m.declaration) for m in
                  (model_contract().mapping(n) for n in model_contract().classes)
                  if hasattr(m, "declaration")}
        actual = set()
        for path in (ROOT / GOVERNED_DIR).rglob("*.sysml"):
            rel = str(path.relative_to(ROOT))
            for declaration in check_model_sync._sysml_definitions(
                path.read_text(encoding="utf-8")
            ):
                actual.add((rel, declaration))
        self.assertEqual(listed - actual, set())
        self.assertEqual(mapped & listed, set())
        statuses = {entry["status"] for entry in report["kernel_declarations"].values()}
        self.assertEqual(statuses, {"projected", "excluded"})

    def test_listed_declarations_carry_reasons(self):
        for rel_file, declarations in _manifest()["declarations"].items():
            self.assertTrue(declarations, f"{rel_file}: empty block")
            for declaration, reason in declarations.items():
                self.assertIsInstance(reason, str)
                self.assertTrue(reason.strip(), f"{rel_file}: '{declaration}' has no reason")

    def test_scan_breadth_covers_two_word_kinds(self):
        """The scanner must inventory forms like 'variation part def'."""
        found = check_model_sync._sysml_definitions(
            _kernel_path("de4sdv_product_line.sysml").read_text(encoding="utf-8")
        )
        self.assertTrue(
            any(declaration.startswith("variation part def ") for declaration in found)
        )


class ContractMappingDirection(unittest.TestCase):
    """Model contract -> kernel direction: mappings must resolve, exactly."""

    def test_every_class_has_exactly_one_typed_mapping(self):
        from de4sdv.semantic.kernel_contract import (
            KernelExternalMapping, KernelFileMapping, KernelNativeMapping)

        contract = model_contract()
        self.assertGreaterEqual(len(contract.classes), 60)
        for name in contract.classes:
            mapping = contract.mapping(name)
            self.assertIsInstance(
                mapping, (KernelFileMapping, KernelNativeMapping, KernelExternalMapping), name)

    def test_catches_renamed_kernel_declaration(self):
        from de4sdv.semantic.kernel_contract import KernelFileMapping

        errors = _run_contract({"EngineeringIncrement": KernelFileMapping(
            GOVERNED_DIR + "/de4sdv_method_context.sysml", "part def NoLongerExists")})
        self.assertTrue(any("part def NoLongerExists" in e and "not found" in e
                            for e in errors), errors)

    def test_catches_mapping_to_same_name_in_wrong_file(self):
        """Name-only matching is banned: the pair must be file-scoped."""
        from de4sdv.semantic.kernel_contract import KernelFileMapping

        errors = _run_contract({"ProductLine": KernelFileMapping(
            GOVERNED_DIR + "/de4sdv_method_context.sysml", "part def ProductLine")})
        self.assertTrue(any("'part def ProductLine'" in e and "not found" in e
                            for e in errors), errors)

    def test_catches_missing_kernel_file(self):
        from de4sdv.semantic.kernel_contract import KernelFileMapping

        errors = _run_contract({"EngineeringIncrement": KernelFileMapping(
            "no/such/file.sysml", "part def EngineeringIncrement")})
        self.assertTrue(any("kernel file not found" in e for e in errors), errors)

    def test_catches_unsafe_kernel_file(self):
        from de4sdv.semantic.kernel_contract import KernelFileMapping

        errors = _run_contract({"EngineeringIncrement": KernelFileMapping(
            "../outside.sysml", "part def EngineeringIncrement")})
        self.assertTrue(any("repository-relative" in e for e in errors), errors)

    def test_catches_half_specified_kernel_mapping(self):
        from de4sdv.semantic.kernel_contract import KernelFileMapping

        errors = _run_contract({"EngineeringIncrement": KernelFileMapping(
            GOVERNED_DIR + "/de4sdv_method_context.sysml", " ")})
        self.assertTrue(any("needs both file and declaration" in e for e in errors), errors)

    def test_catches_unrecognized_kernel_mapping(self):
        errors = _run_contract({"EngineeringIncrement": object()})
        self.assertTrue(any("unrecognized kernel mapping" in e for e in errors), errors)

    def test_catches_class_without_mapping(self):
        errors = _run_contract({"EngineeringIncrement": KeyError("EngineeringIncrement")})
        self.assertTrue(any("EngineeringIncrement: no kernel mapping" in e for e in errors), errors)

    def test_catches_unbuildable_model_contract(self):
        errors: list[str] = []
        with mock.patch.object(check_model_sync, "_load_model_contract",
                               side_effect=ValueError("duplicate provider")):
            check_model_sync.check_ontology_kernel_contract(errors)
        self.assertTrue(any("model-built kernel contract cannot be built" in e
                            and "duplicate provider" in e for e in errors), errors)

    def test_catches_corrupt_model_layer(self):
        """A real layer file that does not parse fails the gate (no fallback)."""
        target = ROOT / BATCH2
        original_text, original_bytes = Path.read_text, Path.read_bytes

        def fake_text(self, *args, **kwargs):
            return "{not json" if self == target else original_text(self, *args, **kwargs)

        def fake_bytes(self, *args, **kwargs):
            return b"{not json" if self == target else original_bytes(self, *args, **kwargs)

        errors: list[str] = []
        with mock.patch.object(Path, "read_text", fake_text), \
                mock.patch.object(Path, "read_bytes", fake_bytes):
            check_model_sync.check_ontology_kernel_contract(errors)
        self.assertTrue(any("model-built kernel contract cannot be built" in e
                            for e in errors), errors)


class ContractInventoryDirection(unittest.TestCase):
    """Kernel -> model direction: every declaration needs a decision.

    Enforced by the model-projection coverage gate over the D3 manifest.
    """

    def test_catches_unclassified_new_kernel_declaration(self):
        process = _kernel_path("de4sdv_method_process.sysml")
        original = process.read_text(encoding="utf-8")
        tampered = original.replace(
            "enum def IncrementSize {",
            "part def BrandNewConcept {\n  }\n\n  enum def IncrementSize {",
        )
        errors = _run_coverage(tampered_texts={str(process): tampered})
        self.assertTrue(
            any("BrandNewConcept" in e and "unclassified" in e for e in errors),
            errors,
        )

    def test_catches_stale_listed_declaration_after_rename(self):
        manifest = _manifest()
        declarations = manifest["declarations"]
        rel_file = next(iter(declarations))
        first = next(iter(declarations[rel_file]))
        del declarations[rel_file][first]
        declarations[rel_file]["part def Ghost"] = "stale"
        errors = _run_coverage(manifest)
        self.assertTrue(any("'part def Ghost' does not exist" in e for e in errors), errors)
        self.assertTrue(any(first in e and "unclassified" in e for e in errors), errors)

    def test_catches_listed_declaration_with_empty_reason(self):
        manifest = _manifest()
        declarations = manifest["declarations"]
        rel_file = next(iter(declarations))
        first = next(iter(declarations[rel_file]))
        declarations[rel_file][first] = ""
        errors = _run_coverage(manifest)
        self.assertTrue(any("needs a non-empty reason" in e for e in errors), errors)

    def test_catches_projection_and_listing_overlap(self):
        manifest = _manifest()
        manifest["declarations"][GOVERNED_DIR + "/de4sdv_method_context.sysml"][
            "part def EngineeringIncrement"] = "double bookkeeping"
        errors = _run_coverage(manifest)
        self.assertTrue(any("'part def EngineeringIncrement' is both projected" in e
                            for e in errors), errors)

    def test_catches_listing_outside_governed_directory(self):
        manifest = _manifest()
        manifest["declarations"]["somewhere/else.sysml"] = {"part def Thing": "not governed"}
        errors = _run_coverage(manifest)
        self.assertTrue(any("outside the governed directory" in e for e in errors), errors)

    def test_catches_missing_manifest_declarations(self):
        """Without declarations the contract itself cannot be built: the
        coverage gate fails closed (it cannot be evaluated)."""
        from de4sdv.semantic import model_projection_coverage as coverage

        manifest = _manifest()
        del manifest["declarations"]
        target = ROOT / MANIFEST
        original_read = Path.read_text

        def fake_read(self, *args, **kwargs):
            if self == target:
                return yaml.safe_dump(manifest)
            return original_read(self, *args, **kwargs)

        with mock.patch.object(Path, "read_text", fake_read):
            errors = coverage.run_check_errors(ROOT)
        self.assertTrue(any("cannot be evaluated" in e and "governed_directory/declarations" in e
                            for e in errors), errors)


class ContractSliceGuard(unittest.TestCase):
    """Feature slices must not re-declare mapped kernel names.

    Enforced by the model-projection coverage gate since O4 Wave C1.
    """

    def test_catches_slice_redeclaration_of_mapped_kernel_name(self):
        slice_path = ROOT / (
            "textual-notation-of-model/packages/features/aebs/"
            "aebs_needs_requirements.sysml"
        )
        original = slice_path.read_text(encoding="utf-8")
        tampered = original + "\npart def RequirementCandidate {}\n"
        errors = _run_coverage(tampered_texts={str(slice_path): tampered})
        self.assertTrue(
            any(
                "re-declares projected kernel name 'RequirementCandidate'" in e
                for e in errors
            ),
            errors,
        )

    def test_slice_guard_derives_names_from_mappings_not_a_list(self):
        """The guard must derive from mappings/projection, not a hand-kept list."""
        import inspect

        from de4sdv.semantic import model_projection_coverage as coverage

        source = inspect.getsource(coverage.kernel_accounting)
        self.assertNotIn("_PROTECTED_CONCEPTS", source)
        self.assertIn("class_pins", source)


class ContractSemanticsPins(unittest.TestCase):
    """Content pins tying the model contract to semantics the gate cannot see."""

    def _batch2(self, identity):
        rows = json.loads((ROOT / BATCH2).read_text(encoding="utf-8"))["rows"]
        return next(row for row in rows if row["identity"] == identity)

    def test_feature_common_capability_disjointness_is_symmetric(self):
        feature = self._batch2("Feature")["grounding"]
        common = self._batch2("CommonCapability")["grounding"]
        self.assertEqual(feature["ontology_relations"]["disjoint_with"], ["CommonCapability"])
        self.assertEqual(common["ontology_relations"]["disjoint_with"], ["Feature"])
        contract = model_contract()
        feature_map = contract.mapping("Feature")
        common_map = contract.mapping("CommonCapability")
        self.assertIn("ProductLineFeatureCandidate", feature_map.declaration)
        self.assertIn("CommonProductLineCapability", common_map.declaration)
        self.assertEqual(feature_map.file, common_map.file)
        kernel_text = check_model_sync._read(ROOT / feature_map.file)
        for declaration in (feature_map.declaration, common_map.declaration):
            self.assertTrue(check_model_sync._declaration_exists(kernel_text, declaration),
                            declaration)

    def test_status_vocabulary_comes_from_upstream_not_local(self):
        """ADR 0009: no parallel local status enums."""
        from de4sdv.semantic.kernel_contract import KernelExternalMapping

        mapping = model_contract().mapping("EvidenceStatus")
        self.assertIsInstance(mapping, KernelExternalMapping)
        self.assertIn("VVStatus", mapping.external)

    def test_semantic_authority_identity_is_model_built(self):
        identity = model_contract().identity
        self.assertEqual(identity.schema, "de4sdv.semantic-authority/v1")
        self.assertTrue(identity.id.startswith("sai-"))
        paths = {path for path, _ in identity.layers}
        self.assertNotIn("approach/framework/ontology/de4sdv-basic-ontology.yaml", paths)
        self.assertIn(BATCH2, paths)

    def test_method_context_kernel_declares_pinned_declarations(self):
        context_file = GOVERNED_DIR + "/de4sdv_method_context.sysml"
        kernel_text = check_model_sync._read(ROOT / context_file)
        contract = model_contract()
        mapped = [m.declaration for m in (contract.mapping(n) for n in contract.classes)
                  if getattr(m, "file", None) == context_file]
        self.assertGreaterEqual(len(mapped), 5)
        for declaration in mapped:
            self.assertTrue(check_model_sync._declaration_exists(kernel_text, declaration),
                            declaration)

    def test_governed_inventory_is_not_empty(self):
        """Meta-check: the scanner must actually find kernel declarations."""
        contract = model_contract()
        mapped = sum(1 for n in contract.classes if hasattr(contract.mapping(n), "declaration"))
        listed = sum(len(d) for d in _manifest()["declarations"].values())
        self.assertGreaterEqual(mapped, 20)
        self.assertGreaterEqual(listed, 50)


if __name__ == "__main__":
    unittest.main()
