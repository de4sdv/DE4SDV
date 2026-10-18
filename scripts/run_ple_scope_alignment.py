#!/usr/bin/env python3
"""Evaluate the PLEML scope alignment of the admitted AEBS product line (PLE-S).

Licensed mode loads the reviewed model roots, the exact-pinned PLEML library
(read from the frozen experiment checkout at PLEML 1.1.0, never from a copy in
this repository) and the scope-alignment model together with the pinned
serializer, serializes them, validates the governed scope exactly as
production does, and evaluates every scope-alignment configuration with the
frozen Gate A resolver extended for exact-one parents. Replay mode
re-evaluates a retained element file offline, with the experiment it records.

Both modes write receipts that say ``qualified: false``: this is an
experiment and never adoption, selection authority or a compliance claim.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
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

from de4sdv.semantic import ple_scope_alignment as alignment
from de4sdv.sysml_api.baseline import BaselineManifest
from de4sdv.sysml_api.product_line_scope import validate_scope_elements
from de4sdv.sysml_api.repository import element_id
from scripts.run_ple_qualification import (
    FROZEN_REVISION,
    LIBRARY,
    PLEML_PIN,
    SERIALIZER_VERSION,
    digest,
    git,
    load_experiment,
    verified_file,
)

MODEL = alignment.MODEL_SOURCE
EVALUATOR = "de4sdv/semantic/ple_scope_alignment.py"
EXECUTOR_INPUTS = (
    "scripts/run_ple_scope_alignment.py",
    "scripts/run_ple_qualification.py",
    EVALUATOR,
    "de4sdv/sysml_api/baseline.py",
    "de4sdv/sysml_api/product_line_scope.py",
    "de4sdv/sysml_api/repository.py",
    MODEL,
    "sysand-lock.toml",
)
ELEMENTS_SCHEMA = "de4sdv.ple-scope-alignment-elements/v1"
RECEIPT_SCHEMA = "de4sdv.ple-scope-alignment/v1"
#: The experiment this revision evaluates with, as a licensed run records it.
CURRENT_EXPERIMENT = {
    "interpreter_revision": FROZEN_REVISION,
    "interpreter_sha256": alignment.FROZEN_INTERPRETER_SHA256,
    "pleml_pin": PLEML_PIN,
    "library_source": alignment.LIBRARY_SOURCE,
}


def require_current_experiment(experiment: Any, executor_revision: Any) -> None:
    """Refuse to replay an element file recorded with another frozen experiment.

    The evaluation reads the library by its source label, with the interpreter
    of one experiment. An element file therefore replays only at a revision
    that pins the experiment it records, such as its own executor revision.
    """
    if not isinstance(experiment, dict):
        raise ValueError("the element file records no experiment identity")
    recorded = {key: experiment.get(key) for key in CURRENT_EXPERIMENT}
    if recorded != CURRENT_EXPERIMENT:
        raise ValueError(
            f"the element file was recorded with the interpreter {recorded['interpreter_revision']} "
            f"(digest {recorded['interpreter_sha256']}, PLEML pin {recorded['pleml_pin']}, library "
            f"{recorded['library_source']}), not with the current experiment; replay it at a revision that "
            f"pins that experiment, such as its executor revision {executor_revision}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--experiment", type=Path,
                        help="frozen experiment checkout at PLEML 1.1.0 (licensed mode)")
    parser.add_argument("--licensed", action="store_true",
                        help="fresh serialization with the pinned licensed serializer on the x86_64 runner")
    parser.add_argument("--expected-executor", help="exact executor SHA (licensed mode)")
    parser.add_argument("--replay", type=Path,
                        help="retained scope-alignment-elements.json to re-evaluate offline")
    parser.add_argument("--interpreter", type=Path,
                        help="verified frozen interpreter file for replay (default: this repository's Git history)")
    parser.add_argument("--out", type=Path, required=True,
                        help="output directory; must not exist and must be outside the repository")
    return parser


def document_label(url: object, library_path: Path) -> str:
    """The source label of a serialized document: repository-relative, or the pinned library."""
    parsed = urlparse(str(url))
    candidate = Path(unquote(parsed.path if parsed.scheme == "file" else str(url))).resolve()
    if candidate == library_path.resolve():
        return alignment.LIBRARY_SOURCE
    try:
        return candidate.relative_to(ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"serializer produced a document outside the reviewed sources: {url}") from exc


Documents = dict[str, list[dict[str, Any]]]

SERIALIZATION = {
    "evaluation": "minimal (the frozen Gate A interpreter's precedent)",
    "governed_scope_validation": "minimal with implied relationships (the production export's options)",
}


def _element_array(serialized: str, label: str) -> list[dict[str, Any]]:
    values = json.loads(serialized)
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ValueError(f"serializer did not produce an element array for {label}")
    return values


def serialize(experiment: Path, out: Path) -> tuple[Documents, Documents, BaselineManifest, str]:
    """Load the reviewed roots, the pinned library and the model in one model; serialize twice.

    The four evaluation documents (model, governed scope, platform stack,
    library) are serialized with the minimal options the frozen Gate A
    interpreter was built against; every production document is serialized
    with the production export's options, so the governed scope is validated
    on the same shapes production validates.
    """
    if platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("licensed Syside requires the supported x86_64 runner; not executed on this host")
    syside = importlib.import_module("syside")
    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError("installed serializer differs from the reviewed pin")
    from scripts.export_sysml_api_baseline import _serialization_options as production_options

    manifest = BaselineManifest.discover(ROOT)
    library_path = experiment.resolve() / LIBRARY
    paths = [ROOT / source.path for source in manifest.sources] + [library_path, ROOT / MODEL]
    model, diagnostics = syside.try_load_model(paths)
    (out / "serializer-diagnostics.txt").write_text(str(diagnostics) + "\n")
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError(
            "the serializer rejected the reviewed roots with the pinned library and the "
            "scope-alignment model; see serializer-diagnostics.txt"
        )
    minimal, production_only = syside.SerializationOptions.minimal(), production_options()
    evaluation: Documents = {}
    production: Documents = {}
    seen: set[str] = set()
    for document in model.user_docs:
        with document.lock() as locked:
            label = document_label(locked.url, library_path)
            if label in seen:
                raise ValueError(f"serializer repeated a source document: {label}")
            seen.add(label)
            if label in alignment.EVALUATION_SOURCES:
                evaluation[label] = _element_array(syside.json.dumps(locked.root_node, minimal), label)
            if label != MODEL:
                production[label] = _element_array(syside.json.dumps(locked.root_node, production_only), label)
    expected = {source.path for source in manifest.sources} | {alignment.LIBRARY_SOURCE, MODEL}
    if seen != expected:
        raise ValueError(
            "serializer source coverage mismatch: "
            f"missing={sorted(expected - seen)}, unexpected={sorted(seen - expected)}"
        )
    if set(evaluation) != set(alignment.EVALUATION_SOURCES):
        raise ValueError(f"evaluation documents missing: {sorted(set(alignment.EVALUATION_SOURCES) - set(evaluation))}")
    return evaluation, production, manifest, version


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


def run(args: argparse.Namespace) -> tuple[dict[str, Any], list[str]]:
    out: Path = args.out
    if out.exists():
        raise ValueError("refusing to overwrite an existing output directory")
    if out.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("output must be outside the repository")
    if args.licensed == bool(args.replay):
        raise ValueError("choose exactly one of --licensed or --replay")
    executor = git(ROOT, "rev-parse", "HEAD")
    executor_source_dirty = bool(git(ROOT, "status", "--porcelain"))
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "mode": "licensed-serialization" if args.licensed else "replay",
        "executor_revision": executor,
        "executor_source_dirty": executor_source_dirty,
        "current_lock_sha256": digest((ROOT / "sysand-lock.toml").read_bytes()),
        "model": {"path": MODEL, "sha256": digest((ROOT / MODEL).read_bytes())},
        "evaluator": {"path": EVALUATOR, "sha256": digest((ROOT / EVALUATOR).read_bytes())},
        "api_ingestion": False,
        "qualified": False,
        "adoption_authorized": False,
        "authority_activation_authorized": False,
        "native_expression_executed": False,
        "xor_constraint_used": False,
        "multiple_binding_policy_proven": False,
        "binding_time": {"scope": "Development-only", "stage_aware_evaluation_proven": False},
    }
    if args.licensed:
        if args.experiment is None:
            raise ValueError("licensed mode requires the frozen experiment checkout")
        if re.fullmatch(r"[0-9a-f]{40}", args.expected_executor or "") is None or args.expected_executor != executor:
            raise ValueError("licensed mode requires the exact executor SHA")
        executor_inputs = {relative: verified_file(ROOT, executor, relative) for relative in EXECUTOR_INPUTS}
        module, _, identity = load_experiment(args.experiment)
        if identity["interpreter_sha256"] != alignment.FROZEN_INTERPRETER_SHA256:
            raise ValueError("the frozen experiment interpreter (PLEML 1.1.0) digest differs from the reviewed one")
        experiment = {
            "interpreter_revision": FROZEN_REVISION,
            "interpreter_sha256": identity["interpreter_sha256"],
            "pleml_pin": PLEML_PIN,
            "library_source": alignment.LIBRARY_SOURCE,
            "library_sha256": identity["library_sha256"],
        }
        out.mkdir(parents=True)
        evaluation, production, manifest, version = serialize(args.experiment, out)
        elements, sources = flatten(evaluation)
        scope = validate_scope_elements(*flatten(production))
        library_bytes = (args.experiment.resolve() / LIBRARY).read_bytes()
        model_bytes = (ROOT / MODEL).read_bytes()
        source_manifest = [
            *manifest.to_dicts(),
            {"path": alignment.LIBRARY_SOURCE, "authority": "pinned-experiment-library",
             "sha256": digest(library_bytes), "size": len(library_bytes)},
            {"path": MODEL, "authority": "experiment-model",
             "sha256": digest(model_bytes), "size": len(model_bytes)},
        ]
        fresh_serialization = True
    else:
        payload = json.loads(args.replay.read_text())
        if payload.get("schema") != ELEMENTS_SCHEMA:
            raise ValueError("replay input is not a retained scope-alignment element file")
        elements, sources = payload["elements"], payload["element_sources"]
        scope, experiment = payload["governed_scope_validation"], payload["experiment"]
        require_current_experiment(experiment, payload.get("executor_revision"))
        source_manifest, version = payload["source_manifest"], payload.get("serializer_version")
        module = alignment.load_frozen_interpreter(args.interpreter)
        executor_inputs = {}
        out.mkdir(parents=True)
        fresh_serialization = False

    subset = [element for element in elements if sources[element_id(element) or ""] in alignment.EVALUATION_SOURCES]
    subset_sources = {element_id(element) or "": sources[element_id(element) or ""] for element in subset}
    report = alignment.evaluate_scope_alignment(module, subset, subset_sources, scope=scope)
    mismatches = alignment.compare_expected(report)

    retained = {
        "schema": ELEMENTS_SCHEMA, "executor_revision": executor, "serializer_version": version,
        "serialization": SERIALIZATION, "experiment": experiment, "source_manifest": source_manifest,
        "governed_scope_validation": scope, "element_sources": subset_sources, "elements": subset,
    }
    (out / "scope-alignment-elements.json").write_text(json.dumps(retained, indent=2, sort_keys=True) + "\n")
    (out / "governed-scope-validation.json").write_text(json.dumps(scope, indent=2, sort_keys=True) + "\n")

    if args.licensed:
        # The read-only experiment, the executor checkout and its inputs did not move mid-run.
        _, _, final_identity = load_experiment(args.experiment)
        if final_identity["interpreter_sha256"] != experiment["interpreter_sha256"] or final_identity["library_sha256"] != experiment["library_sha256"]:
            raise ValueError("experiment sources moved during execution")
        if git(ROOT, "rev-parse", "HEAD") != executor:
            raise ValueError("executor checkout moved during execution")
        for relative, expected in executor_inputs.items():
            if verified_file(ROOT, executor, relative) != expected:
                raise ValueError("executing source moved during execution")

    receipt.update(
        executor_inputs=executor_inputs,
        experiment=experiment,
        serializer_version=version,
        serialization=SERIALIZATION,
        fresh_serialization=fresh_serialization,
        source_manifest=source_manifest,
        governed_scope_validation={"schema": scope.get("schema"), "scope_source": scope.get("scope_source"),
                                   "planned_reference_members": [item["declared_name"] for item in scope["planned_reference_members"]],
                                   "alternatives": sorted(scope["vehicle_platform_integration_mode"]["alternatives"])},
        alignment=report,
        expectation={"matches": not mismatches, "mismatches": mismatches,
                     "expected_outcomes": alignment.EXPECTED_OUTCOMES},
        known_representation_differences=report["known_representation_differences"],
    )
    receipt["artifact_sha256"] = {path.name: digest(path.read_bytes()) for path in sorted(out.iterdir()) if path.is_file()}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt, mismatches


def main() -> int:
    args = build_parser().parse_args()
    try:
        receipt, mismatches = run(args)
    except (ValueError, RuntimeError, OSError, ImportError, KeyError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "receipt": str(args.out / "receipt.json"), "mode": receipt["mode"],
        "configurations": len(receipt["alignment"]["configurations"]),
        "expected_outcomes_match": not mismatches, "mismatches": mismatches,
        "executor_source_dirty": receipt["executor_source_dirty"], "qualified": False,
    }))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
