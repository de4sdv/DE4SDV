"""The governed members use the projections of their configurations.

ADR 0014 admits two planned reference members, Standalone and AAOS-integrated.
The product-level model of each specializes its member decision in the
governed product-line scope, and types its platform stack by the part
definition that the configurator generates from its bill of features. A
configuration applies to the member products whose definitions own a usage
typed by the part definition of its projection. The S5o pull request (#407)
records that derivation in the ``appliesToMemberProduct`` row of the ontology
identity register, as ADR 0022 decision 8 asks. So each member's configuration
applies to that member and to nothing else.

These are lexical source guards; licensed Syside validates the model in CI.
Comments and string literals are blanked before matching. The guards read
every textual form of typing (``:``, ``defined by``, ``typed by``), of
specialization (``:>``, ``specializes``) and of a short name before a declared
name (``<'id'>``). They fail on a part definition header they cannot read, and
a usage belongs to a definition only at the depth of the definition's own body.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLE = Path("model-based-product-line-engineering")
SCOPE = PLE / "scoping/de4sdv_aebs_product_line_scope.sysml"
CONFIGURATIONS = PLE / "feature-configurations"
PROJECTIONS = PLE / "product-models"
#: The INC-AEBS-010 test article: a System 2 specialization of the AAOS-integrated configured member.
TEST_ARTICLE = Path("textual-notation-of-model/packages/features/aebs/aebs_visualization_variability_configuration.sysml")
#: The validated model roots (AGENTS.md).
MODEL_ROOTS = (Path("textual-notation-of-model"), PLE / "product-models", PLE / "scoping")

#: Governed member decision -> (its product-level model, the product definition,
#: the supertype as the model writes it, the member's bill of features).
MEMBERS = {
    "StandaloneAutowareAEBSReferenceMember": (
        PROJECTIONS / "aebs_autoware_reference_product.sysml",
        "AEBSAutowareReferenceProduct",
        "StandaloneAutowareAEBSReferenceMember",
        "aebs-autoware-linux-lidar-camera.yaml",
    ),
    "AAOSIntegratedAutowareAEBSReferenceMember": (
        Path("textual-notation-of-model/packages/features/middleware/middleware_variability_configuration.sysml"),
        "MiddlewareAutowareAAOSSDVConfiguredMember",
        "DE4SDV_AEBSProductLineScope::AAOSIntegratedAutowareAEBSReferenceMember",
        "middleware-autoware-aaos-sdv-reference.yaml",
    ),
}

#: Comments and string literals, matched in one pass so that neither hides the other.
_NOT_CODE = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:[^"\\\n]|\\.)*"', re.DOTALL)
#: A basic name or a single-quoted unrestricted name; qualified names and lists of them.
_NAME = r"(?:[A-Za-z_]\w*|'(?:[^'\\\n]|\\.)*')"
_QUALIFIED = rf"{_NAME}(?:\s*::\s*{_NAME})*"
_LIST = rf"{_QUALIFIED}(?:\s*,\s*{_QUALIFIED})*"
#: An optional short name before a declared name: ``<'M-9'>`` or ``<M9>``.
_SHORT_NAME = rf"(?:<\s*{_NAME}\s*>\s*)?"
#: Typing: ``:`` (never ``:>`` or ``::``), ``defined by`` or ``typed by``.
_TYPING = r"(?::(?![:>])|\bdefined\s+by\b|\btyped\s+by\b)"
#: Specialization: ``:>`` (never ``:>>``) or ``specializes``.
_SPECIALIZATION = r"(?::>(?!>)|\bspecializes\b)"
#: A usage typed by definitions: ``name : T``, ``name[m] defined by Pkg::T``, ``name typed by A, B``.
_TYPED_USAGE = re.compile(rf"(?<![\w:'])(?P<usage>{_NAME})\s*(?:\[[^\]]*\]\s*)?{_TYPING}\s*(?P<types>{_LIST})")
#: A part definition header, with its short name, its supertypes and the start of its body.
_PART_DEF = re.compile(
    rf"\bpart\s+def\s+{_SHORT_NAME}(?P<name>{_NAME})(?:\s*{_SPECIALIZATION}\s*(?P<generals>{_LIST}))?\s*(?P<end>[;{{])")


def _active(text: str) -> str:
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", text)


def _code(path: Path) -> str:
    return _active((ROOT / path).read_text(encoding="utf-8"))


def _bare(name: str) -> str:
    name = name.strip()
    return name[1:-1] if len(name) > 1 and name[0] == name[-1] == "'" else name


def _qualified(name: str) -> str:
    """A qualified name with its segments unquoted and no whitespace around ``::``."""
    return "::".join(_bare(segment) for segment in re.split(r"\s*::\s*", name.strip()))


def _names(names: str | None) -> list[str]:
    """The qualified names of a comma-separated list, in order."""
    return [_qualified(name) for name in re.split(r"\s*,\s*", names.strip())] if names else []


def _projection_name(configuration: str) -> str:
    return yaml.safe_load((ROOT / CONFIGURATIONS / configuration).read_text(encoding="utf-8"))["name"]


def _definitions(code: str) -> list[tuple[str, list[str], int, int]]:
    """(name, qualified supertypes, body start, body end) of each part definition of ``code``.

    Fails closed: a ``part def`` header that this reader cannot parse fails the guard.
    """
    headers = list(_PART_DEF.finditer(code))
    assert len(headers) == len(re.findall(r"\bpart\s+def\b", code)), "a part def header the guard cannot read"
    found = []
    for header in headers:
        start = end = header.start("end")
        if header["end"] == "{":
            depth = 0
            for end in range(start, len(code)):
                depth += {"{": 1, "}": -1}.get(code[end], 0)
                if depth == 0:
                    break
            else:
                raise AssertionError(f"part def {_bare(header['name'])} has an unbalanced body")
        found.append((_bare(header["name"]), _names(header["generals"]), start, end))
    return found


def _definition_body(code: str, name: str, supertype: str) -> str:
    """The braced body of the one ``part def <name>`` of ``code``, which specializes exactly ``supertype``."""
    matches = [definition for definition in _definitions(code) if definition[0] == name]
    assert len(matches) == 1, f"expected one part def {name}, found {len(matches)}"
    _, generals, start, end = matches[0]
    assert generals == [supertype], f"part def {name} specializes {generals}, not {supertype}"
    assert end > start, f"part def {name} has no body"
    return code[start : end + 1]


def _owned_typings(body: str, usage: str) -> list[str]:
    """The types of the ``<usage>`` usages the body owns itself, never through a nested owner."""
    pattern = re.compile(
        rf"\bpart\s+{_SHORT_NAME}(?:(?::>>|\bredefines\b)\s*)?{usage}\s*(?:\[[^\]]*\]\s*)?{_TYPING}\s*(?P<types>{_LIST})")
    return [
        _qualified(name)
        for match in pattern.finditer(body)
        if body.count("{", 0, match.start()) - body.count("}", 0, match.start()) == 1
        for name in _names(match["types"])
    ]


def _model_code() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _active(path.read_text(encoding="utf-8"))
        for root in MODEL_ROOTS
        for path in sorted((ROOT / root).rglob("*.sysml"))
        if "snapshots" not in path.relative_to(ROOT).parts
    }


def _member_lineage(definitions: list[tuple[str, list[str], int, int]]) -> set[str]:
    """The names of the part definitions that specialize ProductLineMemberProduct, directly or not."""
    lineage = {"ProductLineMemberProduct"}
    while True:
        grown = lineage | {name for name, generals, _, _ in definitions
                           if {general.rsplit("::", 1)[-1] for general in generals} & lineage}
        if grown == lineage:
            return lineage
        lineage = grown


def _configuration_projections() -> set[str]:
    return {_projection_name(path.name) for path in sorted((ROOT / CONFIGURATIONS).glob("*.yaml"))}


@pytest.mark.parametrize("member", sorted(MEMBERS))
def test_member_types_its_platform_stack_by_its_configuration_projection(member: str) -> None:
    model, definition, supertype, configuration = MEMBERS[member]
    projection = _projection_name(configuration)
    body = _definition_body(_code(model), definition, supertype)
    assert _owned_typings(body, "platformStack") == [projection]
    governed = [generals for name, generals, _, _ in _definitions(_code(SCOPE)) if name == member]
    assert governed == [["ProductLineMemberProduct"]], f"{member} is not a member decision of the governed scope"
    declaring = [path.name for path in sorted((ROOT / PROJECTIONS).glob("*.sysml"))
                 if (projection, ["SDVPlatformStack"]) in [(name, generals) for name, generals, _, _ in
                                                          _definitions(_active(path.read_text(encoding="utf-8")))]]
    assert len(declaring) == 1, f"the projection {projection} is declared in {declaring}"


def test_only_the_governed_members_use_a_configuration_projection() -> None:
    """No other member product owns a usage typed by a configuration's projection."""
    projections = _configuration_projections()
    assert len(projections) >= 7, "the scan must see the bills of features"
    code = _model_code()
    definitions = {path: _definitions(text) for path, text in code.items()}
    lineage = _member_lineage([definition for found in definitions.values() for definition in found])
    assert {definition for _, definition, _, _ in MEMBERS.values()} <= lineage
    users = set()
    for path, text in code.items():
        for match in _TYPED_USAGE.finditer(text):
            owners = [name for name, _, start, end in definitions[path] if start < match.start() < end]
            if not set(owners) & lineage:
                continue
            for projection in {name.rsplit("::", 1)[-1] for name in _names(match["types"])} & projections:
                users.add((path, owners[-1], _bare(match["usage"]), projection))
    assert users == {
        (model.as_posix(), definition, "platformStack", _projection_name(configuration))
        for model, definition, _, configuration in MEMBERS.values()
    }


