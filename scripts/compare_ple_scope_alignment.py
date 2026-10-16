#!/usr/bin/env python3
"""Compare the operational configuration path with the PLEML scope alignment (PLE-S oracle).

The oracle runs the unchanged ``tools/configure_variant.py`` on the committed
configurations and on probes generated in a temporary directory, records the
exit code (0 valid, 1 invalid, 2 input error) and the ``part :>> <variation> =
<variation>::<variant>;`` selections of each projection, and sets the result
beside the PLE-S evaluation of the same statement. Every row reports two
independent fields:

* ``configuration-valid-under-current-tool`` is the configurator's verdict;
* ``admitted-by-governed-scope`` is derived from serialized governed-scope
  data only: the feature bindings and common realizations of the PLE-S receipt
  (the graph), the classification sets of the governed-scope validation
  (common, derived, reference-only, deferred, excluded), and the declared
  catalogue correspondence that names, for a catalogue node, the governed
  element it restates. The correspondence carries no classification; the
  governed scope does.

Every difference is classified as ``equal``, ``intentional-scope``,
``intentional-representation``, ``not-expressible-under-tool`` or
``both-reject``; anything else is a ``defect`` and the run exits non-zero, as
does any unclassified selection.

The oracle is a comparison, never a second selection authority: the YAML
catalogue, the committed configurations and the configurator are read, never
changed; probes are generated outside the repository and never committed; and
every comparison it writes says ``qualified: false``.

The tree it reads is this repository by default. ``--root`` points it at an
extracted tree instead (for example ``git archive <revision>`` of the commit
that retained a record), with ``--revision`` naming that tree's revision; this
is how a retained record is reproduced at its own revision.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

import yaml

from de4sdv.semantic import ple_scope_alignment as alignment
from de4sdv.sysml_api.product_line_scope import SCOPE_SOURCE

SCHEMA = "de4sdv.ple-scope-alignment-comparison/v1"
RECEIPT_SCHEMA = "de4sdv.ple-scope-alignment/v1"
EVALUATION_SCHEMA = alignment.SCHEMA
GOVERNED_SCHEMA = "de4sdv-aebs-product-line-scope-validation/v1"
CORRESPONDENCE_SCHEMA = "de4sdv.ple-scope-alignment-catalogue-correspondence/v1"
WORKFLOW = ".github/workflows/privileged-ple-scope-alignment.yml"

CONFIGURATOR = Path("tools/configure_variant.py")
CATALOGUE = Path("model-based-product-line-engineering/feature-models/sdv_product_line.yaml")
CONFIGURATIONS = Path("model-based-product-line-engineering/feature-configurations")
CORRESPONDENCE = Path("model-based-product-line-engineering/pleml-scope-alignment/catalogue-correspondence.yaml")
SHARED_ASSETS = Path(alignment.PLATFORM_STACK_SOURCE)
MODEL = Path(alignment.MODEL_SOURCE)
SCOPE = Path(SCOPE_SOURCE)
EVALUATOR = Path("de4sdv/semantic/ple_scope_alignment.py")
SCOPE_VALIDATOR = Path("de4sdv/sysml_api/product_line_scope.py")

#: Receipt inputs the comparison depends on. A receipt whose digests of these
#: differ from the tree it is compared against does not describe that tree's
#: scope alignment and is refused; the other executor inputs are recorded.
BINDING_EXECUTOR_INPUTS = (MODEL, EVALUATOR, SCOPE_VALIDATOR)
BINDING_SOURCES = (SCOPE, SHARED_ASSETS)

CLASSES = ("equal", "intentional-scope", "intentional-representation", "not-expressible-under-tool",
           "both-reject", "defect")
EVIDENCE_KINDS = ("fresh", "retained")
EXIT_MEANING = {0: "valid", 1: "invalid", 2: "input error"}

#: Governed-scope validation sets and the classification they confer.
GOVERNED_SETS = (
    ("common_core", "common"),
    ("derived_realization", "derived"),
    ("reference_only", "reference-only"),
    ("deferred", "deferred"),
    ("excluded_system2", "excluded"),
)
#: Classifications a declared correspondence may confer (the graph confers the rest).
CORRESPONDENCE_CLASSIFICATIONS = ("common", "reference-only", "deferred", "excluded")
ADMISSIBLE = {"admitted-alternative", "common"}
INADMISSIBLE = {"reference-only", "deferred", "excluded", "not-in-governed-scope"}
CATALOGUE_ROLES = {"F": "feature", "C": "common capability", "D": "derived asset", "PL": "product line"}

MEMBER_TEMPLATE = "aebs-autoware-linux-lidar-camera.yaml"
#: An override value that removes the key from the generated probe.
REMOVE = "<removed>"


class OracleRefusal(ValueError):
    """An input is missing, inconsistent or outside the reviewed shape."""


@dataclass(frozen=True)
class Case:
    """One comparison: an operational input against a PLE-S statement."""

    case: str
    tag: str
    purpose: str
    configuration: str | None = None  # committed Bill-of-Features, relative to the configurations directory
    ple_s: str | None = None  # the PLE-S configuration of the receipt this case restates
    probe: str | None = None  # "encode-ple-s" or "overrides": a generated, never committed, probe
    name: str | None = None  # the Bill-of-Features name of a generated probe
    overrides: tuple[tuple[str, Any], ...] = field(default_factory=tuple)


#: The case table: the design's rows (PLE-S design note, section 4) plus the
#: rows the independent V&V review asked for. No row carries an expected
#: outcome: the oracle records what the tool and the scope say.
CASES: tuple[Case, ...] = (
    Case("standalone-member", "member", "the standalone planned reference member",
         configuration="aebs-autoware-linux-lidar-camera.yaml",
         ple_s="standaloneAutowareAEBSReferenceMemberConfiguration"),
    Case("aaos-integrated-member", "member", "the AAOS-integrated planned reference member",
         configuration="middleware-autoware-aaos-sdv-reference.yaml",
         ple_s="aaosIntegratedAutowareAEBSReferenceMemberConfiguration"),
    Case("both-alternatives", "probe", "the PLE-S probe that selects both alternatives, encoded for the tool",
         ple_s="bothIntegrationModesProbe", probe="encode-ple-s", name="BothIntegrationModesProbe"),
    Case("no-alternative", "probe", "the PLE-S probe that selects no alternative, encoded for the tool",
         ple_s="noIntegrationModeProbe", probe="encode-ple-s", name="NoIntegrationModeProbe"),
    Case("ug-09-eclipse-score", "UG-09", "a committed example that selects a reference-only middleware",
         configuration="example-linux-score-autoware.yaml"),
    Case("ug-09-apollo-qnx-qvm", "UG-09",
         "a committed example that selects a reference-only application, OS and hypervisor",
         configuration="apollo-qnx-qvm.yaml"),
    Case("ug-09-autosar-acrn", "UG-09",
         "the remaining reference-only middleware and hypervisor on the standalone derived set",
         probe="overrides", name="AUTOSARAdaptiveACRNProbe",
         overrides=(("PlatformStack.Middleware", "AUTOSARAdaptive"), ("PlatformStack.Hypervisor", "ACRN"))),
    Case("ug-10-openpilot-no-middleware", "UG-10",
         "the catalogue treats the driving stack as a feature; Openpilot without middleware has a derivation rule",
         probe="overrides", name="OpenpilotNoMiddlewareProbe",
         overrides=(("PlatformStack.VehicleApplication", "Openpilot"), ("PlatformStack.Middleware", "None"))),
    Case("ug-10-radar-only", "UG-10",
         "the catalogue treats perception sensors as features; a radar-only selection is tool-valid",
         probe="overrides", name="RadarOnlySensingProbe",
         overrides=(("SensingBoundary.PerceptionSensors", ["Radar"]),)),
    Case("ug-10-lidar-only", "UG-10", "the common sensing baseline without its camera",
         probe="overrides", name="LidarOnlySensingProbe",
         overrides=(("SensingBoundary.PerceptionSensors", ["LiDAR"]),)),
    Case("ug-10-camera-only", "UG-10", "the common sensing baseline without its LiDAR",
         probe="overrides", name="CameraOnlySensingProbe",
         overrides=(("SensingBoundary.PerceptionSensors", ["Camera"]),)),
    Case("ug-10-vehicle-target-aebs-false", "UG-10",
         "the common vehicle-target AEBS capability switched off on the capability axis",
         probe="overrides", name="VehicleTargetAEBSOffProbe",
         overrides=(("Capabilities.ForwardCollisionMitigation.VehicleTargetAEBS", False),)),
    Case("catalogue-only-adaptive-cruise-control", "catalogue-only",
         "a catalogue feature candidate the governed scope has no element for",
         probe="overrides", name="AdaptiveCruiseControlProbe",
         overrides=(("Capabilities.AdaptiveCruiseControl", True),)),
    Case("derived-set-mixed", "UG-14",
         "derived realizations of both alternatives mixed in one tool-valid selection",
         probe="overrides", name="MixedDerivedSetProbe",
         overrides=(("PlatformStack.Middleware", "AndroidSDV"),)),
    Case("both-axes-negative", "independence", "tool-invalid and not admitted, for independent reasons",
         configuration="fixtures/invalid-score-android.yaml"),
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _label(path: Path, root: Path) -> str:
    """A path as the record names it: tree-relative inside the tree, absolute outside."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise OracleRefusal(f"git {args[0]} failed in {root}")
    return result.stdout.decode().strip()


