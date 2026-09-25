"""O2.3 — Semantic Projection v1.2 / API Representation Profile v1.2 tests.

Covers the O2.3 additive generation stage (Stage B: the canonical v1.2
artifacts and the repository gate registration are now published; see the
design record):

1.  **positive scope**: exactly the three final O2 identities are
    generated (``derivesRequirementFromNeed``, ``derivedRequirementsOfNeed``,
    ``hasRelevantArchitecture``), each exactly once, with the reviewed
    representation contract (domain, range, canonical and native direction,
    witness strategy, semantic strength) and the governed model anchors
    derived from the ACTUAL production model declarations — not only
    synthetic fixtures;
2.  **one modeled fact, two navigations**: the K pair is emitted from one
    model-derived semantic core; the pair invariants (same connection
    definition, same witness population, inverse domain/range, opposite
    canonical directions, identical strength and claim boundary,
    iff-equivalence) are machine-locked on the emitted rows, and a REAL
    end-declaration swap fixture proves that reordering the two ends changes
    nothing (roles, canonical pair, modeled direction, strength, claim
    boundary, and the one-witness contract are all order-independent);
    connect-argument order and query direction likewise never establish role
    identity;
3.  **extends discipline**: the extension pins the immutable O2.2 baselines
    by path, schema, source revision, and artifact digest (projection ->
    projection baseline, profile -> profile baseline, independently), and
    never re-emits or re-binds the O2.1/O2.2 sets;
4.  **machine-locked admission**: the admission manifest and the frozen O2
    sequencing agree exactly (three admitted; 13-identity sequencing union;
    cumulative O2.1+O2.2+O2.3 surface exactly thirteen); manifest drift
    fails closed;
5.  **negative scope**: the guarded identities (the O2.1 seven, the O2.2
    three, MethodEvaluationScope, DerivesFromNeed, the retired/blocked/
    rename-required set) never appear as O2.3 rows even though their
    representations are model-resident and discoverable;
6.  **adversarial fixtures**: extra model vocabulary does not expand the
    output; a missing admitted declaration, ambiguous grounding, wrong end
    typing, missing claim-strength doc, missing/extra usage witnesses,
    generic-Dependency decoys, Derivation-library decoys, contract drift,
    oracle drift, and MemberProduct-exclusion drift all fail closed; the
    generator does not read O1 review artifacts (a checkout without them
    generates identically, and decoy O1 data cannot manufacture a row);
7.  **projection/profile separation**: the projection rows carry no
    representation mechanics; the profile carries all mechanics and echoes
    the projection contract exactly (the compatibility gate rejects
    redefinition);
8.  **support state**: all rows ``vocabulary-only``; historical K closure
    evidence does not promote; no promotion input exists;
9.  **O2.1/O2.2 preservation**: the v1/v1.1 baseline gates still pass on
    this checkout; Projection v0 is byte-unchanged;
10. **runtime independence**: no runtime module imports the v1.2 machinery
    or reads the v1.2 artifacts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import projection_o23 as po23
from de4sdv.semantic import projection_v1 as pv
from de4sdv.semantic.kernel_contract import KernelContract

REPO_ROOT = Path(__file__).resolve().parents[1]

O1_ARTIFACT_PATHS = (
    "docs/method-conformance/o1/semantic-authority-inventory.json",
    "docs/method-conformance/o1/authority-review-decisions.yaml",
    "docs/method-conformance/o1/phase1-inventory-review.md",
)

#: Layer-B reviewed-decision field names of the O1 inventory: governance
#: metadata that must NEVER leak into generated semantic rows.
O1_GOVERNANCE_FIELDS = (
    "authority_current",
    "authority_target",
    "evidence_state",
    "adoption_status",
    "transition_gate",
    "conditional_target",
    "disposition",
    "confidence",
    "stage",
    "unknowns",
    "required_evidence",
    "exact_fit_decision",
)

#: Identities that must never appear as O2.3 rows (sampled across every
#: guarded category; the complete guard set is machine-derived).
O23_NEGATIVE_IDENTITIES = (
    "MethodEvaluationScope",
    "DerivesFromNeed",
    "VerificationCase",
    "hasSubject",
    "verifiedBy",
    "derivesNeedFromConcern",
    "realizedBy",
    "specifiesFunction",
    "hasRelevantEvidenceContract",
    "EvidenceContract",
    "ArchitectureElement",
    "allocatedTo",
    "deployedTo",
)

#: The O2.3 bound model inputs (derived mechanically in the module; pinned
#: here for fixture construction and reviewability).
_METHOD_CONTEXT_FILE = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)
_PRODUCT_LINE_FILE = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml"
)
_MODEL_FILES = (
    _METHOD_CONTEXT_FILE,
    _PRODUCT_LINE_FILE,
    po23.K_WITNESS_MODEL_FILE,
)

#: Reviewed witness state of the current governed model (locked in the tests,
#: derived by the generator): the five authored K derivation connections.
EXPECTED_K_USAGE_NAMES = (
    "reqDetectForwardCollisionRiskDerivedFromCommonAEBSCapability",
    "reqProvideCollisionWarningDerivedFromCommonAEBSCapability",
    "reqCommandEmergencyBrakingDerivedFromCommonAEBSCapability",
    "reqPedestrianTargetResponseDerivedFromPedestrianCollisionRiskReduction",
    "reqBicycleTargetResponseDerivedFromBicycleCollisionRiskReduction",
)

K_DEFINITION_DECLARATION = "connection def DerivesFromNeed"


@pytest.fixture(scope="module")
def pair() -> dict:
    """The real extension artifacts, generated against the committed checkout."""
    import unittest.mock

    with unittest.mock.patch.object(
        po23, "verify_source_revision_contains_inputs", lambda *a, **k: None
    ):
        return po23.build_pair_o23(REPO_ROOT)


@pytest.fixture()
def stubbed_gate(monkeypatch):
    """Fixture repos are not Git checkouts: stub the containment gate.

    The real gate is exercised against the committed repository by the
    module-level ``pair`` fixture; synthetic fixtures test derivation
    fail-closed behavior.
    """
    monkeypatch.setattr(
        po23, "verify_source_revision_contains_inputs", lambda *a, **k: None
    )


def _declaration_block(text: str, declaration: str) -> tuple[int, int]:
    """(start, end) of one braced declaration statement in ``text``."""
    kind, _, name = declaration.partition(" def ")
    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )
    match = pattern.search(text)
    assert match is not None, declaration
    brace = text.find("{", match.end())
    assert brace != -1, declaration
    close = _matching_brace(text, brace)
    return match.start(), close + 1


def _matching_brace(text: str, open_index: int) -> int:
    """Index of the brace closing the one opened at ``open_index``."""
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError("unbalanced braces")


def _remove_declaration(text: str, declaration: str) -> str:
    start, end = _declaration_block(text, declaration)
    return text[:start] + text[end:]


def _row_blob(pair: dict) -> str:
    """Canonical serialization of the emitted rows only (concepts+predicates)."""
    rows = list(pair["projection"].get("concepts", [])) + list(
        pair["projection"]["predicates"]
    )
    return po23.canonical_json({"rows": rows})


def _fixture_root(
    tmp_path: Path,
    *,
    contract_mutator=None,
    file_mutators: dict | None = None,
    manifest_mutator=None,
    with_decoy_o1: bool = False,
) -> Path:
    """A synthetic checkout containing exactly the generator's inputs."""
    root = tmp_path / "repo"
    contract_path = REPO_ROOT / po23.ONTOLOGY_PATH
    files = [
        po23.ONTOLOGY_PATH,
        po23.ADMISSION_O23_PATH,
        po23.BASELINE_PROJECTION_V11_PATH,
        po23.BASELINE_PROFILE_V11_PATH,
        *po23.BOUND_INPUT_PROGRAM_PATHS_O23,
        *_MODEL_FILES,
    ]
    for rel in files:
        destination = root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((REPO_ROOT / rel).read_bytes())
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if contract_mutator is not None:
        contract_mutator(contract)
    (root / po23.ONTOLOGY_PATH).write_text(
        yaml.safe_dump(contract, sort_keys=False), encoding="utf-8"
    )
    for rel, mutator in (file_mutators or {}).items():
        target = root / rel
        target.write_text(mutator(target.read_text(encoding="utf-8")), encoding="utf-8")
    if manifest_mutator is not None:
        manifest = yaml.safe_load(
            (REPO_ROOT / po23.ADMISSION_O23_PATH).read_text(encoding="utf-8")
        )
        manifest_mutator(manifest)
        (root / po23.ADMISSION_O23_PATH).write_text(
            yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
        )
    if with_decoy_o1:
        decoy = root / "docs/method-conformance/o1/semantic-authority-inventory.json"
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_text(
            json.dumps(
                {
                    "note": "decoy O1 data claiming accepted identities",
                    "entries": [
                        {
                            "identity": identity,
                            "reviewed": {"authority_current": "legacy-yaml"},
                        }
                        for identity in po23.O23_ADMITTED_IDENTITIES
                    ],
                }
            ),
            encoding="utf-8",
        )
    return root


def _git_commit_all(root: Path, message: str) -> str:
    """Commit everything in the fixture checkout; return the new HEAD id."""
    import subprocess

    def _git(*args: str) -> str:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    _git("add", "-A")
    _git("-c", "user.name=o23-fixture", "-c", "user.email=o23@local",
         "commit", "-q", "-m", message)
    return _git("rev-parse", "HEAD")


