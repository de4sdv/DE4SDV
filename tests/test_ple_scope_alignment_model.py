"""Boundary fence and textual shape of the PLEML scope-alignment model (PLE-S).

The directory sits outside every production selector: it is not exported, not
served, not a validation root and not in any production workflow's trigger.
The textual checks pin the reviewed shape (one variability, no XOR, one
feature per binding, Development-only, every qualified reference resolvable
in its source) so a rename fails here before the licensed run. Lexical checks
only: the privileged scope-alignment workflow is the validator.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import ple_scope_alignment as alignment
from de4sdv.sysml_api.baseline import REVIEWED_ROOTS, BaselineManifest
from scripts import check_naming, check_repo, validate_sysml
from sysml_shapes import strip_comments
from tools.sysml_html_viewer.generate import DEFAULT_ROOTS

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = Path("model-based-product-line-engineering/pleml-scope-alignment")
MODEL = Path(alignment.MODEL_SOURCE)
README = DIRECTORY / "README.md"
DOC = Path("docs/product-line-engineering/ple-s-scope-alignment.md")
SCOPE = Path("model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml")
PLATFORM = Path(alignment.PLATFORM_STACK_SOURCE)
PACKAGE = "DE4SDV_AEBSProductLineScopeAlignment"
FEATURE_MODEL = "AEBSProductLineScopeAlignmentFeatureModel"
TREE = f"{FEATURE_MODEL}::vehiclePlatformIntegrationModeFeatureTree"
PRODUCTION_WORKFLOWS = (
    ".github/workflows/privileged-syside-validation.yml",
    ".github/workflows/method-check.yml",
)


def _code(path: Path) -> str:
    """Comment-stripped source; the ``doc`` keyword of a stripped doc comment goes with it."""
    return re.sub(r"\bdoc\b\s*", "", strip_comments((ROOT / path).read_text(encoding="utf-8")))


def _governed_deploy_paths() -> tuple[str, ...]:
    from deployment.ask_viewer.entrypoint import _GOVERNED_MODEL_PATHS

    return _GOVERNED_MODEL_PATHS


def _glob(pattern: str) -> re.Pattern[str]:
    parts, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts) + r"\Z")


# -- boundary fence -----------------------------------------------------------------


def test_directory_is_outside_every_production_selector() -> None:
    for root in (*REVIEWED_ROOTS, *validate_sysml.MODEL_PATHS, *check_repo.SYSML_MODEL_PATHS):
        assert not MODEL.is_relative_to(root), root
    for root in DEFAULT_ROOTS:
        assert not MODEL.is_relative_to(Path(root)), root
    for governed in _governed_deploy_paths():
        if governed.startswith(":(glob)"):
            assert not _glob(governed[len(":(glob)"):]).match(MODEL.as_posix()), governed
        else:
            assert not MODEL.is_relative_to(Path(governed)), governed
    for root in check_naming.SYSML_MODEL_ROOTS:
        assert not (ROOT / MODEL).is_relative_to(root), root
    manifest = {source.path for source in BaselineManifest.discover(ROOT).sources}
    assert MODEL.as_posix() not in manifest
    assert not any(path.startswith(DIRECTORY.as_posix()) for path in manifest)
    assert (ROOT / MODEL).is_file()


def test_production_workflows_do_not_trigger_on_the_scope_alignment() -> None:
    for workflow in PRODUCTION_WORKFLOWS:
        triggers = yaml.safe_load((ROOT / workflow).read_text(encoding="utf-8"))[True]
        filters = triggers["pull_request"]["paths"]
        assert not any(_glob(pattern).match(MODEL.as_posix()) for pattern in filters), workflow
        assert not any(_glob(pattern).match((DIRECTORY / "README.md").as_posix()) for pattern in filters), workflow


def test_package_name_is_declared_exactly_once_in_the_tracked_models() -> None:
    tracked = [path for path in subprocess.run(
        ["git", "ls-files", "-z", "--", "*.sysml"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0") if path]
    assert MODEL.as_posix() in tracked, "the scope-alignment model must be tracked"
    declaration = re.compile(rf"^\s*(?:library\s+)?package\s+{PACKAGE}\b", re.MULTILINE)
    declared = [path for path in tracked if declaration.search(strip_comments((ROOT / path).read_text(encoding="utf-8")))]
    assert declared == [MODEL.as_posix()]
    assert PACKAGE not in check_repo.find_duplicate_global_packages(ROOT)


# -- textual shape ---------------------------------------------------------------------


def test_exactly_one_variability_with_two_alternatives_and_no_xor() -> None:
    code = _code(MODEL)
    assert code.count("#featureTree occurrence") == 1
    assert code.count("#featureModel occurrence def") == 1
    parents = re.findall(r"#feature occurrence (\w+)\[1\];", code)
    assert parents == ["vehiclePlatformIntegrationMode"]
    alternatives = re.findall(
        r"#feature occurrence (\w+)\[0\.\.1\] :> vehiclePlatformIntegrationMode default null;", code
    )
    assert sorted(alternatives) == ["aaosIntegrated", "standalone"]
    assert len(re.findall(r"#feature occurrence \w+\[", code)) == 3
    for forbidden in ("xorFeatures", "XORConstraint", "requiresFeatures", "RequiresConstraint",
                      "assert constraint", "bindingTime", "LifeCycleKind", "Production", "Operation"):
        assert forbidden not in code, forbidden


def test_member_configurations_and_invalid_probes() -> None:
    code = _code(MODEL)
    names = re.findall(r"#featureConfiguration occurrence (\w+)", code)
    assert sorted(names) == sorted(alignment.EXPECTED_OUTCOMES)
    bodies = {}
    for name in names:
        start = code.index(f"#featureConfiguration occurrence {name}")
        opening = code.index("{", start)
        closing = code.index("}", opening)
        bodies[name] = " ".join(code[opening + 1:closing].split())
    assert bodies["standaloneAutowareAEBSReferenceMemberConfiguration"] == (
        "#feature occurrence :>> vehiclePlatformIntegrationMode[1] = (standalone); "
        "#feature occurrence :>> standalone[1];")
    assert bodies["aaosIntegratedAutowareAEBSReferenceMemberConfiguration"] == (
        "#feature occurrence :>> vehiclePlatformIntegrationMode[1] = (aaosIntegrated); "
        "#feature occurrence :>> aaosIntegrated[1];")
    assert bodies["bothIntegrationModesProbe"] == (
        "#feature occurrence :>> vehiclePlatformIntegrationMode[1] = (standalone, aaosIntegrated); "
        "#feature occurrence :>> standalone[1]; #feature occurrence :>> aaosIntegrated[1];")
    assert bodies["noIntegrationModeProbe"] == "#feature occurrence :>> vehiclePlatformIntegrationMode[1];"
    for name in names:
        header = code[code.index(f"#featureConfiguration occurrence {name}"):]
        header = header[:header.index("{")]
        assert ":> vehiclePlatformIntegrationModeFeatureTree, featureConfigurations" in " ".join(header.split())


def test_one_binding_per_shared_asset_variant_and_one_feature_per_binding() -> None:
    code = _code(MODEL)
    bindings = re.findall(r"#FeatureBinding dependency (\w+)\s+from (\S+)\s+to (\S+);", code)
    assert len(bindings) == 8
    assert code.count("#FeatureBinding dependency") == 8
    clients = [client for _, client, _ in bindings]
    assert len(set(clients)) == 8, "every shared-asset variant is bound at most once"
    assert all(client.startswith("DE4SDV_SDVPlatformStack::SDVPlatformStack::") for client in clients)
    suppliers = [supplier for _, _, supplier in bindings]
    assert all("," not in endpoint for endpoint in clients + suppliers)
    by_feature = {feature: sorted(client.rsplit("::", 2)[1] + "::" + client.rsplit("::", 1)[1]
                                  for _, client, supplier in bindings if supplier == f"{TREE}::{feature}")
                  for feature in ("standalone", "aaosIntegrated")}
    assert by_feature["aaosIntegrated"] == sorted(
        ["middleware::androidSDV", "hypervisor::kvm", "osPlatform::android", "applicationMiddlewareAdapter::autowareToAAOSSDV"])
    assert by_feature["standalone"] == sorted(
        ["middleware::none", "hypervisor::none", "osPlatform::linux", "applicationMiddlewareAdapter::none"])
    # Common content carries no binding; its superset realization is a plain dependency.
    for _, client, _ in bindings:
        assert "InitialCommonCoreEngineeringContent" not in client
    assert re.search(
        r"(?<!#FeatureBinding )dependency commonAutowareApplicationRealizedByAutowareStack\s+"
        r"from DE4SDV_AEBSProductLineScope::InitialCommonCoreEngineeringContent::autowareApplication\s+"
        r"to DE4SDV_SDVPlatformStack::SDVPlatformStack::vehicleApplication::autoware;", code)
    assert code.count("#FeatureConfigurationBinding dependency") == 2


_DECLARATION_KEYWORDS = r"(?:(?:variation|variant|abstract|private|library)\s+)*(?:package|part|occurrence|item|attribute|dependency)"


def _declaration(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w:>])(?:#\w+\s+)?{_DECLARATION_KEYWORDS}\s+(?:def\s+)?{re.escape(name)}(?!\w)")


def _body_after(text: str, position: int) -> str:
    """The balanced-brace body that starts after ``position``; empty for a ``;`` declaration."""
    for index in range(position, len(text)):
        if text[index] == ";":
            return ""
        if text[index] == "{":
            depth = 0
            for end in range(index, len(text)):
                depth += {"{": 1, "}": -1}.get(text[end], 0)
                if depth == 0:
                    return text[index + 1:end]
            raise AssertionError("unbalanced braces")
    raise AssertionError("declaration without body or terminator")


def _resolve(reference: str, heads: dict[str, str]) -> None:
    head, *segments = reference.split("::")
    assert head in heads, f"unknown reference head in {reference}"
    match = _declaration(head).search(heads[head])
    assert match, f"{head} is not declared in its source"
    block = _body_after(heads[head], match.end())
    for index, segment in enumerate(segments):
        match = _declaration(segment).search(block)
        assert match, f"{reference}: {segment} is not declared inside {head}::{'::'.join(segments[:index])}"
        block = _body_after(block, match.end())


def test_every_qualified_reference_resolves_in_its_source() -> None:
    code = _code(MODEL)
    heads = {
        "DE4SDV_AEBSProductLineScope": _code(SCOPE),
        "DE4SDV_SDVPlatformStack": _code(PLATFORM),
        FEATURE_MODEL: code,
    }
    references = sorted(set(re.findall(r"\b[A-Za-z_]\w*(?:::[A-Za-z_]\w*)+", code)))
    assert references, "the model reaches the governed scope and the platform stack by qualified reference"
    assert any(reference.startswith("DE4SDV_AEBSProductLineScope::") for reference in references)
    assert any(reference.startswith("DE4SDV_SDVPlatformStack::") for reference in references)
    for reference in references:
        _resolve(reference, heads)


def test_a_renamed_target_fails_the_reference_check() -> None:
    code = _code(MODEL)
    platform = _code(PLATFORM).replace("variant part androidSDV", "variant part renamedSDV")
    heads = {"DE4SDV_AEBSProductLineScope": _code(SCOPE), "DE4SDV_SDVPlatformStack": platform, FEATURE_MODEL: code}
    with pytest.raises(AssertionError, match="androidSDV is not declared"):
        _resolve("DE4SDV_SDVPlatformStack::SDVPlatformStack::middleware::androidSDV", heads)


def test_names_follow_the_naming_conventions() -> None:
    text = (ROOT / MODEL).read_text(encoding="utf-8")
    assert check_naming.check_declaration_names_in_text(text, MODEL.as_posix()) == []
    assert re.fullmatch(r"[a-z][a-z0-9_]*\.sysml", MODEL.name)
    assert re.fullmatch(r"[a-z][a-z0-9-]*", DIRECTORY.name)
    assert re.search(rf"^package {PACKAGE} \{{", strip_comments(text), re.MULTILINE)
    assert "DE4SDV_AEBSProductLineScope::*" not in text, "no wildcard import of the governed scope"


# -- documentation ---------------------------------------------------------------------


def test_documentation_states_status_evidence_and_non_claims() -> None:
    doc = (ROOT / DOC).read_text(encoding="utf-8")
    readme = (ROOT / README).read_text(encoding="utf-8")
    for required in ("39167884450", "f967a519", "39114284825", "f1da5c0c", "38780181818", "03f7fd22",
                     "qualified: false", "intentional-representation", "INC-MW-011",
                     "pleml-gate-a-frozen", "pleml-1.0.0-frozen", "pleml-1.1.0-frozen",
                     "not an authority", "privileged-ple-scope-alignment.yml",
                     "no XOR", "Development", "No PLEML adoption", "No compliance"):
        assert required in doc, required
    assert "linuxROS2AutowareRuntime" in doc
    assert "ple-s-scope-alignment.md" in readme
    assert "experiment" in readme.lower()
    assert "qualified: false" in readme
    tree = (ROOT / "docs/repository-tree.md").read_text(encoding="utf-8")
    assert "pleml-scope-alignment" in tree
