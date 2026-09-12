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
  documentation, and machinery-witnessed evidence for reviewed consumer
  associations). Nothing in Layer A restates meaning from Python, and Layer A
  never asserts a semantic consumer association — only witnessed evidence at
  reviewed-declared locations.
- **Layer B — reviewed decisions**: committed governance/migration metadata
  (authority classification, targets, evidence state, adoption status,
  transition gates, dispositions, stages, unknowns, required evidence, and
  reviewed consumer associations). Layer B lives in the committed decisions
  dataset (``docs/method-conformance/o1/authority-review-decisions.yaml``),
  never in Python constants, and is never runtime semantic authority.

The generator joins A + B, validates coverage and consistency, and emits the
canonical inventory plus the human-readable review table. Validation fails
closed: an unaccounted ontology entry, kernel declaration, kernel exclusion,
runtime strategy, closure record, or missing decision row is a generation
error.

Revision binding: the artifact binds a ``source_revision`` — a Git commit
that contains every bound source input byte-for-byte — plus per-input content
digests (``binding.bound_inputs``). The gate validates commit existence,
ancestry, per-input content equality, and the digests; a stale revision
cannot pass by string reuse. Generation refuses to bind to a revision that
does not contain the current inputs (commit input changes first).

Determinism: identical inputs (ontology contract, decisions dataset, closure
records, traversal source, model sources, source revision) produce
byte-identical output. No timestamps, no environment-dependent values. Text
parity is exact equality after cosmetic normalization — containment or
similarity is never parity.

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
import subprocess
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

#: Bounded evidence kinds that Layer A can mechanically evaluate for a
#: reviewed consumer association. Layer A never invents associations; it only
#: reports witnessed/unwitnessed evidence at reviewed-declared locations.
CONSUMER_EVIDENCE_KINDS: tuple[str, ...] = (
    "exact-token",
    "sysml-code-token",
    "sysml-type-usage",
    "python-string-constant",
    "python-identifier",
)

#: Reviewed consumer-association block shape (Layer B, per class identity).
CONSUMER_ASSOCIATION_FIELDS: tuple[str, ...] = (
    "support",
    "consumer",
    "consumer_role",
    "evidence",
)

#: Join-added reviewed fields (populated from the decisions dataset; not part
#: of the per-entry decision rows themselves).
REVIEWED_JOIN_FIELDS: tuple[str, ...] = ("runtime_consumption",)

#: Program sources whose behavior produces this artifact. Every one is a
#: bound input: changing any of them requires rebinding the artifact to a
#: commit containing the change. Data inputs are computed separately (see
#: :func:`collect_bound_inputs`).
BOUND_INPUT_PROGRAM_PATHS: tuple[str, ...] = (
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/sysml_api/revisions.py",
    "scripts/generate_semantic_authority_inventory.py",
    "scripts/check_model_sync.py",
)


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


def _leading_owned_doc_bodies(block: str) -> list[str]:
    """Documentation bodies owned by the definition itself (spec-grounded).

    Ownership rule (OMG SysML v2 Part 1, §7.4.2): "The documenting element of
    documentation is always the owning element of the documentation" — a
    ``doc`` comment is owned by the element whose body it lexically sits in,
    not by the sibling member it happens to follow. The definition's own
    documentation is therefore the ``doc /* ... */`` statements at the head of
    its body; a doc that follows a member declaration (``attribute x;`` /
    ``<literal> { ... }``) belongs to the member's OWN body by the same rule
    and must not contaminate the definition-level text.

    The scan walks the body from the opening ``{``:

    * plain ``/* ... * /`` and ``// ...`` comments are presentation comments,
      not model elements — skipped, scanning continues;
    * ``doc /* ... */`` statements are collected as owned documentation;
    * the first any other token (a member declaration) ENDS the scan — from
      there on, any ``doc`` is inside or after member territory.

    This is a bounded textual-notation rule (depth-0 prefix scan, no fuzzy
    matching, no hardcoded definitions). It mirrors the spec's textual
    grammar, where a Documentation is an owned member of the enclosing
    namespace's body.
    """
    docs: list[str] = []
    index = 1  # skip the opening '{' of the declaration block
    length = len(block)
    while index < length:
        char = block[index]
        if char.isspace():
            index += 1
            continue
        if block.startswith("/*", index):
            end = block.find("*/", index + 2)
            if end == -1:
                break
            index = end + 2
            continue
        if block.startswith("//", index):
            end = block.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        match = re.compile(r"doc\s*/\*").match(block, index)
        if match:
            end = block.find("*/", match.end())
            if end == -1:
                break
            docs.append(block[match.end():end])
            index = end + 2
            continue
        break  # first non-doc token: member territory begins
    return docs


