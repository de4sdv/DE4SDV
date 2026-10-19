"""Fence, catalogue restatement and closed-world checks of the PLEML feature models (ADR 0022).

The PLEML feature models (``feature-models/*.sysml``) and their configurations
(``feature-configurations/**/*.sysml``) are fenced until the authority switch
(ADR 0022, step S6). These checks read the model text: they pin the reviewed
shape so that a rename or a drift fails here before the licensed run, and the
closed-world and admission checks evaluate the stated semantics on that text.
The privileged PLE authority workflow (licensed validation, serialization, API
round trip) is the validator, and the evaluator of step S2 owns the
semantics. They pin:

- the fence: outside every production selector;
- each feature model restating its YAML catalogue node for node, by ID, except
  the ``C-`` common-capability nodes, which have no element (decision 2);
- the agreement check over the twelve application-middleware pairs: exactly
  one derivation rule for each allowed pair, exactly one exclusion for each
  unsupported one, and the rule table equal to the catalogue's row by row;
- the complement check of the allowed lists of C001 and C003, and of C002's;
- the closed world: on every structurally valid selection, the model's groups,
  constraints and rules decide as the configurator does;
- one feature binding per shared-asset variant, the correspondences, the
  projection metadata and the unassigned binding times;
- each configuration against its bill of features, and its admission by the
  stated reading of the correspondences.
"""

from __future__ import annotations

import importlib.util
import itertools
import re
import subprocess
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
GROUPS = ("alternative", "or_group")
SUPERSETS = {"DE4SDV_SDVPlatformStack": Path("textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"),
             "DE4SDV_ExecutionEnvironments": Path("textual-notation-of-model/packages/architecture/execution_environments.sysml")}


@dataclass(frozen=True)
class Family:
    catalogue: Path
    model: Path
    package: str
    tree: str
    feature_model: str
    #: The governed element the root feature corresponds to, when the whole family is classified.
    root_correspondence: str | None


FAMILIES = {
    "sdv": Family(FEATURE_MODELS_DIR / "sdv_product_line.yaml", FEATURE_MODELS_DIR / "sdv_product_line.sysml",
                  "DE4SDV_SDVProductLineFeatureModel", "SDVProductLineFeatureTree", "SDVProductLineFeatureModel", None),
    "engineering": Family(
        FEATURE_MODELS_DIR / "engineering_execution_environments.yaml",
        FEATURE_MODELS_DIR / "engineering_execution_environments.sysml",
        "DE4SDV_EngineeringExecutionEnvironmentFeatureModel", "EngineeringExecutionEnvironmentFeatureTree",
        "EngineeringExecutionEnvironmentFeatureModel", "ExcludedSystem2ConcernSet::engineeringExecutionEnvironments"),
    "vehicle": Family(
        FEATURE_MODELS_DIR / "vehicle_execution_environments.yaml",
        FEATURE_MODELS_DIR / "vehicle_execution_environments.sysml",
        "DE4SDV_VehicleTargetExecutionEnvironmentFeatureModel", "VehicleTargetExecutionEnvironmentFeatureTree",
        "VehicleTargetExecutionEnvironmentFeatureModel", "DeferredVariabilitySet::vehicleRuntimeVariability"),
}

