"""Traversal and query surfaces of the trace relations over exact API bindings.

The trace relations (``allocatedTo``, ``hasValidationScenario`` and its
inverse, ``hasRegulatorySource``) and the retired relation names come from the
generated trace-vocabulary contract (:func:`model_contract.load_trace_contract`);
the model-authority runtime composes these classes with the model-built kernel
contract. Endpoint and carrier identity comes from ingestion-validated kernel
bindings, never from names or SysML text.

The ends of a native connector are read with the method's reader
(:mod:`de4sdv.semantic.relation_checks`), so the services and the method checks
follow one reading rule: an allocation's ends through
:func:`~de4sdv.semantic.relation_checks.allocation_ends` (EndFeatureMembership,
then the authored ReferenceSubsetting; an end written as a feature chain reads
as its last chaining feature), a typed connection's through
:func:`~de4sdv.semantic.relation_checks.connection_ends`. Derived ``source`` and
``target`` keys are not read: the licensed export has no ``source``, and its
``target`` names a chained end's chain, not the feature it ends in. Which end
pair an allocation grounds in is decided by the method's reader too
(:func:`~de4sdv.semantic.relation_checks.allocation_hops`); the traversal adds
its witness checks (identity, owning context, decidable typing evidence) and
reports a witness it cannot decide as incomplete.
"""
from __future__ import annotations
import posixpath
from typing import Any, Iterable, Mapping
from urllib.parse import unquote, urlsplit
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id, reference_ids
from .increment_scope import ModelView
from .kernel_binding_index import KernelBindingIndex
from .query import SemanticQueryService
from .relation_checks import (MethodSideInput, allocation_ends, allocation_hops, allocation_pairs,
                              connection_ends)
from .traversal import SemanticTraversal, TraversalHop
from .model_edges import (is_subsumption_hop, is_typing_hop,
                          SUBSUMPTION_FAMILIES, SUBSUMPTION_INLINE_KEYS,
                          TYPING_FAMILIES, TYPING_INLINE_KEYS,
                          REFERENCE_SUBSETTING_FAMILIES)
from .relationships import build_relationship_graph, is_family

#: What an allocatedTo or planning hop never claims.
CLAIM_BOUNDARY = "no satisfaction, execution, result, fulfillment, deployment or compliance"


def unreadable_ends(view: ModelView, connector: str, ends: tuple[str, ...], problem: str, *,
                    kind: str = "connection") -> str:
    """Why a native connector's ends cannot be read, prefixed by the connector ('' when they can).

    The shared reader's own problem; an owned relationship of the connector (an end membership may be
    among them) or one of its read ends that the revision does not hold; or, once the connector owns an
    end, a number of ends other than two. A connector that owns no end is no fact, not unreadable.
    While any connector of a relation cannot be read, the relation's answers are incomplete: the
    connector's ends are unknown, so it may be the one that reaches the subject.
    """
    by_id = view.index.by_id
    reason = problem
    if not reason:
        missing = [r for r in reference_ids(view.index.element(connector).get("ownedRelationship"))
                   if r not in by_id]
        dangling = [end for end in ends if end not in by_id]
        if missing:
            reason = f"its owned relationship {missing[0]!r} is not in the bound revision"
        elif dangling:
            reason = f"its end {dangling[0]!r} is not in the bound revision"
        elif ends and len(ends) != 2:
            reason = f"{len(ends)} ends, a binary {kind} has 2"
    return f"{view.label(connector)}: {reason}" if reason else ""


