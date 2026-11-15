"""R8 attack: an archive must not be able to assert its own identity.

check-archive --repo reconstructs the complete expected identity (tracked
inventory, named groups, tree and scope tree) from Git at the recorded
execution commit and accepts only a record that matches it exactly. A record
that is coherent with itself (digests recomputed, manifest and after-record
rehashed) but not with the commit is rejected.
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
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env={**os.environ, **GIT_ENV}).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helper(*args: str):
    return subprocess.run([PY, str(HELPER), *args], capture_output=True, text=True, timeout=120,
                          env={**os.environ, **GIT_ENV})


def make_repo(top: Path) -> Path:
    top.mkdir()
    shutil.copytree(SCOPE_SRC, top / "de4sdv-virtual-ee",
                    ignore=shutil.ignore_patterns("results", "__pycache__", ".pytest_cache"))
    (top / "README.md").write_text("root\n")
    (top / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.env\n")
    git(top, "init", "-q", "-b", "main")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "fixture")
    return top


@pytest.fixture
def repo(tmp_path) -> Path:
    return make_repo(tmp_path / "repo")


def check(repo: Path, archive: Path):
    return helper("check-archive", "--repo", str(repo), str(archive))


def test_a_minimal_self_asserted_identity_is_rejected(repo):
    """The parent's reproduced forgery: head only, clean false, empty inventory."""
    head = git(repo, "rev-parse", "HEAD")
    archive = repo / "de4sdv-virtual-ee" / "results" / "forged"
    archive.mkdir(parents=True)
    before = archive / "identity-before.json"
    before.write_text(json.dumps({"git": {"head": head}, "clean": False, "inventory": [], "named": {}}, indent=2))
    (archive / "manifest.json").write_text(json.dumps({"git_head": head, "identity_sha256": sha256(before)}))
    (archive / "identity-after.json").write_text(json.dumps({"matches": True, "before_sha256": sha256(before)}))
    proc = check(repo, archive)
    assert proc.returncode == 1, f"forged identity accepted: {proc.stdout}{proc.stderr}"
    assert "identity complete" not in proc.stdout


# --- coherent forgeries of a real archive ----------------------------------------
#
# The attacker edits identity-before.json and then makes everything that hashes it
# agree: inventory_sha256 recomputed, named digests updated, after-record copied,
# manifest and after before_sha256 rehashed. Only the commit can disagree.


def capture_cmd(repo: Path, out: Path):
    return helper("capture", "--scope", str(repo / "de4sdv-virtual-ee"), "--out", str(out))


def complete_archive(repo: Path, name: str = "run") -> Path:
    archive = repo / "de4sdv-virtual-ee" / "results" / name
    archive.mkdir(parents=True)
    proc = capture_cmd(repo, archive / "identity-before.json")
    assert proc.returncode == 0, proc.stderr
    ident = json.loads((archive / "identity-before.json").read_text())
    manifest = {"git_head": ident["git"]["head"], "git_sha": ident["git"]["head"],
                "git_tree": ident["git"]["tree"], "identity_sha256": sha256(archive / "identity-before.json")}
    (archive / "manifest.json").write_text(json.dumps(manifest) + "\n")
    proc = helper("verify", "--identity", str(archive / "identity-before.json"),
                  "--out", str(archive / "identity-after.json"))
    assert proc.returncode == 0, proc.stderr
    return archive


@pytest.fixture(scope="module")
def shared(tmp_path_factory):
    top = make_repo(tmp_path_factory.mktemp("shared") / "repo")
    return top, complete_archive(top, "pristine")


@pytest.fixture
def forged(shared, tmp_path):
    top, pristine = shared
    archive = tmp_path / "archive"
    shutil.copytree(pristine, archive)
    return top, archive


def inv_digest(inventory) -> str:
    return hashlib.sha256("".join(f"{e['path']}\0{e['sha256']}\n" for e in inventory).encode()).hexdigest()


def forge(archive: Path, mutate, *, recompute: bool = True, after_mutate=None) -> None:
    before_path = archive / "identity-before.json"
    ident = json.loads(before_path.read_text())
    mutate(ident)
    if recompute and isinstance(ident.get("inventory"), list):
        try:
            ident["inventory_sha256"] = inv_digest(ident["inventory"])
        except (KeyError, TypeError):
            pass
    before_path.write_text(json.dumps(ident, indent=2, sort_keys=True) + "\n")
    after = json.loads((archive / "identity-after.json").read_text())
    for key in ("git", "inventory_sha256", "named", "extra"):
        if isinstance(ident, dict) and key in ident:
            after["after"][key] = ident[key]
    after["before_sha256"] = sha256(before_path)
    if after_mutate:
        after_mutate(after)
    (archive / "identity-after.json").write_text(json.dumps(after))
    manifest = json.loads((archive / "manifest.json").read_text())
    manifest["identity_sha256"] = sha256(before_path)
    if isinstance(ident, dict) and isinstance(ident.get("git"), dict) and "head" in ident["git"]:
        manifest["git_head"] = manifest["git_sha"] = ident["git"]["head"]
        if "tree" in ident["git"]:
            manifest["git_tree"] = ident["git"]["tree"]
    (archive / "manifest.json").write_text(json.dumps(manifest))


