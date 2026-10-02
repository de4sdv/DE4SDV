"""Versioned non-production relationship service over exact API bindings.

Constructed projection/profile values are model-derived, never decisions JSON.
The predecessor is retained as a component, not silently rewritten.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any
from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.repository import element_id, reference_ids
from .api_binding import OntologyApiBinder
from .kernel_binding_index import KernelBindingIndex
from .kernel_contract import KernelFileMapping, RelationshipMapping
from .query import SemanticQueryService
from .traversal import SemanticTraversal, TraversalHop
from .model_edges import is_reference_subsetting_hop, is_subsumption_hop, is_typing_hop
from .relationships import build_relationship_graph


class SuccessorAuthority:
    def __init__(self, base, contract, binding):
        self.base = base
        self.binding_routes = []
        self.profile = json.loads(json.dumps(contract))
        self.identity = base.identity
        self.source = base.source
        self.classes = dict(base.classes)
        for name, pin in contract["classes"].items():
            self.classes[name] = {"kernel": pin}
        self.relationships = {n: s for n, s in base.relationships.items()
                              if n not in contract["retired"] and n not in contract["relations"]}
        self._inverse = {}
        for name, rows in contract["relations"].items():
            self.relationships[name] = {"sysml_mapping": {"strategy": "successor"}}
            if rows[0]["inverse"]:
                inverse = rows[0]["inverse"]
                if inverse in self.relationships:
                    raise ValueError("overlapping successor inverse identity")
                self._inverse[inverse] = name
                self.relationships[inverse] = {"sysml_mapping": {"strategy": "successor"}}
        payload = dict(profile=contract, binding=binding.to_dict(),
                       predecessor=getattr(base, "authority_id", "legacy"),
                       ontology=base.identity.to_dict())
        self.authority_id = "relationship-successor:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def mapping(self, name):
        pin = self.profile["classes"].get(name) or self.profile["carriers"].get(name)
        return KernelFileMapping(**pin) if pin else self.base.mapping(name)

    def class_mapping(self, name):
        pin = self.profile["classes"].get(name) or self.profile["carriers"].get(name)
        return KernelFileMapping(**pin) if pin else self.base.class_mapping(name)

    def relationship_mapping(self, name):
        canonical = self._inverse.get(name, name)
        if canonical in self.profile["relations"]:
            rows = self.profile["relations"][canonical]
            return RelationshipMapping(name, "successor", rows[0]["strength"], {},
                                       rows[0]["sourceClass"], rows[0]["targetClass"])
        if name in self.profile["retired"]:
            return RelationshipMapping(name, "external", "retired", {})
        return self.base.relationship_mapping(name)

    def provenance(self):
        return dict(kind=self.profile["schema"], authority_id=self.authority_id,
                    activation_blocked=True, supersedes=self.profile["supersedes"],
                    contract_id=self.profile["id"], bound_inputs=self.profile["bound_inputs"],
                    predecessor=getattr(self.base, "authority_id", "legacy"),
                    binding_routes=getattr(self, "binding_routes", []),
                    status="non-production; API closure and consumer retirement pending")


class SuccessorTraversal(SemanticTraversal):
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
    def _reference_owners(item):
        owners = set()
        for key in ("owningRelatedElement", "owner", "subsettingFeature"):
            owners.update(reference_ids(item.get(key)))
        return owners

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

    def _endpoints(self, relationship, key, by_id, graph):
        resolved, witnesses = [], []
        for identifier in reference_ids(relationship.get(key)):
            seen = set()
            while True:
                if identifier in seen or identifier not in by_id:
                    raise IdentityNotFoundError("dangling or cyclic connection endpoint")
                seen.add(identifier)
                # Graph hops expose the native witness identity as ``witness_id``
                # (the removed ``relationship_id`` never existed on Hop).
                graph_references = [
                    dict(source=hop.source, target=hop.target, kind=hop.kind,
                         api_object_id=hop.witness_id)
                    for hop in graph.outgoing(identifier) if is_reference_subsetting_hop(hop)]
                # The frozen graph does not collect referencedFeature on a flat
                # ReferenceSubsetting object. Normalize this native serializer
                # shape locally, never changing O3's shared representation code.
                flat_references = [
                    dict(source=identifier, target=target, kind="ReferenceSubsetting",
                         api_object_id=element_id(item))
                    for item in by_id.values()
                    if item.get("@type") == "ReferenceSubsetting"
                    and identifier in self._reference_owners(item)
                    for target in reference_ids(item.get("referencedFeature"))]
                inline_references = [
                    dict(source=identifier, target=target, kind="referencedFeature", api_object_id=identifier)
                    for target in reference_ids(by_id[identifier].get("referencedFeature"))]
                references = self._normalize_references(graph_references + flat_references + inline_references)
                if not references:
                    resolved.append(identifier)
                    break
                targets = {reference["target"] for reference in references}
                if len(targets) != 1:
                    raise IdentityNotFoundError("ambiguous connection reference endpoint")
                witnesses.extend(references)
                identifier = next(iter(targets))
        return resolved, witnesses

    @staticmethod
    def _typing_is_unresolved(endpoint, resolver, graph, by_id):
        """True when the endpoint's referenced typing evidence cannot decide.

        Every typing/specialization branch must be represented, not merely one
        successful path to a governed root. Missing branches could supply a
        competing meaning. An explicit library URI witnesses an external leaf;
        fully represented unrelated lineage remains supported absence.
        """
        endpoint_id = element_id(endpoint)
        if endpoint_id is None:
            return True
        typed = set(resolver["typed_by"].get(endpoint_id, ()))
        typed |= set(resolver["typed_by_implied"].get(endpoint_id, ()))
        if not typed:
            return True
        pending, seen = [endpoint_id], set()
        while pending:
            identifier = pending.pop()
            if identifier in seen:
                continue
            seen.add(identifier)
            node = by_id[identifier]
            for hop in graph.outgoing(identifier):
                if not (is_typing_hop(hop) or is_subsumption_hop(hop)):
                    continue
                if hop.target in by_id:
                    pending.append(hop.target)
                    continue
                # The frozen graph preserves URI on relationship objects but
                # not inlined properties; recover only the exact target's
                # explicit URI from its containing API object, never a name.
                value = node.get(hop.kind)
                external = hop.target_uri or any(
                    isinstance(ref, dict) and element_id(ref) == hop.target and ref.get("@uri")
                    for ref in (value if isinstance(value, list) else [value]))
                if not external:
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
        by_id = {i: e for e in elements if (i := element_id(e)) is not None}
        graph = build_relationship_graph(elements)
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
                sources, sw = self._endpoints(rel, "source", by_id, graph)
                targets, tw = self._endpoints(rel, "target", by_id, graph)
                if element_id(source) not in (targets if inverse else sources):
                    continue
                if len(sources) != 1 or len(targets) != 1:
                    raise IdentityNotFoundError("native binary connection endpoints are incomplete or ambiguous")
                contexts = reference_ids(rel.get("owningNamespace")) or reference_ids(rel.get("owner")) or reference_ids(rel.get("owningRelatedElement"))
                if len(contexts) != 1 or contexts[0] not in by_id:
                    raise IdentityNotFoundError("native connection context is absent or dangling")
                left, right = by_id[sources[0]], by_id[targets[0]]
                if len(self._governed_meanings(rel, left, right, resolver_for)) > 1:
                    raise IdentityNotFoundError("carrier grounds under overlapping governed endpoint meanings")
                for row in rows:
                    if left.get("@type") != row["sourceUsage"] or right.get("@type") != row["targetUsage"]:
                        continue
                    if row["mechanism"] == "typed-connection":
                        carrier = resolver_for(canonical)
                        if self._typing_is_unresolved(rel, carrier, graph, by_id):
                            raise IdentityNotFoundError("carrier typing evidence is missing or unresolved")
                        if not self._endpoint_grounding(rel, carrier):
                            continue
                    lr = resolver_for(row["sourceClass"])
                    rr = resolver_for(row["targetClass"])
                    for endpoint, resolver in [(left, lr), (right, rr)]:
                        if self._typing_is_unresolved(endpoint, resolver, graph, by_id):
                            raise IdentityNotFoundError("usage endpoint typing evidence is missing or unresolved")
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


def assemble_successor_service(*, base_contract, contract, binding, repository,
                               expected_git_revision, production=False):
    """Assemble from construction-verified records; never read model source."""
    if production:
        raise ValueError("relationship successor is non-production; activation refused")
    binding.require_current(expected_git_revision)
    binding.require_ontology(base_contract.identity)
    index, routes = route_successor_bindings(contract, binding)
    # Profile routing consumes ingestion-validated file/declaration/UUID tuples.
    # An ontology-native Function has no root UUID: the extension's separately
    # mapped AllocatableFunction can supply the exact pin, never a name fallback.
    selected = [b.element_id for b in index.bindings
                if b.ontology_class in {**contract["classes"], **contract["carriers"]}]
    if any(not i or not i.strip() for i in selected) or len(selected) != len(set(selected)):
        raise ValueError("overlapping or blank successor kernel identities")
    authority = SuccessorAuthority(base_contract, contract, binding)
    authority.binding_routes = routes
    binder = OntologyApiBinder(authority, repository, project_id=binding.sysml_project_id,
                              commit_id=binding.sysml_commit_id, kernel_bindings=index)
    traversal = SuccessorTraversal(authority, kernel_bindings=index)
    from .impact import ImpactService
    impact = ImpactService(repository=repository, binding=binding, contract=authority,
                           binder=binder, traversal=traversal)
    return SuccessorQueryService(repository=repository, binding=binding, contract=authority,
        binder=binder, traversal=traversal, impact_service=impact,
        expected_git_revision=expected_git_revision, semantic_authority_id=authority.authority_id)
