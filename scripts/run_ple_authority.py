#!/usr/bin/env python3
"""Licensed validation, serialization and API round trip of the PLEML feature models.

This is the runner of the PLE authority job (ADR 0022, the former PLE-S
workflow). Licensed mode loads the reviewed model roots, the pinned PLEML
library, the three PLEML feature models, their configurations and the invalid
fixture in one model with the pinned serializer and refuses any error
diagnostic. It serializes every document once with the production export's
options, validates the governed product-line scope exactly as production
does, builds the authority bundle (the PLEML documents, the shared-asset
supersets, the governed scope and the library), imports it into an ephemeral
SysML v2 API and verifies the full-payload readback. It then hands the bundle
to the DE4SDV evaluator (ADR 0022, step S2), which writes the receipts.

The models are fenced until the authority switch (step S6). Nothing here
executes a PLEML constraint body natively, qualifies anything or claims
compliance; every record says ``qualified: false``.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import lzma
import platform
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.sysml_api.baseline import BaselineExportBundle, BaselineManifest, build_export_bundle
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.ingestion import import_baseline
from de4sdv.sysml_api.product_line_scope import validate_scope_elements
from de4sdv.sysml_api.repository import element_id
from scripts.run_ple_qualification import PLEML_1_1_0, SERIALIZER_VERSION, digest, git, verified_file

PLE = "model-based-product-line-engineering"
#: The PLEML feature models: one per family (ADR 0022, decision 2).
FEATURE_MODELS = (
    f"{PLE}/feature-models/sdv_product_line.sysml",
    f"{PLE}/feature-models/engineering_execution_environments.sysml",
    f"{PLE}/feature-models/vehicle_execution_environments.sysml",
)
#: One PLEML configuration per committed bill of features.
CONFIGURATIONS = (
    f"{PLE}/feature-configurations/aebs_autoware_linux_lidar_camera.sysml",
    f"{PLE}/feature-configurations/middleware_autoware_aaos_sdv_reference.sysml",
    f"{PLE}/feature-configurations/example_linux_score_autoware.sysml",
    f"{PLE}/feature-configurations/apollo_qnx_qvm.sysml",
    f"{PLE}/feature-configurations/inc_aebs_009a_jetson.sysml",
    f"{PLE}/feature-configurations/apple_silicon_macos_candidate.sysml",
    f"{PLE}/feature-configurations/nxp_zephyr_vehicle_target_candidate.sysml",
)
#: The authority roots: the feature models and the member configurations.
AUTHORITY_SOURCES = FEATURE_MODELS + CONFIGURATIONS
#: The invalid fixture: validated and serialized, never an authority root.
FIXTURES = (f"{PLE}/feature-configurations/fixtures/invalid_score_android.sysml",)
#: Reviewed documents the PLEML models reference: the shared-asset supersets
#: their bindings and derivations target, the governed scope their
#: correspondences target, and the kernel definitions of their derivation
#: rules and projection metadata (ADR 0022, step S2k).
REFERENCED_SOURCES = (
    "textual-notation-of-model/packages/architecture/sdv_platform_stack.sysml",
    "textual-notation-of-model/packages/architecture/execution_environments.sysml",
    f"{PLE}/scoping/de4sdv_aebs_product_line_scope.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line_derivation.sysml",
)

#: The pinned PLEML library this revision validates with. It is the only
#: place that names the provisioning, which moves to the Sysand lock at
#: step S1 (`=1.1.1`, byte-checked against the release tag). Until then the
#: library is the frozen experiment's PLEML 1.1.0 (tag pleml-1.1.0-frozen),
#: whose content equals 1.1.1 apart from its version line.
LIBRARY = {
    "provisioning": "frozen-experiment",
    "label": PLEML_1_1_0.library,
    "version": "1.1.0",
    "sha256": PLEML_1_1_0.library_sha256,
    "experiment_revision": PLEML_1_1_0.revision,
    "pleml_pin": PLEML_1_1_0.pleml_pin,
}


def verify_library(path: Path) -> bytes:
    """The pinned library's bytes, refused unless they are exactly the pinned ones.

    The frozen experiment is relocated outside the executor checkout, so a
    library inside it is refused.
    """
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("the pinned library must be read from outside the executor checkout")
    data = path.read_bytes()
    if digest(data) != LIBRARY["sha256"]:
        raise ValueError("the PLEML library differs from the pinned bytes")
    return data

EXECUTOR_INPUTS = (
    "scripts/run_ple_authority.py",
    "scripts/run_ple_qualification.py",
    "scripts/export_sysml_api_baseline.py",
    "de4sdv/sysml_api/baseline.py",
    "de4sdv/sysml_api/client.py",
    "de4sdv/sysml_api/ingestion.py",
    "de4sdv/sysml_api/product_line_scope.py",
    "de4sdv/sysml_api/repository.py",
    "sysand-lock.toml",
    *AUTHORITY_SOURCES,
    *FIXTURES,
)
RUN_SCHEMA = "de4sdv.ple-authority-run/v1"
ELEMENTS = "authority-elements.json"
API_PROJECT = "DE4SDV isolated PLE authority round trip"
#: The production import's request timeout (scripts/import_sysml_api_baseline.py).
#: The API commits the authority bundle in one request, which outlasts the
#: client's 30-second default (run 39244883381).
API_TIMEOUT_SECONDS = 600.0

Documents = dict[str, list[dict[str, Any]]]


class EvaluatorPending(RuntimeError):
    """The evaluator of ADR 0022 step S2 is not on this revision yet."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--licensed", action="store_true",
                        help="fresh serialization with the pinned licensed serializer on the x86_64 runner")
    parser.add_argument("--library", type=Path, required=True,
                        help="the pinned PLEML.sysml, outside this checkout")
    parser.add_argument("--expected-executor", required=True, help="exact executor SHA")
    parser.add_argument("--api-url", required=True, help="ephemeral loopback SysML v2 API, e.g. http://127.0.0.1:9000")
    parser.add_argument("--out", type=Path, required=True,
                        help="output directory; must not exist and must be outside the repository")
    return parser


