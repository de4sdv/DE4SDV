#!/usr/bin/env python3
"""Probe: does include_implied=True materialize library grounding in the closure?

Answers, on a licensed runner, the question that decides the Lane B read-back
design:

1. Synthetic model: ``verification def`` importing ``VerificationCases::*`` —
   with ``SerializationOptions.minimal()`` (current export) vs
   ``minimal().with_options(include_implied=True)``:
   does an implied ``Subclassification``/subsetting to the bundled
   ``Systems Library/VerificationCases.sysml`` elements appear, and does its
   target id equal the id of ``VerificationCases::VerificationCase`` /
   ``VerificationCases::verificationCases`` when the library file is loaded
   directly?

2. Real DE4SDV pilot model (this checkout): same comparison for
   ``VC-AEBS-009D-DE`` and ``VC-AEBS-009D-01``, and whether the implied
   targets resolve to the library ids found in (1).

Prints a structured JSON report; read-only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import syside

ROOT = Path(__file__).resolve().parents[1]


def _library_dir() -> Path:
    import _syside  # type: ignore[import-not-found]

    candidates = [
        Path(str(_syside.__file__)).resolve().parent / "sysml.library",
        Path(str(syside.__file__)).resolve().parent / "sysml.library",
        Path(str(syside.__file__)).resolve().parent.parent / "_syside" / "sysml.library",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise RuntimeError(f"could not locate sysml.library; tried: {candidates}")


LIBRARY_DIR = _library_dir()
VERIFICATION_CASES = LIBRARY_DIR / "Systems Library" / "VerificationCases.sysml"

RELATIONSHIP_TYPES = {
    "Subclassification",
    "Specialization",
    "Subsetting",
    "FeatureTyping",
    "Conjugation",
    "Redefinition",
}


def _serialize(model, options) -> list[dict]:
    elements: list[dict] = []
    for document in model.user_docs:
        with document.lock() as locked:
            serialized = syside.json.dumps(locked.root_node, options)
        loaded = json.loads(serialized)
        if isinstance(loaded, list):
            elements.extend(loaded)
    return elements


def _ids(value: object) -> list[str]:
    if isinstance(value, dict):
        candidate = value.get("@id")
        return [candidate] if candidate else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_ids(item))
        return out
    return []


def _relationship_edges(elements: list[dict]) -> list[dict]:
    edges = []
    for element in elements:
        type_name = str(element.get("@type") or "")
        if type_name not in RELATIONSHIP_TYPES:
            continue
        source_candidates = []
        for key in ("subclassifier", "specific", "subsettingFeature", "owningRelatedElement", "typedFeature"):
            source_candidates.extend(_ids(element.get(key)))
        target_candidates = []
        for key in ("superclassifier", "general", "subsettedFeature", "type", "redefinedFeature"):
            target_candidates.extend(_ids(element.get(key)))
        for source in source_candidates:
            for target in target_candidates:
                if source != target:
                    edges.append(
                        {
                            "kind": type_name,
                            "witness_id": element.get("@id"),
                            "source": source,
                            "target": target,
                        }
                    )
    return edges


def _by_name(elements: list[dict], name: str) -> list[dict]:
    return [e for e in elements if str(e.get("declaredName") or "") == name]


def _library_ids() -> dict[str, str]:
    """Load the bundled VerificationCases.sysml and return anchor ids."""
    model, diagnostics = syside.try_load_model([VERIFICATION_CASES])
    report: dict[str, object] = {
        "path": str(VERIFICATION_CASES),
        "load_errors": diagnostics.contains_errors(warnings_as_errors=False),
    }
    elements = _serialize(model, syside.SerializationOptions.minimal())
    for name in ("VerificationCase", "verificationCases", "subVerificationCases"):
        matches = _by_name(elements, name)
        report[name] = [m.get("@id") for m in matches]
    report["element_count"] = len(elements)
    return report  # type: ignore[return-value]


def _synthetic(check: dict) -> None:
    doc = Path("/tmp/probe_model.sysml")
    doc.write_text(
        "package Probe {\n"
        "  private import VerificationCases::*;\n"
        "  verification def MyCheck {\n"
        "    subject s;\n"
        "  }\n"
        "}\n"
    )
    model, diagnostics = syside.try_load_model([doc])
    check["synthetic_load_errors"] = diagnostics.contains_errors(warnings_as_errors=False)
    minimal_elements = _serialize(model, syside.SerializationOptions.minimal())
    implied_elements = _serialize(
        model,
        syside.SerializationOptions.minimal().with_options(include_implied=True),
    )
    check["synthetic_counts"] = {
        "minimal": len(minimal_elements),
        "include_implied": len(implied_elements),
    }
    for label, elements in (("minimal", minimal_elements), ("include_implied", implied_elements)):
        edges = _relationship_edges(elements)
        check[f"synthetic_edges_{label}"] = edges
    defn = _by_name(implied_elements, "MyCheck")
    check["synthetic_definition_ids"] = [d.get("@id") for d in defn]
    all_ids = {str(e.get("@id")) for e in implied_elements}
    external_targets = sorted(
        {
            edge["target"]
            for edge in _relationship_edges(implied_elements)
            if edge["target"] not in all_ids
        }
    )
    check["synthetic_external_targets"] = external_targets


def _real_model(check: dict) -> None:
    sys.path.insert(0, str(ROOT))
    from de4sdv.sysml_api.baseline import BaselineManifest

    manifest = BaselineManifest.discover(ROOT)
    paths = [ROOT / source.path for source in manifest.sources]
    model, diagnostics = syside.try_load_model(paths)
    check["real_load_errors"] = diagnostics.contains_errors(warnings_as_errors=False)
    implied_elements = _serialize(
        model,
        syside.SerializationOptions.minimal().with_options(include_implied=True),
    )
    check["real_element_count_include_implied"] = len(implied_elements)
    elements_by_id = {str(e.get("@id")): e for e in implied_elements}
    all_ids = set(elements_by_id)
    for short_name in ("VC-AEBS-009D-DE", "VC-AEBS-009D-01"):
        element = next(
            (e for e in implied_elements if e.get("declaredShortName") == short_name), None
        )
        if element is None:
            check[f"real_{short_name}"] = "MISSING"
            continue
        element_id = str(element.get("@id"))
        edges = [
            edge
            for edge in _relationship_edges(implied_elements)
            if edge["source"] == element_id
        ]
        check[f"real_{short_name}"] = {
            "metaclass": element.get("@type"),
            "edges": [
                {
                    **edge,
                    "target_in_revision": edge["target"] in all_ids,
                    "target_name": str(
                        (elements_by_id.get(edge["target"]) or {}).get("declaredName") or ""
                    ),
                }
                for edge in edges
            ],
        }


def main() -> int:
    report: dict[str, object] = {}
    report["library"] = _library_ids()
    _synthetic(report)
    _real_model(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
