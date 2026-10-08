#!/usr/bin/env python3
"""Build, evidence and close the O4 model-authority bundle at one exact revision.

Subcommands (run in the privileged exact-SHA ingestion, see
``.github/workflows/privileged-full-model-api-ingestion.yml``):

``bundle``   candidate (unclosed) model-authority bundle (``mab-<hex>``,
             ``de4sdv.model-authority-bundle/v2``) from the checkout; no API
             needed. Construction refuses a non-empty routing residual.
``compare``  the model runtime's answer report over the migrated identity
             set (``de4sdv.runtime-answer-report/v1``: the five predicates the
             O3 cutover migrated, the eight class identities, the K pair) plus
             the ``hasRelevantEvidenceContract`` discriminator population
             (owner decision 5). The live EvidenceContract closure must equal,
             by element id, the bound eight members as validated from the
             same-run export by the ingestion binding rule.
``compare-answers``  offline comparison of two answer reports (for example a
             predecessor runtime's and this revision's) over the same SysML API
             elements. Each side's manifest carries its own authority label.
``close``    closure attestation from the produced artifacts. Every gate status
             is DERIVED from the artifact it names (never from CLI text) and
             sha256-bound to it: ``activation_eligible`` = definition closure
             closed AND coverage (empty residual, bundle bound to the checkout)
             AND model runtime answers (discriminator identity EQUAL, K pair
             complete, VerificationCase grounding EQUIVALENT) AND decision-13
             read-back passed AND the three batteries ran under this bundle at
             this revision. The requirement-population delta is measured
             evidence, never a gate.

The authored ontology and the O3/legacy runtimes were removed in O4 Wave C2,
so there is no same-revision comparison against them; the last
authored-vs-model contract comparison is the committed evidence
``docs/method-conformance/o4/closure/contract-equivalence.json``.

Exit codes: 0 success/eligible; 2 measured but not passing / not eligible
(report written); 1 refused.

Claim boundary: an eligible closed bundle is a deployment INPUT. Activation
is a separate owner decision naming the mab id; nothing here deploys,
activates or claims compliance.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MODEL_MODULE = "de4sdv.semantic.model_authority_runtime"
COVERAGE_MODULE = "de4sdv.semantic.model_projection_coverage"
ANSWERS_MODULE = "de4sdv.semantic.runtime_answers"

CANDIDATE_BUNDLE = "de4sdv-model-authority-candidate-bundle.json"
CLOSED_BUNDLE = "de4sdv-model-authority-bundle.json"
ATTESTATION = "de4sdv-model-authority-closure-attestation.json"
ELIGIBILITY = "de4sdv-model-authority-activation-eligibility.json"
ANSWERS = "de4sdv-model-authority-answers.json"
ANSWERS_SCHEMA = "de4sdv.o4-model-authority-answers/v1"
ELIGIBILITY_SCHEMA = "de4sdv.o4-model-authority-activation-eligibility/v2"
READBACK_SCHEMA = "de4sdv.o4-verification-anchor-readback/v1"
DISCRIMINATED_PREDICATE = "hasRelevantEvidenceContract"

#: Validation name (``REQUIRED_MODEL_VALIDATIONS``) -> CLI flag.
VALIDATION_FLAGS = {
    "model_projection_coverage": "coverage",
    "model_runtime_answers": "answers",
    "verification_anchor_readback": "readback",
    "full_model_semantic_queries": "full_model_semantic_queries",
    "product_line_scope": "product_line_scope",
    "semantic_mcp": "semantic_mcp",
}

#: The three batteries: expected output schema per validation name.
BATTERY_SCHEMAS = {
    "full_model_semantic_queries": "de4sdv-full-model-semantic-query-coverage/v1",
    "product_line_scope": "de4sdv-aebs-product-line-scope-validation/v1",
    "semantic_mcp": "de4sdv-semantic-mcp-validation/v2",
}


class Refused(SystemExit):
    def __init__(self, message: str) -> None:
        print(f"refused: {message}", file=sys.stderr)
        super().__init__(1)


def _module(name: str):
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise Refused(f"{name} is unavailable: {exc}") from exc


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _require_exact_revision(requested: str) -> str:
    head = _git_head()
    if requested != head:
        raise Refused(
            f"requested revision {requested!r} does not match the checked-out revision "
            f"{head!r}; exact-revision evidence refuses moving refs"
        )
    return head


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise Refused(f"{path} is not a JSON object")
    return document


def _write(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# bundle
# ---------------------------------------------------------------------------


def run_bundle(args: argparse.Namespace) -> int:
    revision = _require_exact_revision(args.source_revision)
    model = _module(MODEL_MODULE)
    try:
        bundle = model.build_model_bundle(ROOT, git_revision=revision)
    except getattr(model, "ModelAuthorityRefused", ValueError) as exc:
        raise Refused(f"model-authority bundle refused: {exc}") from exc
    errors = list(model.verify_model_bundle(bundle, root=ROOT))
    out = Path(args.out) / CANDIDATE_BUNDLE
    _write(out, bundle)
    components = bundle.get("components") or {}
    print(f"model-authority bundle id: {bundle['bundle_id']}")
    print(f"state: {bundle.get('state')}  git revision: {revision}")
    print(f"semantic authority: {(components.get('semantic_authority') or {}).get('id')}")
    for error in errors:
        print(f"  verification error: {error}")
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# compare (model runtime answers)
# ---------------------------------------------------------------------------


def _build_model_service(args, revision: str, model_path: Path, model_id: str):
    from de4sdv.semantic import entry_authority

    request = entry_authority.ModelAuthorityRequest(bundle_path=model_path, bundle_id=model_id)
    # A candidate bundle is evidenced BEFORE closure; production entry points
    # require the closed, activation-eligible bundle.
    service, _ = entry_authority.build_model_runtime(
        request, api_url=args.api_url, binding_path=args.binding,
        expected_git_revision=revision, require_activation_eligible=False)
    return service


def closure_identity(service, elements: list[dict[str, Any]],
                     closure_members: list[dict[str, Any]]) -> dict[str, Any]:
    """Live EvidenceContract closure vs the validated bound members (by id)."""
    expected = {str(m.get("element_id")) for m in closure_members}
    try:
        _, live, _, _ = service.traversal.evidence_contract_definitions(elements)
    except Exception as exc:  # noqa: BLE001 — recorded, classification fails
        return {"result": "BLOCKING_MISMATCH", "error": str(exc)}
    live = {str(i) for i in live}
    return {"result": "EQUAL" if live == expected and len(expected) == len(closure_members)
            else "BLOCKING_MISMATCH",
            "live_only": sorted(live - expected), "bound_only": sorted(expected - live)}


def discriminator_population(service, elements: list[dict[str, Any]], subjects,
                             closure_members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Model ``hasRelevantEvidenceContract`` population (recorded).

    With ``closure_members`` (the bound members validated from the export),
    the live closure must equal them by element id.
    """
    by_id = {str(e.get("@id")): e for e in elements}
    hops_total = 0
    sources: set[str] = set()
    targets: set[str] = set()
    errors: list[str] = []
    for subject in subjects:
        element = by_id.get(subject)
        if element is None:
            continue
        try:
            hops = service.traversal.traverse(DISCRIMINATED_PREDICATE, element, elements)
        except Exception as exc:  # noqa: BLE001 — recorded, classification fails
            errors.append(f"{subject}: {exc}")
            continue
        for hop in hops:
            hops_total += 1
            sources.add(subject)
            targets.add(str((hop.target or {}).get("@id")))
    identity = (closure_identity(service, elements, closure_members)
                if closure_members is not None else {"result": "NOT_CHECKED"})
    blocking = bool(errors) or identity["result"] == "BLOCKING_MISMATCH"
    return {
        "predicate": DISCRIMINATED_PREDICATE,
        "authority": str(getattr(service, "semantic_authority_id", "")),
        "subject_count": len(list(subjects)),
        "hop_count": hops_total,
        "distinct_sources": len(sources),
        "distinct_targets": sorted(targets),
        "errors": errors[:50],
        "closure_members": list(closure_members or []),
        "closure_identity": identity,
        "classification": "RECORDED" if not blocking else "BLOCKING_MISMATCH",
        "note": ("owner decision 5: model resolution of the adopted EvidenceContract "
                 "type-closure discriminator"),
    }