def doc_text_observation(
    file_text: str, declaration: str, definition: str
) -> str:
    """Exact-parity observation of one declaration's model-resident doc text.

    Definition-level documentation is distinguished from member
    documentation per :func:`_leading_owned_doc_bodies` (spec §7.4.2: a doc
    comment is owned by the element whose body it sits in). Literal and
    attribute docs are member docs and never contaminate the definition text.

    ``normalized-exact`` requires **equality** after the allowed cosmetic
    normalization (case, punctuation, whitespace/line wrapping). Containment
    or substring overlap in either direction is NOT parity: text that adds or
    omits semantic content yields ``differs`` and requires a human-reviewed
    equivalence decision. There is no similarity threshold, token overlap, or
    fuzzy comparison anywhere.
    """
    block, bodyless = declaration_block(file_text, declaration)
    if bodyless:
        return "doc-absent (bodyless declaration)"
    if not block:
        return "block-not-located"
    docs = _leading_owned_doc_bodies(block)
    if not docs:
        return "doc-absent"
    blob = normalize_text(" ".join(docs))
    target = normalize_text(" ".join(str(definition).split()))
    if not target:
        return "doc-present"
    if blob == target:
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
# Source-revision binding (R1)
# ---------------------------------------------------------------------------
#
# A generated artifact cannot bind to the commit that first introduces it.
# The binding therefore names a ``source_revision``: a Git commit that
# actually contains every bound source input byte-for-byte. The gate proves
# that containment against the repository — it does not trust the recorded
# string: it re-checks commit existence, ancestry, per-input content equality
# against the source revision, and the recorded content digests. A stale
# revision can never pass by string reuse.


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_source_revision(root: Path) -> str:
    """The full commit id of the checkout being generated from."""
    result = _git(root, "rev-parse", "HEAD")
    if result.returncode != 0 or not result.stdout.strip():
        raise InventoryError(
            "cannot resolve the source revision (git rev-parse HEAD failed); "
            "the inventory must be generated from a Git checkout"
        )
    return result.stdout.strip()


def collect_bound_inputs(
    root: Path, contract: KernelContract, decisions: dict[str, Any]
) -> dict[str, str]:
    """Every source consumed to produce the artifact: path -> sha256 digest.

    Program sources are declared in :data:`BOUND_INPUT_PROGRAM_PATHS`; data
    inputs (ontology contract, decisions dataset, closure evidence, strategy
    source, governed kernel/method model files, out-of-governed mapped files,
    and consumer-evidence files) are collected mechanically and sorted.
    """
    paths: set[str] = set(BOUND_INPUT_PROGRAM_PATHS)
    paths.update({ONTOLOGY_PATH, DECISIONS_PATH, CLOSURE_PATH, TRAVERSAL_SOURCE_PATH})
    governed = root / contract.governed_directory
    if not governed.is_dir():
        raise InventoryError(
            f"governed kernel directory not found: {contract.governed_directory}"
        )
    for sysml_path in governed.rglob("*.sysml"):
        paths.add(str(sysml_path.relative_to(root).as_posix()))
    for _, file, _ in _declaration_pairs(contract):
        paths.add(file)
    for association in (decisions.get("runtime_consumption") or {}).values():
        if not isinstance(association, dict):
            continue
        for item in association.get("evidence", []) or []:
            if isinstance(item, dict) and item.get("path"):
                paths.add(str(item["path"]))
    inputs: dict[str, str] = {}
    for path in sorted(paths):
        file = root / path
        if not file.is_file():
            raise InventoryError(f"bound input missing: {path}")
        inputs[path] = file_digest(root, path)
    return inputs


def _git_tree_blobs(
    root: Path, revision: str, paths: list[str]
) -> tuple[dict[str, str], str | None]:
    """Blob ids of ``paths`` at ``revision`` (missing paths are absent)."""
    result = _git(root, "ls-tree", "-r", "-z", revision, "--", *paths)
    if result.returncode != 0:
        return {}, result.stderr.strip() or f"git ls-tree failed for {revision}"
    blobs: dict[str, str] = {}
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            blobs[path] = parts[2]
    return blobs, None


