#!/usr/bin/env python3
"""Generate the O4 execution register from the governed ontology review.

The register is deterministically generated from the governed integrated
review (``docs/method-conformance/o4/ontology-review/integrated-review.json``)
using reviewed, machine-checked wave-mapping rules fixed by
``docs/method-conformance/o4/o4-execution-plan.md``. The wave mapping
contains curated named sets and fall-through rules; every curated mapping
assumption is fail-closed against the governed review, so a review edit
that invalidates one of them fails this generator (and ``check_repo.py``).

Rules enforced here:

- every reviewed identity (93) is accounted exactly once (90 retained, 1
  removal, 2 merges); no identity may silently disappear;
- the frozen O3 13 are marked complete and stay outside all O4 waves;
- every retained O4 target has exactly one base (semantic treatment) wave;
- gated rows carry ``base_wave`` (their re-entry destination), ``gate_wave``
  (the W7 decision/holding gate) and ``gate_decisions``/``blockers``;
- curated named sets, gate sources, dependency flags and merge bindings are
  checked against the governed review and its Deliverable 9/10 text.

Usage:
    python scripts/generate_o4_execution_register.py           # write
    python scripts/generate_o4_execution_register.py --check   # verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = Path("docs/method-conformance/o4/o4-execution-register.json")
REVIEW_PATH = Path("docs/method-conformance/o4/ontology-review/integrated-review.json")
REVIEW_MD_PATH = Path("docs/method-conformance/o4/ontology-review/REVIEW.md")

REGISTER_SCHEMA = "de4sdv.o4-execution-register/v2"

GENERATION = (
    "deterministically generated from the governed integrated review using "
    "reviewed, machine-checked wave-mapping rules"
)

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
        "name": "Definitions parity & model authority",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 2 (26 MODEL_AUTHORITY_PARITY rows) + gated definition rows re-entering from the W7 gate",
        "exit": "normalized-exact or reviewed-equivalent definition text for every row; O2 admission unblocked for these rows",
    },
    {
        "id": "W3",
        "name": "Native/library adoption & projection rows",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 3 core (native constructs + accepted library); allocatedTo re-enters from the W7 gate",
        "exit": "projection rows generated from model authority; same-revision equivalence evidence per identity where traversal is claimed",
    },
    {
        "id": "W4",
        "name": "Low-dependency DE4SDV application semantics & vocabulary",
        "kind": "semantic",
        "review_mapping": "review fall-through rule F1 (rows not named in Deliverable 8; lowest-dependency application semantics)",
        "exit": "model-resident definitions bound (parity) + projection rows generated; no redesign required",
    },
    {
        "id": "W5",
        "name": "External-boundary contracts",
        "kind": "semantic",
        "review_mapping": "review Deliverable 8 Wave 4 (10 EXTERNAL_BOUNDARY rows); instantiatesCanonicalArchitecture re-enters from the W7 gate",
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
        "name": "Decision/holding gate (not a semantic treatment)",
        "kind": "gate",
        "review_mapping": "review Deliverable 8 Wave 6 + fall-through rule F2 (architecture/evidence semantics awaiting owner decisions)",
        "exit": "each held row re-enters its base wave when its named decision/evidence resolves (review Deliverable 8 Wave 6 exit rule)",
    },
    {
        "id": "closure",
        "name": "Closure: authored-YAML consumer retirement & one-authority reproducibility",
        "kind": "closure",
        "review_mapping": "review O4 arc (authorship retirement + reproducibility proof)",
        "exit": "complete reviewed target inventory accounted; consumers retired or compatibility-generated; one-authority reproducibility demonstrated",
    },
]

# Deliverable 8 wave 5 named design set (relationships to redesign +
# traceability + claim design).
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

# W7 is a decision/holding gate: each held row has a curated base wave (its
# re-entry destination) plus its gate source (owner decision and/or row
# blocker). Both sides are fail-closed against the governed review.
W7_BASE_MAP: dict[str, tuple[str, str]] = {
    "ArchitectureElement": ("W2", "definitions/model authority — umbrella definition home (decision-5)"),
    "Function": ("W2", "definitions/model authority — umbrella definition home (decision-5)"),
    "LogicalElement": ("W2", "definitions/model authority — umbrella definition home (decision-5)"),
    "PhysicalElement": ("W2", "definitions/model authority — umbrella definition home (decision-5)"),
    "AcceptanceCriterion": ("W2", "definitions/model authority — criterion-role lineage (decision-6; a promotion may adjust the disposition and re-review this base)"),
    "hasAcceptanceCriterion": ("W2", "definitions/model authority — criterion-role model over native objectives (decision-6)"),
    "AssuranceClaim": ("W2", "definitions/model authority — bounded claim vocabulary (decision-3)"),
    "EvidenceContract": ("W2", "definitions/model authority — contract-role lineage after the identity discriminator (row blocker)"),
    "hasRelevantEvidenceContract": ("W2", "definitions/model authority — predicate reopened over the resolved EvidenceContract role (row blocker)"),
    "allocatedTo": ("W3", "native allocation projection — typed allocation-end profile (row blocker; review Deliverable 9: the definition-home decision gates its projection rows)"),
    "instantiatesCanonicalArchitecture": ("W5", "external-boundary typed reference — selector-backed representation, or retirement if the selector design fails (decision-10)"),
}

W7_EXPECTED_CLASSES = {
    "ArchitectureElement": "NEW_APPLICATION_SEMANTICS",
    "Function": "NEW_APPLICATION_SEMANTICS",
    "LogicalElement": "NEW_APPLICATION_SEMANTICS",
    "PhysicalElement": "NEW_APPLICATION_SEMANTICS",
    "AcceptanceCriterion": "NEW_APPLICATION_SEMANTICS",
    "hasAcceptanceCriterion": "NEW_APPLICATION_SEMANTICS",
    "AssuranceClaim": "NEW_APPLICATION_SEMANTICS",
    "EvidenceContract": "BLOCKED",
    "hasRelevantEvidenceContract": "BLOCKED",
    "allocatedTo": "NEW_APPLICATION_SEMANTICS",
    "instantiatesCanonicalArchitecture": "BLOCKED",
}
W7_BLOCKER_GATED = {"EvidenceContract", "hasRelevantEvidenceContract", "allocatedTo"}

# The W7 gate set partitions into two disjoint groups: five rows are
# explicitly named by Deliverable 8 Wave 6, and six are genuinely unnamed
# fall-through rows (rule F2). Both groups and the partition are
# machine-checked against the Deliverable 8 Wave 6 text.
W7_D8_NAMED = {
    "EvidenceContract",
    "hasRelevantEvidenceContract",
    "hasAcceptanceCriterion",
    "allocatedTo",
    "instantiatesCanonicalArchitecture",
}
W7_FALLTHROUGH = {
    "ArchitectureElement",
    "Function",
    "LogicalElement",
    "PhysicalElement",
    "AcceptanceCriterion",
    "AssuranceClaim",
}
FALLTHROUGH_CLOSURE_ROW = "DerivesFromNeed"

# Deliverable 8 wave 3 core minus the MODEL_AUTHORITY_PARITY-classified
# signal rows: the review's Wave 2 text counts 26 MODEL_AUTHORITY_PARITY
# rows explicitly and those three rows carry parity work ("close doc parity
# only"), so parity takes precedence there; the remaining native/adoption/
# projection rows form this wave.
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
W3_EXPECTED_CLASSES = {
    "Concern": "PROJECTION_ONLY",
    "EvidenceStatus": "NATIVE_OR_LIBRARY_ADOPTION",
    "IncrementSize": "PROJECTION_ONLY",
    "Variant": "ALREADY_COMPLETE",
    "VariationPoint": "ALREADY_COMPLETE",
    "VerificationMethod": "NATIVE_OR_LIBRARY_ADOPTION",
    "View": "PROJECTION_ONLY",
    "Viewpoint": "PROJECTION_ONLY",
    "usesVerificationMethod": "NATIVE_OR_LIBRARY_ADOPTION",
    "variesAt": "PROJECTION_ONLY",
}

# Fall-through rule F1: application semantics/vocabulary rows named in no
# Deliverable 8 wave that need definitions + projection rows only (no
# redesign, no owner-gated architecture/evidence decision, no blocker).
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
W4_EXPECTED_CLASSES = {
    "ValidationScenario": "NEW_APPLICATION_SEMANTICS",
    "addressesConcern": "NEW_APPLICATION_SEMANTICS",
    "hasStakeholder": "NEW_APPLICATION_SEMANTICS",
    "selectedViewpoint": "NEW_APPLICATION_SEMANTICS",
    "producesView": "NEW_APPLICATION_SEMANTICS",
    "recordsAssumption": "NEW_APPLICATION_SEMANTICS",
    "recordsGap": "NEW_APPLICATION_SEMANTICS",
    "Interface": "PROJECTION_ONLY",
    "specifiesFeature": "PROJECTION_ONLY",
    "specifiesCommonCapability": "PROJECTION_ONLY",
}

W6_EXPECTED_CLASSES = {
    "TraceLink": "REQUIRES_SEMANTIC_MIGRATION",
    "RequiredTraceChain": "REQUIRES_SEMANTIC_MIGRATION",
    "realizedBy": "REQUIRES_SEMANTIC_MIGRATION",
    "specifiesFunction": "REQUIRES_SEMANTIC_MIGRATION",
    "validatedBy": "REQUIRES_SEMANTIC_MIGRATION",
    "constrainedBy": "REQUIRES_SEMANTIC_MIGRATION",
    "deployedTo": "REQUIRES_SEMANTIC_MIGRATION",
    "hasEvidenceStatus": "REQUIRES_SEMANTIC_MIGRATION",
    "supportedByEvidence": "NEW_APPLICATION_SEMANTICS",
}

# Merge bindings: the normalized successor plus the recorded nuance. Both are
# fail-closed against the review's raw merge_into text.
MERGE_BINDINGS: dict[str, dict[str, str]] = {
    "validatesFitnessForUse": {
        "merge_into": "validatedBy",
        "merge_note": "merges into validatedBy (retained identity; redesign wave W6); no separate target remains",
    },
    "IncrementTraceabilityShell": {
        "merge_into": "RequiredTraceChain",
        "merge_note": "bound to the redesigned per-increment trace-expectation successor intent (RequiredTraceChain redesign); the final successor identity name is pending decision-15 — not yet decided",
    },
}

# Open decisions (Deliverable 10) — statement text is parsed from REVIEW.md;
# the row lists are curated and fail-closed (rows must exist; gates derived).
D10_ROWS: dict[int, list[str]] = {
    1: ["realizedBy", "specifiesFunction", "validatedBy", "constrainedBy", "deployedTo"],
    2: ["constrainedBy"],
    3: ["supportedByEvidence", "AssuranceClaim"],
    4: ["EvidenceStatus", "hasEvidenceStatus"],
    5: ["ArchitectureElement", "Function", "LogicalElement", "PhysicalElement"],
    6: ["AcceptanceCriterion", "hasAcceptanceCriterion"],
    7: ["MethodEvaluationScope"],
    8: ["TraceLink", "RequiredTraceChain"],
    # Configurator/selection authority only; native structural variation
    # (VariationPoint, Variant, variesAt) projects without committing
    # configurator authority (execution-plan interpretation 5).
    9: ["FeatureConfiguration", "selectsFeature", "appliesToMemberProduct", "includesCommonCapability", "selectsVariant"],
    10: ["instantiatesCanonicalArchitecture"],
    11: ["Stakeholder"],
    12: [],
    13: [],
    14: ["Feature", "CommonCapability"],
    15: ["RequiredTraceChain", "TraceLink"],
}
# Decisions with no gated rows: the activity wave they gate.
D10_ACTIVITY_GATES: dict[int, list[str]] = {12: ["W1"], 13: ["W0"]}

# Dependency-flag derivations (review Deliverable 9 / Deliverable 10 anchors).
PLE_FAMILY = {
    "ProductLine",
    "MemberProduct",
    "Feature",
    "ProductLineCharacteristic",
    "CommonCapability",
    "DeferredProductLineScope",
}
PLE_D9_BULLET_EXPECTED = {
    "specifiesFeature",
    "selectsFeature",
    "includesCommonCapability",
    "appliesToMemberProduct",
    "FeatureConfiguration",
    "selectsVariant",
}
PLE_TOKENS = re.compile(
    r"\bple\b|configurator|variation|member product|product line|product-line|feature catalog|selection algebra|\bbof\b",
    re.I,
)
EVIDENCE_TOKENS = re.compile(
    r"evidence|baseline|\bclaim\b|acceptance|attestation|lineage|verdict", re.I
)
EVIDENCE_EXCEPTIONS = {"hasEvidence"}  # single-token corroboration (its EvidenceArtifact dependency)
SAF_TOKENS = re.compile(r"\bsaf\b|role.def|unrecorded provenance", re.I)
CANONICAL_TOKENS = re.compile(r"canonical", re.I)

# Correction-batch rows (review Deliverable 8 Wave 1; no semantic change).
CORRECTIONS_BATCH_ROWS = {"usesVerificationMethod", "VerificationMethod", "IncrementSize"}
CORRECTIONS_BATCH_O3_SIDE = {"verifiedBy", "hasSubject"}

# Retirement-condition templates per base wave.
RETIREMENT_TEMPLATES = {
    "W2": "YAML definition row retires as semantic authority when model-side definition parity (normalized-exact or reviewed-equivalent) is bound and O2 admission for the row completes; YAML remains generated parity/review metadata only.",
    "W3": "YAML row retires as semantic authority when its projection/profile rows are generated from model or pinned-library authority and exact-revision equivalence evidence is recorded wherever traversal is claimed.",
    "W4": "YAML row retires as semantic authority when the model-resident definition (parity) is bound and its projection rows are generated; no redesign is required.",
    "W5": "YAML row retires as semantic authority when the reviewed external-boundary contract and typed-reference schema/profile entries are approved and bound; external facts stay external.",
    "W6": "YAML row retires as semantic authority when the owner-approved redesign lands (successor vocabulary bound, compatibility/deprecation window closed, exact-revision equivalence evidence recorded); no signature is silently changed.",
    "closure": "Already model-authoritative (privileged-closure-proven); no YAML authority remains; closure accounting only.",
}
GATED_SUFFIX = " Held at the W7 decision gate until the named decision/evidence resolves; re-enters its base wave on exit."


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_review(root: Path) -> dict[str, Any]:
    return json.loads((root / REVIEW_PATH).read_text(encoding="utf-8"))


def parse_review_md(root: Path) -> dict[str, Any]:
    """Parse the governed review text: Deliverable 10 decisions + D9 bullets."""
    text = (root / REVIEW_MD_PATH).read_text(encoding="utf-8")
    lines = text.splitlines()

    def section(start_marker: str, end_marker: str) -> list[str]:
        capture, out = False, []
        for line in lines:
            if line.startswith(start_marker):
                capture = True
                continue
            if capture and line.startswith(end_marker):
                break
            if capture:
                out.append(line)
        return out

    decisions: list[dict[str, Any]] = []
    for line in section("## Deliverable 10", "## "):
        match = re.match(r"^(\d+)\. (.+)$", line.strip())
        if match:
            decisions.append({"number": int(match.group(1)), "text": match.group(2).strip()})
    if [d["number"] for d in decisions] != list(range(1, 16)):
        raise SystemExit(
            f"expected Deliverable 10 to contain decisions 1..15, got {[d['number'] for d in decisions]}"
        )

    d9_bullets = [
        line[2:].strip()
        for line in section("## Deliverable 9", "## ")
        if line.startswith("- ")
    ]
    ple_bullet: set[str] = set()
    for bullet in d9_bullets:
        if "PLE-Q/S/A" in bullet:
            ple_bullet = set(re.findall(r"`([A-Za-z][A-Za-z0-9]*)`", bullet))
    if ple_bullet != PLE_D9_BULLET_EXPECTED:
        raise SystemExit(
            f"Deliverable 9 PLE bullet identities drifted: {sorted(ple_bullet)}"
        )

    d8_wave6_text = ""
    for line in lines:
        if line.startswith("**Wave 6 —"):
            d8_wave6_text = line
            break
    if not d8_wave6_text:
        raise SystemExit("Deliverable 8 Wave 6 paragraph not found in REVIEW.md")
    return {"decisions": decisions, "d9_ple_bullet": ple_bullet, "d8_wave6_text": d8_wave6_text}


def o3_identities() -> list[str]:
    """The frozen O3 13 from the runtime code (single source of truth)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    return list(MIGRATED_IDENTITIES)


