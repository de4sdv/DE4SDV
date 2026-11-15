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
        fail and are labelled historical. The identity record must have the
        exact closed shape capture writes; with --repo the complete expected
        identity (inventory, named groups, tree, scope tree) is rebuilt from
        Git at the recorded commit and must match exactly, so a record that
        is only coherent with itself is rejected. Without --repo nothing is
        checked against source: exit 1, labelled metadata-only.

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
SHA256 = re.compile(r"^[0-9a-f]{64}$")
UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
MODES = ("100644", "100755")  # symlinks (120000) are never runtime inputs: their target is not bytes we hash
IDENTITY_KEYS = {"schema", "captured_utc", "repository", "scope", "git", "clean", "excluded", "named", "extra",
                 "inventory_sha256", "inventory"}
AFTER_KEYS = {"before_sha256", "matches", "differences", "after"}
AFTER_IDENTITY_KEYS = ("captured_utc", "git", "inventory_sha256", "named", "extra")


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
        if mode not in MODES or disk.is_symlink():
            problems.append(f"symlink or non-file runtime input: {inner} (mode {mode})")
            continue
        data = disk.read_bytes() if disk.is_file() else None
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
        "inventory_sha256": inventory_digest(inventory),
        "inventory": inventory,
    }


def inventory_digest(inventory: list[dict]) -> str:
    return sha256_bytes("".join(f"{e['path']}\0{e['sha256']}\n" for e in inventory).encode())


def compare(before: dict, after: dict) -> list[str]:
    diffs = []
    for key in ("head", "tree", "scope_tree"):
        if before["git"][key] != after["git"][key]:
            diffs.append(f"git {key} {before['git'][key]} -> {after['git'][key]}")
    old = {e["path"]: e for e in before["inventory"]}
    new = {e["path"]: e for e in after["inventory"]}
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
    before = load_json(path)
    shape = identity_shape_problems(before)
    if shape:
        raise IdentityError("identity record malformed: " + "; ".join(shape))
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


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise IdentityError(f"{path.name} unreadable: {exc}") from None


def _is_str(v) -> bool:
    return isinstance(v, str)


def identity_shape_problems(ident) -> list[str]:
    """The closed shape capture writes; anything else is not an identity record."""
    if not isinstance(ident, dict):
        return ["identity record is not an object"]
    p = []
    if set(ident) != IDENTITY_KEYS:
        p.append(f"identity keys {sorted(set(ident) ^ IDENTITY_KEYS)} missing or unexpected")
        return p
    if ident["schema"] != SCHEMA:
        p.append(f"schema {ident['schema']!r} is not {SCHEMA}")
    if not (_is_str(ident["captured_utc"]) and UTC.match(ident["captured_utc"])):
        p.append("captured_utc malformed")
    if not _is_str(ident["repository"]) or not ident["repository"]:
        p.append("repository malformed")
    scope = ident["scope"]
    if not _is_str(scope) or scope.startswith("/") or ".." in scope.split("/") or scope.endswith("/") \
            or "\\" in scope or "\0" in scope:
        p.append("scope malformed")
    g = ident["git"]
    if not isinstance(g, dict) or set(g) != {"head", "tree", "scope_tree", "branch"}:
        p.append("git record malformed")
    else:
        for key in ("head", "tree", "scope_tree"):
            if not (_is_str(g[key]) and FULL_SHA.match(g[key])):
                p.append(f"git {key} is not a full object id")
        if g["branch"] is not None and not _is_str(g["branch"]):
            p.append("git branch malformed")
    if ident["clean"] is not True:
        p.append("clean is not true")
    if ident["excluded"] != EXCLUDED or not isinstance(ident["excluded"], list):
        p.append("excluded selector is not schema 1")
    inv = ident["inventory"]
    entries_ok = isinstance(inv, list) and all(
        isinstance(e, dict) and set(e) == {"path", "mode", "git_blob", "sha256"}
        and _is_str(e["path"]) and e["path"] and _is_str(e["mode"]) and _is_str(e["git_blob"])
        and FULL_SHA.match(e["git_blob"]) and _is_str(e["sha256"]) and SHA256.match(e["sha256"])
        for e in inv)
    if not entries_ok:
        p.append("inventory entries malformed")
        inv = []
    else:
        paths = [e["path"] for e in inv]
        if len(set(paths)) != len(paths):
            p.append("inventory has duplicate paths")
        if paths != sorted(paths):
            p.append("inventory is not sorted")
        for e in inv:
            if e["mode"] not in MODES:
                p.append(f"inventory {e['path']} mode {e['mode']} is not a regular file")
            if excluded(e["path"]):
                p.append(f"inventory lists excluded path {e['path']}")
        if not (_is_str(ident["inventory_sha256"]) and ident["inventory_sha256"] == inventory_digest(inv)):
            p.append("inventory_sha256 does not match the inventory")
    by_path = {e["path"]: e["sha256"] for e in inv}
    named = ident["named"]
    if not isinstance(named, dict) or set(named) != set(NAMED):
        p.append("named groups are not " + ", ".join(NAMED))
    else:
        for group, paths in NAMED.items():
            expected = {path: by_path.get(path) for path in paths}
            if named[group] != expected or None in expected.values():
                p.append(f"named group {group} does not name its inputs with their inventory digests")
    extra = ident["extra"]
    if not isinstance(extra, dict) or not all(
            _is_str(k) and k and isinstance(v, dict) and set(v) == {"path", "sha256"} and _is_str(v["path"])
            and _is_str(v["sha256"]) and SHA256.match(v["sha256"]) for k, v in extra.items()):
        p.append("extra inputs malformed")
    return p


