"""Semantic Authority Inventory (O1) — observed-fact extraction and validation.

Governance/migration artifact for the O1 parity-controlled extension
(Unified Semantic Engineering Plan v1.1, section 8). This module builds the
canonical *Semantic Authority Inventory* from repository evidence. It is
NEVER imported by the semantic runtime: the inventory is a migration and
governance artifact, not runtime semantic authority, and the generator is
offline and deterministic from repository state.

Two layers, per the accepted Phase-1 review (PR #249):

- **Layer A — observed facts**: mechanically derived from repository evidence
  (ontology contract structure, kernel mappings, kernel declarations and
  exclusions, the runtime traversal strategy dispatch, model-resident
  documentation, consumer associations, retained closure records). Nothing in
  Layer A restates meaning from Python.
- **Layer B — reviewed decisions**: committed governance/migration metadata
  (authority classification, targets, evidence state, adoption status,
  transition gates, dispositions, stages, unknowns, required evidence). Layer
  B lives in the committed decisions dataset
  (``docs/method-conformance/o1/authority-review-decisions.yaml``), never in
  Python constants, and is never runtime semantic authority.

The generator joins A + B, validates coverage and consistency, and emits the
canonical inventory plus the human-readable review table. Validation fails
closed: an unaccounted ontology entry, kernel declaration, kernel exclusion,
runtime strategy, closure record, or missing decision row is a generation
error.

Determinism: identical inputs (ontology contract, decisions dataset, closure
records, traversal source, recorded Git revision/base) produce byte-identical
output. No timestamps, no environment-dependent values.

Boundaries (Wave 0a):

- no runtime semantic behavior change and no import from this module by the
  runtime;
- no new generated Semantic Projection rows and no support promotion;
- no YAML retirement;
- native representation primitives do not establish native semantic
  authority: this module computes grounding facts and preserves the reviewed
  classification, and never infers ``authority_current = native-sysml`` from
  a ``kernel.native`` ontology mapping.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .kernel_contract import KernelContract, declaration_identity

# ---------------------------------------------------------------------------
# Schema and closed vocabularies
# ---------------------------------------------------------------------------

SCHEMA_ID = "de4sdv.semantic-authority-inventory/v1"
DECISIONS_SCHEMA_ID = "de4sdv.semantic-authority-reviews/v1"
CLOSURE_SCHEMA_ID = "de4sdv.closure-evidence/v1"

ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
DECISIONS_PATH = "docs/method-conformance/o1/authority-review-decisions.yaml"
CLOSURE_PATH = "docs/method-conformance/o1/closure-evidence.json"
INVENTORY_JSON_PATH = "docs/method-conformance/o1/semantic-authority-inventory.json"
INVENTORY_MD_PATH = "docs/method-conformance/o1/authority-inventory.md"
TRAVERSAL_SOURCE_PATH = "de4sdv/semantic/traversal.py"

#: Accepted authority vocabulary (where meaning is established). Closed set:
#: extending it requires an explicit reviewed schema decision, not a silent
#: addition (task boundary, Wave 0a).
AUTHORITY_SOURCES: tuple[str, ...] = (
    "model-authoritative",
    "native-sysml",
    "native-kerml",
    "accepted-library-grounded",
    "de4sdv-application-semantic",
    "external-reference",
    "legacy-yaml",
    "unknown",
)

#: Accepted evidence-maturity vocabulary. A target is never current proof.
EVIDENCE_STATES: tuple[str, ...] = (
    "proposed",
    "repository-evidenced",
    "parity-reviewed",
    "exact-toolchain-validated",
    "privileged-closure-proven",
    "blocked",
    "unknown",
)

#: Accepted library/upstream adoption vocabulary.
ADOPTION_STATUSES: tuple[str, ...] = (
    "accepted",
    "pinned-not-adopted",
    "candidate",
    "rejected",
    "not-applicable",
)

#: Disposition vocabulary (migration disposition of one entry).
DISPOSITIONS: tuple[str, ...] = (
    "move-meaning-into-model",
    "keep-as-is",
    "retain-explicit-external-boundary",
    "defer",
    "prove-existing-model-authority",
    "introduce-minimal-de4sdv-relation",
    "adopt-accepted-library-relation",
)

#: Text-parity observation vocabulary (Layer A, doc-text observation).
DOC_OBSERVATIONS: tuple[str, ...] = (
    "normalized-exact",
    "differs",
    "doc-absent",
    "doc-absent (bodyless declaration)",
    "block-not-located",
)

#: Observations that require a reviewed equivalence record before any
#: parity claim is possible. Material wording drift is never auto-upgraded.
REVIEW_REQUIRED_OBSERVATIONS: frozenset[str] = frozenset(
    {"differs", "doc-absent", "doc-absent (bodyless declaration)", "block-not-located"}
)

#: Classification for a runtime traversal strategy that is implemented but
#: is not associated with any ontology relationship mapping. It must be
#: explicitly flagged for review; it must never be silently dropped.
UNASSOCIATED_STRATEGY_CLASSIFICATION = "unassociated-capability-pending-review"

#: Layer-B field names carried per entry (reviewed decisions).
REVIEWED_FIELDS: tuple[str, ...] = (
    "authority_current",
    "authority_target",
    "evidence_state",
    "adoption_status",
    "transition_gate",
    "conditional_target",
    "disposition",
    "confidence",
    "stage",
    "note",
    "unknowns",
    "required_evidence",
    "exact_fit_decision",
    "closure_evidence_ref",
    "semantic_text_equivalence",
)

CONFIDENCE_VALUES: tuple[str, ...] = ("high", "medium", "low")

#: Observed runtime-consumer associations for classes. Each association is a
#: Phase-1-established observation and is VERIFIED against repository evidence
#: on every generation (fail closed): every basis token must be present in its
#: file, or generation fails — a stale association can never pass silently.
#: Classes without an association are ``vocabulary-only``.
CLASS_RUNTIME_CONSUMPTION: dict[str, dict[str, Any]] = {
    "Need": {
        "support": "consumed (identity/lineage)",
        "basis": (("de4sdv/semantic/projection.py", '"Need"'),),
    },
    "Requirement": {
        "support": "consumed (identity/lineage)",
        "basis": (("de4sdv/semantic/impact.py", 'bind_class("Requirement")'),),
    },
    "MemberProduct": {
        "support": "consumed (identity/lineage)",
        "basis": (("de4sdv/semantic/impact.py", '"MemberProduct"'),),
    },
    "VerificationMethod": {
        "support": "consumed (model attributes)",
        "basis": (("de4sdv/semantic/method_evaluator.py", "VerificationMethod"),),
    },
    "EvidenceStatus": {
        "support": "consumed (model attributes)",
        "basis": (
            (
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
                "VVStatus",
            ),
        ),
    },
    "VerificationCase": {
        "support": "consumed (verifiedBy)",
        "basis": (("de4sdv/semantic/impact.py", "VerificationCase"),),
    },
    "MethodPhase": {
        "support": "consumed by method-conformance data",
        "basis": (
            (
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml",
                "MethodPhase",
            ),
        ),
    },
    "MethodContractObligation": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            (
                "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml",
                "MethodContractObligation",
            ),
        ),
    },
    "MethodEvaluationScope": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (("de4sdv/semantic/method_contract.py", "MethodEvaluationScope"),),
    },
    "EvaluationScopeMembership": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            (
                "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml",
                "EvaluationScopeMembership",
            ),
        ),
    },
    "EvaluationSourceKind": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            (
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml",
                "EvaluationSourceKind",
            ),
        ),
    },
    "TestedScopeDeclaration": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            (
                "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml",
                "TestedScopeDeclaration",
            ),
        ),
    },
    "RetainedExecutionRecordReference": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            ("docs/method-conformance/pilot-obligations.yaml", "execution-outcome"),
            (
                "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_conformance.sysml",
                "RetainedExecutionRecordReference",
            ),
        ),
    },
    "AcceptanceAttestationReference": {
        "support": "consumed by method-conformance (Lane C/D)",
        "basis": (
            (
                "textual-notation-of-model/packages/features/aebs/aebs_override_verification.sysml",
                "AcceptanceAttestationReference",
            ),
        ),
    },
}


class InventoryError(Exception):
    """Generation/validation failure for the semantic authority inventory."""


# ---------------------------------------------------------------------------
# Kernel inventory machinery reuse
# ---------------------------------------------------------------------------


def _load_kernel_sync_module():  # type: ignore[no-untyped-def]
    """Return the repository's kernel inventory machinery module.

    ``scripts/check_model_sync.py`` owns declaration extraction
    (``_sysml_definitions``), comment stripping, and the governed-directory
    contract. The inventory reuses that machinery instead of re-implementing
    declaration parsing; the module is loaded by file path when the
    ``scripts`` package is not importable from the current interpreter path.
    """
    try:
        from scripts import check_model_sync  # type: ignore
    except ImportError:
        import importlib.util

        root = Path(__file__).resolve().parents[2]
        path = root / "scripts" / "check_model_sync.py"
        spec = importlib.util.spec_from_file_location(
            "de4sdv_kernel_sync_machinery", path
        )
        if spec is None or spec.loader is None:  # pragma: no cover - defensive
            raise InventoryError(f"cannot load kernel machinery from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return check_model_sync


# ---------------------------------------------------------------------------
# Text normalization and doc-text observation (Layer A)
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Purely cosmetic normalization: case, punctuation, whitespace/wrapping.

    This is the only automatic comparison the inventory performs on
    documentation text. It is exact token normalization — never a similarity
    score, word overlap, or fuzzy match.
    """
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def declaration_block(file_text: str, declaration: str) -> tuple[str, bool]:
    """Best-effort body of one ``<kind> def <Name> { ... }`` declaration.

    Returns ``(block, bodyless)``. ``bodyless`` is True when the declaration
    ends with ``;`` (or has no body at all) — a property of the declaration
    form, not a text difference.
    """
    kind, _, name = declaration.partition(" def ")
    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )
    match = pattern.search(file_text)
    if not match:
        return "", False
    rest = file_text[match.end():]
    brace = rest.find("{")
    semi = rest.find(";")
    if brace == -1 or (semi != -1 and semi < brace):
        return "", True
    depth = 0
    for index, char in enumerate(rest[brace:], start=brace):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return rest[brace:index + 1], False
    return rest[brace:], False


