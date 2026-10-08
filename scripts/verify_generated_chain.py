#!/usr/bin/env python3
"""Verify the whole generated-artifact chain (read-only, runtime-inert).

Single verifier over the generated-artifact chain that carries the repository's
recovery diagnostics and closure-reproducibility evidence: every artifact under
``docs/method-conformance/**`` that declares a ``binding`` block, plus the
committed O3 equivalence scope document.

What is validated (all fail-closed, all against the repository itself — a
recorded string never passes by reuse):

1. ``binding.source_revision`` exists as a commit and is an ancestor of the
   checked-out revision (``git merge-base --is-ancestor``).
2. Every ``binding.bound_inputs`` entry: the bytes at ``source_revision``
   equal the CURRENT working-tree bytes, and the recorded digest
   (``sha256:<64-hex>`` or bare 64-hex) matches the current content digest.
3. ``extends`` blocks (where present): the referenced artifact file exists,
   its digest recorded in ``extends.artifact_digest`` matches the current
   bytes, and ``extends.source_revision`` equals the referenced artifact's own
   ``binding.source_revision``.
4. A top-level ``source_revision`` claim on frozen records without a binding
   block (the ontology-review and validation report) must be a full commit id
   that exists and is an ancestor of the checked-out revision.
5. Frozen records (owner decisions Q7 and D10, 2026-10-07): every file under
   ``docs/method-conformance/{o1,o2,o3}/`` is a frozen record pinned by
   ``docs/method-conformance/frozen-records.json``
   (``de4sdv.frozen-records/v1``). Frozen records are never regenerated and
   never compared with the live tree's inputs. The frozen lane checks, all
   fail-closed:

   a. the manifest equals its deterministic rendering from the tree at its
      ``frozen_at_revision`` (an existing ancestor of the checked-out
      revision), so its record set, digests and record metadata are exactly
      the historical bytes;
   b. the files present under the three directories equal the record set
      (nothing added, nothing removed) and each file's current bytes match
      its recorded ``sha256`` (no edit, no regeneration);
   c. a record that carries a ``binding`` block is checked HISTORICALLY: its
      ``source_revision`` exists and is an ancestor of the checked-out
      revision, and every ``bound_inputs`` entry exists at that revision
      (``git show <rev>:<path>``) with the recorded digest. The current
      working-tree bytes of those inputs are deliberately not consulted, so a
      bound input may be edited or deleted at HEAD without breaking the
      record;
   d. ``extends`` blocks and the O3 equivalence scope basis may reference
      frozen records only, and must match their frozen digests; the O3
      ``comparison_base_revision`` exists and is an ancestor of the
      checked-out revision.

Report: ``{artifact, ok, errors[]}`` entries sorted by path; the CLI prints a
human summary and exits 0 iff every artifact is ok, else 1. ``--json`` emits
the machine-readable report.

Boundaries: read-only and runtime-inert. This module opens files and runs
``git`` read commands only; it never writes, never commits, and is never
imported by the semantic runtime. It reuses the shared authority-inventory
lane helpers (``file_digest`` and the binding validator behind
``verify_source_revision_contains_inputs``) instead of re-implementing the
revision-binding contract.

Usage:

    python scripts/verify_generated_chain.py            # human summary
    python scripts/verify_generated_chain.py --json     # machine report
    python scripts/verify_generated_chain.py --render-frozen-manifest <rev>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

METHOD_CONFORMANCE_DIR = "docs/method-conformance"
O3_SCOPE_PATH = "docs/method-conformance/o3/o3-equivalence-scope.json"

#: Owner decisions Q7 + D10 (2026-10-07): the whole O1/O2/O3 directories are
#: frozen records. They are never regenerated; their bindings are checked at
#: their own historical revisions (see the module docstring, item 5).
FROZEN_MANIFEST_PATH = "docs/method-conformance/frozen-records.json"
FROZEN_SCHEMA = "de4sdv.frozen-records/v1"
FROZEN_DIRECTORIES = (
    "docs/method-conformance/o1",
    "docs/method-conformance/o2",
    "docs/method-conformance/o3",
)
FROZEN_DECISION = {
    "owner_decisions": "Q7 and D10 (Orkun, 2026-10-07)",
    "statement": (
        "Freeze the historical O1, O2 and O3 records (the whole o1/, o2/ and "
        "o3/ directories); do not regenerate them."
    ),
    "record": "docs/method-conformance/o4/owner-decisions-2026-10.md",
}
#: Generators whose outputs are frozen. Their CLIs refuse to write or check
#: and point here; their library code is retired in O4 Wave C2.
RETIRED_GENERATORS = {
    "docs/method-conformance/o1/authority-inventory.md":
        "scripts/generate_semantic_authority_inventory.py",
    "docs/method-conformance/o1/semantic-authority-inventory.json":
        "scripts/generate_semantic_authority_inventory.py",
    "docs/method-conformance/o2/api-representation-profile-v1.json":
        "scripts/generate_semantic_projection_v1.py",
    "docs/method-conformance/o2/semantic-projection-v1.json":
        "scripts/generate_semantic_projection_v1.py",
    "docs/method-conformance/o2/api-representation-profile-v1.1.json":
        "scripts/generate_semantic_projection_o22.py",
    "docs/method-conformance/o2/semantic-projection-v1.1.json":
        "scripts/generate_semantic_projection_o22.py",
    "docs/method-conformance/o2/api-representation-profile-v1.2.json":
        "scripts/generate_semantic_projection_o23.py",
    "docs/method-conformance/o2/semantic-projection-v1.2.json":
        "scripts/generate_semantic_projection_o23.py",
    "docs/method-conformance/o3/o3-equivalence-scope.json":
        "scripts/generate_o3_equivalence_scope.py",
}
#: Frozen records that live code still reads as read-only data.
LIVE_CONSUMERS = {
    "docs/method-conformance/o1/authority-review-decisions.yaml":
        "O4 lifecycle-consistency gate (read-only data)",
    "docs/method-conformance/o1/semantic-authority-inventory.json":
        "O3 equivalence basis (read-only data)",
    "docs/method-conformance/o2/api-representation-profile-v1.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o2/semantic-projection-v1.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o2/api-representation-profile-v1.1.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o2/semantic-projection-v1.1.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o2/api-representation-profile-v1.2.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o2/semantic-projection-v1.2.json":
        "model-authority runtime o2-chain layer and O3 bundle (read-only data)",
    "docs/method-conformance/o3/o3-equivalence-scope.json":
        "O3 equivalence lane (read-only data)",
}
_RECORD_KEYS = (
    "path", "sha256", "kind", "binding_source_revision", "live_consumer",
    "retired_generator",
)

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_BARE_SHA256 = re.compile(r"^[0-9a-f]{64}$")

from de4sdv.semantic.authority_inventory import (  # noqa: E402
    validate_source_binding,
    file_digest,
)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _canonical_digest(value: Any) -> Any:
    """Canonical ``sha256:<64-hex>`` for a bare-hex digest; anything else as-is.

    Recorded digests appear in both forms across the chain (the O3 basis uses
    bare hex for one identity); both must be able to match, and anything that
    is neither form is left untouched so the mismatch is reported against the
    recorded value itself.
    """
    text = str(value)
    if _BARE_SHA256.match(text):
        return "sha256:" + text
    return value


def _binding_problems(root: Path, binding: dict[str, Any]) -> list[str]:
    """Validate one artifact's ``binding`` block against the repository."""
    source_revision = binding.get("source_revision")
    if not isinstance(source_revision, str):
        return [
            "binding.source_revision is required (full commit id of a revision "
            "containing every bound input)"
        ]
    bound_inputs = binding.get("bound_inputs")
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    normalized = {
        str(path): _canonical_digest(value) for path, value in bound_inputs.items()
    }
    return list(validate_source_binding(root, {**binding, "bound_inputs": normalized}))


