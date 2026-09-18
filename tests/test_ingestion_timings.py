"""Out-of-band timings must not change evidence or exception semantics."""
import json

import pytest


def test_timings_are_opt_in_and_propagate_failures(monkeypatch, tmp_path):
    from de4sdv.sysml_api.performance import timing

    path = tmp_path / "timings.jsonl"
    monkeypatch.setenv("DE4SDV_INGESTION_TIMINGS", str(path))
    with timing("normal", elements=2) as metrics:
        metrics["pages"] = 3
    with pytest.raises(ValueError, match="deliberate"):
        with timing("failure"):
            raise ValueError("deliberate")
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["status"] for r in records] == ["passed", "failed"]
    assert records[0]["elements"] == 2
    assert records[0]["pages"] == 3
    assert all(r["elapsed_seconds"] >= 0 for r in records)
    assert all(r["pid"] > 0 for r in records)
    monkeypatch.delenv("DE4SDV_INGESTION_TIMINGS")
    with timing("disabled"):
        pass
    assert len(path.read_text().splitlines()) == 2


def test_unserializable_metadata_never_masks_a_real_failure(monkeypatch, tmp_path):
    from de4sdv.sysml_api.performance import timing

    monkeypatch.setenv("DE4SDV_INGESTION_TIMINGS", str(tmp_path / "timings.jsonl"))
    with pytest.raises(ValueError, match="real failure"):
        with timing("bad-metadata", unserializable=object()):
            raise ValueError("real failure")


def test_transport_records_counts_without_payload_or_url(monkeypatch, tmp_path):
    import io
    import urllib.request
    from de4sdv.sysml_api.client import ApiClient

    class Response(io.BytesIO):
        headers = {}

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Response(b'[{"@id":"secret-id"}]'))
    path = tmp_path / "transport.jsonl"
    monkeypatch.setenv("DE4SDV_INGESTION_TIMINGS", str(path))
    assert ApiClient("http://private-host").get_all("/private-path") == [{"@id": "secret-id"}]
    text = path.read_text()
    records = [json.loads(line) for line in text.splitlines()]
    assert {r["stage"] for r in records} >= {"http_exchange", "json_decode", "paginated_readback"}
    assert next(r for r in records if r["stage"] == "http_exchange")["response_bytes"] == len(b'[{"@id":"secret-id"}]')
    aggregate = next(r for r in records if r["stage"] == "paginated_readback")
    assert aggregate["pages"] == 1
    assert aggregate["elements"] == 1
    assert "secret-id" not in text and "private-host" not in text and "private-path" not in text
