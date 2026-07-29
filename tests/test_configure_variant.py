"""
Tests for the DE4SDV PLE configurator (tools/configure_variant.py).

Tests cover:
  - Valid configurations pass validation and generate correct SysML v2
  - Invalid configurations are rejected with clear error messages
  - Feature tree parsing and path resolution
  - Constraint evaluation (requires, excludes, in, ==, !=)
  - Generation output correctness
"""

import copy
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "configure_variant.py"
FM = REPO_ROOT / "model-based-product-line-engineering" / "feature-models" / "sdv_product_line.yaml"
SHARED_MODEL = (
    REPO_ROOT / "textual-notation-of-model" / "packages" / "architecture"
    / "sdv_platform_stack.sysml"
)
BOF_DIR = REPO_ROOT / "model-based-product-line-engineering" / "feature-configurations"


class TestConfigureVariant(unittest.TestCase):

    def run_config(self, bof_path, extra_args=None, expect_fail=False,
                   feature_model_path=FM, cwd=None):
        """Run the configurator and return (returncode, stdout, stderr)."""
        cmd = [
            sys.executable, str(SCRIPT),
            "--feature-model", str(feature_model_path),
            "--bof", str(bof_path),
        ]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, cwd=cwd
        )

        if expect_fail:
            self.assertNotEqual(result.returncode, 0,
                                f"Expected failure but got success:\n{result.stdout}")
        else:
            self.assertEqual(result.returncode, 0,
                             f"Expected success but got failure:\n{result.stderr}")

        return result.returncode, result.stdout, result.stderr

    # ── Valid configurations ──────────────────────────────

    def test_valid_linux_score_autoware(self):
        """Valid: Autoware + S-CORE + Linux + None hypervisor."""
        rc, out, err = self.run_config(
            BOF_DIR / "example-linux-score-autoware.yaml",
            extra_args=["--check-only"]
        )
        self.assertIn("Configuration valid", err)

    def test_valid_apollo_qnx_qvm(self):
        """Valid: Apollo + AUTOSAR Adaptive + QNX + QVM."""
        rc, out, err = self.run_config(
            BOF_DIR / "apollo-qnx-qvm.yaml",
            extra_args=["--check-only"]
        )
        self.assertIn("Configuration valid", err)

    # ── Invalid configurations ────────────────────────────

    def test_invalid_score_android(self):
        """Invalid: S-CORE + Android HLOS violates C001."""
        rc, out, err = self.run_config(
            BOF_DIR / "invalid-score-android.yaml",
            extra_args=["--check-only"],
            expect_fail=True
        )
        self.assertIn("C001", err)
        self.assertIn("requires", err)

    def test_invalid_missing_mandatory_selection(self):
        """Invalid: missing a mandatory alternative group selection."""
        bof = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        bof.write("""
name: TestMissingMandatory
description: Missing OS selection
selections:
  PlatformStack.VehicleApplication: Autoware
  PlatformStack.Middleware: EclipseSCORE
  # OS missing — mandatory alternative
  PlatformStack.Hypervisor: None
  Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS: true
  Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  Capabilities.ForwardCollisionMitigation.BicycleDetection: false
  Capabilities.AdaptiveCruiseControl: false
  Capabilities.LaneKeepAssist: false
  SensingBoundary.PerceptionSensors: [LiDAR]
""")
        bof.close()
        try:
            rc, out, err = self.run_config(
                bof.name, extra_args=["--check-only"], expect_fail=True
            )
            self.assertIn("no selection", err.lower())
        finally:
            os.unlink(bof.name)

    def test_invalid_wrong_variant_name(self):
        """Invalid: selecting a variant that doesn't exist."""
        bof = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        bof.write("""
name: TestWrongVariant
description: Nonexistent variant
selections:
  PlatformStack.VehicleApplication: NonexistentStack
  PlatformStack.Middleware: EclipseSCORE
  PlatformStack.OS: Linux
  PlatformStack.Hypervisor: None
  Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS: true
  Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  Capabilities.ForwardCollisionMitigation.BicycleDetection: false
  Capabilities.AdaptiveCruiseControl: false
  Capabilities.LaneKeepAssist: false
  SensingBoundary.PerceptionSensors: [LiDAR]
""")
        bof.close()
        try:
            rc, out, err = self.run_config(
                bof.name, extra_args=["--check-only"], expect_fail=True
            )
            self.assertIn("not a valid XOR choice", err)
        finally:
            os.unlink(bof.name)

    def test_invalid_mapping_target(self):
        """Mapped variants must exist in the shared SysML v2 asset."""
        feature_model = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        feature_model.write(
            FM.read_text().replace(
                "maps_to_variant: autoware",
                "maps_to_variant: nonexistentSharedAssetVariant",
                1,
            )
        )
        feature_model.close()
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only"],
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("was not found", err)
            self.assertIn("nonexistentSharedAssetVariant", err)
        finally:
            os.unlink(feature_model.name)

    def test_variant_must_belong_to_mapped_variation(self):
        """A same-named variant under another variation cannot satisfy a mapping."""
        source = SHARED_MODEL.read_text()
        source = source.replace(
            "      variant part autoware : AutowareStack;\n", "", 1
        ).replace(
            "      variant part eclipseSCORE : EclipseSCORE;",
            "      variant part eclipseSCORE : EclipseSCORE;\n"
            "      variant part autoware : AutowareStack;",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("vehicleApplication::autoware", err)
            self.assertIn("complete direct declaration", err)
        finally:
            os.unlink(shared.name)

    def test_comment_only_mapping_target_is_rejected(self):
        """Comment text cannot masquerade as a SysML variant declaration."""
        source = SHARED_MODEL.read_text().replace(
            "      variant part autoware : AutowareStack;",
            "      // variant part autoware : AutowareStack;",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("vehicleApplication::autoware", err)
        finally:
            os.unlink(shared.name)

    def test_nested_variant_is_not_directly_owned(self):
        """A nested declaration cannot satisfy direct variation ownership."""
        source = SHARED_MODEL.read_text().replace(
            "      variant part autoware : AutowareStack;",
            "      part nested { variant part autoware : AutowareStack; }",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("vehicleApplication::autoware", err)
            self.assertIn("complete direct declaration", err)
        finally:
            os.unlink(shared.name)

    def test_semicolon_declaration_cannot_borrow_later_body(self):
        """A semicolon-terminated declaration has no braced body."""
        source = SHARED_MODEL.read_text().replace(
            "  part def SDVPlatformStack {",
            "  part def SDVPlatformStack;\n  part def Unrelated {",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("part def 'SDVPlatformStack' was not found", err)
        finally:
            os.unlink(shared.name)

    def test_nested_stack_under_wrong_owner_is_rejected(self):
        """The imported stack must be a direct child of its expected package."""
        source = SHARED_MODEL.read_text().replace(
            "  part def SDVPlatformStack {",
            "  part def Unrelated {\n  part def SDVPlatformStack {",
            1,
        )
        last_package_close = source.rfind("\n}")
        source = (
            source[:last_package_close] + "\n  }" + source[last_package_close:]
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("complete direct declaration", err)
            self.assertIn("DE4SDV_SDVPlatformStack", err)
        finally:
            os.unlink(shared.name)

    def test_semicolon_variation_cannot_borrow_later_body(self):
        """A body after a semicolon is not owned by the mapped variation."""
        source = SHARED_MODEL.read_text().replace(
            "    variation part vehicleApplication : VehicleApplicationLayer {",
            "    variation part vehicleApplication : VehicleApplicationLayer;\n"
            "    part unrelated {",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("SDVPlatformStack.vehicleApplication", err)
            self.assertIn("was not found", err)
        finally:
            os.unlink(shared.name)

    def test_duplicate_sysml_owner_declarations_are_rejected(self):
        """Mapped ownership must resolve to one package, stack, variation, and variant."""
        base = SHARED_MODEL.read_text()
        cases = {
            "package": base + "\n" + base,
            "stack": base.replace(
                "  part def SDVPlatformStack {",
                "  part def SDVPlatformStack {}\n  part def SDVPlatformStack {",
                1,
            ),
            "variation": base.replace(
                "    variation part vehicleApplication : VehicleApplicationLayer {",
                "    variation part vehicleApplication {}\n"
                "    variation part vehicleApplication : VehicleApplicationLayer {",
                1,
            ),
            "variant": base.replace(
                "      variant part autoware : AutowareStack;",
                "      variant part autoware : AutowareStack;\n"
                "      variant part autoware : AutowareStack;",
                1,
            ),
        }
        for level, source in cases.items():
            with self.subTest(level=level), tempfile.NamedTemporaryFile(
                mode="w", suffix=".sysml", delete=False
            ) as shared:
                shared.write(source)
                shared_path = shared.name
            try:
                rc, out, err = self.run_config(
                    BOF_DIR / "example-linux-score-autoware.yaml",
                    extra_args=["--check-only", "--shared-assets-model", shared_path],
                    expect_fail=True,
                )
                self.assertIn("multiple direct declarations", err)
            finally:
                os.unlink(shared_path)

    def test_unterminated_variant_prefix_is_rejected(self):
        """A mapped variant declaration needs a semicolon or owned body."""
        source = SHARED_MODEL.read_text().replace(
            "      variant part autoware : AutowareStack;",
            "      variant part autoware",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("complete direct declaration", err)
        finally:
            os.unlink(shared.name)

    def test_unmapped_alternative_is_valid_and_annotated(self):
        """Feature choices without mapped assets remain unresolved provenance."""
        feature_data = yaml.safe_load(FM.read_text())
        capabilities = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "Capabilities"
        )
        capabilities["children"].append({
            "name": "DrivingMode",
            "id": "F-CAPABILITY-DRIVING-MODE",
            "binding_time": "unassigned",
            "type": "alternative",
            "children": [
                {
                    "name": "Normal",
                    "id": "F-CAPABILITY-DRIVING-MODE-NORMAL",
                    "binding_time": "unassigned",
                },
                {
                    "name": "Sport",
                    "id": "F-CAPABILITY-DRIVING-MODE-SPORT",
                    "binding_time": "unassigned",
                },
            ],
        })
        bof_data = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )
        bof_data["selections"]["Capabilities.DrivingMode"] = "Normal"

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model, tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as bof:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                Path(bof.name), feature_model_path=Path(feature_model.name)
            )
            self.assertIn("Capabilities.DrivingMode = Normal", out)
            self.assertIn("not resolved in SysML", out)
        finally:
            os.unlink(feature_model.name)
            os.unlink(bof.name)

    def test_unmapped_or_group_accepts_multiple_choices(self):
        """OR groups require one-or-more choices and stay unresolved if unmapped."""
        feature_data = yaml.safe_load(FM.read_text())
        capabilities = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "Capabilities"
        )
        capabilities["children"].append({
            "name": "DrivingModes",
            "id": "F-CAPABILITY-DRIVING-MODES",
            "binding_time": "unassigned",
            "type": "or_group",
            "children": [
                {
                    "name": "Eco",
                    "id": "F-CAPABILITY-DRIVING-MODES-ECO",
                    "binding_time": "unassigned",
                },
                {
                    "name": "Sport",
                    "id": "F-CAPABILITY-DRIVING-MODES-SPORT",
                    "binding_time": "unassigned",
                },
            ],
        })
        bof_data = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )
        bof_data["selections"]["Capabilities.DrivingModes"] = ["Eco", "Sport"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model, tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as bof:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                Path(bof.name), feature_model_path=Path(feature_model.name)
            )
            self.assertIn("Capabilities.DrivingModes = Eco, Sport", out)
            bof_data["selections"]["Capabilities.DrivingModes"] = "Eco"
            Path(bof.name).write_text(
                yaml.safe_dump(bof_data, sort_keys=False)
            )
            rc, out, err = self.run_config(
                Path(bof.name),
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("requires a non-empty list", err)
        finally:
            os.unlink(feature_model.name)
            os.unlink(bof.name)

    def test_mapped_or_group_is_rejected(self):
        """Native SysML variation mapping is XOR, not OR-group derivation."""
        feature_data = yaml.safe_load(FM.read_text())
        platform = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "PlatformStack"
        )
        application = next(
            child for child in platform["children"]
            if child["name"] == "VehicleApplication"
        )
        application["type"] = "or_group"
        bof_data = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )
        bof_data["selections"]["PlatformStack.VehicleApplication"] = ["Autoware"]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model, tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as bof:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                Path(bof.name),
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("must use alternative (XOR), not or_group", err)
        finally:
            os.unlink(feature_model.name)
            os.unlink(bof.name)

    def test_partial_mapping_metadata_fails_cleanly(self):
        """A mapped variation cannot silently omit one child mapping."""
        source = FM.read_text().replace(
            ", maps_to_variant: autoware", "", 1
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            feature_model.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("must map every variant child", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(feature_model.name)

    def test_mapped_child_requires_mapped_parent(self):
        """Variant mapping metadata cannot exist beneath an unmapped group."""
        source = FM.read_text().replace(
            "          maps_to: SDVPlatformStack.vehicleApplication\n", "", 1
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            feature_model.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("has mapped variant children", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(feature_model.name)

    def test_orphan_mapping_on_non_selection_node_is_rejected(self):
        """Ordinary capability nodes cannot carry SysML variant mappings."""
        feature_data = yaml.safe_load(FM.read_text())
        capabilities = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "Capabilities"
        )
        adaptive_cruise = next(
            child for child in capabilities["children"]
            if child["name"] == "AdaptiveCruiseControl"
        )
        adaptive_cruise["maps_to"] = "SDVPlatformStack.orphan"
        adaptive_cruise["maps_to_variant"] = "orphan"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("must not declare maps_to", err)
            self.assertIn("orphan maps_to_variant", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(feature_model.name)

    def test_malformed_mapping_metadata_reports_errors_without_crash(self):
        """Non-string and unhashable YAML values fail validation safely."""
        feature_data = yaml.safe_load(FM.read_text())
        platform = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "PlatformStack"
        )
        application = next(
            child for child in platform["children"]
            if child["name"] == "VehicleApplication"
        )
        application["maps_to"] = 123
        application["binding_time"] = ["design"]
        application["children"][0]["maps_to_variant"] = ["autoware"]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("invalid maps_to", err)
            self.assertIn("invalid binding_time", err)
            self.assertIn("invalid maps_to_variant", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(feature_model.name)

    def test_duplicate_sibling_names_and_paths_are_rejected(self):
        """A selection string must identify exactly one catalogue node."""
        feature_data = yaml.safe_load(FM.read_text())
        platform = next(
            child for child in feature_data["root"]["children"]
            if child["name"] == "PlatformStack"
        )
        application = next(
            child for child in platform["children"]
            if child["name"] == "VehicleApplication"
        )
        duplicate = copy.deepcopy(application["children"][0])
        duplicate["id"] = "F-APP-DUPLICATE-AUTOWARE"
        duplicate["maps_to_variant"] = "openpilot"
        application["children"].append(duplicate)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            yaml.safe_dump(feature_data, feature_model, sort_keys=False)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("Duplicate sibling name 'Autoware'", err)
            self.assertIn(
                "Duplicate computed feature path 'PlatformStack.VehicleApplication.Autoware'",
                err,
            )
        finally:
            os.unlink(feature_model.name)

    def test_root_id_is_required(self):
        """The catalogue root participates in stable-ID validation."""
        source = FM.read_text().replace("  id: PL-DE4SDV\n", "", 1)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as feature_model:
            feature_model.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                expect_fail=True,
                feature_model_path=Path(feature_model.name),
            )
            self.assertIn("SDVProductLine", err)
            self.assertIn("missing stable 'id'", err)
        finally:
            os.unlink(feature_model.name)

    def test_malformed_document_shapes_fail_without_traceback(self):
        """Null/list/scalar YAML shapes are parse errors, not crashes."""
        cases = [
            ("null\n", FM.read_text()),
            ("- bad\n", FM.read_text()),
            ("name: Bad\nselections: []\n", FM.read_text()),
            ((BOF_DIR / "example-linux-score-autoware.yaml").read_text(), "null\n"),
            ((BOF_DIR / "example-linux-score-autoware.yaml").read_text(), "root: []\n"),
            ((BOF_DIR / "example-linux-score-autoware.yaml").read_text(), "root:\n  name: Root\n  children: bad\n"),
            ((BOF_DIR / "example-linux-score-autoware.yaml").read_text(), "root:\n  name: Root\nconstraints: bad\n"),
        ]
        for bof_text, feature_text in cases:
            with self.subTest(bof=bof_text[:20], feature=feature_text[:20]):
                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as bof, tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as feature:
                    bof.write(bof_text)
                    feature.write(feature_text)
                try:
                    rc, out, err = self.run_config(
                        Path(bof.name), feature_model_path=Path(feature.name),
                        expect_fail=True,
                    )
                    self.assertEqual(2, rc)
                    self.assertNotIn("Traceback", err)
                finally:
                    os.unlink(bof.name)
                    os.unlink(feature.name)

    def test_duplicate_yaml_selection_keys_are_rejected(self):
        """A BoF cannot rely on YAML last-key-wins ambiguity."""
        source = (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        source = source.replace(
            "  PlatformStack.OS: Linux",
            "  PlatformStack.OS: QNX\n  PlatformStack.OS: Linux",
            1,
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as bof:
            bof.write(source)
        try:
            rc, out, err = self.run_config(Path(bof.name), expect_fail=True)
            self.assertEqual(2, rc)
            self.assertIn("duplicate YAML key", err)
            self.assertNotIn("Traceback", err)
        finally:
            os.unlink(bof.name)

    def test_relationship_boolean_and_constraint_types_are_enforced(self):
        """Misspelled relationships, non-booleans, and unknown constraints fail."""
        feature_data = yaml.safe_load(FM.read_text())
        platform = next(c for c in feature_data["root"]["children"] if c["name"] == "PlatformStack")
        platform["type"] = "mandatroy"
        feature_data["constraints"].append({
            "id": "C-BAD", "type": "advises", "if": "Capabilities.LaneKeepAssist",
            "then": "Capabilities.AdaptiveCruiseControl",
        })
        bof_data = yaml.safe_load((BOF_DIR / "example-linux-score-autoware.yaml").read_text())
        bof_data["selections"]["Capabilities.LaneKeepAssist"] = "false"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as feature, tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as bof:
            yaml.safe_dump(feature_data, feature, sort_keys=False)
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(Path(bof.name), feature_model_path=Path(feature.name), expect_fail=True)
            self.assertIn("invalid relationship type", err)
            self.assertIn("must be a YAML boolean", err)
            self.assertIn("unknown constraint type", err)
        finally:
            os.unlink(feature.name)
            os.unlink(bof.name)

    def test_or_group_constraint_equality_matches_members(self):
        """Equality against an OR group means membership in selected choices."""
        feature_data = yaml.safe_load(FM.read_text())
        capabilities = next(c for c in feature_data["root"]["children"] if c["name"] == "Capabilities")
        capabilities["children"].append({
            "name": "Modes", "id": "F-MODES", "type": "or_group",
            "binding_time": "unassigned", "children": [
                {"name": "Sport", "id": "F-MODE-SPORT", "binding_time": "unassigned"},
                {"name": "Eco", "id": "F-MODE-ECO", "binding_time": "unassigned"},
            ],
        })
        feature_data["constraints"].append({
            "id": "C-OR", "type": "requires", "if": "Capabilities.Modes == Sport",
            "then": "Capabilities.AdaptiveCruiseControl",
        })
        bof_data = yaml.safe_load((BOF_DIR / "example-linux-score-autoware.yaml").read_text())
        bof_data["selections"]["Capabilities.Modes"] = ["Sport"]
        bof_data["selections"]["Capabilities.AdaptiveCruiseControl"] = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as feature, tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as bof:
            yaml.safe_dump(feature_data, feature, sort_keys=False)
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(Path(bof.name), feature_model_path=Path(feature.name), expect_fail=True)
            self.assertIn("C-OR", err)
        finally:
            os.unlink(feature.name)
            os.unlink(bof.name)

    def test_constraint_expressions_use_known_paths_and_closed_grammar(self):
        """Malformed/unknown conditions cannot silently disable constraints."""
        feature_data = yaml.safe_load(FM.read_text())
        invalid_expressions = [
            "PlatformStack.Middleware = EclipseSCORE",
            "PlatformStack.Middleware ~~ EclipseSCORE",
            "No.Such.Path == Anything",
            "PlatformStack.Middleware in []",
        ]
        for expression in invalid_expressions:
            with self.subTest(expression=expression):
                mutated = copy.deepcopy(feature_data)
                mutated["constraints"] = [{
                    "id": "C-BAD",
                    "type": "requires",
                    "if": expression,
                    "then": "Capabilities.AdaptiveCruiseControl",
                }]
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as feature_file:
                    yaml.safe_dump(mutated, feature_file, sort_keys=False)
                try:
                    rc, out, err = self.run_config(
                        BOF_DIR / "example-linux-score-autoware.yaml",
                        feature_model_path=Path(feature_file.name),
                        expect_fail=True,
                    )
                    self.assertIn("constraint expression", err.lower())
                finally:
                    os.unlink(feature_file.name)

    def test_selection_groups_must_be_nonempty_leaf_sets(self):
        """Accepted group types must have enforceable cardinality semantics."""
        feature_data = yaml.safe_load(FM.read_text())
        cases = []
        empty = copy.deepcopy(feature_data)
        empty["root"]["children"][0]["children"][0]["children"] = []
        cases.append(empty)
        nested = copy.deepcopy(feature_data)
        group = nested["root"]["children"][0]["children"][0]
        group["children"][0]["children"] = [{
            "name": "Nested", "id": "F-NESTED", "type": "optional",
            "binding_time": "unassigned",
        }]
        cases.append(nested)
        for mutated in cases:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as feature_file:
                yaml.safe_dump(mutated, feature_file, sort_keys=False)
            try:
                rc, out, err = self.run_config(
                    BOF_DIR / "example-linux-score-autoware.yaml",
                    feature_model_path=Path(feature_file.name),
                    expect_fail=True,
                )
                self.assertIn("selection group", err.lower())
            finally:
                os.unlink(feature_file.name)

    def test_directory_cli_paths_fail_without_traceback(self):
        """Directory inputs/outputs use controlled exit code 2 diagnostics."""
        for option in ("--feature-model", "--bof"):
            args = [
                sys.executable, str(SCRIPT),
                "--feature-model", str(FM),
                "--bof", str(BOF_DIR / "example-linux-score-autoware.yaml"),
            ]
            args[args.index(option) + 1] = str(REPO_ROOT)
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)
        result = subprocess.run([
            sys.executable, str(SCRIPT), "--feature-model", str(FM),
            "--bof", str(BOF_DIR / "example-linux-score-autoware.yaml"),
            "--output", str(REPO_ROOT),
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_non_utf8_inputs_fail_without_traceback(self):
        """Text inputs with invalid encoding use controlled diagnostics."""
        valid_bof = BOF_DIR / "example-linux-score-autoware.yaml"
        for option in ("--feature-model", "--bof", "--shared-assets-model"):
            with tempfile.NamedTemporaryFile(delete=False) as malformed:
                malformed.write(b"\xff\xfe\x80")
            args = [
                sys.executable, str(SCRIPT),
                "--feature-model", str(FM),
                "--bof", str(valid_bof),
                "--shared-assets-model", str(SHARED_MODEL),
                "--check-only",
            ]
            args[args.index(option) + 1] = malformed.name
            try:
                result = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Error reading input", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
            finally:
                os.unlink(malformed.name)

    def test_globally_unbalanced_sysml_is_rejected(self):
        """Ownership checks do not run against lexically broken source."""
        base = SHARED_MODEL.read_text()
        for source in ("/* unterminated\n" + base, "}\n" + base):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".sysml", delete=False
            ) as shared:
                shared.write(source)
            try:
                rc, out, err = self.run_config(
                    BOF_DIR / "example-linux-score-autoware.yaml",
                    extra_args=["--check-only", "--shared-assets-model", shared.name],
                    expect_fail=True,
                )
                self.assertIn("lexically invalid", err.lower())
            finally:
                os.unlink(shared.name)

    def test_mapped_variant_rejects_nonzero_multiplicity(self):
        source = SHARED_MODEL.read_text().replace(
            "variant part autoware : AutowareStack;",
            "variant part autoware[2] : AutowareStack;",
            1,
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(source)
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--check-only", "--shared-assets-model", shared.name],
                expect_fail=True,
            )
            self.assertIn("complete direct declaration", err)
        finally:
            os.unlink(shared.name)

    # ── Generation ─────────────────────────────────────────

    def test_generates_sysml_output(self):
        """Configurator generates valid SysML v2 part def."""
        rc, out, err = self.run_config(
            BOF_DIR / "example-linux-score-autoware.yaml"
        )
        self.assertIn("part def ExampleLinuxSCOREVariant :> SDVPlatformStack", out)
        self.assertIn("private import DE4SDV_SDVPlatformStack::SDVPlatformStack;", out)
        self.assertIn("platform-stack product-model projection", out)
        self.assertIn("not a complete member-product specification", out)
        shared_hash = hashlib.sha256(SHARED_MODEL.read_bytes()).hexdigest()
        feature_hash = hashlib.sha256(FM.read_bytes()).hexdigest()
        bof_path = BOF_DIR / "example-linux-score-autoware.yaml"
        bof_hash = hashlib.sha256(bof_path.read_bytes()).hexdigest()
        shared_relative = SHARED_MODEL.relative_to(REPO_ROOT).as_posix()
        blob_id = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "hash-object", "--stdin"],
            input=SHARED_MODEL.read_bytes(),
        ).decode().strip()
        self.assertIn(
            f"Shared-assets source baseline: git-blob:{blob_id}:"
            f"{shared_relative} (content-addressed)",
            out,
        )
        self.assertNotIn("Shared-assets source baseline: git:", out)
        self.assertIn(f"Shared-assets model SHA-256: {shared_hash}", out)
        self.assertIn(f"Feature model SHA-256: {feature_hash}", out)
        self.assertIn(f"Bill-of-Features SHA-256: {bof_hash}", out)
        self.assertIn("part :>> vehicleApplication = vehicleApplication::autoware;", out)
        self.assertIn("part :>> middleware = middleware::eclipseSCORE;", out)
        self.assertIn("part :>> osPlatform = osPlatform::linux;", out)
        self.assertIn("part :>> hypervisor = hypervisor::none;", out)

    def test_projection_metadata_targets_declared_package_and_owner(self):
        """One configurator derives projections from reusable non-platform assets."""
        feature_model = """
projection:
  package: DE4SDV_ExecutionEnvironments
  owner: EngineeringExecutionEnvironment
  label: engineering execution-environment
root:
  name: EngineeringEnvironmentFamily
  id: PL-ENGINEERING-ENVIRONMENT
  children:
    - name: ComputeNode
      id: F-ENGINEERING-COMPUTE
      type: alternative
      binding_time: design
      maps_to: EngineeringExecutionEnvironment.computeNode
      children:
        - name: Jetson
          id: F-ENGINEERING-COMPUTE-JETSON
          binding_time: design
          maps_to_variant: jetson
        - name: AppleSilicon
          id: F-ENGINEERING-COMPUTE-APPLE-SILICON
          binding_time: design
          maps_to_variant: appleSilicon
constraints: []
"""
        bof = """
name: JetsonEnvironment
selections:
  ComputeNode: Jetson
"""
        shared_model = """
package DE4SDV_ExecutionEnvironments {
  part def ComputeNode;
  part def JetsonCompute :> ComputeNode;
  part def AppleSiliconCompute :> ComputeNode;
  part def EngineeringExecutionEnvironment {
    variation part computeNode : ComputeNode {
      variant part jetson : JetsonCompute;
      variant part appleSilicon : AppleSiliconCompute;
    }
  }
}
"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fm = tmp / "feature-model.yaml"
            bof_path = tmp / "jetson.yaml"
            shared = tmp / "execution-environments.sysml"
            fm.write_text(feature_model)
            bof_path.write_text(bof)
            shared.write_text(shared_model)
            rc, out, err = self.run_config(
                bof_path,
                feature_model_path=fm,
                extra_args=["--shared-assets-model", str(shared)],
            )

        self.assertIn(
            "private import DE4SDV_ExecutionEnvironments::EngineeringExecutionEnvironment;",
            out,
        )
        self.assertIn(
            "part def JetsonEnvironment :> EngineeringExecutionEnvironment", out
        )
        self.assertIn("engineering execution-environment product-model projection", out)
        self.assertIn("part :>> computeNode = computeNode::jetson;", out)

    def test_projection_metadata_rejects_invalid_sysml_identifiers(self):
        feature_data = yaml.safe_load(FM.read_text())
        for field, value in (("package", "Bad;Package"), ("owner", "Bad Owner")):
            candidate = copy.deepcopy(feature_data)
            candidate["projection"] = {
                "package": "DE4SDV_SDVPlatformStack",
                "owner": "SDVPlatformStack",
                "label": "platform-stack",
            }
            candidate["projection"][field] = value
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as feature_model:
                yaml.safe_dump(candidate, feature_model, sort_keys=False)
            try:
                rc, out, err = self.run_config(
                    BOF_DIR / "example-linux-score-autoware.yaml",
                    feature_model_path=Path(feature_model.name),
                    expect_fail=True,
                )
                self.assertEqual(rc, 2)
                self.assertIn(f"projection.{field}", err)
                self.assertNotIn("Traceback", err)
            finally:
                os.unlink(feature_model.name)

    def test_tested_configuration_requires_retained_evidence(self):
        bof_data = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )
        bof_data["evidence"] = {"status": "tested", "artifacts": []}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as bof:
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(Path(bof.name), expect_fail=True)
            self.assertIn("tested configuration requires retained evidence", err)
        finally:
            os.unlink(bof.name)

    def test_evidence_artifacts_must_be_tracked_repository_files(self):
        """Evidence cannot escape the reviewed Git snapshot."""
        base = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )

        def rejected(path_text, expected):
            candidate = copy.deepcopy(base)
            candidate["evidence"] = {
                "status": "tested",
                "artifacts": [{"id": "EVID-TEST", "path": path_text}],
            }
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as bof:
                yaml.safe_dump(candidate, bof, sort_keys=False)
            try:
                rc, out, err = self.run_config(Path(bof.name), expect_fail=True)
                self.assertEqual(rc, 1)
                self.assertIn(expected, err)
            finally:
                os.unlink(bof.name)

        rejected("../outside.txt", "must be repository-relative")
        rejected("/etc/hosts", "must be repository-relative")
        rejected("missing-evidence.txt", "does not exist")
        rejected(".git/config", "repository metadata")

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as directory:
            untracked = Path(directory) / "untracked.txt"
            untracked.write_text("not retained\n")
            rejected(
                untracked.relative_to(REPO_ROOT).as_posix(),
                "is not tracked by Git",
            )

            escaping = Path(directory) / "escaping-link"
            escaping.symlink_to("/etc/hosts")
            rejected(
                escaping.relative_to(REPO_ROOT).as_posix(),
                "must not traverse symbolic links",
            )

            metadata_dir = Path(directory) / "metadata-dir"
            metadata_dir.symlink_to(REPO_ROOT / ".git", target_is_directory=True)
            rejected(
                (metadata_dir / "config").relative_to(REPO_ROOT).as_posix(),
                "must not traverse symbolic links",
            )

            tracked_target = Path(directory) / "tracked-target-link"
            tracked_target.symlink_to(REPO_ROOT / "README.md")
            rejected(
                tracked_target.relative_to(REPO_ROOT).as_posix(),
                "must not traverse symbolic links",
            )

    def test_bof_name_and_comment_fields_cannot_inject_sysml(self):
        """Generated identifiers are validated and comment data is escaped."""
        bof_data = yaml.safe_load(
            (BOF_DIR / "example-linux-score-autoware.yaml").read_text()
        )
        bof_data["name"] = "Injected { part def Escape"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as bof:
            yaml.safe_dump(bof_data, bof, sort_keys=False)
        try:
            rc, out, err = self.run_config(Path(bof.name), expect_fail=True)
            self.assertIn("valid unquoted SysML identifier", err)
            self.assertNotIn("part def Injected", out)

            bof_data["name"] = "SafeVariant"
            bof_data["description"] = (
                "safe */\n} part def Injected {}\n/* trailing"
            )
            Path(bof.name).write_text(yaml.safe_dump(bof_data, sort_keys=False))
            rc, out, err = self.run_config(Path(bof.name))
            self.assertIn("safe * /", out)
            self.assertIn("/ * trailing", out)
            self.assertNotIn("*/\n   * } part def Injected", out)
        finally:
            os.unlink(bof.name)

    def test_generates_output_file(self):
        """Configurator writes to --output path."""
        with tempfile.NamedTemporaryFile(suffix=".sysml", delete=False) as f:
            out_path = f.name
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--output", out_path]
            )
            with open(out_path) as f:
                content = f.read()
            self.assertIn("ExampleLinuxSCOREVariant", content)
            self.assertIn(":>> vehicleApplication = vehicleApplication::autoware", content)
        finally:
            os.unlink(out_path)

    def test_provenance_paths_are_repository_relative(self):
        """Generated provenance is stable when invoked outside the repository."""
        with tempfile.TemporaryDirectory() as cwd:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                cwd=cwd,
            )
        self.assertIn(
            "Regenerate from: model-based-product-line-engineering/"
            "feature-configurations/example-linux-score-autoware.yaml",
            out,
        )
        self.assertNotIn(str(REPO_ROOT), out)

    def test_external_shared_model_has_no_false_git_baseline(self):
        """External shared assets use their content hash, not repository HEAD."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sysml", delete=False
        ) as shared:
            shared.write(SHARED_MODEL.read_text())
        try:
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--shared-assets-model", shared.name],
            )
            self.assertIn(f"Shared-assets source baseline: external:{shared.name}", out)
            self.assertIn("content hash authoritative", out)
            self.assertNotIn("source baseline: git:", out)
        finally:
            os.unlink(shared.name)

    def test_provenance_paths_escape_comment_delimiters(self):
        """Untrusted external paths cannot terminate generated comments."""
        with tempfile.TemporaryDirectory() as tmp:
            hostile_dir = Path(tmp) / "source*"
            hostile_dir.mkdir()
            shared = hostile_dir / "stack.sysml"
            shared.write_text(SHARED_MODEL.read_text())
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml",
                extra_args=["--shared-assets-model", str(shared)],
            )
            self.assertIn("source* /stack.sysml", out)
            self.assertNotIn(f"external:{shared}", out)

    def test_dirty_shared_model_provenance_is_content_addressed(self):
        """Modified shared assets are identified by bytes, not repository history."""
        original = SHARED_MODEL.read_bytes()
        dirty = original + b"\n"
        try:
            SHARED_MODEL.write_bytes(dirty)
            rc, out, err = self.run_config(
                BOF_DIR / "example-linux-score-autoware.yaml"
            )
            blob_id = subprocess.check_output(
                ["git", "-C", str(REPO_ROOT), "hash-object", "--stdin"],
                input=dirty,
            ).decode().strip()
            self.assertIn(
                f"Shared-assets source baseline: git-blob:{blob_id}:", out
            )
            self.assertIn("(content-addressed)", out)
            self.assertNotIn("(exact)", out)
        finally:
            SHARED_MODEL.write_bytes(original)

    def test_generated_doc_contains_metadata(self):
        """Generated file contains provenance metadata."""
        rc, out, err = self.run_config(
            BOF_DIR / "example-linux-score-autoware.yaml"
        )
        self.assertIn("DO NOT EDIT", out)
        self.assertIn("configure_variant.py", out)
        self.assertIn("feature-models", out)

    def test_generated_doc_contains_capability_annotations(self):
        """Generated file lists capability selections."""
        rc, out, err = self.run_config(
            BOF_DIR / "example-linux-score-autoware.yaml"
        )
        self.assertIn("Feature selections outside this projection (not resolved in SysML):", out)
        self.assertIn("PedestrianDetection = disabled", out)
        self.assertIn("BicycleDetection = disabled", out)

    # ── Constraint coverage ────────────────────────────────

    def test_constraint_c004_acrn_excludes_qnx(self):
        """C004: ACRN + QNX should be rejected."""
        bof = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        bof.write("""
name: TestACRNQNX
description: ACRN + QNX violates C004
selections:
  PlatformStack.VehicleApplication: Autoware
  PlatformStack.Middleware: AUTOSARAdaptive
  PlatformStack.OS: QNX
  PlatformStack.Hypervisor: ACRN
  Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS: true
  Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  Capabilities.ForwardCollisionMitigation.BicycleDetection: false
  Capabilities.AdaptiveCruiseControl: false
  Capabilities.LaneKeepAssist: false
  SensingBoundary.PerceptionSensors: [LiDAR]
""")
        bof.close()
        try:
            rc, out, err = self.run_config(
                bof.name, extra_args=["--check-only"], expect_fail=True
            )
            self.assertIn("C004", err)
        finally:
            os.unlink(bof.name)

    def test_constraint_c002_android_sdv_on_linux(self):
        """C002: AndroidSDV + Linux should pass."""
        bof = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        bof.write("""
name: TestAndroidSDVLinux
description: Android SDV + Linux — valid per C002
selections:
  PlatformStack.VehicleApplication: Apollo
  PlatformStack.Middleware: AndroidSDV
  PlatformStack.OS: Linux
  PlatformStack.Hypervisor: None
  Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS: true
  Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  Capabilities.ForwardCollisionMitigation.BicycleDetection: false
  Capabilities.AdaptiveCruiseControl: false
  Capabilities.LaneKeepAssist: false
  SensingBoundary.PerceptionSensors: [LiDAR]
""")
        bof.close()
        try:
            rc, out, err = self.run_config(
                bof.name, extra_args=["--check-only"]
            )
            self.assertIn("Configuration valid", err)
        finally:
            os.unlink(bof.name)


if __name__ == "__main__":
    unittest.main()
