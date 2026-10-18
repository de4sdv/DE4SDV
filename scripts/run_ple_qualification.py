#!/usr/bin/env python3
"""Requalify frozen PLE inputs with the current serializer and ephemeral API.

No models are copied or vendored. Historical replay is explicitly separate;
observations never authorize adoption or semantic authority activation.

Two frozen experiments: the historical replay and the prior of the fresh arm
read the retained Gate A export with the Gate A experiment (``GATE_A``); the
fresh arm serializes the current experiment at PLEML 1.1.0 (``CURRENT``).
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, NamedTuple
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from de4sdv.semantic.ple_qualification import build_case_report
from de4sdv.sysml_api.baseline import BaselineExportBundle, build_export_bundle
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.ingestion import import_baseline

class ExperimentIdentity(NamedTuple):
    """A frozen PLEML experiment the runners accept: exact revision, pin and digests."""

    revision: str
    tag: str
    pleml_pin: str
    library: str
    interpreter_sha256: str
    library_sha256: str
    fixture_sha256: str


#: The Gate A experiment. It produced the retained historical export (run
#: 33543909037), so the historical replay and the prior of the fresh arm read
#: that export with this interpreter only. It never changes.
GATE_A = ExperimentIdentity(
    revision="6a99626b4af7cd01108f27dac88bf5b55bba207a",
    tag="pleml-gate-a-frozen",
    pleml_pin="5f8ab8560219dc24d8ec7ec90d6f0a145896ef8e",
    library="external/pleml/PLEML/PLEML.sysml",
    interpreter_sha256="4d9180e9fc6b417f2ffef60b550398335d90225940bc8b8a5960fa733733a4c3",
    library_sha256="1fbd5efd95b63877e88eb6b114ce67122b9dba5236d3712e73175254aaf7d216",
    fixture_sha256="78e77890c1f3236a468a5f566ab036b868ae03fcb2b6fd85fa4e1c8817cdd55c",
)
#: The experiment at PLEML 1.0.0: a child of Gate A with the submodule at the
#: 1.0.0 release commit, the library at its new path and the interpreter
#: reading that path. It is the reviewed parent of the experiment at 1.1.0.
PLEML_1_0_0 = ExperimentIdentity(
    revision="84673ea2bca0d11b795a34afeb7584081dd24fd2",
    tag="pleml-1.0.0-frozen",
    pleml_pin="071a69fdb2ecfa154809913938dfe9ebdf37701b",
    library="external/pleml/PLEML.sysml",
    interpreter_sha256="67400e8c8168f9e552b47a61e6d3565c46ebd0ec9a29d62c59394fd5d502e01f",
    library_sha256="94ae698324f9da510d8d20fdf8e7047f51f1bccb71396745e48e84f416dc8159",
    fixture_sha256="78e77890c1f3236a468a5f566ab036b868ae03fcb2b6fd85fa4e1c8817cdd55c",
)
#: The experiment at PLEML 1.1.0: a child of the experiment at 1.0.0 with the
#: submodule at the 1.1.0 release commit, the fixture's constraint usages in
#: the 1.1 form and the interpreter reading the excluded feature as operand B
#: of constrainedFeatures (verify_constraint_operands checks the operands by
#: identity). The scoped probes, the fresh serialization and the scope
#: alignment run on it.
PLEML_1_1_0 = ExperimentIdentity(
    revision="69bbe093c179f2121274b9f604c7d6a10de19e77",
    tag="pleml-1.1.0-frozen",
    pleml_pin="76e2be934453d77c4094141400b8ad8eb90a54a2",
    library="external/pleml/PLEML.sysml",
    interpreter_sha256="552b91798e8c2498e28e0042fadfc7349c2d130c685e80fe9312353545eafb67",
    library_sha256="a89dc5c3436e3c8e5601e278f2b184e1a6d91f66a77f8616854ee0dd1abca787",
    fixture_sha256="2b858117aee7cfc4fc08d005bf2ba09c5a4dbb433d6c25dc2c013b5e8ec9f763",
)
CURRENT = PLEML_1_1_0
FROZEN_REVISION = CURRENT.revision
PLEML_PIN = CURRENT.pleml_pin
SERIALIZER_VERSION = "0.10.3"
FIXTURE = "docs/spikes/pleml-gate-a/pleml_gate_a_fixture.sysml"
LIBRARY = CURRENT.library
SUBMODULE = "external/pleml"
EXECUTOR_INPUTS = ("scripts/run_ple_qualification.py", "de4sdv/semantic/ple_qualification.py",
                   "de4sdv/sysml_api/baseline.py", "de4sdv/sysml_api/ingestion.py",
                   "de4sdv/sysml_api/client.py", "de4sdv/sysml_api/repository.py",
                   "de4sdv/sysml_api/errors.py")


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"Git source verification failed: {args[0]}")
    return result.stdout.decode().strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verified_file(root, revision, relative):
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"source escapes verified checkout: {relative}")
    expected = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{relative}"], capture_output=True, check=False)
    if expected.returncode or path.read_bytes() != expected.stdout:
        raise ValueError(f"source differs from recorded Git object: {relative}")
    return digest(expected.stdout)


def load_experiment(root, identity: ExperimentIdentity = CURRENT) -> tuple[Any, list[dict[str, Any]], dict[str, Any]]:
    """Load the interpreter of a frozen experiment checkout after verifying it is ``identity``."""
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != identity.revision:
        raise ValueError("experiment checkout is not the frozen reviewed revision")
    if git(root / SUBMODULE, "rev-parse", "HEAD") != identity.pleml_pin:
        raise ValueError("PLEML pin mismatch")
    if not identity.library.startswith(SUBMODULE + "/"):
        raise ValueError("the reviewed PLEML library lies outside the PLEML submodule")
    fixture_digest = verified_file(root, identity.revision, FIXTURE)
    library_digest = verified_file(root / SUBMODULE, identity.pleml_pin, identity.library[len(SUBMODULE) + 1:])
    evaluator_digest = verified_file(root, identity.revision, "tools/pleml_gate_a.py")
    if (evaluator_digest, library_digest, fixture_digest) != (
            identity.interpreter_sha256, identity.library_sha256, identity.fixture_sha256):
        raise ValueError("experiment digests differ from the reviewed identity")
    name = "_de4sdv_verified_ple_qualification_oracle_" + identity.revision
    spec = importlib.util.spec_from_file_location(name, root / "tools/pleml_gate_a.py")
    if spec is None or spec.loader is None:
        raise ValueError("cannot load verified experiment interpreter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    source = module.gate_a_source_identity(root, expected_pleml_commit=identity.pleml_pin)
    manifest = list(source.source_manifest)
    if [entry.get("path") for entry in manifest] != [FIXTURE, identity.library]:
        raise ValueError("the experiment interpreter reads other sources than the reviewed identity")
    return module, manifest, {
        "interpreter_revision": identity.revision, "interpreter_sha256": evaluator_digest,
        "fixture_sha256": fixture_digest, "library_sha256": library_digest,
        "pleml_pin": identity.pleml_pin,
    }


def historical_matrix(path, module, manifest):
    """The prior: the retained Gate A export read by the Gate A interpreter, never another one."""
    interpreter = getattr(module, "__file__", None)
    if interpreter is None or digest(Path(interpreter).read_bytes()) != GATE_A.interpreter_sha256:
        raise ValueError("the historical prior requires the Gate A interpreter")
    raw = json.loads(path.read_text())
    identity = raw.get("gate_a_identity", {})
    if (raw.get("source_manifest") != manifest or identity.get("pleml_commit") != GATE_A.pleml_pin
            or identity.get("git_commit") != raw.get("git_commit") or raw.get("git_commit") != GATE_A.revision):
        raise ValueError("historical source manifest or identity mismatch")
    bundle = BaselineExportBundle.from_dict(raw)
    return module.build_observability_matrix(list(bundle.elements.values()), bundle.element_sources), raw["git_commit"]


def serialize(root, manifest, revision):
    syside = importlib.import_module("syside")

    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError("installed serializer differs from current reviewed pin")
    paths = [root / source["path"] for source in manifest]
    model, diagnostics = syside.try_load_model(paths)
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError(f"current serializer rejected frozen qualification inputs: {diagnostics}")
    documents = {}
    for document in model.user_docs:
        with document.lock() as locked:
            parsed = urlparse(str(locked.url))
            source = Path(unquote(parsed.path if parsed.scheme == "file" else str(locked.url))).resolve().relative_to(root).as_posix()
            values = json.loads(syside.json.dumps(locked.root_node, syside.SerializationOptions.minimal()))
        if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
            raise ValueError("serializer did not produce an element array")
        if source in documents:
            raise ValueError("serializer repeated a source document")
        documents[source] = values
    if set(documents) != {source["path"] for source in manifest}:
        raise ValueError("serializer source coverage mismatch")
    bundle = build_export_bundle(git_commit=revision, source_documents=documents)
    raw = bundle.to_dict()
    raw["source_manifest"] = manifest
    return BaselineExportBundle.from_dict(raw), version


def verify_readback(bundle, values):
    if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
        raise ValueError("API readback must contain element objects")
    indexed = {item.get("@id"): item for item in values}
    if len(indexed) != len(values) or set(indexed) != set(bundle.elements):
        raise ValueError("API readback changed or duplicated UUIDs")
    for uuid, expected in bundle.elements.items():
        if indexed[uuid].get("@type") != expected.get("@type"):
            raise ValueError("API readback changed metatype")
    if reference_edges(indexed) != reference_edges(bundle.elements):
        raise ValueError("API readback changed internal references")
    return values


def reference_edges(elements):
    """Preserve reference property paths, targets and multiplicity, not list order."""
    edges = Counter()

    def collect(value, source, path):
        if isinstance(value, dict):
            if "@id" in value and "@type" not in value:
                if set(value) != {"@id"}:
                    raise ValueError("API readback contains a noncanonical reference object")
                target = value["@id"]
                if not isinstance(target, str) or target not in elements:
                    raise ValueError("API readback contains a dangling internal reference")
                edges[(source, path, target)] += 1
                return
            for key, child in value.items():
                collect(child, source, path + (key,))
        elif isinstance(value, list):
            for child in value:
                collect(child, source, path)

    for source, value in elements.items():
        collect(value, source, ())
    return edges


def verify_constraint_operands(bundle, values):
    """Check the operands of the fixture's PLEML 1.1 constraints by identity; the interpreter reads them by shape.

    The constructor must instantiate the ``FeatureOperand`` of the pinned library document. Operand A must reference
    the feature that owns the constraint, or the kernel ``that``: a reference the bundle leaves out whose one pruning
    record names the target of the library's own ``featureConfiguration = that``. Anything else refuses.
    """
    elements = {item["@id"]: item for item in values}
    records = {}
    for record in bundle.external_references:
        if record.get("property_path") == "memberElement":
            records.setdefault(record.get("source_element_id"), []).append(record.get("target_id"))

    def ref(value):
        return value.get("@id") if isinstance(value, dict) else None

    def one(found, what):
        if len(found) != 1:
            raise ValueError(f"constraint operand check: {len(found)} {what}")
        return found[0]

    def owned(owner, kind, name=None):
        return [key for key, item in elements.items() if item.get("@type") == kind
                and ref(item.get("owningRelatedElement")) == owner and (name is None or item.get("memberName") == name)]

    def member(owner, kind, name=None):
        return ref(elements[one(owned(owner, kind, name), f"{kind} {name or ''} of {owner}")].get("memberElement"))

    def library(name):
        return one([key for key, item in elements.items() if item.get("@type") == "OccurrenceDefinition"
                    and item.get("declaredName") == name and bundle.element_sources.get(key) == LIBRARY], f"library {name}")

    def reference(feature):  # a feature whose value is one feature reference: (target, pruning record targets)
        membership = one(owned(member(feature, "FeatureValue"), "Membership"), f"references of {feature}")
        return ref(elements[membership].get("memberElement")), records.get(membership, [])

    feature_operand = library("FeatureOperand")
    configuration = member(library("FeatureConfiguration"), "FeatureMembership", "featureConstraints")
    that = reference(member(configuration, "FeatureMembership", "featureConfiguration"))
    if that[0] is not None or len(that[1]) != 1:
        raise ValueError("constraint operand check: the library's own that is not one left-out reference")
    verified = []
    for usage in sorted(key for key, item in elements.items() if item.get("@type") == "AssertConstraintUsage"
                        and bundle.element_sources.get(key) == FIXTURE and owned(key, "FeatureMembership", "constrainedFeatures")):
        constructor = member(member(usage, "FeatureMembership", "constrainedFeatures"), "FeatureValue")
        if member(constructor, "Membership") != feature_operand:
            raise ValueError(f"constraint operand check: {usage} does not instantiate the library's FeatureOperand")
        owner = ref(elements[ref(elements[usage].get("owningRelationship"))].get("owningRelatedElement"))
        target, pruned = reference(member(member(constructor, "ReturnParameterMembership"), "ParameterMembership", "operandA"))
        if target != owner and (target is not None or pruned != that[1]):
            raise ValueError(f"constraint operand check: operand A of {usage} is neither its owner {owner} nor that")
        verified.append({"constraint": usage, "name": elements[usage].get("declaredName") or elements[usage].get("name"),
                         "owner": owner, "operand_a": "owner" if target == owner else "that", "feature_operand": feature_operand})
    return verified


def observe(module, elements):
    model = module.GateAModel(elements)

    def unique(name):
        matches = [item["@id"] for item in elements if item.get("@type") == "OccurrenceUsage" and (item.get("declaredName") or item.get("name")) == name]
        if len(matches) != 1:
            raise ValueError(f"qualification role missing or ambiguous: {name}")
        return matches[0]

    nominal, ambiguous = unique("nominalAdapterRules"), unique("ambiguousAdapterRules")
    outcomes = {}
    for label, config, rules in (
        ("adapter-required-exactly-one", "validAutowareAndroid", nominal),
        ("valid-no-adapter", "validAutowareNoMiddleware", nominal),
        ("configuration-invalid", "forbiddenApolloAndroid", nominal),
        ("derivation-incomplete", "missingOpenpilotSCORE", nominal),
        ("derivation-ambiguous", "validAutowareAndroid", ambiguous),
    ):
        value = asdict(model.evaluate(unique(config), rule_set_id=rules))
        value["selected_feature_ids"] = sorted(value["selected_feature_ids"])
        outcomes[label] = value
    expected = {"adapter-required-exactly-one": "derivation-complete", "valid-no-adapter": "derivation-complete", "configuration-invalid": "configuration-invalid", "derivation-incomplete": "derivation-incomplete", "derivation-ambiguous": "derivation-ambiguous"}
    if {key: value["status"] for key, value in outcomes.items()} != expected:
        raise ValueError("adapter or incompatibility interpretation changed")
    if outcomes["valid-no-adapter"]["adapter_id"] is not None:
        raise ValueError("no-adapter configuration selected an adapter")
    groups = {"at-least-one": model.group_resolutions(unique("validOneSensor")),
              "multi-select": model.group_resolutions(unique("validBothSensors"))}
    try:
        model.group_resolutions(unique("invalidNoSensor"))
    except module.UnsupportedSemanticShape as exc:
        groups["empty"] = {"status": "configuration-invalid", "reason": str(exc)}
    else:
        raise ValueError("empty at-least-one group unexpectedly passed")
    return {"outcomes": outcomes, "group_resolutions": groups,
            "native_expression_executed": False}


def run(args):
    if args.out.exists():
        raise ValueError("refusing to overwrite an existing receipt")
    # The historical replay is the Gate A experiment on its own export. The
    # fresh arm serializes the current experiment and compares it with the
    # Gate A prior, read from a separate Gate A checkout.
    historical = args.api_url is None
    if historical and args.historical_experiment is not None:
        raise ValueError("the historical replay reads the Gate A experiment as --experiment; "
                         "--historical-experiment belongs to the fresh arm")
    if not historical and args.historical_experiment is None:
        raise ValueError("the fresh arm needs the Gate A experiment checkout (--historical-experiment) for its prior")
    identity = GATE_A if historical else CURRENT
    module, manifest, source_identity = load_experiment(args.experiment, identity)
    if historical:
        prior_module, prior_manifest, prior_identity = module, manifest, source_identity
    else:
        prior_module, prior_manifest, prior_identity = load_experiment(args.historical_experiment, GATE_A)
    executor_revision = git(ROOT, "rev-parse", "HEAD")
    current_lock = verified_file(ROOT, executor_revision, "sysand-lock.toml")
    source_identity.update(executor_revision=executor_revision, current_lock_sha256=current_lock,
                           executor_source_dirty=bool(git(ROOT, "status", "--porcelain")))
    prior, historical_revision = historical_matrix(args.historical_export, prior_module, prior_manifest)
    source_identity["historical_export_revision"] = historical_revision
    source_identity["historical_export_sha256"] = digest(args.historical_export.read_bytes())
    if historical:
        receipt = build_case_report(prior, prior)
        receipt.update(historical=True, fresh_serialization=False, api_readback=False,
                       observations=observe(module, json.loads(args.historical_export.read_text())["elements"]))
    else:
        if re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}", args.api_url) is None or not 1 <= int(args.api_url.rsplit(":", 1)[1]) <= 65535:
            raise ValueError("qualification may write only to an ephemeral loopback API")
        if args.expected_executor != executor_revision or re.fullmatch(r"[0-9a-f]{40}", executor_revision) is None:
            raise ValueError("fresh qualification requires the exact executor revision")
        source_identity["executor_inputs"] = {
            relative: verified_file(ROOT, executor_revision, relative)
            for relative in EXECUTOR_INPUTS
        }
        source_identity["historical_interpreter"] = {
            "interpreter_revision": prior_identity["interpreter_revision"],
            "interpreter_sha256": prior_identity["interpreter_sha256"],
            "pleml_pin": prior_identity["pleml_pin"],
        }
        bundle, version = serialize(args.experiment.resolve(), manifest, identity.revision)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        for filename in ("export.json", "binding.json", "api-readback.json"):
            if (args.out.parent / filename).exists():
                raise ValueError("fresh execution output already exists")
        bundle.write(args.out.parent / "export.json")
        client = ApiClient(args.api_url)
        imported = import_baseline(client, bundle, project_name="DE4SDV isolated PLE qualification")
        values = verify_readback(bundle, client.get_all(f"/projects/{imported.project_id}/commits/{imported.commit_id}/elements"))
        constraint_operands = verify_constraint_operands(bundle, values)
        binding = {"schema": "de4sdv.ple-qualification-binding/v1", "model_revision": identity.revision,
                   "executor_revision": executor_revision, "pleml_pin": identity.pleml_pin,
                   "serializer_version": version, "current_lock_sha256": current_lock,
                   "export_sha256": digest((args.out.parent / "export.json").read_bytes()), **asdict(imported)}
        (args.out.parent / "binding.json").write_text(json.dumps(binding, indent=2) + "\n")
        (args.out.parent / "api-readback.json").write_text(json.dumps(values, indent=2) + "\n")
        matrix = module.build_observability_matrix(values, bundle.element_sources)
        receipt = build_case_report(matrix, prior)
        receipt.update(historical=False, fresh_serialization=True, api_readback=True,
                       binding=binding, observations=observe(module, values),
                       constraint_operands=constraint_operands,
                       pruning_records=list(bundle.external_references))
    # Check that the read-only experiments and current lock did not move mid-run.
    _, final_manifest, final_identity = load_experiment(args.experiment, identity)
    if final_manifest != manifest or final_identity["interpreter_sha256"] != source_identity["interpreter_sha256"] or verified_file(ROOT, executor_revision, "sysand-lock.toml") != current_lock:
        raise ValueError("qualification sources moved during execution")
    if not historical:
        _, final_prior_manifest, final_prior = load_experiment(args.historical_experiment, GATE_A)
        if final_prior_manifest != prior_manifest or final_prior["interpreter_sha256"] != prior_identity["interpreter_sha256"]:
            raise ValueError("qualification sources moved during execution")
    if args.api_url is not None:
        if git(ROOT, "rev-parse", "HEAD") != executor_revision:
            raise ValueError("executor checkout moved during execution")
        for relative, expected in source_identity["executor_inputs"].items():
            if verified_file(ROOT, executor_revision, relative) != expected:
                raise ValueError("executing source moved during qualification")
    receipt["source_identity"] = source_identity
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as output:
        output.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True,
                        help="frozen experiment checkout: Gate A for the historical replay, the current one otherwise")
    parser.add_argument("--historical-experiment", type=Path,
                        help="Gate A experiment checkout that reads the prior of the fresh arm")
    parser.add_argument("--historical-export", type=Path, required=True)
    parser.add_argument("--api-url")
    parser.add_argument("--expected-executor")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = run(args)
    except (ValueError, RuntimeError, OSError, ImportError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"receipt": str(args.out), "historical": receipt["historical"],
                      "case_count": len(receipt["cases"]), "qualified": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