def doc_text_observation(
    file_text: str, declaration: str, definition: str
) -> str:
    """Normalized observation of one declaration's model-resident doc text.

    The comparison is normalized containment of the full definition text
    (either direction) after purely cosmetic normalization — the definition
    must appear verbatim as a normalized token run inside the model doc, or
    the model doc inside the definition, or the texts differ. There is no
    similarity threshold anywhere: any material wording difference yields
    ``differs`` and requires a human-reviewed equivalence decision.
    """
    block, bodyless = declaration_block(file_text, declaration)
    if bodyless:
        return "doc-absent (bodyless declaration)"
    if not block:
        return "block-not-located"
    docs = re.findall(r"doc\s*/\*(.*?)\*/", block, flags=re.DOTALL)
    if not docs:
        return "doc-absent"
    blob = normalize_text(" ".join(docs))
    target = normalize_text(" ".join(str(definition).split()))
    if not target:
        return "doc-present"
    if target in blob or blob in target:
        return "normalized-exact"
    return "differs"


# ---------------------------------------------------------------------------
# Runtime traversal strategy registry (Layer A)
# ---------------------------------------------------------------------------

_STRATEGY_COMPARISON_ATTR = "strategy"


def implemented_traversal_strategies(source: str) -> list[str]:
    """Implemented traversal strategy tokens, derived from the dispatch source.

    The single traversal implementation dispatches on ``mapping.strategy``
    comparisons. This bounded AST scan collects every string literal compared
    against a ``.strategy`` attribute in the module; a new dispatch branch
    using a new literal therefore enters the inventory automatically and must
    be associated with an ontology mapping or explicitly flagged as an
    unassociated capability. The scan is deliberately narrow: a dispatch
    rewrite that stops using ``.strategy`` comparisons must be reviewed
    together with this function (checked against sibling modules by
    :func:`strategy_dispatch_sources`).
    """
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not (
            isinstance(node.left, ast.Attribute)
            and node.left.attr == _STRATEGY_COMPARISON_ATTR
        ):
            continue
        for operator, comparator in zip(node.ops, node.comparators):
            if isinstance(operator, ast.Eq) and isinstance(comparator, ast.Constant):
                if isinstance(comparator.value, str):
                    found.add(comparator.value)
            elif isinstance(operator, ast.In):
                for element in getattr(comparator, "elts", []) or []:
                    if isinstance(element, ast.Constant) and isinstance(
                        element.value, str
                    ):
                        found.add(element.value)
    return sorted(found)


