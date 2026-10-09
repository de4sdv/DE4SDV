"""Isolation of the test suite from the user's environment."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _snapshots_in_the_tests_temporary_directory(tmp_path):
    """Corpus snapshots (and the servers the tests start) use the test's own directory, never ~/.cache.

    The fixture has its own patcher, so a test that calls ``monkeypatch.undo()`` keeps it.
    """
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DE4SDV_SEMANTIC_SNAPSHOT_DIR", str(tmp_path / "semantic-snapshots"))
        yield
