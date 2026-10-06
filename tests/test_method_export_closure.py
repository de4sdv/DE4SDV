"""Narrow library-value closure from official serializer output (synthetic only).

These fixtures are not licensed Syside evidence. They exercise the actual export
adapter and the evaluator without inventing missing values in retained exports.
"""
from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.sysml_api.baseline import BaselineManifest, BaselineSource
import scripts.export_sysml_api_baseline as exporter


def _fixture(monkeypatch, tmp_path: Path, *, omit_kind: str | None = None):
    user = [
        {"@id": "md", "@type": "MetadataUsage", "ownedRelationship": [{"@id": "kind-m"}]},
        {"@id": "kind-m", "@type": "FeatureMembership", "memberName": "kind", "memberElement": {"@id": "kind"}},
        {"@id": "kind", "@type": "ReferenceUsage", "ownedRelationship": [{"@id": "kind-v"}]},
        {"@id": "kind-v", "@type": "FeatureValue", "memberElement": {"@id": "expr"}},
        {"@id": "expr", "@type": "OperatorExpression", "ownedRelationship": [{"@id": "operand-test"}, {"@id": "operand-analyze"}]},
    ]
    uri = "file:///pinned-syside/Systems%20Library/VerificationCases.sysml"
    library = [
        {"@id": "vc-def", "@type": "VerificationCaseDefinition", "declaredName": "VerificationCase"},
        {"@id": "vc-set", "@type": "VerificationCaseUsage", "declaredName": "verificationCases"},
        {"@id": "method-enum", "@type": "EnumerationDefinition", "declaredName": "VerificationMethodKind", "ownedRelationship": [{"@id": f"enum-{kind}"} for kind in ("inspect", "demo", "test", "analyze")]},
        {"@id": "unrelated-library", "@type": "PartDefinition", "declaredName": "Unrelated"},
    ]
    for kind in ("inspect", "demo", "test", "analyze"):
        library.append({"@id": f"enum-{kind}", "@type": "FeatureMembership", "memberElement": {"@id": f"literal-{kind}"}})
        if kind != omit_kind:
            library.append({"@id": f"literal-{kind}", "@type": "EnumerationUsage", "declaredName": kind})
    for kind in ("test", "analyze"):
        user.extend([
            {"@id": f"operand-{kind}", "@type": "FeatureMembership", "memberElement": {"@id": f"expr-{kind}"}},
            {"@id": f"expr-{kind}", "@type": "FeatureReferenceExpression", "ownedRelationship": [{"@id": f"ref-{kind}"}]},
            {"@id": f"ref-{kind}", "@type": "Membership", "memberElement": {"@id": f"literal-{kind}", "@uri": uri}},
        ])

    def document(url, elements):
        return SimpleNamespace(lock=lambda: nullcontext(SimpleNamespace(url=url, root_node=elements)))

    user_doc = document((tmp_path / "model.sysml").as_uri(), user)
    library_doc = document(uri, library)

    class Options:
        @staticmethod
        def minimal():
            return Options()

        def with_options(self, **kwargs):
            return self

    import sys
    monkeypatch.setitem(sys.modules, "syside", SimpleNamespace(
        SerializationOptions=Options,
        json=SimpleNamespace(dumps=lambda elements, options: json.dumps(elements)),
        try_load_model=lambda paths: (
            SimpleNamespace(user_docs=[user_doc], all_docs=[user_doc, library_doc]),
            SimpleNamespace(contains_errors=lambda **kwargs: False),
        ),
    ))
    manifest = BaselineManifest((BaselineSource("model.sysml", "reviewed", "f" * 64, 1),))
    monkeypatch.setattr(exporter, "ROOT", tmp_path)
    monkeypatch.setattr(exporter, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(BaselineManifest, "discover", lambda root: manifest)
    return manifest


def test_export_closes_actual_method_kind_references(monkeypatch, tmp_path: Path):
    manifest = _fixture(monkeypatch, tmp_path)
    path = tmp_path / "export.json"
    exporter.export_baseline(path, "a" * 40)
    artifact = json.loads(path.read_text())
    by_id = {e["@id"]: e for e in artifact["elements"]}
    assert "literal-test" in by_id and "literal-analyze" in by_id
    assert "method-enum" in by_id
    assert "unrelated-library" not in by_id  # bounded enum closure, not a library import
    assert artifact["source_manifest"] == list(manifest.to_dicts())
    assert by_id["ref-test"]["memberElement"] == {"@id": "literal-test"}
    ctx = me.EvaluationContext(
        revision=me.RevisionIdentity("a" * 40, "project", "commit", "candidate"),
        elements=tuple(artifact["elements"]),
        scope=me.DeclaredEvaluationScope("scope", "INC-X", ("usage",), frozenset(), ()),
    )
    values, witnesses, unresolved = me._metadata_kind_values(ctx, "md")
    assert values == ("analyze", "test")
    assert set(witnesses) == {"expr-test", "expr-analyze"}
    assert unresolved == ()


def test_export_refuses_missing_method_kind_literal(monkeypatch, tmp_path: Path):
    _fixture(monkeypatch, tmp_path, omit_kind="test")
    with pytest.raises(RuntimeError, match="VerificationMethodKind"):
        exporter.export_baseline(tmp_path / "export.json", "a" * 40)
