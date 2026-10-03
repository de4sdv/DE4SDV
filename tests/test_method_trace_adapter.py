"""Phase/scope trace obligations evaluated from native model relationships.

The trace declaration only selects method, scope, phases, completion claim and
increment. Phase 0/1 witnesses are the increment package's native relationships;
every mutation below runs on an in-memory overlay of the real framing source
(never a copied model) or on a small synthetic CLI fixture.
"""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]
AEBS = "INC-AEBS-010"
AEBS_NS = "DE4SDV_AEBSVisualizationFraming::"

# Native relationship anchors in the real AEBS framing source.
STAKEHOLDER_CONNECTION = ("connection visualizationStakeholderParticipation : HasStakeholder\n"
                          "    connect incAEBS010 to visualizationProblemStatement.systemsEngineer;")
PROBLEM_SUBJECT = "    subject increment : VisualizationIncrement;\n"
PROBLEM_HEADER = "requirement visualizationProblemStatement : ProblemStatement"
SCOPE_HEADER = "part visualizationScope : IncrementScope"
QUESTION_HEADER = "part visualizationEngineeringQuestion : IncrementEngineeringQuestion"
DECISION_HEADER = "part visualizationLifecycleDecision : IncrementLifecycleDecision"
INCREMENT_DEFINITION = "part def VisualizationIncrement :> EngineeringIncrement;"
FRAMES = ("      frame visualizationProvenanceConcern;\n"
          "      frame visualizationBoundaryConcern;\n"
          "      frame predecessorIndependenceConcern;\n")
SYSTEMS_ENGINEER = "    stakeholder systemsEngineer : SystemsEngineer;\n"
TRACE_SLOT_RELATIONS = ("declaredScope", "problemStatement", "engineeringQuestion",
                        "lifecycleDecision", "stakeholders", "concerns")


