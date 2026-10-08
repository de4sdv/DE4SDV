#!/usr/bin/env python3
"""Generate (or check) the O1 Semantic Authority Inventory.

RETIRED (O4 Wave C1, owner decisions Q7 and D10, 2026-10-07): the output is a
frozen record. The CLI refuses to write or check; the frozen lane of
``scripts/verify_generated_chain.py`` verifies the record instead. The
library functions below stay importable until O4 Wave C2 removes them.

Canonical artifacts:

- ``docs/method-conformance/o1/semantic-authority-inventory.json``
  (machine-readable canonical inventory; Layer A observed facts joined with
  Layer B reviewed decisions, provenance preserved);
- ``docs/method-conformance/o1/authority-inventory.md``
  (human-readable review table derived from the same canonical data).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifact binds a ``source_revision`` — a Git commit that contains
every bound source input byte-for-byte — plus per-input content digests. A
generated artifact cannot bind to the commit that first introduces it, so the
artifact is produced in a two-commit pattern: commit the bound inputs first,
then generate and commit the artifacts bound to that input commit.

``--check`` (used by ``scripts/check_repo.py``) validates the recorded binding
against the repository — commit existence, ancestry, per-input content
equality with the source revision, and the recorded digests — and then
regenerates with the recorded source revision and compares bytes. A stale
revision can never pass by string reuse.

Offline and read-only: no network, no privileged ingestion, no runtime
semantic change. This is a CI/governance check; the runtime never reads the
generated inventory.

Usage:

    python scripts/generate_semantic_authority_inventory.py                 # write
    python scripts/generate_semantic_authority_inventory.py --check         # verify
    python scripts/generate_semantic_authority_inventory.py \
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.authority_inventory import (  # noqa: E402
    INVENTORY_JSON_PATH,
    INVENTORY_MD_PATH,
    InventoryError,
    build_inventory,
    canonical_json,
    render_markdown,
    resolve_source_revision,
    validate_source_binding,
)


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build the canonical inventory bound to a source revision.

    ``source_revision`` defaults to the checkout's HEAD; it must contain every
    bound input byte-for-byte, and generation fails otherwise (commit input
    changes first, then regenerate so the artifact can bind to that commit).
    """
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_inventory(root, source_revision=source_revision)


def run_check_errors(root: Path | None = None) -> list[str]:
    """Check that the committed artifacts equal regeneration from inputs.

    Validates the recorded source-revision binding against the repository
    (commit existence, ancestry of the checked-out revision, per-input content
    equality, recorded digests), then regenerates with the recorded source
    revision and compares bytes for both the canonical JSON and the derived
    review table. Any uncommitted input change, stale binding, coverage
    failure, or hand edit of a generated file is an error.
    """
    root = root or ROOT
    errors: list[str] = []
    json_path = root / INVENTORY_JSON_PATH
    md_path = root / INVENTORY_MD_PATH
    if not json_path.is_file():
        errors.append(f"semantic authority inventory missing: {INVENTORY_JSON_PATH}")
    if not md_path.is_file():
        errors.append(f"semantic authority inventory table missing: {INVENTORY_MD_PATH}")
    if errors:
        return errors
    try:
        committed = json.loads(json_path.read_text(encoding="utf-8"))
        binding = committed["binding"]
    except (KeyError, ValueError) as exc:
        return [
            f"{INVENTORY_JSON_PATH}: cannot read binding for validation: {exc}"
        ]
    binding_errors = validate_source_binding(root, binding)
    if binding_errors:
        return [
            f"{INVENTORY_JSON_PATH}: source-revision binding invalid: {error}"
            for error in binding_errors
        ]
    try:
        inventory = generate(root, source_revision=binding["source_revision"])
    except InventoryError as exc:
        return [f"semantic authority inventory generation failed: {exc}"]
    if canonical_json(inventory) != json_path.read_text(encoding="utf-8"):
        errors.append(
            f"{INVENTORY_JSON_PATH}: committed inventory differs from "
            "regeneration from current inputs (regenerate and commit)"
        )
    if render_markdown(inventory) != md_path.read_text(encoding="utf-8"):
        errors.append(
            f"{INVENTORY_MD_PATH}: committed review table differs from "
            "regeneration from the canonical inventory data"
        )
    return errors


RETIRED_MESSAGE = (
    "scripts/generate_semantic_authority_inventory.py is retired: its output is a frozen record "
    "(owner decisions Q7 and D10, 2026-10-07) and is never regenerated or "
    "re-checked against the live tree. The record bytes are pinned by "
    "docs/method-conformance/frozen-records.json; verify them with "
    "python scripts/verify_generated_chain.py (frozen lane)."
)


def main(argv: list[str] | None = None) -> int:
    """Refuse to write or check: the generated output is a frozen record."""
    del argv
    print(RETIRED_MESSAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