def _revision_claim_problems(root: Path, revision: Any, label: str) -> list[str]:
    """Validate a bare revision claim (frozen record top-level revisions)."""
    if not isinstance(revision, str) or not _FULL_SHA.fullmatch(revision):
        return [f"{label} must be a full 40-hex commit id"]
    if _git(root, "merge-base", "--is-ancestor", revision, "HEAD").returncode:
        return [f"{label} must exist and be an ancestor of HEAD"]
    return []


def _extends_problems(
    root: Path, artifact: dict[str, Any]
) -> list[str]:
    """Validate one artifact's ``extends`` block against the repository."""
    extends = artifact.get("extends")
    if extends is None:
        return []
    if not isinstance(extends, dict):
        return ["extends must be a mapping"]
    errors: list[str] = []
    referenced = extends.get("artifact")
    if not isinstance(referenced, str) or not referenced.strip():
        return [
            "extends.artifact is required (repository-relative path of the "
            "extended artifact)"
        ]
    target = root / referenced
    if Path(referenced).is_absolute() or ".." in Path(referenced).parts or not target.resolve().is_relative_to(root.resolve()):
        return ["extends.artifact must stay inside the repository"]
    revision = extends.get("source_revision")
    if not isinstance(revision, str) or not _FULL_SHA.fullmatch(revision):
        return ["extends.source_revision must be a full commit id"]
    if _git(root, "merge-base", "--is-ancestor", revision, "HEAD").returncode:
        return ["extends.source_revision must exist and be an ancestor of HEAD"]
    if not target.is_file():
        return [f"extends.artifact {referenced} does not exist in the checkout"]
    try:
        referenced_document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"extends.artifact {referenced} is not readable JSON: {exc}"]
    actual = file_digest(root, referenced)
    recorded = extends.get("artifact_digest")
    if _canonical_digest(recorded) != actual:
        errors.append(
            f"extends.artifact_digest {recorded!r} does not match the current "
            f"bytes of {referenced} ({actual})"
        )
    referenced_revision = None
    if isinstance(referenced_document, dict):
        referenced_binding = referenced_document.get("binding")
        if isinstance(referenced_binding, dict):
            referenced_revision = referenced_binding.get("source_revision")
    if extends.get("source_revision") != referenced_revision:
        errors.append(
            f"extends.source_revision {extends.get('source_revision')!r} does "
            "not match the referenced artifact's binding.source_revision "
            f"{referenced_revision!r} ({referenced})"
        )
    return errors


