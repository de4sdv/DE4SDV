#!/usr/bin/env python3
"""Verify the frozen records the runtime still serves (read-only, runtime-inert).

The frozen records are the historical Semantic Projection and API
Representation Profile records (v1 to v1.2) that the model-built kernel
contract reads as its frozen layer. They are never regenerated.

The frozen-records manifest must equal its deterministic rendering from the
recorded ancestor ``frozen_at_revision``. Directory membership and every
frozen file's bytes must match that manifest. Historical bindings are checked
against their own source revisions, never against current inputs; ``extends``
references must name a frozen record at its frozen digest.

The records keep the paths they had when they were frozen inside their own
``extends`` blocks; ``HISTORICAL_DIRECTORY`` maps those paths to the current
directory. Records frozen by the same decision that the runtime no longer
serves are archived at the ``release-2026-10-11`` tag.

Live projection/profile freshness is a separate current-source comparison in
each generator's check mode, aggregated by ``scripts/check_repo.py``. This
verifier neither discovers nor validates live generated outputs.

Reports are sorted ``{artifact, ok, errors[]}`` entries. The CLI exits nonzero
on any historical failure; ``--json`` emits the complete report.
``--render-frozen-manifest <revision>`` is a read-only review aid. Historical
records must never be regenerated or repaired to match current source.
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

FROZEN_MANIFEST_PATH = "de4sdv/semantic/contract-data/frozen-records.json"
FROZEN_SCHEMA = "de4sdv.frozen-records/v2"
#: The directory that holds exactly the frozen records.
FROZEN_DIRECTORY = "de4sdv/semantic/contract-data/frozen-records"
FROZEN_DIRECTORIES = (FROZEN_DIRECTORY,)
#: Where the records lived at ``frozen_at_revision``. Their own ``extends``
#: blocks keep naming these paths.
HISTORICAL_DIRECTORY = "docs/method-conformance/o2"
#: The records the runtime still serves (the frozen layer of
#: ``de4sdv/semantic/model_contract.py``).
FROZEN_RECORD_NAMES = (
    "api-representation-profile-v1.1.json",
    "api-representation-profile-v1.2.json",
    "api-representation-profile-v1.json",
    "semantic-projection-v1.1.json",
    "semantic-projection-v1.2.json",
    "semantic-projection-v1.json",
)
ARCHIVE_TAG = "release-2026-10-11"
#: The owner decision that froze the records, quoted as recorded. The frozen
#: manifest embeds this block byte for byte (``decision``), so its wording,
#: decision codes included, never changes.
FROZEN_DECISION = {
    "owner_decisions": "Q7 and D10 (Orkun, 2026-10-07)",
    "statement": (
        "Freeze the historical O1, O2 and O3 records (the whole o1/, o2/ and "
        "o3/ directories); do not regenerate them."
    ),
    "record": (
        "https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/"
        "docs/method-conformance/o4/owner-decisions-2026-10.md"
    ),
}
LIVE_CONSUMER = "frozen layer of the model-built kernel contract (read-only data)"
_RECORD_KEYS = ("path", "sha256", "kind", "binding_source_revision", "live_consumer")

_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_BARE_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _canonical_digest(value: Any) -> Any:
    """Canonical ``sha256:<64-hex>`` for a bare-hex digest; anything else as-is.

    Recorded digests appear in both forms; both must be able to match, and
    anything that is neither form is left untouched so the mismatch is
    reported against the recorded value itself.
    """
    text = str(value)
    if _BARE_SHA256.match(text):
        return "sha256:" + text
    return value


def _is_frozen_path(relative: str) -> bool:
    return any(
        relative == directory or relative.startswith(directory + "/")
        for directory in FROZEN_DIRECTORIES
    )


def _current_path(relative: Any) -> Any:
    """The current path of a record named by its path at ``frozen_at_revision``."""
    prefix = HISTORICAL_DIRECTORY + "/"
    if isinstance(relative, str) and relative.startswith(prefix):
        return FROZEN_DIRECTORY + "/" + relative[len(prefix):]
    return relative


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

    Every field is derived from the historical bytes (sha256, kind, binding
    source revision) or from the reviewed constants in this module, so the
    committed manifest can be re-derived and compared byte-for-byte. Each
    record is read at ``revision`` under ``HISTORICAL_DIRECTORY`` and listed
    under its current path.
    """
    records = []
    for name in sorted(FROZEN_RECORD_NAMES):
        historical = f"{HISTORICAL_DIRECTORY}/{name}"
        data = _git_bytes(root, revision, historical)
        if data is None:
            raise ValueError(f"{historical} is unreadable at {revision}")
        binding_revision = None
        if name.endswith(".json"):
            try:
                document = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                document = None
            if isinstance(document, dict) and isinstance(document.get("binding"), dict):
                binding_revision = document["binding"].get("source_revision")
        records.append({
            "path": f"{FROZEN_DIRECTORY}/{name}",
            "sha256": _bytes_digest(data),
            "kind": _record_kind(name, data),
            "binding_source_revision": binding_revision,
            "live_consumer": LIVE_CONSUMER,
        })
    return {
        "schema": FROZEN_SCHEMA,
        "note": (
            "Frozen historical records the runtime still serves. Never "
            "regenerated; never compared with the live tree's inputs. Bindings "
            "are verified at their own source revisions by "
            "scripts/verify_generated_chain.py (frozen lane), which "
            "scripts/check_repo.py runs. Not revision-bound evidence itself: "
            "no binding block. The other records frozen by the same decision "
            f"are archived at the {ARCHIVE_TAG} tag."
        ),
        "decision": dict(FROZEN_DECISION),
        "frozen_at_revision": revision,
        "historical_directory": HISTORICAL_DIRECTORY,
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
    referenced = _current_path(extends.get("artifact"))
    if referenced not in digests:
        return [f"extends.artifact {extends.get('artifact')!r} must be a frozen record"]
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
            f"{list(FROZEN_DIRECTORIES)}"
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
        entries.append({"artifact": relative, "ok": not record_errors,
                        "errors": record_errors})
    return entries


def frozen_record_errors(root: Path) -> list[str]:
    """Flat error list of the frozen lane (used by ``scripts/check_repo.py``)."""
    return [
        f"{entry['artifact']}: {error}"
        for entry in _frozen_lane_entries(Path(root))
        for error in entry["errors"]
    ]


def verify_generated_chain(
    root: Path, *, include_passing: bool = False
) -> list[dict[str, Any]]:
    """Report historical failures, or the complete nonempty historical inventory."""
    entries = sorted(_frozen_lane_entries(Path(root)), key=lambda entry: entry["artifact"])
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
        print("Historical-record verification FAILED.")
        for entry in failing:
            for error in entry["errors"]:
                print(f"  - {entry['artifact']}: {error}")
        print(
            f"{len(failing)} of {len(report)} artifact(s) failed; "
            "restore the recorded historical bytes; never regenerate them "
            "against current inputs."
        )
        return 1
    print("Historical-record verification passed.")
    print(f"artifacts checked: {len(report)}")
    for entry in report:
        print(f"  OK  {entry['artifact']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
