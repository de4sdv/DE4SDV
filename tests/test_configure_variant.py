"""
Tests for the DE4SDV PLE configurator (tools/configure_variant.py).

Tests cover:
  - Valid configurations pass validation and generate correct SysML v2
  - Invalid configurations are rejected with clear error messages
  - Feature tree parsing and path resolution
  - Constraint evaluation (requires, excludes, in, ==, !=)
  - Generation output correctness
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "tools" / "configure_variant.py"
FM = REPO_ROOT / "model-based-product-line-engineering" / "feature-models" / "sdv_product_line.yaml"
BOF_DIR = REPO_ROOT / "model-based-product-line-engineering" / "feature-configurations"


class TestConfigureVariant(unittest.TestCase):

    def run_config(self, bof_path, extra_args=None, expect_fail=False):
        """Run the configurator and return (returncode, stdout, stderr)."""
        cmd = [
            sys.executable, str(SCRIPT),
            "--feature-model", str(FM),
            "--bof", str(bof_path),
        ]
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
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
""")
        bof.close()
        try:
            rc, out, err = self.run_config(
                bof.name, extra_args=["--check-only"], expect_fail=True
            )
            self.assertIn("not a valid choice", err)
        finally:
            os.unlink(bof.name)

    # ── Generation ─────────────────────────────────────────

    def test_generates_sysml_output(self):
        """Configurator generates valid SysML v2 part def."""
        rc, out, err = self.run_config(
            BOF_DIR / "example-linux-score-autoware.yaml"
        )
        self.assertIn("part def ExampleLinuxSCOREVariant :> SDVPlatformStack", out)
        self.assertIn("part :>> vehicleApplication = vehicleApplication::autoware;", out)
        self.assertIn("part :>> middleware = middleware::eclipseSCORE;", out)
        self.assertIn("part :>> osPlatform = osPlatform::linux;", out)
        self.assertIn("part :>> hypervisor = hypervisor::none;", out)

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
