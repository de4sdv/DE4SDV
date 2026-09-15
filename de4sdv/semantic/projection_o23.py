"""O2.3 additive extension: Semantic Projection v1.2 / API Representation Profile v1.2.

Final bounded generation stage of the O2 semantic-authority migration. This
module is **additive**: it generates the machine-readable semantic
representation for exactly the three settled identities —

- ``derivesRequirementFromNeed`` (``Requirement -> Need``, inverse navigation
  over the native derivation witness),
- ``derivedRequirementsOfNeed`` (``Need -> Requirement``, forward navigation
  over the SAME witness),
- ``hasRelevantArchitecture`` (``Requirement -> ArchitectureElement``,
  relevance through an authored incoming dependency),

— as an **extension of the immutable O2.2 baseline**, never as a mutation of
it. The O2.1 and O2.2 artifacts (bound to their permanent Stage A revisions)
remain canonical for their identities; this module neither re-emits nor
re-binds them. The extension documents bind their baselines by path, schema,
source revision, and artifact digest (independent ``extends`` pins: the
projection extension extends the projection baseline; the profile extension
independently extends the profile baseline).

K pair — ONE modeled fact, TWO navigations (final K decision,
``docs/method-conformance/k-slice/v11-final-decision.md``):

- The two K predicates are two navigations over exactly ONE modeled witness:
  the DE4SDV application connection definition ``connection def
  DerivesFromNeed`` with its typed ends (``need :
  StakeholderNeedCandidate``, ``derivedRequirement :
  RequirementCandidate``). No second modeled relationship exists, none is
  manufactured, and connection evidence is never duplicated as two
  independent propositions.
- Native modeled direction: ``Need -> Requirement`` — the validated
  ``Native direction:`` statement carried by the connection definition's
  documentation (never inferred from declaration order; reordering the two
  end declarations changes nothing).
  ``derivesRequirementFromNeed`` (Requirement -> Need) is inverse traversal
  over that witness; ``derivedRequirementsOfNeed`` is the forward traversal.
- Role identity is established from the model's typed ends against the
  governed kernel lineages — never from end order, connection argument
  order, query direction, ``declaredName`` alone, ``qualifiedName`` alone,
  package path, or source-text heuristics.
- The semantic claim is provenance only ("the design-input Requirement
  originates from the stakeholder Need"). No logical implication, need or
  requirement satisfaction, allocation, realization, verification, evidence,
  acceptance, approval, or certification is asserted. The standard
  Requirement Derivation Domain Library ``Derivation`` is deliberately NOT
  adopted (its ``originalImpliesDerived`` semantics are stronger and
  semantically wrong for this claim) and is never silently substituted.
- The authored ontology YAML remains, for the K pair, only the
  parity/contract oracle permitted by the existing reviewed architecture:
  both rows are pair-parity-checked against the model-derived semantics and
  any drift fails generation. YAML is never promoted back into semantic
  authority.

Source-of-truth rule (same separation discipline as corrected O2.2):

- **model/contract-derived semantic core** — per identity, the projection
  derives ``identity``, ``semantic_kind``, domain, range (with the governed
  lineage anchor declarations), canonical engineering direction, the native
  modeled direction, semantic strength, the load-bearing scope restrictions,
  the native grounding identity at the semantic level, and model witness
  anchors from the validated authoritative representation: the reviewed
  representation contract (the governed ontology/kernel contract's declared
  entries, consumed read-only, locked against the reviewed O2.3 locks —
  drift fails closed) and the governed model declarations (located
  structurally, fail closed). For the K pair the v0 model-authority probes
  (``model_authority``) are reused exactly as reviewed; v0 remains an
  implementation/evidence reference, never a second semantic authority.
- **projection-schema / reviewed claim-boundary metadata** — the explicit
  negative laws and claim boundaries live in the projection-level
  ``projection_contract.identity_claim_boundaries`` block as SCHEMA-LEVEL
  reviewed contract metadata, never as per-row engineering-semantic fields.
  They are transcribed from the merged reviewed decisions (final K decision;
  O1 c5 relevance/realization review) and governing plans, machine-locked by
  tests; the generator reads no review artifact.

Representation mechanics — connection/dependency strategy, query direction,
connection role names, API metaclasses, property paths, end resolution,
exclusion filters — live ONLY in the API Representation Profile. The
compatibility gate holds the profile to the projection through a
per-identity ``semantic_contract_echo``; mechanics can never redefine
meaning.

``ArchitectureElement`` is an application-semantic umbrella: the reviewed
model has no single file/declaration kernel binding for it, none is
fabricated, and API metaclass equality (PartUsage/ActionUsage and friends)
is never upgraded into semantic identity proof. The range meaning of
``hasRelevantArchitecture`` is established by the exact reviewed application
contract: architecture-side part/action representation AND not MemberProduct
lineage AND authored incoming relevance dependency AND a query source
machine-proven in the governed Requirement lineage. The MemberProduct
exclusion is load-bearing: configured-product traces are product-line
relationships, not architecture relevance.

Support state (established DE4SDV rule): without structured exact-revision
closure evidence matching the artifact source revision exactly,
``support_state`` is ``vocabulary-only``. Historical K closure evidence
(retained privileged run at its own earlier revision) does NOT promote
current support; generation is NOT support promotion; an existing runtime
mapping is NOT support promotion. No promotion input exists anywhere in this
module. The runtime-mapping fact is recorded only as non-support profile
metadata (``runtime_mapping_state = existing-not-authority``).

``api_binding`` stays explicitly ``unclaimed``: no current exact-revision API
closure exists (privileged/CI-owned); retained privileged runs remain
representation-shape evidence only. Generation performs no authority
activation (O3 owns authority transition; O4 owns authored-ontology
retirement). The runtime does not read these artifacts. No model change is
made or needed: the K connection and the architecture-relevance witnesses
already exist.

Squash-safe delivery: Stage A (this module, its generator, the O2.3 admission
manifest, the design record, and the tests) is delivered first and
squash-merged; Stage B generates and commits the v1.2 artifacts bound to that
permanent revision and activates the repository gate. In a squash-only
repository a feature-branch commit never survives in ``main`` ancestry, so no
canonical artifact may bind to one.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .authority_inventory import (
    _DuplicateKeyLoader,
    _git,
    canonical_json,
    file_digest,
    resolve_source_revision,
    validate_source_binding,
    verify_source_revision_contains_inputs,
)
from .kernel_contract import KernelContract, KernelFileMapping
from .model_authority import CLAIM_STRENGTH, PREDICATE_SHAPE
from .projection_o22 import (
    PROFILE_V11_SCHEMA,
    PROJECTION_V11_SCHEMA,
    ProjectionO22Error,
    _contract_class_anchor,
    _locate_required_declaration,
)
from .projection_v1 import (
    O21_ADMITTED_IDENTITIES,
    O21_EXCLUDED_IDENTITIES,
    O2_SEQUENCING,
)

# ---------------------------------------------------------------------------
# Schema and artifact paths
# ---------------------------------------------------------------------------

PROJECTION_V12_SCHEMA = "de4sdv.semantic-projection.v1.2"
PROFILE_V12_SCHEMA = "de4sdv.api-representation-profile.v1.2"
ADMISSION_O23_SCHEMA_ID = "de4sdv.o2-3-admission/v1"

O2_DIRECTORY = "docs/method-conformance/o2"
ADMISSION_O23_PATH = f"{O2_DIRECTORY}/o23-admission.yaml"
PROJECTION_V12_JSON_PATH = f"{O2_DIRECTORY}/semantic-projection-v1.2.json"
PROFILE_V12_JSON_PATH = f"{O2_DIRECTORY}/api-representation-profile-v1.2.json"
BASELINE_PROJECTION_V11_PATH = f"{O2_DIRECTORY}/semantic-projection-v1.1.json"
BASELINE_PROFILE_V11_PATH = f"{O2_DIRECTORY}/api-representation-profile-v1.1.json"

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"

#: Program sources whose behavior produces the O2.3 artifacts. Every one is a
#: bound input. Executed-generation-path audit (O2.3 review correction): the
#: set covers every repository source whose code executes (or whose consumed
#: constant values derive from code) during artifact generation:
#:   * this module and its generator;
#:   * the O2.1 module (frozen locks consumed; anchor helper executed);
#:   * the O2.2 module (reviewed anchor locators executed);
#:   * the v0 K module ``projection.py`` (the reviewed pair-parity gate
#:     ``_assert_oracle_parity`` EXECUTES during generation — its verdict is
#:     part of the generation decision, so a change to it must invalidate the
#:     artifact binding);
#:   * the shared binding/documentation machinery (authority_inventory) and
#:     the governed contract loader (kernel_contract);
#:   * the v0 model-authority module (the reviewed identity/claim probes
#:     consumed as constants);
#:   * the sysml_api revision-identity plumbing (``OntologyIdentity.from_file``
#:     executes during generation through ``KernelContract.load``).
#: Transitively imported modules whose code never executes during generation
#: (``model_edges.py``, ``relationships.py``, ``sysml_api`` siblings) are
#: deliberately NOT bound. None of these files is modified by O2.3.
BOUND_INPUT_PROGRAM_PATHS_O23: tuple[str, ...] = (
    "de4sdv/semantic/projection_o23.py",
    "de4sdv/semantic/projection_o22.py",
    "de4sdv/semantic/projection_v1.py",
    "de4sdv/semantic/projection.py",
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/semantic/model_authority.py",
    "de4sdv/sysml_api/revisions.py",
    "scripts/generate_semantic_projection_o23.py",
)


class ProjectionO23Error(Exception):
    """Generation/validation failure for the O2.3 projection extension."""


# ---------------------------------------------------------------------------
# Machine-locked O2.3 admission boundary
# ---------------------------------------------------------------------------

#: The reviewed O2.3 admission boundary, read from the frozen O2 sequencing.
#: The manifest must agree with this lock exactly (order and set); the
#: emission path iterates this tuple only — new ontology/model entries cannot
#: expand the output.
O23_ADMITTED_IDENTITIES: tuple[str, ...] = O2_SEQUENCING["o2.3"]

_O23_ADMITTED_SET = frozenset(O23_ADMITTED_IDENTITIES)

#: Identities that must never appear in O2.3 output: the O2.1 seven and the
#: O2.2 three (already published in the immutable v1/v1.1 baselines; never
#: re-emitted or re-bound), every identity guarded by the O2.1 exclusion lock,
#: minus the three admitted O2.3 identities. Machine-derived from the frozen
#: locks so a drifted guard set cannot be introduced silently.
O23_GUARDED_IDENTITIES: tuple[str, ...] = tuple(
    sorted(
        (
            set(O21_EXCLUDED_IDENTITIES)
            | set(O21_ADMITTED_IDENTITIES)
            | set(O2_SEQUENCING["o2.2"])
        )
        - _O23_ADMITTED_SET
    )
)

#: The cumulative reviewed O2 semantic surface after O2.3: the O2.1 seven,
#: the O2.2 three, and the O2.3 three = exactly thirteen identities, with no
#: overlap and no fourteenth identity.
O23_CUMULATIVE_SURFACE: tuple[str, ...] = (
    tuple(O21_ADMITTED_IDENTITIES)
    + tuple(O2_SEQUENCING["o2.2"])
    + tuple(O23_ADMITTED_IDENTITIES)
)

#: Bounded K schema identifiers (same bounded-identifier discipline as the v0
#: K slice): they LOCATE the reviewed witness and roles; the semantic values
#: (domain, range, directions, strength, claim boundary) are derived from the
#: model and parity-checked against the authored oracle.
K_CONNECTION_DEFINITION_CLASS = "DerivesFromNeed"
K_NEED_ROLE = "need"
K_REQUIREMENT_ROLE = "derivedRequirement"
K_CANONICAL_PREDICATE = "derivesRequirementFromNeed"
K_COMPANION_PREDICATE = "derivedRequirementsOfNeed"
K_DERIVATION_STRATEGY = "derivation-connection"

#: The only legal query-direction pairing for one inverse-navigation pair.
_PAIR_DIRECTIONS = {"inverse": "forward", "forward": "inverse"}

#: Reviewed predicate contract locks. The governed contract's declared values
#: for these fields were settled by the merged O1 decisions (final K decision;
#: c5 relevance review); a drift means the reviewed boundary changed and
#: requires explicit review — never a silent regeneration. The K locks are
#: the bounded identifiers only (values come from the model/oracle parity);
#: the ``hasRelevantArchitecture`` lock is the full reviewed application
#: contract (its restrictions are load-bearing meaning, not model-derivable).
_O23_PREDICATE_LOCKS: dict[str, dict[str, Any]] = {
    K_CANONICAL_PREDICATE: {
        "domain": "Requirement",
        "range": "Need",
        "strategy": K_DERIVATION_STRATEGY,
        "semantic_strength": "derivation",
        "connection_definition": "DerivesFromNeed",
        "need_role": K_NEED_ROLE,
        "requirement_role": K_REQUIREMENT_ROLE,
        "query_direction": "inverse",
    },
    K_COMPANION_PREDICATE: {
        "domain": "Need",
        "range": "Requirement",
        "strategy": K_DERIVATION_STRATEGY,
        "semantic_strength": "derivation",
        "connection_definition": "DerivesFromNeed",
        "need_role": K_NEED_ROLE,
        "requirement_role": K_REQUIREMENT_ROLE,
        "query_direction": "forward",
    },
    "hasRelevantArchitecture": {
        "domain": "Requirement",
        "range": "ArchitectureElement",
        "strategy": "dependency",
        "semantic_strength": "relevance",
        "relationship_types": ("Dependency",),
        "direction": "incoming",
        "source_property": "source",
        "target_property": "target",
        "source_types": (
            "PartUsage",
            "PartDefinition",
            "ActionUsage",
            "ActionDefinition",
        ),
        "exclude_source_specializations_of": "MemberProduct",
    },
}

#: O2.3-owned witness locator for the K derivation-usages evidence
#: (representation anchor only, never identity basis). The connection
#: DEFINITION identity comes from the governed contract's file-mapped
#: declaration; the usages recorded here are model evidence of the witness
#: population.
K_WITNESS_MODEL_FILE = (
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"
)

#: Reviewed K witness population at the governed model (the five authored
#: ``connection … : DerivesFromNeed connect <need> to <req>;`` usages). The
#: population is a reviewed lock: a usage that disappears, a usage typed by a
#: foreign definition, or a newly added usage changes the reviewed witness
#: set and fails generation — explicit review, never silent absorption. The
#: exact usage names are machine-locked by the tests; the module locks the
#: count so silent drift cannot pass either way.
K_EXPECTED_WITNESS_POPULATION = 5

#: The established DE4SDV support-state rule: without structured
#: exact-revision closure evidence, ``support_state`` is ``vocabulary-only``.
#: Generation of a row is NOT support promotion; an existing runtime mapping
#: is NOT support promotion; retained historical API evidence (including the
#: K slice's retained closure run at its own earlier revision) is NOT current
#: exact-revision closure. No other support vocabulary exists in this module
#: and there is no promotion input anywhere.
SUPPORT_STATE_VOCABULARY_ONLY = "vocabulary-only"

#: Non-support implementation metadata recorded in the representation profile
#: (never in ``support_state``): the reviewed runtime mappings exist, but they
#: are not authority for these artifacts.
RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY = "existing-not-authority"

#: Identity-resolution contract recorded for model witnesses and lineage
#: anchors (ADR 0011 discipline, identical to the O2.2 contract).
_O23_IDENTITY_RESOLUTION = (
    "ingestion-validated kernel binding: exactly one API element whose "
    "declaredName and @type match the governed declaration and whose "
    "serializer-recorded source document equals the bound source file; "
    "multiple candidates are ambiguous and zero candidates is unresolved "
    "(both fail closed); the runtime consumes the resulting "
    "KernelElementBinding through KernelBindingIndex, never a name-based "
    "fallback"
)

_O23_LINEAGE_RESOLUTION = (
    "validated lineage proof over the representation-tolerant relationship "
    "graph: the element's authored typing/classification chain plus the "
    "tool-derived implied subsumption edges resolve to the governed lineage "
    "root through the ingestion-validated kernel binding "
    "(KernelBindingIndex.element_id_for); explicit and implied grounding "
    "provenance stay separate; a missing validated binding fails closed and "
    "no name/path/string fallback exists"
)

#: Reviewed negative-witness registry: the machine-locked negative laws of
#: the final K decision and the merged O1 c5 review. This registry is the
#: reviewed source of the projection-contract claim boundaries
#: (:data:`PROJECTION_CONTRACT_O23` ``identity_claim_boundaries``): the
#: generated artifact serializes the laws as SCHEMA-LEVEL reviewed contract
#: metadata (never as per-row engineering-semantic fields), and tests
#: machine-lock the registry against the serialized boundaries. The O1/K
#: review artifacts themselves are governance records and are never read at
#: generation.
_O23_NEGATIVE_WITNESSES: dict[str, tuple[str, ...]] = {
    K_CANONICAL_PREDICATE: (
        "generic Dependency",
        "standard Derivation library adoption",
        "originalImpliesDerived implication semantics",
        "end order as role identity",
        "connection argument order as role identity",
        "query direction as role identity",
        "declaredName alone",
        "qualifiedName alone",
        "package path",
        "source text heuristics",
        "satisfaction",
        "logical implication",
        "allocation",
        "realization",
        "verification",
        "evidence",
        "acceptance",
        "approval",
        "certification",
    ),
    K_COMPANION_PREDICATE: (
        "generic Dependency",
        "standard Derivation library adoption",
        "originalImpliesDerived implication semantics",
        "end order as role identity",
        "connection argument order as role identity",
        "query direction as role identity",
        "declaredName alone",
        "qualifiedName alone",
        "package path",
        "source text heuristics",
        "satisfaction",
        "logical implication",
        "allocation",
        "realization",
        "verification",
        "evidence",
        "acceptance",
        "approval",
        "certification",
    ),
    "hasRelevantArchitecture": (
        "satisfaction",
        "realization",
        "allocation",
        "verification",
        "specification",
        "product-line selection",
        "configuration membership",
        "deployment",
        "physical realization",
        "API metaclass equality",
        "name-only correspondence",
        "package path",
        "source text heuristics",
        "MemberProduct lineage",
    ),
}

#: Projection-schema contract (Unified Plan section 8.1 analogue): what
#: extension rows may claim and what they do not. Schema/projection metadata
#: — model-derived meaning lives only in each row's derived fields. The claim
#: boundaries are REVIEWED CONTRACT METADATA carried by this module
#: (transcribed from the final K decision, the merged O1 c5 review, and the
#: governing plans); they are explicitly a schema-level block, never
#: serialized as per-row engineering-semantic fields, and the generator reads
#: no review artifact at generation time.
PROJECTION_CONTRACT_O23: dict[str, Any] = {
    "semantic_scope": (
        "design-input derivation provenance (K pair) and bounded "
        "architecture relevance: each row projects the reviewed declared "
        "contract of a predicate identity at the bound source revision; "
        "domain, range, canonical direction, native modeled direction, "
        "semantic strength, native/application grounding identity, and the "
        "load-bearing scope restrictions are the identity's declared meaning"
    ),
    "does_not_assert": [
        "logical implication between connected usages",
        "need satisfaction or requirement satisfaction",
        "allocation",
        "realization",
        "verification execution or results",
        "evidence validity or freshness",
        "acceptance or approval decision",
        "certification",
        "product-line selection or configuration membership",
        "deployment or physical realization",
    ],
    "derivation_rule": (
        "fields in the projected semantic core are derived from the governed "
        "authoritative representation at the bound source revision; for the "
        "K pair the reviewed v0 model-authority probes are reused read-only "
        "(one witness, two navigations); projection-schema claim boundaries, "
        "admission governance, representation-profile mechanics, and "
        "provenance metadata are explicitly separated and identified as such"
    ),
    "identity_claim_boundaries": {
        K_CANONICAL_PREDICATE: {
            "claims": (
                "the design-input Requirement originates from the stakeholder "
                "Need (provenance/traceability only): Requirement -> Need, "
                "inverse navigation over the single native DerivesFromNeed "
                "connection witness"
            ),
            "one_modeled_fact_two_navigations": (
                "this predicate and derivedRequirementsOfNeed are two "
                "navigations over exactly one modeled DerivesFromNeed "
                "witness; the pair shares connection definition, witness "
                "population, typed role binding, semantic strength, and "
                "claim boundary, and differs only in canonical query "
                "direction (inverse domain/range)"
            ),
            "does_not_assert": [
                "that a generic Dependency establishes this relation",
                "that the standard Requirement Derivation Domain Library "
                "Derivation (originalImpliesDerived) semantics apply or were "
                "adopted",
                "logical implication between the connected usages",
                "need satisfaction or requirement satisfaction",
                "allocation, realization, verification, evidence, "
                "acceptance, approval, or certification",
                "that end order, connection argument order, query direction, "
                "declaredName, qualifiedName, package path, or source text "
                "establishes role identity",
            ],
        },
        K_COMPANION_PREDICATE: {
            "claims": (
                "the stakeholder Need is the design-input origin of the "
                "derived Requirement (provenance/traceability only): Need -> "
                "Requirement, forward navigation over the SAME single native "
                "DerivesFromNeed connection witness"
            ),
            "one_modeled_fact_two_navigations": (
                "this predicate and derivesRequirementFromNeed are two "
                "navigations over exactly one modeled DerivesFromNeed "
                "witness; no second modeled relationship exists and "
                "connection evidence is never duplicated as two independent "
                "propositions"
            ),
            "does_not_assert": [
                "that a generic Dependency establishes this relation",
                "that the standard Requirement Derivation Domain Library "
                "Derivation (originalImpliesDerived) semantics apply or were "
                "adopted",
                "logical implication between the connected usages",
                "need satisfaction or requirement satisfaction",
                "allocation, realization, verification, evidence, "
                "acceptance, approval, or certification",
                "that end order, connection argument order, query direction, "
                "declaredName, qualifiedName, package path, or source text "
                "establishes role identity",
            ],
        },
        "hasRelevantArchitecture": {
            "claims": (
                "a native architecture-side part/action element is relevant "
                "to Requirement R through an authored incoming Dependency "
                "(relevance only): Requirement -> ArchitectureElement, with "
                "the load-bearing DE4SDV restrictions below"
            ),
            "restrictions_are_meaning": (
                "the reviewed application contract is load-bearing meaning, "
                "not a query convenience: generic Dependency alone is NOT "
                "this predicate, and the range is an application-semantic "
                "umbrella (no ArchitectureElement kernel binding exists or "
                "is fabricated; API metaclass equality is never identity "
                "proof)"
            ),
            "does_not_assert": [
                "satisfaction, realization, allocation, verification, or "
                "specification",
                "product-line selection or configuration membership",
                "deployment or physical realization",
                "that the relation is realizedBy, specifiesFunction, "
                "allocatedTo, deployedTo, or appliesToMemberProduct (the "
                "canonical RFLP chain is not collapsed)",
                "that a direct relevance edge is anything but "
                "navigation/traceability",
                "that a source in the MemberProduct lineage establishes "
                "architecture relevance (product-line relationships are not "
                "architecture relevance)",
                "that API metaclass equality (PartUsage, ActionUsage, or "
                "any serializer shape) is identity proof",
                "that name-only correspondence, a package path, or source "
                "text establishes the relation",
                "that every PartUsage or ActionUsage is semantically an "
                "ArchitectureElement without the reviewed restrictions",
            ],
        },
    },
    "external_artifact_treatment": (
        "external identities referenced by projected constructs (retained "
        "records, policies, registries) remain external; generation neither "
        "absorbs nor evaluates them"
    ),
    "runtime_boundary": (
        "generation is not authority activation; the runtime does not read "
        "this artifact; no support promotion occurs here and none exists as "
        "an input; historical K closure evidence does not promote current "
        "support; authority transition is a separate reviewed stage (O3)"
    ),
}

# ---------------------------------------------------------------------------
# O2.3 admission manifest (governance boundary)
# ---------------------------------------------------------------------------


def load_admission_manifest_o23(path: Path) -> dict[str, Any]:
    """Load and shape-check the machine-locked O2.3 admission manifest."""
    if not path.is_file():
        raise ProjectionO23Error(f"O2.3 admission manifest not found: {path}")
    try:
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader)
    except ProjectionO23Error:
        raise
    except yaml.YAMLError as exc:
        raise ProjectionO23Error(
            f"O2.3 admission manifest is not valid YAML: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ProjectionO23Error("O2.3 admission manifest must be a YAML mapping")
    if value.get("schema") != ADMISSION_O23_SCHEMA_ID:
        raise ProjectionO23Error(
            f"admission schema must be {ADMISSION_O23_SCHEMA_ID!r}, "
            f"got {value.get('schema')!r}"
        )
    return value


def validate_admission_o23(manifest: dict[str, Any]) -> None:
    """Machine-lock the O2.3 admission boundary; fail closed on any drift.

    Locks (each direction): admitted set equals the frozen o2.3 sequencing
    (order and set); the manifest's sequencing echo equals the frozen O2
    sequencing; the cumulative O2 surface (o2.1 + o2.2 + o2.3) is exactly
    thirteen distinct identities; no identity is both admitted and guarded;
    every guarded entry carries a non-empty reason and a kind in
    {class, relationship}.
    """
    admitted = manifest.get("admitted")
    if not isinstance(admitted, list) or not all(
        isinstance(item, str) and item for item in admitted
    ):
        raise ProjectionO23Error(
            "admission manifest `admitted` must be a list of identities"
        )
    if tuple(admitted) != O23_ADMITTED_IDENTITIES:
        raise ProjectionO23Error(
            "admission manifest `admitted` does not equal the frozen O2.3 "
            f"lock: manifest={tuple(admitted)!r} "
            f"lock={O23_ADMITTED_IDENTITIES!r}"
        )

    sequencing = manifest.get("sequencing")
    if not isinstance(sequencing, dict) or set(sequencing) != set(O2_SEQUENCING):
        raise ProjectionO23Error(
            "admission manifest `sequencing` must echo exactly "
            f"{sorted(O2_SEQUENCING)}"
        )
    for phase, identities in O2_SEQUENCING.items():
        if tuple(sequencing.get(phase, ())) != identities:
            raise ProjectionO23Error(
                f"admission sequencing {phase!r} must equal {identities!r}"
            )
    union = tuple(
        identity
        for phase in ("o2.1", "o2.2", "o2.3")
        for identity in O2_SEQUENCING[phase]
    )
    if len(union) != 13 or len(set(union)) != 13:
        raise ProjectionO23Error(
            "the overall O2 admission must remain exactly 13 distinct identities"
        )
    if len(O23_CUMULATIVE_SURFACE) != 13 or len(set(O23_CUMULATIVE_SURFACE)) != 13:
        raise ProjectionO23Error(
            "the cumulative O2.1+O2.2+O2.3 surface must be exactly thirteen "
            "distinct identities"
        )

    guarded = manifest.get("guarded")
    if not isinstance(guarded, list) or not guarded:
        raise ProjectionO23Error("admission manifest `guarded` must be a non-empty list")
    seen: set[str] = set()
    for entry in guarded:
        if not isinstance(entry, dict):
            raise ProjectionO23Error("guarded entries must be mappings")
        identity = str(entry.get("identity") or "")
        if not identity:
            raise ProjectionO23Error("guarded entry without an identity")
        if identity in seen:
            raise ProjectionO23Error(f"duplicate guarded identity {identity!r}")
        seen.add(identity)
        if entry.get("kind") not in {"class", "relationship"}:
            raise ProjectionO23Error(
                f"guarded identity {identity!r} must declare kind class|relationship"
            )
        if not str(entry.get("reason") or "").strip():
            raise ProjectionO23Error(f"guarded identity {identity!r} has no reason")
    if set(seen) != set(O23_GUARDED_IDENTITIES):
        raise ProjectionO23Error(
            "the manifest `guarded` set must equal the frozen O2.3 guard set: "
            f"manifest-only={sorted(set(seen) - set(O23_GUARDED_IDENTITIES))} "
            f"lock-only={sorted(set(O23_GUARDED_IDENTITIES) - set(seen))}"
        )
    both = set(admitted) & seen
    if both:
        raise ProjectionO23Error(
            f"identities both admitted and guarded: {sorted(both)}"
        )


# ---------------------------------------------------------------------------
# Model-side derivation (governed model + reviewed contract only)
# ---------------------------------------------------------------------------


def _contract_connection_anchor(
    contract: KernelContract, root: Path
) -> dict[str, str]:
    """Resolve the K connection-definition anchor through the contract.

    The ``DerivesFromNeed`` application definition is file-mapped in the
    governed contract; its braced declaration must be locatable exactly once
    (fail closed otherwise — missing, ambiguous, or malformed grounding
    cannot generate a K row). The anchor proves the model-resident witness
    identity at the abstract level; it is never a name-based fallback.
    """
    mapping = contract.mapping(K_CONNECTION_DEFINITION_CLASS)
    if not isinstance(mapping, KernelFileMapping):
        raise ProjectionO23Error(
            f"{K_CANONICAL_PREDICATE}: DerivesFromNeed is not file-mapped in "
            "the governed contract; the derivation witness cannot be proven "
            "and generation fails closed (no name/path fallback exists)"
        )
    _locate_required_declaration(root, mapping.file, mapping.declaration)
    return {"file": mapping.file, "declaration": mapping.declaration}


def _derivation_usage_witnesses(root: Path) -> list[dict[str, str]]:
    """Locate the authored K connection usages (model evidence only).

    The governed feature file declares ``connection <name> : DerivesFromNeed
    connect <need> to <req>;`` witnesses. Each is located structurally by
    its typing witness and captured as evidence of the witness population;
    identity/roles still come from the definition's typed ends, never from
    these names. Fail closed: a zero population (the reviewed witness set
    disappeared), a population that does not match the reviewed count, or a
    usage typed by any definition other than the reviewed one.
    """
    text = (root / K_WITNESS_MODEL_FILE).read_text(encoding="utf-8")
    usages: list[dict[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("connection ") or ": DerivesFromNeed connect " not in stripped:
            continue
        if not stripped.endswith(";"):
            raise ProjectionO23Error(
                "K derivation usage witness is malformed (missing terminator): "
                f"{stripped!r}"
            )
        declaration = stripped[: stripped.index(" connect ")].rstrip()
        name_part = declaration[len("connection ") :].strip()
        if " : " not in name_part:
            raise ProjectionO23Error(
                f"K derivation usage witness is malformed: {stripped!r}"
            )
        usage_name, _, type_name = name_part.partition(" : ")
        usages.append(
            {
                "usage_name": usage_name.strip(),
                "connection_type": type_name.strip(),
            }
        )
    if not usages:
        raise ProjectionO23Error(
            "no DerivesFromNeed connection usage witness found in "
            f"{K_WITNESS_MODEL_FILE}; the reviewed K witness population is "
            "absent and generation fails closed"
        )
    if len(usages) != K_EXPECTED_WITNESS_POPULATION:
        raise ProjectionO23Error(
            f"K witness population drifted: found {len(usages)} typed "
            "DerivesFromNeed connection usages in "
            f"{K_WITNESS_MODEL_FILE} but the reviewed population is "
            f"{K_EXPECTED_WITNESS_POPULATION}; witness drift requires "
            "explicit review, never silent absorption"
        )
    return usages


def _parse_definition_ends(block: str, definition: str) -> list[tuple[str, str]]:
    """The definition block's typed ends as (role, type) pairs.

    Declaration order is preserved only as parse order for pairing role names
    with their types; it is NEVER read as semantic authority — role identity
    is keyed by typing against the governed lineages and the modeled
    direction comes from the validated documentation statement, so reordering
    these declarations changes nothing (machine-locked by a real swap
    fixture).
    """
    end_pattern = re.compile(
        r"(?m)^\s*end\s+([A-Za-z][A-Za-z0-9_]*)\s*:\s*"
        r"([A-Za-z][A-Za-z0-9_]*)\s*;"
    )
    ends = [
        (match.group(1), match.group(2)) for match in end_pattern.finditer(block)
    ]
    if len(ends) != 2:
        raise ProjectionO23Error(
            f"{definition}: expected exactly two typed ends, found "
            f"{len(ends)}; the model does not ground the K domain/range"
        )
    return ends


def _class_declaration_name(contract: KernelContract, ontology_class: str) -> str:
    mapping = contract.mapping(ontology_class)
    if not isinstance(mapping, KernelFileMapping):
        raise ProjectionO23Error(
            f"{ontology_class} is not file-mapped in the governed contract; "
            "the K lineage resolution fails closed"
        )
    _, _, declared = mapping.declaration.partition(" def ")
    return declared.strip()


def _doc_bodies(block: str) -> list[str]:
    """Normalized documentation bodies owned by the located definition block."""
    return [
        " ".join(match.group(1).replace("*", " ").split())
        for match in re.finditer(r"doc\s*/\*(.*?)\*/", block, flags=re.DOTALL)
    ]


def _extract_claim_strength(block: str, definition: str) -> tuple[str, str, str]:
    """The definition doc's claim-strength statement, via the reviewed v0 probe.

    Reuses the v0 ``CLAIM_STRENGTH`` locator exactly: the strength token and
    claim boundary are MODEL TEXT; the probe only finds them. Zero statements
    (missing provenance/claim-boundary doc) and multiple conflicting
    statements both fail closed.
    """
    doc_bodies = _doc_bodies(block)
    if not doc_bodies:
        raise ProjectionO23Error(
            f"{definition}: the definition carries no owned documentation; "
            "meaning and claim strength must come from the model"
        )
    statements: list[tuple[str, str]] = []
    for body in doc_bodies:
        match = CLAIM_STRENGTH.search(body)
        if match is not None:
            statements.append(
                (match.group("strength"), match.group("boundary").strip())
            )
    if not statements:
        raise ProjectionO23Error(
            f"{definition}: the definition documentation does not state "
            "'Claim strength: <token> (<claim boundary>)'; the model does "
            "not carry the predicate's claim strength and provenance meaning"
        )
    distinct = set(statements)
    if len(distinct) > 1:
        raise ProjectionO23Error(
            f"{definition}: the definition owns {len(distinct)} conflicting "
            "claim-strength statements; refusing to pick one"
        )
    strength, boundary = statements[0]
    return strength, boundary, " ".join(doc_bodies)


#: Locator for the modeled semantic direction statement the definition
#: documentation carries ("Native direction: need -> derivedRequirement.").
#: The statement is MODEL TEXT; the probe only finds it and the roles are
#: validated against the typed ends. Declaration order is never read as
#: semantic authority.
_NATIVE_DIRECTION = re.compile(
    r"Native direction:\s*([A-Za-z_][A-Za-z0-9_]*)\s*->\s*([A-Za-z_][A-Za-z0-9_]*)"
)


def _validated_native_direction(
    block: str, definition: str, need_role: str, requirement_role: str
) -> tuple[str, str]:
    """The VALIDATED modeled-direction statement from the model documentation.

    The final K decision fixes the modeled semantic direction as
    ``need -> derivedRequirement``, and the governed model states it
    explicitly in the definition documentation. Generation uses that reviewed
    statement and validates its roles against the typed ends; reordering the
    two end declarations therefore changes nothing. Missing, conflicting, or
    role-mismatched statements fail closed — the direction is never inferred
    from declaration order.
    """
    statements: set[tuple[str, str]] = set()
    for body in _doc_bodies(block):
        for match in _NATIVE_DIRECTION.finditer(body):
            statements.add((match.group(1), match.group(2)))
    if not statements:
        raise ProjectionO23Error(
            f"{definition}: the definition documentation does not state "
            "'Native direction: <role> -> <role>'; the modeled direction "
            "must come from the reviewed model statement, never from "
            "declaration order"
        )
    if len(statements) > 1:
        raise ProjectionO23Error(
            f"{definition}: the definition owns {len(statements)} conflicting "
            "native-direction statements; refusing to pick one"
        )
    roles = next(iter(statements))
    if roles != (need_role, requirement_role):
        raise ProjectionO23Error(
            f"{definition}: the documentation states the native direction "
            f"{roles[0]!r} -> {roles[1]!r} but the typed ends carry "
            f"{need_role!r} -> {requirement_role!r}; drift requires explicit "
            "review, never silent regeneration"
        )
    return roles


def derive_k_semantics(contract: KernelContract, root: Path) -> dict[str, Any]:
    """Derive the K pair's semantic core from the validated model representation.

    Authority chain (final K decision, preserved):

    1. the ``DerivesFromNeed`` application-definition identity comes from the
       governed contract's file-mapped declaration, located in the bound
       model exactly once (no name fallback, ambiguity fails closed);
    2. the typed ends carry domain and range: each end's TYPE is resolved to
       the governed lineage ontology class through the contract's kernel
       mappings — role identity is keyed by typing, NEVER by end order,
       connection argument order, or query direction (reordering the two end
       declarations changes nothing: roles, the canonical pair, and the
       modeled direction are all order-independent — machine-locked by a
       real end-order-swap fixture);
    3. the modeled semantic direction comes from the definition
       documentation's explicit ``Native direction: need -> derivedRequirement``
       statement, VALIDATED against the typed-end roles — declaration order
       is never read as semantic authority (missing, conflicting, or
       role-mismatched statements fail closed);
    4. the definition documentation also carries the provenance meaning and
       the claim boundary, located by the reviewed v0 probe;
    5. the canonical direction for the reviewed canonical predicate identity
       comes from the v0 predicate-shape probe matched against the resolved
       end classes; the query direction follows from the model (inverse
       exactly when the canonical direction is not the modeled one);
    6. the authored ontology YAML is then pair-parity-checked by the
       reviewed v0 parity gate (``_assert_oracle_parity``) — drift fails
       generation; YAML never becomes semantic authority.

    Returns the model-derived semantics dict (v0-compatible keys for the
    parity gate) plus the O2.3 evidence anchors.
    """
    anchor = _contract_connection_anchor(contract, root)
    definition_block = _locate_required_declaration(
        root, anchor["file"], anchor["declaration"]
    )

    ends = _parse_definition_ends(
        definition_block, K_CONNECTION_DEFINITION_CLASS
    )
    type_to_class = {
        _class_declaration_name(contract, cls): cls
        for cls in ("Need", "Requirement")
    }
    resolved: dict[str, dict[str, str]] = {}
    for role, type_name in ends:
        ontology_class = type_to_class.get(type_name)
        if ontology_class is None:
            raise ProjectionO23Error(
                f"{K_CONNECTION_DEFINITION_CLASS}: end {role!r} is typed "
                f"{type_name!r}, which resolves to no governed Need/Requirement "
                "lineage class; the model does not ground the K domain/range "
                "(wrong or missing end typing fails closed)"
            )
        if ontology_class in resolved:
            raise ProjectionO23Error(
                f"{K_CONNECTION_DEFINITION_CLASS}: both ends resolve to "
                f"{ontology_class!r}; the K pair requires exactly one Need "
                "end and one Requirement end"
            )
        resolved[ontology_class] = {
            "role": role,
            "type": type_name,
            "ontology_class": ontology_class,
        }
    if set(resolved) != {"Need", "Requirement"}:
        raise ProjectionO23Error(
            f"{K_CONNECTION_DEFINITION_CLASS}: the typed ends ground "
            f"{sorted(resolved)}; the K pair requires exactly "
            "{Need, Requirement}"
        )

    # Role identity keyed by typing (never by order): the Need-lineage end
    # carries the need role, the Requirement-lineage end carries the
    # requirement role. The reviewed role names must match the frozen locks.
    need_side = resolved["Need"]
    requirement_side = resolved["Requirement"]
    expected_roles = {
        K_NEED_ROLE: _O23_PREDICATE_LOCKS[K_CANONICAL_PREDICATE]["need_role"],
        K_REQUIREMENT_ROLE: _O23_PREDICATE_LOCKS[K_CANONICAL_PREDICATE][
            "requirement_role"
        ],
    }
    if (
        need_side["role"] != expected_roles[K_NEED_ROLE]
        or requirement_side["role"] != expected_roles[K_REQUIREMENT_ROLE]
    ):
        raise ProjectionO23Error(
            f"{K_CONNECTION_DEFINITION_CLASS}: the typed ends name the roles "
            f"need={need_side['role']!r} requirement="
            f"{requirement_side['role']!r} but the reviewed O2.3 locks "
            f"require {expected_roles!r}; contract/model drift requires "
            "explicit review, never silent regeneration"
        )

    strength, claim_boundary, meaning = _extract_claim_strength(
        definition_block, K_CONNECTION_DEFINITION_CLASS
    )

    # The modeled semantic direction is the VALIDATED documentation statement
    # ("Native direction: need -> derivedRequirement.") mapped through the
    # typed-end roles to the governed lineages. Declaration order is never
    # semantic authority; reordering the two end declarations changes nothing.
    direction_roles = _validated_native_direction(
        definition_block,
        K_CONNECTION_DEFINITION_CLASS,
        need_side["role"],
        requirement_side["role"],
    )
    role_to_class = {
        need_side["role"]: need_side["ontology_class"],
        requirement_side["role"]: requirement_side["ontology_class"],
    }
    native_direction = (
        f"{role_to_class[direction_roles[0]]} -> "
        f"{role_to_class[direction_roles[1]]}"
    )
    match = PREDICATE_SHAPE.fullmatch(K_CANONICAL_PREDICATE)
    if match is None:  # pragma: no cover - the frozen identity always matches
        raise ProjectionO23Error(
            f"predicate identity {K_CANONICAL_PREDICATE!r} does not expose "
            "subject/object vocabulary names"
        )
    subject, obj = match.group("subject"), match.group("object")
    if {subject, obj} != {need_side["ontology_class"], requirement_side["ontology_class"]}:
        raise ProjectionO23Error(
            f"predicate {K_CANONICAL_PREDICATE!r} names {sorted([subject, obj])} "
            "but the definition's typed ends ground "
            f"{sorted([need_side['ontology_class'], requirement_side['ontology_class']])}; "
            "domain/range cannot be derived"
        )
    canonical_direction = f"{subject} -> {obj}"
    query_direction = (
        "forward" if canonical_direction == native_direction else "inverse"
    )

    usage_witnesses = _derivation_usage_witnesses(root)
    for witness in usage_witnesses:
        if witness["connection_type"] != K_CONNECTION_DEFINITION_CLASS:
            raise ProjectionO23Error(
                "K usage witness is not typed by the reviewed application "
                f"definition: {witness!r}"
            )

    return {
        # v0-parity-compatible keys (consumed by _assert_oracle_parity):
        "connection_definition": K_CONNECTION_DEFINITION_CLASS,
        "need_role": need_side["role"],
        "requirement_role": requirement_side["role"],
        "need_end_type": need_side["ontology_class"],
        "requirement_end_type": requirement_side["ontology_class"],
        "need_end_type_declaration": need_side["type"],
        "requirement_end_type_declaration": requirement_side["type"],
        "query_direction": query_direction,
        "domain": subject,
        "range": obj,
        "semantic_strength": strength,
        # O2.3 evidence anchors (abstract semantic level):
        "native_direction": native_direction,
        "native_direction_roles": [direction_roles[0], direction_roles[1]],
        "canonical_direction": canonical_direction,
        "claim_boundary": claim_boundary,
        "meaning": meaning,
        "definition_anchor": anchor,
        "ends": [dict(need_side), dict(requirement_side)],
        "usage_witnesses": usage_witnesses,
        "authority_provenance": (
            "validated model representation: the governed DerivesFromNeed "
            "application definition's typed ends (domain/range, roles keyed "
            "by typing against the governed lineages), the validated "
            "'Native direction' documentation statement (the modeled "
            "direction; declaration order is never semantic authority), "
            "predicate identity matched to end classes "
            "(canonical direction), and ingested definition documentation "
            "(meaning, claim strength, claim boundary); the v0 "
            "model-authority probes are reused read-only, the v0 pair-parity "
            "gate executes read-only, and the ontology "
            "YAML is pair-parity-checked as the O0/O1 oracle only"
        ),
    }


def _assert_k_pair_invariants(semantics: dict[str, Any]) -> None:
    """Machine-lock the one-fact/two-navigations pair contract.

    Beyond the v0 oracle parity (which already locks the pair at contract
    level), this asserts the derived semantics themselves: opposite canonical
    directions over the same witness, inverse domain/range, identical
    strength and claim boundary, and the exact iff-equivalence of the two
    navigations for every modeled edge. The modeled direction is the
    validated documentation statement, which must resolve to the typed
    Need -> Requirement lineages (the lock restates that invariant; it never
    reintroduces declaration order).
    """
    if semantics["native_direction"] != (
        f"{semantics['need_end_type']} -> {semantics['requirement_end_type']}"
    ):
        raise ProjectionO23Error(
            "K pair invariant violated: the native direction does not follow "
            "from the typed ends"
        )
    expected_companion_direction = _PAIR_DIRECTIONS.get(semantics["query_direction"])
    if expected_companion_direction is None:
        raise ProjectionO23Error(
            f"unsupported K query direction {semantics['query_direction']!r}; "
            f"the pair direction vocabulary is {sorted(_PAIR_DIRECTIONS)}"
        )
    if semantics["domain"] != "Requirement" or semantics["range"] != "Need":
        raise ProjectionO23Error(
            "K pair invariant violated: the canonical predicate must ground "
            "Requirement -> Need"
        )


# ---------------------------------------------------------------------------
# Row derivation
# ---------------------------------------------------------------------------


def _oracle_row(contract: KernelContract, identity: str) -> tuple[dict[str, Any], Any]:
    """The authored oracle row + mapping for one K predicate (parity input)."""
    mapping = contract.relationship_mapping(identity)
    row = contract.relationships.get(identity) or {}
    return row, mapping


def _assert_oracle_parity_o23(
    contract: KernelContract, semantics: dict[str, Any]
) -> None:
    """Pair-parity-check the authored ontology YAML for BOTH K rows.

    Delegates the per-field comparison to the reviewed v0 parity gate
    (``_assert_oracle_parity``), which locks the complete pair — canonical
    and companion rows — against the model-derived semantics: one shared
    discriminator connection definition, identical typed roles, swapped
    domain/range and lineage sides, opposite query directions, identical
    semantic strength, and traversal of the same native connection witness.
    Any drift in either row fails generation naming the exact field. The
    YAML is the O0/O1 parity oracle only; it may contradict nothing and it
    may not redefine anything.
    """
    from . import projection as v0

    try:
        v0._assert_oracle_parity(contract, semantics)
    except ValueError as exc:
        raise ProjectionO23Error(
            f"ontology parity oracle drift for the K predicate pair: {exc}"
        ) from exc


def derive_k_pair_rows(
    contract: KernelContract, root: Path, semantics: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive BOTH K rows from the single model-derived semantic core.

    One witness, two navigations: both rows are emitted from the SAME
    ``semantics`` dict — the companion row is computed from the canonical
    row by the pair contract (swapped domain/range, opposite direction,
    identical strength/claim boundary/roles), never derived independently
    from the model a second time. Independent drift is structurally
    impossible; the pair invariants are asserted on the emitted rows.
    """
    _assert_oracle_parity_o23(contract, semantics)

    canonical_lock = _O23_PREDICATE_LOCKS[K_CANONICAL_PREDICATE]
    companion_lock = _O23_PREDICATE_LOCKS[K_COMPANION_PREDICATE]
    for identity, lock, direction in (
        (K_CANONICAL_PREDICATE, canonical_lock, semantics["query_direction"]),
        (
            K_COMPANION_PREDICATE,
            companion_lock,
            _PAIR_DIRECTIONS[semantics["query_direction"]],
        ),
    ):
        if lock["strategy"] != K_DERIVATION_STRATEGY:
            raise ProjectionO23Error(
                f"{identity}: reviewed strategy lock "
                f"{lock['strategy']!r} is not {K_DERIVATION_STRATEGY!r}"
            )
        if lock["query_direction"] != direction:
            raise ProjectionO23Error(
                f"{identity}: reviewed query-direction lock "
                f"{lock['query_direction']!r} does not match the "
                f"model-derived direction {direction!r}; drift requires "
                "explicit review"
            )
        oracle_row, mapping = _oracle_row(contract, identity)
        if oracle_row.get("domain") != lock["domain"] or oracle_row.get(
            "range"
        ) != lock["range"]:
            raise ProjectionO23Error(
                f"{identity}: the governed contract's declared domain/range "
                f"({oracle_row.get('domain')!r} -> {oracle_row.get('range')!r}) "
                f"no longer matches the reviewed O2.3 lock "
                f"({lock['domain']!r} -> {lock['range']!r}); contract drift "
                "requires explicit review, never silent regeneration"
            )
        if mapping.strategy != K_DERIVATION_STRATEGY:
            raise ProjectionO23Error(
                f"{identity}: the governed contract's declared strategy "
                f"{mapping.strategy!r} no longer matches the reviewed "
                f"{K_DERIVATION_STRATEGY!r} lock"
            )
        if mapping.semantic_strength != lock["semantic_strength"]:
            raise ProjectionO23Error(
                f"{identity}: the governed contract's declared semantic "
                f"strength {mapping.semantic_strength!r} no longer matches "
                f"the reviewed {lock['semantic_strength']!r} lock"
            )

    def _row(identity: str, lock: dict[str, Any]) -> dict[str, Any]:
        return {
            "identity": identity,
            "semantic_kind": "relationship",
            "relation": {
                "domain": {
                    "ontology_class": lock["domain"],
                    "lineage": dict(
                        _contract_class_anchor(
                            contract, root, lock["domain"], identity
                        )
                    ),
                },
                "range": {
                    "ontology_class": lock["range"],
                    "lineage": dict(
                        _contract_class_anchor(
                            contract, root, lock["range"], identity
                        )
                    ),
                },
                "canonical_direction": f"{lock['domain']} -> {lock['range']}",
                "native_modeled_direction": semantics["native_direction"],
                "inverse_navigation": (
                    "inverse queries reverse traversal direction only; the "
                    "modeled fact carries the validated native direction "
                    "statement (Need -> Requirement)"
                ),
                "one_modeled_fact_two_navigations": {
                    "companion_predicate": (
                        K_COMPANION_PREDICATE
                        if identity == K_CANONICAL_PREDICATE
                        else K_CANONICAL_PREDICATE
                    ),
                    "witness": (
                        "connection def DerivesFromNeed (typed ends: "
                        "need : StakeholderNeedCandidate, "
                        "derivedRequirement : RequirementCandidate)"
                    ),
                    "witness_population": (
                        f"{len(semantics['usage_witnesses'])} authored "
                        "connection usages typed by the reviewed definition"
                    ),
                    "note": (
                        "two navigations over exactly one modeled witness; "
                        "no second modeled relationship exists and "
                        "connection evidence is never duplicated as two "
                        "independent propositions"
                    ),
                },
                "semantic_strength": lock["semantic_strength"],
                "claim_boundary": semantics["claim_boundary"],
                "native_grounding": {
                    "native_construct": "DerivesFromNeed connection definition",
                    "note": (
                        "the typed ends of the governed application "
                        "definition are the grounding identity; role "
                        "identity is keyed by typing against the governed "
                        "Need/Requirement lineages — never by end order, "
                        "argument order, query direction, or names; the "
                        "representation mechanics for this witness are "
                        "recorded in the API Representation Profile"
                    ),
                },
                "scope_restrictions": [
                    {
                        "axis": "role-identity",
                        "restriction": (
                            "end roles are identified by each end's own "
                            "typing against the governed kernel lineages"
                        ),
                        "meaning": (
                            "end order, connection argument order, query "
                            "direction, declaredName, qualifiedName, "
                            "package path, and source text never establish "
                            "role identity"
                        ),
                    },
                    {
                        "axis": "witness",
                        "restriction": (
                            "the only witness is the ConnectionUsage typed "
                            "by the validated DerivesFromNeed application "
                            "definition"
                        ),
                        "meaning": (
                            "a generic Dependency with identical endpoint "
                            "types is never a derivation witness; the "
                            "standard Derivation library is deliberately "
                            "not adopted (originalImpliesDerived is "
                            "stronger and semantically wrong for this "
                            "claim) and is never silently substituted"
                        ),
                    },
                    {
                        "axis": "claim",
                        "restriction": (
                            "design-input provenance only"
                        ),
                        "meaning": (
                            "no logical implication, need or requirement "
                            "satisfaction, allocation, realization, "
                            "verification, evidence, acceptance, approval, "
                            "or certification is asserted"
                        ),
                    },
                ],
            },
            "support_state": SUPPORT_STATE_VOCABULARY_ONLY,
        }

    canonical_row = _row(K_CANONICAL_PREDICATE, canonical_lock)
    companion_row = _row(K_COMPANION_PREDICATE, companion_lock)

    # Emitted-row pair contract: opposite directions, inverse domain/range,
    # identical strength/boundary/grounding; iff-equivalence stated at the
    # contract level (every valid modeled edge satisfies
    # derivesRequirementFromNeed(R, N) iff derivedRequirementsOfNeed(N, R)).
    canonical_relation = canonical_row["relation"]
    companion_relation = companion_row["relation"]
    if (
        canonical_relation["domain"]["ontology_class"]
        != companion_relation["range"]["ontology_class"]
        or canonical_relation["range"]["ontology_class"]
        != companion_relation["domain"]["ontology_class"]
    ):
        raise ProjectionO23Error(
            "K pair drift: the companion row does not swap the canonical "
            "row's domain and range"
        )
    if canonical_relation["semantic_strength"] != companion_relation[
        "semantic_strength"
    ] or canonical_relation["claim_boundary"] != companion_relation[
        "claim_boundary"
    ]:
        raise ProjectionO23Error(
            "K pair drift: strength and claim boundary must be identical "
            "across the pair"
        )
    if canonical_relation["canonical_direction"] == companion_relation[
        "canonical_direction"
    ]:
        raise ProjectionO23Error(
            "K pair drift: the two rows must traverse the same witness in "
            "opposite canonical directions"
        )
    return canonical_row, companion_row


