"""Receipts of the PLEML configuration evaluation (ADR 0022).

The licensed authority job serializes the PLEML feature models with the
production export's options into one export bundle. From that bundle, one
elements file holds the serialized elements, compressed, and each feature
model gets a receipt: its verdicts, derived variants and admission, with the
input digests. Every other run is unlicensed: it re-runs the evaluator on the
committed elements and refuses a receipt whose inputs changed (the elements,
a source, the pinned library), whose evaluation does not reproduce byte for
byte, or whose evaluation records integrity errors. The evaluator's code
identity is provenance: a receipt that still reproduces under other code
holds, and replay reports the difference as an advisory. A receipt that no
longer reproduces from intact inputs is refreshed offline from the same
elements.

The configurator's writer reads its inputs from an evaluated configuration
(``writer_inputs``). The evidence records of the configurations keep the
evidence rules (``evidence_record_errors``).
"""
from __future__ import annotations

import hashlib
import json
import lzma
import re
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from de4sdv.semantic import pleml_configuration as evaluator
from de4sdv.semantic import pleml_package
from de4sdv.sysml_api.baseline import BaselineExportBundle
from de4sdv.sysml_api.product_line_scope import SCOPE_SOURCE, ScopeSemanticError, validate_scope_elements

RECEIPT_SCHEMA = "de4sdv.pleml-configuration-receipt/v2"
ELEMENTS_SCHEMA = "de4sdv.pleml-configuration-elements/v1"
#: The source-manifest roles of the authority bundle that mark the PLEML model documents.
MODEL_ROLES = ("pleml-feature-model", "pleml-feature-configuration", "pleml-fixture")
#: The provenance of one licensed run. A receipt records it beside the elements, never inside them, so the
#: same serialization on another commit gives the same elements file and the same digests.
PROVENANCE = ("executor_revision", "bundle_git_commit")
#: The PLEML-owned code an evaluation runs, relative to the tree of the running evaluator: the evaluator,
#: the receipts, the package record and the CLI. Its digests are provenance, recorded for audit and
#: reported as an advisory; reproduction, not this record, decides whether a receipt still holds. Shared
#: production modules stay outside the record, so that unrelated work never touches it. The configurator
#: reads the receipts and runs no evaluation, so it is outside the record too.
EVALUATOR_MODULES = (
    "de4sdv/semantic/pleml_configuration.py",
    "de4sdv/semantic/pleml_package.py",
    "de4sdv/semantic/pleml_receipts.py",
    "scripts/run_pleml_configuration_evaluation.py",
)
ROOT = Path(__file__).resolve().parents[2]


