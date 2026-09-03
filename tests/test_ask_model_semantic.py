"""Tests for the API-derived method context (ask-model increment B).

The deployed API is never called in tests: the semantic runtime is
monkeypatched. Fixtures are synthetic (no model mirrors). The ladder
under test: semantic off -> "regex"; on + runtime works -> "api";
on + runtime fails -> explicit "regex:fallback:<Error>".
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.sysml_html_viewer import ask_model_semantic as ams  # noqa: E402
from tools.sysml_html_viewer.model_parse import (  # noqa: E402
    build_member_index,
    load_model,
)


FIXTURE = """\
package SemanticFixture {
  part def ProductLineMemberProduct;
  part systemCtx {
    part memberProduct : ProductLineMemberProduct;
  }
  requirement needBounded : Need {
    doc /* N-SEM-001 draft bounded need. */
    subject memberProduct : ProductLineMemberProduct;
  }
}
"""


@pytest.fixture()
def fixture_repo(tmp_path):
    base = tmp_path / "repo"
    (base / "textual-notation-of-model" / "packages" / "fix").mkdir(
        parents=True
    )
    (base / "textual-notation-of-model" / "packages" / "fix"
     / "m.sysml").write_text(FIXTURE, encoding="utf-8")
    return base


def _resolve(fixture_repo):
    files = load_model(fixture_repo, ["textual-notation-of-model"])
    index = build_member_index(files)
    ref, _ = ams._regex_fallback.__globals__["resolve_element"](
        index, "memberProduct"
    ) if False else (None, None)
    # resolve directly (same helper ask_model uses)
    from tools.sysml_html_viewer.ask_model import resolve_element
    ref, cands = resolve_element(index, "memberProduct")
    return ref, files


def test_semantic_disabled_returns_regex(fixture_repo, monkeypatch):
    monkeypatch.delenv("NOUS_ASK_SEMANTIC", raising=False)
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "regex"
    # the fixture declares the subject relation; regex finds it
    subs = ctx.get("requirement_subject_of", [])
    assert any(s.get("id") == "N-SEM-001" for s in subs)


def test_semantic_off_explicit_zero_gives_regex(fixture_repo, monkeypatch):
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "0")
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "regex"


_MAPPINGS = {
    "hasSubject": {
        "membership_types": ["SubjectMembership"],
        "member_property": "memberElement",
        "owner_types": ["RequirementUsage"],
    },
    "verifiedBy": {
        "membership_types": ["RequirementVerificationMembership"],
    },
    "hasRelevantEvidenceContract": {
        "relationship_types": ["Dependency"],
        "source_property": "source",
        "target_property": "target",
    },
    "realizedBy": {
        "relationship_types": ["AllocationUsage"],
    },
}


class _FakeContract:
    def relationship_mapping(self, predicate):
        return type("M", (), {"configuration": _MAPPINGS[predicate]})()


class _FakeService:
    contract = _FakeContract()

    def __init__(self):
        # a warm runtime: the element corpus is already loaded
        self._element_cache = self._build_elements()

    @staticmethod
    def _build_elements():
        # API payload shapes: SubjectMembership referencing its subject
        # through memberElement and its owner through owningRelatedElement
        return [
            {
                "@type": "RequirementUsage",
                "@id": "req-1",
                "declaredName": "needBoundedApi",
            },
            {
                "@type": "SubjectMembership",
                "@id": "sm-1",
                "memberElement": {"@id": "subj-1"},
                "owningRelatedElement": {"@id": "req-1"},
            },
            {
                "@type": "PartUsage",
                "@id": "subj-1",
                "declaredName": "memberProduct",
                "owningRelatedElement": {"@id": "ctx-1"},
            },
            {
                "@type": "PartUsage",
                "@id": "ctx-1",
                "declaredName": "systemCtx",
            },
        ]


def test_api_path_returns_derived_subjects(fixture_repo, monkeypatch):
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")
    monkeypatch.setattr(ams, "_runtime", lambda: _FakeService())
    ams._SEMANTIC_CTX_CACHE.clear()
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "api"
    subs = ctx.get("requirement_subject_of", [])
    assert len(subs) == 1
    assert subs[0]["requirement"] == "needBoundedApi"
    assert subs[0]["sysml_type"] == "RequirementUsage"
    assert "element_id" in subs[0]
    assert "API-derived" in ctx["derivation"]
    ams._SEMANTIC_CTX_CACHE.clear()


def test_api_same_name_union_across_reference_usages(fixture_repo,
                                                     monkeypatch):
    """Subject refs inside requirements are ReferenceUsage elements while
    the browsed element is the PartUsage: union-by-name must collect all
    requirements (the live-verified memberProduct shape)."""
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")

    class _UnionService(_FakeService):
        @staticmethod
        def _build_elements():
            return [
                # the browsed PartUsage: no membership points at it
                {"@type": "PartUsage", "@id": "part-1",
                 "declaredName": "memberProduct",
                 "owningRelatedElement": {"@id": "ctx-1"}},
                {"@type": "PartUsage", "@id": "ctx-1",
                 "declaredName": "systemCtx"},
                # subject reference usages inside requirements
                {"@type": "ReferenceUsage", "@id": "subj-a",
                 "declaredName": "memberProduct"},
                {"@type": "ReferenceUsage", "@id": "subj-b",
                 "declaredName": "memberProduct"},
                # two requirements, each owning one membership
                {"@type": "RequirementUsage", "@id": "req-1",
                 "declaredName": "needBoundedApi"},
                {"@type": "RequirementUsage", "@id": "req-2",
                 "declaredName": "reqOtherApi"},
                {"@type": "SubjectMembership", "@id": "sm-1",
                 "memberElement": {"@id": "subj-a"},
                 "owningRelatedElement": {"@id": "req-1"}},
                {"@type": "SubjectMembership", "@id": "sm-2",
                 "memberElement": {"@id": "subj-b"},
                 "owningRelatedElement": {"@id": "req-2"}},
            ]

    monkeypatch.setattr(ams, "_runtime", lambda: _UnionService())
    ams._SEMANTIC_CTX_CACHE.clear()
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "api"
    subs = ctx.get("requirement_subject_of", [])
    assert {s["requirement"] for s in subs} == {
        "needBoundedApi", "reqOtherApi"
    }
    ams._SEMANTIC_CTX_CACHE.clear()


def test_api_dedupes_shared_subject_across_requirements(fixture_repo,
                                                        monkeypatch):
    """One ReferenceUsage referenced by two memberships: dedupe by owner."""
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")

    class _SharedService(_FakeService):
        @staticmethod
        def _build_elements():
            return [
                {"@type": "ReferenceUsage", "@id": "subj-1",
                 "declaredName": "memberProduct"},
                {"@type": "RequirementUsage", "@id": "req-1",
                 "declaredName": "needA"},
                {"@type": "RequirementUsage", "@id": "req-2",
                 "declaredName": "needB"},
                {"@type": "SubjectMembership", "@id": "sm-1",
                 "memberElement": {"@id": "subj-1"},
                 "owningRelatedElement": {"@id": "req-1"}},
                {"@type": "SubjectMembership", "@id": "sm-2",
                 "memberElement": {"@id": "subj-1"},
                 "owningRelatedElement": {"@id": "req-2"}},
            ]

    monkeypatch.setattr(ams, "_runtime", lambda: _SharedService())
    ams._SEMANTIC_CTX_CACHE.clear()
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    subs = ctx.get("requirement_subject_of", [])
    assert {s["requirement"] for s in subs} == {"needA", "needB"}
    ams._SEMANTIC_CTX_CACHE.clear()


# ---- cold-load policy: snapshot + warmup, visitors never wait ------------

class _Binding:
    git_commit = "sha-test"
    sysml_project_id = "proj-1"
    sysml_commit_id = "commit-1"


class _SnapshotService:
    """Minimal surface for the snapshot functions (no network)."""
    binding = _Binding()
    _element_cache = None


@pytest.fixture()
def snapshot_env(tmp_path, monkeypatch):
    monkeypatch.setattr(ams, "_snapshot_dir", lambda: tmp_path / "snaps")
    return tmp_path / "snaps"


def _fake_elements():
    return [{"@type": "PartUsage", "@id": "e-1", "declaredName": "x"}]


def test_snapshot_roundtrip(snapshot_env):
    """Save then load returns the same elements; tamper and stale
    identity are rejected."""
    service = _SnapshotService()
    d = snapshot_env
    ams._snapshot_write(service, _fake_elements())
    loaded = ams._snapshot_load(service)
    assert loaded == _fake_elements()

    # tampered content -> checksum mismatch -> miss
    path = d / "commit-1.json"
    path.write_text(path.read_text().replace("PartUsage", "PartUsagX"),
                    encoding="utf-8")
    assert ams._snapshot_load(service) is None

    # stale identity -> miss
    ams._snapshot_write(service, _fake_elements())
    data = json.loads(path.read_text())
    data["sysml_commit_id"] = "other-commit"
    path.write_text(json.dumps(data))
    assert ams._snapshot_load(service) is None


def test_warming_ask_never_blocks_and_labels(snapshot_env, fixture_repo,
                                             monkeypatch):
    """Cold process: /ask serves regex immediately with the warming label
    while the background warmup runs; a warm runtime answers 'api'."""
    import threading
    import time as _time

    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")
    monkeypatch.setattr(ams, "_snapshot_dir",
                        lambda: snapshot_env)
    ams._SEMANTIC_CTX_CACHE.clear()
    ams._WARM_STATE.update(status="idle", error=None)

    release = threading.Event()

    class _ColdSlowService:
        """Production shape: fast runtime build; the network element load
        is the slow part and runs in the warmup thread."""
        contract = _FakeContract()
        binding = _Binding()
        _element_cache = None

        def _require_valid_revision(self):
            pass

        def _elements(self):
            release.wait(timeout=15)  # simulates the paginated network load
            return _fake_elements()

    def slow_runtime():
        return _ColdSlowService()

    monkeypatch.setattr(ams, "_runtime", slow_runtime)

    ref, files = _resolve(fixture_repo)

    # 1. ask while cold -> immediate regex:warming, no blocking
    t0 = _time.time()
    ctx, path = ams.build_method_context_api(ref, files)
    elapsed = _time.time() - t0
    assert path == "regex:warming"
    assert elapsed < 2.0  # did NOT wait for the cold load
    subs = ctx.get("requirement_subject_of", [])
    assert any(s.get("id") == "N-SEM-001" for s in subs)
    assert ams.warm_status()["status"] == "warming"

    # 2. warmup completes -> status ready; next ask takes the api path
    release.set()
    for _ in range(100):
        if ams.warm_status()["status"] == "ready":
            break
        _time.sleep(0.05)
    assert ams.warm_status()["status"] == "ready"

    # warm the real runtime into the module state and re-ask
    warm = _FakeService()
    monkeypatch.setattr(ams, "_runtime", lambda: warm)
    warm._element_cache = warm._build_elements()
    ams._WARM_STATE["status"] = "ready"
    ctx2, path2 = ams.build_method_context_api(ref, files)
    assert path2 == "api"
    ams._SEMANTIC_CTX_CACHE.clear()
    ams._WARM_STATE["status"] = "idle"


def test_warmup_failure_labels_ask_path(fixture_repo, monkeypatch):
    """A failed warmup is visible in the label, not silent."""
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")

    def boom():
        raise RuntimeError("snapshot unusable and network down")

    monkeypatch.setattr(ams, "_runtime", boom)
    ams._SEMANTIC_CTX_CACHE.clear()
    ams._WARM_STATE.update(status="idle", error=None)
    ref, files = _resolve(fixture_repo)

    # simulate the state after a failed background warmup
    ams._WARM_STATE["status"] = "error"
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "regex:warmup-failed"
    subs = ctx.get("requirement_subject_of", [])
    assert any(s.get("id") == "N-SEM-001" for s in subs)
    ams._WARM_STATE.update(status="idle", error=None)