def row_text(row: dict[str, Any]) -> str:
    parts = list(row.get("dependencies") or []) + list(row.get("open_decisions") or []) + list(
        row.get("blockers") or []
    )
    return " | ".join(parts)


def clean_text(row: dict[str, Any]) -> str:
    # PLEML appears only in negated form in the review ("not PLEML-dependent",
    # "No PLEML dependency/commit"); strip it so the token scan cannot turn a
    # negation into a false dependency.
    return row_text(row).replace("PLEML", "").replace("pleml", "")


def derive_flags(row: dict[str, Any], d9_ple_bullet: set[str], d9_rows: set[str]) -> dict[str, bool]:
    identity = row["identity"]
    text = clean_text(row)
    evidence_tokens = {match.lower() for match in EVIDENCE_TOKENS.findall(row_text(row))}
    return {
        "ple": bool(
            identity in PLE_FAMILY
            or identity in d9_rows
            or identity in d9_ple_bullet
            or PLE_TOKENS.search(text)
        ),
        "canonical_architecture": bool(CANONICAL_TOKENS.search(row_text(row))),
        "evidence_lineage": bool(
            len(evidence_tokens) >= 2
            or (identity in EVIDENCE_EXCEPTIONS and len(evidence_tokens) >= 1)
        ),
        "saf": bool(SAF_TOKENS.search(row_text(row))),
    }