def _binding_errors(
    root: Path, source_revision: str, bound_inputs: dict[str, str]
) -> list[str]:
    """Validate that ``source_revision`` genuinely contains the bound inputs.

    Checks, all fail-closed:

    1. format: ``source_revision`` is a full 40-hex commit id;
    2. existence: it resolves to a commit in this repository;
    3. ancestry: it is an ancestor of (or equal to) the checked-out revision;
    4. containment: every bound input exists at that revision and its blob is
       byte-identical to the working-tree file;
    5. content contract: the working-tree file digest matches the recorded
       ``sha256`` for that path.
    """
    errors: list[str] = []
    if not _FULL_SHA.match(source_revision):
        return [
            f"binding.source_revision must be a full 40-hex commit id "
            f"(got {source_revision!r})"
        ]
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    if _git(root, "cat-file", "-e", f"{source_revision}^{{commit}}").returncode != 0:
        return [
            f"binding.source_revision {source_revision} is not a commit in this "
            "repository"
        ]
    head_result = _git(root, "rev-parse", "HEAD")
    if head_result.returncode != 0 or not head_result.stdout.strip():
        return [
            "cannot resolve the checked-out revision (git rev-parse HEAD "
            "failed): the source-revision binding cannot be validated"
        ]
    head = head_result.stdout.strip()
    if _git(root, "merge-base", "--is-ancestor", source_revision, head).returncode != 0:
        errors.append(
            f"binding.source_revision {source_revision} is not an ancestor of "
            f"the checked-out revision {head}"
        )

    paths = sorted(bound_inputs)
    revision_blobs, tree_error = _git_tree_blobs(root, source_revision, paths)
    if tree_error:
        errors.append(f"cannot read the source-revision tree: {tree_error}")
        return errors
    missing_at_revision = [path for path in paths if path not in revision_blobs]
    for path in missing_at_revision:
        errors.append(
            f"bound input {path} does not exist at source_revision "
            f"{source_revision}"
        )
    present = [
        path for path in paths if path not in missing_at_revision and (root / path).is_file()
    ]
    missing_here = sorted(set(paths) - set(present) - set(missing_at_revision))
    for path in missing_here:
        errors.append(f"bound input {path} is missing from the checkout")

    current_blobs: dict[str, str] = {}
    if present:
        result = _git(root, "hash-object", "--", *present)
        if result.returncode != 0:
            errors.append(
                f"cannot hash working-tree bound inputs: "
                f"{result.stderr.strip() or 'git hash-object failed'}"
            )
        else:
            current_blobs = dict(zip(present, result.stdout.splitlines()))
    for path in present:
        if revision_blobs[path] != current_blobs.get(path):
            errors.append(
                f"bound input {path} differs from its content at source_revision "
                f"{source_revision}; the recorded revision is stale — regenerate "
                "and commit the artifact bound to a commit that contains the "
                "current inputs"
            )
        recorded = bound_inputs[path]
        digest = file_digest(root, path)
        if recorded != digest:
            errors.append(
                f"bound input {path} content digest {digest} does not match the "
                f"recorded digest {recorded!r}"
            )
    return errors


def validate_source_binding(root: Path, binding: dict[str, Any]) -> list[str]:
    """Validate one artifact's source-revision binding against the repository."""
    source_revision = binding.get("source_revision")
    if not isinstance(source_revision, str):
        return [
            "binding.source_revision is required (full commit id of a revision "
            "containing every bound input)"
        ]
    bound_inputs = binding.get("bound_inputs")
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    errors = _binding_errors(root, source_revision, bound_inputs)
    # Named input views, when present, must agree with the bound-input
    # content contract.
    for key in (
        "ontology_contract",
        "reviewed_decisions",
        "closure_evidence",
        "runtime_strategy_source",
    ):
        if key not in binding:
            continue
        record = binding.get(key)
        if not isinstance(record, dict):
            errors.append(f"binding.{key} must be a mapping")
            continue
        path = record.get("path")
        if not isinstance(path, str) or path not in bound_inputs:
            errors.append(f"binding.{key} path {path!r} is not a bound input")
            continue
        if record.get("digest") != bound_inputs[path]:
            errors.append(
                f"binding.{key} digest {record.get('digest')!r} does not match "
                f"the bound input digest {bound_inputs[path]!r}"
            )
    return errors


