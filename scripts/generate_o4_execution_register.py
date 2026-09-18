#!/usr/bin/env python3
"""Generate the O4 execution register from the governed ontology review.

The register is a mechanical, machine-checked derivation of
``docs/method-conformance/o4/ontology-review/integrated-review.json`` (the
accepted O4 target input) with the wave assignment rules fixed by
``docs/method-conformance/o4/o4-execution-plan.md``:

- every reviewed identity (93) is accounted exactly once (90 retained, 1
  removal, 2 merges); no identity may silently disappear;
- the frozen O3 13 are marked complete and stay outside all O4 waves;
- every retained O4 target is assigned exactly one proposed migration wave
  by documented rules anchored in the review's own burn-down (REVIEW.md
  Deliverable 8), its named sets and its bin classifications.

Usage:
    python scripts/generate_o4_execution_register.py           # write
    python scripts/generate_o4_execution_register.py --check   # verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = Path("docs/method-conformance/o4/o4-execution-register.json")
REVIEW_PATH = Path("docs/method-conformance/o4/ontology-review/integrated-review.json")

REGISTER_SCHEMA = "de4sdv.o4-execution-register/v1"

# ---------------------------------------------------------------------------
# Governing constants — anchored in REVIEW.md Deliverable 8 (O4 burn-down),
# Deliverable 9 (dependency graph) and Deliverable 10 (open decisions).
# ---------------------------------------------------------------------------

WAVES: list[dict[str, str]] = [
    {
        "id": "W0",
        "name": "Execution & gating infrastructure and complete accounting",
        "kind": "infrastructure",
        "review_mapping": "this planning package; review Deliverable 8 preconditions",
        "exit": "register generated, accounting invariants enforced in check_repo, wave rules reviewed",
    },
    {
        "id": "W1",
        "name": "Correction batch (no model changes)",
        "kind": "activity",
        "review_mapping": "review Deliverable 8 Wave 1",
        "exit": "regenerated artifacts bound by the two-commit pattern; CI green at exact head",
    },
    {
        "id": "W2",
        "name": "Definitions parity",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 2 (26 MODEL_AUTHORITY_PARITY rows)",
        "exit": "normalized-exact or reviewed-equivalent definition text for every row; O2 admission unblocked for these rows",
    },
    {
        "id": "W3",
        "name": "Native/library adoption & projection rows",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 3 core (native constructs + accepted library)",
        "exit": "projection rows generated from model authority; same-revision equivalence evidence per identity where traversal is claimed",
    },
    {
        "id": "W4",
        "name": "Low-dependency DE4SDV application semantics & vocabulary",
        "kind": "semantic",
        "review_mapping": "review fall-through rule F1 (rows not named in D8; lowest-dependency application semantics)",
        "exit": "model-resident definitions bound (parity) + projection rows generated; no redesign required",
    },
    {
        "id": "W5",
        "name": "External-boundary contracts",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 4 (10 EXTERNAL_BOUNDARY rows)",
        "exit": "contract docs + profile entries; no traversal; blocked-state surfaced wherever queried",
    },
    {
        "id": "W6",
        "name": "Relationship redesigns & traceability",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 5 (named design set)",
        "exit": "old names retired through the governed transition; no signature silently changed",
    },
    {
        "id": "W7",
        "name": "Gated/blocked closures (incl. architecture-semantics definition homes)",
        "kind": "semantic-gated",
        "review_mapping": "review Deliverable 8 Wave 6 + fall-through rule F2 (architecture/evidence semantics awaiting owner decisions)",
        "exit": "each blocker resolved by the named decision/evidence, then normal earlier-wave treatment",
    },
    {
        "id": "closure",
        "name": "Closure: authored-YAML consumer retirement & one-authority reproducibility",
        "kind": "closure",
        "review_mapping": "review O4 arc (authorship retirement + reproducibility proof)",
        "exit": "complete reviewed target inventory accounted; consumers retired or compatibility-generated; one-authority reproducibility demonstrated",
    },
]

# D8-named design set (relationships to redesign + traceability + claim design).
W6_REDESIGN_NAMED = {
    "TraceLink",
    "RequiredTraceChain",
    "realizedBy",
    "specifiesFunction",
    "validatedBy",
    "constrainedBy",
    "deployedTo",
    "hasEvidenceStatus",
    "supportedByEvidence",
}

# Deliverable 8 wave 6 named set plus the architecture-semantics / evidence rows that carry
# open owner decisions (fall-through rule F2): umbrella definition homes
# (D10 #5), acceptance-criterion promotion (D10 #6), assurance claim design
# (D10 #3).
W7_GATED_NAMED = {
    "EvidenceContract",
    "hasRelevantEvidenceContract",
    "instantiatesCanonicalArchitecture",
    "hasAcceptanceCriterion",
    "allocatedTo",
    "ArchitectureElement",
    "Function",
    "LogicalElement",
    "PhysicalElement",
    "AcceptanceCriterion",
    "AssuranceClaim",
}

# Deliverable 8 wave 3 core minus the MODEL_AUTHORITY_PARITY-classified signal rows: the
# review's Wave 2 text counts 26 MODEL_AUTHORITY_PARITY rows explicitly and
# those three rows carry parity work ("close doc parity only"), so parity
# takes precedence there; the remaining native/adoption/projection rows form
# this wave.
W3_NATIVE_PROJECTION = {
    "Concern",
    "EvidenceStatus",
    "IncrementSize",
    "Variant",
    "VariationPoint",
    "VerificationMethod",
    "View",
    "Viewpoint",
    "usesVerificationMethod",
    "variesAt",
}

# Fall-through rule F1: application semantics/vocabulary rows named in no
# D8 wave that need definitions + projection rows only (no redesign, no
# owner-gated architecture/evidence decision).
W4_LOWDEP = {
    "ValidationScenario",
    "addressesConcern",
    "hasStakeholder",
    "selectedViewpoint",
    "producesView",
    "recordsAssumption",
    "recordsGap",
    "Interface",
    "specifiesFeature",
    "specifiesCommonCapability",
}

# D10 open decisions mapped to the wave they block, with the rows they gate.
D10_DECISIONS: list[dict[str, Any]] = [
    {"id": "decision-1", "decision": "Approve the five renames + deprecation/alias policy", "blocks_waves": ["W6"], "rows": ["realizedBy", "specifiesFunction", "validatedBy", "constrainedBy", "deployedTo"]},
    {"id": "decision-2", "decision": "constrainedBy: provenance-reference vs normative required-constraint semantics", "blocks_waves": ["W6"], "rows": ["constrainedBy"]},
    {"id": "decision-3", "decision": "supportedByEvidence/AssuranceClaim claim model; cited vs assessed-sufficient support", "blocks_waves": ["W6", "W7"], "rows": ["supportedByEvidence", "AssuranceClaim"]},
    {"id": "decision-4", "decision": "EvidenceStatus split: orthogonal status dimensions + authorities", "blocks_waves": ["W3", "W6"], "rows": ["EvidenceStatus", "hasEvidenceStatus"]},
    {"id": "decision-5", "decision": "Umbrella-class definition homes; hasRelevantArchitecture filter width", "blocks_waves": ["W7"], "rows": ["ArchitectureElement", "Function", "LogicalElement", "PhysicalElement"]},
    {"id": "decision-6", "decision": "AcceptanceCriterion kernel promotion vs retained slice mapping", "blocks_waves": ["W7"], "rows": ["AcceptanceCriterion", "hasAcceptanceCriterion"]},
    {"id": "decision-7", "decision": "MethodEvaluationScope exclusions: model-resident representation shape", "blocks_waves": ["W2"], "rows": ["MethodEvaluationScope"]},
    {"id": "decision-8", "decision": "Trace-chain redesign: per-increment trace expectation (public API compatibility scope)", "blocks_waves": ["W6"], "rows": ["TraceLink", "RequiredTraceChain"]},
    {"id": "decision-9", "decision": "PLE configurator authority: external catalogue (ADR 0006) vs model selection algebra", "blocks_waves": ["W5", "W7"], "rows": ["FeatureConfiguration", "selectsFeature", "includesCommonCapability", "appliesToMemberProduct", "selectsVariant", "specifiesFeature", "specifiesCommonCapability", "VariationPoint", "Variant", "variesAt"]},
    {"id": "decision-10", "decision": "Canonical architecture source for instantiatesCanonicalArchitecture", "blocks_waves": ["W7"], "rows": ["instantiatesCanonicalArchitecture"]},
    {"id": "decision-11", "decision": "SAF role-def adoption/publication disposition", "blocks_waves": ["W2"], "rows": ["Stakeholder"]},
    {"id": "decision-12", "decision": "ADR 0009 status header correction", "blocks_waves": ["W1"], "rows": []},
    {"id": "decision-13", "decision": "Live-API anchor read-back before any stronger-than-export claim", "blocks_waves": ["W0"], "rows": []},
    {"id": "decision-14", "decision": "Feature/CommonCapability disjointWith axiom: model-resident or explicitly dropped", "blocks_waves": ["W2"], "rows": ["Feature", "CommonCapability"]},
    {"id": "decision-15", "decision": "Renaming successor for the trace-chain redesign", "blocks_waves": ["W6"], "rows": ["RequiredTraceChain", "TraceLink"]},
]

# Correction-batch rows (review Deliverable 8 Wave 1; no semantic change).
CORRECTIONS_BATCH_ROWS = {"usesVerificationMethod", "VerificationMethod", "IncrementSize"}
CORRECTIONS_BATCH_O3_SIDE = {"verifiedBy", "hasSubject"}

# Dependency-flag groups (review D9/D10 anchors; curated, documented).
PLE_ROWS = {
    "ProductLine",
    "MemberProduct",
    "Feature",
    "ProductLineCharacteristic",
    "CommonCapability",
    "DeferredProductLineScope",
    "FeatureConfiguration",
    "appliesToMemberProduct",
    "selectsFeature",
    "includesCommonCapability",
    "selectsVariant",
    "specifiesFeature",
    "specifiesCommonCapability",
    "VariationPoint",
    "Variant",
    "variesAt",
}
CANONICAL_ARCHITECTURE_ROWS = {"instantiatesCanonicalArchitecture"}
EVIDENCE_LINEAGE_ROWS = {
    "EvidenceContract",
    "hasRelevantEvidenceContract",
    "hasEvidence",
    "hasEvidenceStatus",
    "EvidenceArtifact",
    "EvidenceStatus",
    "Baseline",
    "capturedInBaseline",
    "supportedByEvidence",
    "AssuranceClaim",
    "AcceptanceCriterion",
    "hasAcceptanceCriterion",
}
SAF_ROWS = {"Stakeholder"}

# Retirement-condition templates per wave.
RETIREMENT_TEMPLATES = {
    "W2": "YAML definition row retires as semantic authority when model-side definition parity (normalized-exact or reviewed-equivalent) is bound and O2 admission for the row completes; YAML remains generated parity/review metadata only.",
    "W3": "YAML row retires as semantic authority when its projection/profile rows are generated from model or pinned-library authority and exact-revision equivalence evidence is recorded wherever traversal is claimed.",
    "W4": "YAML row retires as semantic authority when the model-resident definition (parity) is bound and its projection rows are generated; no redesign is required.",
    "W5": "YAML row retires as semantic authority when the reviewed external-boundary contract and typed-reference schema/profile entries are approved and bound; external facts stay external.",
    "W6": "YAML row retires as semantic authority when the owner-approved redesign lands (successor vocabulary bound, compatibility/deprecation window closed, exact-revision equivalence evidence recorded); no signature is silently changed.",
    "W7": "YAML row retires as semantic authority when its named owner decision resolves and the row completes its base-wave treatment (parity/adoption/redesign per disposition).",
    "closure": "Already model-authoritative (privileged-closure-proven); no YAML authority remains; closure accounting only.",
}


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_review(root: Path) -> dict[str, Any]:
    return json.loads((root / REVIEW_PATH).read_text(encoding="utf-8"))


def o3_identities() -> list[str]:
    """The frozen O3 13 from the runtime code (single source of truth)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    return list(MIGRATED_IDENTITIES)


