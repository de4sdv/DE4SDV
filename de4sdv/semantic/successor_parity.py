"""The successor relations as each consumer reads them, and their parity across consumers.

A fact is ``(source, target, end pair, witness)``: one connector that
witnesses a successor relation between two model elements, and the end pair
(profile carrier) it grounds in. The method checks read native connectors
through :mod:`de4sdv.semantic.relation_checks`; the successor traversal
(``semantic_neighbors``, ``trace``, ``impact`` and the MCP tools over them)
reads them with the same reader. :func:`parity_report` collects the facts
each side finds over two corpora of one revision, the export snapshot and an
API revision, so the privileged ingestion can show that the imported API
revision serves exactly the facts the export holds. That is the evidence the
``allocatedTo`` forward obligations of
``de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml`` ask of an
exact-SHA privileged run: the traversal evidence, and the API closure of the
typed allocation ends (:func:`allocation_end_closure`).

Every check compares facts or identities, never a reviewed count, and fails
closed: an empty relation, a reader problem or an incomplete answer fails it.
Model content only: an allocation records a responsibility assignment, and
nothing here claims satisfaction, realization, deployment or compliance.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from de4sdv.sysml_api.errors import IdentityNotFoundError

from .increment_scope import ModelView
from .relation_checks import (
    MethodSideInput,
    allocation_ends,
    allocation_pairs,
    check_relation,
    connection_ends,
    native_allocation_rows,
)
from .trace_vocabulary_traversal import unreadable_ends

PARITY_SCHEMA = "de4sdv.successor-parity/v1"
EXPORT_PARITY_SCHEMA = "de4sdv.successor-parity-export/v1"
ALLOCATED_TO = "allocatedTo"
#: The relations whose facts the privileged ingestion compares (owner decision 2026-10-18, #4).
PARITY_RELATIONS = (ALLOCATED_TO, "hasValidationScenario")

Fact = tuple[str, str, str, str]

#: DE4SDV's accepted form of a native allocation, which every governed allocation uses: its own two
#: ends. An allocation usage without its own ends (an allocation slot that would inherit its
#: definition's) is no fact for the traversal and is refused by the allocation-end closure.
ACCEPTED_ALLOCATION_FORM = ("author the allocation as `allocate <source> to <target>`; "
                            "allocations without their own ends are not an accepted form")


def connectors(view: ModelView, relation: str) -> dict[str, tuple[tuple[str, ...], str]]:
    """The connectors the method reads for ``relation``: every native allocation for
    ``allocatedTo``; else the connections typed by the relation's pinned carrier."""
    if relation == ALLOCATED_TO:
        return dict(allocation_ends(view))
    carriers = view.traversal.class_lineage(relation, view.elements)["explicit_lineage_ids"]
    return {connection: ends for connection, ends in connection_ends(view).items()
            if view.index.typed_by(connection) & carriers}


def end_pair(view: ModelView, relation: str, source: str, target: str) -> str:
    """The end pair (profile carrier) a fact grounds in; refuses anything but exactly one."""
    if relation == ALLOCATED_TO:
        rows = allocation_pairs(view, relation, source, target)
    else:
        rows = list((view.contract.profile.get("relations") or {}).get(relation) or ())
    if len(rows) != 1:
        raise IdentityNotFoundError(f"{relation} {source} -> {target} grounds in {len(rows)} end pairs")
    return str(rows[0]["carrier"])


def _subjects(view: ModelView, relation: str) -> list[str]:
    """Every end of every connector the method reads for ``relation`` (sorted)."""
    return sorted({end for ends, _problem in connectors(view, relation).values() for end in ends})


