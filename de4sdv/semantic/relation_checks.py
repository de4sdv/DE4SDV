"""Relation checks: one implementation per relation, keyed by the relation's name.

A method check names the relation it checks, for example
``derivesRequirementFromNeed``. :func:`relation_checks` maps that name to the
implementation that finds, for one subject element of the bound model
revision, the elements the relation reaches and the witnesses that carry
it. An implementation reads only the model: the subject, the revision-scoped
index, the production traversal and the ingestion-validated kernel bindings
(ADR 0011). It takes no method-representation input (no selector, filter,
cardinality or phase), so any representation of the method that names
relations can use it. How many targets a check requires, and which targets
qualify for a method rule, stays with the method.

Two kinds of names:

- **Relations of the model-built semantic contract.** A relation with a
  SysML mapping is decided by the production traversal; its mechanics hold
  the relation to its declared domain and range, and a check never adds a
  second type contract. A successor relation whose carrier the successor
  profile pins as a connection definition is read from the ends of the
  connections typed by that carrier (the reviewed connection-end mechanics),
  so export-shaped connections stay readable; its targets are the ends in
  the relation's range lineage. A relation without a SysML mapping, or whose
  content is external at this revision, is method side: only a method or
  kernel change can supply it, so it is never reported as a model gap.
- **Native SysML v2 relations**, named by their keyword: ``frame`` (framed
  concerns), ``stakeholder``, ``subject`` and ``verify`` (requirements
  verified by the own or inherited objectives).

A result records a problem with a marker: ``kernel-binding:``,
``governed-relation:`` or ``external-relation:`` for method-side inputs, and
``model-witness:`` for engineering witnesses that cannot be read, which the
author can fix.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from .increment_scope import ModelView
from .kernel_contract import KernelFileMapping

#: Problem markers of inputs that only a method or kernel change can supply.
METHOD_SIDE_PREFIXES = ("kernel-binding:", "governed-relation:", "external-relation:")
#: Problem marker of engineering witnesses that exist but cannot be read.
MODEL_WITNESS_PREFIX = "model-witness:"


class MethodSideInput(Exception):
    """An input only the method or kernel can supply is missing."""

    def __init__(self, marker: str, detail: str) -> None:
        self.marker = marker
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class RelationResult:
    """What one relation reaches from one subject, and through which witnesses."""

    relation: str
    subject: str
    #: ``(target, witness)`` pairs in model order.
    hops: tuple[tuple[str, str], ...] = ()
    #: Empty, or a method-side / model-witness marker.
    problem: str = ""
    #: The problem in model terms.
    detail: str = ""
    #: The raw reason of a model-witness problem.
    reason: str = ""
    #: The statement, in model terms, that no target is reached.
    absent: str = ""
    #: Witnesses that exist but do not count, and why (only when no target).
    near_misses: tuple[str, ...] = ()

    @property
    def targets(self) -> list[str]:
        return list(dict.fromkeys(target for target, _witness in self.hops))

    @property
    def witnesses(self) -> list[str]:
        return list(dict.fromkeys(witness for _target, witness in self.hops))

    @property
    def method_side(self) -> bool:
        return self.problem.startswith(METHOD_SIDE_PREFIXES)


#: A relation check: the bound model view and one subject element.
RelationCheck = Callable[[ModelView, str], RelationResult]


# ---------------------------------------------------------------------------
# Model reading shared by the checks
# ---------------------------------------------------------------------------


def element_name(view: ModelView, element: str | None) -> str:
    """Qualified name of an element (its id when unnamed)."""
    return view.index.qualified_name(element) or str(element or "")


def membership_members(view: ModelView, owner: str, membership_type: str) -> list[str]:
    """Member elements of one membership kind owned by ``owner`` (model order)."""
    return [member for member, _relationship in _membership_hops(view, owner, membership_type)]


def _membership_hops(view: ModelView, owner: str, membership_type: str) -> list[tuple[str, str]]:
    found: dict[str, str] = {}
    for relationship in view.index.owned_relationships(owner, membership_type):
        for member in reference_ids(relationship.get("memberElement")):
            found.setdefault(member, str(relationship.get("@id")))
    return list(found.items())


def in_class(view: ModelView, element: str, ontology_class: str) -> bool:
    """Lineage membership through the validated kernel binding of a class."""
    try:
        return view.in_lineage(element, ontology_class)
    except IdentityNotFoundError as error:
        raise MethodSideInput(f"kernel-binding:{ontology_class}",
                              f"method side: no validated kernel binding for {ontology_class}: {error}")


def _declared_name(declaration: str) -> str:
    """``connection def X`` -> ``X``."""
    return str(declaration or "").rpartition(" ")[2]


def _connection_carrier(view: ModelView, relation: str) -> str | None:
    """Declared name of the connection definition the profile pins for a relation."""
    profile = getattr(view.contract, "profile", None) or {}
    pin = (profile.get("carriers") or {}).get(relation)
    declaration = str((pin or {}).get("declaration") or "")
    if not declaration.startswith("connection def "):
        return None
    return _declared_name(declaration)


def _class_declaration(view: ModelView, ontology_class: str) -> str:
    """Declared name the profile pins for a class (the class name otherwise)."""
    profile = getattr(view.contract, "profile", None) or {}
    pin = (profile.get("classes") or {}).get(ontology_class)
    return _declared_name(pin["declaration"]) if pin and pin.get("declaration") else ontology_class


def _governed_hops(view: ModelView, relation: str, subject_id: str) -> tuple[list[Any], str]:
    """Traversal hops of one governed relation, or a model-witness problem.

    Raises :class:`MethodSideInput` when the relation has no SysML mapping,
    is external, or a class its strategy resolves has no kernel binding.
    """
    contract = view.contract
    try:
        mapping = contract.relationship_mapping(relation)
    except Exception as error:  # noqa: BLE001 - an unmapped relation is method side
        raise MethodSideInput(f"governed-relation:{relation}",
                              f"method side: governed relation {relation} has no SysML mapping ({error})")
    if mapping.strategy == "external":
        raise MethodSideInput(f"external-relation:{relation}",
                              f"method side: {relation} is external data; no native relation at this revision")
    config = mapping.configuration or {}
    # Classes the strategy itself resolves through kernel bindings; a
    # missing binding is method side, not a model gap.
    classes = [mapping.domain, config.get("connection_definition"),
               config.get("source_lineage_of"), config.get("target_lineage_of")]
    for ontology_class in [str(c) for c in classes if c]:
        try:
            file_mapped = isinstance(contract.mapping(ontology_class), KernelFileMapping)
        except Exception:  # noqa: BLE001 - not a class of this contract
            file_mapped = False
        if not file_mapped:
            continue
        try:
            view.traversal.class_lineage(ontology_class, view.elements)
        except IdentityNotFoundError as error:
            raise MethodSideInput(f"kernel-binding:{ontology_class}", f"method side: {error}")
    traversal = view.traversal
    # The traversal de-duplicates its accumulated unsupported records, so the
    # records of this one call are collected on a fresh list and merged back.
    accumulated = getattr(traversal, "unsupported", None)
    if accumulated is not None:
        traversal.unsupported = []
    try:
        hops = traversal.traverse(relation, view.element(subject_id), view.elements)
    except IdentityNotFoundError as error:
        return [], str(error)
    finally:
        if accumulated is not None:
            fresh = traversal.unsupported
            traversal.unsupported = accumulated + [r for r in fresh if r not in accumulated]
    added = [record for record in fresh if record.get("predicate") == relation] if accumulated is not None else []
    if added and not hops:
        return [], "; ".join(str(record.get("reason")) for record in added)
    return hops, ""


def _plural(ontology_class: str) -> str:
    return (ontology_class[:1].lower() + ontology_class[1:] + "s") if ontology_class else "targets"


def plain_dependency_near_misses(view: ModelView, relation: str, subject_id: str) -> tuple[str, ...]:
    """Plain dependencies that stand in for a derivation connection, which do not count.

    Applies to a derivation-connection relation read from its source side
    (for example ``derivesRequirementFromNeed``): a plain dependency from the
    subject to an element of the relation's target lineage is reported as a
    near miss, never as a witness.
    """
    try:
        mapping = view.contract.relationship_mapping(relation)
    except Exception:  # noqa: BLE001 - unmapped relations have no near misses
        return ()
    config = mapping.configuration or {}
    if mapping.strategy != "derivation-connection" or config.get("source_lineage_of") != mapping.domain:
        return ()
    target_class = str(config.get("target_lineage_of") or mapping.range or "")
    count = 0
    for dependency in view.index.elements_of_type("Dependency"):
        element = view.index.by_id[dependency]
        sources = reference_ids(element.get("client")) or reference_ids(element.get("source"))
        if subject_id not in sources:
            continue
        targets = reference_ids(element.get("supplier")) or reference_ids(element.get("target"))
        count += sum(1 for target in targets if view.in_lineage(target, target_class))
    if not count:
        return ()
    return (f"{count} plain dependency derivation(s) to {_plural(target_class)} do not count; only a "
            f"{config.get('connection_definition')} connection does",)


def _connection_ends(view: ModelView) -> dict[str, tuple[tuple[str, ...], str]]:
    """Connection usage -> (connected usages in end order, problem), once per corpus."""

    def build() -> dict[str, tuple[tuple[str, ...], str]]:
        traversal = view.traversal
        index = view.index
        found: dict[str, tuple[tuple[str, ...], str]] = {}
        for connection in index.elements_of_type("ConnectionUsage"):
            element = index.by_id[connection]
            try:
                records = traversal._connection_end_records(element, index.by_id, index.graph)
                ends = tuple(
                    traversal._connected_usage_id(record["end_element_id"], index.graph, index.by_id)[0]
                    for record in records
                )
                found[connection] = (ends, "")
            except IdentityNotFoundError as error:
                found[connection] = ((), str(error))
        return found

    return view.index.memo("connection-ends", build)


# ---------------------------------------------------------------------------
# Relation checks
# ---------------------------------------------------------------------------


def governed_relation_check(relation: str) -> RelationCheck:
    """A contract relation, decided by the production traversal."""

    def check(view: ModelView, subject_id: str) -> RelationResult:
        name = element_name(view, subject_id)
        try:
            hops, problem = _governed_hops(view, relation, subject_id)
        except MethodSideInput as missing:
            return RelationResult(relation, subject_id, problem=missing.marker, detail=missing.detail)
        if problem:
            return RelationResult(relation, subject_id, problem=MODEL_WITNESS_PREFIX + relation,
                                  detail=f"{relation} witnesses of {name} cannot be read: {problem}",
                                  reason=problem)
        pairs = tuple((str(hop.target.get("@id")), str(hop.api_object.get("@id"))) for hop in hops)
        return RelationResult(
            relation, subject_id, hops=pairs, absent=f"{name} has no {relation} target",
            near_misses=() if pairs else plain_dependency_near_misses(view, relation, subject_id),
        )

    check.__name__ = f"governed_{relation}"
    return check


def connection_carried_check(relation: str) -> RelationCheck:
    """A successor relation carried by the connection definition the profile pins."""

    def check(view: ModelView, subject_id: str) -> RelationResult:
        name = element_name(view, subject_id)
        carrier = _connection_carrier(view, relation) or relation
        try:
            mapping = view.contract.relationship_mapping(relation)
        except Exception as error:  # noqa: BLE001 - an unmapped relation is method side
            return RelationResult(relation, subject_id, problem=f"governed-relation:{relation}",
                                  detail=f"method side: governed relation {relation} has no SysML mapping ({error})")
        target_class = str(mapping.range or "")
        try:
            # Routing files the pinned carrier's validated binding under the
            # relation name, so the relation name resolves the carrier lineage.
            carriers = view.traversal.class_lineage(relation, view.elements)["explicit_lineage_ids"]
        except IdentityNotFoundError as error:
            return RelationResult(relation, subject_id, problem=f"kernel-binding:{relation}",
                                  detail=f"method side: {error}")
        hops: list[tuple[str, str]] = []
        problems: list[str] = []
        try:
            for connection, (ends, problem) in sorted(_connection_ends(view).items()):
                if not view.index.typed_by(connection) & carriers:
                    continue
                if problem:
                    problems.append(f"{element_name(view, connection)}: {problem}")
                    continue
                if subject_id not in ends:
                    continue
                for end in ends:
                    if (end != subject_id and end not in (t for t, _w in hops)
                            and in_class(view, end, target_class)):
                        hops.append((end, connection))
        except MethodSideInput as missing:
            return RelationResult(relation, subject_id, problem=missing.marker, detail=missing.detail)
        if not hops and problems:
            reason = f"{carrier} connections cannot be read: {problems[:3]}"
            return RelationResult(relation, subject_id, problem=MODEL_WITNESS_PREFIX + carrier,
                                  detail=reason, reason=reason)
        return RelationResult(
            relation, subject_id, hops=tuple(hops),
            absent=f"{name} has no {carrier} connection to a {_class_declaration(view, target_class)}",
        )

    check.__name__ = f"connection_{relation}"
    return check


def _frame(view: ModelView, subject_id: str) -> RelationResult:
    hops: dict[str, str] = {}
    for relationship in view.index.owned_relationships(subject_id, "FramedConcernMembership"):
        for member in reference_ids(relationship.get("memberElement")):
            concern = view.index.declared_of(member)
            if str(view.element(concern).get("@type")) == "ConcernUsage":
                hops.setdefault(concern, str(relationship.get("@id")))
    return RelationResult("frame", subject_id, hops=tuple(hops.items()),
                          absent=f"{element_name(view, subject_id)} frames no concern")


def _stakeholder(view: ModelView, subject_id: str) -> RelationResult:
    return RelationResult("stakeholder", subject_id,
                          hops=tuple(_membership_hops(view, subject_id, "StakeholderMembership")),
                          absent=f"{element_name(view, subject_id)} declares no stakeholder")


def _subject(view: ModelView, subject_id: str) -> RelationResult:
    return RelationResult("subject", subject_id,
                          hops=tuple(_membership_hops(view, subject_id, "SubjectMembership")),
                          absent=f"{element_name(view, subject_id)} declares no subject")


def _verify(view: ModelView, subject_id: str) -> RelationResult:
    """Requirements verified by the subject's own or inherited objectives."""
    hops: dict[str, str] = {}
    for holder in (subject_id, *sorted(view.index.typed_by(subject_id))):
        for objective in membership_members(view, holder, "ObjectiveMembership"):
            for relationship in view.index.owned_relationships(objective, "RequirementVerificationMembership"):
                for member in reference_ids(relationship.get("memberElement")):
                    hops.setdefault(view.index.declared_of(member), str(relationship.get("@id")))
    return RelationResult("verify", subject_id, hops=tuple(hops.items()),
                          absent=f"{element_name(view, subject_id)} objective verifies no requirement "
                                 "(own or inherited)")


