"""Binding between reviewed Git and parsed SysML repository revisions."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .errors import RevisionMismatchError

BindingStatus = Literal["synchronized", "stale", "unvalidated"]
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class OntologyIdentity:
    """Immutable identity of the executable ontology contract."""

    path: str
    sha256: str

    @classmethod
    def from_dict(cls, value: object) -> "OntologyIdentity":
        if not isinstance(value, dict):
            raise ValueError("revision binding ontology must be a JSON object")
        path = str(value.get("path") or "")
        digest = str(value.get("sha256") or "")
        if not path:
            raise ValueError("revision binding ontology.path is required")
        if not _SHA256.fullmatch(digest):
            raise ValueError("revision binding ontology.sha256 must be a lowercase SHA-256")
        return cls(path=path, sha256=digest)

    @classmethod
    def from_file(cls, path: Path, *, repository_root: Path) -> "OntologyIdentity":
        resolved = path.resolve()
        try:
            source = resolved.relative_to(repository_root.resolve()).as_posix()
        except ValueError:
            source = resolved.as_posix()
        return cls(path=source, sha256=hashlib.sha256(resolved.read_bytes()).hexdigest())

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


SEMANTIC_AUTHORITY_SCHEMA = "de4sdv.semantic-authority/v1"
_AUTHORITY_ID = re.compile(r"^sai-[0-9a-f]{32}$")
_LAYER_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class SemanticAuthorityIdentity:
    """Identity of the model-built semantic contract (O4 Wave C2).

    ``id`` digests the contract content (class and relationship mappings,
    refusals) together with ``layers``: the repository path and sha256 of
    every model-generated projection/profile file and frozen O2-chain record
    the contract is built from. Two contracts are the same authority exactly
    when their identities are equal.
    """

    schema: str
    id: str
    layers: tuple[tuple[str, str], ...]

    @classmethod
    def from_dict(cls, value: object) -> "SemanticAuthorityIdentity":
        if not isinstance(value, dict):
            raise ValueError("semantic_authority must be a JSON object")
        if set(value) != {"schema", "id", "layers"}:
            raise ValueError("semantic_authority must carry exactly schema, id and layers")
        if value.get("schema") != SEMANTIC_AUTHORITY_SCHEMA:
            raise ValueError(
                f"semantic_authority.schema must be {SEMANTIC_AUTHORITY_SCHEMA}")
        identifier = str(value.get("id") or "")
        if not _AUTHORITY_ID.fullmatch(identifier):
            raise ValueError("semantic_authority.id must be sai-<32 lowercase hex>")
        raw_layers = value.get("layers")
        if not isinstance(raw_layers, list) or not raw_layers:
            raise ValueError("semantic_authority.layers must be a non-empty list")
        layers = []
        for item in raw_layers:
            if (not isinstance(item, dict) or set(item) != {"path", "sha256"}
                    or not isinstance(item.get("path"), str) or not item["path"]
                    or not _LAYER_DIGEST.fullmatch(str(item.get("sha256") or ""))):
                raise ValueError("semantic_authority layer must be {path, sha256:<64 hex>}")
            layers.append((item["path"], item["sha256"]))
        if len({path for path, _ in layers}) != len(layers):
            raise ValueError("semantic_authority layers must not repeat a path")
        return cls(schema=SEMANTIC_AUTHORITY_SCHEMA, id=identifier, layers=tuple(layers))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "id": self.id,
                "layers": [{"path": path, "sha256": digest} for path, digest in self.layers]}


@dataclass(frozen=True)
class KernelElementBinding:
    """One ingestion-validated kernel identity for a file-mapped ontology class.

    Produced by ontology/API binding validation at ingestion time: the
    serializer-recorded source document pins the exact API element that
    carries the governed declaration. Runtime consumers use these UUIDs
    directly and never re-derive identity from names or source text.
    """

    ontology_class: str
    element_id: str
    source_file: str
    declaration: str

    @classmethod
    def from_dict(cls, value: object) -> "KernelElementBinding":
        if not isinstance(value, dict):
            raise ValueError("kernel binding must be a JSON object")
        for field in ("ontology_class", "element_id", "source_file", "declaration"):
            if not str(value.get(field) or ""):
                raise ValueError(f"kernel binding {field} is required")
        return cls(
            ontology_class=str(value["ontology_class"]),
            element_id=str(value["element_id"]),
            source_file=str(value["source_file"]),
            declaration=str(value["declaration"]),
        )


@dataclass(frozen=True)
class RevisionBinding:
    git_repository: str
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    import_timestamp: str
    import_tool_version: str
    semantic_validation: str
    ontology: OntologyIdentity
    scope: str = "full-model"
    kernel_bindings: tuple[KernelElementBinding, ...] = ()

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
            "ontology",
        }
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(f"revision binding missing fields: {missing}")
        git_commit = str(value["git_commit"])
        if not _FULL_SHA.fullmatch(git_commit):
            raise ValueError("git_commit must be a full 40-character lowercase SHA")
        raw_kernel_bindings = value.get("kernel_bindings", ())
        if not isinstance(raw_kernel_bindings, (list, tuple)):
            raise ValueError("revision binding kernel_bindings must be a list")
        return cls(
            git_repository=str(value["git_repository"]),
            git_commit=git_commit,
            sysml_project_id=str(value["sysml_project_id"]),
            sysml_commit_id=str(value["sysml_commit_id"]),
            import_timestamp=str(value["import_timestamp"]),
            import_tool_version=str(value["import_tool_version"]),
            semantic_validation=str(value["semantic_validation"]),
            ontology=OntologyIdentity.from_dict(value["ontology"]),
            scope=str(value.get("scope", "full-model")),
            kernel_bindings=tuple(
                KernelElementBinding.from_dict(item)
                for item in raw_kernel_bindings
            ),
        )

    @classmethod
    def load(cls, path: Path) -> "RevisionBinding":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("revision binding must be a JSON object")
        return cls.from_dict(value)

    def to_dict(self) -> dict[str, Any]:
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

    def require_ontology(self, ontology: OntologyIdentity) -> None:
        if ontology != self.ontology:
            raise RevisionMismatchError(
                "ontology contract mismatch: validated binding requires "
                f"{self.ontology.path} sha256:{self.ontology.sha256}, executed "
                f"{ontology.path} sha256:{ontology.sha256}"
            )