def assign_wave(row: dict[str, Any]) -> tuple[str | None, str]:
    """Return (wave_id, wave_basis) for one review row (mechanical rules)."""
    identity = row["identity"]
    target = row.get("target") or {}
    if target.get("merge_into"):
        return None, "accounting: merged (target.merge_into set; review Deliverable 7 merge list)"
    if row.get("migration_class") == "REMOVE_FROM_ONTOLOGY":
        return None, "accounting: removed (review Deliverable 7 removal list)"
    if row.get("o3_protected"):
        return "O4-complete", "frozen O3 13 (o3_protected; outside all O4 waves)"
    if identity in W7_GATED_NAMED:
        return "W7", "review Deliverable 8 Wave 6 named set + fall-through rule F2 (owner-gated architecture/evidence semantics)"
    if identity in W6_REDESIGN_NAMED:
        return "W6", "review Deliverable 8 Wave 5 named design set (redesigns + traceability + claim design)"
    if row.get("migration_class") == "EXTERNAL_BOUNDARY":
        return "W5", "review Deliverable 8 Wave 4 (EXTERNAL_BOUNDARY bin, 10 rows named)"
    if row.get("migration_class") == "MODEL_AUTHORITY_PARITY":
        return "W2", "review Deliverable 8 Wave 2 (MODEL_AUTHORITY_PARITY bin; explicit 26-row count)"
    if identity in W3_NATIVE_PROJECTION:
        return "W3", "review Deliverable 8 Wave 3 core (native/library constructs; signal rows migrate with W2 per the explicit parity count)"
    if identity in W4_LOWDEP:
        return "W4", "fall-through rule F1 (low-dependency application semantics/vocabulary; not named in D8)"
    if row.get("migration_class") == "ALREADY_COMPLETE":
        return "closure", "already model-authoritative (closure accounting only)"
    raise SystemExit(f"unassigned retained identity {identity!r}: no wave rule applies")


