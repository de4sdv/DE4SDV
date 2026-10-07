"""Model-projection coverage gate (O4 Wave B, shadow ratchet).

Classifies four populations as either ``projected`` (provider layer + layer
digest) or ``residual`` (reason), using the same routing the model-authority
bundle binds (:func:`model_authority_runtime.compute_routing`):

- every retained O4 register row (``retained_residual`` -- the owner's
  criterion; it must stay empty and Wave C makes it blocking);
- every ontology YAML identity the register does not list;
- every registered NON-retained row (merged/removed) still present in the
  ontology YAML: the runtime serves such a row from the authored YAML, so it
  is reported as an owner-visible ``exceptions`` entry carrying its reason and
  register disposition (routing does not refuse it; that is a Wave C owner
  call);
- every governed kernel declaration.

The report's total ``residual`` equals the routing residual exactly: every
identity the runtime serves from the authored YAML is listed.

The gate compares the current classification with the committed baseline
``docs/method-conformance/o4/model-authority-coverage-baseline.yaml`` and fails
on:

- residual drift in either direction (a new residual or exception, or a
  resolved one still listed in the baseline — the baseline must stay exact);
- duplicate providers (two layers claiming one identity without agreement);
- routing/layer digest mismatch against the baseline, and — when a bundle is
  supplied — a bundle whose bound routing/layers differ from the checkout.

Shadow mode: a non-empty residual is reported, not refused. Wave C makes an
empty residual blocking. The baseline carries no binding block; it is a
reviewed ratchet record, not revision-bound evidence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import model_authority_runtime as mar
from .kernel_contract import KernelContract, KernelFileMapping
from .o3_bundle import canonical_json

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = "docs/method-conformance/o4/model-authority-coverage-baseline.yaml"
REPORT_SCHEMA = "de4sdv.model-projection-coverage/v1"
BASELINE_SCHEMA = "de4sdv.model-authority-coverage-baseline/v1"
ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
MODE = "shadow"


def _governed_declarations(root: Path, contract: KernelContract) -> list[tuple[str, str]]:
    """``(file, declaration)`` pairs in the governed kernel directory.

    Reuses the existing ontology-kernel gate's declaration extractor (the
    same normalization that gate enforces); this is gate-time accounting,
    never runtime identity.
    """
    from scripts import check_model_sync

    directory = Path(root) / contract.governed_directory
    pairs = []
    for path in sorted(directory.rglob("*.sysml")):
        relative = path.relative_to(root).as_posix()
        for declaration in sorted(check_model_sync._sysml_definitions(path.read_text(encoding="utf-8"))):
            pairs.append((relative, declaration))
    return pairs


def _layer_digests(records: list[dict[str, Any]], root: Path) -> dict[str, str]:
    digests = {record["layer"]: mar._canonical_digest(
        [record["projection"]["sha256"], record["profile"]["sha256"]]) for record in records}
    digests["o3"] = mar._canonical_digest(mar.o3_chain_records(root))
    return digests


def build_report(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    legacy = KernelContract.load(root / ONTOLOGY_PATH)
    records, provisions = mar.load_layers(root)
    contract = mar.generate_successor_contract(root)
    register = mar.load_register_rows(root)
    routing = mar.compute_routing(legacy=legacy, provisions=provisions,
                                  successor_contract=contract, register_rows=register)
    digests = _layer_digests(records, root)
    digests["successor-contract"] = contract["id"]
    retained = sorted(n for n, r in register.items() if r.get("accounting_status") == "retained")
    yaml_identities = set(legacy.classes) | set(legacy.relationships)
    unregistered = sorted(yaml_identities - set(register))
    non_retained = sorted((yaml_identities & set(register)) - set(retained))
    identities: dict[str, Any] = {}
    for name in retained + unregistered + non_retained:
        provision = routing.providers.get(name)
        if name in retained:
            group = "retained-register-row"
        elif name in register:
            group = "registered-non-retained-yaml-identity"
        else:
            group = "unregistered-yaml-identity"
        if provision is not None:
            identities[name] = {"group": group, "status": "projected", "layer": provision.layer,
                                "layer_digest": digests[provision.layer]}
        elif name in mar.DEPRECATED_ALIASES:
            identities[name] = {"group": group, "status": "projected", "layer": "deprecated-alias",
                                "layer_digest": digests["successor-contract"],
                                "successor": mar.DEPRECATED_ALIASES[name].successor}
        elif name in routing.residual:
            entry = {"group": group, "status": "residual", "reason": routing.residual[name]}
            if name in register:
                entry["register"] = {key: register[name].get(key) for key in (
                    "accounting_status", "migration_class", "final_disposition")}
            identities[name] = entry
        else:  # retired by the successor contract: answered by no provider
            identities[name] = {"group": group, "status": "retired",
                                "reason": "retired by the model-derived successor contract"}
    projected_pins: dict[tuple[str, str], str] = {}
    for name, provision in routing.providers.items():
        mapping = provision.mapping
        if provision.layer == "o3":
            continue
        if isinstance(mapping, KernelFileMapping):
            projected_pins.setdefault((mapping.file, mapping.declaration), provision.layer)
        carrier = (provision.spec or {}).get("carrier") if isinstance(provision.spec, dict) else None
        if carrier:
            projected_pins.setdefault((carrier["file"], carrier["declaration"]), provision.layer)
    for carrier in contract["carriers"].values():
        projected_pins.setdefault((carrier["file"], carrier["declaration"]), "successor-contract")
    from .o3_bundle import _load_chain_rows

    o3_rows, _entries = _load_chain_rows(root)
    for name in mar.MIGRATED_CLASSES:
        pin = ((o3_rows.get(name) or {}).get("grounding") or {}).get("kernel_binding_contract") or {}
        if pin.get("source_file") and pin.get("declaration"):
            projected_pins.setdefault((pin["source_file"], pin["declaration"]), "o3")
    yaml_pins = {}
    for name, spec in legacy.classes.items():
        kernel = (spec or {}).get("kernel") or {}
        if isinstance(kernel.get("file"), str) and isinstance(kernel.get("declaration"), str):
            yaml_pins[(kernel["file"], kernel["declaration"])] = name
    declarations: dict[str, Any] = {}
    for file, declaration in _governed_declarations(root, legacy):
        key = f"{file}::{declaration}"
        excluded = (legacy.exclusions.get(file) or {}).get(declaration)
        if (file, declaration) in projected_pins:
            layer = projected_pins[(file, declaration)]
            declarations[key] = {"status": "projected", "layer": layer, "layer_digest": digests[layer]}
        elif excluded:
            declarations[key] = {"status": "excluded", "reason": str(excluded)}
        elif (file, declaration) in yaml_pins:
            declarations[key] = {"status": "residual",
                                 "reason": f"mapped only by authored ontology YAML ({yaml_pins[(file, declaration)]})"}
        else:
            declarations[key] = {"status": "residual", "reason": "unclassified governed declaration"}
    residual = sorted(n for n, v in identities.items() if v["status"] == "residual")
    if residual != sorted(routing.residual):
        missing = sorted(set(routing.residual) - set(residual))
        raise ValueError(f"coverage residual differs from the routing residual: {missing}")
    retained_residual = [n for n in residual if identities[n]["group"] == "retained-register-row"]
    unregistered_residual = [n for n in residual
                             if identities[n]["group"] == "unregistered-yaml-identity"]
    exceptions = [n for n in residual
                  if identities[n]["group"] == "registered-non-retained-yaml-identity"]
    residual_declarations = sorted(k for k, v in declarations.items() if v["status"] == "residual")
    report = {
        "schema": REPORT_SCHEMA,
        "mode": MODE,
        "routing_digest": mar._canonical_digest(routing.record()),
        "layer_digests": digests,
        "duplicates": list(routing.duplicates),
        "identities": identities,
        "kernel_declarations": declarations,
        "summary": {
            "retained_rows": len(retained),
            "unregistered_yaml_identities": len(unregistered),
            "registered_non_retained_yaml_identities": len(non_retained),
            "governed_declarations": len(declarations),
            "projected_identities": sum(v["status"] == "projected" for v in identities.values()),
            "retained_residual": len(retained_residual),
            "unregistered_residual": len(unregistered_residual),
            "exceptions": len(exceptions),
            "residual_identities": len(residual),
            "residual_declarations": len(residual_declarations),
            "retained_residual_empty": not retained_residual,
            "residual_empty": not residual and not residual_declarations,
        },
        "residual": residual,
        "retained_residual": retained_residual,
        "unregistered_residual": unregistered_residual,
        "exceptions": exceptions,
        "residual_declarations": residual_declarations,
    }
    return report


def baseline_from_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": BASELINE_SCHEMA,
        "mode": MODE,
        "note": ("Reviewed shadow ratchet for the model-authority coverage gate. "
                 "Not revision-bound evidence; no binding block. Regenerate with "
                 "scripts/check_model_projection_coverage.py --write-baseline after "
                 "a reviewed projection change. residual equals the runtime routing "
                 "residual; exceptions are the owner-visible registered non-retained "
                 "rows still served from the authored YAML. Wave C makes an empty "
                 "retained_residual blocking."),
        "routing_digest": report["routing_digest"],
        "layer_digests": dict(report["layer_digests"]),
        "residual": list(report["residual"]),
        "retained_residual": list(report["retained_residual"]),
        "exceptions": list(report["exceptions"]),
        "residual_declarations": list(report["residual_declarations"]),
    }


def load_baseline(root: Path = ROOT, path: str = BASELINE_PATH) -> dict[str, Any]:
    document = yaml.safe_load((Path(root) / path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema") != BASELINE_SCHEMA:
        raise ValueError(f"coverage baseline schema mismatch: {path}")
    if "binding" in document:
        raise ValueError("coverage baseline must not carry a binding block")
    return document


def compare(report: Mapping[str, Any], baseline: Mapping[str, Any]) -> list[str]:
    errors = []
    for name in report["duplicates"]:
        errors.append(f"duplicate provider: {name}")
    for key in ("residual", "retained_residual", "exceptions", "residual_declarations"):
        current, recorded = set(report[key]), set(baseline.get(key) or ())
        for name in sorted(current - recorded):
            errors.append(f"residual drift: new {key} entry {name!r} not in the baseline")
        for name in sorted(recorded - current):
            errors.append(f"residual drift: {key} entry {name!r} resolved; update the baseline")
    if report["routing_digest"] != baseline.get("routing_digest"):
        errors.append("routing digest differs from the baseline (provider set changed)")
    if dict(report["layer_digests"]) != dict(baseline.get("layer_digests") or {}):
        errors.append("projection layer digests differ from the baseline")
    return errors


def bundle_errors(report: Mapping[str, Any], bundle: Mapping[str, Any], root: Path = ROOT) -> list[str]:
    """A bundle must bind exactly the checkout's routing and layer bytes."""
    components = (bundle or {}).get("components") or {}
    errors = []
    if mar._canonical_digest(components.get("routing")) != report["routing_digest"]:
        errors.append("bundle routing digest differs from the checkout")
    recorded = {r.get("layer"): mar._canonical_digest(
        [r["projection"]["sha256"], r["profile"]["sha256"]]) for r in components.get("layers") or ()}
    current = {k: v for k, v in report["layer_digests"].items() if k not in ("o3", "successor-contract")}
    if recorded != current:
        errors.append("bundle layer digests differ from the checkout")
    if (components.get("successor_contract") or {}).get("id") != report["layer_digests"]["successor-contract"]:
        errors.append("bundle successor contract differs from the checkout")
    return errors


def run_check_errors(root: Path = ROOT) -> list[str]:
    try:
        report = build_report(root)
        baseline = load_baseline(root)
    except Exception as exc:  # a gate that cannot evaluate fails
        return [f"model-projection coverage cannot be evaluated: {exc}"]
    return compare(report, baseline)


def render_baseline(baseline: Mapping[str, Any]) -> str:
    header = "# Model-authority coverage baseline (shadow ratchet; no binding block).\n"
    return header + yaml.safe_dump(dict(baseline), sort_keys=False, width=100)


def report_digest(report: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(report).encode()).hexdigest()


__all__ = ["build_report", "compare", "bundle_errors", "run_check_errors", "load_baseline",
           "baseline_from_report", "render_baseline", "report_digest", "BASELINE_PATH"]
