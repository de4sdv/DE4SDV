"""Validator wiring against synthetic API data, not privileged closure evidence."""
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import anyio
import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr at collection time

from scripts import validate_semantic_mcp as validator
from de4sdv.semantic.authority_ids import LEGACY_AUTHORITY_ID
from test_c5_integration_closure import _kernel_bindings, _service_elements
from test_semantic_mcp import ontology_identity

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REVISION = "a" * 40


@pytest.fixture
def proof_inputs(tmp_path):
    elements = _service_elements()
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps(dict(
        git_repository="de4sdv/DE4SDV", git_commit=REVISION,
        sysml_project_id="project-1", sysml_commit_id="commit-1",
        import_timestamp="2026-09-01T00:00:00Z", import_tool_version="synthetic-fixture",
        semantic_validation="passed", scope="full-model", ontology=ontology_identity(),
        kernel_bindings=_kernel_bindings(),
    )))
    return binding, elements


@asynccontextmanager
async def synthetic_api(elements, project="project-1", commit="commit-1"):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == f"/projects/{project}":
                payload = {"@id": project, "@type": "Project"}
            elif self.path == f"/projects/{project}/commits/{commit}":
                payload = {"@id": commit, "@type": "Commit"}
            elif self.path.startswith(f"/projects/{project}/commits/{commit}/elements?"):
                payload = elements
            else:
                self.send_error(404)
                return
            encoded = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_explicit_legacy_runtime_drives_selector_and_real_stdio(proof_inputs, monkeypatch):
    binding, elements = proof_inputs
    launched = []
    original_stdio = validator.stdio_client

    @asynccontextmanager
    async def stdio(params):
        launched.append(params)
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "stdio_client", stdio)

    async def run():
        async with synthetic_api(elements) as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding, expected_git_revision=REVISION,
                ontology_path=ONTOLOGY, authority="legacy",
            )

    result = anyio.run(run)
    assert result["proof_a_blocked_evidence_contract"] is True
    assert result["proof_b_native_verification"] is True
    assert result["proof_b_subject"]["element_id"] == "req-1"
    assert result["semantic_authority"]["authority_id"] == LEGACY_AUTHORITY_ID
    argv = launched[0].args
    assert argv[argv.index("--semantic-authority") + 1] == "legacy"
    assert result["tools"]["model_status"]["semantic_authority"]["id"] == LEGACY_AUTHORITY_ID


def selected_inputs(tmp_path):
    """Extend an existing synthetic composition fixture, never mirror model files."""
    import hashlib
    from de4sdv.semantic import o3_bundle as ob
    from de4sdv.sysml_api.revisions import RevisionBinding
    from test_o4_runtime_composition import inputs

    binding, path, bundle, elements = inputs(tmp_path)
    document = json.loads(binding.read_text())
    fixture_bindings = _kernel_bindings()
    replaced = {row["ontology_class"] for row in fixture_bindings}
    removed_ids = {row["element_id"] for row in document["kernel_bindings"]
                   if row["ontology_class"] in replaced}
    document["kernel_bindings"] = [row for row in document["kernel_bindings"]
                                   if row["ontology_class"] not in replaced] + fixture_bindings
    elements = [element for element in elements if element["@id"] not in removed_ids]
    binding.write_text(json.dumps(document))
    elements.extend(_service_elements())
    prior = bundle["api_closure"]
    attestation = ob.build_closure_attestation(
        bundle, binding=RevisionBinding.load(binding),
        binding_sha256="sha256:" + hashlib.sha256(binding.read_bytes()).hexdigest(),
        element_count=len(elements), export_identity_sha256=None,
        validations=prior["validation"],
        verification_case_grounding=prior["verification_case_grounding"],
        generated_at=prior["generated_at"],
    )
    bundle = ob.close_bundle(bundle, attestation)
    path.write_text(json.dumps(bundle))
    return binding, path, bundle, elements


