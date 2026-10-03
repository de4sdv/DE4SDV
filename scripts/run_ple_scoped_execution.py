#!/usr/bin/env python3
"""Pin-qualified synthetic PLE probes plus draft source; not qualification."""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import re
import shlex
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from scripts.run_ple_qualification import (
    FROZEN_REVISION, PLEML_PIN, SERIALIZER_VERSION, LIBRARY,
    digest, git, load_experiment, verified_file,
)

FORMS = ("literal-bounds", "range-operator")


def synthetic_graph(form, binding_count=2):
    """Explicit test doubles, NEVER serialized model output or API evidence."""
    if form not in FORMS or type(binding_count) is not int or not 2 <= binding_count <= 8:
        raise ValueError("form must be declared and binding count must be 2..8")
    rows = []
    def add(identifier, metatype, **properties):
        rows.append({"@id": identifier, "@type": metatype, **properties})
    def ref(identifier):
        return {"@id": identifier}
    def member(owner, child, kind="FeatureMembership"):
        add(owner + ":" + child + ":" + kind, kind,
            owningRelatedElement=ref(owner), memberElement=ref(child))
    add("tree", "OccurrenceUsage", declaredName="scopedTree")
    add("group", "OccurrenceUsage", declaredName="probeGroup")
    member("tree", "group")
    add("bounds", "MultiplicityRange")
    member("group", "bounds", "OwningMembership")
    add("lower", "LiteralInteger", value=1)
    add("upper", "LiteralInfinity")
    if form == "literal-bounds":
        member("bounds", "lower", "OwningMembership")
        member("bounds", "upper", "OwningMembership")
    else:
        add("range", "OperatorExpression", operator="..")
        member("bounds", "range", "OwningMembership")
        for index, literal in enumerate(("lower", "upper")):
            parameter = "parameter" + str(index)
            add(parameter, "Feature")
            member("range", parameter, "ParameterMembership")
            member(parameter, literal, "FeatureValue")
    add("asset", "PartUsage", declaredName="probeAsset")
    for index in range(binding_count):
        identifier = "member" + str(index)
        add(identifier, "OccurrenceUsage", declaredName=identifier)
        member("tree", identifier)
        add("subset" + str(index), "Subsetting", specific=ref(identifier), general=ref("group"))
        add("binding" + str(index), "Dependency", declaredName="binding" + str(index),
            client=[ref("asset")], supplier=[ref(identifier)])
    # Every configuration explicitly redefines the group; 'none' is not a
    # missing configuration and therefore reaches the lower-bound check.
    for scenario, selected in (("at-least-one", [0]), ("multi-select", list(range(binding_count))), ("none", [])):
        add(scenario, "OccurrenceUsage", declaredName=scenario)
        for index, target in enumerate(["group"] + ["member" + str(n) for n in selected]):
            child = scenario + ":selection" + str(index)
            add(child, "OccurrenceUsage")
            member(scenario, child)
            add(child + ":redefinition", "Redefinition", owningRelatedElement=ref(child), redefinedFeature=ref(target))
    return rows


def probe_graph(module, rows, form, binding_count):
    """Use frozen primitive group resolver, no Boolean/native interpreter."""
    if form == "range-operator":
        operators = [row for row in rows if row.get("@id") == "range"]
        if len(operators) != 1 or operators[0].get("operator") != "..":
            raise ValueError("group range operator must be '..'")
    class ScopedModel(module.GateAModel):
        def _group_ids(self):
            return ("group",)
    model = ScopedModel(rows)
    if model._multiplicity("group") != (1, None):
        raise ValueError("scoped group bounds changed")
    expected_members = {"member" + str(n) for n in range(binding_count)}
    if model._group_member_ids("group") != expected_members:
        raise ValueError("scoped subsetting population changed")
    bindings = []
    for n in range(binding_count):
        value = model.by_id["binding" + str(n)]
        if value.get("@type") != "Dependency" or value.get("client") != [{"@id": "asset"}] or value.get("supplier") != [{"@id": "member" + str(n)}]:
            raise ValueError("binding endpoint or metatype changed")
        bindings.append({"id": value["@id"], "asset": "asset", "feature": "member" + str(n), "meaning": "linkage/provenance-only"})
    groups = []
    for scenario, expected in (("at-least-one", ["member0"]), ("multi-select", sorted(expected_members)), ("none", [])):
        try:
            actual = list(model.group_resolutions(scenario)["probeGroup"])
        except module.UnsupportedSemanticShape as exc:
            if scenario != "none" or "selects 0 members" not in str(exc):
                raise
            status, actual, reason = "configuration-invalid", [], str(exc)
        else:
            if scenario == "none":
                raise ValueError("empty group unexpectedly passed")
            status, reason = "resolved", ""
        if actual != expected:
            raise ValueError("scenario population mismatch")
        groups.append({"form": form, "scenario": scenario, "selected": actual,
                       "expected": expected, "status": status, "reason": reason,
                       "evaluation": "frozen-bounded-group-resolver", "native_expression_executed": False,
                       "disjointness_proven": False, "qualified": False})
    return bindings, groups