def source_baseline(path: Path, relative: Path) -> str:
    """The content identity the configurator prints as the shared-assets source baseline.

    ``git hash-object`` needs no repository, so an extracted tree yields the
    same identity as a checkout.
    """
    result = subprocess.run(["git", "hash-object", "--stdin"], input=path.read_bytes(), capture_output=True,
                            check=False)
    if result.returncode:
        raise OracleRefusal(f"git hash-object failed for {relative.as_posix()}")
    return f"git-blob:{result.stdout.decode().strip()}:{relative.as_posix()} (content-addressed)"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise OracleRefusal(message)


def _json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise OracleRefusal(f"{label} is not readable JSON: {exc}") from exc
    _require(isinstance(payload, dict), f"{label} is not a JSON object")
    return payload


# -- the PLE-S side: receipt and governed scope ----------------------------------------


def load_evidence(receipt_path: Path, governed_path: Path, *, evidence: str, run_id: str,
                  artifact: str, root: Path = ROOT) -> dict[str, Any]:
    """The PLE-S receipt and governed-scope validation, verified and bound to the tree at ``root``."""
    _require(evidence in EVIDENCE_KINDS, f"evidence must be one of {EVIDENCE_KINDS}")
    _require(re.fullmatch(r"[0-9]+", run_id or "") is not None, "the run id is the numeric workflow run id")
    receipt = _json(receipt_path, "the receipt")
    governed = _json(governed_path, "the governed-scope validation")
    _require(receipt.get("schema") == RECEIPT_SCHEMA, "the receipt is not a PLE-S scope-alignment receipt")
    _require(receipt.get("mode") == "licensed-serialization" and receipt.get("fresh_serialization") is True,
             "the receipt is not a fresh licensed serialization")
    for key in ("qualified", "adoption_authorized", "authority_activation_authorized"):
        _require(receipt.get(key) is False, f"the receipt must say {key}: false")
    _require(receipt.get("executor_source_dirty") is False, "the receipt was recorded on a dirty executor checkout")
    expectation = receipt.get("expectation") or {}
    _require(expectation.get("matches") is True, "the receipt does not reproduce the expected outcome table")
    report = receipt.get("alignment") or {}
    _require(report.get("schema") == EVALUATION_SCHEMA, "the receipt carries no scope-alignment evaluation")
    _require(governed.get("schema") == GOVERNED_SCHEMA, "the governed-scope validation has the wrong schema")
    governed_digest = sha256_of(governed_path)
    _require((receipt.get("artifact_sha256") or {}).get("governed-scope-validation.json") == governed_digest,
             "the governed-scope validation is not the one the receipt recorded")
    executor = receipt.get("executor_revision") or ""
    _require(re.fullmatch(r"[0-9a-f]{40}", executor) is not None, "the receipt has no exact executor revision")
    _require(artifact == f"ple-scope-alignment-{executor}-{run_id}",
             "the artifact name does not bind the receipt's executor revision and the run id")
    if evidence == "fresh":
        _require(git(root, "rev-parse", "HEAD") == executor, "fresh evidence must be the receipt of this exact head")

    # Content binding: the receipt must describe the scope alignment of the tree it is compared against.
    executor_inputs: dict[str, str] = receipt.get("executor_inputs") or {}
    manifest = {item.get("path"): item.get("sha256") for item in receipt.get("source_manifest") or []}
    stale = []
    for path in BINDING_EXECUTOR_INPUTS:
        if not (root / path).is_file() or executor_inputs.get(path.as_posix()) != sha256_of(root / path):
            stale.append(path.as_posix())
    for path in BINDING_SOURCES:
        if not (root / path).is_file() or manifest.get(path.as_posix()) != sha256_of(root / path):
            stale.append(path.as_posix())
    _require(not stale, "the receipt was produced from inputs that differ from this tree: "
             + ", ".join(stale) + "; rerun the licensed scope alignment and retain its receipt")
    matching = {path: digest == sha256_of(root / path) for path, digest in sorted(executor_inputs.items())
                if (root / path).is_file()}

    experiment = receipt.get("experiment") or {}
    identity = {
        "evidence": evidence,
        "workflow": WORKFLOW,
        "run_id": run_id,
        "artifact": artifact,
        "executor_revision": executor,
        "executor_source_dirty": False,
        "receipt_sha256": sha256_of(receipt_path),
        "governed_scope_validation_sha256": governed_digest,
        "model_sha256": (receipt.get("model") or {}).get("sha256"),
        "evaluator_sha256": (receipt.get("evaluator") or {}).get("sha256"),
        "governed_scope_sha256": manifest.get(SCOPE.as_posix()),
        "shared_assets_sha256": manifest.get(SHARED_ASSETS.as_posix()),
        "interpreter_revision": experiment.get("interpreter_revision"),
        "interpreter_sha256": experiment.get("interpreter_sha256"),
        "pleml_pin": experiment.get("pleml_pin"),
        "library_sha256": experiment.get("library_sha256"),
        "serializer_version": receipt.get("serializer_version"),
        "expectation_matches": True,
        "qualified": False,
        "executor_inputs_matching_tree": matching,
    }
    return {"receipt": receipt, "governed": governed, "identity": identity}