def derive_architecture_row(
    contract: KernelContract, root: Path
) -> dict[str, Any]:
    """Derive the ``hasRelevantArchitecture`` row from the reviewed contract.

    The declared domain/range/strength/restrictions come from the governed
    contract's entry, locked against the reviewed O2.3 lock (drift fails
    closed). The range is the reviewed application-semantic umbrella: no
    kernel binding exists for ``ArchitectureElement``, none is fabricated,
    and the exact reviewed contract (architecture-side part/action
    representation AND not MemberProduct lineage AND authored incoming
    relevance dependency AND Requirement-domain query source) carries the
    range meaning. The Requirement and MemberProduct lineage anchors are
    proven from the governed model declarations.
    """
    identity = "hasRelevantArchitecture"
    lock = _O23_PREDICATE_LOCKS[identity]
    mapping = contract.relationship_mapping(identity)
    if (
        mapping.domain != lock["domain"]
        or mapping.range != lock["range"]
        or mapping.strategy != lock["strategy"]
        or mapping.semantic_strength != lock["semantic_strength"]
    ):
        raise ProjectionO23Error(
            f"{identity}: the governed contract's declared domain/range/"
            "strategy/strength no longer matches the reviewed O2.3 lock "
            f"(contract: domain={mapping.domain!r} range={mapping.range!r} "
            f"strategy={mapping.strategy!r} strength={mapping.semantic_strength!r}); "
            "contract drift requires explicit review, never silent regeneration"
        )
    relationship_types = mapping.configuration.get("relationship_types")
    if (
        not isinstance(relationship_types, list)
        or tuple(relationship_types) != lock["relationship_types"]
    ):
        raise ProjectionO23Error(
            f"{identity}: declared relationship witnesses "
            f"{relationship_types!r} do not match the reviewed witness lock "
            f"{lock['relationship_types']!r}"
        )
    if str(mapping.configuration.get("direction")) != lock["direction"]:
        raise ProjectionO23Error(
            f"{identity}: declared direction "
            f"{mapping.configuration.get('direction')!r} does not match the "
            f"reviewed {lock['direction']!r} lock"
        )
    source_types = mapping.configuration.get("source_types")
    if (
        not isinstance(source_types, list)
        or tuple(source_types) != lock["source_types"]
    ):
        raise ProjectionO23Error(
            f"{identity}: declared source types {source_types!r} do not "
            f"match the reviewed lock {lock['source_types']!r}"
        )
    exclusion = mapping.configuration.get("exclude_source_specializations_of")
    if exclusion != lock["exclude_source_specializations_of"]:
        raise ProjectionO23Error(
            f"{identity}: the load-bearing MemberProduct exclusion "
            f"({exclusion!r}) does not match the reviewed lock "
            f"({lock['exclude_source_specializations_of']!r})"
        )

    domain_anchor = _contract_class_anchor(contract, root, "Requirement", identity)
    exclusion_anchor = _contract_class_anchor(
        contract, root, lock["exclude_source_specializations_of"], identity
    )
    return {
        "identity": identity,
        "semantic_kind": "relationship",
        "relation": {
            "domain": {
                "ontology_class": "Requirement",
                "lineage": dict(domain_anchor),
            },
            "range": {
                "ontology_class": "ArchitectureElement",
                "identity_basis": "application-semantic umbrella",
                "note": (
                    "the reviewed model has no single file/declaration "
                    "kernel binding for ArchitectureElement; none is "
                    "fabricated and API metaclass equality is never "
                    "upgraded into semantic identity proof. The range "
                    "meaning is established by the exact reviewed "
                    "application contract: architecture-side part/action "
                    "representation AND not MemberProduct lineage AND "
                    "authored incoming relevance dependency AND a query "
                    "source machine-proven in the governed Requirement "
                    "lineage"
                ),
            },
            "exclusion_lineage": {
                "ontology_class": lock["exclude_source_specializations_of"],
                "lineage": dict(exclusion_anchor),
                "meaning": (
                    "the load-bearing exclusion set: sources resolving into "
                    "this lineage never become architecture relevance"
                ),
            },
            "canonical_direction": f"{lock['domain']} -> {lock['range']}",
            "inverse_navigation": (
                "the authored witness is an incoming dependency with the "
                "architecture-side element as source and the requirement as "
                "target; the canonical Requirement -> ArchitectureElement "
                "query reads that witness without reversing the semantic "
                "claim"
            ),
            "semantic_strength": lock["semantic_strength"],
            "native_grounding": {
                "native_construct": "authored generic Dependency",
                "note": (
                    "the native generic Dependency supplies the witness; "
                    "the load-bearing DE4SDV restrictions below are part "
                    "of the predicate's meaning — generic Dependency by "
                    "itself is NOT hasRelevantArchitecture. Representation "
                    "mechanics are recorded in the API Representation "
                    "Profile"
                ),
            },
            "scope_restrictions": [
                {
                    "axis": "source-domain",
                    "restriction": (
                        "the canonical query source must machine-resolve "
                        "into the governed Requirement lineage"
                    ),
                    "meaning": (
                        "declared domain enforcement: Need-sourced and "
                        "other non-Requirement queries are quiet absence; "
                        "Requirement identity is proven through the "
                        "validated kernel-binding/lineage mechanism, never "
                        "from the RequirementUsage API metaclass (Need "
                        "serializes through related/same API shapes), "
                        "names, package paths, source text, or filenames"
                    ),
                },
                {
                    "axis": "source-types",
                    "restriction": (
                        "the dependency source must be an architecture-side "
                        "part/action representation (PartUsage, "
                        "PartDefinition, ActionUsage, ActionDefinition)"
                    ),
                    "meaning": (
                        "the representation-level carrier of the "
                        "ArchitectureElement umbrella; a generic Dependency "
                        "without an architecture-side source type is not "
                        "this predicate"
                    ),
                },
                {
                    "axis": "exclusion",
                    "restriction": (
                        "sources in the governed MemberProduct lineage are "
                        "excluded"
                    ),
                    "meaning": (
                        "load-bearing: configured-product traces are "
                        "product-line relationships, not architecture "
                        "relevance; the exclusion is proven through the "
                        "validated MemberProduct specialization lineage, "
                        "not by name"
                    ),
                },
                {
                    "axis": "witness",
                    "restriction": (
                        "an authored incoming Dependency with the "
                        "architecture-side element as source and the "
                        "requirement as target"
                    ),
                    "meaning": (
                        "the canonical Requirement -> ArchitectureElement "
                        "query is reverse reading of this witness; the "
                        "modeled fact never reverses"
                    ),
                },
            ],
        },
        "support_state": SUPPORT_STATE_VOCABULARY_ONLY,
    }