def fixture_text(binding_count):
    """Small independent draft; imports the original library, never copies it."""
    members = "\n".join(f"        #feature occurrence member{n}[0..1] :> probeGroup default null;" for n in range(binding_count))
    selected = ", ".join(f"member{n}" for n in range(binding_count))
    selections = "\n".join(f"        #feature occurrence :>> member{n}[1];" for n in range(binding_count))
    bindings = "\n".join(f"    #FeatureBinding dependency binding{n} from probeAsset to ScopedTree::member{n};" for n in range(binding_count))
    return f"""// Draft synthetic probe; validation requested in privileged workflow.
// PLEML pin {PLEML_PIN}; linkage is not AND/OR/precedence.
package DE4SDV_ScopedPLEExecution {{
    private import PLEML::*;
    #featureTree occurrence def ScopedTree {{
        #feature occurrence probeGroup[1..*];
{members}
        // A single excluded feature reaches the pinned XOR range expression.
        #feature occurrence owner[0..1] default null {{
            assert constraint :>> xorFeatures {{
                in #feature occurrence :>> excluded = (member0);
            }}
        }}
    }}
    #featureConfiguration occurrence atLeastOne : ScopedTree :> featureConfigurations {{
        #feature occurrence :>> probeGroup[1..*] = (member0);
        #feature occurrence :>> member0[1];
    }}
    #featureConfiguration occurrence multiSelect : ScopedTree :> featureConfigurations {{
        #feature occurrence :>> probeGroup[1..*] = ({selected});
{selections}
    }}
    #featureConfiguration occurrence noneSelected : ScopedTree :> featureConfigurations {{
        #feature occurrence :>> probeGroup[1..*];
    }}
    #featureConfiguration occurrence xorCounterexample : ScopedTree :> featureConfigurations {{
        #feature occurrence :>> probeGroup[1..*] = (member0);
        #feature occurrence :>> member0[1];
        #feature occurrence :>> owner[1];
    }}
    part probeAsset;
{bindings}
    constraint nativeXorProbe : PLEML::XORConstraint {{
        in occurrence :>> featureConfiguration = xorCounterexample;
        in occurrence :>> owningFeature = ScopedTree::owner;
        in occurrence :>> excluded = (ScopedTree::member0);
    }}
}}
"""