def assign_base_wave(row: dict[str, Any]) -> tuple[str | None, str]:
    """Return (base_wave, wave_basis) for one review row."""
    identity = row["identity"]
    target = row.get("target") or {}
    if target.get("merge_into"):
        return None, "accounting: merged (target.merge_into set; review Deliverable 7 merge list)"
    if row.get("migration_class") == "REMOVE_FROM_ONTOLOGY":
        return None, "accounting: removed (review Deliverable 7 removal list)"
    if row.get("o3_protected"):
        return "O3-complete", "frozen O3 13 (o3_protected; outside all O4 waves)"
    if identity in W7_BASE_MAP:
        base, reason = W7_BASE_MAP[identity]
        return base, (
            f"W7 gate re-entry: {reason}; held at the W7 decision gate until the gate resolves"
        )
    if identity in W6_REDESIGN_NAMED:
        return "W6", "review Deliverable 8 Wave 5 named design set (redesigns + traceability + claim design)"
    if row.get("migration_class") == "EXTERNAL_BOUNDARY":
        return "W5", "review Deliverable 8 Wave 4 (EXTERNAL_BOUNDARY bin, 10 rows named)"
    if row.get("migration_class") == "MODEL_AUTHORITY_PARITY":
        return "W2", "review Deliverable 8 Wave 2 (MODEL_AUTHORITY_PARITY bin; explicit 26-row count)"
    if identity in W3_NATIVE_PROJECTION:
        return "W3", "review Deliverable 8 Wave 3 core (native/library constructs; signal rows migrate with W2 per the explicit parity count)"
    if identity in W4_LOWDEP:
        return "W4", "fall-through rule F1 (low-dependency application semantics/vocabulary; not named in Deliverable 8)"
    if row.get("migration_class") == "ALREADY_COMPLETE":
        return "closure", "already model-authoritative (closure accounting only)"
    raise SystemExit(f"unassigned retained identity {identity!r}: no base-wave rule applies")