class SuccessorTraversal(SemanticTraversal):
    # Mirror only serializer mechanics, not ontology meaning. Keep raw objects
    # alongside the frozen graph so dropped members cannot prove completeness.
    _RAW_SOURCES = ("subclassifier", "specific", "owningRelatedElement", "owner", "source",
                    "subsettingFeature", "redefiningFeature", "typedFeature", "memberElement")
    _RAW_TARGETS = ("superclassifier", "general", "supertype", "type", "declaredType",
                    "subsettedFeature", "redefinedFeature", "target", "owningRelatedElement",
                    "ownedRelatedElement")

    def __init__(self, contract, kernel_bindings):
        super().__init__(contract, kernel_bindings)
        self.unsupported = []

    def unavailable(self, predicate, reason, state="incomplete"):
        record = dict(predicate=predicate, authority_state=state, reason=str(reason))
        if record not in self.unsupported:
            self.unsupported.append(record)

    def traverse(self, predicate, source, elements):
        if predicate in self.contract.profile["retired"]:
            self.unavailable(predicate, self.contract.profile["retired"][predicate], "retired")
            return []
        try:
            canonical = self.contract._inverse.get(predicate, predicate)
            rows = self.contract.profile["relations"].get(canonical)
            if rows:
                return self._successor_hops(predicate, canonical, rows, source, elements)
            mapping = self.contract.relationship_mapping(predicate)
            if mapping.strategy == "dependency":
                # Native Dependency has client/supplier as well as derived source/target.
                # Normalize mechanics only, preserving original objects and weak meaning.
                # The normalized corpus is built once per corpus (revision index).
                def normalize():
                    normalized = []
                    originals = {}
                    for item in elements:
                        if item.get("@type") != "Dependency":
                            normalized.append(item)
                            continue
                        copy = dict(item)
                        for native, derived in [("client", "source"), ("supplier", "target")]:
                            n, d = reference_ids(item.get(native)), reference_ids(item.get(derived))
                            if n and d and set(n) != set(d):
                                raise IdentityNotFoundError("inconsistent native Dependency " + native)
                            if n:
                                copy[derived] = item[native]
                        normalized.append(copy)
                        originals[element_id(copy)] = item
                    return normalized, originals

                normalized, originals = self.revision_index(elements).memo(
                    "dependency-normalized", normalize)
                hops = super().traverse(predicate, source, normalized)
                from dataclasses import replace
                return [replace(hop, api_object=originals.get(element_id(hop.api_object), hop.api_object),
                    witness={**hop.witness,
                             "native_client": reference_ids(hop.api_object.get("source")),
                             "native_supplier": reference_ids(hop.api_object.get("target")),
                             "claim_boundary": "specification/change-impact dependence only"}) for hop in hops]
            return super().traverse(predicate, source, elements)
        except IdentityNotFoundError as exc:
            self.unavailable(predicate, exc)
            return []

    @staticmethod
    def _checked_references(item, key):
        """Validate raw members before any lossy ID/graph projection.

        Null/empty optional properties are absence; a supplied list member is
        evidence and must carry a nonblank string identity. Never salvage an
        unidentified member from its URI, name, metaclass or another witness.
        """
        value = item.get(key)
        if value is None:
            return []
        members = value if isinstance(value, list) else [value]
        for member in members:
            if not isinstance(member, dict):
                raise IdentityNotFoundError(f"unsupported raw {key} reference member")
            identities = [member[k] for k in ("@id", "elementId", "id") if k in member]
            if (not identities or any(not isinstance(i, str) or not i.strip() for i in identities)
                    or len(set(identities)) != 1):
                raise IdentityNotFoundError(f"missing, blank or conflicting raw {key} reference identity")
        return members

    @classmethod
    def _checked_reference_ids(cls, item, key):
        return [element_id(ref) for ref in cls._checked_references(item, key)]

    @classmethod
    def _raw_relationship_index(cls, elements):
        """Route raw flat/owned witnesses without discarding their members.

        ID extraction here is association only. Every associated raw field is
        validated at use, including unidentified relationship objects that the
        ordinary element index cannot retain. Unlocatable witnesses remain an
        undecidable candidate rather than silently disappearing.
        """
        index = {}

        def collect(item, parent=None):
            if not isinstance(item, dict):
                index.setdefault(parent, []).append(item)
                return
            kind = str(item.get("@type") or "")
            if is_family(kind, TYPING_FAMILIES + SUBSUMPTION_FAMILIES + REFERENCE_SUBSETTING_FAMILIES):
                sources = {i for key in cls._RAW_SOURCES for i in reference_ids(item.get(key))}
                for source in sources or {parent}:
                    index.setdefault(source, []).append(item)
            for key in ("ownedRelationship", "ownedElement", "ownedMember"):
                children = item.get(key)
                if children is None:
                    continue
                for child in children if isinstance(children, list) else [children]:
                    collect(child, element_id(item) or parent)

        for item in elements:
            collect(item)
        return index

    @classmethod
    def _raw_targets(cls, identifier, node, raw_index, families, inline_keys, extra_target_keys=()):
        references = [ref for key in inline_keys for ref in cls._checked_references(node, key)]
        for item in raw_index.get(identifier, []) + raw_index.get(None, []):
            if not isinstance(item, dict):
                raise IdentityNotFoundError("unsupported raw owned relationship member")
            if not is_family(str(item.get("@type") or ""), families):
                continue
            if item in raw_index.get(None, []):
                raise IdentityNotFoundError("raw relationship source is absent or undecidable")
            # A relationship that names no target is a reference the export leaves out: the
            # licensed serializer omits every reference to an element outside the export (the
            # standard library), implied or authored. No such element is in a governed lineage,
            # so it supplies no meaning; a target that is named but missing stays undecided. The
            # import asserts that every such skip is a standard-library omission
            # (targetless_check), so the skip cannot hide a governed type.
            references.extend(cls._named_targets(item, identifier, extra_target_keys))
        return references

    @classmethod
    def _named_targets(cls, item, identifier, extra_target_keys=()):
        """The validated targets a raw relationship names, other than ``identifier`` (its source)."""
        cls._checked_references({"witness": item}, "witness")
        for key in cls._RAW_SOURCES:
            cls._checked_references(item, key)
        targets = [ref for key in cls._RAW_TARGETS + extra_target_keys
                   for ref in cls._checked_references(item, key)]
        return [ref for ref in targets if element_id(ref) != identifier]

    @classmethod
    def targetless_relationships(cls, elements):
        """The ids of the typing and specialization relationships the traversal skips for naming no
        target (sorted). A relationship it cannot read is refused at use (incomplete), not skipped."""
        found = set()
        for source, items in cls._raw_relationship_index(elements).items():
            if source is None:
                continue
            for item in items:
                if not isinstance(item, dict) or not is_family(str(item.get("@type") or ""),
                                                               TYPING_FAMILIES + SUBSUMPTION_FAMILIES):
                    continue
                try:
                    if not cls._named_targets(item, source):
                        found.add(element_id(item))
                except IdentityNotFoundError:
                    continue
        return sorted(found)

    @classmethod
    def _successor_graph(cls, elements, raw_index):
        """Supplement frozen mechanics with validated list-valued lineage.

        These are local graph projections of supplied API witnesses, not new
        API objects or source-inferred relationships. Retain exact witness ID,
        family, implication and target URI. Invalid witnesses stay in the raw
        index for the candidate completeness guard, never normalized away.
        """
        projections = []
        families = TYPING_FAMILIES + SUBSUMPTION_FAMILIES
        for source, items in raw_index.items():
            if source is None:
                continue
            for item in items:
                if not isinstance(item, dict) or not is_family(str(item.get("@type") or ""), families):
                    continue
                try:
                    targets = cls._raw_targets(source, {}, {source: [item]}, families, ())
                except IdentityNotFoundError:
                    continue
                projections.extend({"@id": element_id(item), "@type": item["@type"],
                    "source": {"@id": source}, "target": target,
                    "isImplied": item.get("isImplied") is True} for target in targets)
        return build_relationship_graph(elements + projections)


    @classmethod
    def _typing_is_unresolved(cls, endpoint, graph, by_id, raw_index, *, require_typing=True):
        """True when the endpoint's referenced typing evidence cannot decide.

        Every typing/specialization branch must be represented, not merely one
        successful path to a governed root. Missing branches could supply a
        competing meaning. An explicit library URI witnesses an external leaf;
        fully represented unrelated lineage remains supported absence.
        """
        endpoint_id = element_id(endpoint)
        if endpoint_id is None:
            return True
        typed = any(is_typing_hop(hop) for hop in graph.outgoing(endpoint_id))
        raw_typed = cls._raw_targets(endpoint_id, endpoint, raw_index, TYPING_FAMILIES,
                                    TYPING_INLINE_KEYS)
        if require_typing and not (typed or raw_typed):
            return True
        pending, seen = [endpoint_id], set()
        while pending:
            identifier = pending.pop()
            if identifier in seen:
                continue
            seen.add(identifier)
            node = by_id[identifier]
            raw_targets = cls._raw_targets(identifier, node, raw_index,
                TYPING_FAMILIES + SUBSUMPTION_FAMILIES,
                TYPING_INLINE_KEYS + SUBSUMPTION_INLINE_KEYS)
            external_ids = {element_id(ref) for ref in raw_targets
                            if isinstance(ref.get("@uri"), str) and ref["@uri"].strip()}
            for ref in raw_targets:
                target = element_id(ref)
                assert target is not None  # validated before projection
                if target in by_id:
                    pending.append(target)
                elif target not in external_ids:
                    return True
            for hop in graph.outgoing(identifier):
                if not (is_typing_hop(hop) or is_subsumption_hop(hop)):
                    continue
                if hop.target in by_id:
                    pending.append(hop.target)
                    continue
                # The frozen graph preserves URI on relationship objects but
                # not inlined properties; recover only the exact target's
                # explicit URI from its containing API object, never a name.
                if hop.target not in external_ids:
                    return True
        return False

    def _governed_meanings(self, relationship, left, right, resolver_for):
        """Canonical predicates this exact object carries under the profile.

        Endpoint lineage, usage kinds and carrier lineage are classified across
        the whole governed profile, so a multiply typed carrier cannot acquire
        one meaning per predicate invocation. An alternative whose identity
        cannot be resolved is not counted as a second meaning; the queried
        predicate still fails closed on its own bindings.
        """
        meanings = set()
        for name, profile_rows in self.contract.profile["relations"].items():
            for row in profile_rows:
                try:
                    if (left.get("@type") != row["sourceUsage"]
                            or right.get("@type") != row["targetUsage"]):
                        continue
                    if (row["mechanism"] == "typed-connection"
                            and not self._endpoint_grounding(relationship, resolver_for(name))):
                        continue
                    if not self._endpoint_grounding(left, resolver_for(row["sourceClass"])):
                        continue
                    if not self._endpoint_grounding(right, resolver_for(row["targetClass"])):
                        continue
                except IdentityNotFoundError:
                    continue
                meanings.add(name)
                break
        return meanings

    @staticmethod
    def _context(relationship, index):
        """The connector's owning namespace: the one owner its owning relationship names (the export's
        shape), else a derived owner key. An absent or dangling context refuses, and so does an owning
        relationship that the revision does not hold or that names other than one owner."""
        membership = element_id(relationship.get("owningRelationship"))
        if membership is not None:
            contexts = reference_ids(index.by_id.get(membership, {}).get("owningRelatedElement"))
        else:
            contexts = (reference_ids(relationship.get("owningNamespace"))
                        or reference_ids(relationship.get("owner"))
                        or reference_ids(relationship.get("owningRelatedElement")))
        if len(contexts) != 1 or contexts[0] not in index.by_id:
            raise IdentityNotFoundError("native connection context is absent or dangling")
        return contexts[0]

    def _may_carry(self, connection, ends, reader_problem, carriers, view, graph, raw_index):
        """Whether a connection whose ends cannot be read as two could still carry the relation, so its
        unknown ends leave every answer incomplete: typed by the relation's carrier (as the method
        selects it), typing evidence that cannot decide, or untyped with ends that cannot be read. One
        typed by another definition, or an untyped one whose readable ends are not two (no binary
        carrier lacking its typing), carries none of the relation's facts."""
        by_id = view.index.by_id
        if view.index.typed_by(element_id(connection)) & carriers():
            return True
        if self._typing_is_unresolved(connection, graph, by_id, raw_index, require_typing=False):
            return True
        if not self._typing_is_unresolved(connection, graph, by_id, raw_index):
            return False
        readable = (not reader_problem and all(end in by_id for end in ends)
                    and all(r in by_id for r in reference_ids(connection.get("ownedRelationship"))))
        return not readable

    def _carrier_candidate(self, left, right, rows, resolver_for, graph, by_id, raw_index):
        """True when an untyped connection's ends ground in an end pair of the relation, so it could be a
        carrier that lacks its typing; its endpoints' typing evidence must decide."""
        for endpoint in (left, right):
            if self._typing_is_unresolved(endpoint, graph, by_id, raw_index, require_typing=False):
                raise IdentityNotFoundError("usage endpoint typing evidence is missing or unresolved")
        return any(self._endpoint_grounding(left, resolver_for(row["sourceClass"]))
                   and self._endpoint_grounding(right, resolver_for(row["targetClass"])) for row in rows)

    def _successor_hops(self, predicate, canonical, rows, source, elements):
        """The hops of one successor relation from ``source``.

        A connector's ends are the method's reading of its native ends (``allocation_ends`` or
        ``connection_ends``): the first end is the source, the second the target. A connector whose
        ends cannot be read as two (:func:`unreadable_ends`) leaves every answer of the relation
        incomplete when it may carry the relation: any allocation, and a connection typed by the
        carrier, with typing that cannot decide, or untyped with ends that cannot be read
        (``_may_carry``). For native allocations the method's reader also decides the end pair
        (``allocation_hops``: the one end pair both ends ground in through the validated kernel
        bindings; an end grounding in two endpoint classes, or an allocation it cannot read, leaves
        the relation incomplete). For typed connections the profile rows decide (carrier typing, usage
        kinds, endpoint lineage); an untyped connection is incomplete only when its ends ground in an
        end pair (``_carrier_candidate``), else it is no fact. A witness whose identity, owning context
        or typing evidence cannot be decided is incomplete, never a hop and never an absence.
        """
        index = self.revision_index(elements)
        by_id = index.by_id
        raw_index = index.memo("successor-raw-index", lambda: self._raw_relationship_index(elements))
        graph = index.memo("successor-graph", lambda: self._successor_graph(elements, raw_index))
        view = ModelView(elements, self)
        source_id = element_id(source)
        inverse = predicate != canonical
        allocation = rows[0]["mechanism"] == "native-allocation"
        mechanical_type = "AllocationUsage" if allocation else "ConnectionUsage"
        reached = set()
        if allocation:
            try:
                counted, problems = allocation_hops(view, canonical, source_id, incoming=inverse)
            except MethodSideInput as missing:
                self.unavailable(predicate, missing)
                return []
            for problem in problems:
                self.unavailable(predicate, problem)
            reached = {other for other, _allocation in counted}
        native_ends = allocation_ends(view) if allocation else connection_ends(view)
        resolvers = {}
        carrier_ids = []

        def carriers():
            if not carrier_ids:
                carrier_ids.append(frozenset(self.class_lineage(canonical, elements)["explicit_lineage_ids"]))
            return carrier_ids[0]

        def resolver_for(class_name):
            if class_name not in resolvers:
                resolvers[class_name] = self._lineage_resolver(class_name, by_id, graph)
            return resolvers[class_name]

        result = []
        for rel in elements:
            if rel.get("@type") != mechanical_type:
                continue
            try:
                self._checked_references({"witness": rel}, "witness")
                ends, reader_problem = native_ends.get(element_id(rel), ((), ""))
                if allocation and reader_problem:
                    continue  # reported by the method's reader above (absence is not established)
                problem = unreadable_ends(view, element_id(rel), ends, reader_problem,
                                          kind="allocation" if allocation else "connection")
                if problem and (allocation or self._may_carry(rel, ends, reader_problem, carriers, view,
                                                              graph, raw_index)):
                    raise IdentityNotFoundError(problem)
                if problem or not ends:
                    continue  # it cannot carry the relation, or owns no end: no fact
                sources, targets = list(ends[:1]), list(ends[1:])
                if source_id not in (targets if inverse else sources):
                    continue
                context = self._context(rel, index)
                left, right = by_id[sources[0]], by_id[targets[0]]
                if self._typing_is_unresolved(rel, graph, by_id, raw_index, require_typing=False):
                    raise IdentityNotFoundError("carrier typing evidence is missing or unresolved")
                if not allocation and self._typing_is_unresolved(rel, graph, by_id, raw_index):
                    # Untyped: no carrier. Incomplete only when its ends could carry the relation.
                    if self._carrier_candidate(left, right, rows, resolver_for, graph, by_id, raw_index):
                        raise IdentityNotFoundError("carrier typing evidence is missing or unresolved")
                    continue
                if allocation:
                    for endpoint in (left, right):
                        if self._typing_is_unresolved(endpoint, graph, by_id, raw_index, require_typing=False):
                            raise IdentityNotFoundError("usage endpoint typing evidence is missing or unresolved")
                    if (sources[0] if inverse else targets[0]) not in reached:
                        continue  # the ends ground in no end pair: supported absence
                    pairs = allocation_pairs(view, canonical, sources[0], targets[0])
                    if len(pairs) != 1:
                        raise IdentityNotFoundError("overlapping endpoint identity routing")
                    row = pairs[0]
                    result.append(TraversalHop(predicate, "allocation", row["strength"],
                        right if inverse else left, left if inverse else right, rel,
                        dict(source_lineage=view.grounding(sources[0], str(row["sourceClass"])),
                             target_lineage=view.grounding(targets[0], str(row["targetClass"])),
                             source_root=view.kernel_element(str(row["sourceClass"])),
                             target_root=view.kernel_element(str(row["targetClass"])),
                             native_source=sources[0], native_target=targets[0], context_id=context,
                             carrier=row["carrier"], canonical_predicate=canonical,
                             claim_boundary=CLAIM_BOUNDARY)))
                    continue
                if len(self._governed_meanings(rel, left, right, resolver_for)) > 1:
                    raise IdentityNotFoundError("carrier grounds under overlapping governed endpoint meanings")
                for row in rows:
                    if left.get("@type") != row["sourceUsage"] or right.get("@type") != row["targetUsage"]:
                        continue
                    carrier = resolver_for(canonical) if row["mechanism"] == "typed-connection" else None
                    lr = resolver_for(row["sourceClass"])
                    rr = resolver_for(row["targetClass"])
                    for endpoint in (left, right):
                        if self._typing_is_unresolved(endpoint, graph, by_id, raw_index):
                            raise IdentityNotFoundError("usage endpoint typing evidence is missing or unresolved")
                    if (row["mechanism"] == "typed-connection"
                            and not self._endpoint_grounding(rel, carrier)):
                        continue
                    lg, rg = self._endpoint_grounding(left, lr), self._endpoint_grounding(right, rr)
                    if not lg or not rg:
                        # A fully resolved unrelated lineage is supported absence;
                        # missing or dangling discrimination was refused above.
                        continue
                    if len([r for r in rows if r["sourceClass"] == row["sourceClass"] and r["targetClass"] == row["targetClass"]]) != 1:
                        raise IdentityNotFoundError("overlapping endpoint identity routing")
                    result.append(TraversalHop(predicate, "typed-connection",
                        row["strength"], right if inverse else left, left if inverse else right, rel,
                        dict(source_lineage=lg, target_lineage=rg,
                             source_root=lr["root_id"], target_root=rr["root_id"],
                             native_source=sources[0], native_target=targets[0],
                             context_id=context, carrier=row["carrier"],
                             canonical_predicate=canonical, claim_boundary=CLAIM_BOUNDARY)))
            except (IdentityNotFoundError, MethodSideInput) as exc:
                self.unavailable(predicate, exc)
        # One API object cannot acquire two governed endpoint meanings.
        keys = [(element_id(h.api_object), element_id(h.source), element_id(h.target)) for h in result]
        if len(keys) != len(set(keys)):
            self.unavailable(predicate, "overlapping endpoint lineage identity routing")
            return []
        return result


