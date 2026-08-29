#!/usr/bin/env python3
"""One-shot attribute application: emit SysML attribute blocks per record.

Generates the `attribute :>> source = ...` / `:>> status = ...` blocks for
every ID'd need/requirement in the three needs/requirements slices, from the
controlled per-record assignment table below (reviewed content, not derived).
Run once during migration; output is pasted into the .sysml slices.
"""

from __future__ import annotations

import sys
from pathlib import Path

# record usage-name -> (status, source, rationale)
# status: ReqStatus value; source: non-parent provenance; rationale: why it exists
ASSIGNMENTS: dict[str, tuple[str, str, str]] = {
    # --- AEBS System 1 needs (INC-AEBS-003) ---
    "needCommonAEBSCapability": (
        "InDevelopment",
        "INC-AEBS-001 framing and INC-AEBS-002 operational context",
        "Road-user and occupant collision-risk expectation established in the operational slice; AEBS is a common capability required across member products.",
    ),
    "needPedestrianCollisionRiskReduction": (
        "InDevelopment",
        "INC-AEBS-002 operational context; controlled public-safe source metadata E/ECE/TRANS/505/Rev.3/Add.151/Rev.2 (SRC-UNECE-R152)",
        "Pedestrian forward-collision risk is a distinct stakeholder concern; applicability remains open per GAP-AEBS-REQ-013 and GAP-AEBS-REQ-015.",
    ),
    "needBicycleCollisionRiskReduction": (
        "InDevelopment",
        "INC-AEBS-002 operational context; controlled public-safe source metadata E/ECE/TRANS/505/Rev.3/Add.151/Rev.2 (SRC-UNECE-R152)",
        "Cyclist forward-collision risk is a distinct stakeholder concern; applicability remains open per GAP-AEBS-REQ-013 and GAP-AEBS-REQ-016.",
    ),
    "needBoundedDegradationAndAvailability": (
        "InDevelopment",
        "INC-AEBS-002 operational context degraded-mode scenarios",
        "Unavailable or unhealthy AEBS inputs must not present misleading availability to the driver.",
    ),
    "needTrustworthyInterventionDecisions": (
        "InDevelopment",
        "Requirements QA gate review of the INC-AEBS-003 baseline",
        "Non-activation silence constraints need a System 1 parent whose intent they preserve; nuisance warning/braking erodes driver trust in AEBS.",
    ),
    # --- AEBS System 1 requirement candidates ---
    "reqDetectForwardCollisionRisk": (
        "ReadyForReview",
        "Derived from N-AEBS-001",
        "Detection is the enabling behavior for every downstream AEBS intervention.",
    ),
    "reqProvideCollisionWarning": (
        "ReadyForReview",
        "Derived from N-AEBS-001",
        "Driver warning precedes autonomous braking and is required before intervention.",
    ),
    "reqCommandEmergencyBraking": (
        "ReadyForReview",
        "Derived from N-AEBS-001",
        "Collision-risk reduction ultimately requires braking intervention when warning is insufficient.",
    ),
    "reqAllowDriverOverride": (
        "InDevelopment",
        "Derived from N-AEBS-001",
        "Driver authority over intervention is expected behavior; the controlled override-response mapping is unresolved.",
    ),
    "reqDetectAEBSFailureCondition": (
        "InDevelopment",
        "Derived from N-AEBS-008; carries the bounded-behavior envelope pending safe-operation criteria (GAP-AEBS-REQ-007)",
        "Degradation management presupposes failure detection.",
    ),
    "reqResistFalseReaction": (
        "InDevelopment",
        "Derived from N-AEBS-014",
        "Prevents nuisance warnings when controlled non-activation criteria rule out imminent risk.",
    ),
    "reqHandleDegradedUnavailableInputs": (
        "InDevelopment",
        "Derived from N-AEBS-008",
        "Unhealthy inputs must drive a controlled degraded state rather than silent misbehavior.",
    ),
    "reqPedestrianTargetResponse": (
        "InDevelopment",
        "Derived from N-AEBS-006",
        "Pedestrian targets require distinct detection behavior from vehicle targets; criteria open per GAP-AEBS-REQ-015.",
    ),
    "reqBicycleTargetResponse": (
        "InDevelopment",
        "Derived from N-AEBS-007",
        "Bicycle targets require distinct detection behavior from vehicle targets; criteria open per GAP-AEBS-REQ-016.",
    ),
    "reqResistFalseBrakingCommand": (
        "InDevelopment",
        "Derived from N-AEBS-014",
        "Prevents nuisance braking when controlled non-activation criteria rule out imminent risk.",
    ),
    "reqIndicateDegradedUnavailableStatus": (
        "InDevelopment",
        "Derived from N-AEBS-008",
        "Availability must be apparent to the driver when AEBS inputs or functions are not healthy.",
    ),
    "reqPedestrianTargetControlledResponse": (
        "InDevelopment",
        "Derived from N-AEBS-006",
        "Classified pedestrian-target risk needs a defined response; specializes the REQ-AEBS-003 response family.",
    ),
    "reqBicycleTargetControlledResponse": (
        "InDevelopment",
        "Derived from N-AEBS-007",
        "Classified bicycle-target risk needs a defined response; specializes the REQ-AEBS-003 response family.",
    ),
    # --- AEBS System 2 ---
    "needExplicitOperationalBoundary": (
        "InDevelopment",
        "DE4SDV method increment workflow",
        "Boundary and assumption visibility is a review precondition for derived requirements.",
    ),
    "needProductLineClassification": (
        "InDevelopment",
        "DE4SDV method increment workflow; MBPLE feature-model conventions",
        "Common-capability vs variant classification must stay explicit for product-line derivation.",
    ),
    "needVisibleRegulatoryAssumptions": (
        "InDevelopment",
        "DE4SDV compliance workflow; SRC-UNECE-R152 controlled source identity",
        "Regulatory applicability must be visible and unresolved without implying compliance.",
    ),
    "needRequirementVVPlanning": (
        "InDevelopment",
        "DE4SDV verification and assurance workflow",
        "V&V planning attachments are kept separate from normative requirement text.",
    ),
    "reqKeepProductLineClassificationExplicit": (
        "ReadyForReview",
        "Derived from N-AEBS-003",
        "Makes the classification need enforceable on the increment baseline.",
    ),
    "reqTraceRequirementVVAndGaps": (
        "ReadyForReview",
        "Derived from N-AEBS-004 and N-AEBS-005",
        "Traceability is the mechanism that keeps regulatory assumptions and V&V planning visible.",
    ),
    "reqTraceEvidenceContractsToControlledBoundary": (
        "ReadyForReview",
        "Derived from N-AEBS-002",
        "Evidence contracts are only reviewable against their controlled operational boundary.",
    ),
    # --- AEBS-010 System 2 needs ---
    "needLiveVisualizationOnAAOS": (
        "InDevelopment",
        "INC-AEBS-010 increment framing; GCP AAOS runtime proof environment",
        "Stakeholder-visible AEBS behavior must be reviewable on a real AAOS display, not a host substitute.",
    ),
    "needPreservedSourceProvenance": (
        "InDevelopment",
        "INC-AEBS-010 increment framing",
        "Displayed values must remain traceable to their source identity and context.",
    ),
    "needFailClosedDegradation": (
        "InDevelopment",
        "INC-AEBS-010 increment framing",
        "A lost or invalid source must never be misread as current AEBS state.",
    ),
    "needCorrelatableEvidence": (
        "InDevelopment",
        "INC-AEBS-010 increment framing",
        "Verification needs source-to-screen correlation and replayable evidence.",
    ),
    "needNonInterference": (
        "InDevelopment",
        "INC-AEBS-010 increment framing",
        "Visualization instrumentation must not influence the behavior it observes.",
    ),
    # --- AEBS-010 System 2 requirement candidates ---
    "req010SourceFidelity": (
        "ReadyForReview",
        "Derived from N-AEBS-009 and N-AEBS-010",
        "Preserves provenance for each displayed value.",
    ),
    "req010NativeParticipation": (
        "ReadyForReview",
        "Derived from N-AEBS-009",
        "Anchors the display to the pinned native Autoware AEB component.",
    ),
    "req010NoNativeImpersonation": (
        "ReadyForReview",
        "Derived from N-AEBS-010",
        "Coordinator-derived values must not masquerade as native Autoware output.",
    ),
    "req010De4sdvParticipation": (
        "ReadyForReview",
        "Derived from N-AEBS-009",
        "Displays the DE4SDV coordinator's own warning, braking, and lifecycle state.",
    ),
    "req010NonInterference": (
        "ReadyForReview",
        "Derived from N-AEBS-013",
        "No command path from instrumentation into AEBS or vehicle control.",
    ),
    "req010FailClosedFreshness": (
        "ReadyForReview",
        "Derived from N-AEBS-011",
        "Stale input must suppress threat geometry rather than display it.",
    ),
    "req010AvailabilityDisposition": (
        "ReadyForReview",
        "Derived from N-AEBS-011",
        "Unavailable sources need an explicit disposition, not silence.",
    ),
    "req010InvalidRejection": (
        "ReadyForReview",
        "Derived from N-AEBS-011",
        "Malformed frames must be rejected without displaying payload values.",
    ),
    "req010RestorationBehavior": (
        "ReadyForReview",
        "Derived from N-AEBS-011",
        "Recovery must be bounded and observable without application restart.",
    ),
    "req010RealAAOSRendering": (
        "ReadyForReview",
        "Derived from N-AEBS-009 and N-AEBS-012",
        "The rendering surface must be the real AAOS guest application.",
    ),
    "req010AaosEnvironmentObservation": (
        "ReadyForReview",
        "Derived from N-AEBS-009",
        "Runtime environment evidence must come from the same rendered session.",
    ),
    "req010NoHostBrowserSurface": (
        "ReadyForReview",
        "Derived from N-AEBS-009",
        "A host-side browser page is not the AAOS rendering surface the need demands.",
    ),
    "req010EvidenceCorrelation": (
        "ReadyForReview",
        "Derived from N-AEBS-012",
        "Each rendered state must be correlatable with its observed source event.",
    ),
    # --- Middleware System 1 needs (INC-MW-004) ---
    "needMiddlewareIntegration": (
        "InDevelopment",
        "INC-MW-002 operational context and INC-MW-003 feature classification",
        "ADAS application capability depends on signal, diagnostic, lifecycle, health, and update access through platform middleware.",
    ),
    "needPlatformDecoupling": (
        "InDevelopment",
        "INC-MW-003 feature classification",
        "Middleware selection must remain a product-line feature choice, not an application property.",
    ),
    "needMiddlewareAsFeature": (
        "InDevelopment",
        "INC-MW-003 feature classification",
        "Adapter-layer commonality derives from the application-middleware feature pair.",
    ),
    "needSafetyPathIsolation": (
        "InDevelopment",
        "INC-MW-002 operational context emergency-intervention scenario",
        "Emergency intervention must survive middleware failure regardless of selected architecture; criteria open per GAP-MW-029.",
    ),
    # --- Middleware System 2 needs ---
    "needUpstreamEngagement": (
        "InDevelopment",
        "DE4SDV governance policy on external methodology adoption",
        "Upstream maintainers must be involved before deeper integration or vendoring.",
    ),
    "needSecurityTrustBoundary": (
        "InDevelopment",
        "Requirements QA gate review of the INC-MW-005 baseline",
        "Service-binding authentication needs a defined trust boundary to authenticate across; details deferred per GAP-MW-012.",
    ),
    "needTraceabilityToOperationalContext": (
        "InDevelopment",
        "DE4SDV method increment workflow",
        "Needs must trace to the operational scenarios that justify them.",
    ),
    "needExplicitEngineeringBoundary": (
        "InDevelopment",
        "DE4SDV method increment workflow",
        "Boundary, assumptions, and out-of-scope cases stay explicit while needs are derived.",
    ),
    "needVVPlanningAttachment": (
        "InDevelopment",
        "DE4SDV verification and assurance workflow",
        "Per-need V&V planning attachments stay separate from product obligations.",
    ),
    # --- Middleware System 1 requirement candidates (INC-MW-005) ---
    "reqProvideMiddlewareSignalAccess": (
        "ReadyForReview",
        "Derived from N-MW-001",
        "Signal access is the core middleware integration service for the ADAS application.",
    ),
    "reqProvideMiddlewareDiagnosticAccess": (
        "ReadyForReview",
        "Derived from N-MW-001",
        "Boundary health determinations require diagnostic visibility.",
    ),
    "reqCoordinateMiddlewareLifecycle": (
        "ReadyForReview",
        "Derived from N-MW-001",
        "Lifecycle transitions must be observable at the integration boundary.",
    ),
    "reqMonitorMiddlewareHealth": (
        "ReadyForReview",
        "Derived from N-MW-001",
        "Degraded integration services must be detected and indicated.",
    ),
    "reqCoordinateMiddlewareUpdates": (
        "ReadyForReview",
        "Derived from N-MW-001",
        "Updates must not silently invalidate required interfaces.",
    ),
    "reqIsolateSafetyPath": (
        "InDevelopment",
        "Derived from N-MW-004",
        "Middleware failure must not cause uncontrolled emergency intervention; containment criteria open per GAP-MW-029.",
    ),
    "reqProvideServiceDiscovery": (
        "ReadyForReview",
        "Derived from N-MW-002",
        "Services must be bound before use for decoupled integration.",
    ),
    "reqAuthenticateServiceBinding": (
        "InDevelopment",
        "Derived from N-MW-009",
        "Service data and commands across a trust boundary must be authenticated; boundary details deferred per GAP-MW-012.",
    ),
    # --- Middleware System 2 ---
    "reqMaintainMiddlewareBoundaryTraceability": (
        "ReadyForReview",
        "Derived from N-MW-006",
        "Trace links are the increment's assurance backbone.",
    ),
}


def blocks(name: str) -> str:
    status, source, rationale = ASSIGNMENTS[name]
    return (
        f'attribute :>> status = ReqStatus::{status};\n'
        f'attribute :>> source = "{source}";\n'
        f'attribute :>> rationale = "{rationale}";'
    )


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else "needCommonAEBSCapability"
    if target == "--all":
        for name in ASSIGNMENTS:
            print(f"### {name}\n{blocks(name)}\n")
    else:
        print(blocks(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
