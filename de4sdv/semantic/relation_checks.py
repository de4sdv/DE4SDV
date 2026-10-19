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
  the relation's range lineage. A successor relation carried by native
  allocations (``allocatedTo``) is read from the ends of every
  ``AllocationUsage``, typed or not: an allocation counts for the one end
  pair of the relation its two ends ground in, and an end written as a
  feature chain (``a.b``) reads as its last chaining feature. Absence is not
  established while any allocation is unreadable: a subject without a
  counting allocation is then a model-witness problem, never a gap. Plain
  dependencies between the subject and an element of the class it must
  reach, and allocations that ground in none of the end pairs, are near
  misses: reported, never witnesses. A relation
  without a SysML mapping, or whose content is external at this revision, is
  method side: only a method or kernel change can supply it, so it is never
  reported as a model gap.
- **Native SysML v2 relations**, named by their keyword: ``frame`` (framed
  concerns), ``stakeholder``, ``subject`` and ``verify`` (requirements
  verified by the own or inherited objectives).

A result records a problem with a marker: ``kernel-binding:``,
``library-binding:``, ``governed-relation:`` or ``external-relation:`` for
method-side inputs, and ``model-witness:`` for engineering witnesses that
cannot be read, which the author can fix.

The module also reads the phase-8 signal-mapping control for the named checks
that judge it: the ports of an element that exchange an information item (a
directed feature of the port, of its definition or a conjugated definition's
original, of a feature it narrows, or of a port a connector connects it to),
the allocations typed by the kernel's ``SystemToSoftwareSignalMappingCandidate``
with their records and their ends' feature chains, and the VSS signals an
endpoint carries: the definitions that a metadata usage typed by COVESA_VSS's
``VssSignalMetadata`` annotates, the form of each signal in COVESA_VSS and
DE4SDV_VSS_Extensions. That metadata definition is a library pin, bound by
identity when an export is loaded (:data:`LIBRARY_PINS`); other metadata, or a
path in a doc or a string, is no VSS typing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import reference_ids

from .increment_scope import ModelView
from .kernel_contract import KernelFileMapping

#: Problem markers of inputs that only a method or kernel change can supply.
METHOD_SIDE_PREFIXES = ("kernel-binding:", "library-binding:", "governed-relation:", "external-relation:")
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
    """Qualified name of an element (its id when it has none); both resolve."""
    return view.label(element)


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


def class_declaration(view: ModelView, ontology_class: str) -> str:
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


def connection_ends(view: ModelView) -> dict[str, tuple[tuple[str, ...], str]]:
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


#: The successor mechanism of a relation whose witnesses are native allocations.
NATIVE_ALLOCATION = "native-allocation"


def chained_feature(view: ModelView, feature: str) -> str:
    """A feature chain read as its last chaining feature; any other feature as itself.

    An end written ``a.b`` references a feature whose FeatureChaining
    relationships list the chained features in order (native KerML
    structure); the end names the feature the chain ends in. No name is read.
    Raises :class:`IdentityNotFoundError` when that feature is not in the bound
    revision.
    """
    chainings = view.index.owned_relationships(feature, "FeatureChaining")
    if not chainings:
        return feature
    last = reference_ids(chainings[-1].get("chainingFeature"))
    if not last or last[0] not in view.index.by_id:
        raise IdentityNotFoundError(f"feature chain {feature!r} ends in a feature that is not in the bound revision")
    return last[0]


def allocation_ends(view: ModelView) -> dict[str, tuple[tuple[str, ...], str]]:
    """Allocation usage -> (allocated features in end order, problem), once per corpus.

    The ends are read like connection ends (EndFeatureMembership -> authored
    ReferenceSubsetting); a feature-chain end reads as its last chaining feature.
    """

    def build() -> dict[str, tuple[tuple[str, ...], str]]:
        traversal = view.traversal
        index = view.index
        found: dict[str, tuple[tuple[str, ...], str]] = {}
        for allocation in index.elements_of_type("AllocationUsage"):
            element = index.by_id[allocation]
            try:
                records = traversal._connection_end_records(element, index.by_id, index.graph)
                ends = tuple(
                    chained_feature(view, traversal._connected_usage_id(
                        record["end_element_id"], index.graph, index.by_id)[0])
                    for record in records
                )
                found[allocation] = (ends, "")
            except IdentityNotFoundError as error:
                found[allocation] = ((), str(error))
        return found

    return view.index.memo("allocation-ends", build)


