"""Gate A API-semantic evaluator for the bounded PLEML spike.

This module consumes only SysML API element objects.  It does not read or parse
textual notation.  Engineering identities are UUID references; names are used
only for the governed role schema of the spike extension.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PLEML_PIN = "5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e"
GATE_A_FIXTURE = Path("docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml")
PLEML_SOURCE = Path("external/pleml/PLEML/PLEML.sysml")


class GateASourceError(RuntimeError):
    """The spike checkout or exact-pinned source identity is invalid."""


class UnsupportedSemanticShape(ValueError):
    """The API graph is missing, ambiguous, or outside the proven shape."""


@dataclass(frozen=True)
class DerivationOutcome:
    configuration_id: str
    selected_feature_ids: frozenset[str]
    status: str
    derivation_attempted: bool
    constraint_ids: tuple[str, ...] = ()
    rule_ids: tuple[str, ...] = ()
    adapter_id: str | None = None


@dataclass(frozen=True)
class GateASourceIdentity:
    git_repository: str
    git_commit: str
    pleml_commit: str
    scope: str
    source_manifest: tuple[dict[str, object], ...]


def gate_a_source_identity(
    repository_root: Path, *, expected_pleml_commit: str = PLEML_PIN
) -> GateASourceIdentity:
    root = repository_root.resolve()
    git_repository = _git_output(root, "remote", "get-url", "origin")
    git_commit = _git_output(root, "rev-parse", "HEAD")
    pleml_root = root / "external/pleml"
    pleml_commit = _git_output(pleml_root, "rev-parse", "HEAD")
    if pleml_commit != expected_pleml_commit:
        raise GateASourceError(
            f"PLEML pin mismatch: expected {expected_pleml_commit}, got {pleml_commit}"
        )
    manifest = []
    for relative in (GATE_A_FIXTURE, PLEML_SOURCE):
        path = root / relative
        if not path.is_file():
            raise GateASourceError(f"Gate A source is missing: {relative.as_posix()}")
        data = path.read_bytes()
        manifest.append(
            {
                "path": relative.as_posix(),
                "authority": (
                    "fixture" if relative == GATE_A_FIXTURE else "pinned-dependency"
                ),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    return GateASourceIdentity(
        git_repository=git_repository,
        git_commit=git_commit,
        pleml_commit=pleml_commit,
        scope="fixture",
        source_manifest=tuple(manifest),
    )


def _resolve_bounds(
    feature_id: str, bound_values: list[tuple[bool, int | None]]
) -> tuple[int | None, int | None]:
    """Derive [lower..upper] from bound values without trusting param order.

    The official serializer does not guarantee that ParameterMembership order
    matches textual bound order (real evidence: ``[1..*]`` serialized with the
    LiteralInfinity parameter before the LiteralInteger 1). The derivation is
    therefore order-independent:

    - one integer bound ``N``: ``[N..N]``;
    - one LiteralInfinity: ``[0..*]``;
    - integer(s) + LiteralInfinity (2 bounds): lower = the integer, upper
      unbounded;
    - two integers: lower = min, upper = max (SysML requires lower <= upper);
    - anything else: fail closed.
    """

    integers = [value for is_inf, value in bound_values if not is_inf and value is not None]
    infinities = sum(1 for is_inf, _ in bound_values if is_inf)
    if len(bound_values) == 1:
        if infinities:
            return (0, None)
        assert integers
        return (integers[0], integers[0])
    if len(bound_values) == 2 and infinities == 1:
        return (integers[0], None)
    if len(bound_values) == 2 and not infinities:
        return (min(integers), max(integers))
    raise UnsupportedSemanticShape(
        f"multiplicity range of {feature_id} has an ambiguous bound set: {bound_values}"
    )


def build_observability_matrix(
    elements: Iterable[dict[str, Any]], element_sources: dict[str, str]
) -> tuple[dict[str, object], ...]:
    """Prove concept-specific semantic adequacy over official API objects.

    Every concept row must show, not merely assert: expected API metatype and
    form; UUID identity; the ownership/membership path; the endpoint and
    reference UUIDs it depends on; required semantic values (such as actual
    multiplicity bounds); and source provenance. A row fails closed when any
    required semantic is missing or ambiguous.

    The query predicates are fixture schema anchors, never product-line label
    inference.
    """

    values = tuple(elements)
    by_id: dict[str, dict[str, Any]] = {}
    for element in values:
        element_id = _ref_id(element)
        if element_id:
            by_id[element_id] = element

    def owned_member_ids(owner_id: str) -> list[str]:
        ids = []
        for membership in values:
            if membership.get("@type") not in {
                "FeatureMembership",
                "OwningMembership",
                "Membership",
            }:
                continue
            if _ref_id(membership.get("owningRelatedElement")) != owner_id:
                continue
            member_id = _ref_id(
                membership.get("memberElement")
                or membership.get("ownedRelatedElement")
            )
            if member_id:
                ids.append(member_id)
        return ids

    def multiplicity_of(feature_id: str) -> tuple[int | None, int | None]:
        """Resolve actual [lower..upper] values owned by a feature usage.

        Handles both observed official-serializer shapes: direct literal
        bounds owned by the ``MultiplicityRange`` and a range
        ``OperatorExpression`` whose parameters carry the bound literals.
        lower defaults to 1, upper to 1 (SysML v2 Feature defaults). The
        unbounded upper bound is serialized as LiteralInfinity.
        """

        def resolve_bound(bound: dict[str, Any]) -> tuple[bool, int | None]:
            if bound.get("@type") == "LiteralInfinity":
                return (True, None)
            value = bound.get("value")
            if not isinstance(value, int):
                raise UnsupportedSemanticShape(
                    f"multiplicity bound of {feature_id} lacks an integer value"
                )
            return (False, value)

        def range_operator_bounds(operator_id: str) -> list[tuple[bool, int | None]]:
            bounds: list[tuple[bool, int | None]] = []
            for parameter_membership in values:
                if parameter_membership.get("@type") != "ParameterMembership":
                    continue
                if (
                    _ref_id(parameter_membership.get("owningRelatedElement"))
                    != operator_id
                ):
                    continue
                parameter_id = _ref_id(
                    parameter_membership.get("memberElement")
                    or parameter_membership.get("ownedRelatedElement")
                )
                if not parameter_id:
                    raise UnsupportedSemanticShape(
                        f"range operator of {feature_id} has a null parameter"
                    )
                value_expressions = [
                    _ref_id(
                        item.get("memberElement")
                        or item.get("ownedRelatedElement")
                    )
                    for item in values
                    if item.get("@type") == "FeatureValue"
                    and _ref_id(item.get("owningRelatedElement")) == parameter_id
                ]
                value_expressions = [item for item in value_expressions if item]
                if len(value_expressions) != 1:
                    raise UnsupportedSemanticShape(
                        f"range parameter of {feature_id} has "
                        f"{len(value_expressions)} value expressions"
                    )
                expression = by_id.get(value_expressions[0])
                if not expression or expression.get("@type") not in (
                    "LiteralInteger",
                    "LiteralInfinity",
                ):
                    raise UnsupportedSemanticShape(
                        f"range parameter of {feature_id} is not a bound literal"
                    )
                bounds.append(resolve_bound(expression))
            if not bounds:
                raise UnsupportedSemanticShape(
                    f"range operator of {feature_id} carries no bound parameters"
                )
            return bounds

        lower: int | None = 1
        upper: int | None = 1
        found_range = False
        for relationship in values:
            if relationship.get("@type") not in {
                "OwningMembership",
                "FeatureMembership",
                "Membership",
            }:
                continue
            if _ref_id(relationship.get("owningRelatedElement")) != feature_id:
                continue
            member_id = _ref_id(
                relationship.get("memberElement")
                or relationship.get("ownedRelatedElement")
            )
            if not member_id:
                continue
            member = by_id.get(member_id)
            if not member or member.get("@type") != "MultiplicityRange":
                continue
            found_range = True
            bound_values: list[tuple[bool, int | None]] = []
            for bound_relationship in values:
                if bound_relationship.get("@type") != "OwningMembership":
                    continue
                if (
                    _ref_id(bound_relationship.get("owningRelatedElement"))
                    != member_id
                ):
                    continue
                bound_id = _ref_id(
                    bound_relationship.get("memberElement")
                    or bound_relationship.get("ownedRelatedElement")
                )
                if not bound_id:
                    continue
                bound = by_id.get(bound_id)
                if not bound:
                    continue
                if bound.get("@type") in ("LiteralInteger", "LiteralInfinity"):
                    bound_values.append(resolve_bound(bound))
                elif bound.get("@type") == "OperatorExpression":
                    bound_values.extend(range_operator_bounds(bound_id))
            if not bound_values:
                raise UnsupportedSemanticShape(
                    f"multiplicity range of {feature_id} carries no bound values"
                )
            lower, upper = _resolve_bounds(feature_id, bound_values)
        if not found_range:
            return (1, 1)
        return (lower, upper)

    def ownership_path(element_id: str, limit: int = 32) -> list[dict[str, str]]:
        path: list[dict[str, str]] = []
        current_id: str | None = element_id
        visited: set[str] = set()
        while current_id is not None and current_id not in visited and len(path) < limit:
            visited.add(current_id)
            element = by_id.get(current_id)
            if element is None:
                break
            owning_id = _ref_id(element.get("owningRelationship"))
            if not owning_id:
                break
            relationship = by_id.get(owning_id)
            if relationship is None:
                break
            path.append(
                {
                    "via_relationship_uuid": owning_id,
                    "via_relationship_type": relationship.get("@type", ""),
                    "owner_uuid": _ref_id(
                        relationship.get("owningRelatedElement")
                    )
                    or "",
                }
            )
            current_id = _ref_id(relationship.get("owningRelatedElement"))
        return path

    # concept name -> (anchor predicate, optional semantic verifier). The
    # verifier receives the matched anchor elements and the resolved element
    # graph and must raise UnsupportedSemanticShape on any missing or
    # ambiguous required semantic. It returns concept-specific proof entries
    # merged into the row.
    queries: tuple[tuple[str, Any, Any], ...] = (
        ("Feature model", lambda e: _named(e, "GateAFeatureModel"), None),
        ("Feature tree", lambda e: _named(e, "gateAFeatureTree"), None),
        ("Feature", lambda e: _named(e, "autoware"), None),
        (
            "Parent/child membership",
            lambda e: e.get("@type") == "FeatureMembership"
            and e.get("memberName") == "autoware",
            None,
        ),
        (
            "Exact-one multiplicity",
            lambda e: _named(e, "application"),
            None,
        ),
        (
            "Optional multiplicity",
            lambda e: _named(e, "remoteDiagnostics"),
            None,
        ),
        (
            "At-least-one/multi-select group",
            lambda e: _named(e, "sensorSuite"),
            None,
        ),
        (
            "Group member (radar)",
            lambda e: _named(e, "radar"),
            None,
        ),
        (
            "Group member (camera)",
            lambda e: _named(e, "camera"),
            None,
        ),
        (
            "Group multi-select resolution",
            lambda e: _named(e, "validBothSensors"),
            None,
        ),
        (
            "Group at-least-one resolution",
            lambda e: _named(e, "validOneSensor"),
            None,
        ),
        ("Lifecycle metadata", lambda e: _named(e, "bindingTime"), None),
        ("Feature configuration", lambda e: _named(e, "validAutowareAndroid"), None),
        (
            "Selected feature relationship",
            lambda e: e.get("@type") == "Redefinition"
            and _ref_id(e.get("redefinedFeature")) is not None,
            None,
        ),
        ("Requires relationship", lambda e: _named(e, "requiresFeatures"), None),
        ("Incompatibility constraint", lambda e: _named(e, "xorFeatures"), None),
        ("FeatureBinding", lambda e: _named(e, "gateASimpleFeatureBinding"), None),
        ("Native variation", lambda e: _named(e, "gateAAdapterVariation"), None),
        (
            "Owned variant",
            lambda e: e.get("@type") == "VariantMembership"
            and e.get("memberName") == "autowareToAAOSSDV",
            None,
        ),
        (
            "Common capability outside feature tree",
            lambda e: _named(e, "gateACommonCoreAsset"),
            None,
        ),
        (
            "Native constraint expression probe",
            lambda e: _named(e, "NativeAdapterImplicationProbe"),
            None,
        ),
        ("Adapter realization rule", lambda e: _named(e, "autowareAndroidRule"), None),
    )

    # Semantic expectations verified against the resolved graph, independent
    # of which anchor element matched. Each entry: (concept, checker). A
    # checker raises UnsupportedSemanticShape when required semantics are
    # missing or ambiguous.
    def _check_multiplicity(
        name: str, expected_lower: int | None, expected_upper: int | None
    ) -> None:
        element = _tree_feature(name)
        element_id = _ref_id(element)
        if not element_id:
            raise UnsupportedSemanticShape(f"{name} feature has no UUID")
        lower, upper = multiplicity_of(element_id)
        if (lower, upper) != (expected_lower, expected_upper):
            raise UnsupportedSemanticShape(
                f"{name} multiplicity is [{lower}..{upper}], "
                f"expected [{expected_lower}..{expected_upper}]"
            )
        if not ownership_path(element_id):
            raise UnsupportedSemanticShape(f"{name} has no ownership path")

    def _tree_feature(name: str) -> dict[str, Any]:
        """Find a feature usage owned directly by the feature tree.

        Feature names recur on configuration selection children and constraint
        parameters, so tree ownership scopes the identity lookup.
        """

        tree = [e for e in values if _named(e, "gateAFeatureTree")]
        if len(tree) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one gateAFeatureTree, found {len(tree)}"
            )
        tree_id = _ref_id(tree[0])
        if not tree_id:
            raise UnsupportedSemanticShape("gateAFeatureTree has no UUID")
        usage_types = {"OccurrenceUsage", "PartUsage", "AttributeUsage"}
        matches = []
        for member_id in owned_member_ids(tree_id):
            member = by_id.get(member_id)
            if not member or member.get("@type") not in usage_types:
                continue
            if _named(member, name):
                matches.append(member)
        if len(matches) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one tree feature named {name}, found {len(matches)}"
            )
        return matches[0]

    def _check_group_members() -> None:
        suite = _tree_feature("sensorSuite")
        suite_id = _ref_id(suite)
        if not suite_id:
            raise UnsupportedSemanticShape("sensorSuite feature has no UUID")
        usage_types = {"OccurrenceUsage", "PartUsage", "AttributeUsage"}
        member_ids = {
            member_id
            for member_id in owned_member_ids(suite_id)
            if (member := by_id.get(member_id))
            and member.get("@type") in usage_types
        }
        for member_name in ("radar", "camera"):
            member = _tree_feature(member_name)
            member_id = _ref_id(member)
            if not member_id:
                raise UnsupportedSemanticShape(f"{member_name} has no UUID")
            # Group membership is expressed as Subsetting (radar :>
            # sensorSuite), not tree ownership; verify the specialization
            # relationship by UUID.
            specializations = {
                _ref_id(item.get("subsettedFeature") or item.get("general"))
                for item in values
                if item.get("@type") in {"Subsetting", "Redefinition"}
                and _ref_id(
                    item.get("subsettingFeature") or item.get("specific")
                )
                == member_id
            }
            specializations.discard(None)
            if suite_id not in specializations:
                raise UnsupportedSemanticShape(
                    f"{member_name} does not specialize sensorSuite by UUID"
                )
            member_ids.discard(member_id)
        # radar/camera each declare their own [0..1] ranges as owned parts;
        # nothing else may own membership under the group beyond those two.
        if member_ids:
            raise UnsupportedSemanticShape(
                f"sensorSuite has unexpected owned members: {sorted(member_ids)}"
            )

    def _check_group_resolution(config_name: str, expected_members: tuple[str, ...]) -> None:
        configs = [e for e in values if _named(e, config_name)]
        if len(configs) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one {config_name}, found {len(configs)}"
            )
        config_id = _ref_id(configs[0])
        if not config_id:
            raise UnsupportedSemanticShape(f"{config_name} has no UUID")
        selections: dict[str, set[str]] = {}
        for child_id in owned_member_ids(config_id):
            child = by_id.get(child_id)
            if not child:
                continue
            redefinition_targets = {
                _ref_id(item.get("redefinedFeature") or item.get("general"))
                for item in values
                if item.get("@type") == "Redefinition"
                and _ref_id(item.get("owningRelatedElement")) == child_id
            }
            redefinition_targets.discard(None)
            if not redefinition_targets:
                continue
            if len(redefinition_targets) != 1:
                raise UnsupportedSemanticShape(
                    f"{config_name} selection {child_id} has ambiguous targets"
                )
            target_id = next(iter(redefinition_targets))
            target = by_id.get(target_id or "")
            target_name = (
                target.get("declaredName") or target.get("name")
                if target
                else None
            )
            if target_name:
                selections.setdefault(target_name, set()).add(target_id or "")
        for member_name in expected_members:
            if member_name not in selections:
                raise UnsupportedSemanticShape(
                    f"{config_name} does not resolve required group member "
                    f"{member_name}"
                )
        if "sensorSuite" not in selections:
            raise UnsupportedSemanticShape(
                f"{config_name} does not resolve the sensorSuite group"
            )

    def _constraint_chain(base_name: str) -> tuple[str, str]:
        """Resolve (base UUID, redefining UUID) for a PLEML constraint usage.

        The pinned PLEML library declares the base usage; the fixture's
        ``assert constraint :>> <name>`` serializes a second usage carrying the
        same name (the redefining one). The pair is therefore resolved by
        source provenance and verified through the Redefinition relationship,
        never by name alone.
        """

        base_matches = [
            e
            for e in values
            if _named(e, base_name)
            and element_sources.get(_ref_id(e) or "") == "external/pleml/PLEML/PLEML.sysml"
        ]
        actual_matches = [
            e
            for e in values
            if _named(e, base_name)
            and element_sources.get(_ref_id(e) or "") == "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml"
        ]
        if len(base_matches) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one {base_name} base usage in the pinned "
                f"PLEML source, found {len(base_matches)}"
            )
        if len(actual_matches) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one {base_name} redefining usage in the "
                f"fixture, found {len(actual_matches)}"
            )
        base_id = _ref_id(base_matches[0])
        actual_id = _ref_id(actual_matches[0])
        if not base_id or not actual_id:
            raise UnsupportedSemanticShape(
                f"{base_name} constraint chain has a null UUID"
            )
        redefinitions = [
            e
            for e in values
            if e.get("@type") == "Redefinition"
            and _ref_id(e.get("redefinedFeature") or e.get("general")) == base_id
            and _ref_id(e.get("redefiningFeature") or e.get("specific")) == actual_id
        ]
        if len(redefinitions) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one Redefinition linking {base_name} base "
                f"to the fixture usage, found {len(redefinitions)}"
            )
        actual = by_id.get(actual_id)
        if not actual or actual.get("@type") != "AssertConstraintUsage":
            raise UnsupportedSemanticShape(
                f"{base_name} fixture usage is not an AssertConstraintUsage"
            )
        return base_id, actual_id

    def _role_target(owner_id: str, role_name: str) -> str:
        """Resolve a named role's UUID through the observed reference chain.

        Chain (real-serializer evidence): owning membership named
        ``role_name`` -> role usage -> ``FeatureValue`` ->
        ``FeatureReferenceExpression`` -> ``Membership`` -> target feature.
        """

        role_ids = [
            _ref_id(m.get("memberElement") or m.get("ownedRelatedElement"))
            for m in values
            if m.get("@type")
            in ("FeatureMembership", "OwningMembership", "Membership")
            and m.get("memberName") == role_name
            and _ref_id(m.get("owningRelatedElement")) == owner_id
        ]
        role_ids = [item for item in role_ids if item]
        if len(role_ids) != 1:
            raise UnsupportedSemanticShape(
                f"{owner_id} has {len(role_ids)} {role_name} role usages"
            )
        role_id = role_ids[0]
        value_ids = [
            _ref_id(item.get("memberElement") or item.get("ownedRelatedElement"))
            for item in values
            if item.get("@type") == "FeatureValue"
            and _ref_id(item.get("owningRelatedElement")) == role_id
        ]
        value_ids = [item for item in value_ids if item]
        if len(value_ids) != 1:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} has {len(value_ids)} value expressions"
            )
        expression = by_id.get(value_ids[0])
        if not expression or expression.get("@type") != "FeatureReferenceExpression":
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} is not a feature reference expression"
            )
        targets = [
            _ref_id(m.get("memberElement"))
            for m in values
            if m.get("@type") == "Membership"
            and _ref_id(m.get("owningRelatedElement")) == value_ids[0]
        ]
        targets = [item for item in targets if item]
        if len(targets) != 1:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} reference has {len(targets)} targets"
            )
        return targets[0]

    def _check_incompatibility_shape() -> None:
        base_id, actual_id = _constraint_chain("xorFeatures")
        excluded_id = _role_target(actual_id, "excluded")
        excluded_element = by_id.get(excluded_id)
        if not excluded_element or not _named(excluded_element, "androidSDV"):
            raise UnsupportedSemanticShape(
                "xorFeatures excluded feature is not the fixture's androidSDV"
            )

    def _check_requires_shape() -> None:
        _constraint_chain("requiresFeatures")

    def _check_binding_endpoints() -> None:
        bindings = [e for e in values if _named(e, "gateASimpleFeatureBinding")]
        if len(bindings) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one FeatureBinding dependency, found {len(bindings)}"
            )
        binding = bindings[0]
        if binding.get("@type") != "Dependency":
            raise UnsupportedSemanticShape(
                f"FeatureBinding serialized as {binding.get('@type')}, expected Dependency"
            )

        def role_targets(role: str) -> set[str]:
            # Reference paths carry the list index (e.g. "source[0]"); match
            # on the property base name.
            return {
                item["target_uuid"]
                for item in _reference_paths(binding)
                if item["property_path"].split("[")[0] == role
            }

        source_targets = role_targets("source") | role_targets("client")
        target_targets = role_targets("target") | role_targets("supplier")
        if len(source_targets) != 1:
            raise UnsupportedSemanticShape(
                f"FeatureBinding source endpoint missing or ambiguous: {source_targets}"
            )
        if len(target_targets) != 1:
            raise UnsupportedSemanticShape(
                f"FeatureBinding target endpoint missing or ambiguous: {target_targets}"
            )
        source_element = by_id.get(next(iter(source_targets)))
        target_element = by_id.get(next(iter(target_targets)))
        if not source_element or not _named(source_element, "gateASimpleBoundAsset"):
            raise UnsupportedSemanticShape(
                "FeatureBinding source endpoint is not gateASimpleBoundAsset"
            )
        if not target_element or not _named(target_element, "autoware"):
            raise UnsupportedSemanticShape(
                "FeatureBinding target endpoint is not the autoware feature"
            )

    def _check_variant_membership() -> None:
        memberships = [
            e
            for e in values
            if e.get("@type") == "VariantMembership"
            and e.get("memberName") == "autowareToAAOSSDV"
        ]
        if len(memberships) != 1:
            raise UnsupportedSemanticShape(
                f"expected exactly one autowareToAAOSSDV VariantMembership, "
                f"found {len(memberships)}"
            )
        member_id = _ref_id(memberships[0].get("memberElement"))
        member = by_id.get(member_id or "")
        if not member or not _named(member, "autowareToAAOSSDV"):
            raise UnsupportedSemanticShape(
                "VariantMembership memberElement is not autowareToAAOSSDV"
            )
        variation = [
            e for e in values if _named(e, "gateAAdapterVariation")
        ]
        if len(variation) != 1:
            raise UnsupportedSemanticShape("adapter variation anchor missing")
        variation_id = _ref_id(variation[0])
        variant_member_ids = {
            _ref_id(item.get("memberElement"))
            for item in values
            if item.get("@type") == "VariantMembership"
            and _ref_id(item.get("owningRelatedElement")) == variation_id
        }
        if member_id not in variant_member_ids:
            raise UnsupportedSemanticShape(
                "autowareToAAOSSDV is not a variant of gateAAdapterVariation"
            )

    semantic_checks: tuple[tuple[str, Any], ...] = (
        ("Exact-one multiplicity", lambda: _check_multiplicity("application", 1, 1)),
        ("Optional multiplicity", lambda: _check_multiplicity("remoteDiagnostics", 0, 1)),
        (
            "At-least-one/multi-select group",
            lambda: _check_multiplicity("sensorSuite", 1, None),
        ),
        (
            "Group member (radar)",
            lambda: _check_multiplicity("radar", 0, 1),
        ),
        ("Group member (camera)", lambda: _check_multiplicity("camera", 0, 1)),
        (
            "At-least-one/multi-select group",
            _check_group_members,
        ),
        (
            "Group multi-select resolution",
            lambda: _check_group_resolution("validBothSensors", ("radar", "camera")),
        ),
        (
            "Group at-least-one resolution",
            lambda: _check_group_resolution("validOneSensor", ("radar",)),
        ),
        ("Incompatibility constraint", _check_incompatibility_shape),
        ("Requires relationship", _check_requires_shape),
        ("FeatureBinding", _check_binding_endpoints),
        ("Owned variant", _check_variant_membership),
    )

    rows = []
    for concept, predicate, _ in queries:
        matches = [element for element in values if predicate(element)]
        if not matches:
            raise UnsupportedSemanticShape(
                f"observability matrix has no API anchor for {concept}: "
                f"GateAFeatureModel fixture is incomplete or lossy"
            )
        evidence = []
        for element in sorted(matches, key=lambda item: str(item.get("@id", ""))):
            element_id = _ref_id(element)
            if not element_id:
                raise UnsupportedSemanticShape(f"{concept} anchor has no UUID")
            lower, upper = multiplicity_of(element_id)
            evidence.append(
                {
                    "uuid": element_id,
                    "metatype": element.get("@type"),
                    "name": element.get("declaredName") or element.get("name"),
                    "property_keys": sorted(element),
                    "reference_paths": _reference_paths(element),
                    "ownership_path": ownership_path(element_id),
                    "resolved_multiplicity": {
                        "lower": lower,
                        "upper": upper,
                        "upper_unbounded": upper is None,
                    },
                    "source": element_sources.get(element_id),
                }
            )
        object_observable = bool(evidence)
        provenance_retained = all(item["source"] for item in evidence)
        rows.append(
            {
                "concept": concept,
                "object_observable": object_observable,
                "semantic_properties_retained": None,
                "provenance_retained": provenance_retained,
                "api_only_consumption_adequate": None,
                "exact_gap": ""
                if provenance_retained
                else "source provenance missing",
                "evidence": evidence,
            }
        )

    # Run the fail-closed semantic checks; a failing check marks its concept
    # row as not adequate with the exact gap recorded. A concept may have
    # multiple checks; any failure marks the row inadequate, so apply results
    # in two passes (collect, then commit) to avoid ordering effects.
    by_concept = {row["concept"]: row for row in rows}
    check_results: dict[str, tuple[bool, str]] = {}
    for check_concept, checker in semantic_checks:
        try:
            checker()
        except UnsupportedSemanticShape as exc:
            prior_passed, prior_gap = check_results.get(check_concept, (True, ""))
            check_results[check_concept] = (False, prior_gap or str(exc))
        else:
            check_results.setdefault(check_concept, (True, ""))
    for check_concept, (passed, gap) in check_results.items():
        row = by_concept.get(check_concept)
        if row is None:
            continue
        if passed:
            row["semantic_properties_retained"] = True
            row["api_only_consumption_adequate"] = row["provenance_retained"]
        else:
            row["semantic_properties_retained"] = False
            row["api_only_consumption_adequate"] = False
            row["exact_gap"] = gap

    for row in rows:
        if row["api_only_consumption_adequate"] is None:
            row["api_only_consumption_adequate"] = False
            if not row["exact_gap"]:
                row["exact_gap"] = (
                    "no concept-specific semantic check proven this row adequate"
                )
        if row["semantic_properties_retained"] is None:
            row["semantic_properties_retained"] = False
    return tuple(rows)


class GateAModel:
    """Fail-closed resolver over official serializer/API element objects."""

    def __init__(self, elements: Iterable[dict[str, Any]]) -> None:
        self.elements = tuple(elements)
        self.by_id: dict[str, dict[str, Any]] = {}
        for element in self.elements:
            element_id = _ref_id(element)
            element_type = element.get("@type")
            if not element_id or not isinstance(element_type, str):
                raise UnsupportedSemanticShape("every API element requires @id and @type")
            if element_id in self.by_id:
                raise UnsupportedSemanticShape(f"duplicate API element UUID: {element_id}")
            self.by_id[element_id] = element

    def evaluate(
        self, configuration_id: str, *, rule_set_id: str | None = None
    ) -> DerivationOutcome:
        selected = self.selected_feature_ids(configuration_id)
        invalidating = tuple(
            sorted(
                constraint_id
                for constraint_id, owner_id, excluded_id in self._incompatibilities()
                if owner_id in selected and excluded_id in selected
            )
        )
        if invalidating:
            return DerivationOutcome(
                configuration_id=configuration_id,
                selected_feature_ids=selected,
                status="configuration-invalid",
                derivation_attempted=False,
                constraint_ids=invalidating,
            )

        candidate_rule_ids = set(
            self._typed_usage_ids(
            "AdapterRealizationRule", "OccurrenceDefinition"
            )
        )
        if rule_set_id is not None:
            self._require(rule_set_id)
            candidate_rule_ids &= set(self._owned_member_ids(rule_set_id))
        matching: list[tuple[str, str | None]] = []
        for rule_id in sorted(candidate_rule_ids):
            required = {
                self._required_role(rule_id, "requiredApplication"),
                self._required_role(rule_id, "requiredMiddleware"),
            }
            if required <= selected:
                matching.append((rule_id, self._optional_role(rule_id, "resultingAdapter")))

        if not matching:
            return DerivationOutcome(
                configuration_id=configuration_id,
                selected_feature_ids=selected,
                status="derivation-incomplete",
                derivation_attempted=True,
            )
        if len(matching) > 1:
            return DerivationOutcome(
                configuration_id=configuration_id,
                selected_feature_ids=selected,
                status="derivation-ambiguous",
                derivation_attempted=True,
                rule_ids=tuple(sorted(rule_id for rule_id, _ in matching)),
            )
        rule_id, adapter_id = matching[0]
        return DerivationOutcome(
            configuration_id=configuration_id,
            selected_feature_ids=selected,
            status="derivation-complete",
            derivation_attempted=True,
            rule_ids=(rule_id,),
            adapter_id=adapter_id,
        )

    def group_resolutions(self, configuration_id: str) -> dict[str, tuple[str, ...]]:
        """Resolve at-least-one/multi-select feature groups for a configuration.

        Returns each group's selected member UUIDs. Fails closed when a
        group's lower bound (at-least-one) is violated. The empty-group case
        surfaces as an invalidating group rather than a silent pass.
        """

        configuration = self._require(configuration_id)
        selected = self.selected_feature_ids(configuration_id)
        resolutions: dict[str, tuple[str, ...]] = {}
        for group_id in self._group_ids():
            group = self._require(group_id)
            lower, upper = self._multiplicity(group_id)
            members = sorted(selected & set(self._group_member_ids(group_id)))
            if len(members) < lower:
                raise UnsupportedSemanticShape(
                    f"group {group_id} selects {len(members)} members, "
                    f"violating its [{lower}..{'*' if upper is None else upper}] "
                    f"at-least-one bound in configuration {configuration_id}"
                )
            if upper is not None and len(members) > upper:
                raise UnsupportedSemanticShape(
                    f"group {group_id} selects {len(members)} members, "
                    f"exceeding its [{lower}..{upper}] bound in configuration "
                    f"{configuration_id}"
                )
            resolutions[str(group.get("declaredName") or group.get("name"))] = tuple(
                members
            )
        return resolutions

    def _group_ids(self) -> tuple[str, ...]:
        """Group features have an unbounded upper multiplicity ([N..*]).

        Restricted to usages owned by the fixture feature tree so PLEML's own
        unbounded containers (featureConfigurations, featureTrees,
        featureModels) are never mistaken for feature groups.
        """

        tree_ids = {
            element_id
            for element_id, element in self.by_id.items()
            if _named(element, "gateAFeatureTree")
        }
        groups = []
        for element_id, element in self.by_id.items():
            if element.get("@type") not in {"OccurrenceUsage", "PartUsage"}:
                continue
            owner_ids = {
                _ref_id(item.get("owningRelatedElement"))
                for item in self.elements
                if item.get("@type") == "FeatureMembership"
                and _ref_id(item.get("memberElement")) == element_id
            }
            if not owner_ids & tree_ids:
                continue
            lower, upper = self._multiplicity(element_id)
            if upper is None and lower >= 1:
                groups.append(element_id)
        return tuple(sorted(groups))

    def _group_member_ids(self, group_id: str) -> set[str]:
        """Members of a feature group specialize it via Subsetting.

        ``#feature occurrence radar[0..1] :> sensorSuite`` serializes as a
        Subsetting (or its Redefinition subclass) whose general/subsetted
        feature is the group and whose specific/subsetting feature is the
        member.
        """

        members: set[str] = set()
        for relationship in self.elements:
            if relationship.get("@type") not in {"Subsetting", "Redefinition"}:
                continue
            general_id = _ref_id(
                relationship.get("subsettedFeature") or relationship.get("general")
            )
            if general_id != group_id:
                continue
            specific_id = _ref_id(
                relationship.get("subsettingFeature") or relationship.get("specific")
            )
            if not specific_id:
                raise UnsupportedSemanticShape(
                    f"Subsetting {relationship.get('@id')} has no member feature UUID"
                )
            member = self.by_id.get(specific_id)
            if member and member.get("@type") in {
                "OccurrenceUsage",
                "PartUsage",
                "AttributeUsage",
            }:
                members.add(specific_id)
        return members

    def _multiplicity(self, element_id: str) -> tuple[int, int | None]:
        """Resolve a usage's [lower..upper] bounds from its owned range.

        The official serializer emits two observed range shapes:

        - direct bounds: ``MultiplicityRange`` owning ``LiteralInteger`` /
          ``LiteralInfinity`` children (the single-literal ``[N..N]`` case);
        - a range operator: ``MultiplicityRange`` owning an
          ``OperatorExpression`` (``..``) whose parameters carry the bound
          literals through ``FeatureValue`` expressions.

        Both are resolved here; anything else fails closed.
        """

        lower: int = 1
        upper: int | None = 1
        found_range = False
        for relationship in self.elements:
            if relationship.get("@type") not in {
                "OwningMembership",
                "FeatureMembership",
                "Membership",
            }:
                continue
            if _ref_id(relationship.get("owningRelatedElement")) != element_id:
                continue
            member_id = _ref_id(
                relationship.get("memberElement")
                or relationship.get("ownedRelatedElement")
            )
            if not member_id:
                continue
            member = self.by_id.get(member_id)
            if not member or member.get("@type") != "MultiplicityRange":
                continue
            found_range = True
            bound_values: list[tuple[bool, int | None]] = []
            for bound_relationship in self.elements:
                if bound_relationship.get("@type") != "OwningMembership":
                    continue
                if (
                    _ref_id(bound_relationship.get("owningRelatedElement"))
                    != member_id
                ):
                    continue
                bound_id = _ref_id(
                    bound_relationship.get("memberElement")
                    or bound_relationship.get("ownedRelatedElement")
                )
                if not bound_id:
                    continue
                bound = self.by_id.get(bound_id)
                if not bound:
                    continue
                if bound.get("@type") in ("LiteralInteger", "LiteralInfinity"):
                    bound_values.append(self._bound_value(element_id, bound))
                elif bound.get("@type") == "OperatorExpression":
                    bound_values.extend(
                        self._range_operator_bounds(element_id, bound_id)
                    )
            if not bound_values:
                raise UnsupportedSemanticShape(
                    f"multiplicity range of {element_id} carries no bound values"
                )
            resolved_lower, resolved_upper = _resolve_bounds(element_id, bound_values)
            lower = resolved_lower if resolved_lower is not None else 0
            upper = resolved_upper
        if not found_range:
            return (1, 1)
        return (lower, upper)

    def _bound_value(
        self, element_id: str, bound: dict[str, Any]
    ) -> tuple[bool, int | None]:
        if bound.get("@type") == "LiteralInfinity":
            return (True, None)
        value = bound.get("value")
        if not isinstance(value, int):
            raise UnsupportedSemanticShape(
                f"multiplicity bound of {element_id} lacks an integer value"
            )
        return (False, value)

    def _range_operator_bounds(
        self, element_id: str, operator_id: str
    ) -> list[tuple[bool, int | None]]:
        bounds: list[tuple[bool, int | None]] = []
        for parameter_membership in self.elements:
            if parameter_membership.get("@type") != "ParameterMembership":
                continue
            if (
                _ref_id(parameter_membership.get("owningRelatedElement"))
                != operator_id
            ):
                continue
            parameter_id = _ref_id(
                parameter_membership.get("memberElement")
                or parameter_membership.get("ownedRelatedElement")
            )
            if not parameter_id:
                raise UnsupportedSemanticShape(
                    f"range operator of {element_id} has a null parameter"
                )
            value_expressions = [
                _ref_id(item.get("memberElement") or item.get("ownedRelatedElement"))
                for item in self.elements
                if item.get("@type") == "FeatureValue"
                and _ref_id(item.get("owningRelatedElement")) == parameter_id
            ]
            value_expressions = [item for item in value_expressions if item]
            if len(value_expressions) != 1:
                raise UnsupportedSemanticShape(
                    f"range parameter of {element_id} has "
                    f"{len(value_expressions)} value expressions"
                )
            expression = self.by_id.get(value_expressions[0])
            if not expression or expression.get("@type") not in (
                "LiteralInteger",
                "LiteralInfinity",
            ):
                raise UnsupportedSemanticShape(
                    f"range parameter of {element_id} is not a bound literal"
                )
            bounds.append(self._bound_value(element_id, expression))
        if not bounds:
            raise UnsupportedSemanticShape(
                f"range operator of {element_id} carries no bound parameters"
            )
        return bounds

    def selected_feature_ids(self, configuration_id: str) -> frozenset[str]:
        configuration = self._require(configuration_id)
        if configuration.get("@type") not in {"OccurrenceUsage", "PartUsage"}:
            raise UnsupportedSemanticShape(
                f"configuration {configuration_id} has unsupported type "
                f"{configuration.get('@type')}"
            )
        selected: set[str] = set()
        for child_id in self._owned_member_ids(configuration_id):
            child = self._require(child_id)
            if child.get("@type") not in {"OccurrenceUsage", "PartUsage"}:
                continue
            redefinitions = self._owned_relationships(child_id, "Redefinition")
            if not redefinitions:
                continue
            targets = {
                _ref_id(item.get("redefinedFeature") or item.get("general"))
                for item in redefinitions
            }
            targets.discard(None)
            if len(targets) != 1:
                raise UnsupportedSemanticShape(
                    f"configuration selection {child_id} has ambiguous redefinition targets"
                )
            target = next(iter(targets))
            if target is None:
                raise UnsupportedSemanticShape(
                    f"configuration selection {child_id} has a null target"
                )
            self._require(target)
            selected.add(target)
        if not selected:
            raise UnsupportedSemanticShape(
                f"configuration {configuration_id} has no UUID-backed selected features"
            )
        return frozenset(selected)

    def _typed_usage_ids(self, definition_name: str, definition_type: str) -> tuple[str, ...]:
        definition_id = self._unique_named(definition_name, definition_type)
        usages: set[str] = set()
        for relationship in self.elements:
            if relationship.get("@type") != "FeatureTyping":
                continue
            target = _ref_id(relationship.get("type") or relationship.get("general"))
            if target != definition_id:
                continue
            usage_id = _ref_id(
                relationship.get("typedFeature") or relationship.get("specific")
            )
            if not usage_id:
                raise UnsupportedSemanticShape(
                    f"FeatureTyping {relationship['@id']} has no typed feature UUID"
                )
            self._require(usage_id)
            usages.add(usage_id)
        return tuple(sorted(usages))

    def _incompatibilities(self) -> tuple[tuple[str, str, str], ...]:
        constraints: list[tuple[str, str, str]] = []
        custom_definitions = self._named_ids(
            "GateAIncompatibilityConstraint", "ConstraintDefinition"
        )
        if len(custom_definitions) > 1:
            raise UnsupportedSemanticShape(
                "multiple GateAIncompatibilityConstraint definitions"
            )
        if custom_definitions:
            for constraint_id in self._typed_usage_ids(
                "GateAIncompatibilityConstraint", "ConstraintDefinition"
            ):
                constraints.append(
                    (
                        constraint_id,
                        self._required_role(constraint_id, "owningFeature"),
                        self._required_role(constraint_id, "excludedFeature"),
                    )
                )

        xor_definitions = self._named_ids("XORConstraint", "ConstraintDefinition")
        if len(xor_definitions) > 1:
            raise UnsupportedSemanticShape("multiple PLEML XORConstraint definitions")
        if xor_definitions:
            base_ids = set(self._typed_usage_ids("XORConstraint", "ConstraintDefinition"))
            base_ids = {
                base_id
                for base_id in base_ids
                if _named(self._require(base_id), "xorFeatures")
            }
            if len(base_ids) != 1:
                raise UnsupportedSemanticShape(
                    f"expected one PLEML xorFeatures usage, found {len(base_ids)}"
                )
            base_id = next(iter(base_ids))
            for candidate_id, candidate in self.by_id.items():
                if candidate.get("@type") != "AssertConstraintUsage":
                    continue
                redefinitions = self._owned_relationships(candidate_id, "Redefinition")
                if not any(
                    _ref_id(item.get("redefinedFeature") or item.get("general"))
                    == base_id
                    for item in redefinitions
                ):
                    continue
                owner_ids = {
                    _ref_id(membership.get("owningRelatedElement"))
                    for membership in self.elements
                    if membership.get("@type") == "FeatureMembership"
                    and _ref_id(membership.get("memberElement")) == candidate_id
                }
                owner_ids.discard(None)
                if len(owner_ids) != 1:
                    raise UnsupportedSemanticShape(
                        f"PLEML xor constraint {candidate_id} has {len(owner_ids)} owners"
                    )
                owner_id = next(iter(owner_ids))
                if owner_id is None:
                    raise UnsupportedSemanticShape(
                        f"PLEML xor constraint {candidate_id} has a null owner"
                    )
                constraints.append(
                    (
                        candidate_id,
                        owner_id,
                        self._required_role(candidate_id, "excluded"),
                    )
                )
        if not constraints:
            raise UnsupportedSemanticShape(
                "no UUID-backed incompatibility constraint representation is observable"
            )
        return tuple(sorted(constraints))

    def _required_role(self, owner_id: str, role_name: str) -> str:
        target = self._optional_role(owner_id, role_name)
        if target is None:
            raise UnsupportedSemanticShape(
                f"{owner_id} has no UUID-backed {role_name} reference"
            )
        return target

    def _optional_role(self, owner_id: str, role_name: str) -> str | None:
        role_ids = []
        for membership in self._owned_memberships(owner_id):
            if membership.get("memberName") != role_name:
                continue
            member_id = _ref_id(
                membership.get("memberElement") or membership.get("ownedRelatedElement")
            )
            if member_id:
                role_ids.append(member_id)
        if len(role_ids) > 1:
            raise UnsupportedSemanticShape(
                f"{owner_id} has ambiguous {role_name} role usages: {sorted(role_ids)}"
            )
        if not role_ids:
            return None
        role_id = role_ids[0]
        self._require(role_id)
        values = self._owned_relationships(role_id, "FeatureValue")
        if len(values) != 1:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} requires exactly one FeatureValue"
            )
        expression_id = _ref_id(
            values[0].get("memberElement") or values[0].get("ownedRelatedElement")
        )
        if not expression_id:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} FeatureValue has no expression UUID"
            )
        expression = self._require(expression_id)
        if expression.get("@type") != "FeatureReferenceExpression":
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} uses unsupported expression "
                f"{expression.get('@type')}"
            )
        targets = {
            _ref_id(membership.get("memberElement"))
            for membership in self._owned_memberships(expression_id)
        }
        targets.discard(None)
        if len(targets) != 1:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} reference expression has "
                f"{len(targets)} targets"
            )
        target = next(iter(targets))
        if target is None:
            raise UnsupportedSemanticShape(
                f"{owner_id}.{role_name} reference expression has a null target"
            )
        self._require(target)
        return target

    def _unique_named(self, name: str, element_type: str) -> str:
        matches = self._named_ids(name, element_type)
        if len(matches) != 1:
            raise UnsupportedSemanticShape(
                f"expected one {element_type} named {name}, found {len(matches)}"
            )
        return matches[0]

    def _named_ids(self, name: str, element_type: str) -> list[str]:
        return [
            element_id
            for element_id, element in self.by_id.items()
            if element.get("@type") == element_type
            and (element.get("declaredName") or element.get("name")) == name
        ]

    def _owned_member_ids(self, owner_id: str) -> tuple[str, ...]:
        ids = []
        for membership in self._owned_memberships(owner_id):
            member_id = _ref_id(
                membership.get("memberElement") or membership.get("ownedRelatedElement")
            )
            if member_id:
                ids.append(member_id)
        return tuple(ids)

    def _owned_memberships(self, owner_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            element
            for element in self.elements
            if element.get("@type")
            in {"FeatureMembership", "OwningMembership", "Membership"}
            and _ref_id(element.get("owningRelatedElement")) == owner_id
        )

    def _owned_relationships(
        self, owner_id: str, relationship_type: str
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            element
            for element in self.elements
            if element.get("@type") == relationship_type
            and _ref_id(element.get("owningRelatedElement")) == owner_id
        )

    def _require(self, element_id: str) -> dict[str, Any]:
        try:
            return self.by_id[element_id]
        except KeyError as exc:
            raise UnsupportedSemanticShape(
                f"API reference targets missing UUID: {element_id}"
            ) from exc


def _ref_id(value: object) -> str | None:
    if isinstance(value, dict):
        candidate = value.get("@id") or value.get("elementId") or value.get("id")
        if isinstance(candidate, str) and candidate:
            return candidate
    if isinstance(value, list) and len(value) == 1:
        return _ref_id(value[0])
    return None


def _named(element: dict[str, Any], name: str) -> bool:
    return (element.get("declaredName") or element.get("name")) == name


def _git_output(repository: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), *args], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GateASourceError(
            f"cannot establish Git identity for {repository}: {exc}"
        ) from exc


def _reference_paths(value: object, path: str = "") -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    if isinstance(value, dict):
        if "@id" in value and "@type" not in value:
            target = value.get("@id")
            if isinstance(target, str):
                references.append({"property_path": path, "target_uuid": target})
            return references
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            references.extend(_reference_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            references.extend(_reference_paths(item, f"{path}[{index}]"))
    return references