def answers_overall(answers: dict[str, Any], discriminator: dict[str, Any]) -> tuple[str, list[str]]:
    """Gate verdict of the model runtime answers (problems listed)."""
    problems = []
    if discriminator.get("classification") == "BLOCKING_MISMATCH":
        problems.append("hasRelevantEvidenceContract discriminator is BLOCKING_MISMATCH")
    if (discriminator.get("closure_identity") or {}).get("result") != "EQUAL":
        problems.append("live EvidenceContract closure is not identity-equal to the bound members")
    k_pair = answers.get("k_pair") or {}
    if k_pair.get("classification") != "EQUIVALENT":
        problems.append(f"K pair is {k_pair.get('classification')!r}: "
                        f"{(k_pair.get('errors') or []) + (k_pair.get('missing') or [])}")
    grounding = ((answers.get("classes") or {}).get("VerificationCase") or {}).get("grounding_result")
    if grounding != "EQUIVALENT":
        problems.append(f"VerificationCase grounding is {grounding!r}")
    return ("PASSED" if not problems else "FAILED"), problems


def run_compare(args: argparse.Namespace) -> int:
    from de4sdv.semantic import verification_grounding as vg
    from de4sdv.sysml_api.baseline import BaselineExportBundle

    answers_lib = _module(ANSWERS_MODULE)
    model = _module(MODEL_MODULE)
    revision = _require_exact_revision(args.git_revision)
    model_document = _read_json(args.model)
    model_id = str(model_document.get("bundle_id") or "")
    if model_document.get("git_revision") != revision:
        raise Refused("the model bundle must be bound to the checked-out revision")
    service = _build_model_service(args, revision, Path(args.model), model_id)
    elements = service._elements()
    export_document = _read_json(args.export)
    if export_document.get("git_commit") != revision:
        raise Refused(f"export git_commit {export_document.get('git_commit')!r} != {revision}")
    grounding = vg.prove_verification_case_grounding(
        elements=export_document.get("elements") or [],
        external_references=export_document.get("external_references") or [],
        library_anchors=export_document.get("library_anchors") or {})
    answers = answers_lib.collect_answers(service, elements,
                                          label=str(service.semantic_authority_id),
                                          verification_case_grounding=grounding)
    subjects = answers_lib.subject_population(elements, "hasRelevantArchitecture")
    try:
        export = BaselineExportBundle.load(Path(args.export))
        members = model.validate_closure_members(
            model.bound_evidence_contract_closure(ROOT),
            list(export.elements.values()), export.element_sources)
    except (OSError, ValueError) as exc:  # includes ModelAuthorityRefused
        raise Refused(f"bound EvidenceContract closure members cannot be validated: {exc}") from exc
    discriminator = discriminator_population(service, elements, subjects, closure_members=members)
    overall, problems = answers_overall(answers, discriminator)
    report = {
        "schema": ANSWERS_SCHEMA,
        "git_revision": revision,
        "model_bundle_id": model_id,
        "model_bundle_sha256": _sha256_file(args.model),
        "binding_sha256": _sha256_file(args.binding),
        "authority_id": str(service.semantic_authority_id),
        "answers": answers,
        "verification_case_grounding": grounding,
        "discriminator": discriminator,
        "overall": overall,
        "problems": problems,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": ("the model-authority runtime's answers over the migrated identity "
                           "set at one revision; not activation or compliance"),
    }
    _write(Path(args.out) / ANSWERS, report)
    print(f"model-authority answers: {overall}")
    for problem in problems:
        print(f"  {problem}")
    print(f"  {DISCRIMINATED_PREDICATE}: {discriminator['hop_count']} hop(s) to "
          f"{len(discriminator['distinct_targets'])} target(s)")
    return 0 if overall == "PASSED" else 2