def _is_frozen_path(relative: str) -> bool:
    return any(
        relative == directory or relative.startswith(directory + "/")
        for directory in FROZEN_DIRECTORIES
    )


def _git_bytes(root: Path, revision: str, relative: str) -> bytes | None:
    """Blob bytes of ``relative`` at ``revision``; ``None`` when absent."""
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{relative}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _bytes_digest(data: bytes) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(data).hexdigest()


def _commit_problems(root: Path, revision: Any, label: str) -> list[str]:
    """Format, existence and ancestry of one recorded revision (fail closed)."""
    if not isinstance(revision, str) or not _FULL_SHA.fullmatch(revision):
        return [f"{label} must be a full 40-hex commit id (got {revision!r})"]
    if _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode != 0:
        return [f"{label} {revision} is not a commit in this repository"]
    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0 or not head.stdout.strip():
        return [f"cannot resolve the checked-out revision to validate {label}"]
    if _git(root, "merge-base", "--is-ancestor", revision, head.stdout.strip()).returncode:
        return [
            f"{label} {revision} is not an ancestor of the checked-out revision "
            f"{head.stdout.strip()}"
        ]
    return []


def _tree_paths(root: Path, revision: str) -> list[str]:
    result = _git(root, "ls-tree", "-r", "--name-only", revision, "--", *FROZEN_DIRECTORIES)
    if result.returncode != 0:
        raise ValueError(f"cannot list the frozen directories at {revision}")
    return sorted(line for line in result.stdout.splitlines() if line)


def _worktree_paths(root: Path) -> list[str]:
    paths: list[str] = []
    for directory in FROZEN_DIRECTORIES:
        base = root / directory
        if base.is_dir():
            paths.extend(
                path.relative_to(root).as_posix()
                for path in base.rglob("*")
                if path.is_file() or path.is_symlink()
            )
    return sorted(paths)


def _record_kind(relative: str, data: bytes) -> str:
    if relative.endswith(".md"):
        return "prose"
    if relative.endswith(".json"):
        try:
            document = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return "evidence"
        if isinstance(document, dict) and isinstance(document.get("binding"), dict):
            return "generated"
        return "evidence"
    return "authored"


