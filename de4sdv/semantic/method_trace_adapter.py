"""Opt-in, source-reference trace adapter; no pilot or runtime mutation.

Reuses MethodEvaluator aggregation, result legality and readiness unchanged.
Only the bounded framing reference grammar is supported. Later engineering
relationships and native validation remain UNASSESSED until a reviewed adapter
can supply them. Source-reference PASS is not SysML validation or acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from . import method_evaluator as me

METHOD_ID = "de4sdv.scope-traces.v1"
POLICY_ID = "topic05-approved-phase-scope-obligations/v1"
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
FEATURES = "textual-notation-of-model/packages/features/"

@dataclass(frozen=True)
class TraceDeclaration:
    method_id: str
    scope_kind: str
    phases: tuple[int, ...]
    completion_claim: str

@dataclass(frozen=True)
class IdentifiedArtifact:
    identity: str
    kind: str

@dataclass(frozen=True)
class TraceWitness:
    identity: str
    source: str
    relation: str
    target: str

@dataclass(frozen=True)
class TraceSnapshot:
    revision: me.RevisionIdentity
    declaration: TraceDeclaration
    increment: str
    artifacts: tuple[IdentifiedArtifact, ...]
    witnesses: tuple[TraceWitness, ...]
    unavailable: tuple[str, ...] = ()

# Governed selection, not a candidate-supplied obligation list. R/F/L/P
# remain separate obligations. Unsupported predicates are still required.
PHASE_RELATIONS = {
    0: ("increment", "declaredScope", "problemStatement", "engineeringQuestion", "lifecycleDecision"),
    1: ("stakeholders", "concerns"),
    2: ("operational-context",),
    3: ("capability-classification",),
    4: ("need-origin",),
    5: ("requirement-derivation",),
    6: ("requirement-to-function",),
    7: ("function-to-logical",),
    8: ("logical-to-physical", "software-boundary-mapping"),
    9: ("configuration-to-assets",),
    10: ("verification-to-target", "criterion-to-evidence"),
    11: ("publication-provenance",),
    12: ("baseline-disposition",),
}
SUPPORTED = frozenset(PHASE_RELATIONS[0] + PHASE_RELATIONS[1])
EXPECTED_KINDS = {
    "increment": "part", "declaredScope": "part", "problemStatement": "requirement",
    "engineeringQuestion": "part", "lifecycleDecision": "part",
    "stakeholders": "stakeholder", "concerns": "concern",
}
SCOPE_PROFILES = {
    "framing": ("framingReady", (0, 1, 2)),
    "requirements": ("requirementsReady", tuple(range(6))),
    "functionalArchitecture": ("architectureReady", (6,)),
    "logicalArchitecture": ("architectureReady", (7,)),
    "physicalRealization": ("architectureReady", (8,)),
    "architecture": ("architectureReady", (6, 7, 8)),
    "configuration": ("architectureReady", (9,)),
    "evidence": ("evidenceReady", (10,)),
    "baseline": ("baselineReady", (12,)),
}

# The bounded grammar is the only authoritative input shape. Neither a digit
# substring nor a foreign prefix may stand in for a governed literal: the
# adapter refuses an unrecognized token instead of salvaging a phase number.
CANONICAL_PHASE_LITERALS = {
    0: "phase0_incrementFraming",
    1: "phase1_concernFraming",
    2: "phase2_operationalContext",
    3: "phase3_capabilityClassification",
    4: "phase4_needs",
    5: "phase5_requirements",
    6: "phase6_functionalArchitecture",
    7: "phase7_logicalArchitecture",
    8: "phase8_physicalRealization",
    9: "phase9_variabilityConfiguration",
    10: "phase10_vvEvidence",
    11: "phase11_publication",
    12: "phase12_baselineNextSlice",
}
CANONICAL_COMPLETION_CLAIMS = frozenset(claim for claim, _ in SCOPE_PROFILES.values())

# The exact owning file and namespace is part of each identity, not a
# category label. These are source adapters for two existing usages only.
FRAMINGS = {
    "INC-AEBS-010": (FEATURES + "aebs/aebs_visualization_framing.sysml",
                     "DE4SDV_AEBSVisualizationFraming", "visualizationTraceObligations"),
    "INC-MW-002": (FEATURES + "middleware/middleware_increment_framing.sysml",
                   "DE4SDV_MiddlewareIncrementFraming::Features::Middleware::IncrementFraming",
                   "traceObligationsMW002"),
}

# Reviewed source-consumer pins for existing increments; not production
# semantic authority. The candidate cannot select these classifications.
GOVERNED_SCOPES = {"INC-AEBS-010": "requirements", "INC-MW-002": "framing"}


def validate_increment_scope(increment_id: str, declaration: TraceDeclaration) -> None:
    if declaration.scope_kind != GOVERNED_SCOPES[increment_id]:
        raise ValueError("candidate contradicts governed increment scope")


def selected_contract(declaration: TraceDeclaration) -> me.MethodContract:
    """Refuse unauthorized method/scope/claim or narrowed phase applicability."""
    expected = SCOPE_PROFILES.get(declaration.scope_kind)
    if declaration.method_id != METHOD_ID or expected is None:
        raise ValueError("unapproved method or unsupported scope")
    claim, minimum_phases = expected
    phases = declaration.phases
    if (declaration.completion_claim != claim or len(set(phases)) != len(phases)
            or not set(minimum_phases) <= set(phases)
            or any(p not in PHASE_RELATIONS for p in phases)):
        raise ValueError("declared scope/phases contradict governed completion claim")
    phase_key = ",".join(str(p) for p in sorted(phases)) + "/" + declaration.completion_claim
    specs = []
    for relation in [r for p in sorted(phases) for r in PHASE_RELATIONS[p]] + ["native-validation"]:
        specs.append(me.ObligationSpec(
            obligation_id=relation, phase=phase_key, subject_selector="increment trace declaration",
            selector_kind=me.SELECTOR_SCOPE_SUBJECT, applicability="governed scope and completion claim",
            applicability_kind=me.APPLICABILITY_UNCONDITIONAL, minimum_population=1,
            permitted_empty=False, permitted_empty_disposition=None, predicate=relation,
            target_filters=(), cardinality=(1, 1000000), required=True,
            evaluation_source=me.EVALUATION_SOURCE_REPOSITORY, attestation_policy_ref="",
            claim_boundary="identified source-reference witness only; no native validation, runtime, safety or acceptance claim",
        ))
    return me.MethodContract(METHOD_ID, POLICY_ID, phase_key, tuple(specs), POLICY_ID)

class TraceEvaluator(me.MethodEvaluator):
    """Adapter dispatch only; frozen result algebra and readiness are inherited."""
    def __init__(self, snapshot: TraceSnapshot):
        self.snapshot = snapshot
        # Public snapshots need their own identity check: they need not have
        # come from repository_snapshot. Agreeing projections coalesce; a
        # conflicting kind never becomes authoritative by tuple order.
        self.artifacts = {}
        self.ambiguous_artifacts = set()
        for artifact in snapshot.artifacts:
            previous = self.artifacts.setdefault(artifact.identity, artifact)
            if previous != artifact:
                self.ambiguous_artifacts.add(artifact.identity)
        for increment_id, (_, namespace, usage) in FRAMINGS.items():
            if snapshot.increment == namespace + "::" + usage:
                validate_increment_scope(increment_id, snapshot.declaration)
        self.contract = selected_contract(snapshot.declaration)
        me.validate_contract(self.contract, predicate_names=tuple(PHASE_RELATIONS[p][i]
                             for p in PHASE_RELATIONS for i in range(len(PHASE_RELATIONS[p]))) + ("native-validation",))

    def _evaluate_obligation(self, spec, ctx, results_by_id):
        relation = spec.predicate
        candidates = [w for w in self.snapshot.witnesses
                      if w.source == self.snapshot.increment and w.relation == relation]
        ambiguous = (self.snapshot.increment in self.ambiguous_artifacts
                     or any(w.target in self.ambiguous_artifacts for w in candidates))
        if relation not in SUPPORTED or relation in self.snapshot.unavailable or ambiguous:
            return [me.EvaluationResult(
                unit_id=spec.obligation_id, coverage=me.COVERAGE_UNASSESSED, state=None,
                verdict=None, reason_codes=(me.NOT_ATTEMPTED,),
                diagnostics=(f"{relation}: no supported authoritative evaluator input; completion remains blocked",),
                claim_boundary=spec.claim_boundary)]
        matches = [w for w in candidates
                   if w.target in self.artifacts and self.artifacts[w.target].kind == EXPECTED_KINDS[relation]]
        outcome = me.PredicateOutcome(
            "satisfied" if matches else "violated",
            reason_codes=() if matches else (me.REQUIRED_RELATION_MISSING,),
            targets=tuple(w.target for w in matches), witnesses=tuple(w.identity for w in matches),
            missing=() if matches else (relation,),
            diagnostics=() if matches else (f"missing identified reference for {relation}",),
        )
        return [self._child_result(spec, ctx.scope.scope_id, outcome)]

def evaluate_snapshot(snapshot: TraceSnapshot) -> me.CanonicalEvaluation:
    context = me.EvaluationContext(
        revision=snapshot.revision, elements=(),
        scope=me.DeclaredEvaluationScope(snapshot.increment, snapshot.increment, (), frozenset(), ()),
    )
    return TraceEvaluator(snapshot).evaluate(context, requested_readiness=(
        me.ReadinessTarget("PHASE_EXIT", snapshot.increment + "/" + snapshot.declaration.completion_claim),))

# One bounded lexical rule shared by comment cleaning and ownership scanning.
# Quoted names are inert just like String literals, including escaped quotes.
_QUOTED_TOKEN = r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'"""
_QUALIFIED_NAME = r"[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*"


