"""Instrumentation parity on a synthetic serializer boundary, not Syside proof."""
from contextlib import nullcontext
import json
import sys
from types import SimpleNamespace

from de4sdv.sysml_api.baseline import BaselineManifest, BaselineSource


def test_export_telemetry_preserves_artifact_bytes(monkeypatch, tmp_path):
    from scripts import export_sysml_api_baseline as script

    monkeypatch.setattr(script, "ROOT", tmp_path)
    monkeypatch.setattr(script, "_git_head", lambda: "a" * 40)
    monkeypatch.setattr(script, "_serialization_options", lambda: object())
    monkeypatch.setattr(script, "_resolve_library_anchors", lambda model: {
        "VerificationCases::" + name: "anchor" for name in script._LIBRARY_ANCHOR_NAMES
    })
    manifest = BaselineManifest((BaselineSource("synthetic.sysml", "reviewed", "b" * 64, 1),))
    monkeypatch.setattr(BaselineManifest, "discover", lambda root: manifest)
    locked = SimpleNamespace(url=(tmp_path / "synthetic.sysml").as_uri(), root_node=object())
    model = SimpleNamespace(user_docs=[SimpleNamespace(lock=lambda: nullcontext(locked))])
    fake = SimpleNamespace(
        try_load_model=lambda paths: (model, SimpleNamespace(contains_errors=lambda **kw: False)),
        json=SimpleNamespace(dumps=lambda *a: json.dumps([{"@id": "one", "@type": "Package"}])),
    )
    monkeypatch.setitem(sys.modules, "syside", fake)
    monkeypatch.delenv("DE4SDV_INGESTION_TIMINGS", raising=False)
    before = tmp_path / "before.json"
    first = script.export_baseline(before, "a" * 40)
    timings = tmp_path / "timings.jsonl"
    monkeypatch.setenv("DE4SDV_INGESTION_TIMINGS", str(timings))
    after = tmp_path / "after.json"
    second = script.export_baseline(after, "a" * 40)
    assert before.read_bytes() == after.read_bytes()
    assert {k: v for k, v in first.items() if k != "output"} == {k: v for k, v in second.items() if k != "output"}
    records = [json.loads(line) for line in timings.read_text().splitlines()]
    assert {r["stage"] for r in records} >= {
        "model_load", "resolve_anchors", "serialize_documents", "build_bundle", "write_artifact",
    }
    assert all(r["status"] == "passed" for r in records)
    assert json.loads(after.read_text())["source_manifest"] == list(manifest.to_dicts())
