"""Validator wiring under the model authority (O4 Wave C2), synthetic API data.

The batteries run under a model-authority bundle (closed, or a candidate with
the explicit ``--allow-candidate-bundle`` evidence flag). These tests drive
the REAL MCP validator and the REAL stdio MCP server process against a
synthetic SysML API serving a fixture that a real model bundle of this
checkout verifies against (model-built contract, revision binding v2, kernel
bindings for every pin). Not privileged closure evidence.
"""
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import threading

import anyio
import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr at collection time

from de4sdv.semantic import model_authority_runtime as mar
from de4sdv.sysml_api.revisions import RevisionBinding
from scripts import validate_semantic_mcp as validator
from tests.model_contract_fixtures import binding_dict
from test_model_authority_runtime import EC_DEFS, _close, _elements_and_bindings

ROOT = Path(__file__).resolve().parents[1]
REVISION = "a" * 40
PROJECT, COMMIT = "pid", "cid"


def ref(identifier):
    return {"@id": identifier}


def _proof_elements():
    """reqCommandEmergencyBraking (Proof A), the query cases, a verified req (Proof B)."""
    elements = []

    def requirement(identifier, name):
        elements.extend([
            {"@id": identifier, "@type": "RequirementUsage", "declaredName": name},
            {"@id": f"{identifier}-typing", "@type": "FeatureTyping",
             "owningRelatedElement": ref(identifier), "type": ref("root-Requirement"),
             "typedFeature": ref(identifier)},
        ])

    requirement("req-braking", "reqCommandEmergencyBraking")
    requirement("req-signal", "reqProvideMiddlewareSignalAccess")
    requirement("req-binding", "reqAuthenticateServiceBinding")
    requirement("req-1", "reqVerifiedByCase")
    elements.extend([
        {"@id": "product-1", "@type": "PartUsage", "declaredName": "memberProduct"},
        {"@id": "product-1-typing", "@type": "FeatureTyping", "owningRelatedElement": ref("product-1"),
         "type": ref("root-MemberProduct"), "typedFeature": ref("product-1")},
        {"@id": "subject-membership", "@type": "SubjectMembership",
         "owningRelatedElement": ref("req-braking"), "memberElement": ref("product-1")},
        {"@id": "verification-1", "@type": "VerificationCaseUsage",
         "declaredName": "nominalMovingVehicleTargetVerification"},
        {"@id": "rvm-1", "@type": "RequirementVerificationMembership",
         "owningRelatedElement": ref("verification-1"), "memberElement": ref("req-1")},
    ])
    for index in range(EC_DEFS):
        elements.append({"@id": f"ec-braking-dep-{index}", "@type": "Dependency",
                         "source": [ref(f"ec-use-{index}")], "target": [ref("req-braking")]})
    return elements


def build_inputs(tmp_path, *, close=True):
    elements, bindings = _elements_and_bindings()
    elements += _proof_elements()
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps(binding_dict(
        git_repository="de4sdv/DE4SDV", git_commit=REVISION, sysml_project_id=PROJECT,
        sysml_commit_id=COMMIT, kernel_bindings=bindings)))
    bundle = mar.build_model_bundle(ROOT, git_revision=REVISION)
    if close:
        bundle = _close(bundle, RevisionBinding.load(binding), binding, tmp_path)
    path = tmp_path / "model.json"
    path.write_text(json.dumps(bundle))
    return binding, path, bundle, elements


@pytest.fixture
def inputs(tmp_path):
    return build_inputs(tmp_path)


@asynccontextmanager
async def synthetic_api(elements, project=PROJECT, commit=COMMIT):
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


def instrument(monkeypatch):
    launched = []
    original_stdio = validator.stdio_client

    @asynccontextmanager
    async def stdio(params):
        launched.append(params)
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "stdio_client", stdio)
    return launched


def _run(elements, **kwargs):
    async def run():
        async with synthetic_api(elements) as url:
            return await validator.run_mcp_validation(api_url=url, expected_git_revision=REVISION,
                                                      **kwargs)
    return anyio.run(run)