def instrument(monkeypatch):
    built, selected, launched = [], [], []
    populations = []
    original_build = validator.build_explicit_semantic_runtime
    original_select = validator._select_native_verification_subject
    original_stdio = validator.stdio_client

    def build(**kwargs):
        assert kwargs["environ"] == {}
        runtime, selection = original_build(**kwargs)
        original_list = runtime.repository.list_elements

        def list_elements(*args, **kwargs):
            population = original_list(*args, **kwargs)
            populations.append(population)
            return population

        monkeypatch.setattr(runtime.repository, "list_elements", list_elements)
        built.append((runtime, selection))
        return runtime, selection

    def select(elements, traversal):
        runtime = built[0][0]
        assert traversal is runtime.traversal
        assert traversal.contract is runtime.contract
        assert elements is populations[-1]
        selected.append(traversal)
        return original_select(elements, traversal)

    @asynccontextmanager
    async def stdio(params):
        launched.append(params)
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "build_explicit_semantic_runtime", build)
    monkeypatch.setattr(validator, "_select_native_verification_subject", select)
    monkeypatch.setattr(validator, "stdio_client", stdio)
    return built, selected, launched


@pytest.mark.parametrize("composition", [None, "o3+definitions"])
def test_selected_runtime_and_server_share_authority(tmp_path, monkeypatch, composition):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    built, selected, launched = instrument(monkeypatch)
    options = dict(authority="o3", bundle_path=path, bundle_id=bundle["bundle_id"],
                   composition=composition)

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding, expected_git_revision=REVISION,
                ontology_path=ONTOLOGY, **options,
            )

    report = anyio.run(run)
    assert len(built) == len(selected) == len(launched) == 1
    runtime, selection = built[0]
    assert report["semantic_authority"] == selection.provenance()
    assert report["tools"]["model_status"]["semantic_authority"]["id"] == runtime.semantic_authority_id
    assert report["proof_b_subject"]["element_id"] == "req-1"
    assert report["exercised_tool_count"] == 7
    assert report["exposed_tool_count"] == 11
    argv = launched[0].args
    for flag, value in [("--semantic-authority", "o3"),
                        ("--o3-authority-bundle", str(path)),
                        ("--o3-authority-bundle-id", bundle["bundle_id"]),
                        ("--binding", str(binding)),
                        ("--expected-git-revision", REVISION)]:
        assert argv[argv.index(flag) + 1] == value
    if composition:
        assert argv[argv.index("--runtime-composition") + 1] == composition
        assert report["semantic_authority"]["activation_blocked"] is True
        assert "authored contract" in report["semantic_authority"]["fallback"]
        assert runtime.semantic_authority_id in json.dumps(report["tools"]["impact"]["provenance"])
    else:
        assert "--runtime-composition" not in argv


@pytest.mark.parametrize("mode", ["legacy", "o3", "o3+definitions"])
def test_mcp_paths_resolve_from_caller_working_directory(tmp_path, monkeypatch, mode):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    built, selected, launched = instrument(monkeypatch)
    monkeypatch.chdir(tmp_path)
    options = {}
    if mode != "legacy":
        options.update(authority="o3", bundle_path=path.relative_to(tmp_path),
                       bundle_id=bundle["bundle_id"])
    if mode == "o3+definitions":
        options["composition"] = mode

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding.relative_to(tmp_path),
                expected_git_revision=REVISION,
                ontology_path=Path(os.path.relpath(ONTOLOGY, tmp_path)), **options,
            )

    report = anyio.run(run)
    assert report["semantic_authority"]["kind"] == mode
    assert len(built) == len(selected) == len(launched) == 1
    assert report["tools"]["model_status"]["semantic_authority"]["id"] == built[0][0].semantic_authority_id
    argv = launched[0].args
    assert argv[argv.index("--binding") + 1] == str(binding.resolve())
    assert argv[argv.index("--ontology") + 1] == str(ONTOLOGY.resolve())
    if mode != "legacy":
        assert argv[argv.index("--o3-authority-bundle") + 1] == str(path.resolve())


def test_default_legacy_ignores_authority_environment(proof_inputs, monkeypatch):
    binding, elements = proof_inputs
    monkeypatch.setenv("DE4SDV_SEMANTIC_AUTHORITY", "o3")
    monkeypatch.setenv("DE4SDV_O3_AUTHORITY_BUNDLE", "/absent/environment-bundle.json")
    monkeypatch.setenv("DE4SDV_O3_AUTHORITY_BUNDLE_ID", "foreign-environment-id")
    built, selected, launched = instrument(monkeypatch)

    async def run():
        async with synthetic_api(elements) as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding, expected_git_revision=REVISION,
                ontology_path=ONTOLOGY,
            )

    report = anyio.run(run)
    assert built[0][0].semantic_authority_id == LEGACY_AUTHORITY_ID
    assert len(selected) == 1
    assert report["semantic_authority"]["kind"] == "legacy"
    assert report["tools"]["model_status"]["semantic_authority"]["id"] == LEGACY_AUTHORITY_ID
    assert "--o3-authority-bundle" not in launched[0].args


