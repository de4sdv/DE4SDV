"""Access to the pinned upstream AutoE2E navigation code, read-only.

The upstream sources live in ``.upstream/`` (a clone of
github.com/autowarefoundation/auto_e2e at ``UPSTREAM_COMMIT``) and are never
modified.  This module does two things:

* registers the upstream ``Model/navigation`` directory as the package
  ``navigation`` without executing its ``__init__.py`` (which pulls training
  code in), so ``navigation.contracts``, ``navigation.geometry`` and
  ``navigation.rasterizer`` can be imported as upstream defines them;
* locates the native rasterizer shared library built as-is from
  ``Model/navigation/native/``.

Environment overrides: ``AUTO_E2E_ROOT`` (directory holding ``Model/``) and
``AUTO_E2E_NAVIGATION_RASTERIZER_LIBRARY`` (the .so path, honoured by upstream's
``rasterizer._library_candidates`` too).
"""

from __future__ import annotations

import importlib
import os
import sys
import types
from pathlib import Path

UPSTREAM_REPOSITORY = "https://github.com/autowarefoundation/auto_e2e"
UPSTREAM_COMMIT = "cb50764b8250a3c44ee5b79b87ba02c5a83b0c91"
NAVIGATION_PACKAGE = "navigation"

HERE = Path(__file__).resolve().parent


def upstream_root() -> Path:
    """Directory holding the upstream ``Model/`` tree."""
    configured = os.environ.get("AUTO_E2E_ROOT")
    root = Path(configured) if configured else HERE / ".upstream"
    model = root / "Model"
    if not (model / "navigation" / "contracts.py").is_file():
        raise RuntimeError(
            f"upstream AutoE2E sources not found under {root}; clone "
            f"{UPSTREAM_REPOSITORY} and check out {UPSTREAM_COMMIT} there, or "
            "set AUTO_E2E_ROOT"
        )
    return root


def navigation_directory() -> Path:
    return upstream_root() / "Model" / "navigation"


def _register_package() -> None:
    """Make ``import navigation.<module>`` resolve to the upstream directory."""
    existing = sys.modules.get(NAVIGATION_PACKAGE)
    directory = str(navigation_directory())
    if isinstance(existing, types.ModuleType) and list(
        getattr(existing, "__path__", [])
    ) == [directory]:
        return
    package = types.ModuleType(NAVIGATION_PACKAGE)
    package.__path__ = [directory]
    package.__file__ = str(Path(directory) / "__init__.py")
    sys.modules[NAVIGATION_PACKAGE] = package


def module(name: str):
    """Import one upstream navigation module (``contracts``, ``geometry``...)."""
    _register_package()
    return importlib.import_module(f"{NAVIGATION_PACKAGE}.{name}")


def contracts():
    return module("contracts")


def geometry():
    return module("geometry")


def rasterizer():
    return module("rasterizer")


def native_library_path() -> Path:
    """The shared library built from the upstream native sources, as-is."""
    configured = os.environ.get("AUTO_E2E_NAVIGATION_RASTERIZER_LIBRARY")
    if configured:
        return Path(configured)
    return HERE / "build" / "libnavigation_rasterizer.so"


def require_native_library() -> Path:
    path = native_library_path()
    if not path.is_file():
        raise RuntimeError(
            f"native rasterizer library missing at {path}; run `make "
            "native` (builds it with upstream's own build.py, unmodified)"
        )
    # Keep upstream's loader pointed at the same file.
    os.environ.setdefault("AUTO_E2E_NAVIGATION_RASTERIZER_LIBRARY", str(path))
    return path
