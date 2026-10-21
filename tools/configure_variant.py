#!/usr/bin/env python3
"""
DE4SDV variant configurator: the product-model projection writer.

The PLEML feature models and feature configurations are the product-line
authority (ADR 0022). The DE4SDV evaluator
(de4sdv/semantic/pleml_configuration.py) decides each configuration, and the
licensed authority job records its verdicts, derived variants and admission
in the committed receipts (feature-models/receipts/). The configurator replays
one receipt offline and writes the SysML v2 product-model projection of one
valid configuration with its writer. It decides nothing itself.

How the components of a product-line factory map to the repository:

  Feature model             → feature-models/*.sysml (PLEML)
  Feature configuration     → feature-configurations/*.sysml (PLEML)
  Evaluation and receipts   → de4sdv/semantic/pleml_configuration.py,
                              feature-models/receipts/
  Configurator (this script) → tools/configure_variant.py
  Product asset instance    → product-models/*.sysml (generated projection)

The shared asset superset (150% model) lives under
textual-notation-of-model/packages/architecture/ as native SysML v2
variation/variant notation. Each feature model's projection metadata
identifies its package and owning part definition.

Usage:
  python tools/configure_variant.py \\
    --receipt model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json \\
    --configuration aebsAutowareLinuxLidarCamera --output <output>.sysml

  # Check a configuration without generating (offline replay, no licence):
  python tools/configure_variant.py --receipt ... --configuration ... --check-only

The configuration is named by its declared name, its projection name or its
source document. Variation and variant identity come from the receipt, and
the selections outside the projection are labelled by their PLEML feature
paths. The committed projections are this writer's output.

The configurator projects only a configuration of the served model, whose
document the export reads (``de4sdv/sysml_api/baseline.py``). The receipts
also evaluate the fixtures under ``feature-configurations/fixtures/``, the
invalid configuration and the probes: the configurator refuses to project
one (exit 2), and ``--check-only`` reports its verdict. A new configuration
needs licensed serialization first: the authority job writes its receipt.

Exit codes:
  0 — configuration valid (and optionally generated)
  1 — configuration invalid in its receipt
  2 — input or read error, or a receipt that does not hold
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


# ──────────────────────────────────────────────────────────────
# Provenance helpers
# ──────────────────────────────────────────────────────────────

def sysml_comment_text(value):
    """Escape data embedded in SysML block comments."""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "?", text)
    return text.replace("/*", "/ *").replace("*/", "* /")


def file_sha256(path):
    """Return a content hash suitable for derived-artifact provenance."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance_path(path):
    """Render repository inputs consistently regardless of caller directory."""
    resolved = Path(path).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return str(resolved)