def licensed_probe(args, report):
    """Fresh serialization and real Compiler attempt; no API ingestion."""
    import platform
    if platform.machine() not in {"x86_64", "AMD64"}:
        raise ValueError("licensed Syside requires the supported x86_64 runner; not executed on this host")
    syside = importlib.import_module("syside")
    version = importlib.metadata.version("syside")
    if version != SERIALIZER_VERSION:
        raise ValueError("installed serializer differs from reviewed 0.10.3 pin")
    library = args.experiment.resolve() / LIBRARY
    source = args.out / "scoped-fixture.sysml"
    model, diagnostics = syside.try_load_model([library, source])
    (args.out / "serializer-diagnostics.txt").write_text(str(diagnostics) + "\n")
    if diagnostics.contains_errors(warnings_as_errors=False):
        raise ValueError("serializer rejected scoped draft; see serializer-diagnostics.txt")
    native = report["native_xor"]
    native.update(attempted=False, target_count=0, target_uuid=None,
                  target_source=None, target_diagnostics=[])
    values, native_targets = [], []
    for document in model.user_docs:
        with document.lock() as locked:
            values.extend(json.loads(syside.json.dumps(locked.root_node, syside.SerializationOptions.minimal())))
            for node in locked.nodes(syside.ConstraintUsage):
                if node.declared_name == "nativeXorProbe":
                    native_targets.append((document, node))
                    native["target_diagnostics"].append({"uuid": str(node.element_id),
                        "source": str(locked.url), "name": node.declared_name})
    (args.out / "serialized-elements.json").write_text(json.dumps(values, indent=2) + "\n")
    report["mode"] = "licensed-serialization-with-synthetic-regressions"
    report["fresh_serialization"] = True
    report["representation"]["licensed_validation"] = True
    report["representation"]["serializer_version"] = version
    observed = {}
    for n in range(args.binding_count):
        name = "binding" + str(n)
        matches = [v for v in values if v.get("@type") == "Dependency"
                   and (v.get("declaredName") or v.get("name")) == name]
        if len(matches) != 1:
            raise ValueError("fresh binding dependency population mismatch")
        observed[name] = matches[0]
    report["representation"]["serialized_binding_dependencies"] = observed
    report["representation"]["binding_metadata_adequacy"] = "gap: dependency anchors alone do not prove FeatureBinding metadata or provenance adequacy"
    indexed = {v["@id"]: v for v in values}
    forms = set()
    for relationship in values:
        if relationship.get("@type") != "OwningMembership":
            continue
        owner = indexed.get((relationship.get("owningRelatedElement") or {}).get("@id"), {})
        child = indexed.get((relationship.get("memberElement") or relationship.get("ownedRelatedElement") or {}).get("@id"), {})
        if owner.get("@type") == "MultiplicityRange":
            if child.get("@type") in {"LiteralInteger", "LiteralInfinity"}:
                forms.add("literal-bounds")
            elif child.get("@type") == "OperatorExpression" and child.get("operator") == "..":
                forms.add("range-operator")
    report["representation"]["actual_serializer_forms_observed"] = sorted(forms)
    report["representation"]["group_adequacy"] = "gap: native population evaluation and per-group two-form serialization are not established by global range presence"
    native["target_count"] = len(native_targets)
    if len(native_targets) != 1:
        native["reason"] = "fresh serialization did not expose exactly one ConstraintUsage nativeXorProbe"
        report["execution_error"] = native["reason"]
        return
    native["target_uuid"] = native["target_diagnostics"][0]["uuid"]
    native["target_source"] = native["target_diagnostics"][0]["source"]
    with native_targets[0][0].lock():
        native["attempted"] = True
        try:
            value, diagnostics = syside.Compiler(max_steps=10000).evaluate(native_targets[0][1])
        except (RuntimeError, ValueError, TypeError) as exc:
            native["reason"] = "Syside Compiler.evaluate refused nativeXorProbe: " + str(exc)
            native["attempted"] = True
            return
        native["attempted"] = True
        native["compiler_diagnostics"] = []
        for entry in diagnostics.diagnostics:
            row: dict[str, Any] = {field: str(item) for field in ("message", "code", "severity", "source")
                   if (item := getattr(entry, field, None)) is not None}
            segment = getattr(entry, "segment", None)
            if segment is not None:
                row["segment"] = {field: int(item) for field in ("offset", "end")
                                  if (item := getattr(segment, field, None)) is not None}
            native["compiler_diagnostics"].append(row)
        native["compiler_fatal"] = diagnostics.fatal
        native["returned_value_repr"] = repr(value)
        messages = "; ".join(entry.get("message", "") for entry in native["compiler_diagnostics"])
        native["reason"] = "Syside Compiler.evaluate(nativeXorProbe) returned retained value/diagnostics; instance semantics and Boolean result are not qualified. " + (messages or "No compiler diagnostics emitted.")
        if value is not None and not diagnostics.fatal:
            native["status"] = "native-result-unqualified"
            native["native_expression_executed"] = True
            report["native_expression_executed"] = True
    # Requirement stays failed: no automatic instance-correctness promotion.


