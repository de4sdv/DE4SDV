"""The governed members use the projections of their configurations.

ADR 0014 admits two planned reference members, Standalone and AAOS-integrated.
The product-level model of each specializes its member decision in the
governed product-line scope, and types its platform stack by the part
definition that the configurator generates from its bill of features. A
configuration applies to the member products whose definitions own a usage
typed by the part definition of its projection (ADR 0022), so each member's
configuration applies to that member and to nothing else.

These are lexical source guards; licensed Syside validates the model in CI.
Comments and string literals are blanked before matching, and a usage belongs
to a definition only at the depth of the definition's own body.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLE = Path("model-based-product-line-engineering")
SCOPE = PLE / "scoping/de4sdv_aebs_product_line_scope.sysml"
CONFIGURATIONS = PLE / "feature-configurations"
PROJECTIONS = PLE / "product-models"
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
#: A usage typed by a definition: ``name : Type`` or ``name[m] : Pkg::Type``, never ``:>`` or ``::``.
_TYPED_USAGE = re.compile(
    r"(?<![\w:])(?P<usage>[A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?:(?![:>])\s*(?P<type>(?:\w+::)*\w+)")


def _active(text: str) -> str:
    return _NOT_CODE.sub(lambda match: '""' if match.group().startswith('"') else " ", text)


def _code(path: Path) -> str:
    return _active((ROOT / path).read_text(encoding="utf-8"))


def _projection_name(configuration: str) -> str:
    return yaml.safe_load((ROOT / CONFIGURATIONS / configuration).read_text(encoding="utf-8"))["name"]


def _definition_body(code: str, name: str, supertype: str) -> str:
    """The braced body of the one ``part def <name> :> <supertype> {`` in ``code``."""
    headers = list(re.finditer(rf"\bpart\s+def\s+{name}\b(?P<rest>[^;{{]*)(?P<end>[;{{])", code))
    assert len(headers) == 1, f"expected one part def {name}, found {len(headers)}"
    header = headers[0]
    general = re.fullmatch(r"\s*:>\s*(?P<general>(?:\w+::)*\w+)\s*", header["rest"])
    assert general and general["general"] == supertype, f"part def {name} does not specialize {supertype}"
    assert header["end"] == "{", f"part def {name} has no body"
    depth = 0
    for index in range(header.start("end"), len(code)):
        depth += {"{": 1, "}": -1}.get(code[index], 0)
        if depth == 0:
            return code[header.start("end") : index + 1]
    raise AssertionError(f"part def {name} has an unbalanced body")


def _owned_typings(body: str, usage: str) -> list[str]:
    """Types of the ``part <usage> : <Type>`` usages the body owns, not a nested owner."""
    return [
        match["type"]
        for match in re.finditer(rf"\bpart\s+{usage}\s*:\s*(?P<type>(?:\w+::)*\w+)\s*[;{{]", body)
        if body.count("{", 0, match.start()) - body.count("}", 0, match.start()) == 1
    ]


@pytest.mark.parametrize("member", sorted(MEMBERS))
def test_member_types_its_platform_stack_by_its_configuration_projection(member: str) -> None:
    model, definition, supertype, configuration = MEMBERS[member]
    projection = _projection_name(configuration)
    body = _definition_body(_code(model), definition, supertype)
    assert _owned_typings(body, "platformStack") == [projection]
    assert re.search(rf"\bpart\s+def\s+{member}\s*:>\s*ProductLineMemberProduct\s*\{{", _code(SCOPE)), (
        f"{member} is not a member decision of the governed scope")
    declaring = [path.name for path in sorted((ROOT / PROJECTIONS).glob("*.sysml"))
                 if re.search(rf"\bpart\s+def\s+{projection}\s*:>\s*SDVPlatformStack\s*\{{",
                              _active(path.read_text(encoding="utf-8")))]
    assert len(declaring) == 1, f"the projection {projection} is declared in {declaring}"


_PART_DEF = re.compile(r"\bpart\s+def\s+(?P<name>\w+)(?:\s*:>\s*(?P<generals>(?:\w+::)*\w+(?:\s*,\s*(?:\w+::)*\w+)*))?"
                       r"\s*(?P<end>[;{])")


def _definitions(code: str) -> list[tuple[str, set[str], int, int]]:
    """(name, the last segments of its supertypes, body start, body end) of each part def."""
    found = []
    for header in _PART_DEF.finditer(code):
        generals = {general.strip().rsplit("::", 1)[-1] for general in (header["generals"] or "").split(",") if general}
        start = end = header.start("end")
        if header["end"] == "{":
            depth = 0
            for end in range(start, len(code)):
                depth += {"{": 1, "}": -1}.get(code[end], 0)
                if depth == 0:
                    break
        found.append((header["name"], generals, start, end))
    return found


def _model_code() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _active(path.read_text(encoding="utf-8"))
        for root in MODEL_ROOTS
        for path in sorted((ROOT / root).rglob("*.sysml"))
        if "snapshots" not in path.relative_to(ROOT).parts
    }


def _member_lineage(definitions: list[tuple[str, set[str], int, int]]) -> set[str]:
    """The names of the part defs that specialize ProductLineMemberProduct, directly or not."""
    lineage = {"ProductLineMemberProduct"}
    while True:
        grown = lineage | {name for name, generals, _, _ in definitions if generals & lineage}
        if grown == lineage:
            return lineage
        lineage = grown


def test_only_the_governed_members_use_a_configuration_projection() -> None:
    """No other member product owns a usage typed by a configuration's projection."""
    projections = {_projection_name(path.name) for path in sorted((ROOT / CONFIGURATIONS).glob("*.yaml"))}
    assert len(projections) >= 7, "the scan must see the bills of features"
    code = _model_code()
    definitions = {path: _definitions(text) for path, text in code.items()}
    lineage = _member_lineage([definition for found in definitions.values() for definition in found])
    assert {definition for _, definition, _, _ in MEMBERS.values()} <= lineage
    users = set()
    for path, text in code.items():
        for match in _TYPED_USAGE.finditer(text):
            projection = match["type"].rsplit("::", 1)[-1]
            owners = [name for name, _, start, end in definitions[path] if start < match.start() < end]
            if projection in projections and set(owners) & lineage:
                users.add((path, owners[-1], match["usage"], projection))
    assert users == {
        (model.as_posix(), definition, "platformStack", _projection_name(configuration))
        for model, definition, _, configuration in MEMBERS.values()
    }


# Guard self-tests: the guard refuses the shapes this change replaced and
# typings it does not own. Synthetic inputs only, never copies of model files.

_SUPERSET = "part platformStack : SDVPlatformStack;"
_PROJECTION = "part platformStack : AEBSAutowareLinuxLidarCamera;"


@pytest.mark.parametrize("body, supertype", [
    (_SUPERSET, "StandaloneAutowareAEBSReferenceMember"),
    (f"/* {_PROJECTION} */", "StandaloneAutowareAEBSReferenceMember"),
    (f'attribute note = "{_PROJECTION}";', "StandaloneAutowareAEBSReferenceMember"),
    (f"part def Nested {{ {_PROJECTION} }}", "StandaloneAutowareAEBSReferenceMember"),
    (_PROJECTION, "ProductLineMemberProduct"),
], ids=["superset", "commented", "string", "nested-owner", "ungoverned-member"])
def test_guard_refuses_what_the_member_does_not_own_or_govern(body: str, supertype: str) -> None:
    code = _active(f"package P {{\n  part def Product :> {supertype} {{\n    {body}\n  }}\n}}\n")
    with pytest.raises(AssertionError):
        assert _owned_typings(_definition_body(code, "Product", "StandaloneAutowareAEBSReferenceMember"),
                              "platformStack") == ["AEBSAutowareLinuxLidarCamera"]


def test_usage_scan_sees_qualified_and_multiplicity_typings_but_not_specializations() -> None:
    code = _active(
        "part def AEBSAutowareLinuxLidarCamera :> SDVPlatformStack { part :>> middleware = middleware::none; }\n"
        "part a : AEBSAutowareLinuxLidarCamera;\nref part b : Pkg::AEBSAutowareLinuxLidarCamera;\n"
        "part c[0..1] : AEBSAutowareLinuxLidarCamera;\nalias d for AEBSAutowareLinuxLidarCamera::middleware;\n"
        "/* part e : AEBSAutowareLinuxLidarCamera; */\n")
    assert [(m["usage"], m["type"]) for m in _TYPED_USAGE.finditer(code) if m["type"].endswith("LidarCamera")] == [
        ("a", "AEBSAutowareLinuxLidarCamera"), ("b", "Pkg::AEBSAutowareLinuxLidarCamera"),
        ("c", "AEBSAutowareLinuxLidarCamera")]