def _clean(text: str) -> str:
    # Retain quote tokens before recognizing comments inside their payloads.
    return re.sub(_QUOTED_TOKEN + r'|/\*.*?\*/|//[^\n]*',
                  lambda m: m.group(0) if m.group(0)[0] in "\"'" else " ", text, flags=re.S)

def _structure(text: str) -> str:
    """Mask both quote-token forms without moving offsets; comments removed."""
    return re.sub(_QUOTED_TOKEN, lambda m: " " * len(m.group()), text, flags=re.S)


def _direct_matches(text: str, pattern: str):
    structure = _structure(text)
    depth = 0
    depths = []
    for char in structure:
        depths.append(depth)
        depth += (char == "{") - (char == "}")
    return [m for m in re.finditer(pattern, structure) if depths[m.start()] == 0]


def _matched_body(text: str, match) -> str | None:
    if match.group(1) == ";":
        return ""
    depth = 1
    start = match.end()
    structure = _structure(text)
    for pos in range(start, len(structure)):
        depth += (structure[pos] == "{") - (structure[pos] == "}")
        if depth == 0:
            return text[start:pos]
    return None


def _owned_matches(body: str, pattern: str):
    """Direct-owned CODE matches inside an already comment-free body.

    Matching runs on the quote-masked structure, so a String or unrestricted
    name cannot fabricate a declaration, and depth filtering excludes
    members nested in an inner body or a foreign package — only declarations
    directly owned by ``body`` count. Masking preserves offsets, so a returned
    match addresses the original text.
    """
    structure = _structure(body)
    depths, depth = [], 0
    for char in structure:
        depths.append(depth)
        depth += (char == "{") - (char == "}")
    return [match for match in re.finditer(pattern, structure) if depths[match.start()] == 0]