def run(args):
    if args.out.exists():
        raise ValueError("refusing to overwrite probe output")
    if args.out.resolve().is_relative_to(ROOT):
        raise ValueError("probe output must be outside the repository")
    executor = git(ROOT, "rev-parse", "HEAD")
    if args.licensed:
        if re.fullmatch(r"[0-9a-f]{40}", args.expected_executor or "") is None or args.expected_executor != executor:
            raise ValueError("licensed mode requires exact executor SHA")
        for path in ("scripts/run_ple_scoped_execution.py", "scripts/run_ple_qualification.py", "de4sdv/semantic/ple_qualification.py", "sysand-lock.toml"):
            verified_file(ROOT, executor, path)
    module, _, identity = load_experiment(args.experiment)
    groups, bindings = [], []
    payloads = {}
    for form in FORMS:
        rows = synthetic_graph(form, args.binding_count)
        current_bindings, current_groups = probe_graph(module, rows, form, args.binding_count)
        if bindings and bindings != current_bindings:
            raise ValueError("binding population changed between forms")
        bindings = current_bindings
        groups.extend(current_groups)
        payloads[form + ".synthetic.json"] = json.dumps(rows, indent=2) + "\n"
    command = [sys.executable, "scripts/run_ple_scoped_execution.py", "--experiment", str(args.experiment),
               "--binding-count", str(args.binding_count), "--native-xor", "--out", str(args.out) + "-native-reproducer"]
    if args.licensed:
        command.extend(["--licensed", "--expected-executor", executor])
    report = {"schema": "de4sdv.ple-scoped-execution/v1", "mode": "synthetic",
              "source_identity": identity, "executor_revision": git(ROOT, "rev-parse", "HEAD"),
              "executor_source_sha256": digest(Path(__file__).read_bytes()),
              "current_lock_sha256": digest((ROOT / "sysand-lock.toml").read_bytes()),
              "executor_source_dirty": bool(git(ROOT, "status", "--porcelain")),
              "bindings": bindings, "groups": groups,
              "fresh_serialization": False, "native_expression_executed": False,
              "qualified": False, "adoption_authorized": False, "authority_activation_authorized": False,
              "binding_time": {"scope": "Development-only", "stage_aware_evaluation_proven": False},
              "representation": {"synthetic_shapes_exercised": list(FORMS), "licensed_validation": False,
                                 "actual_serializer_forms_observed": [], "multiple_binding_policy_proven": False},
              "native_xor": {"status": "unsupported", "requirement_status": "failed",
                             "attempted": False, "target_count": 0, "target_uuid": None,
                             "target_source": None, "target_diagnostics": [],
                             "selected_population": ["owner", "member0"],
                             "excluded_population": ["member0"],
                             "native_expression_executed": False, "expected_counterexample_result": False,
                             "reason": "Pinned XORConstraint iterates (1..(size(excluded) - 1)) and tests integer f for inclusion in feature occurrences (PLEML.sysml:170-176). The existing serializer path only loads/serializes models; GateAModel.evaluate is a specialized incompatibility resolver, not native constraint execution. No occurrence-configuration native evaluator is integrated; no substitute is run.",
                             "source": LIBRARY, "pin": PLEML_PIN, "command": shlex.join(command),
                             "expected_exit": 2, "defect_reproduced_natively": False}}
    payloads["scoped-fixture.sysml"] = fixture_text(args.binding_count)
    report["artifact_sha256"] = {name: digest(value.encode()) for name, value in payloads.items()}
    args.out.mkdir(parents=True)
    for name, content in payloads.items():
        (args.out / name).write_text(content)
    report["execution_error"] = ""
    if args.licensed:
        try:
            licensed_probe(args, report)
        except (ValueError, OSError, ImportError, RuntimeError) as exc:
            report["execution_error"] = str(exc)
            report["native_xor"]["reason"] = "licensed execution blocked before native requirement: " + str(exc)
    _, _, final_identity = load_experiment(args.experiment)
    if final_identity != identity or git(ROOT, "rev-parse", "HEAD") != executor:
        raise ValueError("source identity moved during scoped execution")
    report["artifact_sha256"].update({p.name: digest(p.read_bytes()) for p in args.out.iterdir() if p.is_file()})
    (args.out / "receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--binding-count", type=int, default=2)
    parser.add_argument("--licensed", action="store_true", help="fresh pinned serializer and bounded native Compiler attempt on licensed x86_64 runner")
    parser.add_argument("--expected-executor")
    parser.add_argument("--native-xor", action="store_true", help="retain exact unsupported native requirement and exit 2")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args)
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"receipt": str(args.out / "receipt.json"), "group_scenarios": len(report["groups"]),
                      "bindings": len(report["bindings"]), "native_xor": report["native_xor"]["status"], "qualified": False}))
    return 2 if args.native_xor or report["execution_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
