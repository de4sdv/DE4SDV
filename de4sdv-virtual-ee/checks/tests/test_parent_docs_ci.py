"""Publication claims and CI wiring must not regress to the reviewed overclaims."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EE = ROOT / "de4sdv-virtual-ee"


def test_licence_record_does_not_claim_blanket_image_clearance():
    text = (EE / "versions.md").read_text().lower()
    for claim in (
        "the stack now carries no copyleft",
        "nothing blocks it on licence grounds",
        "with attribution and nothing else",
        "free of copyleft in code de4sdv writes",
        "the only component that was",
    ):
        assert claim not in text, f"unsupported distribution claim: {claim}"


def test_index_records_historical_transport_without_licence_clearance():
    text = (ROOT / "UPSTREAM.md").read_text()
    row = next(line for line in text.splitlines() if "[cannelloni]" in line)
    assert "so the stack carries no copyleft" not in row
    assert "initial" in row.lower() or "first pass" in row.lower()


def test_current_docs_do_not_repeat_the_reviewed_overclaims():
    forbidden = {
        "README.md": ["should not carry copyleft to move bytes", "lab fixture on loopback with no auth"],
        "REPORT.md": ["no copyleft in code de4sdv writes or links", "every number here has a sample count and an archive behind it", "no ethernet backbone, no some/ip", "loopback registry without authentication"],
    }
    for path, claims in forbidden.items():
        text = " ".join((EE / path).read_text().lower().split())
        for claim in claims:
            assert claim not in text, f"{path}: unsupported current-state claim: {claim}"


def test_offline_instructions_declare_their_existing_test_dependencies():
    requirements = (EE / "checks/requirements-dev.txt").read_text().lower().splitlines()
    assert any(line.startswith("pytest") for line in requirements), "standalone test instructions need pytest"
    assert any(line.startswith("pyyaml") for line in requirements), "inventory and matrix checks need PyYAML"


def test_virtual_ee_is_registered_in_the_isolated_ci_runner():
    path = ROOT / "tools/run_bench_unit_tests.py"
    spec = importlib.util.spec_from_file_location("parent_ci_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert any("de4sdv-virtual-ee/checks/tests" in suite["tests"] for suite in module.SUITES)
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "-r de4sdv-virtual-ee/checks/requirements-dev.txt" in ci