def after_problems(after, before: dict, before_sha: str) -> list[str]:
    if not isinstance(after, dict) or set(after) != AFTER_KEYS:
        return ["identity-after.json is not a complete verify record"]
    p = []
    if after["matches"] is not True or after["differences"] != [] or after["before_sha256"] != before_sha:
        p.append("identity-after.json does not confirm the inputs were unchanged")
    rec = after["after"]
    if not isinstance(rec, dict) or set(rec) != set(AFTER_IDENTITY_KEYS):
        p.append("identity-after.json carries no after identity")
    else:
        if not (_is_str(rec["captured_utc"]) and UTC.match(rec["captured_utc"])):
            p.append("after captured_utc malformed")
        for key in AFTER_IDENTITY_KEYS[1:]:
            if rec[key] != before.get(key):
                p.append(f"after {key} differs from identity-before.json")
    return p


def cmd_check_archive(args) -> int:
    archive = Path(args.archive)
    problems: list[str] = []
    manifest_path = archive / "manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    if not isinstance(manifest, dict):
        problems.append("manifest.json is not an object")
        manifest = {}
    if not manifest:
        problems.append("manifest.json missing")
    recorded = manifest.get("git_head") or manifest.get("git_sha") or ""
    if not _is_str(recorded):
        problems.append("git_sha malformed")
        recorded = ""
    elif not FULL_SHA.match(recorded):
        # a short id still names a revision the repository check can label; it is never accepted
        problems.append(f"git_sha {recorded or 'absent'!r} is not a full commit id")
    for key in ("git_head", "git_sha"):
        if key in manifest and manifest[key] != recorded:
            problems.append(f"manifest {key} disagrees with the recorded head")
    before_path, after_path = archive / "identity-before.json", archive / "identity-after.json"
    before = None
    if not before_path.is_file() or before_path.is_symlink():
        problems.append("identity-before.json missing (no inventory of what ran)")
    else:
        before_sha = sha256_file(before_path)
        if manifest.get("identity_sha256") != before_sha:
            problems.append("identity_sha256 in the manifest does not match identity-before.json")
        before = load_json(before_path)
        shape = identity_shape_problems(before)
        if shape:
            problems += [f"identity-before.json: {x}" for x in shape]
            before = None
        else:
            if before["git"]["head"] != recorded:
                problems.append("identity-before.json names a different head than the manifest")
            if "git_tree" in manifest and manifest["git_tree"] != before["git"]["tree"]:
                problems.append("manifest git_tree disagrees with identity-before.json")
        if not after_path.is_file() or after_path.is_symlink():
            problems.append("identity-after.json missing (inputs not re-verified after the run)")
        elif before is not None:
            problems += after_problems(load_json(after_path), before, before_sha)
    if args.repo and recorded:
        problems += check_against_repo(Path(args.repo), archive, recorded, manifest, before)
    if problems:
        print(f"{archive.name}: historical/pre-commit run, not exact-commit evidence: " + "; ".join(problems),
              file=sys.stderr)
        return 1
    if not args.repo:
        print(f"{archive.name}: metadata consistent at {recorded}, source provenance NOT verified "
              "(unverified metadata integrity only; pass --repo to rebuild the identity from Git)", file=sys.stderr)
        return 1
    print(f"{archive.name}: identity complete at {recorded}")
    return 0