class StaleReceipt(ValueError):
    """A receipt that does not describe the committed elements, sources or evaluator."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


# -- the committed elements ----------------------------------------------------------------


def elements_payload(*, elements: Iterable[dict[str, Any]], element_sources: Mapping[str, str],
                     model_sources: Iterable[str], library_source: str, kernel_source: str,
                     source_manifest: Iterable[Mapping[str, Any]], serializer: Mapping[str, Any],
                     external_references: Iterable[Mapping[str, Any]] = ()) -> dict[str, Any]:
    """The serialized element set of one evaluation, in its bundle order, with what it was evaluated as."""
    ordered = list(elements)
    return {
        "schema": ELEMENTS_SCHEMA,
        "serializer": dict(serializer),
        "model_sources": sorted(model_sources),
        "library_source": library_source,
        "kernel_source": kernel_source,
        "source_manifest": sorted((dict(item) for item in source_manifest), key=lambda item: item["path"]),
        "element_sources": {item["@id"]: element_sources[item["@id"]] for item in ordered},
        "external_references": sorted((dict(item) for item in external_references),
                                      key=lambda item: (item["source_element_id"], item["property_path"])),
        "elements": ordered,
    }


def write_elements(path: Path, payload: Mapping[str, Any]) -> str:
    """Write the payload as canonical JSON compressed with xz; returns the file digest."""
    data = lzma.compress(canonical(payload), format=lzma.FORMAT_XZ, preset=9)
    path.write_bytes(data)
    return sha256(data)


def read_elements(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(lzma.decompress(path.read_bytes()))
    except (OSError, lzma.LZMAError, ValueError) as exc:
        raise StaleReceipt(f"the elements file {path} is not readable: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != ELEMENTS_SCHEMA:
        raise StaleReceipt(f"{path} is not a PLEML configuration elements file")
    return payload


def _carries_uri(value: Any) -> bool:
    if isinstance(value, dict):
        return "@uri" in value or any(_carries_uri(item) for item in value.values())
    if isinstance(value, list):
        return any(_carries_uri(item) for item in value)
    return False


def pinned_library() -> dict[str, str]:
    """The PLEML release the production lock pins, which every receipt binds."""
    release = pleml_package.RELEASE
    return {"package": pleml_package.PACKAGE, "version": release.version, "tag_commit": release.tag_commit,
            "path": pleml_package.LIBRARY_PATH.as_posix(), "sha256": release.library.sha256}


def run_provenance(bundle: BaselineExportBundle, serializer: Mapping[str, Any]) -> dict[str, Any]:
    """The provenance of the licensed run that produced a bundle."""
    return {"executor_revision": serializer.get("executor_revision"), "bundle_git_commit": bundle.git_commit}


def payload_from_bundle(bundle: BaselineExportBundle | Mapping[str, Any], *, serializer: Mapping[str, Any],
                        model_sources: Iterable[str] | None = None) -> dict[str, Any]:
    """The elements payload of a licensed authority bundle, read by the production bundle reader.

    The model documents are those the bundle's source manifest marks with a
    PLEML role, unless ``model_sources`` names them. The PLEML library must be
    the pinned release: the label of the pinned package and the digest of its
    tag. References are element identities only: the resource path of a
    serializer URI depends on the checkout and on where the library is
    provisioned, so a receipt keeps none, and a bundle element that carries
    one is refused. The run provenance stays out of the payload.
    """
    if not isinstance(bundle, BaselineExportBundle):
        bundle = BaselineExportBundle.from_dict(dict(bundle))
    for element in bundle.elements.values():
        if _carries_uri(element):
            raise ValueError(f"bundle element {element['@id']} carries a resource URI, which depends on the checkout; "
                             "the production bundle builder keeps element identities only")
    manifest = [dict(item) for item in bundle.source_manifest]
    labels = [str(item.get("path")) for item in manifest]
    present = set(bundle.element_sources.values())
    if len(set(labels)) != len(labels) or present - set(labels):
        raise ValueError("the bundle's source manifest must name each of its documents once; unnamed: "
                         f"{sorted(present - set(labels))}")
    library = pinned_library()
    if evaluator.LIBRARY_SOURCE not in present or library["path"] != evaluator.LIBRARY_SOURCE:
        found = sorted(label for label in present if label.endswith("PLEML.sysml"))
        raise ValueError(f"the bundle carries no PLEML library at {evaluator.LIBRARY_SOURCE}, the label of the "
                         f"pinned package; it carries {found or 'none'}")
    entry = next(item for item in manifest if item.get("path") == library["path"])
    if entry.get("sha256") != library["sha256"]:
        raise ValueError(f"the bundle's PLEML library is not the pinned {library['version']}: its sha256 is "
                         f"{entry.get('sha256')}, the tag's {library['sha256']}")
    models = sorted(model_sources if model_sources is not None else
                    (item["path"] for item in manifest if item.get("authority") in MODEL_ROLES))
    if not models:
        raise ValueError("the bundle names no PLEML model documents")
    external = [{key: record[key] for key in ("source_element_id", "property_path", "target_id")}
                for record in bundle.external_references]
    return elements_payload(
        elements=bundle.to_dict()["elements"], element_sources=bundle.element_sources, model_sources=models,
        library_source=evaluator.LIBRARY_SOURCE, kernel_source=evaluator.KERNEL_SOURCE, source_manifest=manifest,
        serializer={key: value for key, value in serializer.items() if key not in PROVENANCE},
        external_references=external)


@lru_cache(maxsize=4)
def model_contract(root: Path = ROOT) -> Any:
    """The model-built kernel contract of the tree, which the kernel bindings are validated against."""
    from de4sdv.semantic.kernel_contract import KernelContract

    return KernelContract.from_layers(root)


def governed_scope(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    """The governed scope, as the production scope validator reads it, when the elements carry it."""
    if SCOPE_SOURCE not in set(payload["element_sources"].values()):
        return None
    try:
        return validate_scope_elements(payload["elements"], dict(payload["element_sources"]))
    except ScopeSemanticError as exc:
        raise evaluator.PlemlShapeError(f"the governed scope does not validate: {exc}") from exc


def evaluate_payload(payload: Mapping[str, Any], *, model_sources: Iterable[str] | None = None,
                     contract: Any = None) -> dict[str, Any]:
    """Evaluate the committed elements, binding the kernel classes as ingestion does.

    With the governed scope among the elements, admission is decided too.
    """
    bindings = evaluator.kernel_bindings(model_contract() if contract is None else contract, payload["elements"],
                                         payload["element_sources"])
    return evaluator.evaluate(payload["elements"], payload["element_sources"],
                              model_sources=sorted(payload["model_sources"] if model_sources is None
                                                   else model_sources),
                              library_source=payload["library_source"], kernel_source=payload["kernel_source"],
                              kernel_bindings=bindings, governed_scope=governed_scope(payload),
                              external_references=payload.get("external_references") or ())


# -- receipts ------------------------------------------------------------------------------


def evaluator_identity() -> dict[str, Any]:
    """The digest of the code an evaluation runs, in the tree of the evaluator that runs (provenance only)."""
    base = Path(evaluator.__file__).resolve().parents[2]
    modules = {module: sha256((base / module).read_bytes()) for module in EVALUATOR_MODULES}
    return {"modules": modules, "sha256": sha256(canonical(modules))}


def evaluator_digest() -> str:
    return evaluator_identity()["sha256"]


def build_receipt(payload: Mapping[str, Any], *, elements_file: str, elements_sha256: str,
                  model_sources: Iterable[str] | None = None, provenance: Mapping[str, Any] | None = None,
                  contract: Any = None) -> dict[str, Any]:
    """The receipt of the feature models in ``model_sources``: inputs by digest and the evaluation."""
    models = sorted(payload["model_sources"] if model_sources is None else model_sources)
    evaluation = evaluate_payload(payload, model_sources=models, contract=contract)
    return {
        "schema": RECEIPT_SCHEMA,
        "feature_models": [item["feature_model"] for item in evaluation["feature_models"]],
        "model_sources": models,
        "elements": {"path": elements_file, "sha256": elements_sha256, "content_sha256": sha256(canonical(payload))},
        "library": pinned_library(),
        "serializer": payload["serializer"],
        "provenance": dict(provenance or {}),
        "sources": payload["source_manifest"],
        "evaluator": evaluator_identity(),
        "evaluation": evaluation,
        "native_expression_executed": False,
        "qualified": False,
    }


def _tracked(root: Path, relative: str) -> bool:
    result = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative],
                            capture_output=True, check=False)
    return result.returncode == 0


def stale_reasons(receipt: Mapping[str, Any], receipt_path: Path, root: Path = ROOT) -> list[str]:
    """Why a receipt no longer describes the tree at ``root`` (empty when it still does)."""
    reasons = []
    if receipt.get("schema") != RECEIPT_SCHEMA:
        return ["not a PLEML configuration receipt"]
    for key in ("native_expression_executed", "qualified"):
        if receipt.get(key) is not False:
            reasons.append(f"the receipt must say {key}: false")
    elements = receipt.get("elements") or {}
    elements_path = receipt_path.parent / str(elements.get("path"))
    if not elements_path.is_file() or sha256(elements_path.read_bytes()) != elements.get("sha256"):
        reasons.append(f"the committed elements {elements.get('path')} differ from the receipt's digest")
        return reasons
    payload = read_elements(elements_path)
    if sha256(canonical(payload)) != elements.get("content_sha256"):
        reasons.append("the elements content differs from the receipt's content digest")
    if payload["source_manifest"] != receipt.get("sources"):
        reasons.append("the receipt and its elements name different sources")
    pinned = pinned_library()
    bound = receipt.get("library") or {}
    if bound != pinned:
        reasons.append(f"the receipt binds PLEML {bound.get('version')} at {bound.get('path')}, and the production "
                       f"lock pins {pinned['version']} at {pinned['path']}; rerun the licensed evaluation")
    library = {source["path"]: source for source in receipt.get("sources") or []}.get(pinned["path"])
    if payload["library_source"] != pinned["path"] or library is None or library.get("sha256") != pinned["sha256"]:
        reasons.append("the elements were not serialized with the pinned PLEML library; rerun the licensed "
                       "evaluation")
    for source in receipt.get("sources") or []:
        path = root / source["path"]
        if path.is_file():
            if sha256(path.read_bytes()) != source.get("sha256"):
                reasons.append(f"{source['path']} changed after the serialization; rerun the licensed evaluation")
        elif source["path"] == pinned["path"]:
            reasons.append(f"the pinned PLEML library {source['path']} is missing; run sysand sync at the "
                           "repository root, the production Sysand project")
        else:
            reasons.append(f"{source['path']} is missing; rerun the licensed evaluation")
    return reasons


def evaluator_advisories(receipt: Mapping[str, Any]) -> list[str]:
    """The code that differs from the code that evaluated a receipt: provenance, never a failure."""
    recorded = (receipt.get("evaluator") or {}).get("modules") or {}
    current = evaluator_identity()["modules"]
    parts = [(label, sorted(modules)) for label, modules in (
        ("changed", {module for module in set(recorded) & set(current) if recorded[module] != current[module]}),
        ("now recorded", set(current) - set(recorded)), ("no longer recorded", set(recorded) - set(current)))
        if modules]
    if not parts:
        return []
    return ["evaluated by other code (" + "; ".join(f"{label}: {', '.join(modules)}" for label, modules in parts)
            + "); the evaluation reproduces, so the receipt holds"]


def replay(receipt_path: Path, root: Path = ROOT, *, contract: Any = None) -> dict[str, Any]:
    """Re-run the evaluator on the committed elements; refuse a stale or non-reproducing receipt."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    reasons = stale_reasons(receipt, receipt_path, root)
    if reasons:
        raise StaleReceipt("; ".join(reasons))
    payload = read_elements(receipt_path.parent / receipt["elements"]["path"])
    evaluation = evaluate_payload(payload, model_sources=receipt.get("model_sources"), contract=contract)
    if canonical(evaluation) != canonical(receipt["evaluation"]):
        raise StaleReceipt("the committed evaluation does not reproduce from the committed elements")
    return receipt