def test_model_runtime_drives_the_selector_and_the_real_stdio_server(inputs, monkeypatch):
    binding, path, bundle, elements = inputs
    launched = instrument(monkeypatch)
    report = _run(elements, binding_path=binding, authority="model", model_bundle_path=path,
                  model_bundle_id=bundle["bundle_id"])
    assert report["proof_a_resolved_evidence_contract"] is True
    assert report["proof_b_native_verification"] is True
    assert report["proof_b_subject"]["element_id"] == "req-1"
    assert report["semantic_authority"]["kind"] == "model"
    assert report["semantic_authority"]["authority_id"] == f"mab:{bundle['bundle_id']}"
    assert report["tools"]["model_status"]["semantic_authority"]["id"] == f"mab:{bundle['bundle_id']}"
    assert report["exercised_tool_count"] == report["tool_count"] == 7
    argv = launched[0].args
    for flag, value in [("--semantic-authority", "model"),
                        ("--model-authority-bundle", str(path.resolve())),
                        ("--model-authority-bundle-id", bundle["bundle_id"]),
                        ("--binding", str(binding.resolve())),
                        ("--expected-git-revision", REVISION)]:
        assert argv[argv.index(flag) + 1] == value
    assert "--allow-candidate-bundle" not in argv
    for retired in ("--ontology", "--o3-authority-bundle", "--runtime-composition"):
        assert retired not in argv


def test_candidate_bundle_runs_only_with_the_explicit_evidence_flag(tmp_path, monkeypatch):
    binding, path, bundle, elements = build_inputs(tmp_path, close=False)

    def forbidden_transport(*args, **kwargs):
        pytest.fail("a candidate bundle without the evidence flag launched a server")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises(ValueError):
        _run(elements, binding_path=binding, authority="model", model_bundle_path=path,
             model_bundle_id=bundle["bundle_id"])
    monkeypatch.undo()
    launched = instrument(monkeypatch)
    report = _run(elements, binding_path=binding, authority="model", model_bundle_path=path,
                  model_bundle_id=bundle["bundle_id"], allow_candidate_bundle=True)
    assert report["semantic_authority"]["authority_id"] == f"mab:{bundle['bundle_id']}"
    assert "--allow-candidate-bundle" in launched[0].args


def test_mcp_paths_resolve_from_caller_working_directory(inputs, tmp_path, monkeypatch):
    binding, path, bundle, elements = inputs
    launched = instrument(monkeypatch)
    monkeypatch.chdir(tmp_path)
    report = _run(elements, binding_path=binding.relative_to(tmp_path), authority="model",
                  model_bundle_path=path.relative_to(tmp_path), model_bundle_id=bundle["bundle_id"])
    assert report["semantic_authority"]["kind"] == "model"
    argv = launched[0].args
    assert argv[argv.index("--binding") + 1] == str(binding.resolve())
    assert argv[argv.index("--model-authority-bundle") + 1] == str(path.resolve())


def test_server_on_a_retired_authority_produces_no_report(inputs, monkeypatch):
    binding, path, bundle, elements = inputs
    original_stdio = validator.stdio_client

    @asynccontextmanager
    async def wrong_authority(params):
        # Deliberately launch the real server with a retired selector.
        params.args[params.args.index("--semantic-authority") + 1] = "legacy"
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "stdio_client", wrong_authority)
    with pytest.raises(BaseException):  # the server refuses to start; no result
        _run(elements, binding_path=binding, authority="model", model_bundle_path=path,
             model_bundle_id=bundle["bundle_id"])


def test_mcp_validator_cli_accepts_the_model_runtime(inputs, tmp_path, monkeypatch):
    binding, path, bundle, elements = inputs
    output = tmp_path / "result.json"

    async def run():
        async with synthetic_api(elements) as url:
            monkeypatch.setattr("sys.argv", ["validate_semantic_mcp.py", "--api-url", url,
                "--binding", str(binding), "--expected-git-revision", REVISION,
                "--output", str(output), "--semantic-authority", "model",
                "--model-authority-bundle", str(path),
                "--model-authority-bundle-id", bundle["bundle_id"]])
            return await anyio.to_thread.run_sync(validator.main)

    assert anyio.run(run) == 0
    assert json.loads(output.read_text())["semantic_authority"]["kind"] == "model"