def native_allocation_rows(view: ModelView, relation: str | None = None) -> list[tuple[str, Mapping[str, Any]]]:
    """``(relation, end-pair row)`` of the served successor relations carried by native allocations."""
    profile = getattr(view.contract, "profile", None) or {}
    relations = profile.get("relations") or {}
    return [(name, row) for name in sorted(relations) if relation is None or name == relation
            for row in relations[name] or () if row.get("mechanism") == NATIVE_ALLOCATION]


def _end_classes(rows: list[tuple[str, Mapping[str, Any]]]) -> list[str]:
    """Every endpoint class of the end pairs, in row order."""
    return list(dict.fromkeys(str(row[key]) for _name, row in rows for key in ("sourceClass", "targetClass")))


def allocation_pairs(view: ModelView, relation: str, source: str, target: str) -> list[Mapping[str, Any]]:
    """The end pairs of ``relation`` an allocation from ``source`` to ``target`` grounds in (validated
    kernel lineage). Raises :class:`MethodSideInput` when a class has no validated kernel binding."""
    return [row for _name, row in native_allocation_rows(view, relation)
            if in_class(view, source, str(row["sourceClass"])) and in_class(view, target, str(row["targetClass"]))]


def allocation_hops(view: ModelView, relation: str, subject_id: str, *,
                    incoming: bool = False) -> tuple[list[tuple[str, str]], list[str]]:
    """``(other end, allocation)`` of the allocations of ``relation`` from (or, ``incoming``, to) the
    subject, and the allocations that cannot be read.

    An allocation counts when its two ends ground in one end pair of the relation. An allocation an end
    of which grounds in two endpoint classes of the relation counts for none and is reported as a
    problem. Every unreadable allocation of the revision is a problem, wherever it is: its ends are
    unknown, so it may be the one that reaches the subject (absence is not established while any
    allocation is unreadable). Raises :class:`MethodSideInput` when a class has no validated kernel
    binding.
    """
    rows = native_allocation_rows(view, relation)
    classes = _end_classes(rows)
    hops: list[tuple[str, str]] = []
    problems: list[str] = []
    for allocation, (ends, problem) in sorted(allocation_ends(view).items()):
        if problem:
            problems.append(f"{element_name(view, allocation)}: {problem}")
            continue
        if subject_id not in ends:
            continue
        if len(ends) != 2:
            problems.append(f"{element_name(view, allocation)}: {len(ends)} ends, a binary allocation has 2")
            continue
        source, target = ends
        if (target if incoming else source) != subject_id:
            continue
        overlapping = [end for end in ends if sum(1 for c in classes if in_class(view, end, c)) > 1]
        if overlapping:
            problems.append(f"{element_name(view, allocation)}: {element_name(view, overlapping[0])} grounds in "
                            f"more than one of {', '.join(classes)}")
            continue
        other = source if incoming else target
        if allocation_pairs(view, relation, source, target) and other not in (o for o, _a in hops):
            hops.append((other, allocation))
    return hops, problems


def allocation_classes(view: ModelView, relation: str, subject_id: str, *, incoming: bool = False) -> list[str]:
    """The classes the subject's allocations of ``relation`` reach: the target classes of the end pairs
    whose source class the subject grounds in (or, ``incoming``, the source classes of the end pairs
    whose target class it grounds in)."""
    near, far = ("targetClass", "sourceClass") if incoming else ("sourceClass", "targetClass")
    return list(dict.fromkeys(str(row[far]) for _name, row in native_allocation_rows(view, relation)
                              if in_class(view, subject_id, str(row[near]))))


