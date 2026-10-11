"""Validator wiring under the deployed runtime, synthetic API data.

The batteries build the production runtime (the startup check, then the
deployed services) and, for the MCP proof, launch the REAL stdio MCP server
process. Both run against a clean shared clone of this repository at HEAD
with a deployment binding bound to that commit, so the real startup check
(exact commit, clean tree, ``sai-`` identity, served-model record) and the
served-model guard run unchanged; only the API is synthetic. There is no
bundle, selector or candidate flag (owner decision 2026-10-11). Not
privileged evidence.
"""
from contextlib import asynccontextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import threading

import anyio
import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr at collection time

from de4sdv.semantic.deployment_runtime import StartupCheckError
from de4sdv.sysml_api.served_model import ServedModel
from scripts import validate_semantic_mcp as validator
from tests.model_contract_fixtures import binding_dict, model_contract
from test_model_authority_runtime import EC_DEFS, _elements_and_bindings

ROOT = Path(__file__).resolve().parents[1]
PROJECT, COMMIT = "pid", "cid"


@pytest.fixture(scope="module")
def checkout(tmp_path_factory):
    """A clean shared clone of this repository at HEAD (the deployed commit)."""
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    root = tmp_path_factory.mktemp("validators") / "DE4SDV"
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(root)],
                   check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "--quiet", "--detach", head], check=True)
    return root, head


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


def build_inputs(tmp_path, head, *, elements=None):
    elements_, bindings = _elements_and_bindings()
    elements_ += _proof_elements()
    elements = elements_ if elements is None else elements
    served = ServedModel.from_elements(elements_, source_export_sha256="e" * 64).to_dict()
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps(binding_dict(
        git_repository="de4sdv/DE4SDV", git_commit=head, sysml_project_id=PROJECT,
        sysml_commit_id=COMMIT, kernel_bindings=bindings, served_model=served)))
    return binding, elements_


@pytest.fixture
def inputs(tmp_path, checkout, monkeypatch):
    root, head = checkout
    monkeypatch.setattr(validator, "ROOT", root)
    binding, elements = build_inputs(tmp_path, head)
    return binding, elements, head


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


def _run(elements, head, **kwargs):
    async def run():
        async with synthetic_api(elements) as url:
            return await validator.run_mcp_validation(api_url=url, expected_git_revision=head,
                                                      **kwargs)
    return anyio.run(run)


def test_deployed_runtime_drives_the_real_stdio_server(inputs, monkeypatch):
    binding, elements, head = inputs
    launched = instrument(monkeypatch)
    report = _run(elements, head, binding_path=binding)
    sai = model_contract().identity.id
    assert report["proof_a_resolved_evidence_contract"] is True
    assert report["proof_b_native_verification"] is True
    assert report["proof_b_subject"]["element_id"] == "req-1"
    authority = report["semantic_authority"]
    assert authority["kind"] == "model" and authority["startup_check"] == "passed"
    assert authority["semantic_authority"] == authority["semantic_authority_id"] == sai
    assert authority["served_model_check"] == "passed"
    assert report["tools"]["model_status"]["semantic_authority"]["id"] == sai
    assert report["exercised_tool_count"] == report["tool_count"] == 7
    argv = launched[0].args
    for flag, value in [("--binding", str(binding.resolve())), ("--expected-git-revision", head)]:
        assert argv[argv.index(flag) + 1] == value
    for retired in ("--semantic-authority", "--model-authority-bundle", "--allow-candidate-bundle",
                    "--ontology", "--o3-authority-bundle", "--runtime-composition"):
        assert retired not in argv


def test_mcp_paths_resolve_from_caller_working_directory(inputs, tmp_path, monkeypatch):
    binding, elements, head = inputs
    launched = instrument(monkeypatch)
    monkeypatch.chdir(tmp_path)
    report = _run(elements, head, binding_path=binding.relative_to(tmp_path))
    assert report["semantic_authority"]["kind"] == "model"
    argv = launched[0].args
    assert argv[argv.index("--binding") + 1] == str(binding.resolve())


def _leaf_exceptions(exc):
    if isinstance(exc, BaseExceptionGroup):
        for inner in exc.exceptions:
            yield from _leaf_exceptions(inner)
    else:
        yield exc