def method_facts(view: ModelView, relation: str) -> tuple[frozenset[Fact], tuple[str, ...]]:
    """The method's facts, one per witness, and its problems.

    For every connector the method reads, a fact for each direction in which the method's relation
    check from one end reaches the other: source to target for an allocation; either way for a typed
    connection, which the check reads from either end. The check keeps one witness per target, so the
    facts count every connector between a pair (two allocations of one pair are two facts). The problems
    are the check's own and every connector whose ends cannot be read, by the traversal's rule
    (:func:`~de4sdv.semantic.trace_vocabulary_traversal.unreadable_ends`).
    """
    found: set[Fact] = set()
    problems: list[str] = []
    reached: dict[str, frozenset[str]] = {}

    def targets_of(subject: str) -> frozenset[str]:
        if subject not in reached:
            result = check_relation(view, relation, subject)
            if result.problem:
                problems.append(f"{view.label(subject)}: {result.problem}: {result.detail}")
            reached[subject] = frozenset(target for target, _witness in result.hops)
        return reached[subject]

    kind = "allocation" if relation == ALLOCATED_TO else "connection"
    for connector, (ends, problem) in sorted(connectors(view, relation).items()):
        problem = unreadable_ends(view, connector, ends, problem, kind=kind)
        if problem:
            problems.append(problem)
            continue
        if not ends:
            continue  # a connector that owns no end is no fact
        directions = [(ends[0], ends[1])] if relation == ALLOCATED_TO else [(ends[0], ends[1]), (ends[1], ends[0])]
        for subject, other in directions:
            if other not in targets_of(subject):
                continue
            try:
                found.add((subject, other, end_pair(view, relation, subject, other), connector))
            except (IdentityNotFoundError, MethodSideInput) as error:
                problems.append(f"{view.label(connector)}: {error}")
    return frozenset(found), tuple(problems)


def traversal_facts(traversal: Any, view: ModelView, relation: str, predicate: str | None = None
                    ) -> tuple[frozenset[Fact], tuple[dict[str, Any], ...]]:
    """The facts the successor traversal returns from every connector end, and its incomplete records,
    each with the ``subject`` it was answered from."""
    name = predicate or relation
    found: set[Fact] = set()
    incomplete: list[dict[str, Any]] = []
    for subject in _subjects(view, relation):
        traversal.unsupported = []
        for hop in traversal.traverse(name, view.element(subject), view.elements):
            found.add((str(hop.source["@id"]), str(hop.target["@id"]), str(hop.witness.get("carrier")),
                       str(hop.api_object["@id"])))
        incomplete.extend(dict(record, subject=subject) for record in traversal.unsupported
                          if record.get("predicate") == name)
    traversal.unsupported = []
    return frozenset(found), tuple(incomplete)


def _details(view: ModelView, method: frozenset[Fact], traversal: frozenset[Fact], problems: tuple[str, ...],
             incomplete: tuple[Mapping[str, Any], ...]) -> list[str]:
    """What a modeller needs to find each failure, by qualified name."""
    def fact(item: Fact) -> str:
        source, target, pair, witness = item
        return f"{view.label(source)} -> {view.label(target)} ({pair}, witness {view.label(witness)})"

    return ([f"the method reads {fact(item)}; the traversal does not" for item in sorted(method - traversal)]
            + [f"the traversal returns {fact(item)}; the method does not" for item in sorted(traversal - method)]
            + list(problems)
            + [f"from {view.label(record.get('subject'))}: {record.get('reason')}" for record in incomplete])


def _facts_record(facts: frozenset[Fact]) -> list[list[str]]:
    return [list(fact) for fact in sorted(facts)]


def relation_parity(export_view: ModelView, api_view: ModelView, relation: str) -> dict[str, Any]:
    """One relation's facts on both corpora: the method's reading of the export is the reference."""
    method, method_problems = method_facts(export_view, relation)
    api_method, api_method_problems = method_facts(api_view, relation)
    export_traversal, export_incomplete = traversal_facts(export_view.traversal, export_view, relation)
    api_traversal, api_incomplete = traversal_facts(api_view.traversal, api_view, relation)
    checks = {
        "the method finds at least one fact on the export": bool(method),
        "the export-snapshot traversal returns the method's facts": export_traversal == method,
        "the API-served traversal returns the method's facts": api_traversal == method,
        "the method reads the same facts on the API revision": api_method == method,
        "no reader problem on either corpus": not method_problems and not api_method_problems,
        "no incomplete traversal answer on either corpus": not export_incomplete and not api_incomplete,
    }
    return {
        "facts": _facts_record(method),
        "by_end_pair": dict(sorted(Counter(pair for _s, _t, pair, _w in method).items())),
        "only_method": _facts_record(method - api_traversal)[:10],
        "only_api": _facts_record(api_traversal - method)[:10],
        "problems": list(method_problems + api_method_problems)[:10],
        "incomplete": [dict(record) for record in export_incomplete + api_incomplete][:10],
        "checks": checks,
        "passed": all(checks.values()),
    }


