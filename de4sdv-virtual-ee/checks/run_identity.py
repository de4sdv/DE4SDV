#!/usr/bin/env python3
"""Bind a run to the committed bytes that executed it.

    capture --scope DIR [--extra LABEL=PATH ...] --out FILE
        Record the full Git head, tree and scope tree, require the scope to be
        clean, and inventory every tracked file in it by content (SHA-256 and
        the Git blob id recomputed from the bytes on disk, so an edit hidden by
        assume-unchanged or skip-worktree still counts). The harness, vehicle
        configuration and lock are named with their digests; files outside the
        repository that the run executes (the UDS tool) are hashed via --extra.
        Exit 1, writing nothing, when the scope is gitless, dirty, or a
        required input is not committed.

    verify --identity FILE [--out FILE]
        Capture again with the same scope and extras and compare. Exit 1 when
        anything that could affect the run changed between start and end.

    check-archive [--repo DIR] ARCHIVE
        Accept an archive only if its manifest names a full head and carries
        the identity record it hashes, verified after the run. Older archives
        fail and are labelled historical; with --repo, the recorded revision is
        also compared to the repository (harness present, lock bytes equal).

Excluded from the scope, because they are what a run produces, not what it
runs: results/ (generated evidence), vehicle/ota-store/ (runtime state, also
outside the package digest), and Python/pytest caches. A copied .git-sha is
never accepted as provenance: there is nothing to check it against.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "de4sdv-virtual-ee/run-identity/1"
EXCLUDED = ["results/", "vehicle/ota-store/", "**/__pycache__/", "**/.pytest_cache/", "*.pyc"]
NAMED = {
    "harness": [
        "checks/run_demo.sh",
        "checks/demo_measure.py",
        "checks/measure_client.py",
        "checks/run_backbone.sh",
        "checks/backbone_measure.py",
        "checks/run_identity.py",
    ],
    "config": [
        "vehicle/vehicle.yaml",
        "vehicle/parts.yaml",
        "vehicle/main.yaml",
        "vehicle/vxp.yaml",
        "vehicle/.vxpignore",
    ],
    "lock": ["vehicle/vxp.lock"],
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


class IdentityError(Exception):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(top: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(top), *args], capture_output=True)
    if check and proc.returncode != 0:
        raise IdentityError(f"git {' '.join(args)} failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc


def excluded(rel: str) -> bool:
    """Generated evidence, runtime state and caches: produced by runs, not run."""
    parts = rel.split("/")
    return (
        rel.startswith(("results/", "vehicle/ota-store/"))
        or any(p in ("__pycache__", ".pytest_cache") for p in parts[:-1])
        or rel.endswith(".pyc")
    )


def locate(scope: Path) -> tuple[Path, str]:
    scope = scope.resolve()
    proc = subprocess.run(["git", "-C", str(scope), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        hint = " (a copied .git-sha is not execution provenance)" if (scope / ".git-sha").exists() else ""
        raise IdentityError(f"{scope} is not a git checkout{hint}; .git-sha/.git-branch copies cannot be verified")
    top = Path(proc.stdout.strip()).resolve()
    rel = scope.relative_to(top).as_posix()
    return top, "" if rel == "." else rel


def capture(scope_dir: Path, extras: dict[str, str]) -> dict:
    top, rel = locate(scope_dir)
    prefix = f"{rel}/" if rel else ""
    head = git(top, "rev-parse", "--verify", "HEAD^{commit}").stdout.decode().strip()
    if not FULL_SHA.match(head):
        raise IdentityError(f"HEAD {head!r} is not a full sha1 commit id")
    tree = git(top, "rev-parse", "HEAD^{tree}").stdout.decode().strip()
    scope_tree = git(top, "rev-parse", f"HEAD:{rel}" if rel else "HEAD^{tree}").stdout.decode().strip()
    branch = git(top, "symbolic-ref", "-q", "--short", "HEAD", check=False).stdout.decode().strip() or None

    problems: list[str] = []
    status = git(top, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching",
                 "--", rel or ".").stdout.decode(errors="replace")
    entries = status.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            i += 1  # the rename source follows
        inner = path[len(prefix):] if path.startswith(prefix) else path
        if excluded(inner):
            continue
        problems.append(f"dirty: {inner} ({code.strip() or '??'})")

    inventory = []
    listing = git(top, "ls-tree", "-r", "-z", "--full-tree", "HEAD", "--", rel or ".").stdout.decode()
    for item in filter(None, listing.split("\0")):
        meta, path = item.split("\t", 1)
        mode, kind, blob = meta.split()
        inner = path[len(prefix):]
        if kind != "blob" or excluded(inner):
            continue
        disk = top / path
        if mode == "120000":
            data = os.readlink(disk).encode() if disk.is_symlink() else None
        else:
            data = disk.read_bytes() if disk.is_file() and not disk.is_symlink() else None
        if data is None:
            problems.append(f"dirty: {inner} (missing on disk)")
            continue
        on_disk_blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
        if on_disk_blob != blob:
            problems.append(f"dirty: {inner} (bytes differ from the committed blob)")
        if mode == "100755" and not os.access(disk, os.X_OK):
            problems.append(f"dirty: {inner} (committed executable, not executable on disk)")
        inventory.append({"path": inner, "mode": mode, "git_blob": blob, "sha256": sha256_bytes(data)})
    inventory.sort(key=lambda e: e["path"])
    by_path = {e["path"]: e["sha256"] for e in inventory}

    named: dict[str, dict[str, str]] = {}
    for group, paths in NAMED.items():
        named[group] = {}
        for path in paths:
            if path not in by_path:
                problems.append(f"required input not committed: {path}")
            else:
                named[group][path] = by_path[path]

    extra = {}
    for label, path in extras.items():
        p = Path(path)
        if not p.is_file():
            problems.append(f"external input {label} missing: {path}")
        else:
            extra[label] = {"path": path, "sha256": sha256_file(p)}

    if problems:
        raise IdentityError("; ".join(problems))
    listing_text = "".join(f"{e['path']}\0{e['sha256']}\n" for e in inventory)
    return {
        "schema": SCHEMA,
        "captured_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": str(top),
        "scope": rel,
        "git": {"head": head, "tree": tree, "scope_tree": scope_tree, "branch": branch},
        "clean": True,
        "excluded": EXCLUDED,
        "named": named,
        "extra": extra,
        "inventory_sha256": sha256_bytes(listing_text.encode()),
        "inventory": inventory,
    }


def compare(before: dict, after: dict) -> list[str]:
    diffs = []
    for key in ("head", "tree", "scope_tree"):
        if before["git"][key] != after["git"][key]:
            diffs.append(f"git {key} {before['git'][key]} -> {after['git'][key]}")
    old = {e["path"]: e["sha256"] for e in before["inventory"]}
    new = {e["path"]: e["sha256"] for e in after["inventory"]}
    for path in sorted(old.keys() | new.keys()):
        if old.get(path) != new.get(path):
            diffs.append(f"input changed: {path}")
    for label in sorted(before["extra"].keys() | after["extra"].keys()):
        if before["extra"].get(label) != after["extra"].get(label):
            diffs.append(f"external input changed: {label}")
    return diffs


def parse_extras(values: list[str]) -> dict[str, str]:
    extras = {}
    for value in values or []:
        label, sep, path = value.partition("=")
        if not sep or not label or not path:
            raise IdentityError(f"--extra expects LABEL=PATH, got {value!r}")
        extras[label] = path
    return extras


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def cmd_capture(args) -> int:
    ident = capture(Path(args.scope), parse_extras(args.extra))
    write_json(Path(args.out), ident)
    print(f"identity: {ident['git']['head']} scope={ident['scope']} inventory={ident['inventory_sha256'][:12]}")
    return 0


def cmd_verify(args) -> int:
    path = Path(args.identity)
    before = json.loads(path.read_text())
    top = Path(before["repository"])
    scope = top / before["scope"] if before["scope"] else top
    result = {"before_sha256": sha256_file(path), "matches": False, "differences": []}
    try:
        after = capture(scope, {k: v["path"] for k, v in before["extra"].items()})
    except IdentityError as exc:
        result["differences"] = [str(exc)]
    else:
        result["differences"] = compare(before, after)
        result["after"] = {k: after[k] for k in ("captured_utc", "git", "inventory_sha256", "named", "extra")}
        result["matches"] = not result["differences"]
    if args.out:
        write_json(Path(args.out), result)
    if not result["matches"]:
        raise IdentityError("inputs changed during the run: " + "; ".join(result["differences"]))
    print(f"identity verified after the run: {before['git']['head']}")
    return 0


def cmd_check_archive(args) -> int:
    archive = Path(args.archive)
    problems: list[str] = []
    manifest_path = archive / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    if not manifest:
        problems.append("manifest.json missing")
    recorded = str(manifest.get("git_head") or manifest.get("git_sha") or "")
    if not FULL_SHA.match(recorded):
        problems.append(f"git_sha {recorded or 'absent'!r} is not a full commit id")
    before_path, after_path = archive / "identity-before.json", archive / "identity-after.json"
    if not before_path.is_file():
        problems.append("identity-before.json missing (no inventory of what ran)")
    else:
        if manifest.get("identity_sha256") != sha256_file(before_path):
            problems.append("identity_sha256 in the manifest does not match identity-before.json")
        before = json.loads(before_path.read_text())
        if before.get("git", {}).get("head") != recorded:
            problems.append("identity-before.json names a different head than the manifest")
        if not after_path.is_file():
            problems.append("identity-after.json missing (inputs not re-verified after the run)")
        else:
            after = json.loads(after_path.read_text())
            if after.get("matches") is not True or after.get("before_sha256") != sha256_file(before_path):
                problems.append("identity-after.json does not confirm the inputs were unchanged")
    if args.repo and recorded:
        problems += check_against_repo(Path(args.repo), archive, recorded, manifest, before_path)
    if problems:
        print(f"{archive.name}: historical/pre-commit run, not exact-commit evidence: " + "; ".join(problems),
              file=sys.stderr)
        return 1
    print(f"{archive.name}: identity complete at {recorded}")
    return 0


def check_against_repo(repo: Path, archive: Path, recorded: str, manifest: dict, before_path: Path) -> list[str]:
    problems = []
    top, _ = locate(repo)
    proc = git(top, "rev-parse", "--verify", "-q", f"{recorded}^{{commit}}", check=False)
    if proc.returncode != 0:
        return [f"{recorded} is not a commit of {top}"]
    commit = proc.stdout.decode().strip()
    scope_abs = archive.resolve().parent.parent
    rel = scope_abs.relative_to(top).as_posix() if scope_abs.is_relative_to(top) else "de4sdv-virtual-ee"

    def committed(path: str) -> bytes | None:
        shown = git(top, "show", f"{commit}:{rel}/{path}", check=False)
        return shown.stdout if shown.returncode == 0 else None

    for path in ("checks/run_demo.sh", "checks/run_backbone.sh"):
        if committed(path) is None:
            problems.append(f"{path} absent at {recorded}")
    lock = committed("vehicle/vxp.lock")
    if manifest.get("lock_sha256") and lock is not None and sha256_bytes(lock) != manifest["lock_sha256"]:
        problems.append(f"lock_sha256 {manifest['lock_sha256'][:12]} differs from the lock committed at "
                        f"{recorded} ({sha256_bytes(lock)[:12]})")
    if before_path.is_file():
        before = json.loads(before_path.read_text())
        for group in before.get("named", {}).values():
            for path, digest in group.items():
                data = committed(path)
                if data is None or sha256_bytes(data) != digest:
                    problems.append(f"{path} recorded digest differs from {recorded}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--scope", required=True)
    c.add_argument("--extra", action="append", default=[], metavar="LABEL=PATH")
    c.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--identity", required=True)
    v.add_argument("--out")
    a = sub.add_parser("check-archive")
    a.add_argument("--repo")
    a.add_argument("archive")
    args = ap.parse_args()
    try:
        return {"capture": cmd_capture, "verify": cmd_verify, "check-archive": cmd_check_archive}[args.cmd](args)
    except IdentityError as exc:
        print(f"[identity] REJECTED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