def verify_source_revision_contains_inputs(
    root: Path, source_revision: str, bound_inputs: dict[str, str]
) -> None:
    """Generation-time guard: refuse to bind to a revision that lacks the inputs."""
    errors = _binding_errors(root, source_revision, bound_inputs)
    if errors:
        raise InventoryError(
            "the source revision does not contain the bound inputs "
            "byte-for-byte:\n  - "
            + "\n  - ".join(errors)
            + "\nCommit the input changes first, then regenerate so the "
            "artifact can bind to that commit."
        )


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


def _non_docstring_string_constants(source: str) -> set[str]:
    """String literal values in code positions (docstrings excluded).

    Docstring bodies are string constants too; module/class/function docstrings
    are excluded so a prose mention cannot masquerade as a code reference.
    """
    tree = ast.parse(source)
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstring_ids.add(id(body[0].value))
    values: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            values.add(node.value)
    return values


def _python_identifiers(source: str) -> set[str]:
    """Identifier names in a Python source: Names, Attributes, defs, classes."""
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _sysml_type_usage(text: str, expected: str) -> bool:
    """``<feature> : <Type>`` usage in comment-stripped SysML text.

    The negative lookbehind keeps ``::``-qualified references (imports) from
    masquerading as typed usages.
    """
    code = _load_kernel_sync_module()._strip_comments(text)
    return (
        re.search(r"(?<!:):\s*" + re.escape(expected) + r"\b", code) is not None
    )


def _validate_consumer_association(identity: str, association: Any) -> list[str]:
    """Shape-check one reviewed consumer-association block (Layer B)."""
    problems: list[str] = []
    if not isinstance(association, dict):
        return [f"runtime_consumption[{identity}] must be a mapping"]
    for field in CONSUMER_ASSOCIATION_FIELDS:
        if field not in association:
            problems.append(
                f"runtime_consumption[{identity}] is missing {field!r}"
            )
    for field in ("support", "consumer", "consumer_role"):
        if not str(association.get(field) or "").strip():
            problems.append(
                f"runtime_consumption[{identity}].{field} must be a non-empty string"
            )
    evidence = association.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        problems.append(
            f"runtime_consumption[{identity}].evidence must be a non-empty list"
        )
        return problems
    for item in evidence:
        if not isinstance(item, dict):
            problems.append(
                f"runtime_consumption[{identity}] evidence entries must be mappings"
            )
            continue
        for field in ("path", "kind", "expect"):
            if not str(item.get(field) or "").strip():
                problems.append(
                    f"runtime_consumption[{identity}] evidence item missing {field!r}"
                )
        if item.get("kind") not in CONSUMER_EVIDENCE_KINDS:
            problems.append(
                f"runtime_consumption[{identity}] evidence kind "
                f"{item.get('kind')!r} outside {CONSUMER_EVIDENCE_KINDS}"
            )
    return problems


def evaluate_consumer_evidence(
    root: Path, identity: str, association: dict[str, Any]
) -> list[dict[str, Any]]:
    """Mechanically evaluate the evidence declared by a reviewed association.

    Returns the witnessed evidence results (Layer A observations). A missing
    file or an unwitnessed expectation raises — a reviewed association whose
    evidence has vanished is a stale association, never a silent pass.
    """
    results: list[dict[str, Any]] = []
    for item in association["evidence"]:
        path = root / str(item["path"])
        kind = str(item["kind"])
        expect = str(item["expect"])
        if not path.is_file():
            raise InventoryError(
                f"consumer evidence file missing for {identity}: {item['path']}"
            )
        text = path.read_text(encoding="utf-8")
        if kind == "exact-token":
            witnessed = expect in text
        elif kind == "sysml-code-token":
            witnessed = expect in _load_kernel_sync_module()._strip_comments(text)
        elif kind == "sysml-type-usage":
            witnessed = _sysml_type_usage(text, expect)
        elif kind == "python-string-constant":
            witnessed = expect in _non_docstring_string_constants(text)
        elif kind == "python-identifier":
            witnessed = expect in _python_identifiers(text)
        else:  # pragma: no cover - shape-checked earlier
            raise InventoryError(
                f"unsupported consumer evidence kind {kind!r} for {identity}"
            )
        if not witnessed:
            raise InventoryError(
                f"consumer evidence not witnessed for {identity}: {kind} "
                f"{expect!r} absent from {item['path']} (stale association?)"
            )
        results.append(
            {
                "path": str(item["path"]),
                "kind": kind,
                "expect": expect,
                "result": "witnessed",
            }
        )
    return results