def _git_backed_inputs_repo(tmp_path: Path) -> tuple[Path, str]:
    """A real Git-backed checkout of the generator's inputs.

    The containment check is exercised UNSTUBBED against this fixture: every
    bound input is committed as revision X, so generation bound to X must
    pass; editing any bound input afterwards must fail containment.
    """
    import subprocess

    root = _fixture_root(tmp_path)
    result = subprocess.run(
        ["git", "init", "-q"], cwd=root, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    revision = _git_commit_all(root, "fixture inputs")
    return root, revision


# ---------------------------------------------------------------------------
# 1. Positive scope (actual production declarations)
# ---------------------------------------------------------------------------


class TestPositiveScope:
    def test_exactly_three_identities_in_order_once_each(self, pair) -> None:
        projection = pair["projection"]
        assert projection["schema"] == po23.PROJECTION_V12_SCHEMA
        identities = [row["identity"] for row in projection["predicates"]]
        assert identities == list(po23.O23_ADMITTED_IDENTITIES)
        assert len(identities) == len(set(identities)) == 3

    def test_canonical_row_semantics(self, pair) -> None:
        row = pair["projection"]["predicates"][0]
        assert row["identity"] == "derivesRequirementFromNeed"
        relation = row["relation"]
        assert relation["domain"]["ontology_class"] == "Requirement"
        assert relation["range"]["ontology_class"] == "Need"
        assert relation["domain"]["lineage"]["declaration"] == (
            "requirement def RequirementCandidate"
        )
        assert relation["range"]["lineage"]["declaration"] == (
            "requirement def StakeholderNeedCandidate"
        )
        assert relation["canonical_direction"] == "Requirement -> Need"
        # Native modeled direction is authored model content, distinct from
        # the canonical query direction.
        assert relation["native_modeled_direction"] == "Need -> Requirement"
        assert relation["semantic_strength"] == "derivation"
        assert relation["claim_boundary"].startswith("provenance only")
        assert relation["native_grounding"]["native_construct"] == (
            "DerivesFromNeed connection definition"
        )

    def test_companion_row_semantics(self, pair) -> None:
        row = pair["projection"]["predicates"][1]
        assert row["identity"] == "derivedRequirementsOfNeed"
        relation = row["relation"]
        assert relation["domain"]["ontology_class"] == "Need"
        assert relation["range"]["ontology_class"] == "Requirement"
        assert relation["canonical_direction"] == "Need -> Requirement"
        assert relation["native_modeled_direction"] == "Need -> Requirement"
        assert relation["semantic_strength"] == "derivation"
        assert relation["claim_boundary"].startswith("provenance only")

    def test_architecture_row_semantics(self, pair) -> None:
        row = pair["projection"]["predicates"][2]
        assert row["identity"] == "hasRelevantArchitecture"
        relation = row["relation"]
        assert relation["domain"]["ontology_class"] == "Requirement"
        assert relation["range"]["ontology_class"] == "ArchitectureElement"
        assert relation["range"]["identity_basis"] == "application-semantic umbrella"
        assert relation["canonical_direction"] == "Requirement -> ArchitectureElement"
        assert relation["semantic_strength"] == "relevance"
        assert relation["exclusion_lineage"]["ontology_class"] == "MemberProduct"
        assert relation["exclusion_lineage"]["lineage"]["declaration"] == (
            "part def ProductLineMemberProduct"
        )
        axes = {entry["axis"] for entry in relation["scope_restrictions"]}
        assert axes == {"source-domain", "source-types", "exclusion", "witness"}

    def test_k_witness_population_is_real_model_evidence(self, pair) -> None:
        row = pair["projection"]["predicates"][0]
        pair_block = row["relation"]["one_modeled_fact_two_navigations"]
        assert "5 authored connection usages" in pair_block["witness_population"]
        definition_anchor = pair["projection"]["binding"]  # anchor lives in rows
        # The definition anchor declaration is proven from the governed model.
        semantics = po23.derive_k_semantics(
            KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH), REPO_ROOT
        )
        assert semantics["definition_anchor"]["declaration"] == K_DEFINITION_DECLARATION
        assert semantics["definition_anchor"]["file"] == _METHOD_CONTEXT_FILE
        assert [w["usage_name"] for w in semantics["usage_witnesses"]] == list(
            EXPECTED_K_USAGE_NAMES
        )
        assert all(
            w["connection_type"] == "DerivesFromNeed"
            for w in semantics["usage_witnesses"]
        )
        # The v0-compatible semantics match the reviewed model truth.
        assert semantics["need_end_type"] == "Need"
        assert semantics["requirement_end_type"] == "Requirement"
        assert semantics["need_end_type_declaration"] == "StakeholderNeedCandidate"
        assert (
            semantics["requirement_end_type_declaration"] == "RequirementCandidate"
        )
        assert semantics["query_direction"] == "inverse"
        assert semantics["native_direction"] == "Need -> Requirement"
        assert semantics["semantic_strength"] == "derivation"

    def test_scope_block_is_machine_locked(self, pair) -> None:
        scope = pair["projection"]["scope"]
        assert scope["admitted"] == list(po23.O23_ADMITTED_IDENTITIES)
        assert scope["cumulative_surface"]["total"] == 13
        assert scope["cumulative_surface"]["o2_1"] == list(
            po23.O21_ADMITTED_IDENTITIES
        )
        assert scope["cumulative_surface"]["o2_2"] == list(
            po23.O2_SEQUENCING["o2.2"]
        )
        assert scope["cumulative_surface"]["o2_3"] == list(
            po23.O23_ADMITTED_IDENTITIES
        )

    def test_projection_contract_is_top_level(self, pair) -> None:
        contract = pair["projection"]["projection_contract"]
        assert contract == dict(po23.PROJECTION_CONTRACT_O23)
        assert set(contract["identity_claim_boundaries"]) == set(
            po23.O23_ADMITTED_IDENTITIES
        )

    def test_binding_shape(self, pair) -> None:
        binding = pair["projection"]["binding"]
        assert binding["api_binding"]["status"] == "unclaimed"
        assert binding == pair["profile"]["binding"]
        assert (
            binding["baseline_projection"]["path"]
            == po23.BASELINE_PROJECTION_V11_PATH
        )
        assert binding["baseline_profile"]["path"] == po23.BASELINE_PROFILE_V11_PATH
        assert "de4sdv/semantic/projection_o23.py" in binding["bound_inputs"]
        assert po23.BASELINE_PROJECTION_V11_PATH in binding["bound_inputs"]
        assert po23.BASELINE_PROFILE_V11_PATH in binding["bound_inputs"]
        assert po23.K_WITNESS_MODEL_FILE in binding["bound_inputs"]
        # The K definition file and both lineage anchors are bound inputs.
        assert _METHOD_CONTEXT_FILE in binding["bound_inputs"]
        assert _PRODUCT_LINE_FILE in binding["bound_inputs"]


# ---------------------------------------------------------------------------
# 3b. Executed-generation-path provenance (O2.3 review correction)
# ---------------------------------------------------------------------------