def render_frozen_manifest(root: Path, revision: str) -> dict[str, Any]:
    """Deterministic frozen-records manifest from the tree at ``revision``.

    Every field is derived from the historical bytes (path, sha256, kind,
    binding source revision) or from the reviewed constants in this module
    (live consumer, retired generator), so the committed manifest can be
    re-derived and compared byte-for-byte.
    """
    records = []
    for relative in _tree_paths(root, revision):
        data = _git_bytes(root, revision, relative)
        if data is None:
            raise ValueError(f"{relative} is unreadable at {revision}")
        binding_revision = None
        if relative.endswith(".json"):
            try:
                document = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                document = None
            if isinstance(document, dict) and isinstance(document.get("binding"), dict):
                binding_revision = document["binding"].get("source_revision")
        records.append({
            "path": relative,
            "sha256": _bytes_digest(data),
            "kind": _record_kind(relative, data),
            "binding_source_revision": binding_revision,
            "live_consumer": LIVE_CONSUMERS.get(relative),
            "retired_generator": RETIRED_GENERATORS.get(relative),
        })
    return {
        "schema": FROZEN_SCHEMA,
        "note": (
            "Frozen historical records. Never regenerated; never compared with "
            "the live tree's inputs. Bindings are verified at their own "
            "source revisions by scripts/verify_generated_chain.py (frozen "
            "lane), which scripts/check_repo.py runs. Not revision-bound "
            "evidence itself: no binding block."
        ),
        "decision": dict(FROZEN_DECISION),
        "frozen_at_revision": revision,
        "directories": list(FROZEN_DIRECTORIES),
        "records": records,
    }


def render_frozen_manifest_text(root: Path, revision: str) -> str:
    return json.dumps(render_frozen_manifest(root, revision), indent=2) + "\n"


def _historical_binding_problems(root: Path, binding: Any) -> list[str]:
    """Check a frozen record's binding at its own revision, never at HEAD."""
    if not isinstance(binding, dict):
        return ["binding block must be a mapping"]
    revision = binding.get("source_revision")
    errors = _commit_problems(root, revision, "binding.source_revision")
    if errors:
        return errors
    bound_inputs = binding.get("bound_inputs")
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    for relative, recorded in sorted(bound_inputs.items()):
        data = _git_bytes(root, revision, str(relative))
        if data is None:
            errors.append(
                f"bound input {relative} does not exist at source revision {revision}"
            )
            continue
        actual = _bytes_digest(data)
        if _canonical_digest(recorded) != actual:
            errors.append(
                f"bound input {relative}: recorded digest {recorded!r} does not "
                f"match its bytes at source revision {revision} ({actual})"
            )
    for key in ("ontology_contract", "reviewed_decisions", "closure_evidence",
                "runtime_strategy_source"):
        if key not in binding:
            continue
        view = binding[key]
        if not isinstance(view, dict) or view.get("path") not in bound_inputs:
            errors.append(f"binding.{key} must name a bound input")
        elif view.get("digest") != bound_inputs[view["path"]]:
            errors.append(f"binding.{key} digest does not match its bound input digest")
    return errors


def _frozen_extends_problems(
    root: Path, document: dict[str, Any], digests: dict[str, str]
) -> list[str]:
    extends = document.get("extends")
    if extends is None:
        return []
    if not isinstance(extends, dict):
        return ["extends must be a mapping"]
    referenced = extends.get("artifact")
    if referenced not in digests:
        return [f"extends.artifact {referenced!r} must be a frozen record"]
    errors = []
    if _canonical_digest(extends.get("artifact_digest")) != digests[referenced]:
        errors.append(
            f"extends.artifact_digest {extends.get('artifact_digest')!r} does not "
            f"match the frozen digest of {referenced} ({digests[referenced]})"
        )
    errors.extend(_commit_problems(root, extends.get("source_revision"),
                                   "extends.source_revision"))
    try:
        target = json.loads((root / referenced).read_text(encoding="utf-8"))
        target_revision = (target.get("binding") or {}).get("source_revision")
    except (OSError, ValueError, AttributeError):
        target_revision = None
    if extends.get("source_revision") != target_revision:
        errors.append(
            f"extends.source_revision {extends.get('source_revision')!r} does not "
            f"match the referenced record's binding.source_revision "
            f"{target_revision!r} ({referenced})"
        )
    return errors


