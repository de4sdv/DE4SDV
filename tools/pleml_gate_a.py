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


def build_observability_matrix(
    elements: Iterable[dict[str, Any]], element_sources: dict[str, str]
) -> tuple[dict[str, object], ...]:
    """Describe exact official-API shapes for the bounded Gate A concepts.

    The query predicates are fixture schema anchors, never product-line label
    inference.  Each matching row records actual UUIDs, metatypes, property
    keys, source paths, and every direct reference property path.
    """

    values = tuple(elements)
    queries: tuple[tuple[str, Any], ...] = (
        ("Feature model", lambda e: _named(e, "GateAFeatureModel")),
        ("Feature tree", lambda e: _named(e, "gateAFeatureTree")),
        ("Feature", lambda e: _named(e, "autoware")),
        (
            "Parent/child membership",
            lambda e: e.get("@type") == "FeatureMembership"
            and e.get("memberName") == "autoware",
        ),
        ("Lower/upper multiplicity", lambda e: e.get("@type") == "MultiplicityRange"),
        ("Lifecycle metadata", lambda e: _named(e, "bindingTime")),
        ("Feature configuration", lambda e: _named(e, "validAutowareAndroid")),
        (
            "Selected feature relationship",
            lambda e: e.get("@type") == "Redefinition"
            and _ref_id(e.get("redefinedFeature")) is not None,
        ),
        ("Requires relationship", lambda e: _named(e, "requiresFeatures")),
        ("Incompatibility constraint", lambda e: _named(e, "xorFeatures")),
        ("FeatureBinding", lambda e: _named(e, "gateASimpleFeatureBinding")),
        ("Native variation", lambda e: _named(e, "gateAAdapterVariation")),
        (
            "Owned variant",
            lambda e: e.get("@type") == "VariantMembership"
            and e.get("memberName") == "autowareToAAOSSDV",
        ),
        ("Common classification", lambda e: _named(e, "gateACommonCoreAsset")),
        (
            "Native constraint expression probe",
            lambda e: _named(e, "NativeAdapterImplicationProbe"),
        ),
        ("Adapter realization rule", lambda e: _named(e, "autowareAndroidRule")),
    )
    rows = []
    for concept, predicate in queries:
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
            evidence.append(
                {
                    "uuid": element_id,
                    "metatype": element.get("@type"),
                    "name": element.get("declaredName") or element.get("name"),
                    "property_keys": sorted(element),
                    "reference_paths": _reference_paths(element),
                    "source": element_sources.get(element_id),
                }
            )
        rows.append(
            {
                "concept": concept,
                "api_only_consumption_adequate": all(item["source"] for item in evidence),
                "evidence": evidence,
                "exact_gap": "" if all(item["source"] for item in evidence) else "source provenance missing",
            }
        )
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

        xor_definitions = self._named_ids("XorConstraint", "ConstraintDefinition")
        if len(xor_definitions) > 1:
            raise UnsupportedSemanticShape("multiple PLEML XorConstraint definitions")
        if xor_definitions:
            base_ids = set(self._typed_usage_ids("XorConstraint", "ConstraintDefinition"))
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
                if candidate.get("@type") != "ConstraintUsage":
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
