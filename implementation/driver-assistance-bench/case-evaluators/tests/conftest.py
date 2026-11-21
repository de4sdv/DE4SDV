"""Puts the case evaluators on the path for their tests.

Paths that tests import by name (HERE, REPO, MODEL) live in case_evaluators_testkit.py, never here: pytest
imports every test directory's conftest.py under the one module name `conftest`
(session/tests/test_bench_collection.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