def rejected(top: Path, archive: Path, needle: str) -> None:
    proc = check(top, archive)
    assert proc.returncode == 1, f"forgery accepted: {proc.stdout}{proc.stderr}"
    assert "identity complete" not in proc.stdout
    assert needle in proc.stderr, proc.stderr
    assert "Traceback" not in proc.stderr


def entry(ident, path):
    return next(e for e in ident["inventory"] if e["path"] == path)


def set_named(ident, path, digest):
    for group in ident["named"].values():
        if path in group:
            group[path] = digest


def test_the_pristine_copy_is_accepted(forged):
    top, archive = forged
    proc = check(top, archive)
    assert proc.returncode == 0, proc.stderr


def test_an_omitted_inventory_entry_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i["inventory"].remove(entry(i, "checks/gate2.py")))
    rejected(top, archive, "inventory omits checks/gate2.py")


def test_an_extra_inventory_entry_is_rejected(forged):
    top, archive = forged
    def add(i):
        i["inventory"].append({"path": "checks/zz_injected.py", "mode": "100644", "git_blob": "a" * 40,
                               "sha256": "b" * 64})
        i["inventory"].sort(key=lambda x: x["path"])
    forge(archive, add)
    rejected(top, archive, "inventory lists checks/zz_injected.py")


def test_a_duplicate_inventory_entry_is_rejected(forged):
    top, archive = forged
    def dup(i):
        e = dict(entry(i, "checks/gate2.py"))
        i["inventory"].append(e)
        i["inventory"].sort(key=lambda x: x["path"])
    forge(archive, dup)
    rejected(top, archive, "duplicate paths")


def test_a_coherently_altered_unnamed_digest_is_rejected(forged):
    """The parent's second finding: named groups were the only paths compared."""
    top, archive = forged
    forge(archive, lambda i: entry(i, "checks/gate2.py").update(sha256="c" * 64))
    rejected(top, archive, "checks/gate2.py recorded sha256 differs")


def test_a_coherently_altered_named_digest_is_rejected(forged):
    top, archive = forged
    def alter(i):
        entry(i, "vehicle/vxp.lock")["sha256"] = "d" * 64
        set_named(i, "vehicle/vxp.lock", "d" * 64)
    forge(archive, alter)
    rejected(top, archive, "vehicle/vxp.lock recorded sha256 differs")


def test_an_altered_blob_id_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: entry(i, "checks/run_demo.sh").update(git_blob="e" * 40))
    rejected(top, archive, "checks/run_demo.sh recorded git_blob differs")


def test_an_altered_mode_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: entry(i, "checks/run_demo.sh").update(mode="100644"))
    rejected(top, archive, "checks/run_demo.sh recorded mode differs")


def test_a_symlink_mode_in_the_record_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: entry(i, "checks/gate2.py").update(mode="120000"))
    rejected(top, archive, "is not a regular file")


@pytest.mark.parametrize("key", ["tree", "scope_tree"])
def test_an_altered_tree_is_rejected(forged, key):
    top, archive = forged
    forge(archive, lambda i: i["git"].update({key: "f" * 40}))
    rejected(top, archive, f"git {key} {'f' * 40} is not the {key}")


@pytest.mark.parametrize("value", [False, "true", 1, None])
def test_a_non_true_clean_flag_is_rejected(forged, value):
    top, archive = forged
    forge(archive, lambda i: i.update(clean=value))
    rejected(top, archive, "clean is not true")


def test_a_widened_exclusion_selector_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i["excluded"].append("vehicle/"))
    rejected(top, archive, "excluded selector is not schema 1")


def test_a_caller_chosen_named_group_list_is_rejected(forged):
    """Named groups come from NAMED, not from whatever the record lists."""
    top, archive = forged
    forge(archive, lambda i: i["named"].pop("lock"))
    rejected(top, archive, "named groups are not")


def test_a_named_group_missing_a_path_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i["named"]["harness"].pop("checks/run_identity.py"))
    rejected(top, archive, "named group harness")


def test_an_unknown_identity_key_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i.update(note="trust me"))
    rejected(top, archive, "missing or unexpected")


def test_an_uncomputed_inventory_digest_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i.update(inventory_sha256="0" * 64), recompute=False)
    rejected(top, archive, "inventory_sha256 does not match")


def test_an_after_record_with_differences_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: None, after_mutate=lambda a: a.update(differences=["input changed: x"]))
    rejected(top, archive, "does not confirm the inputs were unchanged")


