/* Approved Topics 5/6 successor vocabulary. Not production activation. */
package DE4SDV_MethodTraces {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::*;
  private import DE4SDV_Stakeholders::*;

  enum def TraceCompletionClaim {
    framingReady;
    requirementsReady;
    architectureReady;
    evidenceReady;
    baselineReady;
  }

  part def ApprovedTraceMethod {
    doc /* Selected approved method identity. Selecting this reference does not
         * establish conformance, approval of a candidate, or an engineering trace. */
  }

  part approvedScopedTraceMethod : ApprovedTraceMethod {
    doc /* de4sdv.scope-traces.v1: owner-approved Topic 5 semantic direction.
         * Applicability derives from governed scope, phases and completion claim;
         * executable adapter support is bounded and opt-in, not runtime admission.
         * No universal concern-to-baseline chain or implicit transitive claim.
         *
         * Concrete migrated consumers:
         * INC-AEBS-010: requirements scope, phases 0 through 5, requirementsReady.
         * Its visualizationTraceObligations references incAEBS010,
         * visualizationScope, visualizationProblemStatement,
         * visualizationEngineeringQuestion, visualizationLifecycleDecision,
         * visualizationBoundaryConcern and the problem statement's systemsEngineer.
         * INC-MW-002: framing scope, phases 0 through 2, framingReady.
         * Its traceObligationsMW002 references incMW002, scopeMW002,
         * middlewareIntegrationProblemStatement, engineeringQuestionMW002,
         * lifecycleDecisionMW002, middlewareIncrementAssuranceConcern and the
         * problem statement's systemsEngineer. Fully qualified identities live
         * in the owning feature files, not category-name endpoints. Neither
         * existing increment may select a narrower scope to claim completion.
         *
         * Governed phase obligations: phase 0 requires increment, declaredScope,
         * problemStatement, engineeringQuestion and lifecycleDecision; phase 1
         * requires stakeholders and concerns; phase 2 operational-context;
         * phase 3 capability-classification; phase 4 need-origin; phase 5
         * requirement-derivation; phase 6 requirement-to-function; phase 7
         * function-to-logical; phase 8 logical-to-physical and
         * software-boundary-mapping; phase 9 configuration-to-assets; phase 10
         * verification-to-target and criterion-to-evidence; phase 11
         * publication-provenance; phase 12 baseline-disposition.
         * Framing covers phases 0 through 2; requirements covers 0 through 5.
         * Functional, logical and physical scopes cover their respective phase
         * 6, 7 or 8; combined architecture covers 6 through 8; configuration
         * covers 9, evidence 10, baseline 12. Additional declared phases add
         * obligations, never remove the governed minimum. Reuse prior artifacts
         * without requiring every architecture increment to create requirements.
         *
         * The opt-in SOURCE-reference adapter checks only identified phase 0/1
         * references in these two files. Missing supported references yield FAIL;
         * ambiguous/unsupported inputs remain UNASSESSED. Later phase predicates
         * and native-validation stay required and UNASSESSED; both current
         * completion claims remain BLOCKED. HasStakeholder connections are typed
         * vocabulary witnesses only, not evaluated traversal or assignment rights.
         * This is not production semantic runtime parsing, API identity binding,
         * native SysML validation, acceptance, certification or SAF adoption.
         *
         * Runnable source consumer (from repository root):
         * python -m de4sdv.semantic.method_trace_adapter --repo . --increment INC-AEBS-010
         * python -m de4sdv.semantic.method_trace_adapter --repo . --increment INC-MW-002
         * Exit 0 means inspection completed, not readiness PASS; inspect the JSON
         * evaluation and its required blockers. Invalid declarations exit 2.
         * Source provenance is working-tree@Git-HEAD with unbound API identifiers;
         * no committed/native-validation provenance is inferred. Native exact-head
         * validation and generated-authority registration belong to integration.
         */
  }

  part def IncrementTraceObligations {
    doc /* Required traces derive from the selected approved method, not from
         * candidate-selected easy checks. References identify existing artifacts;
         * populating this declaration is not completion evidence. Reuse prior
         * artifacts, preserve R/F/L/P, and do not invent realization or execution
         * for early framing. Missing required traces block the corresponding claim
         * unless an authorized visible disposition permits it. Unsupported or
         * unavailable evaluation stays UNASSESSED, never synthetic PASS. */
    ref part increment : EngineeringIncrement;
    ref part declaredScope : IncrementScope;
    ref part selectedMethod : ApprovedTraceMethod;
    attribute scopeKind : ScalarValues::String;
    attribute applicablePhases[*] : MethodPhase;
    attribute completionClaim : TraceCompletionClaim;
    ref requirement problemStatement[0..1] : ProblemStatement;
    ref part engineeringQuestion[0..1] : IncrementEngineeringQuestion;
    ref part lifecycleDecision[0..1] : IncrementLifecycleDecision;
    ref part stakeholders[*] : Stakeholder;
    ref requirement concerns[*];
    ref part gaps[*] : IncrementGap;
  }
}
