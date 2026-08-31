"""Binding between reviewed Git and parsed SysML repository revisions."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .errors import RevisionMismatchError

BindingStatus = Literal["synchronized", "stale", "unvalidated"]
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RevisionBinding:
    git_repository: str
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    import_timestamp: str
    import_tool_version: str
    semantic_validation: str
    scope: str = "full-model"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RevisionBinding":
        required = {
            "git_repository",
            "git_commit",
            "sysml_project_id",
            "sysml_commit_id",
            "import_timestamp",
            "import_tool_version",
            "semantic_validation",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(f"revision binding missing fields: {missing}")
        git_commit = str(value["git_commit"])
        if not _FULL_SHA.fullmatch(git_commit):
            raise ValueError("git_commit must be a full 40-character lowercase SHA")
        return cls(
            git_repository=str(value["git_repository"]),
            git_commit=git_commit,
            sysml_project_id=str(value["sysml_project_id"]),
            sysml_commit_id=str(value["sysml_commit_id"]),
            import_timestamp=str(value["import_timestamp"]),
            import_tool_version=str(value["import_tool_version"]),
            semantic_validation=str(value["semantic_validation"]),
            scope=str(value.get("scope", "full-model")),
        )

    @classmethod
    def load(cls, path: Path) -> "RevisionBinding":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("revision binding must be a JSON object")
        return cls.from_dict(value)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def status(self, git_revision: str) -> BindingStatus:
        if self.semantic_validation != "passed":
            return "unvalidated"
        if git_revision != self.git_commit:
            return "stale"
        return "synchronized"

    def require_current(self, git_revision: str) -> None:
        status = self.status(git_revision)
        if status != "synchronized":
            raise RevisionMismatchError(
                "SysML binding is "
                f"{status}: Git {git_revision} is not a validated binding to "
                f"project {self.sysml_project_id} commit {self.sysml_commit_id}"
            )