def full_report(binding, tmp_path):
    document = json.loads(binding.read_text())
    report = tmp_path / "semantic-report.json"
    report.write_text(json.dumps(dict(
        git_commit=document["git_commit"], sysml_project_id=document["sysml_project_id"],
        sysml_commit_id=document["sysml_commit_id"], kernel_binding_validation={"passed": True},
        source_document_count=3, semantic_authority=document["semantic_authority"],
    )))
    return report


def test_full_queries_run_under_the_model_runtime(inputs, tmp_path, monkeypatch):
    from scripts import validate_full_model_semantic_queries as queries

    binding, path, bundle, elements = inputs
    report = full_report(binding, tmp_path)
    monkeypatch.setattr(queries, "_git_head", lambda: REVISION)

    async def run():
        async with synthetic_api(elements) as url:
            return queries.run_queries(api_url=url, binding_path=binding, semantic_report_path=report,
                                       authority="model", model_bundle_path=path,
                                       model_bundle_id=bundle["bundle_id"])

    result = anyio.run(run)
    assert len(result["results"]) == len(queries.QUERY_CASES)
    assert result["semantic_authority"]["authority_id"] == f"mab:{bundle['bundle_id']}"
    assert result["evidence_contract_state"] == "resolved"


@pytest.mark.parametrize("entrypoint", ["mcp", "full-queries"])
@pytest.mark.parametrize("bundle_id", [
    " " + "mab-" + "0" * 32, "mab-" + "0" * 32 + "\n", "MAB-" + "0" * 32, "o3b-" + "0" * 32,
])
def test_malformed_bundle_ids_refuse_before_construction(tmp_path, monkeypatch, entrypoint, bundle_id):
    from de4sdv.semantic import entry_authority
    from scripts import validate_full_model_semantic_queries as queries

    def forbidden_construction(*args, **kwargs):
        pytest.fail("malformed bundle ID reached runtime construction")

    monkeypatch.setattr(entry_authority, "build_model_runtime", forbidden_construction)
    monkeypatch.setattr(entry_authority, "build_entry_semantic_runtime", forbidden_construction)
    with pytest.raises(ValueError, match="literal mab-"):
        if entrypoint == "mcp":
            anyio.run(lambda: validator.run_mcp_validation(
                api_url="http://127.0.0.1:1", binding_path=tmp_path / "missing-binding.json",
                expected_git_revision=REVISION, authority="model",
                model_bundle_path=tmp_path / "missing-bundle.json", model_bundle_id=bundle_id,
            ))
        else:
            queries.run_queries(
                api_url="http://127.0.0.1:1", binding_path=tmp_path / "missing-binding.json",
                semantic_report_path=tmp_path / "missing-report.json", authority="model",
                model_bundle_path=tmp_path / "missing-bundle.json", model_bundle_id=bundle_id,
            )


