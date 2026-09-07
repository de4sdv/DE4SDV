"""Behavioral tests for documentation local-link validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_markdown_links.py"


def _load_tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_markdown_links", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_markdown_local_links_resolve() -> None:
    """The committed corpus passes against the real tracked surface."""
    completed = subprocess.run(
        [sys.executable, str(TOOL)], cwd=ROOT, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Markdown local-link check passed" in completed.stdout


import contextlib


@contextlib.contextmanager
def _scenario(tmp_path: Path, files: dict[str, str], tracked: set[str]):
    module = _load_tool()
    for relative, content in files.items():
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    original_root = module.ROOT
    try:
        module.ROOT = tmp_path
        errors = module.broken_links(
            [name for name in files if name.endswith(".md")],
            tracked=frozenset(tracked),
        )
        yield errors
    finally:
        module.ROOT = original_root


def test_tracked_relative_file_passes(tmp_path: Path) -> None:
    with _scenario(
        tmp_path,
        {
            "docs/doc.md": "[target](./target.md)\n",
            "docs/target.md": "exists\n",
        },
        {"docs/doc.md", "docs/target.md"},
    ) as errors:
        assert errors == [], errors


def test_missing_file_fails(tmp_path: Path) -> None:
    with _scenario(
        tmp_path,
        {"docs/doc.md": "[missing](./no-such-file.md)\n"},
        {"docs/doc.md"},
    ) as errors:
        assert errors == ["docs/doc.md:1: broken local link -> ./no-such-file.md (resolved docs/no-such-file.md is not tracked repository content)"], errors


def test_existing_but_untracked_file_fails(tmp_path: Path) -> None:
    """A local file that exists but is not tracked must not satisfy a link."""
    with _scenario(
        tmp_path,
        {
            "docs/doc.md": "[target](./untracked.md)\n",
            "docs/untracked.md": "exists locally, not tracked\n",
        },
        {"docs/doc.md"},  # untracked.md deliberately absent from the surface
    ) as errors:
        assert len(errors) == 1, errors
        assert "untracked.md" in errors[0]
        assert "not tracked repository content" in errors[0]


def test_repository_root_escape_fails(tmp_path: Path) -> None:
    """A link escaping the repo fails even when the outside file exists."""
    outside = tmp_path / "outside-repository-file.md"
    outside.write_text("beyond the root\n", encoding="utf-8")
    with _scenario(
        tmp_path,
        {
            "docs/doc.md": "[escape](../../../../outside-repository-file.md)\n",
        },
        {"docs/doc.md", "outside-repository-file.md"},
    ) as errors:
        assert len(errors) == 1, errors
        assert "escapes repository root" in errors[0]


def test_url_decoded_paths_continue_to_work(tmp_path: Path) -> None:
    with _scenario(
        tmp_path,
        {
            "docs/my doc.md": "exists\n",
            "docs/doc.md": "[decoded](my%20doc.md)\n",
        },
        {"docs/my doc.md", "docs/doc.md"},
    ) as errors:
        assert errors == [], errors


def test_fragment_and_query_stripping(tmp_path: Path) -> None:
    with _scenario(
        tmp_path,
        {
            "docs/target.md": "exists\n",
            "docs/doc.md": (
                "[fragment](./target.md#section)\n"
                "[query](./target.md?download=1)\n"
                "[both](./target.md?download=1#section)\n"
            ),
        },
        {"docs/target.md", "docs/doc.md"},
    ) as errors:
        assert errors == [], errors


def test_tracked_directory_link_passes_and_empty_directory_fails(
    tmp_path: Path,
) -> None:
    """Directory links resolve when tracked content lies beneath them."""
    with _scenario(
        tmp_path,
        {
            "docs/doc.md": "[dir](./sub/)\n",
            "docs/sub/file.md": "tracked content beneath sub\n",
        },
        {"docs/doc.md", "docs/sub/file.md"},
    ) as errors:
        assert errors == [], errors
    with _scenario(
        tmp_path,
        {"docs/doc.md": "[dir](./empty/)\n"},
        {"docs/doc.md"},
    ) as errors:
        assert len(errors) == 1, errors
        assert "no tracked content beneath" in errors[0]
