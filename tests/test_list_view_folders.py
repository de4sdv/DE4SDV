"""View folders come from the model (scripts/list_view_folders.py).

The Privileged Syside Validation checks the published views (VIEWS.md and the
committed diagrams) of every folder this script lists, so no workflow, script
or test names a view folder by hand. Synthetic repositories exercise the rule;
the last test reads the real model.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import list_view_folders
from scripts.list_view_folders import view_folders

ROOT = Path(__file__).resolve().parents[1]

VIEW = "package P {\n  view structureView : GeneralView {\n    expose P::*;\n  }\n}\n"
NO_VIEW = "package Q {\n  part def Thing;\n}\n"


def _write(repository: Path, relative: str, text: str = "") -> Path:
    path = repository / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_a_folder_whose_sysml_declares_a_view_is_a_view_folder(tmp_path: Path) -> None:
    _write(tmp_path, "model/features/new-area/new_area_framing.sysml", VIEW)
    _write(tmp_path, "model/features/other/other_requirements.sysml", NO_VIEW)
    assert view_folders(["model"], repository=tmp_path) == ["model/features/new-area"]


def test_nested_view_folders_are_listed_sorted(tmp_path: Path) -> None:
    _write(tmp_path, "model/b/b.sysml", VIEW)
    _write(tmp_path, "model/a/deep/deep.sysml", VIEW)
    _write(tmp_path, "model/a/a.sysml", NO_VIEW)
    assert view_folders(["model"], repository=tmp_path) == ["model/a/deep", "model/b"]


def test_views_in_comments_or_view_definitions_do_not_count(tmp_path: Path) -> None:
    text = (
        "package P {\n"
        "  // view commentedView { }\n"
        "  doc /* view documentedView { } */\n"
        "  view def StructureViewDefinition { }\n"
        "}\n"
    )
    _write(tmp_path, "model/area/area.sysml", text)
    assert view_folders(["model"], repository=tmp_path) == []


def test_published_artifacts_keep_a_folder_listed_after_its_views_go(tmp_path: Path) -> None:
    # A folder whose views were removed is still checked, so its stale
    # VIEWS.md and diagrams fail the check until they are removed too.
    _write(tmp_path, "model/retired/retired.sysml", NO_VIEW)
    _write(tmp_path, "model/retired/VIEWS.md", "# Retired Views\n")
    _write(tmp_path, "model/stale/diagrams/diagram-oldView.svg", "<svg/>")
    assert view_folders(["model"], repository=tmp_path) == ["model/retired", "model/stale"]


def test_libraries_snapshots_and_fixtures_are_never_view_folders(tmp_path: Path) -> None:
    # The exclusion reads repository-relative parts, so a repository that
    # itself sits under a "fixtures" directory is still scanned.
    repository = tmp_path / "fixtures" / "repository"
    for part in ("libraries", "snapshots", "fixture", "fixtures", ".sysand"):
        _write(repository, f"model/{part}/area/area.sysml", VIEW)
    _write(repository, "model/real/real.sysml", VIEW)
    assert view_folders(["model"], repository=repository) == ["model/real"]


def test_a_model_file_stands_for_its_folder(tmp_path: Path) -> None:
    _write(tmp_path, "model/area/area_framing.sysml", VIEW)
    _write(tmp_path, "model/other/other.sysml", VIEW)
    assert view_folders(["model/area/area_framing.sysml"], repository=tmp_path) == ["model/area"]


def test_several_model_paths_are_merged_without_duplicates(tmp_path: Path) -> None:
    _write(tmp_path, "model/area/area.sysml", VIEW)
    _write(tmp_path, "product-models/product.sysml", VIEW)
    paths = ["model", "model/area", "product-models"]
    assert view_folders(paths, repository=tmp_path) == ["model/area", "product-models"]


def test_the_command_prints_one_folder_per_line(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(list_view_folders, "ROOT", tmp_path)
    _write(tmp_path, "model/b/b.sysml", VIEW)
    _write(tmp_path, "model/a/a.sysml", VIEW)
    assert list_view_folders.main(["model"]) == 0
    assert capsys.readouterr().out == "model/a\nmodel/b\n"


def test_the_command_refuses_an_empty_list_and_a_missing_path(tmp_path: Path, monkeypatch, capsys) -> None:
    # An empty list would silently check nothing.
    monkeypatch.setattr(list_view_folders, "ROOT", tmp_path)
    _write(tmp_path, "model/area/area.sysml", NO_VIEW)
    assert list_view_folders.main(["model"]) == 1
    assert "no view folder" in capsys.readouterr().err
    assert list_view_folders.main(["no-such-path"]) == 2
    assert "no-such-path" in capsys.readouterr().err


def test_the_default_model_paths_are_the_validated_model_roots() -> None:
    import yaml

    from scripts import validate_sysml

    assert list_view_folders.MODEL_ROOTS == tuple(path.as_posix() for path in validate_sysml.MODEL_PATHS)
    # The licensed validation renders these roots by default, so the public
    # tests check the same folders as its published-views step.
    workflow = yaml.safe_load(
        (ROOT / ".github/workflows/privileged-syside-validation.yml").read_text(encoding="utf-8")
    )
    roots = " ".join(list_view_folders.MODEL_ROOTS)
    assert workflow[True]["workflow_dispatch"]["inputs"]["model_paths"]["default"] == roots
    assert workflow["jobs"]["syside-validation"]["env"]["MODEL_PATHS"] == (
        "${{ inputs.model_paths || '" + roots + "' }}"
    )


def test_every_view_folder_of_the_model_is_published() -> None:
    """Publication completeness on the real model: the folders that declare
    views (or hold published views) are exactly the folders whose VIEWS.md is
    committed (the oracle is Git, not the derivation)."""
    derived = set(view_folders())
    tracked = subprocess.run(
        ["git", "ls-files", "--", *list_view_folders.MODEL_ROOTS],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    published = {
        path.rsplit("/", 1)[0]
        for path in tracked
        if path.endswith("/VIEWS.md")
        and not set(path.split("/")) & list_view_folders.EXCLUDED_PARTS
    }
    assert derived, "the model declares no view"
    unpublished = sorted(derived - published)
    assert not unpublished, (
        "view folders without a committed VIEWS.md (run python "
        f"scripts/generate_view_index.py <folder> and commit it): {unpublished}"
    )
    assert derived == published, sorted(published - derived)