def unreadable_allocations(problems: list[str]) -> str:
    """Why absence cannot be established: the allocations that cannot be read (the first three named)."""
    count = len(problems)
    return (f"{count} allocation{'' if count == 1 else 's'} cannot be read, so absence cannot be established: "
            + "; ".join(problems[:3]))


def ungrounded_allocations(view: ModelView, relation: str, subject_id: str) -> list[str]:
    """The other ends of the readable binary allocations between the subject and another element, in
    either direction, that ground in none of the end pairs of ``relation`` (model order)."""
    others: list[str] = []
    for _allocation, (ends, problem) in sorted(allocation_ends(view).items()):
        if problem or len(ends) != 2 or subject_id not in ends or ends[0] == ends[1]:
            continue
        other = ends[1] if ends[0] == subject_id else ends[0]
        if not allocation_pairs(view, relation, *ends) and other not in others:
            others.append(other)
    return others


def allocation_near_misses(view: ModelView, relation: str, subject_id: str, classes: list[str]) -> tuple[str, ...]:
    """What stands in for an allocation of ``relation`` from the subject and does not count: plain
    dependencies from the subject to an element of ``classes``, dependencies from such an element to the
    subject (the ``hasRelevantArchitecture`` shape), and allocations between the subject and another
    element that ground in none of the relation's end pairs."""
    outgoing = incoming = 0
    for dependency in view.index.elements_of_type("Dependency"):
        element = view.index.by_id[dependency]
        sources = reference_ids(element.get("client")) or reference_ids(element.get("source"))
        targets = reference_ids(element.get("supplier")) or reference_ids(element.get("target"))
        if subject_id in sources:
            outgoing += sum(1 for target in targets if any(in_class(view, target, c) for c in classes))
        if subject_id in targets:
            incoming += sum(1 for source in sources if any(in_class(view, source, c) for c in classes))
    named = " or ".join(_plural(class_declaration(view, c)) for c in classes)
    found = []
    if outgoing:
        found.append(f"{outgoing} plain dependency(ies) to {named} do not count; only an allocation does")
    if incoming:
        found.append(f"{incoming} dependency(ies) from {named} to it do not count; only an allocation does")
    others = [element_name(view, other) for other in ungrounded_allocations(view, relation, subject_id)]
    if others:
        found.append(f"{len(others)} allocation(s) between it and {', '.join(others[:3])} ground in no {relation} "
                     "end pair and do not count")
    return tuple(found)


# ---------------------------------------------------------------------------
# System-to-software signal mappings (the phase-8 control)
# ---------------------------------------------------------------------------

#: The kernel's non-claiming allocation from a logical signal responsibility to a software endpoint.
SIGNAL_MAPPING = "SystemToSoftwareSignalMappingCandidate"
#: The kernel's control record a signal mapping owns.
SIGNAL_MAPPING_RECORD = "LogicalToSoftwareSignalMappingRecord"
#: The kernel's disposition of a mapping record.
SIGNAL_MAPPING_DISPOSITION = "SignalMappingDisposition"
#: The VSS signal metadata of COVESA_VSS, read by identity: the loader of an export binds it by ADR 0011's
#: file-mapped rule (metatype, declared name, serializer-recorded source document), never a check by name.
VSS_SIGNAL_METADATA = "COVESA_VSS::MetadataDefinitions::VssSignalMetadata"
#: The library declarations the checks read by identity, by the name a result reports them under.
LIBRARY_PINS: Mapping[str, KernelFileMapping] = MappingProxyType({
    VSS_SIGNAL_METADATA: KernelFileMapping(
        file="textual-notation-of-model/libraries/covesa-vss-sysmlv2/COVESA_VSS.sysml",
        declaration="metadata def VssSignalMetadata"),
})
#: The member of a VSS signal's metadata that names the signal (a feature of the bound definition).
VSS_PATH = "path"
_VSS_DEPTH = 4
#: The remedies' placeholders (de4sdv.semantic.remedies): a record member still holding one states nothing.
OWNER_PLACEHOLDER = "<owner>"
NEXT_ACTION_PLACEHOLDER = "<next action>"
SEMANTIC_SOURCE_PLACEHOLDER = "<what the item is, and why it is no VSS signal>"
REASON_PLACEHOLDER = "<why no information item crosses a software contract>"
REMEDY_PLACEHOLDERS = (OWNER_PLACEHOLDER, NEXT_ACTION_PLACEHOLDER, SEMANTIC_SOURCE_PLACEHOLDER, REASON_PLACEHOLDER)
#: A value that only marks the statement as still to come.
_TO_BE_DETERMINED = re.compile(r"(?:tbd|tbc|tba|todo|to do|fixme|to be (?:determined|defined|decided|confirmed)"
                               r"|\?+|\.{3}|\u2026|-+|\u2014)[.!]*", re.IGNORECASE)


