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
4. ``docs/method-conformance/o3/o3-equivalence-scope.json`` (when present):
   every basis digest (``o1_inventory``, ``o2_chain`` items) matches the
   current file bytes, and its ``comparison_base_revision`` exists and is an
   ancestor of the checked-out revision. The recorded old-bundle digests
   (``ontology``, ``kernel_contract_*``, ``runtime_files``) are bound to the
   comparison base revision by the O3 lane's own gate and are deliberately
   NOT compared against the working tree here.

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

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_BARE_SHA256 = re.compile(r"^[0-9a-f]{64}$")

try:  # shared lane helpers (same repository)
    from de4sdv.semantic.authority_inventory import (  # noqa: E402
        InventoryError,
        _binding_errors,
        file_digest,
    )
except ImportError:  # pragma: no cover - defensive; the repository ships it
    InventoryError = Exception  # type: ignore[assignment,misc]
    _binding_errors = None  # type: ignore[assignment]

    def file_digest(root: Path, relative: str) -> str:  # type: ignore[misc]
        import hashlib

        return "sha256:" + hashlib.sha256((root / relative).read_bytes()).hexdigest()


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
    if _binding_errors is not None:
        return list(_binding_errors(root, source_revision, normalized))
    # Fallback: the generation-time guard behind the same contract, split back
    # into the individual problems it refuses with.
    from de4sdv.semantic.authority_inventory import (  # type: ignore[import]
        verify_source_revision_contains_inputs,
    )

    try:
        verify_source_revision_contains_inputs(root, source_revision, normalized)
    except InventoryError as exc:  # type: ignore[misc]
        body = str(exc).split("byte-for-byte:", 1)[-1]
        return [
            chunk.strip()
            for chunk in body.split("\n  - ")
            if chunk.strip() and not chunk.strip().startswith("Commit the input")
        ]
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


def _o3_scope_entry(root: Path) -> dict[str, Any] | None:
    """Validate the committed O3 equivalence scope basis when it exists."""
    path = root / O3_SCOPE_PATH
    if not path.is_file():
        return None
    errors: list[str] = []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "artifact": O3_SCOPE_PATH,
            "ok": False,
            "errors": [f"o3 equivalence scope is not readable JSON: {exc}"],
        }
    if not isinstance(document, dict):
        return {
            "artifact": O3_SCOPE_PATH,
            "ok": False,
            "errors": ["o3 equivalence scope must be a JSON object"],
        }
    basis = document.get("basis")
    if not isinstance(basis, dict):
        return {
            "artifact": O3_SCOPE_PATH,
            "ok": False,
            "errors": ["o3 equivalence scope has no basis block"],
        }

    def _basis_digest(label: str, record: Any) -> None:
        if not isinstance(record, dict):
            errors.append(f"o3 basis.{label} must be a mapping")
            return
        relative = record.get("path")
        if not isinstance(relative, str) or not relative.strip():
            errors.append(f"o3 basis.{label}.path is required")
            return
        if not (root / relative).is_file():
            errors.append(
                f"o3 basis.{label} file {relative} is missing from the checkout"
            )
            return
        recorded = record.get("sha256")
        actual = file_digest(root, relative)
        if _canonical_digest(recorded) != actual:
            errors.append(
                f"o3 basis.{label} digest {recorded!r} does not match the "
                f"current bytes of {relative} ({actual})"
            )

    _basis_digest("o1_inventory", basis.get("o1_inventory"))
    o2_chain = basis.get("o2_chain")
    if not isinstance(o2_chain, list):
        errors.append("o3 basis.o2_chain must be a list")
    else:
        for index, item in enumerate(o2_chain):
            _basis_digest(f"o2_chain[{index}]", item)

    base_revision = basis.get("comparison_base_revision")
    if not isinstance(base_revision, str) or not _FULL_SHA.match(base_revision):
        errors.append(
            "o3 basis.comparison_base_revision must be a full 40-hex commit id "
            f"(got {base_revision!r})"
        )
    elif _git(root, "cat-file", "-e", f"{base_revision}^{{commit}}").returncode != 0:
        errors.append(
            f"o3 basis.comparison_base_revision {base_revision} is not a commit "
            "in this repository"
        )
    else:
        head = _git(root, "rev-parse", "HEAD")
        if head.returncode != 0 or not head.stdout.strip():
            errors.append(
                "cannot resolve the checked-out revision (git rev-parse HEAD "
                "failed): the o3 comparison base cannot be validated"
            )
        elif (
            _git(
                root, "merge-base", "--is-ancestor", base_revision, head.stdout.strip()
            ).returncode
            != 0
        ):
            errors.append(
                f"o3 basis.comparison_base_revision {base_revision} is not an "
                f"ancestor of the checked-out revision {head.stdout.strip()}"
            )
    return {"artifact": O3_SCOPE_PATH, "ok": not errors, "errors": errors}


def _chain_artifacts(root: Path) -> list[Path]:
    base = root / METHOD_CONFORMANCE_DIR
    if not base.is_dir():
        return []
    return [
        path
        for path in sorted(base.rglob("*.json"))
        if path.is_file() and "__pycache__" not in path.parts
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
    if relative == O3_SCOPE_PATH:
        return None  # validated by the dedicated basis lane
    binding = document.get("binding")
    errors: list[str] = []
    if isinstance(binding, dict):
        errors.extend(_binding_problems(root, binding))
    elif "binding" in document:
        errors.append("binding block must be a mapping")
    else:
        # No binding block: nothing in the binding lane applies, but an
        # extends block (if any) is still chain evidence and is validated.
        if "extends" not in document:
            return None
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
    for path in _chain_artifacts(root):
        entry = _artifact_entry(root, path)
        if entry is not None:
            entries.append(entry)
    o3_entry = _o3_scope_entry(root)
    if o3_entry is not None:
        entries.append(o3_entry)
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
    args = parser.parse_args(argv)

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