#: The schema of the import's target-less relationship check.
TARGETLESS_SCHEMA = "de4sdv.targetless-relationships/v1"


def _standard_library_uri(uri: str, source_file: str) -> bool:
    """True when ``uri`` names a file of the SysML standard library: an absolute file URI into the
    ``sysml.library`` the serializer ships, or, from an element of a standard-library document the
    export carries (``@library/...``), a relative URI that stays inside the library."""
    parts = urlsplit(uri)
    if parts.scheme or parts.netloc:
        return parts.scheme == "file" and "/sysml.library/" in unquote(parts.path)
    if not parts.path or not source_file.startswith("@library/"):
        return False
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_file), unquote(parts.path)))
    return resolved.startswith("@library/")


def targetless_check(elements: Iterable[Mapping[str, Any]], external_references: Iterable[Mapping[str, Any]],
                     element_sources: Mapping[str, str]) -> dict[str, Any]:
    """Every relationship the successor traversal skips for naming no target must be a reference
    the serializer left out because it names a standard-library element: at least one
    external-reference row records the relationship's target, and every row on a target key has a
    standard-library URI. Anything else could hide a governed type, so the import fails closed."""
    rows: dict[str, list[Mapping[str, Any]]] = {}
    for row in external_references:
        rows.setdefault(str(row.get("source_element_id")), []).append(row)
    target_keys = set(SuccessorTraversal._RAW_TARGETS)
    targetless = SuccessorTraversal.targetless_relationships(list(elements))
    violations = []
    for relationship in targetless:
        on_targets = [row for row in rows.get(relationship, ())
                      if str(row.get("property_path") or "").split("[", 1)[0] in target_keys]
        source_file = str(element_sources.get(relationship) or "")
        outside = [str(row.get("uri") or "") for row in on_targets
                   if not _standard_library_uri(str(row.get("uri") or ""), source_file)]
        if not on_targets:
            violations.append({"relationship": relationship, "source_file": source_file,
                               "reason": "no external reference records its target"})
        elif outside:
            violations.append({"relationship": relationship, "source_file": source_file,
                               "reason": "its target is outside the standard library", "uri": outside[0]})
    return {"schema": TARGETLESS_SCHEMA, "targetless": len(targetless),
            "standard_library": len(targetless) - len(violations), "violation_count": len(violations),
            "violations": violations[:20], "passed": not violations}


