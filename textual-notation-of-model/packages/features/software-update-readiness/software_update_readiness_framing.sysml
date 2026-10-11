package DE4SDV_SoftwareUpdateReadinessFraming {
    doc /*
     * Framing of INC-TEST-001: a pre-update vehicle readiness check that runs
     * before an over-the-air (OTA) software update is installed. The check
     * decides whether installation may start, based on the parked state, the
     * available energy and the driver's consent.
     *
     * THROWAWAY: this increment exists only to test whether an agent can walk
     * a new increment through the DE4SDV method from the method model and the
     * semantic API. It is never merged.
     */

    private import DE4SDV_MethodContext::*;
    private import DE4SDV_IncrementWorkflow::*;
    private import DE4SDV_MethodProcess::*;

    // ---- Increment identity -------------------------------------------------

    part def SoftwareUpdateReadinessIncrement :> EngineeringIncrement {
        doc /*
         * Engineering increment that specifies the vehicle-side readiness check
         * gating the start of an OTA software installation.
         */
    }

    part <'INC-TEST-001'> incTEST001 : SoftwareUpdateReadinessIncrement;

    // ---- Stakeholder roles ----------------------------------------------------

    part def VehicleOwner :> DE4SDV_Stakeholders::Stakeholder {
        doc /* Owner or driver of the vehicle who receives and accepts software updates. */
    }

    part def UpdateCampaignOperator :> DE4SDV_Stakeholders::Stakeholder {
        doc /*
         * OEM or fleet role that releases an OTA update campaign and carries the
         * cost of failed or interrupted installations.
         */
    }

    // ---- Charter --------------------------------------------------------------

    part softwareUpdateReadinessCharter : IncrementCharter {
        ref part :>> increment = incTEST001;
        attribute :>> owner = "DE4SDV systems engineering lead (throwaway method-loop test)";
        attribute :>> applicablePhases = (
            MethodPhase::phase0_incrementFraming,
            MethodPhase::phase1_concernFraming,
            MethodPhase::phase4_needs,
            MethodPhase::phase5_requirements,
            MethodPhase::phase10_vvEvidence
        );
        attribute :>> expectedArtifacts = (
            "DE4SDV_SoftwareUpdateReadinessFraming",
            "DE4SDV_SoftwareUpdateReadinessNeedsRequirements",
            "DE4SDV_SoftwareUpdateReadinessVerification"
        );
        attribute :>> expectedReviewEvidence = (
            "PR Method Check report on the exact PR head with 0 blocking gaps",
            "licensed Syside validation of the PR head"
        );
    }

    requirement softwareUpdateReadinessProblemStatement : ProblemStatement {
        doc /*
         * An OTA installation that starts while the vehicle is not secured, lacks
         * the energy to finish or roll back, or was not agreed by the driver can
         * immobilize the vehicle, surprise the driver, or brick the vehicle. The
         * vehicle needs one readiness check that gates the start of installation.
         */
        subject increment : SoftwareUpdateReadinessIncrement;
        stakeholder vehicleOwner : VehicleOwner;
        stakeholder updateCampaignOperator : UpdateCampaignOperator;
    }

    part updateReadinessQuestion : IncrementEngineeringQuestion {
        doc /*
         * Which vehicle preconditions must hold before an OTA installation may
         * start, and how is each precondition verified?
         */
    }

    part updateReadinessDecision : IncrementLifecycleDecision {
        doc /*
         * Approve the readiness-check requirements as design input for the
         * vehicle update client, with planned verification cases.
         */
    }

    part assumptionInstallationNeedsImmobilization : IncrementAssumption {
        doc /*
         * Installing the update makes the vehicle non-drivable for the duration
         * of the installation (no A/B partition switching while driving).
         */
    }

    part assumptionSignalsAvailable : IncrementAssumption {
        doc /*
         * Gear position, parking brake, vehicle speed and battery state of charge
         * are available to the update client with known freshness.
         */
    }

    part updateReadinessScope : IncrementScope {
        doc /*
         * The vehicle-side readiness check that runs after the package has been
         * downloaded and verified and before installation starts: parked state,
         * energy sufficiency, driver consent, and refusal reporting.
         */
    }

    part outOfScopeDownloadAndSecurity : OutOfScopeItem {
        doc /*
         * Package download, cryptographic verification, the backend campaign
         * logic, the installation itself and rollback execution are out of scope.
         * No regulatory compliance claim is made.
         */
    }

    // ---- Concern framed by a viewpoint of a view --------------------------------

    concern vehicleSafetyDuringUpdate {
        doc /*
         * An update must never start in a situation where the vehicle could move,
         * run out of energy mid-installation, or be updated against the driver's will.
         */
        stakeholder vehicleOwner : VehicleOwner;
        stakeholder updateCampaignOperator : UpdateCampaignOperator;
    }

    viewpoint def SoftwareUpdateReadinessViewpoint {
        doc /* Viewpoint for reviewing the preconditions that gate an OTA installation. */
    }

    view softwareUpdateReadinessView {
        doc /* Review view of the OTA readiness-check concern. */
        viewpoint updateReadinessViewpoint : SoftwareUpdateReadinessViewpoint {
            frame vehicleSafetyDuringUpdate;
        }
    }
}