def refreshed(receipt_path: Path, root: Path = ROOT, *, contract: Any = None) -> dict[str, Any]:
    """A receipt re-evaluated offline when only the evaluator changed; elements and sources must still match."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    reasons = stale_reasons(receipt, receipt_path, root)
    if reasons:
        raise StaleReceipt("; ".join(reasons))
    payload = read_elements(receipt_path.parent / receipt["elements"]["path"])
    fresh = build_receipt(payload, elements_file=receipt["elements"]["path"],
                          elements_sha256=receipt["elements"]["sha256"], model_sources=receipt.get("model_sources"),
                          provenance=receipt.get("provenance"), contract=contract)
    previous = (receipt.get("evaluator") or {}).get("sha256")
    if previous != fresh["evaluator"]["sha256"]:
        fresh["evaluator"]["refreshed_from"] = previous
    return fresh


def _decisions(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Each configuration's decision: validity, reason classes, derived variants and admission."""
    decisions = {}
    for model in (receipt.get("evaluation") or {}).get("feature_models") or []:
        for item in model["configurations"]:
            admission = item.get("admission") or {}
            decisions[f"{model['feature_model']}/{item['configuration']}"] = {
                "valid": item["valid"],
                "reasons": sorted(f"{reason['class']} {reason['constraint']}" if reason.get("constraint")
                                  else reason["class"] for reason in item["reasons"]),
                "derived variants": {variant["variation"]: variant["variant"] for variant in item["derived_variants"]},
                "admitted": admission.get("admitted"),
                "admitted alternative": admission.get("alternative"),
            }
    return decisions