def test_an_after_record_matching_as_a_string_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: None, after_mutate=lambda a: a.update(matches="true"))
    rejected(top, archive, "does not confirm the inputs were unchanged")


def test_an_after_identity_that_disagrees_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: None, after_mutate=lambda a: a["after"].update(inventory_sha256="1" * 64))
    rejected(top, archive, "after inventory_sha256 differs")


def test_an_after_record_without_after_identity_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: None, after_mutate=lambda a: a.pop("after"))
    rejected(top, archive, "not a complete verify record")


def test_a_manifest_tree_that_disagrees_is_rejected(forged):
    top, archive = forged
    manifest = json.loads((archive / "manifest.json").read_text())
    manifest["git_tree"] = "2" * 40
    (archive / "manifest.json").write_text(json.dumps(manifest))
    rejected(top, archive, "manifest git_tree disagrees")


@pytest.mark.parametrize("text", ["[]", "null", "\"x\"", "{not json", ""])
def test_a_malformed_identity_record_fails_closed(forged, text):
    top, archive = forged
    (archive / "identity-before.json").write_bytes(text.encode())
    manifest = json.loads((archive / "manifest.json").read_text())
    manifest["identity_sha256"] = sha256(archive / "identity-before.json")
    (archive / "manifest.json").write_text(json.dumps(manifest))
    proc = check(top, archive)
    assert proc.returncode == 1 and "identity complete" not in proc.stdout
    assert "Traceback" not in proc.stderr, proc.stderr


@pytest.mark.parametrize("text", ["[]", "{not json"])
def test_a_malformed_manifest_fails_closed(forged, text):
    top, archive = forged
    (archive / "manifest.json").write_text(text)
    proc = check(top, archive)
    assert proc.returncode == 1 and "Traceback" not in proc.stderr, proc.stderr


def test_without_repo_a_consistent_archive_is_labelled_unverified(forged):
    top, archive = forged
    proc = helper("check-archive", str(archive))
    assert proc.returncode == 1
    assert "identity complete" not in proc.stdout
    assert "source provenance NOT verified" in proc.stderr


# --- legitimate retained archives ------------------------------------------------


def test_a_retained_archive_survives_a_later_commit_that_changes_its_inputs(repo):
    """Reconstruction reads the recorded commit, not the current HEAD or worktree."""
    archive = complete_archive(repo)
    lock = repo / "de4sdv-virtual-ee/vehicle/vxp.lock"
    lock.write_text(lock.read_text() + "# later\n")
    (repo / "de4sdv-virtual-ee/checks/new_tool.py").write_text("x = 1\n")
    git(repo, "add", "-A", "de4sdv-virtual-ee/vehicle", "de4sdv-virtual-ee/checks")
    git(repo, "commit", "-q", "-m", "advance")
    proc = check(repo, archive)
    assert proc.returncode == 0, proc.stderr


def test_a_retained_archive_moved_out_of_the_repository_is_accepted(shared, tmp_path):
    top, pristine = shared
    elsewhere = tmp_path / "store" / "pristine"
    shutil.copytree(pristine, elsewhere)
    proc = check(top, elsewhere)
    assert proc.returncode == 0, proc.stderr


def test_an_archive_naming_a_commit_absent_from_the_repo_is_rejected(forged):
    top, archive = forged
    forge(archive, lambda i: i["git"].update(head="9" * 40))
    rejected(top, archive, "is not a commit of")


# --- symlinked runtime inputs ------------------------------------------------------


def test_a_committed_symlink_runtime_input_is_rejected_at_capture(repo, tmp_path):
    scope = repo / "de4sdv-virtual-ee"
    (scope / "vehicle/link.yaml").symlink_to("vehicle.yaml")
    git(repo, "add", "de4sdv-virtual-ee/vehicle/link.yaml")
    git(repo, "commit", "-q", "-m", "symlink")
    proc = capture_cmd(repo, tmp_path / "id.json")
    assert proc.returncode == 1
    assert "vehicle/link.yaml" in proc.stderr and "symlink" in proc.stderr
    assert not (tmp_path / "id.json").exists()


def test_a_regular_file_replaced_by_a_symlink_on_disk_is_rejected(repo, tmp_path):
    scope = repo / "de4sdv-virtual-ee"
    target = scope / "vehicle/parts.yaml"
    copy = tmp_path / "parts.yaml"
    copy.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(copy)  # same bytes through the link: still not the committed file
    proc = capture_cmd(repo, tmp_path / "id.json")
    assert proc.returncode == 1
    assert "vehicle/parts.yaml" in proc.stderr


def test_verify_rejects_a_malformed_identity_record(tmp_path):
    bad = tmp_path / "id.json"
    bad.write_text(json.dumps({"git": {"head": "0" * 40}, "clean": True}))
    proc = helper("verify", "--identity", str(bad), "--out", str(tmp_path / "after.json"))
    assert proc.returncode == 1 and "malformed" in proc.stderr and "Traceback" not in proc.stderr
