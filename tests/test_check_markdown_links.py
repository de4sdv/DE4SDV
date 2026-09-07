"""Behavioral tests for documentation local-link validation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_markdown_links.py"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_markdown_links", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_markdown_local_links_resolve() -> None:
    completed = subprocess.run(
        [sys.executable, str(TOOL)], cwd=ROOT, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Markdown local-link check passed" in completed.stdout


def test_broken_link_is_reported_with_file_and_line(tmp_path: Path) -> None:
    """The checker fails closed for a tree containing a broken link."""
    module = _load_tool()

    doc = tmp_path / "doc.md"
    doc.write_text(
        "intro\n\n[missing](./no-such-file.md)\n\n[remote](https://example.org)\n",
        encoding="utf-8",
    )
    # Point the module at the synthetic tree by patching ROOT.
    original_root = module.ROOT
    try:
        module.ROOT = tmp_path
        errors = module.broken_links(["doc.md"])
    finally:
        module.ROOT = original_root

    assert errors == ["doc.md:3: broken local link -> ./no-such-file.md"]
