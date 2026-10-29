"""Shared check of the public Ask viewer's served semantic authority.

``/ask-status.json`` reports ``.semantic_authority``. The viewer serves the
model-built contract after one startup check (exact commit, clean tree, the
same ``sai-`` identity recomputed from the checkout, the served model the
deployment binding records); a refused startup reports ``kind == "invalid"``
and the viewer refuses every semantic answer.

The expectation is never declared by an operator: it is read from the
deployment's own status document (``deployment-status.json``,
``baseline.semantic_authority.id``, ``baseline.served_model`` and, when the
deployment records them, ``baseline.export_documents``). The checks
use only fields every served runtime reports (``kind``, the ``sai-`` id under
``semantic_authority`` and the built runtime's ``semantic_authority_id``), so
the scheduled monitor also accepts a deployment from before the
release-ceremony retirement, whose status document records no served model.

Used by ``verify_public_api.py`` (post-deploy), ``verify_public_ask.py``
(Ask deploy) and ``monitor_public_ask.py`` (scheduled). Contract:
``deployment/README.md``, "Runtime contract".
"""
from __future__ import annotations

import re
from typing import Any

SEMANTIC_AUTHORITY_ID = re.compile(r"sai-[0-9a-f]{32}")
SERVED_MODEL_DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


class AuthorityCheckError(RuntimeError):
    """The served semantic authority is not the deployment's."""


def authority_block(ask_status: Any) -> dict[str, Any]:
    """The ``.semantic_authority`` block; ``invalid`` always refuses."""
    block = ask_status.get("semantic_authority") if isinstance(ask_status, dict) else None
    if not isinstance(block, dict):
        raise AuthorityCheckError("/ask-status.json carries no semantic_authority block")
    if block.get("kind") == "invalid":
        raise AuthorityCheckError(
            "the semantic runtime refused to start; every semantic answer is refused: "
            f"{block.get('error') or 'no reason given'}"
        )
    return block


def deployment_expectation(status_doc: Any, *, require_served_model: bool,
                           require_export_documents: bool = False) -> dict[str, Any]:
    """What the deployment says the viewer must serve (``deployment-status.json``)."""
    baseline = status_doc.get("baseline") if isinstance(status_doc, dict) else None
    if not isinstance(baseline, dict):
        raise AuthorityCheckError("deployment-status.json carries no baseline")
    authority = baseline.get("semantic_authority")
    identifier = authority.get("id") if isinstance(authority, dict) else None
    if not isinstance(identifier, str) or not SEMANTIC_AUTHORITY_ID.fullmatch(identifier):
        raise AuthorityCheckError(
            f"deployment-status baseline.semantic_authority.id is not sai-<32 hex>: {identifier!r}")
    served = baseline.get("served_model")
    digest = served.get("content_sha256") if isinstance(served, dict) else None
    if digest is not None and not (isinstance(digest, str) and SERVED_MODEL_DIGEST.fullmatch(digest)):
        raise AuthorityCheckError(
            f"deployment-status baseline.served_model.content_sha256 is malformed: {digest!r}")
    if require_served_model and digest is None:
        raise AuthorityCheckError(
            "deployment-status records no served model: the deployment predates the "
            "release-ceremony retirement; verify it with its own revision's verifier")
    documents = baseline.get("export_documents")
    documents_digest = documents.get("content_sha256") if isinstance(documents, dict) else None
    if documents is not None and not (isinstance(documents_digest, str)
                                      and SERVED_MODEL_DIGEST.fullmatch(documents_digest)):
        raise AuthorityCheckError(
            f"deployment-status baseline.export_documents.content_sha256 is malformed: {documents_digest!r}")
    if require_export_documents and documents_digest is None:
        raise AuthorityCheckError(
            "deployment-status records no export_documents: the deployment's binding was written by an "
            "importer that did not record them")
    return {"semantic_authority": identifier, "served_model": digest, "export_documents": documents_digest}


def check_served_authority(ask_status: Any, expectation: dict[str, Any], *,
                           require_built: bool = True) -> dict[str, Any]:
    """The viewer serves the deployment's semantic authority (and served model).

    ``require_built`` requires the runtime to be built (its
    ``semantic_authority_id`` is reported); a served-model check that failed
    always refuses.
    """
    block = authority_block(ask_status)
    if block.get("kind") != "model":
        raise AuthorityCheckError(f"semantic authority kind is {block.get('kind')!r}, expected 'model'")
    served_id = block.get("semantic_authority_id")
    if require_built and not served_id:
        raise AuthorityCheckError(
            "the semantic runtime is not built yet "
            f"(state {block.get('state') or 'unknown'!r})")
    if (require_built or "semantic_authority" in block) and \
            block.get("semantic_authority") != expectation["semantic_authority"]:
        raise AuthorityCheckError(
            f"the viewer serves semantic authority {block.get('semantic_authority')!r}, the "
            f"deployment records {expectation['semantic_authority']!r}")
    if expectation.get("served_model") is not None and require_built and \
            block.get("served_model") != expectation["served_model"]:
        raise AuthorityCheckError(
            f"the viewer's served model {block.get('served_model')!r} is not the deployment's "
            f"{expectation['served_model']!r}")
    if expectation.get("export_documents") is not None and require_built and \
            block.get("export_documents") != expectation["export_documents"]:
        raise AuthorityCheckError(
            f"the viewer's export documents {block.get('export_documents')!r} are not the deployment's "
            f"{expectation['export_documents']!r}")
    check = str(block.get("served_model_check") or "")
    if check.startswith("failed"):
        raise AuthorityCheckError(f"the served-model check failed: {check}")
    return block


__all__ = ["AuthorityCheckError", "authority_block", "check_served_authority",
           "deployment_expectation"]
