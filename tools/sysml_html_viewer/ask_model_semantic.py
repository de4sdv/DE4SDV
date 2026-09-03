"""API-derived method context for the viewer ask-model capability.

Derives requirement-subject (and, where mapped, verification) relations
from the **deployed SysML v2 API** through the repository's semantic
runtime — ontology-declared predicates, revision-binding enforced,
UUID-addressed — instead of re-deriving them from source text.

Grounding contract (unchanged): every relation listed exists in the
bound API revision; answers stay grounded on the deployed baseline, not
the working tree.

Fallback ladder (explicit, never silent about which path produced the
answer's evidence):
  1. "api"      — SemanticQueryService over the deployed API (requires
                  NOUS_ASK_SEMANTIC_RUNTIME=1 and the runtime contract:
                  binding file + expected SHA + matching ontology).
  2. "regex"    — tools.sysml_html_viewer.ask_model.build_method_context
                  (source-text extraction; the pre-B fallback).
The /ask response reports which path served the evidence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_SEMANTIC_RUNTIME = None
_SEMANTIC_ERROR: str | None = None
# short-lived memo: element UUID -> method-context dict
_SEMANTIC_CTX_CACHE: dict[str, dict] = {}


def semantic_enabled() -> bool:
    return os.environ.get("NOUS_ASK_SEMANTIC", "").strip() not in ("", "0", "false")


def _runtime():
    """Build the semantic runtime once per process (fail-closed contract)."""
    global _SEMANTIC_RUNTIME, _SEMANTIC_ERROR
    if _SEMANTIC_RUNTIME is not None:
        return _SEMANTIC_RUNTIME
    if _SEMANTIC_ERROR is not None:
        raise RuntimeError(_SEMANTIC_ERROR)

    repo = Path(__file__).resolve().parents[2]
    api_url = os.environ.get("DE4SDV_SYSML_API_URL",
                             "https://sysml-api.de4sdv.org")
    binding = os.environ.get(
        "DE4SDV_REVISION_BINDING",
        str(Path.home() / ".hermes/de4sdv-semantic/binding.json"),
    )
    expected = os.environ.get("DE4SDV_EXPECTED_GIT_SHA", "")
    ontology = os.environ.get(
        "DE4SDV_ONTOLOGY_PATH",
        str(repo / "approach/framework/ontology/de4sdv-basic-ontology.yaml"),
    )
    missing = [n for n, v in (
        ("DE4SDV_EXPECTED_GIT_SHA", expected),
    ) if not v]
    if missing:
        _SEMANTIC_ERROR = (
            "semantic runtime contract incomplete: missing " + ", ".join(missing)
        )
        raise RuntimeError(_SEMANTIC_ERROR)
    try:
        from de4sdv.semantic.runtime import build_semantic_runtime
        _SEMANTIC_RUNTIME = build_semantic_runtime(
            api_url=api_url,
            binding_path=Path(binding),
            expected_git_revision=expected,
            ontology_path=Path(ontology),
            api_timeout=float(os.environ.get("DE4SDV_API_TIMEOUT", "900")),
        )
    except Exception as exc:  # noqa: BLE001 — fail-closed, error kept
        _SEMANTIC_ERROR = f"semantic runtime unavailable: {exc}"
        raise RuntimeError(_SEMANTIC_ERROR) from exc
    return _SEMANTIC_RUNTIME


def _ref_ids(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [str(value.get("@id") or "")]
    if isinstance(value, list):
        return [str(x.get("@id")) for x in value if isinstance(x, dict)]
    return [str(value)]


def api_method_context(service, targets: list[dict],
                       elements: list[dict]) -> dict:
    """Reverse-traverse the ontology's hasSubject mapping for elements.

    Walks native SubjectMembership objects of the bound API revision whose
    memberElement resolves to any of the targets; each such membership's
    owner is a requirement the element is the declared subject of.

    Same-name union: the subject references inside requirements are
    ReferenceUsage elements, while the browsed element is typically the
    PartUsage in its system context (live-verified: memberProduct in the
    deployed model — PartUsage carries 0 memberships, each same-name
    ReferenceUsage carries 1; union-by-name reproduces the full subject
    set, parity-proven 24/24 against the deployed API). Dedupe by
    requirement element id.
    """
    cache_key = ",".join(sorted(
        str(t.get("@id") or "") for t in targets
    ))
    if cache_key and cache_key in _SEMANTIC_CTX_CACHE:
        return _SEMANTIC_CTX_CACHE[cache_key]

    mapping = service.contract.relationship_mapping("hasSubject")
    membership_types = {
        str(t) for t in
        mapping.configuration.get("membership_types", ["SubjectMembership"])
    }
    member_prop = str(mapping.configuration.get("member_property",
                                                "memberElement"))
    target_ids = {str(t.get("@id") or "") for t in targets}
    target_ids.discard("")

    by_id: dict[str, dict] = {}
    for e in elements:
        eid = e.get("elementId") or e.get("@id")
        if eid:
            by_id[str(eid)] = e

    seen_reqs: set[str] = set()
    requirements: list[dict] = []
    for m in elements:
        if str(m.get("@type")) not in membership_types:
            continue
        if not (target_ids & set(_ref_ids(m.get(member_prop)))):
            continue
        for oid in _ref_ids(m.get("owningRelatedElement")):
            if oid in seen_reqs:
                continue
            owner = by_id.get(oid)
            if owner is None:
                continue
            seen_reqs.add(oid)
            requirements.append({
                "requirement": owner.get("declaredName")
                or owner.get("name") or "",
                "sysml_type": str(owner.get("@type") or ""),
                "element_id": oid,
            })
    requirements.sort(key=lambda r: (r["requirement"], r["element_id"]))

    ctx: dict = {}
    if requirements:
        ctx["requirement_subject_of"] = requirements
        ctx["derivation"] = (
            "API-derived: native SubjectMembership relationships of the "
            "deployed SysML v2 revision (ontology predicate hasSubject), "
            "same-name subject references united"
        )
    if cache_key:
        _SEMANTIC_CTX_CACHE[cache_key] = ctx
    return ctx


def build_method_context_api(ref, files) -> tuple[dict, str]:
    """Method context for an element with an explicit derivation label.

    Returns (context, path) where path is "api", "api:no-match",
    "api:empty", "regex", or "regex:fallback:<Error>". API failures fall
    back to regex and are reported in the returned path marker.
    """
    if semantic_enabled():
        try:
            service = _runtime()
            elements = service._elements()
            matches = [
                e for e in elements
                if (e.get("declaredName") or e.get("name")) == ref.name
            ]
            if not matches:
                return {}, "api:no-match"
            ctx = api_method_context(service, matches, elements)
            if ctx:
                return ctx, "api"
            return {}, "api:empty"
        except Exception as exc:  # noqa: BLE001 — degrade explicitly
            return (
                _regex_fallback(ref, files),
                f"regex:fallback:{type(exc).__name__}",
            )
    return _regex_fallback(ref, files), "regex"


def _regex_fallback(ref, files):
    from tools.sysml_html_viewer.ask_model import build_method_context
    return build_method_context(ref, files)
