"""F2 guard tests: the AEBS composite reference product binds its instances
to the canonical architecture usages.

Source-level guards (the repo has no local licensed SysML on aarch64; the
privileged workflow owns semantic validation). These tests pin the binding
contract so the explicit dependencies cannot silently disappear.

The extractors are comment-resistant: declarations inside ``/* ... */`` or
``//`` comments do not satisfy the guards, so a commented-out binding fails
exactly like a deleted one. Dependency guards assert the complete
endpoint pair under the owning ``part def`` block, not disconnected
substrings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

COMPOSITE = (
    ROOT
    / "model-based-product-line-engineering/product-models/aebs_autoware_reference_product.sysml"
)

_DEP = re.compile(
    r"^\s*dependency\s+(?P<name>[A-Za-z][A-Za-z0-9_]*)\s+"
    r"from\s+(?P<source>[A-Za-z][A-Za-z0-9_:]*)\s+"
    r"to\s+(?P<target>[A-Za-z][A-Za-z0-9_:]*)\s*;",
    re.MULTILINE,
)


def _strip_comments(text: str) -> str:
    """Remove /* */ and // comments while preserving line structure."""
    result: list[str] = []
    in_block = False
    for line in text.splitlines():
        out: list[str] = []
        index = 0
        while index < len(line):
            if in_block:
                end = line.find("*/", index)
                if end == -1:
                    index = len(line)
                    continue
                out.append(" " * (end + 2 - index))
                index = end + 2
                in_block = False
                continue
            start = line.find("/*", index)
            line_comment = line.find("//", index)
            if line_comment != -1 and (start == -1 or line_comment < start):
                # Keep active code before the // comment; blank only the
                # comment itself.
                out.append(line[index:line_comment] + " " * (len(line) - line_comment))
                index = len(line)
                continue
            if start != -1:
                out.append(" " * (start - index))
                index = start
                in_block = True
                continue
            out.append(line[index:])
            index = len(line)
        result.append("".join(out))
        if in_block:
            # The block continues on the following line.
            pass
    return "\n".join(result)


def _composite_code() -> str:
    """Composite source with comments blanked (multi-line blocks removed)."""
    text = COMPOSITE.read_text(encoding="utf-8")
    # First collapse full multi-line block comments, then line-level ones.
    text = re.sub(r"/\*.*?\*/", lambda m: " " * len(m.group(0)), text, flags=re.DOTALL)
    return _strip_comments(text)


def _part_def_block(code: str, name: str) -> str:
    """Return the brace-balanced body of `part def <name> { ... }`."""
    start = re.search(
        rf"^\s*part\s+def\s+{name}\b", code, re.MULTILINE
    )
    if start is None:
        raise AssertionError(f"part def {name} not found in active code")
    brace = code.find("{", start.end())
    if brace == -1:
        raise AssertionError(f"part def {name} has no body")
    depth = 0
    for index in range(brace, len(code)):
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                return code[brace : index + 1]
    raise AssertionError(f"part def {name} body is unbalanced")


def _dependency_directly_owned(block: str, name: str) -> re.Match[str]:
    """Match the dependency ONLY at the block's immediate brace depth.

    The block string includes its own outer braces, so immediately owned
    members sit at depth 1. A dependency declared inside a nested part def
    or nested block sits deeper and is NOT owned by this part def — the
    guard must not accept structure borrowed from a nested owner.
    """
    matches = [
        match
        for match in _DEP.finditer(block)
        if match.group("name") == name and _match_depth(block, match) == 1
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly one active dependency {name!r} owned directly by "
            f"the part def body, found {len(matches)}"
        )
    return matches[0]


def _match_depth(block: str, match: re.Match[str]) -> int:
    """Brace depth of a match's start position within the block string."""
    depth = 0
    for character in block[: match.start()]:
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
    return depth


def _dependency(block: str, name: str) -> re.Match[str]:
    matches = [match for match in _DEP.finditer(block) if match.group("name") == name]
    if len(matches) != 1:
        raise AssertionError(
            f"expected exactly one active dependency {name!r} in the block, "
            f"found {len(matches)}"
        )
    return matches[0]


def _import_statement(code: str, target: str) -> None:
    pattern = rf"^\s*private\s+import\s+{re.escape(target)}\s*;\s*$"
    assert re.search(pattern, code, re.MULTILINE), (
        f"active private import of {target} not found"
    )


def test_composite_binds_logical_system_to_canonical_system() -> None:
    code = _composite_code()
    block = _part_def_block(code, "AEBSAutowareReferenceProduct")
    dependency = _dependency_directly_owned(
        block, "aebsLogicalSystemBindingToCanonicalSystem"
    )
    assert dependency.group("source") == "aebsLogicalSystem"
    assert (
        dependency.group("target") == "DE4SDV_AEBSLogicalArchitecture::system"
    )


def test_composite_binds_software_to_canonical_physical_software() -> None:
    code = _composite_code()
    block = _part_def_block(code, "AEBSAutowareReferenceProduct")
    dependency = _dependency_directly_owned(
        block, "aebsSoftwareBindingToCanonicalPhysicalSoftware"
    )
    assert dependency.group("source") == "aebsSoftware"
    assert (
        dependency.group("target")
        == "DE4SDV_AEBSPhysicalSoftwareRealization::physicalSoftware"
    )


