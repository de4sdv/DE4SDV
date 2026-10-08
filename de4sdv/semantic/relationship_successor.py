"""Relationship-successor traversal and query surfaces over exact API bindings.

The successor contract is model-derived (``relationship_successor_contract``);
the model-authority runtime composes these classes with the model-built kernel
contract. Constructed values never come from decisions JSON.
"""
from __future__ import annotations
from typing import Any
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id, reference_ids
from .kernel_binding_index import KernelBindingIndex
from .query import SemanticQueryService
from .traversal import SemanticTraversal, TraversalHop
from .model_edges import (is_reference_subsetting_hop, is_subsumption_hop, is_typing_hop,
                          SUBSUMPTION_FAMILIES, SUBSUMPTION_INLINE_KEYS,
                          TYPING_FAMILIES, TYPING_INLINE_KEYS,
                          REFERENCE_SUBSETTING_FAMILIES)
from .relationships import build_relationship_graph, is_family


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
            cls._checked_references({"witness": item}, "witness")
            for key in cls._RAW_SOURCES:
                cls._checked_references(item, key)
            targets = [ref for key in cls._RAW_TARGETS + extra_target_keys
                       for ref in cls._checked_references(item, key)]
            targets = [ref for ref in targets if element_id(ref) != identifier]
            if not targets:
                raise IdentityNotFoundError("raw typing/specialization target is absent")
            references.extend(targets)
        return references

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


    @staticmethod
    def _normalize_references(references):
        """Collapse equivalent graph/flat shapes, never a competing target.

        One native reference can appear both as a relationship-graph hop and as
        a flat ``ReferenceSubsetting`` object. Equivalent source/target pairs
        are the same fact; a disagreement survives normalization so the caller
        refuses it structurally instead of dropping one shape.
        """
        unique = {}
        for reference in references:
            unique.setdefault((reference["source"], reference["target"]), reference)
        return list(unique.values())

    def _endpoints(self, relationship, key, by_id, graph, raw_index):
        resolved, witnesses = [], []
        identifiers = self._checked_reference_ids(relationship, key)
        if not identifiers:
            raise IdentityNotFoundError("native connection endpoint is absent")
        for identifier in identifiers:
            seen = set()
            while True:
                if identifier in seen or identifier not in by_id:
                    raise IdentityNotFoundError("dangling or cyclic connection endpoint")
                seen.add(identifier)
                # Validate all raw shapes before equivalent witnesses coalesce.
                self._raw_targets(identifier, by_id[identifier], raw_index,
                    REFERENCE_SUBSETTING_FAMILIES, ("referencedFeature",), ("referencedFeature",))
                # Graph hops expose the native witness identity as ``witness_id``
                # (the removed ``relationship_id`` never existed on Hop).
                graph_references = [
                    dict(source=hop.source, target=hop.target, kind=hop.kind,
                         api_object_id=hop.witness_id)
                    for hop in graph.outgoing(identifier) if is_reference_subsetting_hop(hop)]
                # The frozen graph can omit flat/owned/list-valued references.
                # Normalize only the validated raw native serializer shapes.
                flat_references = [
                    dict(source=identifier, target=target, kind=item["@type"],
                         api_object_id=element_id(item))
                    for item in raw_index.get(identifier, [])
                    if is_family(str(item.get("@type") or ""), REFERENCE_SUBSETTING_FAMILIES)
                    for target_key in self._RAW_TARGETS + ("referencedFeature",)
                    for target in self._checked_reference_ids(item, target_key)
                    if target != identifier]
                inline_references = [
                    dict(source=identifier, target=target, kind="referencedFeature", api_object_id=identifier)
                    for target in self._checked_reference_ids(by_id[identifier], "referencedFeature")]
                references = self._normalize_references(graph_references + flat_references + inline_references)
                if not references:
                    resolved.append(identifier)
                    break
                targets = {reference["target"] for reference in references}
                if len(targets) != 1:
                    raise IdentityNotFoundError("ambiguous connection reference endpoint")
                witnesses.extend(references)
                identifier = next(iter(targets))
        return list(dict.fromkeys(resolved)), self._normalize_references(witnesses)

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

    def _successor_hops(self, predicate, canonical, rows, source, elements):
        index = self.revision_index(elements)
        by_id = index.by_id
        raw_index = index.memo("successor-raw-index", lambda: self._raw_relationship_index(elements))
        graph = index.memo("successor-graph", lambda: self._successor_graph(elements, raw_index))
        inverse = predicate != canonical
        mechanical_type = "AllocationUsage" if rows[0]["mechanism"] == "native-allocation" else "ConnectionUsage"
        resolvers = {}

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
                sources, sw = self._endpoints(rel, "source", by_id, graph, raw_index)
                targets, tw = self._endpoints(rel, "target", by_id, graph, raw_index)
                if element_id(source) not in (targets if inverse else sources):
                    continue
                if len(sources) != 1 or len(targets) != 1:
                    raise IdentityNotFoundError("native binary connection endpoints are incomplete or ambiguous")
                contexts = reference_ids(rel.get("owningNamespace")) or reference_ids(rel.get("owner")) or reference_ids(rel.get("owningRelatedElement"))
                if len(contexts) != 1 or contexts[0] not in by_id:
                    raise IdentityNotFoundError("native connection context is absent or dangling")
                left, right = by_id[sources[0]], by_id[targets[0]]
                if self._typing_is_unresolved(rel, graph, by_id, raw_index,
                                              require_typing=mechanical_type == "ConnectionUsage"):
                    raise IdentityNotFoundError("carrier typing evidence is missing or unresolved")
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
                    result.append(TraversalHop(predicate,
                        "allocation" if row["mechanism"] == "native-allocation" else "typed-connection",
                        row["strength"], right if inverse else left, left if inverse else right, rel,
                        dict(source_lineage=lg, target_lineage=rg,
                             source_root=lr["root_id"], target_root=rr["root_id"],
                             native_source=sources[0], native_target=targets[0],
                             context_id=contexts[0], reference_witnesses=sw + tw,
                             canonical_predicate=canonical,
                             claim_boundary="no satisfaction, execution, result, fulfillment, deployment or compliance")))
            except IdentityNotFoundError as exc:
                self.unavailable(predicate, exc)
        # One API object cannot acquire two governed endpoint meanings.
        keys = [(element_id(h.api_object), element_id(h.source), element_id(h.target)) for h in result]
        if len(keys) != len(set(keys)):
            self.unavailable(predicate, "overlapping endpoint lineage identity routing")
            return []
        return result


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
