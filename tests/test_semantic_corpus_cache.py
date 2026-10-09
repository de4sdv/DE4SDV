"""Exact-revision corpus snapshot reused across MCP restarts (fast start).

Salvaged from draft PR #284 onto the model-authority runtime: the first
element listing of the bound revision is served from an identity-bound,
checksum-verified snapshot when one exists; a cold miss performs exactly one
API retrieval and writes the snapshot; any doubt is a miss that falls back to
the exact API load. The snapshot identity binds the API endpoint (as a
digest), the Git and SysML project/commit identity, the revision binding
(kernel bindings included), the semantic authority and the format version.
A snapshot is a derived read cache, never a semantic authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import mcp.client.stdio  # noqa: F401  (collection-time import; binds stderr early)
import pytest

from de4sdv.semantic import corpus_cache as cc
from de4sdv.sysml_api.errors import RevisionMismatchError
from de4sdv.sysml_api.repository import SysMLRepository, validated_element_corpus
from de4sdv.sysml_api.revisions import RevisionBinding
from increment_model_fixtures import increment_scenario, install_model_workflow
from model_contract_fixtures import binding_dict, model_service, synthetic_identity

REPO_ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
INCREMENT = "INC-FIXTURE-001"


def _corpus() -> tuple[list[dict], list[dict]]:
    scenario = increment_scenario()
    install_model_workflow(scenario)
    return scenario.builder.elements, scenario.builder.bindings


class CountingClient:
    def __init__(self, elements, base_url: str = "http://sysml2-api:9000") -> None:
        self.elements = elements
        self.base_url = base_url
        self.element_retrievals = 0

    def get_all(self, path: str):
        self.element_retrievals += 1
        return list(self.elements)


def _service(client: CountingClient, bindings, *, expected: str = REVISION, **binding_kwargs):
    document = binding_dict(git_commit=REVISION, sysml_project_id="project-1",
                            sysml_commit_id="commit-1", kernel_bindings=bindings, **binding_kwargs)
    service = model_service(RevisionBinding.from_dict(document), SysMLRepository(client),
                            expected_git_revision=expected)
    return service


@pytest.fixture()
def snapshot_dir(tmp_path, monkeypatch):
    directory = tmp_path / "corpus-snapshots"
    monkeypatch.setenv("DE4SDV_SEMANTIC_SNAPSHOT_DIR", str(directory))
    return directory


def _rewrite(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data), encoding="utf-8")
    path.with_suffix(".json.sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest())


# -- corpus validation --------------------------------------------------------


@pytest.mark.parametrize("bad", [[], "not-a-list", [42], [{"@type": "PartUsage"}],
                                 [{"@id": "x", "@type": "A"}, {"@id": "x", "@type": "B"}]])
def test_a_malformed_corpus_is_refused_entirely(bad) -> None:
    with pytest.raises(ValueError):
        validated_element_corpus(bad)


# -- identity and snapshot validity -------------------------------------------


def test_identity_binds_endpoint_revision_binding_and_semantic_authority() -> None:
    elements, bindings = _corpus()
    service = _service(CountingClient(elements), bindings)
    identity = cc.corpus_identity(service)
    assert identity["format"] == cc.CORPUS_SNAPSHOT_FORMAT
    assert (identity["git_commit"], identity["sysml_project_id"], identity["sysml_commit_id"]) == (
        REVISION, "project-1", "commit-1")
    assert identity["semantic_authority"] == service.binding.semantic_authority.to_dict()
    assert identity["semantic_authority_id"] == service.semantic_authority_id
    assert len(identity["api_endpoint_digest"]) == 64 and len(identity["binding_digest"]) == 64
    other_endpoint = _service(CountingClient(elements, "http://other:9000"), bindings)
    assert cc.corpus_identity(other_endpoint)["api_endpoint_digest"] != identity["api_endpoint_digest"]
    reduced = _service(CountingClient(elements), bindings[:-1])
    assert cc.corpus_identity(reduced)["binding_digest"] != identity["binding_digest"]


def test_snapshot_never_records_credentials(snapshot_dir) -> None:
    elements, bindings = _corpus()
    service = _service(CountingClient(elements, "http://deploy-user:secret@host:9000"), bindings)
    path = cc.write_corpus_snapshot(service, elements)
    raw = path.read_text(encoding="utf-8")
    assert "secret" not in raw and "deploy-user" not in raw
    assert cc.load_corpus_snapshot(service) == elements


def test_any_doubt_is_a_miss(snapshot_dir) -> None:
    elements, bindings = _corpus()
    service = _service(CountingClient(elements), bindings)
    path = cc.write_corpus_snapshot(service, elements)
    path.write_text(path.read_text().replace("need0", "needX"))
    assert cc.load_corpus_snapshot(service) is None  # checksum
    for key, value in (("git_commit", "b" * 40), ("sysml_commit_id", "other"),
                       ("format", cc.CORPUS_SNAPSHOT_FORMAT - 1), ("binding_digest", "0" * 64),
                       ("api_endpoint_digest", "0" * 64), ("semantic_authority_id", "mab:other"),
                       ("semantic_authority", synthetic_identity("other").to_dict())):
        cc.write_corpus_snapshot(service, elements)
        _rewrite(path, lambda data, k=key, v=value: data.__setitem__(k, v))
        assert cc.load_corpus_snapshot(service) is None, key
    for mutate in (lambda d: d.__setitem__("elements", []),
                   lambda d: d.__setitem__("elements", d["elements"] + d["elements"][:1]),
                   lambda d: d.__setitem__("element_count", 1)):
        cc.write_corpus_snapshot(service, elements)
        _rewrite(path, mutate)
        assert cc.load_corpus_snapshot(service) is None
    path.write_text(path.read_text()[:50])
    assert cc.load_corpus_snapshot(service) is None


# -- lazy snapshot-first hook ---------------------------------------------------


def test_restart_serves_the_method_tools_from_the_snapshot(snapshot_dir) -> None:
    elements, bindings = _corpus()
    cold_client = CountingClient(elements)
    cold = _service(cold_client, bindings)
    assert cc.install_corpus_snapshot(cold) is True
    assert cold_client.element_retrievals == 0  # installing performs no I/O
    cold_answer = cold.next_obligation(increment=INCREMENT)
    assert cold_client.element_retrievals == 1
    assert len(list(snapshot_dir.glob("*.json"))) == 1

    warm_client = CountingClient(elements)
    warm = _service(warm_client, bindings)
    cc.install_corpus_snapshot(warm)
    warm_answer = warm.next_obligation(increment=INCREMENT)
    assert warm_client.element_retrievals == 0
    assert warm_answer == cold_answer


def test_snapshot_is_never_served_for_another_revision(snapshot_dir) -> None:
    elements, bindings = _corpus()
    service = _service(CountingClient(elements), bindings)
    cc.write_corpus_snapshot(service, elements)
    client = CountingClient(elements)
    other = _service(client, bindings)
    cc.install_corpus_snapshot(other)
    other.repository.list_elements("project-1", "another-commit")
    assert client.element_retrievals == 1


def test_revision_gate_precedes_snapshot_io(snapshot_dir) -> None:
    elements, bindings = _corpus()
    service = _service(CountingClient(elements), bindings)
    cc.write_corpus_snapshot(service, elements)
    stale = _service(CountingClient(elements), bindings, expected="b" * 40)
    cc.install_corpus_snapshot(stale)
    with pytest.raises(RevisionMismatchError):
        stale.next_obligation(increment=INCREMENT)


def test_install_is_skipped_for_services_without_a_supporting_repository() -> None:
    class Bare:
        repository = None

    assert cc.install_corpus_snapshot(Bare()) is False


# -- end to end: the real stdio server, started twice -----------------------------


def _complete_corpus() -> tuple[list[dict], list[dict]]:
    """The scenario over the complete kernel fixture the runtime needs to construct."""
    from increment_model_fixtures import ModelBuilder
    from test_model_authority_runtime import _elements_and_bindings

    kernel_elements, kernel_bindings = _elements_and_bindings()
    builder = ModelBuilder(label="Complete")
    builder.adopt(kernel_elements, kernel_bindings)
    install_model_workflow(increment_scenario(builder))
    return builder.elements, builder.bindings


@pytest.fixture()
def counting_api_server():
    elements, bindings = _complete_corpus()

    class Handler(BaseHTTPRequestHandler):
        retrievals = 0

        def log_message(self, *args):  # noqa: D401 - silence the test server
            return

        def do_GET(self):  # noqa: N802 - http.server API
            if "/elements" in self.path:
                type(self).retrievals += 1
                body = json.dumps(elements).encode()
            else:
                body = json.dumps({"@id": "x"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield Handler, f"http://{host}:{port}", elements, bindings
    finally:
        server.shutdown()
        thread.join()


def test_stdio_restart_lists_zero_elements(snapshot_dir, counting_api_server, tmp_path) -> None:
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    from test_model_authority_runtime import _close
    from de4sdv.semantic import model_authority_runtime as mar

    handler, api_url, _elements, bindings = counting_api_server
    document = binding_dict(git_repository="de4sdv/DE4SDV", git_commit=REVISION,
                            sysml_project_id="project-1", sysml_commit_id="commit-1",
                            kernel_bindings=bindings)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(document))
    bundle = mar.build_model_bundle(REPO_ROOT, git_revision=REVISION)
    closed = _close(bundle, RevisionBinding.load(binding_path), binding_path, tmp_path)
    bundle_path = tmp_path / "model.json"
    bundle_path.write_text(json.dumps(closed))

    def params() -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable,
            args=["scripts/semantic_mcp_server.py", "--api-url", api_url, "--binding", str(binding_path),
                  "--expected-git-revision", REVISION, "--semantic-authority", "model",
                  "--model-authority-bundle", str(bundle_path),
                  "--model-authority-bundle-id", closed["bundle_id"]],
            cwd=str(REPO_ROOT),
            env=dict(os.environ),
        )

    async def run_session():
        async with stdio_client(params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                during_handshake = handler.retrievals
                answer = await session.call_tool("next_obligation", {"increment": INCREMENT})
                return during_handshake, answer.structuredContent

    during_handshake, cold = anyio.run(run_session)
    assert during_handshake == 0
    assert handler.retrievals == 1
    assert cold["query"] == "next_obligation" and cold["increment"]["resolved"] is True
    assert len(list(snapshot_dir.glob("*.json"))) == 1
    warm_handshake, warm = anyio.run(run_session)
    assert warm_handshake == 1 and handler.retrievals == 1  # restart: zero listings
    assert warm == cold


@pytest.mark.parametrize("commit", ["../escape", "nested/commit", ".."])
def test_a_commit_id_that_is_not_a_file_name_never_becomes_a_path(snapshot_dir, tmp_path, commit) -> None:
    elements, bindings = _corpus()
    client = CountingClient(elements)
    document = binding_dict(git_commit=REVISION, sysml_project_id="project-1",
                            sysml_commit_id=commit, kernel_bindings=bindings)
    service = model_service(RevisionBinding.from_dict(document), SysMLRepository(client),
                            expected_git_revision=REVISION)
    with pytest.raises(ValueError, match="file name"):
        cc.write_corpus_snapshot(service, elements)
    assert cc.load_corpus_snapshot(service) is None
    # The hook falls back to the exact API load and writes nothing anywhere.
    assert cc.install_corpus_snapshot(service)
    assert service.repository.list_elements("project-1", commit) == elements
    assert client.element_retrievals == 1
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_the_suite_never_writes_snapshots_to_the_users_cache() -> None:
    """Every test's snapshot directory is its own temporary directory (tests/conftest.py)."""
    default = Path.home() / ".cache" / "de4sdv" / "semantic-snapshots"
    assert not Path(os.environ.get("DE4SDV_SEMANTIC_SNAPSHOT_DIR", default)).is_relative_to(Path.home() / ".cache")
