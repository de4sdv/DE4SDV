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

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_SEMANTIC_RUNTIME = None
_SEMANTIC_ERROR: str | None = None
# short-lived memo: element UUID -> method-context dict
_SEMANTIC_CTX_CACHE: dict[str, dict] = {}

# cold-load coordination + warmup state (one cold load per process, ever;
# /ask never blocks on it — see build_method_context_api)
_COLD_LOCK = threading.Lock()
_WARM_STATE: dict = {"status": "idle", "error": None}
_SNAPSHOT_FORMAT = 1


def warm_status() -> dict:
    return dict(_WARM_STATE)


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


# ---- per-revision disk snapshot of the API element corpus -----------------
# Only the network retrieval is replaced; binding/ontology enforcement
# still runs on every call and the snapshot identity must match the
# binding exactly. Snapshots live outside the repo (default ~/.cache).

def _snapshot_dir() -> Path:
    d = Path(os.environ.get(
        "DE4SDV_SEMANTIC_SNAPSHOT_DIR",
        str(Path.home() / ".cache" / "de4sdv" / "semantic-snapshots"),
    ))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _snapshot_identity(service) -> dict:
    return {
        "format": _SNAPSHOT_FORMAT,
        "git_commit": str(service.binding.git_commit),
        "sysml_project_id": str(service.binding.sysml_project_id),
        "sysml_commit_id": str(service.binding.sysml_commit_id),
    }


def _snapshot_path(service) -> Path:
    return _snapshot_dir() / f"{service.binding.sysml_commit_id}.json"


def _snapshot_write(service, elements: list[dict]) -> None:
    """Atomic snapshot write + sidecar sha256 of the main file."""
    path = _snapshot_path(service)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    payload = {
        **_snapshot_identity(service),
        "element_count": len(elements),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "elements": elements,
    }
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    path.with_suffix(".json.sha256").write_text(digest, encoding="utf-8")
    os.replace(tmp, path)  # atomic on POSIX


def _snapshot_load(service) -> list[dict] | None:
    """Checksum + identity verified snapshot, or None (any doubt = miss)."""
    path = _snapshot_path(service)
    try:
        raw = path.read_bytes()
        expected_digest = path.with_suffix(".json.sha256").read_text().strip()
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            return None
        data = json.loads(raw.decode("utf-8"))
        for key, value in _snapshot_identity(service).items():
            if data.get(key) != value:
                return None
        elements = data.get("elements")
        if not isinstance(elements, list) or not elements:
            return None
        if data.get("element_count") != len(elements):
            return None
        return elements
    except (OSError, ValueError):
        return None


def _load_elements_with_snapshot(service) -> list[dict]:
    """Binding checks FIRST, then snapshot, then network.

    A snapshot is never trusted without the runtime contract passing; a
    corrupted or stale snapshot is ignored (network load overwrites it).
    """
    service._require_valid_revision()
    if service._element_cache is not None:
        return service._element_cache
    snap = _snapshot_load(service)
    if snap is not None:
        service._element_cache = snap
        return snap
    elements = service._elements()  # network cold load (binding enforced)
    try:
        _snapshot_write(service, elements)
    except OSError:
        pass  # snapshot is an optimization, never a correctness gate
    return elements


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
                       elements: list[dict]) -> dict:
    """Derive the ontology-mapped method context for elements.

    One pass over the bound revision's elements, collecting every
    ontology-declared relation family that touches any target:

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

    Same-name union applies to every family (subject references inside
    requirements are ReferenceUsage elements while the browsed element
    is typically the PartUsage in its system context; parity-proven
    24/24 for hasSubject against the deployed API). Entries dedupe by
    element id; a family is listed only when the model declares it.
    """
    cache_key = ",".join(sorted(
        str(t.get("@id") or "") for t in targets
    ))
    if cache_key and cache_key in _SEMANTIC_CTX_CACHE:
        return _SEMANTIC_CTX_CACHE[cache_key]

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

    target_ids = {str(t.get("@id") or "") for t in targets}
    target_ids.discard("")

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

    subject_reqs: dict[str, dict] = {}
    verifying_cases: dict[str, dict] = {}
    verified_reqs: dict[str, dict] = {}
    incoming_deps: dict[tuple[str, str], dict] = {}
    allocations: dict[str, dict] = {}

    for m in elements:
        mtype = str(m.get("@type") or "")
        if mtype in subject_types:
            if not (target_ids & set(_ref_ids(m.get(member_prop)))):
                continue
            for oid in _ref_ids(m.get("owningRelatedElement")):
                owner = by_id.get(oid)
                if owner is not None:
                    subject_reqs[oid] = element_ref(owner, "requirement")
        elif mtype in rvm_types:
            # Deployed payload shape: the member is the verified
            # requirement, the owner is the verification case.
            if target_ids & set(_ref_ids(m.get("memberElement"))):
                for oid in _ref_ids(m.get("owningRelatedElement")):
                    owner = by_id.get(oid)
                    if owner is not None:
                        verifying_cases[oid] = element_ref(
                            owner, "verification_case")
            if target_ids & set(_ref_ids(m.get("owningRelatedElement"))):
                for mid in _ref_ids(m.get("memberElement")):
                    req = by_id.get(mid)
                    if req is not None:
                        verified_reqs[mid] = element_ref(
                            req, "verified_requirement")
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
        elif mtype in alloc_types:
            if target_ids & set(_ref_ids(m.get("source"))):
                for tid in _ref_ids(m.get("target")):
                    tgt = by_id.get(tid)
                    if tgt is not None:
                        allocations[tid] = element_ref(
                            tgt, "realized_target")

    ctx: dict = {}
    if subject_reqs:
        ctx["requirement_subject_of"] = sorted(
            subject_reqs.values(),
            key=lambda r: (r["requirement"], r["element_id"]))
    if verifying_cases:
        ctx["verified_by"] = sorted(
            verifying_cases.values(),
            key=lambda r: (r["verification_case"], r["element_id"]))
    if verified_reqs:
        ctx["verifies"] = sorted(
            verified_reqs.values(),
            key=lambda r: (r["verified_requirement"], r["element_id"]))
    if incoming_deps:
        ctx["incoming_dependencies"] = sorted(
            incoming_deps.values(),
            key=lambda r: (r["source_element"], r["element_id"]))
    if allocations:
        ctx["realized_by"] = sorted(
            allocations.values(),
            key=lambda r: (r["realized_target"], r["element_id"]))
    if ctx:
        ctx["derivation"] = (
            "API-derived: ontology-declared predicates over the deployed "
            "SysML v2 revision (hasSubject, verifiedBy both directions, "
            "hasRelevantEvidenceContract incoming, realizedBy outgoing), "
            "same-name elements united"
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