def document_label(url: object, library_path: Path) -> str:
    """The source label of a serialized document: repository-relative, or the pinned library."""
    parsed = urlparse(str(url))
    candidate = Path(unquote(parsed.path if parsed.scheme == "file" else str(url))).resolve()
    if candidate == library_path.resolve():
        return LIBRARY["label"]
    try:
        return candidate.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"serializer produced a document outside the reviewed sources: {url}") from exc


def _element_array(serialized: str, label: str) -> list[dict[str, Any]]:
    values = json.loads(serialized)
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ValueError(f"serializer did not produce an element array for {label}")
    return values


def serialize(library_path: Path, out: Path) -> tuple[Documents, BaselineManifest, str]:
    """Load the reviewed roots, the library and the PLEML documents in one model; serialize once.

    Every document is serialized with the production export's options, so the
    governed scope is validated, and the PLEML documents are evaluated, on the
    shapes the served model carries.
    """
    if platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("licensed Syside requires the supported x86_64 runner; not executed on this host")
    syside = importlib.import_module("syside")
    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError("installed serializer differs from the reviewed pin")
    from scripts.export_sysml_api_baseline import _serialization_options as production_options

    manifest = BaselineManifest.discover(ROOT)
    pleml = (*AUTHORITY_SOURCES, *FIXTURES)
    paths = [ROOT / source.path for source in manifest.sources] + [library_path] + [ROOT / p for p in pleml]
    model, diagnostics = syside.try_load_model(paths)
    (out / "serializer-diagnostics.txt").write_text(str(diagnostics) + "\n")
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError(
            "the serializer rejected the reviewed roots with the pinned library and the "
            "PLEML documents; see serializer-diagnostics.txt"
        )
    options = production_options()
    documents: Documents = {}
    for document in model.user_docs:
        with document.lock() as locked:
            label = document_label(locked.url, library_path)
            if label in documents:
                raise ValueError(f"serializer repeated a source document: {label}")
            documents[label] = _element_array(syside.json.dumps(locked.root_node, options), label)
    expected = {source.path for source in manifest.sources} | {LIBRARY["label"], *pleml}
    if set(documents) != expected:
        raise ValueError(
            "serializer source coverage mismatch: "
            f"missing={sorted(expected - set(documents))}, unexpected={sorted(set(documents) - expected)}"
        )
    return documents, manifest, version