def strategy_dispatch_sources(root: Path) -> list[str]:
    """Repository files that compare on a ``.strategy`` attribute.

    Fail-closed guard for the strategy registry: the traversal dispatch is
    owned by exactly one module. If another module starts comparing
    ``.strategy`` values, the registry scan must be reviewed before the new
    dispatch surface can pass the gate.
    """
    sources: list[str] = []
    de4sdv_dir = root / "de4sdv"
    for path in sorted(de4sdv_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"\.strategy\s*(==|in\b)", text):
            sources.append(str(path.relative_to(root).as_posix()))
    return sources


# ---------------------------------------------------------------------------
# Layer A extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KernelAccounting:
    """Kernel-declaration accounting for the governed method-kernel directory."""

    governed_directory: str
    governed_declarations: int
    mapped_in_directory: int
    mapped_out_of_directory: int
    exclusions: int
    cross_slice_mappings: tuple[dict[str, str], ...]


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def file_digest(root: Path, relative: str) -> str:
    return _file_digest(root / relative)


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _declaration_pairs(contract: KernelContract) -> list[tuple[str, str, str]]:
    """(class identity, file, declaration) for file-mapped ontology classes."""
    pairs: list[tuple[str, str, str]] = []
    for name, spec in contract.classes.items():
        kernel = spec.get("kernel") or {}
        if "file" in kernel and "declaration" in kernel:
            pairs.append((name, str(kernel["file"]), str(kernel["declaration"])))
    return pairs


def kernel_accounting(
    root: Path, contract: KernelContract, declaration_scanner=None
) -> KernelAccounting:  # type: ignore[no-untyped-def]
    """Compute the bidirectional kernel accounting and verify it is complete.

    The accepted equation: governed declarations = mapped declarations in the
    governed directory + justified kernel-internal exclusions. File-mapped
    classes outside the governed directory (cross-slice mappings) are
    accounted separately. Every mapped declaration must exist in its file;
    every exclusion must exist and must not be mapped; the equation must hold
    exactly. Any violation raises — the inventory cannot be generated from an
    inconsistent contract.
    """
    if declaration_scanner is None:
        declaration_scanner = _load_kernel_sync_module()._sysml_definitions
    module = _load_kernel_sync_module()
    governed = contract.governed_directory
    governed_path = root / governed
    if not governed_path.is_dir():
        raise InventoryError(f"governed kernel directory not found: {governed}")

    actual: set[tuple[str, str]] = set()
    for sysml_path in sorted(governed_path.rglob("*.sysml")):
        relative = str(sysml_path.relative_to(root).as_posix())
        actual.update(
            (relative, declaration)
            for declaration in declaration_scanner(
                sysml_path.read_text(encoding="utf-8")
            )
        )

    mapped_in: set[tuple[str, str]] = set()
    cross_slice: list[dict[str, str]] = []
    for name, file, declaration in _declaration_pairs(contract):
        file_path = root / file
        if not file_path.exists():
            raise InventoryError(f"kernel file not found for {name}: {file}")
        text = file_path.read_text(encoding="utf-8")
        if not module._declaration_exists(text, declaration):
            raise InventoryError(
                f"mapped declaration missing for {name}: {declaration!r} in {file}"
            )
        if module._is_within(file, governed):
            mapped_in.add((file, declaration))
        else:
            cross_slice.append(
                {"identity": name, "file": file, "declaration": declaration}
            )

    exclusions: set[tuple[str, str]] = set()
    for file, declarations in contract.exclusions.items():
        if not module._is_within(file, governed):
            raise InventoryError(
                f"exclusion file outside governed directory: {file!r}"
            )
        for declaration, reason in declarations.items():
            if not str(reason).strip():
                raise InventoryError(
                    f"exclusion without reason: {file}:{declaration}"
                )
            exclusions.add((file, declaration.strip()))

    unclassified = sorted(actual - mapped_in - exclusions)
    if unclassified:
        raise InventoryError(
            "governed declarations are unclassified (map from an ontology "
            f"class or add a justified exclusion): {unclassified}"
        )
    stale_exclusions = sorted(exclusions - actual)
    if stale_exclusions:
        raise InventoryError(f"stale kernel exclusions: {stale_exclusions}")
    both = sorted(mapped_in & exclusions)
    if both:
        raise InventoryError(
            f"declarations both mapped and excluded: {both}"
        )

    return KernelAccounting(
        governed_directory=governed,
        governed_declarations=len(actual),
        mapped_in_directory=len(mapped_in),
        mapped_out_of_directory=len(cross_slice),
        exclusions=len(exclusions),
        cross_slice_mappings=tuple(
            sorted(cross_slice, key=lambda item: item["identity"])
        ),
    )


def _verify_class_consumption(root: Path, identity: str) -> str:
    """Verified runtime-consumer association for one class, or ``vocabulary-only``.

    Each association in :data:`CLASS_RUNTIME_CONSUMPTION` carries concrete
    repository bases; every basis file must exist and contain its required
    token. A stale or unverifiable association is a generation error.
    """
    association = CLASS_RUNTIME_CONSUMPTION.get(identity)
    if association is None:
        return "vocabulary-only"
    for basis_file, required in association["basis"]:
        path = root / basis_file
        if not path.is_file():
            raise InventoryError(
                f"runtime-consumer basis file missing for {identity}: {basis_file}"
            )
        if required not in path.read_text(encoding="utf-8"):
            raise InventoryError(
                f"runtime-consumer basis token missing for {identity}: "
                f"{required!r} not in {basis_file} (stale association?)"
            )
    return str(association["support"])