_NATIVE_CHECKS: dict[str, RelationCheck] = {
    "frame": _frame, "stakeholder": _stakeholder, "subject": _subject, "verify": _verify,
}


def relation_checks(view: ModelView) -> Mapping[str, RelationCheck]:
    """Relation name -> check: every relation of the view's model-built contract and the
    native SysML relations (read-only, built once per contract)."""

    def build() -> Mapping[str, RelationCheck]:
        contract = view.contract
        carriers = (getattr(contract, "profile", None) or {}).get("carriers") or {}
        table: dict[str, RelationCheck] = {}
        for relation in sorted(getattr(contract, "relationships", {}) or {}):
            try:
                strategy = contract.relationship_mapping(relation).strategy
            except Exception:  # noqa: BLE001 - unmapped: decided as method side
                strategy = ""
            pinned = str((carriers.get(relation) or {}).get("declaration") or "")
            carried = strategy == "successor" and pinned.startswith("connection def ")
            table[relation] = (connection_carried_check if carried else governed_relation_check)(relation)
        if set(table) & set(_NATIVE_CHECKS):
            raise ValueError(f"contract relations shadow native relations: {sorted(set(table) & set(_NATIVE_CHECKS))}")
        return MappingProxyType({**table, **_NATIVE_CHECKS})

    return view.index.memo_bound(("relation-checks",), (view.contract,), build)


def check_relation(view: ModelView, relation: str, subject_id: str) -> RelationResult:
    """What ``relation`` reaches from one subject element."""
    return relation_checks(view)[relation](view, subject_id)