def check_mapping_assumptions(
    review_rows: list[dict[str, Any]],
    register_rows: list[dict[str, Any]],
    d10_items: list[dict[str, Any]],
    d9_ple_bullet: set[str],
    d8_wave6_text: str,
) -> None:
    """Fail closed when a curated mapping assumption no longer holds."""
    by = {r["identity"]: r for r in register_rows}
    rev = {r["identity"]: r for r in review_rows}
    d9_rows = {name for item in d10_items if item["id"] == "decision-9" for name in item["rows"]}

    def fail(message: str) -> None:
        raise SystemExit(f"mapping assumption violated: {message}")

    # W2: rows assigned by migration class carry MODEL_AUTHORITY_PARITY.
    w2_core = [r for r in register_rows if r["base_wave"] == "W2" and not r["gate_wave"]]
    if len(w2_core) != 26:
        fail(f"expected 26 ungated W2 rows, got {len(w2_core)}")
    for r in w2_core:
        if r["migration_class"] != "MODEL_AUTHORITY_PARITY":
            fail(f"{r['identity']} in W2 without MODEL_AUTHORITY_PARITY")

    # W3 curated members retain their expected native/library/projection class.
    for identity, expected in W3_EXPECTED_CLASSES.items():
        if by[identity]["base_wave"] != "W3" or by[identity]["migration_class"] != expected:
            fail(f"{identity}: expected W3/{expected}, got {by[identity]['base_wave']}/{by[identity]['migration_class']}")

    # W4 fall-through members retain the expected class and no blocker.
    for identity, expected in W4_EXPECTED_CLASSES.items():
        row = by[identity]
        if row["base_wave"] != "W4" or row["migration_class"] != expected:
            fail(f"{identity}: expected W4/{expected}, got {row['base_wave']}/{row['migration_class']}")
        if row["blockers"]:
            fail(f"{identity}: W4 member acquired an unacknowledged blocker: {row['blockers']}")

    # W5 members retain EXTERNAL_BOUNDARY.
    w5_core = [r for r in register_rows if r["base_wave"] == "W5" and not r["gate_wave"]]
    if len(w5_core) != 10:
        fail(f"expected 10 ungated W5 rows, got {len(w5_core)}")
    for r in w5_core:
        if r["migration_class"] != "EXTERNAL_BOUNDARY":
            fail(f"{r['identity']} in W5 without EXTERNAL_BOUNDARY")

    # W6 named members retain the expected redesign/semantic-migration class.
    for identity, expected in W6_EXPECTED_CLASSES.items():
        if by[identity]["base_wave"] != "W6" or by[identity]["migration_class"] != expected:
            fail(f"{identity}: expected W6/{expected}, got {by[identity]['base_wave']}/{by[identity]['migration_class']}")

    # W7 gate rows: curated base + expected class + a live gate source.
    for identity, (base, _reason) in W7_BASE_MAP.items():
        row = by[identity]
        if row["base_wave"] != base or row["gate_wave"] != "W7":
            fail(f"{identity}: expected gate W7 with base {base}, got {row['gate_wave']}/{row['base_wave']}")
        if row["migration_class"] != W7_EXPECTED_CLASSES[identity]:
            fail(f"{identity}: expected class {W7_EXPECTED_CLASSES[identity]}, got {row['migration_class']}")
        if not (row["gate_decisions"] or row["blockers"]):
            fail(f"{identity}: gate source vanished (no decision and no blocker)")
        if identity in W7_BLOCKER_GATED and not row["blockers"]:
            fail(f"{identity}: blocker-gated row lost its blocker")
        if identity not in W7_BLOCKER_GATED and not row["gate_decisions"]:
            fail(f"{identity}: decision-gated row lost its decision")

    # W7 gate partition and the "genuinely unnamed" claim, checked against
    # the Deliverable 8 Wave 6 paragraph itself.
    if W7_FALLTHROUGH & W7_D8_NAMED:
        fail("W7_FALLTHROUGH overlaps the Deliverable 8-named W7 rows")
    if set(W7_BASE_MAP) != (W7_FALLTHROUGH | W7_D8_NAMED):
        fail(
            "W7 gate set is not exactly W7_FALLTHROUGH | W7_D8_NAMED: "
            f"{sorted(set(W7_BASE_MAP) ^ (W7_FALLTHROUGH | W7_D8_NAMED))}"
        )
    for name in sorted(W7_D8_NAMED):
        if not re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", d8_wave6_text):
            fail(f"{name} is no longer named by the Deliverable 8 Wave 6 text")
    for name in sorted(W7_FALLTHROUGH):
        if re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", d8_wave6_text):
            fail(
                f"{name} now appears in the Deliverable 8 Wave 6 text; "
                "re-review the W7 fall-through split"
            )

    # Dependency flags cannot silently diverge from the governed row text.
    for row in register_rows:
        derived = derive_flags(rev[row["identity"]], d9_ple_bullet, d9_rows)
        for flag, value in derived.items():
            if row["dependency_flags"][flag] != value:
                fail(
                    f"{row['identity']}: dependency flag {flag} is {row['dependency_flags'][flag]} "
                    f"but the governed row text derives {value}"
                )

    # Merge bindings resolve to retained identities and keep their nuance.
    if "validatedBy" not in str(rev["validatesFitnessForUse"]["target"].get("merge_into")):
        fail("validatesFitnessForUse no longer merges into validatedBy")
    if by["validatedBy"]["accounting_status"] != "retained":
        fail("validatedBy is not a retained identity")
    shell_raw = str(rev["IncrementTraceabilityShell"]["target"].get("merge_into"))
    if "RequiredTraceChain" not in shell_raw:
        fail("IncrementTraceabilityShell no longer merges into the RequiredTraceChain successor intent")
    if by["RequiredTraceChain"]["accounting_status"] != "retained":
        fail("RequiredTraceChain is not a retained identity")
    if "decision-15" not in by["IncrementTraceabilityShell"]["merge_note"]:
        fail("IncrementTraceabilityShell merge note lost its decision-15 binding")

    # hasEvidenceStatus interpretation: structured row classification wins.
    if by["hasEvidenceStatus"]["base_wave"] != "W6":
        fail("hasEvidenceStatus must be handled in the redesign wave (W6)")

    # Deliverable 10 curated row lists must reference existing identities.
    for item in d10_items:
        for name in item["rows"]:
            if name not in rev:
                fail(f"decision-{item['number']} references unknown row {name}")

    # Frozen O3 set (also cross-checked in build_register).
    if sorted(r["identity"] for r in register_rows if r["o3_complete"]) != sorted(
        r["identity"] for r in review_rows if r.get("o3_protected")
    ):
        fail("frozen O3 identity set drifted between register and review")


