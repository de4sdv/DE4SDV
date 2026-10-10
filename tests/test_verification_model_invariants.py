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
- System 1 product requirements (member-product or product-line subject)
  are never verification targets of these System 2 bench cases. A System 2
  design-input requirement is verified with its subject bound to a part
  declared in the case's bench definition, and it states its success
  criteria in its successCriteria attribute (INCOSE A6; owner decision
  2026-10-10) or is listed in a recorded increment gap. A bare verify/satisfy
  of a requirement, which would bind its subject to the whole bench, is
  rejected (comment-insertion resistant);
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
    # Subject-bound requirement verifications count too: since success
    # criteria are requirement attributes, a case may verify only requirements.
    bound = [requirement for _o, requirement, _s, _p, _b in bound_requirement_verifications(code)]
    assert targets or bound, "a verification model must verify something"
    for target in targets:
        declared = re.search(
            rf"\b(?:requirement|part|attribute|item|action|port|enum|verification)"
            rf"\s+(?:def\s+)?{re.escape(target)}\b",
            code,
        )
        assert declared, target
    if bound:
        declared_tree = _declared_requirement_usages()
        for requirement in bound:
            assert requirement in declared_tree, requirement


def test_every_verification_usage_is_performed(model):
    _, code = model
    assert set(verification_usages_names(code)) == set(performed_usages(code))


def verification_usages_names(code: str) -> list[str]:
    return [usage for usage, _ in verification_usages(code)]


def test_no_verify_or_satisfy_relationship_claims_a_product_requirement(model):
    source, _ = model
    assert not has_product_claim(source)


_REQUIREMENT_USAGE_RE = re.compile(r"\brequirement\s+(\w+)\s*:\s*(\w+)\s*\{")
_SUCCESS_CRITERIA_RE = re.compile(r'\battribute\s*:>>\s*successCriteria\s*=\s*"[^"]+"\s*;')
_REQUIREMENT_ID_RE = re.compile(r"\bREQ-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}\b")
_GAP_PART_RE = re.compile(r"\bpart\s+\w+\s*:\s*IncrementGap\s*\{")


# Subject types of System 1 product requirements and needs.
_SYSTEM1_SUBJECT_TYPES = {"ProductLineMemberProduct", "SDVProductLine"}
_SUBJECT_TYPE_RE = re.compile(r"\bsubject\s+\w+\s*:\s*(\w+)\s*;")


def _declared_requirement_usages() -> dict[str, dict]:
    """Requirement usages of the model tree: subject types, whether the usage
    states successCriteria, and the requirement IDs its doc names."""
    usages: dict[str, dict] = {}
    for path in sorted(MODEL_ROOT.rglob("*.sysml")):
        raw = path.read_text(encoding="utf-8")
        code = strip_comments(raw)
        for match in _REQUIREMENT_USAGE_RE.finditer(code):
            body = braced_body(code[match.start():], match.group(0).rstrip("{").strip())
            facts = usages.setdefault(match.group(1), {"subjects": set(), "criteria": False, "ids": set()})
            facts["subjects"].update(_SUBJECT_TYPE_RE.findall(body))
            facts["criteria"] = facts["criteria"] or bool(_SUCCESS_CRITERIA_RE.search(body))
        for match in _REQUIREMENT_USAGE_RE.finditer(raw):
            doc = re.match(r"\s*doc\s*/\*(.*?)\*/", raw[match.end():], re.DOTALL)
            if doc and match.group(1) in usages:
                usages[match.group(1)]["ids"].update(_REQUIREMENT_ID_RE.findall(doc.group(1).split(".")[0]))
    return usages


def _gap_listed_requirement_ids() -> set[str]:
    """Requirement IDs named in the docs of recorded increment gaps."""
    listed: set[str] = set()
    for path in sorted(MODEL_ROOT.rglob("*.sysml")):
        raw = path.read_text(encoding="utf-8")
        for match in _GAP_PART_RE.finditer(raw):
            listed.update(_REQUIREMENT_ID_RE.findall(braced_body(raw[match.start():], match.group(0).rstrip("{").strip())))
    return listed


def _bound_verification_violations(code: str, declared: dict[str, dict], gap_ids: set[str]) -> list[tuple[str, str, str]]:
    """Subject-bound requirement verifications that break the success-criteria/bench rule."""
    violations = []
    for objective, requirement, _subject, part, bench_type in bound_requirement_verifications(code):
        bench_parts = (
            set(re.findall(r"\bpart\s+(\w+)\s*:", braced_body(code, f"part def {bench_type}")))
            if bench_type and re.search(rf"\bpart\s+def\s+{re.escape(bench_type)}\s*\{{", code)
            else set()
        )
        if part not in bench_parts:
            violations.append((objective, requirement, f"bench part {part!r} is not declared in the bench definition"))
        facts = declared.get(requirement)
        if facts is None:
            violations.append((objective, requirement, "target is not a declared design-input requirement"))
            continue
        if facts["subjects"] & _SYSTEM1_SUBJECT_TYPES:
            violations.append((objective, requirement, "target is a System 1 product requirement"))
        if not facts["criteria"] and not (facts["ids"] and facts["ids"] <= gap_ids):
            violations.append((objective, requirement, "target states no successCriteria and no recorded gap lists it"))
    return violations


def test_bound_requirement_verification_states_success_criteria_on_a_bench_part(model):
    _, code = model
    if bound_requirement_verifications(code):
        assert not _bound_verification_violations(code, _declared_requirement_usages(), _gap_listed_requirement_ids())


_SYNTHETIC_CASE = """
  part def Bench { part unitUnderTest : Unit; }
  verification def SyntheticVerification {
    subject verifiedBench : Bench;
    objective syntheticObjective {
      verify reqA { subject unit = verifiedBench.%s; }
    }
  }
"""


def _facts(criteria: bool, subjects: set[str] | None = None) -> dict:
    return {"subjects": subjects or set(), "criteria": criteria, "ids": {"REQ-SYN-S2-001"}}


def test_bound_requirement_verification_rule_rejects_violations():
    stated = {"reqA": _facts(True)}
    assert not _bound_verification_violations(_SYNTHETIC_CASE % "unitUnderTest", stated, set())
    unstated = {"reqA": _facts(False)}
    assert [v[2] for v in _bound_verification_violations(_SYNTHETIC_CASE % "unitUnderTest", unstated, set())] == [
        "target states no successCriteria and no recorded gap lists it"]
    assert not _bound_verification_violations(_SYNTHETIC_CASE % "unitUnderTest", unstated, {"REQ-SYN-S2-001"})
    unknown_part = _bound_verification_violations(_SYNTHETIC_CASE % "elsewhere", stated, set())
    assert [v[2] for v in unknown_part] == ["bench part 'elsewhere' is not declared in the bench definition"]
    outside_bench = _bound_verification_violations(
        (_SYNTHETIC_CASE % "evidenceRecord") + "\n  part evidenceRecord : Record;\n", stated, set())
    assert [v[2] for v in outside_bench] == ["bench part 'evidenceRecord' is not declared in the bench definition"]
    undeclared = _bound_verification_violations(_SYNTHETIC_CASE % "unitUnderTest", {}, set())
    assert [v[2] for v in undeclared] == ["target is not a declared design-input requirement"]
    product = _bound_verification_violations(
        _SYNTHETIC_CASE % "unitUnderTest", {"reqA": _facts(True, {"ProductLineMemberProduct"})}, set())
    assert [v[2] for v in product] == ["target is a System 1 product requirement"]
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