def verdict_changes(committed: Mapping[str, Any], fresh: Mapping[str, Any]) -> list[str]:
    """Every change of a configuration's validity, reasons, derived variants or admission, one line each."""
    before, after = _decisions(committed), _decisions(fresh)
    changes = [f"{name}: {'only in the refreshed receipt' if name in after else 'only in the committed receipt'}"
               for name in sorted(set(before) ^ set(after))]
    for name in sorted(set(before) & set(after)):
        for key, value in before[name].items():
            if after[name][key] != value:
                changes.append(f"{name}: {key} {value} -> {after[name][key]}")
    return changes


def write_receipt(receipt_path: Path, receipt: Mapping[str, Any]) -> None:
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class VerdictChanges(ValueError):
    """A refresh that would change verdicts, derived variants or admission without being told to."""

    def __init__(self, changes: list[str]) -> None:
        super().__init__("the refresh changes verdicts: " + "; ".join(changes))
        self.changes = changes


def refresh(receipt_path: Path, root: Path = ROOT, *, contract: Any = None,
            accept_verdict_changes: bool = False) -> dict[str, Any]:
    """Rewrite one receipt from its intact committed elements when it no longer reproduces.

    A refresh that changes a verdict, a derived variant or an admission is
    refused unless ``accept_verdict_changes`` says so: such a change is a
    rollback trigger of the plan, never a silent rewrite.
    """
    fresh = refreshed(receipt_path, root, contract=contract)
    changes = verdict_changes(json.loads(receipt_path.read_text(encoding="utf-8")), fresh)
    if changes and not accept_verdict_changes:
        raise VerdictChanges(changes)
    write_receipt(receipt_path, fresh)
    return fresh


