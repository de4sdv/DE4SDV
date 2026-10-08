"""Shared revision-binding and documentation-parity helpers (authority_inventory).

The O1 inventory generator was deleted in O4 Wave C2 (its output is a frozen
record); the helpers it shared with the live generators and the chain
verifier stay. These tests are ported unchanged from the deleted
``tests/test_semantic_authority_inventory.py`` (``TestTextParity`` and
``TestRevisionBinding`` without its two O1-artifact tests).
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from de4sdv.semantic import authority_inventory as ai


_GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


class TestTextParity:
    def _file(self, body: str) -> str:
        return f"package T {{\n  {body}\n}}\n"

    def test_equal_after_cosmetic_normalization_is_exact(self):
        file_text = self._file(
            "part def Widget {\n    doc /* A WIDGET does one thing, cleanly. */\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "normalized-exact"
        )

    def test_model_text_with_extra_semantic_sentence_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing cleanly. It also implies acceptance. */\n"
            "  }"
        )
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "differs"
        )

    def test_yaml_text_with_extra_semantic_sentence_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n    doc /* A widget does one thing cleanly. */\n  }"
        )
        assert (
            ai.doc_text_observation(
                file_text,
                "part def Widget",
                "a widget does one thing cleanly and implies acceptance",
            )
            == "differs"
        )

    def test_containment_in_either_direction_is_not_parity(self):
        file_text = self._file(
            "part def Widget {\n"
            "    doc /* A widget does one thing cleanly, in the approved style. */\n"
            "  }"
        )
        # Definition contained in the doc (doc adds text) — not parity.
        assert (
            ai.doc_text_observation(
                file_text, "part def Widget", "a widget does one thing cleanly"
            )
            == "differs"
        )
        # Doc contained in the definition (definition adds text) — not parity.
        assert (
            ai.doc_text_observation(
                file_text,
                "part def Widget",
                "a widget does one thing cleanly in the approved style, always",
            )
            == "differs"
        )

    def test_doc_absent_and_bodyless_observations(self):
        bodyless = self._file("part def Empty;")
        assert (
            ai.doc_text_observation(bodyless, "part def Empty", "definition")
            == "doc-absent (bodyless declaration)"
        )
        no_doc = self._file("part def Silent {\n  }")
        assert (
            ai.doc_text_observation(no_doc, "part def Silent", "definition")
            == "doc-absent"
        )



def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    import os

    env = dict(os.environ)
    env.update(_GIT_ENV)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    result = subprocess.run(
        ["git", "init", "-q"], cwd=repo, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return repo


def _write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit_all(repo: Path, message: str = "commit") -> str:
    _git(repo, "add", "-A")
    result = _git(repo, "commit", "-q", "-m", message)
    assert result.returncode == 0, result.stderr
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _digest(repo: Path, relative: str) -> str:
    return (
        "sha256:"
        + hashlib.sha256((repo / relative).read_bytes()).hexdigest()
    )


def _binding(repo: Path, revision: str, paths: list[str]) -> dict:
    return {
        "source_revision": revision,
        "bound_inputs": {path: _digest(repo, path) for path in sorted(paths)},
    }


class TestRevisionBinding:
    FILES = {"src/module.py": "x = 1\n", "data/input.yaml": "a: 1\n"}

    def _repo_with_commit(self, tmp_path: Path) -> tuple[Path, str]:
        repo = _init_repo(tmp_path)
        for relative, content in self.FILES.items():
            _write(repo, relative, content)
        revision = _commit_all(repo)
        return repo, revision

    def test_correct_source_revision_with_matching_digests_passes(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        assert ai.validate_source_binding(repo, binding) == []

    def test_changed_bound_input_with_unchanged_recorded_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        # Uncommitted change to a bound input.
        _write(repo, "src/module.py", "x = 2\n")
        errors = ai.validate_source_binding(repo, binding)
        assert any("differs from its content at source_revision" in e for e in errors)
        # Committed change without rebinding is equally stale.
        _commit_all(repo, "change")
        errors = ai.validate_source_binding(repo, binding)
        assert any("differs from its content at source_revision" in e for e in errors)

    def test_generation_refuses_uncommitted_input_changes(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        bound_inputs = {
            path: _digest(repo, path) for path in sorted(self.FILES)
        }
        _write(repo, "data/input.yaml", "a: 2\n")
        with pytest.raises(ai.InventoryError, match="Commit the input changes first"):
            ai.verify_source_revision_contains_inputs(repo, revision, bound_inputs)

    def test_arbitrary_revision_string_cannot_self_authorize(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        binding["source_revision"] = "a" * 40
        errors = ai.validate_source_binding(repo, binding)
        assert any("not a commit in this repository" in e for e in errors)
        binding["source_revision"] = "not-a-sha"
        errors = ai.validate_source_binding(repo, binding)
        assert any("40-hex" in e for e in errors)

    def test_missing_bound_input_at_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        _write(repo, "src/extra.py", "y = 1\n")
        _commit_all(repo, "add extra")
        paths = sorted(list(self.FILES) + ["src/extra.py"])
        binding = _binding(repo, revision, paths)
        errors = ai.validate_source_binding(repo, binding)
        assert any(
            "src/extra.py does not exist at source_revision" in e for e in errors
        )

    def test_digest_mismatch_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        binding = _binding(repo, revision, list(self.FILES))
        binding["bound_inputs"]["src/module.py"] = "sha256:" + "0" * 64
        errors = ai.validate_source_binding(repo, binding)
        assert any("does not match the recorded digest" in e for e in errors)

    def test_non_ancestor_revision_fails(self, tmp_path):
        repo, revision = self._repo_with_commit(tmp_path)
        branch = _git(repo, "symbolic-ref", "--short", "HEAD").stdout.strip()
        # Create an orphan history whose commit is not an ancestor of HEAD.
        _git(repo, "checkout", "-q", "--orphan", "other")
        _git(repo, "rm", "-rf", "-q", ".")
        _write(repo, "src/module.py", "z = 9\n")
        side_revision = _commit_all(repo, "side")
        _git(repo, "checkout", "-q", branch)
        binding = _binding(repo, revision, list(self.FILES))
        # HEAD moved back to the original branch; its binding still validates.
        assert ai.validate_source_binding(repo, binding) == []
        side_binding = {
            "source_revision": side_revision,
            "bound_inputs": {"src/module.py": _digest(repo, "src/module.py")},
        }
        errors = ai.validate_source_binding(repo, side_binding)
        assert any(
            "not an ancestor of the checked-out revision" in e for e in errors
        ), errors


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_no_fuzzy_matching_code_path():
    """The module exposes exactly one text comparator; no similarity API."""
    source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(encoding="utf-8")
    for forbidden in ("difflib", "SequenceMatcher", "cosine", "levenshtein"):
        assert forbidden not in source
    assert ai.normalize_text("A-b  c!") == "a b c"


def test_no_authored_ontology_or_inventory_generator_remains():
    """O4 Wave C2: the O1 generator (and its authored-ontology reads) is gone."""
    source = (REPO_ROOT / "de4sdv/semantic/authority_inventory.py").read_text(encoding="utf-8")
    for removed in ("build_inventory", "KernelContract", "de4sdv-basic-ontology", "yaml"):
        assert removed not in source, removed