def run_compare_answers(args: argparse.Namespace) -> int:
    answers_lib = _module(ANSWERS_MODULE)

    def load(path: Path) -> dict[str, Any]:
        document = _read_json(path)
        return document.get("answers") if document.get("schema") == ANSWERS_SCHEMA else document

    try:
        report = answers_lib.compare_answer_reports(
            load(args.old), load(args.new), allow_revision_change=args.allow_revision_change)
    except ValueError as exc:
        raise Refused(str(exc)) from exc
    _write(Path(args.out), report)
    print(f"answer comparison {report['labels']['old']} -> {report['labels']['new']}: "
          f"{report['overall']}")
    for error in report["manifest_validation"]["errors"]:
        print(f"  manifest: {error}")
    for name, entry in report["per_identity"].items():
        if entry["classification"] != "EQUIVALENT":
            print(f"  {name}: {entry['classification']}")
    return 0 if report["overall"] == "EQUIVALENT" else 2


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


def readback_gate(document: dict[str, Any], *, revision: str) -> list[str]:
    problems = []
    if document.get("schema") != READBACK_SCHEMA:
        problems.append("read-back report schema mismatch")
    if document.get("git_revision") != revision:
        problems.append("read-back report is bound to a different revision")
    if document.get("passed") is not True or document.get("activation_eligible") is not True:
        problems.append("decision-13 read-back did not pass")
    if document.get("failures"):
        problems.append("read-back report records failures")
    return problems