def kernel_lineage(view: ModelView, ontology_class: str) -> frozenset[str]:
    """The validated kernel definition of a class and its specializations. Raises
    :class:`MethodSideInput` when the class has no validated kernel binding."""
    try:
        return view.index.specializations(view.kernel_element(ontology_class))
    except IdentityNotFoundError as error:
        raise MethodSideInput(f"kernel-binding:{ontology_class}",
                              f"method side: no validated kernel binding for {ontology_class}: {error}")


def library_lineage(view: ModelView, pin: str) -> frozenset[str]:
    """The bound library declaration of a pin and its specializations. Raises :class:`MethodSideInput`
    when the pin is unbound (no export bound it, or its file-mapped rule found no or several elements)."""
    try:
        return view.index.specializations(view.library_element(pin))
    except IdentityNotFoundError as error:
        raise MethodSideInput(f"library-binding:{pin}", f"method side: {error}")


def stated_texts(view: ModelView, owner: str, member: str) -> list[str]:
    """The String values of ``owner``'s member that state something: not empty, not a remedy placeholder
    left unfilled, and not only a to-be-determined marker (TBD, TBC, TODO). What a stated value says is
    not judged."""
    return [text for leaf in view.index.feature_values(owner, member)
            if leaf.kind == "string" and (text := str(leaf.value or "")).strip()
            and not any(placeholder in text for placeholder in REMEDY_PLACEHOLDERS)
            and not _TO_BE_DETERMINED.fullmatch(text.strip())]


#: Declared (never implied) relations from a feature to the features it narrows.
_NARROWING = (("Subsetting", "subsettedFeature"), ("Redefinition", "redefinedFeature"),
              ("ReferenceSubsetting", "referencedFeature"))


def narrowed_features(view: ModelView, feature: str) -> list[str]:
    """``feature`` and every feature it subsets, redefines or references, transitively (declared
    relationships only)."""
    found: list[str] = []
    frontier = [feature]
    while frontier:
        current = frontier.pop(0)
        if current in found:
            continue
        found.append(current)
        for relationship_type, key in _NARROWING:
            for relationship in view.index.owned_relationships(current, relationship_type):
                if relationship.get("isImplied"):
                    continue
                frontier.extend(reference_ids(relationship.get(key)))
    return found


def _conjugated_originals(view: ModelView, definition: str) -> list[str]:
    """The original port definition of a conjugated one (``~P``, its PortConjugation)."""
    return [original for relationship in view.index.owned_relationships(definition, "PortConjugation")
            for original in reference_ids(relationship.get("originalPortDefinition"))]


def type_lineage(view: ModelView, element: str) -> list[str]:
    """The definitions that type ``element`` and those they specialize, nearest first; a conjugated port
    definition brings its original's."""
    found: list[str] = []
    for definition in sorted(view.index.typed_by(element)):
        for typed in (definition, *_conjugated_originals(view, definition)):
            for general in view.index.generals(typed):
                if general not in found:
                    found.append(general)
    return found


def member_features(view: ModelView, element: str) -> list[str]:
    """What ``element`` owns and what its definitions own, then the same for each feature it narrows
    (redefines, subsets or references), in that order."""
    index = view.index
    found: list[str] = []
    for feature in narrowed_features(view, element):
        for holder in (feature, *type_lineage(view, feature)):
            found.extend(member for member in index.owned_members(holder) if member not in found)
    return found