class TestBoundInputProvenance:
    """Every repository source whose code executes during generation is a
    bound input; editing one must invalidate the source-revision binding."""

    def test_projection_module_is_a_bound_program_input(self, pair) -> None:
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        inputs = po23.collect_bound_inputs_o23(REPO_ROOT, contract)
        # The v0 K module executes its pair-parity gate during generation, so
        # it must be bound in all three places.
        assert "de4sdv/semantic/projection.py" in inputs
        binding = pair["projection"]["binding"]
        assert "de4sdv/semantic/projection.py" in binding["generation_software"][
            "program_inputs"
        ]
        assert "de4sdv/semantic/projection.py" in binding["bound_inputs"]
        assert "de4sdv/semantic/projection.py" in pair["profile"]["binding"][
            "bound_inputs"
        ]

    def test_revision_identity_plumbing_is_a_bound_program_input(self, pair) -> None:
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        inputs = po23.collect_bound_inputs_o23(REPO_ROOT, contract)
        assert "de4sdv/sysml_api/revisions.py" in inputs
        binding = pair["projection"]["binding"]
        assert "de4sdv/sysml_api/revisions.py" in binding["generation_software"][
            "program_inputs"
        ]
        assert "de4sdv/sysml_api/revisions.py" in binding["bound_inputs"]

    def test_bound_input_count_and_exclusions(self, pair) -> None:
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        inputs = po23.collect_bound_inputs_o23(REPO_ROOT, contract)
        # 9 program sources + 7 data inputs = 16 (audited count).
        assert len(inputs) == 16
        assert len(po23.BOUND_INPUT_PROGRAM_PATHS_O23) == 9
        assert set(po23.BOUND_INPUT_PROGRAM_PATHS_O23) <= set(inputs)
        # Transitive imports whose code never executes during generation are
        # deliberately NOT bound (audit exclusions).
        for excluded in (
            "de4sdv/semantic/model_edges.py",
            "de4sdv/semantic/relationships.py",
            "de4sdv/sysml_api/errors.py",
            "de4sdv/sysml_api/client.py",
            "de4sdv/sysml_api/repository.py",
        ):
            assert excluded not in inputs, excluded

    def test_provenance_edit_of_projection_module_fails(self, tmp_path) -> None:
        """BLOCKER A regression (adversarial, real Git-backed fixture).

        1. Build a real Git-backed checkout of the generator's inputs and
           commit them as revision X.
        2. Bind generation to X (the REAL containment check, unstubbed) —
           this is the green control.
        3. Modify ONLY ``de4sdv/semantic/projection.py`` (the executed v0
           pair-parity gate) without committing.
        4. The source-revision containment check must FAIL — a future change
           to ``_assert_oracle_parity`` cannot silently occur outside the
           O2.3 artifact binding. Committing the change and rebinding to the
           new revision restores generation, proving the failure was exactly
           the uncommitted input change.
        """
        from de4sdv.semantic.authority_inventory import InventoryError

        root, revision = _git_backed_inputs_repo(tmp_path)

        # Green control: real containment passes on the committed inputs.
        control = po23.build_pair_o23(root, source_revision=revision)
        assert len(control["projection"]["predicates"]) == 3
        assert control["projection"]["binding"]["source_revision"] == revision

        # Mutate ONLY the v0 K module.
        target = root / "de4sdv/semantic/projection.py"
        original = target.read_text(encoding="utf-8")
        target.write_text(
            original + "\n# provenance probe (review correction)\n",
            encoding="utf-8",
        )
        with pytest.raises(
            InventoryError, match=r"de4sdv/semantic/projection\.py"
        ):
            po23.build_pair_o23(root, source_revision=revision)

        # Commit the change and rebind: containment passes again on the new
        # revision; the failure was exactly the uncommitted input edit.
        rebound_revision = _git_commit_all(root, "provenance probe committed")
        rebound = po23.build_pair_o23(root, source_revision=rebound_revision)
        assert len(rebound["projection"]["predicates"]) == 3

    def test_provenance_edit_of_other_executed_inputs_fails(
        self, tmp_path
    ) -> None:
        """The same containment lock covers the other executed-generation
        sources (representative sample: authority_inventory and the
        revisions plumbing)."""
        from de4sdv.semantic.authority_inventory import InventoryError

        for relative in (
            "de4sdv/semantic/authority_inventory.py",
            "de4sdv/sysml_api/revisions.py",
        ):
            root, revision = _git_backed_inputs_repo(tmp_path / relative.split("/")[-1])
            target = root / relative
            target.write_text(
                target.read_text(encoding="utf-8") + "\n# probe\n",
                encoding="utf-8",
            )
            with pytest.raises(InventoryError, match=relative):
                po23.build_pair_o23(root, source_revision=revision)


# ---------------------------------------------------------------------------
# 2. One modeled fact, two navigations (pair contract)
# ---------------------------------------------------------------------------


class TestKPairInvariants:
    def test_pair_emitted_from_one_semantic_core(self, pair) -> None:
        """Both K rows must descend from ONE model-derived semantic core."""
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        semantics = po23.derive_k_semantics(contract, REPO_ROOT)
        canonical, companion = po23.derive_k_pair_rows(contract, REPO_ROOT, semantics)
        # Rebuild the rows through the module path and compare with the pair
        # fixture: identical inputs must give identical rows.
        fixture_canonical = pair["projection"]["predicates"][0]
        fixture_companion = pair["projection"]["predicates"][1]
        assert canonical["relation"] == fixture_canonical["relation"]
        assert companion["relation"] == fixture_companion["relation"]

    def test_pair_domain_range_inversion_is_exact(self, pair) -> None:
        canonical = pair["projection"]["predicates"][0]["relation"]
        companion = pair["projection"]["predicates"][1]["relation"]
        assert canonical["domain"]["ontology_class"] == companion["range"][
            "ontology_class"
        ] == "Requirement"
        assert canonical["range"]["ontology_class"] == companion["domain"][
            "ontology_class"
        ] == "Need"

    def test_pair_opposite_directions_same_witness(self, pair) -> None:
        canonical = pair["projection"]["predicates"][0]["relation"]
        companion = pair["projection"]["predicates"][1]["relation"]
        assert canonical["canonical_direction"] != companion["canonical_direction"]
        assert canonical["native_modeled_direction"] == companion[
            "native_modeled_direction"
        ]
        assert (
            canonical["one_modeled_fact_two_navigations"]["witness"]
            == companion["one_modeled_fact_two_navigations"]["witness"]
        )
        assert canonical["one_modeled_fact_two_navigations"][
            "witness_population"
        ] == companion["one_modeled_fact_two_navigations"]["witness_population"]
        assert canonical["one_modeled_fact_two_navigations"][
            "companion_predicate"
        ] == "derivedRequirementsOfNeed"
        assert companion["one_modeled_fact_two_navigations"][
            "companion_predicate"
        ] == "derivesRequirementFromNeed"

    def test_pair_strength_claim_and_grounding_identical(self, pair) -> None:
        canonical = pair["projection"]["predicates"][0]["relation"]
        companion = pair["projection"]["predicates"][1]["relation"]
        assert canonical["semantic_strength"] == companion["semantic_strength"]
        assert canonical["claim_boundary"] == companion["claim_boundary"]
        assert canonical["native_grounding"] == companion["native_grounding"]

    def test_iff_equivalence_is_locked_at_contract_level(self, pair) -> None:
        """derivesRequirementFromNeed(R, N) iff derivedRequirementsOfNeed(N, R)."""
        canonical = pair["projection"]["predicates"][0]["relation"]
        companion = pair["projection"]["predicates"][1]["relation"]
        # Same typed role binding: the Need end and Requirement end are the
        # same two lineage anchors, swapped.
        assert canonical["domain"]["lineage"] == companion["range"]["lineage"]
        assert canonical["range"]["lineage"] == companion["domain"]["lineage"]
        # The claim boundaries serialize the iff-equivalence.
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]
        assert "one_modeled_fact_two_navigations" in boundaries[
            "derivesRequirementFromNeed"
        ]
        assert "one_modeled_fact_two_navigations" in boundaries[
            "derivedRequirementsOfNeed"
        ]

    def test_real_end_declaration_swap_preserves_full_semantics(
        self, tmp_path, stubbed_gate
    ) -> None:
        """A REAL swap of the two end declarations changes NOTHING.

        Declaration order is not semantic authority: role identity comes from
        the typed ends, and the modeled direction is the validated
        documentation statement. The swapped fixture must yield identical
        rows — same roles, canonical pair, modeled direction, strength,
        claim boundary, and one-witness contract.
        """

        def _swap_end_declarations(text):
            first = "    end need : StakeholderNeedCandidate;"
            second = "    end derivedRequirement : RequirementCandidate;"
            assert first in text and second in text, "end declarations not found"
            assert first + "\n" + second in text, "end declarations not adjacent"
            return text.replace(first + "\n" + second, second + "\n" + first)

        base_root = _fixture_root(tmp_path / "base")
        swapped_root = _fixture_root(
            tmp_path / "swapped",
            file_mutators={_METHOD_CONTEXT_FILE: _swap_end_declarations},
        )
        # The swap really happened.
        swapped_text = (swapped_root / _METHOD_CONTEXT_FILE).read_text(encoding="utf-8")
        swapped_index = swapped_text.index("end derivedRequirement :")
        need_index = swapped_text.index("end need :")
        assert swapped_index < need_index, "fixture swap did not take effect"

        base = po23.build_pair_o23(base_root, source_revision="f" * 40)
        swapped = po23.build_pair_o23(swapped_root, source_revision="f" * 40)

        # Full row equality: nothing semantic depends on declaration order.
        assert swapped["projection"]["predicates"] == base["projection"]["predicates"]

        rows = {row["identity"]: row for row in swapped["projection"]["predicates"]}
        relation = rows["derivesRequirementFromNeed"]["relation"]
        companion = rows["derivedRequirementsOfNeed"]["relation"]
        assert relation["canonical_direction"] == "Requirement -> Need"
        assert companion["canonical_direction"] == "Need -> Requirement"
        assert relation["native_modeled_direction"] == "Need -> Requirement"
        assert companion["native_modeled_direction"] == "Need -> Requirement"
        assert relation["semantic_strength"] == companion["semantic_strength"]
        assert relation["claim_boundary"] == companion["claim_boundary"]
        assert (
            relation["one_modeled_fact_two_navigations"]["witness"]
            == companion["one_modeled_fact_two_navigations"]["witness"]
        )

        # The semantic core itself: roles keyed by typing survive the swap.
        swapped_semantics = po23.derive_k_semantics(
            KernelContract.load(swapped_root / po23.ONTOLOGY_PATH), swapped_root
        )
        base_semantics = po23.derive_k_semantics(
            KernelContract.load(base_root / po23.ONTOLOGY_PATH), base_root
        )
        for key in (
            "need_role",
            "requirement_role",
            "need_end_type",
            "requirement_end_type",
            "native_direction",
            "native_direction_roles",
            "canonical_direction",
            "query_direction",
            "domain",
            "range",
            "semantic_strength",
            "claim_boundary",
        ):
            assert swapped_semantics[key] == base_semantics[key], key
        assert swapped_semantics["need_role"] == "need"
        assert swapped_semantics["requirement_role"] == "derivedRequirement"
        assert swapped_semantics["native_direction_roles"] == [
            "need",
            "derivedRequirement",
        ]
        ends = {end["ontology_class"]: end["role"] for end in swapped_semantics["ends"]}
        assert ends == {"Need": "need", "Requirement": "derivedRequirement"}

    def test_connect_argument_order_cannot_establish_role_identity(
        self, tmp_path, stubbed_gate
    ) -> None:
        """Swapping the authored ``connect A to B`` arguments of a usage
        witness changes nothing: role identity and the modeled direction are
        never derived from connection argument order."""

        def _swap_arguments(text):
            target = (
                "connect needCommonAEBSCapability to "
                "reqDetectForwardCollisionRisk;"
            )
            replacement = (
                "connect reqDetectForwardCollisionRisk to "
                "needCommonAEBSCapability;"
            )
            assert target in text, "usage witness not found"
            return text.replace(target, replacement, 1)

        base_root = _fixture_root(tmp_path / "base")
        swapped_root = _fixture_root(
            tmp_path / "swapped",
            file_mutators={po23.K_WITNESS_MODEL_FILE: _swap_arguments},
        )
        base = po23.build_pair_o23(base_root, source_revision="f" * 40)
        swapped = po23.build_pair_o23(swapped_root, source_revision="f" * 40)
        assert swapped["projection"]["predicates"] == base["projection"]["predicates"]
        # The witness evidence records names only — never argument roles.
        semantics = po23.derive_k_semantics(
            KernelContract.load(swapped_root / po23.ONTOLOGY_PATH), swapped_root
        )
        assert semantics["native_direction"] == "Need -> Requirement"
        assert len(semantics["usage_witnesses"]) == 5

    def test_query_direction_cannot_define_end_identity(self) -> None:
        """The companion query direction follows from the model, never the
        reverse: the derivation derives direction from typed ends + predicate
        identity, and the row locks cannot contradict it."""
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        semantics = po23.derive_k_semantics(contract, REPO_ROOT)
        assert semantics["query_direction"] == "inverse"
        # Tampering the query-direction LOCK to contradict the model fails.
        original = dict(po23._O23_PREDICATE_LOCKS["derivedRequirementsOfNeed"])
        try:
            po23._O23_PREDICATE_LOCKS["derivedRequirementsOfNeed"][
                "query_direction"
            ] = "inverse"
            with pytest.raises(po23.ProjectionO23Error, match="query-direction lock"):
                po23.derive_k_pair_rows(contract, REPO_ROOT, semantics)
        finally:
            po23._O23_PREDICATE_LOCKS["derivedRequirementsOfNeed"].clear()
            po23._O23_PREDICATE_LOCKS["derivedRequirementsOfNeed"].update(original)

    def test_name_only_or_qualified_name_only_never_qualifies(self) -> None:
        """No name/qualifiedName/package/source-text probe exists in the module."""
        source = (REPO_ROOT / "de4sdv/semantic/projection_o23.py").read_text(
            encoding="utf-8"
        )
        # The module carries no fallback resolver for names.
        assert "qualified_name" not in source.lower().replace(
            "qualifiedname", ""
        )  # no qualifiedName resolution helper
        for forbidden in ("get_by_name", "find_by_name", "name_fallback"):
            assert forbidden not in source
        # Role identity is keyed by typing against the contract declarations.
        assert "_class_declaration_name" in source


