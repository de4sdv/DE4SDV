/*
 * DE4SDV middleware increment framing model slice.
 *
 * INC-MW-002 frames the middleware integration increment only. It establishes
 * the question, scope shell, traceability shell, and assurance view for the
 * middleware integration story. It does not commit to AAOS SDV, Eclipse
 * S-CORE, AUTOSAR Adaptive, adapter realization, or any physical/software
 * implementation choice.
 */

package DE4SDV_MiddlewareIncrementFraming {
  package Features {
    package Middleware {
      package IncrementFraming {
        private import Views::*;
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import SAF_Viewpoints::*;

        part def MiddlewareIncrement :> EngineeringIncrement;

        part incMW002 : MiddlewareIncrement {
          doc /*
           * INC-MW-002: middleware integration operational context and framing
           * shell.
           */
        }

        requirement middlewareIntegrationProblemStatement : ProblemStatement {
          doc /* How can DE4SDV model middleware integration between a domain-specific ADAS application and a vehicle platform so that platform decoupling, product-line variability, safety-path boundaries, upstream engagement, and evidence traceability remain explicit without selecting a concrete realization? */
          subject increment : MiddlewareIncrement;
          stakeholder platformEngineer : SystemsEngineer;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder productLineEngineer : ProductLineEngineer;
          stakeholder safetyExpert : SafetyExpert;
          stakeholder maintainer : Maintainer;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        part scopeMW002 : IncrementScope {
          doc /*
           * Scope: vehicle signals, lifecycle coordination, health monitoring,
           * diagnostics, update coordination, and the explicit emergency
           * intervention boundary.
           */
        }

        part traceabilityShellMW002 : IncrementTraceabilityShell {
          doc /*
           * Traceability shell: increment framing -> concerns/views ->
           * operational context -> operational story -> assumptions/gaps.
           */
        }

        part engineeringQuestionMW002 : IncrementEngineeringQuestion {
          doc /*
           * What operational scenarios require middleware integration between an
           * ADAS application and the vehicle platform, and who are the
           * operational actors?
           */
        }

        part lifecycleDecisionMW002 : IncrementLifecycleDecision {
          doc /*
           * Decide whether the middleware operational context is correctly scoped
           * before deriving requirements or functional architecture.
           */
        }

        part asmMW005 : IncrementAssumption {
          doc /*
           * ASM-MW-005: The operational scenarios assume the ADAS application is
           * already functionally complete. The middleware integration does not
           * change what the ADAS application does — it changes how the ADAS
           * application accesses vehicle platform services.
           */
        }

        part asmMW006 : IncrementAssumption {
          doc /*
           * ASM-MW-006: The middleware provides vehicle signals, diagnostics,
           * lifecycle, health, and update coordination as distributed services.
           * The operational context does not assume a specific middleware
           * implementation.
           */
        }

        part asmMW007 : IncrementAssumption {
          doc /*
           * ASM-MW-007: Multiple SDV Core instances may operate together (as
           * separate VMs on one SoC, on different SoCs, or across the vehicle
           * network). The operational context covers the distributed case, not
           * just a single instance.
           */
        }

        part gapMW006 : IncrementGap {
          doc /*
           * GAP-MW-006: The specific vehicle signals that the ADAS application
           * needs from the middleware are not yet enumerated. This is deferred to
           * INC-MW-005 (requirements).
           */
        }

        part gapMW007 : IncrementGap {
          doc /*
           * GAP-MW-007: The mapping between ROS 2 topics and middleware service
           * interfaces is not yet defined. This is deferred to INC-MW-006
           * (functional architecture) and INC-MW-008 (physical realization).
           */
        }

        part gapMW008 : IncrementGap {
          doc /*
           * GAP-MW-008: The security and trust boundary for middleware
           * communication (DICE identity, attestation, VLAN segmentation) is not
           * yet modeled. This is deferred to a security-focused increment or
           * INC-MW-005 (requirements).
           */
        }

        concern middlewareIncrementAssuranceConcern : ArgumentationAssuranceConcern {
          doc /*
           * Reviewers need the increment claim, scope, assumptions, gaps, and
           * traceability shell linked in an assurance argument for this
           * middleware framing slice.
           */
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }

        view middlewareIncrementAssuranceView {
          viewpoint selectedIncrementAssuranceViewpoint : ArgumentationAssuranceViewpoint {
            frame middlewareIncrementAssuranceConcern;
          }

          expose IncrementFraming::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
