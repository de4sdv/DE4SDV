#!/usr/bin/env python3
"""Export the bounded Gate A fixture with the official Syside serializer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.baseline import build_export_bundle
from tools.pleml_gate_a import gate_a_source_identity


def _relative_document_path(url: object) -> str:
    raw = str(url)
    parsed = urlparse(raw)
    candidate = Path(unquote(parsed.path if parsed.scheme == "file" else raw)).resolve()
    try:
        return candidate.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"Syside exported document outside repository: {raw}") from exc


def export_gate_a(output: Path) -> dict[str, object]:
    try:
        import syside  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Syside Automator is required; use the privileged Gate A workflow "
            "where its native package and license are available"
        ) from exc

    identity = gate_a_source_identity(ROOT)
    paths = [ROOT / str(source["path"]) for source in identity.source_manifest]
    model, diagnostics = syside.try_load_model(paths)
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise RuntimeError(f"Syside rejected the Gate A fixture:\n{diagnostics}")

    source_documents: dict[str, list[dict[str, object]]] = {}
    for document in model.user_docs:
        with document.lock() as locked:
            source_path = _relative_document_path(locked.url)
            serialized = syside.json.dumps(
                locked.root_node,
                syside.SerializationOptions.minimal(),
            )
        elements = json.loads(serialized)
        if not isinstance(elements, list) or not all(
            isinstance(element, dict) for element in elements
        ):
            raise RuntimeError(f"Syside JSON for {source_path} is not an element array")
        source_documents[source_path] = elements

    expected_paths = {str(source["path"]) for source in identity.source_manifest}
    actual_paths = set(source_documents)
    if expected_paths != actual_paths:
        raise RuntimeError(
            "Syside Gate A document coverage mismatch: "
            f"missing={sorted(expected_paths - actual_paths)}, "
            f"unexpected={sorted(actual_paths - expected_paths)}"
        )
    bundle = build_export_bundle(
        git_commit=identity.git_commit,
        source_documents=source_documents,
    )
    artifact = bundle.to_dict()
    artifact["source_manifest"] = list(identity.source_manifest)
    artifact["gate_a_identity"] = {
        "scope": identity.scope,
        "git_repository": identity.git_repository,
        "git_commit": identity.git_commit,
        "pleml_commit": identity.pleml_commit,
        "serializer": "Syside official minimal JSON",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        **artifact["gate_a_identity"],
        "document_count": len(source_documents),
        "element_count": len(bundle.elements),
        "external_reference_count": len(bundle.external_references),
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export_gate_a(args.output), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
