"""Model-projection coverage gate (O4 Wave C2: blocking, one authority).

Replaces the old bidirectional hand-maintained ontology/kernel gate with
model-to-generated-projection coverage plus justified exclusions. It
classifies, using the routing the model-authority bundle binds
(:func:`model_contract.compute_routing`):

- every O4 register row and every identity of the model-built contract
  (:func:`KernelContract.from_layers`): ``projected`` (provider layer + layer
  digest), ``refused`` (a registered non-retained row: merged/removed, with
  its register disposition), ``retired`` (a successor retirement, e.g. a
  former deprecated alias) or ``residual`` (a retained row no layer provides);
- every governed kernel declaration: projected by a model-generated layer
  (class pin or relationship-carrier pin), or listed in the kernel-internal
  declarations manifest with a reason (owner decision D3,
  ``docs/method-conformance/o4/kernel-internal-declarations.yaml``). The
  equation is a disjoint union: a declaration is projected or listed, never
  both.

It fails, regardless of the baseline, on any residual (identity or
declaration), any duplicate provider, and any kernel-accounting error: an
unclassified governed declaration, a stale or reason-less manifest entry, a
manifest entry outside the governed directory, a listed declaration that is
also projected, or a feature slice re-declaring a class-mapped kernel name.

The committed baseline
``docs/method-conformance/o4/model-authority-coverage-baseline.yaml`` is a
reviewed ratchet for the routing digest, the layer digests and the refused /
retired sets: any change needs a reviewed baseline update. It carries no
binding block.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import model_contract as mc
from .kernel_contract import KernelContract, KernelFileMapping
from .model_contract import canonical_json

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = "docs/method-conformance/o4/model-authority-coverage-baseline.yaml"
REPORT_SCHEMA = "de4sdv.model-projection-coverage/v3"
BASELINE_SCHEMA = "de4sdv.model-authority-coverage-baseline/v3"
KERNEL_INTERNAL_PATH = "docs/method-conformance/o4/kernel-internal-declarations.yaml"
KERNEL_INTERNAL_SCHEMA = "de4sdv.kernel-internal-declarations/v1"
FEATURES_DIRECTORY = "textual-notation-of-model/packages/features"
MODE = "blocking"


def _sysml_definitions(text: str) -> set[str]:
    """Normalized ``<kind> def <Name>`` declarations (the gate's extractor)."""
    from scripts import check_model_sync

    return check_model_sync._sysml_definitions(text)


def _is_within(relative_file: str, relative_directory: str) -> bool:
    """The model-sync gate's repository-relative containment rule."""
    from scripts import check_model_sync

    return check_model_sync._is_within(relative_file, relative_directory)


def _governed_declarations(root: Path, directory: str) -> list[tuple[str, str]]:
    """``(file, declaration)`` pairs in the governed kernel directory.

    Reuses the existing model-sync gate's declaration extractor (the same
    normalization); this is gate-time accounting, never runtime identity.
    """
    pairs = []
    for path in sorted((Path(root) / directory).rglob("*.sysml")):
        relative = path.relative_to(root).as_posix()
        for declaration in sorted(_sysml_definitions(path.read_text(encoding="utf-8"))):
            pairs.append((relative, declaration))
    return pairs


def _feature_declarations(root: Path) -> list[tuple[str, str]]:
    pairs = []
    base = Path(root) / FEATURES_DIRECTORY
    if base.is_dir():
        for path in sorted(base.rglob("*.sysml")):
            relative = path.relative_to(root).as_posix()
            for declaration in sorted(_sysml_definitions(path.read_text(encoding="utf-8"))):
                pairs.append((relative, declaration))
    return pairs


def load_kernel_internal(root: Path = ROOT) -> tuple[str | None, dict[str, dict[str, str]], list[str]]:
    """Read the kernel-internal declarations manifest (owner decision D3).

    Returns ``(governed_directory, {file: {declaration: reason}}, errors)``.
    Structural problems are reported as errors (fail closed) and the
    offending entries are left out, so the accounting still runs and every
    consequence is reported.
    """
    path = Path(root) / KERNEL_INTERNAL_PATH
    tag = "kernel-internal manifest"
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, {}, [f"{tag} {KERNEL_INTERNAL_PATH} is unreadable: {exc}"]
    if not isinstance(document, dict):
        return None, {}, [f"{tag} must be a mapping"]
    errors: list[str] = []
    if document.get("schema") != KERNEL_INTERNAL_SCHEMA:
        errors.append(f"{tag} schema must be {KERNEL_INTERNAL_SCHEMA}")
    if "binding" in document:
        errors.append(f"{tag} must not carry a binding block")
    directory = document.get("governed_directory")
    if (not isinstance(directory, str) or not directory.strip()
            or Path(directory).is_absolute() or ".." in Path(directory).parts
            or not (Path(root) / directory).is_dir()):
        errors.append(f"{tag} governed directory not found or unsafe: {directory!r}")
        directory = None
    raw = document.get("declarations")
    if not isinstance(raw, dict):
        errors.append(f"{tag} declarations must map files to declarations and reasons")
        raw = {}
    declarations: dict[str, dict[str, str]] = {}
    for rel_file, entries in raw.items():
        if not isinstance(rel_file, str) or directory is None or not _is_within(rel_file, directory):
            errors.append(f"{tag} file is outside the governed directory or unsafe: {rel_file!r}")
            continue
        if not isinstance(entries, dict):
            errors.append(f"{tag} entries for {rel_file} must map declarations to reasons")
            continue
        for declaration, reason in entries.items():
            if not isinstance(declaration, str) or not declaration.strip():
                errors.append(f"{tag} {rel_file}: declaration must be a non-empty string")
                continue
            if not isinstance(reason, str) or not reason.strip():
                errors.append(f"{tag} {rel_file}: '{declaration}' needs a non-empty reason")
                continue
            declarations.setdefault(rel_file, {})[" ".join(declaration.split())] = reason
    return directory, declarations, errors


def kernel_accounting(
    governed: list[tuple[str, str]],
    internal: Mapping[str, Mapping[str, str]],
    projected: Mapping[tuple[str, str], str],
    class_pins: set[tuple[str, str]],
    feature_declarations: list[tuple[str, str]],
    directory: str,
) -> tuple[dict[str, Any], list[str]]:
    """Classify every governed declaration and return the accounting errors.

    The equation: governed declarations = projected declarations + listed
    kernel-internal declarations (each with a reason), as a disjoint union.
    ``projected`` holds every model-projected pin (class mappings and
    relationship-carrier pins); ``class_pins`` are the class mappings only.
    A listed declaration must not also be projected (one home per
    declaration). Class-mapped kernel names (in the governed directory) may
    be specialized or imported by feature slices but never re-declared there.
    """
    errors: list[str] = []
    governed_set = set(governed)
    listed = {(file, declaration): reason
              for file, entries in internal.items() for declaration, reason in entries.items()}
    declarations: dict[str, Any] = {}
    for file, declaration in governed:
        key = f"{file}::{declaration}"
        if (file, declaration) in projected:
            layer = projected[(file, declaration)]
            declarations[key] = {"status": "projected", "layer": layer}
        elif (file, declaration) in listed:
            declarations[key] = {"status": "excluded", "reason": str(listed[(file, declaration)])}
        else:
            declarations[key] = {"status": "residual", "reason": "unclassified governed declaration"}
            errors.append(
                f"kernel accounting: {file}: declaration '{declaration}' is unclassified; "
                f"project it through a model-generated layer or list it in "
                f"{KERNEL_INTERNAL_PATH} with a reason")
    for file, declaration in sorted(set(listed) - governed_set):
        errors.append(f"kernel accounting: {file}: listed kernel-internal declaration "
                      f"'{declaration}' does not exist (stale entry?)")
    for file, declaration in sorted(set(listed) & set(projected)):
        errors.append(f"kernel accounting: {file}: declaration '{declaration}' is both projected "
                      f"({projected[(file, declaration)]}) and listed as kernel-internal")
    protected = {declaration.split()[-1] for (file, declaration) in set(class_pins)
                 if _is_within(file, directory)}
    for file, declaration in feature_declarations:
        name = declaration.split()[-1]
        if name in protected:
            errors.append(f"kernel accounting: {file}: feature slice re-declares projected kernel "
                          f"name '{name}'; specialize or import the kernel declaration instead")
    return declarations, errors


def _layer_digests(records: list[dict[str, Any]]) -> dict[str, str]:
    digests = {}
    for record in records:
        if record.get("frozen"):
            digests[record["layer"]] = mc._canonical_digest(
                [item["sha256"] for item in record["chain"]])
        else:
            digests[record["layer"]] = mc._canonical_digest(
                [record["projection"]["sha256"], record["profile"]["sha256"]])
    return digests


def build_report(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    records, provisions = mc.load_model_layers(root)
    successor = mc.generate_model_successor_contract(root, records=records, provisions=provisions)
    register = mc.load_register_rows(root)
    routing = mc.compute_routing(
        provisions=[p for p in provisions if p.layer != mc.O2_CHAIN_LAYER],
        successor_contract=successor, register_rows=register,
        seed=[p for p in provisions if p.layer == mc.O2_CHAIN_LAYER])
    contract = KernelContract.from_layers(root)
    digests = _layer_digests(records)
    digests["successor-contract"] = successor["id"]
    retired = dict(successor.get("retired") or {})
    universe = (set(register) | set(contract.classes) | set(contract.relationships)
                | set(contract.refused) | set(routing.providers))
    identities: dict[str, Any] = {}
    for name in sorted(universe):
        row = register.get(name)
        group = ("register-row" if row is not None else "model-identity")
        provision = routing.providers.get(name)
        if provision is not None and name not in contract.refused:
            entry = {"group": group, "status": "projected", "layer": provision.layer,
                     "layer_digest": digests[provision.layer]}
        elif name in retired:
            entry = {"group": group, "status": "retired",
                     "reason": contract.refused.get(name) or str(retired.get(name) or "")}
        elif name in contract.refused:
            entry = {"group": group, "status": "refused", "reason": contract.refused[name]}
        else:
            entry = {"group": group, "status": "residual",
                     "reason": routing.residual.get(name, "no model provider and no disposition")}
        if row is not None:
            entry["register"] = {key: row.get(key) for key in (
                "accounting_status", "migration_class", "final_disposition")}
        identities[name] = entry
    projected_pins: dict[tuple[str, str], str] = {}
    class_pins: set[tuple[str, str]] = set()
    for name, provision in routing.providers.items():
        mapping = provision.mapping
        if isinstance(mapping, KernelFileMapping):
            projected_pins.setdefault((mapping.file, mapping.declaration), provision.layer)
            class_pins.add((mapping.file, mapping.declaration))
        carrier = (provision.spec or {}).get("carrier") if isinstance(provision.spec, dict) else None
        if carrier:
            projected_pins.setdefault((carrier["file"], carrier["declaration"]), provision.layer)
    for carrier in successor["carriers"].values():
        projected_pins.setdefault((carrier["file"], carrier["declaration"]), "successor-contract")
    directory, internal, accounting_errors = load_kernel_internal(root)
    directory = directory or contract.governed_directory
    declarations, errors = kernel_accounting(
        _governed_declarations(root, directory), internal, projected_pins, class_pins,
        _feature_declarations(root), directory)
    accounting_errors.extend(errors)
    for value in declarations.values():
        if value["status"] == "projected":
            value["layer_digest"] = digests[value["layer"]]
    residual = sorted(n for n, v in identities.items() if v["status"] == "residual")
    if sorted(routing.residual) != [n for n in residual if n in routing.residual]:
        raise ValueError("coverage residual differs from the routing residual")
    residual_declarations = sorted(k for k, v in declarations.items() if v["status"] == "residual")
    refused = sorted(n for n, v in identities.items() if v["status"] == "refused")
    retired_names = sorted(n for n, v in identities.items() if v["status"] == "retired")
    report = {
        "schema": REPORT_SCHEMA,
        "mode": MODE,
        "routing_digest": mc._canonical_digest(routing.record()),
        "layer_digests": digests,
        "semantic_authority": contract.identity.to_dict(),
        "duplicates": list(routing.duplicates),
        "identities": identities,
        "kernel_declarations": declarations,
        "summary": {
            "register_rows": len(register),
            "identities": len(identities),
            "governed_declarations": len(declarations),
            "projected_identities": sum(v["status"] == "projected" for v in identities.values()),
            "refused": len(refused),
            "retired": len(retired_names),
            "residual_identities": len(residual),
            "residual_declarations": len(residual_declarations),
            "residual_empty": not residual and not residual_declarations,
        },
        "residual": residual,
        "refused": refused,
        "retired": retired_names,
        "residual_declarations": residual_declarations,
        "kernel_accounting_errors": accounting_errors,
    }
    return report


def baseline_from_report(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": BASELINE_SCHEMA,
        "mode": MODE,
        "note": ("Reviewed ratchet for the model-authority coverage gate. "
                 "Not revision-bound evidence; no binding block. Regenerate with "
                 "scripts/check_model_projection_coverage.py --write-baseline after "
                 "a reviewed projection change. Any residual identity or declaration "
                 "and any kernel-accounting error block regardless of this baseline "
                 "(O4 Wave C2); refused and retired list the identities answered only "
                 "with their disposition."),
        "routing_digest": report["routing_digest"],
        "layer_digests": dict(report["layer_digests"]),
        "refused": list(report["refused"]),
        "retired": list(report["retired"]),
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
    # Absolute (O4 Wave C2): never satisfiable by updating the baseline.
    for name in report["residual"]:
        errors.append(f"residual is blocking: {name!r} has no model-projected provider")
    for name in report["residual_declarations"]:
        errors.append(f"residual is blocking: governed declaration {name!r} is unclassified")
    errors.extend(report.get("kernel_accounting_errors") or ())
    for name in report["duplicates"]:
        errors.append(f"duplicate provider: {name}")
    if baseline.get("mode") != MODE:
        errors.append(f"baseline mode {baseline.get('mode')!r} is not {MODE!r}")
    for key in ("refused", "retired"):
        current, recorded = set(report[key]), set(baseline.get(key) or ())
        for name in sorted(current - recorded):
            errors.append(f"{key} drift: {name!r} is {key} but not in the baseline")
        for name in sorted(recorded - current):
            errors.append(f"{key} drift: baseline lists {name!r} as {key}; update the baseline")
    if report["routing_digest"] != baseline.get("routing_digest"):
        errors.append("routing digest differs from the baseline (provider set changed)")
    if dict(report["layer_digests"]) != dict(baseline.get("layer_digests") or {}):
        errors.append("projection layer digests differ from the baseline")
    return errors


def bundle_errors(report: Mapping[str, Any], bundle: Mapping[str, Any], root: Path = ROOT) -> list[str]:
    """A bundle must bind exactly the checkout's routing, layers and authority."""
    components = (bundle or {}).get("components") or {}
    errors = []
    if mc._canonical_digest(components.get("routing")) != report["routing_digest"]:
        errors.append("bundle routing digest differs from the checkout")
    recorded = _layer_digests(list(components.get("layers") or ()))
    current = {k: v for k, v in report["layer_digests"].items() if k != "successor-contract"}
    if recorded != current:
        errors.append("bundle layer digests differ from the checkout")
    if (components.get("successor_contract") or {}).get("id") != report["layer_digests"]["successor-contract"]:
        errors.append("bundle successor contract differs from the checkout")
    if components.get("semantic_authority") != report["semantic_authority"]:
        errors.append("bundle semantic authority differs from the checkout")
    return errors


def run_check_errors(root: Path = ROOT) -> list[str]:
    try:
        report = build_report(root)
        baseline = load_baseline(root)
    except Exception as exc:  # a gate that cannot evaluate fails
        return [f"model-projection coverage cannot be evaluated: {exc}"]
    return compare(report, baseline)


def render_baseline(baseline: Mapping[str, Any]) -> str:
    header = ("# Model-authority coverage baseline (ratchet; any residual blocking; "
              "no binding block).\n")
    return header + yaml.safe_dump(dict(baseline), sort_keys=False, width=100)


def report_digest(report: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(report).encode()).hexdigest()


__all__ = ["build_report", "compare", "bundle_errors", "run_check_errors", "load_baseline",
           "baseline_from_report", "render_baseline", "report_digest", "BASELINE_PATH",
           "KERNEL_INTERNAL_PATH", "kernel_accounting", "load_kernel_internal"]
