#!/usr/bin/env python3
"""Export the reviewed DE4SDV baseline with the official Syside serializer.

This script intentionally imports Syside only at runtime. Syside is the textual
parser/semantic engine; this repository only adapts its standard JSON output to
the Systems Modeling API Services commit format.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.baseline import BaselineManifest, build_export_bundle


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


#: Systems Model Library anchors the v1.1 grounding rule requires the
#: read-back to prove. Resolved at export time by the licensed toolchain from
#: a library-inclusive serialization (same load context as the model, so the
#: ids match the ones referenced by implied relationships).
_LIBRARY_ANCHOR_NAMES = ("VerificationCase", "verificationCases")
_VERIFICATION_CASES_DOCUMENT = "Systems Library/VerificationCases.sysml"


def _serialization_options():
    """Minimal JSON plus implied relationships.

    ``minimal()`` documents that it excludes implied relationships; the v1.1
    grounding proof requires the SysML-implied library specializations
    (``checkVerificationCaseDefinitionSpecialization`` and the
    ``verificationCases`` subsetting) to be present in the closure, so the
    licensed serializer is asked to include them (KerML 10.3
    ``includesImplied``).
    """
    import syside  # type: ignore[import-not-found]

    return syside.SerializationOptions.minimal().with_options(include_implied=True)


def _resolve_library_anchors(model) -> dict[str, str]:
    """Resolve the VerificationCases library anchor ids by name."""
    import syside  # type: ignore[import-not-found]

    anchors: dict[str, str] = {}
    for document in model.all_docs:
        with document.lock() as locked:
            url = unquote(str(getattr(locked, "url", "")))
            if not url.endswith(_VERIFICATION_CASES_DOCUMENT):
                continue
            serialized = syside.json.dumps(
                locked.root_node, syside.SerializationOptions.minimal()
            )
        for element in json.loads(serialized):
            name = str(element.get("declaredName") or "")
            if name in _LIBRARY_ANCHOR_NAMES and element.get("@id"):
                anchors[f"VerificationCases::{name}"] = str(element["@id"])
    return anchors


def _relative_document_path(url: object) -> str:
    raw = str(url)
    parsed = urlparse(raw)
    candidate = Path(unquote(parsed.path if parsed.scheme == "file" else raw)).resolve()
    try:
        return candidate.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"Syside exported document outside repository: {raw}") from exc


def export_baseline(output: Path, git_commit: str) -> dict[str, object]:
    try:
        import syside  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Syside Automator is required for production export; use the privileged "
            "workflow on platforms where its native package is unavailable"
        ) from exc

    if git_commit != _git_head():
        raise RuntimeError(
            f"requested Git commit {git_commit} does not match checked-out HEAD {_git_head()}"
        )
    manifest = BaselineManifest.discover(ROOT)
    paths = [ROOT / source.path for source in manifest.sources]
    model, diagnostics = syside.try_load_model(paths)
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise RuntimeError(f"Syside rejected the reviewed baseline:\n{diagnostics}")

    serialization_options = _serialization_options()
    library_anchors = _resolve_library_anchors(model)
    missing_anchors = sorted(
        f"VerificationCases::{name}"
        for name in _LIBRARY_ANCHOR_NAMES
        if f"VerificationCases::{name}" not in library_anchors
    )
    if missing_anchors:
        raise RuntimeError(
            "could not resolve Systems Model Library anchor ids (pinned "
            f"toolchain closure incomplete): {missing_anchors}"
        )

    source_documents: dict[str, list[dict[str, object]]] = {}
    for document in model.user_docs:
        with document.lock() as locked:
            source_path = _relative_document_path(locked.url)
            serialized = syside.json.dumps(
                locked.root_node,
                serialization_options,
            )
        elements = json.loads(serialized)
        if not isinstance(elements, list) or not all(
            isinstance(element, dict) for element in elements
        ):
            raise RuntimeError(f"Syside JSON for {source_path} is not an element array")
        source_documents[source_path] = elements

    expected_paths = {source.path for source in manifest.sources}
    actual_paths = set(source_documents)
    if expected_paths != actual_paths:
        raise RuntimeError(
            "Syside document coverage mismatch: "
            f"missing={sorted(expected_paths - actual_paths)}, "
            f"unexpected={sorted(actual_paths - expected_paths)}"
        )
    bundle = build_export_bundle(
        git_commit=git_commit,
        source_documents=source_documents,
    )
    artifact = bundle.to_dict()
    artifact["source_manifest"] = list(manifest.to_dicts())
    artifact["library_anchors"] = dict(library_anchors)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "git_commit": git_commit,
        "document_count": len(source_documents),
        "element_count": len(bundle.elements),
        "external_reference_count": len(bundle.external_references),
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--git-commit", default=None)
    args = parser.parse_args()
    result = export_baseline(args.output, args.git_commit or _git_head())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