class ScopedTraceTests(unittest.TestCase):
    # ── Real sources ────────────────────────────────────────────────────────
    def test_real_framing_is_evaluated_from_native_relationships(self):
        self.assertIsNotNone(importlib.util.find_spec("de4sdv.semantic.method_trace_adapter"))
        from de4sdv.semantic.method_trace_adapter import evaluate_repository_framing, repository_snapshot
        for increment in ("INC-AEBS-010", "INC-MW-002"):
            result = evaluate_repository_framing(ROOT, increment)
            self.assertEqual(result.assessment_coverage, "UNASSESSED")
            self.assertIsNone(result.conformance_verdict)
            self.assertEqual(result.readiness[0].readiness, "BLOCKED")
            known = [r for r in result.results if r.verdict == "PASS"]
            self.assertEqual(len(known), 7)
            self.assertTrue(all(r.witnesses for r in known))
            self.assertNotIn("physical-realization", result.required_units)
            snapshot = repository_snapshot(ROOT, increment)
            # Witness identities name native relationships, never a declaration slot.
            for witness in snapshot.witnesses:
                self.assertNotIn("TraceObligations::", witness.identity)

    def test_real_witnesses_are_the_native_relationship_targets(self):
        from de4sdv.semantic.method_trace_adapter import repository_snapshot
        snapshot = repository_snapshot(ROOT, AEBS)
        by_relation = {}
        for witness in snapshot.witnesses:
            by_relation.setdefault(witness.relation, set()).add(witness.target)
        self.assertEqual(by_relation, {
            "increment": {AEBS_NS + "incAEBS010"},
            "declaredScope": {AEBS_NS + "visualizationScope"},
            "problemStatement": {AEBS_NS + "visualizationProblemStatement"},
            "engineeringQuestion": {AEBS_NS + "visualizationEngineeringQuestion"},
            "lifecycleDecision": {AEBS_NS + "visualizationLifecycleDecision"},
            "stakeholders": {AEBS_NS + "visualizationProblemStatement::systemsEngineer"},
            "concerns": {AEBS_NS + "visualizationProvenanceConcern",
                         AEBS_NS + "visualizationBoundaryConcern",
                         AEBS_NS + "predecessorIndependenceConcern"},
        })
        stakeholder = next(w for w in snapshot.witnesses if w.relation == "stakeholders")
        self.assertEqual(stakeholder.identity, AEBS_NS + "visualizationStakeholderParticipation")

    def test_trace_declaration_carries_no_parallel_reference_slots(self):
        import re
        from de4sdv.semantic.method_trace_adapter import _clean
        model = (ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_traces.sysml").read_text()
        block = _clean(model).split("part def IncrementTraceObligations", 1)[1]
        features = set(re.findall(r"(?:ref\s+part|ref\s+requirement|attribute)\s+(\w+)", block))
        self.assertEqual(features, {"increment", "selectedMethod", "scopeKind",
                                    "applicablePhases", "completionClaim"})
        for path in ("textual-notation-of-model/packages/features/aebs/aebs_visualization_framing.sysml",
                     "textual-notation-of-model/packages/features/middleware/middleware_increment_framing.sysml"):
            text = _clean((ROOT / path).read_text())
            for relation in TRACE_SLOT_RELATIONS:
                self.assertNotRegex(text, r":>>\s+" + relation + r"\b")

    # ── Native evidence is the evaluated evidence (review R1) ───────────────
    def test_deleting_native_stakeholder_connection_fails_stakeholders(self):
        result = self._evaluate_mutation(STAKEHOLDER_CONNECTION, "")
        self.assertIn("stakeholders", result.failed_ids)
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")

    def test_each_native_relationship_removal_fails_only_its_obligation(self):
        cases = (
            (SCOPE_HEADER, "part visualizationScope : IncrementAssumption", ("declaredScope",)),
            (QUESTION_HEADER, "part visualizationEngineeringQuestion : IncrementAssumption",
             ("engineeringQuestion",)),
            (DECISION_HEADER, "part visualizationLifecycleDecision : IncrementAssumption",
             ("lifecycleDecision",)),
            (PROBLEM_SUBJECT, "", ("problemStatement",)),
            (FRAMES, "", ("concerns",)),
            (STAKEHOLDER_CONNECTION, "", ("stakeholders",)),
        )
        for old, new, failed in cases:
            with self.subTest(old=old.strip()[:60]):
                result = self._evaluate_mutation(old, new)
                self.assertEqual(set(result.failed_ids), set(failed))
                for row in result.results:
                    row.validate()
                    if row.unit_id in failed:
                        self.assertEqual(row.verdict, "FAIL")
                        self.assertIn("REQUIRED_RELATION_MISSING", row.reason_codes)
                        self.assertFalse(row.witnesses)
                self.assertEqual(result.readiness[0].readiness, "BLOCKED")
                self.assertIsNone(result.conformance_verdict)

    def test_problem_statement_needs_subject_typed_by_the_increment(self):
        result = self._evaluate_mutation(PROBLEM_SUBJECT, "    subject increment : OtherIncrement;\n")
        self.assertIn("problemStatement", result.failed_ids)

    def test_stakeholder_connection_from_another_owner_is_not_participation(self):
        result = self._evaluate_mutation(
            "connect incAEBS010 to visualizationProblemStatement.systemsEngineer;",
            "connect visualizationScope to visualizationProblemStatement.systemsEngineer;")
        self.assertIn("stakeholders", result.failed_ids)

    def test_stakeholder_end_must_be_a_native_stakeholder_member(self):
        result = self._evaluate_mutation(
            "visualizationProblemStatement.systemsEngineer;",
            "visualizationProblemStatement.notAMember;")
        self.assertIn("stakeholders", result.failed_ids)

    def test_increment_typed_by_non_increment_definition_fails(self):
        result = self._evaluate_mutation(INCREMENT_DEFINITION,
                                         "part def VisualizationIncrement :> IncrementScope;")
        self.assertIn("increment", result.failed_ids)

    def test_missing_increment_reference_fails_increment_and_blocks_dependents(self):
        result = self._evaluate_mutation(
            "    ref part :>> increment = DE4SDV_AEBSVisualizationFraming::incAEBS010;\n", "")
        self.assertIn("increment", result.failed_ids)
        for relation in ("problemStatement", "stakeholders"):
            self.assertIn(relation, result.unassessed_ids)

    # ── Inert text and foreign ownership cannot fabricate witnesses ─────────
    def test_quoted_or_commented_relationships_are_inert(self):
        for wrap in (lambda s: "/* " + s + " */",
                     lambda s: "attribute note : ScalarValues::String = \"" + s.replace('"', "") + "\";",
                     lambda s: "attribute '" + s + "' : ScalarValues::String;"):
            with self.subTest(wrap=wrap("x")):
                result = self._evaluate_mutation(STAKEHOLDER_CONNECTION, wrap(STAKEHOLDER_CONNECTION))
                self.assertIn("stakeholders", result.failed_ids)
                result = self._evaluate_mutation(FRAMES, "      " + wrap(FRAMES.strip()) + "\n")
                self.assertIn("concerns", result.failed_ids)

    def test_relationship_nested_in_foreign_owner_is_not_the_increments(self):
        result = self._evaluate_mutation(
            STAKEHOLDER_CONNECTION, "package Foreign {\n  " + STAKEHOLDER_CONNECTION + "\n}")
        self.assertIn("stakeholders", result.failed_ids)
        result = self._evaluate_mutation(
            SCOPE_HEADER, "package Foreign { part visualizationScope : IncrementScope; }\n"
                          "part otherThing : IncrementAssumption")
        self.assertIn("declaredScope", result.failed_ids)

    def test_framed_concern_not_owned_by_the_increment_is_not_its_witness(self):
        result = self._evaluate_mutation(
            FRAMES, "      frame DE4SDV_MethodViewpoints::IncrementBoundaryConcern;\n")
        self.assertIn("concerns", result.unassessed_ids)
        result = self._evaluate_mutation(FRAMES, "      frame foreignOnlyConcern;\n")
        self.assertIn("concerns", result.failed_ids)

    # ── Ambiguity and unsupported present input stay UNASSESSED ─────────────
    def test_duplicate_native_artifacts_are_unassessed_not_failed(self):
        cases = (
            (SCOPE_HEADER + " {", "part secondScope : IncrementScope;\n  " + SCOPE_HEADER + " {",
             ("declaredScope",)),
            (QUESTION_HEADER + " {", "part secondQuestion : IncrementEngineeringQuestion;\n  "
             + QUESTION_HEADER + " {", ("engineeringQuestion",)),
            (DECISION_HEADER + " {", "part secondDecision : IncrementLifecycleDecision;\n  "
             + DECISION_HEADER + " {", ("lifecycleDecision",)),
            (STAKEHOLDER_CONNECTION, STAKEHOLDER_CONNECTION + "\n  " + STAKEHOLDER_CONNECTION,
             ("stakeholders",)),
            (SYSTEMS_ENGINEER, SYSTEMS_ENGINEER + SYSTEMS_ENGINEER, ("stakeholders",)),
            (PROBLEM_SUBJECT, PROBLEM_SUBJECT + PROBLEM_SUBJECT, ("problemStatement",)),
            ("part incAEBS010 : VisualizationIncrement {",
             "part incAEBS010 : VisualizationIncrement;\n  part incAEBS010 : VisualizationIncrement {",
             ("increment", "problemStatement", "stakeholders")),
        )
        for old, new, relations in cases:
            with self.subTest(new=new.strip()[:70]):
                self._assert_unavailable(self._snapshot_mutation(old, new), relations)

    def test_short_name_or_untyped_duplicates_are_unassessed(self):
        for duplicate in ("part visualizationScope;", "part <probe> visualizationScope;",
                          "item visualizationScope;", "part < probe > visualizationScope;"):
            for first in (True, False):
                with self.subTest(duplicate=duplicate, first=first):
                    old = SCOPE_HEADER + " {"
                    new = (duplicate + "\n  " + old) if first else old
                    snapshot = (self._snapshot_mutation(old, new) if first else
                                self._snapshot_mutation(INCREMENT_DEFINITION,
                                                        INCREMENT_DEFINITION + "\n  " + duplicate))
                    self._assert_unavailable(snapshot, ("declaredScope",))

    def test_unsupported_native_shapes_are_unassessed(self):
        view = "view aebsVisualizationFramingView {"
        viewpoint = "viewpoint selectedFramingViewpoint : IncrementFramingViewpoint {"
        cases = (
            # SPEC review: duplicate or modifier-prefixed view/viewpoint headers are
            # present input; they must not PASS nor be silently ignored into FAIL.
            (view, "view aebsVisualizationFramingView;\n  " + view, ("concerns",)),
            (viewpoint, "viewpoint selectedFramingViewpoint;\n    " + viewpoint, ("concerns",)),
            (view, "private " + view, ("concerns",)),
            (viewpoint, "private " + viewpoint, ("concerns",)),
            (view, "view <probe> aebsVisualizationFramingView {", ("concerns",)),
            (SCOPE_HEADER, "part visualizationScope : IncrementScope[1]", ("declaredScope",)),
            (SCOPE_HEADER, "part visualizationScope : (IncrementScope)", ("declaredScope",)),
            (PROBLEM_HEADER, "requirement visualizationProblemStatement : ProblemStatement[1]",
             ("problemStatement",)),
            (PROBLEM_SUBJECT, "    subject increment;\n", ("problemStatement",)),
            ("connect incAEBS010 to visualizationProblemStatement.systemsEngineer;",
             "connect (incAEBS010) to visualizationProblemStatement.systemsEngineer;", ("stakeholders",)),
            ("frame visualizationBoundaryConcern;", "frame (visualizationBoundaryConcern);", ("concerns",)),
            (SYSTEMS_ENGINEER, "    stakeholder systemsEngineer : SystemsEngineer[1];\n",
             ("stakeholders",)),
        )
        for old, new, relations in cases:
            with self.subTest(new=new.strip()[:70]):
                self._assert_unavailable(self._snapshot_mutation(old, new), relations)

    def test_local_kernel_homonym_cannot_witness_increment_or_typed_artifacts(self):
        """SPEC re-review F1: a local EngineeringIncrement/IncrementScope homonym
        hides the kernel identity; unqualified references must not PASS."""
        shadow = INCREMENT_DEFINITION + "\n  part def EngineeringIncrement :> IncrementAssumption;"
        snapshot = self._snapshot_mutation(INCREMENT_DEFINITION, shadow)
        self._assert_unavailable(snapshot, ("increment", "problemStatement", "stakeholders"))
        direct = self._snapshot_mutation(
            (INCREMENT_DEFINITION, "part incAEBS010 : VisualizationIncrement {"),
            (INCREMENT_DEFINITION + "\n  part def EngineeringIncrement :> IncrementAssumption;",
             "part incAEBS010 : EngineeringIncrement {"))
        self._assert_unavailable(direct, ("increment",))
        for type_name, relation in (("IncrementScope", "declaredScope"),
                                    ("ProblemStatement", "problemStatement"),
                                    ("HasStakeholder", "stakeholders")):
            with self.subTest(type_name=type_name):
                snapshot = self._snapshot_mutation(
                    INCREMENT_DEFINITION, INCREMENT_DEFINITION + "\n  part def " + type_name + ";")
                self._assert_unavailable(snapshot, (relation,))

    def test_unrelated_local_kernel_name_does_not_shadow_a_different_reference(self):
        """Final SPEC: only a same-name local declaration shadows; a different
        kernel name declared locally must not over-refuse direct typing."""
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        for extra in ("part def Foo;", "part def FeatureIncrement :> IncrementAssumption;"):
            with self.subTest(extra=extra):
                snapshot = self._snapshot_mutation(
                    (INCREMENT_DEFINITION, "part incAEBS010 : VisualizationIncrement {",
                     "subject increment : VisualizationIncrement;"),
                    (INCREMENT_DEFINITION + "\n  " + extra, "part incAEBS010 : EngineeringIncrement {",
                     "subject increment : EngineeringIncrement;"))
                result = evaluate_snapshot(snapshot)
                self.assertEqual(len([r for r in result.results if r.verdict == "PASS"]), 7)
        same = self._snapshot_mutation(
            (INCREMENT_DEFINITION, "part incAEBS010 : VisualizationIncrement {"),
            (INCREMENT_DEFINITION + "\n  part def EngineeringIncrement;",
             "part incAEBS010 : EngineeringIncrement {"))
        self._assert_unavailable(same, ("increment",))

    def test_qualified_kernel_parent_still_identifies_the_increment(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._snapshot_mutation(
            INCREMENT_DEFINITION,
            "part def VisualizationIncrement :> DE4SDV_MethodContext::EngineeringIncrement;")
        result = evaluate_snapshot(snapshot)
        self.assertEqual(len([r for r in result.results if r.verdict == "PASS"]), 7)

    def test_stakeholder_owner_must_be_a_requirement(self):
        """SPEC re-review F2: a stakeholder member inside a part is not admitted."""
        owner = ("part asmStakeholderHost : IncrementAssumption {\n"
                 "    stakeholder systemsEngineer : SystemsEngineer;\n  }\n  ")
        snapshot = self._snapshot_mutation(
            (INCREMENT_DEFINITION, "connect incAEBS010 to visualizationProblemStatement.systemsEngineer;"),
            (owner + INCREMENT_DEFINITION, "connect incAEBS010 to asmStakeholderHost.systemsEngineer;"))
        self._assert_unavailable(snapshot, ("stakeholders",))

    def test_nested_or_quoted_homonym_is_not_a_direct_duplicate(self):
        for extra in ("package Foreign { " + SCOPE_HEADER + "; }",
                      "attribute '" + SCOPE_HEADER + "' : String;"):
            with self.subTest(extra=extra):
                snapshot = self._snapshot_mutation(INCREMENT_DEFINITION, INCREMENT_DEFINITION + "\n  " + extra)
                row = self._row(snapshot, "declaredScope")
                self.assertEqual(row.verdict, "PASS")
                self.assertEqual(len(row.witnesses), 1)

    # ── Snapshot algebra (public snapshot inputs) ───────────────────────────
    def test_wrong_artifact_kind_cannot_witness_problem_statement(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, AEBS)
        target = next(w.target for w in snapshot.witnesses if w.relation == "problemStatement")
        altered = replace(snapshot, artifacts=tuple(replace(a, kind="part") if a.identity == target else a
                                                   for a in snapshot.artifacts))
        self.assertIn("problemStatement", evaluate_snapshot(altered).failed_ids)

    def test_snapshot_identity_conflict_is_unassessed_in_both_orders(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, AEBS)
        target_id = next(w.target for w in snapshot.witnesses if w.relation == "problemStatement")
        target = next(a for a in snapshot.artifacts if a.identity == target_id)
        conflict = replace(target, kind="part")
        reports = []
        for artifacts in ((conflict,) + snapshot.artifacts, snapshot.artifacts + (conflict,)):
            with self.subTest(conflict_first=artifacts[0] == conflict):
                result = evaluate_snapshot(replace(snapshot, artifacts=artifacts))
                reports.append(result.increment_status())
                row = next(r for r in result.results if r.unit_id == "problemStatement")
                row.validate()
                self.assertEqual(row.coverage, "UNASSESSED")
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)
                unaffected = next(r for r in result.results if r.unit_id == "increment")
                self.assertEqual(unaffected.verdict, "PASS")
                self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertEqual(reports[0], reports[1])

    def test_agreeing_snapshot_projections_are_coalesced(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, AEBS)
        expected = evaluate_snapshot(snapshot).increment_status()
        for artifacts in (snapshot.artifacts * 2, tuple(reversed(snapshot.artifacts * 2))):
            with self.subTest(reversed=artifacts[0] != snapshot.artifacts[0]):
                result = evaluate_snapshot(replace(snapshot, artifacts=artifacts))
                self.assertEqual(result.increment_status(), expected)

    def test_missing_witness_blocks_corresponding_completion(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        for increment in ("INC-AEBS-010", "INC-MW-002"):
            snapshot = repository_snapshot(ROOT, increment)
            missing = replace(snapshot, witnesses=tuple(w for w in snapshot.witnesses
                                                        if w.relation != "problemStatement"))
            result = evaluate_snapshot(missing)
            self.assertIn("problemStatement", result.failed_ids)
            self.assertEqual(result.readiness[0].readiness, "BLOCKED")
            self.assertIsNone(result.conformance_verdict)

    def test_unsupported_predicates_remain_required_without_pass(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_repository_framing
        expected = {"operational-context", "capability-classification", "need-origin",
                    "requirement-derivation", "native-validation"}
        result = evaluate_repository_framing(ROOT, AEBS)
        self.assertLessEqual(expected, set(result.required_units))
        self.assertLessEqual(expected, set(result.unassessed_ids))
        for row in result.results:
            row.validate()
            if row.unit_id in expected:
                self.assertEqual(row.coverage, "UNASSESSED")
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)

    # ── Governed scope, method and enum grammar ─────────────────────────────
    def test_logical_scope_does_not_require_new_requirements_or_physical_artifacts(self):
        from de4sdv.semantic.method_trace_adapter import TraceDeclaration, selected_contract, METHOD_ID
        contract = selected_contract(TraceDeclaration(METHOD_ID, "logicalArchitecture", (7,), "architectureReady"))
        ids = {s.obligation_id for s in contract.obligations}
        self.assertIn("function-to-logical", ids)
        self.assertNotIn("logical-to-physical", ids)
        self.assertNotIn("requirement-derivation", ids)

    def test_candidate_cannot_reduce_existing_increment_to_easier_scope(self):
        with self.assertRaisesRegex(ValueError, "governed increment scope"):
            self._snapshot_mutation(
                ('scopeKind = "requirements"', "TraceCompletionClaim::requirementsReady"),
                ('scopeKind = "framing"', "TraceCompletionClaim::framingReady"))

    def test_snapshot_cannot_bypass_governed_increment_scope(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, AEBS)
        narrowed = replace(snapshot, declaration=replace(snapshot.declaration,
                           scope_kind="framing", completion_claim="framingReady", phases=(0, 1, 2)))
        with self.assertRaisesRegex(ValueError, "governed increment scope"):
            evaluate_snapshot(narrowed)

    def test_namespace_mismatch_or_duplicate_namespace_refuses(self):
        for old, new in (
            ("package DE4SDV_AEBSVisualizationFraming", "package NotTheDeclaredPackage"),
            ("package DE4SDV_AEBSVisualizationFraming {",
             "package DE4SDV_AEBSVisualizationFraming {}\npackage DE4SDV_AEBSVisualizationFraming {"),
        ):
            with self.subTest(new=new[:50]):
                with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                    self._snapshot_mutation(old, new)

    def test_phase_narrowing_or_wrong_method_is_rejected(self):
        for old, new in (
            (", MethodPhase::phase5_requirements", ""),
            ("DE4SDV_MethodTraces::approvedScopedTraceMethod", "DE4SDV_MethodTraces::unapprovedMethod"),
        ):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    self._snapshot_mutation(old, new)

    def test_foreign_or_undeclared_enum_literals_are_refused(self):
        for old, new in (
            ("applicablePhases = (MethodPhase::phase0_incrementFraming",
             "applicablePhases = (ForeignMethodPhase::phase0_incrementFraming"),
            ("MethodPhase::phase5_requirements", "ForeignNamespace::MethodPhase::phase5_requirements"),
            ("TraceCompletionClaim::requirementsReady",
             "ForeignNamespace::TraceCompletionClaim::requirementsReady"),
            ("MethodPhase::phase5_requirements", "MethodPhase::phase5_notADeclaredPhase"),
            ("MethodPhase::phase5_requirements", "MethodPhase::phase05_requirements"),
        ):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    self._snapshot_mutation(old, new)

    def test_exact_governed_enum_owners_are_accepted(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._snapshot_mutation(
            ("MethodPhase::phase5_requirements", "TraceCompletionClaim::requirementsReady"),
            ("DE4SDV_MethodProcess::MethodPhase::phase5_requirements",
             "DE4SDV_MethodTraces::TraceCompletionClaim::requirementsReady"))
        self.assertEqual(snapshot.declaration.phases, tuple(range(6)))
        result = evaluate_snapshot(snapshot)
        self.assertEqual(len([r for r in result.results if r.verdict == "PASS"]), 7)
        self.assertEqual(len(result.unassessed_ids), 5)
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")

    def test_all_phase_literals_require_the_original_ascii_spelling(self):
        from de4sdv.semantic.method_trace_adapter import parse_applicable_phases, CANONICAL_PHASE_LITERALS
        for number, literal in CANONICAL_PHASE_LITERALS.items():
            for prefix in ("MethodPhase::", "DE4SDV_MethodProcess::MethodPhase::"):
                with self.subTest(number=number, prefix=prefix):
                    self.assertEqual(parse_applicable_phases("(" + prefix + literal + ")"), (number,))
                    for malformed in (literal.replace("phase", "phase0", 1),
                                      literal.replace(str(number), str(number).translate(
                                          str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")), 1)):
                        with self.assertRaises(ValueError):
                            parse_applicable_phases("(" + prefix + malformed + ")")

    # ── Lexical primitives ──────────────────────────────────────────────────
    def test_quote_tokens_are_inert_to_comments_braces_and_declarations(self):
        from de4sdv.semantic.method_trace_adapter import _clean, _structure, _owned_matches, _body
        reference = "ref part :>> increment = Owner::increment;"
        for quote in ("'", '"'):
            for payload in (reference, "} " + reference, "{ " + reference,
                            "/* " + reference, "// " + reference,
                            "escaped\\" + quote + " } /* // " + reference):
                with self.subTest(quote=quote, payload=payload):
                    token = quote + payload + quote
                    source = "attribute " + token + " : String;\n" + reference
                    clean = _clean(source)
                    self.assertIn(token, clean)
                    self.assertEqual(_structure(token), " " * len(token))
                    matches = _owned_matches(clean, r"\bref\s+part\s+:>>\s+increment\s*=")
                    self.assertEqual(len(matches), 1)
                    self.assertEqual(matches[0].start(), clean.rindex(reference))
                    self.assertEqual(_body("part owner : Type { " + clean + " }", "owner"),
                                     " " + clean + " ")

    def test_header_scan_is_linear_and_equivalent(self):
        """QUALITY follow-up: long unterminated input must not backtrack quadratically."""
        import random
        import re
        import time
        from de4sdv.semantic.method_trace_adapter import (
            _HEADER_PATTERN, _NativeFraming, _clean, _direct_matches, _structure)

        def regex_scan(text):
            structure, depth, depths = _structure(text), 0, []
            for char in structure:
                depths.append(depth)
                depth += (char == "{") - (char == "}")
            return [(m.start(), m.end(), m.group(1)) for m in re.finditer(_HEADER_PATTERN, structure)
                    if depths[m.start()] == 0]

        def linear_scan(text):
            return [(m.start(), m.end(), m.group(1)) for m in _direct_matches(text, _HEADER_PATTERN)]
        for path in sorted((ROOT / "textual-notation-of-model").rglob("*.sysml")):
            text = _clean(path.read_text())
            self.assertEqual(linear_scan(text), regex_scan(text), path.name)
        generator = random.Random(7)
        for _ in range(2000):
            text = "".join(generator.choice("ab {};\n:") for _ in range(generator.randint(0, 50)))
            self.assertEqual(linear_scan(text), regex_scan(text), text)
        namespace = AEBS_NS[:-2]
        started = time.perf_counter()
        _NativeFraming("a" * 20000, namespace,
                       "ref part :>> increment = " + AEBS_NS + "inc;").evaluate()
        self.assertLess(time.perf_counter() - started, 2.0)

    def test_quoted_escape_newline_does_not_expose_declaration_text(self):
        from de4sdv.semantic.method_trace_adapter import _clean, _structure, _owned_matches
        for quote in ("'", '"'):
            with self.subTest(quote=quote):
                token = quote + "escaped\\\n} /* // ref part :>> increment = Owner::increment;" + quote
                source = _clean("attribute " + token + " : String;")
                self.assertEqual(_structure(token), " " * len(token))
                self.assertFalse(_owned_matches(source, r"\bref\s+part\s+:>>\s+increment"))

    # ── Stakeholder vocabulary (Topic 6) ────────────────────────────────────
    def test_saf_adaptation_notices_and_stakeholder_carrier_are_bounded(self):
        kernel = ROOT / "textual-notation-of-model/packages/methods/de4sdv"
        roles = (kernel / "de4sdv_stakeholders.sysml").read_text()
        self.assertIn("c57bd42db60a00c51168f6aba8e2229ba0165b6c", roles)
        self.assertIn("not forbidden", roles)
        self.assertIn("locally adapted", roles)
        context = (kernel / "de4sdv_method_context.sysml").read_text()
        self.assertIn("connection def HasStakeholder", context)
        self.assertIn("end increment : EngineeringIncrement;", context)
        self.assertIn("end stakeholderRole : Stakeholder;", context)

    def test_eight_adapted_and_seven_local_roles_remain_reusable(self):
        import re
        from de4sdv.semantic.method_trace_adapter import _clean
        text = (ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml").read_text()
        local, adapted = text.split("// ─── Eight locally adapted GfSE SAF roles", 1)
        self.assertEqual(set(re.findall(r"part def (\w+) :> Stakeholder", local)),
                         {"RoadUser", "VehicleOccupant", "SystemsEngineer", "ProductLineEngineer",
                          "ComplianceEngineer", "VerificationEngineer", "OpenSourceReviewer"})
        self.assertEqual(set(re.findall(r"part def (\w+) :> Stakeholder", adapted)),
                         {"SafetyExpert", "SecurityExpert", "SystemArchitect", "SoftwareDeveloper",
                          "HardwareDeveloper", "Maintainer", "Supplier", "ProjectManager"})
        self.assertNotRegex(_clean(text), r"\bindividual\s+(?:part|item)\s+def")

    # ── CLI ─────────────────────────────────────────────────────────────────
    def test_cli_consumes_real_sources_and_preserves_blockers(self):
        import json
        from de4sdv.semantic.method_trace_adapter import evaluate_repository_framing
        for increment in ("INC-AEBS-010", "INC-MW-002"):
            run = self._cli(ROOT, increment)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads(run.stdout)
            self.assertEqual(report["inspection_kind"], "opt-in-source-reference")
            self.assertFalse(report["production_runtime"])
            self.assertEqual(report["evaluation"], evaluate_repository_framing(ROOT, increment).increment_status())
            self.assertIn("native-validation", report["evaluation"]["unassessed_ids"])
            self.assertEqual(report["evaluation"]["readiness"][0]["readiness"], "BLOCKED")

    def test_cli_native_relationships_drive_the_verdict(self):
        import json
        complete = json.loads(self._synthetic_cli_mutation("", "").stdout)["evaluation"]
        verdicts = {r["unit_id"]: r.get("conformance_verdict") for r in complete["results"]}
        self.assertEqual({k: verdicts[k] for k in ("increment", "problemStatement", "stakeholders")},
                         {"increment": "PASS", "problemStatement": "PASS", "stakeholders": "PASS"})
        run = self._synthetic_cli_mutation("  connection participation : HasStakeholder\n"
                                           "    connect syntheticIncrement to syntheticProblem.engineer;\n", "")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)["evaluation"]
        stakeholders = next(r for r in report["results"] if r["unit_id"] == "stakeholders")
        self.assertEqual(stakeholders["conformance_verdict"], "FAIL")
        self.assertEqual(report["readiness"][0]["readiness"], "BLOCKED")

    def test_cli_refuses_easier_scope_and_foreign_namespace(self):
        import json
        for old, new in (
            (('scopeKind = "requirements"', "TraceCompletionClaim::requirementsReady"),
             ('scopeKind = "framing"', "TraceCompletionClaim::framingReady")),
            ("package DE4SDV_AEBSVisualizationFraming", "package ForeignNamespace"),
        ):
            run = self._synthetic_cli_mutation(old, new)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn("error", json.loads(run.stdout))

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _overlay_text(self, old, new):
        from de4sdv.semantic.method_trace_adapter import FRAMINGS
        content = (ROOT / FRAMINGS[AEBS][0]).read_text()
        pairs = zip(old, new) if isinstance(old, tuple) else [(old, new)]
        for before, after in pairs:
            self.assertIn(before, content)
            content = content.replace(before, after, 1)
        return content

    def _snapshot_mutation(self, old, new):
        from unittest.mock import patch
        from de4sdv.semantic.method_trace_adapter import FRAMINGS, repository_snapshot
        source = ROOT / FRAMINGS[AEBS][0]
        content = self._overlay_text(old, new)
        read_text = Path.read_text

        def overlay(path, *args, **kwargs):
            return content if path == source else read_text(path, *args, **kwargs)
        with patch.object(Path, "read_text", overlay):
            return repository_snapshot(ROOT, AEBS)

    def _evaluate_mutation(self, old, new):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        return evaluate_snapshot(self._snapshot_mutation(old, new))

    @staticmethod
    def _row(snapshot, relation):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        return next(r for r in evaluate_snapshot(snapshot).results if r.unit_id == relation)

    def _assert_unavailable(self, snapshot, relations):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        result = evaluate_snapshot(snapshot)
        for relation in relations:
            with self.subTest(relation=relation):
                self.assertIn(relation, snapshot.unavailable)
                self.assertIn(relation, result.unassessed_ids)
                self.assertNotIn(relation, result.failed_ids)
                row = next(r for r in result.results if r.unit_id == relation)
                row.validate()
                self.assertEqual(row.coverage, "UNASSESSED")
                self.assertIsNone(row.state)
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)
                self.assertFalse([w for w in snapshot.witnesses if w.relation == relation])
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def _synthetic_cli_mutation(self, old, new):
        """Small authored fixture, never a duplicate/mirror of a real model."""
        import subprocess
        import tempfile
        from de4sdv.semantic.method_trace_adapter import FRAMINGS
        content = '''package DE4SDV_AEBSVisualizationFraming {
  part def SyntheticIncrement :> EngineeringIncrement;
  part syntheticIncrement : SyntheticIncrement;
  requirement syntheticProblem : ProblemStatement {
    subject increment : SyntheticIncrement;
    stakeholder engineer : SystemsEngineer;
  }
  connection participation : HasStakeholder
    connect syntheticIncrement to syntheticProblem.engineer;
  part visualizationTraceObligations : SyntheticTrace {
    attribute :>> scopeKind = "requirements";
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming,
      MethodPhase::phase1_concernFraming, MethodPhase::phase2_operationalContext,
      MethodPhase::phase3_capabilityClassification, MethodPhase::phase4_needs,
      MethodPhase::phase5_requirements);
    attribute :>> completionClaim = TraceCompletionClaim::requirementsReady;
    ref part :>> selectedMethod = DE4SDV_MethodTraces::approvedScopedTraceMethod;
    ref part :>> increment = DE4SDV_AEBSVisualizationFraming::syntheticIncrement;
  }
}
'''
        pairs = zip(old, new) if isinstance(old, tuple) else [(old, new)]
        for before, after in pairs:
            self.assertIn(before, content)
            content = content.replace(before, after, 1)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            # The fixture brings its own repository: ROOT/.git is a directory in a
            # clone and a file in a linked worktree, so it must never be copied.
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.email=synthetic@example.invalid",
                            "-c", "user.name=Synthetic Fixture", "commit", "-q",
                            "--allow-empty", "-m", "synthetic fixture"],
                           cwd=repo, check=True, capture_output=True)
            target = repo / FRAMINGS[AEBS][0]
            target.parent.mkdir(parents=True)
            target.write_text(content)
            return self._cli(repo, AEBS)

    @staticmethod
    def _cli(repo, increment):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, "-m", "de4sdv.semantic.method_trace_adapter",
             "--repo", str(repo), "--increment", increment], cwd=ROOT,
            text=True, capture_output=True, timeout=30,
        )


if __name__ == "__main__":
    unittest.main()
