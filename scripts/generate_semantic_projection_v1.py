#!/usr/bin/env python3
"""Generate (or check) the O2.1 Semantic Projection v1 and Representation Profile v1.

RETIRED (O4 Wave C1, owner decisions Q7 and D10, 2026-10-07): the output is a
frozen record. The CLI refuses to write or check; the frozen lane of
``scripts/verify_generated_chain.py`` verifies the record instead. The
library functions below stay importable until O4 Wave C2 removes them.

Canonical artifacts:

- ``docs/method-conformance/o2/semantic-projection-v1.json``
  (DE4SDV Semantic Projection v1: the generated semantic representation of
  the seven settled c1 method-conformance identities);
- ``docs/method-conformance/o2/api-representation-profile-v1.json``
  (SysML API Representation Profile v1: representation mechanics only).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifacts bind a ``source_revision`` — a Git commit that contains
every bound source input byte-for-byte — plus per-input content digests. A
generated artifact cannot bind to the commit that first introduces it, and in
a squash-only repository a feature-branch commit does not survive in ``main``
ancestry, so the artifacts are published by the squash-safe delivery
sequence: Stage A (this PR) delivers the architecture, generator, tests,
design record, and admission manifest; its squash-merge produces a permanent
``main`` commit; Stage B then generates and commits the artifacts bound to
that permanent commit (itself following the two-commit pattern inside the
Stage B PR). Stage A does not register the ``--check`` gate in
``scripts/check_repo.py`` — the gate is registered in Stage B together with
the artifacts it validates.

``--check`` (registered in ``scripts/check_repo.py`` in Stage B) validates the
recorded binding against the repository — commit existence, ancestry,
per-input content equality with the source revision, and the recorded digests
— and then regenerates with the recorded source revision and compares bytes.
A stale revision can never pass by string reuse; absent artifacts are
reported, never silently passed.

Boundaries (O2.1): offline and read-only; no network, no privileged
ingestion, no runtime semantic change; generation is not authority
activation; the runtime never reads these artifacts; the O1 migration
inventory is never read (governance, not semantic authority); no support
promotion.

Usage:

    python scripts/generate_semantic_projection_v1.py              # write
    python scripts/generate_semantic_projection_v1.py --check      # verify
    python scripts/generate_semantic_projection_v1.py \
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

RETIRED_MESSAGE = (
    "scripts/generate_semantic_projection_v1.py is retired: its output is a frozen record "
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
