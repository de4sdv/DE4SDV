#!/usr/bin/env python3
"""Decision-13 live-API read-back of the implied VerificationCase anchors.

Owner decision 13 (O4 W0, reaffirmed 2026-10-07 for Wave B): before any
claim stronger than the export, the implied library-anchor edges of the
governed VerificationCase population (22 definitions / 34 usages at the
reviewed revision) are read back from the LIVE SysML v2 API at the exact
revision. A failure BLOCKS activation (``activation_eligible`` = false).

The proof reuses the ONE shared predicate
(``de4sdv.semantic.verification_grounding``) and adds what the export cannot
show:

1. exact revision: binding, export and checkout name the same Git SHA;
2. corpus identity: the live element id set equals the export element id set
   (and the semantic report's ``element_count`` when supplied) — this is also
   the restored-database identity check of the separable workflow job;
3. the shared grounding proof evaluated over the LIVE element listing proves
   every governed element (result ``EQUIVALENT``) with the expected
   population counts;
4. the live witness set (role, governed element, witness id, mechanism)
   equals the export-derived witness set;
5. every proved witness and its governed element are dereferenced by direct
   ``GET .../elements/<id>`` and must carry the reviewed shape (type,
   ``isImplied`` true, specific end = governed element).

Claim boundary: presence and shape of the implied anchor edges in the live
API at one revision. It does not establish verification adequacy, evidence
validity or acceptance. Exit 0 only when every check passes; the report is
written either way.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic import verification_grounding as vg  # noqa: E402
from de4sdv.sysml_api.repository import reference_ids  # noqa: E402

READBACK_SCHEMA = "de4sdv.o4-verification-anchor-readback/v1"
EXPECTED_DEFINITIONS = 22
EXPECTED_USAGES = 34

_ROLES = {
    "definition_role": (vg.GOVERNED_DEFINITION_TYPE, vg.DEFINITION_KINDS,
                        vg.DEFINITION_SPECIFIC_KEYS),
    "usage_role": (vg.GOVERNED_USAGE_TYPE, vg.USAGE_KINDS, vg.USAGE_SPECIFIC_KEYS),
}


def _witness_set(proof: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    return {
        (role, str(row.get("element_id")), str(row.get("witness_id")),
         str(row.get("mechanism")))
        for role, rows in (proof.get("proved") or {}).items()
        for row in rows
    }


def _dereference(repository, binding, role: str, row: dict[str, Any]) -> list[str]:
    governed_type, kinds, specific_keys = _ROLES[role]
    project, commit = binding.sysml_project_id, binding.sysml_commit_id
    governed_id = str(row["element_id"])
    witness_id = str(row["witness_id"])
    problems: list[str] = []
    try:
        witness = repository.get_element(project, commit, witness_id)
    except Exception as exc:  # noqa: BLE001 — any read failure is a failed read-back
        return [f"{role}: witness {witness_id} not readable from the live API: {exc}"]
    try:
        governed = repository.get_element(project, commit, governed_id)
    except Exception as exc:  # noqa: BLE001
        return [f"{role}: governed element {governed_id} not readable from the live API: {exc}"]
    if str(witness.get("@id") or witness.get("elementId") or "") != witness_id:
        problems.append(f"{role}: witness {witness_id} dereferenced to a different id")
    if str(witness.get("@type")) not in kinds:
        problems.append(f"{role}: witness {witness_id} has type {witness.get('@type')!r}")
    if witness.get("isImplied") is not True:
        problems.append(f"{role}: witness {witness_id} is not isImplied in the live API")
    specific: set[str] = set()
    for key in specific_keys:
        specific.update(reference_ids(witness.get(key)))
    if governed_id not in specific:
        problems.append(
            f"{role}: witness {witness_id} specific end does not name {governed_id}"
        )
    if str(governed.get("@type")) != governed_type:
        problems.append(
            f"{role}: governed element {governed_id} has type {governed.get('@type')!r}"
        )
    return problems


def readback_anchors(
    repository,
    binding,
    export: dict[str, Any],
    *,
    revision: str,
    semantic_report: dict[str, Any] | None = None,
    expected_definitions: int = EXPECTED_DEFINITIONS,
    expected_usages: int = EXPECTED_USAGES,
) -> dict[str, Any]:
    """Evaluate the decision-13 read-back (pure over the supplied transport)."""
    failures: list[str] = []
    if str(binding.git_commit) != revision:
        failures.append(f"binding revision {binding.git_commit} != {revision}")
    if str(export.get("git_commit")) != revision:
        failures.append(f"export revision {export.get('git_commit')} != {revision}")

    references = [r for r in (export.get("external_references") or []) if isinstance(r, dict)]
    anchors = dict(export.get("library_anchors") or {})
    export_elements = [e for e in (export.get("elements") or []) if isinstance(e, dict)]
    live = repository.list_elements(binding.sysml_project_id, binding.sysml_commit_id)

    live_ids = {str(e.get("@id")) for e in live}
    export_ids = {str(e.get("@id")) for e in export_elements}
    if live_ids != export_ids:
        failures.append(
            "live corpus differs from the export: "
            f"missing={len(export_ids - live_ids)} unexpected={len(live_ids - export_ids)}"
        )
    if semantic_report is not None and int(semantic_report.get("element_count", -1)) != len(live):
        failures.append(
            f"semantic report element_count {semantic_report.get('element_count')} != "
            f"live element count {len(live)}"
        )

    export_proof = vg.prove_verification_case_grounding(
        elements=export_elements, external_references=references, library_anchors=anchors)
    live_proof = vg.prove_verification_case_grounding(
        elements=live, external_references=references, library_anchors=anchors)
    if live_proof["result"] != "EQUIVALENT":
        failures.append(f"live grounding result {live_proof['result']} (expected EQUIVALENT)")
    population = live_proof.get("governed_population") or {}
    proved = live_proof.get("proved") or {}
    measured = {
        "definitions": int(population.get("definitions", 0)),
        "usages": int(population.get("usages", 0)),
        "proved_definitions": len(proved.get("definition_role", [])),
        "proved_usages": len(proved.get("usage_role", [])),
    }
    if measured["definitions"] != expected_definitions or measured["proved_definitions"] != expected_definitions:
        failures.append(
            f"definition population {measured['definitions']}/{measured['proved_definitions']} "
            f"proved; expected {expected_definitions}"
        )
    if measured["usages"] != expected_usages or measured["proved_usages"] != expected_usages:
        failures.append(
            f"usage population {measured['usages']}/{measured['proved_usages']} proved; "
            f"expected {expected_usages}"
        )
    live_witnesses, export_witnesses = _witness_set(live_proof), _witness_set(export_proof)
    if live_witnesses != export_witnesses:
        failures.append(
            "live witness set differs from the export witness set: "
            f"live-only={len(live_witnesses - export_witnesses)} "
            f"export-only={len(export_witnesses - live_witnesses)}"
        )

    dereferenced: list[dict[str, Any]] = []
    for role in ("definition_role", "usage_role"):
        for row in proved.get(role, []):
            problems = _dereference(repository, binding, role, row)
            failures.extend(problems)
            dereferenced.append({
                "role": role,
                "element_id": row["element_id"],
                "witness_id": row["witness_id"],
                "mechanism": row.get("mechanism"),
                "status": "passed" if not problems else "failed",
            })
    measured["dereferenced"] = sum(1 for row in dereferenced if row["status"] == "passed")

    passed = not failures
    return {
        "schema": READBACK_SCHEMA,
        "decision": "decision-13",
        "git_revision": revision,
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "live_element_count": len(live),
        "expected": {"definitions": expected_definitions, "usages": expected_usages},
        "measured": measured,
        "live_grounding": live_proof,
        "export_grounding_result": export_proof["result"],
        "dereferenced": dereferenced,
        "failures": failures,
        "passed": passed,
        "activation_eligible": passed,
        "claim_boundary": (
            "presence and shape of the implied VerificationCase library-anchor "
            "edges in the live API at one exact revision; does not establish "
            "verification adequacy, evidence validity, acceptance or compliance"
        ),
    }


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _load_binding(path: Path):
    from de4sdv.sysml_api.revisions import RevisionBinding

    return RevisionBinding.load(path)


def _repository(api_url: str):
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    return SysMLRepository(ApiClient(api_url, timeout=1800.0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--git-revision", required=True)
    parser.add_argument("--semantic-report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    head = _git_head()
    if args.git_revision != head:
        raise SystemExit(
            f"requested revision {args.git_revision!r} does not match the checked-out "
            f"revision {head!r}; exact-revision evidence refuses moving refs"
        )
    binding = _load_binding(args.binding)
    export_bytes = args.export.read_bytes()
    export = json.loads(export_bytes)
    semantic_report = (
        json.loads(args.semantic_report.read_text(encoding="utf-8"))
        if args.semantic_report else None
    )
    report = readback_anchors(_repository(args.api_url), binding, export,
                              revision=args.git_revision, semantic_report=semantic_report)
    report["binding_sha256"] = "sha256:" + hashlib.sha256(args.binding.read_bytes()).hexdigest()
    report["export_sha256"] = "sha256:" + hashlib.sha256(export_bytes).hexdigest()
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"decision-13 read-back: {'passed' if report['passed'] else 'FAILED'}")
    print(f"measured: {report['measured']}")
    print(f"activation_eligible: {report['activation_eligible']}")
    for failure in report["failures"][:20]:
        print(f"  failure: {failure}")
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
