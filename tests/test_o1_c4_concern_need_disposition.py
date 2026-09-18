"""O1 c4 — concern–need semantic disposition review (PR #249).

Covers the c4 disposition for exactly one identity:

- relationship ``derivesNeedFromConcern`` (``Need -> Concern``): the c4
  Outcome A decision — the pre-assumed predicate is **retired without
  replacement**. It has no required engineering meaning in the target
  architecture, no witness (no need frames, references, or addresses a
  concern anywhere in the governed model), and no consumer (zero runtime,
  MCP, viewer, conformance-evaluator, or model-transformation readers).
  Native Concern/Viewpoint semantics plus the existing Need
  ``source``/``rationale`` provenance remain; the predicate must not be
  emitted as an active O2 Semantic Projection relation.

The batch tests:

1.  exactly ``derivesNeedFromConcern`` comprises c4 (no second identity
    promoted; the global parity-reviewed set is the seven c1 rows plus the
    two c2 rows plus the c3 row plus this one);
2.  authority is unchanged: ``legacy-yaml`` (no O3 cutover) with the reviewed
    retirement target and parity-reviewed evidence;
3.  the reviewed decision records Outcome A, the three-claim decomposition,
    the concern-usage inventory, the native framing analysis, and the
    forward-only required evidence;
4.  the intentional-retirement representation is machine-enforced and cannot
    be conflated with ``unknown`` or ``blocked`` (schema unit laws plus
    inventory shape laws);
5.  ``addressesConcern`` remains ``EngineeringIncrement -> Concern`` and is
    not repurposed, generalized, or redefined (identifier-collision law);
6.  no ``motivatesNeed`` inverse, no Need-specific addresses-style relation,
    and no generic source predicate are introduced;
7.  Need ``source``/``rationale`` provenance is not declared satisfied by any
    concern link;
8.  the governed model still contains zero requirement/need-owned ``frame``
    concern usages (the c4 finding is drift-checked, not just documented);
9.  c1/c2/c3/K/PLE/c5 rows remain unchanged;
10. the generated inventory reproduces the reviewed c4 decision (red between
    Commit A and Commit B by design — the two-commit binding gate);
11. the inventory stays runtime-inert: no Semantic Projection row, no runtime
    reader, no closure evidence, no privileged claim, no dispatched
    privileged ingestion.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import authority_inventory as ai
from de4sdv.semantic.kernel_contract import KernelContract

REPO_ROOT = Path(__file__).resolve().parents[1]

INVENTORY_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/semantic-authority-inventory.json"
)
DECISIONS_PATH = (
    REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
)
CLOSURE_PATH = REPO_ROOT / "docs/method-conformance/o1/closure-evidence.json"
REVIEW_DOC = (
    REPO_ROOT / "docs/method-conformance/o1/c4-concern-need-disposition-review.md"
)
ONTOLOGY_PATH = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
TRAVERSAL_SOURCE = REPO_ROOT / "de4sdv/semantic/traversal.py"
PROJECTION_SOURCE = REPO_ROOT / "de4sdv/semantic/projection.py"

C4_IDENTITIES: tuple[str, ...] = ("derivesNeedFromConcern",)

#: The intentional-retirement target literal and its paired disposition.
RETIRED_TARGET = "retired"
RETIRED_DISPOSITION = "retire-without-replacement"

#: The seven c1 identities accepted as parity-reviewed (unchanged by c4).
C1_ACCEPTED: tuple[str, ...] = (
    "MethodPhase",
    "MethodContractObligation",
    "EvaluationSourceKind",
    "EvaluationScopeMembership",
    "TestedScopeDeclaration",
    "RetainedExecutionRecordReference",
    "AcceptanceAttestationReference",
)

#: The one c1 identity that stays incomplete (no c4 silent closure).
C1_INCOMPLETE: tuple[str, ...] = ("MethodEvaluationScope",)

#: The two c2 identities (unchanged by c4).
C2_IDENTITIES: tuple[str, ...] = ("VerificationCase", "verifiedBy")

#: The one c3 identity (unchanged by c4).
C3_IDENTITIES: tuple[str, ...] = ("hasSubject",)

#: PLE-family rows under the adoption gate (unchanged by c4).
PLE_GATED: tuple[str, ...] = (
    "FeatureConfiguration",
    "specifiesFeature",
    "specifiesCommonCapability",
    "appliesToMemberProduct",
    "selectsFeature",
    "includesCommonCapability",
    "variesAt",
    "selectsVariant",
)

#: K rows with the r6-3 closure record (unchanged by c4).
K_TRIPLE: tuple[str, ...] = (
    "DerivesFromNeed",
    "derivesRequirementFromNeed",
    "derivedRequirementsOfNeed",
)

#: c5 rows (unchanged by c4).
C5_ROWS: tuple[str, ...] = (
    "realizedBy",
    "specifiesFunction",
    "hasRelevantArchitecture",
    "hasRelevantEvidenceContract",
)

#: The six deferred unknown-TARGET rows (unchanged by c4 — target NOT
#: determined, which is deliberately distinct from intentional retirement).
UNKNOWN_TARGET_ROWS: tuple[str, ...] = (
    "AssuranceClaim",
    "allocatedTo",
    "deployedTo",
    "instantiatesCanonicalArchitecture",
    "validatedBy",
    "validatesFitnessForUse",
)

#: The fourteen remaining blocked rows after c4 and the c5 correction (the
#: eight PLE-family rows, the five T/E-style gated targets, and the
#: corrected ``hasRelevantEvidenceContract`` row whose declared
#: EvidenceContract range is not machine-resolvable at the reviewed
#: revision). ``derivesNeedFromConcern`` is no longer among them: a decided
#: retirement is not a block.
BLOCKED_ROWS_AFTER_C4: tuple[str, ...] = tuple(
    sorted(
        PLE_GATED
        + (
            "allocatedTo",
            "deployedTo",
            "instantiatesCanonicalArchitecture",
            "validatedBy",
            "validatesFitnessForUse",
            "hasRelevantEvidenceContract",
        )
    )
)

#: Governed model roots for the frame/concern scan.
GOVERNED_MODEL_DIRS: tuple[str, ...] = (
    "textual-notation-of-model/packages",
    "model-based-product-line-engineering",
)

#: Scan floor: fail closed if the scan machinery silently stops finding
#: governed frame sites (a vacuous pass would hide drift).
GOVERNED_FRAME_SITES_FLOOR = 60


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def decisions() -> dict:
    return yaml.safe_load(DECISIONS_PATH.read_text(encoding="utf-8"))


def _entries(inventory: dict, names=None) -> dict[str, dict]:
    by_identity = {entry["identity"]: entry for entry in inventory["entries"]}
    if names is None:
        return by_identity
    return {name: by_identity[name] for name in names}


def _decision_text(row: dict) -> str:
    parts = [str(row.get("note") or ""), str(row.get("exact_fit_decision") or "")]
    parts.extend(str(item) for item in row.get("required_evidence") or [])
    parts.extend(str(item) for item in row.get("unknowns") or [])
    return "\n".join(parts)


def _review_text() -> str:
    """Whitespace-normalized review-doc text (markdown wraps lines)."""
    return " ".join(REVIEW_DOC.read_text(encoding="utf-8").split())


def _contract() -> KernelContract:
    return KernelContract.load(ONTOLOGY_PATH)


def _observed_relationship() -> dict:
    return {
        "yaml_path": "relationships:probe",
        "domain": "Need",
        "range": "Concern",
        "grounding_kind": "yaml-vocabulary",
        "runtime_support": "vocabulary-only",
    }


def _reviewed_row(**overrides) -> dict:
    """A valid intentional-retirement reviewed row for schema probes."""
    row = {
        "authority_current": "legacy-yaml",
        "authority_target": RETIRED_TARGET,
        "evidence_state": "parity-reviewed",
        "adoption_status": "not-applicable",
        "transition_gate": None,
        "conditional_target": False,
        "disposition": RETIRED_DISPOSITION,
        "confidence": "high",
        "stage": "c4 (probe)",
        "note": "probe",
        "unknowns": [],
        "required_evidence": ["O2 probe", "O4 probe"],
        "exact_fit_decision": "not exact native fit",
        "closure_evidence_ref": None,
        "semantic_text_equivalence": None,
        "runtime_consumption": None,
    }
    row.update(overrides)
    return row


def _probe(**overrides) -> list[str]:
    return ai._entry_problems(
        "probe", "relationship", _observed_relationship(), _reviewed_row(**overrides), {}
    )


# ---------------------------------------------------------------------------
# Model scan machinery: brace-aware owner detection for ``frame`` / ``concern``
# ---------------------------------------------------------------------------

_OPEN_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|abstract|derived|ref|in|out)\s+)*"
    r"(package|part|requirement|viewpoint|concern|view|use case|action|analysis"
    r"|verification|connection|interface|state|calc|constraint|attribute)\b"
    r"[^\n;]*\{"
)
_FRAME_RE = re.compile(r"^\s*frame\s+([A-Za-z_]\w*)\s*;")
_CONCERN_USAGE_RE = re.compile(r"^\s*concern\s+([A-Za-z_]\w*)\s*:\s*([\w:]+)")


def _iter_governed_sites():  # type: ignore[no-untyped-def]
    """Yield (path, line_no, kind, name, owner_kind) for governed model sites.

    ``kind`` is ``"frame"`` or ``"concern-usage"``; ``owner_kind`` is the
    innermost enclosing declaration keyword from a small, explicit keyword
    set (brace-depth aware), or ``"file"`` at file scope.
    """
    for base in GOVERNED_MODEL_DIRS:
        for path in sorted((REPO_ROOT / base).rglob("*.sysml")):
            if ".sysand" in path.parts:
                continue
            lines = path.read_text(encoding="utf-8").splitlines()
            stack: list[tuple[int, str]] = []
            depth = 0
            for number, line in enumerate(lines, 1):
                owner = stack[-1][1] if stack else "file"
                frame = _FRAME_RE.match(line)
                if frame:
                    yield path, number, "frame", frame.group(1), owner
                concern = _CONCERN_USAGE_RE.match(line)
                if concern:
                    yield path, number, "concern-usage", concern.group(1), owner
                net = line.count("{") - line.count("}")
                opener = _OPEN_RE.match(line)
                if net > 0 and opener:
                    stack.append((depth + net, opener.group(1)))
                depth += net
                while stack and depth < stack[-1][0]:
                    stack.pop()


# ---------------------------------------------------------------------------
# Scope, decisions, and inventory state
# ---------------------------------------------------------------------------


class TestC4ScopeAndCounts:
    def test_c4_is_exactly_one_identity(self):
        assert C4_IDENTITIES == ("derivesNeedFromConcern",)

    def test_c4_identity_is_the_ontology_relationship(self, inventory, decisions):
        entry = _entries(inventory)["derivesNeedFromConcern"]
        assert entry["kind"] == "relationship"
        # The OBSERVED contract facts are unchanged by retirement: the row
        # still exists in the authored ontology with its Need -> Concern
        # domain/range; only the reviewed target/disposition change.
        assert entry["observed"]["domain"] == "Need"
        assert entry["observed"]["range"] == "Concern"
        assert "derivesNeedFromConcern" in decisions["entries"]

    def test_only_c4_identity_carries_the_c4_stage(self, inventory):
        staged = [
            entry["identity"]
            for entry in inventory["entries"]
            if str(entry["reviewed"]["stage"]).startswith("c4")
        ]
        assert staged == ["derivesNeedFromConcern"]

    def test_global_parity_set_advances_by_exactly_the_c4_row(self, inventory):
        """The global parity-reviewed set after c4: c1(7) + c2(2) + c3(1) +
        c4(1) = 11. The c5 batch has since executed too: the c5 file
        (tests/test_o1_c5_relevance_realization.py) owns the global set from
        c5 onward and, after the c5 correction, pins c1+c2+c3+c4+c5(3) = 14
        (the corrected hasRelevantEvidenceContract row is governed
        blocked/defer, not parity)."""
        parity = {
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "parity-reviewed"
        }
        assert parity == (
            set(C1_ACCEPTED)
            | set(C2_IDENTITIES)
            | set(C3_IDENTITIES)
            | set(C4_IDENTITIES)
            | (set(C5_ROWS) - {"hasRelevantEvidenceContract"})
        )
        assert len(parity) == 14

    def test_authority_current_remains_legacy_yaml(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["authority_current"] == "legacy-yaml"

    def test_authority_target_is_retired(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["authority_target"] == RETIRED_TARGET

    def test_disposition_is_retire_without_replacement(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["disposition"] == RETIRED_DISPOSITION

    def test_evidence_state_is_parity_reviewed(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["evidence_state"] == "parity-reviewed"

    def test_no_closure_evidence_and_no_privileged_claim(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["closure_evidence_ref"] is None
        assert entry["reviewed"]["evidence_state"] != "privileged-closure-proven"
        assert entry["reviewed"]["evidence_state"] != "exact-toolchain-validated"
        closure = json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))
        assert len(closure["records"]) == 1
        assert closure["records"][0]["id"] == "r6-3"
        assert "derivesNeedFromConcern" not in closure["records"][0][
            "subject_identities"
        ]

    def test_retired_row_is_not_conditional_and_has_no_gate(self, inventory):
        entry = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"]
        assert entry["reviewed"]["conditional_target"] is False
        assert entry["reviewed"]["transition_gate"] is None

    def test_no_new_semantic_projection_row(self):
        source = PROJECTION_SOURCE.read_text(encoding="utf-8")
        for name in C4_IDENTITIES:
            assert f'"{name}"' not in source, name

    def test_runtime_does_not_read_the_inventory_or_the_retired_identity(self):
        assert "NEVER imported by the semantic runtime" in (ai.__doc__ or "")
        runtime = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "authority_inventory" not in runtime
        assert "semantic-authority-inventory" not in runtime
        # The retired identity gains no traversal strategy and no mapping.
        assert "derivesNeedFromConcern" not in runtime

    def test_expected_evidence_state_counts(self, inventory):
        """c4 advances evidence maturity only: the retired row leaves the
        blocked set (14 -> 13) and joins parity-reviewed (10 -> 11). The c5
        batch then moved three rows to parity-reviewed (parity 11 -> 14,
        repository 65 -> 61) and its correction moved the
        hasRelevantEvidenceContract row to the governed blocked state
        (blocked 13 -> 14)."""
        assert inventory["evidence_state_counts"] == {
            "blocked": 14,
            "parity-reviewed": 14,
            "privileged-closure-proven": 3,
            "repository-evidenced": 61,
            "unknown": 1,
        }

    def test_expected_authority_target_counts(self, inventory):
        """Target descriptions move under the review chain: the c4 retirement
        moved one target row (de4sdv-application-semantic 5 -> 4; retired
        appears with 1); the O4 review correction batch (W1) then corrected
        the accepted-library labels of
        usesVerificationMethod/VerificationMethod (accepted-library-grounded
        12 -> 10; native-sysml 7 -> 8) and verifiedBy's description
        (native-sysml -> de4sdv-application-semantic;
        de4sdv-application-semantic 4 -> 5)."""
        assert inventory["authority_target_counts"] == {
            "accepted-library-grounded": 10,
            "de4sdv-application-semantic": 5,
            "external-reference": 2,
            "model-authoritative": 61,
            "native-sysml": 8,
            "retired": 1,
            "unknown": 6,
        }
        assert inventory["authority_current_counts"] == {
            "accepted-library-grounded": 2,
            "external-reference": 3,
            "legacy-yaml": 78,
            "model-authoritative": 3,
            "native-sysml": 6,
            "unknown": 1,
        }

    def test_conditional_target_counts_after_c4(self, inventory):
        """Resolving the former c4 conditional target leaves only the
        eight PLE-family conditional rows."""
        assert inventory["authority_target_conditional_counts"] == {
            "accepted-library-grounded": 8,
        }

    def test_c1_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for name in C1_ACCEPTED:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["authority_target"] == "model-authoritative", name
            assert row["evidence_state"] == "parity-reviewed", name
        for name in C1_INCOMPLETE:
            row = entries[name]["reviewed"]
            assert row["authority_current"] == "legacy-yaml", name
            assert row["evidence_state"] == "repository-evidenced", name

    def test_c2_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        verification = entries["VerificationCase"]["reviewed"]
        assert verification["authority_current"] == "native-sysml"
        assert verification["authority_target"] == "native-sysml"
        assert verification["evidence_state"] == "parity-reviewed"
        verified_by = entries["verifiedBy"]["reviewed"]
        assert verified_by["authority_current"] == "legacy-yaml"
        # O4 review correction (W1, finding 17): corrected from native-sysml.
        assert verified_by["authority_target"] == "de4sdv-application-semantic"
        assert verified_by["evidence_state"] == "parity-reviewed"

    def test_c3_row_unchanged(self, inventory):
        row = _entries(inventory)["hasSubject"]["reviewed"]
        assert row["stage"] == "c3 (hasSubject review batch)"
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "de4sdv-application-semantic"
        assert row["evidence_state"] == "parity-reviewed"
        assert row["disposition"] == "prove-existing-model-authority"

    def test_ple_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in PLE_GATED:
            row = entries[identity]["reviewed"]
            assert row["evidence_state"] == "blocked", identity
            assert row["adoption_status"] == "pinned-not-adopted", identity
            assert row["conditional_target"] is True, identity

    def test_k_rows_unchanged(self, inventory):
        entries = _entries(inventory)
        for identity in K_TRIPLE:
            row = entries[identity]["reviewed"]
            assert row["authority_current"] == "model-authoritative", identity
            assert row["evidence_state"] == "privileged-closure-proven", identity
            assert row["closure_evidence_ref"] == "r6-3", identity

    def test_c5_rows_unchanged(self, inventory):
        """The c5 batch has since executed (PR #249 c5), and its
        hasRelevantEvidenceContract row was then corrected by the
        independent review (c5 correction): three rows advanced to
        parity-reviewed as recorded in their own batch file — current
        authority unchanged (legacy-yaml), stage renamed to the executed
        batch — while the corrected row is governed blocked/defer."""
        entries = _entries(inventory)
        for identity in C5_ROWS:
            row = entries[identity]["reviewed"]
            assert row["stage"] == "c5 (relevance and realization review batch)", identity
            assert row["authority_current"] == "legacy-yaml", identity
        for identity in ("realizedBy", "specifiesFunction", "hasRelevantArchitecture"):
            row = entries[identity]["reviewed"]
            assert row["evidence_state"] == "parity-reviewed", identity
        corrected = entries["hasRelevantEvidenceContract"]["reviewed"]
        assert corrected["evidence_state"] == "blocked"
        assert corrected["disposition"] == "defer"
        assert corrected["transition_gate"]


# ---------------------------------------------------------------------------
# Reviewed decision (the source row)
# ---------------------------------------------------------------------------


class TestC4ReviewedDecision:
    def _row(self, decisions) -> dict:
        return decisions["entries"]["derivesNeedFromConcern"]

    def test_decision_records_outcome_a(self, decisions):
        text = _decision_text(self._row(decisions))
        assert "Outcome A" in text
        assert "retire without replacement" in text
        assert "retired" in text

    def test_decision_records_the_three_claim_decomposition(self, decisions):
        text = _decision_text(self._row(decisions))
        assert "origin provenance" in text
        assert "native framing" in text
        assert "weak concern addressing" in text
        # The claims are explicitly separated; framing is not called
        # provenance or weak addressing.
        assert "not provenance and not weak addressing" in text

    def test_decision_records_the_concern_usage_inventory_and_findings(
        self, decisions
    ):
        text = _decision_text(self._row(decisions))
        assert "23 governed need usages" in text
        assert "89 governed" in text
        assert "68 governed frame sites" in text
        assert "zero are requirement-owned" in text
        assert "FramedConcernMembership" in text
        assert "viewpoint-owned" in text

    def test_decision_records_the_consumer_finding(self, decisions):
        text = _decision_text(self._row(decisions))
        assert "no concrete query or consumer requires" in text
        assert "zero runtime, MCP, viewer, conformance-evaluator" in text

    def test_decision_records_the_identifier_collision_treatment(self, decisions):
        text = _decision_text(self._row(decisions))
        assert "addressesConcern" in text
        assert "EngineeringIncrement -> Concern" in text
        assert "not repurposed, not generalized" in text

    def test_decision_keeps_provenance_requirement_and_non_claims(self, decisions):
        text = _decision_text(self._row(decisions))
        # Provenance stays with source/rationale and is NOT satisfied by a
        # concern link.
        assert (
            "Need source/rationale provenance remains required and is not "
            "satisfied by any concern link" in text
        )
        # No inverse, no generic source predicate, no new ontology class.
        assert "motivatesNeed" in text  # recorded as a non-claim
        assert "no generic source predicate" in text
        assert "no new UseCase ontology class" in self._row(decisions)[
            "exact_fit_decision"
        ]

    def test_final_disposition_fields_are_machine_locked(self, decisions):
        row = self._row(decisions)
        assert row["authority_target"] == RETIRED_TARGET
        assert row["disposition"] == RETIRED_DISPOSITION
        assert row["evidence_state"] == "parity-reviewed"
        assert row["conditional_target"] is False
        assert row["transition_gate"] is None
        assert row["unknowns"] == []
        assert row["closure_evidence_ref"] is None

    def test_exact_fit_decision_is_populated_and_not_native(self, decisions):
        decision = self._row(decisions)["exact_fit_decision"]
        assert isinstance(decision, str)
        assert decision.strip()
        assert decision.startswith("not exact native fit")
        for fragment in (
            "retired without replacement",
            "Origin provenance",
            "Native framing",
            "Weak concern addressing",
            "required constraint",
            "satisfaction-condition claim",
            "No second modeled relationship",
        ):
            assert fragment in decision, fragment

    def test_required_evidence_is_forward_only(self, decisions):
        items = self._row(decisions)["required_evidence"]
        assert len(items) == 2
        assert items[0].startswith("O2 ")
        assert items[1].startswith("O4 ")
        joined = " ".join(items)
        # The former c4 gate items were completed BY c4; they must not remain
        # listed as outstanding, and no completed c4 work may be listed.
        assert "concern-usage" not in joined
        assert "claim boundary" not in joined
        assert "docs/method-conformance/o1" not in joined

    def test_review_doc_exists_and_names_the_decision(self):
        text = _review_text()
        for fragment in (
            "Outcome A",
            "retire without replacement",
            "retired",
            "NOT interchangeable",
            "FramedConcernMembership",
            "RequirementUsage::framedConcern",
            "viewpoint-owned",
            "not duplicated as concerns",
            "source/rationale",
            "addressesConcern",
            "EngineeringIncrement -> Concern",
            "89 governed concern usages",
            "23 governed need usages",
            "68 governed frame sites",
            "no concrete current query or consumer",
            "No `.sysml` file changed",
            "No privileged ingestion was dispatched for c4",
        ):
            assert fragment in text, fragment

    def test_review_doc_records_the_retirement_representation_rationale(self):
        text = _review_text()
        assert "retire-without-replacement" in text
        assert "intentionally retired" in text
        # The non-conflation of unknown / blocked / retired is documented.
        assert "not an unknown, not a block" in text
        assert "unknown" in text and "blocked" in text


# ---------------------------------------------------------------------------
# Retirement representation — schema unit laws
# ---------------------------------------------------------------------------


class TestRetirementRepresentationSchema:
    def test_target_vocabulary_extends_locations_with_retired(self):
        assert ai.AUTHORITY_TARGETS == ai.AUTHORITY_SOURCES + (RETIRED_TARGET,)
        assert RETIRED_TARGET not in ai.AUTHORITY_SOURCES
        # ``retired`` is a target state; it can never be a current location.
        assert "authority_current: retired" not in (
            ONTOLOGY_PATH.read_text(encoding="utf-8")
        )

    def test_disposition_vocabulary_contains_retirement(self):
        assert RETIRED_DISPOSITION in ai.DISPOSITIONS

    def test_valid_retired_row_passes_validation(self):
        assert _probe() == []

    def test_retired_target_requires_the_retirement_disposition(self):
        problems = _probe(disposition="introduce-minimal-de4sdv-relation")
        assert any("requires disposition" in problem for problem in problems)

    def test_retirement_disposition_requires_the_retired_target(self):
        problems = _probe(authority_target="legacy-yaml")
        assert any("requires authority_target 'retired'" in p for p in problems)

    def test_retired_row_cannot_be_conditional(self):
        problems = _probe(conditional_target=True, transition_gate="some gate")
        assert any("cannot carry a conditional target" in p for p in problems)

    def test_retired_row_has_no_transition_gate(self):
        problems = _probe(transition_gate="some gate")
        assert any("has no transition gate" in p for p in problems)

    def test_retired_row_cannot_be_blocked_or_unknown(self):
        for state in ("blocked", "unknown"):
            problems = _probe(evidence_state=state)
            assert any(
                "must carry a decided evidence state" in p for p in problems
            ), state

    def test_retired_is_unrepresentable_as_current_authority(self):
        problems = _probe(authority_current=RETIRED_TARGET)
        assert any("authority_current" in p for p in problems)

    def test_inventory_row_is_consistent_with_the_decisions_row(
        self, inventory, decisions
    ):
        """The generated artifact must reproduce the reviewed decision row
        (governance consistency between source and artifact)."""
        reviewed = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"][
            "reviewed"
        ]
        source = decisions["entries"]["derivesNeedFromConcern"]
        for field in (
            "authority_target",
            "disposition",
            "evidence_state",
            "conditional_target",
            "transition_gate",
            "unknowns",
            "required_evidence",
            "exact_fit_decision",
        ):
            assert reviewed[field] == source[field], field

    def test_artifact_declares_the_target_vocabulary(self, inventory):
        dimensions = inventory["dimensions"]
        assert dimensions.get("authority_target") == list(ai.AUTHORITY_TARGETS)
        assert RETIRED_TARGET not in dimensions["authority_source"]


# ---------------------------------------------------------------------------
# Non-conflation: intentionally retired vs unknown vs blocked
# ---------------------------------------------------------------------------


class TestIntentionalRetirementDistinguishable:
    def test_exactly_one_retired_row(self, inventory):
        retired = [
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["authority_target"] == RETIRED_TARGET
        ]
        assert retired == ["derivesNeedFromConcern"]

    def test_unknown_target_rows_are_untouched(self, inventory):
        unknown = sorted(
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["authority_target"] == "unknown"
        )
        assert unknown == sorted(UNKNOWN_TARGET_ROWS)

    def test_blocked_rows_after_c4_are_exactly_expected(self, inventory):
        blocked = sorted(
            entry["identity"]
            for entry in inventory["entries"]
            if entry["reviewed"]["evidence_state"] == "blocked"
        )
        assert blocked == sorted(BLOCKED_ROWS_AFTER_C4)
        assert "derivesNeedFromConcern" not in blocked

    def test_retired_row_is_not_blocked_or_unknown(self, inventory):
        reviewed = _entries(inventory, C4_IDENTITIES)["derivesNeedFromConcern"][
            "reviewed"
        ]
        assert reviewed["evidence_state"] not in {"blocked", "unknown"}

    def test_retired_never_appears_as_a_current_authority(self, inventory):
        for entry in inventory["entries"]:
            assert entry["reviewed"]["authority_current"] != RETIRED_TARGET
        assert RETIRED_TARGET not in inventory["authority_current_counts"]

    def test_retired_row_is_not_a_conditional_target(self, inventory):
        assert RETIRED_TARGET not in inventory["authority_target_conditional_counts"]
        for entry in inventory["entries"]:
            if entry["reviewed"]["authority_target"] == RETIRED_TARGET:
                assert entry["reviewed"]["conditional_target"] is False

    def test_decision_note_drops_the_former_blocked_gate_language(self, decisions):
        """The retired row must not still read as a blocked/deferred row: the
        former gate string and the former disposition are gone."""
        text = _decision_text(decisions["entries"]["derivesNeedFromConcern"])
        assert "concern-usage inventory resolves endpoint semantics" not in text
        assert "introduce-minimal-de4sdv-relation" not in text
        assert "Same family as K" not in text


# ---------------------------------------------------------------------------
# Identifier collision: addressesConcern stays increment-level
# ---------------------------------------------------------------------------


class TestAddressesConcernUntouched:
    def test_addresses_concern_contract_is_unchanged(self):
        relationships = _contract().relationships
        assert relationships["addressesConcern"]["domain"] == "EngineeringIncrement"
        assert relationships["addressesConcern"]["range"] == "Concern"
        # No mapping was silently attached or changed.
        assert "sysml_mapping" not in relationships["addressesConcern"]

    def test_derives_need_from_concern_contract_is_unchanged(self):
        relationships = _contract().relationships
        assert relationships["derivesNeedFromConcern"]["domain"] == "Need"
        assert relationships["derivesNeedFromConcern"]["range"] == "Concern"
        assert "sysml_mapping" not in relationships["derivesNeedFromConcern"]

    def test_addresses_concern_reviewed_row_is_unchanged(self, decisions):
        row = decisions["entries"]["addressesConcern"]
        assert row["authority_current"] == "legacy-yaml"
        assert row["authority_target"] == "model-authoritative"
        assert row["evidence_state"] == "repository-evidenced"
        assert row["disposition"] == "move-meaning-into-model"
        assert row["conditional_target"] is False
        assert row["stage"] == "batched-parity (post-0a/0b)"

    def test_addresses_concern_observed_entry_is_unchanged(self, inventory):
        observed = _entries(inventory)["addressesConcern"]["observed"]
        assert observed["domain"] == "EngineeringIncrement"
        assert observed["range"] == "Concern"
        assert observed["grounding_kind"] == "yaml-vocabulary"

    def test_no_silent_repurposing_anywhere_in_the_reviewed_dataset(
        self, decisions
    ):
        # The retired row never borrows the increment-level identity, and no
        # distinct need-specific addresses-style name appears as a row.
        assert "needAddressesConcern" not in decisions["entries"]

    def test_no_motivates_inverse_or_generic_source_predicate(self, decisions):
        assert "motivatesNeed" not in decisions["entries"]
        assert "traceToSource" not in decisions["entries"]
        ontology = ONTOLOGY_PATH.read_text(encoding="utf-8")
        for token in (
            "motivatesNeed",
            "needAddressesConcern",
            "derivesNeedFromUseCase",
            "derivesNeedFromRisk",
            "derivesNeedFromScenario",
            "traceToSource",
        ):
            assert token not in ontology, token
        runtime = TRAVERSAL_SOURCE.read_text(encoding="utf-8")
        assert "motivatesNeed" not in runtime
        assert "traceToSource" not in runtime

    def test_ontology_relationship_set_is_unchanged(self, decisions):
        raw = yaml.safe_load(ONTOLOGY_PATH.read_text(encoding="utf-8"))
        relationships = raw["relationships"]
        assert len(relationships) == 34
        assert "addressesConcern" in relationships
        assert "derivesNeedFromConcern" in relationships
        # The retired row keeps its contract shape: domain/range only.
        assert set(relationships["derivesNeedFromConcern"]) == {"domain", "range"}
        assert set(relationships["addressesConcern"]) == {"domain", "range"}


# ---------------------------------------------------------------------------
# Governed-model scan laws (the c4 finding, drift-checked)
# ---------------------------------------------------------------------------


class TestGovernedModelScanLaws:
    def test_no_requirement_or_need_owned_frame_sites(self):
        """The c4 finding: no need frames a concern. Every governed ``frame``
        site is viewpoint-owned (frame = viewpoint framing of its concerns);
        a requirement-owned frame site would void the reviewed basis and must
        fail this law, never pass silently."""
        sites = list(_iter_governed_sites())
        frames = [site for site in sites if site[2] == "frame"]
        assert len(frames) >= GOVERNED_FRAME_SITES_FLOOR, len(frames)
        offenders = [
            f"{path}:{number} owner={owner}"
            for path, number, _kind, _name, owner in frames
            if owner != "viewpoint"
        ]
        assert offenders == []
        requirement_owned = [
            (path, number)
            for path, number, _kind, _name, owner in frames
            if owner == "requirement"
        ]
        assert requirement_owned == []

    def test_no_requirement_owned_concern_usages(self):
        """No concern usage is owned by a requirement-like usage: concerns
        cannot be smuggled into the need bodies as direct members."""
        sites = list(_iter_governed_sites())
        concerns = [site for site in sites if site[2] == "concern-usage"]
        assert len(concerns) >= 80, len(concerns)
        offenders = [
            f"{path}:{number} owner={owner}"
            for path, number, _kind, _name, owner in concerns
            if owner == "requirement"
        ]
        assert offenders == []

    def test_frame_site_population_is_recorded_in_the_review_doc(self):
        """The review record cites the scan it was decided on (68 governed
        frame sites; all viewpoint-owned)."""
        text = _review_text()
        assert "68 governed frame sites" in text
        assert "all viewpoint-owned" in text