#: The connectors whose ends exchange what their features carry.
_CONNECTORS = ("ConnectionUsage", "InterfaceUsage", "FlowUsage", "SuccessionFlowUsage", "FlowConnectionUsage",
               "SuccessionFlowConnectionUsage", "BindingConnectorAsUsage")


def connected_peers(view: ModelView) -> tuple[Mapping[str, tuple[str, ...]], tuple[str, ...]]:
    """(feature -> the features a connector connects it to, each end read as its last chaining feature;
    the connectors that cannot be read), once per corpus."""

    def build() -> tuple[Mapping[str, tuple[str, ...]], tuple[str, ...]]:
        traversal, index = view.traversal, view.index
        peers: dict[str, list[str]] = {}
        problems: list[str] = []
        for connector in index.elements_of_type(*_CONNECTORS):
            try:
                records = traversal._connection_end_records(index.by_id[connector], index.by_id, index.graph)
                ends = [chained_feature(view, traversal._connected_usage_id(
                    record["end_element_id"], index.graph, index.by_id)[0]) for record in records]
            except IdentityNotFoundError as error:
                problems.append(f"{element_name(view, connector)}: {error}")
                continue
            for end in ends:
                bucket = peers.setdefault(end, [])
                bucket.extend(other for other in ends if other != end and other not in bucket)
        return MappingProxyType({end: tuple(found) for end, found in peers.items()}), tuple(problems)

    return view.index.memo("connected-peers", build)


def port_reading(view: ModelView, element: str) -> tuple[list[str], list[str]]:
    """(the information ports of ``element``, why its other ports cannot be read). An information port
    is a port of ``element``, own or inherited, with a directed feature: of its own or of its definitions
    (a conjugated port definition's original included), of a feature it narrows, or of a port a connector
    connects it to (``in item speedSample : Payload;``). A port cannot be read when a definition typing it
    is not in the bound revision, or when it has no type, no feature, nothing it narrows and no connected
    port. While a connector of the revision cannot be read, the connected ports of a port without a
    directed feature of its own are not known, so such a port cannot be read either; an element without
    such a port is unaffected."""
    index = view.index
    peers, problems = connected_peers(view)
    information: list[str] = []
    unreadable: list[str] = []
    peer_dependent: list[str] = []
    for port in member_features(view, element):
        if str(index.element(port).get("@type")) != "PortUsage":
            continue
        narrowed = narrowed_features(view, port)
        connected = [peer for feature in narrowed for peer in peers.get(feature, ())]
        content = [*member_features(view, port), *(f for peer in connected for f in member_features(view, peer))]
        if any(index.element(feature).get("direction") for feature in content):
            information.append(port)
            continue
        peer_dependent.append(port)  # no directed feature of its own: its connected ports decide
        types = [definition for feature in narrowed for definition in type_lineage(view, feature)]
        missing = [definition for definition in types if definition not in index.by_id]
        if missing:
            unreadable.append(f"{element_name(view, port)} is typed by an element that is not in the bound revision")
        elif not (types or content or connected or len(narrowed) > 1):
            unreadable.append(f"{element_name(view, port)} has no type, no feature and no connected port")
    if not information and problems and peer_dependent:
        unreadable.append(f"the connected ports of {len(peer_dependent)} port(s) are unknown while "
                          f"{len(problems)} connector(s) cannot be read: {'; '.join(problems[:3])}")
    return information, unreadable


def information_ports(view: ModelView, element: str) -> list[str]:
    """The information ports of ``element`` (see :func:`port_reading`)."""
    return port_reading(view, element)[0]


