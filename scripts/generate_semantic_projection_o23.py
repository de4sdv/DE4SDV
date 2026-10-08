#!/usr/bin/env python3
"""Generate (or check) the O2.3 Semantic Projection v1.2 / Profile v1.2 extension.

RETIRED (O4 Wave C1, owner decisions Q7 and D10, 2026-10-07): the output is a
frozen record. The CLI refuses to write or check; the frozen lane of
``scripts/verify_generated_chain.py`` verifies the record instead. The
library functions below stay importable until O4 Wave C2 removes them.

Canonical artifacts (additive extensions of the immutable O2.2 baselines —
the projection extends the projection baseline, the profile extends the
profile baseline; published in Stage B):

- ``docs/method-conformance/o2/semantic-projection-v1.2.json``
  (DE4SDV Semantic Projection v1.2: the generated semantic representation of
  the final O2 slice — the K derivation pair ``derivesRequirementFromNeed`` /
  ``derivedRequirementsOfNeed`` (ONE modeled fact, TWO navigations) and
  ``hasRelevantArchitecture`` — extending the O2.2 projection baseline by
  reference, never by mutation);
- ``docs/method-conformance/o2/api-representation-profile-v1.2.json``
  (SysML API Representation Profile v1.2: representation mechanics only).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifacts bind a ``source_revision`` — a Git commit that contains
every bound input byte-for-byte — plus per-input content digests, and pin the
O2.2 baseline by path, schema, source revision, and artifact digest
(``extends`` block). Because DE4SDV keeps squash-only linear history, the
canonical artifacts are published by the squash-safe delivery sequence:
Stage A (this foundation PR) delivers the module, generator, admission
manifest, design record, and tests; its squash-merge produces a permanent
``main`` commit; Stage B generates and commits the artifacts bound to that
permanent commit and activates the repository gate. Stage A does not register
the ``--check`` gate in ``scripts/check_repo.py``.

``--check`` (registered in ``scripts/check_repo.py`` in Stage B) validates the
recorded binding against the repository (commit existence, ancestry,
per-input content equality, recorded digests), validates the baseline
anchoring (baseline digest equality; baseline source revision ancestor of the
extension source revision), then regenerates with the recorded source
revision and compares bytes. A stale revision can never pass by string reuse;
absent artifacts are reported, never silently passed.

Boundaries (O2.3): offline and read-only; no network, no privileged
ingestion, no runtime semantic change; generation is not authority
activation; the runtime never reads these artifacts; the O1 migration
inventory is never read; no support promotion (historical K closure evidence
does not promote current support); no current SysML API project/commit
closure is claimed; no model file changes.

Usage:

    python scripts/generate_semantic_projection_o23.py              # write
    python scripts/generate_semantic_projection_o23.py --check      # verify
    python scripts/generate_semantic_projection_o23.py \\
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

RETIRED_MESSAGE = (
    "scripts/generate_semantic_projection_o23.py is retired: its output is a frozen record "
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
