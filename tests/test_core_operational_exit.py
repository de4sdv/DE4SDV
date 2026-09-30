"""Core operational-exit package — receipt validation and orchestration (D exit).

Covers the reusable pieces added for the Method Core operational-exit evidence
package:

- trusted exact-revision ingestion artifact receipts are validated locally
  (digest, count, identity discipline); abbreviated / moving / divergent
  revisions are refused with no "latest" fallback;
- battery receipts from the four fresh-process parity modes are validated
  cross-mode (one canonical evaluation key, reproduction, refusal matrix);
- scope is classified truthfully (historical vs current-exact-revision);
- a separately bound independent-review record is either accepted as a
  bound external record or reported missing — MC-30 agreement is never
  claimed by this package itself.

Synthetic fixtures only; no real model files or network access.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from de4sdv.semantic import operational_exit as oe

REV = "0a" + "2" * 38
OTHER_REV = "b" * 40
HEAD_REV = "c" * 40
KEY = "7" * 64
PAYLOAD_DIGEST = "f" * 64


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_dir(tmp_path: Path, **overrides: object) -> Path:
    rev = str(overrides.get("rev", REV))
    export: dict = {"elements": [{"@id": "e1", "@type": "PartUsage"}]}
    if overrides.get("export_rev", rev) is not None:
        export["git_commit"] = overrides.get("export_rev", rev)
    export_path = _write(tmp_path / "de4sdv-candidate-export.json", export)
    binding = {
        "git_commit": overrides.get("binding_rev", rev),
        "git_repository": "de4sdv/DE4SDV",
        "scope": "candidate",
        "semantic_validation": overrides.get("semantic_validation", "passed"),
        "sysml_project_id": "proj-1",
        "sysml_commit_id": "commit-1",
    }
    _write(tmp_path / "de4sdv-candidate-binding.json", binding)
    identity = {
        "schema": overrides.get(
            "identity_schema", "de4sdv-candidate-export-identity/v1"
        ),
        "export_sha256": overrides.get(
            "identity_export_sha", _sha256_file(export_path)
        ),
        "element_count": overrides.get("element_count", 1),
        "git_commit": overrides.get("identity_rev", rev),
        "source_checkout_head": overrides.get("source_checkout_head", rev),
        "transaction_id": "t-1",
        "transaction_label": "candidate-1",
    }
    _write(tmp_path / "de4sdv-candidate-export-identity.json", identity)
    return tmp_path


# ---------------------------------------------------------------------------
# Ingestion artifact receipts
# ---------------------------------------------------------------------------


def test_ingestion_artifacts_valid(tmp_path: Path) -> None:
    receipt = oe.validate_ingestion_artifacts(_artifact_dir(tmp_path))
    assert receipt.git_commit == REV
    assert receipt.scope == "candidate"
    assert receipt.element_count == 1
    payload = receipt.as_payload()
    assert payload["export_sha256"] == receipt.export_sha256
    assert payload["binding_sha256"] == receipt.binding_sha256
    assert payload["identity_sha256"] == receipt.identity_sha256


@pytest.mark.parametrize(
    "overrides",
    [
        {"identity_export_sha": "0" * 64},  # export bytes do not match identity
        {"semantic_validation": "failed"},  # binding not validated
        {"binding_rev": "0a23902"},  # abbreviated revision
        {"binding_rev": "main"},  # moving ref
        {"binding_rev": OTHER_REV},  # binding/identity divergence
        {"identity_rev": OTHER_REV},  # identity/binding divergence
        {"export_rev": OTHER_REV},  # export/binding divergence
        {"element_count": 99},  # count mismatch
        {"identity_schema": "other/v9"},  # unknown identity schema
    ],
)
def test_ingestion_artifact_refusals(tmp_path: Path, overrides: dict) -> None:
    with pytest.raises(oe.OperationalExitRefusal) as excinfo:
        oe.validate_ingestion_artifacts(_artifact_dir(tmp_path, **overrides))
    assert excinfo.value.reasons


def test_ingestion_artifact_missing_file_refused(tmp_path: Path) -> None:
    _artifact_dir(tmp_path)
    (tmp_path / "de4sdv-candidate-export-identity.json").unlink()
    with pytest.raises(oe.OperationalExitRefusal) as excinfo:
        oe.validate_ingestion_artifacts(tmp_path)
    assert any("identity" in reason for reason in excinfo.value.reasons)


# ---------------------------------------------------------------------------
# Battery receipts
# ---------------------------------------------------------------------------


def _execution(
    tmp_path: Path, mode: str, report: dict, exit_code: int = 0
) -> oe.ModeExecution:
    path = _write(tmp_path / f"{mode}-report.json", report)
    return oe.ModeExecution(
        mode=mode,
        command=("python3", "scripts/run_snapshot_parity.py", mode),
        exit_code=exit_code,
        wall_seconds=0.25,
        report_path=path,
        report_sha256=_sha256_file(path),
        report=report,
    )


def _snapshot(tmp_path: Path) -> Path:
    return _write(tmp_path / "snapshot.json", {"snapshot": "payload"})


def _tamper_cases() -> list[dict]:
    names = (
        "pristine-control", "tampered-element-payload", "tampered-file-blob",
        "self-attested-provenance", "wrong-method-digest", "corrupt-payload-digest",
        "wrong-tested-head", "element-mutation-reforged", "candidate-file-mutation-reforged",
        "tested-file-mutation-reforged", "missing-trusted-record", "wrong-git-revision-trusted",
    )
    return [
        {"case": name, "expected": "accepted" if name == "pristine-control" else "refused",
         "result": "accepted" if name == "pristine-control" else "refused", "expected_met": True}
        for name in names
    ]


def _valid_executions(tmp_path: Path) -> dict[str, oe.ModeExecution]:
    snapshot = _snapshot(tmp_path)
    build = {
        "mode": "build",
        "status": "built",
        "declared_evaluation_key": KEY,
        "snapshot": {"sha256": _sha256_file(snapshot)},
    }
    verify = {
        "mode": "verify",
        "status": "identical",
        "identical": True,
        "reproduced_declared_key": True,
        "declared_evaluation_key": KEY,
        "api_transport": {"evaluation_key": KEY},
        "snapshot_transport": {"evaluation_key": KEY, "payload_digest": PAYLOAD_DIGEST},
    }
    offline = {
        "mode": "offline",
        "status": "reproduced",
        "reproduced": True,
        "evaluation_key": KEY,
        "declared_evaluation_key": KEY,
        "payload_digest": PAYLOAD_DIGEST,
    }
    tamper = {
        "mode": "tamper",
        "status": "refusal-matrix-ok",
        "all_expected_outcomes_met": True,
        "cases": _tamper_cases(),
    }
    return {
        "build": _execution(tmp_path, "build", build),
        "verify": _execution(tmp_path, "verify", verify),
        "offline": _execution(tmp_path, "offline", offline),
        "tamper": _execution(tmp_path, "tamper", tamper),
    }


def test_battery_receipts_pass(tmp_path: Path) -> None:
    verdict = oe.validate_battery_receipts(
        _valid_executions(tmp_path), snapshot_path=tmp_path / "snapshot.json"
    )
    assert verdict["all_passed"] is True
    assert verdict["refusals"] == []
    assert verdict["evaluation_key"] == KEY


@pytest.mark.parametrize(
    "mutate,expected_fragment",
    [
        (lambda e: e["verify"].report.update({"identical": False}), "verify"),
        (
            lambda e: e["verify"].report["api_transport"].update({"evaluation_key": "x" * 64}),
            "evaluation key",
        ),
        (lambda e: e["offline"].report.update({"reproduced": False}), "offline"),
        (
            lambda e: e["offline"].report.update({"evaluation_key": "y" * 64}),
            "evaluation key",
        ),
        (
            lambda e: e["tamper"].report.update({"all_expected_outcomes_met": False}),
            "tamper",
        ),
        (lambda e: e["build"].report.update({"status": "refused-input"}), "build"),
        (
            lambda e: e["build"].report["snapshot"].update({"sha256": "0" * 64}),
            "snapshot",
        ),
    ],
)
def test_battery_receipt_refusals(
    tmp_path: Path, mutate, expected_fragment: str
) -> None:
    executions = _valid_executions(tmp_path)
    mutate(executions)
    verdict = oe.validate_battery_receipts(
        executions, snapshot_path=tmp_path / "snapshot.json"
    )
    assert verdict["all_passed"] is False
    assert any(expected_fragment in reason for reason in verdict["refusals"])


def test_battery_nonzero_exit_refused(tmp_path: Path) -> None:
    executions = _valid_executions(tmp_path)
    executions["offline"] = _execution(
        tmp_path, "offline", executions["offline"].report, exit_code=2
    )
    verdict = oe.validate_battery_receipts(
        executions, snapshot_path=tmp_path / "snapshot.json"
    )
    assert verdict["all_passed"] is False
    assert any("exit" in reason for reason in verdict["refusals"])


# ---------------------------------------------------------------------------
# Scope classification
# ---------------------------------------------------------------------------


def test_scope_current_exact_revision() -> None:
    scope = oe.classify_scope(
        artifact_git_commit=REV, repo_head=REV, expected_revision=REV
    )
    assert scope.mode == "current-exact-revision"
    assert scope.historical is False
    assert scope.current_exact_revision_verified is True


def test_scope_historical_when_head_differs() -> None:
    scope = oe.classify_scope(artifact_git_commit=REV, repo_head=HEAD_REV)
    assert scope.mode == "historical"
    assert scope.historical is True
    assert scope.current_exact_revision_verified is False
    assert any(REV in reason for reason in scope.reasons)
    assert any(HEAD_REV in reason for reason in scope.reasons)
    assert "not" in scope.claim_boundary.lower()


def test_scope_expected_revision_mismatch_refused() -> None:
    scope = oe.classify_scope(
        artifact_git_commit=REV, repo_head=REV, expected_revision=OTHER_REV
    )
    assert scope.mode == "refused-expectation-mismatch"
    assert scope.historical is False
    assert scope.current_exact_revision_verified is False
    assert any(OTHER_REV in reason for reason in scope.reasons)


# ---------------------------------------------------------------------------
# Independent review binding (MC-30): never self-claimed
# ---------------------------------------------------------------------------


def test_independent_review_missing_reported_not_claimed() -> None:
    review = oe.bind_independent_review(
        record_path=None, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    assert review["status"] == "missing"
    assert review["acceptance"] == "not-established"
    assert review["reasons"]


def test_independent_review_bound_agreement(tmp_path: Path) -> None:
    record = _write(
        tmp_path / "review.json",
        {
            "parity": "agreed",
            "evaluation_key": KEY,
            "git_commit": REV,
            "contract_digest": "d" * 64,
            "source": "independent manual pilot review",
        },
    )
    review = oe.bind_independent_review(
        record_path=record, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    assert review["status"] == "bound-agreement"
    assert review["acceptance"] == "record-bound"
    assert review["agreement_source"] == "external-independent-review-record"


@pytest.mark.parametrize(
    "overrides,expected_status",
    [
        ({"parity": "partial"}, "partial"),
        ({"parity": "timeout"}, "timeout"),
        ({"parity": "disagreed"}, "disagreed"),
    ],
)
def test_independent_review_non_agreement_not_acceptance(
    tmp_path: Path, overrides: dict, expected_status: str
) -> None:
    record = _write(
        tmp_path / "review.json",
        {
            "parity": "agreed",
            "evaluation_key": KEY,
            "git_commit": REV,
            "contract_digest": "d" * 64,
            **overrides,
        },
    )
    review = oe.bind_independent_review(
        record_path=record, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    assert review["status"] == expected_status
    assert review["acceptance"] == "not-established"


@pytest.mark.parametrize(
    "overrides",
    [
        {"evaluation_key": "0" * 64},
        {"git_commit": OTHER_REV},
        {"contract_digest": "0" * 64},
        {"parity": "probably"},
    ],
)
def test_independent_review_mismatch_refused(tmp_path: Path, overrides: dict) -> None:
    record = _write(
        tmp_path / "review.json",
        {
            "parity": "agreed",
            "evaluation_key": KEY,
            "git_commit": REV,
            "contract_digest": "d" * 64,
            **overrides,
        },
    )
    review = oe.bind_independent_review(
        record_path=record, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    assert review["status"] == "refused"
    assert review["acceptance"] == "not-established"
    assert review["reasons"]


# ---------------------------------------------------------------------------
# Orchestration: fresh-process battery wiring
# ---------------------------------------------------------------------------


def test_run_battery_with_injected_runner(tmp_path: Path) -> None:
    artifacts_dir = _artifact_dir(tmp_path / "artifacts")
    artifacts = oe.validate_ingestion_artifacts(artifacts_dir)
    out_dir = tmp_path / "out"
    calls: list[tuple[str, ...]] = []

    def fake_runner(command, cwd, log_path):
        calls.append(tuple(command))
        mode = command[2]
        out = Path(command[command.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        if mode == "build":
            snapshot = _write(out / "snapshot.json", {"snapshot": "payload"})
            _write(
                out / "report.json",
                {
                    "mode": "build",
                    "status": "built",
                    "declared_evaluation_key": KEY,
                    "snapshot": {"sha256": _sha256_file(snapshot)},
                },
            )
        elif mode == "verify":
            _write(
                out / "parity-report.json",
                {
                    "mode": "verify",
                    "status": "identical",
                    "identical": True,
                    "reproduced_declared_key": True,
                    "declared_evaluation_key": KEY,
                    "api_transport": {"evaluation_key": KEY},
                    "snapshot_transport": {
                        "evaluation_key": KEY,
                        "payload_digest": PAYLOAD_DIGEST,
                    },
                },
            )
        elif mode == "offline":
            _write(
                out / "offline-report.json",
                {
                    "mode": "offline",
                    "status": "reproduced",
                    "reproduced": True,
                    "evaluation_key": KEY,
                    "declared_evaluation_key": KEY,
                    "payload_digest": PAYLOAD_DIGEST,
                },
            )
        else:
            _write(
                out / "tamper-report.json",
                {
                    "mode": "tamper",
                    "status": "refusal-matrix-ok",
                    "all_expected_outcomes_met": True,
                    "cases": _tamper_cases(),
                },
            )
        return 0, 0.01

    battery = oe.run_battery(
        script=Path("scripts/run_snapshot_parity.py"),
        repo=tmp_path,
        artifacts=artifacts,
        out_dir=out_dir,
        spec=None,
        validation_run="123",
        artifact_label="full-model-api-ingestion-" + REV,
        runner=fake_runner,
    )
    assert [call[2] for call in calls] == ["build", "verify", "offline", "tamper"]
    assert battery.verdict["all_passed"] is True
    assert set(battery.executions) == {"build", "verify", "offline", "tamper"}
    # The verify command must consume the built snapshot and retained export.
    verify_call = calls[1]
    assert str(out_dir / "build" / "snapshot.json") in verify_call
    assert "--candidate-export" in verify_call
    # The offline command must not receive any repository argument.
    assert "--repo" not in calls[2]


def test_run_battery_refusal_when_mode_fails(tmp_path: Path) -> None:
    artifacts_dir = _artifact_dir(tmp_path / "artifacts")
    artifacts = oe.validate_ingestion_artifacts(artifacts_dir)
    out_dir = tmp_path / "out"

    def failing_runner(command, cwd, log_path):
        mode = command[2]
        out = Path(command[command.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        if mode == "build":
            snapshot = _write(out / "snapshot.json", {"snapshot": "payload"})
            _write(
                out / "report.json",
                {
                    "mode": "build",
                    "status": "built",
                    "declared_evaluation_key": KEY,
                    "snapshot": {"sha256": _sha256_file(snapshot)},
                },
            )
        if mode == "tamper":
            return 2, 0.02
        return 0, 0.01

    battery = oe.run_battery(
        script=Path("scripts/run_snapshot_parity.py"),
        repo=tmp_path,
        artifacts=artifacts,
        out_dir=out_dir,
        spec=None,
        validation_run="123",
        artifact_label="label",
        runner=failing_runner,
    )
    assert battery.verdict["all_passed"] is False
    assert any("tamper" in reason for reason in battery.verdict["refusals"])


def test_default_runner_executes_fresh_process(tmp_path: Path) -> None:
    exit_code, wall_seconds = oe.default_process_runner(
        [sys.executable, "-c", "print('fresh-process-ok')"],
        cwd=tmp_path,
        log_path=tmp_path / "fresh.log",
    )
    assert exit_code == 0
    assert wall_seconds >= 0.0
    assert "fresh-process-ok" in (tmp_path / "fresh.log").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Receipt composition
# ---------------------------------------------------------------------------


def test_build_receipt_truthful_scope(tmp_path: Path) -> None:
    artifacts_dir = _artifact_dir(tmp_path / "artifacts")
    artifacts = oe.validate_ingestion_artifacts(artifacts_dir)
    executions = _valid_executions(tmp_path)
    verdict = oe.validate_battery_receipts(
        executions, snapshot_path=tmp_path / "snapshot.json"
    )
    scope = oe.classify_scope(artifact_git_commit=REV, repo_head=HEAD_REV)
    review = oe.bind_independent_review(
        record_path=None, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    receipt = oe.build_receipt(
        artifacts=artifacts,
        battery_executions=executions,
        verdict=verdict,
        scope=scope,
        independent_review=review,
        validation_run="34576049742",
        artifact_label="full-model-api-ingestion-" + REV,
        environment={"host": "test"},
    )
    assert receipt["schema"] == oe.RECEIPT_SCHEMA
    assert receipt["scope"]["mode"] == "historical"
    assert receipt["scope"]["current_exact_revision_verified"] is False
    assert receipt["independent_review"]["status"] == "missing"
    assert receipt["method_decision"]["status"] == "evidence-produced"
    assert receipt["measurements"]["evaluation_key"] == KEY
    assert receipt["claim_boundary"]
    # No secret-looking fields and no self-attested trust.
    assert receipt["ingestion_artifacts"]["git_commit"] == REV


def test_build_receipt_refused_verdict(tmp_path: Path) -> None:
    artifacts_dir = _artifact_dir(tmp_path / "artifacts")
    artifacts = oe.validate_ingestion_artifacts(artifacts_dir)
    executions = _valid_executions(tmp_path)
    executions["verify"].report.update({"identical": False})
    verdict = oe.validate_battery_receipts(
        executions, snapshot_path=tmp_path / "snapshot.json"
    )
    scope = oe.classify_scope(artifact_git_commit=REV, repo_head=REV)
    review = oe.bind_independent_review(
        record_path=None, evaluation_key=KEY, git_commit=REV, contract_digest="d" * 64
    )
    receipt = oe.build_receipt(
        artifacts=artifacts,
        battery_executions=executions,
        verdict=verdict,
        scope=scope,
        independent_review=review,
        validation_run="34576049742",
        artifact_label="label",
        environment={},
    )
    assert receipt["method_decision"]["status"] == "refused"
    assert receipt["refusals"]


def test_tamper_empty_matrix_cannot_pass(tmp_path: Path) -> None:
    executions = _valid_executions(tmp_path)
    executions["tamper"].report["cases"] = []
    verdict = oe.validate_battery_receipts(executions, snapshot_path=tmp_path / "snapshot.json")
    assert verdict["all_passed"] is False
    assert any("tamper" in reason for reason in verdict["refusals"])


def test_cli_refuses_missing_artifact_without_running_modes(tmp_path: Path) -> None:
    import subprocess

    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "result"
    process = subprocess.run(
        [sys.executable, str(root / "scripts/run_core_operational_exit.py"),
         "--repo", str(root), "--artifacts", str(tmp_path / "missing"),
         "--validation-run", "123", "--out", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert process.returncode == 2
    receipt = json.loads((output / "receipt.json").read_text())
    assert receipt["status"] == "refused-input"
    assert not (output / "build").exists()


def test_intended_runner_workflow_has_exact_artifact_origin_guards() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/method-core-operational-evidence.yml").read_text())
    job = workflow["jobs"]["observe"]
    assert job["runs-on"] == "ubuntu-latest"
    text = "\n".join(step.get("run", "") for step in job["steps"])
    assert "merge-base" in text and "origin/main" in text
    assert "head_sha" in text and "conclusion" in text and "workflow_id" in text
    assert "--expected-revision" in text
    assert "--allow-historical" not in text
    assert "run_delivery_gate.py" in text


@pytest.mark.parametrize("field", ["parity", "source"])
def test_review_malformed_values_refuse_without_crashing(tmp_path: Path, field: str) -> None:
    record = _write(tmp_path / "review.json", {
        "parity": "agreed", "source": "independent manual review",
        "evaluation_key": KEY, "git_commit": REV, "contract_digest": "d" * 64,
        field: [],
    })
    result = oe.bind_independent_review(record_path=record, evaluation_key=KEY,
                                       git_commit=REV, contract_digest="d" * 64)
    assert result["status"] == "refused"


@pytest.mark.parametrize("field", ["snapshot", "api_transport", "snapshot_transport"])
def test_battery_malformed_nested_report_refused(tmp_path: Path, field: str) -> None:
    executions = _valid_executions(tmp_path)
    mode = "build" if field == "snapshot" else "verify"
    report = dict(executions[mode].report)
    report[field] = []
    executions[mode] = _execution(tmp_path, mode, report)
    verdict = oe.validate_battery_receipts(executions, snapshot_path=tmp_path / "snapshot.json")
    assert verdict["all_passed"] is False


def test_duplicate_json_keys_refused(tmp_path: Path) -> None:
    directory = _artifact_dir(tmp_path)
    path = directory / "de4sdv-candidate-binding.json"
    original = path.read_text()
    path.write_text('{"semantic_validation": "failed",' + original[1:])
    with pytest.raises(oe.OperationalExitRefusal):
        oe.validate_ingestion_artifacts(directory)


def _cli_with_separate_model_checkout(tmp_path: Path, monkeypatch):
    import importlib.util
    import subprocess

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "core_provenance_cli", root / "scripts/run_core_operational_exit.py"
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    actual_git = subprocess.check_output
    executor_head = actual_git(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    assert executor_head != REV
    model_repo = tmp_path / "synthetic-model-checkout"
    model_repo.mkdir()
    artifacts = _artifact_dir(tmp_path / "artifacts")
    reports = tmp_path / "synthetic-reports"
    executions = _valid_executions(reports)
    verdict = oe.validate_battery_receipts(
        executions, snapshot_path=reports / "snapshot.json"
    )
    monkeypatch.setattr(
        cli.oe, "run_battery",
        lambda **kwargs: oe.Battery(executions=executions, verdict=verdict),
    )

    def git_output(command, **kwargs):
        if command[:3] == ["git", "-C", str(model_repo)]:
            assert command[3:] == ["rev-parse", "HEAD"]
            return REV + "\n"
        return actual_git(command, **kwargs)

    monkeypatch.setattr(cli.subprocess, "check_output", git_output)
    output = tmp_path / "result"
    monkeypatch.setattr(sys, "argv", [
        "run_core_operational_exit.py", "--repo", str(model_repo),
        "--artifacts", str(artifacts), "--validation-run", "123",
        "--allow-historical", "--out", str(output),
    ])
    assert cli.main() == 0
    receipt = json.loads((output / "receipt.json").read_text())
    return receipt, executor_head


def test_cli_executor_head_describes_running_script_checkout(tmp_path, monkeypatch):
    receipt, executor_head = _cli_with_separate_model_checkout(tmp_path, monkeypatch)
    assert receipt["environment"]["executor_git_head"] == executor_head
    assert receipt["environment"]["model_repo_git_head"] == REV


def test_cli_different_executor_revision_is_never_current(tmp_path, monkeypatch):
    receipt, executor_head = _cli_with_separate_model_checkout(tmp_path, monkeypatch)
    assert receipt["scope"]["historical"] is True
    assert receipt["scope"]["current_exact_revision_verified"] is False
    assert any(executor_head in reason for reason in receipt["scope"]["reasons"])
    assert receipt["method_decision"]["core_accepted"] is False
