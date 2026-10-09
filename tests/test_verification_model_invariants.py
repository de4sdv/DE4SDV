"""Capability-agnostic invariants for every SysML verification model.

One parametrized suite over *all* verification models discovered under
``textual-notation-of-model/`` (AEBS, middleware, and any future capability).
Adding a new capability with verification content adds test cases here
automatically — no new per-capability model-shape test file.

What each model must satisfy structurally:

- every ``verification def`` has exactly one ``objective``, a
  collect → process → evaluate data pipeline, a ``verifiedBench`` subject,
  and a deterministic ``verdict`` return;
- every ``verification`` usage binds its subject and carries a
  ``@VerificationMethod`` and its type resolves to a ``verification def``
  in the same file;
- every ``verify`` target is declared somewhere in the file and every usage
  is performed;
- a design-input requirement is verified only next to an acceptance
  criterion of the same objective and with its subject bound to a declared
  part of the case's bench (owner decision 2026-10-09: a case verifies the
  requirement its criterion bounds); a bare verify/satisfy of a requirement,
  which would bind its subject to the whole bench, is rejected
  (comment-insertion resistant);
- any outcome→verdict mapping stays inside the bounded VerdictKind
  vocabulary {pass, fail, inconclusive, error} and every scenario-identity
  literal referenced is a member of the corresponding enum.
"""

from __future__ import annotations

import re

import pytest

from sysml_shapes import (
    MODEL_ROOT,
    bound_requirement_verifications,
    braced_body,
    has_product_claim,
    load_model,
    performed_usages,
    strip_comments,
    verification_defs,
    verification_model_paths,
    verification_usages,
    verify_targets,
)

VERDICT_LITERALS = {"pass", "fail", "inconclusive", "error"}

# Verdicts must flow from these native SysML kinds; anything else is drift.
_VERDICT_KIND_RE = re.compile(r"VerdictKind::(\w+)")


@pytest.fixture(
    params=verification_model_paths(),
    ids=lambda p: f"{p.parent.name}/{p.name}",
)
def model(request) -> tuple[str, str]:
    """(raw source, comment-stripped source) for each verification model."""
    return load_model(request.param)


def test_model_discovers_at_least_the_known_verification_models():
    # Guard the discovery itself: if this ever drops below the known set,
    # discovery (not the model) probably regressed.
    paths = verification_model_paths()
    names = {p.name for p in paths}
    assert "aebs_evidence.sysml" in names
    assert "middleware_verification_evidence.sysml" in names
    assert len(paths) >= 9


def test_every_verification_def_has_single_objective(model):
    source, code = model
    for definition in verification_defs(code):
        body = braced_body(code, f"verification def {definition}")
        assert len(re.findall(r"\bobjective\b", body)) == 1, definition


def test_every_verification_def_runs_the_collect_process_evaluate_pipeline(model):
    _, code = model
    for definition in verification_defs(code):
        body = braced_body(code, f"verification def {definition}")
        assert "action collectData" in body, definition
        assert "action processData" in body, definition
        assert "action evaluateData" in body, definition
        assert "return verdict : VerdictKind = evaluateData.verdict;" in body, (
            definition
        )
        assert re.search(r"\bsubject\s+verifiedBench\s*:\s*\S", body), definition


def test_every_verification_usage_binds_subject_and_verification_method(model):
    _, code = model
    usage_re = re.compile(r"\bverification\s+\w+\s*:\s*\w+\s*\{")
    for match in usage_re.finditer(code):
        body = braced_body(code, match.group(0).rstrip("{").strip())
        assert "subject verifiedBench :>" in body, match.group(0)
        assert "@VerificationMethod{" in body, match.group(0)


def test_every_verification_usage_type_resolves_to_a_local_def(model):
    _, code = model
    defs = set(verification_defs(code))
    usages = verification_usages(code)
    assert usages, "model declares verification content but no usages"
    for usage, definition in usages:
        assert definition in defs, (usage, definition)


def test_every_verify_target_is_declared_in_the_model(model):
    _, code = model
    targets = verify_targets(code)
    assert targets, "a verification model must verify something"
    for target in targets:
        declared = re.search(
            rf"\b(?:requirement|part|attribute|item|action|port|enum|verification)"
            rf"\s+(?:def\s+)?{re.escape(target)}\b",
            code,
        )
        assert declared, target


def test_every_verification_usage_is_performed(model):
    _, code = model
    assert set(verification_usages_names(code)) == set(performed_usages(code))


def verification_usages_names(code: str) -> list[str]:
    return [usage for usage, _ in verification_usages(code)]


def test_no_unbound_verify_or_satisfy_of_a_requirement(model):
    source, _ = model
    assert not has_product_claim(source)


