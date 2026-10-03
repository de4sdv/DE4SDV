"""Actual framing migration and evaluator-facing missing-link regression."""
from pathlib import Path
import importlib.util
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ScopedTraceTests(unittest.TestCase):
    def test_real_framing_is_evaluated_not_a_populated_shell(self):
        self.assertIsNotNone(importlib.util.find_spec("de4sdv.semantic.method_trace_adapter"),
                             "phase/scope trace adapter is missing")
        from de4sdv.semantic.method_trace_adapter import evaluate_repository_framing
        for increment in ("INC-AEBS-010", "INC-MW-002"):
            result = evaluate_repository_framing(ROOT, increment)
            self.assertEqual(result.assessment_coverage, "UNASSESSED")
            self.assertIsNone(result.conformance_verdict)
            self.assertEqual(result.readiness[0].readiness, "BLOCKED")
            known = [r for r in result.results if r.verdict == "PASS"]
            self.assertTrue(known)
            self.assertTrue(all(r.witnesses for r in known))
            self.assertNotIn("physical-realization", result.required_units)

    def test_wrong_artifact_kind_cannot_witness_problem_statement(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, "INC-AEBS-010")
        target = next(w.target for w in snapshot.witnesses if w.relation == "problemStatement")
        altered = replace(snapshot, artifacts=tuple(replace(a, kind="part") if a.identity == target else a
                                                   for a in snapshot.artifacts))
        result = evaluate_snapshot(altered)
        self.assertIn("problemStatement", result.failed_ids)

    def test_snapshot_identity_conflict_is_unassessed_in_both_orders(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, "INC-AEBS-010")
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
                self.assertIsNone(row.state)
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)
                self.assertNotIn("problemStatement", result.failed_ids)
                unaffected = next(r for r in result.results if r.unit_id == "increment")
                self.assertEqual(unaffected.verdict, "PASS")
                self.assertEqual(result.readiness[0].readiness, "BLOCKED")
                self.assertIsNone(result.conformance_verdict)
        self.assertEqual(reports[0], reports[1])

    def test_agreeing_snapshot_projections_are_coalesced(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, "INC-AEBS-010")
        expected = evaluate_snapshot(snapshot).increment_status()
        for artifacts in (snapshot.artifacts * 2, tuple(reversed(snapshot.artifacts * 2))):
            with self.subTest(artifacts=artifacts):
                result = evaluate_snapshot(replace(snapshot, artifacts=artifacts))
                self.assertEqual(result.increment_status(), expected)
                row = next(r for r in result.results if r.unit_id == "problemStatement")
                self.assertEqual(row.verdict, "PASS")
                self.assertEqual(len(row.witnesses), 1)

    def test_logical_scope_does_not_require_new_requirements_or_physical_artifacts(self):
        from de4sdv.semantic.method_trace_adapter import TraceDeclaration, selected_contract, METHOD_ID
        contract = selected_contract(TraceDeclaration(METHOD_ID, "logicalArchitecture", (7,), "architectureReady"))
        ids = {s.obligation_id for s in contract.obligations}
        self.assertIn("function-to-logical", ids)
        self.assertNotIn("logical-to-physical", ids)
        self.assertNotIn("requirement-derivation", ids)

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

    def test_missing_real_reference_blocks_corresponding_completion(self):
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

    def _source_mutation(self, increment, old, new, consumer=None):
        from unittest.mock import patch
        from de4sdv.semantic.method_trace_adapter import FRAMINGS, repository_snapshot
        source = ROOT / FRAMINGS[increment][0]
        content = source.read_text()
        pairs = zip(old, new) if isinstance(old, tuple) else [(old, new)]
        for before, after in pairs:
            self.assertIn(before, content)
            content = content.replace(before, after)
        read_text = Path.read_text
        def overlay(path, *args, **kwargs):
            return content if path == source else read_text(path, *args, **kwargs)
        self.assertIsNone(consumer, "subprocess mutations require the synthetic CLI fixture")
        with patch.object(Path, "read_text", overlay):
            return repository_snapshot(ROOT, increment)

    def _synthetic_cli_mutation(self, old, new):
        """Small authored fixture, never a duplicate/mirror of a real model."""
        import subprocess
        import tempfile
        from de4sdv.semantic.method_trace_adapter import FRAMINGS
        content = '''package DE4SDV_AEBSVisualizationFraming {
  requirement syntheticProblem : SyntheticProblem;
  part visualizationTraceObligations : SyntheticTrace {
    attribute :>> scopeKind = "requirements";
    attribute :>> applicablePhases = (MethodPhase::phase0_incrementFraming,
      MethodPhase::phase1_concernFraming, MethodPhase::phase2_operationalContext,
      MethodPhase::phase3_capabilityClassification, MethodPhase::phase4_needs,
      MethodPhase::phase5_requirements);
    attribute :>> completionClaim = TraceCompletionClaim::requirementsReady;
    ref part :>> selectedMethod = DE4SDV_MethodTraces::approvedScopedTraceMethod;
    ref requirement :>> problemStatement = DE4SDV_AEBSVisualizationFraming::syntheticProblem;
  }
}
'''
        pairs = zip(old, new) if isinstance(old, tuple) else [(old, new)]
        for before, after in pairs:
            self.assertIn(before, content)
            content = content.replace(before, after)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            # The fixture brings its own repository: ROOT/.git is a directory in a
            # clone and a file in a linked worktree, so it must never be copied.
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.email=synthetic@example.invalid",
                            "-c", "user.name=Synthetic Fixture", "commit", "-q",
                            "--allow-empty", "-m", "synthetic fixture"],
                           cwd=repo, check=True, capture_output=True)
            target = repo / FRAMINGS["INC-AEBS-010"][0]
            target.parent.mkdir(parents=True)
            target.write_text(content)
            return self._cli(repo, "INC-AEBS-010")

    def test_candidate_cannot_reduce_existing_increment_to_easier_scope(self):
        with self.assertRaisesRegex(ValueError, "governed increment scope"):
            self._source_mutation("INC-AEBS-010",
                 ('scopeKind = "requirements"', 'TraceCompletionClaim::requirementsReady'),
                 ('scopeKind = "framing"', 'TraceCompletionClaim::framingReady'))

    def test_namespace_mismatch_cannot_supply_identified_targets(self):
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            self._source_mutation("INC-AEBS-010",
                    "package DE4SDV_AEBSVisualizationFraming", "package NotTheDeclaredPackage")

    def test_snapshot_cannot_bypass_governed_increment_scope(self):
        from dataclasses import replace
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, evaluate_snapshot
        snapshot = repository_snapshot(ROOT, "INC-AEBS-010")
        narrowed = replace(snapshot, declaration=replace(snapshot.declaration,
                           scope_kind="framing", completion_claim="framingReady", phases=(0, 1, 2)))
        with self.assertRaisesRegex(ValueError, "governed increment scope"):
            evaluate_snapshot(narrowed)

    def test_duplicate_owning_namespace_is_not_identity(self):
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            self._source_mutation("INC-AEBS-010", "package DE4SDV_AEBSVisualizationFraming {",
                "package DE4SDV_AEBSVisualizationFraming {}\npackage DE4SDV_AEBSVisualizationFraming {")

    def test_nested_namespace_target_is_not_owner_namespace_target(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._source_mutation("INC-AEBS-010",
            "part visualizationScope : IncrementScope {",
            "package Foreign { part visualizationScope : IncrementScope; }\npart otherScope : IncrementScope {")
        result = evaluate_snapshot(snapshot)
        self.assertIn("declaredScope", result.failed_ids)

    def test_phase_narrowing_or_wrong_method_is_rejected(self):
        for old, new in (
            (", MethodPhase::phase5_requirements", ""),
            ("DE4SDV_MethodTraces::approvedScopedTraceMethod", "DE4SDV_MethodTraces::unapprovedMethod"),
        ):
            with self.assertRaises(ValueError):
                self._source_mutation("INC-AEBS-010", old, new)

    # Reviewed source-adapter findings: non-code text and foreign ownership must
    # not fabricate an identified source reference. Every case keeps the source
    # syntactically plausible and asserts the fabricated PASS disappears.
    def test_reference_text_inside_string_cannot_witness_problem_statement(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._source_mutation("INC-AEBS-010",
            "ref requirement :>> problemStatement = DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;",
            "attribute fabricatedNote : ScalarValues::String = \"ref requirement :>> problemStatement ="
            " DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;\";")
        result = evaluate_snapshot(snapshot)
        self.assertIn("problemStatement", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "problemStatement"])

    def test_nested_reference_cannot_witness_the_original_trace_usage(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._source_mutation("INC-AEBS-010",
            "ref requirement :>> problemStatement = DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;",
            "part nestedHost { ref requirement :>> problemStatement ="
            " DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement; }")
        result = evaluate_snapshot(snapshot)
        self.assertIn("problemStatement", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "problemStatement"])

    _PROBLEM_STAKEHOLDERS = ("    stakeholder systemsEngineer : SystemsEngineer;\n"
                             "    stakeholder productLineEngineer : ProductLineEngineer;\n"
                             "    stakeholder verificationEngineer : VerificationEngineer;\n"
                             "    stakeholder maintainer : Maintainer;\n"
                             "    stakeholder reviewer : OpenSourceReviewer;\n")

    def test_stakeholder_text_inside_string_cannot_witness_participation(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        replacement = self._PROBLEM_STAKEHOLDERS.replace(
            "    stakeholder systemsEngineer : SystemsEngineer;\n",
            "    attribute fabricatedStakeholderNote : ScalarValues::String ="
            " \"stakeholder systemsEngineer : SystemsEngineer;\";\n", 1)
        snapshot = self._source_mutation("INC-AEBS-010", self._PROBLEM_STAKEHOLDERS, replacement)
        result = evaluate_snapshot(snapshot)
        self.assertIn("stakeholders", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "stakeholders"])

    def test_stakeholder_in_nested_foreign_package_is_not_the_referenced_member(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        replacement = self._PROBLEM_STAKEHOLDERS.replace(
            "    stakeholder systemsEngineer : SystemsEngineer;\n",
            "    package Foreign { stakeholder systemsEngineer : SystemsEngineer; }\n", 1)
        snapshot = self._source_mutation("INC-AEBS-010", self._PROBLEM_STAKEHOLDERS, replacement)
        result = evaluate_snapshot(snapshot)
        self.assertIn("stakeholders", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "stakeholders"])

    def test_reference_in_unrestricted_name_is_not_a_source_witness(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        reference = ("ref requirement :>> problemStatement = "
                     "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;")
        snapshot = self._source_mutation("INC-AEBS-010", reference,
            "attribute '" + reference + "' : ScalarValues::String = \"not a reference\";")
        result = evaluate_snapshot(snapshot)
        self.assertIn("problemStatement", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "problemStatement"])
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def test_stakeholder_in_unrestricted_name_is_not_a_source_witness(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        role = "stakeholder systemsEngineer : SystemsEngineer;"
        snapshot = self._source_mutation("INC-AEBS-010", role,
            "attribute '" + role + "' : ScalarValues::String = \"not a stakeholder\";")
        result = evaluate_snapshot(snapshot)
        self.assertIn("stakeholders", result.failed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "stakeholders"])
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def test_quote_tokens_are_inert_to_comments_braces_and_declarations(self):
        from de4sdv.semantic.method_trace_adapter import _clean, _structure, _owned_matches, _body
        reference = "ref part :>> increment = Owner::increment;"
        # Both quote forms, escaped delimiters, comment markers and unbalanced
        # brace text must remain one inert token; active code after it survives.
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

    def test_quoted_escape_newline_does_not_expose_declaration_text(self):
        from de4sdv.semantic.method_trace_adapter import _clean, _structure, _owned_matches
        for quote in ("'", '"'):
            with self.subTest(quote=quote):
                token = quote + "escaped\\\n} /* // ref part :>> increment = Owner::increment;" + quote
                source = _clean("attribute " + token + " : String;")
                self.assertEqual(_structure(token), " " * len(token))
                self.assertFalse(_owned_matches(source, r"\bref\s+part\s+:>>\s+increment"))

    def test_non_ascii_target_name_is_outside_the_bounded_identity_grammar(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._source_mutation("INC-AEBS-010", "visualizationProblemStatement",
                                        "visualizationPröblemStatement")
        result = evaluate_snapshot(snapshot)
        self.assertIn("problemStatement", result.unassessed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "problemStatement"])

    def test_foreign_phase_namespace_is_not_the_governed_phase_declaration(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010",
                "applicablePhases = (MethodPhase::phase0_incrementFraming",
                "applicablePhases = (ForeignMethodPhase::phase0_incrementFraming")

    def test_foreign_qualified_phase_owner_is_refused(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010", "MethodPhase::phase5_requirements",
                "ForeignNamespace::MethodPhase::phase5_requirements")

    def test_foreign_qualified_completion_owner_is_refused(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010", "TraceCompletionClaim::requirementsReady",
                "ForeignNamespace::TraceCompletionClaim::requirementsReady")

    def test_exact_governed_enum_owners_are_accepted(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        snapshot = self._source_mutation("INC-AEBS-010",
            ("MethodPhase::phase5_requirements", "TraceCompletionClaim::requirementsReady"),
            ("DE4SDV_MethodProcess::MethodPhase::phase5_requirements",
             "DE4SDV_MethodTraces::TraceCompletionClaim::requirementsReady"))
        self.assertEqual(snapshot.declaration.phases, tuple(range(6)))
        self.assertEqual(snapshot.declaration.completion_claim, "requirementsReady")
        result = evaluate_snapshot(snapshot)
        self.assertEqual(len([r for r in result.results if r.verdict == "PASS"]), 7)
        self.assertEqual(len(result.unassessed_ids), 5)
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def test_undeclared_phase_literal_is_refused_not_salvaged(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010",
                "MethodPhase::phase5_requirements", "MethodPhase::phase5_notADeclaredPhase")

    def test_leading_zero_phase_literal_is_refused_without_normalization(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010",
                "MethodPhase::phase5_requirements", "MethodPhase::phase05_requirements")

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

    def test_duplicate_direct_stakeholder_identity_is_unassessed(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        role = "stakeholder systemsEngineer : SystemsEngineer;"
        snapshot = self._source_mutation("INC-AEBS-010", role, role + "\n" + role)
        result = evaluate_snapshot(snapshot)
        self.assertIn("stakeholders", snapshot.unavailable)
        self.assertIn("stakeholders", result.unassessed_ids)
        self.assertNotIn("stakeholders", result.failed_ids)
        row = next(r for r in result.results if r.unit_id == "stakeholders")
        self.assertIsNone(row.state)
        self.assertIsNone(row.verdict)
        self.assertFalse(row.witnesses)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "stakeholders"])
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def test_nested_or_quoted_stakeholder_homonym_is_not_a_direct_duplicate(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        role = "stakeholder systemsEngineer : SystemsEngineer;"
        for extra in ("package Foreign { " + role + " }",
                      "attribute '" + role + "' : String;"):
            with self.subTest(extra=extra):
                snapshot = self._source_mutation("INC-AEBS-010", role, role + "\n" + extra)
                result = evaluate_snapshot(snapshot)
                row = next(r for r in result.results if r.unit_id == "stakeholders")
                self.assertEqual(row.verdict, "PASS")
                self.assertEqual(len(row.witnesses), 1)
                self.assertNotIn("stakeholders", snapshot.unavailable)

    def test_duplicate_direct_target_identity_is_unassessed_not_failed(self):
        """Reviewed finding: target ambiguity is unavailable, never absence."""
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        declaration = "requirement visualizationProblemStatement : ProblemStatement"
        snapshot = self._source_mutation("INC-AEBS-010", declaration,
                                         declaration + ";\n" + declaration)
        result = evaluate_snapshot(snapshot)
        for relation in ("problemStatement", "stakeholders"):
            with self.subTest(relation=relation):
                self.assertIn(relation, snapshot.unavailable)
                self.assertIn(relation, result.unassessed_ids)
                self.assertNotIn(relation, result.failed_ids)
                row = next(r for r in result.results if r.unit_id == relation)
                self.assertIsNone(row.state)
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)
        self.assertFalse([w for w in snapshot.witnesses
                          if w.relation in {"problemStatement", "stakeholders"}])
        self.assertEqual(result.readiness[0].readiness, "BLOCKED")
        self.assertIsNone(result.conformance_verdict)

    def _assert_unavailable_relations(self, snapshot, relations):
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

    def test_duplicate_untyped_target_identity_is_unassessed(self):
        declaration = "requirement visualizationProblemStatement : ProblemStatement"
        for duplicate in ("requirement visualizationProblemStatement;",
                          "item visualizationProblemStatement;",
                          "requirement <probe> visualizationProblemStatement;",
                          "requirement < probe > visualizationProblemStatement;",
                          "requirement <'probe'> visualizationProblemStatement;"):
            for first in (True, False):
                with self.subTest(duplicate=duplicate, first=first):
                    if first:
                        snapshot = self._source_mutation(
                            "INC-AEBS-010", declaration, duplicate + "\n" + declaration)
                    else:
                        ending = self._PROBLEM_STAKEHOLDERS + "  }"
                        snapshot = self._source_mutation(
                            "INC-AEBS-010", ending, ending + "\n" + duplicate)
                    self._assert_unavailable_relations(snapshot, ("problemStatement", "stakeholders"))

    def test_duplicate_untyped_stakeholder_identity_is_unassessed(self):
        role = "stakeholder systemsEngineer : SystemsEngineer;"
        for duplicate in ("stakeholder systemsEngineer;", "part systemsEngineer;",
                          "stakeholder <probe> systemsEngineer;",
                          "stakeholder < probe > systemsEngineer;",
                          "stakeholder <'probe'> systemsEngineer;"):
            for first in (True, False):
                with self.subTest(duplicate=duplicate, first=first):
                    replacement = duplicate + "\n" + role if first else role + "\n" + duplicate
                    snapshot = self._source_mutation("INC-AEBS-010", role, replacement)
                    self._assert_unavailable_relations(snapshot, ("stakeholders",))

    def test_present_unsupported_reference_is_unassessed_for_each_sibling(self):
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, SUPPORTED
        original = repository_snapshot(ROOT, "INC-AEBS-010")
        self.assertEqual({w.relation for w in original.witnesses}, set(SUPPORTED))
        for witness in original.witnesses:
            with self.subTest(relation=witness.relation):
                kind = "requirement" if witness.relation in {"problemStatement", "concerns"} else "part"
                reference = f"ref {kind} :>> {witness.relation} = {witness.target};"
                snapshot = self._source_mutation("INC-AEBS-010", reference,
                    f"ref {kind} :>> {witness.relation} = ({witness.target});")
                self._assert_unavailable_relations(snapshot, (witness.relation,))

    def test_short_name_reference_header_is_present_but_unavailable_for_each_sibling(self):
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, SUPPORTED
        original = repository_snapshot(ROOT, "INC-AEBS-010")
        self.assertEqual({w.relation for w in original.witnesses}, set(SUPPORTED))
        for witness in original.witnesses:
            for short_name in ("<probe>", "< probe >", "<'probe'>"):
                with self.subTest(relation=witness.relation, short_name=short_name):
                    kind = "requirement" if witness.relation in {"problemStatement", "concerns"} else "part"
                    reference = f"ref {kind} :>> {witness.relation} = {witness.target};"
                    replacement = f"ref {kind} {short_name} {witness.relation} = {witness.target};"
                    snapshot = self._source_mutation("INC-AEBS-010", reference, replacement)
                    self._assert_unavailable_relations(snapshot, (witness.relation,))

    def test_present_unsupported_reference_shapes_are_not_absence(self):
        target = "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement"
        reference = "ref requirement :>> problemStatement = " + target + ";"
        for replacement in (
            "ref requirement :>> problemStatement;",
            "ref requirement :>> problemStatement = ;",
            'ref requirement :>> problemStatement = "' + target + '";',
            "ref requirement :>> problemStatement = " + target + ' "inert payload";',
            "ref requirement :>> problemStatement = " + target + " + " + target + ";",
            "ref requirement :>> problemStatement = " + target + "::systemsEngineer::extra;",
            "ref requirement problemStatement : ProblemStatement;",
        ):
            with self.subTest(replacement=replacement):
                snapshot = self._source_mutation("INC-AEBS-010", reference, replacement)
                self._assert_unavailable_relations(snapshot, ("problemStatement",))

    def test_supported_reference_with_unsupported_duplicate_is_unassessed(self):
        reference = ("ref requirement :>> problemStatement = "
                     "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;")
        for duplicate in ("ref requirement :>> problemStatement;",
                          "ref requirement :>> problemStatement = ("
                          "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement);"):
            for first in (True, False):
                with self.subTest(duplicate=duplicate, first=first):
                    replacement = duplicate + "\n" + reference if first else reference + "\n" + duplicate
                    snapshot = self._source_mutation("INC-AEBS-010", reference, replacement)
                    self._assert_unavailable_relations(snapshot, ("problemStatement",))

    def test_present_unsupported_target_shape_is_unassessed(self):
        declaration = "requirement visualizationProblemStatement : ProblemStatement"
        for replacement in (
            "requirement visualizationProblemStatement",
            "item visualizationProblemStatement : ProblemStatement",
            "requirement visualizationProblemStatement : (ProblemStatement)",
            "requirement visualizationProblemStatement : ProblemStatement[1]",
            'requirement visualizationProblemStatement : ProblemStatement "inert payload"',
            "requirement def visualizationProblemStatement : ProblemStatement",
        ):
            with self.subTest(replacement=replacement):
                snapshot = self._source_mutation("INC-AEBS-010", declaration, replacement)
                self._assert_unavailable_relations(snapshot, ("problemStatement", "stakeholders"))

    def test_present_unsupported_stakeholder_shape_is_unassessed(self):
        role = "stakeholder systemsEngineer : SystemsEngineer;"
        for replacement in ("stakeholder systemsEngineer;", "part systemsEngineer : SystemsEngineer;",
                            "stakeholder systemsEngineer : (SystemsEngineer);",
                            "stakeholder systemsEngineer : SystemsEngineer[1];",
                            "stakeholder systemsEngineer : SystemsEngineer 'inert payload';"):
            with self.subTest(replacement=replacement):
                snapshot = self._source_mutation("INC-AEBS-010", role, replacement)
                self._assert_unavailable_relations(snapshot, ("stakeholders",))

    def test_untyped_target_is_unassessed_for_each_direct_sibling(self):
        import re
        from de4sdv.semantic.method_trace_adapter import repository_snapshot, FRAMINGS
        original = repository_snapshot(ROOT, "INC-AEBS-010")
        source = (ROOT / FRAMINGS["INC-AEBS-010"][0]).read_text()
        artifacts = {a.identity: a for a in original.artifacts}
        relations = {w.relation for w in original.witnesses if w.relation != "stakeholders"}
        self.assertEqual(len(relations), 6)
        for witness in original.witnesses:
            if witness.relation == "stakeholders":
                continue
            with self.subTest(relation=witness.relation):
                artifact = artifacts[witness.target]
                name = witness.target.rsplit("::", 1)[1]
                prefix = artifact.kind + " " + name
                headers = re.findall(r"\b" + re.escape(prefix)
                                     + r"\s*:\s*[A-Za-z_][A-Za-z0-9_:]*", source)
                self.assertEqual(len(headers), 1)
                snapshot = self._source_mutation("INC-AEBS-010", headers[0], prefix)
                affected = (("problemStatement", "stakeholders")
                            if witness.relation == "problemStatement" else (witness.relation,))
                self._assert_unavailable_relations(snapshot, affected)

    def test_proven_reference_or_target_absence_is_assessed_fail(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        reference = ("ref requirement :>> problemStatement = "
                     "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;")
        for old, new, relations in (
            (reference, "", ("problemStatement",)),
            ("requirement visualizationProblemStatement : ProblemStatement",
             "requirement differentProblemStatement : ProblemStatement", ("problemStatement", "stakeholders")),
            ("stakeholder systemsEngineer : SystemsEngineer;",
             "stakeholder differentEngineer : SystemsEngineer;", ("stakeholders",)),
        ):
            with self.subTest(old=old):
                snapshot = self._source_mutation("INC-AEBS-010", old, new)
                result = evaluate_snapshot(snapshot)
                for relation in relations:
                    row = next(r for r in result.results if r.unit_id == relation)
                    row.validate()
                    self.assertNotIn(relation, snapshot.unavailable)
                    self.assertEqual(row.coverage, "ASSESSED")
                    self.assertEqual(row.verdict, "FAIL")
                    self.assertIn("REQUIRED_RELATION_MISSING", row.reason_codes)
                    self.assertFalse(row.witnesses)
                self.assertEqual(result.readiness[0].readiness, "BLOCKED")
                self.assertIsNone(result.conformance_verdict)

    def test_duplicate_direct_reference_identity_is_unassessed(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_snapshot
        reference = ("ref requirement :>> problemStatement = "
                     "DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;")
        snapshot = self._source_mutation("INC-AEBS-010", reference, reference + "\n" + reference)
        result = evaluate_snapshot(snapshot)
        self.assertIn("problemStatement", result.unassessed_ids)
        self.assertFalse([w for w in snapshot.witnesses if w.relation == "problemStatement"])

    def test_unsupported_predicates_remain_required_without_pass(self):
        from de4sdv.semantic.method_trace_adapter import evaluate_repository_framing
        expected = {"operational-context", "capability-classification", "need-origin",
                    "requirement-derivation", "native-validation"}
        result = evaluate_repository_framing(ROOT, "INC-AEBS-010")
        self.assertLessEqual(expected, set(result.required_units))
        self.assertLessEqual(expected, set(result.unassessed_ids))
        for row in result.results:
            row.validate()
            if row.unit_id in expected:
                self.assertEqual(row.coverage, "UNASSESSED")
                self.assertIsNone(row.verdict)
                self.assertFalse(row.witnesses)

    def test_eight_adapted_and_seven_local_roles_remain_reusable(self):
        import re
        text = (ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_stakeholders.sysml").read_text()
        local, adapted = text.split("// ─── Eight locally adapted GfSE SAF roles", 1)
        self.assertEqual(set(re.findall(r"part def (\w+) :> Stakeholder", local)),
                         {"RoadUser", "VehicleOccupant", "SystemsEngineer", "ProductLineEngineer",
                          "ComplianceEngineer", "VerificationEngineer", "OpenSourceReviewer"})
        self.assertEqual(set(re.findall(r"part def (\w+) :> Stakeholder", adapted)),
                         {"SafetyExpert", "SecurityExpert", "SystemArchitect", "SoftwareDeveloper",
                          "HardwareDeveloper", "Maintainer", "Supplier", "ProjectManager"})
        from de4sdv.semantic.method_trace_adapter import _clean
        self.assertNotRegex(_clean(text), r"\bindividual\s+(?:part|item)\s+def")

    @staticmethod
    def _cli(repo, increment):
        import subprocess
        import sys
        return subprocess.run(
            [sys.executable, "-m", "de4sdv.semantic.method_trace_adapter",
             "--repo", str(repo), "--increment", increment], cwd=ROOT,
            text=True, capture_output=True, timeout=30,
        )

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

    def test_cli_missing_reference_is_fail_not_pass(self):
        import json
        run = self._synthetic_cli_mutation(
            "ref requirement :>> problemStatement = DE4SDV_AEBSVisualizationFraming::syntheticProblem;", "")
        self.assertEqual(run.returncode, 0, run.stderr)
        report = json.loads(run.stdout)["evaluation"]
        problem = next(r for r in report["results"] if r["unit_id"] == "problemStatement")
        self.assertEqual(problem["conformance_verdict"], "FAIL")
        self.assertEqual(report["readiness"][0]["readiness"], "BLOCKED")

    def test_cli_refuses_easier_scope_and_foreign_namespace(self):
        import json
        for old, new in (
            (( 'scopeKind = "requirements"', 'TraceCompletionClaim::requirementsReady'),
             ( 'scopeKind = "framing"', 'TraceCompletionClaim::framingReady')),
            ("package DE4SDV_AEBSVisualizationFraming", "package ForeignNamespace"),
        ):
            run = self._synthetic_cli_mutation(old, new)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn("error", json.loads(run.stdout))

if __name__ == "__main__":
    unittest.main()
