#!/usr/bin/env python3
"""Compare two PLE qualification artifacts across a re-pin of PLEML: pass or fail, mechanically.

The baseline is the artifact of a PLE qualification run on the previous release
(``pleml_package.PREVIOUS``), the candidate one on the pinned release
(``pleml_package.RELEASE``). Every value must be equal, except:

- ``ALLOWED`` JSON paths: the executor identity, the fresh API import, and the
  PLEML pin and library digest. The identity paths in ``EXPECTED`` must name the
  previous release in the baseline and the pinned release in the candidate.
- The library's own text, which may differ only as the recorded re-pin
  (``pleml_package.REPIN``) says: its Documentation body, the library entry of
  the source manifest, and the pin in the scoped fixture's comment.

A difference anywhere else, a missing or extra file, or an allowed path without
the expected value fails. ``sysml-api.log`` is not compared. The candidate adds
``pleml-package.json``, the byte check of the fenced package.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_package as package

SCHEMA = "de4sdv.ple-qualification-comparison/v1"
#: The library label of the frozen interpreter, in the source manifests.
LIBRARY_LABEL = "external/pleml/PLEML.sysml"
#: JSON paths (dotted) that may differ between the two runs; a path covers its subtree.
ALLOWED: dict[str, set[str]] = {
    "current/receipt.json": {
        "binding.executor_revision", "binding.export_sha256", "binding.project_id", "binding.commit_id",
        "binding.content_sha256", "binding.pleml_pin",
        "source_identity.executor_revision", "source_identity.executor_inputs",
        "source_identity.library_sha256", "source_identity.pleml_pin", "source_identity.library_provision",
    },
    "current/binding.json": {"executor_revision", "export_sha256", "project_id", "commit_id", "content_sha256",
                             "pleml_pin"},
    "historical-replay.json": {"source_identity.executor_revision"},
    "provider-origin.json": {"executor_revision"},
    "scoped/receipt.json": {
        "executor_revision", "executor_source_sha256", "native_xor.pin", "native_xor.command",
        "source_identity.library_sha256", "source_identity.pleml_pin", "source_identity.library_provision",
        "artifact_sha256.scoped-fixture.sysml", "artifact_sha256.serialized-elements.json",
    },
}
#: Element files: equal element by element, except the library's Documentation body (the re-pin's lines).
ELEMENT_FILES = ("current/export.json", "current/api-readback.json", "scoped/serialized-elements.json")
#: Files that must be byte-equal.
EQUAL_FILES = ("scoped/literal-bounds.synthetic.json", "scoped/range-operator.synthetic.json",
               "scoped/cli-exit.txt", "scoped/serializer-diagnostics.txt", "sysand-version.txt")
FIXTURE_FILE = "scoped/scoped-fixture.sysml"
IGNORED = ("sysml-api.log",)
NEW_FILE = "pleml-package.json"


def _provision(release: package.Release) -> dict[str, str]:
    return {"provision": "sysand", "package": package.PACKAGE, "version": release.version, "tag": release.tag,
            "lock": (package.PROJECT / "sysand-lock.toml").as_posix()}


def expected(release: package.Release, *, provisioned: bool) -> dict[str, dict[str, Any]]:
    """The identity paths and the values a run on ``release`` holds; ``provisioned``: through the fenced lock."""
    pin, library = release.tag_commit, release.library.sha256
    identity = {"source_identity.pleml_pin": pin, "source_identity.library_sha256": library}
    if provisioned:
        identity["source_identity.library_provision"] = _provision(release)
    return {
        "current/receipt.json": {"binding.pleml_pin": pin, **identity},
        "current/binding.json": {"pleml_pin": pin},
        "scoped/receipt.json": {"native_xor.pin": pin, **identity},
    }


def _get(value: Any, path: str) -> Any:
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return _MISSING
        value = value[key]
    return value


_MISSING = object()


def _differences(left: Any, right: Any, path: str = "") -> list[str]:
    """Dotted paths where ``left`` and ``right`` differ (lists compared as wholes)."""
    if isinstance(left, dict) and isinstance(right, dict):
        found = []
        for key in sorted(set(left) | set(right), key=str):
            child = f"{path}.{key}" if path else str(key)
            if key not in left or key not in right:
                found.append(child)
            else:
                found.extend(_differences(left[key], right[key], child))
        return found
    return [] if left == right else [path or "<root>"]


def _allowed(path: str, allowed: set[str]) -> bool:
    return any(path == item or path.startswith(item + ".") for item in allowed)


def _normalized_command(command: str, revision: str) -> list[str]:
    tokens = command.split()
    return ["PYTHON", *[token.replace(revision, "EXECUTOR") if revision else token for token in tokens[1:]]]


def _version_lines(baseline: str, candidate: str, release: package.Release, repin: package.Repin) -> list[str]:
    """Problems with a Documentation body change: only the recorded lines, to the pinned version."""
    old, new = baseline.splitlines(), candidate.splitlines()
    if len(old) != len(new):
        return [f"the line count changes from {len(old)} to {len(new)}"]
    recorded = {text.strip().lstrip("*").strip() for _, text in repin.previous_lines}
    target = re.compile(r"Version:\s*v" + re.escape(release.version))
    return [f"line {number}: {before!r} -> {after!r}" for number, (before, after) in enumerate(zip(old, new), 1)
            if before != after and not (before.strip() in recorded and target.fullmatch(after.strip()))]


def _elements(data: Any) -> list[dict[str, Any]]:
    return data["elements"] if isinstance(data, dict) else data


def compare_elements(name: str, baseline: Any, candidate: Any, *, release: package.Release,
                     previous: package.Release, repin: package.Repin) -> list[str]:
    problems: list[str] = []
    left = {item.get("@id"): item for item in _elements(baseline)}
    right = {item.get("@id"): item for item in _elements(candidate)}
    if set(left) != set(right):
        return [f"{name}: the element ids differ ({len(set(left) ^ set(right))} not in both)"]
    changed = [key for key in sorted(left) if left[key] != right[key]]
    for key in changed:
        before, after = left[key], right[key]
        keys = _differences(before, after)
        if before.get("@type") != "Documentation" or keys != ["body"]:
            problems.append(f"{name}: element {key} differs in {keys}")
            continue
        problems.extend(f"{name}: element {key} body {line}"
                        for line in _version_lines(before["body"], after["body"], release, repin))
    if len(changed) > 1 or (repin.previous_lines and not changed and previous.library != release.library):
        problems.append(f"{name}: {len(changed)} elements differ; the re-pin changes exactly one Documentation body")
    if isinstance(baseline, dict):
        for key in _differences({k: v for k, v in baseline.items() if k not in ("elements", "source_manifest")},
                                {k: v for k, v in candidate.items() if k not in ("elements", "source_manifest")}):
            problems.append(f"{name}: {key} differs")
        manifests = baseline.get("source_manifest"), candidate.get("source_manifest")
        for side, manifest, release_side in (("baseline", manifests[0], previous), ("candidate", manifests[1], release)):
            entry = next((item for item in manifest or [] if item.get("path") == LIBRARY_LABEL), None)
            if entry is None or (entry.get("sha256"), entry.get("size")) != (release_side.library.sha256,
                                                                             release_side.library.size):
                problems.append(f"{name}: the {side} source manifest does not record PLEML {release_side.version}")
        others = [[item for item in manifest or [] if item.get("path") != LIBRARY_LABEL] for manifest in manifests]
        if others[0] != others[1]:
            problems.append(f"{name}: the source manifests differ outside the library entry")
    return problems


def compare(baseline: Path, candidate: Path, *, candidate_revision: str | None = None,
            release: package.Release = package.RELEASE, previous: package.Release = package.PREVIOUS,
            repin: package.Repin = package.REPIN) -> dict[str, Any]:
    problems: list[str] = []
    left = {path.relative_to(baseline).as_posix() for path in baseline.rglob("*") if path.is_file()}
    right = {path.relative_to(candidate).as_posix() for path in candidate.rglob("*") if path.is_file()}
    if right != left | {NEW_FILE} or NEW_FILE in left:
        problems.append(f"the files differ: only in the baseline {sorted(left - right)}, "
                        f"only in the candidate {sorted(right - left - {NEW_FILE})}, "
                        f"{NEW_FILE} {'in the baseline' if NEW_FILE in left else 'missing' if NEW_FILE not in right else 'present'}")
    load = lambda root, name: json.loads((root / name).read_text(encoding="utf-8"))  # noqa: E731
    # The baseline read the previous release from a frozen experiment; the candidate reads the pin.
    before_expected, after_expected = expected(previous, provisioned=False), expected(release, provisioned=True)
    for name, allowed in ALLOWED.items():
        if name not in left or name not in right:
            continue
        old, new = load(baseline, name), load(candidate, name)
        for path in _differences(old, new):
            if not _allowed(path, allowed):
                problems.append(f"{name}: {path} differs")
        for side, data, values in (("baseline", old, before_expected.get(name, {})),
                                   ("candidate", new, after_expected.get(name, {}))):
            for path, value in values.items():
                if _get(data, path) != value:
                    problems.append(f"{name}: the {side}'s {path} is {_get(data, path)!r}, not {value!r}")
        if candidate_revision:
            for path in (item for item in allowed if item.endswith("executor_revision")):
                if _get(new, path) != candidate_revision:
                    problems.append(f"{name}: {path} is not the candidate revision {candidate_revision}")
        if name == "scoped/receipt.json":
            old_command = _normalized_command(_get(old, "native_xor.command"), _get(old, "executor_revision"))
            new_command = _normalized_command(_get(new, "native_xor.command"), _get(new, "executor_revision"))
            if old_command != new_command:
                problems.append(f"{name}: native_xor.command differs beyond the interpreter path and the executor")
        if name == "current/receipt.json":
            inputs = _get(new, "source_identity.executor_inputs") or {}
            for required in ("de4sdv/semantic/pleml_package.py", (package.PROJECT / "sysand-lock.toml").as_posix()):
                if required not in inputs:
                    problems.append(f"{name}: the candidate's executor inputs do not verify {required}")
    for name in ELEMENT_FILES:
        if name in left and name in right:
            problems.extend(compare_elements(name, load(baseline, name), load(candidate, name),
                                             release=release, previous=previous, repin=repin))
    for name in EQUAL_FILES:
        if name in left and name in right and (baseline / name).read_bytes() != (candidate / name).read_bytes():
            problems.append(f"{name} differs")
    if FIXTURE_FILE in left and FIXTURE_FILE in right:
        old_text = (baseline / FIXTURE_FILE).read_text(encoding="utf-8")
        new_text = (candidate / FIXTURE_FILE).read_text(encoding="utf-8")
        if old_text.replace(previous.tag_commit, release.tag_commit) != new_text or previous.tag_commit not in old_text:
            problems.append(f"{FIXTURE_FILE} differs beyond the PLEML pin in its comment")
    if NEW_FILE in right:
        receipt = load(candidate, NEW_FILE)
        checks = {"byte_check.byte_identical_to_tag": True, "byte_check.version": release.version,
                  "byte_check.tag_commit": release.tag_commit, "release_diff.path": repin.path,
                  "tag.tag_commit": release.tag_commit}
        for path, value in checks.items():
            if _get(receipt, path) != value:
                problems.append(f"{NEW_FILE}: {path} is {_get(receipt, path)!r}, not {value!r}")
    return {"schema": SCHEMA, "baseline": str(baseline), "candidate": str(candidate),
            "previous": previous.version, "release": release.version, "repin_path": repin.path,
            "allowed": {name: sorted(paths) for name, paths in ALLOWED.items()},
            "verdict": "fail" if problems else "pass", "problems": problems}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline", type=Path, required=True, help="artifact directory of the run on PREVIOUS")
    parser.add_argument("--candidate", type=Path, required=True, help="artifact directory of the run on RELEASE")
    parser.add_argument("--candidate-revision", help="the exact executor SHA the candidate run must record")
    parser.add_argument("--out", type=Path, help="write the comparison here")
    args = parser.parse_args()
    report = compare(args.baseline, args.candidate, candidate_revision=args.candidate_revision)
    text = json.dumps(report, indent=2) + "\n"
    if args.out is not None:
        args.out.write_text(text)
    print(text, end="")
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
