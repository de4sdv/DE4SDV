#!/usr/bin/env python3
"""Build, compare and close the O4 model-authority bundle at one exact revision.

Three subcommands, run in the privileged exact-SHA ingestion (separate job,
see ``.github/workflows/privileged-full-model-api-ingestion.yml``):

``bundle``   candidate (unclosed) model-authority bundle (``mab-<hex>``) from
             the checkout plus the closed O3 bundle of the same revision.
``compare``  same-revision runtime equivalence: model vs O3 and model vs
             legacy over the O3 identity set (the reviewed
             ``run_o3_equivalence`` report builder, unchanged), plus the
             model-only ``hasRelevantEvidenceContract`` discriminator
             population as recorded evidence (owner decision 5).
``close``    closure attestation from the produced artifacts. Every gate
             status is DERIVED from the artifact it names (never from CLI
             text) and sha256-bound to it:
             ``activation_eligible`` = O3 eligible AND definition closure
             closed AND coverage (residual drift none, bundle bound to the
             checkout) AND model/O3/legacy equivalence AND decision-13
             read-back passed. The requirement-population delta is measured
             evidence, never a gate.

The model-authority runtime (``de4sdv.semantic.model_authority_runtime``) is
imported lazily. Exit codes: 0 success/eligible; 2 measured but not
equivalent / not eligible (report written); 1 refused.

Claim boundary: an eligible closed bundle is a deployment INPUT. Activation
is a separate owner decision naming the mab id; nothing here deploys,
activates, retires YAML, or claims compliance.
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

CANDIDATE_BUNDLE = "de4sdv-model-authority-candidate-bundle.json"
CLOSED_BUNDLE = "de4sdv-model-authority-bundle.json"
ATTESTATION = "de4sdv-model-authority-closure-attestation.json"
ELIGIBILITY = "de4sdv-model-authority-activation-eligibility.json"
EQUIVALENCE = "de4sdv-model-authority-equivalence-report.json"
COMPARE_SCHEMA = "de4sdv.o4-model-authority-equivalence/v1"
ELIGIBILITY_SCHEMA = "de4sdv.o4-model-authority-activation-eligibility/v1"
READBACK_SCHEMA = "de4sdv.o4-verification-anchor-readback/v1"
DISCRIMINATED_PREDICATE = "hasRelevantEvidenceContract"

#: Validation name (B2 contract ``REQUIRED_MODEL_VALIDATIONS``) -> CLI flag.
VALIDATION_FLAGS = {
    "model_projection_coverage": "coverage",
    "model_o3_legacy_equivalence": "equivalence",
    "verification_anchor_readback": "readback",
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
    o3_bundle = _read_json(args.o3_bundle)
    if o3_bundle.get("git_revision") != revision:
        raise Refused("the O3 bundle is bound to a different Git revision")
    try:
        bundle = model.build_model_bundle(ROOT, o3_bundle=o3_bundle, git_revision=revision)
    except getattr(model, "ModelAuthorityRefused", ValueError) as exc:
        raise Refused(f"model-authority bundle refused: {exc}") from exc
    errors = list(model.verify_model_bundle(bundle, root=ROOT))
    out = Path(args.out) / CANDIDATE_BUNDLE
    _write(out, bundle)
    print(f"model-authority bundle id: {bundle['bundle_id']}")
    print(f"state: {bundle.get('state')}  git revision: {revision}")
    print(f"o3 component: {(bundle.get('components') or {}).get('o3', {}).get('bundle_id')}")
    for error in errors:
        print(f"  verification error: {error}")
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def _build_services(args, revision: str, o3_bundle: dict[str, Any], model_path: Path,
                    model_id: str):
    from de4sdv.semantic import entry_authority
    from de4sdv.semantic.runtime import build_semantic_runtime

    common = dict(api_url=args.api_url, binding_path=args.binding,
                  expected_git_revision=revision, ontology_path=args.ontology)
    legacy = build_semantic_runtime(**common)
    o3 = build_semantic_runtime(**common, semantic_authority=o3_bundle)
    request = entry_authority.ModelAuthorityRequest(bundle_path=model_path, bundle_id=model_id)
    # A candidate bundle is compared BEFORE closure; production entry points
    # require the closed, activation-eligible bundle.
    model, _ = entry_authority.build_model_runtime(
        request, require_activation_eligible=False, **common)
    return legacy, o3, model


def discriminator_population(service, elements: list[dict[str, Any]], subjects) -> dict[str, Any]:
    """Model-only ``hasRelevantEvidenceContract`` population (recorded)."""
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
    return {
        "predicate": DISCRIMINATED_PREDICATE,
        "authority": str(getattr(service, "semantic_authority_id", "")),
        "subject_count": len(list(subjects)),
        "hop_count": hops_total,
        "distinct_sources": len(sources),
        "distinct_targets": sorted(targets),
        "errors": errors[:50],
        "classification": "RECORDED" if not errors else "BLOCKING_MISMATCH",
        "note": ("owner decision 5: model-only resolution of the adopted "
                 "EvidenceContract type-closure discriminator; legacy/O3 keep "
                 "the blocked range, so this is recorded evidence, not an "
                 "equivalence row"),
    }


def compare_overall(pairs: dict[str, dict[str, Any]], discriminator: dict[str, Any]) -> str:
    if discriminator.get("classification") == "BLOCKING_MISMATCH":
        return "BLOCKING_MISMATCH"
    overalls = [str(report.get("overall")) for report in pairs.values()]
    if overalls and all(value == "EQUIVALENT" for value in overalls):
        return "EQUIVALENT"
    from scripts import run_o3_equivalence as roe

    return roe._worst_classification(*overalls) if overalls else "NOT_YET_COMPARABLE"


def run_compare(args: argparse.Namespace) -> int:
    from de4sdv.sysml_api.revisions import RevisionBinding
    from scripts import run_o3_equivalence as roe

    revision = _require_exact_revision(args.git_revision)
    binding = RevisionBinding.load(args.binding)
    o3_bundle = _read_json(args.o3)
    model_document = _read_json(args.model)
    model_id = str(model_document.get("bundle_id") or "")
    if model_document.get("git_revision") != revision or o3_bundle.get("git_revision") != revision:
        raise Refused("model/O3 bundles must be bound to the checked-out revision")
    model_o3 = ((model_document.get("components") or {}).get("o3") or {}).get("bundle_id")
    if model_o3 != o3_bundle.get("bundle_id"):
        raise Refused(f"model bundle embeds O3 {model_o3!r}, compared O3 is "
                      f"{o3_bundle.get('bundle_id')!r}; exactly one O3 identity is permitted")
    binding_digest = roe._binding_sha256(args.binding)
    legacy, o3, model = _build_services(args, revision, o3_bundle, Path(args.model), model_id)
    elements = roe._load_elements(args.api_url, binding)
    grounding = roe._load_export_grounding(args.export, revision=revision)
    closure_digest = roe.resolve_attested_closure(
        o3_bundle, binding=binding, binding_sha256=binding_digest, element_count=len(elements))
    generated_at = datetime.now(timezone.utc).isoformat()
    pairs: dict[str, dict[str, Any]] = {}
    for name, baseline in (("o3_vs_model", o3), ("legacy_vs_model", legacy)):
        pairs[name] = roe.build_runtime_equivalence_report(
            baseline, model, root=ROOT, bundle=o3_bundle, binding=binding,
            binding_sha256=binding_digest, import_closure_digest=closure_digest,
            git_revision=revision, verification_case_grounding=grounding,
            generated_at=generated_at)
    subjects = roe.subject_population(elements, "hasRelevantArchitecture")
    discriminator = discriminator_population(model, elements, subjects)
    overall = compare_overall(pairs, discriminator)
    report = {
        "schema": COMPARE_SCHEMA,
        "git_revision": revision,
        "model_bundle_id": model_id,
        "model_bundle_sha256": _sha256_file(args.model),
        "o3_bundle_id": str(o3_bundle.get("bundle_id") or ""),
        "binding_sha256": binding_digest,
        "import_closure_digest": closure_digest,
        "authority_ids": {
            "legacy": str(getattr(legacy, "semantic_authority_id", "")),
            "o3": str(getattr(o3, "semantic_authority_id", "")),
            "model": str(getattr(model, "semantic_authority_id", "")),
        },
        "pairs": {name: {"overall": r["overall"], "per_identity": r["per_identity"],
                         "manifest_validation": r["manifest_validation"],
                         "k_pair": r["k_pair"], "diagnostics": r["diagnostics"]}
                  for name, r in pairs.items()},
        "o3_vs_legacy": "see the same-run O3 runtime-equivalence report",
        "discriminator": discriminator,
        "overall": overall,
        "generated_at": generated_at,
        "claim_boundary": ("same-revision answer equivalence of the model-authority "
                           "runtime with O3 and legacy over the O3 identity set; not "
                           "activation, retirement or compliance"),
    }
    out = Path(args.out)
    _write(out / EQUIVALENCE, report)
    for name, full in pairs.items():
        _write(out / f"de4sdv-model-authority-{name.replace('_', '-')}-report.json", full)
    print(f"model-authority equivalence: {overall}")
    for name, entry in pairs.items():
        print(f"  {name}: {entry['overall']}")
    print(f"  {DISCRIMINATED_PREDICATE}: {discriminator['hop_count']} hop(s) to "
          f"{len(discriminator['distinct_targets'])} target(s)")
    return 0 if overall == "EQUIVALENT" else 2


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


def equivalence_gate(document: dict[str, Any], *, revision: str, bundle_id: str) -> list[str]:
    problems = []
    if document.get("schema") != COMPARE_SCHEMA:
        problems.append("equivalence report schema mismatch")
    if document.get("git_revision") != revision:
        problems.append("equivalence report is bound to a different revision")
    if document.get("model_bundle_id") != bundle_id:
        problems.append("equivalence report compares a different model bundle")
    if document.get("overall") != "EQUIVALENT":
        problems.append(f"model/O3/legacy equivalence is {document.get('overall')!r}")
    pairs = document.get("pairs") or {}
    if set(pairs) != {"o3_vs_model", "legacy_vs_model"} or any(
            (p or {}).get("overall") != "EQUIVALENT" for p in pairs.values()):
        problems.append("both model comparison pairs must be EQUIVALENT")
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
    binding = RevisionBinding.load(args.binding)
    paths = {name: Path(getattr(args, flag)) for name, flag in VALIDATION_FLAGS.items()}
    gates = {
        "verification_anchor_readback": readback_gate(_read_json(paths["verification_anchor_readback"]),
                                                      revision=revision),
        "model_o3_legacy_equivalence": equivalence_gate(
            _read_json(paths["model_o3_legacy_equivalence"]), revision=revision, bundle_id=bundle_id),
        "model_projection_coverage": coverage_gate(_read_json(paths["model_projection_coverage"]),
                                                   bundle),
    }
    validations = {
        name: {"status": "passed" if not problems else "failed", "artifact": name,
               "path": str(paths[name]), "sha256": _sha256_file(paths[name])}
        for name, problems in gates.items()
    }
    closed_ok, probe_problems = definition_closure_closed(_read_json(args.definition_probe),
                                                          revision=revision)
    attestation = model.build_model_closure_attestation(
        bundle, binding=binding, binding_sha256=_sha256_file(args.binding),
        definition_closure_closed=closed_ok, validations=validations,
        generated_at=datetime.now(timezone.utc).isoformat())
    closed = model.close_model_bundle(bundle, attestation)
    errors = list(model.verify_model_bundle(
        closed, root=ROOT, binding=binding, binding_sha256=_sha256_file(args.binding),
        require_closed=True, validation_artifacts=paths))
    eligible = attestation.get("activation_eligible") is True and not errors
    summary = {
        "schema": ELIGIBILITY_SCHEMA,
        "bundle_id": bundle_id,
        "git_revision": revision,
        "gates": {
            "o3_activation_eligible": attestation.get("o3_activation_eligible") is True,
            "definition_closure_closed": closed_ok,
            **{name: not problems for name, problems in gates.items()},
        },
        "problems": {**{n: p for n, p in gates.items() if p},
                     **({"definition_closure": probe_problems} if probe_problems else {}),
                     **({"bundle_verification": errors} if errors else {})},
        "activation_eligible": eligible,
        "owner_gated": ["sysml-api-production deployment approval",
                        f"activation decision naming {bundle_id}"],
        "claim_boundary": ("eligibility of a deployment input only; activation, "
                           "rollback proof and YAML retirement are separate steps"),
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
    bundle.add_argument("--o3-bundle", required=True, type=Path,
                        help="closed O3 bundle of the same revision")
    bundle.add_argument("--out", required=True, type=Path)
    bundle.set_defaults(func=run_bundle)

    compare = sub.add_parser("compare", allow_abbrev=False, help="model vs O3 vs legacy runtime equivalence")
    compare.add_argument("--model", required=True, type=Path)
    compare.add_argument("--o3", required=True, type=Path)
    compare.add_argument("--out", required=True, type=Path)
    compare.add_argument("--api-url", required=True)
    compare.add_argument("--binding", required=True, type=Path)
    compare.add_argument("--export", required=True, type=Path)
    compare.add_argument("--git-revision", required=True)
    compare.add_argument("--ontology", type=Path,
                         default=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml")
    compare.set_defaults(func=run_compare)

    close = sub.add_parser("close", allow_abbrev=False, help="derive gates from artifacts and close the bundle")
    close.add_argument("--model", required=True, type=Path, help="candidate model bundle")
    close.add_argument("--binding", required=True, type=Path)
    close.add_argument("--git-revision", required=True)
    close.add_argument("--definition-probe", required=True, type=Path)
    close.add_argument("--coverage", required=True, type=Path)
    close.add_argument("--equivalence", required=True, type=Path)
    close.add_argument("--readback", required=True, type=Path)
    close.add_argument("--out", required=True, type=Path)
    close.set_defaults(func=run_close)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