def _o3_basis_problems(
    root: Path, document: dict[str, Any], digests: dict[str, str]
) -> list[str]:
    """The O3 scope basis may reference frozen records only, at their digests."""
    basis = document.get("basis")
    if not isinstance(basis, dict):
        return ["o3 equivalence scope has no basis block"]
    errors: list[str] = []

    def _basis_digest(label: str, record: Any) -> None:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            errors.append(f"o3 basis.{label} must be a mapping with a path")
            return
        relative = record["path"]
        if relative not in digests:
            errors.append(f"o3 basis.{label} {relative} must be a frozen record")
            return
        if _canonical_digest(record.get("sha256")) != digests[relative]:
            errors.append(
                f"o3 basis.{label} digest {record.get('sha256')!r} does not match "
                f"the frozen digest of {relative} ({digests[relative]})"
            )

    _basis_digest("o1_inventory", basis.get("o1_inventory"))
    chain = basis.get("o2_chain")
    if not isinstance(chain, list):
        errors.append("o3 basis.o2_chain must be a list")
    else:
        for index, item in enumerate(chain):
            _basis_digest(f"o2_chain[{index}]", item)
    errors.extend(_commit_problems(root, basis.get("comparison_base_revision"),
                                   "o3 basis.comparison_base_revision"))
    return errors


def _frozen_lane_entries(root: Path) -> list[dict[str, Any]]:
    """Report entries for the frozen-records manifest and every frozen record."""
    manifest_path = root / FROZEN_MANIFEST_PATH

    def _fail(errors: list[str]) -> list[dict[str, Any]]:
        return [{"artifact": FROZEN_MANIFEST_PATH, "ok": False, "errors": errors}]

    if not manifest_path.is_file():
        return _fail(["frozen-records manifest is missing"])
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail([f"frozen-records manifest is not readable JSON: {exc}"])
    if not isinstance(manifest, dict) or manifest.get("schema") != FROZEN_SCHEMA:
        return _fail([f"frozen-records manifest schema must be {FROZEN_SCHEMA}"])
    errors: list[str] = []
    for key in ("binding", "source_revision", "extends"):
        if key in manifest:
            errors.append(f"frozen-records manifest must not carry a {key!r} key")
    if manifest.get("directories") != list(FROZEN_DIRECTORIES):
        errors.append(
            "frozen-records directories must be exactly "
            f"{list(FROZEN_DIRECTORIES)} (owner decision D10)"
        )
    revision = manifest.get("frozen_at_revision")
    revision_errors = _commit_problems(root, revision, "frozen_at_revision")
    errors.extend(revision_errors)
    records = manifest.get("records")
    if not isinstance(records, list) or not all(
        isinstance(r, dict) and tuple(r) == _RECORD_KEYS for r in records
    ):
        return _fail(errors + [
            f"frozen-records records must be a list of {list(_RECORD_KEYS)} mappings"
        ])
    paths = [record["path"] for record in records]
    if len(set(paths)) != len(paths):
        errors.append("frozen-records manifest lists a path twice")
    if not revision_errors:
        try:
            rendered = render_frozen_manifest_text(root, revision)
        except ValueError as exc:
            errors.append(f"cannot render the frozen manifest at {revision}: {exc}")
        else:
            if rendered != manifest_path.read_text(encoding="utf-8"):
                errors.append(
                    "frozen-records manifest differs from its rendering at "
                    f"frozen_at_revision {revision} (record set, digests or record "
                    "metadata changed)"
                )
    present = set(_worktree_paths(root))
    for relative in sorted(present - set(paths)):
        errors.append(f"{relative} is under a frozen directory but not a frozen record")
    for relative in sorted(set(paths) - present):
        errors.append(f"frozen record {relative} is missing from the checkout")
    entries = [{"artifact": FROZEN_MANIFEST_PATH, "ok": not errors, "errors": errors}]
    digests = {record["path"]: record["sha256"] for record in records}
    for record in records:
        relative = record["path"]
        record_errors: list[str] = []
        if not _is_frozen_path(relative):
            record_errors.append("frozen record path is outside the frozen directories")
        path = root / relative
        if not path.is_file():
            entries.append({"artifact": relative, "ok": False,
                            "errors": ["frozen record is missing from the checkout"]})
            continue
        data = path.read_bytes()
        if _bytes_digest(data) != record["sha256"]:
            record_errors.append(
                f"frozen record bytes changed: recorded {record['sha256']}, current "
                f"{_bytes_digest(data)} (frozen records are never edited or "
                "regenerated)"
            )
        if relative.endswith(".json"):
            try:
                document = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                document = None
                record_errors.append(f"frozen record is not readable JSON: {exc}")
            if isinstance(document, dict):
                if "binding" in document:
                    record_errors.extend(
                        _historical_binding_problems(root, document["binding"]))
                    if record["binding_source_revision"] != (
                        document["binding"] or {}).get("source_revision"):
                        record_errors.append(
                            "binding_source_revision differs from the record's binding")
                elif "source_revision" in document:
                    record_errors.extend(_commit_problems(
                        root, document["source_revision"], "top-level source_revision"))
                record_errors.extend(_frozen_extends_problems(root, document, digests))
                if relative == O3_SCOPE_PATH:
                    record_errors.extend(_o3_basis_problems(root, document, digests))
        entries.append({"artifact": relative, "ok": not record_errors,
                        "errors": record_errors})
    if O3_SCOPE_PATH not in digests:
        entries.append({"artifact": O3_SCOPE_PATH, "ok": False,
                        "errors": ["required O3 scope artifact is not a frozen record"]})
    return entries


