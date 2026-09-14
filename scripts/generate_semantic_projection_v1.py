#!/usr/bin/env python3
"""Generate (or check) the O2.1 Semantic Projection v1 and Representation Profile v1.

Canonical artifacts:

- ``docs/method-conformance/o2/semantic-projection-v1.json``
  (DE4SDV Semantic Projection v1: the generated semantic representation of
  the seven settled c1 method-conformance identities);
- ``docs/method-conformance/o2/api-representation-profile-v1.json``
  (SysML API Representation Profile v1: representation mechanics only).

Determinism and revision binding: identical inputs produce byte-identical
output. The artifacts bind a ``source_revision`` — a Git commit that contains
every bound source input byte-for-byte — plus per-input content digests. A
generated artifact cannot bind to the commit that first introduces it, so the
artifacts are produced in a two-commit pattern: commit the bound inputs
(architecture, generator, tests, design record, admission manifest) first,
then generate and commit the artifacts bound to that input commit.

``--check`` (used by ``scripts/check_repo.py``) validates the recorded binding
against the repository — commit existence, ancestry, per-input content
equality with the source revision, and the recorded digests — and then
regenerates with the recorded source revision and compares bytes. A stale
revision can never pass by string reuse.

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

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.projection_v1 import (  # noqa: E402
    PROFILE_V1_JSON_PATH,
    PROJECTION_V1_JSON_PATH,
    ProjectionV1Error,
    build_pair,
    canonical_json,
    resolve_source_revision,
    run_check_errors,
)


def generate(root: Path, *, source_revision: str | None = None) -> dict:
    """Build both artifacts bound to a source revision.

    ``source_revision`` defaults to the checkout's HEAD; it must contain every
    bound input byte-for-byte, and generation fails otherwise (commit inputs
    first, then regenerate so the artifacts can bind to that commit).
    """
    if source_revision is None:
        source_revision = resolve_source_revision(root)
    return build_pair(root, source_revision=source_revision)


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
        errors = run_check_errors(ROOT)
        if errors:
            print("Semantic projection v1 check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Semantic projection v1 check passed.")
        return 0

    try:
        artifacts = generate(ROOT, source_revision=args.source_revision)
    except ProjectionV1Error as exc:
        print("Semantic projection v1 generation FAILED.")
        print(f"  - {exc}")
        return 1
    (ROOT / PROJECTION_V1_JSON_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (ROOT / PROFILE_V1_JSON_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    print(f"wrote {PROJECTION_V1_JSON_PATH}")
    print(f"wrote {PROFILE_V1_JSON_PATH}")
    print(
        "source revision: "
        f"{artifacts['projection']['binding']['source_revision']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())