def feature_chain(view: ModelView, feature: str) -> tuple[str, ...]:
    """The chaining features of a feature chain (``a.b``), in order; any other feature as itself. Raises
    :class:`IdentityNotFoundError` when the chain ends in a feature that is not in the bound revision."""
    chainings = view.index.owned_relationships(feature, "FeatureChaining")
    if not chainings:
        return (feature,)
    chain = tuple(found for chaining in chainings for found in reference_ids(chaining.get("chainingFeature")))
    if not chain or chain[-1] not in view.index.by_id:
        raise IdentityNotFoundError(f"feature chain {feature!r} ends in a feature that is not in the bound revision")
    return chain


def allocation_end_chains(view: ModelView) -> Mapping[str, tuple[tuple[tuple[str, ...], ...], str]]:
    """Allocation usage -> (each end's chaining features, or its feature alone; problem), once per corpus.
    The last feature of each end is the end :func:`allocation_ends` reads."""

    def build() -> Mapping[str, tuple[tuple[tuple[str, ...], ...], str]]:
        traversal, index = view.traversal, view.index
        found: dict[str, tuple[tuple[tuple[str, ...], ...], str]] = {}
        for allocation in index.elements_of_type("AllocationUsage"):
            try:
                records = traversal._connection_end_records(index.by_id[allocation], index.by_id, index.graph)
                found[allocation] = (tuple(feature_chain(view, traversal._connected_usage_id(
                    record["end_element_id"], index.graph, index.by_id)[0]) for record in records), "")
            except IdentityNotFoundError as error:
                found[allocation] = ((), str(error))
        return MappingProxyType(found)

    return view.index.memo("allocation-end-chains", build)


def signal_mappings(view: ModelView) -> Mapping[str, tuple[tuple[str, ...], str]]:
    """Signal-mapping allocation -> (its ends, problem): every allocation typed in the lineage of the
    kernel's system-to-software signal mapping, read like any allocation (a chain end as its last
    feature), once per corpus. Raises :class:`MethodSideInput` when that class has no validated
    kernel binding."""
    lineage = kernel_lineage(view, SIGNAL_MAPPING)

    def build() -> Mapping[str, tuple[tuple[str, ...], str]]:
        return MappingProxyType({allocation: found for allocation, found in sorted(allocation_ends(view).items())
                                 if view.index.typed_by(allocation) & lineage})

    return view.index.memo(("signal-mappings", lineage), build)


def mapping_records(view: ModelView, mapping: str) -> list[str]:
    """The kernel mapping records a signal mapping owns, in model order."""
    lineage = kernel_lineage(view, SIGNAL_MAPPING_RECORD)
    return [member for member in view.index.owned_members(mapping) if view.index.typed_by(member) & lineage]


def vss_signal_paths(view: ModelView) -> Mapping[str, tuple[str, ...]]:
    """Element -> the VSS paths its signal metadata names: every element that a metadata usage typed by
    the bound VSS signal metadata annotates, read from the usage's Annotation relationships, or, with
    none, its owner (KerML's annotated element; ``@VssSignalMetadata about Vehicle_Speed { path =
    "Vehicle.Speed"; }``, as COVESA_VSS and DE4SDV_VSS_Extensions declare each signal), once per corpus.
    Metadata of another definition, a ``path`` included, is no VSS typing. Raises
    :class:`MethodSideInput` when the VSS signal metadata is unbound."""
    lineage = library_lineage(view, VSS_SIGNAL_METADATA)

    def build() -> Mapping[str, tuple[str, ...]]:
        index = view.index
        found: dict[str, list[str]] = {}
        for metadata in index.elements_of_type("MetadataUsage"):
            if not index.typed_by(metadata) & lineage:
                continue
            paths = [str(leaf.value) for leaf in index.feature_values(metadata, VSS_PATH)
                     if leaf.kind == "string" and str(leaf.value or "").strip()]
            if not paths:
                continue
            annotated = [element for relationship in index.owned_relationships(metadata, "Annotation")
                         for element in reference_ids(relationship.get("annotatedElement"))]
            owner = index.owner_of(metadata)
            for element in dict.fromkeys(annotated or ([owner] if owner else [])):
                bucket = found.setdefault(element, [])
                bucket.extend(path for path in paths if path not in bucket)
        return MappingProxyType({element: tuple(paths) for element, paths in found.items()})

    return view.index.memo(("vss-signal-paths", lineage), build)


