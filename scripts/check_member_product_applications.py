#!/usr/bin/env python3
"""Derive appliesToMemberProduct over the licensed export of a pull-request head.

The derived fact of ADR 0022, decision 8 (``de4sdv.semantic.applies_to_member_product``)
runs in the scope battery of the privileged full-model ingestion, on the
served model. This gate runs the same derivation before the merge: the Method
Check runs it over the export of the pull-request head. The kernel bindings
are the ones the export itself validates (``export_evaluation.load_export_snapshot``,
ADR 0011). The governed scope is the record of the production scope validator
(``product_line_scope.validate_scope_elements``), as in the scope battery.

A refusal is a technical error: the script writes the refusal and exits 1.
Two examples are a configuration that applies to more than one member product,
and a projection name that two part definitions of ``product-models/``
declare. The method check stays advisory. This gate refuses only what the
scope battery of the next release would refuse.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "de4sdv.member-product-gate/v1"


def load_export(export_path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    """What the derivation reads from one export: its elements and sources, the
    kernel bindings it validates, its external references and the governed scope record."""
    from de4sdv.semantic.export_evaluation import load_export_snapshot
    from de4sdv.sysml_api.baseline import BaselineExportBundle
    from de4sdv.sysml_api.product_line_scope import validate_scope_elements

    snapshot = load_export_snapshot(export_path, None, root=root)
    sources = dict(snapshot.sources)
    return {
        "git_commit": snapshot.revision.git_commit,
        "export_sha256": snapshot.export_sha256,
        "elements": snapshot.elements,
        "element_sources": sources,
        "kernel_bindings": {binding.ontology_class: binding.element_id for binding in snapshot.kernel_bindings},
        "external_references": BaselineExportBundle.load(export_path).external_references,
        "governed_scope": validate_scope_elements(snapshot.elements, sources),
    }


def derive(model: Mapping[str, Any]) -> dict[str, Any]:
    """The derived fact over one loaded model; a refusal raises."""
    from de4sdv.semantic.applies_to_member_product import member_product_applications

    options = {"library_source": model["library_source"]} if model.get("library_source") else {}
    return member_product_applications(
        model["elements"], model["element_sources"], kernel_bindings=model["kernel_bindings"],
        external_references=model.get("external_references") or (),
        governed_scope=model.get("governed_scope"), **options)


def check(export_path: Path, revision: str, *, root: Path = ROOT) -> dict[str, Any]:
    """The gate's record of one export of the exact revision; a refusal raises."""
    model = load_export(export_path, root=root)
    if model["git_commit"] != revision:
        raise ValueError(f"the export is of {model['git_commit'] or 'no revision'}, not of {revision}")
    applications = derive(model)
    return {
        "schema": SCHEMA,
        "revision": revision,
        "export_sha256": model.get("export_sha256"),
        "status": "derived",
        "configuration_member_products": applications,
    }


def summary(record: Mapping[str, Any]) -> str:
    """The job-summary section of one gate record."""
    lines = ["## appliesToMemberProduct (gate)", ""]
    if record["status"] != "derived":
        lines += [f"**Refused** on `{record['revision']}`: {record['error']}", ""]
        return "\n".join(lines) + "\n"
    rows = record["configuration_member_products"]["configurations"]
    lines += [f"Derived on `{record['revision']}`: {sum(1 for row in rows if row['member_product'])} of "
              f"{len(rows)} configurations apply to a member product.", "",
              "| Configuration | Member product |", "|---|---|"]
    for row in rows:
        member = row["member_product"]
        name = f"`{member['declared_name']}`" if member else "none"
        lines.append(f"| `{row['configuration']}` | {name} |")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--export", required=True, type=Path, help="the licensed export of the revision")
    parser.add_argument("--revision", required=True, help="the full commit the export must be of")
    parser.add_argument("--output", required=True, type=Path, help="where the gate record is written")
    parser.add_argument("--summary", type=Path, help="a job summary to append the result to")
    args = parser.parse_args(argv)
    try:
        record = check(args.export, args.revision)
    except Exception as error:  # noqa: BLE001 - every refusal of the derivation is a technical error here
        record = {"schema": SCHEMA, "revision": args.revision, "status": "refused",
                  "error": f"{type(error).__name__}: {error}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary is not None:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary(record))
    if record["status"] != "derived":
        print(f"appliesToMemberProduct refused on {args.revision}: {record['error']}", file=sys.stderr)
        return 1
    rows = record["configuration_member_products"]["configurations"]
    print(json.dumps({row["configuration"]: (row["member_product"] or {}).get("declared_name") for row in rows},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