def test_composite_specializes_governed_member_decision() -> None:
    code = _composite_code()
    assert re.search(
        r"^\s*part\s+def\s+AEBSAutowareReferenceProduct\s*:\s*>"
        r"\s*StandaloneAutowareAEBSReferenceMember\s*\{",
        code,
        re.MULTILINE,
    ), "active specialization of StandaloneAutowareAEBSReferenceMember not found"
    _import_statement(code, "DE4SDV_AEBSProductLineScope::*")


def test_composite_keeps_bounded_projection_limitation_wording() -> None:
    """The binding must not upgrade the composite to a resolved product."""
    text = COMPOSITE.read_text(encoding="utf-8")
    start = re.search(
        r"part\s+def\s+AEBSAutowareReferenceProduct\b", text
    )
    assert start is not None
    brace = text.find("{", start.end())
    assert brace != -1
    depth = 0
    end = None
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index
                break
    assert end is not None
    body = text[brace:end]
    # Join ALL doc blocks under the part def (the composite carries several);
    # strip comment leaders before the prose check.
    docs = re.findall(r"/\*(.*?)\*/", body, re.DOTALL)
    assert docs, "composite doc blocks not found"
    normalized = " ".join(
        " ".join(doc.replace("*", " ").split()) for doc in docs
    )
    assert "not make this composite a" in normalized
    assert "resolved configured product" in normalized
    assert "Product-level trace claims" in normalized
    assert "canonical allocation records" in normalized
    assert "sensing-boundary perception-sensor selections live in the" in normalized
    # The binding is reference-only: no executable query reachability claim.
    assert "no executable semantic query maps them yet" in normalized
    assert "reachability through the revision-bound API is not claimed" in normalized


def test_ontology_declares_instantiates_canonical_architecture_vocabulary() -> None:
    import yaml

    ontology = yaml.safe_load(
        (
            ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        ).read_text(encoding="utf-8")
    )
    relationship = ontology["relationships"]["instantiatesCanonicalArchitecture"]
    assert relationship["domain"] == "MemberProduct"
    assert relationship["range"] == "ArchitectureElement"
    # Vocabulary only: no executable mapping until a canonical-usage selector
    # exists (a name-based filter is not acceptable).
    assert "sysml_mapping" not in relationship
    assert "canonical-usage selector" in relationship["definition"]
    # The definition must not claim implemented query reachability: the old
    # claim sentence must stay gone, and the mapping-deferral requirement
    # must stay present.
    definition = " ".join(relationship["definition"].split())
    assert "makes the canonical trace path reachable from product-level" not in definition
    assert "must therefore define which elements carry" in definition


# --- Guard self-tests: the extractor must reject commented/deleted/retargeted
# structure. These run the real helpers against synthetic active-code inputs,
# never against copies of authoritative model files.


def _code_with_dependency(dependency_line: str) -> str:
    return (
        "package P {\n"
        "  part def ProductLineMemberProduct;\n"
        "  part def Composite {\n"
        "    part aebsLogicalSystem;\n"
        f"    {dependency_line}\n"
        "  }\n"
        "}\n"
    )


def test_dependency_guard_rejects_commented_out_binding() -> None:
    code = _code_with_dependency(
        "/* dependency bound from aebsLogicalSystem to Canonical::system; */"
    )
    block = _part_def_block(code, "Composite")
    with pytest.raises(AssertionError, match="exactly one active dependency"):
        _dependency(block, "bound")


def test_dependency_guard_requires_exact_endpoint_pair() -> None:
    code = _code_with_dependency(
        "dependency bound from aebsLogicalSystem to Wrong::target;"
    )
    block = _part_def_block(code, "Composite")
    dependency = _dependency(block, "bound")
    assert dependency.group("target") != "Canonical::system"


def test_dependency_guard_rejects_deleted_binding() -> None:
    code = _code_with_dependency("part innerPart;")
    block = _part_def_block(code, "Composite")
    with pytest.raises(AssertionError, match="exactly one active dependency"):
        _dependency(block, "bound")


def test_full_guard_rejects_binding_owned_by_nested_definition(monkeypatch) -> None:
    """The real guard must not accept structure owned by a nested part def.

    Regression for the review probe: a nested unrelated definition declares
    the usage AND the correctly spelled dependency. Endpoint spelling alone
    does not establish ownership — the full logical-binding guard must fail
    on this input, not silently accept the borrowed structure.
    """
    import sys

    code = (
        "package DE4SDV_AEBSAutowareReferenceProduct {\n"
        "  private import DE4SDV_AEBSProductLineScope::*;\n"
        "  part def AEBSAutowareReferenceProduct :> StandaloneAutowareAEBSReferenceMember {\n"
        "    part def UnrelatedNested {\n"
        "      part aebsLogicalSystem;\n"
        "      dependency aebsLogicalSystemBindingToCanonicalSystem\n"
        "        from aebsLogicalSystem\n"
        "        to DE4SDV_AEBSLogicalArchitecture::system;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    monkeypatch.setitem(
        sys.modules[__name__].__dict__, "_composite_code", lambda: code
    )
    with pytest.raises(AssertionError, match="owned directly by"):
        test_composite_binds_logical_system_to_canonical_system()


def test_comment_stripping_preserves_multiplication_operators() -> None:
    """Blanking comments must not delete '*' operators in active code."""
    code = "part def M {\n  attribute x = 2 * 3; // note\n}\n"
    stripped = _strip_comments(code)
    assert "2 * 3" in stripped