class ScopeIndex:
    """What the serialized PLE-S evaluation and the governed scope say, by name."""

    def __init__(self, receipt: dict[str, Any], governed: dict[str, Any]) -> None:
        report = receipt["alignment"]
        self.bindings: dict[tuple[str, str], dict[str, Any]] = {}
        for item in report.get("bindings") or []:
            key = (item["variation"], item["variant"])
            _require(key not in self.bindings, f"the receipt binds {key[0]}::{key[1]} more than once")
            self.bindings[key] = item
        self.bound_variations = {variation for variation, _ in self.bindings}
        self.alternatives: dict[str, str] = dict(governed["vehicle_platform_integration_mode"]["alternatives"])
        self.common: dict[str, str] = dict(governed["common_core"])
        self.common_realizations: dict[tuple[str, str], dict[str, Any]] = {}
        for item in report.get("common_assets") or []:
            realization = item.get("superset_realization")
            if realization:
                self.common_realizations[(realization["variation"], realization["variant"])] = item
        self.sets: dict[str, tuple[str, str, str]] = {}  # governed name -> (set, classification, element id)
        for set_name, classification in GOVERNED_SETS:
            for name, element_id in (governed.get(set_name) or {}).items():
                _require(name not in self.sets, f"governed element {name} is classified twice")
                self.sets[name] = (set_name, classification, element_id)
        for name, element_id in self.alternatives.items():
            _require(name not in self.sets, f"alternative {name} is also classified content")
            self.sets[name] = ("vehicle_platform_integration_mode.alternatives", "admitted-alternative", element_id)
        self.configurations: dict[str, dict[str, Any]] = {
            item["configuration"]: item for item in report.get("configurations") or []
        }
        self.features = {item["feature"] for item in report.get("features") or [] if item.get("role") == "alternative"}
        _require(self.features == set(self.alternatives), "the receipt's alternatives differ from the governed scope")
        for item in self.bindings.values():
            _require(item["feature"] in self.features, f"binding {item['binding']} names an unknown feature")
        self.differences = [
            item for item in receipt.get("known_representation_differences") or []
            if item.get("confirmed_in_graph") is True
        ]

    def binds(self, feature: str | None, variation: str) -> bool:
        """Whether ``feature`` binds a variant of ``variation``."""
        return feature is not None and any(
            key[0] == variation and item["feature"] == feature for key, item in self.bindings.items())

    def expected_selection(self, configuration: dict[str, Any]) -> dict[str, str]:
        """Derived variants plus common realizations of a valid PLE-S configuration."""
        selected = {item["variation"]: item["variant"] for item in configuration.get("derived_asset_variants") or []}
        for (variation, variant), item in self.common_realizations.items():
            if item["asset"] in (configuration.get("common_assets") or []):
                _require(variation not in selected, f"{variation} is both derived and a common realization")
                selected[variation] = variant
        return selected


# -- the operational side: catalogue and correspondence ------------------------------


