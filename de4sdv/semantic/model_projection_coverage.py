"""Model-projection coverage gate (O4 Wave B ratchet; Wave C1 blocking retained residual).

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
- every governed kernel declaration: projected by a model-generated layer, or
  listed in the kernel-internal declarations manifest with a reason (owner
  decision D3, ``docs/method-conformance/o4/kernel-internal-declarations.yaml``).

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

It also fails, regardless of the baseline (O4 Wave C1, mode
``blocking-retained``), on:

- a non-empty ``retained_residual`` (the owner's criterion);
- any kernel-accounting error: an unclassified governed declaration, a stale
  or reason-less manifest entry, a manifest entry outside the governed
  directory or also projected, a feature slice re-declaring a projected kernel
  name, or a manifest that differs from the authored ontology list (the C1
  transition lock; Wave C2 deletes the authored list and the lock).

These kernel-accounting checks replace the kernel -> ontology direction and
the feature-slice guard of ``scripts/check_model_sync.py`` sync point 5.

The two owner-visible exceptions stay ratcheted (reported and allowed) until
Wave C2. The baseline carries no binding block; it is a reviewed ratchet
record, not revision-bound evidence.
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
REPORT_SCHEMA = "de4sdv.model-projection-coverage/v2"
BASELINE_SCHEMA = "de4sdv.model-authority-coverage-baseline/v2"
ONTOLOGY_PATH = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
KERNEL_INTERNAL_PATH = "docs/method-conformance/o4/kernel-internal-declarations.yaml"
KERNEL_INTERNAL_SCHEMA = "de4sdv.kernel-internal-declarations/v1"
FEATURES_DIRECTORY = "textual-notation-of-model/packages/features"
MODE = "blocking-retained"


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
    authored_pins: Mapping[tuple[str, str], str],
    feature_declarations: list[tuple[str, str]],
    directory: str,
) -> tuple[dict[str, Any], list[str]]:
    """Classify every governed declaration and return the accounting errors.

    The equation: governed declarations = projected declarations + listed
    kernel-internal declarations (each with a reason). ``authored_pins`` are
    the authored ontology's file mappings: until O4 Wave C2 a declaration
    pinned only there is a ratcheted residual, never ``unclassified``.
    ``class_pins`` are the model-projected class mappings (a subset of
    ``projected``, which also holds relationship-carrier pins). A listed
    kernel-internal declaration must not also be a class mapping; a carrier
    pin may also be listed (a carrier is not ontology class vocabulary).
    Class-mapped kernel names (in the governed directory) may be specialized
    or imported by feature slices but never re-declared there.
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
        elif (file, declaration) in authored_pins:
            declarations[key] = {"status": "residual", "reason":
                                 f"mapped only by authored ontology YAML ({authored_pins[(file, declaration)]})"}
        else:
            declarations[key] = {"status": "residual", "reason": "unclassified governed declaration"}
            errors.append(
                f"kernel accounting: {file}: declaration '{declaration}' is unclassified; "
                f"project it through a model-generated layer or list it in "
                f"{KERNEL_INTERNAL_PATH} with a reason")
    for file, declaration in sorted(set(listed) - governed_set):
        errors.append(f"kernel accounting: {file}: listed kernel-internal declaration "
                      f"'{declaration}' does not exist (stale entry?)")
    for file, declaration in sorted(set(listed) & set(class_pins)):
        errors.append(f"kernel accounting: {file}: declaration '{declaration}' is both projected "
                      f"and listed as kernel-internal")
    for file, declaration in sorted(set(listed) & set(authored_pins)):
        errors.append(f"kernel accounting: {file}: declaration '{declaration}' is both "
                      f"ontology-mapped and listed as kernel-internal")
    protected = {declaration.split()[-1] for (file, declaration) in
                 set(class_pins) | set(authored_pins) if _is_within(file, directory)}
    for file, declaration in feature_declarations:
        name = declaration.split()[-1]
        if name in protected:
            errors.append(f"kernel accounting: {file}: feature slice re-declares projected kernel "
                          f"name '{name}'; specialize or import the kernel declaration instead")
    return declarations, errors


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
    class_pins: set[tuple[str, str]] = set()  # model-projected class mappings
    for name, provision in routing.providers.items():
        mapping = provision.mapping
        if provision.layer == "o3":
            continue
        if isinstance(mapping, KernelFileMapping):
            projected_pins.setdefault((mapping.file, mapping.declaration), provision.layer)
            class_pins.add((mapping.file, mapping.declaration))
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
            class_pins.add((pin["source_file"], pin["declaration"]))
    yaml_pins = {}
    for name, spec in legacy.classes.items():
        kernel = (spec or {}).get("kernel") or {}
        if isinstance(kernel.get("file"), str) and isinstance(kernel.get("declaration"), str):
            yaml_pins[(kernel["file"], kernel["declaration"])] = name
    directory, internal, accounting_errors = load_kernel_internal(root)
    # C1 transition lock (removed with the authored list in Wave C2): the
    # manifest is the gate's source, and must not drift from the authored list.
    authored = {file: {" ".join(d.split()): r for d, r in (entries or {}).items()}
                for file, entries in (legacy.exclusions or {}).items()}
    if directory != legacy.governed_directory or internal != authored:
        accounting_errors.append(
            f"kernel accounting: {KERNEL_INTERNAL_PATH} differs from the authored ontology "
            "list of kernel-internal declarations (keep both equal until O4 Wave C2 retires "
            "the authored list)")
    directory = directory or legacy.governed_directory
    declarations, errors = kernel_accounting(
        _governed_declarations(root, directory), internal, projected_pins, class_pins,
        yaml_pins, _feature_declarations(root), directory)
    accounting_errors.extend(errors)
    for value in declarations.values():
        if value["status"] == "projected":
            value["layer_digest"] = digests[value["layer"]]
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
                 "a reviewed projection change. residual equals the runtime routing "
                 "residual; exceptions are the owner-visible registered non-retained "
                 "rows still served from the authored YAML (ratcheted until O4 Wave "
                 "C2). Since O4 Wave C1 a non-empty retained_residual and any "
                 "kernel-accounting error block regardless of this baseline."),
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
    # Absolute (O4 Wave C1): never satisfiable by updating the baseline.
    for name in report["retained_residual"]:
        errors.append(f"retained residual is blocking: {name!r} is a retained register row "
                      "without a model-projected provider")
    errors.extend(report.get("kernel_accounting_errors") or ())
    if baseline.get("mode") != MODE:
        errors.append(f"baseline mode {baseline.get('mode')!r} is not {MODE!r}")
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
    header = ("# Model-authority coverage baseline (ratchet; retained residual blocking; "
              "no binding block).\n")
    return header + yaml.safe_dump(dict(baseline), sort_keys=False, width=100)


def report_digest(report: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(report).encode()).hexdigest()


__all__ = ["build_report", "compare", "bundle_errors", "run_check_errors", "load_baseline",
           "baseline_from_report", "render_baseline", "report_digest", "BASELINE_PATH",
           "KERNEL_INTERNAL_PATH", "kernel_accounting", "load_kernel_internal"]
