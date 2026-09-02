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
- no verify/satisfy relationship claims a product requirement (System 1
  members are never verification targets; comment-insertion resistant);
- any outcome→verdict mapping stays inside the bounded VerdictKind
  vocabulary {pass, fail, inconclusive, error} and every scenario-identity
  literal referenced is a member of the corresponding enum.
"""

from __future__ import annotations

import re

import pytest

from sysml_shapes import (
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


def test_no_verify_or_satisfy_relationship_claims_a_product_requirement(model):
    source, _ = model
    assert not has_product_claim(source)


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