def test_the_visualization_test_article_inherits_the_platform_stack_and_owns_none() -> None:
    """The INC-AEBS-010 test article specializes the AAOS-integrated configured member, so it
    is in the governed AAOS member's lineage. It inherits ``platformStack`` and owns no usage
    typed by a projection, so the owned-usage derivation does not reach it."""
    body = _definition_body(_code(TEST_ARTICLE), "AEBSAutowareAAOSSDVVisualizationTestArticle",
                            "MiddlewareAutowareAAOSSDVConfiguredMember")
    projections = _configuration_projections()
    assert _owned_typings(body, "platformStack") == []
    assert not [match["usage"] for match in _TYPED_USAGE.finditer(body)
                if {name.rsplit("::", 1)[-1] for name in _names(match["types"])} & projections]


# Guard self-tests on synthetic inputs, never copies of model files.

_EXTRA_MODEL = "textual-notation-of-model/packages/probe/probe.sysml"
_ANOTHER_MEMBER = {
    "colon-typing": "part def ExtraMember :> MiddlewareAutowareAAOSSDVConfiguredMember {"
                    " part platformStack : AEBSAutowareLinuxLidarCamera; }",
    "defined-by": "part def ExtraMember :> MiddlewareAutowareAAOSSDVConfiguredMember {"
                  " part platformStack defined by AEBSAutowareLinuxLidarCamera; }",
    "typed-by": "part def ExtraMember :> MiddlewareAutowareAAOSSDVConfiguredMember {"
                " part platformStack typed by AEBSAutowareLinuxLidarCamera; }",
    "specializes": "part def ExtraMember specializes MiddlewareAutowareAAOSSDVConfiguredMember {"
                   " part platformStack : AEBSAutowareLinuxLidarCamera; }",
    "short-name": "part def <'M-9'> ExtraMember :> MiddlewareAutowareAAOSSDVConfiguredMember {"
                  " part platformStack : AEBSAutowareLinuxLidarCamera; }",
    "redefinition": "abstract part def ExtraMember\n  :> MiddlewareAutowareAAOSSDVConfiguredMember {\n"
                    "  part :>> platformStack : MiddlewareAutowareAAOSSDVReference; }",
    "all-forms": "part def <M9> 'Extra Member' specializes Other, DE4SDV_AEBSProductLineScope::"
                 "StandaloneAutowareAEBSReferenceMember { part <'P-1'> platformStack[1] typed by "
                 "Pkg :: 'AEBSAutowareLinuxLidarCamera'; }",
}


