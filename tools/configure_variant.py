#!/usr/bin/env python3
"""
DE4SDV variant configurator.

Reads a Bill-of-Features (YAML) and validates it against the feature model
(YAML), then generates a SysML v2 part def that resolves variant selections.

The configurator implements three of the four ISO/IEC 26580 PLE Factory
components in a lightweight, in-repo way:

  Feature Catalogue         → feature-models/*.yaml
  Bill-of-Features          → feature-configurations/*.yaml
  Configurator (this script) → tools/configure_variant.py
  Product Asset Instance    → product-models/*.sysml (generated)

The fourth component — the Shared Asset Superset (150% model) — lives
in textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml
as native SysML v2 variation/variant notation.

Selection semantics:
  - Alternative groups:  assign the child name as value
    e.g. PlatformStack.Middleware: EclipseSCORE
  - Optional features:   assign true or false
    e.g. Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  - Mandatory features:  may be explicit (true) or implicit (assumed selected)

Usage:
  python tools/configure_variant.py \\
    --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \\
    --bof model-based-product-line-engineering/feature-configurations/<config>.yaml \\
    --output model-based-product-line-engineering/product-models/<output>.sysml

  # Validate without generating:
  python tools/configure_variant.py \\
    --feature-model ... --bof ... --check-only

Exit codes:
  0 — configuration valid (and optionally generated)
  1 — configuration invalid (constraint or structural violation)
  2 — internal error (file not found, parse error, etc.)
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "Error: PyYAML is required. Install with: pip install pyyaml\n"
    )
    sys.exit(2)


# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────

class FeatureNode:
    """A node in the feature tree."""

    def __init__(self, name, ftype, description="", maps_to=None,
                 maps_to_variant=None, parent=None):
        self.name = name
        self.type = ftype  # mandatory, optional, alternative, or_group
        self.description = description
        self.maps_to = maps_to
        self.maps_to_variant = maps_to_variant
        self.parent = parent
        self.children = []
        self.path = ""  # dotted path from root's first child level

    def is_leaf(self):
        return len(self.children) == 0

    def is_variant_leaf(self):
        """A leaf with maps_to_variant — these become SysML redefinitions."""
        return self.is_leaf() and self.maps_to_variant is not None

    def is_selection_group(self):
        """An alternative or or_group node whose children are variant leaves."""
        if self.type not in ("alternative", "or_group"):
            return False
        return all(c.is_variant_leaf() for c in self.children)

    def __repr__(self):
        return f"FeatureNode({self.path!r}, type={self.type})"


# ──────────────────────────────────────────────────────────────
# Feature tree parsing
# ──────────────────────────────────────────────────────────────

def build_feature_tree(feature_model_data):
    """
    Parse the feature model YAML into a FeatureNode tree.
    Returns (root_node, constraints_list).

    Paths are built WITHOUT the root name — so a feature under
    root → PlatformStack → Middleware → EclipseSCORE has path
    'PlatformStack.Middleware.EclipseSCORE'.
    """
    root_data = feature_model_data["root"]
    constraints = feature_model_data.get("constraints", [])

    def build_node(data, parent=None, path_prefix=""):
        name = data["name"]
        ftype = data.get("type", "optional")
        description = data.get("description", "")
        maps_to = data.get("maps_to")
        maps_to_variant = data.get("maps_to_variant")

        node = FeatureNode(
            name=name, ftype=ftype, description=description,
            maps_to=maps_to, maps_to_variant=maps_to_variant,
            parent=parent
        )
        # Root gets empty path; first level gets just the name
        node.path = f"{path_prefix}.{name}" if path_prefix else name

        for child_data in data.get("children", []):
            child = build_node(child_data, parent=node, path_prefix=node.path)
            node.children.append(child)

        return node

    # Build root with empty path prefix so its children start at level 0
    root = build_node(root_data)
    # Override: root path is empty so children's paths start clean
    root.path = ""
    # Rebuild children paths without root prefix
    for child in root.children:
        _fix_paths(child, "")

    return root, constraints


def _fix_paths(node, prefix):
    """Set node.path without the root name."""
    node.path = f"{prefix}.{node.name}" if prefix else node.name
    for child in node.children:
        _fix_paths(child, node.path)


def collect_all_nodes(root):
    """Collect all nodes (except root) as a dict keyed by path."""
    nodes = {}

    def walk(node):
        if node.path:  # skip root
            nodes[node.path] = node
        for child in node.children:
            walk(child)

    walk(root)
    return nodes


def collect_variant_leaves(root):
    """Collect all leaf nodes that have maps_to_variant."""
    leaves = []

    def walk(node):
        if node.is_variant_leaf():
            leaves.append(node)
        for child in node.children:
            walk(child)

    walk(root)
    return leaves


def find_alternative_groups(root):
    """Find all nodes of type 'alternative' or 'or_group'."""
    groups = []

    def walk(node):
        if node.type in ("alternative", "or_group"):
            groups.append(node)
        for child in node.children:
            walk(child)

    walk(root)
    return groups


def find_mandatory_leaves(root):
    """Collect all leaf nodes that are transitively mandatory."""
    leaves = []

    def walk(node, parent_mandatory):
        is_mandatory = parent_mandatory and node.type == "mandatory"
        if node.is_leaf() and is_mandatory:
            leaves.append(node)
        for child in node.children:
            walk(child, is_mandatory)

    walk(root, True)
    return leaves


def is_transitively_mandatory(node):
    """
    Check if a node is transitively mandatory — meaning every ancestor
    between it and the root is mandatory (type == 'mandatory').
    The node's own type doesn't matter; what matters is whether the
    chain of ancestors forces selection.
    """
    current = node.parent
    while current is not None:
        if current.parent is None:
            # current is root — root is always selected
            break
        if current.type != "mandatory":
            return False
        current = current.parent
    return True


# ──────────────────────────────────────────────────────────────
# Bill-of-Features parsing
# ──────────────────────────────────────────────────────────────

def parse_bof(bof_data):
    """
    Parse the Bill-of-Features YAML.
    Returns (name, description, selections_dict).
    """
    name = bof_data["name"]
    description = bof_data.get("description", "")
    selections = bof_data.get("selections", {})
    return name, description, selections


# ──────────────────────────────────────────────────────────────
# Validation
# ──────────────────────────────────────────────────────────────

def validate_structure(root, all_nodes, selections):
    """
    Pass 1: Structural validation against the feature tree.
    """
    errors = []

    # Build a set of valid selection keys:
    # - Leaf nodes: their own path (boolean selection)
    # - Alternative/or_group nodes with variant leaves: their own path (value = child name)
    valid_selection_keys = set()
    for path, node in all_nodes.items():
        if node.is_leaf():
            valid_selection_keys.add(path)
        elif node.is_selection_group():
            valid_selection_keys.add(path)

    # Check: every selection key references a valid path
    for sel_key in selections:
        if sel_key not in valid_selection_keys:
            # Is it a non-leaf non-group node? Then it's a wrong selection level.
            if sel_key in all_nodes:
                node = all_nodes[sel_key]
                errors.append(
                    f"'{sel_key}' is a {node.type} group node with non-variant "
                    f"children — cannot select directly. Select its children."
                )
            else:
                errors.append(
                    f"Unknown feature path in selections: '{sel_key}'"
                )

    # Check: every alternative group has exactly one child selected
    for group in find_alternative_groups(root):
        if not group.is_selection_group():
            # Non-variant-leaf alternative group — check sub-selections
            continue

        selected = selections.get(group.path)
        if selected is not None and selected is not False:
            # Verify the selected value is a valid child
            child_names = [c.name for c in group.children]
            if selected not in child_names:
                errors.append(
                    f"'{group.path}': '{selected}' is not a valid choice. "
                    f"Valid: {child_names}"
                )

        # Mandatory alternative must have a selection
        if is_transitively_mandatory(group):
            if selected is None or selected is False:
                errors.append(
                    f"Mandatory alternative group '{group.path}' "
                    f"has no selection"
                )

    # Check: every transitively-mandatory leaf is selected
    for leaf in find_mandatory_leaves(root):
        sel = selections.get(leaf.path)
        if sel is None or sel is False:
            errors.append(
                f"Mandatory feature not selected: '{leaf.path}'"
            )

    return errors


def evaluate_condition(condition_str, selections):
    """
    Evaluate a constraint condition/target string against the selections.
    Returns True if matched/satisfied.

    Supported syntax:
      Path.To.Feature == Value     → True if selection equals Value
      Path.To.Feature != Value     → True if selection differs from Value
      Path.To.Feature              → True if feature is selected (truthy)
      Path.To.Feature in [A, B, C] → True if selection is in the list
    """
    condition_str = condition_str.strip()

    # Path in [A, B, C]
    m = re.match(r'^(.+?)\s+in\s+\[(.+?)\]$', condition_str)
    if m:
        path = m.group(1).strip()
        values = [v.strip() for v in m.group(2).split(",")]
        sel = selections.get(path)
        return sel in values

    # Path == Value
    m = re.match(r'^(.+?)\s+==\s*(.+)$', condition_str)
    if m:
        path = m.group(1).strip()
        value = m.group(2).strip()
        sel = selections.get(path)
        return str(sel) == value

    # Path != Value
    m = re.match(r'^(.+?)\s+!=\s*(.+)$', condition_str)
    if m:
        path = m.group(1).strip()
        value = m.group(2).strip()
        sel = selections.get(path)
        return str(sel) != value

    # Bare path (boolean feature)
    sel = selections.get(condition_str)
    return bool(sel) if sel is not None else False


def validate_constraints(constraints, selections):
    """
    Pass 2: Constraint validation.
    Returns list of error strings (empty if valid).
    """
    errors = []

    for constraint in constraints:
        cid = constraint.get("id", "???")
        ctype = constraint["type"]
        condition = constraint["if"]
        target = constraint["then"]
        rationale = constraint.get("rationale", "")

        cond_met = evaluate_condition(condition, selections)
        if not cond_met:
            continue  # constraint not active

        target_met = evaluate_condition(target, selections)

        if ctype == "requires":
            if not target_met:
                errors.append(
                    f"[{cid}] requires: '{target}' is not satisfied "
                    f"when '{condition}' holds. {rationale}"
                )
        elif ctype == "excludes":
            if target_met:
                errors.append(
                    f"[{cid}] excludes: '{target}' would be satisfied "
                    f"when '{condition}' holds. {rationale}"
                )

    return errors


# ──────────────────────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────────────────────

def generate_sysml(bof_name, bof_description, root, all_nodes, selections,
                   feature_model_path, bof_path):
    """
    Pass 3: Generate SysML v2 part def with variant redefinitions.
    """
    redefinitions = []
    capability_annotations = []

    for path, node in all_nodes.items():
        # Variant leaf under a selection group: emit redefinition if selected
        if node.is_variant_leaf():
            parent_group = node.parent
            if parent_group and parent_group.is_selection_group():
                selected = selections.get(parent_group.path)
                if selected == node.name:
                    part_name = parent_group.maps_to.split(".")[-1]
                    redefinitions.append((part_name, node.maps_to_variant))

        # Optional boolean leaf: capability annotation
        elif (node.is_leaf() and node.type == "optional" and
              not node.maps_to_variant):
            sel = selections.get(node.path)
            if sel is not None:
                status = "enabled" if sel else "disabled"
                capability_annotations.append((node.path, status))

    # Build SysML output
    desc_clean = ""
    if bof_description:
        desc_clean = bof_description.strip().replace("\n", "\n   * ")

    lines = [
        "/*",
        " * Generated by configure_variant.py — DO NOT EDIT.",
        f" * Regenerate from: {bof_path}",
        f" * Feature model:  {feature_model_path}",
        " */",
        "",
        "private import DE4SDV_SDVPlatformStack::SDVPlatformStack;",
        "",
        f"part def {bof_name} :> SDVPlatformStack {{",
        "  doc /*",
        "   * Configured member product generated from Bill-of-Features.",
    ]

    if desc_clean:
        lines.append(f"   * {desc_clean}")
    lines.append("   *")
    lines.append("   * Variant selections:")
    for part_name, variant_name in redefinitions:
        lines.append(f"   *   {part_name} = {variant_name}")

    if capability_annotations:
        lines.append("   *")
        lines.append("   * Capability selections:")
        for path, status in capability_annotations:
            lines.append(f"   *   {path} = {status}")

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
    # redefinition targets. See ADR 0011 for the full rationale.
    for part_name, variant_name in redefinitions:
        lines.append(f"  part :>> {part_name} = {part_name}::{variant_name};")

    lines.append("}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Configure an SDV variant from a Bill-of-Features"
    )
    parser.add_argument(
        "--feature-model", required=True,
        help="Path to feature model YAML"
    )
    parser.add_argument(
        "--bof", required=True,
        help="Path to Bill-of-Features YAML"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output .sysml path (default: stdout)"
    )
    parser.add_argument(
        "--check-only", action="store_true",
        help="Validate without generating"
    )

    args = parser.parse_args()

    # Load files
    try:
        with open(args.feature_model) as f:
            feature_model_data = yaml.safe_load(f)
        with open(args.bof) as f:
            bof_data = yaml.safe_load(f)
    except FileNotFoundError as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(2)
    except yaml.YAMLError as e:
        sys.stderr.write(f"Error parsing YAML: {e}\n")
        sys.exit(2)

    # Build feature tree
    root, constraints = build_feature_tree(feature_model_data)
    all_nodes = collect_all_nodes(root)
    bof_name, bof_description, selections = parse_bof(bof_data)

    # Pass 1: Structural validation
    structural_errors = validate_structure(root, all_nodes, selections)
    # Pass 2: Constraint validation
    constraint_errors = validate_constraints(constraints, selections)

    all_errors = structural_errors + constraint_errors

    if all_errors:
        sys.stderr.write(
            f"\n\u2717 Configuration INVALID \u2014 {len(all_errors)} "
            f"violation(s):\n\n"
        )
        for err in all_errors:
            sys.stderr.write(f"  \u2022 {err}\n")
        sys.stderr.write("\n")
        sys.exit(1)

    sys.stderr.write(
        "\u2713 Configuration valid \u2014 all constraints satisfied.\n"
    )

    if args.check_only:
        return

    # Pass 3: Generate
    sysml_output = generate_sysml(
        bof_name, bof_description, root, all_nodes, selections,
        args.feature_model, args.bof
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(sysml_output + "\n")
        sys.stderr.write(f"\u2713 Generated {output_path}\n")
    else:
        print(sysml_output)


if __name__ == "__main__":
    main()
