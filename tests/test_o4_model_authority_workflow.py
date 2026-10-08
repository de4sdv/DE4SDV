"""O4 privileged-run wiring, Wave C2 form (static + argument-spy; no network, no dispatch).

The model-authority steps run in a separate job of the privileged ingestion
workflow. These tests pin the job topology, the exact-revision inputs, the
artifact naming boundary with the deploy/core-evidence consumers, the
gate/measurement exit policy, and that every workflow command line parses
against the REAL script parser (the parser is spied; nothing executes).
"""
from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
JOB = "model-authority-evidence"
REV = "a" * 40


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job(name=JOB):
    return _workflow()["jobs"][name]


def _step(name, job=JOB):
    matches = [s for s in _job(job)["steps"] if s.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _names(job=JOB):
    return [s.get("name") for s in _job(job)["steps"]]


READBACK = "Decision-13 read-back of the implied verification anchors (restored same-run API snapshot)"
DELTA = "Measure the Wave A Requirement-population delta"
BUNDLE = "Rebuild the candidate model-authority bundle (must equal the batteries' bundle)"
INGEST_BUNDLE = "Build candidate model-authority bundle"
COVERAGE = "Model-projection coverage report against the candidate bundle"
COMPARE = "Model runtime answers over the migrated identity set (EvidenceContract discriminator, K pair)"
BATTERIES = ("Exercise three production semantic concerns",
             "Validate governed product-line scope through API identity",
             "Exercise read-only semantic MCP tools")
CLOSE = "Close the model-authority bundle (activation eligibility)"
UPLOAD = "Upload model-authority evidence"


def test_separate_job_after_ingestion_keeps_both_budgets():
    job = _job()
    assert job["needs"] == "ingest-and-validate"
    assert "needs.ingest-and-validate.result == 'success'" in job["if"]
    assert "workflow_dispatch" in job["if"]
    assert job["timeout-minutes"] <= 360
    assert _job("ingest-and-validate")["timeout-minutes"] <= 360
    # The ingestion job builds the candidate bundle (no API) and runs the three
    # batteries under it; read-back, answers and close stay in the model job.
    ingest = _names("ingest-and-validate")
    for name in (READBACK, DELTA, BUNDLE, COMPARE, CLOSE):
        assert name not in ingest
    assert ingest.index(INGEST_BUNDLE) < min(ingest.index(name) for name in BATTERIES)


def test_batteries_run_under_the_candidate_bundle_explicitly():
    for name in BATTERIES:
        run = _step(name, "ingest-and-validate")["run"]
        for token in ("--semantic-authority model",
                      "--model-authority-bundle /tmp/o4/de4sdv-model-authority-candidate-bundle.json",
                      '--model-authority-bundle-id "$(cat /tmp/o4/candidate-bundle-id)"',
                      "--allow-candidate-bundle"):
            assert token in run, (name, token)


def test_no_o3_or_legacy_step_remains():
    text = WORKFLOW.read_text(encoding="utf-8")
    for token in ("run_o3_equivalence", "/tmp/o3/", "--ontology", "--o3-", "de4sdv-basic-ontology",
                  "semantic-authority o3", "semantic-authority legacy"):
        assert token not in text, token


def test_model_job_does_not_turn_the_ingestion_run_red():
    # deploy-public-sysml-api / method-core evidence require a successful run.
    assert _job()["continue-on-error"] is True


def test_model_job_needs_no_licence_secret():
    text = yaml.safe_dump(_job())
    assert "secrets." not in text


def test_snapshot_artifact_never_matches_the_ingestion_artifact_prefix():
    ingest = _job("ingest-and-validate")["steps"]
    names = [s.get("with", {}).get("name", "") for s in ingest if "upload-artifact" in str(s.get("uses"))]
    names += [s.get("with", {}).get("name", "") for s in _job()["steps"]
              if "upload-artifact" in str(s.get("uses"))]
    prefixed = [n for n in names if n.startswith("full-model-api-ingestion-")]
    assert prefixed == ["full-model-api-ingestion-${{ github.sha }}"]


def test_snapshot_is_taken_after_the_ingestion_tests():
    ingest = _names("ingest-and-validate")
    assert ingest.index("Run production-ingestion tests") < ingest.index(
        "Snapshot API database for the model-authority job")


def test_restored_inputs_are_revision_checked_before_use():
    names = _names()
    assert names.index("Verify inputs are bound to the checked-out revision") < names.index(
        "Restore API database snapshot") < names.index(READBACK)
    run = _step("Verify inputs are bound to the checked-out revision")["run"]
    assert "sha256sum -c" in run
    for path in ("de4sdv-full-model-export.json", "de4sdv-full-model-binding.json",
                 "o4/de4sdv-model-authority-candidate-bundle.json"):
        assert path in run


def test_step_order_and_gate_policy():
    names = _names()
    order = [READBACK, DELTA, BUNDLE, COVERAGE, COMPARE, CLOSE, UPLOAD]
    assert [names.index(n) for n in order] == sorted(names.index(n) for n in order)
    assert _step(READBACK).get("if") is None  # never skipped
    for name in (DELTA, BUNDLE, COVERAGE, COMPARE, CLOSE):
        assert _step(name)["if"] == "${{ !cancelled() && steps.restore-proof.outcome == 'success' }}"
    assert _step(UPLOAD)["if"] == "always()"
    # The delta tolerates ONLY exit 2 (measured difference); errors still fail.
    delta = _step(DELTA)["run"]
    assert 'if [ "$rc" = "2" ]' in delta and 'exit "$rc"' in delta
    for name in (READBACK, COMPARE, CLOSE):
        assert "set +e" not in _step(name)["run"]
    # The rebuilt candidate must be the bundle the batteries ran under.
    rebuild = _step(BUNDLE)["run"]
    assert 'expected="$(cat /tmp/o4/candidate-bundle-id)"' in rebuild
    assert '[ "$rebuilt" != "$expected" ]' in rebuild and "exit 1" in rebuild


def _commands(job=JOB):
    out = []
    for step in _job(job)["steps"]:
        run = step.get("run") or ""
        joined = re.sub(r"\\\n\s*", " ", run)
        for line in joined.splitlines():
            line = line.strip()
            # Workflow-revision helpers run from /tmp/de4sdv-ci (see
            # test_ci_helpers_come_from_the_workflow_revision); parse them as
            # the repository scripts they were materialized from.
            line = re.sub(r"^(python3?) /tmp/de4sdv-ci/", r"\1 scripts/", line)
            if line.startswith(("python scripts/", "python3 scripts/")):
                line = re.sub(r'"\$\(git rev-parse HEAD\)"', REV, line)
                line = re.sub(r'"\$\(cat /tmp/o4/candidate-bundle-id\)"', "mab-" + "b" * 32, line)
                out.append((step["name"], shlex.split(line)))
    return out


class _Parsed(Exception):
    pass


@pytest.mark.parametrize("name, argv", _commands(), ids=[c[0] for c in _commands()])
def test_workflow_command_lines_parse_with_the_real_parsers(monkeypatch, name, argv):
    import importlib

    script = argv[1]
    if not (ROOT / script).is_file():
        # B2's coverage CLI lands in the integrated PR; this guard is removed
        # by the controller's integration check (it must then parse too).
        pytest.skip(f"{script} is provided by a sibling implementer")
    module = importlib.import_module("scripts." + Path(script).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    with pytest.raises(_Parsed):
        module.main(argv[2:])
    namespace = vars(captured["namespace"])
    for key in ("git_revision", "source_revision"):
        if key in namespace:
            assert namespace[key] == REV


_INGEST_SCRIPTS = ("run_model_authority_bundle.py", "validate_full_model_semantic_queries.py",
                   "validate_product_line_scope_api.py", "validate_semantic_mcp.py",
                   "import_sysml_api_baseline.py", "probe_definition_migration.py")
_INGEST = [c for c in _commands("ingest-and-validate") if Path(c[1][1]).name in _INGEST_SCRIPTS]


@pytest.mark.parametrize("name, argv", _INGEST, ids=[c[0] for c in _INGEST])
def test_ingest_command_lines_parse_with_the_real_parsers(monkeypatch, name, argv):
    import importlib
    import inspect
    import sys

    argv = argv[:argv.index(">")] if ">" in argv else argv
    module = importlib.import_module("scripts." + Path(argv[1]).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    monkeypatch.setattr(sys, "argv", argv[1:])
    with pytest.raises(_Parsed):
        if inspect.signature(module.main).parameters:
            module.main(argv[2:])
        else:
            module.main()
    namespace = vars(captured["namespace"])
    for key in ("git_revision", "source_revision", "expected_git_revision"):
        if key in namespace:
            assert namespace[key] == REV


def test_every_model_output_is_uploaded_and_close_reads_produced_files():
    produced = set()
    for _, argv in _commands():
        for flag in ("--output", "--json"):
            if flag in argv:
                produced.add(argv[argv.index(flag) + 1])
    produced |= {"/tmp/o4/de4sdv-model-authority-candidate-bundle.json",
                 "/tmp/o4/de4sdv-model-authority-answers.json"}
    close = dict(zip(*[iter(next(a for n, a in _commands() if n == CLOSE)[3:])] * 2))
    from_job1 = {"/tmp/de4sdv-full-model-binding.json",
                 "/tmp/o4/de4sdv-o4-definition-migration-probe.json",
                 "/tmp/de4sdv-full-model-semantic-query-coverage.json",
                 "/tmp/de4sdv-product-line-scope-validation.json",
                 "/tmp/de4sdv-semantic-mcp-validation.json",
                 "/tmp/o4/de4sdv-model-authority-candidate-bundle.json",
                 "/tmp/o4/candidate-bundle-id"}
    for flag in ("--model", "--coverage", "--answers", "--readback"):
        assert close[flag] in produced, flag
    for flag in ("--binding", "--definition-probe", "--full-model-semantic-queries",
                 "--product-line-scope", "--semantic-mcp"):
        assert close[flag] in from_job1, flag
    ingest_produced = set()
    for _, argv in _commands("ingest-and-validate"):
        if "--output" in argv:
            ingest_produced.add(argv[argv.index("--output") + 1])
    for flag in ("--full-model-semantic-queries", "--product-line-scope", "--semantic-mcp"):
        assert close[flag] in ingest_produced, flag
    ingest_upload = _step("Upload exact-head ingestion evidence", "ingest-and-validate")
    for path in from_job1:
        assert path in ingest_upload["with"]["path"]
    uploaded = _step(UPLOAD)["with"]["path"]
    from scripts import run_model_authority_bundle as cli

    for path in produced | {f"/tmp/o4/{cli.CLOSED_BUNDLE}", f"/tmp/o4/{cli.ATTESTATION}",
                            f"/tmp/o4/{cli.ELIGIBILITY}"}:
        assert path in uploaded, path


SNAPSHOT = "Snapshot API database for the model-authority job"
SNAPSHOT_UPLOAD = "Upload API database snapshot for the model-authority job"
SNAPSHOT_DOWNLOAD = "Download same-run API database snapshot"
SNAPSHOT_REQUIRED = "Require the same-run API database snapshot"


def test_snapshot_steps_are_off_the_ingestion_critical_path():
    """R4: a snapshot/upload failure never fails ingest-and-validate; scheduled runs skip it."""
    for name in (SNAPSHOT, SNAPSHOT_UPLOAD):
        step = _step(name, "ingest-and-validate")
        assert step["if"] == "github.event_name == 'workflow_dispatch'", name
        assert step["continue-on-error"] is True, name


def test_missing_snapshot_fails_the_model_job_clearly():
    names = _names()
    download = _step(SNAPSHOT_DOWNLOAD)
    assert download["continue-on-error"] is True
    required = _step(SNAPSHOT_REQUIRED)
    assert names.index(SNAPSHOT_DOWNLOAD) < names.index(SNAPSHOT_REQUIRED) < names.index(
        "Verify inputs are bound to the checked-out revision")
    assert required.get("if") is None and required.get("continue-on-error") is None
    run = required["run"]
    assert "::error" in run and "model-authority-api-db-" in run and "exit 1" in run
    for path in ("/tmp/o4-db/sysml2.dump", "/tmp/o4-db/sysml2.dump.sha256"):
        assert path in run



# --- Schema preservation, restore proof, reuse mode (run 37677500924 fix) ---

import subprocess  # noqa: E402

BUILD = "Build pinned Systems Modeling API service"
START = "Start pinned Systems Modeling API service on the restored database"
PROOF = "Prove the restored API serves the export corpus"
REUSE_VERIFY = "Verify the reused ingestion run (reuse mode)"
REUSE_INGESTION_DOWNLOAD = "Download reused-run ingestion evidence (reuse mode)"
REUSE_SNAPSHOT_DOWNLOAD = "Download reused-run API database snapshot (reuse mode)"
SAME_RUN_DOWNLOAD = "Download same-run ingestion evidence"
VERIFY_INPUTS = "Verify inputs are bound to the checked-out revision"
REUSE_SET = "github.event.inputs.reuse_ingestion_run != ''"
REUSE_EMPTY = "github.event.inputs.reuse_ingestion_run == ''"
CREATE_DROP = 'hibernate.hbm2ddl.auto" value="create-drop"'
PATCH_BEGIN = "# >>> schema-preservation patch"
PATCH_END = "# <<< schema-preservation patch"


def _patch_block():
    run = _step(BUILD)["run"]
    assert run.count(PATCH_BEGIN) == 1 and run.count(PATCH_END) == 1
    return run.split(PATCH_BEGIN, 1)[1].split(PATCH_END, 1)[0]


def test_persistence_patch_is_in_the_model_job_before_staging():
    run = _step(BUILD)["run"]
    checkout = run.index("checkout 0af711b14bbcea7b240bb0a3a65817ae68302092")
    assert checkout < run.index(PATCH_BEGIN) < run.index(PATCH_END) < run.index("sbt-launch.jar stage")
    block = _patch_block()
    assert "conf/META-INF/persistence.xml" in block
    assert f"grep -q '{CREATE_DROP}'" in block  # guard before the edit
    assert block.index(f"grep -q '{CREATE_DROP}'") < block.index("sed -i")
    assert "grep -q 'create-drop'" in block  # nothing left after the edit
    assert block.count("::error::") >= 2 and block.count("exit 1") >= 2


def test_ingestion_job_keeps_create_drop_on_its_empty_database():
    ingest = yaml.safe_dump(_job("ingest-and-validate"))
    assert "persistence.xml" not in ingest and "hbm2ddl" not in ingest
    assert "schema-preservation" not in ingest


def _run_patch(tmp_path, content):
    conf = tmp_path / "conf/META-INF/persistence.xml"
    conf.parent.mkdir(parents=True)
    conf.write_text(content, encoding="utf-8")
    script = _patch_block().replace("/tmp/sysmlv2-api-services", str(tmp_path))
    result = subprocess.run(["bash", "-e", "-c", script], capture_output=True, text=True)
    return result, conf.read_text(encoding="utf-8")


UPSTREAM_LINE = '            <property name="hibernate.hbm2ddl.auto" value="create-drop"/>\n'


def test_patch_turns_create_drop_into_update(tmp_path):
    result, patched = _run_patch(tmp_path, "<x>\n" + UPSTREAM_LINE + "</x>\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'hibernate.hbm2ddl.auto" value="update"' in patched
    assert "create-drop" not in patched


def test_patch_fails_loudly_when_the_expected_line_is_absent(tmp_path):
    result, _ = _run_patch(tmp_path, '<property name="hibernate.hbm2ddl.auto" value="validate"/>\n')
    assert result.returncode != 0
    assert "::error::" in result.stdout


def test_patch_fails_loudly_when_create_drop_remains(tmp_path):
    result, _ = _run_patch(tmp_path, UPSTREAM_LINE + '<property name="x" value="create-drop"/>\n')
    assert result.returncode != 0
    assert "::error::" in result.stdout


def test_restore_proof_runs_right_after_api_start_and_before_every_evidence_step():
    names = _names()
    assert names.index(START) + 1 == names.index(PROOF)
    assert names.index(PROOF) < names.index(READBACK)
    proof = _step(PROOF)
    assert proof.get("if") is None and proof.get("continue-on-error") is None
    assert proof["id"] == "restore-proof"
    run = proof["run"]
    for path in ("/tmp/de4sdv-full-model-binding.json", "/tmp/de4sdv-full-model-export.json",
                 "/tmp/de4sdv-full-model-semantic-validation.json"):
        assert path in run
    assert "/tmp/o4/de4sdv-o4-restored-corpus-proof.json" in _step(UPLOAD)["with"]["path"]
    # A refused proof stops the evidence steps; they never read an unproven API.
    for name in (DELTA, BUNDLE, COVERAGE, COMPARE, CLOSE):
        assert "steps.restore-proof.outcome == 'success'" in _step(name)["if"], name


def test_reuse_input_is_an_optional_dispatch_string():
    inputs = _workflow()[True]["workflow_dispatch"]["inputs"]  # yaml 'on' -> True
    reuse = inputs["reuse_ingestion_run"]
    assert reuse["type"] == "string" and reuse["required"] is False
    assert reuse.get("default", "") == ""


def test_reuse_mode_skips_ingestion_and_runs_the_model_job():
    assert "!github.event.inputs.reuse_ingestion_run" in _job("ingest-and-validate")["if"]
    cond = " ".join(_job()["if"].split())
    assert cond.startswith("!cancelled() &&")
    assert "needs.ingest-and-validate.result == 'success'" in cond
    assert f"({REUSE_SET} && needs.ingest-and-validate.result == 'skipped')" in cond


def test_only_the_model_job_gains_actions_read():
    assert _workflow()["permissions"] == {"contents": "read"}
    assert "permissions" not in _job("ingest-and-validate")
    assert _job()["permissions"] == {"contents": "read", "actions": "read"}


def test_reuse_preconditions_are_verified_before_anything_else():
    names = _names()
    step = _step(REUSE_VERIFY)
    assert step["if"] == REUSE_SET and step["id"] == "reuse"
    # Only the workflow-revision helper materialization sits in between.
    assert names.index("Validate exact-revision checkout") + 2 == names.index(REUSE_VERIFY)
    assert names[names.index(REUSE_VERIFY) - 1] == "Materialize workflow-revision CI helpers"
    for later in ("Install Sysand and pinned model dependencies", SAME_RUN_DOWNLOAD,
                  REUSE_INGESTION_DOWNLOAD, REUSE_SNAPSHOT_DOWNLOAD, VERIFY_INPUTS):
        assert names.index(REUSE_VERIFY) < names.index(later), later
    run = re.sub(r"\\\n\s*", " ", step["run"])
    assert "python3 /tmp/de4sdv-ci/verify_reuse_ingestion_run.py" in run
    assert '--ref "${{ github.event.inputs.ref }}"' in run
    assert '--run-id "${{ github.event.inputs.reuse_ingestion_run }}"' in run
    assert "/tmp/o4/de4sdv-o4-ingestion-source.json" in run
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"


def test_reuse_downloads_bind_to_the_verified_artifacts_never_github_sha():
    for name, output in ((REUSE_INGESTION_DOWNLOAD, "ingestion_artifact_id"),
                         (REUSE_SNAPSHOT_DOWNLOAD, "snapshot_artifact_id")):
        step = _step(name)
        assert step["if"] == REUSE_SET
        assert "download-artifact@v4" in step["uses"]
        assert step["with"]["artifact-ids"] == "${{ steps.reuse.outputs.%s }}" % output
        assert step["with"]["run-id"] == "${{ github.event.inputs.reuse_ingestion_run }}"
        assert step["with"]["github-token"] == "${{ github.token }}"
        assert step["with"]["merge-multiple"] is True
        assert "github.sha" not in yaml.safe_dump(step)
    assert _step(REUSE_INGESTION_DOWNLOAD)["with"]["path"] == "/tmp"
    assert _step(REUSE_SNAPSHOT_DOWNLOAD)["with"]["path"] == "/tmp/o4-db"
    assert _step(REUSE_SNAPSHOT_DOWNLOAD)["continue-on-error"] is True


def test_normal_mode_downloads_are_unchanged():
    assert _step(SAME_RUN_DOWNLOAD) == {
        "name": SAME_RUN_DOWNLOAD, "if": REUSE_EMPTY,
        "uses": "actions/download-artifact@v4",
        "with": {"name": "full-model-api-ingestion-${{ github.sha }}", "path": "/tmp"}}
    assert _step(SNAPSHOT_DOWNLOAD) == {
        "name": SNAPSHOT_DOWNLOAD, "if": REUSE_EMPTY, "continue-on-error": True,
        "uses": "actions/download-artifact@v4",
        "with": {"name": "model-authority-api-db-${{ github.sha }}", "path": "/tmp/o4-db"}}


def test_mode_guards_touch_only_the_mode_specific_steps():
    reuse_only = {REUSE_VERIFY, REUSE_INGESTION_DOWNLOAD, REUSE_SNAPSHOT_DOWNLOAD}
    normal_only = {SAME_RUN_DOWNLOAD, SNAPSHOT_DOWNLOAD}
    for step in _job()["steps"]:
        guard = str(step.get("if", ""))
        name = step.get("name")
        if name in reuse_only:
            assert guard == REUSE_SET, name
        elif name in normal_only:
            assert guard == REUSE_EMPTY, name
        else:
            assert "reuse_ingestion_run" not in guard, name
    # Content binding still runs in both modes, after every download.
    names = _names()
    verify = _step(VERIFY_INPUTS)
    assert verify.get("if") is None
    for download in reuse_only | normal_only | {SNAPSHOT_REQUIRED}:
        assert names.index(download) < names.index(VERIFY_INPUTS), download


def test_evidence_names_follow_the_ref_in_reuse_mode():
    selector = "github.event.inputs.reuse_ingestion_run != '' && github.event.inputs.ref || github.sha"
    assert _step(UPLOAD)["with"]["name"] == "model-authority-evidence-${{ %s }}" % selector
    assert "model-authority-api-db-${{ %s }}" % selector in _step(SNAPSHOT_REQUIRED)["run"]
    assert "/tmp/o4/de4sdv-o4-ingestion-source.json" in _step(UPLOAD)["with"]["path"]


MATERIALIZE = "Materialize workflow-revision CI helpers"


def test_ci_helpers_come_from_the_workflow_revision():
    """A reuse dispatch checks out an OLDER ref (e.g. ff0311b) that predates
    the helpers; they must come from the workflow's own revision."""
    names = _names()
    step = _step(MATERIALIZE)
    assert step.get("if") is None
    assert names.index("Validate exact-revision checkout") < names.index(MATERIALIZE) < names.index(
        REUSE_VERIFY)
    run = step["run"]
    assert 'git show "${{ github.sha }}:scripts/$helper"' in run
    assert "inputs.ref" not in run
    used = set()
    for other in _job()["steps"]:
        used |= set(re.findall(r"/tmp/de4sdv-ci/([A-Za-z0-9_]+\.py)", other.get("run") or ""))
    assert used == {"verify_reuse_ingestion_run.py", "verify_restored_api_corpus.py"}
    for helper in used:
        assert helper in run and (ROOT / "scripts" / helper).is_file()
        assert f"python scripts/{helper}" not in yaml.safe_dump(_job())
        assert f"python3 scripts/{helper}" not in yaml.safe_dump(_job())
    # The restore proof imports de4sdv from the evidence checkout.
    assert "PYTHONPATH" in _step(PROOF).get("env", {})
    assert names.index(MATERIALIZE) < names.index(PROOF)



def test_materialized_helpers_run_outside_the_checkout(tmp_path):
    """Run copies the way the workflow does: from /tmp/de4sdv-ci-like dirs."""
    import shutil
    import sys

    for helper in ("verify_reuse_ingestion_run.py", "verify_restored_api_corpus.py"):
        shutil.copy(ROOT / "scripts" / helper, tmp_path / helper)
    env = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(ROOT)}
    proof = subprocess.run(
        [sys.executable, str(tmp_path / "verify_restored_api_corpus.py"),
         "--api-url", "http://127.0.0.1:9", "--binding", str(tmp_path / "missing.json"),
         "--export", str(tmp_path / "missing.json"), "--output", str(tmp_path / "o.json")],
        capture_output=True, text=True, env=env, cwd=tmp_path)
    # de4sdv resolved from PYTHONPATH; it fails on the missing binding, not an import.
    assert proof.returncode != 0
    assert "ModuleNotFoundError" not in proof.stderr and "FileNotFoundError" in proof.stderr
    reuse = subprocess.run([sys.executable, "-I", str(tmp_path / "verify_reuse_ingestion_run.py"),
                            "--help"], capture_output=True, text=True, cwd=tmp_path)
    assert reuse.returncode == 0, reuse.stderr  # stdlib only, isolated mode
