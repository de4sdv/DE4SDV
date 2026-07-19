#!/usr/bin/env python3
"""
DE4SDV variant configurator.

Reads a Bill-of-Features (YAML), validates it against the feature model (YAML),
then generates the implemented platform-stack SysML v2 product-model projection.
Selections without mapped variable shared assets are validated but not derived.

The configurator implements three of the four ISO/IEC 26580 PLE Factory
components in a lightweight, in-repo way:

  Feature Catalogue         → feature-models/*.yaml
  Bill-of-Features          → feature-configurations/*.yaml
  Configurator (this script) → tools/configure_variant.py
  Product Asset Instance    → product-models/*.sysml (generated platform slice)

The fourth component — the Shared Asset Superset (150% model) — lives
in textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml
as native SysML v2 variation/variant notation.

Selection semantics:
  - Alternative groups: assign one child name as a scalar value
    e.g. PlatformStack.Middleware: EclipseSCORE
  - OR-groups: assign a non-empty list of child names
  - Optional/mandatory leaves: assign a YAML Boolean true or false
    e.g. Capabilities.ForwardCollisionMitigation.PedestrianDetection: false

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
  2 — input/read/parse/schema error
"""

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

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

    # Check: every transitively-mandatory leaf is selected
    for leaf in find_mandatory_leaves(root):
        sel = selections.get(leaf.path)
        if sel is None or sel is False:
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


def validate_platform_mapping_metadata(root):
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
            r"SDVPlatformStack\.[A-Za-z_]\w*", group.maps_to
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


def validate_sysml_mapping_targets(root, shared_model_path):
    """Verify mapped variants belong to the mapped SDVPlatformStack variation."""
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
        r"\bpackage\s+DE4SDV_SDVPlatformStack\b\s*",
        "SysML package 'DE4SDV_SDVPlatformStack'",
    )
    if package_error:
        return [f"{package_error} in '{shared_model_path}'"]
    stack_body, stack_error = unique_direct_braced_body(
        package_body,
        r"\bpart\s+def\s+SDVPlatformStack\b\s*",
        "SysML part def 'SDVPlatformStack'",
    )
    if stack_error:
        return [
            f"{stack_error} under package 'DE4SDV_SDVPlatformStack' in "
            f"'{shared_model_path}'"
        ]

    errors = []
    for group in find_alternative_groups(root):
        if not isinstance(group.maps_to, str) or not re.fullmatch(
            r"SDVPlatformStack\.[A-Za-z_]\w*", group.maps_to
        ):
            continue
        part_name = group.maps_to.rsplit(".", 1)[-1]
        variation_body, variation_error = unique_direct_braced_body(
            stack_body,
            rf"\bvariation\s+part\s+{re.escape(part_name)}\b"
            rf"(?:\s*:\s*[A-Za-z_]\w*)?\s*",
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
    """Describe whether shared-asset bytes exactly match a Git revision."""
    resolved = Path(path).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    try:
        relative = resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return f"external:{resolved} (content hash authoritative)"

    try:
        source_commit = subprocess.check_output(
            [
                "git", "-C", str(repo_root), "log", "-1",
                "--format=%H", "--", relative,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not source_commit:
            return (
                f"untracked-or-unavailable:{relative} "
                "(content hash authoritative)"
            )
        committed = subprocess.check_output(
            [
                "git", "-C", str(repo_root), "show",
                f"{source_commit}:{relative}",
            ],
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return f"untracked-or-unavailable:{relative} (content hash authoritative)"

    if committed == resolved.read_bytes():
        return f"git:{source_commit}:{relative} (exact)"
    return (
        f"working-tree:{relative} "
        f"(differs from git:{source_commit}; hash authoritative)"
    )


# ──────────────────────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────────────────────

def generate_sysml(bof_name, bof_description, root, all_nodes, selections,
                   feature_model_path, bof_path, shared_model_path):
    """Generate a derived platform-stack product-model projection."""
    redefinitions = []
    capability_annotations = []

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

    for path, node in all_nodes.items():
        # Optional booleans without mapped assets remain provenance only.
        if (node.is_leaf() and node.type == "optional" and
                not node.maps_to_variant):
            sel = selections.get(node.path)
            if sel is not None:
                status = "enabled" if sel else "disabled"
                capability_annotations.append((node.path, status))

    # Build SysML output
    desc_clean = ""
    if bof_description:
        desc_clean = sysml_comment_text(bof_description.strip()).replace(
            "\n", "\n   * "
        )

    feature_model_hash = file_sha256(feature_model_path)
    bof_hash = file_sha256(bof_path)
    shared_model_hash = file_sha256(shared_model_path)
    source_baseline = shared_asset_baseline(shared_model_path)

    lines = [
        "/*",
        " * Derived platform-stack product-model projection — DO NOT EDIT.",
        " * Generated by configure_variant.py.",
        " * This is not a complete member-product specification.",
        f" * Shared-assets source baseline: {sysml_comment_text(source_baseline)}",
        f" * Shared-assets model: {sysml_comment_text(provenance_path(shared_model_path))}",
        f" * Shared-assets model SHA-256: {shared_model_hash}",
        f" * Feature model SHA-256: {feature_model_hash}",
        f" * Bill-of-Features SHA-256: {bof_hash}",
        f" * Regenerate from: {sysml_comment_text(provenance_path(bof_path))}",
        f" * Feature model: {sysml_comment_text(provenance_path(feature_model_path))}",
        " */",
        "",
        "private import DE4SDV_SDVPlatformStack::SDVPlatformStack;",
        "",
        f"part def {bof_name} :> SDVPlatformStack {{",
        "  doc /*",
        "   * Derived platform-stack projection from Bill-of-Features.",
    ]

    if desc_clean:
        lines.append(f"   * {desc_clean}")
    lines.append("   *")
    lines.append("   * Variant selections:")
    for part_name, variant_name in redefinitions:
        lines.append(
            f"   *   {sysml_comment_text(part_name)} = "
            f"{sysml_comment_text(variant_name)}"
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
        "--shared-assets-model",
        default=str(
            Path(__file__).resolve().parent.parent
            / "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml"
        ),
        help="SysML v2 shared-assets model used to verify feature mappings"
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
    all_nodes = collect_all_nodes(root)
    bof_name, bof_description, selections = parse_bof(bof_data)

    # Pass 1: Structural and mapping-metadata validation
    structural_errors = validate_structure(root, all_nodes, selections)
    bof_metadata_errors = validate_bof_metadata(bof_name, bof_description)
    mapping_errors = validate_platform_mapping_metadata(root)
    mapping_target_errors = validate_sysml_mapping_targets(
        root, args.shared_assets_model
    )
    # Pass 2: Constraint validation
    constraint_definition_errors = validate_constraint_definitions(
        constraints, all_nodes
    )
    constraint_errors = validate_constraints(constraints, selections)

    all_errors = (
        structural_errors + bof_metadata_errors + mapping_errors
        + mapping_target_errors + constraint_definition_errors
        + constraint_errors
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
        args.feature_model, args.bof, args.shared_assets_model
    )

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w") as f:
                f.write(sysml_output + "\n")
        except OSError as exc:
            sys.stderr.write(f"Error writing output: {exc}\n")
            sys.exit(2)
        sys.stderr.write(f"✓ Generated {output_path}\n")
    else:
        print(sysml_output)


if __name__ == "__main__":
    main()
