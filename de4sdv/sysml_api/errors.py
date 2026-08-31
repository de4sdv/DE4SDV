"""SysML API error types."""

from __future__ import annotations


class SysMLApiError(RuntimeError):
    """Base error for the DE4SDV SysML API layer."""


class ApiError(SysMLApiError):
    """An HTTP or payload failure returned by a SysML API service."""

    def __init__(self, method: str, path: str, detail: str, *, status: int | None = None) -> None:
        self.method = method
        self.path = path
        self.status = status
        self.detail = detail
        prefix = f"{method} {path}"
        if status is not None:
            prefix += f" failed with HTTP {status}"
        else:
            prefix += " failed"
        super().__init__(f"{prefix}: {detail}")


class RevisionMismatchError(SysMLApiError):
    """The bound SysML commit is not known to represent the requested Git SHA."""


class BaselineImportError(SysMLApiError):
    """A production baseline import or exact readback verification failed."""


class IdentityResolutionError(SysMLApiError):
    """An element identity could not be resolved safely."""


class AmbiguousIdentityError(IdentityResolutionError):
    """More than one API element matches the supplied identity hints."""


class IdentityNotFoundError(IdentityResolutionError):
    """No API element matches the supplied identity hints."""
