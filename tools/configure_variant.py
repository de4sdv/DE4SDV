#!/usr/bin/env python3
"""
DE4SDV variant configurator.

Since the switch of ADR 0022 (step S6) the PLEML feature models and
configurations are the product-line authority, and the configurator
generates every committed product-model projection from the evaluation
receipt of its configuration (receipt mode, below). Its YAML path is the
non-authoritative shadow until the YAML retires (step S7): the parity check
(scripts/check_pleml_parity.py) compares the two paths.

The YAML path reads a Bill-of-Features (YAML), validates it against the
feature catalogue (YAML), then generates a SysML v2 product-model projection
of the catalogue's declared shared-asset owner.
Selections without mapped variable shared assets are validated but not derived.
Assets declared under ``derived_asset_selections`` are resolved from their
source feature choices and cannot be selected independently in the BoF.

The configurator implements three of the four ISO/IEC 26580 PLE Factory
components in a lightweight, in-repo way:

  Feature Catalogue         → feature-models/*.yaml
  Bill-of-Features          → feature-configurations/*.yaml
  Configurator (this script) → tools/configure_variant.py
  Product Asset Instance    → product-models/*.sysml (generated projection)

The fourth component — the Shared Asset Superset (150% model) — lives under
textual-notation-of-model/packages/architecture/ as native SysML v2
variation/variant notation. Each catalogue's projection metadata identifies
its package and owning part definition.

Selection semantics:
  - Alternative groups: assign one child name as a scalar value
    e.g. PlatformStack.Middleware: EclipseSCORE
  - OR-groups: assign a non-empty list of child names
  - Optional/mandatory leaves: assign a YAML Boolean true or false
    e.g. Capabilities.ForwardCollisionMitigation.PedestrianDetection: false
  - A mandatory leaf whose ancestors below the catalogue root are all
    mandatory counts as selected when the BoF leaves it out, for the
    mandatory-leaf check and for the constraints alike; setting it to
    false is a violation.

Usage:
  python tools/configure_variant.py \\
    --feature-model model-based-product-line-engineering/feature-models/sdv_product_line.yaml \\
    --bof model-based-product-line-engineering/feature-configurations/<config>.yaml \\
    --output model-based-product-line-engineering/product-models/<output>.sysml

  # Validate without generating:
  python tools/configure_variant.py \\
    --feature-model ... --bof ... --check-only

Receipt mode (ADR 0022, plan steps S4 and S6), the authority path: the same
writer generates the projection of one evaluated configuration of a committed
PLEML receipt, after replaying the receipt offline, instead of deciding a
Bill-of-Features:

  python tools/configure_variant.py \\
    --receipt model-based-product-line-engineering/feature-models/receipts/sdv_product_line.receipt.json \\
    --configuration aebsAutowareLinuxLidarCamera --output <output>.sysml

The configuration is named by its declared name, its projection name or its
source document. Variation and variant identity come from the receipt; the
lexical mapping checks stay with the YAML path, which remains the oracle and
the shadow until S7. The committed projections are receipt mode's output
since the switch, and the parity check requires the YAML path's normalised
bodies to equal them.

Exit codes:
  0 — configuration valid (and optionally generated)
  1 — configuration invalid (constraint or structural violation)
  2 — input/read/parse/schema error, or a receipt that does not hold
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_STATUSES = {
    "draft", "planned", "inspected", "simulated", "analyzed",
    "tested", "accepted", "rejected", "gap",
}
EVIDENCE_BEARING_STATUSES = {
    "inspected", "simulated", "analyzed", "tested", "accepted", "rejected",
}

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "Error: PyYAML is required. Install with: pip install pyyaml\n"
    )
    sys.exit(2)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def construct_unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found an unhashable YAML key", key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate YAML key: {key!r}", key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def load_yaml_unique(stream):
    return yaml.load(stream, Loader=UniqueKeyLoader)


DEFAULT_PROJECTION = {
    "package": "DE4SDV_SDVPlatformStack",
    "owner": "SDVPlatformStack",
    "label": "platform-stack",
}


def projection_metadata(feature_data):
    """Return the declared shared-asset projection target with legacy defaults."""
    declared = feature_data.get("projection") or {}
    return {**DEFAULT_PROJECTION, **declared}


# ──────────────────────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────────────────────

class FeatureNode:
    """A node in the feature tree."""

    def __init__(self, name, ftype, description="", feature_id=None,
                 binding_time=None, maps_to=None, maps_to_variant=None,
                 parent=None):
        self.name = name
        self.type = ftype  # mandatory, optional, alternative, or_group
        self.description = description
        self.feature_id = feature_id
        self.binding_time = binding_time
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
        """An alternative/or_group whose direct children are selectable leaves."""
        if self.type not in ("alternative", "or_group"):
            return False
        return bool(self.children) and all(child.is_leaf() for child in self.children)

    def __repr__(self):
        return f"FeatureNode({self.path!r}, type={self.type})"


# ──────────────────────────────────────────────────────────────
# Feature tree parsing
# ──────────────────────────────────────────────────────────────

def validate_document_shapes(feature_data, bof_data):
    """Return schema errors that would otherwise make parsing ambiguous or crash."""
    errors = []
    if not isinstance(feature_data, dict):
        errors.append("feature model document must be a YAML mapping")
    if not isinstance(bof_data, dict):
        errors.append("Bill-of-Features document must be a YAML mapping")
    if errors:
        return errors

    root = feature_data.get("root")
    if not isinstance(root, dict):
        errors.append("feature model 'root' must be a YAML mapping")

    projection = feature_data.get("projection")
    if projection is not None:
        if not isinstance(projection, dict):
            errors.append("feature model 'projection' must be a YAML mapping")
        else:
            unknown = sorted(set(projection) - {"package", "owner", "label"})
            for field in unknown:
                errors.append(f"unknown projection field: '{field}'")
            for field in ("package", "owner"):
                value = projection.get(field)
                if not isinstance(value, str) or not re.fullmatch(
                    r"[A-Za-z_]\w*", value
                ):
                    errors.append(
                        f"projection.{field} must be a valid unquoted SysML identifier"
                    )
            label = projection.get("label")
            if not isinstance(label, str) or not label.strip():
                errors.append("projection.label must be a non-empty string")

    constraints = feature_data.get("constraints", [])
    if not isinstance(constraints, list):
        errors.append("feature model 'constraints' must be a YAML list")
    else:
        for index, constraint in enumerate(constraints):
            if not isinstance(constraint, dict):
                errors.append(f"constraint[{index}] must be a YAML mapping")
                continue
            for field in ("type", "if", "then"):
                if not isinstance(constraint.get(field), str):
                    errors.append(f"constraint[{index}].{field} must be a string")

    derived_assets = feature_data.get("derived_asset_selections", [])
    if not isinstance(derived_assets, list):
        errors.append(
            "feature model 'derived_asset_selections' must be a YAML list"
        )

    def check_node(node, path):
        if not isinstance(node, dict):
            errors.append(f"feature node '{path}' must be a YAML mapping")
            return
        if "name" not in node:
            errors.append(f"feature node '{path}' is missing 'name'")
        children = node.get("children", [])
        if not isinstance(children, list):
            errors.append(f"feature node '{path}.children' must be a YAML list")
            return
        for index, child in enumerate(children):
            check_node(child, f"{path}.children[{index}]")

    if isinstance(root, dict):
        check_node(root, "root")

    if "name" not in bof_data:
        errors.append("Bill-of-Features is missing 'name'")
    if not isinstance(bof_data.get("selections", {}), dict):
        errors.append("Bill-of-Features 'selections' must be a YAML mapping")
    evidence = bof_data.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, dict):
            errors.append("Bill-of-Features 'evidence' must be a YAML mapping")
        else:
            unknown = sorted(set(evidence) - {"status", "artifacts"})
            for field in unknown:
                errors.append(f"unknown evidence field: '{field}'")
            status = evidence.get("status")
            if status not in EVIDENCE_STATUSES:
                errors.append(
                    "evidence.status must be one of: "
                    + ", ".join(sorted(EVIDENCE_STATUSES))
                )
            artifacts = evidence.get("artifacts", [])
            if not isinstance(artifacts, list):
                errors.append("evidence.artifacts must be a YAML list")
            else:
                for index, artifact in enumerate(artifacts):
                    if not isinstance(artifact, dict):
                        errors.append(
                            f"evidence.artifacts[{index}] must be a YAML mapping"
                        )
                        continue
                    if set(artifact) != {"id", "path"}:
                        errors.append(
                            f"evidence.artifacts[{index}] must contain exactly id and path"
                        )
                    if not isinstance(artifact.get("id"), str):
                        errors.append(f"evidence.artifacts[{index}].id must be a string")
                    if not isinstance(artifact.get("path"), str):
                        errors.append(f"evidence.artifacts[{index}].path must be a string")
    return errors


def validate_bof_evidence(bof_data):
    """Enforce status-to-retained-artifact rules for configuration evidence."""
    evidence = bof_data.get("evidence")
    if evidence is None:
        return []
    status = evidence["status"]
    artifacts = evidence.get("artifacts", [])
    errors = []
    if status in EVIDENCE_BEARING_STATUSES and not artifacts:
        errors.append(f"{status} configuration requires retained evidence artifacts")

    seen_ids = set()
    for artifact in artifacts:
        artifact_id = artifact["id"]
        path_text = artifact["path"]
        if not re.fullmatch(r"[A-Z][A-Z0-9-]*", artifact_id):
            errors.append(f"evidence artifact id '{artifact_id}' is invalid")
        elif artifact_id in seen_ids:
            errors.append(f"duplicate evidence artifact id '{artifact_id}'")
        seen_ids.add(artifact_id)

        path = Path(path_text)
        if path.is_absolute() or ".." in path.parts:
            errors.append(
                f"evidence artifact path '{path_text}' must be repository-relative"
            )
            continue
        if ".git" in path.parts:
            errors.append(
                f"evidence artifact path '{path_text}' may not reference repository metadata"
            )
            continue

        candidate = REPO_ROOT / path
        current = REPO_ROOT
        traverses_symlink = False
        for component in path.parts:
            current = current / component
            if current.is_symlink():
                traverses_symlink = True
                break
        if traverses_symlink:
            errors.append(
                f"evidence artifact path '{path_text}' must not traverse symbolic links"
            )
            continue
        if not candidate.is_file():
            errors.append(f"evidence artifact does not exist: '{path_text}'")
            continue

        resolved = candidate.resolve()
        try:
            resolved.relative_to(REPO_ROOT.resolve())
        except ValueError:
            errors.append(f"evidence artifact path '{path_text}' escapes the repository")
            continue

        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", path.as_posix()],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode != 0:
            errors.append(f"evidence artifact '{path_text}' is not tracked by Git")
    return errors


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
        feature_id = data.get("id")
        binding_time = data.get("binding_time")
        maps_to = data.get("maps_to")
        maps_to_variant = data.get("maps_to_variant")

        node = FeatureNode(
            name=name, ftype=ftype, description=description,
            feature_id=feature_id, binding_time=binding_time,
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


def iter_feature_nodes(root):
    """Yield every node without collapsing duplicate computed paths."""
    yield root
    for child in root.children:
        yield from iter_feature_nodes(child)


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
    """
    Collect all leaf nodes that are transitively mandatory.
    The root is always selected, whatever type it declares or defaults
    to, so the walk starts at its children.
    """
    leaves = []

    def walk(node, parent_mandatory):
        is_mandatory = parent_mandatory and node.type == "mandatory"
        if node.is_leaf() and is_mandatory:
            leaves.append(node)
        for child in node.children:
            walk(child, is_mandatory)

    for child in root.children:
        walk(child, True)
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
    # - Alternative/or_group nodes with leaf choices: their own path
    valid_selection_keys = set()
    for path, node in all_nodes.items():
        if node.is_leaf() and not (
            node.parent and node.parent.is_selection_group()
        ):
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

    for path, node in all_nodes.items():
        if (
            node.is_leaf()
            and not (node.parent and node.parent.is_selection_group())
            and path in selections
            and not isinstance(selections[path], bool)
        ):
            errors.append(f"'{path}' must be a YAML boolean")

    # Check selection cardinality and valid child names.
    for group in find_alternative_groups(root):
        if not group.is_selection_group():
            continue

        selected = selections.get(group.path)
        child_names = [child.name for child in group.children]

        if group.type == "alternative":
            if selected is not None and selected is not False:
                if not isinstance(selected, str) or selected not in child_names:
                    errors.append(
                        f"'{group.path}': '{selected}' is not a valid XOR choice. "
                        f"Valid: {child_names}"
                    )
        elif selected is not None and selected is not False:
            if not isinstance(selected, list) or not selected:
                errors.append(
                    f"'{group.path}' is an or_group and requires a non-empty list"
                )
            else:
                non_strings = [choice for choice in selected if not isinstance(choice, str)]
                if non_strings:
                    errors.append(
                        f"'{group.path}' OR choices must all be strings"
                    )
                else:
                    invalid = [
                        choice for choice in selected if choice not in child_names
                    ]
                    if invalid:
                        errors.append(
                            f"'{group.path}' has invalid OR choice(s): {invalid}. "
                            f"Valid: {child_names}"
                        )
                    if len(selected) != len(set(selected)):
                        errors.append(
                            f"'{group.path}' contains duplicate OR choices"
                        )

        if is_transitively_mandatory(group) and not selected:
            errors.append(
                f"Mandatory {group.type} group '{group.path}' has no selection"
            )

    # Check: no transitively-mandatory leaf is set to false. One the BoF
    # leaves out counts as selected, here and in the constraint pass.
    for leaf in find_mandatory_leaves(root):
        sel = selections.get(leaf.path)
        if sel is False:
            errors.append(
                f"Mandatory feature not selected: '{leaf.path}'"
            )

    return errors


def parse_constraint_expression(expression):
    """Parse the closed BoF constraint grammar and return its feature path."""
    path = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"
    value = r"[A-Za-z_]\w*"
    patterns = [
        rf"^({path})\s*(?:==|!=)\s*{value}$",
        rf"^({path})\s+in\s+\[\s*{value}(?:\s*,\s*{value})*\s*\]$",
        rf"^({path})$",
    ]
    for pattern in patterns:
        match = re.fullmatch(pattern, expression.strip())
        if match:
            return match.group(1)
    return None


def validate_constraint_definitions(constraints, all_nodes):
    """Reject malformed expressions and references before evaluation."""
    errors = []
    known_paths = set(all_nodes)
    for constraint in constraints:
        cid = constraint.get("id", "?")
        for field in ("if", "then"):
            expression = constraint[field]
            path = parse_constraint_expression(expression)
            if path is None:
                errors.append(
                    f"[{cid}] invalid constraint expression in '{field}': "
                    f"'{expression}'"
                )
            elif path not in known_paths:
                errors.append(
                    f"[{cid}] constraint expression references unknown path "
                    f"'{path}'"
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
        if isinstance(sel, list):
            return any(choice in values for choice in sel)
        return sel in values

    # Path == Value
    m = re.match(r'^(.+?)\s+==\s*(.+)$', condition_str)
    if m:
        path = m.group(1).strip()
        value = m.group(2).strip()
        sel = selections.get(path)
        if isinstance(sel, list):
            return value in sel
        return str(sel) == value

    # Path != Value
    m = re.match(r'^(.+?)\s+!=\s*(.+)$', condition_str)
    if m:
        path = m.group(1).strip()
        value = m.group(2).strip()
        sel = selections.get(path)
        if isinstance(sel, list):
            return value not in sel
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

        if ctype not in {"requires", "excludes"}:
            errors.append(f"[{cid}] unknown constraint type: '{ctype}'")
            continue

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


def validate_platform_mapping_metadata(root, projection_owner="SDVPlatformStack"):
    """Validate catalogue IDs, binding times, and complete mapping metadata."""
    errors = []
    nodes = list(iter_feature_nodes(root))
    seen_ids = {}
    seen_paths = {}
    allowed_binding_times = {"design", "unassigned"}
    allowed_relationship_types = {"mandatory", "optional", "alternative", "or_group"}

    for parent in nodes:
        sibling_names = set()
        for child in parent.children:
            if not isinstance(child.name, str):
                continue
            if child.name in sibling_names:
                parent_path = parent.path or parent.name
                errors.append(
                    f"Duplicate sibling name '{child.name}' under '{parent_path}'"
                )
            else:
                sibling_names.add(child.name)

    for node in nodes:
        path = node.path or str(node.name)
        if not isinstance(node.name, str) or not re.fullmatch(
            r"[A-Za-z_]\w*", node.name
        ):
            errors.append(f"Feature/catalogue node '{path}' has invalid name")
        if path in seen_paths:
            errors.append(
                f"Duplicate computed feature path '{path}'"
            )
        else:
            seen_paths[path] = node

        if (
            not isinstance(node.type, str)
            or node.type not in allowed_relationship_types
        ):
            errors.append(
                f"Feature/catalogue node '{path}' has invalid relationship type: "
                f"'{node.type}'"
            )
        if isinstance(node.type, str) and node.type in {"alternative", "or_group"}:
            if not node.children:
                errors.append(f"Selection group '{path}' must not be empty")
            elif any(child.children for child in node.children):
                errors.append(
                    f"Selection group '{path}' must contain only leaf choices"
                )
        if not node.feature_id:
            errors.append(f"Feature/catalogue node '{path}' is missing stable 'id'")
        elif not isinstance(node.feature_id, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9-]*", node.feature_id
        ):
            errors.append(f"Feature/catalogue node '{path}' has invalid id")
        elif node.feature_id in seen_ids:
            errors.append(
                f"Duplicate feature id '{node.feature_id}' on '{path}' and "
                f"'{seen_ids[node.feature_id]}'"
            )
        else:
            seen_ids[node.feature_id] = path

        if node.binding_time is not None and (
            not isinstance(node.binding_time, str) or
            node.binding_time not in allowed_binding_times
        ):
            errors.append(
                f"Feature/catalogue node '{path}' has invalid binding_time: "
                f"'{node.binding_time}'"
            )

        if node.maps_to is not None and not node.is_selection_group():
            errors.append(
                f"Non-selection node '{path}' must not declare maps_to"
            )
        if node.maps_to_variant is not None:
            parent = node.parent
            if parent is None or not parent.is_selection_group():
                errors.append(
                    f"Node '{path}' has orphan maps_to_variant metadata"
                )

    seen_variation_targets = {}
    for group in find_alternative_groups(root):
        group_is_mapped = group.maps_to is not None
        mapped_children = [
            child for child in group.children
            if child.maps_to_variant is not None
        ]

        if group_is_mapped and group.type != "alternative":
            errors.append(
                f"Mapped variation '{group.path}' must use alternative (XOR), "
                "not or_group"
            )
        if group_is_mapped and len(mapped_children) != len(group.children):
            errors.append(
                f"Mapped variation '{group.path}' must map every variant child"
            )
        if not group_is_mapped and mapped_children:
            errors.append(
                f"Unmapped variation '{group.path}' has mapped variant children"
            )
        if not group_is_mapped:
            continue

        if group.binding_time != "design":
            errors.append(
                f"Mapped variation '{group.path}' must declare binding_time: design"
            )
        if not isinstance(group.maps_to, str) or not re.fullmatch(
            rf"{re.escape(projection_owner)}\.[A-Za-z_]\w*", group.maps_to
        ):
            errors.append(
                f"Mapped variation '{group.path}' has invalid maps_to: "
                f"'{group.maps_to}'"
            )
        elif group.maps_to in seen_variation_targets:
            errors.append(
                f"Duplicate maps_to target '{group.maps_to}' on '{group.path}' "
                f"and '{seen_variation_targets[group.maps_to]}'"
            )
        else:
            seen_variation_targets[group.maps_to] = group.path

        seen_variant_targets = set()
        for variant in group.children:
            if variant.binding_time != "design":
                errors.append(
                    f"Mapped variant '{variant.path}' must declare binding_time: design"
                )
            if not isinstance(variant.maps_to_variant, str) or not re.fullmatch(
                r"[A-Za-z_]\w*", variant.maps_to_variant
            ):
                errors.append(
                    f"Mapped variant '{variant.path}' has invalid maps_to_variant"
                )
            elif variant.maps_to_variant in seen_variant_targets:
                errors.append(
                    f"Duplicate maps_to_variant '{variant.maps_to_variant}' "
                    f"under '{group.path}'"
                )
            else:
                seen_variant_targets.add(variant.maps_to_variant)
    return errors


def validate_derived_asset_selections(feature_data, all_nodes,
                                      projection_owner="SDVPlatformStack"):
    """Validate deterministic, non-selectable shared-asset derivation rules."""
    declarations = feature_data.get("derived_asset_selections", [])
    if not isinstance(declarations, list):
        return []  # The document-shape pass owns this diagnostic.

    errors = []
    seen_ids = {}
    seen_targets = {}
    allowed_fields = {"id", "maps_to", "source_selections", "rules"}
    mapped_feature_targets = {
        node.maps_to for node in all_nodes.values()
        if node.is_selection_group() and node.maps_to is not None
    }

    for index, declaration in enumerate(declarations):
        label = f"derived_asset_selections[{index}]"
        if not isinstance(declaration, dict):
            errors.append(f"{label} must be a YAML mapping")
            continue

        unknown_fields = sorted(
            set(declaration) - allowed_fields, key=lambda field: str(field)
        )
        for field in unknown_fields:
            errors.append(f"{label} has unknown field '{field}'")
        missing_fields = sorted(allowed_fields - set(declaration))
        for field in missing_fields:
            errors.append(f"{label} is missing '{field}'")

        derivation_id = declaration.get("id")
        if not isinstance(derivation_id, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9-]*", derivation_id
        ):
            errors.append(f"{label}.id must be a stable uppercase identifier")
        elif derivation_id in seen_ids:
            errors.append(
                f"Duplicate derived asset id '{derivation_id}' on {label} and "
                f"{seen_ids[derivation_id]}"
            )
        else:
            seen_ids[derivation_id] = label

        target = declaration.get("maps_to")
        if not isinstance(target, str) or not re.fullmatch(
            rf"{re.escape(projection_owner)}\.[A-Za-z_]\w*", target
        ):
            errors.append(f"{label}.maps_to has invalid target: '{target}'")
        elif target in seen_targets:
            errors.append(
                f"Duplicate derived maps_to target '{target}' on {label} and "
                f"{seen_targets[target]}"
            )
        else:
            seen_targets[target] = label
            if target in mapped_feature_targets:
                errors.append(
                    f"Derived asset target '{target}' is already independently "
                    "selectable from the feature tree"
                )

        source_paths = declaration.get("source_selections")
        valid_source_paths = []
        if not isinstance(source_paths, list) or not source_paths:
            errors.append(f"{label}.source_selections must be a non-empty YAML list")
        elif any(not isinstance(path, str) for path in source_paths):
            errors.append(f"{label}.source_selections must contain only strings")
        else:
            valid_source_paths = source_paths
            if len(source_paths) != len(set(source_paths)):
                errors.append(f"{label}.source_selections contains duplicates")
            for path in source_paths:
                node = all_nodes.get(path)
                if node is None:
                    errors.append(
                        f"{label}.source_selections references unknown path '{path}'"
                    )
                elif not node.is_selection_group() or node.type != "alternative":
                    errors.append(
                        f"{label}.source_selections path '{path}' must be an "
                        "alternative selection group"
                    )

        rules = declaration.get("rules")
        if not isinstance(rules, list) or not rules:
            errors.append(f"{label}.rules must be a non-empty YAML list")
            continue

        seen_conditions = {}
        for rule_index, rule in enumerate(rules):
            rule_label = f"{label}.rules[{rule_index}]"
            if not isinstance(rule, dict):
                errors.append(f"{rule_label} must be a YAML mapping")
                continue
            unknown_rule_fields = sorted(
                set(rule) - {"when", "maps_to_variant"},
                key=lambda field: str(field),
            )
            for field in unknown_rule_fields:
                errors.append(f"{rule_label} has unknown field '{field}'")
            for field in sorted({"when", "maps_to_variant"} - set(rule)):
                errors.append(f"{rule_label} is missing '{field}'")

            conditions = rule.get("when")
            if not isinstance(conditions, dict) or not conditions:
                errors.append(f"{rule_label}.when must be a non-empty YAML mapping")
                continue
            if valid_source_paths:
                condition_paths = set(conditions)
                expected_paths = set(valid_source_paths)
                for path in sorted(
                    condition_paths - expected_paths, key=lambda item: str(item)
                ):
                    errors.append(
                        f"{rule_label}.when references undeclared source path '{path}'"
                    )
                for path in sorted(
                    expected_paths - condition_paths, key=lambda item: str(item)
                ):
                    errors.append(
                        f"{rule_label}.when is missing source path '{path}'"
                    )

                condition_values_valid = condition_paths == expected_paths
                for path in valid_source_paths:
                    value = conditions.get(path)
                    node = all_nodes.get(path)
                    if not isinstance(value, str):
                        condition_values_valid = False
                        errors.append(
                            f"{rule_label}.when['{path}'] must be a string choice"
                        )
                    elif node is not None and node.is_selection_group() and value not in {
                        child.name for child in node.children
                    }:
                        condition_values_valid = False
                        errors.append(
                            f"{rule_label}.when['{path}'] has unknown choice '{value}'"
                        )
                if condition_values_valid:
                    condition_key = tuple(
                        (path, conditions[path]) for path in valid_source_paths
                    )
                    if condition_key in seen_conditions:
                        errors.append(
                            f"{rule_label} duplicates the condition in "
                            f"{seen_conditions[condition_key]}"
                        )
                    else:
                        seen_conditions[condition_key] = rule_label

            variant = rule.get("maps_to_variant")
            if not isinstance(variant, str) or not re.fullmatch(
                r"[A-Za-z_]\w*", variant
            ):
                errors.append(
                    f"{rule_label}.maps_to_variant must be a valid SysML identifier"
                )
    return errors


def resolve_derived_asset_selections(feature_data, selections):
    """Resolve exactly one shared-asset variant for each derived declaration."""
    resolved = []
    errors = []
    for declaration in feature_data.get("derived_asset_selections", []):
        matches = [
            rule for rule in declaration["rules"]
            if all(
                selections.get(path) == value
                for path, value in rule["when"].items()
            )
        ]
        target = declaration["maps_to"]
        derivation_id = declaration["id"]
        source_summary = ", ".join(
            f"{path}={selections.get(path)!r}"
            for path in declaration["source_selections"]
        )
        if not matches:
            errors.append(
                f"Derived asset '{derivation_id}' for '{target}' has no rule "
                f"matching {source_summary}"
            )
        elif len(matches) > 1:
            errors.append(
                f"Derived asset '{derivation_id}' for '{target}' has "
                f"{len(matches)} matching rules for {source_summary}"
            )
        else:
            resolved.append((
                target.rsplit(".", 1)[-1],
                matches[0]["maps_to_variant"],
                derivation_id,
            ))
    return resolved, errors


def validate_sysml_lexical_balance(source):
    """Check global comment/string termination and brace balance."""
    brace_depth = 0
    comment_depth = 0
    quote = None
    index = 0
    while index < len(source):
        pair = source[index:index + 2]
        char = source[index]
        if comment_depth:
            if pair == "/*":
                comment_depth += 1
                index += 2
                continue
            if pair == "*/":
                comment_depth -= 1
                index += 2
                continue
            index += 1
            continue
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if pair == "/*":
            comment_depth = 1
            index += 2
            continue
        if pair == "//":
            newline = source.find("\n", index + 2)
            index = len(source) if newline == -1 else newline + 1
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth < 0:
                return "unmatched closing brace"
        index += 1
    if comment_depth:
        return "unterminated block comment"
    if quote:
        return "unterminated string"
    if brace_depth:
        return "unbalanced braces"
    return None


def strip_sysml_comments_and_strings(source):
    """Remove text that cannot declare SysML elements, preserving line breaks."""
    token_pattern = re.compile(
        r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'",
        re.DOTALL,
    )

    def blank(match):
        return "".join("\n" if char == "\n" else " " for char in match.group())

    return token_pattern.sub(blank, source)


def direct_declaration_matches(source, declaration_pattern):
    """Find all declarations beginning at brace depth zero in a body."""
    pattern = re.compile(declaration_pattern)
    matches = []
    depth = 0
    index = 0
    while index < len(source):
        char = source[index]
        if char == "{":
            depth += 1
            index += 1
            continue
        if char == "}":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth == 0:
            match = pattern.match(source, index)
            if match:
                matches.append(match)
                index = match.end()
                continue
        index += 1
    return matches


def balanced_body_at(source, open_brace):
    """Return the body of the balanced block starting at open_brace."""
    depth = 1
    for index in range(open_brace + 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1:index]
    return None


def braced_body_for_match(source, match):
    cursor = match.end()
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor < len(source) and source[cursor] == "{":
        return balanced_body_at(source, cursor)
    return None


def unique_direct_braced_body(source, pattern, label):
    """Resolve exactly one direct braced declaration or return a diagnostic."""
    matches = direct_declaration_matches(source, pattern)
    bodies = [braced_body_for_match(source, match) for match in matches]
    bodies = [body for body in bodies if body is not None]
    if len(matches) > 1:
        return None, f"{label} has multiple direct declarations"
    if len(matches) == 0 or len(bodies) == 0:
        return None, f"{label} was not found as a complete direct declaration"
    return bodies[0], None


def validate_sysml_mapping_targets(root, shared_model_path, projection=None,
                                   feature_data=None):
    """Verify selected and derived variants belong to their shared variations."""
    projection = projection or DEFAULT_PROJECTION
    package_name = projection["package"]
    owner_name = projection["owner"]
    try:
        source = Path(shared_model_path).read_text()
    except (OSError, UnicodeError) as exc:
        return [f"Cannot read shared-assets model '{shared_model_path}': {exc}"]

    lexical_error = validate_sysml_lexical_balance(source)
    if lexical_error:
        return [
            f"Shared-assets model '{shared_model_path}' is lexically invalid: "
            f"{lexical_error}"
        ]
    source = strip_sysml_comments_and_strings(source)
    package_body, package_error = unique_direct_braced_body(
        source,
        rf"\bpackage\s+{re.escape(package_name)}\b\s*",
        f"SysML package '{package_name}'",
    )
    if package_error:
        return [f"{package_error} in '{shared_model_path}'"]
    stack_body, stack_error = unique_direct_braced_body(
        package_body,
        rf"\bpart\s+def\s+{re.escape(owner_name)}\b"
        rf"(?:\s*:>\s*[A-Za-z_]\w*)?\s*",
        f"SysML part def '{owner_name}'",
    )
    if stack_error:
        return [
            f"{stack_error} under package '{package_name}' in "
            f"'{shared_model_path}'"
        ]

    errors = []
    for group in find_alternative_groups(root):
        if not isinstance(group.maps_to, str) or not re.fullmatch(
            rf"{re.escape(owner_name)}\.[A-Za-z_]\w*", group.maps_to
        ):
            continue
        part_name = group.maps_to.rsplit(".", 1)[-1]
        variation_body, variation_error = unique_direct_braced_body(
            stack_body,
            rf"\bvariation\s+part\s+{re.escape(part_name)}\b"
            rf"(?:\s*:\s*[A-Za-z_]\w*)?"
            rf"(?:\s*\[(?:\d+|\d+\.\.(?:\d+|\*))\])?\s*",
            f"Mapped SysML variation '{group.maps_to}'",
        )
        if variation_error:
            errors.append(f"{variation_error} in '{shared_model_path}'")
            continue
        for variant in group.children:
            variant_name = variant.maps_to_variant
            if not isinstance(variant_name, str) or not re.fullmatch(
                r"[A-Za-z_]\w*", variant_name
            ):
                continue
            variant_pattern = (
                rf"\bvariant\s+part\s+{re.escape(variant_name)}"
                rf"(?:\s*\[0\])?"
                rf"(?:\s*:\s*[A-Za-z_]\w*)?\s*;"
            )
            matches = direct_declaration_matches(variation_body, variant_pattern)
            if len(matches) > 1:
                errors.append(
                    f"Mapped SysML variant '{group.maps_to}::{variant_name}' has "
                    f"multiple direct declarations in '{shared_model_path}'"
                )
            elif not matches:
                errors.append(
                    f"Mapped SysML variant '{group.maps_to}::{variant_name}' was "
                    f"not found as a complete direct declaration in "
                    f"'{shared_model_path}'"
                )

    for declaration in (feature_data or {}).get("derived_asset_selections", []):
        target = declaration["maps_to"]
        part_name = target.rsplit(".", 1)[-1]
        variation_body, variation_error = unique_direct_braced_body(
            stack_body,
            rf"\bvariation\s+part\s+{re.escape(part_name)}\b"
            rf"(?:\s*:\s*[A-Za-z_]\w*)?"
            rf"(?:\s*\[(?:\d+|\d+\.\.(?:\d+|\*))\])?\s*",
            f"Derived SysML variation '{target}'",
        )
        if variation_error:
            errors.append(f"{variation_error} in '{shared_model_path}'")
            continue
        variant_names = {
            rule["maps_to_variant"] for rule in declaration["rules"]
        }
        for variant_name in sorted(variant_names):
            variant_pattern = (
                rf"\bvariant\s+part\s+{re.escape(variant_name)}"
                rf"(?:\s*\[0\])?"
                rf"(?:\s*:\s*[A-Za-z_]\w*)?\s*;"
            )
            matches = direct_declaration_matches(variation_body, variant_pattern)
            if len(matches) > 1:
                errors.append(
                    f"Derived SysML variant '{target}::{variant_name}' has "
                    f"multiple direct declarations in '{shared_model_path}'"
                )
            elif not matches:
                errors.append(
                    f"Derived SysML variant '{target}::{variant_name}' was not "
                    f"found as a complete direct declaration in "
                    f"'{shared_model_path}'"
                )
    return errors


def sysml_comment_text(value):
    """Escape data embedded in SysML block comments."""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "?", text)
    return text.replace("/*", "/ *").replace("*/", "* /")


def validate_bof_metadata(name, description):
    """Validate Bill-of-Features fields used in generated SysML syntax."""
    errors = []
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w*", name):
        errors.append(
            "Bill-of-Features 'name' must be a valid unquoted SysML identifier"
        )
    if description is not None and not isinstance(description, str):
        errors.append("Bill-of-Features 'description' must be a string")
    return errors


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
# Generation
# ──────────────────────────────────────────────────────────────

def generate_sysml(bof_name, bof_description, root, all_nodes, selections,
                   feature_model_path, bof_path, shared_model_path,
                   projection=None, derived_redefinitions=None):
    """Generate a derived product-model projection of one shared-asset owner."""
    projection = projection or DEFAULT_PROJECTION
    redefinitions, derived_ids_by_part, capability_annotations = projection_content(
        root, all_nodes, selections, derived_redefinitions
    )
    provenance = [
        "Generated by configure_variant.py.",
        "This is not a complete member-product specification.",
        "Shared-assets source baseline: "
        f"{sysml_comment_text(shared_asset_baseline(shared_model_path))}",
        f"Shared-assets model: {sysml_comment_text(provenance_path(shared_model_path))}",
        f"Shared-assets model SHA-256: {file_sha256(shared_model_path)}",
        f"Feature model SHA-256: {file_sha256(feature_model_path)}",
        f"Bill-of-Features SHA-256: {file_sha256(bof_path)}",
        f"Regenerate from: {sysml_comment_text(provenance_path(bof_path))}",
        f"Feature model: {sysml_comment_text(provenance_path(feature_model_path))}",
    ]
    return render_projection(
        bof_name, bof_description, projection, redefinitions,
        derived_ids_by_part, capability_annotations, provenance,
        "Bill-of-Features",
    )


def projection_content(root, all_nodes, selections, derived_redefinitions=None):
    """Return what a valid Bill-of-Features states for its projection.

    The result is the variant selections (mapped groups in tree order, then
    the derived ones), the derivation ID of each derived part, and the
    selections outside the projection: unmapped groups, then optional leaves
    the Bill-of-Features sets explicitly.
    """
    redefinitions = []
    capability_annotations = []
    derived_redefinitions = derived_redefinitions or []
    derived_ids_by_part = {
        part_name: derivation_id
        for part_name, _variant_name, derivation_id in derived_redefinitions
    }

    for group in find_alternative_groups(root):
        selected = selections.get(group.path)
        if selected is None:
            continue
        selected_node = next(
            (child for child in group.children if child.name == selected),
            None,
        )
        if (group.maps_to and selected_node and
                selected_node.maps_to_variant):
            part_name = group.maps_to.rsplit(".", 1)[-1]
            redefinitions.append((part_name, selected_node.maps_to_variant))
        else:
            annotation_value = (
                ", ".join(selected) if isinstance(selected, list)
                else str(selected)
            )
            capability_annotations.append((group.path, annotation_value))

    redefinitions.extend(
        (part_name, variant_name)
        for part_name, variant_name, _derivation_id in derived_redefinitions
    )

    for path, node in all_nodes.items():
        # Optional booleans without mapped assets remain provenance only.
        if (node.is_leaf() and node.type == "optional" and
                not node.maps_to_variant):
            sel = selections.get(node.path)
            if sel is not None:
                status = "enabled" if sel else "disabled"
                capability_annotations.append((node.path, status))
    return redefinitions, derived_ids_by_part, capability_annotations


def render_projection(name, description, projection, redefinitions,
                      derived_ids_by_part, capability_annotations, provenance,
                      source):
    """The writer: render one derived product-model projection.

    ``provenance`` holds the header lines below the title, and ``source``
    names what decided the selection in the derivation-source line of the
    doc, which the parity check normalises (plan section 5).
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
# Receipts (ADR 0022, plan step S4)
# ──────────────────────────────────────────────────────────────