def test_server_authority_mismatch_refuses_real_results(tmp_path, monkeypatch):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    original_stdio = validator.stdio_client

    @asynccontextmanager
    async def wrong_authority(params):
        # Deliberately launch a different real authority, not forged tool output.
        params.args[params.args.index("--semantic-authority") + 1] = "legacy"
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "stdio_client", wrong_authority)

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding, expected_git_revision=REVISION,
                ontology_path=ONTOLOGY, authority="o3", bundle_path=path,
                bundle_id=bundle["bundle_id"],
            )

    with pytest.raises(RuntimeError, match="authority mismatch"):
        anyio.run(run)


def full_report(binding, tmp_path):
    from scripts.validate_full_model_semantic_queries import QUERY_CASES
    document = json.loads(binding.read_text())
    report = tmp_path / "semantic-report.json"
    report.write_text(json.dumps(dict(
        git_commit=document["git_commit"], sysml_project_id=document["sysml_project_id"],
        sysml_commit_id=document["sysml_commit_id"], ontology={"passed": True},
        source_document_count=3, ontology_identity=document["ontology"],
    )))
    elements = _service_elements()
    for index, case in enumerate(QUERY_CASES[1:]):
        elements.extend([
            {"@id": f"query-{index}", "@type": "RequirementUsage", "declaredName": case.identifier},
            {"@id": f"query-type-{index}", "@type": "FeatureTyping",
             "owningRelatedElement": {"@id": f"query-{index}"},
             "typedFeature": {"@id": f"query-{index}"}, "type": {"@id": "kernel-requirement"}},
        ])
    return report, elements


def test_full_queries_load_only_shared_runtime_contract(proof_inputs, tmp_path, monkeypatch):
    from de4sdv.semantic.kernel_contract import KernelContract
    from scripts import validate_full_model_semantic_queries as queries
    binding, _ = proof_inputs
    report, elements = full_report(binding, tmp_path)
    original = KernelContract.load
    loaded = []

    def load(path):
        loaded.append(path)
        return original(path)

    monkeypatch.setattr(KernelContract, "load", load)
    monkeypatch.setattr(queries, "_git_head", lambda: REVISION)

    async def run():
        async with synthetic_api(elements) as url:
            return queries.run_queries(api_url=url, binding_path=binding, semantic_report_path=report)

    result = anyio.run(run)
    assert len(result["results"]) == len(queries.QUERY_CASES)
    assert len(loaded) == 1


def test_mcp_validator_cli_accepts_explicit_runtime(tmp_path, monkeypatch):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    output = tmp_path / "result.json"

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            monkeypatch.setattr("sys.argv", ["validate_semantic_mcp.py", "--api-url", url,
                "--binding", str(binding), "--expected-git-revision", REVISION,
                "--output", str(output), "--semantic-authority", "o3",
                "--o3-authority-bundle", str(path), "--o3-authority-bundle-id", bundle["bundle_id"],
                "--runtime-composition", "o3+definitions"])
            return await anyio.to_thread.run_sync(validator.main)

    assert anyio.run(run) == 0
    assert json.loads(output.read_text())["semantic_authority"]["kind"] == "o3+definitions"


@pytest.mark.parametrize("composition", [None, "o3+definitions"])
def test_mcp_refuses_padded_bundle_id(tmp_path, composition):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    supplied_id = " \t" + bundle["bundle_id"] + "\n"

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return await validator.run_mcp_validation(
                api_url=url, binding_path=binding, expected_git_revision=REVISION,
                ontology_path=ONTOLOGY, authority="o3", bundle_path=path,
                bundle_id=supplied_id, composition=composition,
            )

    with pytest.raises(ValueError, match="literal.*bundle|bundle.*literal"):
        anyio.run(run)