#: The correspondences of the SDV features to the governed scope, by feature ID: the
#: retired PLE-S catalogue correspondence restated feature by feature, plus the PLE-S
#: derived-realization bindings (a derived realization corresponds to its admitted
#: alternative) and the common realization of Autoware. C- nodes have none (decision 2).
SDV_CORRESPONDENCES = {
    "F-PLATFORM-VEHICLE-APPLICATION": {"DeferredVariabilitySet::drivingStackVariability"},
    "F-PLATFORM-VEHICLE-APPLICATION-AUTOWARE": {"InitialCommonCoreEngineeringContent::autowareApplication"},
    "F-PLATFORM-VEHICLE-APPLICATION-OPENPILOT": {"ReferenceOnlyAlternativeSet::openpilot"},
    "F-PLATFORM-VEHICLE-APPLICATION-APOLLO": {"ReferenceOnlyAlternativeSet::apollo"},
    "F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE": {"ReferenceOnlyAlternativeSet::eclipseSCORE"},
    "F-PLATFORM-MIDDLEWARE-ANDROID-SDV": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-MIDDLEWARE-AUTOSAR-ADAPTIVE": {"ReferenceOnlyAlternativeSet::autosarAdaptive"},
    "F-PLATFORM-MIDDLEWARE-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-PLATFORM-OS-LINUX": {"vehiclePlatformIntegrationMode::standalone",
                            "InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime"},
    "F-PLATFORM-OS-ANDROID": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-OS-QNX": {"ReferenceOnlyAlternativeSet::qnxQVM"},
    "F-PLATFORM-HYPERVISOR-QVM": {"ReferenceOnlyAlternativeSet::qnxQVM"},
    "F-PLATFORM-HYPERVISOR-ACRN": {"ReferenceOnlyAlternativeSet::acrn"},
    "F-PLATFORM-HYPERVISOR-KVM": {"vehiclePlatformIntegrationMode::aaosIntegrated"},
    "F-PLATFORM-HYPERVISOR-NONE": {"vehiclePlatformIntegrationMode::standalone"},
    "F-SENSING-PERCEPTION": {"DeferredVariabilitySet::sensingVariability"},
    "F-SENSING-PERCEPTION-LIDAR": {"InitialCommonCoreEngineeringContent::currentSensingBaseline"},
    "F-SENSING-PERCEPTION-RADAR": {"DeferredVariabilitySet::sensingVariability"},
    "F-SENSING-PERCEPTION-CAMERA": {"InitialCommonCoreEngineeringContent::currentSensingBaseline"},
    "F-CAPABILITY-AEBS-PEDESTRIAN-DETECTION": {"DeferredVariabilitySet::expandedAEBSCapabilityVariability"},
    "F-CAPABILITY-AEBS-BICYCLE-DETECTION": {"DeferredVariabilitySet::expandedAEBSCapabilityVariability"},
}
#: Features with no governed-scope element of their own: the grouping features, the
#: middleware, operating-system and hypervisor groups, and two catalogue candidates.
SDV_WITHOUT_CORRESPONDENCE = {
    "F-PLATFORM-STACK", "F-PLATFORM-MIDDLEWARE", "F-PLATFORM-OS", "F-PLATFORM-HYPERVISOR", "F-SENSING",
    "F-CAPABILITIES", "F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL", "F-CAPABILITY-LANE-KEEP-ASSIST",
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
    r"\s*\{\s*in occurrence constrainedFeatures = new FeatureOperand\(that, (?P<operand>\([^()]*\)|\w+)\);\s*\}"
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


def _operands(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.strip("()").split(","))


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
        constraints = [{"id": c["id"], "name": c["name"], "kind": c["kind"], "operands": _operands(c["operand"])}
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


def _catalogue(family: Family):
    data = configurator.load_yaml_unique(_raw(family.catalogue))
    root, constraints = configurator.build_feature_tree(data)
    return data, root, constraints


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


def _is_common(node) -> bool:
    return bool(node.feature_id) and node.feature_id.startswith("C-")


def _enclosing(node):
    """The catalogue node whose PLEML feature encloses the feature of ``node``.

    A choice of an alternative or OR group is a sibling of its group feature;
    a C- node has no feature, so its children move to its nearest feature.
    """
    parent = node.parent
    if parent.parent is not None and parent.type in GROUPS:
        return _enclosing(parent)
    while parent.parent is not None and _is_common(parent):
        parent = parent.parent
    return parent


def _choice(nodes: dict, group: str, choice: str):
    return next(child for child in nodes[group].children if child.name == choice)


def _variants(superset: Path, owner: str, variation: str) -> set[str]:
    code = _code(superset)
    owner_match = re.search(rf"\bpart def {owner}\b[^{{;]*\{{", code)
    assert owner_match, owner
    body, _end = _braced(code, owner_match.end() - 1)
    variation_match = re.search(rf"\bvariation part {variation}\b[^{{;]*\{{", body)
    assert variation_match, variation
    inner, _end = _braced(body, variation_match.end() - 1)
    return set(re.findall(r"\bvariant part (\w+)", inner))


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


# -- the fence --------------------------------------------------------------------------------


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


@pytest.mark.parametrize("path", PLEML_FILES)
def test_every_pleml_file_is_outside_every_production_selector(path: str) -> None:
    model = Path(path)
    assert (ROOT / model).is_file(), path
    for root in (*REVIEWED_ROOTS, *validate_sysml.MODEL_PATHS, *check_repo.SYSML_MODEL_PATHS):
        assert not model.is_relative_to(root), root
    for root in DEFAULT_ROOTS:
        assert not model.is_relative_to(Path(root)), root
    for governed in _governed_deploy_paths():
        if governed.startswith(":(glob)"):
            assert not _glob(governed[len(":(glob)"):]).match(model.as_posix()), governed
        else:
            assert not model.is_relative_to(Path(governed)), governed
    for root in check_naming.SYSML_MODEL_ROOTS:
        assert not (ROOT / model).is_relative_to(root), root
    assert model.as_posix() not in {source.path for source in BaselineManifest.discover(ROOT).sources}


def test_no_pinned_dependency_is_pleml() -> None:
    assert not any("pleml" in dependency.as_posix().lower() for dependency in PINNED_DEPENDENCIES)


@pytest.mark.parametrize("workflow", PRODUCTION_WORKFLOWS)
def test_no_production_workflow_triggers_on_or_reads_the_pleml_files(workflow: str) -> None:
    text = _raw(workflow)
    filters = (yaml.safe_load(text)[True].get("pull_request") or {}).get("paths") or []
    for path in PLEML_FILES:
        assert not any(_glob(pattern).match(path) for pattern in filters), (workflow, path)
        assert path not in text, (workflow, path)


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


@pytest.mark.parametrize("path", PLEML_FILES)
def test_the_pleml_files_follow_the_naming_rules(path: str) -> None:
    text = _raw(path)
    assert check_naming.check_declaration_names_in_text(text, path) == []
    assert check_naming.check_identifier_tokens_in_text(text, path, ".sysml") == []


# -- the catalogue restated node for node ----------------------------------------------------------


@pytest.mark.parametrize("name", FAMILIES)
def test_every_catalogue_node_but_common_content_is_one_feature_by_id(name: str) -> None:
    family = FAMILIES[name]
    _data, root, _constraints = _catalogue(family)
    tree_id, features = _tree(family)
    assert tree_id == root.feature_id
    _by_name(features)
    index = _by_id(features)
    nodes = [node for node in configurator.iter_feature_nodes(root) if node.parent is not None]
    assert set(index) == {node.feature_id for node in nodes if not _is_common(node)}
    common = {node.feature_id for node in nodes if _is_common(node)}
    assert not (set(re.findall(r"<'([^']+)'>", _code(family.model))) & common), "a common-capability node has an element"


@pytest.mark.parametrize("name", FAMILIES)
def test_the_hierarchy_and_multiplicities_restate_the_catalogue(name: str) -> None:
    family = FAMILIES[name]
    _data, root, _constraints = _catalogue(family)
    _tree_id, features = _tree(family)
    index, by_name = _by_id(features), _by_name(features)
    for node in configurator.iter_feature_nodes(root):
        if node.parent is None or _is_common(node):
            continue
        feature = index[node.feature_id]
        enclosing = _enclosing(node)
        assert feature.path[:-1] == (() if enclosing.parent is None else index[enclosing.feature_id].path), node.feature_id
        if node.parent.parent is not None and node.parent.type in GROUPS:
            assert (feature.multiplicity, feature.default_null) == ("0..1", True), node.feature_id
            assert feature.parent is not None and by_name[feature.parent].id == node.parent.feature_id
        else:
            assert feature.parent is None, node.feature_id
            expected = {"mandatory": ("1", False), "alternative": ("1", False), "or_group": ("1..*", False),
                        "optional": ("0..1", True)}[node.type]
            assert (feature.multiplicity, feature.default_null) == expected, node.feature_id


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
def test_unassigned_binding_time_marks_exactly_the_unassigned_catalogue_features(name: str) -> None:
    family = FAMILIES[name]
    _data, root, _constraints = _catalogue(family)
    features = _tree(family)[1]
    unassigned = {node.feature_id for node in configurator.iter_feature_nodes(root) if node.binding_time == "unassigned"}
    assert {feature.id for feature in features if feature.unassigned} == unassigned
    # A feature that a binding, a derived variation or a rule names has a decided binding time.
    named = {supplier for dependency in _dependencies(family.model) if dependency.metadata
             for supplier in dependency.suppliers}
    assert not any(_qualified(family, feature) in named for feature in features if feature.unassigned)


# -- constraints, the agreement check and the complement check ---------------------------------------


def _expression(text: str) -> tuple[str, str, tuple[str, ...]]:
    """``Group == Choice`` or ``Group in [A, B]`` as (operator, group path, choice names)."""
    if (match := re.fullmatch(r"([\w.]+) == (\w+)", text)) is not None:
        return "==", match[1], (match[2],)
    if (match := re.fullmatch(r"([\w.]+) in \[([\w, ]+)\]", text)) is not None:
        return "in", match[1], tuple(part.strip() for part in match[2].split(","))
    raise AssertionError(f"an unreviewed constraint expression: {text!r}")


def _sdv():
    data, root, constraints = _catalogue(FAMILIES["sdv"])
    features = _tree(FAMILIES["sdv"])[1]
    return data, constraints, _by_id(features), _by_name(features), configurator.collect_all_nodes(root)


def _exclusions(by_name: dict[str, Feature]) -> list[tuple[Feature, dict]]:
    return [(feature, constraint) for feature in by_name.values() for constraint in feature.constraints
            if constraint["kind"] == "xorFeatures"]


def test_the_sdv_catalogue_constraints_become_exclusions_or_dropped_rules() -> None:
    _data, constraints, _index, by_name, nodes = _sdv()
    by_constraint = {constraint["id"]: (feature, constraint) for feature, constraint in _exclusions(by_name)
                     if constraint["id"]}
    assert set(by_constraint) == {"C001", "C003", "C004", "C005"}
    for item in constraints:
        if item["id"] == "C006":
            assert _is_common(nodes[item["then"]]), "C006 targets common content, which has no feature"
            continue
        _op, group, (choice,) = _expression(item["if"])
        premise = _choice(nodes, group, choice)
        operator, target_group, targets = _expression(item["then"])
        if item["type"] == "excludes":
            excluded = {_choice(nodes, target_group, target).feature_id for target in targets}
        else:
            assert operator == "in"
            excluded = {child.feature_id for child in nodes[target_group].children if child.name not in targets}
        if not excluded:
            assert item["id"] == "C002" and item["id"] not in by_constraint
            continue
        owner, constraint = by_constraint[item["id"]]
        assert owner.id == premise.feature_id, item["id"]
        assert {by_name[name].id for name in constraint["operands"]} == excluded, item["id"]
    assert all(constraint["kind"] == "xorFeatures" for feature in by_name.values() for constraint in feature.constraints)


def _derivation(data: dict, nodes: dict, index: dict[str, Feature]):
    [derived] = data["derived_asset_selections"]
    projection = configurator.projection_metadata(data)
    owner, variation = derived["maps_to"].split(".")
    client = f"{projection['package']}::{owner}::{variation}"
    family = FAMILIES["sdv"]
    sources = tuple(_qualified(family, index[nodes[path].feature_id]) for path in derived["source_selections"])
    rows = set()
    for rule in derived["rules"]:
        premises = tuple(_qualified(family, index[_choice(nodes, path, rule["when"][path]).feature_id])
                         for path in derived["source_selections"])
        rows.add((f"{client}::{rule['maps_to_variant']}", premises))
    assert len(rows) == len(derived["rules"]), "the catalogue repeats a rule"
    return derived["id"], client, sources, rows, (owner, variation)


def test_the_derived_variation_and_its_rules_restate_the_catalogue_rule_table() -> None:
    data, _constraints, index, _by_name_, nodes = _sdv()
    identity, client, sources, rows, (owner, variation) = _derivation(data, nodes, index)
    dependencies = _dependencies(FAMILIES["sdv"].model)
    [derived] = [d for d in dependencies if d.metadata == "DerivedVariation"]
    assert (derived.short, derived.client, derived.suppliers) == (identity, client, sources)
    rules = [d for d in dependencies if d.metadata == "DerivationRule"]
    assert {(rule.client, rule.suppliers) for rule in rules} == rows and len(rules) == len(rows)
    assert not any(rule.short for rule in rules)
    variants = _variants(SUPERSETS["DE4SDV_SDVPlatformStack"], owner, variation)
    assert {rule.client.rsplit("::", 1)[1] for rule in rules} <= variants
    # A derived variant is never a feature: no binding targets the derived variation.
    assert not any(d.client.startswith(client) for d in dependencies if d.metadata == "FeatureBinding")


def test_the_agreement_check_covers_all_twelve_pairs_exactly_once() -> None:
    data, _constraints, index, by_name, nodes = _sdv()
    _identity, _client, _sources, rows, _variation = _derivation(data, nodes, index)
    applications = {_qualified(FAMILIES["sdv"], index[child.feature_id])
                    for child in nodes["PlatformStack.VehicleApplication"].children}
    middlewares = {_qualified(FAMILIES["sdv"], index[child.feature_id])
                   for child in nodes["PlatformStack.Middleware"].children}
    rules = [d for d in _dependencies(FAMILIES["sdv"].model) if d.metadata == "DerivationRule"]
    covered: dict[tuple[str, str], list[str]] = {}
    for rule in rules:
        assert len(rule.suppliers) == 2, rule.name
        application, middleware = rule.suppliers
        assert application in applications and middleware in middlewares, rule.name
        covered.setdefault((application, middleware), []).append(f"rule {rule.name}")
    exclusion_owners = 0
    for owner, constraint in _exclusions(by_name):
        if _qualified(FAMILIES["sdv"], owner) not in applications:
            continue
        exclusion_owners += 1
        assert constraint["id"] is None, constraint["name"]
        for name in constraint["operands"]:
            assert _qualified(FAMILIES["sdv"], by_name[name]) in middlewares, name
            covered.setdefault((_qualified(FAMILIES["sdv"], owner), _qualified(FAMILIES["sdv"], by_name[name])),
                               []).append(f"exclusion {constraint['name']}")
    every = {(application, middleware) for application in applications for middleware in middlewares}
    assert len(every) == 12 and set(covered) == every
    assert all(len(statements) == 1 for statements in covered.values()), covered
    assert sum(1 for statements in covered.values() if statements[0].startswith("rule")) == len(rows) == 8
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
    _data, constraints, index, by_name, nodes = _sdv()
    raw = _raw(FAMILIES["sdv"].model)
    options = {feature.name for feature in by_name.values() if feature.parent == "operatingSystem"}
    allowed: dict[str, set[str]] = {}
    for rule, owner in ALLOWED_LIST_RULES.items():
        lists = ALLOWED_LIST.findall(_rationale(raw, owner))
        assert len(lists) == 1, rule
        allowed[rule] = {name.strip() for name in lists[0].split(",")}
    exclusions, catalogue_lists = {}, {}
    for item in constraints:
        if item["id"] not in ALLOWED_LIST_RULES:
            continue
        _op, group, (choice,) = _expression(item["if"])
        premise = index[_choice(nodes, group, choice).feature_id]
        exclusions[item["id"]] = {name for constraint in premise.constraints if constraint["kind"] == "xorFeatures"
                                  for name in constraint["operands"] if name in options}
        _op, target_group, choices = _expression(item["then"])
        catalogue_lists[item["id"]] = {index[_choice(nodes, target_group, name).feature_id].name for name in choices}
    return options, allowed, exclusions, catalogue_lists


def test_the_allowed_lists_are_the_catalogue_lists_and_each_exclusion_set_their_complement() -> None:
    options, allowed, exclusions, catalogue_lists = _complement_inputs()
    assert options == {"linux", "android", "qnx"}
    assert allowed == catalogue_lists, "until S7 the recorded lists are the catalogue's"
    assert complement_violations(options, allowed, exclusions) == []
    assert exclusions["C002"] == set(), "the dropped rule owns no exclusion"


def test_the_complement_check_fails_when_an_operating_system_option_is_added() -> None:
    options, allowed, exclusions, _lists = _complement_inputs()
    violations = complement_violations(options | {"automotiveGradeLinux"}, allowed, exclusions)
    assert [violation.split(":")[0] for violation in violations] == ["C001", "C002", "C003"]


def test_the_dropped_rules_keep_their_rationale_in_the_model() -> None:
    raw = _raw(FAMILIES["sdv"].model)
    assert "Dropped rule C002" in _rationale(raw, "androidSDV")
    assert "Dropped rule C006" in _rationale(raw, "pedestrianDetection")


@pytest.mark.parametrize("name", ["engineering", "vehicle"])
def test_the_environment_catalogue_constraints_become_requires_constraints(name: str) -> None:
    family = FAMILIES[name]
    _data, root, constraints = _catalogue(family)
    features = _tree(family)[1]
    by_name = _by_name(features)
    nodes = configurator.collect_all_nodes(root)
    found = {constraint["id"]: (feature, constraint) for feature in features for constraint in feature.constraints}
    assert set(found) == {item["id"] for item in constraints}
    for item in constraints:
        assert item["type"] == "requires"
        _op, group, (choice,) = _expression(item["if"])
        operator, target_group, (target,) = _expression(item["then"])
        assert operator == "=="
        owner, constraint = found[item["id"]]
        assert constraint["kind"] == "requiresFeatures"
        assert owner.id == _choice(nodes, group, choice).feature_id
        assert [by_name[operand].id for operand in constraint["operands"]] == [_choice(nodes, target_group, target).feature_id]


# -- the closed world, evaluated ------------------------------------------------------------------


def _valid_selections(root) -> list[dict]:
    """Every structurally valid selection of a catalogue, as Bill-of-Features selections.

    One choice per alternative group, a non-empty subset per OR group, and both
    values of each optional leaf; a mandatory leaf stays implied. Structurally
    invalid selections are outside the equality: an exclusion presumes the
    exactly-one structure of its group, so both sides reject them, but not
    always for the same constraint IDs.
    """
    axes = []
    for node in configurator.collect_all_nodes(root).values():
        if node.is_selection_group():
            names = [child.name for child in node.children]
            axes.append((node.path, names if node.type == "alternative" else
                         [list(subset) for size in range(1, len(names) + 1)
                          for subset in itertools.combinations(names, size)]))
        elif node.is_leaf() and node.type == "optional" and node.parent.type not in GROUPS:
            axes.append((node.path, [False, True]))
    return [dict(zip((path for path, _values in axes), combination))
            for combination in itertools.product(*(values for _path, values in axes))]


def _configurator_verdict(data: dict, root, constraints: list, selection: dict) -> tuple[bool, frozenset, bool, str | None]:
    """(valid, constraint IDs, no matching rule, derived variant) as the configurator decides.

    The derived variant counts for a valid selection only: derivation applies
    to valid configurations (the kernel's derivation rule).
    """
    nodes = configurator.collect_all_nodes(root)
    assert configurator.validate_structure(root, nodes, selection) == [], selection
    implied = {leaf.path: True for leaf in configurator.find_mandatory_leaves(root) if leaf.path not in selection}
    errors = configurator.validate_constraints(constraints, {**selection, **implied})
    ids = frozenset(re.match(r"\[([^\]]+)\]", error)[1] for error in errors)
    resolved, unresolved = configurator.resolve_derived_asset_selections(data, selection)
    no_rule = any("has no rule" in error for error in unresolved)
    valid = not errors and not unresolved
    return valid, ids, no_rule, resolved[0][1] if valid and resolved else None


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


def _selected_features(selection: dict, root, features: list[Feature]) -> set[str]:
    """The features a selection selects: its choices and set leaves, plus every mandatory feature."""
    index, nodes = _by_id(features), configurator.collect_all_nodes(root)
    selected = {feature.name for feature in features if not feature.multiplicity.startswith("0")}
    for path, value in selection.items():
        if value is False:
            continue
        names = [value] if isinstance(value, str) else value if isinstance(value, list) else []
        targets = [_choice(nodes, path, name) for name in names] if names else [nodes[path]]
        selected.update(index[node.feature_id].name for node in targets if not _is_common(node))
    return selected


@pytest.mark.parametrize("name", FAMILIES)
def test_the_closed_world_decides_as_the_catalogue_on_every_structurally_valid_selection(name: str) -> None:
    """The agreement and complement checks, evaluated: on every structurally valid
    selection the model and the configurator give the same verdict, the same
    constraint IDs and the same derived variant, and an unsupported pair is
    rejected by a pair exclusion exactly where the configurator finds no rule."""
    family = FAMILIES[name]
    data, root, constraints = _catalogue(family)
    features = _tree(family)[1]
    rules = [d for d in _dependencies(family.model) if d.metadata == "DerivationRule"]
    selections = _valid_selections(root)
    assert len(selections) == {"sdv": 16128, "engineering": 27, "vehicle": 8}[name]
    verdicts = {True: 0, False: 0}
    for selection in selections:
        expected = _configurator_verdict(data, root, constraints, selection)
        assert _model_verdict(features, rules, _selected_features(selection, root, features)) == expected, selection
        verdicts[expected[0]] += 1
    assert verdicts[True] and verdicts[False], verdicts


def test_the_closed_world_check_catches_a_dropped_exclusion() -> None:
    family = FAMILIES["sdv"]
    data, root, constraints = _catalogue(family)
    features = _tree(family)[1]
    rules = [d for d in _dependencies(family.model) if d.metadata == "DerivationRule"]
    weakened = [Feature(**{**feature.__dict__, "constraints": [c for c in feature.constraints if c["id"] != "C001"]})
                for feature in features]
    selection = {**_valid_selections(root)[0], "PlatformStack.VehicleApplication": "Autoware",
                 "PlatformStack.Middleware": "EclipseSCORE", "PlatformStack.OS": "Android",
                 "PlatformStack.Hypervisor": "None"}
    expected = _configurator_verdict(data, root, constraints, selection)
    assert expected == (False, frozenset({"C001"}), False, None)
    assert _model_verdict(features, rules, _selected_features(selection, root, features)) == expected
    assert _model_verdict(weakened, rules, _selected_features(selection, root, weakened)) != expected


# -- bindings, correspondences and projection metadata -------------------------------------------------


@pytest.mark.parametrize("name", FAMILIES)
def test_one_binding_per_shared_asset_variant_with_the_asset_as_client(name: str) -> None:
    family = FAMILIES[name]
    data, root, _constraints = _catalogue(family)
    index = _by_id(_tree(family)[1])
    projection = configurator.projection_metadata(data)
    expected = set()
    for group in configurator.find_alternative_groups(root):
        if not group.maps_to:
            continue
        owner, variation = group.maps_to.split(".")
        assert owner == projection["owner"]
        for child in group.children:
            expected.add((f"{projection['package']}::{owner}::{variation}::{child.maps_to_variant}",
                          _qualified(family, index[child.feature_id])))
        assert {child.maps_to_variant for child in group.children} == _variants(
            SUPERSETS[projection["package"]], owner, variation), variation
    bindings = [d for d in _dependencies(family.model) if d.metadata == "FeatureBinding"]
    assert all(len(binding.suppliers) == 1 and binding.short is None for binding in bindings)
    assert {(binding.client, binding.suppliers[0]) for binding in bindings} == expected
    assert len(bindings) == len(expected), "a variant is bound more than once"


@pytest.mark.parametrize("name", FAMILIES)
def test_the_feature_model_carries_the_catalogue_projection_block(name: str) -> None:
    family = FAMILIES[name]
    data, _root, _constraints = _catalogue(family)
    projection = configurator.projection_metadata(data)
    code = _code(family.model)
    [match] = re.finditer(rf"#featureModel occurrence def {family.feature_model}\s*\{{", code)
    body, _end = _braced(code, match.end() - 1)
    assert _owned_metadata(body, "ProductModelProjection") == [{
        "packageName": projection["package"], "ownerName": projection["owner"], "label": projection["label"]}]
    assert len(re.findall(r"@ProductModelProjection\b", code)) == 1, "the projection is owned by the feature model only"


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


# -- each configuration against its bill of features ---------------------------------------------------


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


def _bill(path: Path) -> dict:
    return configurator.load_yaml_unique(_raw(path))


def _family_of(bill: dict) -> str:
    if any(key.startswith("PlatformStack.") for key in bill["selections"]):
        return "sdv"
    _data, root, _constraints = _catalogue(FAMILIES["engineering"])
    choices = {child.name for child in configurator.collect_all_nodes(root)["Environment.ComputeNode"].children}
    return "engineering" if bill["selections"]["Environment.ComputeNode"] in choices else "vehicle"


def _expected_redefinitions(family: Family, bill: dict) -> dict[tuple[str, ...], tuple[str, tuple[str, ...]]]:
    _data, root, _constraints = _catalogue(family)
    index = _by_id(_tree(family)[1])
    nodes = configurator.collect_all_nodes(root)
    expected: dict[tuple[str, ...], tuple[str, tuple[str, ...]]] = {}
    for path, value in bill["selections"].items():
        node = nodes[path]
        if _is_common(node):
            continue  # common content has no feature; the catalogue's mandatory leaf is implied
        feature = index[node.feature_id]
        for depth in range(1, len(feature.path)):
            expected.setdefault(feature.path[:depth], ("1", ()))
        if node.type in GROUPS:
            chosen = [index[_choice(nodes, path, choice).feature_id]
                      for choice in ([value] if isinstance(value, str) else list(value))]
            expected[feature.path] = (feature.multiplicity, tuple(item.name for item in chosen))
            for item in chosen:
                expected[item.path] = ("1", ())
        else:
            expected[feature.path] = ("1" if value else "0", ())
    return expected


BILLS = sorted(path.relative_to(ROOT) for path in (ROOT / CONFIGURATIONS_DIR).rglob("*.yaml"))


def _configuration_of(bill: Path) -> Path:
    return bill.with_name(bill.stem.replace("-", "_") + ".sysml")


def test_every_bill_of_features_has_exactly_one_pleml_configuration() -> None:
    assert len(BILLS) == 8
    assert {_configuration_of(bill).as_posix() for bill in BILLS} == set(PLEML_FILES) - set(runner.FEATURE_MODELS)


@pytest.mark.parametrize("bill", BILLS, ids=lambda path: path.stem)
def test_the_configuration_restates_its_bill_of_features(bill: Path) -> None:
    data = _bill(bill)
    family = FAMILIES[_family_of(data)]
    configuration = _configuration_of(bill)
    code = _code(configuration)
    [match] = list(_CONFIGURATION.finditer(code))
    tree = match[2]
    assert tree == family.tree
    assert f"private import {family.package}::{family.tree};" in code
    body, _end = _braced(code, match.end() - 1)
    assert _redefinitions(body) == _expected_redefinitions(family, data)
    assert _owned_metadata(body, "ProductModelProjectionName") == [{"partDefinitionName": data["name"]}]
    assert len(re.findall(r"@ProductModelProjectionName\b", code)) == 1, "the name is owned by the configuration only"


@pytest.mark.parametrize("bill", BILLS, ids=lambda path: path.stem)
def test_the_configuration_doc_is_the_folded_description(bill: Path) -> None:
    data = _bill(bill)
    match = re.search(r"#featureConfiguration occurrence \w+ : \w+ :> featureConfigurations\s*\{\s*doc /\*(.*?)\*/",
                      _raw(_configuration_of(bill)), re.DOTALL)
    assert match, bill
    doc = " ".join(line.strip().lstrip("*").strip() for line in match[1].splitlines()).strip()
    assert " ".join(doc.split()) == " ".join(data["description"].split())


def test_the_fixture_is_the_only_configuration_outside_the_authority_roots() -> None:
    assert runner.FIXTURES == (f"{CONFIGURATIONS_DIR.as_posix()}/fixtures/invalid_score_android.sysml",)
    fixture = _bill(CONFIGURATIONS_DIR / "fixtures/invalid-score-android.yaml")
    assert (fixture["selections"]["PlatformStack.Middleware"], fixture["selections"]["PlatformStack.OS"]) == (
        "EclipseSCORE", "Android")


# -- admission by the stated reading of the correspondences ----------------------------------------------


#: The class of a governed element, by the set or variation that owns it in the governed scope.
GOVERNED_CLASSES = {
    "InitialCommonCoreEngineeringContent": "common", "ReferenceOnlyAlternativeSet": "reference-only",
    "DeferredVariabilitySet": "deferred", "ExcludedSystem2ConcernSet": "excluded",
    "vehiclePlatformIntegrationMode": "admitted-alternative",
}
ADMISSIBLE = {"admitted-alternative", "common"}
#: The representation difference PLE-S recorded: the common Linux runtime, whose one choice shares the
#: single operating-system slot with the realization of an alternative that takes that slot otherwise.
REPRESENTATION_DIFFERENCES = {("InitialCommonCoreEngineeringContent::linuxROS2AutowareRuntime", "operatingSystem")}
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


def _configuration_selection(bill: Path) -> tuple[Family, set[str]]:
    family = FAMILIES[_family_of(_bill(bill))]
    code = _code(_configuration_of(bill))
    [match] = list(_CONFIGURATION.finditer(code))
    body, _end = _braced(code, match.end() - 1)
    return family, {key[-1] for key, (multiplicity, _operands) in _redefinitions(body).items() if multiplicity != "0"}


@pytest.mark.parametrize("bill", [bill for bill in BILLS if "fixtures" not in bill.parts], ids=lambda path: path.stem)
def test_admission_admits_exactly_the_governed_members(bill: Path) -> None:
    """Review R2: read as PLE-S read it, admission admits the standalone and the
    AAOS-integrated member of ADR 0014 and nothing else: the reference examples
    and both execution-environment families are not admitted."""
    family, selected = _configuration_selection(bill)
    correspondences, family_elements = _correspondences(family)
    alternative, blocking = admission(_tree(family)[1], correspondences, family_elements, selected)
    stem = _configuration_of(bill).stem
    if stem in GOVERNED_MEMBERS:
        assert (alternative, blocking) == (GOVERNED_MEMBERS[stem], [])
    else:
        assert blocking, stem


def test_admission_blocks_only_on_selected_choices_and_leaves() -> None:
    family = FAMILIES["sdv"]
    features = _tree(family)[1]
    correspondences, family_elements = _correspondences(family)
    _family, standalone = _configuration_selection(CONFIGURATIONS_DIR / "aebs-autoware-linux-lidar-camera.yaml")
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
    assert admission(features, correspondences, family_elements, standalone - {"linux"} | {"android"})[1] == [
        "realizes 2 admitted alternatives"]