#: The evaluated states in which a feature is selected.
RECEIPT_SELECTED_STATES = {"enabled", "implied"}
#: What decided the selection, as the derivation-source line of a receipt projection names it.
RECEIPT_SOURCE = "PLEML configuration receipt"


def receipt_projection_content(model, configuration, writer):
    """Return what one valid configuration of a receipt states for its projection.

    The content is the one ``projection_content`` gives for a
    Bill-of-Features, read from the receipt: the bound variants in the tree
    order of their groups, the derived ones after them in the order of their
    derivations, each with its derivation's ID, and the selections outside
    the projection, unbound groups then optional features set explicitly.
    Until S7 these are labelled by the catalogue paths the receipt records.
    """
    features = model["features"]
    order = {feature["path"]: index for index, feature in enumerate(features)}
    by_path = {feature["path"]: feature for feature in features}
    bindings = {item["binding"]: item for item in model["bindings"]}
    bound_features = {item["feature"] for item in model["bindings"]}
    paths = writer["catalogue_paths"]
    states = configuration["states"]

    def catalogue_path(path):
        value = paths.get(path)
        if not value:
            raise ValueError(f"the receipt records no catalogue path for {path}")
        return value

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
        chosen = [catalogue_path(member).rsplit(".", 1)[-1] for member in members
                  if states.get(member) in RECEIPT_SELECTED_STATES]
        if chosen:
            capability_annotations.append((catalogue_path(feature["path"]), ", ".join(chosen)))
    explicit = writer["explicit_optional_states"]
    for feature in features:
        if feature["path"] in explicit:
            capability_annotations.append((catalogue_path(feature["path"]), explicit[feature["path"]]))
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
    source document. A receipt whose inputs changed, whose evaluation or
    shadow does not reproduce, or that records integrity, complement or
    rule-table errors is refused, with the evaluator's own replay.
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
    writers = {item["tree"]: item["writer_inputs"]
               for item in (receipt.get("shadow") or {}).get("feature_models", [])}
    writer = writers.get(model["tree"]["name"], {}).get(configuration["configuration"])
    if writer is None or "catalogue_paths" not in writer:
        raise ValueError(
            f"the receipt records no writer inputs with catalogue paths for "
            f"'{configuration['configuration']}'; its YAML shadow carries them until S7"
        )
    payload = pleml_receipts.read_elements(receipt_path.parent / receipt["elements"]["path"])
    shared_assets = receipt_shared_assets(model, payload["element_sources"])
    return receipt, model, configuration, writer, shared_assets