class SuccessorQueryService(SemanticQueryService):
    def _decorate(self, report: dict[str, Any]) -> dict[str, Any]:
        records = list(report.get("unsupported_predicates", []))
        for record in self.traversal.unsupported:
            if record not in records:
                records.append(record)
        report["unsupported_predicates"] = records
        report["semantic_status"] = "incomplete" if records else "complete"
        report["semantic_authority"] = self.contract.provenance()
        return report

    def semantic_neighbors(self, identifier, *, predicates=None):
        self.traversal.unsupported = []
        return self._decorate(super().semantic_neighbors(identifier, predicates=predicates))

    def trace(self, source_identifier, target_identifier, *, max_depth=4):
        self.traversal.unsupported = []
        return self._decorate(super().trace(source_identifier, target_identifier, max_depth=max_depth))

    def impact(self, identifier):
        # No universal chain obligations and no retired realization/deployment labels.
        # Bounded reachability exposes individual witnessed edges, not inferred allocations.
        self.traversal.unsupported = []
        resolution, elements = self._resolve(identifier)
        root = resolution.element
        nodes = {element_id(root): self._compact_element(root)}
        edges, seen = [], set()
        frontier = [(root, 0)]
        while frontier:
            current, depth = frontier.pop(0)
            eid = element_id(current)
            if eid in seen or depth >= 4:
                continue
            seen.add(eid)
            for predicate in self._mapped_predicates():
                if predicate in self.traversal.blocked_predicates():
                    self.traversal.unavailable(predicate, self._blocked_unsupported(predicate)["reason"], "blocked")
                    continue
                for hop in self.traversal.traverse(predicate, current, elements):
                    edge = self._edge(hop)
                    if edge not in edges:
                        edges.append(edge)
                    nodes[element_id(hop.target)] = self._compact_element(hop.target)
                    frontier.append((hop.target, depth + 1))
        report = dict(query="impact", revision=self._revision(),
            root={**self._compact_element(root), "resolution_level": resolution.level},
            nodes=list(nodes.values()), edges=edges, gaps=[], provenance=self._provenance(),
            traversal_boundary=dict(max_depth=4, inferred_facts=False))
        return self._decorate(report)

    def verification_coverage(self, requirement_identifier):
        # Frozen native verification behavior remains distinct from planning associations.
        self.traversal.unsupported = []
        report = super().verification_coverage(requirement_identifier)
        report = self._decorate(report)
        if report["semantic_status"] == "incomplete":
            report["status"] = "partial" if report["verification_edges"] else "incomplete"
        return report

    def model_status(self):
        report = super().model_status()
        report["semantic_authority"] = self.contract.provenance()
        return report