@pytest.mark.parametrize("composition", [None, "o3+definitions"])
def test_actual_mcp_cli_refuses_padded_bundle_id(tmp_path, composition):
    binding, path, bundle, elements = selected_inputs(tmp_path)
    output = tmp_path / "must-not-exist.json"
    command = [
        sys.executable, "-B", str(ROOT / "scripts/validate_semantic_mcp.py"),
        "--binding", str(binding), "--expected-git-revision", REVISION,
        "--ontology", str(ONTOLOGY), "--output", str(output),
        "--semantic-authority", "o3", "--o3-authority-bundle", str(path),
        "--o3-authority-bundle-id", " \t" + bundle["bundle_id"] + "\n",
    ]
    if composition is not None:
        command += ["--runtime-composition", composition]

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return await anyio.to_thread.run_sync(lambda: subprocess.run(
                command + ["--api-url", url], cwd=tmp_path, text=True,
                capture_output=True, timeout=45,
            ))

    result = anyio.run(run)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "literal" in result.stderr and "bundle" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("composition", [None, "o3+definitions"])
def test_full_queries_refuse_padded_bundle_id(tmp_path, monkeypatch, composition):
    from scripts import validate_full_model_semantic_queries as queries
    binding, path, bundle, elements = selected_inputs(tmp_path)
    report, query_elements = full_report(binding, tmp_path)
    combined = list({item["@id"]: item for item in elements + query_elements}.values())
    monkeypatch.setattr(queries, "_git_head", lambda: REVISION)

    async def run():
        async with synthetic_api(combined, "pid", "cid") as url:
            return queries.run_queries(
                api_url=url, binding_path=binding, semantic_report_path=report,
                authority="o3", bundle_path=path,
                bundle_id=" \t" + bundle["bundle_id"] + "\n", composition=composition,
            )

    with pytest.raises(ValueError, match="literal.*bundle|bundle.*literal"):
        anyio.run(run)


@pytest.mark.parametrize("entrypoint", ["mcp", "full-queries"])
@pytest.mark.parametrize("bundle_id", [
    " " + "o3b-" + "0" * 32, "o3b-" + "0" * 32 + "\n",
    "O3B-" + "0" * 32, "", 7, [],
])
def test_malformed_bundle_ids_refuse_before_construction(tmp_path, monkeypatch, entrypoint, bundle_id):
    from de4sdv.semantic import composition_construction
    from scripts import validate_full_model_semantic_queries as queries

    def forbidden_construction(*args, **kwargs):
        pytest.fail("malformed bundle ID reached runtime construction")

    monkeypatch.setattr(validator, "build_explicit_semantic_runtime", forbidden_construction)
    monkeypatch.setattr(composition_construction, "build_explicit_semantic_runtime", forbidden_construction)
    with pytest.raises(ValueError, match="literal.*bundle|bundle.*literal"):
        if entrypoint == "mcp":
            anyio.run(lambda: validator.run_mcp_validation(
                api_url="http://127.0.0.1:1", binding_path=tmp_path / "missing-binding.json",
                expected_git_revision=REVISION, ontology_path=ONTOLOGY, authority="o3",
                bundle_path=tmp_path / "missing-bundle.json", bundle_id=bundle_id,
            ))
        else:
            queries.run_queries(
                api_url="http://127.0.0.1:1", binding_path=tmp_path / "missing-binding.json",
                semantic_report_path=tmp_path / "missing-report.json", authority="o3",
                bundle_path=tmp_path / "missing-bundle.json", bundle_id=bundle_id,
            )


