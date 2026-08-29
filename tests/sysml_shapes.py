"""Shared SysML v2 textual-notation shape helpers for model tests.

Single home for the comment-stripping, braced-block extraction, and
verification-model discovery logic that used to be copy-pasted across
per-capability test files. Nothing here knows about AEBS or middleware:
discovery is tree-wide, so new capabilities are covered automatically.

Regex parsing is a test-side convenience, not a SysML v2 parser. Semantic
validation stays with syside (`python scripts/validate_sysml.py`).
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_ROOT = REPO_ROOT / "textual-notation-of-model"

_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)

# A verification usage instantiates a definition: verification <usage> : <Def> {
_USAGE_RE = re.compile(r"\bverification\s+(\w+)\s*:\s*(\w+)\s*\{")
_DEF_RE = re.compile(r"\bverification\s+def\s+(\w+)")
_VERIFY_TARGET_RE = re.compile(r"\bverify\s+(\w+)\s*;")
_PERFORM_RE = re.compile(r"\bperform\s+(\w+)\s*;")
_PRODUCT_CLAIM_RE = re.compile(
    r"\b(?:verify|satisfy)\s+(?:/\*.*?\*/\s*)?req\w+\s*;", re.DOTALL
)

# A verification model is any package file that declares at least one
# verification definition or usage.
_VERIFICATION_FILE_HINT = re.compile(r"\bverification\s+(?:def\s+\w+|\w+\s*:\s*\w+\s*\{)")


def strip_comments(source: str) -> str:
    """Return text with doc/block and line comments removed."""
    return _COMMENT_RE.sub("", source)


def braced_body(source: str, declaration: str) -> str:
    """Return the balanced-brace body following ``declaration``.

    ``declaration`` is the exact declaration prefix, e.g.
    ``"verification def NominalMovingVehicleTargetVerification009B"`` or
    ``"calc def Map009FOutcomeToVerdict"``.
    """
    start = source.index(declaration)
    opening = source.index("{", start + len(declaration))
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"unclosed declaration: {declaration}")


def requirement_block(model_text: str, element_name: str) -> str | None:
    """Return the full block of the named requirement usage, or None."""
    match = re.search(
        rf"\bre[^ ]* {re.escape(element_name)}\b[^{{]*\{{", model_text
    )
    if not match:
        return None
    start = match.end() - 1
    depth = 1
    for i in range(start + 1, len(model_text)):
        if model_text[i] == "{":
            depth += 1
        elif model_text[i] == "}":
            depth -= 1
            if depth == 0:
                return model_text[match.start() : i + 1]
    return None


@lru_cache(maxsize=1)
def verification_model_paths() -> tuple[Path, ...]:
    """Every model file under the notation tree declaring verification content."""
    return tuple(
        sorted(
            path
            for path in MODEL_ROOT.rglob("*.sysml")
            if _VERIFICATION_FILE_HINT.search(strip_comments(path.read_text(encoding="utf-8")))
        )
    )


@lru_cache(maxsize=None)
def load_model(path: Path) -> tuple[str, str]:
    """Return (raw source, comment-stripped source) for a model file."""
    source = path.read_text(encoding="utf-8")
    return source, strip_comments(source)


def verification_defs(code: str) -> list[str]:
    """Names of all ``verification def`` declarations."""
    return _DEF_RE.findall(code)


def verification_usages(code: str) -> list[tuple[str, str]]:
    """(usage, definition) pairs of all verification usage declarations."""
    return _USAGE_RE.findall(code)


def verify_targets(code: str) -> list[str]:
    """Names referenced by ``verify <name>;`` relationships."""
    return _VERIFY_TARGET_RE.findall(code)


def performed_usages(code: str) -> list[str]:
    """Names referenced by ``perform <name>;`` statements."""
    return _PERFORM_RE.findall(code)


def has_product_claim(source: str) -> bool:
    """True when a verify/satisfy relationship claims a product requirement.

    Deliberately matched against the raw source (comments intact) so comment
    insertion cannot smuggle a product claim past the check.
    """
    return bool(_PRODUCT_CLAIM_RE.search(source))
