"""Receipts of the PLEML configuration evaluation and the parity primitives (ADR 0022).

A licensed run serializes the fenced feature models and writes, per feature
model, a receipt together with the serialized elements it evaluated. Every
other run is unlicensed: it re-runs the evaluator on the committed elements
and refuses a receipt that is stale by digest or does not reproduce. A
receipt whose only difference is the evaluator revision can be refreshed
offline from the same elements.

The parity primitives serve the comparison with the configurator until S7:
the normalised projection body, the writer inputs a receipt carries, the
reason keys of an evaluated configuration and the classification of one
parity row, with ``not-expressible`` limited to a pinned, reviewed list.
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

RECEIPT_SCHEMA = "de4sdv.pleml-configuration-receipt/v1"
ELEMENTS_SCHEMA = "de4sdv.pleml-configuration-elements/v1"
EVALUATOR = "de4sdv/semantic/pleml_configuration.py"
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
    """The serialized element set of one evaluation, in serializer order, with what it was evaluated as."""
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


@lru_cache(maxsize=4)
def model_contract(root: Path = ROOT) -> Any:
    """The model-built kernel contract of the tree, which the kernel bindings are validated against."""
    from de4sdv.semantic.kernel_contract import KernelContract

    return KernelContract.from_layers(root)


def evaluate_payload(payload: Mapping[str, Any], *, contract: Any = None) -> dict[str, Any]:
    """Evaluate the committed elements, binding the kernel classes as ingestion does."""
    bindings = evaluator.kernel_bindings(model_contract() if contract is None else contract, payload["elements"],
                                         payload["element_sources"])
    return evaluator.evaluate(payload["elements"], payload["element_sources"],
                              model_sources=payload["model_sources"], library_source=payload["library_source"],
                              kernel_source=payload["kernel_source"], kernel_bindings=bindings,
                              external_references=payload.get("external_references") or ())


# -- receipts ------------------------------------------------------------------------------


def evaluator_digest() -> str:
    """The digest of the evaluator code that runs (the imported module, wherever the tree is)."""
    return sha256(Path(evaluator.__file__).read_bytes())


def build_receipt(payload: Mapping[str, Any], *, elements_file: str, elements_sha256: str,
                  shadow: Mapping[str, Any] | None = None, contract: Any = None) -> dict[str, Any]:
    """The receipt of one evaluation: inputs by digest, the evaluation, and the shadow checks until S7."""
    return {
        "schema": RECEIPT_SCHEMA,
        "elements": {"path": elements_file, "sha256": elements_sha256, "content_sha256": sha256(canonical(payload))},
        "serializer": payload["serializer"],
        "sources": payload["source_manifest"],
        "evaluator": {"path": EVALUATOR, "sha256": evaluator_digest()},
        "evaluation": evaluate_payload(payload, contract=contract),
        "shadow": dict(shadow or {}),
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
    for source in receipt.get("sources") or []:
        path = root / source["path"]
        if path.is_file():
            if sha256(path.read_bytes()) != source.get("sha256"):
                reasons.append(f"{source['path']} changed after the serialization; rerun the licensed evaluation")
        elif _tracked(root, source["path"]) or ".sysand" not in Path(source["path"]).parts:
            reasons.append(f"{source['path']} is missing; rerun the licensed evaluation")
    if (receipt.get("evaluator") or {}).get("sha256") != evaluator_digest():
        reasons.append("the receipt was evaluated by another evaluator revision; refresh it offline")
    return reasons


def replay(receipt_path: Path, root: Path = ROOT, *, shadow: Mapping[str, Any] | None = None,
           contract: Any = None) -> dict[str, Any]:
    """Re-run the evaluator on the committed elements; refuse a stale or non-reproducing receipt."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    reasons = stale_reasons(receipt, receipt_path, root)
    if reasons:
        raise StaleReceipt("; ".join(reasons))
    payload = read_elements(receipt_path.parent / receipt["elements"]["path"])
    evaluation = evaluate_payload(payload, contract=contract)
    if canonical(evaluation) != canonical(receipt["evaluation"]):
        raise StaleReceipt("the committed evaluation does not reproduce from the committed elements")
    if shadow is not None and canonical(dict(shadow)) != canonical(receipt.get("shadow") or {}):
        raise StaleReceipt("the shadow checks of the receipt do not reproduce")
    return receipt


def refresh(receipt_path: Path, root: Path = ROOT, *, shadow: Mapping[str, Any] | None = None,
            contract: Any = None) -> dict[str, Any]:
    """Re-evaluate a receipt offline when only the evaluator changed; elements and sources must still match."""
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    reasons = [reason for reason in stale_reasons(receipt, receipt_path, root) if "evaluator revision" not in reason]
    if reasons:
        raise StaleReceipt("; ".join(reasons))
    payload = read_elements(receipt_path.parent / receipt["elements"]["path"])
    fresh = build_receipt(payload, elements_file=receipt["elements"]["path"],
                          elements_sha256=receipt["elements"]["sha256"],
                          shadow=receipt.get("shadow") if shadow is None else shadow, contract=contract)
    fresh["serializer"] = receipt.get("serializer") or fresh["serializer"]  # the serialization did not change
    previous = (receipt.get("evaluator") or {}).get("sha256")
    if previous != fresh["evaluator"]["sha256"]:
        fresh["evaluator"]["refreshed_from"] = previous
    receipt_path.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return fresh


