"""Shared revision-binding and model-documentation helpers.

Originally the O1 Semantic Authority Inventory generator. O4 Wave C2 deleted
the inventory generator (it read the retired authored ontology; its output is
a frozen O1 record, ``docs/method-conformance/frozen-records.json``). What
remains is the shared machinery the live generators and gates use:

- revision binding: :func:`validate_source_binding`,
  :func:`verify_source_revision_contains_inputs`,
  :func:`resolve_source_revision`, :func:`file_digest` — a generated artifact
  binds a ``source_revision`` that contains every bound input byte-for-byte
  plus per-input content digests;
- model documentation text: :func:`normalize_text`,
  :func:`declaration_block`, :func:`doc_text_observation` (exact equality
  after cosmetic normalization; containment or similarity is never parity).

Never imported by the semantic runtime.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

class InventoryError(Exception):
    """Generation/validation failure for the semantic authority inventory."""


def normalize_text(text: str) -> str:
    """Purely cosmetic normalization: case, punctuation, whitespace/wrapping.

    This is the only automatic comparison the inventory performs on
    documentation text. It is exact token normalization — never a similarity
    score, word overlap, or fuzzy match.
    """
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def declaration_block(file_text: str, declaration: str) -> tuple[str, bool]:
    """Best-effort body of one ``<kind> def <Name> { ... }`` declaration.

    Returns ``(block, bodyless)``. ``bodyless`` is True when the declaration
    ends with ``;`` (or has no body at all) — a property of the declaration
    form, not a text difference.

    Brace matching is comment- and string-aware (final-O1 R1 correction):
    braces or comment markers inside ``/* ... */``, ``//`` comments, or
    double-quoted string content never terminate the declaration early or
    extend it past its own closing brace.
    """
    kind, _, name = declaration.partition(" def ")
    pattern = re.compile(
        r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
        + re.escape(kind.strip()).replace(r"\ ", r"\s+")
        + r"\s+def\s+"
        + re.escape(name.strip())
        + r"\b"
    )
    match = pattern.search(file_text)
    if not match:
        return "", False
    rest = file_text[match.end():]
    length = len(rest)
    brace = -1
    semi = -1
    index = 0
    while index < length:
        if rest.startswith("/*", index):
            end = rest.find("*/", index + 2)
            if end == -1:
                break
            index = end + 2
            continue
        if rest.startswith("//", index):
            end = rest.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        char = rest[index]
        if char == '"':
            index = _skip_string_literal(rest, index)
            continue
        if char == "{":
            brace = index
            break
        if char == ";":
            semi = index
            break
        index += 1
    if brace == -1 or (semi != -1 and semi < brace):
        return "", True
    depth = 0
    index = brace
    while index < length:
        if rest.startswith("/*", index):
            end = rest.find("*/", index + 2)
            if end == -1:
                return rest[brace:], False
            index = end + 2
            continue
        if rest.startswith("//", index):
            end = rest.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        char = rest[index]
        if char == '"':
            index = _skip_string_literal(rest, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return rest[brace:index + 1], False
        index += 1
    return rest[brace:], False


def _skip_string_literal(block: str, index: int) -> int:
    """Index after a double-quoted string literal starting at ``index``.

    Bounded robustness for the supported textual subset: escaped quotes do
    not terminate the literal; braces or comment-like tokens inside string
    content are not structural.
    """
    index += 1  # opening quote
    length = len(block)
    while index < length:
        char = block[index]
        if char == "\\":
            index += 2
            continue
        if char == '"':
            return index + 1
        index += 1
    return length


def _owned_doc_bodies(block: str) -> list[str]:
    """Documentation bodies owned by the definition itself (spec-grounded).

    Ownership rule (OMG SysML v2 Part 1, §7.4.2): "The documenting element of
    documentation is always the owning element of the documentation" — a
    ``doc`` comment is owned by the element whose body it lexically sits in.
    The rule is **uniform lexical containment**:

    * a ``doc`` statement at the declaration body's direct lexical depth is
      owned by the declaration — regardless of position, of preceding member
      declarations, and of whether another direct-body doc appeared earlier
      (ownership = containment, not adjacency, ordering, or the presence of a
      leading doc block; a doc following a semicolon-terminated member sits in
      no member body);
    * a ``doc`` inside a nested member body (literals, nested items, ...) is
      owned by that nested element and never enters the declaration's
      documentation.

    One bounded scan over the complete body: brace nesting is tracked,
    comment interiors and string-literal content are structurally inert,
    scanning continues past semicolon-terminated members, and docs are
    collected in source order. Deterministic; no fuzzy matching, no names,
    paths, or declaration-specific special cases.
    """
    docs: list[str] = []
    depth = 0
    index = 1  # skip the opening '{' of the declaration block
    length = len(block)
    while index < length:
        if block.startswith("/*", index):
            end = block.find("*/", index + 2)
            if end == -1:
                break
            if depth == 0:
                behind = block[:index].rstrip()
                if re.search(r"(?<![A-Za-z0-9_])doc$", behind):
                    docs.append(block[index + 2:end])
            index = end + 2
            continue
        if block.startswith("//", index):
            end = block.find("\n", index)
            index = length if end == -1 else end + 1
            continue
        char = block[index]
        if char == '"':
            index = _skip_string_literal(block, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                break  # the declaration body's closing brace
            depth -= 1
        index += 1
    return docs


def doc_text_observation(
    file_text: str, declaration: str, definition: str
) -> str:
    """Exact-parity observation of one declaration's model-resident doc text.

    Definition-level documentation is determined by :func:`_owned_doc_bodies`
    (spec §7.4.2: a doc comment is owned by the element whose body it lexically
    sits in) — uniform lexical containment: every ``doc`` statement at the
    declaration body's direct lexical depth is the definition's documentation,
    regardless of position, of preceding semicolon-terminated members, or of
    whether another direct-body doc appeared earlier; docs inside nested
    member bodies are never definition documentation.

    ``normalized-exact`` requires **equality** after the allowed cosmetic
    normalization (case, punctuation, whitespace/line wrapping). Containment
    or substring overlap in either direction is NOT parity: text that adds or
    omits semantic content yields ``differs`` and requires a human-reviewed
    equivalence decision. There is no similarity threshold, token overlap, or
    fuzzy comparison anywhere.
    """
    block, bodyless = declaration_block(file_text, declaration)
    if bodyless:
        return "doc-absent (bodyless declaration)"
    if not block:
        return "block-not-located"
    docs = _owned_doc_bodies(block)
    if not docs:
        return "doc-absent"
    blob = normalize_text(" ".join(docs))
    target = normalize_text(" ".join(str(definition).split()))
    if not target:
        return "doc-present"
    if blob == target:
        return "normalized-exact"
    return "differs"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def resolve_source_revision(root: Path) -> str:
    """The full commit id of the checkout being generated from."""
    result = _git(root, "rev-parse", "HEAD")
    if result.returncode != 0 or not result.stdout.strip():
        raise InventoryError(
            "cannot resolve the source revision (git rev-parse HEAD failed); "
            "the inventory must be generated from a Git checkout"
        )
    return result.stdout.strip()


def _git_tree_blobs(
    root: Path, revision: str, paths: list[str]
) -> tuple[dict[str, str], str | None]:
    """Blob ids of ``paths`` at ``revision`` (missing paths are absent)."""
    result = _git(root, "ls-tree", "-r", "-z", revision, "--", *paths)
    if result.returncode != 0:
        return {}, result.stderr.strip() or f"git ls-tree failed for {revision}"
    blobs: dict[str, str] = {}
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        meta, _, path = entry.partition("\t")
        parts = meta.split()
        if len(parts) == 3 and parts[1] == "blob":
            blobs[path] = parts[2]
    return blobs, None


def _binding_errors(
    root: Path, source_revision: str, bound_inputs: dict[str, str]
) -> list[str]:
    """Validate that ``source_revision`` genuinely contains the bound inputs.

    Checks, all fail-closed:

    1. format: ``source_revision`` is a full 40-hex commit id;
    2. existence: it resolves to a commit in this repository;
    3. ancestry: it is an ancestor of (or equal to) the checked-out revision;
    4. containment: every bound input exists at that revision and its blob is
       byte-identical to the working-tree file;
    5. content contract: the working-tree file digest matches the recorded
       ``sha256`` for that path.
    """
    errors: list[str] = []
    if not _FULL_SHA.match(source_revision):
        return [
            f"binding.source_revision must be a full 40-hex commit id "
            f"(got {source_revision!r})"
        ]
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    if _git(root, "cat-file", "-e", f"{source_revision}^{{commit}}").returncode != 0:
        return [
            f"binding.source_revision {source_revision} is not a commit in this "
            "repository"
        ]
    head_result = _git(root, "rev-parse", "HEAD")
    if head_result.returncode != 0 or not head_result.stdout.strip():
        return [
            "cannot resolve the checked-out revision (git rev-parse HEAD "
            "failed): the source-revision binding cannot be validated"
        ]
    head = head_result.stdout.strip()
    if _git(root, "merge-base", "--is-ancestor", source_revision, head).returncode != 0:
        errors.append(
            f"binding.source_revision {source_revision} is not an ancestor of "
            f"the checked-out revision {head}"
        )

    paths = sorted(bound_inputs)
    revision_blobs, tree_error = _git_tree_blobs(root, source_revision, paths)
    if tree_error:
        errors.append(f"cannot read the source-revision tree: {tree_error}")
        return errors
    missing_at_revision = [path for path in paths if path not in revision_blobs]
    for path in missing_at_revision:
        errors.append(
            f"bound input {path} does not exist at source_revision "
            f"{source_revision}"
        )
    present = [
        path for path in paths if path not in missing_at_revision and (root / path).is_file()
    ]
    missing_here = sorted(set(paths) - set(present) - set(missing_at_revision))
    for path in missing_here:
        errors.append(f"bound input {path} is missing from the checkout")

    current_blobs: dict[str, str] = {}
    if present:
        result = _git(root, "hash-object", "--", *present)
        if result.returncode != 0:
            errors.append(
                f"cannot hash working-tree bound inputs: "
                f"{result.stderr.strip() or 'git hash-object failed'}"
            )
        else:
            current_blobs = dict(zip(present, result.stdout.splitlines()))
    for path in present:
        if revision_blobs[path] != current_blobs.get(path):
            errors.append(
                f"bound input {path} differs from its content at source_revision "
                f"{source_revision}; the recorded revision is stale — regenerate "
                "and commit the artifact bound to a commit that contains the "
                "current inputs"
            )
        recorded = bound_inputs[path]
        digest = file_digest(root, path)
        if recorded != digest:
            errors.append(
                f"bound input {path} content digest {digest} does not match the "
                f"recorded digest {recorded!r}"
            )
    return errors


def validate_source_binding(root: Path, binding: dict[str, Any]) -> list[str]:
    """Validate one artifact's source-revision binding against the repository."""
    source_revision = binding.get("source_revision")
    if not isinstance(source_revision, str):
        return [
            "binding.source_revision is required (full commit id of a revision "
            "containing every bound input)"
        ]
    bound_inputs = binding.get("bound_inputs")
    if not isinstance(bound_inputs, dict) or not bound_inputs:
        return ["binding.bound_inputs must be a non-empty path -> sha256 mapping"]
    errors = _binding_errors(root, source_revision, bound_inputs)
    # Named input views, when present, must agree with the bound-input
    # content contract.
    for key in (
        "ontology_contract",
        "reviewed_decisions",
        "closure_evidence",
        "runtime_strategy_source",
    ):
        if key not in binding:
            continue
        record = binding.get(key)
        if not isinstance(record, dict):
            errors.append(f"binding.{key} must be a mapping")
            continue
        path = record.get("path")
        if not isinstance(path, str) or path not in bound_inputs:
            errors.append(f"binding.{key} path {path!r} is not a bound input")
            continue
        if record.get("digest") != bound_inputs[path]:
            errors.append(
                f"binding.{key} digest {record.get('digest')!r} does not match "
                f"the bound input digest {bound_inputs[path]!r}"
            )
    return errors


def verify_source_revision_contains_inputs(
    root: Path, source_revision: str, bound_inputs: dict[str, str]
) -> None:
    """Generation-time guard: refuse to bind to a revision that lacks the inputs."""
    errors = _binding_errors(root, source_revision, bound_inputs)
    if errors:
        raise InventoryError(
            "the source revision does not contain the bound inputs "
            "byte-for-byte:\n  - "
            + "\n  - ".join(errors)
            + "\nCommit the input changes first, then regenerate so the "
            "artifact can bind to that commit."
        )


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def file_digest(root: Path, relative: str) -> str:
    return _file_digest(root / relative)


_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


