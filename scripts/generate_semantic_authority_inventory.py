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

RETIRED_MESSAGE = (
    "scripts/generate_semantic_authority_inventory.py is retired: its output is a frozen record "
    "(owner decisions Q7 and D10, 2026-10-07) and is never regenerated or "
    "re-checked against the live tree. The record bytes are pinned by "
    "docs/method-conformance/frozen-records.json; verify them with "
    "python scripts/verify_generated_chain.py (frozen lane)."
)


def main(argv: list[str] | None = None) -> int:
    """Refuse to write or check: the generated output is a frozen record.

    O4 Wave C2 deleted the generator library (it read the retired authored
    ontology); only this refusal remains.
    """
    del argv
    print(RETIRED_MESSAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
