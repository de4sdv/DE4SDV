"""Synthetic execution is diagnostic; never native evaluation or adoption."""
from pathlib import Path
import json
import subprocess
import sys
import os

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_ple_scoped_execution.py"
EXPERIMENT = Path(os.environ.get("DE4SDV_PLE_ORACLE", "/tmp/de4sdv-pleml-gate-a"))


@pytest.fixture(autouse=True)
def require_configured_oracle():
    if "DE4SDV_PLE_ORACLE" in os.environ and (not os.environ["DE4SDV_PLE_ORACLE"] or not EXPERIMENT.is_dir()):
        pytest.fail("configured PLE oracle unavailable: " + os.environ["DE4SDV_PLE_ORACLE"])


def test_cli_executes_multiple_bindings_and_both_group_forms(tmp_path):
    assert SCRIPT.is_file(), "scoped executable probe CLI is missing"
    if not EXPERIMENT.is_dir():
        import pytest
        pytest.skip("optional exact-pin oracle checkout unavailable")
    result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--experiment", str(EXPERIMENT),
                             "--out", str(tmp_path / "probes")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "probes/receipt.json").read_text())
    assert report["mode"] == "synthetic"
    assert report["qualified"] is False
    assert report["fresh_serialization"] is False
    assert len(report["bindings"]) == 2
    assert {row["form"] for row in report["groups"]} == {"literal-bounds", "range-operator"}
    assert len(report["groups"]) == 6
    assert [row["status"] for row in report["groups"]].count("configuration-invalid") == 2
    assert report["native_xor"]["status"] == "unsupported"
    assert report["native_xor"]["requirement_status"] == "failed"
    assert (tmp_path / "probes/scoped-fixture.sysml").is_file()


def test_licensed_mode_requires_exact_executor_before_serializer(tmp_path):
    assert SCRIPT.is_file()
    result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--experiment", str(EXPERIMENT),
                             "--licensed", "--expected-executor", "bad-token", "--out", str(tmp_path / "licensed")],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "exact executor" in result.stderr
    assert not (tmp_path / "licensed").exists()


def runner():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_scoped_runner_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_licensed_workflow_calls_scoped_package_without_native_success_claim():
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/privileged-ple-qualification.yml").read_text())
    steps = workflow["jobs"]["qualify"]["steps"]
    step = next((s for s in steps if s.get("name") == "Execute missing scoped PLE probes"), None)
    assert step is not None, "scoped package not integrated in licensed workflow"
    assert "--licensed" in step["run"]
    assert '--expected-executor "$SELECTED_REVISION"' in step["run"]
    assert "RUNNER_TEMP" in step["run"]
    assert "SYSIDE_LICENSE_KEY" in step["env"]


def test_synthetic_probe_rejects_changed_range_operator():
    import pytest
    from scripts.run_ple_qualification import load_experiment
    if not EXPERIMENT.is_dir():
        pytest.skip("optional pinned oracle checkout unavailable")
    module, _, _ = load_experiment(EXPERIMENT)
    rows = runner().synthetic_graph("range-operator")
    next(r for r in rows if r["@id"] == "range")["operator"] = "+"
    with pytest.raises(ValueError, match="operator"):
        runner().probe_graph(module, rows, "range-operator", 2)


def test_binding_population_and_none_case_are_explicit(tmp_path):
    import pytest
    from scripts.run_ple_qualification import load_experiment
    if not EXPERIMENT.is_dir():
        pytest.skip("optional pinned oracle checkout unavailable")
    oracle, _, _ = load_experiment(EXPERIMENT)
    r = runner()
    rows = r.synthetic_graph("literal-bounds", 3)
    bindings, groups = r.probe_graph(oracle, rows, "literal-bounds", 3)
    assert len(bindings) == 3
    assert groups[1]["selected"] == ["member0", "member1", "member2"]
    assert groups[2]["status"] == "configuration-invalid"
    next(row for row in rows if row["@id"] == "binding1")["supplier"] = [{"@id": "member0"}]
    with pytest.raises(ValueError, match="binding endpoint"):
        r.probe_graph(oracle, rows, "literal-bounds", 3)


def test_native_reproducer_exits_two_and_preserves_flags(tmp_path):
    if not EXPERIMENT.is_dir():
        import pytest
        pytest.skip("optional pinned oracle checkout unavailable")
    result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--experiment", str(EXPERIMENT),
                             "--native-xor", "--out", str(tmp_path / "native")], capture_output=True, text=True)
    assert result.returncode == 2, result.stderr
    report = json.loads((tmp_path / "native/receipt.json").read_text())
    assert report["native_xor"]["native_expression_executed"] is False
    assert report["native_xor"]["defect_reproduced_natively"] is False
    assert report["adoption_authorized"] is False
    assert report["authority_activation_authorized"] is False
    assert "size(excluded) - 1" in report["native_xor"]["reason"]