def integrity_failures(receipt: Mapping[str, Any]) -> list[str]:
    """The integrity errors the evaluation of a receipt records, one line each, by feature tree."""
    return [f"{model['tree']['name']}: {error}" for model in receipt["evaluation"]["feature_models"]
            for error in model["integrity_errors"]]


def replay_receipts(paths: Iterable[Path], root: Path = ROOT, *, contract: Any = None) -> list[str]:
    """Replay receipts offline; every failure, as text, and an empty list when all of them hold.

    A receipt fails when its inputs changed, when its evaluation does not
    reproduce byte for byte, or when the evaluation it records has integrity
    errors.
    """
    failures = []
    for path in paths:
        try:
            receipt = replay(path, root, contract=contract)
        except (StaleReceipt, evaluator.PlemlShapeError, ValueError, KeyError, OSError) as exc:
            failures.append(f"{path}: {exc}")
            continue
        failures += [f"{path}: {failure}" for failure in integrity_failures(receipt)]
    return failures


def replay_committed(committed: Path, root: Path = ROOT, *, contract: Any = None) -> list[str]:
    """Replay every receipt of a committed directory; an empty list when all of them hold."""
    paths = sorted(committed.glob("*.receipt.json")) if committed.is_dir() else []
    if not paths:
        return [f"{committed}: no committed receipt"]
    return replay_receipts(paths, root, contract=contract)


def _elements_identity(receipt_path: Path) -> str:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    return sha256(canonical(read_elements(receipt_path.parent / str(receipt["elements"]["path"]))))


def compare_with_committed(fresh: Iterable[Path], committed: Path) -> list[str]:
    """Why the committed receipts are not those of a fresh licensed run (empty when they are).

    Their elements must be identical; the run provenance may differ. A receipt
    that only one side has fails too. This is the authenticity check of the
    committed elements: offline replay cannot tell a consistent edit of an
    elements file and its receipts, so a licensed run compares every head that
    carries receipts.
    """
    fresh_by_name = {path.name: path for path in fresh}
    present = {path.name: path for path in committed.glob("*.receipt.json")} if committed.is_dir() else {}
    failures = [f"{name}: committed, but the fresh run writes no such receipt"
                for name in sorted(set(present) - set(fresh_by_name))]
    for name in sorted(fresh_by_name):
        if name not in present:
            failures.append(f"{name}: not committed; commit the fresh receipts and their elements")
            continue
        try:
            same = _elements_identity(present[name]) == _elements_identity(fresh_by_name[name])
        except (StaleReceipt, OSError, ValueError, KeyError) as exc:
            failures.append(f"{name}: {exc}")
            continue
        if not same:
            failures.append(f"{name}: the committed elements differ from the fresh serialization")
    return failures


