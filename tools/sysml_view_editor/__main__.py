"""Entry point for `python -m tools.sysml_view_editor`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