def allocation_end_closure(export_view: ModelView, api_view: ModelView, *,
                           incomplete: tuple[Mapping[str, Any], ...] = ()) -> dict[str, Any]:
    """The exact-revision API closure of the typed allocation ends (the second forward obligation of
    ``allocatedTo``): every class that types an end of an ``allocatedTo`` end pair has exactly one
    ingestion-validated kernel binding, equal to the profile pin (file and declaration), whose element the
    API revision serves with the declared metaclass and which names the element the export's own validated
    bindings name; and every native allocation the API revision serves is readable and binary, with the
    ends the export gives it, and the typing evidence of its ends decides (``incomplete`` is empty)."""
    pins = (api_view.contract.profile.get("classes") or {})
    classes = sorted({str(row[key]) for _name, row in native_allocation_rows(api_view, ALLOCATED_TO)
                      for key in ("sourceClass", "targetClass")})
    bindings = {b.ontology_class: b for b in getattr(api_view.traversal.kernel_bindings, "bindings", ())}
    end_classes: dict[str, dict[str, Any]] = {}
    for name in classes:
        record: dict[str, Any] = {"pin": dict(pins.get(name) or {})}
        bound = bindings.get(name)
        if bound is not None:
            record.update(element_id=bound.element_id, source_file=bound.source_file,
                          declaration=bound.declaration)
        try:
            record["served"] = api_view.kernel_element(name)
        except IdentityNotFoundError as error:
            record["served_error"] = str(error)
        try:
            record["export_element_id"] = export_view.kernel_element(name)
        except IdentityNotFoundError as error:
            record["export_error"] = str(error)
        record["closed"] = (bound is not None and record.get("served") == bound.element_id
                            == record.get("export_element_id")
                            and (bound.source_file, bound.declaration)
                            == (record["pin"].get("file"), record["pin"].get("declaration")))
        end_classes[name] = record
    api_allocations = allocation_ends(api_view)
    export_allocations = allocation_ends(export_view)
    unreadable = _unreadable_allocations(api_view, api_allocations)
    differing = sorted(allocation for allocation in set(api_allocations) | set(export_allocations)
                       if api_allocations.get(allocation) != export_allocations.get(allocation))
    checks = {
        "every end-pair class is bound, served and equal to the export's": bool(end_classes) and all(
            record["closed"] for record in end_classes.values()),
        "every served allocation is readable and binary": not unreadable,
        "the API serves the export's allocations with the same ends": bool(api_allocations) and not differing,
        "the typing evidence of every allocation end decides": not incomplete,
    }
    return {
        "end_pair_classes": end_classes,
        "allocations": len(api_allocations),
        "unreadable": sorted(unreadable)[:10],
        "unreadable_reasons": [unreadable[key] for key in sorted(unreadable)][:10],
        "differing_from_export": differing[:10],
        "checks": checks,
        "passed": all(checks.values()),
    }


def _unreadable_allocations(view: ModelView, allocations: Mapping[str, tuple[tuple[str, ...], str]]
                            ) -> dict[str, str]:
    """The closure's rule, allocation -> reason: an allocation is readable and binary when the traversal
    can read its ends (:func:`~de4sdv.semantic.trace_vocabulary_traversal.unreadable_ends`), which
    refuses any count but two once an allocation owns an end. An allocation without its own ends is no
    fact for the traversal, and not an accepted form here (:data:`ACCEPTED_ALLOCATION_FORM`)."""
    found = {}
    for allocation, (ends, problem) in sorted(allocations.items()):
        reason = unreadable_ends(view, allocation, ends, problem, kind="allocation")
        if not reason and not ends:
            reason = f"{view.label(allocation)}: it has no ends of its own; {ACCEPTED_ALLOCATION_FORM}"
        if reason:
            found[allocation] = reason
    return found