@pytest.mark.parametrize("failure", [
    "unknown-authority", "missing-bundle", "wrong-bundle-id", "unclosed-bundle",
    "unknown-composition", "legacy-composition", "composition-missing-bundle",
    "foreign-binding", "incomplete-definitions",
])
def test_invalid_selection_refuses_before_server_launch(tmp_path, monkeypatch, failure):
    binding, path, bundle, _ = selected_inputs(tmp_path)
    options = dict(authority="o3", bundle_path=path, bundle_id=bundle["bundle_id"])
    if failure == "unknown-authority":
        options["authority"] = "unknown"
    elif failure == "missing-bundle":
        options.pop("bundle_path")
    elif failure == "wrong-bundle-id":
        options["bundle_id"] = "o3b-" + "0" * 32
    elif failure == "unclosed-bundle":
        bundle["state"] = "core"
        path.write_text(json.dumps(bundle))
    elif failure == "unknown-composition":
        options["composition"] = "unknown"
    elif failure == "legacy-composition":
        options.update(authority="legacy", composition="o3+definitions")
    elif failure == "composition-missing-bundle":
        options.pop("bundle_path")
        options["composition"] = "o3+definitions"
    elif failure == "foreign-binding":
        document = json.loads(binding.read_text())
        document["sysml_commit_id"] = "foreign-commit"
        binding.write_text(json.dumps(document))
    else:
        document = json.loads(binding.read_text())
        document["kernel_bindings"].pop(0)
        binding.write_text(json.dumps(document))
        options["composition"] = "o3+definitions"

    def forbidden_transport(*args, **kwargs):
        pytest.fail("invalid explicit selection launched a fallback server")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises(ValueError):
        anyio.run(lambda: validator.run_mcp_validation(
            api_url="http://127.0.0.1:1", binding_path=binding,
            expected_git_revision=REVISION, ontology_path=ONTOLOGY, **options,
        ))


@pytest.mark.parametrize("failure", ["revision", "scope", "ontology"])
def test_mcp_binding_guards_still_refuse(proof_inputs, monkeypatch, failure):
    binding, _ = proof_inputs
    document = json.loads(binding.read_text())
    if failure == "revision":
        document["git_commit"] = "b" * 40
    elif failure == "scope":
        document["scope"] = "fixture"
    else:
        document["ontology"]["sha256"] = "b" * 64
    binding.write_text(json.dumps(document))

    def forbidden_transport(*args, **kwargs):
        pytest.fail("invalid binding reached MCP transport")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises((ValueError, RuntimeError)):
        anyio.run(lambda: validator.run_mcp_validation(
            api_url="http://127.0.0.1:1", binding_path=binding,
            expected_git_revision=REVISION, ontology_path=ONTOLOGY,
        ))


@pytest.mark.parametrize("failure", [
    "report-revision", "ontology-not-passed", "source-document-count",
    "report-ontology", "binding-current", "runtime-ontology",
])
def test_full_queries_preserve_report_and_runtime_guards(proof_inputs, tmp_path, monkeypatch, failure):
    from scripts import validate_full_model_semantic_queries as queries
    binding, _ = proof_inputs
    report, _ = full_report(binding, tmp_path)
    document = json.loads(report.read_text())
    if failure == "report-revision":
        document["sysml_commit_id"] = "foreign-commit"
    elif failure == "ontology-not-passed":
        document["ontology"]["passed"] = False
    elif failure == "source-document-count":
        document["source_document_count"] = 2
    elif failure == "report-ontology":
        document["ontology_identity"]["sha256"] = "b" * 64
    elif failure == "runtime-ontology":
        bound = json.loads(binding.read_text())
        bound["ontology"]["sha256"] = "b" * 64
        document["ontology_identity"] = bound["ontology"]
        binding.write_text(json.dumps(bound))
    report.write_text(json.dumps(document))
    monkeypatch.setattr(queries, "_git_head", lambda: "b" * 40 if failure == "binding-current" else REVISION)
    with pytest.raises((ValueError, RuntimeError)):
        queries.run_queries(api_url="http://127.0.0.1:1", binding_path=binding, semantic_report_path=report)


def test_full_queries_reuse_composed_runtime(tmp_path, monkeypatch):
    from scripts import validate_full_model_semantic_queries as queries
    binding, path, bundle, elements = selected_inputs(tmp_path)
    report, query_elements = full_report(binding, tmp_path)
    elements = list({element["@id"]: element for element in elements + query_elements}.values())
    monkeypatch.setattr(queries, "_git_head", lambda: REVISION)

    async def run():
        async with synthetic_api(elements, "pid", "cid") as url:
            return queries.run_queries(
                api_url=url, binding_path=binding, semantic_report_path=report,
                authority="o3", bundle_path=path, bundle_id=bundle["bundle_id"],
                composition="o3+definitions",
            )

    result = anyio.run(run)
    assert len(result["results"]) == len(queries.QUERY_CASES)
    for entry in result["results"]:
        assert entry["impact"]["semantic_authority"]["kind"] == "o3+definitions"
        assert entry["impact"]["semantic_authority"]["activation_blocked"] is True