def parse_applicable_phases(value: str) -> tuple[int, ...]:
    """Whole bounded enum-list grammar; unrecognized tokens are refused.

    The complete canonical literal is validated, not a salvaged digit: a
    foreign enum namespace, an undeclared literal, extra expressions and
    literal-string substitutes all raise instead of becoming the canonical
    declaration. Only the exact governed owner qualification is permitted.
    """
    match = re.fullmatch(r"\s*\((?P<items>[^()]*)\)\s*", value)
    if not match:
        raise ValueError("applicablePhases must be a parenthesized governed phase list")
    items = [item.strip() for item in match.group("items").split(",")]
    if not items or any(not item for item in items):
        raise ValueError("applicablePhases contains an empty or missing phase token")
    phases = []
    for item in items:
        token = re.fullmatch(r"(?:DE4SDV_MethodProcess::)?MethodPhase::([A-Za-z_][A-Za-z0-9_]*)", item)
        if not token:
            raise ValueError("unsupported phase token: " + item)
        # Compare original spelling before selecting a number; never normalize
        # leading zeros or Unicode digits into a declared ASCII enum literal.
        number = next((n for n, literal in CANONICAL_PHASE_LITERALS.items()
                       if literal == token.group(1)), None)
        if number is None:
            raise ValueError("phase token is not a governed MethodPhase literal: " + item)
        phases.append(number)
    return tuple(phases)


