"""The increments a model revision declares, found through charters and short names.

An engineering increment is the part usage in the EngineeringIncrement
lineage whose declared short name is its registered identifier
(``INC-<SUBJECT>-<SEQ>``, docs/naming/naming-conventions.md); its charter is
the IncrementTraceObligations-lineage part usage whose ``increment`` value
references it (see :mod:`de4sdv.semantic.increment_scope`). Discovery reads
both directions from validated kernel identity (ADR 0011), never from element
names:

- every charter, through its ``increment`` value, names an increment usage;
  the usage's declared short name is the identifier;
- every increment usage carrying an identifier counts, with or without a
  charter (the evaluation then reports the missing charter).

What cannot be evaluated is reported as a note, never guessed: a charter
whose increment usage carries no identifier, an identifier-shaped short name
on an element outside the increment lineage, and an identifier that several
increment usages carry (listed once; its evaluation reports the ambiguity).
A charter's increment that cannot be identified is also recorded as not
evaluated, with its usage, charters and reason, so reports can list it
beside the evaluated increments (owner decision D14); it is never matched to
an identifier by its name.
A missing kernel binding of either lineage raises
:class:`IdentityNotFoundError`; it is never an empty result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .increment_scope import (
    CHARTER_CLASS,
    INCREMENT_ATTRIBUTE,
    INCREMENT_CLASS,
    IncrementIdentifierError,
    ModelView,
    parse_increment_id,
)


@dataclass(frozen=True)
class DeclaredIncrement:
    """One increment the model declares, with its usage and charters."""

    increment_id: str
    usage: Mapping[str, Any]
    charters: tuple[Mapping[str, Any], ...]


@dataclass(frozen=True)
class UnidentifiedIncrement:
    """A charter's increment usage the method cannot evaluate: it is not identified as an increment."""

    usage: Mapping[str, Any]
    charters: tuple[Mapping[str, Any], ...]
    reason: str
    #: The notes this record stands for (one per charter that references the usage).
    notes: tuple[str, ...]


@dataclass(frozen=True)
class IncrementDiscovery:
    """Every declared increment (identifier order) and what could not be evaluated."""

    increments: tuple[DeclaredIncrement, ...]
    notes: tuple[str, ...]
    #: The charters' increments that are not evaluated (qualified-name order).
    not_evaluated: tuple[UnidentifiedIncrement, ...] = ()

    @property
    def increment_ids(self) -> tuple[str, ...]:
        return tuple(increment.increment_id for increment in self.increments)


def _ordered(view: ModelView, identifiers: Iterable[str]) -> tuple[str, ...]:
    """Distinct identifiers by the ownership path of their named owners, then identifier
    (corpus-order independent); the path is an ordering key only, never a printed name."""
    unique = list(dict.fromkeys(identifiers))
    return tuple(sorted(unique, key=lambda item: (view.index.qualified_name(item), item)))


def _identifier(value: Any) -> str | None:
    try:
        return parse_increment_id(str(value)) if value else None
    except IncrementIdentifierError:
        return None


def declared_increments(view: ModelView) -> IncrementDiscovery:
    """The increments ``view`` declares, through charters and short names."""
    index = view.index
    usages: dict[str, set[str]] = {}
    charters_of: dict[str, set[str]] = {}
    notes: list[str] = []

    def label(identifier: str) -> str:
        return view.label(identifier)

    for usage in index.elements_of_type("PartUsage"):
        identifier = _identifier(index.element(usage).get("declaredShortName"))
        if identifier is not None and view.in_lineage(usage, INCREMENT_CLASS):
            usages.setdefault(identifier, set()).add(usage)

    unidentified: dict[str, dict[str, list[str]]] = {}
    for charter in _ordered(view, [c for c in index.elements_of_type("PartUsage")
                                           if view.in_lineage(c, CHARTER_CLASS)]):
        referenced = [leaf.value for leaf in index.feature_values(charter, INCREMENT_ATTRIBUTE)
                      if leaf.kind == "reference" and leaf.value]
        for usage in referenced:
            identifier = _identifier(index.element(usage).get("declaredShortName"))
            if identifier is None or not view.in_lineage(usage, INCREMENT_CLASS):
                note = (f"charter {label(charter)} references {label(usage)}, which carries no increment "
                        "identifier as the declared short name of an increment usage; it is not evaluated")
                notes.append(note)
                record = unidentified.setdefault(usage, {"charters": [], "notes": []})
                record["charters"].append(charter)
                record["notes"].append(note)
                continue
            usages.setdefault(identifier, set()).add(usage)
            charters_of.setdefault(identifier, set()).add(charter)

    for holder in _ordered(view, [e for e in index.by_id
                                          if _identifier(index.element(e).get("declaredShortName"))]):
        identifier = _identifier(index.element(holder).get("declaredShortName"))
        if holder not in usages.get(identifier, set()):
            notes.append(
                f"{label(holder)} carries the increment identifier {identifier} as its declared short "
                "name but is not a part usage in the EngineeringIncrement lineage; it is not evaluated")

    increments = []
    for identifier in sorted(usages):
        ordered = _ordered(view, sorted(usages[identifier]))
        if len(ordered) > 1:
            notes.append(f"{len(ordered)} increment usages carry the identifier {identifier} "
                         f"({', '.join(label(u) for u in ordered)}); its evaluation reports the ambiguity")
        charters = _ordered(view, sorted(charters_of.get(identifier, ())))
        increments.append(DeclaredIncrement(
            increment_id=identifier,
            usage=view.describe(ordered[0]),
            charters=tuple(view.describe(charter) for charter in charters),
        ))
    not_evaluated = tuple(
        UnidentifiedIncrement(
            usage=view.describe(usage),
            charters=tuple(view.describe(charter) for charter in unidentified[usage]["charters"]),
            reason=_not_evaluated_reason(view, usage),
            notes=tuple(unidentified[usage]["notes"]),
        )
        for usage in _ordered(view, unidentified))
    return IncrementDiscovery(increments=tuple(increments), notes=tuple(notes), not_evaluated=not_evaluated)


def _not_evaluated_reason(view: ModelView, usage: str) -> str:
    """Why a charter's increment usage is not evaluated."""
    if _identifier(view.index.element(usage).get("declaredShortName")) is None:
        return ("its increment usage carries no increment identifier (INC-<SUBJECT>-<SEQ>) as its declared short "
                "name, and the method finds an increment only by that short name")
    return ("its increment usage carries an increment identifier but is not a part usage in the "
            "EngineeringIncrement lineage, so the method cannot evaluate it as an increment")
