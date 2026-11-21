"""Paths the case evaluators' tests import by name: HERE, REPO and MODEL.

They live here, not in conftest.py, because pytest imports every test directory's conftest.py under the one
module name `conftest`. When the gcc13 gate collects the whole bench in one run, `from conftest import ...` can
bind to another directory's conftest (session/tests/test_bench_collection.py).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

REPO = HERE.parents[3]
MODEL = REPO / "textual-notation-of-model" / "packages" / "features" / "driving"
