import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

REPO = HERE.parents[3]
MODEL = REPO / "textual-notation-of-model" / "packages" / "features" / "driving"
