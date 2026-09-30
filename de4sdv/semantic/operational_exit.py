"""Read-only orchestration of the existing Method Core snapshot evidence runners.

Receipts establish input consistency and observed process outcomes, not trusted
artifact origin, independent reviewer authority, product acceptance, or cutover.
The calling workflow retains the provider-side artifact/run provenance separately.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable

from de4sdv.semantic import method_pilot as mp

RECEIPT_SCHEMA = "de4sdv.method-core-operational-receipt/v1"
MODES = ("build", "verify", "offline", "tamper")
REPORT_NAMES = {"build": "report.json", "verify": "parity-report.json",
                "offline": "offline-report.json", "tamper": "tamper-report.json"}
TAMPER_CASES = frozenset((
    "pristine-control", "tampered-element-payload", "tampered-file-blob",
    "self-attested-provenance", "wrong-method-digest", "corrupt-payload-digest",
    "wrong-tested-head", "element-mutation-reforged", "candidate-file-mutation-reforged",
    "tested-file-mutation-reforged", "missing-trusted-record", "wrong-git-revision-trusted",
))
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class OperationalExitRefusal(ValueError):
    def __init__(self, reasons: list[str]):
        self.reasons = tuple(reasons)
        super().__init__("; ".join(reasons))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError, RecursionError) as error:
        raise OperationalExitRefusal([f"cannot read {path.name}: {error}"]) from error
    if not isinstance(payload, dict):
        raise OperationalExitRefusal([f"{path.name} must contain a JSON object"])
    return payload


@dataclass(frozen=True)
class IngestionArtifacts:
    directory: Path
    git_commit: str
    scope: str
    element_count: int
    export_sha256: str
    binding_sha256: str
    identity_sha256: str
    sysml_project_id: str
    sysml_commit_id: str

    def as_payload(self) -> dict:
        return {key: value for key, value in self.__dict__.items() if key != "directory"}


def validate_ingestion_artifacts(directory: Path) -> IngestionArtifacts:
    directory = directory.resolve()
    export_path = directory / "de4sdv-candidate-export.json"
    binding_path = directory / "de4sdv-candidate-binding.json"
    identity_path = directory / "de4sdv-candidate-export-identity.json"
    export, binding, identity_doc = map(_json, (export_path, binding_path, identity_path))
    identity, diagnostics = mp.establish_candidate_identity(binding=binding, export=export)
    reasons = list(diagnostics) if identity is None else []
    revision = binding.get("git_commit")
    if not isinstance(revision, str) or not FULL_SHA.fullmatch(revision):
        reasons.append("binding git_commit must be an exact lowercase 40-character SHA")
    if binding.get("semantic_validation") != "passed":
        reasons.append("candidate binding semantic_validation is not passed")
    if binding.get("scope") != "candidate":
        reasons.append("binding scope must be candidate")
    if identity_doc.get("schema") != "de4sdv-candidate-export-identity/v1":
        reasons.append("unknown candidate export identity schema")
    for field in ("git_commit", "source_checkout_head"):
        if identity_doc.get(field) != revision:
            reasons.append(f"identity {field} differs from binding git_commit")
    export_digest = sha256_file(export_path)
    if identity_doc.get("export_sha256") != export_digest:
        reasons.append("identity export digest does not match export bytes")
    elements = export.get("elements")
    if not isinstance(elements, list) or not elements or not all(isinstance(e, dict) for e in elements):
        reasons.append("export must carry a nonempty element-object list")
    count = len(elements) if isinstance(elements, list) else 0
    if type(identity_doc.get("element_count")) is not int or identity_doc["element_count"] != count:
        reasons.append("identity element_count does not match export")
    if reasons:
        raise OperationalExitRefusal(reasons)
    assert identity is not None
    return IngestionArtifacts(directory, identity.git_commit, identity.scope, count,
                              export_digest, sha256_file(binding_path), sha256_file(identity_path),
                              identity.sysml_project_id, identity.sysml_commit_id)


@dataclass(frozen=True)
class ModeExecution:
    mode: str
    command: tuple[str, ...]
    exit_code: int
    wall_seconds: float
    report_path: Path
    report_sha256: str
    report: dict

    def as_payload(self) -> dict:
        return {"mode": self.mode, "command": list(self.command), "exit_code": self.exit_code,
                "wall_seconds": self.wall_seconds, "report_path": str(self.report_path),
                "report_sha256": self.report_sha256,
                "performance": self.report.get("performance", {}),
                "environment": self.report.get("environment", {})}


def validate_battery_receipts(executions: dict[str, ModeExecution], *, snapshot_path: Path) -> dict:
    reasons: list[str] = []
    if set(executions) != set(MODES):
        reasons.append("battery requires exactly build, verify, offline, tamper executions")
    reports = {}
    for mode in MODES:
        execution = executions.get(mode)
        if execution is None:
            reports[mode] = {}
            continue
        report = execution.report
        reports[mode] = report
        if execution.mode != mode or report.get("mode") != mode:
            reasons.append(f"{mode}: missing or wrong mode receipt")
        if type(execution.exit_code) is not int or execution.exit_code != 0:
            reasons.append(f"{mode}: nonzero process exit {execution.exit_code}")
        try:
            if sha256_file(execution.report_path) != execution.report_sha256 or _json(execution.report_path) != report:
                reasons.append(f"{mode}: report bytes changed after process execution")
        except (OSError, OperationalExitRefusal):
            reasons.append(f"{mode}: process report unavailable")
    build, verify, offline, tamper = (reports[mode] for mode in MODES)

    def nested(report: dict, field: str) -> dict:
        value = report.get(field)
        if not isinstance(value, dict):
            reasons.append(f"{report.get('mode')}: {field} must be an object")
            return {}
        return value

    built_snapshot = nested(build, "snapshot")
    api_transport = nested(verify, "api_transport")
    snapshot_transport = nested(verify, "snapshot_transport")
    key = build.get("declared_evaluation_key")
    if not isinstance(key, str) or not DIGEST.fullmatch(key):
        reasons.append("build: missing canonical evaluation key")
    if build.get("status") != "built":
        reasons.append("build: snapshot was not built")
    try:
        if built_snapshot.get("sha256") != sha256_file(snapshot_path):
            reasons.append("build: snapshot digest differs from built bytes")
    except OSError:
        reasons.append("build: snapshot is missing")
    if verify.get("status") != "identical" or verify.get("identical") is not True or verify.get("reproduced_declared_key") is not True:
        reasons.append("verify: canonical retained-export/snapshot parity not established")
    if offline.get("status") != "reproduced" or offline.get("reproduced") is not True:
        reasons.append("offline: snapshot-only reproduction not established")
    keys = [verify.get("declared_evaluation_key"), api_transport.get("evaluation_key"),
            snapshot_transport.get("evaluation_key"), offline.get("evaluation_key"),
            offline.get("declared_evaluation_key")]
    if any(observed != key for observed in keys):
        reasons.append("verify/offline: evaluation key differs across transports")
    payload_digest = snapshot_transport.get("payload_digest")
    if not isinstance(payload_digest, str) or not DIGEST.fullmatch(payload_digest) or offline.get("payload_digest") != payload_digest:
        reasons.append("verify/offline: snapshot payload digest differs or is missing")
    cases = tamper.get("cases")
    names = [c.get("case") for c in cases if isinstance(c, dict) and isinstance(c.get("case"), str)] if isinstance(cases, list) else []
    if (tamper.get("status") != "refusal-matrix-ok" or tamper.get("all_expected_outcomes_met") is not True
            or set(names) != TAMPER_CASES or len(names) != len(TAMPER_CASES)):
        reasons.append("tamper: complete refusal matrix not established")
    if isinstance(cases, list):
        for case in cases:
            if not isinstance(case, dict):
                reasons.append("tamper: invalid case receipt")
                continue
            expected = "accepted" if case.get("case") == "pristine-control" else "refused"
            if case.get("expected") != expected or case.get("result") != expected or case.get("expected_met") is not True:
                reasons.append(f"tamper: wrong outcome for {case.get('case')}")
    return {"all_passed": not reasons, "refusals": reasons, "evaluation_key": key,
            "payload_digest": payload_digest}


@dataclass(frozen=True)
class Scope:
    mode: str
    historical: bool
    current_exact_revision_verified: bool
    reasons: tuple[str, ...]
    claim_boundary: str

    def as_payload(self) -> dict:
        return dict(self.__dict__)


def classify_scope(*, artifact_git_commit: str, repo_head: str, expected_revision: str | None = None) -> Scope:
    if (not FULL_SHA.fullmatch(artifact_git_commit) or not FULL_SHA.fullmatch(repo_head)
            or expected_revision is not None and expected_revision != artifact_git_commit):
        return Scope("refused-expectation-mismatch", False, False,
                     (f"expected {expected_revision!r}, artifact {artifact_git_commit}, checkout {repo_head}",),
                     "No current-revision evidence or acceptance established.")
    if artifact_git_commit != repo_head:
        return Scope("historical", True, False,
                     (f"retained artifact {artifact_git_commit} differs from checkout HEAD {repo_head}",),
                     "Historical artifact replay, not current-main/API closure or permanent provenance.")
    return Scope("current-exact-revision", False, True, (),
                 "Artifact revision equals compared checkout HEAD; origin trust, clean executor, permanent ancestry and acceptance are separate gates.")


def bind_independent_review(*, record_path: Path | None, evaluation_key: str,
                            git_commit: str, contract_digest: str) -> dict:
    result = {"status": "missing", "acceptance": "not-established",
              "reasons": ["No separately bound independent manual pilot review supplied."],
              "mc30_accepted": False}
    if record_path is None:
        return result
    try:
        record = _json(record_path)
        reasons = [f"review {field} mismatch" for field, value in (
            ("evaluation_key", evaluation_key), ("git_commit", git_commit), ("contract_digest", contract_digest)
        ) if record.get(field) != value]
        parity = record.get("parity")
        if not isinstance(parity, str) or parity not in {"agreed", "disagreed", "timeout", "partial", "not-run"}:
            reasons.append("unknown review parity")
        if parity == "agreed" and (not isinstance(record.get("source"), str) or not record["source"].strip()):
            reasons.append("agreement record lacks independent source")
        result.update(status="refused" if reasons else "bound-agreement" if parity == "agreed" else parity,
                      reasons=reasons, record_sha256=sha256_file(record_path))
        if not reasons and parity == "agreed":
            result.update(acceptance="record-bound", agreement_source="external-independent-review-record",
                          claim_boundary="Binding only; reviewer identity, independence, disposition and approval must be independently verified.")
    except (OperationalExitRefusal, OSError) as error:
        result.update(status="refused", reasons=[str(error)])
    return result


def default_process_runner(command: list[str], *, cwd: Path, log_path: Path) -> tuple[int, float]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as log:
        try:
            process = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=300, check=False)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            log.write("\nProcess timed out; no acceptance established.\n")
            exit_code = 124
    return exit_code, time.perf_counter() - start


@dataclass(frozen=True)
class Battery:
    executions: dict[str, ModeExecution]
    verdict: dict


def run_battery(*, script: Path, repo: Path, artifacts: IngestionArtifacts, out_dir: Path,
                spec: Path | None, validation_run: str, artifact_label: str,
                runner: Callable = default_process_runner) -> Battery:
    # A fresh output directory prevents old success receipts masking a failed process.
    out_dir = out_dir.resolve()
    if out_dir.exists():
        raise OperationalExitRefusal(["battery output directory already exists; use a fresh path"])
    build_dir = out_dir / "build"
    build_dir.mkdir(parents=True)
    export = str(artifacts.directory / "de4sdv-candidate-export.json")
    binding = str(artifacts.directory / "de4sdv-candidate-binding.json")
    snapshot = build_dir / "snapshot.json"
    common = ["--snapshot", str(snapshot)]
    trust = ["--trusted-json", str(build_dir / "trusted.json"),
             "--expectations-json", str(build_dir / "expectations.json")]
    commands = {
        "build": ["--repo", str(repo), "--candidate-export", export, "--candidate-binding", binding,
                  "--export-identity", str(artifacts.directory / "de4sdv-candidate-export-identity.json"),
                  "--validation-run", validation_run, "--artifact", artifact_label],
        "verify": ["--repo", str(repo), "--candidate-export", export, "--candidate-binding", binding, *common],
        "offline": [*common, *trust, "--spec", str(build_dir / "spec-copy.yaml")],
        "tamper": [*common, *trust],
    }
    if spec is not None:
        commands["build"] += ["--spec", str(spec)]
    executions = {}
    for mode in MODES:
        mode_dir = build_dir if mode in {"build", "verify"} else out_dir / mode
        mode_dir.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(script), mode, *commands[mode], "--out", str(mode_dir)]
        exit_code, seconds = runner(command, cwd=repo, log_path=out_dir / "logs" / f"{mode}.log")
        report_path = mode_dir / REPORT_NAMES[mode]
        try:
            report = _json(report_path)
            digest = sha256_file(report_path)
        except (OperationalExitRefusal, OSError):
            report, digest = {}, ""
        executions[mode] = ModeExecution(mode, tuple(command), exit_code, seconds, report_path, digest, report)
    return Battery(executions, validate_battery_receipts(executions, snapshot_path=snapshot))


def build_receipt(*, artifacts: IngestionArtifacts, battery_executions: dict[str, ModeExecution],
                  verdict: dict, scope: Scope, independent_review: dict, validation_run: str,
                  artifact_label: str, environment: dict) -> dict:
    passed = verdict.get("all_passed") is True and scope.mode != "refused-expectation-mismatch"
    return {"schema": RECEIPT_SCHEMA, "ingestion_artifacts": artifacts.as_payload(),
            "validation_run": validation_run, "artifact_label": artifact_label,
            "artifact_origin_trust": "not-established-by-local-receipt",
            "scope": scope.as_payload(), "environment": environment,
            "executions": {mode: run.as_payload() for mode, run in battery_executions.items()},
            "measurements": {"evaluation_key": verdict.get("evaluation_key"),
                             "per_mode": {mode: run.report.get("performance", {}) for mode, run in battery_executions.items()}},
            "independent_review": independent_review,
            "method_decision": {"status": "evidence-produced" if passed else "refused",
                                "core_accepted": False, "product_accepted": False},
            "refusals": list(verdict.get("refusals", [])) + list(scope.reasons if scope.mode == "refused-expectation-mismatch" else ()),
            "open_acceptance": ["MC-30 independent manual agreement and reviewer authority",
                                "intended-runner measurement suitability and adopted budget",
                                "exact-head real advisory delivery observation",
                                "current permanent-revision API closure where required"],
            "claim_boundary": "Retained validated-export replay versus snapshot, not live API fetch latency, reviewer approval, certification or authority activation."}
