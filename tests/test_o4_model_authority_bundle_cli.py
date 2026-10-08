"""``scripts/run_model_authority_bundle.py`` against a FAKE model-authority module.

The real ``model_authority_runtime`` / ``model_projection_coverage`` modules
are replaced through ``sys.modules`` so the CLI is tested against the
controller-defined interface, not against any real bundle. No network; a pass
here is CLI/gate-derivation consistency, never privileged evidence. O4 Wave C2
form: no O3 bundle input, model runtime answers instead of the model/O3/legacy
comparison, and the three batteries as closure gates.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import types
from types import SimpleNamespace

import pytest

from de4sdv.semantic import entry_authority as ea
from scripts import run_model_authority_bundle as cli

REV = "c" * 40
MAB = "mab-" + "a" * 32


def _digest(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


class Refused(ValueError):
    pass


def install_model_module(monkeypatch, *, verify_errors=()):
    module = types.ModuleType(cli.MODEL_MODULE)
    module.ModelAuthorityRefused = Refused
    module.calls = []

    def build_model_bundle(root, *, git_revision):
        module.calls.append(("build", git_revision))
        return {"schema": "fake", "bundle_id": MAB, "git_revision": git_revision,
                "state": "candidate",
                "components": {"semantic_authority": {"id": "sai-" + "3" * 32}}}

    def verify_model_bundle(bundle, **kwargs):
        module.calls.append(("verify", bundle["state"], sorted(kwargs)))
        return list(verify_errors)

    def build_model_closure_attestation(bundle, *, binding, binding_sha256,
                                        definition_closure_closed, validations, generated_at,
                                        evidence_contract_closure):
        module.calls.append(("attest", list(evidence_contract_closure)))
        eligible = definition_closure_closed and all(
            v["status"] == "passed" for v in validations.values())
        return {"bundle_id": bundle["bundle_id"], "semantic_authority_id": "sai-" + "3" * 32,
                "definition_closure_closed": definition_closure_closed,
                "validation": validations, "activation_eligible": eligible}

    def close_model_bundle(bundle, attestation):
        return {**bundle, "state": "closed", "closure": attestation}

    module.build_model_bundle = build_model_bundle
    module.verify_model_bundle = verify_model_bundle
    module.build_model_closure_attestation = build_model_closure_attestation
    module.close_model_bundle = close_model_bundle
    monkeypatch.setitem(sys.modules, cli.MODEL_MODULE, module)
    return module


def install_coverage_module(monkeypatch, report, *, drift=(), bundle_errors=()):
    module = types.ModuleType(cli.COVERAGE_MODULE)
    module.build_report = lambda root: copy.deepcopy(report)
    module.load_baseline = lambda root: {}
    module.compare = lambda fresh, baseline: list(drift)
    module.bundle_errors = lambda fresh, bundle, root: list(bundle_errors)
    monkeypatch.setitem(sys.modules, cli.COVERAGE_MODULE, module)
    return module


@pytest.fixture(autouse=True)
def pinned_head(monkeypatch):
    monkeypatch.setattr(cli, "_git_head", lambda: REV)


def write(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


# -- bundle ------------------------------------------------------------------


def test_bundle_writes_candidate_and_verifies(tmp_path, monkeypatch):
    module = install_model_module(monkeypatch)
    assert cli.main(["bundle", "--source-revision", REV, "--out", str(tmp_path / "out")]) == 0
    written = json.loads((tmp_path / "out" / cli.CANDIDATE_BUNDLE).read_text())
    assert written["bundle_id"] == MAB and written["state"] == "candidate"
    assert ("build", REV) in module.calls


def test_bundle_takes_no_o3_input(tmp_path, monkeypatch):
    install_model_module(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(["bundle", "--source-revision", REV, "--o3-bundle", "o3.json",
                  "--out", str(tmp_path)])
    assert exc.value.code == 2


def test_bundle_verification_error_is_nonzero(tmp_path, monkeypatch):
    install_model_module(monkeypatch, verify_errors=["routing differs"])
    assert cli.main(["bundle", "--source-revision", REV, "--out", str(tmp_path)]) == 1


def test_bundle_refuses_moving_revision(tmp_path, monkeypatch):
    install_model_module(monkeypatch)
    with pytest.raises(SystemExit) as exc:
        cli.main(["bundle", "--source-revision", "d" * 40, "--out", str(tmp_path)])
    assert exc.value.code == 1


def test_bundle_refuses_when_model_runtime_missing(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, cli.MODEL_MODULE, None)  # import -> ImportError
    with pytest.raises(SystemExit) as exc:
        cli.main(["bundle", "--source-revision", REV, "--out", str(tmp_path)])
    assert exc.value.code == 1


# -- close: every gate derived from its artifact -------------------------------


COVERAGE = {"schema": "de4sdv.model-projection-coverage/v1", "residual": []}


def readback(passed=True, revision=REV):
    return {"schema": cli.READBACK_SCHEMA, "git_revision": revision, "passed": passed,
            "activation_eligible": passed, "failures": [] if passed else ["x"]}


MEMBERS = [{"source_file": f"f{i}.sysml", "declaration": f"requirement def C{i}",
            "element_id": f"ec{i}"} for i in range(8)]


def answers(overall="PASSED", bundle_id=MAB, identity="EQUAL", authority=None,
            k_pair="EQUIVALENT", grounding="EQUIVALENT", revision=REV):
    return {"schema": cli.ANSWERS_SCHEMA, "git_revision": revision, "model_bundle_id": bundle_id,
            "authority_id": authority or f"mab:{bundle_id}", "overall": overall,
            "answers": {"k_pair": {"classification": k_pair, "errors": [], "missing": []},
                        "classes": {"VerificationCase": {"grounding_result": grounding}}},
            "discriminator": {"closure_members": MEMBERS, "classification": "RECORDED",
                              "closure_identity": {"result": identity}}}


def queries(revision=REV, authority=f"mab:{MAB}", schema=None):
    return {"schema": schema or cli.BATTERY_SCHEMAS["full_model_semantic_queries"],
            "git_commit": revision, "semantic_authority": {"authority_id": authority}}


def scope(revision=REV, authority=f"mab:{MAB}"):
    return {"schema": cli.BATTERY_SCHEMAS["product_line_scope"],
            "revision": {"git_commit": revision}, "model_authority": {"authority_id": authority}}


def mcp(revision=REV, authority=f"mab:{MAB}", tool_count=7, read_only=True):
    return {"schema": cli.BATTERY_SCHEMAS["semantic_mcp"], "revision": {"git_commit": revision},
            "semantic_authority": {"authority_id": authority}, "read_only": read_only,
            "tool_count": tool_count}


def probe(closed=True, revision=REV):
    return {"closure": {"closed": closed, "expected_git_revision": revision,
                        "binding_git_revision": revision}}


@pytest.fixture
def close_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr("de4sdv.sysml_api.revisions.RevisionBinding.load",
                        staticmethod(lambda path: SimpleNamespace(git_commit=REV)))
    files = {
        "model": write(tmp_path / "candidate.json", {"bundle_id": MAB, "git_revision": REV,
                                                     "state": "candidate"}),
        "binding": write(tmp_path / "binding.json", {"git_commit": REV}),
        "definition-probe": write(tmp_path / "probe.json", probe()),
        "coverage": write(tmp_path / "coverage.json", COVERAGE),
        "answers": write(tmp_path / "answers.json", answers()),
        "readback": write(tmp_path / "readback.json", readback()),
        "full-model-semantic-queries": write(tmp_path / "queries.json", queries()),
        "product-line-scope": write(tmp_path / "scope.json", scope()),
        "semantic-mcp": write(tmp_path / "mcp.json", mcp()),
    }
    return tmp_path, files


def run_close(tmp_path, files):
    argv = ["close", "--git-revision", REV, "--out", str(tmp_path / "closed")]
    for flag, path in files.items():
        argv += [f"--{flag}", str(path)]
    code = cli.main(argv)
    summary = json.loads((tmp_path / "closed" / cli.ELIGIBILITY).read_text())
    attestation = json.loads((tmp_path / "closed" / cli.ATTESTATION).read_text())
    return code, summary, attestation


def test_close_all_gates_pass_is_activation_eligible(close_inputs, monkeypatch):
    tmp_path, files = close_inputs
    model = install_model_module(monkeypatch)
    install_coverage_module(monkeypatch, COVERAGE)
    code, summary, attestation = run_close(tmp_path, files)
    assert code == 0 and summary["activation_eligible"] is True
    assert all(summary["gates"].values())
    for name, flag in cli.VALIDATION_FLAGS.items():
        record = attestation["validation"][name]
        assert record["status"] == "passed"
        assert record["sha256"] == _digest(files[flag.replace("_", "-")])  # bound to the artifact
    closed = json.loads((tmp_path / "closed" / cli.CLOSED_BUNDLE).read_text())
    assert closed["state"] == "closed"
    assert ("verify", "closed", ["binding", "binding_sha256", "require_closed", "root",
                                 "validation_artifacts"]) in model.calls
    assert any(MAB in item for item in summary["owner_gated"])
    assert ("attest", MEMBERS) in model.calls  # validated members flow into the attestation


@pytest.mark.parametrize("flag, document, gate", [
    ("readback", readback(passed=False), "verification_anchor_readback"),
    ("readback", readback(revision="e" * 40), "verification_anchor_readback"),
    ("readback", {**readback(), "passed": False}, "verification_anchor_readback"),
    ("readback", {**readback(), "activation_eligible": "true"}, "verification_anchor_readback"),
    ("answers", answers("FAILED"), "model_runtime_answers"),
    ("answers", answers(bundle_id="mab-" + "f" * 32), "model_runtime_answers"),
    ("answers", answers(authority="mab:mab-" + "f" * 32), "model_runtime_answers"),
    ("answers", answers(identity="BLOCKING_MISMATCH"), "model_runtime_answers"),
    ("answers", answers(k_pair="NOT_YET_COMPARABLE"), "model_runtime_answers"),
    ("answers", answers(grounding="BLOCKING_MISMATCH"), "model_runtime_answers"),
    ("answers", answers(revision="e" * 40), "model_runtime_answers"),
    ("full-model-semantic-queries", queries(revision="e" * 40), "full_model_semantic_queries"),
    ("full-model-semantic-queries", queries(authority="mab:mab-" + "f" * 32),
     "full_model_semantic_queries"),
    ("full-model-semantic-queries", queries(schema="other"), "full_model_semantic_queries"),
    ("product-line-scope", scope(authority=None), "product_line_scope"),
    ("product-line-scope", scope(revision="e" * 40), "product_line_scope"),
    ("semantic-mcp", mcp(tool_count=6), "semantic_mcp"),
    ("semantic-mcp", mcp(read_only=False), "semantic_mcp"),
    ("semantic-mcp", mcp(authority="o3:o3b-" + "b" * 32), "semantic_mcp"),
    ("definition-probe", probe(closed=False), "definition_closure_closed"),
    ("definition-probe", probe(revision="e" * 40), "definition_closure_closed"),
])
def test_close_failed_gate_blocks_activation(close_inputs, monkeypatch, flag, document, gate):
    tmp_path, files = close_inputs
    install_model_module(monkeypatch)
    install_coverage_module(monkeypatch, COVERAGE)
    write(files[flag], document)
    code, summary, _ = run_close(tmp_path, files)
    assert code == 2
    assert summary["activation_eligible"] is False
    assert summary["gates"][gate] is False


@pytest.mark.parametrize("kwargs", [
    {"drift": ["residual drift: new residual entry 'Feature'"]},
    {"bundle_errors": ["bundle routing digest differs from the checkout"]},
])
def test_close_coverage_problems_block_activation(close_inputs, monkeypatch, kwargs):
    tmp_path, files = close_inputs
    install_model_module(monkeypatch)
    install_coverage_module(monkeypatch, COVERAGE, **kwargs)
    code, summary, _ = run_close(tmp_path, files)
    assert code == 2 and summary["gates"]["model_projection_coverage"] is False


def test_close_coverage_artifact_must_equal_recomputed_report(close_inputs, monkeypatch):
    tmp_path, files = close_inputs
    install_model_module(monkeypatch)
    install_coverage_module(monkeypatch, {**COVERAGE, "residual": ["Feature"]})
    code, summary, _ = run_close(tmp_path, files)
    assert code == 2 and summary["gates"]["model_projection_coverage"] is False


def test_close_bundle_verification_error_blocks(close_inputs, monkeypatch):
    tmp_path, files = close_inputs
    install_model_module(monkeypatch, verify_errors=["digest differs"])
    install_coverage_module(monkeypatch, COVERAGE)
    code, summary, _ = run_close(tmp_path, files)
    assert code == 2 and summary["activation_eligible"] is False
    assert summary["problems"]["bundle_verification"] == ["digest differs"]


def test_close_refuses_already_closed_or_foreign_revision(close_inputs, monkeypatch):
    tmp_path, files = close_inputs
    install_model_module(monkeypatch)
    install_coverage_module(monkeypatch, COVERAGE)
    write(files["model"], {"bundle_id": MAB, "git_revision": REV, "state": "closed"})
    with pytest.raises(SystemExit):
        run_close(tmp_path, files)


def test_population_delta_is_not_a_gate():
    assert set(cli.VALIDATION_FLAGS) == {
        "model_projection_coverage", "model_runtime_answers", "verification_anchor_readback",
        "full_model_semantic_queries", "product_line_scope", "semantic_mcp"}


def test_close_validations_match_the_runtime_contract():
    from de4sdv.semantic import model_authority_runtime as mar

    assert set(cli.VALIDATION_FLAGS) == set(mar.REQUIRED_MODEL_VALIDATIONS)


# -- compare helpers -----------------------------------------------------------


class _Traversal:
    def __init__(self, hops=None, raise_on=()):
        self.hops, self.raise_on, self.calls = hops or {}, set(raise_on), []

    def traverse(self, predicate, element, elements):
        self.calls.append(predicate)
        if element["@id"] in self.raise_on:
            raise RuntimeError("identity not found")
        return [SimpleNamespace(target={"@id": t}) for t in self.hops.get(element["@id"], [])]


def test_discriminator_population_records_model_resolution():
    elements = [{"@id": s} for s in ("s1", "s2", "s3")]
    service = SimpleNamespace(traversal=_Traversal({"s1": ["ec1", "ec2"], "s2": ["ec1"]}),
                              semantic_authority_id=f"mab:{MAB}")
    record = cli.discriminator_population(service, elements, ["s1", "s2", "s3"])
    assert record["hop_count"] == 3 and record["distinct_sources"] == 2
    assert record["distinct_targets"] == ["ec1", "ec2"]
    assert record["classification"] == "RECORDED"
    assert set(service.traversal.calls) == {cli.DISCRIMINATED_PREDICATE}


class _ClosureTraversal(_Traversal):
    def __init__(self, live):
        super().__init__()
        self.live = live

    def evidence_contract_definitions(self, elements):
        return "root", set(self.live), set(), {}


def test_discriminator_closure_member_swap_keeping_the_count_blocks():
    """R5: eight live definitions must be the eight validated bound members (by id)."""
    members = [{"element_id": f"ec{i}"} for i in range(8)]
    same = SimpleNamespace(traversal=_ClosureTraversal([f"ec{i}" for i in range(8)]))
    record = cli.discriminator_population(same, [], [], closure_members=members)
    assert record["closure_identity"]["result"] == "EQUAL"
    assert record["classification"] == "RECORDED"
    swapped = SimpleNamespace(traversal=_ClosureTraversal([f"ec{i}" for i in range(7)] + ["other"]))
    record = cli.discriminator_population(swapped, [], [], closure_members=members)
    assert record["closure_identity"] == {"result": "BLOCKING_MISMATCH", "live_only": ["other"],
                                          "bound_only": ["ec7"]}
    assert record["classification"] == "BLOCKING_MISMATCH"


def test_discriminator_errors_block():
    service = SimpleNamespace(traversal=_Traversal(raise_on={"s1"}))
    record = cli.discriminator_population(service, [{"@id": "s1"}], ["s1"])
    assert record["classification"] == "BLOCKING_MISMATCH"
    overall, problems = cli.answers_overall(answers()["answers"], record)
    assert overall == "FAILED" and problems


def test_answers_overall_passes_only_when_every_term_holds():
    good = answers()
    assert cli.answers_overall(good["answers"], good["discriminator"]) == ("PASSED", [])
    for bad in (answers(identity="BLOCKING_MISMATCH"), answers(k_pair="BLOCKING_MISMATCH"),
                answers(grounding="NOT_YET_COMPARABLE")):
        overall, problems = cli.answers_overall(bad["answers"], bad["discriminator"])
        assert overall == "FAILED" and problems


def test_compare_refuses_a_bundle_of_another_revision(tmp_path):
    model = write(tmp_path / "m.json", {"bundle_id": MAB, "git_revision": "e" * 40})
    binding = write(tmp_path / "b.json", {})
    with pytest.raises(SystemExit) as exc:
        cli.main(["compare", "--model", str(model), "--out", str(tmp_path),
                  "--api-url", "http://127.0.0.1:9", "--binding", str(binding),
                  "--export", str(binding), "--git-revision", REV])
    assert exc.value.code == 1


def test_compare_takes_no_o3_input(tmp_path):
    with pytest.raises(SystemExit) as exc:
        cli.main(["compare", "--model", "m", "--o3", "o3", "--out", str(tmp_path),
                  "--api-url", "u", "--binding", "b", "--export", "e", "--git-revision", REV])
    assert exc.value.code == 2


def test_compare_builds_model_runtime_without_eligibility_requirement(monkeypatch, tmp_path):
    """The candidate is evidenced before closure; entry points default to eligible."""
    seen = {}

    def fake_build_model_runtime(request, **kwargs):
        seen.update(kwargs, bundle_id=request.bundle_id)
        return "model", None

    monkeypatch.setattr(ea, "build_model_runtime", fake_build_model_runtime)
    args = SimpleNamespace(api_url="u", binding=tmp_path / "b")
    assert cli._build_model_service(args, REV, tmp_path / "m.json", MAB) == "model"
    assert seen["require_activation_eligible"] is False and seen["bundle_id"] == MAB
    assert "ontology_path" not in seen