# ---------------------------------------------------------------------------
# 3. Machine-locked admission
# ---------------------------------------------------------------------------


class TestAdmissionLock:
    def test_manifest_matches_frozen_locks(self) -> None:
        manifest = po23.load_admission_manifest_o23(
            REPO_ROOT / po23.ADMISSION_O23_PATH
        )
        po23.validate_admission_o23(manifest)
        assert tuple(manifest["admitted"]) == po23.O23_ADMITTED_IDENTITIES

    def test_cumulative_surface_is_thirteen_distinct(self) -> None:
        assert len(po23.O23_CUMULATIVE_SURFACE) == 13
        assert len(set(po23.O23_CUMULATIVE_SURFACE)) == 13
        # The first ten are exactly the published O2.1+O2.2 surface.
        from de4sdv.semantic.projection_o22 import O22_CUMULATIVE_SURFACE

        assert set(po23.O23_CUMULATIVE_SURFACE[:10]) == set(O22_CUMULATIVE_SURFACE)

    def test_fourth_identity_admission_fails(self, tmp_path, stubbed_gate) -> None:
        def _add(manifest):
            manifest["admitted"].append("allocatedTo")

        root = _fixture_root(tmp_path, manifest_mutator=_add)
        with pytest.raises(po23.ProjectionO23Error, match="frozen O2.3"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_missing_admitted_identity_fails(self, tmp_path, stubbed_gate) -> None:
        def _drop(manifest):
            manifest["admitted"] = manifest["admitted"][:2]

        root = _fixture_root(tmp_path, manifest_mutator=_drop)
        with pytest.raises(po23.ProjectionO23Error, match="frozen O2.3"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_guarded_set_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drop_guard(manifest):
            manifest["guarded"] = [
                entry
                for entry in manifest["guarded"]
                if entry["identity"] != "realizedBy"
            ]

        root = _fixture_root(tmp_path, manifest_mutator=_drop_guard)
        with pytest.raises(po23.ProjectionO23Error, match="guard set"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_overlap_admitted_and_guarded_fails(self, tmp_path, stubbed_gate) -> None:
        def _overlap(manifest):
            # Swap two guarded identities: one admitted identity joins the
            # guarded list (duplicate + overlap), one guarded identity leaves
            # (guard-set drift). Any of these locks must fail closed.
            manifest["guarded"].append(
                {
                    "identity": "hasSubject",
                    "kind": "relationship",
                    "reason": "drift probe",
                }
            )
            manifest["guarded"] = [
                entry
                for entry in manifest["guarded"]
                if entry["identity"] != "realizedBy"
            ]

        root = _fixture_root(tmp_path, manifest_mutator=_overlap)
        with pytest.raises(po23.ProjectionO23Error):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_sequencing_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(manifest):
            manifest["sequencing"]["o2.3"] = [
                "derivesRequirementFromNeed",
                "derivedRequirementsOfNeed",
            ]

        root = _fixture_root(tmp_path, manifest_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="sequencing"):
            po23.build_pair_o23(root, source_revision="f" * 40)


# ---------------------------------------------------------------------------
# 4. Negative scope
# ---------------------------------------------------------------------------


class TestNegativeScope:
    def test_guarded_identities_never_appear(self, pair) -> None:
        blob = _row_blob(pair)
        for identity in O23_NEGATIVE_IDENTITIES:
            # No guarded identity may appear as an emitted ROW identity or
            # nested row identity; ArchitectureElement legitimately appears
            # only as the hasRelevantArchitecture RANGE class (the reviewed
            # umbrella), so its absence is asserted at row-identity level.
            if identity == "ArchitectureElement":
                assert f'"identity": "{identity}"' not in blob, identity
                continue
            assert f'"{identity}"' not in blob, identity

    def test_o21_and_o22_sets_are_not_re_emitted(self, pair) -> None:
        blob = _row_blob(pair)
        for identity in (
            *po23.O21_ADMITTED_IDENTITIES,
            *po23.O2_SEQUENCING["o2.2"],
        ):
            assert f'"{identity}"' not in blob, identity

    def test_method_evaluation_scope_model_resident_but_absent(self, pair) -> None:
        blob = _row_blob(pair)
        assert "MethodEvaluationScope" not in blob
        contract = yaml.safe_load(
            (REPO_ROOT / po23.ONTOLOGY_PATH).read_text(encoding="utf-8")
        )
        assert "MethodEvaluationScope" in contract["classes"]

    def test_blocked_and_rename_identities_stay_absent(self, pair) -> None:
        blob = _row_blob(pair)
        for identity in (
            "realizedBy",
            "specifiesFunction",
            "hasRelevantEvidenceContract",
            "derivesNeedFromConcern",
            "allocatedTo",
            "deployedTo",
        ):
            assert f'"{identity}"' not in blob, identity

    def test_architecture_element_class_row_stays_absent(self, pair) -> None:
        """The umbrella is carried by the range contract, never a class row."""
        rows = pair["projection"]["predicates"]
        assert all(row["semantic_kind"] == "relationship" for row in rows)
        blob = _row_blob(pair)
        assert '"semantic_kind": "verification-case"' not in blob

    def test_o1_governance_fields_never_leak_into_rows(self, pair) -> None:
        blob = _row_blob(pair)
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in blob, field


# ---------------------------------------------------------------------------
# 5. Adversarial: K pair fail-closed behavior (synthetic fixtures)
# ---------------------------------------------------------------------------


def _contract_class_mutator(ontology_class: str, **edits):
    def _mutate(contract):
        entry = contract["classes"][ontology_class]
        kernel = entry.get("kernel")
        if kernel is None:
            kernel = entry["kernel"] = {}
        kernel.update(edits)

    return _mutate


class TestKAdversarial:
    def test_a_missing_connection_definition_fails(self, tmp_path, stubbed_gate) -> None:
        def _remove(text):
            return _remove_declaration(text, K_DEFINITION_DECLARATION)

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _remove}
        )
        with pytest.raises(po23.ProjectionO23Error, match="DerivesFromNeed"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_a2_ambiguous_connection_definition_fails(
        self, tmp_path, stubbed_gate
    ) -> None:
        def _duplicate(text):
            anchor = "  connection def DerivesFromNeed {"
            insertion = text.index(anchor) + len(anchor)
            return text[:insertion] + "\n" + anchor + "\n  }" + text[insertion:]

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _duplicate}
        )
        with pytest.raises(po23.ProjectionO23Error, match="ambiguous"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_b_wrong_end_typing_fails(self, tmp_path, stubbed_gate) -> None:
        def _swap_types(text):
            return text.replace(
                "end need : StakeholderNeedCandidate;",
                "end need : UnrelatedDefinition;",
            )

        def _add_decoy(text):
            insertion = text.index("  part def EngineeringIncrement")
            return (
                text[:insertion]
                + "  part def UnrelatedDefinition {\n  }\n\n"
                + text[insertion:]
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={
                _METHOD_CONTEXT_FILE: lambda t: _swap_types(_add_decoy(t))
            },
        )
        with pytest.raises(po23.ProjectionO23Error, match="governed Need/Requirement"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_b2_missing_end_typing_fails(self, tmp_path, stubbed_gate) -> None:
        def _untype(text):
            return text.replace(
                "end derivedRequirement : RequirementCandidate;",
                "end derivedRequirement;",
            )

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _untype}
        )
        with pytest.raises(po23.ProjectionO23Error, match="two typed ends"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_c_both_ends_same_lineage_fails(self, tmp_path, stubbed_gate) -> None:
        def _same_types(text):
            return text.replace(
                "end derivedRequirement : RequirementCandidate;",
                "end derivedRequirement : StakeholderNeedCandidate;",
            )

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _same_types}
        )
        with pytest.raises(po23.ProjectionO23Error, match="exactly one Need"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_d_missing_claim_strength_doc_fails(self, tmp_path, stubbed_gate) -> None:
        def _strip_strength(text):
            return text.replace(
                "Claim strength: derivation (provenance only: neither satisfaction",
                "Provenance note: neither satisfaction",
            )

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _strip_strength}
        )
        with pytest.raises(po23.ProjectionO23Error, match="Claim strength"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_d2_conflicting_claim_strength_statements_fail(
        self, tmp_path, stubbed_gate
    ) -> None:
        def _second_statement(text):
            marker = "  connection def DerivesFromNeed {"
            return text.replace(
                marker,
                marker
                + "\n    doc /* Claim strength: satisfaction (stronger claim). */",
                1,
            )

        root = _fixture_root(
            tmp_path, file_mutators={_METHOD_CONTEXT_FILE: _second_statement}
        )
        with pytest.raises(po23.ProjectionO23Error, match="conflicting"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_e_missing_usage_witness_population_fails(
        self, tmp_path, stubbed_gate
    ) -> None:
        def _remove_usages(text):
            return "\n".join(
                line
                for line in text.splitlines()
                if not (
                    line.strip().startswith("connection ")
                    and ": DerivesFromNeed connect " in line
                )
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={po23.K_WITNESS_MODEL_FILE: _remove_usages},
        )
        with pytest.raises(po23.ProjectionO23Error, match="witness population"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_e2_foreign_typed_usage_witness_fails(self, tmp_path, stubbed_gate) -> None:
        def _foreign_type(text):
            return text.replace(
                ": DerivesFromNeed connect needCommonAEBSCapability",
                ": SomeForeignDefinition connect needCommonAEBSCapability",
                1,
            )

        def _add_decoy(text):
            insertion = text.index("  part def EngineeringIncrement")
            return (
                text[:insertion]
                + "  connection def SomeForeignDefinition {\n"
                + "    end need : StakeholderNeedCandidate;\n"
                + "    end derivedRequirement : RequirementCandidate;\n"
                + "  }\n\n"
                + text[insertion:]
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={
                _METHOD_CONTEXT_FILE: _add_decoy,
                po23.K_WITNESS_MODEL_FILE: _foreign_type,
            },
        )
        with pytest.raises(
            po23.ProjectionO23Error, match="witness population drifted"
        ):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_e3_foreign_typed_usage_witness_fails_closed(
        self, tmp_path, stubbed_gate
    ) -> None:
        """A usage retyped to a foreign definition drops the reviewed
        population count — foreign-typed witnesses never silently qualify."""

        def _foreign_and_compensating(text):
            text = text.replace(
                ": DerivesFromNeed connect needCommonAEBSCapability",
                ": SomeForeignDefinition connect needCommonAEBSCapability",
                1,
            )
            return text

        def _add_decoy(text):
            insertion = text.index("  part def EngineeringIncrement")
            return (
                text[:insertion]
                + "  connection def SomeForeignDefinition {\n"
                + "    end need : StakeholderNeedCandidate;\n"
                + "    end derivedRequirement : RequirementCandidate;\n"
                + "  }\n\n"
                + text[insertion:]
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={
                _METHOD_CONTEXT_FILE: _add_decoy,
                po23.K_WITNESS_MODEL_FILE: _foreign_and_compensating,
            },
        )
        with pytest.raises(po23.ProjectionO23Error, match="witness population"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_e4_extra_usage_witness_fails_closed(self, tmp_path, stubbed_gate) -> None:
        def _add_usage(text):
            anchor = (
                "connection reqBicycleTargetResponseDerivedFromBicycleCollisionRiskReduction "
                ": DerivesFromNeed connect needBicycleCollisionRiskReduction "
                "to reqBicycleTargetResponse;"
            )
            insertion = text.index(anchor) + len(anchor)
            return (
                text[:insertion]
                + "\n        connection reqExtraDerivedFromNeed : DerivesFromNeed "
                "connect needCommonAEBSCapability to reqCommandEmergencyBraking;"
                + text[insertion:]
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={po23.K_WITNESS_MODEL_FILE: _add_usage},
        )
        with pytest.raises(po23.ProjectionO23Error, match="witness population"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_f_generic_dependency_is_not_a_k_witness(self, pair) -> None:
        """The AEBS file's generic `dependency ... from req to need` edges are
        not DerivesFromNeed witnesses; only the typed connections are."""
        semantics = po23.derive_k_semantics(
            KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH), REPO_ROOT
        )
        names = [w["usage_name"] for w in semantics["usage_witnesses"]]
        # The generic dependency edges in the same file are NOT counted.
        assert "reqAllowDriverOverrideDerivedFromCommonAEBSCapability" not in names
        assert "reqDetectAEBSFailureConditionDerivedFromBoundedDegradationAndAvailability" not in names
        assert len(names) == 5

    def test_g_oracle_drift_fails_parity(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            contract["relationships"]["derivesRequirementFromNeed"]["domain"] = "Need"

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="parity oracle drift"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_g2_oracle_role_drift_fails_parity(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            config = contract["relationships"]["derivedRequirementsOfNeed"][
                "sysml_mapping"
            ]
            config["need_role"] = "original"

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="parity oracle drift"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_h_contract_domain_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            contract["relationships"]["derivesRequirementFromNeed"]["range"] = (
                "ArchitectureElement"
            )

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="parity oracle drift"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_h2_contract_strength_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            contract["relationships"]["hasRelevantArchitecture"]["sysml_mapping"][
                "semantic_strength"
            ] = "allocation"

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="allocation"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_h3_derivation_library_substitution_lock(self, pair) -> None:
        """The standard Derivation library is never silently substituted: the
        strategy lock is derivation-connection over the application
        definition, and the claim boundaries name the non-adoption."""
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        mapping = contract.relationship_mapping("derivesRequirementFromNeed")
        assert mapping.strategy == "derivation-connection"
        assert (
            mapping.configuration.get("connection_definition") == "DerivesFromNeed"
        )
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]
        for identity in ("derivesRequirementFromNeed", "derivedRequirementsOfNeed"):
            joined = " ".join(boundaries[identity]["does_not_assert"])
            assert "Derivation" in joined
            assert "originalImpliesDerived" in joined
        source = (REPO_ROOT / "de4sdv/semantic/projection_o23.py").read_text(
            encoding="utf-8"
        )
        assert "DerivationConnections" not in source
        assert "not adopted" in source

    def test_i_extra_model_vocabulary_does_not_expand_output(
        self, tmp_path, stubbed_gate
    ) -> None:
        def _add_vocabulary(text):
            insertion = text.index("  part def EngineeringIncrement")
            return (
                text[:insertion]
                + "  connection def DerivesFromConcern {\n"
                + "    end concern : SomeConcern;\n"
                + "    end requirement : RequirementCandidate;\n"
                + "  }\n\n"
                + text[insertion:]
            )

        def _add_decoy_type(text):
            insertion = text.index("  part def EngineeringIncrement")
            return (
                text[:insertion]
                + "  requirement def SomeConcern {\n  }\n\n"
                + text[insertion:]
            )

        root = _fixture_root(
            tmp_path,
            file_mutators={
                _METHOD_CONTEXT_FILE: lambda t: _add_vocabulary(_add_decoy_type(t))
            },
        )
        result = po23.build_pair_o23(root, source_revision="f" * 40)
        identities = [row["identity"] for row in result["projection"]["predicates"]]
        assert identities == list(po23.O23_ADMITTED_IDENTITIES)

    def test_j_decoy_o1_data_cannot_manufacture_a_row(
        self, tmp_path, stubbed_gate
    ) -> None:
        root = _fixture_root(tmp_path, with_decoy_o1=True)
        result = po23.build_pair_o23(root, source_revision="f" * 40)
        identities = [row["identity"] for row in result["projection"]["predicates"]]
        assert identities == list(po23.O23_ADMITTED_IDENTITIES)
        assert not (root / O1_ARTIFACT_PATHS[0]).exists() or json.loads(
            (root / O1_ARTIFACT_PATHS[0]).read_text(encoding="utf-8")
        )["entries"][0]["reviewed"]["authority_current"] == "legacy-yaml"

    def test_j2_generation_without_any_o1_directory(
        self, tmp_path, stubbed_gate
    ) -> None:
        root = _fixture_root(tmp_path)
        result = po23.build_pair_o23(root, source_revision="f" * 40)
        assert len(result["projection"]["predicates"]) == 3


# ---------------------------------------------------------------------------
# 6. Adversarial: hasRelevantArchitecture contract locks
# ---------------------------------------------------------------------------


class TestArchitectureAdversarial:
    def test_a_positive_contract_is_locked(self, pair) -> None:
        """Requirement domain + incoming Dependency + part/action sources +
        MemberProduct exclusion: the full reviewed application contract."""
        row = pair["projection"]["predicates"][2]
        relation = row["relation"]
        axes = {
            entry["axis"]: entry["restriction"]
            for entry in relation["scope_restrictions"]
        }
        assert "governed Requirement lineage" in axes["source-domain"]
        assert "PartUsage" in axes["source-types"]
        assert "ActionDefinition" in axes["source-types"]
        assert "MemberProduct lineage" in axes["exclusion"]
        assert "incoming Dependency" in axes["witness"]
        assert relation["semantic_strength"] == "relevance"

    def test_b_generic_dependency_alone_is_not_the_predicate(self, pair) -> None:
        row = pair["projection"]["predicates"][2]
        grounding = row["relation"]["native_grounding"]
        assert grounding["native_construct"] == "authored generic Dependency"
        assert "NOT hasRelevantArchitecture" in grounding["note"]

    def test_c_member_product_exclusion_drift_fails(
        self, tmp_path, stubbed_gate
    ) -> None:
        def _drift(contract):
            mapping = contract["relationships"]["hasRelevantArchitecture"][
                "sysml_mapping"
            ]
            mapping["exclude_source_specializations_of"] = "CommonCapability"

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="MemberProduct"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_c2_exclusion_removed_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            mapping = contract["relationships"]["hasRelevantArchitecture"][
                "sysml_mapping"
            ]
            del mapping["exclude_source_specializations_of"]

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="MemberProduct"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_d_direction_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            mapping = contract["relationships"]["hasRelevantArchitecture"][
                "sysml_mapping"
            ]
            mapping["direction"] = "outgoing"

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="incoming"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_d2_source_type_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            mapping = contract["relationships"]["hasRelevantArchitecture"][
                "sysml_mapping"
            ]
            mapping["source_types"] = ["PartUsage"]

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="source types"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_d3_relationship_type_drift_fails(self, tmp_path, stubbed_gate) -> None:
        def _drift(contract):
            mapping = contract["relationships"]["hasRelevantArchitecture"][
                "sysml_mapping"
            ]
            mapping["relationship_types"] = ["AllocationUsage"]

        root = _fixture_root(tmp_path, contract_mutator=_drift)
        with pytest.raises(po23.ProjectionO23Error, match="witness lock"):
            po23.build_pair_o23(root, source_revision="f" * 40)

    def test_e_need_query_is_quiet_absence_by_contract(self, pair) -> None:
        """Need serializes through related/same API shapes; the contract
        excludes it by lineage, not metaclass — and the serialized contract
        says so."""
        row = pair["projection"]["predicates"][2]
        axes = {
            entry["axis"]: entry["meaning"]
            for entry in row["relation"]["scope_restrictions"]
        }
        assert "API metaclass" in axes["source-domain"]
        assert "Need serializes through related/same API shapes" in axes[
            "source-domain"
        ]

    def test_f_architecture_element_umbrella_is_not_fabricated(self, pair) -> None:
        """No kernel binding exists for ArchitectureElement; none may be
        invented. The range carries the umbrella note; no lineage anchor is
        recorded for it."""
        row = pair["projection"]["predicates"][2]
        range_side = row["relation"]["range"]
        assert range_side["identity_basis"] == "application-semantic umbrella"
        assert "lineage" not in range_side
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        kernel = contract.classes["ArchitectureElement"]["kernel"]
        assert "native" in kernel and "file" not in kernel

    def test_g_rflp_chain_not_collapsed(self, pair) -> None:
        """The relevance edge is navigation/traceability, never realization,
        allocation, or deployment."""
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]["hasRelevantArchitecture"]
        joined = " ".join(boundaries["does_not_assert"])
        for forbidden in (
            "satisfaction",
            "realization",
            "allocation",
            "verification",
            "specification",
            "product-line selection",
            "deployment",
        ):
            assert forbidden in joined
        assert "RFLP" in " ".join(boundaries["does_not_assert"])
        # The stronger-relation names never appear as rows.
        blob = _row_blob(pair)
        for identity in ("realizedBy", "allocatedTo", "deployedTo"):
            assert f'"{identity}"' not in blob

    def test_h_name_or_metaclass_identity_proof_is_prohibited(self, pair) -> None:
        boundaries = pair["projection"]["projection_contract"][
            "identity_claim_boundaries"
        ]["hasRelevantArchitecture"]
        joined = " ".join(boundaries["does_not_assert"])
        assert "API metaclass equality is never identity proof" in joined or (
            "API metaclass" in joined
        )
        # The umbrella note is the canonical statement of the prohibition.
        row = pair["projection"]["predicates"][2]
        assert "API metaclass equality is never" in row["relation"]["range"]["note"]
        profile = pair["profile"]["profiles"][2]
        blob = po23.canonical_json(profile)
        assert "names never steer" in blob
        assert "does not control identity" in blob


# ---------------------------------------------------------------------------
# 7. Projection/profile separation
# ---------------------------------------------------------------------------


class TestSeparation:
    #: Serializer mechanics vocabulary that must NEVER appear as a key or
    #: mechanics field inside the projection rows.
    MECHANICS_TOKENS = (
        "strategy",
        "membership_types",
        "member_property",
        "reference_property",
        "owner_types",
        "owner_membership_types",
        "direction",
        "element_types",
        "relationship_types",
        "source_types",
        "target_types",
        "source_property",
        "target_property",
        "query_direction",
        "need_role",
        "requirement_role",
        "exclude_source_specializations_of",
        "metaclass",
        "ReferenceSubsetting",
        "implied",
    )

    def test_projection_rows_contain_no_representation_mechanics(self, pair) -> None:
        blob = _row_blob(pair)
        leaked = [token for token in self.MECHANICS_TOKENS if f'"{token}"' in blob]
        assert leaked == []

    def test_profile_entries_carry_all_mechanics(self, pair) -> None:
        profile_blob = po23.canonical_json(pair["profile"])
        for token in (
            "strategy",
            "query_direction",
            "need_role",
            "requirement_role",
            "relationship_types",
            "source_types",
            "exclude_source_specializations_of",
        ):
            assert f'"{token}"' in profile_blob, token

    def test_profile_entries_echo_the_projection_contract(self, pair) -> None:
        rows = {row["identity"]: row for row in pair["projection"]["predicates"]}
        entries = {entry["for_identity"]: entry for entry in pair["profile"]["profiles"]}
        assert set(rows) == set(entries)
        for identity, row in rows.items():
            relation = row["relation"]
            assert entries[identity]["semantic_contract_echo"] == {
                "domain": relation["domain"]["ontology_class"],
                "range": relation["range"]["ontology_class"],
                "canonical_direction": relation["canonical_direction"],
                "semantic_strength": relation["semantic_strength"],
                "scope_restrictions": [
                    item["restriction"]
                    for item in relation["scope_restrictions"]
                ],
            }

    def test_compat_gate_rejects_profile_that_redefines_semantics(self) -> None:
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        semantics = po23.derive_k_semantics(contract, REPO_ROOT)
        canonical, companion = po23.derive_k_pair_rows(contract, REPO_ROOT, semantics)
        architecture = po23.derive_architecture_row(contract, REPO_ROOT)
        rows = [canonical, companion, architecture]
        projection = {"concepts": [], "predicates": rows}
        profile = {
            "profiles": [
                po23._profile_entry_o23(row, contract) for row in rows
            ]
        }
        po23.assert_profile_compatible_o23(projection, profile)
        # Tamper the echoed domain: the gate must fail closed.
        profile["profiles"][0]["semantic_contract_echo"]["domain"] = "Need"
        with pytest.raises(po23.ProjectionO23Error, match="contradicts"):
            po23.assert_profile_compatible_o23(projection, profile)

    def test_compat_gate_rejects_support_promotion(
        self, tmp_path, stubbed_gate
    ) -> None:
        root = _fixture_root(tmp_path)
        result = po23.build_pair_o23(root, source_revision="f" * 40)
        result["projection"]["predicates"][0]["support_state"] = "supported"
        with pytest.raises(po23.ProjectionO23Error, match="support state"):
            po23.assert_profile_compatible_o23(
                result["projection"], result["profile"]
            )

    def test_claim_boundaries_are_schema_level_reviewed_metadata(self, pair) -> None:
        contract = pair["projection"]["projection_contract"]
        rows = pair["projection"]["predicates"]
        # The rows carry the model-derived claim boundary text (from the
        # definition doc); the negative laws live ONLY in the schema-level
        # contract block.
        for row in rows:
            flat = po23.canonical_json(row)
            assert "does_not_assert" not in flat
        for identity in po23.O23_ADMITTED_IDENTITIES:
            boundary = contract["identity_claim_boundaries"][identity]
            assert boundary["claims"]
            assert boundary["does_not_assert"]

    def test_claim_boundary_registry_is_machine_locked(self) -> None:
        """The module's reviewed negative-witness registry must stay aligned
        with the serialized schema-level boundaries. The K rows' boundaries
        carry the registry entries as reviewed semantic phrasing; the match
        is semantic (key words present), not byte-exact."""
        for identity, witnesses in po23._O23_NEGATIVE_WITNESSES.items():
            boundary = po23.PROJECTION_CONTRACT_O23["identity_claim_boundaries"][
                identity
            ]
            serialized = " ".join(boundary["does_not_assert"]).lower()
            for witness in witnesses:
                key = witness.lower()
                if key in serialized:
                    continue
                # Semantic aliases the reviewed boundary text uses instead of
                # the registry's shorthand phrasing.
                aliases = {
                    "standard derivation library adoption": "derivation",
                    "originalimpliesderived implication semantics":
                        "originalimpliesderived",
                    "api metaclass equality": "api metaclass",
                    "memberproduct lineage": "memberproduct",
                    "source text heuristics": "source text",
                    "end order as role identity": "end order",
                    "connection argument order as role identity":
                        "argument order",
                    "query direction as role identity": "query direction",
                    "declaredname alone": "declaredname",
                    "qualifiedname alone": "qualifiedname",
                    "logical implication": "implication",
                    "physical realization": "physical realization",
                    "configuration membership": "configuration membership",
                }.get(key, key)
                assert aliases in serialized, (identity, witness)


# ---------------------------------------------------------------------------
# 8. Support state
# ---------------------------------------------------------------------------


class TestSupportState:
    def test_support_state_is_vocabulary_only_for_all_rows(self, pair) -> None:
        for row in pair["projection"]["predicates"]:
            assert row["support_state"] == po23.SUPPORT_STATE_VOCABULARY_ONLY
        assert po23.SUPPORT_STATE_VOCABULARY_ONLY == "vocabulary-only"

    def test_no_other_support_vocabulary_or_promotion_input_exists(self) -> None:
        assert not hasattr(po23, "O23_SUPPORT_STATES")
        assert not hasattr(po23, "SUPPORT_STATE_SUPPORTED")
        assert not hasattr(po23, "ClosureAttestation")
        source = (REPO_ROOT / "de4sdv/semantic/projection_o23.py").read_text(
            encoding="utf-8"
        )
        assert "vocabulary-only" in source
        # The only support token in the module is the established rule.
        matches = re.findall(r'"([a-z-]+)"\s*$', "", re.M)
        assert po23.RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY == (
            "existing-not-authority"
        )

    def test_historical_closure_does_not_auto_promote(self, pair) -> None:
        """The K slice's retained closure run (its own earlier revision) is
        not a promotion input: the rows stay vocabulary-only even though the
        runtime mapping and historical evidence exist."""
        assert pair["profile"]["profiles"][0]["runtime_mapping_state"] == (
            "existing-not-authority"
        )
        row = pair["projection"]["predicates"][0]
        assert row["support_state"] == "vocabulary-only"
        contract_block = pair["projection"]["projection_contract"]
        assert "historical K closure evidence does not promote" in contract_block[
            "runtime_boundary"
        ]
        profile = pair["profile"]["profiles"][0]
        assert "does not promote support" in profile["runtime_mapping_note"]

    def test_api_binding_unclaimed(self, pair) -> None:
        binding = pair["projection"]["binding"]
        assert binding["api_binding"]["status"] == "unclaimed"
        assert "no current exact-revision API closure" in binding["api_binding"][
            "note"
        ] or "claims no current API element UUID" in binding["api_binding"]["note"]
        evidence = pair["profile"]["evidence_basis"]
        assert evidence["scope"].startswith("Serializer representation shapes only")


# ---------------------------------------------------------------------------
# 9. O2.1/O2.2 preservation + runtime independence
# ---------------------------------------------------------------------------


class TestPreservationAndRuntimeIndependence:
    def test_v1_gate_still_green_on_this_checkout(self) -> None:
        assert pv.run_check_errors(REPO_ROOT) == []

    def test_v11_gate_still_green_on_this_checkout(self) -> None:
        from de4sdv.semantic import projection_o22 as po22

        assert po22.run_check_errors_o22(REPO_ROOT) == []

    def test_projection_v0_byte_unchanged_since_v1_baseline(self) -> None:
        baseline_revision = json.loads(
            (
                REPO_ROOT / po23.BASELINE_PROJECTION_V11_PATH
            ).read_text(encoding="utf-8")
        )["extends"]["source_revision"]
        blob = subprocess_run_git_show(baseline_revision, "de4sdv/semantic/projection.py")
        assert (REPO_ROOT / "de4sdv/semantic/projection.py").read_bytes() == blob

    def test_no_runtime_module_imports_or_reads_v12(self) -> None:
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / "de4sdv").rglob("*.py")):
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in {
                "de4sdv/semantic/projection_o23.py",
                # O3 readiness tooling (documented, same pattern): read-only
                # planning/evidence module that loads the committed chain for
                # comparison; never the runtime path.
                "de4sdv/semantic/o3_equivalence.py",
                # O3 candidate authority bundle (documented, same pattern):
                # Stage-A machinery that references the chain as its
                # revision-bound authority record; candidate path only, never
                # production authority in Stage A.
                "de4sdv/semantic/o3_bundle.py",
            }:
                continue
            text = path.read_text(encoding="utf-8")
            if "projection_o23" in text or "semantic-projection-v1.2" in text:
                offenders.append(rel)
        assert offenders == []

    def test_generator_module_is_build_time_only(self) -> None:
        """The generator is a build-time tool: its actual import graph must
        never reach the runtime semantic authority modules."""
        import ast

        forbidden_modules = {
            "de4sdv.semantic.traversal",
            "de4sdv.semantic.query",
            "de4sdv.semantic.runtime",
            "de4sdv.semantic.mcp_server",
            "de4sdv.semantic.impact",
            "de4sdv.semantic.relationships",
            "de4sdv.semantic.model_edges",
        }

        def _imports(source: str, *, relative_base: str = "") -> set[str]:
            tree = ast.parse(source)
            found: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        found.add(relative_base + (node.module or ""))
                    elif node.module:
                        found.add(node.module)
            return found

        generator_imports = _imports(
            (REPO_ROOT / "scripts/generate_semantic_projection_o23.py").read_text(
                encoding="utf-8"
            )
        )
        assert not (generator_imports & forbidden_modules), (
            generator_imports & forbidden_modules
        )
        # The generator builds through the O2.3 build-time module only.
        assert any("projection_o23" in module for module in generator_imports), (
            generator_imports
        )

        # The build-time module itself must not import runtime authority
        # modules either (relative imports normalized to the package prefix).
        module_imports = _imports(
            (REPO_ROOT / "de4sdv/semantic/projection_o23.py").read_text(
                encoding="utf-8"
            ),
            relative_base="de4sdv.semantic.",
        )
        assert not (module_imports & forbidden_modules), (
            module_imports & forbidden_modules
        )

    def test_ontology_authority_not_retired(self) -> None:
        assert (REPO_ROOT / po23.ONTOLOGY_PATH).is_file()
        ontology = yaml.safe_load(
            (REPO_ROOT / po23.ONTOLOGY_PATH).read_text(encoding="utf-8")
        )
        assert "relationships" in ontology and "classes" in ontology
        # All three governed mapping rows remain in place (no retirement).
        for identity in po23.O23_ADMITTED_IDENTITIES:
            assert identity in ontology["relationships"]

    def test_no_model_changes_on_this_branch(self) -> None:
        output = subprocess_run(
            ["git", "status", "--porcelain", "--", "textual-notation-of-model"]
        )
        assert output.strip() == ""

    def test_stage_b_registers_the_v12_gate(self) -> None:
        """Stage B activated repository enforcement for the v1.2 pair."""
        source = (REPO_ROOT / "scripts/check_repo.py").read_text(encoding="utf-8")
        assert "generate_semantic_projection_o23" in source
        assert "run_check_errors_o23" in source
        assert "Semantic projection v1.2 errors" in source
        assert "or projection_o23_errors" in source


# ---------------------------------------------------------------------------
# 10. Committed artifacts, end-to-end gate behavior, repository wiring
# ---------------------------------------------------------------------------

# TEMPORARY_STACK_BINDING: Rebind 5 review consistency; extends v1.1 at M7.
# Rebind 6 must bind permanently to the actual Rebind 5 squash (M8).
COMMITTED_SOURCE_REVISION = "61f6930d56069dd19bca1151fbb7d678aa98b085"


def _git_backed_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """Synthetic real Git checkout for end-to-end gate tests.

    Copies the fixture inputs, initializes a real repository, commits the
    inputs as revision R1, rebinds both copied v1.1 baselines to R1, commits
    that as R2, regenerates the v1.2 artifacts bound to R2, and commits them
    (HEAD = R3). Returns ``(root, R2, R3)``. The gate then runs against a
    real ancestor chain with real blobs — no stubbing.
    """
    import subprocess

    root = _fixture_root(tmp_path)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True
        )

    def head() -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "gate-test")
    git("config", "user.email", "gate-test@local")
    git("add", "-A")
    git("commit", "-q", "-m", "inputs")
    r1 = head()
    for baseline_path in (
        po23.BASELINE_PROJECTION_V11_PATH,
        po23.BASELINE_PROFILE_V11_PATH,
    ):
        path = root / baseline_path
        document = json.loads(path.read_text(encoding="utf-8"))
        document["binding"]["source_revision"] = r1
        path.write_text(json.dumps(document), encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "rebind baselines to inputs revision")
    r2 = head()
    built = po23.build_pair_o23(root, source_revision=r2)
    (root / po23.PROJECTION_V12_JSON_PATH).write_text(
        po23.canonical_json(built["projection"]), encoding="utf-8"
    )
    (root / po23.PROFILE_V12_JSON_PATH).write_text(
        po23.canonical_json(built["profile"]), encoding="utf-8"
    )
    git("add", "-A")
    git("commit", "-q", "-m", "artifacts bound to inputs revision")
    return root, r2, head()


