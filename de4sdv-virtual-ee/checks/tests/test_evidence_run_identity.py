"""R8: a run is bound to the committed bytes that executed it.

checks/run_identity.py records the full Git head and tree, rejects a dirty or
gitless scope, inventories every tracked runtime input by content, names the
harness/config/lock digests, and re-verifies all of it after the run. The
historical archives are checked read-only and must be labelled, not accepted.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1]
SCOPE_SRC = CHECKS.parent
HELPER = CHECKS / "run_identity.py"
PY = "/usr/bin/python3"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env=env).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def repo(tmp_path) -> Path:
    """A committed checkout holding the real de4sdv-virtual-ee tree (no results)."""
    top = tmp_path / "repo"
    top.mkdir()
    shutil.copytree(SCOPE_SRC, top / "de4sdv-virtual-ee",
                    ignore=shutil.ignore_patterns("results", "__pycache__", ".pytest_cache"))
    (top / "README.md").write_text("root\n")
    (top / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.env\n")
    git(top, "init", "-q", "-b", "main")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "fixture")
    return top


def helper(*args: str, cwd: Path | None = None):
    return subprocess.run([PY, str(HELPER), *args], capture_output=True, text=True, timeout=120,
                          cwd=cwd, env={**os.environ, **GIT_ENV})


def capture(repo: Path, out: Path, *extra: str):
    return helper("capture", "--scope", str(repo / "de4sdv-virtual-ee"), "--out", str(out), *extra)


def test_capture_records_the_full_committed_identity(repo, tmp_path):
    out = tmp_path / "id.json"
    proc = capture(repo, out)
    assert proc.returncode == 0, proc.stderr
    ident = json.loads(out.read_text())
    assert ident["git"]["head"] == git(repo, "rev-parse", "HEAD") and len(ident["git"]["head"]) == 40
    assert ident["git"]["tree"] == git(repo, "rev-parse", "HEAD^{tree}")
    assert ident["git"]["scope_tree"] == git(repo, "rev-parse", "HEAD:de4sdv-virtual-ee")
    assert ident["scope"] == "de4sdv-virtual-ee" and ident["clean"] is True
    inv = {e["path"]: e for e in ident["inventory"]}
    scope = repo / "de4sdv-virtual-ee"
    assert inv["checks/run_demo.sh"]["sha256"] == sha256(scope / "checks/run_demo.sh")
    assert inv["checks/run_demo.sh"]["git_blob"] == git(repo, "rev-parse", "HEAD:de4sdv-virtual-ee/checks/run_demo.sh")
    assert not any(p.startswith("results/") for p in inv)
    assert ident["named"]["lock"]["vehicle/vxp.lock"] == sha256(scope / "vehicle/vxp.lock")
    for path in ("checks/run_demo.sh", "checks/run_backbone.sh", "checks/demo_measure.py",
                 "checks/backbone_measure.py", "checks/measure_client.py", "checks/run_identity.py"):
        assert ident["named"]["harness"][path] == sha256(scope / path)
    for path in ("vehicle/vehicle.yaml", "vehicle/parts.yaml", "vehicle/vxp.yaml"):
        assert ident["named"]["config"][path] == sha256(scope / path)
    listing = "".join(f"{e['path']}\0{e['sha256']}\n" for e in sorted(ident["inventory"], key=lambda e: e["path"]))
    assert ident["inventory_sha256"] == hashlib.sha256(listing.encode()).hexdigest()


def test_a_modified_tracked_input_is_rejected(repo, tmp_path):
    (repo / "de4sdv-virtual-ee/vehicle/parts.yaml").write_text("# edited\n")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode != 0, "a dirty scope was accepted"
    assert "dirty" in proc.stderr and "vehicle/parts.yaml" in proc.stderr
    assert not (tmp_path / "id.json").exists()


def test_an_untracked_file_in_scope_is_rejected(repo, tmp_path):
    (repo / "de4sdv-virtual-ee/checks/patch_me.py").write_text("x = 1\n")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode != 0, "an untracked harness file was accepted"
    assert "checks/patch_me.py" in proc.stderr


def test_an_ignored_but_unexcluded_file_in_scope_is_rejected(repo, tmp_path):
    (repo / "de4sdv-virtual-ee/vehicle/.env").write_text("VXEDGE_ENDPOINT=x\n")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode != 0, "a gitignored file inside the scope was accepted"
    assert "vehicle/.env" in proc.stderr


def test_generated_evidence_caches_and_runtime_state_are_excluded(repo, tmp_path):
    scope = repo / "de4sdv-virtual-ee"
    (scope / "results/20990101T000000Z-x").mkdir(parents=True)
    (scope / "results/20990101T000000Z-x/summary.json").write_text("{}\n")
    (scope / "vehicle/ota-store").mkdir()
    (scope / "vehicle/ota-store/root.json").write_text("{}\n")
    (scope / "checks/__pycache__").mkdir()
    (scope / "checks/__pycache__/demo_measure.cpython-310.pyc").write_bytes(b"\0")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode == 0, proc.stderr


def test_dirt_outside_the_scope_does_not_block(repo, tmp_path):
    (repo / "README.md").write_text("edited\n")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode == 0, proc.stderr


def test_content_is_checked_even_when_git_is_told_not_to_look(repo, tmp_path):
    path = "de4sdv-virtual-ee/checks/demo_measure.py"
    git(repo, "update-index", "--assume-unchanged", path)
    (repo / path).write_text((repo / path).read_text() + "\n# hidden edit\n")
    assert git(repo, "status", "--porcelain") == ""  # git itself sees nothing
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode != 0, "an edit hidden by assume-unchanged was accepted"
    assert "checks/demo_measure.py" in proc.stderr


def test_a_gitless_copy_with_a_git_sha_file_is_not_provenance(repo, tmp_path):
    copy = tmp_path / "copy"
    shutil.copytree(repo / "de4sdv-virtual-ee", copy / "de4sdv-virtual-ee")
    (copy / "de4sdv-virtual-ee/.git-sha").write_text(git(repo, "rev-parse", "--short", "HEAD") + "\n")
    proc = helper("capture", "--scope", str(copy / "de4sdv-virtual-ee"), "--out", str(tmp_path / "id.json"))
    assert proc.returncode != 0, "a copied .git-sha was accepted as execution provenance"
    assert "not a git checkout" in proc.stderr and ".git-sha" in proc.stderr


def test_a_required_input_that_is_not_committed_is_rejected(repo, tmp_path):
    git(repo, "rm", "-q", "de4sdv-virtual-ee/vehicle/vxp.lock")
    git(repo, "commit", "-q", "-m", "drop lock")
    proc = capture(repo, tmp_path / "id.json")
    assert proc.returncode != 0
    assert "vehicle/vxp.lock" in proc.stderr and "not committed" in proc.stderr


def test_verify_accepts_the_unchanged_inputs(repo, tmp_path):
    ident = tmp_path / "id.json"
    assert capture(repo, ident).returncode == 0
    (repo / "de4sdv-virtual-ee/results/r").mkdir(parents=True)  # the run writes its archive
    (repo / "de4sdv-virtual-ee/results/r/x.log").write_text("x\n")
    after = tmp_path / "after.json"
    proc = helper("verify", "--identity", str(ident), "--out", str(after))
    assert proc.returncode == 0, proc.stderr
    result = json.loads(after.read_text())
    assert result["matches"] is True and result["differences"] == []
    assert result["before_sha256"] == sha256(ident)


def test_verify_rejects_an_input_changed_during_the_run(repo, tmp_path):
    ident = tmp_path / "id.json"
    assert capture(repo, ident).returncode == 0
    (repo / "de4sdv-virtual-ee/vehicle/parts.yaml").write_text("# swapped mid-run\n")
    after = tmp_path / "after.json"
    proc = helper("verify", "--identity", str(ident), "--out", str(after))
    assert proc.returncode != 0, "a mid-run input change passed verification"
    assert "vehicle/parts.yaml" in proc.stderr
    assert json.loads(after.read_text())["matches"] is False


def test_verify_rejects_a_moved_head(repo, tmp_path):
    ident = tmp_path / "id.json"
    assert capture(repo, ident).returncode == 0
    (repo / "README.md").write_text("moved\n")
    git(repo, "commit", "-qam", "move head")
    proc = helper("verify", "--identity", str(ident), "--out", str(tmp_path / "after.json"))
    assert proc.returncode != 0
    assert "head" in proc.stderr


def test_an_external_input_is_hashed_and_reverified(repo, tmp_path):
    tool = tmp_path / "udsTool.py"
    tool.write_text("print('v1')\n")
    ident = tmp_path / "id.json"
    assert capture(repo, ident, "--extra", f"uds_tool={tool}").returncode == 0
    assert json.loads(ident.read_text())["extra"]["uds_tool"] == {"path": str(tool), "sha256": sha256(tool)}
    tool.write_text("print('v2')\n")
    proc = helper("verify", "--identity", str(ident), "--out", str(tmp_path / "after.json"))
    assert proc.returncode != 0
    assert "uds_tool" in proc.stderr


def test_a_missing_external_input_is_rejected(repo, tmp_path):
    proc = capture(repo, tmp_path / "id.json", "--extra", f"uds_tool={tmp_path / 'absent.py'}")
    assert proc.returncode != 0
    assert "uds_tool" in proc.stderr


# --- archives -------------------------------------------------------------------


RESULTS = SCOPE_SRC / "results"
HISTORICAL = sorted(p for p in RESULTS.iterdir() if p.is_dir())


def _digest(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("archive", HISTORICAL, ids=[p.name for p in HISTORICAL])
def test_historical_archives_are_labelled_not_exact_commit_evidence(archive):
    before = _digest(archive)
    proc = helper("check-archive", str(archive))
    assert proc.returncode != 0, f"{archive.name} accepted as exact-commit evidence"
    assert "historical" in proc.stderr and "git_sha" in proc.stderr
    assert _digest(archive) == before


def test_the_first_demo_names_a_commit_without_its_harness():
    archive = RESULTS / "20261115T005422Z-657d64c6"
    proc = helper("check-archive", "--repo", str(SCOPE_SRC), str(archive))
    assert proc.returncode != 0
    assert "checks/run_demo.sh absent at 657d64c6" in proc.stderr


def test_the_backbone_archive_lock_differs_from_its_commits_lock():
    archive = RESULTS / "20261115T022118Z-04ee8739-backbone"
    proc = helper("check-archive", "--repo", str(SCOPE_SRC), str(archive))
    assert proc.returncode != 0
    assert "lock_sha256 a4a3e5a07cc7" in proc.stderr and "3054e3695da5" in proc.stderr


def _complete_archive(repo: Path, tmp_path: Path) -> Path:
    scope = repo / "de4sdv-virtual-ee"
    archive = scope / "results" / "run"
    archive.mkdir(parents=True)
    assert capture(repo, archive / "identity-before.json").returncode == 0
    ident = json.loads((archive / "identity-before.json").read_text())
    manifest = {"git_head": ident["git"]["head"], "git_sha": ident["git"]["head"],
                "identity_sha256": sha256(archive / "identity-before.json")}
    (archive / "manifest.json").write_text(json.dumps(manifest) + "\n")
    assert helper("verify", "--identity", str(archive / "identity-before.json"),
                  "--out", str(archive / "identity-after.json")).returncode == 0
    return archive


def test_a_complete_archive_passes_the_check(repo, tmp_path):
    archive = _complete_archive(repo, tmp_path)
    proc = helper("check-archive", "--repo", str(repo), str(archive))
    assert proc.returncode == 0, proc.stderr


def test_an_archive_whose_identity_record_was_edited_fails(repo, tmp_path):
    archive = _complete_archive(repo, tmp_path)
    path = archive / "identity-before.json"
    ident = json.loads(path.read_text())
    ident["named"]["lock"]["vehicle/vxp.lock"] = "0" * 64
    path.write_text(json.dumps(ident))
    proc = helper("check-archive", "--repo", str(repo), str(archive))
    assert proc.returncode != 0
    assert "identity_sha256" in proc.stderr
