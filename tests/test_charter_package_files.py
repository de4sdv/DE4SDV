"""The helper that gives an increment's tests their files, on synthetic folders.

An increment's packages are the ones its charter names in ``expectedArtifacts``. The helper has to refuse what it
cannot resolve to exactly one file: a test that reads fewer files than the increment has passes on less.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sysml_shapes import charter_package_files

CHARTER = """package Framing {{
  part theCharter : IncrementCharter {{
    attribute :>> expectedArtifacts = {artifacts};
  }}
}}
"""


def _folder(tmp_path: Path, artifacts: str, **files: str) -> Path:
    charter_file = tmp_path / "framing.sysml"
    charter_file.write_text(CHARTER.format(artifacts=artifacts), encoding="utf-8")
    for name, text in files.items():
        (tmp_path / f"{name}.sysml").write_text(text, encoding="utf-8")
    return charter_file


def test_the_files_of_the_named_packages_come_back_sorted(tmp_path: Path):
    charter_file = _folder(tmp_path, '("Needs", "Framing")', needs="package Needs {\n}\n",
                           other="package OtherIncrement {\n}\n")
    assert [path.name for path in charter_package_files(charter_file, "theCharter")] == [
        "framing.sysml", "needs.sysml"], "the file of a package that the charter does not name is left out"


def test_a_package_inside_another_package_is_not_one_that_a_charter_can_name(tmp_path: Path):
    charter_file = _folder(tmp_path, '("Framing", "Inner")', outer="package Outer {\n  package Inner {\n  }\n}\n")
    with pytest.raises(AssertionError, match=r"without exactly one file in its folder: \['Inner'\]"):
        charter_package_files(charter_file, "theCharter")


@pytest.mark.parametrize("value", ["Outer::Inner", "Q-R", ""])
def test_a_value_that_is_not_a_plain_package_name_is_refused_and_not_skipped(tmp_path: Path, value: str):
    charter_file = _folder(tmp_path, f'("Framing", "{value}")')
    with pytest.raises(AssertionError, match="not plain package names"):
        charter_package_files(charter_file, "theCharter")


def test_a_package_in_two_files_is_refused(tmp_path: Path):
    charter_file = _folder(tmp_path, '("Framing", "Needs")', needs="package Needs {\n}\n",
                           needs_again="package Needs {\n}\n")
    with pytest.raises(AssertionError, match=r"without exactly one file in its folder: \['Needs'\]"):
        charter_package_files(charter_file, "theCharter")


def test_a_package_of_another_folder_is_refused(tmp_path: Path):
    charter_file = _folder(tmp_path, '("Framing", "Elsewhere")')
    other = tmp_path / "other"
    other.mkdir()
    (other / "elsewhere.sysml").write_text("package Elsewhere {\n}\n", encoding="utf-8")
    with pytest.raises(AssertionError, match=r"without exactly one file in its folder: \['Elsewhere'\]"):
        charter_package_files(charter_file, "theCharter")


def test_a_package_that_only_a_comment_declares_is_refused(tmp_path: Path):
    charter_file = _folder(tmp_path, '("Framing", "Needs")', needs="/*\npackage Needs {\n}\n*/\npackage Later {\n}\n")
    with pytest.raises(AssertionError, match=r"without exactly one file in its folder: \['Needs'\]"):
        charter_package_files(charter_file, "theCharter")


def test_a_charter_without_a_list_of_packages_is_refused(tmp_path: Path):
    charter_file = _folder(tmp_path, '"Framing"')
    with pytest.raises(AssertionError, match="lists no expectedArtifacts"):
        charter_package_files(charter_file, "theCharter")