def answers_gate(document: dict[str, Any], *, revision: str, bundle_id: str) -> list[str]:
    problems = []
    if document.get("schema") != ANSWERS_SCHEMA:
        problems.append("answers report schema mismatch")
    if document.get("git_revision") != revision:
        problems.append("answers report is bound to a different revision")
    if document.get("model_bundle_id") != bundle_id:
        problems.append("answers report evidences a different model bundle")
    if document.get("authority_id") != f"mab:{bundle_id}":
        problems.append("answers report was not produced by this bundle's runtime")
    overall, recomputed = answers_overall(document.get("answers") or {},
                                          document.get("discriminator") or {})
    if overall != "PASSED" or document.get("overall") != "PASSED":
        problems.extend(recomputed or ["model runtime answers did not pass"])
    return problems


def battery_gate(name: str, document: dict[str, Any], *, revision: str, bundle_id: str) -> list[str]:
    """A battery passed under THIS candidate bundle at THIS revision.

    Each battery script exits non-zero on any failed assertion and writes its
    output only on success; the gate checks the output's schema, revision and
    the serving authority recorded in it.
    """
    problems = []
    if document.get("schema") != BATTERY_SCHEMAS[name]:
        problems.append(f"{name} output schema mismatch")
    recorded = document.get("git_commit") or (document.get("revision") or {}).get("git_commit")
    if recorded != revision:
        problems.append(f"{name} output is bound to revision {recorded!r}, not {revision}")
    authority = document.get("semantic_authority") if name != "product_line_scope" else document.get(
        "model_authority")
    if (authority or {}).get("authority_id") != f"mab:{bundle_id}":
        problems.append(f"{name} did not run under mab:{bundle_id} "
                        f"(recorded {(authority or {}).get('authority_id')!r})")
    if name == "semantic_mcp" and (document.get("read_only") is not True
                                   or document.get("tool_count") != 7):
        problems.append("semantic_mcp output does not describe a clean seven-tool read-only run")
    return problems


def coverage_gate(document: dict[str, Any], bundle: dict[str, Any]) -> list[str]:
    coverage = _module(COVERAGE_MODULE)
    fresh = coverage.build_report(ROOT)
    problems = []
    if document != json.loads(json.dumps(fresh)):
        problems.append("coverage report differs from the checkout's recomputed coverage")
    problems += [f"coverage: {e}" for e in coverage.compare(fresh, coverage.load_baseline(ROOT))]
    problems += [f"coverage: {e}" for e in coverage.bundle_errors(fresh, bundle, ROOT)]
    return problems


def definition_closure_closed(probe: dict[str, Any], *, revision: str) -> tuple[bool, list[str]]:
    closure = probe.get("closure") if isinstance(probe.get("closure"), dict) else {}
    problems = []
    if closure.get("closed") is not True:
        problems.append("O4 definition closure probe is not closed")
    for key in ("expected_git_revision", "binding_git_revision"):
        if closure.get(key) != revision:
            problems.append(f"definition probe closure.{key} {closure.get(key)!r} != {revision}")
    return (not problems, problems)


