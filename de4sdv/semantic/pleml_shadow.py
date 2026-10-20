"""The YAML shadow of the PLEML evaluation, until the catalogue retires at S7 (ADR 0022).

The YAML catalogue stays the reviewed source of three checks a receipt records:
each feature's catalogue path (by short name), the allowed-list complement check
and the row-by-row rule-table comparison. The catalogue is read with the
configurator's own parser, never re-implemented. Nothing here is an authority.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

from de4sdv.semantic import pleml_receipts as receipts

ROOT = Path(__file__).resolve().parents[2]
CONFIGURATOR = Path("tools/configure_variant.py")

# -- the YAML shadow (until S7) --------------------------------------------------------------


def load_configurator(root: Path = ROOT):
    """The configurator of the tree, imported for its own catalogue parser (never re-implemented)."""
    path = (root / CONFIGURATOR).resolve()
    name = f"_de4sdv_pleml_shadow_configurator_{abs(hash(str(path)))}"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import the configurator at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Catalogue:
    """The YAML catalogue read with the configurator's functions."""

    def __init__(self, path: Path, root: Path = ROOT) -> None:
        self.path = path
        self.module = module = load_configurator(root)
        with path.open(encoding="utf-8") as handle:
            self.data = module.load_yaml_unique(handle)
        self.root, self.constraints = module.build_feature_tree(self.data)
        self.nodes = module.collect_all_nodes(self.root)
        self.by_id = {node.feature_id: node for node in module.iter_feature_nodes(self.root) if node.feature_id}

    def child(self, group_path: str, name: str):
        group = self.nodes.get(group_path)
        matches = [child for child in (group.children if group else []) if child.name == name]
        return matches[0] if len(matches) == 1 else None

    def paths(self) -> dict[str, str]:
        return {identifier: node.path for identifier, node in self.by_id.items() if node.path}

    def allowed_lists(self) -> list[dict[str, Any]]:
        """``requires`` constraints of the form ``G == V`` then ``P in [..]``: allowed lists by node id."""
        lists = []
        for constraint in self.constraints:
            condition = re.fullmatch(r"\s*([\w.]+)\s*==\s*(\w+)\s*", constraint.get("if", ""))
            target = re.fullmatch(r"\s*([\w.]+)\s+in\s+\[([^\]]*)\]\s*", constraint.get("then", ""))
            if constraint.get("type") != "requires" or not condition or not target:
                continue
            owner = self.child(condition.group(1), condition.group(2))
            group = self.nodes.get(target.group(1))
            allowed = [self.child(target.group(1), name.strip()) for name in target.group(2).split(",")]
            if owner is None or group is None or None in allowed:
                raise ValueError(f"allowed list {constraint.get('id')} names unknown catalogue nodes")
            lists.append({"id": constraint["id"], "owner": owner.feature_id, "group": group.feature_id,
                          "allowed": sorted(node.feature_id for node in allowed)})
        return lists