def observed_entries(
    root: Path, contract: KernelContract
) -> dict[str, dict[str, Any]]:
    """Layer A facts for every ontology class and relationship.

    Returns ``{identity: {"kind": ..., "observed": {...}}}`` in ontology
    declaration order (classes, then relationships).
    """
    entries: dict[str, dict[str, Any]] = {}
    for name, spec in contract.classes.items():
        kernel = spec.get("kernel") or {}
        observed: dict[str, Any] = {"yaml_path": f"classes:{name}"}
        if "file" in kernel:
            file = str(kernel["file"])
            declaration = str(kernel["declaration"])
            observed.update(
                {
                    "grounding_kind": "file-declaration",
                    "file": file,
                    "declaration": declaration,
                }
            )
            file_path = root / file
            if not file_path.is_file():
                raise InventoryError(
                    f"kernel file not found for class {name}: {file}"
                )
            observed["doc_text_observation"] = doc_text_observation(
                file_path.read_text(encoding="utf-8"),
                declaration,
                str(spec.get("definition", "")),
            )
        elif "native" in kernel:
            observed.update(
                {
                    "grounding_kind": "native",
                    "ref": " ".join(str(kernel["native"]).split()),
                }
            )
        elif "external" in kernel:
            observed.update(
                {
                    "grounding_kind": "external",
                    "ref": " ".join(str(kernel["external"]).split()),
                }
            )
        else:
            raise InventoryError(f"class without kernel mapping: {name}")
        observed["runtime_support"] = _verify_class_consumption(root, name)
        entries[name] = {"kind": "class", "observed": observed}

    for name, spec in contract.relationships.items():
        domain = spec.get("domain")
        range_ = spec.get("range")
        observed = {
            "yaml_path": f"relationships:{name}",
            "domain": domain,
            "range": range_,
        }
        mapping = spec.get("sysml_mapping")
        if isinstance(mapping, dict):
            strategy = mapping.get("strategy")
            observed.update(
                {
                    "grounding_kind": "sysml_mapping",
                    "strategy": strategy,
                    "semantic_strength": mapping.get("semantic_strength"),
                    "query_direction": mapping.get("query_direction"),
                }
            )
            if strategy == "external":
                observed["runtime_support"] = "external (no traversal)"
            else:
                observed["runtime_support"] = f"implemented ({strategy})"
        else:
            observed.update(
                {
                    "grounding_kind": "yaml-vocabulary",
                    "runtime_support": "vocabulary-only",
                }
            )
        entries[name] = {"kind": "relationship", "observed": observed}

    return entries


def strategy_accounting(
    root: Path,
    contract: KernelContract,
    decisions: dict[str, Any],
) -> list[dict[str, Any]]:
    """Runtime strategy rows: implemented strategies with their association.

    Every implemented runtime strategy must be either associated with an
    ontology relationship mapping or explicitly classified as an unassociated
    capability pending review in the decisions dataset. Every ``sysml_mapping``
    strategy must be implemented. Both directions fail closed.
    """
    implemented = implemented_traversal_strategies(
        _read(root, TRAVERSAL_SOURCE_PATH)
    )
    by_strategy: dict[str, list[str]] = {strategy: [] for strategy in implemented}
    for name, spec in contract.relationships.items():
        mapping = spec.get("sysml_mapping")
        if not isinstance(mapping, dict):
            continue
        strategy = str(mapping.get("strategy"))
        if strategy not in by_strategy:
            raise InventoryError(
                f"relationship {name} declares strategy {strategy!r} that is "
                f"not implemented in {TRAVERSAL_SOURCE_PATH}"
            )
        by_strategy[strategy].append(name)

    declared = decisions.get("runtime_strategies")
    if not isinstance(declared, dict):
        raise InventoryError(
            "decisions dataset has no runtime_strategies section"
        )

    rows: list[dict[str, Any]] = []
    for strategy in implemented:
        entries = sorted(by_strategy[strategy])
        if entries:
            row = {
                "strategy": strategy,
                "association": "ontology-mapping",
                "entries": entries,
            }
            if strategy in declared:
                raise InventoryError(
                    f"strategy {strategy!r} is associated with ontology "
                    "mappings but the decisions dataset still declares it as "
                    "unassociated (stale row)"
                )
        else:
            record = declared.get(strategy)
            if not isinstance(record, dict):
                raise InventoryError(
                    f"runtime strategy {strategy!r} is implemented but not "
                    "associated with any ontology mapping and has no reviewed "
                    "disposition row"
                )
            classification = record.get("classification")
            if classification != UNASSOCIATED_STRATEGY_CLASSIFICATION:
                raise InventoryError(
                    f"runtime strategy {strategy!r} has unsupported "
                    f"classification {classification!r}; expected "
                    f"{UNASSOCIATED_STRATEGY_CLASSIFICATION!r}"
                )
            row = {
                "strategy": strategy,
                "association": "unassociated-capability",
                "classification": classification,
                "note": " ".join(str(record.get("note", "")).split()),
                "entries": [],
            }
        rows.append(row)

    stale = sorted(set(declared) - set(implemented))
    if stale:
        raise InventoryError(
            "decisions dataset declares unassociated strategies that are not "
            f"implemented: {stale}"
        )
    return rows


# ---------------------------------------------------------------------------
# Layer B loading
# ---------------------------------------------------------------------------