def test_actual_mcp_cli_refuses_padded_bundle_id(inputs, tmp_path):
    binding, path, bundle, elements = inputs
    output = tmp_path / "must-not-exist.json"
    command = [
        sys.executable, "-B", str(ROOT / "scripts/validate_semantic_mcp.py"),
        "--binding", str(binding), "--expected-git-revision", REVISION, "--output", str(output),
        "--semantic-authority", "model", "--model-authority-bundle", str(path),
        "--model-authority-bundle-id", " \t" + bundle["bundle_id"] + "\n",
    ]

    async def run():
        async with synthetic_api(elements) as url:
            return await anyio.to_thread.run_sync(lambda: subprocess.run(
                command + ["--api-url", url], cwd=tmp_path, text=True,
                capture_output=True, timeout=45,
            ))

    result = anyio.run(run)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "literal" in result.stderr and "mab-" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("failure", [
    "unset-authority", "legacy-authority", "o3-authority", "unknown-authority", "missing-bundle",
    "wrong-bundle-id", "foreign-binding", "incomplete-definitions", "v1-binding",
])
def test_invalid_selection_refuses_before_server_launch(inputs, monkeypatch, failure):
    binding, path, bundle, _ = inputs
    options = dict(authority="model", model_bundle_path=path, model_bundle_id=bundle["bundle_id"])
    document = json.loads(binding.read_text())
    if failure == "unset-authority":
        options["authority"] = None
    elif failure == "legacy-authority":
        options["authority"] = "legacy"
    elif failure == "o3-authority":
        options["authority"] = "o3"
    elif failure == "unknown-authority":
        options["authority"] = "unknown"
    elif failure == "missing-bundle":
        options.pop("model_bundle_path")
    elif failure == "wrong-bundle-id":
        options["model_bundle_id"] = "mab-" + "0" * 32
    elif failure == "foreign-binding":
        document["sysml_commit_id"] = "foreign-commit"
    elif failure == "incomplete-definitions":
        document["kernel_bindings"].pop(0)
    else:
        document.pop("schema")
        document.pop("semantic_authority")
        document["ontology"] = {"path": "x.yaml", "sha256": "0" * 64}
    binding.write_text(json.dumps(document))

    def forbidden_transport(*args, **kwargs):
        pytest.fail("invalid explicit selection launched a server")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises(ValueError):
        anyio.run(lambda: validator.run_mcp_validation(
            api_url="http://127.0.0.1:1", binding_path=binding,
            expected_git_revision=REVISION, **options,
        ))


@pytest.mark.parametrize("failure", ["revision", "scope", "semantic-authority"])
def test_mcp_binding_guards_still_refuse(inputs, monkeypatch, failure):
    binding, path, bundle, _ = inputs
    document = json.loads(binding.read_text())
    if failure == "revision":
        document["git_commit"] = "b" * 40
    elif failure == "scope":
        document["scope"] = "fixture"
    else:
        document["semantic_authority"]["id"] = "sai-" + "b" * 32
    binding.write_text(json.dumps(document))

    def forbidden_transport(*args, **kwargs):
        pytest.fail("invalid binding reached MCP transport")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises((ValueError, RuntimeError)):
        anyio.run(lambda: validator.run_mcp_validation(
            api_url="http://127.0.0.1:1", binding_path=binding, expected_git_revision=REVISION,
            authority="model", model_bundle_path=path, model_bundle_id=bundle["bundle_id"],
        ))


@pytest.mark.parametrize("failure", [
    "report-revision", "kernel-bindings-not-passed", "source-document-count",
    "report-semantic-authority", "binding-current", "runtime-semantic-authority",
])
def test_full_queries_preserve_report_and_runtime_guards(inputs, tmp_path, monkeypatch, failure):
    from scripts import validate_full_model_semantic_queries as queries
    binding, path, bundle, _ = inputs
    report = full_report(binding, tmp_path)
    document = json.loads(report.read_text())
    if failure == "report-revision":
        document["sysml_commit_id"] = "foreign-commit"
    elif failure == "kernel-bindings-not-passed":
        document["kernel_binding_validation"]["passed"] = False
    elif failure == "source-document-count":
        document["source_document_count"] = 2
    elif failure == "report-semantic-authority":
        document["semantic_authority"]["id"] = "sai-" + "b" * 32
    elif failure == "runtime-semantic-authority":
        bound = json.loads(binding.read_text())
        bound["semantic_authority"]["id"] = "sai-" + "b" * 32
        document["semantic_authority"] = bound["semantic_authority"]
        binding.write_text(json.dumps(bound))
    report.write_text(json.dumps(document))
    monkeypatch.setattr(queries, "_git_head",
                        lambda: "b" * 40 if failure == "binding-current" else REVISION)
    with pytest.raises((ValueError, RuntimeError)):
        queries.run_queries(api_url="http://127.0.0.1:1", binding_path=binding,
                            semantic_report_path=report, authority="model",
                            model_bundle_path=path, model_bundle_id=bundle["bundle_id"])