def observed_entries(
    root: Path, contract: KernelContract, decisions: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Layer A facts for every ontology class and relationship.

    Consumer support is reviewed (Layer B); Layer A only reports the
    mechanically witnessed evidence for reviewed associations. Returns
    ``{identity: {"kind": ..., "observed": {...}}}`` in ontology declaration
    order (classes, then relationships).
    """
    consumption = decisions.get("runtime_consumption") or {}
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
        association = consumption.get(name)
        observed["consumer_evidence"] = (
            evaluate_consumer_evidence(root, name, association)
            if association is not None
            else []
        )
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
    consumption = value.get("runtime_consumption")
    if consumption is not None:
        if not isinstance(consumption, dict):
            raise InventoryError(
                "runtime_consumption must be a mapping of class identity -> "
                "association block"
            )
        problems: list[str] = []
        for identity, association in consumption.items():
            if not isinstance(identity, str) or not identity:
                problems.append("runtime_consumption identities must be non-empty strings")
                continue
            problems.extend(_validate_consumer_association(identity, association))
        if problems:
            raise InventoryError(
                "reviewed consumer associations failed shape validation:\n  - "
                + "\n  - ".join(problems)
            )
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
    if "runtime_consumption" not in reviewed:
        problems.append(
            f"{identity}: joined reviewed view must carry runtime_consumption "
            "(null when no reviewed association exists)"
        )
    consumption = reviewed.get("runtime_consumption")
    evidence_results = observed.get("consumer_evidence")
    if kind == "class":
        if "runtime_support" in observed:
            problems.append(
                f"{identity}: class observed facts must not assert runtime "
                "support; consumer support is reviewed provenance"
            )
        if consumption is not None:
            problems.extend(_validate_consumer_association(identity, consumption))
            if not evidence_results:
                problems.append(
                    f"{identity}: reviewed consumer association without "
                    "mechanically witnessed evidence"
                )
            else:
                for result in evidence_results:
                    if (
                        not isinstance(result, dict)
                        or result.get("result") != "witnessed"
                    ):
                        problems.append(
                            f"{identity}: consumer evidence results must be "
                            "mechanically witnessed"
                        )
                        break
        elif evidence_results:
            problems.append(
                f"{identity}: consumer evidence present without a reviewed "
                "consumer association"
            )
    else:
        if consumption is not None:
            problems.append(
                f"{identity}: runtime_consumption is class-only; relationship "
                "entries must not carry it"
            )
        if evidence_results:
            problems.append(
                f"{identity}: relationship observed facts must not carry "
                "consumer_evidence"
            )

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
        support = (
            observed.get("runtime_support")
            if kind == "relationship"
            else (consumption or {}).get("support")
        )
        if evidence_state in {"blocked", "unknown"} and support == (
            "supported (closure-verified)"
        ):
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
    consumption_rows = decisions.get("runtime_consumption") or {}
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
        joined = dict(row)
        joined["runtime_consumption"] = consumption_rows.get(identity)
        problems.extend(
            _entry_problems(
                identity, entry["kind"], entry["observed"], joined, by_id
            )
        )
    for identity in sorted(set(reviewed_entries) - set(observed)):
        problems.append(
            f"coverage: reviewed decision row {identity!r} has no ontology entry"
        )

    # Reviewed consumer associations: class-only, existing identities, shape
    # valid. Layer A evidence for them is evaluated during extraction.
    for identity, association in sorted(consumption_rows.items()):
        entry = observed.get(identity)
        if entry is None:
            problems.append(
                f"runtime_consumption[{identity}]: no ontology entry"
            )
        elif entry["kind"] != "class":
            problems.append(
                f"runtime_consumption[{identity}]: consumer associations are "
                "class-only"
            )
        else:
            problems.extend(_validate_consumer_association(identity, association))

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
    source_revision: str,
    contract: KernelContract | None = None,
) -> dict[str, Any]:
    """Build the canonical inventory (Layer A + Layer B), fully validated.

    ``source_revision`` must be a Git commit that contains every bound source
    input byte-for-byte; a revision that does not is refused before anything
    is generated. Raises :class:`InventoryError` on any coverage or
    consistency failure.
    """
    if contract is None:
        contract = KernelContract.load(root / ONTOLOGY_PATH)
    decisions = load_reviewed_decisions(root / DECISIONS_PATH)
    closure_records = load_closure_records(root / CLOSURE_PATH)

    bound_inputs = collect_bound_inputs(root, contract, decisions)
    verify_source_revision_contains_inputs(root, source_revision, bound_inputs)

    observed = observed_entries(root, contract, decisions)
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

    # Join A + B with per-field provenance preserved. The reviewed consumer
    # association is Layer B; its witnessed evidence stays Layer A.
    consumption_rows = decisions.get("runtime_consumption") or {}
    entries: list[dict[str, Any]] = []
    for identity, entry in observed.items():
        reviewed = {
            field: decisions["entries"][identity][field]
            for field in REVIEWED_FIELDS
        }
        reviewed["runtime_consumption"] = consumption_rows.get(identity)
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
            "source_revision": source_revision,
            "source_revision_note": (
                "Git commit that contains every bound source input "
                "byte-for-byte. The gate validates commit existence, ancestry "
                "of the checked-out revision, per-input content equality, and "
                "the recorded content digests — a stale revision cannot pass "
                "by string reuse."
            ),
            "artifact_commit": None,
            "artifact_commit_note": (
                "The commit that introduces this artifact cannot be known when "
                "the artifact is generated; left explicitly unclaimed."
            ),
            "ontology_contract": {
                "path": ONTOLOGY_PATH,
                "digest": bound_inputs[ONTOLOGY_PATH],
            },
            "reviewed_decisions": {
                "path": DECISIONS_PATH,
                "digest": bound_inputs[DECISIONS_PATH],
            },
            "closure_evidence": {
                "path": CLOSURE_PATH,
                "digest": bound_inputs[CLOSURE_PATH],
            },
            "runtime_strategy_source": {
                "path": TRAVERSAL_SOURCE_PATH,
                "digest": bound_inputs[TRAVERSAL_SOURCE_PATH],
            },
            "bound_inputs": bound_inputs,
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
                "and machinery-witnessed evidence for reviewed consumer "
                "associations — evidence only, never the association itself)"
            ),
            "reviewed": (
                "committed governance/migration decisions from "
                f"{DECISIONS_PATH} (authority classification, targets, "
                "evidence state, adoption, gates, dispositions, stages, "
                "unknowns, required evidence, reviewed consumer associations) "
                "— reviewable metadata, never runtime semantic authority"
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
            "Observation values: normalized-exact (equality after purely "
            "cosmetic normalization: case/punctuation/whitespace/line "
            "wrapping; containment or substring overlap is NOT parity) | "
            "differs (material wording drift -> "
            "semantic_text_equivalence=review-required; fuzzy similarity is "
            "NOT parity) | doc-absent | doc-absent (bodyless declaration) | "
            "block-not-located. Definition-level rule: a doc comment is owned "
            "by the element whose body it lexically sits in (SysML v2 "
            "specification, Comments and Documentation); the observed text is "
            "the declaration's leading owned documentation only — attribute, "
            "enum-literal, and other member documentation never contaminate "
            "the class-definition comparison."
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
            "All facts are established from repository evidence at the bound "
            "source revision (ontology contract, kernel, runtime dispatch, "
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
    lines.append(f"- Source revision: `{binding['source_revision']}`")
    lines.append(
        "- Artifact commit: unclaimed (cannot be known when the artifact is "
        "generated)"
    )
    for key in (
        "ontology_contract",
        "reviewed_decisions",
        "closure_evidence",
        "runtime_strategy_source",
    ):
        record = binding[key]
        lines.append(f"- {key}: `{record['path']}` ({record['digest']})")
    lines.append(
        f"- Bound inputs: {len(binding['bound_inputs'])} files "
        "(content-addressed; see the canonical JSON `binding.bound_inputs`)"
    )
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
            support = observed.get("runtime_support")
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
            consumption = reviewed.get("runtime_consumption")
            support = (
                consumption["support"] if consumption else "vocabulary-only"
            )
        return (
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    entry["identity"],
                    grounding,
                    support,
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
    lines.append("## Reviewed consumer associations (Layer B) with witnessed evidence (Layer A)")
    lines.append("")
    lines.append("| class | support | consumer | role | evidence (witnessed) |")
    lines.append("|---|---|---|---|---|")
    for entry in classes:
        consumption = entry["reviewed"].get("runtime_consumption")
        if not consumption:
            continue
        evidence = entry["observed"].get("consumer_evidence") or []
        rendered = ", ".join(
            f"{item['kind']} {item['expect']!r} in {item['path']}"
            for item in evidence
        )
        lines.append(
            "| "
            + " | ".join(
                _cell(item)
                for item in (
                    entry["identity"],
                    consumption["support"],
                    consumption["consumer"],
                    consumption["consumer_role"],
                    rendered,
                )
            )
            + " |"
        )
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
