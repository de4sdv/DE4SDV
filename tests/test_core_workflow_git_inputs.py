"""Execute the Core workflow's declared-tested Git prerequisite."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import yaml
import pytest

from de4sdv.semantic import method_pilot as mp
from de4sdv.semantic import operational_exit as oe

ROOT = Path(__file__).resolve().parents[1]
STEP = "Make declared tested Git input available without changing scope"


def _step_script() -> str:
    steps = yaml.safe_load(
        (ROOT / ".github/workflows/method-core-operational-evidence.yml").read_text()
    )["jobs"]["observe"]["steps"]
    matches = [step for step in steps if step.get("name") == STEP]
    assert len(matches) == 1, "Core replay is missing its declared-tested Git prerequisite"
    assert steps.index(matches[0]) < next(
        i for i, step in enumerate(steps)
        if step.get("name") == "Exercise fresh-process parity, offline replay and refusal matrix"
    )
    return matches[0]["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def _git(directory: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(directory), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def test_main_only_clone_fetches_exact_declared_tested_object(tmp_path, monkeypatch):
    script = _step_script()
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-b", "main")
    author = ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid")
    _git(origin, *author, "commit", "--allow-empty", "-m", "candidate")
    candidate = _git(origin, "rev-parse", "HEAD")
    _git(origin, "checkout", "--orphan", "historical-execution")
    _git(origin, *author, "commit", "--allow-empty", "-m", "declared tested execution")
    tested = _git(origin, "rev-parse", "HEAD")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "--no-local", "--single-branch", "--branch", "main",
         str(origin), str(clone)], check=True, capture_output=True,
    )
    probe = subprocess.run(
        ["git", "-C", str(clone), "cat-file", "-e", tested + "^{commit}"],
        capture_output=True,
    )
    assert probe.returncode != 0, "fixture must reproduce CI's absent tested Git object"
    retained = tmp_path / "runner temp" / "retained-ingestion"
    retained.mkdir(parents=True)
    (retained / "de4sdv-candidate-export.json").write_text(json.dumps({"elements": []}))
    evidence = tmp_path / "runner temp" / "core-evidence"
    evidence.mkdir()
    monkeypatch.chdir(clone)
    monkeypatch.setenv("SELECTED_REVISION", candidate)
    monkeypatch.setenv("GITHUB_REPOSITORY", "fixture/repository")
    monkeypatch.setenv("RETAINED_ARTIFACT_DIR", str(retained))
    monkeypatch.setenv("CORE_EVIDENCE_DIR", str(evidence))

    def validate_artifacts(path):
        assert path == retained
        return SimpleNamespace(directory=retained, git_commit=candidate)

    monkeypatch.setattr(oe, "validate_ingestion_artifacts", validate_artifacts)
    monkeypatch.setattr(mp, "decode_declared_tested_scope", lambda elements: ({"@id": "scope"}, [], []))
    monkeypatch.setattr(mp, "_member_text_value", lambda *args: (None, tested))
    exec(compile(script, "<Core declared-tested prerequisite>", "exec"), {})
    assert _git(clone, "rev-parse", "HEAD") == candidate
    _git(clone, "cat-file", "-e", tested + "^{commit}")
    record = json.loads((evidence / "tested-git-input.json").read_text())
    assert record["candidate_git_commit"] == candidate
    assert record["tested_git_commit"] == tested
    assert record["role"] == "declared-tested-execution-input"
    assert record["permanent_executor_provenance"] is False
    assert _git(clone, "status", "--porcelain") == ""


@pytest.mark.parametrize("tested", [None, "", "B" * 40, "b" * 39, "b" * 41,
                                   "b" * 40 + " ", "b" * 40 + "\n"])
def test_invalid_declared_sha_refuses_before_git_fetch(tmp_path, monkeypatch, tested):
    script = _step_script()
    candidate = "a" * 40
    retained = tmp_path / "retained-ingestion"
    retained.mkdir()
    (retained / "de4sdv-candidate-export.json").write_text(json.dumps({"elements": []}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SELECTED_REVISION", candidate)
    monkeypatch.setenv("RETAINED_ARTIFACT_DIR", str(retained))
    monkeypatch.setattr(oe, "validate_ingestion_artifacts", lambda path: SimpleNamespace(
        directory=retained, git_commit=candidate,
    ))
    monkeypatch.setattr(mp, "decode_declared_tested_scope", lambda elements: ({"@id": "scope"}, [], []))
    monkeypatch.setattr(mp, "_member_text_value", lambda *args: (None, tested))
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: candidate + "\n")

    def unexpected_git(*args, **kwargs):
        pytest.fail("invalid scope must refuse before object lookup or network fetch")

    monkeypatch.setattr(subprocess, "run", unexpected_git)
    with pytest.raises(SystemExit, match="declared tested Git input is not an exact SHA"):
        exec(compile(script, "<Core declared-tested prerequisite>", "exec"), {})
