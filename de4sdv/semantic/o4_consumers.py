"""O4 closure preparation: authored-YAML consumer inventory + retirement ledger.

Read-only detection machinery. It never retires, rewrites or bypasses the
authored ontology authority; the authoritative YAML stays in place until the
O4 closure conditions prove every executable consumer is retired or
compatibility-generated. The ledger is authored governance data
(``docs/method-conformance/o4/consumer-ledger.yaml``), never derived from
runtime state, and the checker fails closed on: set drift in either
direction, marker drift per file, unknown roles/statuses, and any ``retired``
row that still shows live consumption markers.

Scanner semantics: every git-tracked file, all file types, full content,
casefolded search — no truncation, no extension filter.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

LEDGER_PATH = "docs/method-conformance/o4/consumer-ledger.yaml"

MARKERS: dict[str, str] = {
    # Filename tokens for the authored ontology YAML (any case).
    "ontology_path_token": "de4sdv-basic-ontology",
    "ontology_path_us_token": "de4sdv_basic_ontology",
    # Directory reference.
    "ontology_dir_token": "approach/framework/ontology",
    # The KernelContract loader symbol and its module path.
    "kernel_contract_symbol": "kernelcontract",
    "kernel_contract_module": "kernel_contract",
    # Symbols in the ontology-machinery tooling.
    "ontology_yaml_symbol": "ontology_yaml",
    "kernel_sync_key": "kernel_sync",
    # The authority dimension value used across governance artifacts.
    "legacy_yaml_authority": "legacy-yaml",
}

ROLES = (
    "authored-authority",
    "runtime-consumer",
    "validation-consumer",
    "gate",
    "governance-machinery",
    "closure-preparation-machinery",
    "test-reference",
    "documentation",
    "model",
    "build",
)

RETIREMENT_STATUSES = ("active", "pending", "retired", "compatibility-generated", "not-applicable")

MIN_TRACKED_FILES = 100


class ConsumerScanError(RuntimeError):
    """The tracked-file scan could not be completed (fail closed)."""


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ConsumerScanError(
            f"git {' '.join(args)} failed: {result.stderr.strip() or 'unknown error'}"
        )
    return result.stdout


def scan_files(root: Path, files: list[str]) -> dict[str, dict]:
    """Case-insensitive full-content marker scan over the given relative files."""
    hits: dict[str, dict] = {}
    for rel in files:
        path = root / rel
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ConsumerScanError(f"tracked file unreadable: {rel}: {exc}") from exc
        lowered = raw.decode("utf-8", errors="replace").casefold()
        lines = lowered.splitlines()
        markers: dict[str, list[int]] = {}
        for marker, token in MARKERS.items():
            token_cf = token.casefold()
            if token_cf in lowered:
                markers[marker] = [
                    idx + 1 for idx, line in enumerate(lines) if token_cf in line
                ]
        if markers:
            hits[rel] = {"markers": markers}
    return hits


def scan_tracked_files(root: Path) -> dict[str, dict]:
    """Scan every git-tracked file of the repository (guarded, fail closed)."""
    listing = _git(root, "ls-files", "-z")
    files = [f for f in listing.split("\0") if f]
    if len(files) < MIN_TRACKED_FILES:
        raise ConsumerScanError(
            f"suspiciously small tracked file set: {len(files)} (expected >= {MIN_TRACKED_FILES})"
        )
    return scan_files(root, files)


def load_ledger(path: Path) -> dict:
    import yaml

    if not path.is_file():
        raise ConsumerScanError(f"consumer ledger missing: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("entries"), dict):
        raise ConsumerScanError(f"consumer ledger malformed: {path}")
    return document


def check_ledger(root: Path, ledger: dict, scan: dict[str, dict]) -> list[str]:
    """Fail-closed ledger validation against a live scan."""
    errors: list[str] = []
    entries = ledger.get("entries")
    if not isinstance(entries, dict):
        return [f"{LEDGER_PATH}: ledger has no entries mapping"]

    identity = ledger.get("identity")
    if identity and identity != LEDGER_PATH:
        errors.append(f"{LEDGER_PATH}: ledger identity does not name this path: {identity!r}")

    for rel in sorted(set(scan) - set(entries)):
        errors.append(f"{LEDGER_PATH}: {rel} consumes the authored authority but is missing from the ledger")
    for rel in sorted(set(entries) - set(scan)):
        row = entries[rel]
        status = row.get("retirement_status") if isinstance(row, dict) else None
        if status == "retired":
            continue  # a retired consumer must no longer show live markers
        errors.append(f"{LEDGER_PATH}: {rel} has no live scan hit (stale ledger row)")

    for rel in sorted(set(entries) & set(scan)):
        row = entries[rel]
        if not isinstance(row, dict):
            errors.append(f"{LEDGER_PATH}: {rel}: entry must be a mapping")
            continue
        role = row.get("role")
        if role not in ROLES:
            errors.append(f"{LEDGER_PATH}: {rel}: unknown role {role!r}")
        status = row.get("retirement_status")
        if status not in RETIREMENT_STATUSES:
            errors.append(f"{LEDGER_PATH}: {rel}: unknown retirement_status {status!r}")
        if status == "retired":
            errors.append(
                f"{LEDGER_PATH}: {rel}: retired consumer still consumes the authored authority"
            )
        recorded = row.get("markers")
        live = sorted(scan[rel]["markers"])
        if not isinstance(recorded, list) or sorted(recorded) != live:
            errors.append(
                f"{LEDGER_PATH}: {rel}: marker set drifted (recorded {recorded!r}, live {live!r})"
            )
    return errors


def load_and_check(root: Path) -> list[str]:
    """Convenience entry point used by the repository gate."""
    ledger = load_ledger(root / LEDGER_PATH)
    scan = scan_tracked_files(root)
    return check_ledger(root, ledger, scan)