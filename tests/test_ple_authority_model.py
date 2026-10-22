"""Production surface, shape and closed-world checks of the PLEML feature models (ADR 0022).

The PLEML feature models (``feature-models/*.sysml``) and their configurations
(``feature-configurations/**/*.sysml``) are the product-line authority since
the switch (ADR 0022, step S6), and since step S7 the only product-line
source: the YAML catalogues and Bills-of-Features they restated retired. These
checks read the model text: they pin the reviewed shape so that a rename or a
drift fails here before the licensed run, and the closed-world and admission
checks evaluate the stated semantics on that text. The privileged PLE
authority workflow (licensed validation, serialization, API round trip) is the
validator, and the evaluator of step S2 owns the semantics. They pin:

- the production surface: every production selector reads the PLEML
  documents, and the fixtures stay out of the export and the served model;
- the shape of each feature model: one feature ID per feature, no element for
  common content (decision 2), the groups and their multiplicities, the
  Development binding time and the unassigned binding times;
- the agreement check over the twelve application-middleware pairs: exactly
  one derivation rule for each allowed pair and exactly one exclusion for each
  unsupported one;
- the exclusions and the requires constraints of the SDV product line;
- the complement check of the allowed lists of C001 and C003, and of C002's;
- the closed world: on every structurally valid selection, the model's
  groups, constraints and rules give the reviewed table of verdicts, which
  the DE4SDV evaluator reproduced on the same tree (INC-MW-011 phase 9);
- one feature binding per shared-asset variant, the correspondences, the
  projection metadata and the configurations' shape;
- the admission of each configuration by the stated reading of the
  correspondences.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
import subprocess
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import yaml

from de4sdv.sysml_api.baseline import PINNED_DEPENDENCIES, REVIEWED_ROOTS, BaselineManifest
from scripts import check_naming, check_repo, run_ple_authority as runner, validate_sysml
from sysml_shapes import strip_comments
from tools.sysml_html_viewer.generate import DEFAULT_ROOTS

ROOT = Path(__file__).resolve().parents[1]
_CONFIGURATOR = importlib.util.spec_from_file_location("_ple_authority_configurator", ROOT / "tools/configure_variant.py")
assert _CONFIGURATOR is not None and _CONFIGURATOR.loader is not None
configurator = importlib.util.module_from_spec(_CONFIGURATOR)
_CONFIGURATOR.loader.exec_module(configurator)

PLE = Path("model-based-product-line-engineering")
FEATURE_MODELS_DIR = PLE / "feature-models"
CONFIGURATIONS_DIR = PLE / "feature-configurations"
SCOPE = PLE / "scoping/de4sdv_aebs_product_line_scope.sysml"
PLEML_FILES = (*runner.AUTHORITY_SOURCES, *runner.FIXTURES)
PRODUCTION_WORKFLOWS = (
    ".github/workflows/privileged-syside-validation.yml",
    ".github/workflows/method-check.yml",
    ".github/workflows/privileged-full-model-api-ingestion.yml",
    ".github/workflows/deploy-public-sysml-api.yml",
)
SUPERSETS = {"DE4SDV_SDVPlatformStack": Path("textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"),
             "DE4SDV_ExecutionEnvironments": Path("textual-notation-of-model/packages/architecture/execution_environments.sysml")}


@dataclass(frozen=True)
class Family:
    model: Path
    package: str
    tree: str
    feature_model: str
    #: The governed element the root feature corresponds to, when the whole family is classified.
    root_correspondence: str | None


FAMILIES = {
    "sdv": Family(FEATURE_MODELS_DIR / "sdv_product_line.sysml", "DE4SDV_SDVProductLineFeatureModel",
                  "SDVProductLineFeatureTree", "SDVProductLineFeatureModel", None),
    "engineering": Family(
        FEATURE_MODELS_DIR / "engineering_execution_environments.sysml",
        "DE4SDV_EngineeringExecutionEnvironmentFeatureModel", "EngineeringExecutionEnvironmentFeatureTree",
        "EngineeringExecutionEnvironmentFeatureModel", "ExcludedSystem2ConcernSet::engineeringExecutionEnvironments"),
    "vehicle": Family(
        FEATURE_MODELS_DIR / "vehicle_execution_environments.sysml",
        "DE4SDV_VehicleTargetExecutionEnvironmentFeatureModel", "VehicleTargetExecutionEnvironmentFeatureTree",
        "VehicleTargetExecutionEnvironmentFeatureModel", "DeferredVariabilitySet::vehicleRuntimeVariability"),
}
#: The projection metadata of each feature model: the package, owner and label of the projections that
#: its configurations generate.
PROJECTIONS = {
    "sdv": ("DE4SDV_SDVPlatformStack", "SDVPlatformStack", "platform-stack"),
    "engineering": ("DE4SDV_ExecutionEnvironments", "EngineeringExecutionEnvironment",
                    "engineering execution-environment"),
    "vehicle": ("DE4SDV_ExecutionEnvironments", "VehicleTargetExecutionEnvironment",
                "vehicle-target execution-environment"),
}
#: The features whose binding time is not decided: the five capabilities of the SDV product line.
UNASSIGNED = {
    "sdv": {"F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION", "F-CAPABILITY-AEBS-BICYCLE-DETECTION",
            "F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL", "F-CAPABILITY-LANE-KEEP-ASSIST", "F-CAPABILITY-HMI-DISPLAY"},
    "engineering": set(),
    "vehicle": set(),
}
#: The SDV exclusions with a constraint ID: (owner, excluded features). The pair exclusions of Openpilot
#: and Apollo carry no ID; the agreement check covers them.
SDV_EXCLUSIONS = {
    "C001": ("eclipseSCORE", {"android"}),
    "C003": ("autosarAdaptive", {"android"}),
    "C004": ("acrn", {"qnx"}),
    "C005": ("kvm", {"qnx"}),
}
#: The SDV requires constraints of INC-MW-011 phase 9: (owner, required features). Each requires
#: constraint states its rule exactly, so it needs no allowed list and no complement check.
SDV_REQUIRES = {
    "C007": ("noHypervisor", {"noGuestOS"}),
    "C008": ("guestAndroidSDV", {"guestAndroid"}),
    "C009": ("androidSDV", {"guestAndroidSDV"}),
    "C010": ("hmiDisplay", {"guestAndroidSDV"}),
    "C011": ("autoware", {"linux"}),
}

#: The correspondences of the SDV features to the governed scope, by feature ID: the
#: retired PLE-S catalogue correspondence restated feature by feature, plus the PLE-S
#: derived-realization bindings (a derived realization corresponds to its admitted
#: alternative) and the common realization of Autoware. C- nodes have none (decision 2).
#: Since INC-MW-011 phase 9 the guest choices carry the split topology of the
#: AAOS-integrated alternative, and Linux corresponds to the common runtime only.
SDV_CORRESPONDENCES = {
    "F-PLATFORM-VEHICLE-APPLICATION": {"DeferredVariabilitySet::drivingStackVariability"},
    "F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE": {"InitialCommonCoreEngineeringContent::autowareApplication"},
    "F-PLATFORM-VEHICLE-APPLICATION-OPENPILOT": {"ReferenceOnlyAlternativeSet::openpilot"},
    "F-PLATFORM-VEHICLE-APPLICATION-APOLLO": {"ReferenceOnlyAlternativeSet::apollo"},
    "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE": {"ReferenceOnlyAlternativeSet::eclipseSCORE"},
    "F-PLATFORM-MIDDLEWARE-ANDROID-SDV": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-MIDDLEWARE-AUTOSAR-ADAPTIVE": {"ReferenceOnlyAlternativeSet::autosarAdaptive"},
    "F-PLATFORM-MIDDLEWARE-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-PLATFORM-OS-LINUX": {"InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime"},
    "F-PLATFORM-OS-QNX": {"ReferenceOnlyAlternativeSet::qnxQVM"},
    "F-PLATFORM-HYPERVISOR-QVM": {"ReferenceOnlyAlternativeSet::qnxQVM"},
    "F-PLATFORM-HYPERVISOR-ACRN": {"ReferenceOnlyAlternativeSet::acrn"},
    "F-PLATFORM-HYPERVISOR-KVM": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-HYPERVISOR-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-PLATFORM-GUEST-OS-ANDROID": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-GUEST-OS-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-PLATFORM-GUEST-MIDDLEWARE-ANDROID-SDV": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-GUEST-MIDDLEWARE-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-SENSING-PERCEPTION": {"DeferredVariabilitySet::sensingVariability"},
    "F-SENSING-PERCEPTION-LIDAR": {"InitialCommonCoreEngineeringContent::currentSensingBaseline"},
    "F-SENSING-PERCEPTION-RADAR": {"DeferredVariabilitySet::sensingVariability"},
    "F-SENSING-PERCEPTION-CAMERA": {"InitialCommonCoreEngineeringContent::currentSensingBaseline"},
    "F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION": {"DeferredVariabilitySet::expandedAEBSCapabilityVariability"},
    "F-CAPABILITY-AEBS-BICYCLE-DETECTION": {"DeferredVariabilitySet::expandedAEBSCapabilityVariability"},
}
#: Features with no governed-scope element of their own: the grouping features, the
#: middleware, operating-system, hypervisor and guest groups, two catalogue candidates,
#: main-side Android and the HMI display.
SDV_WITHOUT_CORRESPONDENCE = {
    "F-PLATFORM-STACK", "F-PLATFORM-MIDDLEWARE", "F-PLATFORM-OS", "F-PLATFORM-HYPERVISOR", "F-PLATFORM-GUEST-OS",
    "F-PLATFORM-GUEST-MIDDLEWARE", "F-SENSING", "F-CAPABILITIES", "F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL",
    "F-CAPABILITY-LANE-KEEP-ASSIST", "F-PLATFORM-OS-ANDROID", "F-CAPABILITY-HMI-DISPLAY",
}
ALLOWED_LIST = re.compile(r"Allowed operating systems: ([a-zA-Z0-9]+(?:, [a-zA-Z0-9]+)*)\.")
#: The allowed-list rules and where their reviewed list is recorded: the rationale of the
#: exclusion (C001, C003), or the rationale comment of the dropped rule's premise (C002).
ALLOWED_LIST_RULES = {"C001": "C001", "C003": "C003", "C002": "androidSDV"}


# -- a lexical reader of the reviewed shapes --------------------------------------------------


def _raw(path: Path | str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _code(path: Path | str) -> str:
    """Comment-stripped source; the ``doc`` keyword of a stripped doc comment goes with it."""
    return re.sub(r"\bdoc\b\s*", "", strip_comments(_raw(path)))


def _braced(text: str, opening: int) -> tuple[str, int]:
    """The body of the brace at ``opening`` and the index after its closing brace."""
    assert text[opening] == "{"
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[opening + 1:index], index + 1
    raise AssertionError("unbalanced braces")


_FEATURE = re.compile(
    r"#feature (?P<unassigned>#UnassignedBindingTime )?occurrence <'(?P<id>[^']+)'> (?P<name>\w+)\[(?P<mult>[^\]]+)\]"
    r"(?: :> (?P<parent>\w+))?(?P<default> default null)?\s*(?P<end>[;{])"
)
_CONSTRAINT = re.compile(
    r"assert constraint (?:<'(?P<id>[^']+)'> )?(?P<name>\w+) :> (?P<kind>xorFeatures|requiresFeatures|impliesFeatures)"
    r"\s*\{\s*in occurrence constrainedFeatures = new FeatureOperand\(that, (?P<operand>\([^()]*\)|[\w:]+)\);\s*\}"
)
_DEPENDENCY = re.compile(
    r"(?:#(?P<metadata>\w+) )?dependency (?:<'(?P<short>[^']+)'> )?(?P<name>\w+)\s+from (?P<client>[\w:]+)"
    r"\s+to (?P<suppliers>[\w:]+(?:\s*,\s*[\w:]+)*);"
)


@dataclass
class Feature:
    id: str
    name: str
    multiplicity: str
    parent: str | None
    default_null: bool
    unassigned: bool
    path: tuple[str, ...]
    constraints: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class Dependency:
    metadata: str | None
    short: str | None
    name: str
    client: str
    suppliers: tuple[str, ...]


def _written_operands(text: str) -> tuple[tuple[str, ...], ...]:
    """The operands as written: each a name, or a qualified name split at ``::``."""
    return tuple(tuple(segment.strip() for segment in part.strip().split("::")) for part in text.strip("()").split(","))


def _operands(text: str) -> tuple[str, ...]:
    """The names of the operands; feature names are unique within a tree (``_by_name``)."""
    return tuple(written[-1] for written in _written_operands(text))


def _without_nested_features(text: str) -> str:
    parts, position = [], 0
    while (match := _FEATURE.search(text, position)) is not None:
        parts.append(text[position:match.start()])
        position = match.end() if match["end"] == ";" else _braced(text, match.end() - 1)[1]
    parts.append(text[position:])
    return "".join(parts)


def _features(body: str, path: tuple[str, ...] = ()) -> list[Feature]:
    found, position = [], 0
    while (match := _FEATURE.search(body, position)) is not None:
        inner, position = ("", match.end()) if match["end"] == ";" else _braced(body, match.end() - 1)
        own = _without_nested_features(inner)
        constraints = [{"id": c["id"], "name": c["name"], "kind": c["kind"], "operands": _operands(c["operand"]),
                        "written": _written_operands(c["operand"])}
                       for c in _CONSTRAINT.finditer(own)]
        assert own.count("assert constraint") == len(constraints), f"an unreviewed constraint form in {match['name']}"
        feature = Feature(match["id"], match["name"], match["mult"], match["parent"], bool(match["default"]),
                          bool(match["unassigned"]), (*path, match["name"]), constraints)
        found.append(feature)
        found.extend(_features(inner, feature.path))
    return found


def _tree(family: Family) -> tuple[str, list[Feature]]:
    code = _code(family.model)
    match = re.search(rf"#featureTree occurrence def <'(?P<id>[^']+)'> {family.tree}\s*\{{", code)
    assert match, family.tree
    body, _end = _braced(code, match.end() - 1)
    assert body.count("#feature ") == len(_features(body)), "an unreviewed feature form"
    return match["id"], _features(body)


def _dependencies(path: Path | str) -> list[Dependency]:
    code = _code(path)
    found = [Dependency(m["metadata"], m["short"], m["name"], m["client"],
                        tuple(part.strip() for part in m["suppliers"].split(",")))
             for m in _DEPENDENCY.finditer(code)]
    assert len(found) == len(re.findall(r"\bdependency\b", code)), "an unreviewed dependency form"
    return found


def _by_id(features: list[Feature]) -> dict[str, Feature]:
    index = {feature.id: feature for feature in features}
    assert len(index) == len(features), "a catalogue ID is the short name of more than one feature"
    return index


def _by_name(features: list[Feature]) -> dict[str, Feature]:
    index = {feature.name: feature for feature in features}
    assert len(index) == len(features), "feature names repeat within a tree"
    return index


def _qualified(family: Family, feature: Feature) -> str:
    return "::".join((family.tree, *feature.path))


def _variants(superset: Path, owner: str, variation: str) -> set[str]:
    code = _code(superset)
    owner_match = re.search(rf"\bpart def {owner}\b[^{{;]*\{{", code)
    assert owner_match, owner
    body, _end = _braced(code, owner_match.end() - 1)
    variation_match = re.search(rf"\bvariation part {variation}\b[^{{;]*\{{", body)
    assert variation_match, variation
    inner, _end = _braced(body, variation_match.end() - 1)
    # A variant is a part, or a reference part such as the AAOS SDV partner of middleware.
    return set(re.findall(r"\bvariant (?:ref )?part (\w+)", inner))


def _owned_metadata(body: str, metadata: str) -> list[dict[str, str]]:
    """The ``@<metadata> { name = "value"; }`` blocks that ``body`` owns directly, as attribute maps.

    Kernel metadata sits in the body of the element it annotates; a block
    nested in a member of that element annotates the member instead.
    """
    found = []
    for match in re.finditer(rf"@{metadata}\s*\{{", body):
        prefix = body[:match.start()]
        if prefix.count("{") != prefix.count("}"):
            continue
        inner, _end = _braced(body, match.end() - 1)
        found.append(dict(re.findall(r'(\w+) = "([^"]*)";', inner)))
    return found


#: Metadata applied from outside the annotated element: ``@M about X`` or ``metadata m : M about X``.
_METADATA_ABOUT = re.compile(r"(?:@\s*[\w:]+|\bmetadata\s+(?:\w+\s*)?:\s*[\w:]+)\s+about\b")


# -- the production surface (the switch, ADR 0022 step S6) ------------------------------------


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


def _governed_deploy_paths() -> tuple[str, ...]:
    from deployment.ask_viewer.entrypoint import _GOVERNED_MODEL_PATHS

    return _GOVERNED_MODEL_PATHS


@pytest.fixture(scope="module")
def production_selection() -> dict[str, frozenset[str]]:
    """The repository-relative model files each production selector reads.

    The repository check and the R003 check of the model sync read the same
    roots; their fixture exclusion is tested on synthetic trees
    (``tests/test_check_repo.py``, ``tests/test_check_model_sync.py``).
    """
    from tools.sysml_html_viewer.model_parse import model_paths

    governed = subprocess.run(["git", "ls-files", "-z", "--", *_governed_deploy_paths()], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.split("\0")
    return {
        "export (API baseline)": frozenset(source.path for source in BaselineManifest.discover(ROOT).sources
                                           if source.authority == "reviewed"),
        "licensed validation (validate_sysml)": frozenset(
            path.relative_to(ROOT).as_posix() for model_path in validate_sysml.MODEL_PATHS
            for path in validate_sysml.model_files(ROOT, model_path)),
        "naming (declarations)": frozenset(path.relative_to(ROOT).as_posix()
                                           for path in check_naming.iter_declaration_model_files()),
        "viewer": frozenset(path.relative_to(ROOT).as_posix() for path in model_paths(ROOT, DEFAULT_ROOTS)),
        "drift gate of the served model": frozenset(path for path in governed if path),
    }


@pytest.mark.parametrize("path", runner.AUTHORITY_SOURCES)
def test_every_authority_source_is_a_model_file_of_every_production_selector(
        path: str, production_selection: dict[str, frozenset[str]]) -> None:
    """Since the switch the feature models and the member configurations are model
    files of every production selector: the export, the licensed validation, the
    naming checks, the viewer and the drift gate of the served model."""
    model = Path(path)
    assert (ROOT / model).is_file(), path
    for roots in (REVIEWED_ROOTS, validate_sysml.MODEL_PATHS, check_repo.SYSML_MODEL_PATHS):
        assert any(model.is_relative_to(root) for root in roots), roots
    assert any((ROOT / model).is_relative_to(root) for root in check_naming.SYSML_MODEL_ROOTS)
    for selector, files in production_selection.items():
        assert path in files, selector
    assert not check_naming._is_exempt_sysml(ROOT / model)


@pytest.mark.parametrize("path", runner.FIXTURES)
def test_no_fixture_is_a_model_file_of_a_production_selector(
        path: str, production_selection: dict[str, frozenset[str]]) -> None:
    """The invalid configuration and the parity probes are fixtures: the PLE
    authority job validates, serializes and evaluates them, and no production
    selector reads them; the export (#405 R14), the licensed validation, the
    repository and naming checks, the viewer and the drift gate leave them out
    (#411 R5)."""
    from scripts import list_view_folders

    assert (ROOT / path).is_file(), path
    for selector, files in production_selection.items():
        assert path not in files, selector
    assert check_naming._is_exempt_sysml(ROOT / path)
    assert not any(path.startswith(folder + "/") for folder in list_view_folders.view_folders())
    assert not configurator.served_configuration({"source": path})


@pytest.mark.parametrize("path", runner.CONFIGURATIONS)
def test_the_configurator_projects_every_member_configuration(path: str) -> None:
    assert configurator.served_configuration({"source": path})


def test_the_licensed_validation_leaves_out_the_fixtures() -> None:
    """The check, the diagrams and the grid views of the licensed validation exclude
    the fixtures, as the wrapper does; the PLE authority job validates them."""
    steps = yaml.safe_load(_raw(".github/workflows/privileged-syside-validation.yml"))["jobs"]["syside-validation"]["steps"]
    commands = {}
    for step in steps:
        run = " ".join(re.sub(r"\\\n\s*", " ", step.get("run") or "").split())
        for command in ("syside check", "syside viz view", "syside table export"):
            if command in run:
                commands[command] = run
    assert sorted(commands) == ["syside check", "syside table export", "syside viz view"]
    for command, run in commands.items():
        assert '--exclude "**/fixtures/**"' in run, command
    assert validate_sysml.check_command("syside")[-2:] == ["--exclude", "**/fixtures/**"]


def test_the_pinned_library_is_the_one_pleml_dependency_of_the_api_baseline() -> None:
    from de4sdv.semantic import pleml_package

    pins = [dependency for dependency in PINNED_DEPENDENCIES if "pleml" in dependency.as_posix().lower()]
    assert pins == [pleml_package.LIBRARY_PATH]


@pytest.mark.parametrize("workflow", PRODUCTION_WORKFLOWS)
def test_production_workflows_trigger_on_the_pleml_files_and_read_them_through_their_roots(workflow: str) -> None:
    """A pull request that changes a PLEML file gets the licensed validation and the
    method check; no production workflow names a PLEML file, it reads the roots."""
    text = _raw(workflow)
    filters = (yaml.safe_load(text)[True].get("pull_request") or {}).get("paths") or []
    for path in PLEML_FILES:
        assert path not in text, (workflow, path)
        if filters:
            assert any(_glob(pattern).match(path) for pattern in filters), (workflow, path)


def test_the_runner_lists_every_pleml_file_and_only_those() -> None:
    present = {path.relative_to(ROOT).as_posix()
               for directory in (FEATURE_MODELS_DIR, CONFIGURATIONS_DIR)
               for path in (ROOT / directory).rglob("*.sysml")}
    assert present == set(PLEML_FILES)
    assert len(PLEML_FILES) == len(set(PLEML_FILES))
    assert set(runner.FEATURE_MODELS) == {family.model.as_posix() for family in FAMILIES.values()}
    assert all("/fixtures/" in path for path in runner.FIXTURES)
    assert not any("/fixtures/" in path for path in runner.AUTHORITY_SOURCES)


def _tracked_sysml() -> list[str]:
    return [path for path in subprocess.run(
        ["git", "ls-files", "-z", "--", "*.sysml"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0") if path]


def test_every_pleml_file_declares_one_unique_package() -> None:
    declaration = re.compile(r"^\s*(?:library\s+)?package\s+(\w+)\b", re.MULTILINE)
    owners: dict[str, list[str]] = {}
    for path in {*_tracked_sysml(), *PLEML_FILES}:
        for name in declaration.findall(strip_comments(_raw(path))):
            owners.setdefault(name, []).append(path)
    for path in PLEML_FILES:
        names = declaration.findall(strip_comments(_raw(path)))
        assert len(names) == 1, path
        assert owners[names[0]] == [path], names[0]


def test_only_the_pleml_files_import_the_pleml_library() -> None:
    importing = {path for path in {*_tracked_sysml(), *PLEML_FILES}
                 if re.search(r"\bimport\s+PLEML::", strip_comments(_raw(path)))}
    assert importing == set(PLEML_FILES)


def test_the_pleml_files_are_the_model_files_of_the_import_roots() -> None:
    """The confinement of step S1: the import roots of the package record hold exactly
    the files the authority job validates, the fixture included."""
    from de4sdv.semantic import pleml_package

    under = {path.relative_to(ROOT).as_posix() for root in pleml_package.IMPORT_ROOTS
             for path in (ROOT / root).rglob("*.sysml")}
    assert under == set(PLEML_FILES)
    assert not any(path.startswith("model-based-product-line-engineering/pleml-scope-alignment/")
                   for path in pleml_package.IMPORT_EXEMPTIONS), "S3 retired the PLE-S model and its exemption"


@pytest.mark.parametrize("path", PLEML_FILES)
def test_the_pleml_files_follow_the_naming_rules(path: str) -> None:
    text = _raw(path)
    assert check_naming.check_declaration_names_in_text(text, path) == []
    assert check_naming.check_identifier_tokens_in_text(text, path, ".sysml") == []




# -- the shape of the feature models ---------------------------------------------------------------


def test_the_yaml_product_line_layer_is_retired() -> None:
    """Since S7 no YAML catalogue and no Bill-of-Features exists; the evidence records are YAML."""
    assert not list((ROOT / FEATURE_MODELS_DIR).rglob("*.yaml"))
    assert {path.parent.relative_to(ROOT).as_posix() for path in (ROOT / CONFIGURATIONS_DIR).rglob("*.yaml")} <= {
        (CONFIGURATIONS_DIR / "evidence").as_posix()}


@pytest.mark.parametrize("name", FAMILIES)
def test_every_feature_has_one_feature_id_and_common_content_has_no_element(name: str) -> None:
    """Each feature carries one F- ID and the tree a PL- ID. A C- ID names a constraint only: common
    capabilities have no feature and no element (ADR 0022, decision 2)."""
    family = FAMILIES[name]
    tree_id, features = _tree(family)
    assert tree_id.startswith("PL-")
    _by_name(features)
    index = _by_id(features)
    assert all(identifier.startswith("F-") for identifier in index), sorted(index)
    constraint_ids = {constraint["id"] for feature in features for constraint in feature.constraints
                      if constraint["id"]}
    derivations = {dependency.short for dependency in _dependencies(family.model)
                   if dependency.metadata == "DerivedVariation"}
    assert all(identifier.startswith("D-") for identifier in derivations)
    assert set(re.findall(r"<'([^']+)'>", _code(family.model))) == {tree_id, *index, *constraint_ids, *derivations}
    assert all(identifier.startswith("C") for identifier in constraint_ids)


@pytest.mark.parametrize("name", FAMILIES)
def test_the_groups_and_multiplicities_keep_the_reviewed_shape(name: str) -> None:
    """A group member is a [0..1] feature with default null that subsets its group and is its sibling.
    A group is [1] (exactly one member) or [1..*] (at least one). Any other feature is a [1] grouping
    feature or a [0..1] optional feature with default null."""
    features = _tree(FAMILIES[name])[1]
    by_name = _by_name(features)
    groups = {feature.parent for feature in features if feature.parent}
    for feature in features:
        if feature.parent is not None:
            assert (feature.multiplicity, feature.default_null) == ("0..1", True), feature.id
            assert feature.path[:-1] == by_name[feature.parent].path[:-1], feature.id
        elif feature.name in groups:
            assert (feature.multiplicity, feature.default_null) in {("1", False), ("1..*", False)}, feature.id
        else:
            assert (feature.multiplicity, feature.default_null) in {("1", False), ("0..1", True)}, feature.id
    assert all(by_name[group].parent is None for group in groups), "a group member is no group"


def test_pedestrian_and_bicycle_detection_move_under_capabilities() -> None:
    index = _by_id(_tree(FAMILIES["sdv"])[1])
    for identifier in ("F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION", "F-CAPABILITY-AEBS-BICYCLE-DETECTION"):
        assert index[identifier].path[:-1] == ("capabilities",)


@pytest.mark.parametrize("name", FAMILIES)
def test_every_feature_keeps_the_development_binding_time_and_no_implies_exists(name: str) -> None:
    code = _code(FAMILIES[name].model)
    for forbidden in ("bindingTime", "LifeCycleKind", "impliesFeatures", "ImpliesConstraint", "#featureConfiguration"):
        assert forbidden not in code, forbidden


@pytest.mark.parametrize("name", FAMILIES)
def test_unassigned_binding_time_marks_exactly_the_reviewed_features(name: str) -> None:
    family = FAMILIES[name]
    features = _tree(family)[1]
    assert {feature.id for feature in features if feature.unassigned} == UNASSIGNED[name]
    # A feature that a binding, a derived variation or a rule names has a decided binding time.
    named = {supplier for dependency in _dependencies(family.model) if dependency.metadata
             for supplier in dependency.suppliers}
    assert not any(_qualified(family, feature) in named for feature in features if feature.unassigned)


# -- constraints, the agreement check and the complement check ---------------------------------------


def _exclusions(by_name: dict[str, Feature]) -> list[tuple[Feature, dict]]:
    return [(feature, constraint) for feature in by_name.values() for constraint in feature.constraints
            if constraint["kind"] == "xorFeatures"]



def test_the_sdv_exclusions_are_the_reviewed_constraints() -> None:
    """C001, C003, C004 and C005 are exclusions, each owned by one choice and excluding choices of another
    group; C002 and C006 are dropped rules with no constraint (below). Every SDV constraint is an exclusion
    or one of the reviewed requires constraints; no implies constraint exists."""
    by_name = _by_name(_tree(FAMILIES["sdv"])[1])
    identified = {constraint["id"]: (owner.name, set(constraint["operands"]))
                  for owner, constraint in _exclusions(by_name) if constraint["id"]}
    assert identified == SDV_EXCLUSIONS
    for identifier, (owner, excluded) in identified.items():
        group = by_name[owner].parent
        assert group and all(by_name[name].parent not in (None, group) for name in excluded), identifier
    kinds = Counter(constraint["kind"] for feature in by_name.values() for constraint in feature.constraints)
    assert kinds == {"xorFeatures": len(SDV_EXCLUSIONS) + 2, "requiresFeatures": len(SDV_REQUIRES)}, kinds


def test_the_sdv_requires_constraints_are_the_reviewed_constraints() -> None:
    """C007 to C011 (INC-MW-011 phase 9) are requires constraints, each with its constraint ID, owned by one
    feature and requiring one choice of another group: the guest side, its hypervisor, the AAOS SDV partner,
    the HMI display and Autoware's Linux. Each owner other than the HMI display is a choice of a group."""
    by_name = _by_name(_tree(FAMILIES["sdv"])[1])
    identified = {constraint["id"]: (owner.name, set(constraint["operands"]))
                  for owner in by_name.values() for constraint in owner.constraints
                  if constraint["kind"] == "requiresFeatures"}
    assert identified == SDV_REQUIRES
    for identifier, (owner, required) in identified.items():
        [operand] = required
        assert by_name[operand].parent not in (None, by_name[owner].parent), identifier
        assert by_name[owner].parent or by_name[owner].path[:-1] == ("capabilities",), identifier


def test_every_constraint_operand_names_a_feature_its_owner_can_see() -> None:
    """A name resolves in an enclosing namespace of the constraint, and a qualified name walks down from
    one: C010, owned by the HMI display under capabilities, names platformStack::guestAndroidSDV."""
    for name, family in FAMILIES.items():
        by_name = _by_name(_tree(family)[1])
        for owner in by_name.values():
            for constraint in owner.constraints:
                for written, operand in zip(constraint["written"], constraint["operands"]):
                    path = by_name[operand].path
                    assert path[-len(written):] == written, (name, constraint["name"], written)
                    scope = path[:-len(written)]
                    assert owner.path[:len(scope)] == scope, (name, constraint["name"], written)
    hmi_display = _by_name(_tree(FAMILIES["sdv"])[1])["hmiDisplay"]
    assert [constraint["written"] for constraint in hmi_display.constraints] == [(("platformStack",
                                                                                   "guestAndroidSDV"),)]


#: The interface usages of SDVPlatformStack after the W1 re-wiring of INC-MW-011 phase 9: (first end,
#: second end). S-CORE and AUTOSAR Adaptive connect to the main-side OS through their variants, the guest
#: middleware to the guest OS, and only the guest OS to the guest port of the hypervisor.
SUPERSET_WIRING = {
    "applicationMiddlewareBoundary": ("vehicleApplication.middlewarePort", "applicationMiddlewareAdapter.applicationPort"),
    "adapterMiddlewareBoundary": ("applicationMiddlewareAdapter.middlewarePort", "middleware.applicationPort"),
    "eclipseSCOREOSBoundary": ("middleware::eclipseSCORE.osPort", "osPlatform.middlewarePort"),
    "autosarAdaptiveOSBoundary": ("middleware::autosarAdaptive.osPort", "osPlatform.middlewarePort"),
    "guestMiddlewareOSBoundary": ("guestMiddleware.osPort", "guestOSPlatform.middlewarePort"),
    "guestOSHypervisorBoundary": ("guestOSPlatform.hypervisorPort", "hypervisor.guestPort"),
    "hypervisorHardwareBoundary": ("hypervisor.hypervisorPort", "hardware.hypervisorPort"),
}


def test_the_superset_wiring_says_where_each_layer_runs() -> None:
    """W1: no projection says that AAOS SDV runs on the main side, or that the main side is a KVM guest. The
    projections inherit the interfaces of SDVPlatformStack, so the superset may connect the middleware that
    the vehicle application integrates with to the main-side OS only through the variants that run there,
    and only the guest OS to the guest port. The AAOS SDV partner refers to the guest's AAOS SDV, so a
    product model holds one AAOS SDV instance."""
    code = _code(SUPERSETS["DE4SDV_SDVPlatformStack"])
    owner = re.search(r"\bpart def SDVPlatformStack\b[^{;]*\{", code)
    assert owner
    body, _end = _braced(code, owner.end() - 1)
    wiring = {match[1]: (match[2], match[3]) for match in re.finditer(
        r"\binterface (\w+) : \w+\s+connect ([\w:.]+) to ([\w:.]+);", body)}
    assert len(wiring) == len(re.findall(r"\binterface\b", body)), "an unreviewed interface form"
    assert wiring == SUPERSET_WIRING
    ends = [end for pair in wiring.values() for end in pair]
    assert "osPlatform.hypervisorPort" not in ends, "the main-side OS is not connected to the guest port"
    assert not any(end.startswith("middleware.") and other.startswith("osPlatform.")
                   for end, other in wiring.values()), "the partner middleware has no unconditional main-side OS"
    middleware = re.search(r"\bvariation part middleware\b[^{;]*\{", body)
    assert middleware
    variants, _end = _braced(body, middleware.end() - 1)
    assert re.findall(r"\bvariant ref part (\w+) : (\w+) references ([\w:]+);", variants) == [
        ("androidSDV", "AndroidSDVMiddleware", "guestMiddleware::androidSDV")]
    for variation, expected in (("guestOSPlatform", {"android", "none"}), ("guestMiddleware", {"androidSDV", "none"})):
        assert _variants(SUPERSETS["DE4SDV_SDVPlatformStack"], "SDVPlatformStack", variation) == expected


def test_the_derived_variation_and_its_rules_target_the_superset_and_no_binding() -> None:
    family = FAMILIES["sdv"]
    dependencies = _dependencies(family.model)
    [derived] = [dependency for dependency in dependencies if dependency.metadata == "DerivedVariation"]
    client = "DE4SDV_SDVPlatformStack::SDVPlatformStack::applicationMiddlewareAdapter"
    assert (derived.short, derived.client, derived.suppliers) == (
        "D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER", client,
        (f"{family.tree}::platformStack::vehicleApplication", f"{family.tree}::platformStack::middleware"))
    rules = [dependency for dependency in dependencies if dependency.metadata == "DerivationRule"]
    assert rules and not any(rule.short for rule in rules)
    assert all(rule.client.rsplit("::", 1)[0] == client for rule in rules)
    variants = _variants(SUPERSETS["DE4SDV_SDVPlatformStack"], "SDVPlatformStack", "applicationMiddlewareAdapter")
    assert {rule.client.rsplit("::", 1)[1] for rule in rules} <= variants
    # A derived variant is never a feature: no binding targets the derived variation.
    assert not any(dependency.client.startswith(client) for dependency in dependencies
                   if dependency.metadata == "FeatureBinding")


def test_the_agreement_check_covers_all_twelve_pairs_exactly_once() -> None:
    family = FAMILIES["sdv"]
    by_name = _by_name(_tree(family)[1])
    applications = {_qualified(family, feature) for feature in by_name.values() if feature.parent == "vehicleApplication"}
    middlewares = {_qualified(family, feature) for feature in by_name.values() if feature.parent == "middleware"}
    rules = [dependency for dependency in _dependencies(family.model) if dependency.metadata == "DerivationRule"]
    covered: dict[tuple[str, str], list[str]] = {}
    for rule in rules:
        assert len(rule.suppliers) == 2, rule.name
        application, middleware = rule.suppliers
        assert application in applications and middleware in middlewares, rule.name
        covered.setdefault((application, middleware), []).append(f"rule {rule.name}")
    exclusion_owners = 0
    for owner, constraint in _exclusions(by_name):
        if _qualified(family, owner) not in applications:
            continue
        exclusion_owners += 1
        assert constraint["id"] is None, constraint["name"]
        for name in constraint["operands"]:
            assert _qualified(family, by_name[name]) in middlewares, name
            covered.setdefault((_qualified(family, owner), _qualified(family, by_name[name])),
                               []).append(f"exclusion {constraint['name']}")
    every = {(application, middleware) for application in applications for middleware in middlewares}
    assert len(every) == 12 and set(covered) == every
    assert all(len(statements) == 1 for statements in covered.values()), covered
    assert sum(1 for statements in covered.values() if statements[0].startswith("rule")) == len(rules) == 8
    assert exclusion_owners == 2


def _rationale(raw: str, owner: str) -> str:
    """The doc of the exclusion with short name ``owner``, or the comment about the feature ``owner``."""
    for pattern in (rf"assert constraint <'{owner}'> \w+ :> xorFeatures \{{\s*doc /\*(.*?)\*/",
                    rf"comment about [\w:]+::{owner}\s*/\*(.*?)\*/"):
        if (match := re.search(pattern, raw, re.DOTALL)) is not None:
            return " ".join(line.strip().lstrip("*").strip() for line in match[1].splitlines()).strip()
    raise AssertionError(f"no rationale for {owner}")


def complement_violations(options: set[str], allowed: dict[str, set[str]], exclusions: dict[str, set[str]]) -> list[str]:
    """The complement check: each rule's exclusion set equals its allowed list's complement.

    ``options`` are the operating-system features, ``allowed`` maps a rule to its
    reviewed allowed list and ``exclusions`` to the operating systems its premise
    excludes. A new option outside a list makes the check fail.
    """
    violations = []
    for rule, names in sorted(allowed.items()):
        if not names <= options:
            violations.append(f"{rule}: the allowed list names unknown options {sorted(names - options)}")
        complement = options - names
        if exclusions.get(rule, set()) != complement:
            violations.append(f"{rule}: excludes {sorted(exclusions.get(rule, set()))}, complement is {sorted(complement)}")
    return violations




def _complement_inputs():
    """The main-side operating-system options, the reviewed allowed list of each rule as its rationale
    records it, and the operating systems the rule's premise excludes. The guest operating systems are
    another group: C007 and C008 state their rules exactly, so they need no allowed list."""
    by_name = _by_name(_tree(FAMILIES["sdv"])[1])
    raw = _raw(FAMILIES["sdv"].model)
    options = {feature.name for feature in by_name.values() if feature.parent == "operatingSystem"}
    allowed: dict[str, set[str]] = {}
    exclusions: dict[str, set[str]] = {}
    for rule, where in ALLOWED_LIST_RULES.items():
        lists = ALLOWED_LIST.findall(_rationale(raw, where))
        assert len(lists) == 1, rule
        allowed[rule] = {name.strip() for name in lists[0].split(",")}
        if where == rule:
            [premise] = [owner for owner, constraint in _exclusions(by_name) if constraint["id"] == rule]
        else:
            premise = by_name[where]
        exclusions[rule] = {name for constraint in premise.constraints if constraint["kind"] == "xorFeatures"
                            for name in constraint["operands"] if name in options}
    return options, allowed, exclusions


def test_each_exclusion_set_is_the_complement_of_its_reviewed_allowed_list() -> None:
    options, allowed, exclusions = _complement_inputs()
    assert options == {"linux", "android", "qnx"}
    assert sorted(allowed) == ["C001", "C002", "C003"]
    assert complement_violations(options, allowed, exclusions) == []
    assert exclusions["C002"] == set(), "the dropped rule owns no exclusion of an operating system"
    # Since INC-MW-011 phase 9 the AAOS SDV partner runs in the guest (C009), and the rationale says so.
    rationale = _rationale(_raw(FAMILIES["sdv"].model), "androidSDV")
    assert "runs in the guest (C009)" in rationale and "main side" in rationale


def test_the_complement_check_fails_when_an_operating_system_option_is_added() -> None:
    options, allowed, exclusions = _complement_inputs()
    violations = complement_violations(options | {"automotiveGradeLinux"}, allowed, exclusions)
    assert [violation.split(":")[0] for violation in violations] == ["C001", "C002", "C003"]
def test_the_dropped_rules_keep_their_rationale_in_the_model() -> None:
    raw = _raw(FAMILIES["sdv"].model)
    assert "Dropped rule C002" in _rationale(raw, "androidSDV")
    assert "Dropped rule C006" in _rationale(raw, "pedestrianDetection")



@pytest.mark.parametrize("name", ["engineering", "vehicle"])
def test_the_environment_constraints_are_requires_constraints_between_choices(name: str) -> None:
    """Each constraint of an execution-environment family is a requires constraint with the family's
    C-ENG- or C-VEHICLE- ID, owned by a choice and requiring one choice of another group."""
    features = _tree(FAMILIES[name])[1]
    by_name = _by_name(features)
    prefix = {"engineering": "C-ENG-", "vehicle": "C-VEHICLE-"}[name]
    constraints = [(feature, constraint) for feature in features for constraint in feature.constraints]
    assert constraints and len({constraint["id"] for _owner, constraint in constraints}) == len(constraints)
    for owner, constraint in constraints:
        assert constraint["kind"] == "requiresFeatures" and constraint["id"].startswith(prefix), constraint
        [operand] = constraint["operands"]
        assert owner.parent and by_name[operand].parent not in (None, owner.parent), constraint["id"]


# -- the closed world, evaluated ------------------------------------------------------------------


def _structural_selections(features: list[Feature]) -> list[set[str]]:
    """Every structurally valid selection of a feature model, as the names of the selected features.

    One member per [1] group, a non-empty subset of the members of a [1..*] group, and both states of
    each optional feature outside a group; every feature with a lower bound of one is selected.
    Structurally invalid selections are outside the enumeration: an exclusion presumes the
    exactly-one structure of its group.
    """
    groups: dict[str, list[str]] = {}
    for feature in features:
        if feature.parent:
            groups.setdefault(feature.parent, []).append(feature.name)
    axes = []
    for feature in features:
        if feature.name in groups:
            names = groups[feature.name]
            axes.append([{name} for name in names] if feature.multiplicity == "1" else
                        [set(subset) for size in range(1, len(names) + 1)
                         for subset in itertools.combinations(names, size)])
        elif feature.parent is None and feature.multiplicity == "0..1":
            axes.append([set(), {feature.name}])
    selected = {feature.name for feature in features if not feature.multiplicity.startswith("0")}
    return [selected.union(*choice) for choice in itertools.product(*axes)]


def _model_verdict(features: list[Feature], rules: list[Dependency], selected: set[str]) -> tuple[bool, frozenset, bool, str | None]:
    """(valid, constraint IDs, pair exclusion, derived variant) by the model's own semantics.

    A ``[1]`` group needs exactly one selected member and a ``[1..*]`` group
    at least one. An exclusion of a selected owner fails when it selects an
    excluded feature, a requires constraint when it misses a required one;
    an exclusion without an ID is a pair exclusion. A valid configuration
    then derives the variant of the one rule whose premises are all selected;
    none or several rejects it.
    """
    by_name = _by_name(features)
    reasons: set[str] = set()
    for group in {feature.parent for feature in features if feature.parent}:
        count = sum(feature.name in selected for feature in features if feature.parent == group)
        lower, _, upper = by_name[group].multiplicity.partition("..")
        if count < int(lower) or (upper != "*" and count > int(upper or lower)):
            reasons.add(f"group {group}")
    for feature in features:
        if feature.name in selected:
            for constraint in feature.constraints:
                operands = set(constraint["operands"])
                if (constraint["kind"] == "xorFeatures" and operands & selected
                        or constraint["kind"] == "requiresFeatures" and not operands <= selected):
                    reasons.add(constraint["id"] or f"pair {feature.name}")
    variant = None
    if rules and not reasons:
        matching = [rule for rule in rules if {premise.rsplit("::", 1)[1] for premise in rule.suppliers} <= selected]
        if len(matching) == 1:
            variant = matching[0].client.rsplit("::", 1)[1]
        else:
            reasons.add("no rule" if not matching else "several rules")
    ids = frozenset(reason for reason in reasons if " " not in reason and reason != "no rule")
    return not reasons, ids, any(reason.startswith("pair ") for reason in reasons), variant



#: The verdicts of the closed world on every structurally valid selection, (valid, constraint IDs, pair
#: exclusion, derived adapter) -> count: a reviewed table. Until S7 a test compared each selection with the
#: configurator's verdict on the YAML catalogue. The SDV table changed with the two-sided tree of INC-MW-011
#: phase 9. Two computations gave it and agree selection by selection: this lexical model over the model
#: text, and the DE4SDV evaluator over a synthetic graph of the same tree. Of the 129,024 SDV selections,
#: 16,016 are valid; they are 143 valid platform and display selections, each with the 112 choices of the
#: sensors and the four other capabilities, which no constraint names.
CLOSED_WORLD = {
    "sdv": {
        (False, (), True, None): 7168,
        (False, ('C001',), False, None): 2912,
        (False, ('C001', 'C007'), False, None): 672,
        (False, ('C001', 'C007', 'C010'), False, None): 224,
        (False, ('C001', 'C007', 'C010', 'C011'), False, None): 112,
        (False, ('C001', 'C007', 'C011'), False, None): 336,
        (False, ('C001', 'C008'), False, None): 1792,
        (False, ('C001', 'C008', 'C011'), False, None): 896,
        (False, ('C001', 'C010'), False, None): 1568,
        (False, ('C001', 'C010', 'C011'), False, None): 784,
        (False, ('C001', 'C011'), False, None): 1456,
        (False, ('C003',), True, None): 2912,
        (False, ('C003', 'C007'), True, None): 672,
        (False, ('C003', 'C007', 'C010'), True, None): 224,
        (False, ('C003', 'C007', 'C010', 'C011'), False, None): 112,
        (False, ('C003', 'C007', 'C011'), False, None): 336,
        (False, ('C003', 'C008'), True, None): 1792,
        (False, ('C003', 'C008', 'C011'), False, None): 896,
        (False, ('C003', 'C010'), True, None): 1568,
        (False, ('C003', 'C010', 'C011'), False, None): 784,
        (False, ('C003', 'C011'), False, None): 1456,
        (False, ('C004',), False, None): 1792,
        (False, ('C004',), True, None): 1344,
        (False, ('C004', 'C008'), False, None): 896,
        (False, ('C004', 'C008'), True, None): 896,
        (False, ('C004', 'C008', 'C011'), False, None): 896,
        (False, ('C004', 'C009'), True, None): 448,
        (False, ('C004', 'C009', 'C010'), True, None): 448,
        (False, ('C004', 'C009', 'C010', 'C011'), False, None): 224,
        (False, ('C004', 'C009', 'C011'), False, None): 224,
        (False, ('C004', 'C010'), False, None): 896,
        (False, ('C004', 'C010'), True, None): 448,
        (False, ('C004', 'C010', 'C011'), False, None): 672,
        (False, ('C004', 'C011'), False, None): 1568,
        (False, ('C005',), False, None): 1792,
        (False, ('C005',), True, None): 1344,
        (False, ('C005', 'C008'), False, None): 896,
        (False, ('C005', 'C008'), True, None): 896,
        (False, ('C005', 'C008', 'C011'), False, None): 896,
        (False, ('C005', 'C009'), True, None): 448,
        (False, ('C005', 'C009', 'C010'), True, None): 448,
        (False, ('C005', 'C009', 'C010', 'C011'), False, None): 224,
        (False, ('C005', 'C009', 'C011'), False, None): 224,
        (False, ('C005', 'C010'), False, None): 896,
        (False, ('C005', 'C010'), True, None): 448,
        (False, ('C005', 'C010', 'C011'), False, None): 672,
        (False, ('C005', 'C011'), False, None): 1568,
        (False, ('C007',), False, None): 4592,
        (False, ('C007',), True, None): 2688,
        (False, ('C007', 'C009'), False, None): 112,
        (False, ('C007', 'C009'), True, None): 672,
        (False, ('C007', 'C009', 'C010'), False, None): 112,
        (False, ('C007', 'C009', 'C010'), True, None): 672,
        (False, ('C007', 'C009', 'C010', 'C011'), False, None): 224,
        (False, ('C007', 'C009', 'C011'), False, None): 224,
        (False, ('C007', 'C010'), False, None): 1456,
        (False, ('C007', 'C010'), True, None): 448,
        (False, ('C007', 'C010', 'C011'), False, None): 448,
        (False, ('C007', 'C011'), False, None): 1792,
        (False, ('C008',), False, None): 10752,
        (False, ('C008',), True, None): 7168,
        (False, ('C008', 'C011'), False, None): 3584,
        (False, ('C009',), False, None): 784,
        (False, ('C009',), True, None): 3808,
        (False, ('C009', 'C010'), False, None): 784,
        (False, ('C009', 'C010'), True, None): 3808,
        (False, ('C009', 'C010', 'C011'), False, None): 1120,
        (False, ('C009', 'C011'), False, None): 1120,
        (False, ('C010',), False, None): 8400,
        (False, ('C010',), True, None): 2240,
        (False, ('C010', 'C011'), False, None): 1792,
        (False, ('C011',), False, None): 4032,
        (True, (), False, 'apolloToSCORE'): 2016,
        (True, (), False, 'autowareToAAOSSDV'): 672,
        (True, (), False, 'autowareToAUTOSAR'): 1456,
        (True, (), False, 'autowareToSCORE'): 1456,
        (True, (), False, 'none'): 8400,
        (True, (), False, 'openpilotToSCORE'): 2016,
    },
    "engineering": {
        (False, ('C-ENG-AOSP-HOST-REQUIRES-LINUX-X86-64', 'C-ENG-AOSP-HOST-REQUIRES-NESTED-KVM'), False, None): 4,
        (False, ('C-ENG-AOSP-HOST-REQUIRES-LINUX-X86-64',), False, None): 2,
        (False, ('C-ENG-AOSP-HOST-REQUIRES-NESTED-KVM',), False, None): 2,
        (False, ('C-ENG-APPLE-REQUIRES-MACOS', 'C-ENG-APPLE-REQUIRES-VIRTUAL-LINUX-OCI'), False, None): 4,
        (False, ('C-ENG-APPLE-REQUIRES-MACOS',), False, None): 2,
        (False, ('C-ENG-APPLE-REQUIRES-VIRTUAL-LINUX-OCI',), False, None): 2,
        (False, ('C-ENG-JETSON-REQUIRES-NATIVE-OCI', 'C-ENG-JETSON-REQUIRES-TEGRA-LINUX'), False, None): 4,
        (False, ('C-ENG-JETSON-REQUIRES-NATIVE-OCI',), False, None): 2,
        (False, ('C-ENG-JETSON-REQUIRES-TEGRA-LINUX',), False, None): 2,
        (True, (), False, None): 3,
    },
    "vehicle": {
        (False, ('C-VEHICLE-NATIVE-ZEPHYR-REQUIRES-NXP', 'C-VEHICLE-NO-COMPUTE-REQUIRES-NO-OS', 'C-VEHICLE-NO-COMPUTE-REQUIRES-NO-RUNTIME', 'C-VEHICLE-ZEPHYR-REQUIRES-NXP'), False, None): 1,
        (False, ('C-VEHICLE-NATIVE-ZEPHYR-REQUIRES-NXP', 'C-VEHICLE-NO-COMPUTE-REQUIRES-NO-RUNTIME'), False, None): 1,
        (False, ('C-VEHICLE-NO-COMPUTE-REQUIRES-NO-OS', 'C-VEHICLE-ZEPHYR-REQUIRES-NXP'), False, None): 1,
        (False, ('C-VEHICLE-NXP-REQUIRES-NATIVE-ZEPHYR', 'C-VEHICLE-NXP-REQUIRES-ZEPHYR'), False, None): 1,
        (False, ('C-VEHICLE-NXP-REQUIRES-NATIVE-ZEPHYR',), False, None): 1,
        (False, ('C-VEHICLE-NXP-REQUIRES-ZEPHYR',), False, None): 1,
        (True, (), False, None): 2,
    },
}
#: Cross-platform mixes and partial resolutions of the environment configurations: (configuration,
#: replaced choice, replacing choice, the requires constraints that reject the mix).
ENVIRONMENT_MIXES = [
    ("apple_silicon_macos_candidate", "macOSAppleSilicon", "ubuntu2204Tegra", {"C-ENG-APPLE-REQUIRES-MACOS"}),
    ("apple_silicon_macos_candidate", "virtualizedLinuxArm64OCIOnMacOS", "nativeLinuxArm64OCI",
     {"C-ENG-APPLE-REQUIRES-VIRTUAL-LINUX-OCI"}),
    ("inc_aebs_009a_jetson", "ubuntu2204Tegra", "macOSAppleSilicon", {"C-ENG-JETSON-REQUIRES-TEGRA-LINUX"}),
    ("inc_aebs_009a_jetson", "nativeLinuxArm64OCI", "virtualizedLinuxArm64OCIOnMacOS",
     {"C-ENG-JETSON-REQUIRES-NATIVE-OCI"}),
    ("nxp_zephyr_vehicle_target_candidate", "zephyr", "noConcreteOperatingSystem", {"C-VEHICLE-NXP-REQUIRES-ZEPHYR"}),
    ("nxp_zephyr_vehicle_target_candidate", "nativeZephyr", "noConcreteExecutionRuntime",
     {"C-VEHICLE-NXP-REQUIRES-NATIVE-ZEPHYR"}),
    ("nxp_zephyr_vehicle_target_candidate", "nxpVehicleCompute", "noConcreteComputeNode",
     {"C-VEHICLE-NATIVE-ZEPHYR-REQUIRES-NXP", "C-VEHICLE-NO-COMPUTE-REQUIRES-NO-OS",
      "C-VEHICLE-NO-COMPUTE-REQUIRES-NO-RUNTIME", "C-VEHICLE-ZEPHYR-REQUIRES-NXP"}),
]


def _rules(family: Family) -> list[Dependency]:
    return [dependency for dependency in _dependencies(family.model) if dependency.metadata == "DerivationRule"]


@pytest.mark.parametrize("name", FAMILIES)
def test_the_closed_world_keeps_its_verdicts_on_every_structurally_valid_selection(name: str) -> None:
    """The agreement and complement checks, evaluated: the model's groups, constraints and rules decide
    every structurally valid selection as the reviewed table records it (see CLOSED_WORLD)."""
    family = FAMILIES[name]
    features = _tree(family)[1]
    rules = _rules(family)
    histogram: Counter = Counter()
    for selected in _structural_selections(features):
        valid, ids, pair, variant = _model_verdict(features, rules, selected)
        histogram[(valid, tuple(sorted(ids)), pair, variant)] += 1
    assert sum(histogram.values()) == {"sdv": 129024, "engineering": 27, "vehicle": 8}[name]
    assert dict(histogram) == CLOSED_WORLD[name]


def test_the_closed_world_check_catches_a_dropped_exclusion() -> None:
    family = FAMILIES["sdv"]
    features = _tree(family)[1]
    weakened = [Feature(**{**feature.__dict__, "constraints": [c for c in feature.constraints if c["id"] != "C001"]})
                for feature in features]
    _family, selected = _configuration_selection(runner.FIXTURES[0])
    # The invalid fixture runs Autoware on main-side Android, so C011 rejects it too.
    assert _model_verdict(features, _rules(family), selected) == (False, frozenset({"C001", "C011"}), False, None)
    assert _model_verdict(weakened, _rules(family), selected) == (False, frozenset({"C011"}), False, None)


@pytest.mark.parametrize("stem, replaced, replacing, rejecting", ENVIRONMENT_MIXES,
                         ids=[f"{stem}-{replacing}" for stem, _old, replacing, _ids in ENVIRONMENT_MIXES])
def test_the_requires_constraints_reject_a_cross_platform_mix(stem: str, replaced: str, replacing: str,
                                                              rejecting: set[str]) -> None:
    family, selected = _configuration_selection(f"{CONFIGURATIONS_DIR.as_posix()}/{stem}.sysml")
    features = _tree(family)[1]
    assert _model_verdict(features, [], selected) == (True, frozenset(), False, None)
    assert replaced in selected
    assert _model_verdict(features, [], selected - {replaced} | {replacing}) == (
        False, frozenset(rejecting), False, None)


# -- bindings, correspondences and projection metadata -------------------------------------------------


@pytest.mark.parametrize("name", FAMILIES)
def test_one_binding_per_shared_asset_variant_with_the_asset_as_client(name: str) -> None:
    """Every variant of a bound variation is bound exactly once, by a choice of one group, and the
    choices of a group are bound to one variation or none."""
    family = FAMILIES[name]
    package, owner, _label = PROJECTIONS[name]
    features = _tree(family)[1]
    bindings = [dependency for dependency in _dependencies(family.model) if dependency.metadata == "FeatureBinding"]
    assert bindings and all(len(binding.suppliers) == 1 and binding.short is None for binding in bindings)
    assert len({binding.client for binding in bindings}) == len(bindings), "a variant is bound more than once"
    assert len({binding.suppliers[0] for binding in bindings}) == len(bindings), "a feature binds two variants"
    variation_of: dict[str, str] = {}
    bound: dict[str, set[str]] = {}
    for binding in bindings:
        assert binding.client.startswith(f"{package}::{owner}::"), binding.name
        variation, variant = binding.client.removeprefix(f"{package}::{owner}::").split("::")
        bound.setdefault(variation, set()).add(variant)
        variation_of[binding.suppliers[0]] = variation
    for variation, variants in bound.items():
        assert variants == _variants(SUPERSETS[package], owner, variation), variation
    choices = {_qualified(family, feature): feature.parent for feature in features if feature.parent}
    assert set(variation_of) <= set(choices), "a binding names a feature that is no group member"
    for group in set(choices.values()):
        members = [path for path, parent in choices.items() if parent == group]
        assert len({variation_of.get(path) for path in members}) == 1, group


@pytest.mark.parametrize("name", FAMILIES)
def test_the_feature_model_carries_its_projection_block(name: str) -> None:
    family = FAMILIES[name]
    package, owner, label = PROJECTIONS[name]
    code = _code(family.model)
    [match] = re.finditer(rf"#featureModel occurrence def {family.feature_model}\s*\{{", code)
    body, _end = _braced(code, match.end() - 1)
    assert _owned_metadata(body, "ProductModelProjection") == [{"packageName": package, "ownerName": owner,
                                                                "label": label}]
    assert len(re.findall(r"@ProductModelProjection\b", code)) == 1, "the projection is owned by the feature model only"
    assert re.search(rf"\bpart def {owner}\b", _code(SUPERSETS[package])), owner
@pytest.mark.parametrize("path", PLEML_FILES)
def test_kernel_metadata_sits_in_the_body_of_the_element_it_annotates(path: str) -> None:
    """The evaluator reads only the metadata an element owns, the prefix ``#M`` or a body ``@M``,
    so metadata applied from outside with ``about`` is refused here before the licensed run."""
    assert not _METADATA_ABOUT.findall(_code(path))


@pytest.mark.parametrize("text", [
    "@ProductModelProjection about M { label = \"x\"; }",
    "@DE4SDV_ProductLineDerivation::ProductModelProjectionName about c { partDefinitionName = \"X\"; }",
    "metadata name : ProductModelProjectionName about c { partDefinitionName = \"X\"; }",
    "metadata : UnassignedBindingTime about f;",
])
def test_the_about_guard_refuses_metadata_applied_from_outside(text: str) -> None:
    assert _METADATA_ABOUT.findall(text)
    assert not _METADATA_ABOUT.findall("comment about f /* a comment is no metadata */")


def _governed_elements() -> set[str]:
    code = _code(SCOPE)
    elements = set()
    for owner in ("InitialCommonCoreEngineeringContent", "ReferenceOnlyAlternativeSet", "DeferredVariabilitySet",
                  "ExcludedSystem2ConcernSet"):
        match = re.search(rf"\bpart def {owner}\b[^{{;]*\{{", code)
        assert match, owner
        body, _end = _braced(code, match.end() - 1)
        elements.update(f"{owner}::{part}" for part in re.findall(r"\bpart (\w+) :", body))
    match = re.search(r"\bvariation part vehiclePlatformIntegrationMode\s*\{", code)
    assert match
    body, _end = _braced(code, match.end() - 1)
    elements.update(f"vehiclePlatformIntegrationMode::{variant}" for variant in re.findall(r"\bvariant part (\w+)", body))
    return elements


def test_the_sdv_correspondences_restate_the_governed_scope_feature_by_feature() -> None:
    family = FAMILIES["sdv"]
    features = _tree(family)[1]
    by_path = {_qualified(family, feature): feature for feature in features}
    found: dict[str, set[str]] = {}
    for dependency in _dependencies(family.model):
        if dependency.metadata:
            continue
        [supplier] = dependency.suppliers
        assert supplier.startswith("DE4SDV_AEBSProductLineScope::"), supplier
        assert dependency.client in by_path, f"{dependency.client} is not a feature"
        found.setdefault(by_path[dependency.client].id, set()).add(supplier.removeprefix("DE4SDV_AEBSProductLineScope::"))
    assert found == SDV_CORRESPONDENCES
    assert set(_by_id(features)) == set(SDV_CORRESPONDENCES) | SDV_WITHOUT_CORRESPONDENCE
    governed = _governed_elements()
    for targets in SDV_CORRESPONDENCES.values():
        assert targets <= governed, targets - governed


def test_the_features_without_a_governed_element_say_so() -> None:
    match = re.search(r"comment about ([\w:,\s]+?)\s*/\*(.*?)\*/", _raw(FAMILIES["sdv"].model), re.DOTALL)
    assert match and "adaptiveCruiseControl" in match[1] and "laneKeepAssist" in match[1]
    assert "no governed-scope" in " ".join(match[2].split())


@pytest.mark.parametrize("name", ["engineering", "vehicle"])
def test_an_environment_family_corresponds_as_a_whole(name: str) -> None:
    family = FAMILIES[name]
    plain = [d for d in _dependencies(family.model) if not d.metadata]
    assert [(d.client, d.suppliers) for d in plain] == [
        (family.tree, (f"DE4SDV_AEBSProductLineScope::{family.root_correspondence}",))]
    assert family.root_correspondence in _governed_elements()



# -- the configurations ---------------------------------------------------------------------------


_CONFIGURATION = re.compile(r"#featureConfiguration occurrence (\w+) : (\w+) :> featureConfigurations\s*\{")
_REDEFINITION = re.compile(r"#feature occurrence :>> (\w+)\[([^\]]+)\](?: = \(([^)]*)\))?\s*([;{])")


def _redefinitions(body: str, path: tuple[str, ...] = ()) -> dict[tuple[str, ...], tuple[str, tuple[str, ...]]]:
    found, position = {}, 0
    while (match := _REDEFINITION.search(body, position)) is not None:
        inner, position = ("", match.end()) if match[4] == ";" else _braced(body, match.end() - 1)
        key = (*path, match[1])
        assert key not in found, key
        found[key] = (match[2], _operands(match[3]) if match[3] else ())
        found.update(_redefinitions(inner, key))
    return found



def _configuration_family(path: str | Path) -> Family:
    """The family whose tree the configuration of ``path`` is typed by."""
    [match] = list(_CONFIGURATION.finditer(_code(path)))
    [family] = [family for family in FAMILIES.values() if family.tree == match[2]]
    return family


def _configuration_body(path: str | Path) -> str:
    code = _code(path)
    [match] = list(_CONFIGURATION.finditer(code))
    return _braced(code, match.end() - 1)[0]


def _configuration_selection(path: str | Path) -> tuple[Family, set[str]]:
    """The family and the names of the features a configuration redefines with multiplicity other than 0."""
    return _configuration_family(path), {key[-1] for key, (multiplicity, _operands)
                                         in _redefinitions(_configuration_body(path)).items() if multiplicity != "0"}


CONFIGURATION_FILES = (*runner.CONFIGURATIONS, *runner.FIXTURES)


@pytest.mark.parametrize("path", CONFIGURATION_FILES, ids=lambda path: Path(path).stem)
def test_each_configuration_specializes_its_family_tree_and_names_its_projection(path: str) -> None:
    family = _configuration_family(path)
    code = _code(path)
    assert f"private import {family.package}::{family.tree};" in code
    [name] = _owned_metadata(_configuration_body(path), "ProductModelProjectionName")
    assert set(name) == {"partDefinitionName"} and re.fullmatch(r"[A-Z]\w*", name["partDefinitionName"])
    assert len(re.findall(r"@ProductModelProjectionName\b", code)) == 1, "the name is owned by the configuration only"


@pytest.mark.parametrize("path", CONFIGURATION_FILES, ids=lambda path: Path(path).stem)
def test_each_configuration_redefines_features_of_its_tree_only(path: str) -> None:
    """A redefinition names a feature at its own path in the tree. A group redefinition lists members
    of that group only, and each listed member is redefined [1]."""
    features = _tree(_configuration_family(path))[1]
    by_path = {feature.path: feature for feature in features}
    by_name = _by_name(features)
    redefinitions = _redefinitions(_configuration_body(path))
    assert redefinitions, path
    for key, (_multiplicity, operands) in redefinitions.items():
        assert key in by_path, (path, key)
        for operand in operands:
            assert by_name[operand].parent == key[-1], (path, key, operand)
            assert redefinitions.get((*key[:-1], operand)) == ("1", ()), (path, operand)


def test_the_fixture_and_the_probes_are_the_only_configurations_outside_the_authority_roots() -> None:
    assert runner.FIXTURES == (f"{CONFIGURATIONS_DIR.as_posix()}/fixtures/invalid_score_android.sysml",
                               *runner.PARITY_PROBES)
    assert len(runner.PARITY_PROBES) == len(set(runner.PARITY_PROBES)) == 17
    assert all(path.startswith(f"{CONFIGURATIONS_DIR.as_posix()}/fixtures/parity-probes/")
               for path in runner.PARITY_PROBES)
    _family, selected = _configuration_selection(runner.FIXTURES[0])
    assert {"eclipseSCORE", "android"} <= selected


# -- admission by the stated reading of the correspondences ----------------------------------------------


#: The class of a governed element, by the set or variation that owns it in the governed scope.
GOVERNED_CLASSES = {
    "InitialCommonCoreEngineeringContent": "common", "ReferenceOnlyAlternativeSet": "reference-only",
    "DeferredVariabilitySet": "deferred", "ExcludedSystem2ConcernSet": "excluded",
    "vehiclePlatformIntegrationMode": "admitted-alternative",
}
ADMISSIBLE = {"admitted-alternative", "common"}
#: The representation differences: a common element whose choice shares a slot with the realization of an
#: alternative that takes the slot otherwise. PLE-S recorded one, the common Linux runtime under the
#: AAOS-integrated alternative. None is left since INC-MW-011 phase 9: the AAOS-integrated member runs
#: Autoware on Linux on the main side and its Android in the guest, so no member needs an exemption.
REPRESENTATION_DIFFERENCES: set[tuple[str, str]] = set()
#: The governed members of ADR 0014 and the alternative each realizes.
GOVERNED_MEMBERS = {"aebs_autoware_linux_lidar_camera": "vehiclePlatformIntegrationMode::standalone",
                    "middleware_autoware_aaos_sdv_reference": "vehiclePlatformIntegrationMode::aaosIntegrated"}


def _classes(elements: set[str]) -> set[str]:
    return {GOVERNED_CLASSES[element.split("::")[0]] for element in elements}


def admission(features: list[Feature], correspondences: dict[str, set[str]], family_elements: set[str],
              selected: set[str]) -> tuple[str | None, list[str]]:
    """(the realized admitted alternative, the blocking reasons) by the reading the model states.

    ``correspondences`` maps a feature to the governed elements it corresponds
    to, and ``family_elements`` holds the family-level ones. Only selected
    choices and leaves block: a grouping feature carries no admission, and a
    group feature's correspondence never blocks.
    """
    groups = {feature.parent for feature in features if feature.parent}
    owners = {feature.path[-2] for feature in features if len(feature.path) > 1}
    choices = {feature.name: feature for feature in features if feature.name not in groups | owners}
    chosen = selected & set(choices)
    blocking = []
    if family_elements and not _classes(family_elements) & ADMISSIBLE:
        blocking.append(f"the family is {', '.join(sorted(_classes(family_elements)))}")
    for name in sorted(chosen):
        kinds = _classes(correspondences.get(name, set()))
        if not kinds & ADMISSIBLE:
            blocking.append(f"{name}: {', '.join(sorted(kinds)) or 'not in the governed scope'}")
    realized = {element for name in chosen for element in correspondences.get(name, set())
                if _classes({element}) == {"admitted-alternative"}}
    if len(realized) != 1:
        return None, [*blocking, f"realizes {len(realized)} admitted alternatives"]
    [alternative] = realized
    realizations = {name for name in choices if alternative in correspondences.get(name, set())}
    slots = {choices[name].parent for name in realizations}
    for slot in sorted(slots):
        if not any(choices[name].parent == slot for name in realizations & chosen):
            blocking.append(f"a derived realization of {alternative} is missing in {slot}")
    for name in sorted(set(choices) - chosen):
        for element in sorted(correspondences.get(name, set())):
            if _classes({element}) != {"common"}:
                continue
            slot = choices[name].parent
            exempt = (element, slot) in REPRESENTATION_DIFFERENCES and slot in slots and name not in realizations
            if not exempt:
                blocking.append(f"{element} is not represented: {name} is not selected")
    return alternative, blocking


def _correspondences(family: Family) -> tuple[dict[str, set[str]], set[str]]:
    features, family_elements = {}, set()
    for dependency in _dependencies(family.model):
        if dependency.metadata:
            continue
        [target] = dependency.suppliers
        element = target.removeprefix("DE4SDV_AEBSProductLineScope::")
        if dependency.client == family.tree:
            family_elements.add(element)
        else:
            features.setdefault(dependency.client.rsplit("::", 1)[1], set()).add(element)
    return features, family_elements



@pytest.mark.parametrize("path", runner.CONFIGURATIONS, ids=lambda path: Path(path).stem)
def test_admission_admits_exactly_the_governed_members(path: str) -> None:
    """Review R2: read as PLE-S read it, admission admits the standalone and the
    AAOS-integrated member of ADR 0014 and nothing else: the reference examples
    and both execution-environment families are not admitted."""
    family, selected = _configuration_selection(path)
    correspondences, family_elements = _correspondences(family)
    alternative, blocking = admission(_tree(family)[1], correspondences, family_elements, selected)
    stem = Path(path).stem
    if stem in GOVERNED_MEMBERS:
        assert (alternative, blocking) == (GOVERNED_MEMBERS[stem], [])
    else:
        assert blocking, stem


def test_admission_blocks_only_on_selected_choices_and_leaves() -> None:
    family = FAMILIES["sdv"]
    features = _tree(family)[1]
    correspondences, family_elements = _correspondences(family)
    _family, standalone = _configuration_selection(CONFIGURATIONS_DIR / "aebs_autoware_linux_lidar_camera.sysml")
    # A deferred group correspondence and the uncorresponded grouping features never block.
    assert _classes(correspondences["vehicleApplication"]) == {"deferred"} and "vehicleApplication" in standalone
    assert {"platformStack", "middleware"} <= standalone - set(correspondences)
    assert admission(features, correspondences, family_elements, standalone) == (
        "vehiclePlatformIntegrationMode::standalone", [])
    # A selected leaf without a correspondence blocks, and so does a partly represented common asset.
    assert admission(features, correspondences, family_elements, standalone | {"adaptiveCruiseControl"})[1] == [
        "adaptiveCruiseControl: not in the governed scope"]
    assert admission(features, correspondences, family_elements, standalone - {"camera"})[1] == [
        "InitialCommonCoreEngineeringContent::currentSensingBaseline is not represented: camera is not selected"]
    # Two admitted alternatives, or a missing derived realization, reject.
    assert admission(features, correspondences, family_elements, standalone - {"noGuestOS"} | {"guestAndroid"})[1] == [
        "realizes 2 admitted alternatives"]
    _family, integrated = _configuration_selection(CONFIGURATIONS_DIR / "middleware_autoware_aaos_sdv_reference.sysml")
    assert admission(features, correspondences, family_elements, integrated) == (
        "vehiclePlatformIntegrationMode::aaosIntegrated", [])
    assert admission(features, correspondences, family_elements, integrated - {"kvm"})[1] == [
        "a derived realization of vehiclePlatformIntegrationMode::aaosIntegrated is missing in hypervisor"]
    # Main-side Android and the HMI display have no governed element (INC-MW-011 phase 9), and Linux
    # represents the common runtime in both members, so no exemption covers its absence.
    assert admission(features, correspondences, family_elements, standalone - {"linux"} | {"android"})[1] == [
        "android: not in the governed scope",
        "InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime is not represented: linux is not selected"]
    assert admission(features, correspondences, family_elements, integrated | {"hmiDisplay"})[1] == [
        "hmiDisplay: not in the governed scope"]
