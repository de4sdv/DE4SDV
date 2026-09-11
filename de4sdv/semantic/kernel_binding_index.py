"""Runtime kernel identity from ingestion-validated binding metadata.

ADR 0011 boundary: DE4SDV introduces no custom textual SysML parser and
infers no runtime semantics from source text. Canonical kernel identity is
established exactly once, at ingestion, by
:func:`de4sdv.semantic.validation.validate_ontology_bindings` combining API
type/name with serializer-recorded source-document provenance, and persisted
in the revision binding's ``kernel_bindings``. Runtime traversal and class
binding consume those validated UUIDs directly against the API graph.

Fail-closed contract:

- a revision binding without a validated binding for a required class is a
  hard error (``IdentityNotFoundError``), never a name-based fallback;
- a validated UUID that does not exist in the bound API revision is a hard
  error (the binding and the revision are inconsistent);
- a validated UUID whose element type contradicts the governed declaration
  is a hard error (binding corruption);
- more than one validated candidate for one class cannot be represented in
  the binding schema, so ambiguity is rejected at ingestion time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from de4sdv.sysml_api.errors import IdentityNotFoundError
from de4sdv.sysml_api.revisions import KernelElementBinding
from de4sdv.sysml_api.repository import element_id

from .kernel_contract import declaration_identity


@dataclass(frozen=True)
class KernelBindingIndex:
    """Validated ontology-class -> API UUID bindings for one revision."""

    bindings: tuple[KernelElementBinding, ...]
    _by_class: dict[str, KernelElementBinding]

    @classmethod
    def from_binding(cls, binding) -> "KernelBindingIndex":  # type: ignore[no-untyped-def]
        """Build the index from a revision binding's kernel_bindings.

        Duplicate ontology-class entries are rejected here even though the
        import path cannot produce them: the runtime must not guess which
        entry wins.
        """
        by_class: dict[str, KernelElementBinding] = {}
        for item in binding.kernel_bindings:
            if item.ontology_class in by_class:
                raise IdentityNotFoundError(
                    f"revision binding carries multiple kernel bindings for "
                    f"ontology class {item.ontology_class!r}"
                )
            by_class[item.ontology_class] = item
        return cls(bindings=binding.kernel_bindings, _by_class=by_class)

    def ontology_class_for(
        self, element_id_value: str, by_id: dict[str, dict[str, Any]]
    ) -> str:
        """Return the ontology class whose validated binding grounds an element.

        This is the model->vocabulary direction of the same ingestion-validated
        contract ``element_id_for`` consumes: the caller has already resolved a
        model element (for example a connection definition's typed end) and
        needs the governed class name for it. Fails closed when no binding
        claims the element or when several do — an ambiguous vocabulary
        identity must not be guessed.
        """
        matches = sorted(
            item.ontology_class
            for item in self.bindings
            if item.element_id == element_id_value
        )
        if not matches:
            raise IdentityNotFoundError(
                f"no validated kernel binding claims element "
                f"{element_id_value!r}; the model does not ground an ontology "
                f"class for it"
            )
        if len(matches) > 1:
            raise IdentityNotFoundError(
                f"element {element_id_value!r} is claimed by multiple kernel "
                f"bindings {matches!r}; vocabulary identity is ambiguous"
            )
        return matches[0]

    def element_id_for(self, ontology_class: str, by_id: dict[str, dict[str, Any]]) -> str:
        """Return the validated API UUID for one file-mapped ontology class.

        The UUID must exist in the bound revision and its element type must
        match the governed declaration's expected API type. Anything else
        fails closed: a missing class means ingestion never validated this
        mapping for this revision, and runtime has no authority to recover
        it from names.
        """
        item = self._by_class.get(ontology_class)
        if item is None:
            raise IdentityNotFoundError(
                f"revision binding carries no validated kernel binding for "
                f"ontology class {ontology_class!r}; runtime cannot resolve "
                f"kernel identity from names (run ingestion to validate and "
                f"persist the binding)"
            )
        element = by_id.get(item.element_id)
        if element is None:
            raise IdentityNotFoundError(
                f"validated kernel binding for {ontology_class!r} points at "
                f"API element {item.element_id!r}, which does not exist in the "
                f"bound revision"
            )
        _, expected_type = declaration_identity(item.declaration)
        if str(element.get("@type")) != expected_type:
            raise IdentityNotFoundError(
                f"validated kernel binding for {ontology_class!r} points at "
                f"element {item.element_id!r} of type "
                f"{element.get('@type')!r}, contradicting governed declaration "
                f"{item.declaration!r} (expected {expected_type})"
            )
        return item.element_id


def require_validated_binding_id(
    index: KernelBindingIndex | None,
    ontology_class: str,
    by_id: dict[str, dict[str, Any]],
) -> str:
    """Module-level helper for consumers holding an optional index."""
    if index is None:
        raise IdentityNotFoundError(
            f"no validated kernel binding index is available; ontology class "
            f"{ontology_class!r} cannot be resolved without ingestion-validated "
            f"binding metadata"
        )
    return index.element_id_for(ontology_class, by_id)


def validated_bindings_report(index: KernelBindingIndex) -> list[dict[str, str]]:
    """Serialize the index for provenance echo in query results."""
    return [
        {
            "ontology_class": item.ontology_class,
            "element_id": item.element_id,
            "source_file": item.source_file,
            "declaration": item.declaration,
        }
        for item in index.bindings
    ]