def run_close(args: argparse.Namespace) -> int:
    from de4sdv.sysml_api.revisions import RevisionBinding

    revision = _require_exact_revision(args.git_revision)
    model = _module(MODEL_MODULE)
    bundle = _read_json(args.model)
    bundle_id = str(bundle.get("bundle_id") or "")
    if bundle.get("state") != "candidate" or bundle.get("git_revision") != revision:
        raise Refused("close requires the candidate model bundle of the checked-out revision")
    try:
        binding = RevisionBinding.load(args.binding)
    except ValueError as exc:
        raise Refused(f"revision binding refused: {exc}") from exc
    paths = {name: Path(getattr(args, flag)) for name, flag in VALIDATION_FLAGS.items()}
    gates = {
        "verification_anchor_readback": readback_gate(_read_json(paths["verification_anchor_readback"]),
                                                      revision=revision),
        "model_runtime_answers": answers_gate(_read_json(paths["model_runtime_answers"]),
                                              revision=revision, bundle_id=bundle_id),
        "model_projection_coverage": coverage_gate(_read_json(paths["model_projection_coverage"]),
                                                   bundle),
        **{name: battery_gate(name, _read_json(paths[name]), revision=revision, bundle_id=bundle_id)
           for name in BATTERY_SCHEMAS},
    }
    validations = {
        name: {"status": "passed" if not problems else "failed", "artifact": name,
               "path": str(paths[name]), "sha256": _sha256_file(paths[name])}
        for name, problems in gates.items()
    }
    closed_ok, probe_problems = definition_closure_closed(_read_json(args.definition_probe),
                                                          revision=revision)
    answers = _read_json(paths["model_runtime_answers"])
    members = list((answers.get("discriminator") or {}).get("closure_members") or [])
    attestation = model.build_model_closure_attestation(
        bundle, binding=binding, binding_sha256=_sha256_file(args.binding),
        definition_closure_closed=closed_ok, validations=validations,
        generated_at=datetime.now(timezone.utc).isoformat(),
        evidence_contract_closure=members)
    closed = model.close_model_bundle(bundle, attestation)
    errors = list(model.verify_model_bundle(
        closed, root=ROOT, binding=binding, binding_sha256=_sha256_file(args.binding),
        require_closed=True, validation_artifacts=paths))
    eligible = attestation.get("activation_eligible") is True and not errors
    summary = {
        "schema": ELIGIBILITY_SCHEMA,
        "bundle_id": bundle_id,
        "git_revision": revision,
        "semantic_authority": attestation.get("semantic_authority_id"),
        "gates": {
            "definition_closure_closed": closed_ok,
            **{name: not problems for name, problems in gates.items()},
        },
        "problems": {**{n: p for n, p in gates.items() if p},
                     **({"definition_closure": probe_problems} if probe_problems else {}),
                     **({"bundle_verification": errors} if errors else {})},
        "activation_eligible": eligible,
        "owner_gated": ["sysml-api-production deployment approval",
                        f"activation decision naming {bundle_id}"],
        "claim_boundary": ("eligibility of a deployment input only; activation and the "
                           "rollback drill are separate owner-gated steps"),
    }
    out = Path(args.out)
    _write(out / CLOSED_BUNDLE, closed)
    _write(out / ATTESTATION, attestation)
    _write(out / ELIGIBILITY, summary)
    print(f"model-authority bundle {bundle_id}: activation_eligible={eligible}")
    for name, value in summary["gates"].items():
        print(f"  {name}: {'pass' if value else 'FAIL'}")
    for name, problems in summary["problems"].items():
        for problem in problems[:10]:
            print(f"  {name}: {problem}")
    return 0 if eligible else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)

    bundle = sub.add_parser("bundle", allow_abbrev=False, help="build the candidate model-authority bundle")
    bundle.add_argument("--source-revision", "--git-revision", dest="source_revision",
                        required=True)
    bundle.add_argument("--out", required=True, type=Path)
    bundle.set_defaults(func=run_bundle)

    compare = sub.add_parser("compare", allow_abbrev=False,
                             help="model runtime answers + EvidenceContract discriminator")
    compare.add_argument("--model", required=True, type=Path)
    compare.add_argument("--out", required=True, type=Path)
    compare.add_argument("--api-url", required=True)
    compare.add_argument("--binding", required=True, type=Path)
    compare.add_argument("--export", required=True, type=Path)
    compare.add_argument("--git-revision", required=True)
    compare.set_defaults(func=run_compare)

    compare_answers = sub.add_parser("compare-answers", allow_abbrev=False,
                                     help="offline comparison of two answer reports")
    compare_answers.add_argument("--old", required=True, type=Path)
    compare_answers.add_argument("--new", required=True, type=Path)
    compare_answers.add_argument("--out", required=True, type=Path)
    compare_answers.add_argument("--allow-revision-change", action="store_true",
                                 help="the two runtimes come from different Git revisions "
                                      "(same SysML API project/commit and subjects required)")
    compare_answers.set_defaults(func=run_compare_answers)

    close = sub.add_parser("close", allow_abbrev=False, help="derive gates from artifacts and close the bundle")
    close.add_argument("--model", required=True, type=Path, help="candidate model bundle")
    close.add_argument("--binding", required=True, type=Path)
    close.add_argument("--git-revision", required=True)
    close.add_argument("--definition-probe", required=True, type=Path)
    close.add_argument("--coverage", required=True, type=Path)
    close.add_argument("--answers", required=True, type=Path)
    close.add_argument("--readback", required=True, type=Path)
    close.add_argument("--full-model-semantic-queries", dest="full_model_semantic_queries",
                       required=True, type=Path)
    close.add_argument("--product-line-scope", dest="product_line_scope", required=True, type=Path)
    close.add_argument("--semantic-mcp", dest="semantic_mcp", required=True, type=Path)
    close.add_argument("--out", required=True, type=Path)
    close.set_defaults(func=run_close)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