_REQUIREMENT_USAGE_RE = re.compile(r"\brequirement\s+(\w+)\s*:\s*(\w+)\s*\{")
_CRITERION_DEF_RE = re.compile(r"\brequirement\s+def\s+(\w+)\s*:>\s*AcceptanceCriterion\s*;")


def _declared_requirement_usages() -> set[str]:
    names: set[str] = set()
    for path in sorted(MODEL_ROOT.rglob("*.sysml")):
        names.update(name for name, _ in _REQUIREMENT_USAGE_RE.findall(strip_comments(path.read_text(encoding="utf-8"))))
    return names


def _bound_verification_violations(code: str, declared: set[str]) -> list[tuple[str, str, str]]:
    """Subject-bound requirement verifications that break the criterion/bench rule."""
    criterion_defs = set(_CRITERION_DEF_RE.findall(code))
    criteria = {name for name, definition in _REQUIREMENT_USAGE_RE.findall(code) if definition in criterion_defs}
    bench_parts = set(re.findall(r"\bpart\s+(\w+)\s*:", code))
    violations = []
    for objective, requirement, _subject, part in bound_requirement_verifications(code):
        body = braced_body(code, f"objective {objective}")
        if not criteria & set(re.findall(r"\bverify\s+(\w+)\s*;", body)):
            violations.append((objective, requirement, "no acceptance criterion verified in the objective"))
        if part not in bench_parts:
            violations.append((objective, requirement, f"bench part {part!r} is not declared"))
        if requirement not in declared or requirement in criteria:
            violations.append((objective, requirement, "target is not a declared design-input requirement"))
    return violations


def test_bound_requirement_verification_sits_next_to_a_criterion_on_a_bench_part(model):
    _, code = model
    if bound_requirement_verifications(code):
        assert not _bound_verification_violations(code, _declared_requirement_usages())


_SYNTHETIC_CASE = """
  requirement def SyntheticCriterion :> AcceptanceCriterion;
  requirement criterionA : SyntheticCriterion { }
  requirement reqA : SyntheticRequirement { }
  part def Bench { part unitUnderTest : Unit; }
  verification def SyntheticVerification {
    subject verifiedBench : Bench;
    objective syntheticObjective {
      %s
      verify reqA { subject unit = verifiedBench.%s; }
    }
  }
"""


def test_bound_requirement_verification_rule_rejects_violations():
    declared = {"criterionA", "reqA"}
    assert not _bound_verification_violations(_SYNTHETIC_CASE % ("verify criterionA;", "unitUnderTest"), declared)
    without_criterion = _bound_verification_violations(_SYNTHETIC_CASE % ("", "unitUnderTest"), declared)
    assert [v[2] for v in without_criterion] == ["no acceptance criterion verified in the objective"]
    unknown_part = _bound_verification_violations(_SYNTHETIC_CASE % ("verify criterionA;", "elsewhere"), declared)
    assert [v[2] for v in unknown_part] == ["bench part 'elsewhere' is not declared"]
    undeclared = _bound_verification_violations(_SYNTHETIC_CASE % ("verify criterionA;", "unitUnderTest"), {"criterionA"})
    assert [v[2] for v in undeclared] == ["target is not a declared design-input requirement"]
    assert has_product_claim("objective o { verify reqA; }")


def test_no_satisfy_relationships_anywhere(model):
    # Verification models prove claims via native verify relationships;
    # satisfy belongs to product/configuration models, not evidence models.
    _, code = model
    assert not re.search(r"\bsatisfy\b", code)


def test_verdict_vocabulary_is_bounded(model):
    _, code = model
    found = set(_VERDICT_KIND_RE.findall(code))
    unexpected = found - VERDICT_LITERALS
    assert not unexpected, sorted(unexpected)


def test_outcome_to_verdict_mapping_is_total_and_native(model):
    _, code = model
    for increment in re.findall(r"\bcalc def Map(\d{3}[A-Z0-9]*)OutcomeToVerdict", code):
        body = braced_body(code, f"calc def Map{increment}OutcomeToVerdict")
        assert f"in outcome : EvidenceOutcome{increment}" in body, increment
        assert "VerdictKind::" in body, increment


def test_scenario_identity_literals_are_enum_members(model):
    _, code = model
    for increment in re.findall(r"\benum def ScenarioIdentity(\d{3}[A-Z0-9]*)", code):
        enum_body = braced_body(code, f"enum def ScenarioIdentity{increment}")
        members = set(re.findall(r"(\w+)\s*;", enum_body))
        referenced = set(
            re.findall(rf"ScenarioIdentity{increment}::(\w+)", code)
        )
        assert members, increment
        assert referenced <= members, (
            increment,
            sorted(referenced - members),
        )