def flatten(documents: Documents) -> tuple[list[dict[str, Any]], dict[str, str]]:
    elements: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    for label, values in documents.items():
        for element in values:
            identifier = element_id(element)
            if not identifier:
                raise ValueError(f"serialized element without identity in {label}")
            if identifier in sources:
                raise ValueError(f"serialized element identity repeated across documents: {identifier}")
            sources[identifier] = label
            elements.append(element)
    return elements, sources


def _authority_role(path: str) -> str:
    if path == LIBRARY["label"]:
        return "pinned-pleml-library"
    if path in FEATURE_MODELS:
        return "pleml-feature-model"
    if path in CONFIGURATIONS:
        return "pleml-feature-configuration"
    if path in FIXTURES:
        return "pleml-fixture"
    return "reviewed"


def _repository_bytes(label: str) -> bytes:
    return (ROOT / label).read_bytes()


def authority_bundle(documents: Documents, executor: str, library_bytes: bytes,
                     read=_repository_bytes) -> BaselineExportBundle:
    """The authority documents as one export bundle, with their source manifest.

    References that leave the bundle (the kernel and standard library) are
    pruned and recorded by the production bundle builder; nothing is
    reconstructed from text.
    """
    labels = (LIBRARY["label"], *AUTHORITY_SOURCES, *FIXTURES, *REFERENCED_SOURCES)
    missing = [label for label in labels if label not in documents]
    if missing:
        raise ValueError(f"authority documents missing from the serialization: {missing}")
    bundle = build_export_bundle(git_commit=executor, source_documents={label: documents[label] for label in labels})
    manifest = []
    for label in labels:
        data = library_bytes if label == LIBRARY["label"] else read(label)
        manifest.append({"path": label, "authority": _authority_role(label), "sha256": digest(data), "size": len(data)})
    raw = bundle.to_dict()
    raw["source_manifest"] = manifest
    return BaselineExportBundle.from_dict(raw)


def round_trip(bundle: BaselineExportBundle, api_url: str) -> dict[str, Any]:
    """Import the bundle into the ephemeral API and verify the full-payload readback.

    ``import_baseline`` is the production import: it refuses a readback whose
    element identities, internal references or element payloads differ.
    """
    if re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}", api_url) is None or not 1 <= int(api_url.rsplit(":", 1)[1]) <= 65535:
        raise ValueError("the round trip may write only to an ephemeral loopback API")
    imported = import_baseline(ApiClient(api_url, timeout=API_TIMEOUT_SECONDS), bundle, project_name=API_PROJECT)
    return {
        "verified": True,
        "check": "full-payload readback: element identities, internal references and element payloads",
        "project_id": imported.project_id,
        "commit_id": imported.commit_id,
        "element_count": imported.element_count,
        "internal_reference_count": imported.internal_reference_count,
        "content_sha256": imported.content_sha256,
        "external_reference_count": len(bundle.external_references),
    }


def evaluate(bundle: BaselineExportBundle, scope: dict[str, Any], out: Path) -> dict[str, Any]:
    """Hand the authority bundle to the DE4SDV evaluator, which writes the receipts.

    The runner's only coupling to the evaluator and derivation module of
    ADR 0022 step S2. That module is not on this revision yet, so the
    licensed run stops here, after the validation, the serialization and the
    round trip, and writes no receipt.
    """
    raise EvaluatorPending(
        "the evaluator of ADR 0022 step S2 is not on this revision: the serialization and the API "
        "round trip passed, and the receipts are pending"
    )