# -- writer inputs and the normalised body (plan section 5) ---------------------------------


def fold_description(body: str | None) -> str:
    """The description as the writer receives a folded YAML scalar: lines joined, paragraphs kept."""
    if not body:
        return ""
    paragraphs = re.split(r"\n[ \t]*\n", body.strip())
    return "\n".join(" ".join(line.strip() for line in paragraph.splitlines() if line.strip())
                     for paragraph in paragraphs)


def writer_inputs(configuration: Mapping[str, Any], features: Iterable[Mapping[str, Any]],
                  catalogue_paths: Mapping[str, str] | None = None) -> dict[str, Any]:
    """What the projection writer needs from one evaluated configuration."""
    by_path = {feature["path"]: feature for feature in features}
    optional = {}
    for path, state in configuration["states"].items():
        feature = by_path[path]
        plain_optional = feature["multiplicity"] == {"lower": 0, "upper": 1} and not (feature["group"]
                                                                                    or feature["members"])
        if plain_optional and state in {"enabled", "disabled"}:
            optional[path] = state
    result: dict[str, Any] = {"projection_name": configuration["projection_name"],
                              "description": fold_description(configuration["description"]),
                              "explicit_optional_states": optional}
    if catalogue_paths is not None:
        result["catalogue_paths"] = {feature["path"]: catalogue_paths.get(feature["short_name"] or "")
                                     for feature in features}
    return result


_HEADER_END = re.compile(r"\A/\*.*?\n \*/\n\n?", re.DOTALL)
_DERIVATION_SOURCE = re.compile(r"^(\s*\* Derived .+ projection) from .+\.$", re.MULTILINE)


def normalised_body(projection: str) -> str:
    """The projection below its provenance header, with the derivation-source line normalised."""
    match = _HEADER_END.match(projection)
    if match is None:
        raise ValueError("the projection has no provenance header")
    return _DERIVATION_SOURCE.sub(r"\1 from <configuration source>.", projection[match.end():])


# -- reason keys and parity rows -------------------------------------------------------------

#: Reviewed constructs that PLEML cannot express, each pinned to its parity row (plan section 5).
NOT_EXPRESSIBLE = ({"row": "ug-10-vehicle-target-aebs-false", "construct": "common-capability-false",
                    "reason": "common content has no feature (OQ4)"},)


def reason_keys(configuration: Mapping[str, Any]) -> set[tuple[str, str | None]]:
    """Comparable reason keys: the class, and the constraint identifier for constraint violations."""
    return {(reason["class"], reason.get("constraint") if reason["class"] == "constraint" else None)
            for reason in configuration["reasons"]}


def classify_row(row: str, yaml: Mapping[str, Any], pleml: Mapping[str, Any], *,
                 yaml_remainder: Mapping[str, Any] | None = None) -> dict[str, str]:
    """``equal``, ``both-reject``, ``not-expressible`` or ``defect`` for one parity row.

    Each outcome has ``valid``, ``keys`` (reason keys), ``derived_variants``
    ({variation: variant}) and, when valid, ``body`` (normalised). A
    ``not-expressible`` row needs a pinned construct for this row as the sole
    YAML violation, and the YAML evaluation of the remainder must equal the
    PLEML outcome; anything else that differs is a defect.
    """
    if yaml["valid"] and pleml["valid"]:
        if yaml["derived_variants"] != pleml["derived_variants"]:
            return {"class": "defect", "detail": "the derived variants differ"}
        if yaml.get("body") != pleml.get("body"):
            return {"class": "defect", "detail": "the normalised bodies differ"}
        return {"class": "equal", "detail": ""}
    if not yaml["valid"] and not pleml["valid"]:
        if set(yaml["keys"]) == set(pleml["keys"]):
            return {"class": "both-reject", "detail": ""}
        return {"class": "defect", "detail": f"reason classes differ: {sorted(map(str, yaml['keys']))} and "
                                             f"{sorted(map(str, pleml['keys']))}"}
    pinned = {item["construct"] for item in NOT_EXPRESSIBLE if item["row"] == row}
    keys = list(yaml["keys"])
    if (not yaml["valid"] and pleml["valid"] and len(keys) == 1 and keys[0][0] in pinned
            and yaml.get("violations", 1) == 1 and yaml_remainder is not None):
        remainder = classify_row(row, yaml_remainder, pleml)
        if remainder["class"] == "equal":
            return {"class": "not-expressible", "detail": f"pinned construct {keys[0][0]}"}
        return {"class": "defect", "detail": f"the remainder is not equal: {remainder['detail']}"}
    return {"class": "defect", "detail": "one side accepts what the other rejects"}


# -- evidence records (plan section 4) ---------------------------------------------------------

EVIDENCE_STATUSES = {"draft", "planned", "inspected", "simulated", "analyzed", "tested", "accepted", "rejected", "gap"}
EVIDENCE_BEARING = {"inspected", "simulated", "analyzed", "tested", "accepted", "rejected"}


def evidence_record_errors(record: Any, root: Path = ROOT) -> list[str]:
    """The configurator's evidence rules over one external evidence record (status and artifacts)."""
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