def frozen_record_errors(root: Path) -> list[str]:
    """Flat error list of the frozen lane (used by ``scripts/check_repo.py``)."""
    return [
        f"{entry['artifact']}: {error}"
        for entry in _frozen_lane_entries(Path(root))
        for error in entry["errors"]
    ]


def _expected_inputs(root: Path) -> dict[str, set[str]]:
    """Required coverage comes from supported lanes, never artifact declarations."""
    # Frozen O1/O2 records (owner decision Q7) are not live lanes: the frozen
    # lane checks their bindings at their own revisions instead.
    from de4sdv.semantic import projection_o2p as plus
    from de4sdv.semantic import definition_projection as definitions
    from de4sdv.semantic import definition_projection_batch2 as definitions_b2
    from de4sdv.semantic import vocabulary_carrier as carriers

    expected: dict[str, set[str]] = {}
    admission = plus.load_admission_o2p(root / plus.ADMISSION_O2P_PATH)
    inputs = set(plus.collect_bound_inputs_o2p(root, admission))
    for prefix in ("semantic-projection", "api-representation-profile"):
        expected[f"docs/method-conformance/o2plus/{prefix}-o2plus.json"] = inputs
    outputs = definitions.build_outputs(root, definitions.load_document(root))
    inputs = set(definitions.collect_bound_inputs(root, outputs))
    for suffix in ("projection", "profile"):
        expected[f"docs/method-conformance/o4/definition-{suffix}.json"] = inputs
    outputs = definitions_b2.build_outputs(root, definitions_b2.load_document(root))
    inputs = set(definitions_b2.collect_bound_inputs(root, outputs))
    for relative in (definitions_b2.PROJECTION_PATH, definitions_b2.PROFILE_PATH):
        expected[relative] = inputs
    document = carriers.load_carriers(root / carriers.CARRIERS_PATH)
    outputs = carriers.build_carrier_outputs(root, document, carriers.load_review(root))
    inputs = set(carriers.collect_bound_inputs(root, document, outputs))
    for suffix in ("projection", "profile"):
        expected[f"docs/method-conformance/o4/vocabulary-carriers-{suffix}.json"] = inputs
    return expected


