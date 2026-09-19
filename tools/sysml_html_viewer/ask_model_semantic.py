"""API-derived method context for the viewer ask-model capability.

Derives requirement-subject (and, where mapped, verification) relations
from the **deployed SysML v2 API** through the repository's semantic
runtime — ontology-declared predicates, revision-binding enforced,
UUID-addressed — instead of re-deriving them from source text.

Grounding contract (unchanged): every relation listed exists in the
bound API revision; answers stay grounded on the deployed baseline, not
the working tree.

Cold-load policy (visitors never wait):
  The full-model retrieval over the public API costs minutes per fresh
  process. A persistent per-revision disk snapshot (checksum-verified,
  identity-bound to the runtime contract) plus a background warmup at
  boot remove that wait from the request path:

  - server boot: start_warmup() loads the corpus from the snapshot when
    present (seconds) or starts the network load in a background thread;
  - while warming, /ask serves the regex path immediately, labeled
    "regex:warming" — it never blocks on the cold load;
  - the snapshot is only trusted AFTER the runtime's binding checks pass
    (expected Git SHA, ontology identity) and only when its recorded
    project/commit identity matches the binding exactly.

Fallback ladder (explicit, never silent about which path produced the
answer's evidence):
  "api" | "api:no-match" | "api:empty" | "regex" | "regex:warming" |
  "regex:warmup-failed" | "regex:fallback:<Error>"
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from de4sdv.semantic import corpus_cache

_SEMANTIC_RUNTIME = None
_SEMANTIC_ERROR: str | None = None
#: Provenance of the authority selection the running service was built
#: under (captured at build time; exposed through /ask-status.json).
_AUTHORITY_SELECTION: dict | None = None
# short-lived memo: element UUID -> method-context dict
_SEMANTIC_CTX_CACHE: dict[str, dict] = {}

# cold-load coordination + warmup state (one cold load per process, ever;
# /ask never blocks on it — see build_method_context_api)
_COLD_LOCK = threading.Lock()
_WARM_STATE: dict = {"status": "idle", "error": None}
# Snapshot format identity now lives in the shared corpus cache
# (de4sdv.semantic.corpus_cache): a snapshot produced under one authority,
# endpoint, binding or ontology must never load under another (identity
# mismatch is a cache miss, never reinterpretation).
_SNAPSHOT_FORMAT = corpus_cache.CORPUS_SNAPSHOT_FORMAT


def warm_status() -> dict:
    status = dict(_WARM_STATE)
    service = _SEMANTIC_RUNTIME
    if service is not None:
        status["semantic_authority_id"] = str(
            getattr(service, "semantic_authority_id", "") or ""
        )
    return status


def semantic_authority_status() -> dict:
    """Deployment provenance: which semantic authority is requested/served.

    Always available (even before warmup or after a fail-closed startup):
    reports the explicit selector, the exact bundle id for an O3 selection,
    and — once the runtime is built — the served authority id. An invalid
    selector surfaces its error here; semantic answers are refused in that
    state (the explicitly labeled regex path never consults semantic
    authority).
    """
    if _AUTHORITY_SELECTION is not None:
        block = dict(_AUTHORITY_SELECTION)
    else:
        try:
            from de4sdv.semantic.authority_selection import (
                resolve_authority_selection,
            )

            block = resolve_authority_selection(environ=os.environ).provenance()
        except Exception as exc:  # noqa: BLE001 — status must survive
            block = {
                "kind": "invalid",
                "error": str(exc),
                "note": (
                    "semantic authority selector is invalid; semantic "
                    "answers are refused (no fallback to legacy authority)"
                ),
            }
    service = _SEMANTIC_RUNTIME
    if service is not None:
        block["semantic_authority_id"] = str(
            getattr(service, "semantic_authority_id", "") or ""
        )
    return block


def semantic_enabled() -> bool:
    return os.environ.get("NOUS_ASK_SEMANTIC", "").strip() not in ("", "0", "false")


def _runtime():
    """Build the semantic runtime once per process (fail-closed contract).

    Authority is selected explicitly through the deployment environment
    (``DE4SDV_SEMANTIC_AUTHORITY``; default legacy). A requested O3 bundle
    that fails selection or startup verification raises here — the viewer
    serves NO semantic answers in that state and never degrades to legacy
    answers; the failure is surfaced through ``semantic_authority_status()``
    and ``warm_status()``.
    """
    global _SEMANTIC_RUNTIME, _SEMANTIC_ERROR, _AUTHORITY_SELECTION
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
        from de4sdv.semantic.authority_selection import (
            build_selected_semantic_runtime,
        )
        _SEMANTIC_RUNTIME, selection = build_selected_semantic_runtime(
            api_url=api_url,
            binding_path=Path(binding),
            expected_git_revision=expected,
            ontology_path=Path(ontology),
            api_timeout=float(os.environ.get("DE4SDV_API_TIMEOUT", "900")),
        )
        _AUTHORITY_SELECTION = selection.provenance()
    except Exception as exc:  # noqa: BLE001 — fail-closed, error kept
        _SEMANTIC_ERROR = f"semantic runtime unavailable: {exc}"
        raise RuntimeError(_SEMANTIC_ERROR) from exc
    return _SEMANTIC_RUNTIME


# ---- per-revision disk snapshot of the API element corpus -----------------
# The mechanism is shared with the MCP server (de4sdv.semantic.corpus_cache):
# one identity-bound, checksum-verified snapshot per exact revision. Only the
# network retrieval is replaced; binding/ontology enforcement still runs on
# every call and the snapshot identity must match the binding exactly.
# Snapshots live outside the repo (default ~/.cache). The helpers below are
# thin compatibility delegates to the shared module.

def _snapshot_dir() -> Path:
    return corpus_cache.snapshot_directory()


def _authority_component(service) -> str:
    return corpus_cache.authority_component(service)


def _snapshot_identity(service) -> dict:
    return corpus_cache.corpus_identity(service)


def _snapshot_path(service) -> Path:
    return corpus_cache.corpus_snapshot_path(service, directory=_snapshot_dir())


def _snapshot_write(service, elements: list[dict]) -> None:
    """Atomic snapshot write + sidecar sha256 of the main file."""
    corpus_cache.write_corpus_snapshot(
        service, elements, directory=_snapshot_dir()
    )


def _snapshot_load(service) -> list[dict] | None:
    """Checksum + identity verified snapshot, or None (any doubt = miss)."""
    return corpus_cache.load_corpus_snapshot(service, directory=_snapshot_dir())


def _load_elements_with_snapshot(service) -> list[dict]:
    """Binding checks FIRST, then snapshot, then network.

    A snapshot is never trusted without the runtime contract passing; a
    corrupted or stale snapshot is ignored (network load overwrites it).
    On a snapshot hit the shared repository is hydrated through the explicit
    validated adoption method (plus the service cache), so impact and the
    ontology binder are served without refetching the full model.
    """
    return corpus_cache.load_elements_with_snapshot(
        service, directory=_snapshot_dir()
    )


def start_warmup() -> None:
    """Begin semantic warmup in a background thread (idempotent).

    Sets the status synchronously so callers can label the ask path
    deterministically right after calling this. A failed warmup is NOT
    auto-retried: a retry per ask would hammer the public API with
    concurrent cold loads (each potentially 10-30+ min under
    contention). Recovery from "error" is a process restart; the error
    stays visible via warm_status().
    """
    if not semantic_enabled():
        return
    if _WARM_STATE["status"] in ("warming", "ready", "error"):
        return
    _WARM_STATE.update(status="warming", error=None)

    def _run():
        if not _COLD_LOCK.acquire(blocking=False):
            return  # another warmup owns the cold load
        try:
            service = _runtime()
            _load_elements_with_snapshot(service)
            _WARM_STATE["status"] = "ready"
        except Exception as exc:  # noqa: BLE001 — surfaced via warm_status
            _WARM_STATE.update(status="error", error=str(exc))
        finally:
            _COLD_LOCK.release()

    threading.Thread(target=_run, daemon=True,
                     name="ask-semantic-warmup").start()


def _ref_ids(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [str(value.get("@id") or "")]
    if isinstance(value, list):
        return [str(x.get("@id")) for x in value if isinstance(x, dict)]
    return [str(value)]


def api_method_context(service, targets: list[dict],
                       elements: list[dict],
                       *, max_hops: int = 2) -> dict:
    """Derive the ontology-mapped method context for elements.

    Collects every ontology-declared relation family that touches any
    target, then CHAINS: reached elements become pass-2 targets so a
    multi-hop trace (requirement -> evidence contract -> verification
    case) reaches its leaf. Each pass is the same single sweep:

    - requirement_subject_of  (hasSubject: SubjectMembership whose
      memberElement resolves to the element; the owner is the
      requirement declaring the element as subject)
    - verified_by             (verifiedBy, reversed: the element is the
      memberElement of a RequirementVerificationMembership; the owner
      is the verification case — live-proven owner=case,
      member=verified requirement, 50/50 resolvable on the deployed
      API)
    - verifies                (verifiedBy forward: the element IS the
      verification case; each memberElement is a verified requirement)
    - incoming_dependencies   (hasRelevantEvidenceContract as mapped:
      Dependency edges targeting the element; covers evidence-contract
      and derivation dependencies, semantic_strength: relevance)
    - realized_by             (realizedBy: AllocationUsage edges from
      the element, direction outgoing)

    Every entry records ``hops`` (1 = direct neighbor of the asked
    element, 2 = reached through one chained element), so a consumer can
    show direct traces only by filtering on hops == 1. Chaining is
    bounded by ``max_hops`` and dedupes by element id, so the sweep is
    finite; entries merge across passes and a family is listed only when
    the model declares it.

    Same-name union applies to every family (subject references inside
    requirements are ReferenceUsage elements while the browsed element
    is typically the PartUsage in its system context; parity-proven
    24/24 for hasSubject against the deployed API). Entries dedupe by
    element id; a family is listed only when the model declares it.
    """
    authority_key = str(getattr(service, "semantic_authority_id", "") or "")
    cache_key = f"{authority_key}|" + ", ".join(sorted(
        str(t.get("@id") or "") for t in targets
    ))
    if cache_key and cache_key in _SEMANTIC_CTX_CACHE:
        return _SEMANTIC_CTX_CACHE[cache_key]

    by_id: dict[str, dict] = {}
    for e in elements:
        eid = e.get("elementId") or e.get("@id")
        if eid:
            by_id[str(eid)] = e

    def element_ref(e: dict, role: str) -> dict:
        return {
            role: e.get("declaredName") or e.get("name") or "",
            "sysml_type": str(e.get("@type") or ""),
            "element_id": str(e.get("elementId") or e.get("@id") or ""),
        }

    def collect(target_ids: set[str]) -> tuple[dict, set[str]]:
        """One sweep: families touching target_ids; returns ctx + reached ids."""
        subject_reqs: dict[str, dict] = {}
        verifying_cases: dict[str, dict] = {}
        verified_reqs: dict[str, dict] = {}
        incoming_deps: dict[tuple[str, str], dict] = {}
        allocations: dict[str, dict] = {}
        reached: set[str] = set()
        subject_mapping = service.contract.relationship_mapping("hasSubject")
        subject_types = {
            str(t) for t in subject_mapping.configuration.get(
                "membership_types", ["SubjectMembership"])
        }
        member_prop = str(subject_mapping.configuration.get(
            "member_property", "memberElement"))
        ver_mapping = service.contract.relationship_mapping("verifiedBy")
        rvm_types = {
            str(t) for t in ver_mapping.configuration.get(
                "membership_types", ["RequirementVerificationMembership"])
        }
        dep_mapping = service.contract.relationship_mapping(
            "hasRelevantEvidenceContract")
        dep_types = {
            str(t) for t in dep_mapping.configuration.get(
                "relationship_types", ["Dependency"])
        }
        dep_source_prop = str(dep_mapping.configuration.get(
            "source_property", "source"))
        dep_target_prop = str(dep_mapping.configuration.get(
            "target_property", "target"))
        alloc_mapping = service.contract.relationship_mapping("realizedBy")
        alloc_types = {
            str(t) for t in alloc_mapping.configuration.get(
                "relationship_types", ["AllocationUsage"])
        }

        for m in elements:
            mtype = str(m.get("@type") or "")
            if mtype in subject_types:
                if not (target_ids & set(_ref_ids(m.get(member_prop)))):
                    continue
                for oid in _ref_ids(m.get("owningRelatedElement")):
                    owner = by_id.get(oid)
                    if owner is not None:
                        subject_reqs[oid] = element_ref(owner, "requirement")
                        reached.add(oid)
            elif mtype in rvm_types:
                # Deployed payload shape: the member is the verified
                # requirement, the owner is the verification case.
                if target_ids & set(_ref_ids(m.get("memberElement"))):
                    for oid in _ref_ids(m.get("owningRelatedElement")):
                        owner = by_id.get(oid)
                        if owner is not None:
                            verifying_cases[oid] = element_ref(
                                owner, "verification_case")
                            reached.add(oid)
                if target_ids & set(_ref_ids(m.get("owningRelatedElement"))):
                    for mid in _ref_ids(m.get("memberElement")):
                        req = by_id.get(mid)
                        if req is not None:
                            verified_reqs[mid] = element_ref(
                                req, "verified_requirement")
                            reached.add(mid)
            elif mtype in dep_types:
                if target_ids & set(_ref_ids(m.get(dep_target_prop))):
                    for sid in _ref_ids(m.get(dep_source_prop)):
                        src = by_id.get(sid)
                        if src is not None:
                            incoming_deps[
                                (sid, str(m.get("@id") or ""))
                            ] = {
                                **element_ref(src, "source_element"),
                                "dependency": (
                                    m.get("declaredName") or m.get("name") or ""
                                ),
                            }
                            reached.add(sid)
            elif mtype in alloc_types:
                if target_ids & set(_ref_ids(m.get("source"))):
                    for tid in _ref_ids(m.get("target")):
                        tgt = by_id.get(tid)
                        if tgt is not None:
                            allocations[tid] = element_ref(
                                tgt, "realized_target")
                            reached.add(tid)
        families: dict[str, list] = {}
        if subject_reqs:
            families["requirement_subject_of"] = sorted(
                subject_reqs.values(),
                key=lambda r: (r["requirement"], r["element_id"]))
        if verifying_cases:
            families["verified_by"] = sorted(
                verifying_cases.values(),
                key=lambda r: (r["verification_case"], r["element_id"]))
        if verified_reqs:
            families["verifies"] = sorted(
                verified_reqs.values(),
                key=lambda r: (r["verified_requirement"], r["element_id"]))
        if incoming_deps:
            families["incoming_dependencies"] = sorted(
                incoming_deps.values(),
                key=lambda r: (r["source_element"], r["element_id"]))
        if allocations:
            families["realized_by"] = sorted(
                allocations.values(),
                key=lambda r: (r["realized_target"], r["element_id"]))
        return families, reached

    merged: dict[str, dict[str, dict]] = {}
    target_ids = {str(t.get("@id") or "") for t in targets}
    target_ids.discard("")
    frontier: set[str] = set(target_ids)
    seen_ids: set[str] = set(target_ids)
    for hop in range(1, max(1, max_hops) + 1):
        if not frontier:
            break
        families, reached = collect(frontier)
        for family, entries in families.items():
            bucket = merged.setdefault(family, {})
            for entry in entries:
                key = entry.get("element_id") or ""
                if not key:
                    continue
                existing = bucket.get(key)
                if existing is None:
                    entry["hops"] = hop
                    bucket[key] = entry
        frontier = {
            rid for rid in reached
            if rid not in seen_ids
        }
        seen_ids |= frontier

    ctx: dict = {}
    for family, bucket in merged.items():
        ctx[family] = sorted(
            bucket.values(),
            key=lambda r: (
                next(iter(v for k, v in r.items()
                          if k not in ("sysml_type", "element_id", "hops")),
                     ""),
                r["element_id"],
            ))
    if ctx:
        ctx["derivation"] = (
            "API-derived: ontology-declared predicates over the deployed "
            "SysML v2 revision (hasSubject, verifiedBy both directions, "
            "hasRelevantEvidenceContract incoming, realizedBy outgoing), "
            "chained to "
            f"{max(1, max_hops)} hop(s) so multi-hop traces reach their "
            "leaf; entries carry hops (1 = direct neighbor of the asked "
            "element), same-name elements united"
        )
    if cache_key:
        _SEMANTIC_CTX_CACHE[cache_key] = ctx
    return ctx


def build_method_context_api(ref, files) -> tuple[dict, str]:
    """Method context for an element with an explicit derivation label.

    Returns (context, path). API failures fall back to regex and the
    returned path marker says exactly what served the evidence. The ask
    path NEVER blocks on the cold load: while the corpus is loading the
    regex result is served with the "regex:warming" label.
    """
    if semantic_enabled():
        if _WARM_STATE["status"] == "error":
            return (
                _regex_fallback(ref, files),
                "regex:warmup-failed",
            )
        try:
            service = _runtime()
        except Exception as exc:  # noqa: BLE001 — degrade explicitly
            return (
                _regex_fallback(ref, files),
                f"regex:fallback:{type(exc).__name__}",
            )
        if getattr(service, "_element_cache", None) is None:
            # cold process: warm up in the background, answer now
            start_warmup()
            status = _WARM_STATE["status"]
            label = ("regex:warming" if status == "warming"
                     else "regex:warmup-failed")
            return _regex_fallback(ref, files), label
        elements = service._element_cache or []
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
    return _regex_fallback(ref, files), "regex"


def _regex_fallback(ref, files):
    from tools.sysml_html_viewer.ask_model import build_method_context
    return build_method_context(ref, files)
