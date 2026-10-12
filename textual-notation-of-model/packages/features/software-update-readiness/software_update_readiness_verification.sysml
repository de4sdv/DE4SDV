package DE4SDV_SoftwareUpdateReadinessVerification {
    doc /*
     * Planned verification cases of INC-TEST-001, the pre-update vehicle
     * readiness check. Every case is planned and not executed; no result,
     * evidence or acceptance is claimed.
     *
     * THROWAWAY: method-loop test content, never merged.
     */

    private import DE4SDV_SoftwareUpdateReadinessFraming::*;
    private import DE4SDV_SoftwareUpdateReadinessNeedsRequirements::*;

    // The package holding the increment's verification cases references the increment usage.
    ref part verifiedIncrement references DE4SDV_SoftwareUpdateReadinessFraming::incTEST001;

    verification <'VC-TEST-001-01'> parkedStatePreconditionTest {
        doc /*
         * Bench test of the update client with simulated gear, parking-brake and
         * speed signals over all 16 combinations. Planned, not executed.
         */
        objective {
            verify reqParkedStatePrecondition;
        }
    }

    verification <'VC-TEST-001-02'> energyPreconditionAndRefusalTest {
        doc /*
         * Bench test with simulated low-voltage and traction battery state of
         * charge around the declared minimums, recording the display output and
         * the backend log for every refusal. Planned, not executed.
         */
        objective {
            verify reqEnergyPrecondition;
            verify reqRefusalReporting;
        }
    }

    verification <'VC-TEST-001-03'> consentPreconditionDemonstration {
        doc /*
         * Demonstration on a vehicle display mock-up: no consent, consent for a
         * different package version, expired consent, and valid consent.
         * Planned, not executed.
         */
        objective {
            verify reqConsentPrecondition;
        }
    }
}
