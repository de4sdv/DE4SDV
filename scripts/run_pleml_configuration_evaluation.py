#!/usr/bin/env python3
"""Evaluate fenced PLEML feature models and keep their receipts (ADR 0022, plan step S2).

Commands:

* ``receipts``: the entry point of the licensed authority job. It takes the
  job's export bundle (serialized with the production export's options, the
  PLEML library labelled with the fenced package's ``LIBRARY_PATH``), writes
  ``<name>.elements.json.xz`` and one ``<feature-model file stem>.receipt.json``
  per feature model to ``--out``, and exits 1 on an integrity, complement or
  rule-table failure. ``--compare`` refuses when the fresh elements differ
  from the committed receipts' (they are stale or are not the serializer's
  output). :func:`write_receipts` is the same entry point as a function.
* ``replay``: unlicensed. Re-run the evaluator on the committed elements of
  each receipt; exit 1 when a receipt is stale by digest or does not
  reproduce, including its shadow checks.
* ``refresh``: unlicensed. Rewrite a receipt from its committed elements when
  only the evaluator changed.

Until S7 the YAML catalogue with the feature model's file stem is the reviewed
source of three shadow checks the receipt records: each feature's catalogue
path (by short name), the allowed-list complement check and the row-by-row
rule-table comparison. The configurator's rejection messages are classified
here for the parity check. Nothing here qualifies anything or executes a PLEML
expression natively.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_configuration as evaluator  # noqa: E402
from de4sdv.semantic import pleml_receipts as receipts  # noqa: E402
from de4sdv.sysml_api.baseline import BaselineExportBundle  # noqa: E402

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


# -- the configurator's rejections, as parity reason keys -------------------------------------

_YAML_CLASSES: tuple[tuple[str, str], ...] = (
    (r"^'(?P<path>[^']+)': '\[.*\]' is not a valid XOR choice", "upper-bound"),
    (r"^'(?P<path>[^']+)': '.*' is not a valid XOR choice", "unknown-feature"),
    (r"^Mandatory \w+ group '(?P<path>[^']+)' has no selection$", "lower-bound"),
    (r"^'(?P<path>[^']+)' is an or_group and requires a non-empty list$", "lower-bound"),
    (r"^'(?P<path>[^']+)' (OR choices must all be strings|has invalid OR choice)", "unknown-feature"),
    (r"^'(?P<path>[^']+)' is a \w+ group node with non-variant children", "unknown-feature"),
    (r"^'(?P<path>[^']+)' (contains duplicate OR choices|must be a YAML boolean)", "input-error"),
    (r"^Unknown feature path in selections: '(?P<path>[^']+)'$", "unknown-feature"),
    (r"^Mandatory feature not selected: '(?P<path>[^']+)'$", "lower-bound"),
    (r"^\[(?P<id>[^\]]+)\] (requires|excludes): ", "constraint"),
    (r"^\[[^\]]+\] (unknown constraint type|invalid constraint expression|constraint expression references)",
     "model-integrity"),
    (r"^Derived asset '(?P<id>[^']+)' for '[^']+' has no rule matching ", "pair-exclusion"),
    (r"^Derived asset '[^']+' for '[^']+' has \d+ matching rules", "derivation-ambiguous"),
    (r"(^|\b)(evidence[ .]|Bill-of-Features 'evidence'|unknown evidence field|duplicate evidence artifact|"
     r"\w+ configuration requires retained evidence)", "evidence-record"),
    (r"^Bill-of-Features '(name|description)' must be", "configuration-metadata"),
    (r"^(Feature/catalogue node|Duplicate |Non-selection node|Mapped variation|Unmapped variation|Selection group|"
     r"Node '.*' has orphan|Mapped variant|derived_asset_selections\[|Derived asset target|Mapped SysML|"
     r"Derived SysML|SysML package|SysML part def|Cannot read shared-assets|Shared-assets model)", "model-integrity"),
    (r"^(feature model|Bill-of-Features|feature node|unknown projection field|projection\.|constraint\[|"
     r"Error reading input|Error parsing YAML)", "input-error"),
)


def yaml_reason_keys(messages: Sequence[str], selections: Mapping[str, Any],
                     catalogue: Catalogue) -> tuple[set[tuple[str, str | None]], int]:
    """(reason keys, counted violations) of one configurator run, comparable with ``reason_keys``.

    A ``no rule matching`` whose source selection is not one valid choice is
    a consequence of a structural error and is dropped, as the evaluator
    derives nothing for an invalid configuration. An unknown path naming a
    derived asset is a hand-picked derived variant; a mandatory common
    capability (``C-``) set to false is the pinned not-expressible construct.
    """
    derived_targets = {str(item.get("maps_to", "")).rsplit(".", 1)[-1].lower(): item
                       for item in catalogue.data.get("derived_asset_selections") or []}
    keys: set[tuple[str, str | None]] = set()
    counted = 0
    for message in messages:
        for pattern, reason in _YAML_CLASSES:
            match = re.search(pattern, message)
            if not match:
                continue
            groups = match.groupdict()
            if reason == "constraint":
                keys.add((reason, groups["id"]))
            elif reason == "pair-exclusion":
                declaration = next((item for item in derived_targets.values() if item.get("id") == groups["id"]), {})
                sources = declaration.get("source_selections") or []
                if all(isinstance(selections.get(path), str) and catalogue.child(path, selections[path])
                       for path in sources):
                    keys.add((reason, None))
                else:
                    break  # consequential: the structural error is already counted
            elif reason == "unknown-feature" and groups.get("path", "").rsplit(".", 1)[-1].lower() in derived_targets:
                keys.add(("derived-variant-not-selectable", None))
            elif reason == "lower-bound" and message.startswith("Mandatory feature not selected"):
                node = catalogue.nodes.get(groups["path"])
                keys.add(("common-capability-false" if node and str(node.feature_id).startswith("C-")
                          else "lower-bound", None))
            else:
                keys.add((reason, None))
            counted += 1
            break
        else:
            raise ValueError(f"unclassified configurator message: {message}")
    return keys, counted


# -- the entry point of the licensed authority job ----------------------------------------------


def catalogue_for(model_document: str, root: Path = ROOT) -> Path | None:
    """The YAML catalogue a feature model restates until S7: the same path, with the ``.yaml`` suffix."""
    candidate = Path(model_document).with_suffix(".yaml")
    return candidate if (root / candidate).is_file() else None


def write_receipts(bundle: BaselineExportBundle | Mapping[str, Any], out: Path, *, serializer: Mapping[str, Any],
                   name: str = "pleml-feature-models", model_sources: Iterable[str] | None = None,
                   root: Path = ROOT) -> dict[str, Any]:
    """Write the elements file and one receipt per feature model of a licensed bundle into ``out``.

    ``serializer`` records the serialization: its name, version and options,
    which the elements carry, and the executor revision, which only the
    receipts record (with the bundle's commit) as the run's provenance. ``out``
    must not exist. Returns the written paths and the failures (integrity,
    complement and rule-table errors), which a licensed job must treat as a
    failed run. A bundle without the governed scope is refused: every receipt
    records the admission of its configurations.
    """
    if not isinstance(bundle, BaselineExportBundle):
        bundle = BaselineExportBundle.from_dict(dict(bundle))
    payload = receipts.payload_from_bundle(bundle, serializer=serializer, model_sources=model_sources)
    provenance = receipts.run_provenance(bundle, serializer)
    combined = receipts.evaluate_payload(payload)
    if combined["admission_authority"] is None:
        raise ValueError("the bundle carries no governed scope; every receipt records the admission of its "
                         "configurations")
    groups: dict[str, set[str]] = {}
    for model in combined["feature_models"]:
        document = model["tree"]["source"]
        groups.setdefault(document, {document}).update(item["source"] for item in model["configurations"])
    owners: dict[str, list[str]] = {}
    for document, members in groups.items():
        for member in members:
            owners.setdefault(member, []).append(document)
    shared = sorted(member for member, documents in owners.items() if len(documents) > 1)
    unused = sorted(set(payload["model_sources"]) - set(owners))
    if shared or unused:
        raise ValueError(f"each model document belongs to one feature model; shared: {shared}, in none: {unused}")
    out.mkdir(parents=True)
    elements_file = f"{name}.elements.json.xz"
    digest = receipts.write_elements(out / elements_file, payload)
    written, failures = [], []
    for document in sorted(groups):
        receipt = receipts.build_receipt(payload, elements_file=elements_file, elements_sha256=digest,
                                         model_sources=sorted(groups[document]), provenance=provenance)
        expected = [item for item in combined["feature_models"] if item["tree"]["source"] == document]
        if receipts.canonical(receipt["evaluation"]["feature_models"]) != receipts.canonical(expected):
            raise ValueError(f"the feature model of {document} does not evaluate alone; it needs other documents")
        receipt["shadow"] = shadow_checks(receipt["evaluation"], catalogue_for(document, root), root)
        path = out / f"{Path(document).stem}.receipt.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
        failures += _shadow_failures(receipt)
    return {"elements": out / elements_file, "receipts": written, "failures": failures}


def run_receipts(args: argparse.Namespace) -> int:
    out: Path = args.out
    if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("--out must be a new directory outside the repository")
    serializer = {"name": "syside", "version": args.serializer_version, "options": "production export",
                  "executor_revision": args.executor_revision}
    result = write_receipts(BaselineExportBundle.load(args.bundle), out, serializer=serializer, name=args.name)
    failures = list(result["failures"])
    if args.compare is not None:
        failures += receipts.compare_with_committed(result["receipts"], args.compare)
    print(json.dumps({"elements": str(result["elements"]), "receipts": [str(path) for path in result["receipts"]],
                      "failures": failures}, indent=2))
    return 1 if failures else 0


def _shadow_failures(receipt: Mapping[str, Any]) -> list[str]:
    failures = []
    for model in receipt["evaluation"]["feature_models"]:
        failures += [f"{model['tree']['name']}: {error}" for error in model["integrity_errors"]]
    for model in (receipt.get("shadow") or {}).get("feature_models", []):
        failures += [f"{model['tree']}: {error}" for error in model["complement_errors"] + model["rule_table_errors"]]
    return failures


def _receipt_shadow(receipt_path: Path) -> dict[str, Any] | None:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    catalogue = (receipt.get("shadow") or {}).get("catalogue")
    if not catalogue:
        return None
    if receipts.sha256((ROOT / catalogue["path"]).read_bytes()) != catalogue["sha256"]:
        raise receipts.StaleReceipt(f"{catalogue['path']} changed after the receipt; refresh it")
    return shadow_checks(receipt["evaluation"], Path(catalogue["path"]), ROOT)


def run_replay(args: argparse.Namespace) -> int:
    failures = []
    for path in args.receipt:
        try:
            receipt = receipts.replay(path, ROOT, shadow=_receipt_shadow(path))
            failures += [f"{path}: {failure}" for failure in _shadow_failures(receipt)]
        except (receipts.StaleReceipt, evaluator.PlemlShapeError) as exc:
            failures.append(f"{path}: {exc}")
    print(json.dumps({"receipts": [str(path) for path in args.receipt], "failures": failures}, indent=2))
    return 1 if failures else 0


def run_refresh(args: argparse.Namespace) -> int:
    """Refresh every receipt before writing any of them, so a refusal leaves all of them as they were."""
    fresh = []
    for path in args.receipt:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        catalogue = (receipt.get("shadow") or {}).get("catalogue")
        payload = receipts.read_elements(path.parent / receipt["elements"]["path"])
        evaluation = receipts.evaluate_payload(payload, model_sources=receipt.get("model_sources"))
        shadow = shadow_checks(evaluation, Path(catalogue["path"]), ROOT) if catalogue else {}
        fresh.append((path, receipts.refreshed(path, ROOT, shadow=shadow)))
    for path, receipt in fresh:
        receipts.write_receipt(path, receipt)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("receipts", help="write the receipts of a licensed authority bundle")
    command.add_argument("--bundle", type=Path, required=True, help="the export bundle of the licensed job (JSON)")
    command.add_argument("--serializer-version", required=True, help="the serializer version of the bundle")
    command.add_argument("--executor-revision", required=True, help="the exact executor revision of the job")
    command.add_argument("--name", default="pleml-feature-models", help="file stem of the elements file")
    command.add_argument("--compare", type=Path, help="a directory of committed receipts the fresh elements must equal")
    command.add_argument("--out", type=Path, required=True, help="new output directory outside the repository")
    for name, help_text in (("replay", "re-run the evaluator on committed elements (unlicensed)"),
                            ("refresh", "rewrite receipts from their committed elements (unlicensed)")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("receipt", type=Path, nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return {"receipts": run_receipts, "replay": run_replay, "refresh": run_refresh}[args.command](args)
    except (ValueError, OSError, ImportError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