def route_successor_bindings(contract, binding):
    """Route profile slots from exact ingestion pins, not ontology/native names.

    Licensed ingestion still validates the authored ontology as-is. A separately
    mapped extension class may hold a pin requested by a narrower profile slot.
    This scoped index aliases that validated pin only; it does not rewrite the
    revision binding, global ontology, predecessor index or production selector.
    Missing pins stay incomplete, conflicting/ambiguous pins fail closed.
    """
    from dataclasses import replace
    from types import SimpleNamespace
    original = KernelBindingIndex.from_binding(binding)
    pins = {**contract["classes"], **contract["carriers"]}
    routed = [b for b in binding.kernel_bindings if b.ontology_class not in pins]
    routes = []
    for name, pin in pins.items():
        candidates = [b for b in binding.kernel_bindings
                      if b.source_file == pin["file"] and b.declaration == pin["declaration"]]
        if len(candidates) > 1:
            raise IdentityNotFoundError(f"ambiguous exact successor binding for {name}")
        if not candidates:
            if name in original._by_class:
                raise IdentityNotFoundError(f"wrong exact successor binding for {name}")
            continue
        selected = candidates[0]
        routed = [b for b in routed if b.ontology_class != selected.ontology_class]
        routed.append(replace(selected, ontology_class=name))
        routes.append(dict(profile_class=name, ingestion_class=selected.ontology_class,
                           element_id=selected.element_id, **pin))
    return KernelBindingIndex.from_binding(SimpleNamespace(kernel_bindings=tuple(routed))), routes