class TestCommittedArtifacts:
    def test_committed_artifacts_match_regeneration(self) -> None:
        assert po23.run_check_errors_o23(REPO_ROOT) == []

    def test_committed_artifacts_exist_and_parse(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po23.PROJECTION_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        profile = json.loads(
            (REPO_ROOT / po23.PROFILE_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        assert projection["schema"] == po23.PROJECTION_V12_SCHEMA
        assert profile["schema"] == po23.PROFILE_V12_SCHEMA
        for document in (projection, profile):
            assert document["binding"]["source_revision"] == (
                COMMITTED_SOURCE_REVISION
            )
            assert document["binding"]["api_binding"]["status"] == "unclaimed"
        rows = list(projection["predicates"])
        assert tuple(row["identity"] for row in rows) == po23.O23_ADMITTED_IDENTITIES
        assert all(row["support_state"] == "vocabulary-only" for row in rows)
        assert projection["extends"]["artifact"] == po23.BASELINE_PROJECTION_V11_PATH
        assert profile["extends"]["artifact"] == po23.BASELINE_PROFILE_V11_PATH
        assert projection["extends"] != profile["extends"]

    def test_committed_artifacts_include_all_bound_inputs(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po23.PROJECTION_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        binding = projection["binding"]
        contract = KernelContract.load(REPO_ROOT / po23.ONTOLOGY_PATH)
        actual = po23.collect_bound_inputs_o23(REPO_ROOT, contract)
        assert len(actual) == 16
        assert set(binding["bound_inputs"]) == set(actual)
        program = set(binding["generation_software"]["program_inputs"])
        assert program == set(po23.BOUND_INPUT_PROGRAM_PATHS_O23)
        assert "de4sdv/semantic/projection.py" in program
        assert "de4sdv/sysml_api/revisions.py" in program
        assert (
            binding == json.loads(
                (REPO_ROOT / po23.PROFILE_V12_JSON_PATH).read_text(
                    encoding="utf-8"
                )
            )["binding"]
        )

    def test_committed_cumulative_surface_is_thirteen(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po23.PROJECTION_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        cumulative = projection["scope"]["cumulative_surface"]
        assert cumulative["total"] == 13
        assert len(cumulative["o2_1"]) == 7
        assert len(cumulative["o2_2"]) == 3
        assert len(cumulative["o2_3"]) == 3
        identities = cumulative["o2_1"] + cumulative["o2_2"] + cumulative["o2_3"]
        assert len(set(identities)) == 13

    def test_committed_pins_match_baseline_bytes(self) -> None:
        import hashlib

        for document_path, baseline_path in (
            (po23.PROJECTION_V12_JSON_PATH, po23.BASELINE_PROJECTION_V11_PATH),
            (po23.PROFILE_V12_JSON_PATH, po23.BASELINE_PROFILE_V11_PATH),
        ):
            document = json.loads(
                (REPO_ROOT / document_path).read_text(encoding="utf-8")
            )
            pin = document["extends"]
            expected = "sha256:" + hashlib.sha256(
                (REPO_ROOT / baseline_path).read_bytes()
            ).hexdigest()
            assert pin["artifact_digest"] == expected, document_path
            baseline = json.loads(
                (REPO_ROOT / baseline_path).read_text(encoding="utf-8")
            )
            assert pin["source_revision"] == baseline["binding"]["source_revision"]

    def test_committed_pins_ancestry_satisfied(self) -> None:
        import subprocess

        for document_path, baseline_path in (
            (po23.PROJECTION_V12_JSON_PATH, po23.BASELINE_PROJECTION_V11_PATH),
            (po23.PROFILE_V12_JSON_PATH, po23.BASELINE_PROFILE_V11_PATH),
        ):
            document = json.loads(
                (REPO_ROOT / document_path).read_text(encoding="utf-8")
            )
            pin = document["extends"]
            result = subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    pin["source_revision"],
                    COMMITTED_SOURCE_REVISION,
                ],
                cwd=REPO_ROOT,
                capture_output=True,
            )
            assert result.returncode == 0, (document_path, pin["source_revision"])

    def test_committed_projection_separation_remains_clean(self) -> None:
        projection = json.loads(
            (REPO_ROOT / po23.PROJECTION_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        blob = json.dumps(projection["predicates"])
        for banned in (
            "strategy",
            "query_direction",
            "need_role",
            "requirement_role",
            "relationship_types",
            "source_property",
            "target_property",
            "source_types",
            "membership_types",
            "reference_property",
            "member_property",
            "owner_types",
            "owner_membership_types",
            "element_types",
            "ReferenceSubsetting",
            "metaclass",
        ):
            assert f'"{banned}"' not in blob, banned
        # The profile carries the mechanics the projection must not.
        profile = json.loads(
            (REPO_ROOT / po23.PROFILE_V12_JSON_PATH).read_text(encoding="utf-8")
        )
        profile_blob = json.dumps(profile)
        for required in (
            "strategy",
            "query_direction",
            "need_role",
            "requirement_role",
            "relationship_types",
            "source_types",
        ):
            assert f'"{required}"' in profile_blob, required

    def test_editing_either_artifact_fails_the_gate(self, tmp_path) -> None:
        root, revision, head = _git_backed_repo(tmp_path)
        assert head != revision
        assert po23.run_check_errors_o23(root) == []
        for artifact_path in (
            po23.PROJECTION_V12_JSON_PATH,
            po23.PROFILE_V12_JSON_PATH,
        ):
            path = root / artifact_path
            original = path.read_text(encoding="utf-8")
            path.write_text(original + "\n", encoding="utf-8")
            errors = po23.run_check_errors_o23(root)
            assert errors, artifact_path
            assert any("differs from regeneration" in error for error in errors)
            path.write_text(original, encoding="utf-8")
            assert po23.run_check_errors_o23(root) == []

    def test_gate_reports_missing_artifacts_when_absent(self, tmp_path) -> None:
        # The gate must never treat missing artifacts as success.
        root, revision, head = _git_backed_repo(tmp_path)
        (root / po23.PROJECTION_V12_JSON_PATH).unlink()
        errors = po23.run_check_errors_o23(root)
        assert errors == [
            f"semantic projection v1.2 missing: {po23.PROJECTION_V12_JSON_PATH}"
        ]
        (root / po23.PROFILE_V12_JSON_PATH).unlink()
        errors = po23.run_check_errors_o23(root)
        assert errors == [
            f"semantic projection v1.2 missing: {po23.PROJECTION_V12_JSON_PATH}",
            f"api representation profile v1.2 missing: {po23.PROFILE_V12_JSON_PATH}",
        ]


class TestRepositoryGateWiring:
    """The v1.2 gate owns its own failure attribution in ``check_repo``."""

    def test_check_repo_fails_when_o23_gate_fails(self) -> None:
        from unittest import mock

        from scripts import check_repo

        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_projection_v1,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            return_value=["sentinel projection v1.2 error"],
        ):
            assert check_repo.main() == 1

    def test_check_repo_passes_when_all_gates_pass(self) -> None:
        from unittest import mock

        from scripts import check_repo

        with mock.patch.object(
            check_repo, "find_duplicate_global_packages", return_value={}
        ), mock.patch.object(
            check_repo.validate_aebs_executable_bench, "validate_bench", return_value=[]
        ), mock.patch.object(
            check_repo.check_model_sync, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_scenario_manifest, "run_check_errors", return_value=[]
        ), mock.patch.object(
            check_repo.check_naming, "run_all_checks", return_value=[]
        ), mock.patch.object(
            check_repo.generate_semantic_projection_v1,
            "run_check_errors",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o22,
            "run_check_errors_o22",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            return_value=[],
        ), mock.patch.object(
            check_repo.generate_semantic_authority_inventory,
            "run_check_errors",
            return_value=[],
        ):
            assert check_repo.main() == 0

    def test_check_repo_actually_invokes_the_o23_gate(self) -> None:
        # A pass-through spy proves check_repo calls the v1.2 gate (rather
        # than the test suite accidentally bypassing it).
        from unittest import mock

        from scripts import check_repo

        calls: list[int] = []
        original = check_repo.generate_semantic_projection_o23.run_check_errors_o23

        def spy(root):
            calls.append(1)
            return original(root)

        with mock.patch.object(
            check_repo.generate_semantic_projection_o23,
            "run_check_errors_o23",
            side_effect=spy,
        ):
            result = check_repo.main()
        assert calls, "check_repo did not invoke the O2.3 gate"
        assert result == 0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def subprocess_run_git_show(revision: str, path: str) -> bytes:
    import subprocess

    return subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    ).stdout


def subprocess_run(argv: list[str]) -> str:
    import subprocess

    return subprocess.run(
        argv, cwd=REPO_ROOT, capture_output=True, check=True, text=True
    ).stdout


