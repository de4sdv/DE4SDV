#!/usr/bin/env python3
"""Build and verify a validated method-conformance snapshot (Lane D).

The snapshot serializes the exact semantic inputs of the deterministic
evaluator for one validated API revision. It is rebuilt from the retained
exact-run artifacts of the controlled importer chain; the trust record
(validated binding + export identity digests) travels separately from the
snapshot so a bundle can never authorize itself.

Modes
-----
build     compose the snapshot payload from the retained export + binding +
          export identity and the repository revisions it was produced from;
          declare the expected canonical evaluation key computed through the
          API transport. Writes ``snapshot.json``, ``trusted.json``,
          ``expectations.json`` and ``report.json`` into the output directory.
verify    evaluate the same verified inputs through BOTH transports (API:
          retained export + git revisions; snapshot: the snapshot file) and
          compare the canonical conformance payloads; measure timing and
          footprint; emit the conformance summary for the delivery gate.
offline   evaluate from the snapshot file alone (no repository, no export,
          no API): ``--snapshot`` + ``--trusted-json`` + ``--expectations-json``
          + ``--spec`` only; assert the declared evaluation key reproduces.
tamper    refusal matrix over mutated copies of the snapshot (never mutates
          the original).

Read-only: this script performs no repository/API/GitHub writes. Exit codes:
0 evidence produced; 2 refused (identity/trust/completeness/reproduction
failure) or expected-refusal matrix violated; 1 unexpected error.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import platform
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import delivery_gate as dg  # noqa: E402
from de4sdv.semantic import method_evaluator as me  # noqa: E402
from de4sdv.semantic import method_pilot as mp  # noqa: E402
from de4sdv.semantic import snapshot as sn  # noqa: E402

PHASE_EXIT_TARGET = me.ReadinessTarget(
    target_type="PHASE_EXIT", target_id=f"{mp.PILOT_SCOPE_RECORD}/phase10"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"refused: {path} is not a JSON object")
    return value


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def _capture_root(repo: Path, revision: str, roots: list[str]) -> dict[str, bytes]:
    """Capture every blob under the declared roots at one revision."""
    source = mp.GitRevisionFileSource(repo, revision)
    files: dict[str, bytes] = {}
    for root in roots:
        listing = source.list_files(root)
        for relative in listing or ():
            blob = source.read_bytes(relative)
            if blob is not None:
                files[relative] = blob
    return files


def _conformance_summary(evaluation: me.CanonicalEvaluation) -> dict:
    summary = dg.ConformanceSummary.from_canonical(evaluation)
    payload = summary.as_payload()
    payload.update(
        {
            "required_units": list(summary.required_units),
            "failed_ids": list(summary.failed_ids),
            "indeterminate_ids": list(summary.indeterminate_ids),
            "errored_ids": list(summary.errored_ids),
            "unassessed_ids": list(summary.unassessed_ids),
        }
    )
    return payload


def _canonical_projection(evaluation: me.CanonicalEvaluation) -> dict:
    return {
        "evaluation_key": evaluation.evaluation_key,
        "increment_status": evaluation.increment_status(),
        "readiness": [block.as_dict() for block in evaluation.readiness],
    }


def _first_difference(left, right, path: str = "$"):
    if type(left) is not type(right):
        return f"{path}: type {type(left).__name__} != {type(right).__name__}"
    if isinstance(left, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left:
                return f"{path}.{key}: missing on the API side"
            if key not in right:
                return f"{path}.{key}: missing on the snapshot side"
            found = _first_difference(left[key], right[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(left, list):
        if len(left) != len(right):
            return f"{path}: length {len(left)} != {len(right)}"
        for index, (a, b) in enumerate(zip(left, right)):
            found = _first_difference(a, b, f"{path}[{index}]")
            if found:
                return found
        return None
    if left != right:
        return f"{path}: {left!r} != {right!r}"
    return None


def _environment_record() -> dict:
    return {
        "host": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "peak_rss_kib_after_run": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


# ---------------------------------------------------------------------------
# Shared setup
# ---------------------------------------------------------------------------


def _load_approved(spec: Path) -> me.MethodContract:
    return mp.load_approved_contract_from_yaml(spec)


def _expectations_from_json(payload: dict) -> sn.SnapshotExpectations:
    return sn.SnapshotExpectations(
        method_id=str(payload["method_id"]),
        contract_id=str(payload["contract_id"]),
        contract_digest=str(payload["contract_digest"]),
        policy_bundle_id=str(payload["policy_bundle_id"]),
        evaluator_build=str(payload["evaluator_build"]),
        scope_id=str(payload["scope_id"]),
        increment_id=str(payload["increment_id"]),
        usage_ids=tuple(payload["usage_ids"]),
        profiles=tuple(payload["profiles"]),
        declared_tested_head=payload.get("declared_tested_head"),
        candidate_roots=tuple(payload["candidate_roots"]),
        tested_roots=tuple(payload["tested_roots"]),
        expected_evaluation_key=payload.get("expected_evaluation_key"),
    )


def _trusted_from_json(payload: dict) -> sn.TrustedSnapshotBinding:
    return sn.TrustedSnapshotBinding(
        git_commit=str(payload["git_commit"]),
        sysml_project_id=str(payload["sysml_project_id"]),
        sysml_commit_id=str(payload["sysml_commit_id"]),
        scope=str(payload["scope"]),
        export_sha256=str(payload["export_sha256"]),
        expected_payload_digest=str(payload["expected_payload_digest"]),
        binding_sha256=payload.get("binding_sha256"),
        validation_run=str(payload.get("validation_run") or ""),
        expected_elements_digest=payload.get("expected_elements_digest"),
        expected_candidate_files_digest=payload.get(
            "expected_candidate_files_digest"
        ),
        expected_tested_files_digest=payload.get("expected_tested_files_digest"),
    )


def _evaluate_via_snapshot(
    snapshot_path: Path,
    trusted: sn.TrustedSnapshotBinding,
    expectations: sn.SnapshotExpectations,
    contract: me.MethodContract,
) -> tuple[sn.LoadedSnapshot, me.CanonicalEvaluation, float, float]:
    start = time.perf_counter()
    loaded = sn.load_snapshot(
        snapshot_path, trusted=trusted, expectations=expectations
    )
    load_seconds = time.perf_counter() - start
    start = time.perf_counter()
    assembly = mp.assemble_pilot_context(
        approved_contract=contract,
        elements=loaded.elements,
        revision=loaded.revision,
        candidate_source=loaded.sources["candidate"],
        tested_source=loaded.sources["tested"],
    )
    evaluation = me.MethodEvaluator(contract).evaluate(
        assembly.context, requested_readiness=[PHASE_EXIT_TARGET]
    )
    assemble_evaluate_seconds = time.perf_counter() - start
    return loaded, evaluation, load_seconds, assemble_evaluate_seconds


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def mode_build(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    binding = _load_json(args.candidate_binding)
    export = _load_json(args.candidate_export)
    identity_doc = _load_json(args.export_identity)
    elements = export.get("elements") or []
    export_sha = _sha256_file(args.candidate_export)
    binding_sha = _sha256_file(args.candidate_binding)

    reasons: list[str] = []
    if identity_doc.get("schema") != "de4sdv-candidate-export-identity/v1":
        reasons.append(f"unexpected export-identity schema {identity_doc.get('schema')!r}")
    if str(identity_doc.get("export_sha256") or "") != export_sha:
        reasons.append(
            "retained export identity digest does not match the export file "
            f"(identity {identity_doc.get('export_sha256')!r}, file {export_sha!r})"
        )
    if str(binding.get("semantic_validation") or "") != "passed":
        reasons.append("candidate binding is not validated (semantic_validation != passed)")
    identity, identity_diagnostics = mp.establish_candidate_identity(
        binding=binding, export=export, requested_revision=None
    )
    if identity is None:
        reasons.extend(identity_diagnostics)
    if not elements:
        reasons.append("candidate export carries no elements")
    if reasons:
        print(json.dumps({"status": "refused-input", "reasons": reasons}, indent=2))
        return 2

    assert identity is not None
    scope_item, declared_profiles, scope_diagnostics = mp.decode_declared_tested_scope(
        elements
    )
    if scope_item is None or scope_diagnostics:
        print(
            json.dumps(
                {
                    "status": "refused-input",
                    "reasons": [
                        "declared tested scope is unresolved",
                        *scope_diagnostics,
                    ],
                },
                indent=2,
            )
        )
        return 2
    by_id = mp._elements_by_id(elements)
    _, tested_head = mp._member_text_value(by_id, scope_item, "executionHead")
    if not tested_head:
        print(json.dumps({"status": "refused-input", "reasons": ["executionHead unresolved"]}, indent=2))
        return 2

    git_checks: dict[str, str] = {}
    for label, revision in (("candidate", identity.git_commit), ("tested", tested_head)):
        probe = _git(repo, "cat-file", "-e", f"{revision}^{{commit}}")
        git_checks[label] = "present" if probe.returncode == 0 else "missing"
    if "missing" in git_checks.values():
        print(
            json.dumps(
                {"status": "refused-input", "reasons": [f"git objects missing: {git_checks}"]},
                indent=2,
            )
        )
        return 2

    spec_path: Path = args.spec or repo / "docs/method-conformance/pilot-obligations.yaml"
    contract = _load_approved(spec_path)
    spec_copy = out_dir / "spec-copy.yaml"
    shutil.copyfile(spec_path, spec_copy)

    start = time.perf_counter()
    candidate_files = _capture_root(
        repo, identity.git_commit, [mp.BENCH_ROOT, mp.REGISTRY_PATH]
    )
    tested_files = _capture_root(repo, tested_head, [mp.BENCH_ROOT])
    capture_seconds = time.perf_counter() - start

    payload = sn.build_snapshot_payload(
        semantic_binding={
            "git_repository": str(binding.get("git_repository") or ""),
            "git_commit": identity.git_commit,
            "sysml_project_id": identity.sysml_project_id,
            "sysml_commit_id": identity.sysml_commit_id,
            "scope": identity.scope,
            "ontology": binding.get("ontology"),
            "kernel_binding_count": len(binding.get("kernel_bindings") or ()),
        },
        method_binding={
            "method_id": contract.method_id,
            "contract_id": contract.contract_id,
            "contract_digest": contract.digest(),
            "policy_bundle_id": contract.policy_bundle_id,
            "source": str(spec_path),
        },
        evaluator_binding={"build_id": me.EVALUATOR_BUILD_ID},
        scope_binding={
            "scope_id": mp.PILOT_SCOPE_RECORD,
            "increment_id": mp.PILOT_INCREMENT,
            "usage_ids": list(mp.PILOT_SCOPE_USAGES),
            "profiles": list(mp.PILOT_PROFILES),
            "declared_tested_head": tested_head,
        },
        elements=elements,
        file_sources={
            "candidate": {
                "revision": identity.git_commit,
                "roots": [mp.BENCH_ROOT, mp.REGISTRY_PATH],
                "files": candidate_files,
            },
            "tested": {
                "revision": tested_head,
                "roots": [mp.BENCH_ROOT],
                "files": tested_files,
            },
        },
        provenance={
            "kind": sn.PROVENANCE_VALIDATED,
            "validation_handle": {
                "validation_run": str(args.validation_run or identity_doc.get("run_id") or ""),
                "artifact": str(args.artifact or f"full-model-api-ingestion-{identity.git_commit}"),
                "git_commit": identity.git_commit,
                "sysml_project_id": identity.sysml_project_id,
                "sysml_commit_id": identity.sysml_commit_id,
                "scope": identity.scope,
                "export_sha256": export_sha,
                "binding_sha256": binding_sha,
                "transaction_id": str(identity_doc.get("transaction_id") or ""),
            },
        },
        declared_evaluation_key=None,
        build_notes=[
            "rebuilt from the retained exact-run candidate artifacts "
            "(validated binding + export identity) and the repository revisions",
            f"capture roots: candidate {mp.BENCH_ROOT}, {mp.REGISTRY_PATH}; "
            f"tested {mp.BENCH_ROOT}",
        ],
    )

    # API-transport evaluation declares the expected canonical key.
    assembly = mp.assemble_pilot_context(
        approved_contract=contract,
        elements=elements,
        revision=identity,
        candidate_source=mp.GitRevisionFileSource(repo, identity.git_commit),
        tested_source=mp.GitRevisionFileSource(repo, tested_head),
    )
    if assembly.closure_mismatches:
        print(
            json.dumps(
                {
                    "status": "refused-policy-closure-mismatch",
                    "mismatches": list(assembly.closure_mismatches),
                },
                indent=2,
            )
        )
        return 2
    evaluation = me.MethodEvaluator(contract).evaluate(
        assembly.context, requested_readiness=[PHASE_EXIT_TARGET]
    )

    payload["completeness"]["declared_evaluation_key"] = evaluation.evaluation_key
    payload = sn.finalize_payload(payload)
    snapshot_path = out_dir / "snapshot.json"
    sn.write_snapshot(payload, snapshot_path)

    (out_dir / "trusted.json").write_text(
        json.dumps(
            {
                "git_commit": identity.git_commit,
                "sysml_project_id": identity.sysml_project_id,
                "sysml_commit_id": identity.sysml_commit_id,
                "scope": identity.scope,
                "export_sha256": export_sha,
                "expected_payload_digest": payload["integrity"]["payload_digest"],
                "expected_elements_digest": payload["integrity"]["elements_digest"],
                "expected_candidate_files_digest": payload["integrity"][
                    "file_source_digests"
                ]["candidate"],
                "expected_tested_files_digest": payload["integrity"][
                    "file_source_digests"
                ]["tested"],
                "binding_sha256": binding_sha,
                "validation_run": str(args.validation_run or ""),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "expectations.json").write_text(
        json.dumps(
            {
                "method_id": contract.method_id,
                "contract_id": contract.contract_id,
                "contract_digest": contract.digest(),
                "policy_bundle_id": contract.policy_bundle_id,
                "evaluator_build": me.EVALUATOR_BUILD_ID,
                "scope_id": mp.PILOT_SCOPE_RECORD,
                "increment_id": mp.PILOT_INCREMENT,
                "usage_ids": list(mp.PILOT_SCOPE_USAGES),
                "profiles": list(mp.PILOT_PROFILES),
                "declared_tested_head": tested_head,
                "candidate_roots": [mp.BENCH_ROOT, mp.REGISTRY_PATH],
                "tested_roots": [mp.BENCH_ROOT],
                "expected_evaluation_key": evaluation.evaluation_key,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    report = {
        "mode": "build",
        "status": "built",
        "candidate": {
            "git_commit": identity.git_commit,
            "sysml_project_id": identity.sysml_project_id,
            "sysml_commit_id": identity.sysml_commit_id,
            "scope": identity.scope,
        },
        "declared_tested_head": tested_head,
        "declared_profiles": list(declared_profiles),
        "retained_inputs": {
            "export_sha256": export_sha,
            "binding_sha256": binding_sha,
            "validation_run": str(args.validation_run or ""),
            "transaction_id": str(identity_doc.get("transaction_id") or ""),
            "git_checks": git_checks,
        },
        "snapshot": {
            "path": str(snapshot_path),
            "bytes": snapshot_path.stat().st_size,
            "sha256": _sha256_file(snapshot_path),
            "payload_digest": payload["integrity"]["payload_digest"],
            "elements_digest": payload["integrity"]["elements_digest"],
            "element_count": payload["graph"]["element_count"],
            "file_counts": {
                role: len(entry["files"])
                for role, entry in payload["file_sources"].items()
            },
            "file_bytes": {
                role: sum(
                    len(base64.b64decode(file_entry["content_b64"]))
                    for file_entry in entry["files"].values()
                )
                for role, entry in payload["file_sources"].items()
            },
        },
        "declared_evaluation_key": evaluation.evaluation_key,
        "evaluation_disposition": {
            "assessment_coverage": evaluation.assessment_coverage,
            "evaluation_state": evaluation.evaluation_state,
            "conformance_verdict": evaluation.conformance_verdict,
        },
        "assembly_diagnostics": list(assembly.diagnostics),
        "timing": {"capture_seconds": capture_seconds},
        "environment": _environment_record(),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


def mode_verify(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    out_dir = args.out.resolve()
    snapshot_path: Path = args.snapshot
    trusted = _trusted_from_json(_load_json(out_dir / "trusted.json"))
    expectations = _expectations_from_json(_load_json(out_dir / "expectations.json"))
    contract = _load_approved(args.spec or out_dir / "spec-copy.yaml")

    reasons: list[str] = []
    if contract.digest() != expectations.contract_digest:
        reasons.append(
            "the local approved contract does not match the contract digest "
            "bound by the snapshot expectations"
        )
    binding = _load_json(args.candidate_binding)
    start = time.perf_counter()
    export = json.loads(args.candidate_export.read_text(encoding="utf-8"))
    api_export_parse_seconds = time.perf_counter() - start
    identity, identity_diagnostics = mp.establish_candidate_identity(
        binding=binding, export=export, requested_revision=None
    )
    if identity is None:
        reasons.extend(identity_diagnostics)
    if not expectations.declared_tested_head:
        reasons.append("snapshot expectations carry no declared tested head")
    if reasons:
        print(json.dumps({"status": "refused-input", "reasons": reasons}, indent=2))
        return 2
    assert identity is not None

    # API transport: retained export elements + repository file revisions.
    elements = export.get("elements") or []
    start = time.perf_counter()
    api_assembly = mp.assemble_pilot_context(
        approved_contract=contract,
        elements=elements,
        revision=identity,
        candidate_source=mp.GitRevisionFileSource(repo, identity.git_commit),
        tested_source=mp.GitRevisionFileSource(repo, expectations.declared_tested_head),
    )
    api_evaluation = me.MethodEvaluator(contract).evaluate(
        api_assembly.context, requested_readiness=[PHASE_EXIT_TARGET]
    )
    api_seconds = time.perf_counter() - start

    # Snapshot transport: the snapshot file alone.
    loaded, snapshot_evaluation, load_seconds, snapshot_assemble_seconds = (
        _evaluate_via_snapshot(snapshot_path, trusted, expectations, contract)
    )

    api_projection = _canonical_projection(api_evaluation)
    snapshot_projection = _canonical_projection(snapshot_evaluation)
    difference = _first_difference(api_projection, snapshot_projection)
    identical = difference is None
    reproduced_declared = (
        snapshot_evaluation.evaluation_key == loaded.declared_evaluation_key
        and api_evaluation.evaluation_key == loaded.declared_evaluation_key
    )

    report_path = out_dir / "parity-report.json"
    report = {
        "mode": "verify",
        "status": "identical" if identical else "divergent",
        "identical": identical,
        "first_difference": difference,
        "reproduced_declared_key": reproduced_declared,
        "api_transport": {
            "evaluation_key": api_evaluation.evaluation_key,
            "element_count": len(elements),
            "source": "retained validated export + git revision file sources",
        },
        "snapshot_transport": {
            "evaluation_key": snapshot_evaluation.evaluation_key,
            "snapshot_sha256": _sha256_file(snapshot_path),
            "payload_digest": loaded.payload_digest,
            "source": "validated snapshot file (no API, no git)",
        },
        "declared_evaluation_key": loaded.declared_evaluation_key,
        "disposition": {
            "assessment_coverage": snapshot_evaluation.assessment_coverage,
            "evaluation_state": snapshot_evaluation.evaluation_state,
            "conformance_verdict": snapshot_evaluation.conformance_verdict,
            "failed_ids": list(snapshot_evaluation.failed_ids),
            "indeterminate_ids": list(snapshot_evaluation.indeterminate_ids),
            "errored_ids": list(snapshot_evaluation.errored_ids),
            "unassessed_ids": list(snapshot_evaluation.unassessed_ids),
        },
        "readiness": [block.as_dict() for block in snapshot_evaluation.readiness],
        "conformance_summary": _conformance_summary(snapshot_evaluation),
        "performance": {
            "snapshot_file_bytes": snapshot_path.stat().st_size,
            "snapshot_load_seconds": load_seconds,
            "snapshot_assemble_evaluate_seconds": snapshot_assemble_seconds,
            "api_export_parse_seconds": api_export_parse_seconds,
            "api_assemble_evaluate_seconds": api_seconds,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "environment": _environment_record(),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if identical and reproduced_declared else 2


# ---------------------------------------------------------------------------
# offline
# ---------------------------------------------------------------------------


def mode_offline(args: argparse.Namespace) -> int:
    out_dir = args.out.resolve()
    trusted = _trusted_from_json(_load_json(args.trusted_json))
    expectations = _expectations_from_json(_load_json(args.expectations_json))
    contract = _load_approved(args.spec)
    if contract.digest() != expectations.contract_digest:
        print(
            json.dumps(
                {
                    "status": "refused-input",
                    "reasons": ["approved spec digest does not match the snapshot expectations"],
                },
                indent=2,
            )
        )
        return 2
    loaded, evaluation, load_seconds, assemble_seconds = _evaluate_via_snapshot(
        args.snapshot, trusted, expectations, contract
    )
    reproduced = (
        loaded.declared_evaluation_key is not None
        and evaluation.evaluation_key == loaded.declared_evaluation_key
    )
    report = {
        "mode": "offline",
        "status": "reproduced" if reproduced else "divergent",
        "reproduced": reproduced,
        "evaluation_key": evaluation.evaluation_key,
        "declared_evaluation_key": loaded.declared_evaluation_key,
        "payload_digest": loaded.payload_digest,
        "inputs": {
            "repository": "not accessed (no repo argument)",
            "api_export": "not accessed (no export argument)",
            "snapshot": str(args.snapshot),
            "spec": str(args.spec),
        },
        "performance": {
            "snapshot_load_seconds": load_seconds,
            "snapshot_assemble_evaluate_seconds": assemble_seconds,
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "environment": _environment_record(),
    }
    (out_dir / "offline-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if reproduced else 2


# ---------------------------------------------------------------------------
# tamper
# ---------------------------------------------------------------------------


def mode_tamper(args: argparse.Namespace) -> int:
    out_dir = args.out.resolve()
    mutate_dir = out_dir / "tamper"
    mutate_dir.mkdir(parents=True, exist_ok=True)
    original = _load_json(args.snapshot)
    trusted = _trusted_from_json(_load_json(args.trusted_json))
    expectations = _expectations_from_json(_load_json(args.expectations_json))

    import copy
    from typing import Any as _Any

    cases: list[dict[str, _Any]] = []

    def attempt(
        name: str,
        payload: dict,
        mut_trusted: sn.TrustedSnapshotBinding | None,
        expect_refusal: bool,
        finalize: bool,
    ) -> None:
        candidate = copy.deepcopy(payload)
        if finalize:
            candidate = sn.finalize_payload(candidate)
        path = mutate_dir / f"{name}.json"
        sn.write_snapshot(candidate, path)
        outcome: dict[str, _Any] = {
            "case": name,
            "expected": "refused" if expect_refusal else "accepted",
        }
        try:
            sn.load_snapshot(path, trusted=mut_trusted, expectations=expectations)
            outcome["result"] = "accepted"
            outcome["refusal"] = None
        except (sn.SnapshotError, ValueError) as error:
            outcome["result"] = "refused"
            outcome["error_type"] = type(error).__name__
            outcome["reasons"] = list(getattr(error, "reasons", ()))[:2] or [str(error)[:200]]
        outcome["expected_met"] = (outcome["result"] == "refused") == expect_refusal
        cases.append(outcome)

    attempt("pristine-control", original, trusted, expect_refusal=False, finalize=False)

    mutated = copy.deepcopy(original)
    if mutated["graph"]["elements"]:
        mutated["graph"]["elements"][0]["declaredName"] = "TamperedName"
    attempt("tampered-element-payload", mutated, trusted, expect_refusal=True, finalize=False)

    mutated = copy.deepcopy(original)
    role = mutated["file_sources"]["candidate"]
    first = sorted(role["files"])[0]
    role["files"][first]["content_b64"] = base64.b64encode(b"tampered").decode()
    attempt("tampered-file-blob", mutated, trusted, expect_refusal=True, finalize=False)

    mutated = copy.deepcopy(original)
    mutated["provenance"]["kind"] = sn.PROVENANCE_SELF_ATTESTED
    attempt("self-attested-provenance", mutated, trusted, expect_refusal=True, finalize=True)

    mutated = copy.deepcopy(original)
    mutated["method_binding"]["contract_digest"] = "0" * 64
    attempt("wrong-method-digest", mutated, trusted, expect_refusal=True, finalize=True)

    mutated = copy.deepcopy(original)
    mutated["integrity"]["payload_digest"] = "0" * 64
    attempt("corrupt-payload-digest", mutated, trusted, expect_refusal=True, finalize=False)

    mutated = copy.deepcopy(original)
    mutated["file_sources"]["tested"]["revision"] = "9" * 40
    attempt("wrong-tested-head", mutated, trusted, expect_refusal=True, finalize=True)

    def reforge(payload: dict) -> dict:
        """Recompute every internal digest — the competent-attacker model."""
        forged = copy.deepcopy(payload)
        for entry in forged["file_sources"].values():
            for file_entry in entry["files"].values():
                blob = base64.b64decode(file_entry["content_b64"])
                file_entry["sha256"] = hashlib.sha256(blob).hexdigest()
        return sn.finalize_payload(forged)

    mutated = copy.deepcopy(original)
    if mutated["graph"]["elements"]:
        mutated["graph"]["elements"][0]["declaredName"] = "ReforgedTamper"
    attempt(
        "element-mutation-reforged",
        sn.finalize_payload(mutated),
        trusted,
        expect_refusal=True,
        finalize=False,
    )

    mutated = copy.deepcopy(original)
    candidate_entry = mutated["file_sources"]["candidate"]
    first = sorted(candidate_entry["files"])[0]
    candidate_entry["files"][first]["content_b64"] = base64.b64encode(
        b"reforged-candidate-tamper"
    ).decode()
    attempt(
        "candidate-file-mutation-reforged",
        reforge(mutated),
        trusted,
        expect_refusal=True,
        finalize=False,
    )

    mutated = copy.deepcopy(original)
    tested_entry = mutated["file_sources"]["tested"]
    first = sorted(tested_entry["files"])[0]
    tested_entry["files"][first]["content_b64"] = base64.b64encode(
        b"reforged-tested-tamper"
    ).decode()
    attempt(
        "tested-file-mutation-reforged",
        reforge(mutated),
        trusted,
        expect_refusal=True,
        finalize=False,
    )

    attempt("missing-trusted-record", original, None, expect_refusal=True, finalize=False)

    from dataclasses import replace

    attempt(
        "wrong-git-revision-trusted",
        original,
        replace(trusted, git_commit="9" * 40),
        expect_refusal=True,
        finalize=False,
    )

    all_met = all(case["expected_met"] for case in cases)
    report = {
        "mode": "tamper",
        "status": "refusal-matrix-ok" if all_met else "refusal-matrix-violated",
        "all_expected_outcomes_met": all_met,
        "snapshot": str(args.snapshot),
        "cases": cases,
    }
    (out_dir / "tamper-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0 if all_met else 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    build = sub.add_parser("build")
    build.add_argument("--repo", type=Path, required=True)
    build.add_argument("--candidate-export", type=Path, required=True)
    build.add_argument("--candidate-binding", type=Path, required=True)
    build.add_argument("--export-identity", type=Path, required=True)
    build.add_argument("--validation-run", default="")
    build.add_argument("--artifact", default="")
    build.add_argument("--spec", type=Path, default=None)
    build.add_argument("--out", type=Path, required=True)
    build.set_defaults(func=mode_build)

    verify = sub.add_parser("verify")
    verify.add_argument("--repo", type=Path, required=True)
    verify.add_argument("--candidate-export", type=Path, required=True)
    verify.add_argument("--candidate-binding", type=Path, required=True)
    verify.add_argument("--snapshot", type=Path, required=True)
    verify.add_argument("--spec", type=Path, default=None)
    verify.add_argument("--out", type=Path, required=True)
    verify.set_defaults(func=mode_verify)

    offline = sub.add_parser("offline")
    offline.add_argument("--snapshot", type=Path, required=True)
    offline.add_argument("--trusted-json", type=Path, required=True)
    offline.add_argument("--expectations-json", type=Path, required=True)
    offline.add_argument("--spec", type=Path, required=True)
    offline.add_argument("--out", type=Path, required=True)
    offline.set_defaults(func=mode_offline)

    tamper = sub.add_parser("tamper")
    tamper.add_argument("--snapshot", type=Path, required=True)
    tamper.add_argument("--trusted-json", type=Path, required=True)
    tamper.add_argument("--expectations-json", type=Path, required=True)
    tamper.add_argument("--out", type=Path, required=True)
    tamper.set_defaults(func=mode_tamper)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
