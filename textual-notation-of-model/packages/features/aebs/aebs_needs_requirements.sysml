/*
 * DE4SDV AEBS needs and draft requirements model slice.
 *
 * System 1 product needs and requirements are partitioned from System 2
 * engineering-assurance and evidence-governance needs and requirements.
 * Stable externally imported usage names are retained where practical.
 * No V&V verdict, realization, or UNECE R152 compliance claim is made here.
 */
package DE4SDV_AEBSNeedsRequirements {
  package Features {
    package AEBS {
      package NeedsRequirements {
        private import DE4SDV_Stakeholders::*;
        private import DE4SDV_MethodContext::*;
        private import DE4SDV_ProductLine::*;
        private import DE4SDV_MethodViewpoints::*;
        private import SAF_Viewpoints::*;
        private import SysideViews::**;
        private import Views::*;

        part def AEBSCapability :> CommonProductLineCapability;

        requirement def PedestrianCollisionRiskNeed :> StakeholderNeedCandidate;
        requirement def BicycleCollisionRiskNeed :> StakeholderNeedCandidate;

        part incAEBS003 : NeedsRequirementsIncrement;

        part aebsNeedsRequirementsSystemContext : SystemContext {
          doc /* DE4SDV method system context for INC-AEBS-003. */
          part productLine : SDVProductLine :>> systemOfInterest;
          part memberProduct : ProductLineMemberProduct;
          part aebsCapability : AEBSCapability;
          part roadUserStakeholder : RoadUser;
          part occupantStakeholder : VehicleOccupant;
          part systemsEngineerStakeholder : SystemsEngineer;
          part productLineEngineerStakeholder : ProductLineEngineer;
          part complianceEngineerStakeholder : ComplianceEngineer;
          part verificationEngineerStakeholder : VerificationEngineer;

          requirement aebsNeedsRequirementsProblemStatement : ProblemStatement {
            doc /* How can DE4SDV define partitioned AEBS product and assurance needs and draft requirements while preserving boundaries, gaps, and controlled source constraints without making realization or compliance claims? */
            subject increment : NeedsRequirementsIncrement;
            stakeholder roadUser : RoadUser;
            stakeholder occupant : VehicleOccupant;
            stakeholder systemsEngineer : SystemsEngineer;
            stakeholder productLineEngineer : ProductLineEngineer;
            stakeholder complianceEngineer : ComplianceEngineer;
            stakeholder verificationEngineer : VerificationEngineer;
          }
        }

        package System1Product {
          requirement needCommonAEBSCapability : ProductLineCommonCapabilityNeed {
            doc /* N-AEBS-001 draft System 1 need. */
            subject productLine : SDVProductLine;
            stakeholder roadUser : RoadUser;
            stakeholder occupant : VehicleOccupant;
            require constraint statement { language "English" /* Road users and vehicle occupants need the SDV product line to define AEBS as a common capability required across member products to reduce forward rear-end in-lane collision risk with a vehicle target under defined operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-AEBS-001 framing and INC-AEBS-002 operational context";
            attribute :>> rationale = "Road-user and occupant collision-risk expectation established in the operational slice; AEBS is a common capability required across member products.";
          }
          requirement needPedestrianCollisionRiskReduction : PedestrianCollisionRiskNeed {
            doc /* N-AEBS-006 draft System 1 need; source identity is controlled and applicability remains open. */
            subject productLine : SDVProductLine;
            stakeholder pedestrian : RoadUser;
            require constraint statement { language "English" /* Pedestrians need the SDV product line to provide a common AEBS capability that reduces forward collision risk with a pedestrian target under defined applicable operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-AEBS-002 operational context; controlled public-safe source metadata E/ECE/TRANS/505/Rev.3/Add.151/Rev.2 (SRC-UNECE-R152)";
            attribute :>> rationale = "Pedestrian forward-collision risk is a distinct stakeholder concern; applicability remains open per GAP-AEBS-REQ-013 and GAP-AEBS-REQ-015.";
          }
          requirement needBicycleCollisionRiskReduction : BicycleCollisionRiskNeed {
            doc /* N-AEBS-007 draft System 1 need; source identity is controlled and applicability remains open. */
            subject productLine : SDVProductLine;
            stakeholder cyclist : RoadUser;
            require constraint statement { language "English" /* Cyclists need the SDV product line to provide a common AEBS capability that reduces forward collision risk with a bicycle target under defined applicable operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-AEBS-002 operational context; controlled public-safe source metadata E/ECE/TRANS/505/Rev.3/Add.151/Rev.2 (SRC-UNECE-R152)";
            attribute :>> rationale = "Cyclist forward-collision risk is a distinct stakeholder concern; applicability remains open per GAP-AEBS-REQ-013 and GAP-AEBS-REQ-016.";
          }
          requirement needBoundedDegradationAndAvailability : ProductSafetyAvailabilityNeed {
            doc /* N-AEBS-008 draft System 1 safety and availability need. */
            subject memberProduct : ProductLineMemberProduct;
            stakeholder roadUser : RoadUser;
            stakeholder occupant : VehicleOccupant;
            require constraint statement { language "English" /* Road users and vehicle occupants need each SDV product-line member product to manage AEBS degradation so that behavior remains bounded and AEBS availability is apparent when required inputs or AEBS functions are not healthy. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "INC-AEBS-002 operational context degraded-mode scenarios";
            attribute :>> rationale = "Unavailable or unhealthy AEBS inputs must not present misleading availability to the driver.";
          }
          requirement needTrustworthyInterventionDecisions : ProductSafetyAvailabilityNeed {
            doc /* N-AEBS-014 draft System 1 need; non-activation and false-reaction parent derived from N-AEBS-008 review findings. */
            subject memberProduct : ProductLineMemberProduct;
            stakeholder roadUser : RoadUser;
            stakeholder occupant : VehicleOccupant;
            require constraint statement { language "English" /* Road users and vehicle occupants need each SDV product-line member product to keep AEBS intervention decisions trustworthy so that neither a collision warning nor emergency braking occurs when AEBS controlled non-activation criteria determine that imminent collision risk is absent under defined operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Requirements QA gate review of the INC-AEBS-003 baseline";
            attribute :>> rationale = "Non-activation silence constraints need a System 1 parent whose intent they preserve; nuisance warning/braking erodes driver trust in AEBS.";
          }

          requirement reqDetectForwardCollisionRisk : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-001 candidate. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Each SDV product-line member product shall realize the common AEBS capability by detecting imminent forward collision risk with a vehicle target under defined operating conditions. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-001";
            attribute :>> rationale = "Detection is the enabling behavior for every downstream AEBS intervention.";
            attribute :>> verificationMethod = "analyze";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqProvideCollisionWarning : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-002 candidate. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Each SDV product-line member product shall realize the common AEBS capability by providing a collision warning to the driver when defined warning conditions are met. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-001";
            attribute :>> rationale = "Driver warning precedes autonomous braking and is required before intervention.";
            attribute :>> verificationMethod = "demo";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqCommandEmergencyBraking : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-003 candidate. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Each SDV product-line member product shall realize the common AEBS capability by commanding emergency braking when defined activation conditions are met and no overriding condition prevents intervention. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-001";
            attribute :>> rationale = "Collision-risk reduction ultimately requires braking intervention when warning is insufficient.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqAllowDriverOverride : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-004 draft; controlled override-response mapping remains a blocker. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* When a valid, fresh, and unambiguous driver input is classified as a conscious override under controlled override criteria during AEBS intervention, each SDV product-line member product shall apply the intervention response selected by the controlled override-response mapping. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-001";
            attribute :>> rationale = "Driver authority over intervention is expected behavior; the controlled override-response mapping is unresolved.";
            attribute :>> verificationMethod = "demo";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqDetectAEBSFailureCondition : SafetyConstraintRequirementCandidate {
            doc /* REQ-AEBS-005 failure-detection draft derived from N-AEBS-008; carries the bounded-behavior envelope of N-AEBS-008 pending safe-operation criteria, see GAP-AEBS-REQ-007. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Under controlled failure-detection criteria, each SDV product-line member product shall detect AEBS-related failure conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-008; carries the bounded-behavior envelope pending safe-operation criteria (GAP-AEBS-REQ-007)";
            attribute :>> rationale = "Degradation management presupposes failure detection.";
            attribute :>> verificationMethod = "inspect";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqResistFalseReaction : SafetyConstraintRequirementCandidate {
            doc /* REQ-AEBS-008 warning-silence draft derived from N-AEBS-014; criteria, window, and tolerances remain gaps. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* When controlled non-activation criteria determine that imminent forward collision risk is absent under defined operating conditions, each SDV product-line member product shall not issue an AEBS collision warning. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-014";
            attribute :>> rationale = "Prevents nuisance warnings when controlled non-activation criteria rule out imminent risk.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqHandleDegradedUnavailableInputs : SafetyConstraintRequirementCandidate {
            doc /* REQ-AEBS-009 state-transition draft; state mapping, ownership, and timing remain gaps. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* When a required AEBS input is stale, missing, malformed, inconsistent, or unavailable under controlled input-health criteria, each SDV product-line member product shall enter the AEBS state selected by the controlled degraded-state mapping. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-008";
            attribute :>> rationale = "Unhealthy inputs must drive a controlled degraded state rather than silent misbehavior.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqPedestrianTargetResponse : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-010 pedestrian detection draft; stable usage name retained for imports. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Each SDV product-line member product shall detect imminent forward collision risk with a pedestrian target under defined applicable pedestrian-target operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-006";
            attribute :>> rationale = "Pedestrian targets require distinct detection behavior from vehicle targets; criteria open per GAP-AEBS-REQ-015.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqBicycleTargetResponse : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-011 bicycle detection draft; stable usage name retained for imports. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Each SDV product-line member product shall detect imminent forward collision risk with a bicycle target under defined applicable bicycle-target operating conditions. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-007";
            attribute :>> rationale = "Bicycle targets require distinct detection behavior from vehicle targets; criteria open per GAP-AEBS-REQ-016.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqResistFalseBrakingCommand : SafetyConstraintRequirementCandidate {
            doc /* REQ-AEBS-012 braking-silence draft derived from N-AEBS-014. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* When controlled non-activation criteria determine that imminent forward collision risk is absent under defined operating conditions, each SDV product-line member product shall not command AEBS emergency braking. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-014";
            attribute :>> rationale = "Prevents nuisance braking when controlled non-activation criteria rule out imminent risk.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqIndicateDegradedUnavailableStatus : SafetyConstraintRequirementCandidate {
            doc /* REQ-AEBS-013 status-indication draft. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* When a required AEBS input is stale, missing, malformed, inconsistent, or unavailable under controlled input-health criteria, each SDV product-line member product shall provide the status indication selected by the controlled degraded-state indication mapping. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-008";
            attribute :>> rationale = "Availability must be apparent to the driver when AEBS inputs or functions are not healthy.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqPedestrianTargetControlledResponse : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-014 pedestrian response draft; specializes the braking-command response family of REQ-AEBS-003 for classified pedestrian-target risk. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Under defined applicable pedestrian-target operating conditions, each SDV product-line member product shall apply the controlled AEBS response to classified pedestrian-target collision risk. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-006";
            attribute :>> rationale = "Classified pedestrian-target risk needs a defined response; specializes the REQ-AEBS-003 response family.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqBicycleTargetControlledResponse : FunctionalRequirementCandidate {
            doc /* REQ-AEBS-015 bicycle response draft; specializes the braking-command response family of REQ-AEBS-003 for classified bicycle-target risk. */
            subject memberProduct : ProductLineMemberProduct;
            require constraint statement { language "English" /* Under defined applicable bicycle-target operating conditions, each SDV product-line member product shall apply the controlled AEBS response to classified bicycle-target collision risk. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "Derived from N-AEBS-007";
            attribute :>> rationale = "Classified bicycle-target risk needs a defined response; specializes the REQ-AEBS-003 response family.";
            attribute :>> verificationMethod = "test";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
        }

        package System2EngineeringAssurance {
          requirement needExplicitOperationalBoundary : EngineeringTraceabilityNeed {
            doc /* N-AEBS-002 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder systemsEngineer : SystemsEngineer;
            require constraint statement { language "English" /* Systems engineers need the DE4SDV AEBS increment to keep its operational boundary, assumptions, source constraints, and out-of-scope cases explicit while draft requirements are derived. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV method increment workflow";
            attribute :>> rationale = "Boundary and assumption visibility is a review precondition for derived requirements.";
          }
          requirement needProductLineClassification : ProductLineClassificationNeed {
            doc /* N-AEBS-003 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder productLineEngineer : ProductLineEngineer;
            require constraint statement { language "English" /* Product-line engineers need the DE4SDV AEBS increment to keep AEBS classified as a common capability, with native SysML v2 variation and variant choices modeled separately without weakening the System 1 capability. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV method increment workflow; MBPLE feature-model conventions";
            attribute :>> rationale = "Common-capability vs variant classification must stay explicit for product-line derivation.";
          }
          requirement needVisibleRegulatoryAssumptions : RegulatoryVisibilityNeed {
            doc /* N-AEBS-004 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder complianceEngineer : ComplianceEngineer;
            require constraint statement { language "English" /* Compliance engineers need the DE4SDV AEBS increment to keep regulatory assumptions, controlled source references, and open applicability and interpretation gaps visible without implying compliance or type approval. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV compliance workflow; SRC-UNECE-R152 controlled source identity";
            attribute :>> rationale = "Regulatory applicability must be visible and unresolved without implying compliance.";
          }
          requirement needRequirementVVPlanning : VerificationPlanningNeed {
            doc /* N-AEBS-005 draft System 2 need. */
            subject increment : NeedsRequirementsIncrement;
            stakeholder verificationEngineer : VerificationEngineer;
            require constraint statement { language "English" /* Verification engineers need the DE4SDV AEBS increment to maintain a separate controlled V&V planning attachment for each draft AEBS requirement without changing the product obligation. */ }
            attribute :>> status = ReqStatus::InDevelopment;
            attribute :>> source = "DE4SDV verification and assurance workflow";
            attribute :>> rationale = "V&V planning attachments are kept separate from normative requirement text.";
          }
          requirement reqKeepProductLineClassificationExplicit : ProductLineConstraintRequirementCandidate {
            doc /* REQ-AEBS-006 System 2 candidate. */
            subject increment : NeedsRequirementsIncrement;
            require constraint statement { language "English" /* The DE4SDV AEBS increment shall keep common-capability, feature, and native SysML v2 variation and variant classifications explicit for each AEBS behavior or scope element in its model baseline. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-003";
            attribute :>> rationale = "Makes the classification need enforceable on the increment baseline.";
            attribute :>> verificationMethod = "inspect";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqTraceRequirementVVAndGaps : TraceabilityConstraintRequirementCandidate {
            doc /* REQ-AEBS-007 System 2 candidate. */
            subject increment : NeedsRequirementsIncrement;
            require constraint statement { language "English" /* The DE4SDV AEBS increment shall maintain separate trace links from each draft AEBS requirement to its source, stakeholder need, unresolved gaps, validation reference, and controlled V&V planning attachment. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-004 and N-AEBS-005";
            attribute :>> rationale = "Traceability is the mechanism that keeps regulatory assumptions and V&V planning visible.";
            attribute :>> verificationMethod = "inspect";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
          requirement reqTraceEvidenceContractsToControlledBoundary : EvidenceContractTraceabilityRequirementCandidate {
            doc /* REQ-AEBS-S2-001 System 2 evidence-contract candidate derived only from N-AEBS-002. */
            subject increment : NeedsRequirementsIncrement;
            require constraint statement { language "English" /* The DE4SDV AEBS increment shall maintain trace links from each AEBS evidence contract to its controlled operational boundary, assumptions, source constraints, and exclusions. */ }
            attribute :>> status = ReqStatus::ReadyForReview;
            attribute :>> source = "Derived from N-AEBS-002";
            attribute :>> rationale = "Evidence contracts are only reviewable against their controlled operational boundary.";
            attribute :>> verificationMethod = "inspect";
            attribute :>> verificationStatus = VVStatus::NotStarted;
          }
        }

        dependency req001DerivedFromNeed001 from reqDetectForwardCollisionRisk to needCommonAEBSCapability;
        dependency req002DerivedFromNeed001 from reqProvideCollisionWarning to needCommonAEBSCapability;
        dependency req003DerivedFromNeed001 from reqCommandEmergencyBraking to needCommonAEBSCapability;
        dependency req004DerivedFromNeed001 from reqAllowDriverOverride to needCommonAEBSCapability;
        dependency req005DerivedFromNeed008 from reqDetectAEBSFailureCondition to needBoundedDegradationAndAvailability;
        dependency req009DerivedFromNeed008 from reqHandleDegradedUnavailableInputs to needBoundedDegradationAndAvailability;
        dependency req013DerivedFromNeed008 from reqIndicateDegradedUnavailableStatus to needBoundedDegradationAndAvailability;
        dependency req008DerivedFromNeed014 from reqResistFalseReaction to needTrustworthyInterventionDecisions;
        dependency req012DerivedFromNeed014 from reqResistFalseBrakingCommand to needTrustworthyInterventionDecisions;
        dependency req010DerivedFromNeed006 from reqPedestrianTargetResponse to needPedestrianCollisionRiskReduction;
        dependency req014DerivedFromNeed006 from reqPedestrianTargetControlledResponse to needPedestrianCollisionRiskReduction;
        dependency req011DerivedFromNeed007 from reqBicycleTargetResponse to needBicycleCollisionRiskReduction;
        dependency req015DerivedFromNeed007 from reqBicycleTargetControlledResponse to needBicycleCollisionRiskReduction;
        dependency req006DerivedFromNeed003 from reqKeepProductLineClassificationExplicit to needProductLineClassification;
        dependency req007DerivedFromNeed004 from reqTraceRequirementVVAndGaps to needVisibleRegulatoryAssumptions;
        dependency req007DerivedFromNeed005 from reqTraceRequirementVVAndGaps to needRequirementVVPlanning;
        dependency reqS2001DerivedFromNeed002 from reqTraceEvidenceContractsToControlledBoundary to needExplicitOperationalBoundary;

        public import System1Product::*;
        public import System2EngineeringAssurance::*;

        /*
         * Gaps — deferred scope items per the DE4SDV method.
         * These are the most important gap categories; individual
         * requirement-level gaps are referenced in the YAML V&V planning.
         */
        part operatingConditionsGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-001: Selected operating conditions remain undefined. */
        }
        part detectionCriteriaGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-002: Vehicle-target detection criteria remain undefined. */
        }
        part warningCriteriaGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-003: Collision-warning timing, modality, and observability criteria remain undefined. */
        }
        part brakingActivationGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-004: Emergency-braking activation conditions and braking demand profile remain undefined. */
        }
        part nonActivationGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-005: Non-activation and false-reaction constraints remain undefined. */
        }
        part overrideCriteriaGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-006: Conscious driver override inputs and resulting behavior remain undefined. */
        }
        part failureDetectionGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-007: AEBS failure detection, indication, and safe-operation criteria remain undefined. */
        }
        part variationModelingGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-008: Native SysML v2 variation and variant choices are not yet modeled. */
        }
        part vssSignalGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-009: VSS signal candidates are intentionally deferred until the functional-interface increment. */
        }
        part satisfactionGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-010: Requirement satisfaction assertions are deferred until functional/conceptual realization exists. */
        }
        part nonActivationScenarioGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-011: Complete non-activation scenarios, observation windows, classification rules, and false-reaction tolerances remain undefined. */
        }
        part degradedStateOwnershipGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-012: Degraded/unavailable state ownership, transition timing, indication behavior, and safe-operation response remain undefined. */
        }
        part regulatoryApplicabilityGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-013: Source identity is controlled, but amendment-selection rationale, vehicle-category applicability, and authority interpretation remain unresolved. */
        }
        part quantifiedThresholdGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-014: Promotion of quantified thresholds into System 1 obligations remains deferred. */
        }
        part pedestrianTargetGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-015: Pedestrian target definition, operating conditions, response criteria, and applicability remain unresolved. */
        }
        part bicycleTargetGap : DeferredProductLineScope {
          doc /* GAP-AEBS-REQ-016: Bicycle target definition, operating conditions, response criteria, and applicability remain unresolved. */
        }

        concern stakeholderNeedsConcern : StakeholderNeedsConcern {
          subject;
          stakeholder systemsEngineer : SystemsEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }
        concern requirementTraceConcern : RequirementTraceConcern {
          subject;
          stakeholder verificationEngineer : VerificationEngineer;
          stakeholder reviewer : OpenSourceReviewer;
        }
        view aebsStakeholderNeedsView : TVD::TableView {
          viewpoint selectedStakeholderNeedsViewpoint : StakeholderRequirementDefinitionViewpoint { frame stakeholderNeedsConcern; }
          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          filter @ SysML::RequirementUsage;
          attribute :>> includeReferenceElements = true;
          attribute :>> maxRowHeight = 300;
          view ID :> columnViews {
            attribute :>> featureToRender = CT::declaredName;
          }
          view Name :> columnViews {
            attribute :>> featureToRender = CT::heritage;
          }
          view Statement :> columnViews {
            attribute :>> featureToRender = CT::constraintLanguage {
              attribute constraintName = "statement";
              attribute constraintType = CL::ConT::required;
              attribute constraintLanguage = "English";
            }
            attribute :>> columnWidth = 360;
          }
        }
        view aebsRequirementTraceView {
          viewpoint selectedRequirementTraceViewpoint : SystemRequirementTraceabilityViewpoint { frame requirementTraceConcern; }
          expose System1Product::*;
          expose System2EngineeringAssurance::*;
          render asTreeDiagram;
        }
      }
    }
  }
}
