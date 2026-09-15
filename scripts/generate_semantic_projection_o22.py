#!/usr/bin/env python3
"""Generate (or check) the O2.2 Semantic Projection v1.1 / Profile v1.1 extension.

Canonical artifacts (additive extensions of the immutable O2.1 baselines —
the projection extends the projection baseline, the profile extends the
profile baseline):

- ``docs/method-conformance/o2/semantic-projection-v1.1.json``
  (DE4SDV Semantic Projection v1.1: the generated semantic representation of
  the three settled c2/c3 identities — ``VerificationCase``, ``hasSubject``,
  ``verifiedBy`` — extending the O2.1 projection baseline by reference, never
  by mutation);
- ``docs/method-conformance/o2/api-representation-profile-v1.1.json``
  (SysML API Representation Profile v1.1: representation mechanics only).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifacts bind a ``source_revision`` — a Git commit that contains
every bound input byte-for-byte — plus per-input content digests, and pin the
O2.1 baseline by path, schema, source revision, and artifact digest
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

Boundaries (O2.2): offline and read-only; no network, no privileged
ingestion, no runtime semantic change; generation is not authority
activation; the runtime never reads these artifacts; the O1 migration
inventory is never read; no support promotion; no current SysML API
project/commit closure is claimed.

Usage:

    python scripts/generate_semantic_projection_o22.py              # write
    python scripts/generate_semantic_projection_o22.py --check      # verify
    python scripts/generate_semantic_projection_o22.py \\
        --source-revision <40-hex commit id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.projection_o22 import (  # noqa: E402
    PROFILE_V11_JSON_PATH,
    PROJECTION_V11_JSON_PATH,
    ProjectionO22Error,
    build_pair_o22,
    canonical_json,
    resolve_source_revision,
    run_check_errors_o22,
)


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both extension artifacts bound to a source revision.

    ``source_revision`` defaults to the checkout's HEAD; it must contain every
    bound input byte-for-byte, and generation fails otherwise (commit inputs
    first, then regenerate so the artifacts can bind to that commit).
    """
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_pair_o22(root, source_revision=source_revision)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts equal regeneration (no writes)",
    )
    parser.add_argument(
        "--source-revision",
        default=None,
        help=(
            "explicit Git commit id that contains every bound input "
            "byte-for-byte (default: HEAD)"
        ),
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors_o22(ROOT)
        if errors:
            print("Semantic projection v1.1 check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Semantic projection v1.1 check passed.")
        return 0

    try:
        artifacts = generate(ROOT, source_revision=args.source_revision)
    except ProjectionO22Error as exc:
        print("Semantic projection v1.1 generation FAILED.")
        print(f"  - {exc}")
        return 1
    (ROOT / PROJECTION_V11_JSON_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (ROOT / PROFILE_V11_JSON_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    print(f"wrote {PROJECTION_V11_JSON_PATH}")
    print(f"wrote {PROFILE_V11_JSON_PATH}")
    print(
        "source revision: "
        f"{artifacts['projection']['binding']['source_revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())