"""Deployed runtime: one startup check, then answers only from the validated export.

The startup check runs on a real Git checkout (a shared clone of this
repository at HEAD) with the real model-built contract. Each refusal
condition has its own negative test: wrong commit, dirty tree, wrong
``sai-`` semantic authority, and a served model that is not the validated
export. Only the API transport is replaced.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from de4sdv.semantic import deployment_runtime as dr
from de4sdv.sysml_api.errors import ServedModelMismatchError
from de4sdv.sysml_api.served_model import SERVED_MODEL_SCHEMA, served_model_digest
from tests.model_contract_fixtures import binding_dict, model_contract, synthetic_identity

ROOT = Path(__file__).resolve().parents[1]
CORPUS = [
    {"@id": "pkg", "@type": "Package", "declaredName": "p"},
    {"@id": "part", "@type": "PartUsage", "declaredName": "brake", "owner": {"@id": "pkg"}},
]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture(scope="module")
def checkout(tmp_path_factory) -> tuple[Path, str]:
    """A clean shared clone of this repository at HEAD."""
    head = _git(ROOT, "rev-parse", "HEAD")
    root = tmp_path_factory.mktemp("deployed") / "DE4SDV"
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(root)],
                   check=True)
    _git(root, "checkout", "--quiet", "--detach", head)
    return root, head


def _served(elements=CORPUS) -> dict:
    return {"schema": SERVED_MODEL_SCHEMA, "source_export_sha256": "e" * 64,
            "element_count": len(elements), "content_sha256": served_model_digest(elements)}


def _binding(tmp_path: Path, head: str, **changes) -> Path:
    document = binding_dict(git_commit=head, served_model=_served())
    document.update(changes)
    path = tmp_path / "deployment-binding.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class _Client:
    base_url = "http://deployed-api.invalid"

    def __init__(self, elements):
        self.elements = elements

    def get_all(self, path):
        return [dict(element) for element in self.elements]


def _repository(elements):
    from de4sdv.sysml_api.repository import SysMLRepository

    return SysMLRepository(_Client(elements))


# ---------------------------------------------------------------------------
# The startup check passes on the four inputs and nothing else.
# ---------------------------------------------------------------------------


def test_startup_check_passes_for_the_deployed_commit_clean_tree_and_binding(checkout, tmp_path):
    root, head = checkout
    check = dr.verify_startup(root, binding_path=_binding(tmp_path, head),
                              expected_git_revision=head)
    assert check.head == head and check.application_revision == head
    assert check.contract.identity == model_contract().identity
    assert check.binding.served_model.content_sha256 == served_model_digest(CORPUS)
    report = check.report()
    assert report["startup_check"] == "passed"
    assert report["semantic_authority"] == model_contract().identity.id
    assert report["served_model"] == served_model_digest(CORPUS)


def test_wrong_commit_checkout_is_refused(checkout, tmp_path):
    root, head = checkout
    other = "0" * 40
    with pytest.raises(dr.StartupCheckError, match="wrong commit: checkout HEAD"):
        dr.verify_startup(root, binding_path=_binding(tmp_path, other),
                          expected_git_revision=other)


def test_wrong_commit_binding_is_refused(checkout, tmp_path):
    root, head = checkout
    with pytest.raises(dr.StartupCheckError, match="wrong commit: the deployment binding"):
        dr.verify_startup(root, binding_path=_binding(tmp_path, "1" * 40),
                          expected_git_revision=head)


def test_wrong_commit_application_revision_must_descend_from_the_model_revision(checkout, tmp_path):
    root, head = checkout
    with pytest.raises(dr.StartupCheckError, match="wrong commit"):
        dr.verify_startup(root, binding_path=_binding(tmp_path, "1" * 40),
                          expected_git_revision="1" * 40, application_revision=head)


@pytest.mark.parametrize("make_dirty", ["modified", "untracked"])
def test_dirty_tree_is_refused(checkout, tmp_path, make_dirty):
    root, head = checkout
    target = root / ("README.md" if make_dirty == "modified" else "stray-untracked-file.txt")
    original = target.read_bytes() if target.exists() else None
    target.write_bytes((original or b"") + b"\nlocal edit\n")
    try:
        with pytest.raises(dr.StartupCheckError, match="dirty tree"):
            dr.verify_startup(root, binding_path=_binding(tmp_path, head),
                              expected_git_revision=head)
    finally:
        if original is None:
            target.unlink()
        else:
            target.write_bytes(original)
    assert _git(root, "status", "--porcelain") == ""


def test_wrong_semantic_authority_is_refused(checkout, tmp_path):
    root, head = checkout
    path = _binding(tmp_path, head, semantic_authority=synthetic_identity("other").to_dict())
    with pytest.raises(dr.StartupCheckError, match="wrong semantic authority"):
        dr.verify_startup(root, binding_path=path, expected_git_revision=head)


def test_binding_without_a_served_model_is_refused(checkout, tmp_path):
    root, head = checkout
    path = tmp_path / "deployment-binding.json"
    path.write_text(json.dumps(binding_dict(git_commit=head)), encoding="utf-8")
    with pytest.raises(dr.StartupCheckError, match="no served model"):
        dr.verify_startup(root, binding_path=path, expected_git_revision=head)


@pytest.mark.parametrize("changes,match", [
    ({"scope": "candidate"}, "full-model"),
    ({"semantic_validation": "failed"}, "wrong commit"),
    ({"schema": "de4sdv.revision-binding/v1"}, "revision binding"),
])
def test_unusable_binding_is_refused(checkout, tmp_path, changes, match):
    root, head = checkout
    with pytest.raises(dr.StartupCheckError, match=match):
        dr.verify_startup(root, binding_path=_binding(tmp_path, head, **changes),
                          expected_git_revision=head)


def test_unreadable_binding_is_refused(checkout, tmp_path):
    root, head = checkout
    with pytest.raises(dr.StartupCheckError, match="revision binding"):
        dr.verify_startup(root, binding_path=tmp_path / "missing.json", expected_git_revision=head)


# ---------------------------------------------------------------------------
# The served model must be the validated export, whenever a corpus loads.
# ---------------------------------------------------------------------------


def test_served_model_equal_to_the_export_is_served(checkout, tmp_path):
    root, head = checkout
    padded = [{**element, "qualifiedName": None, "documentation": []} for element in CORPUS]
    service = dr.build_deployment_runtime(
        root, api_url="http://deployed-api.invalid", binding_path=_binding(tmp_path, head),
        expected_git_revision=head, repository=_repository(padded))
    assert service.authority_status()["served_model_check"] == "pending"
    assert len(service._elements()) == len(CORPUS)
    status = service.authority_status()
    assert status["served_model_check"] == "passed"
    assert status["semantic_authority"] == status["semantic_authority_id"] == model_contract().identity.id
    assert status["kind"] == "model" and status["startup_check"] == "passed"


def test_served_model_different_from_the_export_is_refused(checkout, tmp_path):
    root, head = checkout
    drifted = [dict(CORPUS[0]), {**CORPUS[1], "declaredName": "renamed"}]
    service = dr.build_deployment_runtime(
        root, api_url="http://deployed-api.invalid", binding_path=_binding(tmp_path, head),
        expected_git_revision=head, repository=_repository(drifted))
    with pytest.raises(ServedModelMismatchError, match="served model differs from the validated export"):
        service._elements()
    with pytest.raises(ServedModelMismatchError):  # refused again, never adopted
        service._elements()
    assert service.authority_status()["served_model_check"].startswith("failed")
    status = service.model_status()
    assert status["current_baseline"] is False
    assert any(gap["category"] == "runtime-served-model" for gap in status["gaps"])


def test_served_model_check_applies_to_snapshots(checkout, tmp_path):
    root, head = checkout
    service = dr.build_deployment_runtime(
        root, api_url="http://deployed-api.invalid", binding_path=_binding(tmp_path, head),
        expected_git_revision=head, repository=_repository(CORPUS))
    assert service.corpus_matches(CORPUS) is True
    assert service.corpus_matches([CORPUS[0]]) is False


def test_startup_refusal_happens_before_any_api_access(checkout, tmp_path):
    root, head = checkout

    class _Untouchable:
        def __getattr__(self, name):
            raise AssertionError("the API must not be read before the startup check passes")

    with pytest.raises(dr.StartupCheckError):
        dr.build_deployment_runtime(
            root, api_url="http://deployed-api.invalid",
            binding_path=_binding(tmp_path, head, semantic_authority=synthetic_identity().to_dict()),
            expected_git_revision=head, repository=_Untouchable())


def test_a_refused_api_corpus_is_not_downloaded_again(checkout, tmp_path):
    root, head = checkout

    class _CountingClient(_Client):
        calls = 0

        def get_all(self, path):
            type(self).calls += 1
            return super().get_all(path)

    from de4sdv.sysml_api.repository import SysMLRepository

    client = _CountingClient([CORPUS[0]])
    service = dr.build_deployment_runtime(
        root, api_url="http://deployed-api.invalid", binding_path=_binding(tmp_path, head),
        expected_git_revision=head, repository=SysMLRepository(client))
    for _ in range(3):
        with pytest.raises(ServedModelMismatchError):
            service._elements()
    assert _CountingClient.calls == 1


def test_a_stale_snapshot_does_not_mark_the_runtime_failed(checkout, tmp_path):
    root, head = checkout
    from de4sdv.sysml_api.repository import SysMLRepository

    repository = SysMLRepository(_Client(CORPUS))
    repository.install_corpus_source(lambda p, c: [CORPUS[0]])
    service = dr.build_deployment_runtime(
        root, api_url="http://deployed-api.invalid", binding_path=_binding(tmp_path, head),
        expected_git_revision=head, repository=repository)
    assert len(service._elements()) == 2
    assert service.authority_status()["served_model_check"] == "passed"