def _namespace_body(text: str, namespace: str) -> str:
    for name in namespace.split("::"):
        matches = _direct_matches(text, r"\bpackage\s+" + re.escape(name) + r"\s*({)")
        if len(matches) != 1:
            raise ValueError("increment namespace missing or ambiguous")
        child_body = _matched_body(text, matches[0])
        if child_body is None:
            raise ValueError("increment namespace missing or ambiguous")
        text = child_body
    return text


def _body(text: str, name: str) -> str | None:
    """Compatibility view: a body only when exactly one direct declaration."""
    body, unavailable = _owned_body(text, name)
    return None if unavailable else body


def _owned_records(text: str, name: str):
    """Inventory a named direct-owned header before interpreting its shape.

    Header boundaries stop at the declaration's own semicolon/opening brace;
    nested bodies, comments (already cleaned) and quote tokens cannot count.
    Discovery deliberately does not require an explicit type or supported kind.
    A bounded optional short-name token also establishes header presence, but
    never expands the supported witness grammar below.
    It is a bounded identity inventory, not a general SysML parser.
    """
    prefix = (r"\s*(?:doc\s+)*(?:(?:public|private|protected|abstract|variation|variant|"
              r"individual|ref|readonly|derived|in|out|inout)\s+)*"
              r"[A-Za-z_][A-Za-z0-9_]*(?:\s+def)?\s+(?:<[^<>;{}]*>\s*)?(?::>>\s*)?"
              + re.escape(name) + r"(?!\w)")
    return [record for record in _direct_matches(text, r"[^{};]*([;{])")
            if re.match(prefix, record.group())]


def _owned_body(text: str, name: str) -> tuple[str | None, bool]:
    """Return ``(body, unavailable)`` for one directly owned declaration.

    No declaration is quiet absence, which the caller resolves per relation.
    Two or more directly owned declarations are a bounded identity ambiguity:
    the adapter cannot know which one a reference meant, so the relation must
    become unavailable/UNASSESSED rather than an assessed FAIL or PASS.
    A present but unsupported header is likewise unavailable, not absence.
    """
    matches = _owned_records(text, name)
    if len(matches) > 1:
        return None, True
    if not matches:
        return None, False
    if not re.fullmatch(r"\s*(?:doc\s+)*(?:part|requirement|concern)\s+" + re.escape(name)
                        + r"\s*:\s*" + _QUALIFIED_NAME + r"\s*[;{]",
                        text[matches[0].start():matches[0].end()]):
        return None, True
    body = _matched_body(text, matches[0])
    return body, body is None

