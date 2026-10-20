#!/usr/bin/env python3
"""Release evidence over the export (privileged run, after the import rehearsal).

The mechanical acceptance checks that a release needs, run in CI over the
licensed export of the exact revision. They replace the per-release
acceptance package and the deployed-API closure that the release ceremony
ran (owner decision 2026-10-11, release ceremony retired). Every check
compares content or identities, never a reviewed count, so legitimate model
growth cannot trip it and a count-preserving swap cannot pass it.

- **Revision.** The checkout, export, binding and semantic report name one
  Git commit.
- **Served model.** The export file digest, the served-model record of the
  binding and the semantic report agree; the content digest recomputed over
  the export equals the record (the full-payload import read-back produced
  it from the API listing).
- **Binding.** v2, full-model, validation passed; the kernel bindings
  re-derived from the export alone equal the binding's (ADR 0011).
- **Runtime over the export.** The production construction
  (:func:`build_deployment_runtime`: startup check, then a corpus that must be
  the validated export) with the API transport replaced by the export:
  - the K pair (``derivesRequirementFromNeed`` and its inverse) returns
    exactly the export's ``DerivesFromNeed`` connections, by id;
  - the ``hasRelevantEvidenceContract`` discriminator resolves without
    errors, and its live ``EvidenceContract`` closure equals, by element id,
    the bound members validated from the export;
  - ``VerificationCase`` grounds on the standard library (the decision-13
    anchors) with nothing missing or conflicting.
- **Coverage.** The model-projection coverage residual is empty.
- **Batteries** (when given). Each report names this revision, the binding's
  SysML project/commit and semantic authority, and a served model that passed;
  the MCP proof is read-only with seven exercised tools; the query-coverage
  battery carries a passing successor parity: over the imported API revision
  the ``allocatedTo`` and ``hasValidationScenario`` facts equal the export's
  and the method's, and the typed allocation ends close (the evidence the
  ``allocatedTo`` forward obligations ask of an exact-SHA privileged run).

Usage (paths as in the privileged workflow):

    python scripts/check_release_evidence.py \\
      --export /tmp/de4sdv-full-model-export.json \\
      --binding /tmp/de4sdv-full-model-binding.json \\
      --semantic-report /tmp/de4sdv-full-model-semantic-validation.json \\
      --query-coverage /tmp/de4sdv-full-model-semantic-query-coverage.json \\
      --scope-validation /tmp/de4sdv-product-line-scope-validation.json \\
      --mcp-validation /tmp/de4sdv-semantic-mcp-validation.json \\
      --output /tmp/de4sdv-release-evidence.json

Exit 0 when every check passed, 1 otherwise (the report is always written).
Not a compliance, certification or homologation claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.successor_parity import PARITY_RELATIONS, PARITY_SCHEMA  # noqa: E402
from de4sdv.sysml_api.repository import SysMLRepository  # noqa: E402
from de4sdv.sysml_api.revisions import RevisionBinding  # noqa: E402
from de4sdv.sysml_api.served_model import served_model_digest  # noqa: E402

REPORT_SCHEMA = "de4sdv.release-evidence/v1"
BATTERY_SCHEMAS = {
    "query_coverage": "de4sdv-full-model-semantic-query-coverage/v2",
    "scope_validation": "de4sdv-aebs-product-line-scope-validation/v1",
    "mcp_validation": "de4sdv-semantic-mcp-validation/v2",
}
EXPORT_API_URL = "export://the-licensed-export"


class _ExportClient:
    """The API transport replaced by the export (listing and element reads)."""

    base_url = EXPORT_API_URL

    def __init__(self, elements: list[dict[str, Any]], project_id: str, commit_id: str):
        self._elements = elements
        self._by_id = {str(e.get("@id")): e for e in elements}
        self._prefix = f"/projects/{project_id}/commits/{commit_id}/elements"

    def get_all(self, path: str) -> list[dict[str, Any]]:
        if not path.startswith(self._prefix):
            raise ValueError(f"the export serves only its bound revision, not {path}")
        return [dict(element) for element in self._elements]

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        if method != "GET" or not path.startswith(self._prefix + "/"):
            raise ValueError(f"the export answers only element reads, not {method} {path}")
        return dict(self._by_id[path[len(self._prefix) + 1:]])


def export_repository(elements: list[dict[str, Any]], binding: RevisionBinding) -> SysMLRepository:
    return SysMLRepository(_ExportClient(elements, binding.sysml_project_id, binding.sysml_commit_id))


@dataclass
class Evidence:
    """Everything the checks compare (collected once; evaluated purely)."""

    head: str
    export: dict[str, Any]
    export_sha256: str
    binding_document: dict[str, Any]
    semantic_report: dict[str, Any]
    batteries: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    export_content_sha256: str = ""
    export_kernel_bindings: list[tuple[str, str, str, str]] | None = None
    export_kernel_error: str = ""
    checkout_semantic_authority: dict[str, Any] | None = None
    runtime: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)


def _check(results: list[dict[str, Any]], name: str, ok: bool, observed: Any,
           expected: Any = None) -> None:
    results.append({"check": name, "ok": bool(ok), "observed": observed, "expected": expected})


def evaluate(evidence: Evidence) -> list[dict[str, Any]]:
    """The checks over the collected evidence (pure)."""
    results: list[dict[str, Any]] = []
    binding = evidence.binding_document
    served = binding.get("served_model") or {}
    report = evidence.semantic_report
    head = evidence.head

    revisions = {"checkout": head, "export": evidence.export.get("git_commit"),
                 "binding": binding.get("git_commit"), "semantic_report": report.get("git_commit")}
    _check(results, "revision: checkout, export, binding and semantic report name one commit",
           len(set(revisions.values())) == 1, revisions, head)

    digests = {"export_file": evidence.export_sha256,
               "semantic_report": report.get("source_export_sha256"),
               "binding_served_model": served.get("source_export_sha256")}
    _check(results, "served model: export file digest = semantic report = binding record",
           len(set(digests.values())) == 1, digests, evidence.export_sha256)
    elements = evidence.export.get("elements") or []
    counts = {"export": len(elements), "binding_served_model": served.get("element_count"),
              "semantic_report": report.get("element_count")}
    _check(results, "served model: content digest recomputed over the export = binding record",
           evidence.export_content_sha256 == served.get("content_sha256")
           and len(set(counts.values())) == 1,
           {"export_content": evidence.export_content_sha256, **counts},
           served.get("content_sha256"))

    shape = (binding.get("schema"), binding.get("scope"), binding.get("semantic_validation"))
    _check(results, "binding: v2, full-model, validation passed",
           shape == ("de4sdv.revision-binding/v2", "full-model", "passed"), list(shape))
    _check(results, "binding: semantic authority = the checkout's model-built contract",
           binding.get("semantic_authority") == evidence.checkout_semantic_authority
           and report.get("semantic_authority") == evidence.checkout_semantic_authority,
           (binding.get("semantic_authority") or {}).get("id"),
           (evidence.checkout_semantic_authority or {}).get("id"))
    recorded = sorted((b.get("ontology_class"), b.get("element_id"), b.get("source_file"),
                       b.get("declaration")) for b in binding.get("kernel_bindings") or ())
    derived = evidence.export_kernel_bindings
    _check(results, "binding: kernel bindings re-derived from the export alone = the binding's",
           derived is not None and [tuple(r) for r in recorded] == [tuple(d) for d in derived]
           and bool(recorded),
           {"binding": len(recorded), "export": None if derived is None else len(derived),
            "error": evidence.export_kernel_error or None})

    runtime = evidence.runtime
    _check(results, "runtime over the export: startup check passed and the corpus is the export",
           runtime.get("startup_check") == "passed" and runtime.get("served_model_check") == "passed",
           {key: runtime.get(key) for key in ("startup_check", "served_model_check", "error")})
    k_pair = runtime.get("k_pair") or {}
    _check(results, "K pair: both navigations return exactly the export's DerivesFromNeed connections",
           k_pair.get("classification") == "EQUIVALENT",
           {"classification": k_pair.get("classification"),
            "export_connections": len(k_pair.get("export_witness_population") or []),
            "errors": k_pair.get("errors"), "missing": k_pair.get("missing")})
    discriminator = runtime.get("discriminator") or {}
    _check(results, "discriminator: hasRelevantEvidenceContract resolves without errors",
           discriminator.get("errors") == [] and discriminator.get("hop_count", 0) > 0,
           {key: discriminator.get(key) for key in ("hop_count", "distinct_sources", "errors")})
    closure = runtime.get("closure_identity") or {}
    _check(results, "discriminator: live EvidenceContract closure = bound members from the export",
           closure.get("result") == "EQUAL", closure)
    grounding = runtime.get("grounding") or {}
    _check(results, "VerificationCase: standard-library grounding (decision-13 anchors) is complete",
           grounding.get("result") == "EQUIVALENT" and grounding.get("missing") == []
           and grounding.get("conflicts") == [],
           {key: grounding.get(key) for key in ("result", "governed_population", "missing", "conflicts")})

    coverage = evidence.coverage
    _check(results, "coverage: empty residual, no duplicate provider, clean kernel accounting",
           coverage.get("residual") == [] and coverage.get("residual_declarations") == []
           and coverage.get("duplicates") == [] and coverage.get("kernel_accounting_errors") == [],
           {key: coverage.get(key) for key in ("residual", "residual_declarations", "duplicates",
                                                 "kernel_accounting_errors")})

    sai = (binding.get("semantic_authority") or {}).get("id")
    project = (binding.get("sysml_project_id"), binding.get("sysml_commit_id"))
    for name, document in evidence.batteries.items():
        if document is None:
            continue
        if name == "query_coverage":
            revision = document.get("git_commit")
            served_project = (document.get("sysml_project_id"), document.get("sysml_commit_id"))
            authority = document.get("semantic_authority") or {}
        elif name == "scope_validation":
            revision = (document.get("revision") or {}).get("git_commit")
            served_project = ((document.get("revision") or {}).get("sysml_project_id"),
                              (document.get("revision") or {}).get("sysml_commit_id"))
            authority = document.get("model_authority") or {}
        else:
            revision = (document.get("revision") or {}).get("git_commit")
            served_project = ((document.get("revision") or {}).get("sysml_project_id"),
                              (document.get("revision") or {}).get("sysml_commit_id"))
            authority = document.get("semantic_authority") or {}
        _check(results, f"battery {name}: schema, revision, SysML project/commit, semantic "
                        "authority and served model",
               document.get("schema") == BATTERY_SCHEMAS[name] and revision == head
               and served_project == project and authority.get("semantic_authority") == sai
               and authority.get("served_model") == served.get("content_sha256"),
               {"schema": document.get("schema"), "revision": revision,
                "project": list(served_project), "semantic_authority": authority.get("semantic_authority"),
                "served_model": authority.get("served_model")})
    queries = evidence.batteries.get("query_coverage")
    if queries is not None:
        parity = queries.get("successor_parity") or {}
        relations = parity.get("relations") or {}
        closure = parity.get("allocation_end_closure") or {}
        _check(results, "battery query_coverage: successor parity and allocation-end closure over the "
                        "imported API revision",
               parity.get("schema") == PARITY_SCHEMA and parity.get("passed") is True
               and all((relations.get(name) or {}).get("passed") is True for name in PARITY_RELATIONS)
               and closure.get("passed") is True,
               {"schema": parity.get("schema"), "passed": parity.get("passed"),
                "relations": {name: (relations.get(name) or {}).get("passed") for name in PARITY_RELATIONS},
                "allocation_end_closure": closure.get("passed")})
    mcp = evidence.batteries.get("mcp_validation")
    if mcp is not None:
        _check(results, "battery mcp_validation: read-only, seven exercised tools",
               mcp.get("read_only") is True and mcp.get("tool_count") == 7,
               {"read_only": mcp.get("read_only"), "tool_count": mcp.get("tool_count")})
    scope = evidence.batteries.get("scope_validation")
    if scope is not None:
        _check(results, "battery scope_validation: the API listing holds the served model's elements",
               scope.get("api_element_count") == served.get("element_count"),
               scope.get("api_element_count"), served.get("element_count"))
    return results


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _read(path: Path | None) -> dict[str, Any] | None:
    return None if path is None else json.loads(Path(path).read_text(encoding="utf-8"))


def collect(*, export_path: Path, binding_path: Path, semantic_report_path: Path,
            batteries: dict[str, Path | None], root: Path = ROOT) -> Evidence:
    """Run the computations once (export digests, runtime, answers, coverage)."""
    from de4sdv.semantic import model_projection_coverage as coverage
    from de4sdv.semantic import runtime_answers as answers
    from de4sdv.semantic import verification_grounding as vg
    from de4sdv.semantic.deployment_runtime import build_deployment_runtime
    from de4sdv.semantic.export_evaluation import load_export_snapshot
    from de4sdv.semantic.model_contract import (
        bound_evidence_contract_closure,
        build_model_contract,
        validate_closure_members,
    )
    from de4sdv.sysml_api.baseline import BaselineExportBundle

    raw = Path(export_path).read_bytes()
    export = json.loads(raw)
    elements = list(export.get("elements") or [])
    evidence = Evidence(
        head=_git_head(), export=export, export_sha256=hashlib.sha256(raw).hexdigest(),
        binding_document=_read(binding_path) or {}, semantic_report=_read(semantic_report_path) or {},
        batteries={name: _read(path) for name, path in batteries.items()},
    )
    evidence.export_content_sha256 = served_model_digest(elements)
    evidence.checkout_semantic_authority = build_model_contract(root).identity.to_dict()
    try:
        snapshot = load_export_snapshot(Path(export_path), None, root=root)
        evidence.export_kernel_bindings = sorted(
            (b.ontology_class, b.element_id, b.source_file, b.declaration)
            for b in snapshot.kernel_bindings)
    except Exception as exc:  # noqa: BLE001 — recorded; the check fails
        evidence.export_kernel_error = str(exc)
    evidence.coverage = coverage.build_report(root)

    runtime: dict[str, Any] = {}
    try:
        binding = RevisionBinding.load(Path(binding_path))
        service = build_deployment_runtime(
            root, api_url=EXPORT_API_URL, binding_path=binding_path,
            expected_git_revision=evidence.head, repository=export_repository(elements, binding))
        served_elements = service._elements()
        status = service.authority_status()
        runtime.update(startup_check=status.get("startup_check"),
                       served_model_check=status.get("served_model_check"))
        grounding = vg.prove_verification_case_grounding(
            elements=elements, external_references=export.get("external_references") or [],
            library_anchors=export.get("library_anchors") or {})
        report = answers.collect_answers(
            service, served_elements, label=str(service.semantic_authority_id),
            verification_case_grounding=grounding, export_elements=elements)
        runtime["k_pair"] = report["k_pair"]
        runtime["grounding"] = grounding
        runtime["discriminator"] = _discriminator(service, served_elements, answers)
        bundle = BaselineExportBundle.from_dict(export)
        members = validate_closure_members(bound_evidence_contract_closure(root), elements,
                                           bundle.element_sources)
        runtime["closure_identity"] = _closure_identity(service, served_elements, members)
    except Exception as exc:  # noqa: BLE001 — recorded; the runtime checks fail
        runtime["error"] = f"{type(exc).__name__}: {exc}"
    evidence.runtime = runtime
    return evidence


def _discriminator(service, elements, answers) -> dict[str, Any]:
    by_id = {str(e.get("@id")): e for e in elements}
    hops, sources, errors = 0, set(), []
    for subject in answers.subject_population(elements, "hasRelevantArchitecture"):
        element = by_id.get(subject)
        if element is None:
            continue
        try:
            found = service.traversal.traverse("hasRelevantEvidenceContract", element, elements)
        except Exception as exc:  # noqa: BLE001 — recorded
            errors.append(f"{subject}: {exc}")
            continue
        hops += len(found)
        if found:
            sources.add(subject)
    return {"hop_count": hops, "distinct_sources": len(sources), "errors": errors[:50]}


def _closure_identity(service, elements, members) -> dict[str, Any]:
    expected = {str(m["element_id"]) for m in members}
    try:
        _, live, _, _ = service.traversal.evidence_contract_definitions(elements)
    except Exception as exc:  # noqa: BLE001 — recorded
        return {"result": "BLOCKING_MISMATCH", "error": str(exc)}
    live = {str(i) for i in live}
    return {"result": "EQUAL" if live == expected and len(expected) == len(members)
            else "BLOCKING_MISMATCH",
            "live_only": sorted(live - expected), "bound_only": sorted(expected - live)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--semantic-report", type=Path, required=True)
    parser.add_argument("--query-coverage", type=Path)
    parser.add_argument("--scope-validation", type=Path)
    parser.add_argument("--mcp-validation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence = collect(
        export_path=args.export, binding_path=args.binding,
        semantic_report_path=args.semantic_report,
        batteries={"query_coverage": args.query_coverage,
                   "scope_validation": args.scope_validation,
                   "mcp_validation": args.mcp_validation},
    )
    results = evaluate(evidence)
    failed = [r for r in results if not r["ok"]]
    report = {
        "schema": REPORT_SCHEMA,
        "git_revision": evidence.head,
        "export_sha256": evidence.export_sha256,
        "served_model": evidence.binding_document.get("served_model"),
        "semantic_authority": (evidence.checkout_semantic_authority or {}).get("id"),
        "batteries_checked": sorted(n for n, d in evidence.batteries.items() if d is not None),
        "checks": results,
        "passed": not failed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": ("mechanical release evidence over the licensed export of one "
                           "revision; not compliance, certification or homologation"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for result in results:
        print(("PASS " if result["ok"] else "FAIL ") + result["check"])
    print(f"release evidence: {len(results) - len(failed)}/{len(results)} checks passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
