"""Isolation of the test suite from the user's environment."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _snapshots_in_the_tests_temporary_directory(tmp_path, monkeypatch) -> None:
    """Corpus snapshots (and the servers the tests start) use the test's own directory, never ~/.cache."""
    monkeypatch.setenv("DE4SDV_SEMANTIC_SNAPSHOT_DIR", str(tmp_path / "semantic-snapshots"))
