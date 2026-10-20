#!/usr/bin/env python3
"""Evaluate the PLEML feature models and keep their receipts (ADR 0022, plan step S2).

Commands:

* ``receipts``: the entry point of the licensed authority job. It takes the
  job's export bundle (serialized with the production export's options, the
  PLEML library labelled with the pinned package's ``LIBRARY_PATH``), writes
  ``<name>.elements.json.xz`` and one ``<feature-model file stem>.receipt.json``
  per feature model to ``--out``, and exits 1 on an integrity, complement or
  rule-table failure. ``--compare`` refuses when the fresh elements differ
  from the committed receipts' (they are stale or are not the serializer's
  output). :func:`write_receipts` is the same entry point as a function.
* ``replay``: unlicensed. Re-run the evaluator on the committed elements of
  each receipt; exit 1 when its inputs changed or its evaluation or shadow
  does not reproduce byte for byte. Code that differs from the code that
  evaluated a receipt is reported as an advisory. ``replay_receipts`` and
  ``replay_committed`` of ``pleml_receipts`` are the same check as functions.
* ``refresh``: unlicensed. Rewrite receipts from their intact committed
  elements when the evaluation no longer reproduces. It lists every change of
  a verdict, a derived variant or an admission, and writes nothing when there
  is one, unless ``--accept-verdict-changes``.

Until S7 the YAML catalogue with the feature model's file stem is the reviewed
source of three shadow checks the receipt records: each feature's catalogue
path (by short name), the allowed-list complement check and the row-by-row
rule-table comparison. The configurator's rejection messages are classified
here for the parity check. Nothing here qualifies anything or executes a PLEML
expression natively.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_receipts as receipts  # noqa: E402
from de4sdv.semantic.pleml_shadow import (  # noqa: E402,F401  (the shadow's names, for the CLI and its tests)
    CONFIGURATOR, Catalogue, catalogue_for, complement_errors, load_configurator, receipt_shadow, rule_table_errors,
    shadow_checks, shadow_failures)
from de4sdv.sysml_api.baseline import BaselineExportBundle  # noqa: E402

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


def yaml_reasons(messages: Sequence[str], selections: Mapping[str, Any],
                 catalogue: Catalogue) -> list[dict[str, Any]]:
    """Each counted rejection of one configurator run: its parity class, constraint ID and location.

    The location is what the message names: the catalogue path of a group or
    feature, the choices of a pair without a rule, or the derived variation
    of a hand-picked variant, in lower case. A constraint is located by its ID.
    A ``no rule matching`` whose source selection is not one valid choice is
    a consequence of a structural error and is dropped, as the evaluator
    derives nothing for an invalid configuration. An unknown path naming a
    derived asset is a hand-picked derived variant; a mandatory common
    capability (``C-``) set to false is the pinned not-expressible construct.
    """
    derived_targets = {str(item.get("maps_to", "")).rsplit(".", 1)[-1].lower(): item
                       for item in catalogue.data.get("derived_asset_selections") or []}
    found: list[dict[str, Any]] = []
    for message in messages:
        for pattern, reason in _YAML_CLASSES:
            match = re.search(pattern, message)
            if not match:
                continue
            groups = match.groupdict()
            path = groups.get("path")
            if reason == "constraint":
                found.append({"class": reason, "constraint": groups["id"], "location": None})
            elif reason == "pair-exclusion":
                declaration = next((item for item in derived_targets.values() if item.get("id") == groups["id"]), {})
                sources = declaration.get("source_selections") or []
                if not all(isinstance(selections.get(source), str) and catalogue.child(source, selections[source])
                           for source in sources):
                    break  # consequential: the structural error is already counted
                found.append({"class": reason, "constraint": None,
                              "location": sorted(f"{source}.{selections[source]}" for source in sources)})
            elif reason == "unknown-feature" and (path or "").rsplit(".", 1)[-1].lower() in derived_targets:
                found.append({"class": "derived-variant-not-selectable", "constraint": None,
                              "location": [str(path).rsplit(".", 1)[-1].lower()]})
            elif reason == "lower-bound" and message.startswith("Mandatory feature not selected"):
                node = catalogue.nodes.get(str(path))
                common = bool(node and str(node.feature_id).startswith("C-"))
                found.append({"class": "common-capability-false" if common else "lower-bound", "constraint": None,
                              "location": [path]})
            else:
                found.append({"class": reason, "constraint": None,
                              "location": [path] if reason in {"lower-bound", "upper-bound"} and path else None})
            break
        else:
            raise ValueError(f"unclassified configurator message: {message}")
    return found


def yaml_reason_keys(messages: Sequence[str], selections: Mapping[str, Any],
                     catalogue: Catalogue) -> tuple[set[tuple[str, str | None]], int]:
    """(reason keys, counted violations) of one configurator run, comparable with ``reason_keys``."""
    reasons = yaml_reasons(messages, selections, catalogue)
    return {(item["class"], item["constraint"]) for item in reasons}, len(reasons)


# -- the entry point of the licensed authority job ----------------------------------------------


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
        failures += shadow_failures(receipt)
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


def run_replay(args: argparse.Namespace) -> int:
    failures = receipts.replay_receipts(args.receipt, ROOT)
    advisories = [] if failures else [
        f"{path}: {line}" for path in args.receipt
        for line in receipts.evaluator_advisories(json.loads(path.read_text(encoding="utf-8")))]
    print(json.dumps({"receipts": [str(path) for path in args.receipt], "failures": failures,
                      "advisories": advisories}, indent=2))
    return 1 if failures else 0


def run_refresh(args: argparse.Namespace) -> int:
    """Refresh every receipt before writing any of them, so a refusal leaves all of them as they were.

    Every change of a verdict, a derived variant or an admission is listed. With
    any such change nothing is written, unless ``--accept-verdict-changes``.
    """
    fresh, changes = [], []
    for path in args.receipt:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        catalogue = (receipt.get("shadow") or {}).get("catalogue")
        payload = receipts.read_elements(path.parent / receipt["elements"]["path"])
        evaluation = receipts.evaluate_payload(payload, model_sources=receipt.get("model_sources"))
        shadow = shadow_checks(evaluation, Path(catalogue["path"]), ROOT) if catalogue else {}
        refreshed = receipts.refreshed(path, ROOT, shadow=shadow)
        changes += [f"{path.name}: {change}" for change in receipts.verdict_changes(receipt, refreshed)]
        fresh.append((path, refreshed))
    write = not changes or args.accept_verdict_changes
    if write:
        for path, receipt in fresh:
            receipts.write_receipt(path, receipt)
    print(json.dumps({"receipts": [str(path) for path in args.receipt], "verdict_changes": changes,
                      "written": write}, indent=2))
    return 0 if write else 1


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
        if name == "refresh":
            command.add_argument("--accept-verdict-changes", action="store_true",
                                 help="write the receipts although verdicts, derived variants or admission change")
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
