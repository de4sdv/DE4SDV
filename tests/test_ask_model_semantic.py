"""Tests for the API-derived method context (ask-model increment B).

The deployed API is never called in tests: the semantic runtime is
monkeypatched. Fixtures are synthetic (no model mirrors). The ladder
under test: semantic off -> "regex"; on + runtime works -> "api";
on + runtime fails -> explicit "regex:fallback:<Error>".
"""
from __future__ import annotations

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


class _FakeMapping:
    configuration = {
        "membership_types": ["SubjectMembership"],
        "member_property": "memberElement",
        "owner_types": ["RequirementUsage"],
    }


class _FakeContract:
    def relationship_mapping(self, predicate):
        assert predicate == "hasSubject"
        return _FakeMapping()


class _FakeService:
    contract = _FakeContract()

    @staticmethod
    def _elements():
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
        def _elements():
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
        def _elements():
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


def test_api_failure_degrades_to_labeled_regex(fixture_repo, monkeypatch):
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")

    def boom():
        raise RuntimeError("binding mismatch")

    monkeypatch.setattr(ams, "_runtime", boom)
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path.startswith("regex:fallback:")
    assert "binding mismatch" in path or "RuntimeError" in path
    # evidence still complete: regex found the fixture's subject relation
    subs = ctx.get("requirement_subject_of", [])
    assert any(s.get("id") == "N-SEM-001" for s in subs)


def test_api_empty_context_reports_api_empty(fixture_repo, monkeypatch):
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")

    class _NoMatch(_FakeService):
        @staticmethod
        def _elements():
            return []  # API has no such element (revision drift)

    monkeypatch.setattr(ams, "_runtime", lambda: _NoMatch())
    ref, files = _resolve(fixture_repo)
    ctx, path = ams.build_method_context_api(ref, files)
    assert path == "api:no-match"
    assert ctx == {}


def test_runtime_contract_missing_sha_fails_closed(fixture_repo, monkeypatch):
    monkeypatch.setenv("NOUS_ASK_SEMANTIC", "1")
    monkeypatch.delenv("DE4SDV_EXPECTED_GIT_SHA", raising=False)
    monkeypatch.delenv("DE4SDV_REVISION_BINDING", raising=False)
    with pytest.raises(RuntimeError, match="missing DE4SDV_EXPECTED_GIT_SHA"):
        ams._runtime()