def _chain_artifacts(root: Path) -> list[Path]:
    base = root / METHOD_CONFORMANCE_DIR
    if not base.is_dir():
        return []
    return [
        path
        for path in sorted(base.rglob("*.json"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and not _is_frozen_path(path.relative_to(root).as_posix())
        and path.relative_to(root).as_posix() != FROZEN_MANIFEST_PATH
    ]


def _artifact_entry(root: Path, path: Path) -> dict[str, Any] | None:
    """One report entry for an artifact carrying a ``binding`` block."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        relative = path.relative_to(root).as_posix()
        return {
            "artifact": relative,
            "ok": False,
            "errors": [f"artifact is not readable JSON: {exc}"],
        }
    if not isinstance(document, dict):
        # A non-object JSON document cannot carry a binding/extends block, so
        # it is outside this verifier's scope (e.g. list-shaped record files).
        return None
    relative = path.relative_to(root).as_posix()
    if _is_frozen_path(relative) or relative == FROZEN_MANIFEST_PATH:
        return None  # validated by the frozen lane
    binding = document.get("binding")
    errors: list[str] = []
    if isinstance(binding, dict):
        errors.extend(_binding_problems(root, binding))
    elif "binding" in document:
        errors.append("binding block must be a mapping")
    else:
        # No binding block: an extends block (if any) is still chain evidence;
        # a top-level source_revision claim (frozen review/validation records)
        # is validated too, never trusted as a recorded string.
        if "extends" in document:
            errors.extend(_extends_problems(root, document))
            return {"artifact": relative, "ok": not errors, "errors": errors}
        top_revision = document.get("source_revision")
        if top_revision is None:
            return None
        errors.extend(
            _revision_claim_problems(root, top_revision, "top-level source_revision")
        )
        return {"artifact": relative, "ok": not errors, "errors": errors}
    errors.extend(_extends_problems(root, document))
    return {"artifact": relative, "ok": not errors, "errors": errors}


def verify_generated_chain(
    root: Path, *, include_passing: bool = False
) -> list[dict[str, Any]]:
    """Verify every binding-carrying artifact under ``docs/method-conformance``.

    Returns the report entries — ``{artifact, ok, errors[]}`` sorted by path —
    for the artifacts that failed. An empty list therefore means the whole
    chain is consistent. Pass ``include_passing=True`` for the full report
    (one entry per verified artifact, passing ones included).
    """
    root = Path(root)
    entries: list[dict[str, Any]] = []
    try:
        expected = _expected_inputs(root)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return [{"artifact": METHOD_CONFORMANCE_DIR, "ok": False,
                 "errors": [f"cannot derive required chain inputs: {exc}"]}]
    paths = set(_chain_artifacts(root)) | {root / path for path in expected}
    for path in sorted(paths):
        entry = _artifact_entry(root, path)
        relative = path.relative_to(root).as_posix()
        if relative in expected:
            if entry is None:
                entry = {"artifact": relative, "ok": False,
                         "errors": ["required generated artifact has no binding"]}
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                binding = document.get("binding") if isinstance(document, dict) else None
                inputs = binding.get("bound_inputs") if isinstance(binding, dict) else None
                if not isinstance(inputs, dict) or set(inputs) != expected[relative]:
                    entry["errors"].append("bound_inputs differs from generator-required input set")
            except (OSError, ValueError):
                pass  # _artifact_entry already reports unreadable artifacts.
            entry["ok"] = not entry["errors"]
        if entry is not None:
            entries.append(entry)
    entries.extend(_frozen_lane_entries(root))
    entries.sort(key=lambda entry: entry["artifact"])
    if include_passing:
        return entries
    return [entry for entry in entries if not entry["ok"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the machine-readable report instead of the human summary",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="repository root to verify (default: this script's repository)",
    )
    parser.add_argument(
        "--render-frozen-manifest",
        metavar="REVISION",
        help=(
            "print the frozen-records manifest rendered from the tree at "
            "REVISION (review aid; never writes)"
        ),
    )
    args = parser.parse_args(argv)

    if args.render_frozen_manifest:
        sys.stdout.write(
            render_frozen_manifest_text(Path(args.root), args.render_frozen_manifest)
        )
        return 0

    report = verify_generated_chain(Path(args.root), include_passing=True)
    failing = [entry for entry in report if not entry["ok"]]
    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if failing else 0

    if failing:
        print("Generated-artifact chain verification FAILED.")
        for entry in failing:
            for error in entry["errors"]:
                print(f"  - {entry['artifact']}: {error}")
        print(
            f"{len(failing)} of {len(report)} artifact(s) failed; "
            "regenerate the artifact bound to a commit that contains the "
            "current inputs."
        )
        return 1
    print("Generated-artifact chain verification passed.")
    print(f"artifacts checked: {len(report)}")
    for entry in report:
        print(f"  OK  {entry['artifact']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())