"""Native scan identity must survive the scan, not only match its first look."""
import subprocess

import pytest

from test_parent_sbom import fixture


def generate(root, env):
    return subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)


def assert_unpublished(root):
    assert not (root / "sbom/inventory.json").exists(), "a rejected scan must not publish an inventory"
    assert not list((root / "sbom").glob("*.cdx.json.gz")), "neither inventory may be replaced by a rejected scan"


def test_image_identity_change_during_scan_publishes_no_inventory(tmp_path):
    root, env = fixture(tmp_path)
    env["CHANGE_NATIVE_ID"] = "1"
    result = generate(root, env)
    assert result.returncode == 1
    assert_unpublished(root)
    assert "native image binding changed during the scan" in result.stdout


@pytest.mark.parametrize("field,value", [("SCANNER_ARCH", "arm64"), ("SCANNER_OS", "freebsd")])
def test_scanner_platform_must_match_the_native_image(tmp_path, field, value):
    root, env = fixture(tmp_path)
    env[field] = value
    result = generate(root, env)
    assert result.returncode == 1, "a different scanner platform must be rejected even with a matching image ID"
    assert_unpublished(root)
    assert "scanner platform differs from the inspected image" in result.stdout


def test_scanner_requested_reference_must_match_the_locked_reference(tmp_path):
    root, env = fixture(tmp_path)
    env["WRONG_USER_INPUT"] = "registry.example:5000/other@sha256:" + "c" * 64
    result = generate(root, env)
    assert result.returncode == 1, "a different requested reference must not be accepted as the locked input"
    assert_unpublished(root)
    assert "scanner source does not identify the requested image" in result.stdout