def expected_identity(top: Path, commit: str, rel: str) -> tuple[dict, list[str]]:
    """Rebuild tree, scope tree, inventory and named groups from Git at commit (selector schema 1)."""
    problems = []
    prefix = f"{rel}/" if rel else ""
    tree = git(top, "rev-parse", f"{commit}^{{tree}}").stdout.decode().strip()
    proc = git(top, "rev-parse", "--verify", "-q", f"{commit}:{rel}" if rel else f"{commit}^{{tree}}", check=False)
    scope_tree = proc.stdout.decode().strip() if proc.returncode == 0 else None
    if scope_tree is None:
        problems.append(f"scope {rel!r} absent at {commit}")
        return {"tree": tree, "scope_tree": None, "inventory": [], "named": {}}, problems
    listing = git(top, "ls-tree", "-r", "-z", "--full-tree", commit, "--", rel or ".").stdout.decode()
    wanted = []
    for item in filter(None, listing.split("\0")):
        meta, path = item.split("\t", 1)
        mode, kind, blob = meta.split()
        inner = path[len(prefix):]
        if kind != "blob" or excluded(inner):
            continue
        if mode not in MODES:
            problems.append(f"symlink or non-file runtime input at {commit}: {inner} (mode {mode})")
        wanted.append((inner, mode, blob))
    batch = subprocess.run(["git", "-C", str(top), "cat-file", "--batch"], capture_output=True,
                           input="".join(f"{b}\n" for _, _, b in wanted).encode())
    if batch.returncode != 0:
        raise IdentityError("git cat-file --batch failed")
    out, pos, inventory = batch.stdout, 0, []
    for inner, mode, blob in wanted:
        nl = out.index(b"\n", pos)
        size = int(out[pos:nl].split()[2])
        data = out[nl + 1:nl + 1 + size]
        pos = nl + 1 + size + 1
        inventory.append({"path": inner, "mode": mode, "git_blob": blob, "sha256": sha256_bytes(data)})
    inventory.sort(key=lambda e: e["path"])
    by_path = {e["path"]: e["sha256"] for e in inventory}
    named = {group: {p: by_path[p] for p in paths if p in by_path} for group, paths in NAMED.items()}
    for paths in NAMED.values():
        problems += [f"required input {p} not committed at {commit}" for p in paths if p not in by_path]
    return {"tree": tree, "scope_tree": scope_tree, "inventory": inventory, "named": named}, problems


def check_against_repo(repo: Path, archive: Path, recorded: str, manifest: dict, before: dict | None) -> list[str]:
    problems = []
    top, _ = locate(repo)
    proc = git(top, "rev-parse", "--verify", "-q", f"{recorded}^{{commit}}", check=False)
    if proc.returncode != 0:
        return [f"{recorded} is not a commit of {top}"]
    commit = proc.stdout.decode().strip()
    if before is not None:
        rel = before["scope"]
    else:
        scope_abs = archive.resolve().parent.parent
        rel = scope_abs.relative_to(top).as_posix() if scope_abs.is_relative_to(top) else "de4sdv-virtual-ee"
        rel = "" if rel == "." else rel

    def committed(path: str) -> bytes | None:
        shown = git(top, "show", f"{commit}:{rel + '/' if rel else ''}{path}", check=False)
        return shown.stdout if shown.returncode == 0 else None

    for path in ("checks/run_demo.sh", "checks/run_backbone.sh"):
        if committed(path) is None:
            problems.append(f"{path} absent at {recorded}")
    lock = committed("vehicle/vxp.lock")
    if manifest.get("lock_sha256") and lock is not None and sha256_bytes(lock) != manifest["lock_sha256"]:
        problems.append(f"lock_sha256 {str(manifest['lock_sha256'])[:12]} differs from the lock committed at "
                        f"{recorded} ({sha256_bytes(lock)[:12]})")
    if before is None:
        return problems
    expected, missing = expected_identity(top, commit, rel)
    problems += missing
    for key in ("tree", "scope_tree"):
        if before["git"][key] != expected[key]:
            problems.append(f"git {key} {before['git'][key]} is not the {key} of {recorded}")
    have = {e["path"]: e for e in before["inventory"]}
    want = {e["path"]: e for e in expected["inventory"]}
    for path in sorted(want.keys() - have.keys()):
        problems.append(f"inventory omits {path} committed at {recorded}")
    for path in sorted(have.keys() - want.keys()):
        problems.append(f"inventory lists {path}, not a runtime input at {recorded}")
    for path in sorted(have.keys() & want.keys()):
        for field in ("mode", "git_blob", "sha256"):
            if have[path][field] != want[path][field]:
                problems.append(f"{path} recorded {field} differs from {recorded}")
    if before["named"] != expected["named"]:
        problems.append(f"named groups differ from those rebuilt at {recorded}")
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
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeDecodeError) as exc:
        print(f"[identity] REJECTED: malformed input ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