def _write_elements(bundle: BaselineExportBundle, out: Path) -> dict[str, str]:
    text = json.dumps(bundle.to_dict(), indent=2, sort_keys=True) + "\n"
    (out / ELEMENTS).write_text(text, encoding="utf-8")
    compressed = lzma.compress(text.encode("utf-8"), preset=9)
    (out / f"{ELEMENTS}.xz").write_bytes(compressed)
    return {"json_sha256": digest(text.encode("utf-8")), "xz_sha256": digest(compressed)}


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    out: Path = args.out
    if out.exists():
        raise ValueError("refusing to overwrite an existing output directory")
    if out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("output must be outside the repository")
    if not args.licensed:
        raise ValueError("only --licensed is supported; the offline replay is the evaluator's (ADR 0022, step S2)")
    library_path: Path = args.library
    executor = git(ROOT, "rev-parse", "HEAD")
    if re.fullmatch(r"[0-9a-f]{40}", args.expected_executor) is None or args.expected_executor != executor:
        raise ValueError("licensed mode requires the exact executor SHA")
    if git(ROOT, "status", "--porcelain"):
        raise ValueError("the executor checkout is not clean")
    library_bytes = verify_library(library_path)
    executor_inputs = {relative: verified_file(ROOT, executor, relative) for relative in EXECUTOR_INPUTS}

    out.mkdir(parents=True)
    record: dict[str, Any] = {
        "schema": RUN_SCHEMA,
        "mode": "licensed-serialization",
        "executor_revision": executor,
        "executor_source_dirty": False,
        "executor_inputs": executor_inputs,
        "library": {**LIBRARY, "sha256": digest(library_bytes)},
        "authority_sources": list(AUTHORITY_SOURCES),
        "fixtures": list(FIXTURES),
        "referenced_sources": list(REFERENCED_SOURCES),
        "qualified": False,
        "native_expression_executed": False,
        "authority_effective": False,
    }
    documents, manifest, version = serialize(library_path, out)
    production = {label: values for label, values in documents.items()
                  if label in {source.path for source in manifest.sources}}
    scope = validate_scope_elements(*flatten(production))
    (out / "governed-scope-validation.json").write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n")
    bundle = authority_bundle(documents, executor, library_bytes)
    record.update(serializer_version=version, elements=_write_elements(bundle, out),
                  element_count=len(bundle.elements), external_reference_count=len(bundle.external_references))
    record["api_round_trip"] = round_trip(bundle, args.api_url)

    code = 0
    try:
        record["evaluation"] = evaluate(bundle, scope, out)
    except EvaluatorPending as exc:
        record["evaluation"] = {"status": "pending", "reason": str(exc)}
        code = 3

    # The executor checkout, its inputs and the library did not move mid-run.
    if git(ROOT, "rev-parse", "HEAD") != executor or git(ROOT, "status", "--porcelain"):
        raise ValueError("executor checkout moved during execution")
    if verify_library(library_path) != library_bytes:
        raise ValueError("the PLEML library moved during execution")
    for relative, expected in executor_inputs.items():
        if verified_file(ROOT, executor, relative) != expected:
            raise ValueError("executing source moved during execution")
    (out / "authority-run.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record, code


def main() -> int:
    args = build_parser().parse_args()
    try:
        record, code = run(args)
    except (ValueError, RuntimeError, OSError, ImportError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "run": str(args.out / "authority-run.json"),
        "elements": record["element_count"],
        "api_round_trip_verified": record["api_round_trip"]["verified"],
        "evaluation": record["evaluation"].get("status", "evaluated"),
        "qualified": False,
    }))
    if code:
        print(f"refused: {record['evaluation']['reason']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