def build_register(root: Path) -> dict[str, Any]:
    review = load_review(root)
    review_md = parse_review_md(root)
    rows = review["rows"]
    o3 = o3_identities()
    o3_review = sorted(r["identity"] for r in rows if r.get("o3_protected"))
    if sorted(o3) != o3_review:
        raise SystemExit(
            "frozen O3 identity set mismatch between runtime code and review: "
            f"code={sorted(o3)} review={o3_review}"
        )

    d9_rows = {name for item in review_md["decisions"] if item["number"] == 9 for name in D10_ROWS[9]}
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
        base_wave, basis = assign_base_wave(row)
        merged = bool(target.get("merge_into"))
        removed = row.get("migration_class") == "REMOVE_FROM_ONTOLOGY"
        accounting = "merged" if merged else ("removed" if removed else "retained")
        membership = "o3-complete" if row.get("o3_protected") else (
            "o4-target" if accounting == "retained" else accounting
        )
        dependencies = list(row.get("dependencies") or [])
        blockers = list(row.get("blockers") or [])
        other_targets = sorted(
            name
            for name in all_names
            if name != identity and any(name in dep for dep in dependencies)
        )
        gate_decisions = [
            f"decision-{item['number']}"
            for item in review_md["decisions"]
            if identity in D10_ROWS[item["number"]]
        ]
        gate_wave = "W7" if identity in W7_BASE_MAP else None
        gated_by_parts = []
        if gate_decisions:
            gated_by_parts.append("owner-decision")
        if blockers:
            gated_by_parts.append("row-blocker")
        flags = derive_flags(row, review_md["d9_ple_bullet"], d9_rows)
        merge_binding = MERGE_BINDINGS.get(identity, {})
        if accounting == "retained":
            retirement = RETIREMENT_TEMPLATES.get(base_wave or "", None)
            if gate_wave:
                retirement = (retirement or "") + GATED_SUFFIX
        elif removed:
            retirement = "retired; historical evidence retained (no migration target)"
        else:
            retirement = "merged away; intent carried by the named successor (no separate target)"
        register_rows.append(
            {
                "identity": identity,
                "kind": row.get("kind"),
                "review_index": index,
                "accounting_status": accounting,
                "membership": membership,
                "merge_into": merge_binding.get("merge_into") if merged else None,
                "merge_note": merge_binding.get("merge_note") if merged else None,
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
                "blockers": blockers,
                "open_decisions": list(row.get("open_decisions") or []),
                "dependencies": dependencies,
                "dependency_flags": {
                    **flags,
                    "other_targets": other_targets,
                },
                "base_wave": base_wave,
                "wave_basis": basis,
                "gate_wave": gate_wave,
                "gate_decisions": gate_decisions,
                "gated_by": " + ".join(gated_by_parts) if gated_by_parts else None,
                "corrections_batch": (
                    "inventory-description correction (no semantic change)" if identity in CORRECTIONS_BATCH_ROWS
                    else ("o3-side inventory-description recorded; frozen semantics untouched" if identity in CORRECTIONS_BATCH_O3_SIDE else None)
                ),
                "retirement_condition": retirement,
            }
        )

    retained = [r for r in register_rows if r["accounting_status"] == "retained"]
    o4_targets = [r for r in retained if not r["o3_complete"]]
    merged_rows = [r for r in register_rows if r["accounting_status"] == "merged"]
    removed_rows = [r for r in register_rows if r["accounting_status"] == "removed"]
    gated_rows = [r for r in register_rows if r["gate_wave"] == "W7"]

    # Hard accounting invariants.
    if len(register_rows) != 93:
        raise SystemExit(f"expected 93 accounted rows, got {len(register_rows)}")
    if len(retained) != 90:
        raise SystemExit(f"expected 90 retained rows, got {len(retained)}")
    if len(merged_rows) != 2 or len(removed_rows) != 1:
        raise SystemExit("expected exactly 2 merges and 1 removal")
    if len(o4_targets) != 77:
        raise SystemExit(f"expected exactly 77 O4 targets, got {len(o4_targets)}")
    expected_base_counts = {"W2": 35, "W3": 11, "W4": 10, "W5": 11, "W6": 9, "closure": 1}
    actual_base_counts = {w: sum(1 for r in o4_targets if r["base_wave"] == w) for w in expected_base_counts}
    if actual_base_counts != expected_base_counts:
        raise SystemExit(f"base-wave counts drifted: {actual_base_counts} != {expected_base_counts}")
    if sum(actual_base_counts.values()) != len(o4_targets):
        raise SystemExit("base-wave coverage is not exact: some O4 target lacks a base wave")
    if len(gated_rows) != 11:
        raise SystemExit(f"expected 11 W7-held rows, got {len(gated_rows)}")
    for r in retained:
        if r["base_wave"] is None:
            raise SystemExit(f"{r['identity']}: retained row without a base wave")
        if (r["gate_wave"] == "W7") != (r["identity"] in W7_BASE_MAP):
            raise SystemExit(f"{r['identity']}: gate_wave does not match the curated gate set")

    by_migration_class: dict[str, int] = {}
    by_disposition: dict[str, int] = {}
    for r in register_rows:
        by_migration_class[r["migration_class"]] = by_migration_class.get(r["migration_class"], 0) + 1
        by_disposition[str(r["final_disposition"])] = by_disposition.get(str(r["final_disposition"]), 0) + 1

    d10_items: list[dict[str, Any]] = []
    register_by_name = {r["identity"]: r for r in register_rows}
    for item in review_md["decisions"]:
        number = item["number"]
        curated_rows = D10_ROWS[number]
        base_waves = sorted(
            {
                register_by_name[name]["base_wave"]
                for name in curated_rows
                if name in register_by_name and register_by_name[name]["base_wave"]
            }
        )
        d10_items.append(
            {
                "id": f"decision-{number}",
                "decision": item["text"],
                "rows": curated_rows,
                "gates_base_waves": base_waves,
                "activity_gates": D10_ACTIVITY_GATES.get(number, []),
            }
        )

    check_mapping_assumptions(rows, register_rows, d10_items, review_md["d9_ple_bullet"], review_md["d8_wave6_text"])

    blockers_by_wave: dict[str, dict[str, list[str]]] = {}

    def wave_entry(wave_id: str) -> dict[str, list[str]]:
        return blockers_by_wave.setdefault(
            wave_id,
            {"review_open_decisions": [], "rows_with_row_blockers": [], "held_in_gate": []},
        )

    for item in d10_items:
        for wave_id in item["gates_base_waves"] + item["activity_gates"]:
            wave_entry(wave_id)["review_open_decisions"].append(item["id"])
    for r in register_rows:
        if r["blockers"] and r["base_wave"] and not r["gate_wave"]:
            wave_entry(r["base_wave"])["rows_with_row_blockers"].append(r["identity"])
        if r["gate_wave"] == "W7":
            wave_entry(r["base_wave"])["held_in_gate"].append(r["identity"])

    interpretations = [
        {
            "id": "interp-1",
            "statement": "The three MODEL_AUTHORITY_PARITY-classified signal rows are native-classified in the review but carry parity work; the explicit 26-row parity count takes precedence — they migrate with the definitions parity wave (W2).",
            "rows": ["SignalMappingDisposition", "LogicalToSoftwareSignalMappingRecord", "SystemToSoftwareSignalMappingCandidate"],
        },
        {
            "id": "interp-2",
            "statement": "Seventeen rows named in no Deliverable-8 burn-down wave are accounted by the execution mapping: ten F1 low-dependency rows enter W4; six F2 owner-gated architecture/evidence rows enter the W7 holding gate with base-wave re-entry; and DerivesFromNeed is retained as closure-accounting only.",
            "rows": sorted(set(W4_LOWDEP) | W7_FALLTHROUGH | {FALLTHROUGH_CLOSURE_ROW}),
        },
        {
            "id": "interp-3",
            "statement": "hasEvidenceStatus: the burn-down prose lists it with the external-boundary items, but the final structured row classification (REQUIRES_SEMANTIC_MIGRATION, disposition REDESIGN) takes precedence — it is handled in the redesign wave (W6). The source review is not modified; this is an execution-plan interpretation.",
            "rows": ["hasEvidenceStatus"],
        },
        {
            "id": "interp-4",
            "statement": "W7 is a decision/holding gate, not a semantic treatment: held rows carry base_wave (their curated, machine-checked re-entry destination), gate_wave W7 and their gate decisions/blockers; a review edit that invalidates a base or gate assumption fails the register gate.",
            "rows": sorted(W7_BASE_MAP),
        },
        {
            "id": "interp-5",
            "statement": "Decision-9 (PLE configurator authority) covers the configuration/selection rows only; native structural variation (VariationPoint, Variant, variesAt) projects without committing configurator authority, and PLE-domain rows that carry dependency flags but no gate keep their base waves.",
            "rows": sorted(set(D10_ROWS[9]) | {"VariationPoint", "Variant", "variesAt"}),
        },
        {
            "id": "interp-6",
            "statement": "Dependency flags are derived from the governed row text and anchors (PLE family + decision-9 + the Deliverable 9 PLE bullet + tokens; evidence >=2-token rule with the hasEvidence exception; SAF and canonical-architecture patterns); a review edit that changes an anchor fails the register gate.",
            "rows": [],
        },
    ]

    interp2 = next(item for item in interpretations if item["id"] == "interp-2")
    expected_interp2 = set(W4_LOWDEP) | W7_FALLTHROUGH | {FALLTHROUGH_CLOSURE_ROW}
    if len(interp2["rows"]) != 17 or set(interp2["rows"]) != expected_interp2:
        raise SystemExit(
            "interp-2 must account for exactly the 17 fall-through rows "
            f"(W4_LOWDEP | W7_FALLTHROUGH | {{{FALLTHROUGH_CLOSURE_ROW}}})"
        )
    if set(interp2["rows"]) & W7_D8_NAMED:
        raise SystemExit(
            "interp-2 must not contain rows explicitly named by Deliverable 8 Wave 6: "
            f"{sorted(set(interp2['rows']) & W7_D8_NAMED)}"
        )

    register = {
        "schema": REGISTER_SCHEMA,
        "generation": GENERATION,
        "source": {
            "integrated_review_path": str(REVIEW_PATH),
            "integrated_review_schema": review.get("schema"),
            "integrated_review_sha256": sha256_file(root / REVIEW_PATH),
            "review_md_path": str(REVIEW_MD_PATH),
            "review_md_sha256": sha256_file(root / REVIEW_MD_PATH),
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
            "by_base_wave": actual_base_counts,
            "by_migration_class": by_migration_class,
            "by_disposition": by_disposition,
            "gated_total": len(gated_rows),
        },
        "corrections_batch": {
            "review_mapping": "review Deliverable 8 Wave 1 (no model changes)",
            "activity_rows": sorted(CORRECTIONS_BATCH_ROWS),
            "o3_side_recorded": sorted(CORRECTIONS_BATCH_O3_SIDE),
            "doc_items": ["ADR 0009 status wording"],
        },
        "interpretations": interpretations,
        "blockers_by_wave": blockers_by_wave,
        "review_open_decisions": d10_items,
        "wave_dependencies": [
            {"wave": "W0", "requires": [], "unblocks": ["*"], "basis": "execution/gating infrastructure precedes all waves; complete accounting is a precondition for any migration claim"},
            {"wave": "W1", "requires": [], "unblocks": [], "basis": "correction batch (no model changes) precedes model-changing waves (review Deliverable 8 Wave 1)"},
            {"wave": "W2", "requires": [], "unblocks": ["W3", "W6"], "basis": "review Deliverable 8 dependency rule: parity unblocks the native/projection and redesign waves; W7-held definition rows re-enter here"},
            {"wave": "W3", "requires": ["W2"], "unblocks": ["W4"], "basis": "adoption/projection mechanics established before the low-dependency semantics rows reuse them; definition parity needed for their text"},
            {"wave": "W4", "requires": ["W2", "W3"], "unblocks": [], "basis": "low-dependency rows reuse parity text + projection mechanics"},
            {"wave": "W5", "requires": ["W2"], "unblocks": [], "independent_of": ["W3"], "basis": "review Deliverable 8: 'wave 3 is independent of 4'; external contracts need definition text from parity but not the projection rows"},
            {"wave": "W6", "requires": ["W2"], "unblocks": [], "basis": "successor definition text and parity must exist before redesigns bind"},
            {"wave": "W7", "kind": "gate", "requires": ["named owner decisions (Deliverable 10) and row blockers"], "unblocks": [], "basis": "held rows re-enter their base wave when the named decision/evidence resolves (review Deliverable 8 Wave 6 exit rule)"},
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