def build_register(root: Path) -> dict[str, Any]:
    review = load_review(root)
    rows = review["rows"]
    o3 = o3_identities()
    o3_review = sorted(r["identity"] for r in rows if r.get("o3_protected"))
    if sorted(o3) != o3_review:
        raise SystemExit(
            "frozen O3 identity set mismatch between runtime code and review: "
            f"code={sorted(o3)} review={o3_review}"
        )

    register_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_names = [r["identity"] for r in rows]
    for index, row in enumerate(rows):
        identity = row["identity"]
        if identity in seen:
            raise SystemExit(f"duplicate identity in review rows: {identity}")
        seen.add(identity)
        target = row.get("target") or {}
        current = row.get("current") or {}
        wave, basis = assign_wave(row)
        merged = bool(target.get("merge_into"))
        removed = row.get("migration_class") == "REMOVE_FROM_ONTOLOGY"
        accounting = "merged" if merged else ("removed" if removed else "retained")
        membership = "o3-complete" if row.get("o3_protected") else (
            "o4-target" if accounting == "retained" else accounting
        )
        dependencies = list(row.get("dependencies") or [])
        other_targets = sorted(
            name
            for name in all_names
            if name != identity and any(name in dep for dep in dependencies)
        )
        register_rows.append(
            {
                "identity": identity,
                "kind": row.get("kind"),
                "review_index": index,
                "accounting_status": accounting,
                "membership": membership,
                "merge_into": target.get("merge_into"),
                "o3_complete": bool(row.get("o3_protected")),
                "review_classification": (row.get("classification") or {}).get("sysml_semantic_classification"),
                "final_disposition": target.get("disposition"),
                "migration_class": row.get("migration_class"),
                "current_authority": current.get("authority"),
                "desired_target_authority": target.get("authority"),
                "required_model_or_library_change": {
                    "new_modeling_required": target.get("new_modeling_required"),
                    "native_representation_exists": target.get("native_representation_exists"),
                    "grounding": target.get("grounding"),
                    "proposed_name": target.get("proposed_name"),
                },
                "required_semantic_projection_change": target.get("projection_required"),
                "required_api_representation_profile_change": target.get("api_profile_required"),
                "required_runtime_or_consumer_change": {
                    "runtime_support_target": target.get("runtime_support_target"),
                    "traversal_required": target.get("traversal_required"),
                    "current_runtime_support": current.get("runtime_support"),
                },
                "validation_evidence_requirement": list(target.get("evidence_needed") or []),
                "current_evidence_state": current.get("evidence_state"),
                "blockers": list(row.get("blockers") or []),
                "open_decisions": list(row.get("open_decisions") or []),
                "dependencies": dependencies,
                "dependency_flags": {
                    "ple": identity in PLE_ROWS,
                    "canonical_architecture": identity in CANONICAL_ARCHITECTURE_ROWS,
                    "evidence_lineage": identity in EVIDENCE_LINEAGE_ROWS,
                    "saf": identity in SAF_ROWS,
                    "other_targets": other_targets,
                },
                "proposed_wave": wave,
                "wave_basis": basis,
                "corrections_batch": (
                    "inventory-description correction (no semantic change)" if identity in CORRECTIONS_BATCH_ROWS
                    else ("o3-side inventory-description recorded; frozen semantics untouched" if identity in CORRECTIONS_BATCH_O3_SIDE else None)
                ),
                "retirement_condition": RETIREMENT_TEMPLATES.get(wave or "", None) if accounting == "retained" else (
                    "retired; historical evidence retained (no migration target)" if removed else
                    "merged away; intent carried by the named successor (no separate target)"
                ),
            }
        )

    by_wave: dict[str, int] = {}
    for r in register_rows:
        key = r["proposed_wave"] or f"({r['accounting_status']})"
        by_wave[key] = by_wave.get(key, 0) + 1

    retained = [r for r in register_rows if r["accounting_status"] == "retained"]
    o4_targets = [r for r in retained if not r["o3_complete"]]
    merged_rows = [r for r in register_rows if r["accounting_status"] == "merged"]
    removed_rows = [r for r in register_rows if r["accounting_status"] == "removed"]

    # Hard accounting invariants.
    if len(register_rows) != 93:
        raise SystemExit(f"expected 93 accounted rows, got {len(register_rows)}")
    if len(retained) != 90:
        raise SystemExit(f"expected 90 retained rows, got {len(retained)}")
    if len(merged_rows) != 2 or len(removed_rows) != 1:
        raise SystemExit("expected exactly 2 merges and 1 removal")
    expected_wave_counts = {
        "W2": 26, "W3": 10, "W4": 10, "W5": 10, "W6": 9, "W7": 11, "closure": 1,
    }
    actual_wave_counts = {w: sum(1 for r in o4_targets if r["proposed_wave"] == w) for w in expected_wave_counts}
    if actual_wave_counts != expected_wave_counts:
        raise SystemExit(f"wave counts drifted: {actual_wave_counts} != {expected_wave_counts}")
    if sum(actual_wave_counts.values()) != len(o4_targets):
        raise SystemExit("wave coverage is not exact: some O4 target lacks a wave")

    blockers_by_wave: dict[str, dict[str, list[str]]] = {}
    for decision in D10_DECISIONS:
        for wave_id in decision["blocks_waves"]:
            entry = blockers_by_wave.setdefault(wave_id, {"review_open_decisions": [], "rows_with_row_blockers": []})
            entry["review_open_decisions"].append(decision["id"])
    for r in iter(register_rows):
        if r["blockers"] and r["proposed_wave"]:
            blockers_by_wave.setdefault(r["proposed_wave"], {"review_open_decisions": [], "rows_with_row_blockers": []})
            blockers_by_wave[r["proposed_wave"]]["rows_with_row_blockers"].append(r["identity"])

    register = {
        "schema": REGISTER_SCHEMA,
        "source": {
            "integrated_review_path": str(REVIEW_PATH),
            "integrated_review_schema": review.get("schema"),
            "integrated_review_sha256": sha256_file(root / REVIEW_PATH),
            "reviewed_semantic_baseline": review.get("source_revision"),
        },
        "o4_completion_boundary": [
            "the complete reviewed target inventory is accounted for (93 = 90 retained + 1 removal + 2 merges; machine-enforced)",
            "semantic authority has migrated to the intended model/native/library sources",
            "Semantic Projection coverage is generated from those governed sources",
            "the API Representation Profile carries representation mechanics separately",
            "all production, ingestion, validation, viewer and tooling consumers of authored-ontology authority are retired or explicitly retained only as compatibility-generated output",
            "the authored YAML is no longer an independent semantic authority",
            "one-authority reproducibility is demonstrated",
            "exclusions, removals and merges are machine-accounted",
            "unresolved items cannot silently disappear (check_repo-enforced register completeness)",
        ],
        "waves": WAVES,
        "accounting": {
            "total_reviewed": len(register_rows),
            "o3_complete": len(retained) - len(o4_targets),
            "merged": len(merged_rows),
            "removed": len(removed_rows),
            "o4_targets": len(o4_targets),
            "retained_total": len(retained),
            "by_wave": actual_wave_counts,
        },
        "corrections_batch": {
            "review_mapping": "review Deliverable 8 Wave 1 (no model changes)",
            "activity_rows": sorted(CORRECTIONS_BATCH_ROWS),
            "o3_side_recorded": sorted(CORRECTIONS_BATCH_O3_SIDE),
            "doc_items": ["ADR 0009 status wording"],
        },
        "blockers_by_wave": blockers_by_wave,
        "review_open_decisions": D10_DECISIONS,
        "wave_dependencies": [
            {"wave": "W0", "requires": [], "unblocks": ["*"], "basis": "execution/gating infrastructure precedes all waves; complete accounting is a precondition for any migration claim"},
            {"wave": "W1", "requires": [], "unblocks": [], "basis": "correction batch (no model changes) precedes model-changing waves (review Deliverable 8 Wave 1)"},
            {"wave": "W2", "requires": [], "unblocks": ["W3", "W6"], "basis": "review Deliverable 8 dependency rule: parity unblocks the native/projection and redesign waves"},
            {"wave": "W3", "requires": ["W2"], "unblocks": ["W4"], "basis": "adoption/projection mechanics established before the low-dependency semantics rows reuse them; definition parity needed for their text"},
            {"wave": "W4", "requires": ["W2", "W3"], "unblocks": [], "basis": "low-dependency rows reuse parity text + projection mechanics"},
            {"wave": "W5", "requires": ["W2"], "unblocks": [], "independent_of": ["W3"], "basis": "review Deliverable 8: 'wave 3 is independent of 4'; external contracts need definition text from parity but not the projection rows"},
            {"wave": "W6", "requires": ["W2"], "unblocks": [], "basis": "successor definition text and parity must exist before redesigns bind"},
            {"wave": "W7", "requires": ["named owner decisions (Deliverable 10)"], "unblocks": [], "basis": "gated rows re-enter earlier waves when their blocker resolves (review Deliverable 8 Wave 6 rule); blocked rows re-enter the earlier waves"},
            {"wave": "closure", "requires": ["all wave exits", "consumer retirement inventory", "one-authority reproducibility proof"], "unblocks": [], "basis": "closure requires every wave exit bound + consumers retired or compatibility-generated + reproducibility demonstrated"},
        ],
        "rows": register_rows,
    }
    return register


def canonical(register: dict[str, Any]) -> str:
    return json.dumps(register, indent=2, sort_keys=True) + "\n"


def run_write(root: Path) -> None:
    (root / REGISTER_PATH).write_text(canonical(build_register(root)), encoding="utf-8")


def run_check_errors(root: Path | None = None) -> list[str]:
    root = root or ROOT
    target = root / REGISTER_PATH
    if not target.is_file():
        return [f"missing O4 execution register: {REGISTER_PATH}"]
    try:
        expected = canonical(build_register(root))
    except SystemExit as exc:
        return [f"O4 execution register derivation failed: {exc}"]
    actual = target.read_text(encoding="utf-8")
    if actual != expected:
        return [
            f"{REGISTER_PATH} is stale: regenerate with "
            "python scripts/generate_o4_execution_register.py"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed register")
    args = parser.parse_args(argv)
    if args.check:
        errors = run_check_errors(ROOT)
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    run_write(ROOT)
    print(f"wrote {REGISTER_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