# -- writer inputs ---------------------------------------------------------------------------


def fold_description(body: str | None) -> str:
    """The description as the writer prints it: the lines of each paragraph joined, paragraphs kept."""
    if not body:
        return ""
    paragraphs = re.split(r"\n[ \t]*\n", body.strip())
    return "\n".join(" ".join(line.strip() for line in paragraph.splitlines() if line.strip())
                     for paragraph in paragraphs)


def writer_inputs(configuration: Mapping[str, Any], features: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """What the projection writer needs from one evaluated configuration.

    The projection name, the folded description, and the explicit enabled or
    disabled state of each plain optional feature, by its PLEML feature path.
    """
    by_path = {feature["path"]: feature for feature in features}
    optional = {}
    for path, state in configuration["states"].items():
        feature = by_path[path]
        plain_optional = feature["multiplicity"] == {"lower": 0, "upper": 1} and not (feature["group"]
                                                                                    or feature["members"])
        if plain_optional and state in {"enabled", "disabled"}:
            optional[path] = state
    return {"projection_name": configuration["projection_name"],
            "description": fold_description(configuration["description"]),
            "explicit_optional_states": optional}


# -- evidence records ------------------------------------------------------------------------

EVIDENCE_STATUSES = {"draft", "planned", "inspected", "simulated", "analyzed", "tested", "accepted", "rejected", "gap"}
EVIDENCE_BEARING = {"inspected", "simulated", "analyzed", "tested", "accepted", "rejected"}


def evidence_record_errors(record: Any, root: Path = ROOT) -> list[str]:
    """The evidence rules over one evidence record of a configuration: its status and its artifacts."""
    if not isinstance(record, dict):
        return ["the evidence record must be a mapping"]
    errors = [f"unknown evidence field: '{field}'" for field in sorted(set(record) - {"status", "artifacts"})]
    status, artifacts = record.get("status"), record.get("artifacts", [])
    if status not in EVIDENCE_STATUSES:
        errors.append("evidence.status must be one of: " + ", ".join(sorted(EVIDENCE_STATUSES)))
    if not isinstance(artifacts, list):
        return errors + ["evidence.artifacts must be a YAML list"]
    shaped = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict) or set(artifact) != {"id", "path"} or not all(
                isinstance(artifact.get(key), str) for key in ("id", "path")):
            errors.append(f"evidence.artifacts[{index}] must contain exactly a string id and path")
        else:
            shaped.append(artifact)
    if errors:
        return errors
    if status in EVIDENCE_BEARING and not artifacts:
        errors.append(f"{status} configuration requires retained evidence artifacts")
    seen = set()
    for artifact in shaped:
        identifier, text = artifact["id"], artifact["path"]
        if not re.fullmatch(r"[A-Z][A-Z0-9-]*", identifier):
            errors.append(f"evidence artifact id '{identifier}' is invalid")
        elif identifier in seen:
            errors.append(f"duplicate evidence artifact id '{identifier}'")
        seen.add(identifier)
        path = Path(text)
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"evidence artifact path '{text}' must be repository-relative")
        elif ".git" in path.parts:
            errors.append(f"evidence artifact path '{text}' may not reference repository metadata")
        elif any((root / Path(*path.parts[:depth])).is_symlink() for depth in range(1, len(path.parts) + 1)):
            errors.append(f"evidence artifact path '{text}' must not traverse symbolic links")
        elif not (root / path).is_file():
            errors.append(f"evidence artifact does not exist: '{text}'")
        elif not _tracked(root, path.as_posix()):
            errors.append(f"evidence artifact '{text}' is not tracked by Git")
    return errors