class _DuplicateKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys (identity safety)."""


def _construct_unique_mapping(loader, node, deep=False):  # type: ignore[no-untyped-def]
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise InventoryError(
                f"duplicate key {key!r} in reviewed decisions YAML; identities "
                "must be unique"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def load_reviewed_decisions(path: Path) -> dict[str, Any]:
    """Load and shape-check the committed reviewed-decisions dataset."""
    if not path.is_file():
        raise InventoryError(f"reviewed decisions dataset not found: {path}")
    try:
        value = yaml.load(
            path.read_text(encoding="utf-8"), Loader=_DuplicateKeyLoader
        )
    except InventoryError:
        raise
    except yaml.YAMLError as exc:
        raise InventoryError(f"reviewed decisions dataset is not valid YAML: {exc}")
    if not isinstance(value, dict):
        raise InventoryError("reviewed decisions document must be a YAML mapping")
    if value.get("schema") != DECISIONS_SCHEMA_ID:
        raise InventoryError(
            f"reviewed decisions schema must be {DECISIONS_SCHEMA_ID!r}, "
            f"got {value.get('schema')!r}"
        )
    dimensions = value.get("dimensions")
    if not isinstance(dimensions, dict):
        raise InventoryError("reviewed decisions document has no dimensions block")
    expected = {
        "authority_source": list(AUTHORITY_SOURCES),
        "evidence_state": list(EVIDENCE_STATES),
        "adoption_status": list(ADOPTION_STATUSES),
    }
    for key, vocabulary in expected.items():
        declared = dimensions.get(key)
        if declared != vocabulary:
            raise InventoryError(
                f"dimensions.{key} must declare the accepted closed vocabulary; "
                f"got {declared!r}"
            )
    entries = value.get("entries")
    if not isinstance(entries, dict):
        raise InventoryError("reviewed decisions document has no entries mapping")
    return value


def load_closure_records(path: Path) -> list[dict[str, Any]]:
    """Load and shape-check the structured closure-evidence records."""
    if not path.is_file():
        raise InventoryError(f"closure evidence file not found: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != CLOSURE_SCHEMA_ID:
        raise InventoryError(
            f"closure evidence schema must be {CLOSURE_SCHEMA_ID!r}"
        )
    records = value.get("records")
    if not isinstance(records, list):
        raise InventoryError("closure evidence records must be a list")
    return records


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_ARCHIVE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _entry_problems(
    identity: str,
    kind: str,
    observed: dict[str, Any],
    reviewed: dict[str, Any],
    closure_records: dict[str, dict[str, Any]],
) -> list[str]:
    problems: list[str] = []

    missing = [field for field in REVIEWED_FIELDS if field not in reviewed]
    if missing:
        problems.append(f"{identity}: reviewed decision missing fields {missing}")

    authority_current = reviewed.get("authority_current")
    authority_target = reviewed.get("authority_target")
    evidence_state = reviewed.get("evidence_state")
    adoption = reviewed.get("adoption_status")

    if authority_current not in AUTHORITY_SOURCES:
        problems.append(
            f"{identity}: authority_current {authority_current!r} outside the "
            "accepted authority vocabulary"
        )
    if authority_target not in AUTHORITY_SOURCES:
        problems.append(
            f"{identity}: authority_target {authority_target!r} outside the "
            "accepted authority vocabulary"
        )
    if evidence_state not in EVIDENCE_STATES:
        problems.append(
            f"{identity}: evidence_state {evidence_state!r} outside the "
            "accepted evidence-state vocabulary"
        )
    if adoption not in ADOPTION_STATUSES:
        problems.append(
            f"{identity}: adoption_status {adoption!r} outside the accepted "
            "adoption vocabulary"
        )
    disposition = reviewed.get("disposition")
    if disposition not in DISPOSITIONS:
        problems.append(
            f"{identity}: disposition {disposition!r} outside the accepted "
            "disposition vocabulary"
        )
    if reviewed.get("confidence") not in CONFIDENCE_VALUES:
        problems.append(
            f"{identity}: confidence {reviewed.get('confidence')!r} outside "
            f"{CONFIDENCE_VALUES}"
        )
    if not str(reviewed.get("stage", "")).strip():
        problems.append(f"{identity}: stage must be a non-empty string")

    # Conditional targets: a conditional target is never current authority and
    # always carries its transition gate.
    conditional = reviewed.get("conditional_target")
    gate = reviewed.get("transition_gate")
    if not isinstance(conditional, bool):
        problems.append(f"{identity}: conditional_target must be a boolean")
    elif conditional:
        if not str(gate or "").strip():
            problems.append(
                f"{identity}: conditional target without a transition gate"
            )
        if authority_target == authority_current:
            problems.append(
                f"{identity}: conditional target equals the current authority"
            )
    if gate is not None and not str(gate).strip():
        problems.append(f"{identity}: transition_gate must be null or non-empty")

    # Adoption gates.
    if adoption == "pinned-not-adopted":
        if not conditional:
            problems.append(
                f"{identity}: pinned-not-adopted requires a conditional target"
            )
        if authority_target != "accepted-library-grounded":
            problems.append(
                f"{identity}: pinned-not-adopted target must remain an "
                f"accepted-library-grounded candidate target, got "
                f"{authority_target!r}"
            )
    if adoption == "accepted" and authority_target != "accepted-library-grounded":
        problems.append(
            f"{identity}: adoption_status accepted requires an "
            "accepted-library-grounded authority target"
        )

    # Closure evidence: privileged-closure-proven requires a structured
    # revision-bound closure record. A bare boolean is never sufficient.
    ref = reviewed.get("closure_evidence_ref")
    if evidence_state == "privileged-closure-proven":
        if not ref:
            problems.append(
                f"{identity}: privileged-closure-proven without a closure "
                "evidence record"
            )
        elif ref not in closure_records:
            problems.append(
                f"{identity}: closure_evidence_ref {ref!r} has no record"
            )
        elif identity not in closure_records[ref]["subject_identities"]:
            problems.append(
                f"{identity}: closure record {ref!r} does not bind this identity"
            )
    else:
        if ref:
            problems.append(
                f"{identity}: closure_evidence_ref present but evidence_state "
                f"is {evidence_state!r}"
            )
        if evidence_state in {"blocked", "unknown"} and observed.get(
            "runtime_support"
        ) == "supported (closure-verified)":
            problems.append(
                f"{identity}: blocked/unknown entry cannot carry a "
                "closure-verified support state"
            )
        if evidence_state not in {"proposed", "blocked", "unknown"} and not (
            reviewed.get("required_evidence")
        ):
            problems.append(
                f"{identity}: active evidence state requires non-empty "
                "required_evidence"
            )

    # Text parity: material wording difference or missing doc requires an
    # explicit reviewed equivalence record; exact observations never get an
    # automatic equivalence upgrade.
    observation = observed.get("doc_text_observation")
    equivalence = reviewed.get("semantic_text_equivalence")
    if observation in REVIEW_REQUIRED_OBSERVATIONS:
        if equivalence != "review-required":
            problems.append(
                f"{identity}: doc observation {observation!r} requires "
                "semantic_text_equivalence = 'review-required'"
            )
        if not reviewed.get("required_evidence"):
            problems.append(
                f"{identity}: review-required text parity needs non-empty "
                "required_evidence"
            )
    else:
        if equivalence not in (None,):
            problems.append(
                f"{identity}: semantic_text_equivalence must be null for doc "
                f"observation {observation!r} (no automatic upgrade)"
            )

    # NOTE (native-semantics rule): native representation primitive != native
    # semantic authority. This validator deliberately does NOT infer
    # authority_current = native-sysml from an ontology `kernel.native`
    # mapping; the reviewed classification is preserved as decided.
    return problems


def validate_inventory(
    observed: dict[str, dict[str, Any]],
    decisions: dict[str, Any],
    closure_records: list[dict[str, Any]],
    strategy_rows: list[dict[str, Any]],
) -> list[str]:
    """Full coverage/consistency validation; returns all problems found."""
    problems: list[str] = []

    by_id: dict[str, dict[str, Any]] = {}
    for record in closure_records:
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            problems.append("closure record without an id")
            continue
        if record_id in by_id:
            problems.append(f"duplicate closure record id {record_id!r}")
            continue
        by_id[record_id] = record

    # Coverage: exactly one reviewed row per ontology entry, no extras.
    reviewed_entries = decisions["entries"]
    if len(reviewed_entries) != len(observed):
        problems.append(
            f"coverage: {len(observed)} ontology entries but "
            f"{len(reviewed_entries)} reviewed decision rows"
        )
    for identity, entry in observed.items():
        row = reviewed_entries.get(identity)
        if row is None:
            problems.append(f"coverage: missing reviewed decision row for {identity}")
            continue
        if not isinstance(row, dict):
            problems.append(f"{identity}: reviewed decision row must be a mapping")
            continue
        problems.extend(
            _entry_problems(
                identity, entry["kind"], entry["observed"], row, by_id
            )
        )
    for identity in sorted(set(reviewed_entries) - set(observed)):
        problems.append(
            f"coverage: reviewed decision row {identity!r} has no ontology entry"
        )

    # Closure record completeness: every record must be structurally
    # revision-bound with a real artifact identity and proof result.
    for record_id, record in sorted(by_id.items()):
        for field in (
            "schema",
            "subject_identities",
            "git_sha",
            "sysml_project_id",
            "sysml_commit_id",
            "evidence_source",
            "artifact",
            "proof",
            "status",
        ):
            if field not in record:
                problems.append(f"closure record {record_id!r}: missing {field!r}")
        if record.get("schema") != CLOSURE_SCHEMA_ID:
            problems.append(
                f"closure record {record_id!r}: schema must be {CLOSURE_SCHEMA_ID!r}"
            )
        if not _FULL_SHA.match(str(record.get("git_sha", ""))):
            problems.append(
                f"closure record {record_id!r}: git_sha must be a full 40-hex "
                "revision"
            )
        for field in ("sysml_project_id", "sysml_commit_id"):
            if not str(record.get(field) or "").strip():
                problems.append(f"closure record {record_id!r}: {field} is required")
        source = record.get("evidence_source")
        if not isinstance(source, dict) or not str(source.get("workflow_run", "")).strip():
            problems.append(
                f"closure record {record_id!r}: evidence_source.workflow_run is required"
            )
        artifact = record.get("artifact")
        if not isinstance(artifact, dict):
            problems.append(f"closure record {record_id!r}: artifact must be a mapping")
        else:
            if not str(artifact.get("name") or "").strip():
                problems.append(f"closure record {record_id!r}: artifact name required")
            digest = artifact.get("archive_content_digest")
            if digest is not None and not _ARCHIVE_DIGEST.match(str(digest)):
                problems.append(
                    f"closure record {record_id!r}: archive_content_digest must be "
                    "a sha256:<64-hex> archive digest or null (never fabricated)"
                )
        proof = record.get("proof")
        if not isinstance(proof, dict):
            problems.append(f"closure record {record_id!r}: proof must be a mapping")
        elif proof.get("result") != "pass":
            problems.append(
                f"closure record {record_id!r}: proof.result must be 'pass' for a "
                "privileged-closure-proven state"
            )
        subject_ids = record.get("subject_identities")
        if not isinstance(subject_ids, list) or not subject_ids:
            problems.append(
                f"closure record {record_id!r}: subject_identities must be non-empty"
            )
        else:
            for subject in subject_ids:
                if subject not in observed:
                    problems.append(
                        f"closure record {record_id!r}: subject {subject!r} is not "
                        "an inventory entry"
                    )

    # Runtime strategy accounting must cover the full implemented set.
    implemented = sorted(row["strategy"] for row in strategy_rows)
    reviewed_rows = decisions.get("runtime_strategies") or {}
    unassociated = sorted(
        row["strategy"] for row in strategy_rows if row["association"] != "ontology-mapping"
    )
    if sorted(reviewed_rows) != unassociated:
        problems.append(
            "runtime strategy coverage mismatch: implemented="
            f"{implemented}, unassociated rows={unassociated}, "
            f"declared={sorted(reviewed_rows)}"
        )

    # Duplicate canonical identity guard (classes versus relationships).
    all_identities = list(observed)
    if len(all_identities) != len(set(all_identities)):
        problems.append("duplicate canonical identity in the ontology contract")

    return problems


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _counts(
    contract: KernelContract,
    entries: dict[str, dict[str, Any]],
    kernel: KernelAccounting,
    strategy_rows: list[dict[str, Any]],
    governance_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    classes = {name: spec for name, spec in contract.classes.items()}
    mapping_kinds = {"file": 0, "native": 0, "external": 0}
    for spec in classes.values():
        kernel_spec = spec.get("kernel") or {}
        for kind in mapping_kinds:
            if kind in kernel_spec:
                mapping_kinds[kind] += 1
    relationships = contract.relationships
    return {
        "classes": len(classes),
        "relationships": len(relationships),
        "total_entries": len(entries),
        "class_mappings": mapping_kinds,
        "relationship_mappings": sum(
            1 for spec in relationships.values() if "sysml_mapping" in spec
        ),
        "relationship_vocabulary_only": sum(
            1 for spec in relationships.values() if "sysml_mapping" not in spec
        ),
        "kernel_declarations_governed_dir": kernel.governed_declarations,
        "kernel_mapped_in_dir": kernel.mapped_in_directory,
        "kernel_mapped_out_of_dir": kernel.mapped_out_of_directory,
        "kernel_exclusions": kernel.exclusions,
        "governance_rules": len(governance_rules),
        "runtime_strategies_implemented": len(strategy_rows),
        "runtime_strategies_unassociated": sum(
            1 for row in strategy_rows if row["association"] != "ontology-mapping"
        ),
    }


def _governance_rules(root: Path, contract: KernelContract) -> list[dict[str, Any]]:
    """Ontology ``validation_rules`` as observed governance facts."""
    value = yaml.safe_load((root / ONTOLOGY_PATH).read_text(encoding="utf-8"))
    rules = value.get("validation_rules")
    if not isinstance(rules, list):
        return []
    observed: list[dict[str, Any]] = []
    for rule in rules:
        observed.append(
            {
                "identity": str(rule.get("id", "")),
                "kind": "validation-rule",
                "statement": " ".join(str(rule.get("statement", "")).split()),
                "enforced_by": " ".join(
                    str(rule.get("enforced_by", "")).split()
                ),
            }
        )
    return sorted(observed, key=lambda item: item["identity"])


def build_inventory(
    root: Path,
    *,
    revision: str,
    base_sha: str,
    contract: KernelContract | None = None,
) -> dict[str, Any]:
    """Build the canonical inventory (Layer A + Layer B), fully validated.

    Raises :class:`InventoryError` on any coverage or consistency failure.
    """
    if contract is None:
        contract = KernelContract.load(root / ONTOLOGY_PATH)
    decisions = load_reviewed_decisions(root / DECISIONS_PATH)
    closure_records = load_closure_records(root / CLOSURE_PATH)

    observed = observed_entries(root, contract)
    kernel = kernel_accounting(root, contract)
    strategy_rows = strategy_accounting(root, contract, decisions)

    problems = validate_inventory(
        observed,
        decisions,
        closure_records,
        strategy_rows,
    )
    if problems:
        raise InventoryError(
            "inventory validation failed:\n  - " + "\n  - ".join(problems)
        )

    # Join A + B with per-field provenance preserved.
    entries: list[dict[str, Any]] = []
    for identity, entry in observed.items():
        reviewed = {
            field: decisions["entries"][identity][field]
            for field in REVIEWED_FIELDS
        }
        # Closure-bound runtime support: the only promotion path from
        # "implemented" to a closure-verified support state is a complete
        # closure record binding this identity (never a bare boolean).
        if reviewed.get("closure_evidence_ref"):
            if entry["kind"] == "relationship" and str(
                entry["observed"].get("runtime_support", "")
            ).startswith("implemented ("):
                entry["observed"]["runtime_support"] = "supported (closure-verified)"
        entries.append(
            {"identity": identity, "kind": entry["kind"], "observed": entry["observed"], "reviewed": reviewed}
        )

    closure_by_id = {record["id"]: record for record in closure_records}
    for entry in entries:
        ref = entry["reviewed"].get("closure_evidence_ref")
        if ref and ref not in closure_by_id:
            raise InventoryError(
                f"{entry['identity']}: closure record {ref!r} not found"
            )

    counts = _counts(
        contract, {e["identity"]: e for e in entries}, kernel, strategy_rows,
        _governance_rules(root, contract),
    )

    def _tally(field: str) -> dict[str, int]:
        tally: dict[str, int] = {}
        for entry in entries:
            value = entry["reviewed"].get(field)
            if value is None:
                continue
            tally[value] = tally.get(value, 0) + 1
        return dict(sorted(tally.items()))

    conditional_tally: dict[str, int] = {}
    for entry in entries:
        if entry["reviewed"].get("conditional_target"):
            value = entry["reviewed"]["authority_target"]
            conditional_tally[value] = conditional_tally.get(value, 0) + 1

    return {
        "schema": SCHEMA_ID,
        "revision": 1,
        "status": "canonical generated O1 migration inventory",
        "warning": (
            "Generated migration/governance artifact. Layer B fields are "
            "reviewed decisions and are NEVER runtime semantic authority; the "
            "runtime does not read this artifact. Generated by "
            "scripts/generate_semantic_authority_inventory.py."
        ),
        "binding": {
            "git_revision": revision,
            "base_sha": base_sha,
            "git_revision_source": (
                "explicit generator input; defaults to HEAD at generation and "
                "is re-supplied verbatim by the committed-artifact check"
            ),
            "ontology_contract": {
                "path": ONTOLOGY_PATH,
                "digest": file_digest(root, ONTOLOGY_PATH),
            },
            "reviewed_decisions": {
                "path": DECISIONS_PATH,
                "digest": file_digest(root, DECISIONS_PATH),
            },
            "closure_evidence": {
                "path": CLOSURE_PATH,
                "digest": file_digest(root, CLOSURE_PATH),
            },
            "runtime_strategy_source": {
                "path": TRAVERSAL_SOURCE_PATH,
                "digest": file_digest(root, TRAVERSAL_SOURCE_PATH),
            },
            "governed_kernel_directory": contract.governed_directory,
        },
        "dimensions": {
            "authority_source": list(AUTHORITY_SOURCES),
            "evidence_state": list(EVIDENCE_STATES),
            "adoption_status": list(ADOPTION_STATUSES),
            "note": (
                "Authority and evidence are SEPARATE dimensions. No entry is "
                "'proven' by its target; privileged-closure-proven requires a "
                "structured closure-evidence record. Conditional targets are "
                "not counted as current authority."
            ),
        },
        "layers": {
            "observed": (
                "facts mechanically derived from repository evidence (ontology "
                "structure, kernel mappings and declarations, the runtime "
                "traversal strategy dispatch, model-resident documentation, "
                "verified consumer associations)"
            ),
            "reviewed": (
                "committed governance/migration decisions from "
                f"{DECISIONS_PATH} (authority classification, targets, "
                "evidence state, adoption, gates, dispositions, stages, "
                "unknowns, required evidence) — reviewable metadata, never "
                "runtime semantic authority"
            ),
            "field_rule": (
                "every entry field is attributable to exactly one layer; this "
                "generator joins observed+reviewed, validates consistency, and "
                "preserves the provenance split"
            ),
        },
        "counts": counts,
        "authority_current_counts": _tally("authority_current"),
        "authority_target_counts": _tally("authority_target"),
        "authority_target_conditional_counts": dict(sorted(conditional_tally.items())),
        "evidence_state_counts": _tally("evidence_state"),
        "adoption_status_counts": _tally("adoption_status"),
        "kernel_accounting": {
            "governed_directory": kernel.governed_directory,
            "governed_declarations": kernel.governed_declarations,
            "mapped_in_directory": kernel.mapped_in_directory,
            "mapped_out_of_directory": kernel.mapped_out_of_directory,
            "exclusions": kernel.exclusions,
            "equation": (
                "governed declarations = mapped in directory + justified "
                "exclusions; cross-slice mappings accounted separately"
            ),
            "cross_slice_mappings": list(kernel.cross_slice_mappings),
        },
        "runtime_strategy_registry": {
            "source": TRAVERSAL_SOURCE_PATH,
            "strategies": strategy_rows,
        },
        "governance_rules": _governance_rules(root, contract),
        "entries": entries,
        "closure_evidence": sorted(closure_records, key=lambda item: item["id"]),
        "doc_observation_note": (
            "Observation values: normalized-exact (exact comparison after "
            "purely cosmetic normalization: case/punctuation/whitespace/line "
            "wrapping) | differs (material wording drift -> "
            "semantic_text_equivalence=review-required; fuzzy similarity is "
            "NOT parity) | doc-absent | doc-absent (bodyless declaration) | "
            "block-not-located."
        ),
        "supersession": {
            "supersedes": [
                "docs/method-conformance/r0-handoff/semantic-authority-inventory.csv",
                "docs/method-conformance/o1/semantic-authority-inventory.draft.json",
            ],
            "note": (
                "This generated inventory is the current migration inventory "
                "for the inspected ontology. The R0 CSV (84 rows at its own "
                "baseline) and the Phase-1 review draft remain historical "
                "records; see the supersession pointers on those records. No "
                "second inventory is authoritative."
            ),
        },
        "evidence_sufficiency": (
            "All facts are established from repository evidence at the "
            "recorded revision (ontology contract, kernel, runtime dispatch, "
            "retained closure records). No privileged ingestion is required "
            "or claimed."
        ),
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def canonical_json(inventory: dict[str, Any]) -> str:
    """Byte-deterministic canonical JSON serialization."""
    return json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"


def _cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "/")


def render_markdown(inventory: dict[str, Any]) -> str:
    """Human-readable review table derived from the canonical inventory data."""
    lines: list[str] = []
    lines.append("# O1 Semantic Authority Inventory — generated review table")
    lines.append("")
    lines.append(
        "Generated from the canonical inventory data by "
        "`scripts/generate_semantic_authority_inventory.py`; do not edit by "
        "hand. The canonical machine-readable artifact is "
        "`semantic-authority-inventory.json`."
    )
    lines.append("")
    binding = inventory["binding"]
    lines.append("## Binding")
    lines.append("")
    lines.append(f"- Git revision: `{binding['git_revision']}`")
    lines.append(f"- Base: `{binding['base_sha']}`")
    for key in (
        "ontology_contract",
        "reviewed_decisions",
        "closure_evidence",
        "runtime_strategy_source",
    ):
        record = binding[key]
        lines.append(f"- {key}: `{record['path']}` ({record['digest']})")
    lines.append("")
    counts = inventory["counts"]
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    for key in (
        "classes",
        "relationships",
        "total_entries",
        "relationship_mappings",
        "relationship_vocabulary_only",
        "kernel_declarations_governed_dir",
        "kernel_mapped_in_dir",
        "kernel_mapped_out_of_dir",
        "kernel_exclusions",
        "governance_rules",
        "runtime_strategies_implemented",
        "runtime_strategies_unassociated",
    ):
        lines.append(f"| {key} | {counts[key]} |")
    for key in (
        "authority_current_counts",
        "authority_target_counts",
        "authority_target_conditional_counts",
        "evidence_state_counts",
        "adoption_status_counts",
    ):
        tally = inventory[key]
        rendered = ", ".join(f"{name}: {count}" for name, count in tally.items())
        lines.append(f"| {key} | {rendered} |")
    lines.append("")

    def _entry_row(entry: dict[str, Any], relationship: bool) -> str:
        reviewed = entry["reviewed"]
        observed = entry["observed"]
        authority = (
            f"{reviewed['authority_current']} -> {reviewed['authority_target']}"
            + (" [cond]" if reviewed["conditional_target"] else "")
        )
        if relationship:
            grounding = (
                f"{observed.get('domain')} -> {observed.get('range')}"
                + (
                    f" ({observed.get('strategy')})"
                    if observed.get("grounding_kind") == "sysml_mapping"
                    else ""
                )
            )
        else:
            kind = observed.get("grounding_kind")
            if kind == "file-declaration":
                grounding = f"{observed.get('file')}: {observed.get('declaration')}"
            elif kind == "native":
                grounding = f"native: {observed.get('ref')}"
            elif kind == "external":
                grounding = f"external: {observed.get('ref')}"
            else:  # pragma: no cover - defensive
                grounding = str(kind)
        return (
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    entry["identity"],
                    grounding,
                    observed.get("runtime_support"),
                    authority,
                    reviewed["evidence_state"],
                    reviewed["adoption_status"],
                    reviewed["disposition"],
                    reviewed["stage"],
                    reviewed.get("closure_evidence_ref") or "",
                )
            )
            + " |"
        )

    header = (
        "| id | grounding | runtime support | authority (current -> target) | "
        "evidence | adoption | disposition | stage | closure |"
    )
    divider = "|" + "|".join(["---"] * 9) + "|"
    classes = [e for e in inventory["entries"] if e["kind"] == "class"]
    relationships = [e for e in inventory["entries"] if e["kind"] == "relationship"]
    lines.append(f"## Classes ({len(classes)})")
    lines.append("")
    lines.append(header)
    lines.append(divider)
    for entry in classes:
        lines.append(_entry_row(entry, relationship=False))
    lines.append("")
    lines.append(f"## Relationships ({len(relationships)})")
    lines.append("")
    lines.append(header)
    lines.append(divider)
    for entry in relationships:
        lines.append(_entry_row(entry, relationship=True))
    lines.append("")
    lines.append("## Runtime strategy registry")
    lines.append("")
    lines.append("| strategy | association | entries | classification |")
    lines.append("|---|---|---|---|")
    for row in inventory["runtime_strategy_registry"]["strategies"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    row["strategy"],
                    row["association"],
                    ", ".join(row["entries"]),
                    row.get("classification", ""),
                )
            )
            + " |"
        )
    lines.append("")
    lines.append("## Closure evidence")
    lines.append("")
    lines.append(
        "| id | git sha | sysml project | sysml commit | workflow run | "
        "artifact | archive digest | proof |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for record in inventory["closure_evidence"]:
        artifact = record["artifact"]
        lines.append(
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    record["id"],
                    record["git_sha"],
                    record["sysml_project_id"],
                    record["sysml_commit_id"],
                    record["evidence_source"]["workflow_run"],
                    artifact["name"],
                    artifact.get("archive_content_digest"),
                    record["proof"]["result"],
                )
            )
            + " |"
        )
    lines.append("")
    return "\n".join(lines)