def shared_asset_baseline(path):
    """Return a history-independent content identity for a shared asset."""
    resolved = Path(path).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    try:
        relative = resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return f"external:{resolved} (content hash authoritative)"

    try:
        blob_id = subprocess.check_output(
            ["git", "-C", str(repo_root), "hash-object", "--stdin"],
            input=resolved.read_bytes(),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return f"content-only:{relative} (SHA-256 authoritative)"

    return f"git-blob:{blob_id}:{relative} (content-addressed)"


# ──────────────────────────────────────────────────────────────
# The writer
# ──────────────────────────────────────────────────────────────

def render_projection(name, description, projection, redefinitions,
                      derived_ids_by_part, capability_annotations, provenance,
                      source):
    """The writer: render one derived product-model projection.

    ``provenance`` holds the header lines below the title, and ``source``
    names what decided the selection in the derivation-source line of the
    doc.
    """
    package_name = projection["package"]
    owner_name = projection["owner"]
    projection_label = projection["label"]
    desc_clean = ""
    if description:
        desc_clean = sysml_comment_text(description.strip()).replace(
            "\n", "\n   * "
        )

    lines = [
        "/*",
        f" * Derived {sysml_comment_text(projection_label)} product-model projection — DO NOT EDIT.",
        *(f" * {line}" for line in provenance),
        " */",
        "",
        f"private import {package_name}::{owner_name};",
        "",
        f"part def {name} :> {owner_name} {{",
        "  doc /*",
        f"   * Derived {sysml_comment_text(projection_label)} projection from {sysml_comment_text(source)}.",
    ]

    if desc_clean:
        lines.append(f"   * {desc_clean}")
    lines.append("   *")
    lines.append("   * Variant selections:")
    for part_name, variant_name in redefinitions:
        derivation_suffix = ""
        if part_name in derived_ids_by_part:
            derivation_suffix = (
                " (derived by "
                f"{sysml_comment_text(derived_ids_by_part[part_name])})"
            )
        lines.append(
            f"   *   {sysml_comment_text(part_name)} = "
            f"{sysml_comment_text(variant_name)}{derivation_suffix}"
        )

    if capability_annotations:
        lines.append("   *")
        lines.append("   * Feature selections outside this projection (not resolved in SysML):")
        for path, status in capability_annotations:
            lines.append(
                f"   *   {sysml_comment_text(path)} = "
                f"{sysml_comment_text(status)}"
            )

    lines.append("   */")
    lines.append("")

    # Emit spec-correct variant selection. Per OMG SysML v2 §7.6.7 and the
    # reference implementation (Systems-Modeling/SysML-v2-Release,
    # examples/Variability Examples/VehicleVariabilityModel.sysml, "100% Model"),
    # a configured product selects a variant by subsetting the inherited
    # variation-point feature and assigning the variant via the
    # variation::variant qualified path:
    #
    #     part :>> vehicleApplication = vehicleApplication::autoware;
    #
    # `redefines <variantName>` is incorrect: variants are nested subset usages
    # of the variation, not features of the owning definition, so they cannot be
    # redefinition targets. See ADR 0006 for the full rationale.
    for part_name, variant_name in redefinitions:
        lines.append(f"  part :>> {part_name} = {part_name}::{variant_name};")

    lines.append("}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Receipts (ADR 0022)
# ──────────────────────────────────────────────────────────────

#: The evaluated states in which a feature is selected.
RECEIPT_SELECTED_STATES = {"enabled", "implied"}
#: What decided the selection, as the derivation-source line of a receipt projection names it.
RECEIPT_SOURCE = "PLEML configuration receipt"


def receipt_projection_content(model, configuration, writer):
    """Return what one valid configuration of a receipt states for its projection.

    The content is the bound variants in the tree order of their groups, the
    derived ones after them in the order of their derivations, each with its
    derivation's ID, and the selections outside the projection: unbound
    groups with their selected members, then the optional features the
    configuration sets explicitly. Each selection outside the projection is
    labelled by the PLEML feature path the receipt records, and a group's
    members by their feature names.
    """
    features = model["features"]
    order = {feature["path"]: index for index, feature in enumerate(features)}
    by_path = {feature["path"]: feature for feature in features}
    bindings = {item["binding"]: item for item in model["bindings"]}
    bound_features = {item["feature"] for item in model["bindings"]}
    states = configuration["states"]

    bound, derived = [], []
    for item in configuration["derived_variants"]:
        if "binding" in item:
            feature = by_path[bindings[item["binding"]]["feature"]]
            bound.append(((order[feature["group"] or feature["path"]], order[feature["path"]]), item))
        else:
            derived.append(item)
    derivation_order = {
        item["short_name"] or item["derivation"] or item["element_id"]: index
        for index, item in enumerate(model["derivations"])
    }
    derived.sort(key=lambda item: derivation_order[item["derivation"]])
    redefinitions = [(item["variation"], item["variant"])
                     for _key, item in sorted(bound, key=lambda entry: entry[0])]
    redefinitions += [(item["variation"], item["variant"]) for item in derived]
    derived_ids_by_part = {item["variation"]: item["derivation"] for item in derived}

    capability_annotations = []
    for feature in features:
        members = feature["members"]
        if (not members or set(members) & bound_features
                or states.get(feature["path"]) not in RECEIPT_SELECTED_STATES):
            continue
        chosen = [by_path[member]["name"] for member in members
                  if states.get(member) in RECEIPT_SELECTED_STATES]
        if chosen:
            capability_annotations.append((feature["path"], ", ".join(chosen)))
    explicit = writer["explicit_optional_states"]
    for feature in features:
        if feature["path"] in explicit:
            capability_annotations.append((feature["path"], explicit[feature["path"]]))
    return redefinitions, derived_ids_by_part, capability_annotations


def receipt_shared_assets(model, element_sources):
    """Return the one shared-assets model holding every variant a feature model binds or derives."""
    variants = [item["variant_id"] for item in model["bindings"]]
    variants += [item["derived_variation_id"] for item in model["derivations"]]
    documents = {element_sources.get(item) for item in variants}
    if len(documents) != 1 or None in documents:
        raise ValueError(
            f"the feature model {model['feature_model']} binds variants in "
            f"{sorted(map(str, documents))}, not in one shared-assets model"
        )
    return documents.pop()


def load_receipt_configuration(receipt_path, name, root=REPO_ROOT):
    """Replay a receipt offline and return one of its configurations with what the writer reads.

    Returns ``(receipt, model, configuration, writer, shared_assets)``. The
    configuration is named by its declared name, its projection name or its
    source document. A receipt whose inputs changed, whose evaluation does
    not reproduce, or that records integrity errors is refused, with the
    evaluator's own replay. The writer inputs are read from the evaluated
    configuration.
    """
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from de4sdv.semantic import pleml_receipts

    receipt_path = Path(receipt_path)
    failures = pleml_receipts.replay_receipts([receipt_path], Path(root))
    if failures:
        raise ValueError("the receipt does not hold: " + "; ".join(failures))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    found = [
        (model, configuration)
        for model in receipt["evaluation"]["feature_models"]
        for configuration in model["configurations"]
        if name in (configuration["configuration"], configuration["projection_name"],
                    configuration["source"])
    ]
    if len(found) != 1:
        raise ValueError(f"the receipt holds {len(found)} configurations named '{name}'")
    model, configuration = found[0]
    writer = pleml_receipts.writer_inputs(configuration, model["features"])
    payload = pleml_receipts.read_elements(receipt_path.parent / receipt["elements"]["path"])
    shared_assets = receipt_shared_assets(model, payload["element_sources"])
    return receipt, model, configuration, writer, shared_assets


def served_configuration(configuration, root=REPO_ROOT):
    """Whether the configurator may project this configuration of a receipt.

    Only a configuration of the served model may be projected: its source
    document is one the export reads. The fixtures the receipts evaluate (the
    invalid configuration and the probes) are not.
    """
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from de4sdv.sysml_api.baseline import reviewed_source

    return reviewed_source(configuration["source"])


def receipt_projection(receipt_path, receipt, model, configuration, writer,
                       shared_assets, root=REPO_ROOT):
    """Render the projection of one valid configuration of a receipt that holds, with the writer.

    The command line writes it for a configuration of the served model only
    (``served_configuration``).
    """
    name = configuration["projection_name"]
    if not configuration["valid"]:
        raise ValueError(f"'{configuration['configuration']}' is not valid in its receipt")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w*", name):
        raise ValueError(f"'{configuration['configuration']}' records no projection name")
    redefinitions, derived_ids_by_part, capability_annotations = (
        receipt_projection_content(model, configuration, writer)
    )
    digests = {item["path"]: item["sha256"] for item in receipt["sources"]}
    receipt_path = Path(receipt_path)
    provenance = [
        "Generated by configure_variant.py from a PLEML configuration receipt.",
        "This is not a complete member-product specification.",
        "Shared-assets source baseline: "
        f"{sysml_comment_text(shared_asset_baseline(Path(root) / shared_assets))}",
        f"Shared-assets model: {sysml_comment_text(shared_assets)}",
        f"Shared-assets model SHA-256: {digests[shared_assets]}",
        f"Receipt: {sysml_comment_text(provenance_path(receipt_path))}",
        f"Receipt SHA-256: {file_sha256(receipt_path)}",
        f"Elements SHA-256: {receipt['elements']['sha256']}",
        f"Feature configuration: {sysml_comment_text(configuration['source'])} "
        f"({sysml_comment_text(configuration['configuration'])})",
        f"Feature configuration SHA-256: {digests[configuration['source']]}",
        f"PLEML feature model: {sysml_comment_text(model['tree']['source'])}",
        f"PLEML feature model SHA-256: {digests[model['tree']['source']]}",
    ]
    return render_projection(
        name, writer["description"], model["projection"], redefinitions,
        derived_ids_by_part, capability_annotations, provenance, RECEIPT_SOURCE,
    )


def projection_file(text):
    """Return the content of a projection file, as the configurator writes it."""
    return text + "\n"


def write_projection(output, text):
    """Write a generated projection to ``output``, or to stdout without one."""
    if output:
        output_path = Path(output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(projection_file(text))
        except OSError as exc:
            sys.stderr.write(f"Error writing output: {exc}\n")
            sys.exit(2)
        sys.stderr.write(f"✓ Generated {output_path}\n")
    else:
        print(text)


def main_receipt(args):
    """Replay the receipt, then project one of its valid configurations."""
    receipt_path = Path(args.receipt)
    try:
        receipt, model, configuration, writer, shared_assets = (
            load_receipt_configuration(receipt_path, args.configuration)
        )
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        sys.stderr.write(f"Error reading input: {exc}\n")
        sys.exit(2)

    if not args.check_only and not served_configuration(configuration):
        sys.stderr.write(
            f"Error: '{configuration['configuration']}' is a fixture of the receipt "
            f"({configuration['source']}), not a configuration of the served model: "
            "the configurator projects only a configuration whose document the export "
            "reads; --check-only reports a fixture's verdict\n"
        )
        sys.exit(2)

    if not configuration["valid"]:
        reasons = configuration["reasons"]
        sys.stderr.write(
            f"\n✗ Configuration INVALID — {len(reasons)} "
            f"violation(s) in the receipt:\n\n"
        )
        for reason in reasons:
            sys.stderr.write(f"  • {reason['detail']}\n")
        sys.stderr.write("\n")
        sys.exit(1)

    sys.stderr.write(
        "✓ Configuration valid — the receipt replays and records no violation.\n"
    )
    if args.check_only:
        return
    try:
        text = receipt_projection(receipt_path, receipt, model, configuration,
                                  writer, shared_assets)
    except (OSError, ValueError, KeyError) as exc:
        sys.stderr.write(f"Error reading input: {exc}\n")
        sys.exit(2)
    write_projection(args.output, text)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Project one configuration of a committed PLEML configuration "
                    "receipt as a SysML v2 product-model projection"
    )
    parser.add_argument(
        "--receipt", required=True,
        help="a committed PLEML configuration receipt"
    )
    parser.add_argument(
        "--configuration", required=True,
        help="the configuration's declared name, projection name or source document"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output .sysml path (default: stdout)"
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Report the configuration's verdict without generating"
    )
    main_receipt(parser.parse_args())


if __name__ == "__main__":
    main()
