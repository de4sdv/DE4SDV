#!/usr/bin/env python3
"""Evaluate the PLEML feature models and keep their receipts (ADR 0022, plan step S2).

Commands:

* ``receipts``: the entry point of the licensed authority job. It takes the
  job's export bundle (serialized with the production export's options, the
  PLEML library labelled with the pinned package's ``LIBRARY_PATH``), writes
  ``<name>.elements.json.xz`` and one ``<feature-model file stem>.receipt.json``
  per feature model to ``--out``, and exits 1 when an evaluation records
  integrity errors. ``--compare`` refuses when the fresh elements differ
  from the committed receipts' (they are stale or are not the serializer's
  output). :func:`write_receipts` is the same entry point as a function.
* ``replay``: unlicensed. Re-run the evaluator on the committed elements of
  each receipt; exit 1 when its inputs changed, its evaluation does not
  reproduce byte for byte or it records integrity errors. Code that differs
  from the code that evaluated a receipt is reported as an advisory.
  ``replay_receipts`` and ``replay_committed`` of ``pleml_receipts`` are the
  same check as functions.
* ``refresh``: unlicensed. Rewrite receipts from their intact committed
  elements when the evaluation no longer reproduces. It lists every change of
  a verdict, a derived variant or an admission, and writes nothing when there
  is one, unless ``--accept-verdict-changes``.

Nothing here qualifies anything or executes a PLEML expression natively.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic import pleml_receipts as receipts  # noqa: E402
from de4sdv.sysml_api.baseline import BaselineExportBundle  # noqa: E402

# -- the entry point of the licensed authority job ----------------------------------------------


def write_receipts(bundle: BaselineExportBundle | Mapping[str, Any], out: Path, *, serializer: Mapping[str, Any],
                   name: str = "pleml-feature-models", model_sources: Iterable[str] | None = None) -> dict[str, Any]:
    """Write the elements file and one receipt per feature model of a licensed bundle into ``out``.

    ``serializer`` records the serialization: its name, version and options,
    which the elements carry, and the executor revision, which only the
    receipts record (with the bundle's commit) as the run's provenance. ``out``
    must not exist. Returns the written paths and the failures (the integrity
    errors the evaluations record), which a licensed job must treat as a
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
        path = out / f"{Path(document).stem}.receipt.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
        failures += receipts.integrity_failures(receipt)
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
        refreshed = receipts.refreshed(path, ROOT)
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