def _with_extra_model(monkeypatch, text: str) -> None:
    original = _model_code
    monkeypatch.setattr(sys.modules[__name__], "_model_code", lambda: {**original(), _EXTRA_MODEL: _active(text)})


@pytest.mark.parametrize("text", list(_ANOTHER_MEMBER.values()), ids=list(_ANOTHER_MEMBER))
def test_uniqueness_guard_refuses_another_member_in_every_form(monkeypatch, text: str) -> None:
    _with_extra_model(monkeypatch, text)
    with pytest.raises(AssertionError):
        test_only_the_governed_members_use_a_configuration_projection()


def test_uniqueness_guard_accepts_a_projection_outside_the_member_lineage(monkeypatch) -> None:
    """Positive control: a bench that is no member product may type a usage by a projection."""
    _with_extra_model(monkeypatch, "part def Bench :> ExecutionBench { part platformStack typed by "
                                   "AEBSAutowareLinuxLidarCamera; }")
    test_only_the_governed_members_use_a_configuration_projection()


def test_uniqueness_guard_refuses_a_header_it_cannot_read(monkeypatch) -> None:
    _with_extra_model(monkeypatch, "part def ExtraMember :> MiddlewareAutowareAAOSSDVConfiguredMember ordered { }")
    with pytest.raises(AssertionError, match="cannot read"):
        test_only_the_governed_members_use_a_configuration_projection()