def repository_snapshot(repo: Path, increment_id: str) -> TraceSnapshot:
    """Bounded source-reference extraction, NOT a SysML parser/API binding.

    Only direct-owned, simple ASCII-named declarations supply identities;
    quote tokens are inert. No evaluation of arbitrary expressions, imports,
    subtyping, full SysML validity or transitive relationships. Unrecognized
    or ambiguous declarations are unavailable; native validation stays gated.
    """
    path, namespace, usage = FRAMINGS[increment_id]
    text = _namespace_body(_clean((repo / path).read_text()), namespace)
    body = _body(text, usage)
    if body is None:
        raise ValueError("increment trace declaration missing or ambiguous")
    def declared(pattern):
        matches = _owned_matches(body, pattern)
        if len(matches) != 1:
            raise ValueError("missing/ambiguous declaration: " + pattern)
        return body[matches[0].start():matches[0].end()]

    def scalar(name):
        raw = declared(r"attribute\s+:>>\s+" + name + r"\s*=\s*[^;]*;")
        return raw.split("=", 1)[1].rstrip().rstrip(";").strip()

    claim_match = re.fullmatch(r"(?:DE4SDV_MethodTraces::)?TraceCompletionClaim::([A-Za-z_]\w*)",
                               scalar("completionClaim"))
    if not claim_match or claim_match.group(1) not in CANONICAL_COMPLETION_CLAIMS:
        raise ValueError("completionClaim is not a governed TraceCompletionClaim literal")
    claim = claim_match.group(1)
    scope_match = re.fullmatch(r'"([^"]*)"', scalar("scopeKind"))
    if not scope_match:
        raise ValueError("scopeKind must be one String literal")
    scope = scope_match.group(1)
    phases = parse_applicable_phases(scalar("applicablePhases"))
    selected = [match.group(1) for match in _owned_matches(
        body, r"ref\s+part\s+:>>\s+selectedMethod\s*=\s*([\w:]+);")]
    if selected != ["DE4SDV_MethodTraces::approvedScopedTraceMethod"]:
        raise ValueError("selected method is not the governed approved method identity")
    declaration = TraceDeclaration(METHOD_ID, scope, phases, claim)
    selected_contract(declaration)
    validate_increment_scope(increment_id, declaration)
    owner = namespace + "::" + usage
    artifacts, witnesses, unavailable = [], [], []
    for relation in SUPPORTED:
        refs = _owned_records(body, relation)
        if len(refs) > 1:
            unavailable.append(relation)
            continue
        if not refs: continue
        # Presence/identity is established first. Parsing only supported RHS
        # expressions must not erase an unsupported member into missing/FAIL.
        reference = re.fullmatch(r"\s*(?:doc\s+)*ref\s+(?:part|requirement)\s+:>>\s+"
                                 + re.escape(relation) + r"\s*=\s*(" + _QUALIFIED_NAME + r")\s*;",
                                 body[refs[0].start():refs[0].end()])
        if not reference:
            unavailable.append(relation)
            continue
        target = reference.group(1)
        prefix = namespace + "::"
        if not target.startswith(prefix):
            unavailable.append(relation)
            continue
        names = target[len(prefix):].split("::")
        if len(names) not in (1, 2):
            unavailable.append(relation)
            continue
        artifact_body, unavailable_target = _owned_body(text, names[0])
        if unavailable_target:
            # Ambiguous or unsupported targets cannot supply a single witness.
            unavailable.append(relation)
            continue
        if artifact_body is None: continue
        if len(names) == 2:
            stakeholders = _owned_records(artifact_body, names[1])
            if len(stakeholders) > 1:
                unavailable.append(relation)
                continue
            if not stakeholders:
                continue
            if not re.fullmatch(r"\s*(?:doc\s+)*stakeholder\s+" + re.escape(names[1])
                                + r"\s*:\s*" + _QUALIFIED_NAME + r"\s*[;{]",
                                artifact_body[stakeholders[0].start():stakeholders[0].end()]):
                unavailable.append(relation)
                continue
        kind_matches = _owned_matches(
            text, r"\b(part|requirement|concern)\s+" + re.escape(names[0]) + r"\s*:")
        if len(kind_matches) != 1: continue
        kind = "stakeholder" if len(names) == 2 else kind_matches[0].group(1)
        artifacts.append(IdentifiedArtifact(target, kind))
        witnesses.append(TraceWitness(owner + "::" + relation, owner, relation, target))
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    # Deliberately distinguish working-tree source inspection from native API
    # or exact committed candidate evidence. No API provenance is invented.
    revision = me.RevisionIdentity("working-tree@" + commit, "unbound", "unbound", owner)
    return TraceSnapshot(revision, declaration, owner, tuple(artifacts), tuple(witnesses), tuple(unavailable))

def evaluate_repository_framing(repo: Path, increment_id: str) -> me.CanonicalEvaluation:
    return evaluate_snapshot(repository_snapshot(repo, increment_id))


def main(argv=None) -> int:
    """Inspection success is exit 0, not an engineering readiness approval."""
    import argparse
    import json
    parser = argparse.ArgumentParser(description="Opt-in SOURCE-reference inspection, not production semantic runtime parsing")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--increment", choices=sorted(FRAMINGS), required=True)
    args = parser.parse_args(argv)
    envelope = {"inspection_kind": "opt-in-source-reference", "production_runtime": False}
    try:
        envelope["evaluation"] = evaluate_repository_framing(args.repo, args.increment).increment_status()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        envelope["error"] = str(error)
        print(json.dumps(envelope, sort_keys=True))
        return 2
    print(json.dumps(envelope, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
