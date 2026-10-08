#!/usr/bin/env python3
"""O4 Wave C2 dual construction (design E6): authored-YAML vs model-built contract.

The oracle side runs the code and data of the PR base revision (``main`` at
the Wave C1 merge, where the authored ontology and the Wave B runtime still
exist), materialized in a temporary detached worktree; the model side is the
YAML-free model-built contract of the checkout
(:func:`KernelContract.from_layers`). Two comparisons over the whole identity
universe:

1. **Served contract.** The base revision's Wave B model-authority facade
   (the contract the activated ``mab-`` runtime serves: model layers, the
   frozen O2 chain, the model successor contract, and the authored YAML as
   its residual provider) against the model-built contract. Acceptance (owner
   decision D9 evidence): the only differences are the 2 owner-visible
   exceptions (``IncrementTraceabilityShell``, ``derivesNeedFromConcern``)
   and the 5 deprecated aliases, each refused by the model-built contract.
2. **Authored contract.** The base revision's raw authored contract
   (``KernelContract.load``) against the model-built contract. Every
   difference is classified; an unclassified one fails. These are the
   reinterpretations Wave B already serves (successor pins and relations,
   native/external description text from the projection rows), disclosed
   here, not introduced by C2.

Wave C2 deletes this script and its test with the authored ontology; the
report written with ``--write``
(``docs/method-conformance/o4/closure/contract-equivalence.json``) stays as
evidence. It carries no binding block.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ONTOLOGY = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REPORT_PATH = "docs/method-conformance/o4/closure/contract-equivalence.json"
SCHEMA = "de4sdv.o4-contract-equivalence/v1"
#: PR base: main at the Wave C1 merge (#340), the last main revision with the
#: authored ontology and the Wave B runtime.
BASE_REVISION = "6dab3e9e45df00cd28b1b0ad824e30708097a663"

EXCEPTIONS = ("IncrementTraceabilityShell", "derivesNeedFromConcern")
ALIASES = ("constrainedBy", "deployedTo", "realizedBy", "validatedBy", "validatesFitnessForUse")


def _record(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "__dataclass_fields__"):
        return {"type": type(value).__name__, **asdict(value)}
    return value


def contract_surface(contract: Any, names: "set[str] | None" = None) -> dict[str, Any]:
    """What a contract answers for each identity (mapping, spec or absence)."""
    if names is None:
        names = set(contract.classes) | set(contract.relationships) | set(
            getattr(contract, "refused", None) or ())
    surface = {}
    for name in sorted(names):
        kind = "class" if name in contract.classes else "relationship"
        entry: dict[str, Any] = {"listed": name in contract.classes or name in contract.relationships}
        try:
            if kind == "class":
                entry["mapping"] = _record(contract.mapping(name))
            else:
                entry["mapping"] = _record(contract.relationship_mapping(name))
        except KeyError as exc:
            entry["absent"] = str(exc).strip("'\"")
        if name in contract.relationships:
            entry["spec"] = json.loads(json.dumps(contract.relationships[name], sort_keys=True))
        surface[name] = entry
    return surface


def oracle_surfaces(root: Path) -> dict[str, Any]:
    """Served (Wave B facade) and authored surfaces; runs INSIDE the base tree."""
    from de4sdv.semantic import model_authority_runtime as mar
    from de4sdv.semantic.kernel_contract import KernelContract
    from de4sdv.semantic.o3_bundle import O3AuthorityFacade, _load_chain_rows

    legacy = KernelContract.load(root / ONTOLOGY)
    rows, entries = _load_chain_rows(root)
    o3 = O3AuthorityFacade(legacy=legacy,
                           bundle={"bundle_id": "o3b-" + "0" * 32,
                                   "ontology_compatibility_identity": legacy.identity.to_dict()},
                           projection_rows=rows, profile_entries=entries)
    _, provisions = mar.load_layers(root)
    successor = mar.generate_successor_contract(root)
    routing = mar.compute_routing(legacy=legacy, provisions=provisions,
                                  successor_contract=successor,
                                  register_rows=mar.load_register_rows(root))
    facade = mar.ModelAuthorityFacade(legacy=legacy, o3_facade=o3, routing=routing,
                                      successor_contract=successor,
                                      bundle_id="mab-" + "0" * 32, components={})
    names = (set(legacy.classes) | set(legacy.relationships) | set(facade.classes)
             | set(facade.relationships) | set(mar.DEPRECATED_ALIASES))
    return {
        "served": contract_surface(facade, names),
        "authored": contract_surface(legacy, names),
        "providers": {name: p.layer for name, p in routing.providers.items()},
        "ontology_sha256": legacy.identity.sha256,
        "raw": {"classes": legacy.classes, "relationships": legacy.relationships,
                "validation_rules": __import__("yaml").safe_load(
                    (root / ONTOLOGY).read_text(encoding="utf-8")).get("validation_rules")},
    }


def _run_oracle(base: str) -> dict[str, Any]:
    """Materialize the base revision and compute its surfaces there."""
    with tempfile.TemporaryDirectory(prefix="de4sdv-e6-") as scratch:
        tree = Path(scratch) / "base"
        subprocess.run(["git", "worktree", "add", "--detach", "--quiet", str(tree), base],
                       cwd=ROOT, check=True)
        try:
            code = ("import json, sys; from pathlib import Path; "
                    f"sys.path.insert(0, {str(tree)!r}); sys.path.insert(1, {str(ROOT / 'scripts')!r}); "
                    "import compare_model_contract as c; "
                    f"print(json.dumps(c.oracle_surfaces(Path({str(tree)!r}))))")
            result = subprocess.run([sys.executable, "-c", code], cwd=tree, check=True,
                                    capture_output=True, text=True)
            return json.loads(result.stdout)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT,
                           check=False, capture_output=True)


def _classify_authored(name: str, authored: dict[str, Any], model: dict[str, Any],
                       provider: str | None) -> str | None:
    """Why a raw-authored vs model difference is pre-existing Wave B behavior."""
    if name in EXCEPTIONS:
        return "owner-visible exception: refused with its register disposition (D5)"
    if name in ALIASES:
        return "deprecated alias: refused, retired; use the successor (D4)"
    if provider == "successor-contract":
        return ("Wave B successor contract (owner decision 2026-10-07): the model "
                "successor owns this identity's mapping")
    a, m = authored.get("mapping") or {}, model.get("mapping") or {}
    if a.get("type") == m.get("type") and a.get("type") in ("KernelNativeMapping", "KernelExternalMapping"):
        return (f"same {a['type']} kind; the description text comes from the {provider} "
                "projection row instead of the authored entry")
    if name == "usesVerificationMethod" and provider == "o2plus":
        return ("O2+ relationship row: vocabulary-only, no executable mapping in either "
                "contract; the authored domain/range text is not projected (D9 residual)")
    return None


def build_report(root: Path = ROOT, *, base: str = BASE_REVISION,
                 oracle: dict[str, Any] | None = None, model: Any = None) -> dict[str, Any]:
    from de4sdv.semantic.kernel_contract import KernelContract

    oracle = oracle if oracle is not None else _run_oracle(base)
    model = model if model is not None else KernelContract.from_layers(root)
    served, authored, providers = oracle["served"], oracle["authored"], oracle["providers"]
    universe = set(served) | set(model.classes) | set(model.relationships) | set(model.refused)
    built = contract_surface(model, universe)
    for name, disposition in model.refused.items():
        built[name]["refused"] = disposition
    empty = {"listed": False, "absent": "not in the contract"}
    served_diff = sorted(n for n in universe if served.get(n, empty) != built[n])
    authored_diff = {}
    for name in sorted(universe):
        a, m = authored.get(name, empty), built[name]
        a_core = {k: a.get(k) for k in ("listed", "mapping", "absent")}
        m_core = {k: m.get(k) for k in ("listed", "mapping", "absent")}
        a_dr = {k: (a.get("spec") or {}).get(k) for k in ("domain", "range")}
        m_dr = {k: (m.get("spec") or {}).get(k) for k in ("domain", "range")}
        same_mapping = a_core == m_core
        same_domain_range = a_dr == m_dr or not (a.get("listed") and m.get("listed"))
        if same_mapping and same_domain_range:
            continue
        authored_diff[name] = {
            "authored": {**a_core, "domain_range": a_dr},
            "model": {**m_core, "domain_range": m_dr},
            "classification": _classify_authored(name, a, m, providers.get(name)),
        }
    expected = sorted(EXCEPTIONS + ALIASES)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                          capture_output=True).stdout.strip()
    return {
        "schema": SCHEMA,
        "oracle_revision": base,
        "oracle_revision_note": ("main at the Wave C1 merge: the last main revision with the "
                                 "authored ontology and the Wave B runtime; its own code built "
                                 "the served and authored surfaces"),
        "model_revision": head,
        "model_revision_note": ("the commit whose model-built contract was compared; "
                                "informational, not a binding"),
        "authored_ontology": {"path": ONTOLOGY, "sha256": oracle["ontology_sha256"]},
        "model_contract_identity": model.identity.to_dict(),
        "identity_universe": len(universe),
        "served_contract": {
            "oracle": ("Wave B model-authority facade (model layers, frozen O2 chain, model "
                       "successor contract; authored YAML as residual provider)"),
            "differences": served_diff,
            "expected_differences": expected,
            "result": "EQUAL_EXCEPT_EXPECTED" if served_diff == expected else "UNEXPECTED_DIFFERENCE",
            "detail": {name: {"served": served.get(name, empty), "model": built[name]}
                       for name in served_diff},
        },
        "authored_contract": {
            "oracle": "raw authored contract (KernelContract.load of the authored YAML)",
            "differences": authored_diff,
            "unclassified": sorted(n for n, d in authored_diff.items() if d["classification"] is None),
        },
        "model_only_identities": sorted(n for n in set(model.classes) | set(model.relationships)
                                        if not authored.get(n, empty).get("listed")),
        "manifest_held_fields": manifest_held_fields(root, oracle["raw"]),
        "batch1_reviewed_definitions": batch1_reviewed_definitions(root, oracle["raw"]),
        "authored_identities": {
            "note": "every class and relationship name of the authored ontology",
            "classes": sorted(oracle["raw"]["classes"]),
            "relationships": sorted(oracle["raw"]["relationships"]),
        },
        "authored_validation_rules": {
            "note": ("the authored validation rules R001-R010 (statement, enforcement, R003 "
                     "groundings); tests lock their model homes "
                     "(de4sdv_ontology_validation_rules.sysml) to it after the deletion"),
            "rules": oracle["raw"]["validation_rules"],
        },
        "authored_definitions": {
            "note": ("the authored definition text of every class and relationship that had "
                     "one, normalized; tests lock the model documentation homes "
                     "(kernel-definition-homes.json) to it after the deletion"),
            "entries": {f"{kind}:{name}": " ".join(str(row["definition"]).split())
                        for kind in ("classes", "relationships")
                        for name, row in sorted(oracle["raw"][kind].items())
                        if isinstance(row, dict) and row.get("definition")},
        },
        "claim_boundary": ("last executable parity proof between the authored ontology and the "
                           "model-built contract over class and relationship mappings; not a "
                           "semantic proof beyond them; no compliance or certification claim"),
    }


MANIFEST_PATH = "docs/method-conformance/o4/definition-admission-batch2.yaml"


def manifest_held_values(row: dict[str, Any]) -> dict[str, Any]:
    """The contract fields one batch-2 manifest row holds (owner decision D9)."""
    values: dict[str, Any] = {"reviewed_definition": row.get("reviewed_definition")}
    if row["semantic_kind"] == "class":
        grounding = row["grounding"]
        values.update(kernel_mapping=grounding["kernel_mapping"],
                      sub_class_of=grounding["sub_class_of"],
                      disjoint_with=list(grounding["disjoint_with"]))
    elif row["admission_class"] != "successor":
        values["relation"] = dict(row["relation"])
        if "mechanics" in row:
            values["mechanics"] = dict(row["mechanics"])
    return values


def authored_values(row: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any] | None:
    """The same fields read from the authored ontology (same rules as the
    retired batch-2 lock test)."""
    identity = row["identity"]
    if row["semantic_kind"] == "class":
        spec = raw["classes"].get(identity)
        if spec is None:
            return None
        return {"reviewed_definition": " ".join(str(spec.get("definition") or "").split()) or None,
                "kernel_mapping": spec.get("kernel"), "sub_class_of": spec.get("subClassOf"),
                "disjoint_with": list(spec.get("disjointWith", []))}
    spec = raw["relationships"].get(identity)
    if spec is None or row["admission_class"] == "successor":
        return None
    mapping = spec.get("sysml_mapping") or {}
    values: dict[str, Any] = {
        "reviewed_definition": (" ".join(str(spec["definition"]).split())
                                if row["home"]["form"] in ("owned-doc", "named-doc") else None),
        "relation": {"domain": spec.get("domain"), "range": spec.get("range"),
                     "semantic_strength": mapping.get("semantic_strength")},
    }
    if "mechanics" in row:
        values["mechanics"] = {k: v for k, v in mapping.items() if k != "semantic_strength"}
    return values


def manifest_held_fields(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    """Per batch-2 row: the manifest-held contract fields and their authored values."""
    import yaml

    rows = yaml.safe_load((root / MANIFEST_PATH).read_text(encoding="utf-8"))["admitted"]
    entries: dict[str, Any] = {}
    for row in sorted(rows, key=lambda r: r["identity"]):
        held = manifest_held_values(row)
        authored = authored_values(row, raw)
        entries[row["identity"]] = {"admission_class": row["admission_class"], "manifest": held,
                                    "authored": authored,
                                    "equal": authored is None or authored == held}
    contract_rows = [n for n, e in entries.items()
                     if "relation" in e["manifest"] or "kernel_mapping" in e["manifest"]]
    return {
        "manifest": MANIFEST_PATH,
        "rows": len(entries),
        "rows_with_manifest_held_contract_fields": len(contract_rows),
        "relation_rows": sum("relation" in e["manifest"] for e in entries.values()),
        "kernel_mapping_rows": sum("kernel_mapping" in e["manifest"] for e in entries.values()),
        "unequal": sorted(n for n, e in entries.items() if not e["equal"]),
        "entries": entries,
    }


BATCH1_MANIFEST_PATH = "docs/method-conformance/o4/definition-admission.yaml"


def batch1_reviewed_definitions(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    """Batch-1 reviewed definitions vs the authored class definitions."""
    import yaml

    rows = yaml.safe_load((root / BATCH1_MANIFEST_PATH).read_text(encoding="utf-8"))["admitted"]
    entries = {}
    for row in sorted(rows, key=lambda r: r["identity"]):
        spec = raw["classes"].get(row["identity"]) or raw["relationships"].get(row["identity"]) or {}
        authored = " ".join(str(spec.get("definition") or "").split()) or None
        entries[row["identity"]] = {"manifest": row.get("reviewed_definition"), "authored": authored,
                                    "equal": authored == row.get("reviewed_definition")}
    return {"manifest": BATCH1_MANIFEST_PATH, "rows": len(entries),
            "unequal": sorted(n for n, e in entries.items() if not e["equal"]), "entries": entries}


def report_errors(report: dict[str, Any]) -> list[str]:
    errors = []
    served = report["served_contract"]
    if served["result"] != "EQUAL_EXCEPT_EXPECTED":
        errors.append("served contract differs beyond the 2 exceptions and 5 aliases: "
                      f"{served['differences']}")
    if report["authored_contract"]["unclassified"]:
        errors.append("unclassified authored-vs-model differences: "
                      f"{report['authored_contract']['unclassified']}")
    if report["batch1_reviewed_definitions"]["unequal"]:
        errors.append("batch-1 reviewed definitions differ from the authored ontology: "
                      f"{report['batch1_reviewed_definitions']['unequal']}")
    if report["manifest_held_fields"]["unequal"]:
        errors.append("manifest-held contract fields differ from the authored ontology: "
                      f"{report['manifest_held_fields']['unequal']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default=BASE_REVISION)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help=f"write {REPORT_PATH}")
    mode.add_argument("--json", type=Path, help="write the report to this path")
    args = parser.parse_args(argv)
    report = build_report(ROOT, base=args.base)
    errors = report_errors(report)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        target = ROOT / REPORT_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    elif args.json:
        args.json.write_text(text, encoding="utf-8")
    print(f"served contract: {report['served_contract']['result']} "
          f"({len(report['served_contract']['differences'])} differences: "
          f"{', '.join(report['served_contract']['differences'])})")
    print(f"authored contract: {len(report['authored_contract']['differences'])} classified differences, "
          f"{len(report['authored_contract']['unclassified'])} unclassified")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    # Only as a script: the oracle subprocess imports this module from the
    # base worktree's sys.path and must not see this checkout's package.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
