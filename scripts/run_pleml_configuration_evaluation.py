#!/usr/bin/env python3
"""Evaluate fenced PLEML feature models and keep their receipts (ADR 0022, plan step S2).

Commands:

* ``licensed``: on the x86_64 runner with the pinned serializer, load the
  reviewed roots, the pinned PLEML library and the fenced model files, keep
  the documents the models reference, evaluate them, and write
  ``<name>.elements.json.xz`` and ``<name>.receipt.json`` to ``--out``.
  ``--compare`` refuses when the fresh elements differ from a committed
  receipt's (its elements are stale or are not the serializer's output).
* ``replay``: unlicensed. Re-run the evaluator on the committed elements of
  each receipt; exit 1 when a receipt is stale by digest or does not
  reproduce, including its shadow checks.
* ``refresh``: unlicensed. Rewrite a receipt from its committed elements when
  only the evaluator changed.

Until S7 the YAML catalogue is the reviewed source of three shadow checks the
receipt records: each feature's catalogue path (by short name), the
allowed-list complement check and the row-by-row rule-table comparison. The
configurator's rejection messages are classified here for the parity check.
Nothing here qualifies anything or executes a PLEML expression natively.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import importlib.util
import json
import platform
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_configuration as evaluator  # noqa: E402
from de4sdv.semantic import pleml_receipts as receipts  # noqa: E402
from de4sdv.sysml_api.baseline import BaselineManifest, build_export_bundle  # noqa: E402

SERIALIZER_VERSION = "0.10.3"
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
    (r"^'(?P<path>[^']+)' (contains duplicate OR choices|must be a YAML boolean)", "yaml-encoding"),
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


# -- licensed serialization --------------------------------------------------------------------


def _label(url: object, library: Path, library_label: str, root: Path) -> str:
    parsed = urlparse(str(url))
    candidate = Path(unquote(parsed.path if parsed.scheme == "file" else str(url))).resolve()
    if candidate == library.resolve():
        return library_label
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"the serializer produced a document outside the reviewed sources: {url}") from exc


def serialize(models: Sequence[Path], library: Path, library_label: str,
              root: Path = ROOT) -> tuple[dict[str, list[dict[str, Any]]], str]:
    """Every loaded document, minimally serialized and labelled by its source."""
    if platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("licensed Syside requires the supported x86_64 runner; not executed on this host")
    syside = importlib.import_module("syside")
    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError(f"the installed serializer {version} differs from the reviewed {SERIALIZER_VERSION}")
    manifest = BaselineManifest.discover(root)
    paths = [root / source.path for source in manifest.sources] + [library] + [root / model for model in models]
    model, diagnostics = syside.try_load_model(paths)
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError(f"the serializer rejected the reviewed roots with the library and the models: {diagnostics}")
    documents: dict[str, list[dict[str, Any]]] = {}
    for document in model.user_docs:
        with document.lock() as locked:
            label = _label(locked.url, library, library_label, root)
            values = json.loads(syside.json.dumps(locked.root_node, syside.SerializationOptions.minimal()))
        if label in documents or not isinstance(values, list):
            raise ValueError(f"the serializer repeated or malformed the document {label}")
        documents[label] = values
    return documents, version


def evaluation_documents(documents: Mapping[str, list[dict[str, Any]]], models: Sequence[str],
                         library: str) -> list[str]:
    """The model documents, the library and every document a model element references (the kernel among them)."""
    where = {element["@id"]: label for label, values in documents.items() for element in values}
    chosen = set(models) | {library}

    def referenced(value: Any) -> Iterable[str]:
        if isinstance(value, dict):
            if "@id" in value and "@type" not in value:
                yield str(value["@id"])
            else:
                for item in value.values():
                    yield from referenced(item)
        elif isinstance(value, list):
            for item in value:
                yield from referenced(item)

    for label in models:
        for element in documents[label]:
            for key, value in element.items():
                if key != "@id":
                    chosen.update(where[target] for target in referenced(value) if target in where)
    missing = sorted(chosen - set(documents))
    if missing:
        raise ValueError(f"documents absent from the serialization: {missing}")
    return sorted(chosen)


def payload_from_documents(documents: Mapping[str, list[dict[str, Any]]], chosen: Sequence[str],
                           models: Sequence[str], library_label: str, library: Path, root: Path,
                           version: str) -> dict[str, Any]:
    bundle = build_export_bundle(git_commit="", source_documents={label: documents[label] for label in chosen})
    manifest = []
    for label in chosen:
        data = (library if label == library_label else root / label).read_bytes()
        manifest.append({"path": label, "sha256": receipts.sha256(data), "size": len(data)})
    external = [{key: record[key] for key in ("source_element_id", "property_path", "target_id")}
                for record in bundle.external_references]
    return receipts.elements_payload(
        elements=list(bundle.elements.values()), element_sources=bundle.element_sources, model_sources=models,
        library_source=library_label, kernel_source=evaluator.KERNEL_SOURCE, source_manifest=manifest,
        serializer={"name": "syside", "version": version, "options": "minimal"}, external_references=external)


# -- commands ----------------------------------------------------------------------------------


def run_licensed(args: argparse.Namespace) -> int:
    from scripts.run_ple_qualification import git

    out: Path = args.out
    if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("--out must be a new directory outside the repository")
    executor = git(ROOT, "rev-parse", "HEAD")
    if args.expected_executor != executor or git(ROOT, "status", "--porcelain"):
        raise ValueError("licensed mode requires the exact, clean executor revision")
    library = (ROOT / args.library) if not args.library.is_absolute() else args.library
    models = [model.as_posix() for model in args.model]
    documents, version = serialize(args.model, library, args.library_label)
    chosen = evaluation_documents(documents, models, args.library_label)
    payload = payload_from_documents(documents, chosen, models, args.library_label, library, ROOT, version)
    out.mkdir(parents=True)
    elements_file = f"{args.name}.elements.json.xz"
    digest = receipts.write_elements(out / elements_file, payload)
    report = receipts.evaluate_payload(payload)
    receipt = receipts.build_receipt(payload, elements_file=elements_file, elements_sha256=digest,
                                     shadow=shadow_checks(report, args.catalogue))
    receipt["serializer"] = {**receipt["serializer"], "executor_revision": executor}
    (out / f"{args.name}.receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                                                  encoding="utf-8")
    failures = _shadow_failures(receipt)
    if args.compare is not None:
        committed = json.loads(args.compare.read_text(encoding="utf-8"))
        if committed["elements"]["content_sha256"] != receipt["elements"]["content_sha256"]:
            failures.append("the fresh elements differ from the committed receipt's elements")
    print(json.dumps({"receipt": str(out / f"{args.name}.receipt.json"), "failures": failures}))
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
    return shadow_checks(receipt["evaluation"], Path(catalogue["path"]))


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
    for path in args.receipt:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        catalogue = (receipt.get("shadow") or {}).get("catalogue")
        payload = receipts.read_elements(path.parent / receipt["elements"]["path"])
        shadow = shadow_checks(receipts.evaluate_payload(payload), Path(catalogue["path"])) if catalogue else {}
        receipts.refresh(path, ROOT, shadow=shadow)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    licensed = commands.add_parser("licensed", help="serialize and evaluate on the licensed x86_64 runner")
    licensed.add_argument("--model", type=Path, action="append", required=True,
                          help="a fenced PLEML model file, repository-relative (repeatable)")
    licensed.add_argument("--name", required=True, help="file stem of the receipt and its elements")
    licensed.add_argument("--library", type=Path, default=Path(evaluator.LIBRARY_SOURCE),
                          help="the pinned PLEML library file")
    licensed.add_argument("--library-label", default=evaluator.LIBRARY_SOURCE,
                          help="the source label the library is recorded under")
    licensed.add_argument("--catalogue", type=Path, help="the YAML catalogue of the shadow checks (until S7)")
    licensed.add_argument("--expected-executor", required=True, help="exact 40-character executor revision")
    licensed.add_argument("--compare", type=Path, help="a committed receipt the fresh elements must equal")
    licensed.add_argument("--out", type=Path, required=True, help="new output directory outside the repository")
    for name, help_text in (("replay", "re-run the evaluator on committed elements (unlicensed)"),
                            ("refresh", "rewrite receipts from their committed elements (unlicensed)")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("receipt", type=Path, nargs="+")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return {"licensed": run_licensed, "replay": run_replay, "refresh": run_refresh}[args.command](args)
    except (ValueError, OSError, ImportError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