def load_configurator(root: Path):
    """Import the configurator of the tree at ``root`` for its catalogue parser (never re-implemented).

    The subprocess runs of the same file are the operational verdicts; the
    import only reads the catalogue in the tool's own grammar.
    """
    path = (root / CONFIGURATOR).resolve()
    _require(path.is_file(), f"the configurator is missing at {path}")
    name = "_de4sdv_configurator_" + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    _require(spec is not None and spec.loader is not None, f"cannot import the configurator at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Catalogue:
    """The YAML catalogue, parsed by the configurator's own functions."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root
        self.module = load_configurator(root)
        self.path = root / CATALOGUE
        with self.path.open(encoding="utf-8") as handle:
            self.data = self.module.load_yaml_unique(handle)
        self.tree, _constraints = self.module.build_feature_tree(self.data)
        self.nodes = self.module.collect_all_nodes(self.tree)  # path -> node
        self.by_id = {node.feature_id: node for node in self.module.iter_feature_nodes(self.tree) if node.feature_id}
        self.projection = self.module.projection_metadata(self.data)
        self.selectable_variations: dict[str, Any] = {}
        for node in self.nodes.values():
            if node.is_selection_group() and isinstance(node.maps_to, str):
                self.selectable_variations[node.maps_to.rsplit(".", 1)[-1]] = node
        self.derived_variations = {
            str(item.get("maps_to", "")).rsplit(".", 1)[-1]: item.get("id")
            for item in self.data.get("derived_asset_selections") or []
        }

    def load_bof(self, path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as handle:
            data = self.module.load_yaml_unique(handle)
        _require(isinstance(data, dict) and isinstance(data.get("selections"), dict),
                 f"{path.name} is not a Bill-of-Features")
        return data

    @staticmethod
    def role(node) -> str:
        prefix = str(node.feature_id or "").split("-", 1)[0]
        return CATALOGUE_ROLES.get(prefix, "unregistered")

    @staticmethod
    def variant_of(node) -> tuple[str, str] | None:
        parent = node.parent
        if parent is None or not parent.is_selection_group() or not isinstance(parent.maps_to, str):
            return None
        if not isinstance(node.maps_to_variant, str):
            return None
        return parent.maps_to.rsplit(".", 1)[-1], node.maps_to_variant

    @staticmethod
    def is_choice(node) -> bool:
        """A child of a selection group: selected by name through the group's key."""
        return node.parent is not None and node.parent.is_selection_group()

    @staticmethod
    def is_implied_when_absent(node) -> bool:
        """A mandatory leaf outside any selection group: part of every product unless switched off."""
        return node.is_leaf() and node.type == "mandatory" and not Catalogue.is_choice(node)

    def child_for_variant(self, variation: str, variant: str):
        group = self.selectable_variations.get(variation)
        _require(group is not None, f"{variation} is not a selectable catalogue variation")
        matches = [child for child in group.children if child.maps_to_variant == variant]
        _require(len(matches) == 1, f"{variation}::{variant} has {len(matches)} catalogue choices")
        return matches[0]


def load_correspondence(path: Path, catalogue: Catalogue, index: ScopeIndex) -> dict[str, dict[str, Any]]:
    """Catalogue node id -> governed element, classified by the governed scope (fail closed)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise OracleRefusal(f"the catalogue correspondence is not readable: {exc}") from exc
    _require(isinstance(data, dict) and data.get("schema") == CORRESPONDENCE_SCHEMA,
             "the catalogue correspondence has the wrong schema")
    _require(data.get("catalogue") == CATALOGUE.as_posix() and data.get("governed_scope") == SCOPE.as_posix(),
             "the catalogue correspondence names other sources")
    entries = data.get("correspondence")
    _require(isinstance(entries, list) and entries, "the catalogue correspondence lists no entries")
    result: dict[str, dict[str, Any]] = {}
    for position, entry in enumerate(entries):
        _require(isinstance(entry, dict) and set(entry) <= {"node", "governed", "note"} and "node" in entry
                 and "governed" in entry, f"correspondence[{position}] must declare node and governed")
        node_id = entry["node"]
        _require(isinstance(node_id, str) and node_id in catalogue.by_id,
                 f"correspondence[{position}] names an unknown catalogue node: {node_id!r}")
        _require(node_id not in result, f"catalogue node {node_id} corresponds more than once")
        governed = entry["governed"]
        if governed is None:
            note = entry.get("note")
            _require(isinstance(note, str) and note.strip(), f"{node_id}: a null correspondence needs a note")
            result[node_id] = {"governed": None, "governed_id": None, "set": None,
                               "classification": "not-in-governed-scope", "note": note.strip()}
            continue
        _require(isinstance(governed, str) and governed in index.sets,
                 f"{node_id}: {governed!r} is not a serialized governed-scope element")
        set_name, classification, element_id = index.sets[governed]
        _require(classification in CORRESPONDENCE_CLASSIFICATIONS,
                 f"{node_id}: a correspondence may not confer {classification} ({governed}); the graph does")
        result[node_id] = {"governed": governed, "governed_id": element_id, "set": set_name,
                           "classification": classification, "note": entry.get("note")}
    return result


# -- probes --------------------------------------------------------------------------


def encode_ple_s_configuration(configuration: dict[str, Any], index: ScopeIndex, catalogue: Catalogue,
                               template: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """The tool's encoding of a PLE-S configuration: its alternatives' bound variants per selectable variation.

    A variation that no alternative binds (the common ``vehicleApplication``)
    keeps the template's selection. One variant becomes the scalar the tool
    takes; none removes the key; more than one has no scalar encoding and is
    handed to the tool as a list so its actual response is recorded.
    """
    data = copy.deepcopy(template)
    per_variation: dict[str, list[str]] = {}
    for feature in configuration.get("selected_alternatives") or []:
        for (variation, variant), item in sorted(index.bindings.items()):
            if item["feature"] == feature and variation in catalogue.selectable_variations:
                per_variation.setdefault(variation, []).append(catalogue.child_for_variant(variation, variant).name)
    encoding: dict[str, Any] = {"selected_alternatives": list(configuration.get("selected_alternatives") or []),
                                "selections": {}, "removed": [], "expressible": True}
    for variation, group in sorted(catalogue.selectable_variations.items()):
        if variation not in index.bound_variations:
            continue
        names = per_variation.get(variation, [])
        if not names:
            data["selections"].pop(group.path, None)
            encoding["removed"].append(group.path)
        elif len(names) == 1:
            data["selections"][group.path] = names[0]
            encoding["selections"][group.path] = names[0]
        else:
            data["selections"][group.path] = names
            encoding["selections"][group.path] = names
            encoding["expressible"] = False
    return data, encoding


def generate_probe(case: Case, index: ScopeIndex, catalogue: Catalogue) -> tuple[dict[str, Any], dict[str, Any]]:
    template = catalogue.load_bof(catalogue.root / CONFIGURATIONS / MEMBER_TEMPLATE)
    encoding: dict[str, Any] = {"expressible": True}
    if case.probe == "encode-ple-s":
        configuration = index.configurations.get(case.ple_s or "")
        _require(configuration is not None, f"{case.case}: the receipt has no configuration {case.ple_s}")
        data, encoding = encode_ple_s_configuration(configuration, index, catalogue, template)
    elif case.probe == "overrides":
        data = copy.deepcopy(template)
        for key, value in case.overrides:
            if value == REMOVE:
                data["selections"].pop(key, None)
            else:
                data["selections"][key] = copy.deepcopy(value)
        encoding["overrides"] = {key: copy.deepcopy(value) for key, value in case.overrides}
    else:
        raise OracleRefusal(f"{case.case}: unknown probe kind {case.probe!r}")
    data["name"] = case.name
    data["description"] = (f"Generated probe of the PLE-S comparison oracle: {case.purpose}. "
                           "Not a member, not a committed configuration.")
    return data, encoding


# -- the tool ---------------------------------------------------------------------


SELECTION = re.compile(r"^\s*part :>> (\w+) = (\w+)::(\w+);\s*$", re.MULTILINE)
DERIVED = re.compile(r"^\s*\*\s+(\w+) = (\w+) \(derived by ([A-Z][A-Z0-9-]*)\)\s*$", re.MULTILINE)
HEADERS = {
    "shared_assets_sha256": re.compile(r"^ \* Shared-assets model SHA-256: ([0-9a-f]{64})$", re.MULTILINE),
    "feature_model_sha256": re.compile(r"^ \* Feature model SHA-256: ([0-9a-f]{64})$", re.MULTILINE),
    "bill_of_features_sha256": re.compile(r"^ \* Bill-of-Features SHA-256: ([0-9a-f]{64})$", re.MULTILINE),
    "shared_assets_source_baseline": re.compile(r"^ \* Shared-assets source baseline: (.+)$", re.MULTILINE),
}
MESSAGE = re.compile(r"^\s+[\u2022-] (.+)$")
CONSTRAINT = re.compile(r"^\[([A-Z]\d{3})\]")


def parse_projection(text: str) -> dict[str, Any]:
    """Selected variants and header digests of a generated projection."""
    selected: dict[str, str] = {}
    for variation, qualifier, variant in SELECTION.findall(text):
        _require(variation == qualifier, f"projection selects {variation} through {qualifier}")
        _require(variation not in selected, f"projection selects {variation} twice")
        selected[variation] = variant
    _require(selected, "projection selects no variant")
    headers: dict[str, str] = {}
    for key, pattern in HEADERS.items():
        match = pattern.search(text)
        _require(match is not None, f"projection header lacks {key}")
        headers[key] = match.group(1)
    derived = {variation: {"variant": variant, "rule": rule} for variation, variant, rule in DERIVED.findall(text)}
    for variation, item in derived.items():
        _require(selected.get(variation) == item["variant"], f"derived {variation} differs from its selection")
    return {"selected": selected, "derived": derived, "headers": headers}


def run_configurator(bof: Path, output: Path, root: Path = ROOT) -> dict[str, Any]:
    """Run the unchanged configurator of the tree once and record exactly what it says."""
    argv = [sys.executable, str(root / CONFIGURATOR), "--feature-model", str(root / CATALOGUE),
            "--bof", str(bof), "--output", str(output)]
    result = subprocess.run(argv, cwd=str(root), capture_output=True, text=True, timeout=120, check=False)
    messages = [match.group(1).strip() for match in map(MESSAGE.match, result.stderr.splitlines()) if match]
    projection = None
    if result.returncode == 0:
        _require(output.is_file(), "the configurator reported success without a projection")
        projection = parse_projection(output.read_text(encoding="utf-8"))
    constraints = sorted({match.group(1) for match in map(CONSTRAINT.match, messages) if match})
    if result.returncode == 0:
        summary = "valid"
    elif result.returncode == 1:
        summary = f"invalid ({len(messages)} violation{'s' if len(messages) != 1 else ''}): " + (
            ", ".join(constraints) if constraints else (messages[0] if messages else "no message"))
    else:
        summary = f"input error (exit {result.returncode})"
    return {
        "valid": result.returncode == 0,
        "exit_code": result.returncode,
        "meaning": EXIT_MEANING.get(result.returncode, "unexpected"),
        "messages": messages,
        "violated_constraints": constraints,
        "summary": summary,
        "projection": projection,
    }


# -- admission ------------------------------------------------------------------------


def _classify_node(node, catalogue: Catalogue, index: ScopeIndex,
                   correspondence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    kinds: list[dict[str, Any]] = []
    variant = catalogue.variant_of(node)
    if variant is not None:
        binding = index.bindings.get(variant)
        if binding is not None:
            kinds.append({
                "kind": "admitted-alternative", "governed": binding["feature"], "governed_id": binding["feature_id"],
                "variant": f"{variant[0]}::{variant[1]}",
                "source": f"receipt:alignment.bindings[{binding['binding']}] (FeatureBinding; derived realization)",
            })
        realization = index.common_realizations.get(variant)
        if realization is not None:
            kinds.append({
                "kind": "common", "governed": realization["asset"], "governed_id": realization["element_id"],
                "variant": f"{variant[0]}::{variant[1]}",
                "source": (f"receipt:alignment.common_assets[{realization['asset']}].superset_realization"
                           f"[{realization['superset_realization']['dependency']}]"),
            })
    entry = correspondence.get(node.feature_id)
    if entry is not None:
        source = (f"governed-scope-validation:{entry['set']}[{entry['governed']}] via catalogue correspondence"
                  if entry["governed"] else "catalogue correspondence: no governed element")
        kinds.append({"kind": entry["classification"], "governed": entry["governed"],
                      "governed_id": entry["governed_id"], "variant": f"{variant[0]}::{variant[1]}" if variant else None,
                      "source": source, **({"note": entry["note"]} if entry.get("note") else {})})
    return kinds


def classify_selections(selections: dict[str, Any], catalogue: Catalogue, index: ScopeIndex,
                        correspondence: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per selected catalogue item, with every classification the data confers."""
    records: list[dict[str, Any]] = []
    for path, value in selections.items():
        node = catalogue.nodes.get(path)
        if node is None:
            records.append({"path": path, "node": None, "catalogue_role": None, "value": value, "selected": True,
                            "item": path, "classifications": [], "unclassified": "unknown catalogue path"})
            continue
        if node.is_selection_group():
            group_kinds = [kind for kind in _classify_node(node, catalogue, index, correspondence)]
            if isinstance(value, str):
                names = [value]
            elif isinstance(value, list):
                names = [item for item in value if isinstance(item, str)]
            else:
                names = []
            children = {child.name: child for child in node.children}
            unknown = [name for name in names if name not in children]
            if not names or unknown or not isinstance(value, (str, list)):
                records.append({"path": path, "node": node.feature_id, "catalogue_role": catalogue.role(node),
                                "value": value, "selected": True, "item": path, "classifications": group_kinds,
                                "unclassified": f"value is not a catalogue choice: {value!r}"})
                continue
            for name in names:
                child = children[name]
                kinds = _classify_node(child, catalogue, index, correspondence)
                records.append({
                    "path": path, "node": child.feature_id, "catalogue_role": catalogue.role(child),
                    "value": value, "selected": True, "item": f"{path} = {name}",
                    "group": {"node": node.feature_id, "type": node.type, "catalogue_role": catalogue.role(node),
                              "classifications": group_kinds},
                    "classifications": kinds,
                    "unclassified": None if kinds else "no governed classification",
                })
            continue
        kinds = _classify_node(node, catalogue, index, correspondence)
        selected = value is True
        records.append({
            "path": path, "node": node.feature_id, "catalogue_role": catalogue.role(node), "value": value,
            "selected": selected, "item": f"{path} = {value!r}", "classifications": kinds,
            "unclassified": (None if kinds else "no governed classification") if isinstance(value, bool)
            else f"value is not a YAML boolean: {value!r}",
        })
    return records


def representable_nodes(index: ScopeIndex, catalogue: Catalogue,
                        correspondence: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Common asset -> catalogue nodes that represent it (correspondence and graph realization).

    Only selection surface counts: choices of a selection group and leaves.
    A group node corresponding to common content is variability, not a
    representation.
    """
    nodes: dict[str, list[str]] = {name: [] for name in index.common}
    for node_id, entry in correspondence.items():
        node = catalogue.by_id[node_id]
        if entry["classification"] == "common" and entry["governed"] in nodes and not node.is_selection_group():
            nodes[entry["governed"]].append(node_id)
    for (variation, variant), item in index.common_realizations.items():
        if item["asset"] in nodes and variation in catalogue.selectable_variations:
            child = catalogue.child_for_variant(variation, variant)
            if child.feature_id not in nodes[item["asset"]]:
                nodes[item["asset"]].append(child.feature_id)
    return {name: sorted(ids) for name, ids in nodes.items()}


def _common_asset_status(asset: str, element_id: str, nodes: list[str], chosen: set[str], dropped: set[str],
                         catalogue: Catalogue) -> dict[str, Any]:
    """How one common asset is represented by the selections: every representable node counts.

    A node is represented when it is chosen (a group choice, or a leaf set to
    true), implied when it is a mandatory leaf outside every selection group
    that the selections leave untouched, dropped when such a leaf is switched
    off, and missing otherwise. The asset is represented only when no node is
    missing or dropped (V&V finding R1 of PR #379).
    """
    status_by_node: dict[str, str] = {}
    for node_id in nodes:
        if node_id in chosen:
            status_by_node[node_id] = "represented"
        elif node_id in dropped:
            status_by_node[node_id] = "dropped"
        elif catalogue.is_implied_when_absent(catalogue.by_id[node_id]):
            status_by_node[node_id] = "implied"
        else:
            status_by_node[node_id] = "missing"
    represented = sorted(n for n, s in status_by_node.items() if s == "represented")
    implied = sorted(n for n, s in status_by_node.items() if s == "implied")
    missing = sorted(n for n, s in status_by_node.items() if s == "missing")
    dropped_nodes = sorted(n for n, s in status_by_node.items() if s == "dropped")
    if not nodes:
        complete, status = None, "outside the catalogue's selection surface"
    elif not missing and not dropped_nodes:
        complete, status = True, "represented" + (f" (implied: {', '.join(implied)})" if implied else "")
    elif represented or implied:
        complete, status = False, "partially represented"
    else:
        complete, status = False, "not represented"
    if complete is False:
        details = [f"missing: {', '.join(missing)}" if missing else "",
                   f"dropped: {', '.join(dropped_nodes)}" if dropped_nodes else ""]
        status += " (" + "; ".join(d for d in details if d) + ")"
    return {"asset": asset, "element_id": element_id, "representable_by": nodes, "represented_by": represented,
            "implied_by": implied, "missing": missing, "dropped": dropped_nodes, "complete": complete,
            "status": status}


def admission(records: list[dict[str, Any]], index: ScopeIndex, catalogue: Catalogue,
              representable: dict[str, list[str]]) -> dict[str, Any]:
    """``admitted-by-governed-scope`` with its reasons, from the classified selections."""
    realized: dict[str, list[str]] = {}
    chosen_variants: dict[str, str] = {}
    chosen_nodes: set[str] = set()
    dropped_nodes: set[str] = set()
    reasons: list[str] = []
    blocking: list[str] = []
    unclassified: list[str] = []
    for record in records:
        if record["unclassified"]:
            unclassified.append(f"{record['item']}: {record['unclassified']}")
            continue
        if not record["selected"]:
            if record["value"] is False and record["node"]:
                dropped_nodes.add(record["node"])
            kinds = ", ".join(sorted({kind["kind"] for kind in record["classifications"]}))
            reasons.append(f"{record['item']}: not selected ({kinds})")
            continue
        chosen_nodes.add(record["node"])
        kinds = {kind["kind"] for kind in record["classifications"]}
        for kind in record["classifications"]:
            if kind["kind"] == "admitted-alternative":
                realized.setdefault(kind["governed"], []).append(record["item"])
                variation, variant = kind["variant"].split("::", 1)
                chosen_variants[variation] = variant
        described = "; ".join(f"{kind['kind']} {kind['governed']}" if kind["governed"] else kind["kind"]
                              for kind in record["classifications"])
        reasons.append(f"{record['item']}: {described}")
        if not (kinds & ADMISSIBLE) and (kinds & INADMISSIBLE):
            blocking.append(f"{record['item']}: {described}")
    for record in records:
        group = record.get("group")
        if group and group["classifications"]:
            described = "; ".join(f"{kind['kind']} {kind['governed']}" for kind in group["classifications"])
            note = f"{record['path']} is catalogue variability ({group['catalogue_role']}); governed: {described}"
            if note not in reasons:
                reasons.append(note)
    implied_alternatives = sorted(realized)
    implied = implied_alternatives[0] if len(implied_alternatives) == 1 else None
    missing_derived: list[str] = []
    if implied is not None:
        for (variation, variant), item in sorted(index.bindings.items()):
            if item["feature"] == implied and variation in catalogue.selectable_variations:
                if chosen_variants.get(variation) != variant:
                    missing_derived.append(f"{variation}::{variant}")
    common_assets = [
        _common_asset_status(asset, index.common[asset], representable.get(asset, []), chosen_nodes, dropped_nodes,
                             catalogue)
        for asset in sorted(index.common)
    ]
    incomplete = [item for item in common_assets if item["complete"] is False]
    # The confirmed representation difference exempts an asset only in the rows whose implied
    # alternative binds the variation that causes it (V&V finding R3 of PR #379).
    covered = {item["common_asset"] for item in index.differences if index.binds(implied, item["variation"])}
    uncovered = [item for item in incomplete if item["asset"] not in covered]
    verdict: list[str] = []
    if unclassified:
        verdict.append("unclassified selections: " + "; ".join(unclassified))
    if blocking:
        verdict.append("not admitted content selected: " + "; ".join(blocking))
    if len(implied_alternatives) == 0:
        verdict.append("no admitted alternative is realized by the selections")
    elif len(implied_alternatives) > 1:
        verdict.append("the selections realize more than one admitted alternative: " + ", ".join(implied_alternatives))
    elif missing_derived:
        verdict.append(f"derived realizations of {implied} missing from the selections: " + ", ".join(missing_derived))
    if uncovered:
        verdict.append("common content not fully represented by the selections: "
                       + "; ".join(f"{item['asset']} {item['status']}" for item in uncovered))
    admitted = not verdict
    return {
        "admitted": admitted,
        "implied_alternative": implied,
        "alternatives_realized": {name: items for name, items in sorted(realized.items())},
        "summary": (f"yes: {implied} (every selection is common content or its derived realization)"
                    if admitted else "no: " + " | ".join(verdict)),
        "verdict_reasons": verdict,
        "reasons": reasons,
        "unclassified": unclassified,
        "common_assets": common_assets,
        "incomplete_common_assets": [item["asset"] for item in incomplete],
        "exempted_common_assets": sorted(item["asset"] for item in incomplete if item["asset"] in covered),
        "selections": records,
    }


# -- comparison and classification ------------------------------------------------


def _ple_s_side(case: Case, index: ScopeIndex, admitted: dict[str, Any]) -> dict[str, Any]:
    if case.ple_s is not None:
        configuration = index.configurations.get(case.ple_s)
        _require(configuration is not None, f"{case.case}: the receipt has no configuration {case.ple_s}")
        return {
            "configuration": case.ple_s,
            "element_id": configuration.get("element_id"),
            "role": configuration.get("role"),
            "member": configuration.get("member"),
            "status": configuration.get("status"),
            "violated_bound": configuration.get("violated_bound"),
            "selected_alternatives": list(configuration.get("selected_alternatives") or []),
            "derived_asset_variants": {item["variation"]: item["variant"]
                                       for item in configuration.get("derived_asset_variants") or []},
            "common_assets": list(configuration.get("common_assets") or []),
            "summary": (configuration.get("status", "?")
                        + (f" ({configuration['violated_bound']} bound)" if configuration.get("violated_bound") else "")),
        }
    inadmissible = sorted({
        f"{kind['governed']} ({kind['kind']})" if kind["governed"] else kind["kind"]
        for record in admitted["selections"] if record["selected"] and not record["unclassified"]
        for kind in record["classifications"]
        if kind["kind"] in INADMISSIBLE and not ({k["kind"] for k in record["classifications"]} & ADMISSIBLE)
    })
    if inadmissible:
        reason = "no PLE-S configuration: the admitted tree has no feature for " + ", ".join(inadmissible)
    elif admitted["verdict_reasons"]:
        reason = "no PLE-S configuration: " + "; ".join(admitted["verdict_reasons"])
    else:
        reason = "no PLE-S configuration restates this selection"
    return {"configuration": None, "element_id": None, "status": None, "violated_bound": None,
            "selected_alternatives": [], "derived_asset_variants": {}, "common_assets": [], "reason": reason,
            "alternatives_realized_by_admitted_selections": sorted(admitted["alternatives_realized"]),
            "summary": reason}


def _differences(admitted: dict[str, Any], index: ScopeIndex) -> list[dict[str, Any]]:
    """Whether each confirmed representation difference of the receipt manifests in this row."""
    result = []
    assets = {item["asset"]: item for item in admitted["common_assets"]}
    for item in index.differences:
        asset = assets.get(item["common_asset"])
        binds_variation = index.binds(admitted["implied_alternative"], item["variation"])
        manifests = bool(admitted["admitted"] and binds_variation and asset is not None and asset["complete"] is False)
        result.append({
            "common_asset": item["common_asset"], "variation": item["variation"],
            "implied_alternative_binds_variation": binds_variation,
            "representable_by": asset["representable_by"] if asset else [],
            "represented_by": asset["represented_by"] if asset else [],
            "missing": asset["missing"] if asset else [],
            "manifests": manifests,
        })
    return result


def classify_row(tool: dict[str, Any], admitted: dict[str, Any], ple_s: dict[str, Any],
                 encoding: dict[str, Any], comparison: dict[str, Any], index: ScopeIndex) -> tuple[str, str]:
    """The UG-14 difference class of one row, with the reason."""
    ple_s_valid = ple_s.get("status") == "configuration-valid"
    if not encoding.get("expressible", True):
        if tool["valid"]:
            return "defect", "the tool accepted a statement that has no scalar encoding in the catalogue"
        return ("not-expressible-under-tool",
                "an alternative group takes one scalar; the statement needs more than one variant per variation "
                f"and the tool rejected the list encoding (exit {tool['exit_code']}); "
                f"PLE-S: {ple_s['summary']}")
    if tool["exit_code"] not in (0, 1):
        return "defect", f"the configurator reported an input error: {tool['summary']}"
    if admitted["unclassified"]:
        return "defect", "unclassified selections: " + "; ".join(admitted["unclassified"])
    if tool["valid"] and admitted["admitted"]:
        if not ple_s_valid:
            return "defect", f"admitted and tool-valid, but PLE-S says {ple_s['summary']}"
        if comparison["differing"]:
            return "defect", "the projection and the PLE-S derivation differ on " + ", ".join(comparison["differing"])
        manifesting = [item for item in comparison["representation_differences"] if item["manifests"]]
        if manifesting:
            dispositions = {item["common_asset"]: item["disposition"] for item in index.differences}
            return ("intentional-representation",
                    "equal on " + ", ".join(comparison["equal_on"]) + "; " + "; ".join(
                        f"{item['common_asset']} is common in the governed scope but not represented "
                        f"({item['variation']} is bound per alternative): {dispositions[item['common_asset']]}"
                        for item in manifesting))
        return "equal", "the projection selects exactly the PLE-S derived variants and common realization"
    if tool["valid"] and not admitted["admitted"]:
        if ple_s_valid:
            return "defect", "PLE-S holds a valid configuration for a selection the governed scope does not admit"
        return "intentional-scope", f"tool-valid; {admitted['summary']}"
    if not tool["valid"] and admitted["admitted"]:
        return "defect", f"the operational authority rejects an admitted member: {tool['summary']}"
    if ple_s_valid:
        return "defect", "PLE-S holds a valid configuration for a selection the tool rejects and the scope does not admit"
    return "both-reject", (f"the tool rejects and the governed scope does not admit, for independent reasons: "
                           f"tool {tool['summary']}; governed scope {admitted['summary']}; PLE-S {ple_s['summary']}")


def compare_case(case: Case, evidence: dict[str, Any], index: ScopeIndex, catalogue: Catalogue,
                 correspondence: dict[str, dict[str, Any]], representable: dict[str, list[str]],
                 workspace: Path) -> dict[str, Any]:
    root = catalogue.root
    encoding: dict[str, Any] = {"expressible": True}
    if case.configuration is not None:
        bof_path = root / CONFIGURATIONS / case.configuration
        _require(bof_path.is_file(), f"{case.case}: committed configuration missing: {case.configuration}")
        data = catalogue.load_bof(bof_path)
        operational_input = {"kind": "committed", "path": (CONFIGURATIONS / case.configuration).as_posix(),
                             "name": data.get("name"), "selections": data["selections"], "sha256": sha256_of(bof_path)}
    else:
        data, encoding = generate_probe(case, index, catalogue)
        bof_path = workspace / f"{case.case}.yaml"
        bof_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        operational_input = {"kind": "generated", "path": None, "template": (CONFIGURATIONS / MEMBER_TEMPLATE).as_posix(),
                             "name": data.get("name"), "selections": data["selections"], "sha256": sha256_of(bof_path),
                             "encoding": encoding}
    tool = run_configurator(bof_path, workspace / f"{case.case}.sysml", root)
    records = classify_selections(data["selections"], catalogue, index, correspondence)
    admitted = admission(records, index, catalogue, representable)
    ple_s = _ple_s_side(case, index, admitted)

    tool_selected = tool["projection"]["selected"] if tool["projection"] else None
    expected = index.expected_selection(index.configurations[case.ple_s]) if (
        case.ple_s is not None and ple_s.get("status") == "configuration-valid") else None
    equal_on, differing = [], []
    if tool_selected is not None and expected is not None:
        for variation in sorted(set(tool_selected) | set(expected)):
            if tool_selected.get(variation) == expected.get(variation):
                equal_on.append(f"{variation}::{expected[variation]}")
            else:
                differing.append(f"{variation}: tool {tool_selected.get(variation)}, PLE-S {expected.get(variation)}")
    comparison = {"tool_selected": tool_selected, "ple_s_expected": expected, "equal_on": equal_on,
                  "differing": differing, "representation_differences": _differences(admitted, index)}
    difference_class, reason = classify_row(tool, admitted, ple_s, encoding, comparison, index)

    if tool["projection"]:
        headers = tool["projection"]["headers"]
        provenance = {**headers, "digest_origin": "projection header"}
        _require(headers["feature_model_sha256"] == sha256_of(root / CATALOGUE)
                 and headers["bill_of_features_sha256"] == operational_input["sha256"]
                 and headers["shared_assets_sha256"] == sha256_of(root / SHARED_ASSETS),
                 f"{case.case}: projection header digests differ from the inputs")
    else:
        provenance = {
            "feature_model_sha256": sha256_of(root / CATALOGUE),
            "bill_of_features_sha256": operational_input["sha256"],
            "shared_assets_sha256": sha256_of(root / SHARED_ASSETS),
            "shared_assets_source_baseline": source_baseline(root / SHARED_ASSETS, SHARED_ASSETS),
            "digest_origin": "computed by the oracle (the tool generated no projection)",
        }
    identity = evidence["identity"]
    # The receipt identity in full is the comparison's ``ple_s`` block; each row carries the keys that
    # name the receipt and the PLE-S element it was compared with.
    provenance["ple_s_receipt"] = {
        "run_id": identity["run_id"], "executor_revision": identity["executor_revision"],
        "receipt_sha256": identity["receipt_sha256"], "configuration_element_id": ple_s.get("element_id"),
    }
    return {
        "case": case.case,
        "tag": case.tag,
        "purpose": case.purpose,
        "operational_input": operational_input,
        "configuration_valid_under_current_tool": {key: value for key, value in tool.items() if key != "projection"},
        "admitted_by_governed_scope": admitted,
        "ple_s": ple_s,
        "comparison": comparison,
        "class": difference_class,
        "class_reason": reason,
        "provenance": provenance,
    }


def run_oracle(evidence: dict[str, Any], *, root: Path = ROOT, revision: str | None = None,
               work_dir: Path | None = None, correspondence_path: Path | None = None,
               cases: tuple[Case, ...] = CASES) -> dict[str, Any]:
    """The whole comparison, as data.

    ``root`` is the tree the operational side is read from (this repository,
    or an extracted tree of a revision, in which case ``revision`` names it).
    Probes and projections live in a temporary directory under ``work_dir``.
    """
    root = root.resolve()
    if revision is None:
        executor_revision = git(root, "rev-parse", "HEAD")
        executor_source_dirty = bool(git(root, "status", "--porcelain"))
        tree_source = "git checkout"
    else:
        _require(re.fullmatch(r"[0-9a-f]{40}", revision) is not None, "the revision is a full commit id")
        executor_revision, executor_source_dirty, tree_source = revision, False, "extracted tree, revision as declared"
    index = ScopeIndex(evidence["receipt"], evidence["governed"])
    catalogue = Catalogue(root)
    correspondence_path = correspondence_path or root / CORRESPONDENCE
    correspondence = load_correspondence(correspondence_path, catalogue, index)
    representable = representable_nodes(index, catalogue, correspondence)
    rows = []
    with tempfile.TemporaryDirectory(prefix="de4sdv-ple-s-oracle-", dir=work_dir) as temporary:
        workspace = Path(temporary)
        for case in cases:
            rows.append(compare_case(case, evidence, index, catalogue, correspondence, representable, workspace))
    classes: dict[str, list[str]] = {name: [] for name in CLASSES}
    for row in rows:
        classes[row["class"]].append(row["case"])
    defects = [row["case"] for row in rows if row["class"] == "defect"]
    unclassified = [row["case"] for row in rows if row["admitted_by_governed_scope"]["unclassified"]]
    return {
        "schema": SCHEMA,
        "oracle": {
            "script": Path(__file__).resolve().relative_to(ROOT.resolve()).as_posix(),
            "script_sha256": sha256_of(Path(__file__).resolve()),
            "executor_revision": executor_revision,
            "executor_source_dirty": executor_source_dirty,
            "tree_source": tree_source,
            "configurator": CONFIGURATOR.as_posix(),
            "configurator_sha256": sha256_of(root / CONFIGURATOR),
            "catalogue": CATALOGUE.as_posix(),
            "catalogue_sha256": sha256_of(root / CATALOGUE),
            "shared_assets": SHARED_ASSETS.as_posix(),
            "shared_assets_sha256": sha256_of(root / SHARED_ASSETS),
            "correspondence": _label(correspondence_path, root),
            "correspondence_sha256": sha256_of(correspondence_path),
            "selection_authority": ("the YAML catalogue, the committed configurations and "
                                    "tools/configure_variant.py, unchanged; the oracle is a comparison only"),
        },
        "ple_s": evidence["identity"],
        "representation_differences": list(evidence["receipt"].get("known_representation_differences") or []),
        "classes": list(CLASSES),
        "rows": rows,
        "summary": {"classes": classes, "defects": defects, "unclassified": unclassified,
                    "exit_code": 1 if defects or unclassified else 0},
        "qualified": False,
        "adoption_authorized": False,
        "authority_activation_authorized": False,
    }


# -- rendering ---------------------------------------------------------------------


def _cell(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _short(digest: Any) -> str:
    return f"`{str(digest)[:12]}`" if digest else "-"


def render_markdown(comparison: dict[str, Any]) -> str:
    """The comparison as Markdown: identity, classification, derived assets, provenance."""
    identity = comparison["ple_s"]
    lines = [
        f"PLE-S receipt: `{identity['evidence']}` evidence of run `{identity['run_id']}` at executor "
        f"`{identity['executor_revision']}` (artifact `{identity['artifact']}`); receipt SHA-256 "
        f"`{identity['receipt_sha256']}`; model `{identity['model_sha256']}`; evaluator "
        f"`{identity['evaluator_sha256']}`; PLEML pin `{identity['pleml_pin']}`; library "
        f"`{identity['library_sha256']}`; serializer `{identity['serializer_version']}`; qualified: false.",
        "",
        "| Case | Operational input | Valid under current tool | Admitted by governed scope | PLE-S outcome | Difference class |",
        "|---|---|---|---|---|---|",
    ]
    for row in comparison["rows"]:
        source = row["operational_input"]
        operational = (f"`{source['path']}`" if source["kind"] == "committed"
                       else f"generated `{source['name']}` from `{source['template']}`")
        tool = row["configuration_valid_under_current_tool"]
        valid = ("yes" if tool["valid"] else "no") + f" (exit {tool['exit_code']}"
        valid += "; " + ", ".join(tool["violated_constraints"]) + ")" if tool["violated_constraints"] else ")"
        admitted = row["admitted_by_governed_scope"]
        admitted_cell = (f"yes: {admitted['implied_alternative']}" if admitted["admitted"]
                         else "no: " + "; ".join(admitted["verdict_reasons"]))
        lines.append(f"| {row['case']} | {_cell(operational)} | {_cell(valid)} | {_cell(admitted_cell)} | "
                     f"{_cell(row['ple_s']['summary'])} | {row['class']} |")
    lines += ["", "| Case | Tool projection | PLE-S derived variants and common realization | Equal on | Differing | Class reason |",
              "|---|---|---|---|---|---|"]
    for row in comparison["rows"]:
        comparison_block = row["comparison"]
        selected = comparison_block["tool_selected"]
        expected = comparison_block["ple_s_expected"]
        lines.append(
            f"| {row['case']} | {_cell(', '.join(f'{k}::{v}' for k, v in sorted(selected.items())) if selected else '-')} | "
            f"{_cell(', '.join(f'{k}::{v}' for k, v in sorted(expected.items())) if expected else '-')} | "
            f"{_cell(', '.join(comparison_block['equal_on']) or '-')} | {_cell(', '.join(comparison_block['differing']) or '-')} | "
            f"{_cell(row['class_reason'])} |")
    lines += ["", "| Case | Feature model | Bill-of-Features | Shared assets | Digest origin |", "|---|---|---|---|---|"]
    for row in comparison["rows"]:
        provenance = row["provenance"]
        lines.append(f"| {row['case']} | {_short(provenance['feature_model_sha256'])} | "
                     f"{_short(provenance['bill_of_features_sha256'])} | {_short(provenance['shared_assets_sha256'])} | "
                     f"{_cell(provenance['digest_origin'])} |")
    classes = comparison["summary"]["classes"]
    lines += ["", "Classes: " + "; ".join(f"{name}: {', '.join(classes.get(name) or []) or 'none'}"
                                          for name in comparison["classes"])
              + ". Full digests and reasons: the JSON comparison.", ""]
    return "\n".join(lines)


# -- command line --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--receipt", type=Path, required=True, help="PLE-S receipt.json of a licensed run")
    parser.add_argument("--governed-scope", type=Path, required=True,
                        help="governed-scope-validation.json of the same run")
    parser.add_argument("--evidence", choices=EVIDENCE_KINDS, required=True,
                        help="fresh: the receipt of this exact head; retained: a committed receipt of an earlier run")
    parser.add_argument("--run-id", required=True, help="the workflow run id that produced the receipt")
    parser.add_argument("--artifact", required=True, help="the artifact name of that run")
    parser.add_argument("--correspondence", type=Path, default=None,
                        help=f"catalogue correspondence (default: {CORRESPONDENCE.as_posix()} of the tree)")
    parser.add_argument("--root", type=Path, default=None,
                        help="the tree to compare (default: this repository); an extracted tree needs --revision")
    parser.add_argument("--revision", default=None,
                        help="the full commit id of an extracted --root tree (recorded, not verified)")
    parser.add_argument("--out", type=Path, required=True,
                        help="output directory; must not exist and must be outside the repository and the tree")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = (args.root or ROOT).resolve()
    _require((root / CONFIGURATOR).is_file() and (root / CATALOGUE).is_file(), f"{root} is not a DE4SDV tree")
    if args.revision is not None:
        _require(re.fullmatch(r"[0-9a-f]{40}", args.revision) is not None, "--revision is a full commit id")
    elif args.root is not None:
        _require(subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                                check=False).returncode == 0, "an extracted --root tree needs --revision")
    out: Path = args.out
    if out.exists():
        raise OracleRefusal("refusing to overwrite an existing output directory")
    for forbidden in (ROOT.resolve(), root):
        if out.resolve().is_relative_to(forbidden):
            raise OracleRefusal("output must be outside the repository and the compared tree")
    evidence = load_evidence(args.receipt, args.governed_scope, evidence=args.evidence, run_id=args.run_id,
                             artifact=args.artifact, root=root)
    out.parent.mkdir(parents=True, exist_ok=True)
    comparison = run_oracle(evidence, root=root, revision=args.revision, work_dir=out.parent,
                            correspondence_path=args.correspondence)
    out.mkdir()
    (out / "comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "comparison.md").write_text(render_markdown(comparison), encoding="utf-8")
    return comparison


def main() -> int:
    args = build_parser().parse_args()
    try:
        comparison = run(args)
    except (OracleRefusal, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    summary = comparison["summary"]
    print(json.dumps({
        "comparison": str(args.out / "comparison.json"), "evidence": comparison["ple_s"]["evidence"],
        "tree": comparison["oracle"]["tree_source"], "revision": comparison["oracle"]["executor_revision"],
        "rows": len(comparison["rows"]), "classes": {name: len(cases) for name, cases in summary["classes"].items()},
        "defects": summary["defects"], "unclassified": summary["unclassified"], "qualified": False,
    }))
    return summary["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
