package DE4SDV_SoftwareUpdateReadinessNeedsRequirements {
    doc /*
     * Stakeholder needs and design-input requirements of INC-TEST-001, the
     * pre-update vehicle readiness check. Validation scenarios are planned only.
     *
     * THROWAWAY: method-loop test content, never merged.
     */

    private import DE4SDV_MethodContext::*;
    private import DE4SDV_RelationshipSuccessor::*;
    private import DE4SDV_SoftwareUpdateReadinessFraming::*;

    // ---- Stakeholder needs ----------------------------------------------------

    requirement <'NEED-TEST-001'> needVehicleSecuredDuringUpdate : StakeholderNeedCandidate {
        doc /* Owner need: the vehicle stays stationary and secured while it is updated. */
        subject increment : SoftwareUpdateReadinessIncrement;
        stakeholder vehicleOwner : VehicleOwner;
        require constraint statement {
            language "English"
            /* The vehicle owner needs the vehicle to stay stationary and secured
               for the whole time a software update is being installed. */
        }
        attribute :>> source = "Owner interviews and field reports of vehicles that could not be driven after an interrupted update (illustrative source for this test increment)";
        attribute :>> rationale = "Installation makes the vehicle non-drivable, so starting it while the vehicle could move or is in traffic puts the occupants and other road users at risk.";
    }

    requirement <'NEED-TEST-002'> needDriverControlsUpdateTiming : StakeholderNeedCandidate {
        doc /* Owner need: the driver decides whether and when an update is installed. */
        subject increment : SoftwareUpdateReadinessIncrement;
        stakeholder vehicleOwner : VehicleOwner;
        require constraint statement {
            language "English"
            /* The vehicle owner needs to decide whether and when a software update
               is installed, and to learn why an agreed update did not start. */
        }
        attribute :>> source = "Owner complaints about updates that blocked the vehicle at an inconvenient time (illustrative source for this test increment)";
        attribute :>> rationale = "An update that installs without the driver's agreement removes the vehicle from use without warning and erodes trust in OTA updates.";
    }

    requirement <'NEED-TEST-003'> needUpdateCompletesOrRecovers : StakeholderNeedCandidate {
        doc /* Campaign operator need: no vehicle is left unusable by an update that cannot finish. */
        subject increment : SoftwareUpdateReadinessIncrement;
        stakeholder updateCampaignOperator : UpdateCampaignOperator;
        require constraint statement {
            language "English"
            /* The update campaign operator needs an installation to start only when
               the vehicle can either complete it or roll it back, so that no vehicle
               is left unusable. */
        }
        attribute :>> source = "Campaign cost analysis of roadside assistance calls after updates that ran out of battery (illustrative source for this test increment)";
        attribute :>> rationale = "An installation interrupted by an empty battery can leave the vehicle without a bootable software image, which needs a workshop visit to recover.";
    }

    // ---- Planned validation scenarios -------------------------------------------

    part <'SC-TEST-001-01'> overnightHomeUpdateScenario : ValidationPlanningScenario {
        doc /*
         * The owner parks at home in the evening, gets the update notice on the
         * vehicle display, agrees, and the update installs overnight. Checks that
         * the readiness check fits the owner's routine. Planned, not executed.
         */
    }

    part <'SC-TEST-001-02'> lowEnergyDepotScenario : ValidationPlanningScenario {
        doc /*
         * A fleet vehicle with a low battery is parked at the depot when the
         * campaign starts. The installation is deferred until the vehicle has been
         * charged and the operator sees why. Planned, not executed.
         */
    }

    connection vehicleSecuredValidatedByOvernightHomeUpdate : ValidationPlanningAssociation
        connect needVehicleSecuredDuringUpdate to overnightHomeUpdateScenario;

    connection driverControlValidatedByOvernightHomeUpdate : ValidationPlanningAssociation
        connect needDriverControlsUpdateTiming to overnightHomeUpdateScenario;

    connection updateRecoveryValidatedByLowEnergyDepot : ValidationPlanningAssociation
        connect needUpdateCompletesOrRecovers to lowEnergyDepotScenario;

    // ---- Design-input requirements --------------------------------------------

    requirement <'REQ-TEST-001'> reqParkedStatePrecondition : RequirementCandidate {
        doc /* Parked-state precondition for starting an installation. */
        subject increment : SoftwareUpdateReadinessIncrement;
        require constraint statement {
            language "English"
            /* The vehicle update client shall permit an installation to start only
               while the gear selector is in park, the parking brake is applied, and
               the vehicle speed is 0 km/h. */
        }
        attribute :>> verificationMethod = "test";
        attribute :>> successCriteria = "Installation start is permitted in the combination park, parking brake applied and 0 km/h, and refused in all 15 other combinations of gear (P, R, N, D), parking brake (applied, released) and speed (0 km/h, 5 km/h).";
    }

    requirement <'REQ-TEST-002'> reqEnergyPrecondition : RequirementCandidate {
        doc /* Energy precondition for starting an installation. */
        subject increment : SoftwareUpdateReadinessIncrement;
        require constraint statement {
            language "English"
            /* The vehicle update client shall permit an installation to start only
               when the low-voltage battery state of charge, and on vehicles with a
               traction battery also the traction battery state of charge, is at or
               above the minimum declared in the update package. */
        }
        attribute :>> verificationMethod = "test";
        attribute :>> successCriteria = "With declared minimums of 70 % (low-voltage) and 30 % (traction), installation start is refused at 69 % or 29 % and permitted at 70 % and 30 %, on a bench with simulated battery signals.";
    }

    requirement <'REQ-TEST-003'> reqConsentPrecondition : RequirementCandidate {
        doc /* Driver-consent precondition for starting an installation. */
        subject increment : SoftwareUpdateReadinessIncrement;
        require constraint statement {
            language "English"
            /* The vehicle update client shall permit an installation to start only
               if the driver confirmed consent for that exact update package version
               on the vehicle display within the 10 minutes before the start. */
        }
        attribute :>> verificationMethod = "demo";
        attribute :>> successCriteria = "The installation does not start without consent, with consent for another package version, or 10 min 1 s after consent; it starts when consent for the same version was given less than 10 min earlier.";
    }

    requirement <'REQ-TEST-004'> reqRefusalReporting : RequirementCandidate {
        doc /* Reporting of a refused installation start. */
        subject increment : SoftwareUpdateReadinessIncrement;
        require constraint statement {
            language "English"
            /* When the vehicle update client refuses to start an installation, it
               shall report every unmet precondition to the vehicle display and to
               the update backend within 5 s of the refusal. */
        }
        attribute :>> verificationMethod = "test";
        attribute :>> successCriteria = "For each single unmet precondition and for all of them unmet together, the display and the backend log name every unmet precondition within 5 s of the refusal.";
    }

    // ---- Requirement provenance (DerivesFromNeed only) --------------------------

    connection parkedStateDerivesFromVehicleSecured : DerivesFromNeed
        connect needVehicleSecuredDuringUpdate to reqParkedStatePrecondition;

    connection energyDerivesFromUpdateRecovery : DerivesFromNeed
        connect needUpdateCompletesOrRecovers to reqEnergyPrecondition;

    connection consentDerivesFromDriverControl : DerivesFromNeed
        connect needDriverControlsUpdateTiming to reqConsentPrecondition;

    connection refusalReportingDerivesFromDriverControl : DerivesFromNeed
        connect needDriverControlsUpdateTiming to reqRefusalReporting;

    connection refusalReportingDerivesFromUpdateRecovery : DerivesFromNeed
        connect needUpdateCompletesOrRecovers to reqRefusalReporting;
}
