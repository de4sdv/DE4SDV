"""Behavioral tests for the check that UPSTREAM.md lists the repositories the tree names."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_upstream_index.py"
INDEX = "UPSTREAM.md"


def _load_tool():
    spec = importlib.util.spec_from_file_location("check_upstream_index", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _url(repository: str, host: str = "github.com") -> str:
    """A link to a repository, put together here so that this file names none itself."""
    return f"https://{host}/{repository}"


def _errors(files: Mapping[str, str | bytes], omissions: Mapping[str, str] | None = None) -> list[str]:
    encoded = {path: text if isinstance(text, bytes) else text.encode("utf-8") for path, text in files.items()}
    return _load_tool().index_errors(encoded, omissions or {})


# The committed repository


def test_committed_index_lists_every_repository_the_tree_names() -> None:
    completed = subprocess.run([sys.executable, str(TOOL)], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Upstream index check passed" in completed.stdout


def test_committed_scan_finds_repositories_where_the_tree_is_known_to_name_them() -> None:
    """The scan must not pass by finding nothing: these references exist, in three written forms."""
    tool = _load_tool()
    files = tool.read_tracked()
    named = tool.named_repositories(files)
    known = {
        # a `url:` value in a .repos file
        "autowarefoundation/autoware_universe": "implementation/aebs-autoware-executable-bench/autoware-009a.repos",
        # a Markdown autolink
        "covesa/vehicle_signal_specification": "textual-notation-of-model/libraries/covesa-vss-sysmlv2/README.md",
        # a Go module path without a scheme
        "mholt/caddy-ratelimit": "deployment/caddy/Dockerfile",
    }
    for repository, path in known.items():
        assert path in named.get(repository, []), (repository, named.get(repository))
    assert len(named) >= 20, sorted(named)
    assert not [repository for repository in named if repository.split("/")[0] in tool.OWN_OWNERS]
    assert not [paths for paths in named.values() if INDEX in paths]
    linked = tool.linked_repositories(files)
    assert len(linked) >= 20, sorted(linked)
    assert set(tool.OMISSIONS) <= set(named), "every omission is a repository the tree names"


def test_list_shows_each_named_repository_with_its_state() -> None:
    completed = subprocess.run([sys.executable, str(TOOL), "--list"], cwd=ROOT, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    states = {line.split()[1]: line.split()[0] for line in completed.stdout.splitlines()}
    assert states["autowarefoundation/autoware_universe"] == "entry"
    assert states["mholt/caddy-ratelimit"] == "omission"
    assert set(states.values()) == {"entry", "omission"}, completed.stdout


# What counts as an entry


def test_a_named_repository_that_the_index_links_passes() -> None:
    assert _errors({INDEX: f"| [Widget]({_url('acme/widget')}) |\n", "bench/README.md": _url("acme/widget")}) == []


def test_a_named_repository_without_an_entry_is_reported_with_the_file_that_names_it() -> None:
    assert _errors({INDEX: "# Upstream projects\n", "bench/README.md": f"Built on {_url('acme/widget')}.\n"}) == [
        "acme/widget has no entry in UPSTREAM.md: named in bench/README.md"
    ]


def test_several_naming_files_are_counted_and_the_first_is_shown() -> None:
    files = {INDEX: "", "b.md": _url("acme/widget"), "a/run.sh": _url("acme/widget"), "c.yaml": _url("acme/widget")}
    assert _errors(files) == ["acme/widget has no entry in UPSTREAM.md: named in a/run.sh and 2 more files"]


def test_each_missing_repository_is_reported_once_in_order() -> None:
    files = {INDEX: _url("acme/listed"), "x.md": f"{_url('zeta/tool')} {_url('acme/widget')} {_url('acme/listed')}"}
    assert _errors(files) == [
        "acme/widget has no entry in UPSTREAM.md: named in x.md",
        "zeta/tool has no entry in UPSTREAM.md: named in x.md",
    ]


@pytest.mark.parametrize(
    "written",
    [
        _url("Acme/Widget"),
        _url("acme/widget.git"),
        _url("acme/widget") + "/tree/0123abc/src",
        _url("acme/widget") + ".",
        _url("acme/widget", host="www.github.com"),
        "git@github.com:" + "acme/widget.git",
        "github.com/" + "acme/widget@0123abc",
        _url("acme/widget/main/file.txt", host="raw.githubusercontent.com"),
        _url("acme/widget/tar.gz/v1", host="codeload.github.com"),
        _url("repos/acme/widget/releases", host="api.github.com"),
    ],
)
def test_every_written_form_names_the_same_repository(written: str) -> None:
    assert _errors({INDEX: "", "x.md": written}) == ["acme/widget has no entry in UPSTREAM.md: named in x.md"]
    assert _errors({INDEX: _url("acme/widget"), "x.md": written}) == []


@pytest.mark.parametrize(
    "written",
    [
        _url("orgs/acme/projects/3"),
        _url("search?q=widget"),
        _url("acme"),
        _url("acme/widget", host="gist.github.com"),
        _url("acme/widget", host="notgithub.com"),
        "https://example.org/github.com-mirror",
        _url("repos/acme", host="api.github.com"),
    ],
)
def test_pages_that_are_not_repositories_name_nothing(written: str) -> None:
    assert _errors({INDEX: "", "x.md": written}) == []


def test_the_projects_own_repositories_need_no_entry() -> None:
    tool = _load_tool()
    own = sorted(tool.OWN_OWNERS)[0]
    assert _errors({INDEX: "", "README.md": _url(f"{own}/anything")}) == []
    assert _errors({INDEX: "", "README.md": _url(f"{own.upper()}/Anything")}) == []


def test_the_index_alone_does_not_name_a_repository() -> None:
    assert _errors({INDEX: _url("acme/widget")}) == []


def test_a_binary_file_is_not_read() -> None:
    reference = _url("acme/widget").encode("utf-8")
    assert _errors({INDEX: "", "image.png": b"\x89PNG\x00\x00" + reference}) == []
    assert _errors({INDEX: "", "notes.txt": b"text " + reference}) == [
        "acme/widget has no entry in UPSTREAM.md: named in notes.txt"
    ]


def test_a_missing_index_is_an_error() -> None:
    assert _errors({"x.md": "nothing"}) == ["UPSTREAM.md is not a tracked file"]


# Omissions


def test_an_omission_with_a_reason_stands_in_for_an_entry() -> None:
    files = {INDEX: "", "run.sh": _url("acme/buildtool")}
    assert _errors(files, {"acme/buildtool": "build tool that run.sh downloads by digest"}) == []


def test_an_omission_needs_a_reason() -> None:
    files = {INDEX: "", "run.sh": _url("acme/buildtool")}
    for reason in ("", "   "):
        assert _errors(files, {"acme/buildtool": reason}) == ["omission acme/buildtool has no reason"]


def test_an_omission_that_the_index_links_is_reported() -> None:
    files = {INDEX: _url("acme/buildtool"), "run.sh": _url("acme/buildtool")}
    assert _errors(files, {"acme/buildtool": "build tool"}) == [
        "omission acme/buildtool is linked in UPSTREAM.md: keep the entry or the omission"
    ]


def test_an_omission_that_no_file_names_any_more_is_reported() -> None:
    assert _errors({INDEX: "", "run.sh": "echo done"}, {"acme/buildtool": "build tool"}) == [
        "omission acme/buildtool is named in no tracked file: remove it"
    ]


@pytest.mark.parametrize("key", ["Acme/BuildTool", "acme", "acme/buildtool/extra", _url("acme/buildtool")])
def test_an_omission_is_written_as_lower_case_owner_and_repository(key: str) -> None:
    files = {INDEX: "", "run.sh": _url("acme/buildtool")}
    errors = _errors(files, {key: "build tool"})
    assert f"omission {key} is not written as lower-case owner/repository" in errors, errors


# The tracked surface


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _repository(tmp_path: Path, files: dict[str, str]) -> None:
    _git(tmp_path, "init", "-q")
    for relative, content in files.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def _run_main(tool, root: Path, capsys) -> tuple[int, str, str]:
    with mock.patch.object(tool, "ROOT", root), mock.patch.object(sys, "argv", ["check_upstream_index.py"]):
        code = tool.main()
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_only_tracked_files_name_repositories(tmp_path: Path, capsys) -> None:
    tool = _load_tool()
    _repository(tmp_path, {INDEX: "# Upstream projects\n", "scratch/notes.md": _url("acme/widget")})
    _git(tmp_path, "add", INDEX)
    with mock.patch.object(tool, "OMISSIONS", {}):
        code, out, _ = _run_main(tool, tmp_path, capsys)
        assert (code, "Upstream index check passed" in out) == (0, True), out
        _git(tmp_path, "add", "scratch/notes.md")
        code, out, _ = _run_main(tool, tmp_path, capsys)
    assert code == 1
    assert "- acme/widget has no entry in UPSTREAM.md: named in scratch/notes.md" in out
    assert "tools/check_upstream_index.py" in out, "the failure says where an omission goes"


def test_a_tracked_file_deleted_from_the_tree_names_nothing(tmp_path: Path, capsys) -> None:
    tool = _load_tool()
    _repository(tmp_path, {INDEX: "# Upstream projects\n", "gone.md": _url("acme/widget")})
    _git(tmp_path, "add", INDEX, "gone.md")
    (tmp_path / "gone.md").unlink()
    with mock.patch.object(tool, "OMISSIONS", {}):
        code, out, _ = _run_main(tool, tmp_path, capsys)
    assert (code, "Upstream index check passed" in out) == (0, True), out


def test_git_inventory_failure_fails_closed(capsys) -> None:
    """A failed git inventory must fail the check, not pass on an empty file list."""
    tool = _load_tool()
    failed = subprocess.CompletedProcess(["git"], 128, b"", b"fatal: not a git repository")
    with mock.patch.object(tool.subprocess, "run", return_value=failed):
        code, _, err = _run_main(tool, ROOT, capsys)
    assert code == 1
    assert "git ls-files failed" in err
