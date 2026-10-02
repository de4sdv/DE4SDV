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
        import tempfile
        import shutil
        from de4sdv.semantic.method_trace_adapter import FRAMINGS, repository_snapshot
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            shutil.copyfile(ROOT / ".git", repo / ".git")
            source = FRAMINGS[increment][0]
            target = repo / source
            target.parent.mkdir(parents=True)
            content = (ROOT / source).read_text()
            pairs = zip(old, new) if isinstance(old, tuple) else [(old, new)]
            for before, after in pairs:
                content = content.replace(before, after)
            target.write_text(content)
            return (consumer or repository_snapshot)(repo, increment)

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

    def test_foreign_phase_namespace_is_not_the_governed_phase_declaration(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010",
                "applicablePhases = (MethodPhase::phase0_incrementFraming",
                "applicablePhases = (ForeignMethodPhase::phase0_incrementFraming")

    def test_undeclared_phase_literal_is_refused_not_salvaged(self):
        with self.assertRaises(ValueError):
            self._source_mutation("INC-AEBS-010",
                "MethodPhase::phase5_requirements", "MethodPhase::phase5_notADeclaredPhase")

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
        run = self._source_mutation("INC-AEBS-010",
            "ref requirement :>> problemStatement = DE4SDV_AEBSVisualizationFraming::visualizationProblemStatement;",
            "", self._cli)
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
            run = self._source_mutation("INC-AEBS-010", old, new, self._cli)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn("error", json.loads(run.stdout))

if __name__ == "__main__":
    unittest.main()