def receipt_projection(receipt_path, receipt, model, configuration, writer,
                       shared_assets, root=REPO_ROOT):
    """Render the projection of one valid configuration of a receipt that holds, with the writer."""
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
    """Receipt mode: replay the receipt, then project one of its valid configurations."""
    receipt_path = Path(args.receipt)
    try:
        receipt, model, configuration, writer, shared_assets = (
            load_receipt_configuration(receipt_path, args.configuration)
        )
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        sys.stderr.write(f"Error reading input: {exc}\n")
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
        description="Configure an SDV variant from a Bill-of-Features, or "
                    "project one configuration of a PLEML receipt"
    )
    parser.add_argument(
        "--feature-model",
        help="Path to feature model YAML"
    )
    parser.add_argument(
        "--bof",
        help="Path to Bill-of-Features YAML"
    )
    parser.add_argument(
        "--receipt",
        help="Receipt mode: a committed PLEML configuration receipt, with "
             "--configuration instead of --feature-model and --bof"
    )
    parser.add_argument(
        "--configuration",
        help="Receipt mode: the configuration's declared name, projection "
             "name or source document"
    )
    parser.add_argument(
        "--shared-assets-model", default=None,
        help="SysML v2 shared-assets model used to verify feature mappings "
             "(default: the SDV platform stack; a receipt names its own)"
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
    if args.receipt is not None or args.configuration is not None:
        if (args.feature_model is not None or args.bof is not None
                or args.shared_assets_model is not None):
            parser.error("receipt mode takes no --feature-model, --bof or "
                         "--shared-assets-model: the receipt names its documents")
        if args.receipt is None or args.configuration is None:
            parser.error("receipt mode needs both --receipt and --configuration")
        main_receipt(args)
        return
    if args.feature_model is None or args.bof is None:
        parser.error("the following arguments are required: --feature-model, --bof")
    if args.shared_assets_model is None:
        args.shared_assets_model = str(
            REPO_ROOT / "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"
        )

    # Load files
    try:
        with open(args.feature_model) as f:
            feature_model_data = load_yaml_unique(f)
        with open(args.bof) as f:
            bof_data = load_yaml_unique(f)
        # Preflight the shared textual input so encoding/path failures use the
        # same controlled input-error contract as the YAML documents.
        Path(args.shared_assets_model).read_text()
    except (OSError, UnicodeError) as e:
        sys.stderr.write(f"Error reading input: {e}\n")
        sys.exit(2)
    except yaml.YAMLError as e:
        sys.stderr.write(f"Error parsing YAML: {e}\n")
        sys.exit(2)

    schema_errors = validate_document_shapes(feature_model_data, bof_data)
    if schema_errors:
        sys.stderr.write("Error: invalid input schema:\n")
        for error in schema_errors:
            sys.stderr.write(f"  - {error}\n")
        sys.exit(2)

    # Build feature tree
    root, constraints = build_feature_tree(feature_model_data)
    projection = projection_metadata(feature_model_data)
    all_nodes = collect_all_nodes(root)
    bof_name, bof_description, selections = parse_bof(bof_data)

    # Pass 1: Structural and mapping-metadata validation
    structural_errors = validate_structure(root, all_nodes, selections)
    bof_metadata_errors = validate_bof_metadata(bof_name, bof_description)
    evidence_errors = validate_bof_evidence(bof_data)
    mapping_errors = validate_platform_mapping_metadata(root, projection["owner"])
    derived_metadata_errors = validate_derived_asset_selections(
        feature_model_data, all_nodes, projection["owner"]
    )
    if derived_metadata_errors:
        derived_redefinitions = []
        derived_resolution_errors = []
        mapping_target_errors = validate_sysml_mapping_targets(
            root, args.shared_assets_model, projection
        )
    else:
        derived_redefinitions, derived_resolution_errors = (
            resolve_derived_asset_selections(feature_model_data, selections)
        )
        mapping_target_errors = validate_sysml_mapping_targets(
            root, args.shared_assets_model, projection, feature_model_data
        )
    # Pass 2: Constraint validation. A transitively-mandatory leaf the BoF
    # leaves out counts as selected here too, as in the structural check.
    constraint_definition_errors = validate_constraint_definitions(
        constraints, all_nodes
    )
    implied_leaves = {
        leaf.path: True for leaf in find_mandatory_leaves(root)
        if leaf.path not in selections
    }
    constraint_errors = validate_constraints(
        constraints, {**selections, **implied_leaves}
    )

    all_errors = (
        structural_errors + bof_metadata_errors + evidence_errors + mapping_errors
        + derived_metadata_errors + derived_resolution_errors
        + mapping_target_errors + constraint_definition_errors + constraint_errors
    )

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
        args.feature_model, args.bof, args.shared_assets_model, projection,
        derived_redefinitions
    )
    write_projection(args.output, sysml_output)


if __name__ == "__main__":
    main()