@pytest.mark.parametrize("body, supertype", [
    ("part platformStack : SDVPlatformStack;", "StandaloneAutowareAEBSReferenceMember"),
    ("/* part platformStack : AEBSAutowareLinuxLidarCamera; */", "StandaloneAutowareAEBSReferenceMember"),
    ('attribute note = "part platformStack : AEBSAutowareLinuxLidarCamera;";', "StandaloneAutowareAEBSReferenceMember"),
    ("part def Nested { part platformStack : AEBSAutowareLinuxLidarCamera; }", "StandaloneAutowareAEBSReferenceMember"),
    ("part platformStack : AEBSAutowareLinuxLidarCamera;", "ProductLineMemberProduct"),
], ids=["superset", "commented", "string", "nested-owner", "ungoverned-member"])
def test_member_guard_refuses_what_the_member_does_not_own_or_govern(body: str, supertype: str) -> None:
    code = _active(f"package P {{\n  part def Product :> {supertype} {{\n    {body}\n  }}\n}}\n")
    with pytest.raises(AssertionError):
        assert _owned_typings(_definition_body(code, "Product", "StandaloneAutowareAEBSReferenceMember"),
                              "platformStack") == ["AEBSAutowareLinuxLidarCamera"]


@pytest.mark.parametrize("usage", [
    "part platformStack : AEBSAutowareLinuxLidarCamera;",
    "part platformStack defined by AEBSAutowareLinuxLidarCamera;",
    "part <'P-1'> platformStack typed by AEBSAutowareLinuxLidarCamera;",
    "part :>> platformStack : AEBSAutowareLinuxLidarCamera;",
], ids=["colon", "defined-by", "short-name-typed-by", "redefinition"])
def test_member_guard_reads_every_typing_form(usage: str) -> None:
    for keyword in (":>", "specializes"):
        code = _active(f"part def <'M-1'> Product {keyword} StandaloneAutowareAEBSReferenceMember {{ {usage} }}")
        body = _definition_body(code, "Product", "StandaloneAutowareAEBSReferenceMember")
        assert _owned_typings(body, "platformStack") == ["AEBSAutowareLinuxLidarCamera"], (keyword, usage)


def test_usage_scan_reads_every_typing_form_but_no_specialization() -> None:
    code = _active(
        "part def AEBSAutowareLinuxLidarCamera :> SDVPlatformStack { part :>> middleware = middleware::none; }\n"
        "part a : AEBSAutowareLinuxLidarCamera;\nref part b : Pkg::AEBSAutowareLinuxLidarCamera;\n"
        "part c[0..1] defined by AEBSAutowareLinuxLidarCamera;\npart d typed by Other, AEBSAutowareLinuxLidarCamera;\n"
        "alias e for AEBSAutowareLinuxLidarCamera::middleware;\npart f :> g;\n"
        "/* part h : AEBSAutowareLinuxLidarCamera; */\n")
    found = [(_bare(match["usage"]), [name.rsplit("::", 1)[-1] for name in _names(match["types"])])
             for match in _TYPED_USAGE.finditer(code)]
    assert found == [("a", ["AEBSAutowareLinuxLidarCamera"]), ("b", ["AEBSAutowareLinuxLidarCamera"]),
                     ("c", ["AEBSAutowareLinuxLidarCamera"]), ("d", ["Other", "AEBSAutowareLinuxLidarCamera"])]
