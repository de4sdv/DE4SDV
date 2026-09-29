"""Exact read-back reuse: API data, never an export substitute."""
from copy import deepcopy

import pytest

from de4sdv.sysml_api.baseline import BaselineExportBundle
from de4sdv.sysml_api.errors import BaselineImportError
from de4sdv.sysml_api.ingestion import import_baseline


class RecordingClient:
    def __init__(self, values):
        self.values = values
        self.reads = []
        self.posts = []

    def request(self, method, path, payload=None):
        self.posts.append((method, path, payload))
        return {"@id": "project" if path == "/projects" else "commit"}

    def get_all(self, path):
        self.reads.append(path)
        return deepcopy(self.values)


def bundle():
    return BaselineExportBundle(
        git_commit="a" * 40,
        elements={
            "one": {"@id": "one", "@type": "PartUsage", "type": {"@id": "two"}},
            "two": {"@id": "two", "@type": "PartDefinition"},
        },
        element_sources={"one": "example.sysml", "two": "example.sysml"},
        external_references=(),
        source_manifest=(),
    )


def test_import_returns_complete_verified_api_values_not_export_values():
    exported = bundle()
    values = deepcopy(list(exported.elements.values()))
    values[0]["serverField"] = "preserved"
    client = RecordingClient(values)
    result = import_baseline(client, exported, project_name="test")
    assert list(result.readback_elements) == values
    assert result.readback_elements[0] is not exported.elements["one"]
    assert len(client.reads) == 1
    assert result.element_count == 2
    assert result.internal_reference_count == 1
    assert len(client.posts) == 2


def test_run_import_does_not_fetch_verified_commit_twice(monkeypatch, tmp_path):
    import json
    from types import SimpleNamespace
    from scripts import import_sysml_api_baseline as script
    from de4sdv.sysml_api.baseline import BaselineManifest

    exported = bundle()
    path = tmp_path / "export.json"
    path.write_text(json.dumps(exported.to_dict()))
    values = deepcopy(list(exported.elements.values()))
    values[0]["serverField"] = "from API only"
    client = RecordingClient(values)
    monkeypatch.setattr(script, "_git_head", lambda: exported.git_commit)
    monkeypatch.setattr(script, "ApiClient", lambda *args, **kwargs: client)
    monkeypatch.setattr(BaselineManifest, "discover", lambda *args: BaselineManifest(()))
    seen = []

    def validate(contract, elements, sources):
        seen.extend(elements)
        return SimpleNamespace(entries=[], passed=True, summary={}, to_dict=lambda: {})

    monkeypatch.setattr(script, "validate_ontology_bindings", validate)
    script.run_import(
        api_url="http://unused", export_path=path,
        binding_path=tmp_path / "binding.json", report_path=tmp_path / "report.json",
        project_name="test", git_repository="test/repo",
    )
    assert len(client.reads) == 1
    assert seen == values
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["source_manifest"] == []
    assert report["external_references"] == []


@pytest.mark.parametrize("bad", ["duplicate", "missing-id", "missing-element", "lost-reference", "non-object"])
def test_readback_failure_never_returns_reusable_values(bad):
    exported = bundle()
    values = deepcopy(list(exported.elements.values()))
    if bad == "duplicate":
        values.append(deepcopy(values[0]))
    elif bad == "missing-id":
        values.append({"@type": "PartUsage"})
    elif bad == "missing-element":
        values.pop()
    elif bad == "lost-reference":
        del values[0]["type"]
    else:
        values.append(None)
    with pytest.raises(BaselineImportError):
        import_baseline(RecordingClient(values), exported, project_name="test")


def test_import_records_reference_and_payload_stages(monkeypatch, tmp_path):
    import json
    path = tmp_path / "timings.jsonl"
    monkeypatch.setenv("DE4SDV_INGESTION_TIMINGS", str(path))
    exported = bundle()
    import_baseline(RecordingClient(list(exported.elements.values())), exported, project_name="test")
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert {r["stage"] for r in records} >= {"commit_payload", "baseline_post", "internal_reference_comparison"}
    refs = next(r for r in records if r["stage"] == "internal_reference_comparison")
    assert refs["expected_references"] == refs["actual_references"] == 1


@pytest.mark.parametrize("change", ["head", "source"])
def test_stale_inputs_refuse_before_any_api_write(change, monkeypatch, tmp_path):
    import json
    from scripts import import_sysml_api_baseline as script
    from de4sdv.sysml_api.baseline import BaselineManifest, BaselineSource

    exported = bundle()
    path = tmp_path / "export.json"
    path.write_text(json.dumps(exported.to_dict()))
    client = RecordingClient([])
    monkeypatch.setattr(script, "ApiClient", lambda *a, **kw: client)
    monkeypatch.setattr(script, "_git_head", lambda: "b" * 40 if change == "head" else exported.git_commit)
    current = BaselineManifest((BaselineSource("changed.sysml", "reviewed", "c" * 64, 1),))
    monkeypatch.setattr(BaselineManifest, "discover", lambda *a: current)
    with pytest.raises((RuntimeError, ValueError), match="stale"):
        script.run_import(
            api_url="http://unused", export_path=path,
            binding_path=tmp_path / "binding.json", report_path=tmp_path / "report.json",
            project_name="test", git_repository="test/repo",
        )
    assert not client.posts and not client.reads
    assert not (tmp_path / "binding.json").exists()