# ---------------------------------------------------------------------------
# Binding collection and the extends (baseline) block
# ---------------------------------------------------------------------------


def collect_bound_inputs_o23(root: Path, contract: KernelContract) -> dict[str, str]:
    """Every source consumed to produce the extension artifacts.

    Program inputs are declared in :data:`BOUND_INPUT_PROGRAM_PATHS_O23`;
    data inputs are the O2.3 admission manifest, the ontology/kernel contract
    (locators + oracle only), the baseline v1.1 projection and profile (the
    extensions' ``extends`` targets), the governed lineage-anchor model files
    (Requirement, Need, MemberProduct), the K connection-definition file, and
    the governed K usage-witness file. Derived mechanically so a changed
    membership cannot silently drop an input.
    """
    paths: set[str] = set(BOUND_INPUT_PROGRAM_PATHS_O23)
    paths.add(ADMISSION_O23_PATH)
    paths.add(ONTOLOGY_PATH)
    paths.add(BASELINE_PROJECTION_V11_PATH)
    paths.add(BASELINE_PROFILE_V11_PATH)
    paths.add(K_WITNESS_MODEL_FILE)
    for ontology_class in ("Requirement", "Need", "MemberProduct"):
        mapping = contract.mapping(ontology_class)
        if isinstance(mapping, KernelFileMapping):
            paths.add(mapping.file)
    mapping = contract.mapping(K_CONNECTION_DEFINITION_CLASS)
    if isinstance(mapping, KernelFileMapping):
        paths.add(mapping.file)
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise ProjectionO23Error(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


def read_baseline_pins(root: Path) -> dict[str, dict[str, Any]]:
    """Build the two independent ``extends`` pins from the v1.1 baselines.

    The Semantic Projection extension extends the Semantic Projection
    baseline; the API Representation Profile extension independently extends
    the API Representation Profile baseline. Each pin records and verifies
    the baseline's artifact path, schema, source revision, and artifact
    digest — fail closed on a missing, unreadable, wrong-schema, or
    revision-less baseline. The two baselines happen to share one source
    revision today, but each pin records its own; nothing assumes equality.
    """
    pins: dict[str, dict[str, Any]] = {}
    for key, artifact_path, expected_schema in (
        ("projection", BASELINE_PROJECTION_V11_PATH, PROJECTION_V11_SCHEMA),
        ("profile", BASELINE_PROFILE_V11_PATH, PROFILE_V11_SCHEMA),
    ):
        pins[key] = _read_baseline_pin(root, artifact_path, expected_schema)
    return pins


def _read_baseline_pin(
    root: Path, artifact_path: str, expected_schema: str
) -> dict[str, Any]:
    import json

    path = root / artifact_path
    if not path.is_file():
        raise ProjectionO23Error(
            f"O2.2 baseline not found: {artifact_path}; the extension cannot "
            "anchor to an unpublished baseline"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ProjectionO23Error(
            f"O2.2 baseline {artifact_path} is not readable JSON: {exc}"
        ) from exc
    if document.get("schema") != expected_schema:
        raise ProjectionO23Error(
            f"O2.2 baseline {artifact_path} schema mismatch: expected "
            f"{expected_schema!r}, found {document.get('schema')!r}"
        )
    baseline_revision = (document.get("binding") or {}).get("source_revision")
    if not isinstance(baseline_revision, str) or len(baseline_revision) != 40:
        raise ProjectionO23Error(
            f"O2.2 baseline {artifact_path} does not record a full-commit "
            "binding.source_revision"
        )
    return {
        "artifact": artifact_path,
        "schema": expected_schema,
        "source_revision": baseline_revision,
        "artifact_digest": file_digest(root, artifact_path),
        "note": (
            "Additive extension of this immutable O2.2 baseline: the baseline "
            "remains canonical for its own content and is neither re-emitted "
            "nor re-bound here. The recorded digest pins the baseline bytes "
            "this extension was generated against; the baseline's own "
            "repository gate validates its revision binding, and the "
            "extension gate additionally requires the baseline source "
            "revision to remain an ancestor of the extension source revision."
        ),
    }


# ---------------------------------------------------------------------------
# Artifact assembly
# ---------------------------------------------------------------------------


def _binding_block_o23(
    root: Path,
    source_revision: str,
    bound_inputs: dict[str, str],
) -> dict[str, Any]:
    """Revision binding shared by the extension projection and profile."""
    program_inputs = sorted(BOUND_INPUT_PROGRAM_PATHS_O23)
    non_program = (
        set(BOUND_INPUT_PROGRAM_PATHS_O23)
        | {
            ADMISSION_O23_PATH,
            ONTOLOGY_PATH,
            BASELINE_PROJECTION_V11_PATH,
            BASELINE_PROFILE_V11_PATH,
        }
    )
    return {
        "source_revision": source_revision,
        "source_revision_note": (
            "Git commit that contains every bound input byte-for-byte. The "
            "gate validates commit existence, ancestry of the checked-out "
            "revision, per-input content equality, and the recorded content "
            "digests - a stale revision cannot pass by string reuse."
        ),
        "artifact_commit": None,
        "artifact_commit_note": (
            "The commit that introduces these artifacts cannot be known when "
            "they are generated; left explicitly unclaimed."
        ),
        "generation_software": {
            "program_inputs": program_inputs,
            "note": (
                "Generation-software revision: the commit containing these "
                "program inputs byte-for-byte (including the frozen O2.1 "
                "module whose locks this extension imports, the O2.2 module "
                "whose reviewed anchor locators it reuses, the v0 K module "
                "whose reviewed pair-parity gate `_assert_oracle_parity` "
                "EXECUTES during generation, the v0 model-authority module "
                "whose K probes it reuses, and the sysml_api revision-identity "
                "plumbing executed through contract loading). "
                "Distinguished from the semantic-model revision so generator "
                "changes are never confused with model or contract changes."
            ),
        },
        "semantic_model_revision": {
            "model_inputs": sorted(
                path for path in bound_inputs if path not in non_program
            ),
            "note": (
                "Semantic-model revision: the governed model declarations "
                "and the reviewed contract files these artifacts were "
                "generated from, contained byte-for-byte in source_revision. "
                "The ontology/kernel contract supplies the reviewed declared "
                "predicate contract and declaration locators (and, for the K "
                "pair only, the O0/O1 parity oracle rows); the model files "
                "carry the lineage anchors and the governed derivation "
                "witnesses."
            ),
        },
        "api_binding": {
            "status": "unclaimed",
            "note": (
                "O2.3 produces no validated SysML API project/commit closure "
                "and claims no current API element UUID. Element identity is "
                "resolved at a bound API revision through ingestion-validated "
                "kernel bindings (KernelBindingIndex, fail closed); the "
                "exact-revision API closure belongs to the privileged "
                "ingestion path and a later reviewed step. Retained "
                "privileged-run evidence (including the K slice's retained "
                "closure run at its own earlier revision) is "
                "representation-shape evidence only."
            ),
        },
        "admission_manifest": {
            "path": ADMISSION_O23_PATH,
            "digest": bound_inputs[ADMISSION_O23_PATH],
        },
        "ontology_contract_locator": {
            "path": ONTOLOGY_PATH,
            "digest": bound_inputs[ONTOLOGY_PATH],
        },
        "baseline_projection": {
            "path": BASELINE_PROJECTION_V11_PATH,
            "digest": bound_inputs[BASELINE_PROJECTION_V11_PATH],
        },
        "baseline_profile": {
            "path": BASELINE_PROFILE_V11_PATH,
            "digest": bound_inputs[BASELINE_PROFILE_V11_PATH],
        },
        "bound_inputs": bound_inputs,
    }


def _scope_block_o23(manifest: dict[str, Any]) -> dict[str, Any]:
    """The machine-locked O2.3 admission boundary, echoed for reviewability."""
    return {
        "admission": (
            "O2.3 additive generation stage (final O2 slice: K pair and "
            "bounded architecture relevance)"
        ),
        "admitted": list(O23_ADMITTED_IDENTITIES),
        "sequencing": {
            phase: list(identities) for phase, identities in O2_SEQUENCING.items()
        },
        "cumulative_surface": {
            "o2_1": list(O21_ADMITTED_IDENTITIES),
            "o2_2": list(O2_SEQUENCING["o2.2"]),
            "o2_3": list(O23_ADMITTED_IDENTITIES),
            "total": len(O23_CUMULATIVE_SURFACE),
            "note": (
                "Cumulative reviewed O2 semantic surface: the O2.1 seven (in "
                "the immutable v1 baseline) plus the O2.2 three (in the "
                "immutable v1.1 baseline) plus the O2.3 three (in this "
                "extension) = exactly thirteen distinct identities; no "
                "fourteenth identity exists."
            ),
        },
        "guarded": [
            {
                "identity": str(entry["identity"]),
                "kind": str(entry["kind"]),
                "reason": " ".join(str(entry["reason"]).split()),
            }
            for entry in manifest["guarded"]
        ],
        "admission_note": (
            "Machine-locked reviewed migration boundary: the emission path "
            "iterates the admitted set only (no heuristic query); an extra "
            "identity, a missing admitted identity, a re-emission of the "
            "O2.1/O2.2 baseline sets, or any other guarded identity is a "
            "generation failure."
        ),
    }


# ---------------------------------------------------------------------------
# Representation profile (mechanics only)
# ---------------------------------------------------------------------------


def _profile_entry_o23(row: dict[str, Any], contract: KernelContract) -> dict[str, Any]:
    """Per-identity representation profile (mechanics, keyed to semantics).

    All serializer/API mechanics live here: connection/dependency strategy,
    query direction, connection role names, API metaclasses, property paths,
    end resolution, exclusion filters, resolution rules, and evidence. The
    entry echoes the projection's semantic contract as
    ``semantic_contract_echo``; the compatibility gate fails closed if the
    echo contradicts the projection — mechanics can never redefine meaning.
    """
    identity = row["identity"]
    relation = row["relation"]
    echo = {
        "domain": relation["domain"]["ontology_class"],
        "range": relation["range"]["ontology_class"],
        "canonical_direction": relation["canonical_direction"],
        "semantic_strength": relation["semantic_strength"],
        "scope_restrictions": [
            entry["restriction"] for entry in relation["scope_restrictions"]
        ],
    }

    if identity in (K_CANONICAL_PREDICATE, K_COMPANION_PREDICATE):
        mapping = contract.relationship_mapping(identity)
        config = mapping.configuration
        mechanics = {
            "strategy": mapping.strategy,
            "connection_definition": config.get("connection_definition"),
            "need_role": config.get("need_role"),
            "requirement_role": config.get("requirement_role"),
            "query_direction": config.get("query_direction"),
            "source_lineage_of": config.get("source_lineage_of"),
            "target_lineage_of": config.get("target_lineage_of"),
            "semantic_strength": mapping.semantic_strength,
        }
        canonical_is_inverse = identity == K_CANONICAL_PREDICATE
        witness_forms = [
            "ConnectionUsage typed by the validated `connection def "
            "DerivesFromNeed` application definition (an ontology-mapped "
            "kernel declaration resolved through the ingestion-validated "
            "kernel binding index, never by name) — the only witness; a "
            "generic Dependency with identical endpoint types is never a "
            "derivation, and the standard Derivation library is deliberately "
            "not adopted and never silently substituted",
            "end-role extraction is keyed by each end's OWN typing against "
            "the governed Need/Requirement kernel lineages (need : "
            "StakeholderNeedCandidate, derivedRequirement : "
            "RequirementCandidate) — never by end order, connection argument "
            "order, query direction, declaredName, qualifiedName, package "
            "path, or source text; the modeled direction is the validated "
            "documentation statement (need -> derivedRequirement), so "
            "reordering the two end declarations changes nothing",
            (
                "the canonical Requirement -> Need query is INVERSE traversal "
                "over the native witness (native direction need -> "
                "derivedRequirement)"
                if canonical_is_inverse
                else "the canonical Need -> Requirement query is FORWARD "
                "traversal over the SAME native witness (native direction "
                "need -> derivedRequirement)"
            ),
            "one modeled fact, two navigations: both predicates traverse the "
            "identical witness population; no second modeled relationship "
            "exists and connection evidence is never duplicated as two "
            "independent propositions",
            "lineage enforcement runs through the validated kernel binding "
            "index and the representation-tolerant relationship graph; "
            "explicit versus implied grounding provenance is preserved; a "
            "corrupted witness (untyped end, foreign definition typing, end "
            "outside the declared kernel lineages) raises instead of "
            "degrading silently",
        ]
        return {
            "profile_identity": f"{PROFILE_V12_SCHEMA}#{identity}",
            "for_identity": identity,
            "representation_class": f"{mapping.strategy}-relationship",
            "semantic_contract_echo": echo,
            "serializer_mechanics": mechanics,
            "resolution": {
                "identity": _O23_IDENTITY_RESOLUTION,
                "lineage": _O23_LINEAGE_RESOLUTION,
            },
            "witness_forms": witness_forms,
            "mechanics_refs": {
                "runtime_strategy": mapping.strategy,
                "lineage_resolver": (
                    "validated lineage proof through the kernel binding index "
                    "and the representation-tolerant relationship graph "
                    "(fail closed)"
                ),
            },
            "runtime_mapping_state": RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY,
            "runtime_mapping_note": (
                "the derivation-connection runtime mapping exists and is "
                "reviewed; it is representation evidence for this profile, "
                "never semantic authority for the projection, and its "
                "historical closure evidence does not promote support"
            ),
        }

    mapping = contract.relationship_mapping(identity)
    config = mapping.configuration
    mechanics = {
        "strategy": mapping.strategy,
        "relationship_types": list(config.get("relationship_types") or ()),
        "direction": config.get("direction"),
        "source_property": config.get("source_property"),
        "target_property": config.get("target_property"),
        "source_types": list(config.get("source_types") or ()),
        "exclude_source_specializations_of": config.get(
            "exclude_source_specializations_of"
        ),
    }
    witness_forms = [
        "the authored witness is an incoming Dependency with the "
        "architecture-side element as source and the requirement as target "
        "(source_property/target_property extraction); the canonical "
        "Requirement -> ArchitectureElement query reads the witness via "
        "direction: incoming without reversing the semantic claim",
        "candidate-first: a queried source touching no configured Dependency "
        "on the traversal side is quiet absence and performs no lineage "
        "resolution",
        "source-domain identity rule: the queried source must machine-prove "
        "governed Requirement identity through the validated kernel-binding "
        "and lineage mechanism — RequirementUsage API metaclass equality is "
        "representation evidence only (Need serializes through related/same "
        "API shapes); Need-sourced and other non-Requirement queries are "
        "quiet absence; candidates-with-candidates missing bindings raise "
        "(IdentityNotFoundError); names never steer",
        "MemberProduct exclusion by specialization lineage (definitions and "
        "usages typed by them), proven through the validated lineage "
        "mechanism — a same-named part without lineage proof does not "
        "control identity",
        "the source-types filter (PartUsage, PartDefinition, ActionUsage, "
        "ActionDefinition) is the representation-level carrier of the "
        "ArchitectureElement umbrella; the metaclass match alone is not "
        "semantic identity proof",
        "generic Dependency existence alone does not imply satisfaction, "
        "realization, allocation, specification, product-line selection, or "
        "deployment",
    ]
    return {
        "profile_identity": f"{PROFILE_V12_SCHEMA}#{identity}",
        "for_identity": identity,
        "representation_class": f"{mapping.strategy}-relationship",
        "semantic_contract_echo": echo,
        "serializer_mechanics": mechanics,
        "resolution": {
            "identity": _O23_IDENTITY_RESOLUTION,
            "lineage": _O23_LINEAGE_RESOLUTION,
        },
        "witness_forms": witness_forms,
        "mechanics_refs": {
            "runtime_strategy": mapping.strategy,
            "lineage_resolver": (
                "validated lineage proof through the kernel binding index and "
                "the representation-tolerant relationship graph (fail closed)"
            ),
            "exclusion_resolver": (
                "MemberProduct specialization-lineage exclusion over the "
                "representation-tolerant relationship graph (load-bearing, "
                "fail closed)"
            ),
        },
        "runtime_mapping_state": RUNTIME_MAPPING_STATE_EXISTING_NOT_AUTHORITY,
        "runtime_mapping_note": (
            "the dependency runtime mapping exists and is reviewed (c5 "
            "retained-run shape evidence at its own revision); it is "
            "representation evidence for this profile, never semantic "
            "authority for the projection"
        ),
    }


def _representation_contract_o23() -> dict[str, Any]:
    """The O2.3 representation mechanics, witnessed by the evidence basis."""
    return {
        "identity_resolution": {
            "rule": _O23_IDENTITY_RESOLUTION,
            "prohibited_fallbacks": [
                "declaredName alone",
                "qualifiedName alone",
                "package path",
                "source filename",
                "doc text",
                "string matching",
            ],
        },
        "lineage_resolution": _O23_LINEAGE_RESOLUTION,
        "derivation_connection_mechanics": (
            "the K witness is the ConnectionUsage typed by the validated "
            "DerivesFromNeed application definition; end roles are keyed by "
            "typing against the governed Need/Requirement lineages; the "
            "native direction is need -> derivedRequirement and the two "
            "canonical queries read the same witness forward and inverse; "
            "witness corruption raises instead of degrading silently"
        ),
        "dependency_mechanics": (
            "the architecture-relevance witness is the authored generic "
            "Dependency read incoming (architecture-side source, requirement "
            "target); domain, source-type, and MemberProduct-lineage "
            "restrictions are enforced fail-closed through the validated "
            "kernel bindings before a hop is emitted"
        ),
        "serializer_importer_compatibility": {
            "uuid_preservation": "single-transaction-required",
            "known_omissions": [],
            "out_of_export_risk": (
                "the DerivesFromNeed definition, its typed ends, its "
                "connection usages, the lineage anchors, and the authored "
                "relevance dependencies must survive official export, API "
                "import, and read-back; pruning any required witness makes "
                "the identity unsupported for that revision"
            ),
        },
        "completeness_check": (
            "fail closed: a missing or drifted contract entry, a missing or "
            "ambiguous model witness (definition or usage population), a "
            "missing lineage anchor declaration, a missing or conflicting "
            "claim-strength doc, or a foreign connection typing blocks "
            "generation for that identity"
        ),
    }


def assert_profile_compatible_o23(
    projection: dict[str, Any], profile: dict[str, Any]
) -> None:
    """Compatibility gate: mechanics must not contradict the projection.

    Same discipline as corrected O2.2: the profile's per-identity
    ``semantic_contract_echo`` must equal the projection's semantic contract
    (domain, range, canonical direction, semantic strength, scope
    restrictions), so representation mechanics can never redefine meaning;
    and every row must carry the established ``vocabulary-only`` support
    state — there is no promotion path and no other support vocabulary.
    """
    projection_rows = list(projection.get("concepts", [])) + list(
        projection["predicates"]
    )
    projection_by_identity = {row["identity"]: row for row in projection_rows}
    profile_by_identity = {entry["for_identity"]: entry for entry in profile["profiles"]}
    if set(projection_by_identity) != set(profile_by_identity):
        raise ProjectionO23Error(
            "profile identities do not match the projection identities: "
            f"projection-only={sorted(set(projection_by_identity) - set(profile_by_identity))} "
            f"profile-only={sorted(set(profile_by_identity) - set(projection_by_identity))}"
        )
    for identity, row in projection_by_identity.items():
        if row["support_state"] != SUPPORT_STATE_VOCABULARY_ONLY:
            raise ProjectionO23Error(
                f"{identity}: support state {row['support_state']!r} violates "
                "the established rule (without structured exact-revision "
                "closure evidence, support_state is vocabulary-only)"
            )
        entry = profile_by_identity[identity]
        relation = row["relation"]
        expected = {
            "domain": relation["domain"]["ontology_class"],
            "range": relation["range"]["ontology_class"],
            "canonical_direction": relation["canonical_direction"],
            "semantic_strength": relation["semantic_strength"],
            "scope_restrictions": [
                item["restriction"] for item in relation["scope_restrictions"]
            ],
        }
        if entry["semantic_contract_echo"] != expected:
            raise ProjectionO23Error(
                f"{identity}: the representation profile's echoed semantic "
                "contract contradicts the projection — mechanics cannot "
                "redefine domain, range, canonical direction, semantic "
                "strength, scope restrictions, or claim boundaries"
            )


# ---------------------------------------------------------------------------
# Build + committed-artifact consistency gate (--check)
# ---------------------------------------------------------------------------


def _build_pair_o23(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
    contract: KernelContract | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build both extension artifacts over identical inputs."""
    if manifest is None:
        manifest = load_admission_manifest_o23(root / ADMISSION_O23_PATH)
    validate_admission_o23(manifest)
    if contract is None:
        contract = KernelContract.load(root / ONTOLOGY_PATH)
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    bound_inputs = collect_bound_inputs_o23(root, contract)
    verify_source_revision_contains_inputs(root, source_revision, bound_inputs)
    baseline_pins = read_baseline_pins(root)

    try:
        semantics = derive_k_semantics(contract, root)
        _assert_k_pair_invariants(semantics)
        canonical_row, companion_row = derive_k_pair_rows(
            contract, root, semantics
        )
        architecture_row = derive_architecture_row(contract, root)
    except ProjectionO22Error as exc:
        # The O2.2 anchor locators are reused read-only; their fail-closed
        # errors are translated into this stage's error type so the gate
        # reports O2.3 attribution.
        raise ProjectionO23Error(
            f"O2.3 model grounding failed via the shared O2.2 anchor "
            f"locators: {exc}"
        ) from exc

    emitted = (
        canonical_row["identity"],
        companion_row["identity"],
        architecture_row["identity"],
    )
    if emitted != O23_ADMITTED_IDENTITIES:
        raise ProjectionO23Error(
            f"emitted identities {emitted!r} do not equal the frozen O2.3 "
            f"admission {O23_ADMITTED_IDENTITIES!r}"
        )
    leaked = sorted(set(emitted) & set(O23_GUARDED_IDENTITIES))
    if leaked:
        raise ProjectionO23Error(
            f"guarded identities leaked into O2.3 output: {leaked}"
        )

    binding = _binding_block_o23(root, source_revision, bound_inputs)
    projection = {
        "schema": PROJECTION_V12_SCHEMA,
        "status": (
            "generated O2.3 additive semantic projection extension "
            "(final O2 slice: the K derivation pair and bounded "
            "architecture relevance)"
        ),
        "warning": (
            "Generated artifact. Additive extension of the immutable O2.2 "
            "semantic-projection baseline (see `extends`). Generation is NOT "
            "authority activation: this projection does not switch runtime "
            "dispatch, does not retire authored contract authority, and "
            "promotes no support state (historical K closure evidence does "
            "not promote current support). The O1 migration inventory is "
            "governance, never semantic authority, and is not read by this "
            "generator. The runtime does not read this artifact. Fields in "
            "the projected semantic core are derived from the governed "
            "authoritative representation; projection-schema claim "
            "boundaries, admission governance, representation-profile "
            "mechanics, and provenance metadata are explicitly separated and "
            "identified as such. Generated by "
            "scripts/generate_semantic_projection_o23.py."
        ),
        "extends": baseline_pins["projection"],
        "binding": binding,
        "scope": _scope_block_o23(manifest),
        "projection_contract": dict(PROJECTION_CONTRACT_O23),
        "predicates": [canonical_row, companion_row, architecture_row],
    }
    profile = {
        "schema": PROFILE_V12_SCHEMA,
        "profile_version": "v1.2",
        "status": (
            "generated O2.3 SysML API Representation Profile extension "
            "(representation mechanics for the K derivation pair and "
            "bounded architecture relevance)"
        ),
        "warning": (
            "Generated artifact. Representation mechanics only: this profile "
            "cannot redefine domain, range, canonical direction, semantic "
            "strength, scope restrictions, exclusions, or claim boundaries - "
            "those live in the Semantic Projection (the per-identity "
            "`semantic_contract_echo` is held to them by the compatibility "
            "gate). No current SysML API project/commit closure was produced "
            "and no current API element UUID is claimed; retained privileged "
            "runs are representation-shape evidence only. The runtime does "
            "not read this artifact."
        ),
        "extends": baseline_pins["profile"],
        "binding": binding,
        "evidence_basis": {
            "kind": "retained privileged full-model API ingestion run",
            "run": "10195168006",
            "artifact": (
                "full-model-api-ingestion-0a23902370de9fc74d6118afe480382e0b0d8aa0"
            ),
            "candidate_revision": "0a23902370de9fc74d6118afe480382e0b0d8aa0",
            "scope": (
                "Serializer representation shapes only (dependency witness "
                "shapes, lineage enforcement shapes). Not a current "
                "exact-revision API closure and not a semantic source for "
                "generation; the K slice's retained closure run is likewise "
                "shape evidence only and does not promote support."
            ),
        },
        "representation_contract": _representation_contract_o23(),
        "profiles": [
            _profile_entry_o23(row, contract)
            for row in (canonical_row, companion_row, architecture_row)
        ],
    }
    assert_profile_compatible_o23(projection, profile)
    return projection, profile


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_pair_o23(
    root: Path,
    *,
    source_revision: str | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build both extension artifacts from the given checkout."""
    projection, profile = _build_pair_o23(
        root, source_revision=source_revision, manifest=manifest
    )
    return {"projection": projection, "profile": profile}


def run_check_errors_o23(root: Path) -> list[str]:
    """Check that the extension artifacts equal regeneration from inputs.

    Validates the recorded source-revision binding (commit existence,
    ancestry, per-input content equality, recorded digests), the two
    INDEPENDENT baseline anchors (each extension must extend its own v1.1
    baseline: path/schema/source revision/digest — digest equality against
    the committed baseline bytes and baseline-source-revision ancestry),
    then regenerates with the recorded source revision and compares bytes
    for both artifacts. Absent artifacts are reported as errors — nothing is
    silently passed. Stage A does not register this gate in ``check_repo``;
    Stage B registers it together with the artifacts.
    """
    import json

    errors: list[str] = []
    projection_path = root / PROJECTION_V12_JSON_PATH
    profile_path = root / PROFILE_V12_JSON_PATH
    if not projection_path.is_file():
        errors.append(f"semantic projection v1.2 missing: {PROJECTION_V12_JSON_PATH}")
    if not profile_path.is_file():
        errors.append(
            f"api representation profile v1.2 missing: {PROFILE_V12_JSON_PATH}"
        )
    if errors:
        return errors
    try:
        committed = json.loads(projection_path.read_text(encoding="utf-8"))
        committed_profile = json.loads(profile_path.read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [
            f"{PROJECTION_V12_JSON_PATH}: cannot read binding for validation: {exc}"
        ]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{PROJECTION_V12_JSON_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    source_revision = binding["source_revision"]
    for label, document, artifact_path, expected_schema in (
        (
            "projection",
            committed,
            BASELINE_PROJECTION_V11_PATH,
            PROJECTION_V11_SCHEMA,
        ),
        ("profile", committed_profile, BASELINE_PROFILE_V11_PATH, PROFILE_V11_SCHEMA),
    ):
        pin = document.get("extends")
        if not isinstance(pin, dict):
            errors.append(
                f"{PROJECTION_V12_JSON_PATH}: {label} extension pin missing"
            )
            continue
        if pin.get("artifact") != artifact_path or pin.get("schema") != expected_schema:
            errors.append(
                f"{label} extension must extend {artifact_path} "
                f"({expected_schema}); recorded pin: "
                f"artifact={pin.get('artifact')!r} schema={pin.get('schema')!r}"
            )
        baseline_file = root / artifact_path
        if not baseline_file.is_file():
            errors.append(f"O2.2 baseline missing: {artifact_path}")
            continue
        if pin.get("artifact_digest") != file_digest(root, artifact_path):
            errors.append(
                f"{label} baseline digest does not match `extends.artifact_digest` "
                "(the baseline was modified or the extension is stale)"
            )
        baseline_revision = pin.get("source_revision")
        if isinstance(baseline_revision, str) and baseline_revision:
            result = _git(
                root, "merge-base", "--is-ancestor", baseline_revision, source_revision
            )
            if result.returncode != 0:
                errors.append(
                    f"{label} baseline source revision {baseline_revision} is "
                    f"not an ancestor of the extension source revision "
                    f"{source_revision}"
                )
    if errors:
        return errors
    try:
        artifacts = build_pair_o23(root, source_revision=source_revision)
    except ProjectionO23Error as exc:
        return [f"semantic projection v1.2 generation failed: {exc}"]
    if canonical_json(artifacts["projection"]) != projection_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROJECTION_V12_JSON_PATH}: committed projection differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if canonical_json(artifacts["profile"]) != profile_path.read_text(
        encoding="utf-8"
    ):
        errors.append(
            f"{PROFILE_V12_JSON_PATH}: committed profile differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    return errors





