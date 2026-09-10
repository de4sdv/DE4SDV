#!/usr/bin/env python3
"""Produce the isolated committed-candidate export with the licensed serializer.

Candidate production path (frozen baseline Section 12, Lane B Increment B):

    exact Git SHA
    -> isolated detached clean checkout/worktree at that SHA
    -> pinned model dependencies synced in that checkout
    -> licensed Syside validation/export run FROM that checkout
    -> distinct candidate export artifact + recorded toolchain identity

Importing one serialized export twice is NOT candidate-production proof; the
export consumed by the candidate API import must come from the isolated
checkout and must be a separate serialization transaction from the ordinary
baseline export.
"""

from __future__ import annotations

import argparse
import hashlib
import datetime
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.candidate import prepare_isolated_checkout  # noqa: E402
from de4sdv.sysml_api.repository import element_id  # noqa: E402

EXPORT_SCHEMA = "de4sdv-sysml-api-baseline-export/v1"


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def _sync_dependencies(checkout: Path) -> None:
    """Sync the pinned model dependencies inside the isolated checkout."""
    _run(["sysand", "sync"], cwd=checkout)


def _run_serializer(checkout: Path, git_commit: str, output: Path) -> None:
    """Run the licensed serializer FROM the isolated checkout.

    Module-level so tests can substitute a fake serializer; the privileged
    workflow always takes this default (the real Syside Automator path).
    """
    _run(
        [
            sys.executable,
            str(checkout / "scripts" / "export_sysml_api_baseline.py"),
            "--git-commit",
            git_commit,
            "--output",
            str(output),
        ],
        cwd=checkout,
    )


def _toolchain_identity(checkout: Path) -> dict[str, object]:
    identity: dict[str, object] = {
        "python": sys.version.split()[0],
        "sysand_lock_sha256": None,
        "sysand_lock_present": False,
        "syside_version": None,
    }
    lock = checkout / "sysand-lock.toml"
    if lock.is_file():
        identity["sysand_lock_present"] = True
        identity["sysand_lock_sha256"] = _sha256_bytes(lock)
    try:
        identity["syside_version"] = importlib.metadata.version("syside")
    except importlib.metadata.PackageNotFoundError:
        identity["syside_version"] = None
    serializer = checkout / "scripts" / "export_sysml_api_baseline.py"
    if serializer.is_file():
        identity["serializer_sha256"] = _sha256_bytes(serializer)
    return identity


def _reuse_existing_checkout(
    worktree: Path, git_commit: str
) -> Path:
    """Validate an already-prepared isolated checkout for a later transaction.

    MC-14 requires two INDEPENDENT serialization transactions of the SAME
    committed source: the checkout is deliberately shared, each transaction
    runs a fresh serializer process against it.
    """
    if not worktree.is_dir():
        raise ValueError(f"worktree {worktree} does not exist")
    head = subprocess.check_output(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != git_commit:
        raise ValueError(
            f"existing worktree HEAD {head} does not match requested {git_commit}"
        )
    return worktree


def prepare_candidate_export(
    repository: Path,
    git_commit: str,
    worktree: Path,
    output: Path,
    identity_path: Path,
    *,
    transaction_label: str = "candidate-1",
    baseline_export: Path | None = None,
    comparison_export: Path | None = None,
    reuse_checkout: bool = False,
    sync_dependencies: bool = True,
) -> dict[str, object]:
    """Run one isolated candidate export transaction and record its identity."""
    if reuse_checkout:
        checkout = _reuse_existing_checkout(worktree, git_commit)
    else:
        checkout = prepare_isolated_checkout(repository, git_commit, worktree)
    if sync_dependencies:
        _sync_dependencies(checkout)
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_serializer(checkout, git_commit, output)
    if not output.is_file():
        raise RuntimeError("candidate serializer produced no export artifact")

    artifact = json.loads(output.read_text(encoding="utf-8"))
    if artifact.get("schema") != EXPORT_SCHEMA:
        raise RuntimeError(
            f"candidate export schema {artifact.get('schema')!r} is not {EXPORT_SCHEMA!r}"
        )
    exported_commit = str(artifact.get("git_commit") or "")
    if exported_commit != git_commit:
        raise RuntimeError(
            f"candidate export declares commit {exported_commit!r}, "
            f"expected {git_commit!r}"
        )
    elements = artifact.get("elements")
    if not isinstance(elements, list) or not elements:
        raise RuntimeError("candidate export contains no elements")
    if not all(element_id(element) for element in elements):
        raise RuntimeError("candidate export contains elements without identity")

    candidate_digest = _sha256_bytes(output)

    def _digest_of(path: Path | None) -> str | None:
        return _sha256_bytes(path) if path is not None and path.is_file() else None

    baseline_digest = _digest_of(baseline_export)
    comparison_digest = _digest_of(comparison_export)
    # Distinctness is reported, not fabricated: a deterministic serializer may
    # legitimately emit identical bytes for the same committed source. What
    # makes this a distinct production transaction is the isolated checkout,
    # the separate serializer process invocation, this transaction identity,
    # and the separate API project/commit it is imported into.
    identity: dict[str, object] = {
        "schema": "de4sdv-candidate-export-identity/v1",
        "transaction_label": transaction_label,
        "transaction_id": hashlib.sha256(
            f"{transaction_label}:{checkout}:{git_commit}:{candidate_digest}".encode()
        ).hexdigest(),
        "generated_at": _utc_now(),
        "git_commit": git_commit,
        "scope": "candidate",
        "isolated_checkout": str(checkout),
        "export_path": str(output),
        "export_sha256": candidate_digest,
        "element_count": len(elements),
        "source_document_count": len(artifact.get("source_manifest") or []),
        "source_checkout_head": subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
        ).strip(),
        "baseline_export_sha256": baseline_digest,
        "candidate_export_equals_baseline_bytes": (
            None if baseline_digest is None else baseline_digest == candidate_digest
        ),
        "comparison_export_sha256": comparison_digest,
        "candidate_export_equals_comparison_bytes": (
            None if comparison_digest is None else comparison_digest == candidate_digest
        ),
        "independent_transaction_basis": [
            "isolated detached checkout at the exact selected SHA",
            "separate licensed serializer process invocation",
            "separate API project/commit for the resulting import",
            "explicit transaction identity recorded here",
        ],
        "toolchain": _toolchain_identity(checkout),
    }
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return identity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--git-commit", required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--baseline-export", type=Path, default=None)
    parser.add_argument("--comparison-export", type=Path, default=None)
    parser.add_argument("--transaction-label", default="candidate-1")
    parser.add_argument(
        "--sync-deps",
        dest="sync_dependencies",
        default=True,
        type=lambda value: value.lower() in {"1", "true", "yes"},
        help="Run `sysand sync` inside the checkout (default: true).",
    )
    parser.add_argument(
        "--reuse-checkout",
        action="store_true",
        help=(
            "Reuse an isolated checkout already prepared at this SHA (second "
            "independent serializer transaction of the same committed source)."
        ),
    )
    args = parser.parse_args()
    identity = prepare_candidate_export(
        args.repository,
        args.git_commit,
        args.worktree,
        args.output,
        args.identity,
        transaction_label=args.transaction_label,
        baseline_export=args.baseline_export,
        comparison_export=args.comparison_export,
        reuse_checkout=args.reuse_checkout,
        sync_dependencies=args.sync_dependencies,
    )
    print(json.dumps(identity, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