def carried_vss_paths(view: ModelView, element: str) -> list[str]:
    """The VSS paths of the signals ``element`` carries: of its definitions, and of the features it and
    they own (a port's items, an item's attributes), to a bounded depth. A path in a doc or a string is
    no VSS typing. Raises :class:`MethodSideInput` when the VSS signal metadata is unbound."""
    signals = vss_signal_paths(view)
    found: list[str] = []
    seen: set[str] = set()
    frontier = [(element, 0)]
    while frontier:
        current, depth = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        for definition in type_lineage(view, current):
            found.extend(path for path in signals.get(definition, ()) if path not in found)
        if depth < _VSS_DEPTH:
            frontier.extend((feature, depth + 1) for feature in member_features(view, current)
                            if str(view.index.element(feature).get("@type")) in SIGNAL_CARRIERS)
    return found


#: The usages through which an endpoint carries a signal (a port's items, an item's attributes); a signal
#: mapping's VSS typing is read only at a target of these kinds, never at an element.
SIGNAL_CARRIERS = frozenset({"PortUsage", "ItemUsage", "AttributeUsage", "ReferenceUsage"})


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
            for connection, (ends, problem) in sorted(connection_ends(view).items()):
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
            absent=f"{name} has no {carrier} connection to a {class_declaration(view, target_class)}",
        )

    check.__name__ = f"connection_{relation}"
    return check


def allocation_carried_check(relation: str) -> RelationCheck:
    """A successor relation carried by native allocations: the subject is the source end of an
    allocation that grounds one of the relation's end pairs. Without one, an unreadable allocation
    anywhere makes the result a model-witness problem (absence is not established)."""

    def check(view: ModelView, subject_id: str) -> RelationResult:
        name = element_name(view, subject_id)
        try:
            hops, problems = allocation_hops(view, relation, subject_id)
            classes = allocation_classes(view, relation, subject_id)
            near_misses = () if hops else allocation_near_misses(view, relation, subject_id, classes)
        except MethodSideInput as missing:
            return RelationResult(relation, subject_id, problem=missing.marker, detail=missing.detail)
        if not hops and problems:
            reason = unreadable_allocations(problems)
            return RelationResult(relation, subject_id, problem=MODEL_WITNESS_PREFIX + relation,
                                  detail=reason, reason=reason)
        reached = " or ".join(class_declaration(view, c) for c in classes)
        return RelationResult(
            relation, subject_id, hops=tuple(hops),
            absent=(f"{name} is allocated to no {reached}" if reached
                    else f"{name} grounds in no source class of the {relation} end pairs"),
            near_misses=near_misses,
        )

    check.__name__ = f"allocation_{relation}"
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
        allocated = {name for name, _row in native_allocation_rows(view)}
        table: dict[str, RelationCheck] = {}
        for relation in sorted(getattr(contract, "relationships", {}) or {}):
            try:
                strategy = contract.relationship_mapping(relation).strategy
            except Exception:  # noqa: BLE001 - unmapped: decided as method side
                strategy = ""
            pinned = str((carriers.get(relation) or {}).get("declaration") or "")
            if strategy == "successor" and pinned.startswith("connection def "):
                table[relation] = connection_carried_check(relation)
            elif strategy == "successor" and relation in allocated:
                table[relation] = allocation_carried_check(relation)
            else:
                table[relation] = governed_relation_check(relation)
        if set(table) & set(_NATIVE_CHECKS):
            raise ValueError(f"contract relations shadow native relations: {sorted(set(table) & set(_NATIVE_CHECKS))}")
        return MappingProxyType({**table, **_NATIVE_CHECKS})

    return view.index.memo_bound(("relation-checks",), (view.contract,), build)


def check_relation(view: ModelView, relation: str, subject_id: str) -> RelationResult:
    """What ``relation`` reaches from one subject element."""
    return relation_checks(view)[relation](view, subject_id)