def test_invalid_binding_counts_are_refused():
    import pytest
    for count in (1, 9, True):
        with pytest.raises(ValueError, match="binding count"):
            runner().synthetic_graph("literal-bounds", count)


# Synthetic API fakes below test orchestration ONLY, never Syside semantics or
# licensed execution. They call the real receipt path without importing Syside.
def synthetic_api_probe(monkeypatch, tmp_path, target_count=1, result=None, failure=None, require_lock=False):
    from contextlib import contextmanager
    from types import SimpleNamespace
    import platform
    r = runner()
    state = {"locked": False, "evaluations": 0}
    nodes = [SimpleNamespace(declared_name="nativeXorProbe", element_id="synthetic-target-" + str(n))
             for n in range(target_count)]
    rows = [{"@id": "synthetic-binding-0", "@type": "Dependency", "declaredName": "binding0"}]
    class Document:
        url = "file:///synthetic/scoped-fixture.sysml"
        root_node = object()
        @contextmanager
        def lock(self):
            state["locked"] = True
            try:
                yield self
            finally:
                state["locked"] = False
        def nodes(self, kind):
            assert state["locked"]
            return nodes
    class Compiler:
        def __init__(self, max_steps):
            assert max_steps == 10000
        def evaluate(self, target):
            state["evaluations"] += 1
            if require_lock:
                assert state["locked"], "synthetic evaluation escaped document lock"
            if callable(result):
                return result(state)
            if failure is not None:
                raise failure
            return result if result is not None else (None, SimpleNamespace(fatal=True, diagnostics=[]))
    fake = SimpleNamespace(
        try_load_model=lambda sources: (SimpleNamespace(user_docs=[Document()]),
            SimpleNamespace(contains_errors=lambda **kwargs: False)),
        json=SimpleNamespace(dumps=lambda *args: json.dumps(rows)),
        SerializationOptions=SimpleNamespace(minimal=lambda: None),
        ConstraintUsage=object(), Compiler=Compiler)
    real_import = r.importlib.import_module
    monkeypatch.setattr(r.importlib, "import_module", lambda name: fake if name == "syside" else real_import(name))
    monkeypatch.setattr(r.importlib.metadata, "version", lambda name: r.SERIALIZER_VERSION)
    monkeypatch.setattr(platform, "machine", lambda: "x86_64")
    args = SimpleNamespace(experiment=tmp_path, out=tmp_path, binding_count=1)
    report = {"representation": {}, "native_xor": {"status": "unsupported", "requirement_status": "failed",
              "native_expression_executed": False}, "execution_error": "", "qualified": False,
              "adoption_authorized": False, "authority_activation_authorized": False}
    r.licensed_probe(args, report)
    return report, state


def workflow_scoped_predicate(tmp_path, report):
    import yaml
    import os
    workflow = yaml.safe_load((ROOT / ".github/workflows/privileged-ple-qualification.yml").read_text())
    step = next(s for s in workflow["jobs"]["qualify"]["steps"]
                if s.get("name") == "Execute missing scoped PLE probes")
    code = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    output = tmp_path / "ple-evidence/scoped"
    output.mkdir(parents=True, exist_ok=True)
    (output / "receipt.json").write_text(json.dumps(report))
    (output / "cli-exit.txt").write_text("2\n")
    return subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path,
                          env=os.environ.copy(), capture_output=True, text=True)


def test_missing_or_ambiguous_native_target_is_execution_error(monkeypatch, tmp_path):
    for count in (0, 2):
        report, state = synthetic_api_probe(monkeypatch, tmp_path, target_count=count)
        assert report["native_xor"].get("attempted") is False
        assert report["execution_error"]
        assert report["native_xor"]["target_count"] == count
        assert len(report["native_xor"]["target_diagnostics"]) == count
        assert state["evaluations"] == 0


def test_workflow_rejects_no_attempt_and_accepts_attempted_refusal(tmp_path):
    receipt = {"execution_error": "", "fresh_serialization": True, "qualified": False,
               "native_xor": {"requirement_status": "failed", "attempted": False}}
    assert workflow_scoped_predicate(tmp_path, receipt).returncode != 0
    receipt["native_xor"]["attempted"] = True
    assert workflow_scoped_predicate(tmp_path, receipt).returncode == 0