def export_allocation_closure(view: ModelView) -> dict[str, Any]:
    """The export half of :func:`allocation_end_closure`: every class that types an end of an
    ``allocatedTo`` end pair resolves to one validated kernel element of the export, and every native
    allocation is readable and binary. The API half (the binding equals the pin and the API serves the
    export's allocations with the same ends) needs the imported revision."""
    classes = sorted({str(row[key]) for _name, row in native_allocation_rows(view, ALLOCATED_TO)
                      for key in ("sourceClass", "targetClass")})
    end_classes: dict[str, dict[str, Any]] = {}
    for name in classes:
        try:
            end_classes[name] = {"element_id": view.kernel_element(name), "resolved": True}
        except IdentityNotFoundError as error:
            end_classes[name] = {"error": str(error), "resolved": False}
    allocations = allocation_ends(view)
    unreadable = _unreadable_allocations(view, allocations)
    checks = {
        "every end-pair class resolves to a validated kernel element of the export": bool(end_classes) and all(
            record["resolved"] for record in end_classes.values()),
        "every allocation is readable and binary": not unreadable,
    }
    return {"end_pair_classes": end_classes, "allocations": len(allocations), "unreadable": sorted(unreadable)[:10],
            "unreadable_reasons": [unreadable[key] for key in sorted(unreadable)][:10],
            "checks": checks, "passed": all(checks.values())}


def export_parity(view: ModelView) -> dict[str, Any]:
    """The export half of :func:`parity_report`, over one export.

    Per relation: the export-snapshot traversal returns the method's facts, one per witness, with no
    reader problem and no incomplete answer; and the export half of the allocation-end closure
    (:func:`export_allocation_closure`). These are the checks of the privileged parity that need no
    imported API revision, run with the same functions, so a model the privileged parity would refuse
    for its content fails here, on the pull request, first. A relation without facts passes here with a
    note (a model under construction may declare none); the privileged parity, over the full model,
    requires at least one. ``details`` name each failure by qualified name.
    """
    relations: dict[str, Any] = {}
    for relation in PARITY_RELATIONS:
        method, problems = method_facts(view, relation)
        traversal, incomplete = traversal_facts(view.traversal, view, relation)
        checks = {
            "the export-snapshot traversal returns the method's facts": traversal == method,
            "no reader problem": not problems,
            "the export-snapshot traversal answers completely": not incomplete,
        }
        relations[relation] = {
            "facts": len(method),
            "by_end_pair": dict(sorted(Counter(pair for _s, _t, pair, _w in method).items())),
            "only_method": _facts_record(method - traversal)[:10],
            "only_traversal": _facts_record(traversal - method)[:10],
            "problems": list(problems)[:10],
            "incomplete": [dict(record) for record in incomplete][:10],
            "details": _details(view, method, traversal, problems, incomplete)[:10],
            "checks": checks,
            "passed": all(checks.values()),
        }
    closure = export_allocation_closure(view)
    return {
        "schema": EXPORT_PARITY_SCHEMA,
        "relations": relations,
        "allocation_end_closure": closure,
        "notes": [f"{relation} has no fact on this export; the privileged parity requires at least one"
                  for relation, record in relations.items() if not record["facts"]],
        "passed": all(record["passed"] for record in relations.values()) and closure["passed"],
        "claim_boundary": ("consistency of the method's reading and the export-snapshot traversal on one "
                           "export; no satisfaction, realization, deployment or compliance claim"),
    }


def parity_report(export_view: ModelView, api_view: ModelView) -> dict[str, Any]:
    """Parity of :data:`PARITY_RELATIONS` between the export snapshot and an API revision of one
    revision, and the API closure of the typed allocation ends. ``passed`` only when every check holds."""
    relations = {relation: relation_parity(export_view, api_view, relation) for relation in PARITY_RELATIONS}
    closure = allocation_end_closure(
        export_view, api_view,
        incomplete=tuple(relations[ALLOCATED_TO]["incomplete"]))
    return {
        "schema": PARITY_SCHEMA,
        "relations": relations,
        "allocation_end_closure": closure,
        "passed": all(record["passed"] for record in relations.values()) and closure["passed"],
        "claim_boundary": ("model content of one revision: the facts are responsibility assignments and "
                           "planning associations; no satisfaction, realization, deployment, validation "
                           "result or compliance claim"),
    }


__all__ = ["ACCEPTED_ALLOCATION_FORM", "ALLOCATED_TO", "EXPORT_PARITY_SCHEMA", "Fact", "PARITY_RELATIONS",
           "PARITY_SCHEMA", "allocation_end_closure", "connectors", "end_pair", "export_allocation_closure",
           "export_parity", "method_facts", "parity_report", "relation_parity", "traversal_facts"]