def _features_by_short_name(feature_model: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {feature["short_name"]: feature for feature in feature_model["features"] if feature["short_name"]}


def complement_errors(feature_model: Mapping[str, Any], allowed_lists: Iterable[Mapping[str, Any]]) -> list[str]:
    """Each allowed list's exclusions equal its complement over the model's current options (R9)."""
    features = _features_by_short_name(feature_model)
    by_path = {feature["path"]: feature for feature in feature_model["features"]}
    errors = []
    for item in allowed_lists:
        owner, group = features.get(item["owner"]), features.get(item["group"])
        if owner is None or group is None:
            errors.append(f"{item['id']}: the model has no feature {item['owner'] if owner is None else item['group']}")
            continue
        options = {by_path[path]["short_name"] or path for path in group["members"]}
        missing = sorted(set(item["allowed"]) - options)
        if missing:
            errors.append(f"{item['id']}: the allowed options {missing} are no members of {group['path']}")
        complement = sorted(options - set(item["allowed"]))
        excluded = sorted({by_path[path]["short_name"] or path
                           for constraint in feature_model["constraints"]
                           if constraint["kind"] == "xor" and constraint["short_name"] == item["id"]
                           and constraint["owner"] == owner["path"] for path in constraint["operand_b"]})
        stray = [constraint["owner"] for constraint in feature_model["constraints"]
                 if constraint["short_name"] == item["id"] and (constraint["kind"] != "xor"
                                                                or constraint["owner"] != owner["path"])]
        if excluded != complement or stray:
            errors.append(f"{item['id']}: the exclusions of {owner['path']} are {excluded}, the complement of the "
                          f"allowed list {item['allowed']} is {complement}" + (f"; stray {stray}" if stray else ""))
    return errors


def rule_table_errors(feature_model: Mapping[str, Any], catalogue: Catalogue) -> list[str]:
    """The model's derivation rules equal the catalogue's rule table row by row (R10, until S7)."""
    features = {feature["path"]: feature for feature in feature_model["features"]}
    derivations = {item["short_name"]: item for item in feature_model["derivations"]}
    errors = []
    declarations = catalogue.data.get("derived_asset_selections") or []
    for declaration in declarations:
        identifier = declaration.get("id")
        derivation = derivations.get(identifier)
        if derivation is None:
            errors.append(f"{identifier}: the model has no rule set with this short name")
            continue
        if derivation["derived_variation"] != str(declaration.get("maps_to", "")).rsplit(".", 1)[-1]:
            errors.append(f"{identifier}: the rule set derives {derivation['derived_variation']}")
        sources = sorted(catalogue.nodes[path].feature_id for path in declaration.get("source_selections") or [])
        model_sources = sorted(features[path]["short_name"] or path for path in derivation["source_groups"])
        if sources != model_sources:
            errors.append(f"{identifier}: source groups {model_sources}, the catalogue has {sources}")
        expected = {}
        for rule in declaration.get("rules") or []:
            premises = frozenset(catalogue.child(path, value).feature_id for path, value in rule["when"].items())
            expected[premises] = rule["maps_to_variant"]
        actual = {frozenset(features[path]["short_name"] or path for path in rule["premises"]): rule["result"]
                  for rule in derivation["rules"]}
        for premises in sorted(set(expected) | set(actual), key=sorted):
            if expected.get(premises) != actual.get(premises):
                errors.append(f"{identifier}: rule {sorted(premises)} yields {actual.get(premises)} in the model "
                              f"and {expected.get(premises)} in the catalogue")
    extra = sorted(set(derivations) - {item.get("id") for item in declarations})
    if extra:
        errors.append(f"rule sets without a catalogue declaration: {extra}")
    return errors


def shadow_checks(report: Mapping[str, Any], catalogue_path: Path | None, root: Path = ROOT) -> dict[str, Any]:
    """The shadow section of a receipt: catalogue paths and the two static comparisons."""
    if catalogue_path is None:
        return {}
    catalogue = Catalogue(root / catalogue_path, root)
    lists = catalogue.allowed_lists()
    shadow: dict[str, Any] = {"catalogue": {"path": catalogue_path.as_posix(),
                                            "sha256": receipts.sha256((root / catalogue_path).read_bytes())},
                              "allowed_lists": lists, "feature_models": []}
    paths = catalogue.paths()
    for model in report["feature_models"]:
        shadow["feature_models"].append({
            "tree": model["tree"]["name"],
            "writer_inputs": {item["configuration"]: receipts.writer_inputs(item, model["features"], paths)
                              for item in model["configurations"]},
            "complement_errors": complement_errors(model, lists),
            "rule_table_errors": rule_table_errors(model, catalogue),
        })
    return shadow


def catalogue_for(model_document: str, root: Path = ROOT) -> Path | None:
    """The YAML catalogue a feature model restates until S7: the same path, with the ``.yaml`` suffix."""
    candidate = Path(model_document).with_suffix(".yaml")
    return candidate if (root / candidate).is_file() else None


def shadow_failures(receipt: Mapping[str, Any]) -> list[str]:
    """The integrity errors of a receipt's evaluation and the errors of its shadow checks."""
    failures = []
    for model in receipt["evaluation"]["feature_models"]:
        failures += [f"{model['tree']['name']}: {error}" for error in model["integrity_errors"]]
    for model in (receipt.get("shadow") or {}).get("feature_models", []):
        failures += [f"{model['tree']}: {error}" for error in model["complement_errors"] + model["rule_table_errors"]]
    return failures


def receipt_shadow(receipt_path: Path, root: Path = ROOT) -> dict[str, Any] | None:
    """The shadow checks of a receipt's recorded evaluation, recomputed against the catalogue of ``root``."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    catalogue = (receipt.get("shadow") or {}).get("catalogue")
    if not catalogue:
        return None
    if receipts.sha256((root / catalogue["path"]).read_bytes()) != catalogue["sha256"]:
        raise receipts.StaleReceipt(f"{catalogue['path']} changed after the receipt; refresh it")
    return shadow_checks(receipt["evaluation"], Path(catalogue["path"]), root)
