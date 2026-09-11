#!/usr/bin/env python3
"""Generate (or check) the O1 Semantic Authority Inventory.

Canonical artifacts:

- ``docs/method-conformance/o1/semantic-authority-inventory.json``
  (machine-readable canonical inventory; Layer A observed facts joined with
  Layer B reviewed decisions, provenance preserved);
- ``docs/method-conformance/o1/authority-inventory.md``
  (human-readable review table derived from the same canonical data).

Determinism: identical inputs produce byte-identical output. The recorded Git
revision and base are explicit inputs (``--revision`` / ``--base-sha``);
generation defaults them to the current checkout, and the committed-artifact
check re-supplies the recorded values so byte comparison isolates input drift.

Offline and read-only: no network, no privileged ingestion, no runtime
semantic change. This is a CI/governance check; the runtime never reads the
generated inventory.

Usage:

    python scripts/generate_semantic_authority_inventory.py            # write
    python scripts/generate_semantic_authority_inventory.py --check    # verify
"""

from __future__ import annotations

import argparse
import json
import subprocess
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
)


def resolve_git_revision(root: Path) -> str:
    """Full HEAD revision of the checkout being generated from."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise InventoryError(
            "cannot resolve the Git revision (git rev-parse HEAD failed); "
            "pass --revision explicitly"
        )
    return result.stdout.strip()


def resolve_base_sha(root: Path) -> str:
    """Merge-base of the checkout with origin/main (or main)."""
    for reference in ("origin/main", "main"):
        result = subprocess.run(
            ["git", "merge-base", reference, "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise InventoryError(
        "cannot resolve the base revision (no origin/main or main merge-base); "
        "pass --base-sha explicitly"
    )


def generate(
    root: Path, *, revision: str | None = None, base_sha: str | None = None
) -> dict:
    """Build the canonical inventory with resolved binding inputs."""
    if revision is None:
        revision = resolve_git_revision(root)
    if base_sha is None:
        base_sha = resolve_base_sha(root)
    return build_inventory(root, revision=revision, base_sha=base_sha)


def run_check_errors(root: Path | None = None) -> list[str]:
    """Check that the committed artifacts equal regeneration from inputs.

    Regenerates with the binding inputs recorded in the committed artifact and
    compares bytes for both the canonical JSON and the derived review table.
    Any uncommitted input change, coverage failure, or hand edit of a
    generated file is an error.
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
        revision = committed["binding"]["git_revision"]
        base_sha = committed["binding"]["base_sha"]
    except (KeyError, ValueError) as exc:
        return [
            f"{INVENTORY_JSON_PATH}: cannot read binding inputs for "
            f"regeneration: {exc}"
        ]
    try:
        inventory = generate(root, revision=revision, base_sha=base_sha)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed artifacts equal regeneration (no writes)",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="explicit Git revision to record (default: HEAD)",
    )
    parser.add_argument(
        "--base-sha",
        default=None,
        help="explicit base revision to record (default: merge-base with main)",
    )
    args = parser.parse_args(argv)

    if args.check:
        errors = run_check_errors()
        if errors:
            print("Semantic authority inventory check FAILED.")
            for error in errors:
                print(f"  - {error}")
            return 1
        print("Semantic authority inventory check passed.")
        return 0

    try:
        inventory = generate(
            ROOT, revision=args.revision, base_sha=args.base_sha
        )
    except InventoryError as exc:
        print("Semantic authority inventory generation FAILED.")
        print(f"  - {exc}")
        return 1
    (ROOT / INVENTORY_JSON_PATH).write_text(
        canonical_json(inventory), encoding="utf-8"
    )
    (ROOT / INVENTORY_MD_PATH).write_text(
        render_markdown(inventory), encoding="utf-8"
    )
    print(f"wrote {INVENTORY_JSON_PATH}")
    print(f"wrote {INVENTORY_MD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
