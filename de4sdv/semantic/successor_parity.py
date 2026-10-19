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

PARITY_SCHEMA = "de4sdv.successor-parity/v1"
ALLOCATED_TO = "allocatedTo"
#: The relations whose facts the privileged ingestion compares (owner decision 2026-10-18, #4).
PARITY_RELATIONS = (ALLOCATED_TO, "hasValidationScenario")

Fact = tuple[str, str, str, str]


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
    """The facts the method's relation check finds from every connector end, and its problems."""
    found: set[Fact] = set()
    problems: list[str] = []
    for subject in _subjects(view, relation):
        result = check_relation(view, relation, subject)
        if result.problem:
            problems.append(f"{subject}: {result.problem}: {result.detail}")
        for target, witness in result.hops:
            try:
                found.add((subject, target, end_pair(view, relation, subject, target), witness))
            except (IdentityNotFoundError, MethodSideInput) as error:
                problems.append(f"{subject}: {error}")
    return frozenset(found), tuple(problems)


def traversal_facts(traversal: Any, view: ModelView, relation: str, predicate: str | None = None
                    ) -> tuple[frozenset[Fact], tuple[dict[str, Any], ...]]:
    """The facts the successor traversal returns from every connector end, and its incomplete records."""
    traversal.unsupported = []
    found: set[Fact] = set()
    for subject in _subjects(view, relation):
        for hop in traversal.traverse(predicate or relation, view.element(subject), view.elements):
            found.add((str(hop.source["@id"]), str(hop.target["@id"]), str(hop.witness.get("carrier")),
                       str(hop.api_object["@id"])))
    incomplete = tuple(record for record in traversal.unsupported
                       if record.get("predicate") == (predicate or relation))
    traversal.unsupported = []
    return frozenset(found), incomplete


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
    unreadable = sorted(allocation for allocation, (ends, problem) in api_allocations.items()
                        if problem or len(ends) != 2)
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
        "unreadable": unreadable[:10],
        "differing_from_export": differing[:10],
        "checks": checks,
        "passed": all(checks.values()),
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


__all__ = ["ALLOCATED_TO", "Fact", "PARITY_RELATIONS", "PARITY_SCHEMA", "allocation_end_closure",
           "connectors", "end_pair", "method_facts", "parity_report", "relation_parity", "traversal_facts"]