def test_attempted_exception_retains_target_and_failed_requirement(monkeypatch, tmp_path):
    report, state = synthetic_api_probe(monkeypatch, tmp_path, failure=RuntimeError("synthetic unsupported"))
    native = report["native_xor"]
    assert native["attempted"] is True
    assert native["target_uuid"] == "synthetic-target-0"
    assert native["target_source"] == "file:///synthetic/scoped-fixture.sysml"
    assert "synthetic unsupported" in native["reason"]
    assert native["requirement_status"] == "failed"
    assert report["execution_error"] == ""
    assert state["evaluations"] == 1
    assert report["qualified"] is report["adoption_authorized"] is report["authority_activation_authorized"] is False



def test_compiler_entries_retained_with_fatal_separate(monkeypatch, tmp_path):
    from types import SimpleNamespace
    class OpaqueReport:
        fatal = True
        diagnostics = [SimpleNamespace(message="synthetic unsupported body", code="synthetic-code",
            severity="Error", source="synthetic compiler", segment=SimpleNamespace(offset=17, end=23))]
        def __str__(self):
            return "opaque report; not emitted diagnostics"
    report, _ = synthetic_api_probe(monkeypatch, tmp_path, result=(None, OpaqueReport()))
    native = report["native_xor"]
    assert native["compiler_diagnostics"] == [{"message": "synthetic unsupported body",
        "code": "synthetic-code", "severity": "Error", "source": "synthetic compiler",
        "segment": {"offset": 17, "end": 23}}]
    assert native["compiler_fatal"] is True
    assert "synthetic unsupported body" in native["reason"]
    assert "opaque report" not in native["reason"]
    assert native["attempted"] is True
    assert native["requirement_status"] == "failed"
    assert native["native_expression_executed"] is False
    assert report["qualified"] is False


def test_evaluation_and_exception_materialization_hold_document_lock(monkeypatch, tmp_path):
    report, state = synthetic_api_probe(monkeypatch, tmp_path, require_lock=True,
        failure=RuntimeError("synthetic refusal under lock"))
    assert report["native_xor"]["attempted"] is True
    assert "synthetic refusal under lock" in report["native_xor"]["reason"]
    assert state["locked"] is False


def test_value_and_diagnostic_materialization_hold_document_lock(monkeypatch, tmp_path):
    def protected_result(state):
        class ProtectedValue:
            def __repr__(self):
                assert state["locked"], "synthetic value repr escaped document lock"
                return "synthetic unqualified value"
        class ProtectedDiagnostic:
            @property
            def message(self):
                assert state["locked"], "synthetic diagnostic escaped document lock"
                return "synthetic diagnostic under lock"
        class ProtectedReport:
            @property
            def diagnostics(self):
                assert state["locked"], "synthetic report escaped document lock"
                return [ProtectedDiagnostic()]
            @property
            def fatal(self):
                assert state["locked"], "synthetic fatal escaped document lock"
                return False
        return ProtectedValue(), ProtectedReport()
    report, state = synthetic_api_probe(monkeypatch, tmp_path, result=protected_result)
    native = report["native_xor"]
    assert native["returned_value_repr"] == "synthetic unqualified value"
    assert native["compiler_diagnostics"] == [{"message": "synthetic diagnostic under lock"}]
    assert native["compiler_fatal"] is False
    assert native["status"] == "native-result-unqualified"
    assert native["requirement_status"] == "failed"
    assert report["qualified"] is report["adoption_authorized"] is report["authority_activation_authorized"] is False
    assert state["locked"] is False


def test_configured_missing_oracle_fails_instead_of_skipping(tmp_path):
    import os
    environment = dict(os.environ, DE4SDV_PLE_ORACLE=str(tmp_path / "missing-oracle"))
    result = subprocess.run([sys.executable, "-B", "-m", "pytest", str(Path(__file__)),
        "-k", "cli_executes_multiple_bindings", "-q"], cwd=ROOT,
        env=environment, capture_output=True, text=True)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "configured PLE oracle unavailable" in result.stdout + result.stderr


def test_workflow_wires_existing_frozen_checkout_to_oracle_tests():
    import yaml
    workflow = yaml.safe_load((ROOT / ".github/workflows/privileged-ple-qualification.yml").read_text())
    step = next(s for s in workflow["jobs"]["qualify"]["steps"]
                if s.get("name") == "Execute missing scoped PLE probes")
    assert step["env"]["DE4SDV_PLE_ORACLE"] == "${{ github.workspace }}/_ple-experiment"