def test_a_server_serving_another_model_produces_no_report(inputs, monkeypatch):
    """The REAL server launched against an API whose corpus is not the
    validated export starts (its startup check passes) and refuses every
    tool call at the served-model guard; the validator produces no report."""
    binding, elements, head = inputs
    drifted = [dict(e, declaredName="drifted") if e.get("@id") == "req-signal" else e
               for e in elements]
    original_stdio = validator.stdio_client
    launched = []

    @asynccontextmanager
    async def drifted_server(params):
        async with synthetic_api(drifted) as url:
            args = params.args
            args[args.index("--api-url") + 1] = url
            launched.append(list(args))
            async with original_stdio(params) as streams:
                yield streams

    monkeypatch.setattr(validator, "stdio_client", drifted_server)
    with pytest.raises(BaseException) as excinfo:
        _run(elements, head, binding_path=binding)
    assert launched, "the real server was launched"
    messages = [str(leaf) for leaf in _leaf_exceptions(excinfo.value)]
    assert any("served model differs from the validated export" in m for m in messages), messages


def test_a_server_on_another_commit_refuses_to_start(inputs, tmp_path, monkeypatch):
    binding, elements, head = inputs
    other = tmp_path / "other-binding.json"
    document = json.loads(binding.read_text())
    document["git_commit"] = "b" * 40
    other.write_text(json.dumps(document))
    original_stdio = validator.stdio_client

    @asynccontextmanager
    async def other_commit_server(params):
        args = params.args
        args[args.index("--binding") + 1] = str(other)
        args[args.index("--expected-git-revision") + 1] = "b" * 40
        async with original_stdio(params) as streams:
            yield streams

    monkeypatch.setattr(validator, "stdio_client", other_commit_server)
    with pytest.raises(BaseException):  # the server refuses to start; no result
        _run(elements, head, binding_path=binding)


def test_mcp_validator_cli_accepts_the_deployed_runtime(inputs, tmp_path, monkeypatch):
    binding, elements, head = inputs
    output = tmp_path / "result.json"

    async def run():
        async with synthetic_api(elements) as url:
            monkeypatch.setattr("sys.argv", ["validate_semantic_mcp.py", "--api-url", url,
                "--binding", str(binding), "--expected-git-revision", head,
                "--output", str(output)])
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


def test_full_queries_run_under_the_deployed_runtime(inputs, tmp_path, monkeypatch):
    from scripts import validate_full_model_semantic_queries as queries

    binding, elements, head = inputs
    monkeypatch.setattr(queries, "ROOT", validator.ROOT)
    report = full_report(binding, tmp_path)

    async def run():
        async with synthetic_api(elements) as url:
            return queries.run_queries(api_url=url, binding_path=binding, semantic_report_path=report)

    result = anyio.run(run)
    assert len(result["results"]) == len(queries.QUERY_CASES)
    assert result["semantic_authority"]["semantic_authority"] == model_contract().identity.id
    assert result["semantic_authority"]["served_model_check"] == "passed"
    assert result["evidence_contract_state"] == "resolved"


@pytest.mark.parametrize("failure,match", [
    ("wrong-commit", "wrong commit"),
    ("scope", "full-model"),
    ("semantic-authority", "wrong semantic authority"),
    ("no-served-model", "no served model"),
    ("v1-binding", "revision binding"),
])
def test_a_refused_startup_check_refuses_before_server_launch(inputs, monkeypatch, failure, match):
    binding, elements, head = inputs
    document = json.loads(binding.read_text())
    if failure == "wrong-commit":
        document["git_commit"] = "b" * 40
    elif failure == "scope":
        document["scope"] = "fixture"
    elif failure == "semantic-authority":
        document["semantic_authority"]["id"] = "sai-" + "b" * 32
    elif failure == "no-served-model":
        document.pop("served_model")
    else:
        document.pop("schema")
        document.pop("semantic_authority")
        document["ontology"] = {"path": "x.yaml", "sha256": "0" * 64}
    binding.write_text(json.dumps(document))

    def forbidden_transport(*args, **kwargs):
        pytest.fail("a refused startup check launched a server")

    monkeypatch.setattr(validator, "stdio_client", forbidden_transport)
    with pytest.raises(StartupCheckError, match=match):
        anyio.run(lambda: validator.run_mcp_validation(
            api_url="http://127.0.0.1:1", binding_path=binding, expected_git_revision=head))


@pytest.mark.parametrize("failure", [
    "report-revision", "kernel-bindings-not-passed", "source-document-count",
    "report-semantic-authority", "binding-current", "runtime-semantic-authority",
])
def test_full_queries_preserve_report_and_runtime_guards(inputs, tmp_path, monkeypatch, failure):
    from scripts import validate_full_model_semantic_queries as queries
    binding, elements, head = inputs
    monkeypatch.setattr(queries, "ROOT", validator.ROOT)
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
    if failure == "binding-current":
        monkeypatch.setattr(queries, "_git_head", lambda: "b" * 40)
    with pytest.raises((ValueError, RuntimeError)):
        queries.run_queries(api_url="http://127.0.0.1:1", binding_path=binding,
                            semantic_report_path=report)
