package DE4SDV_AEBSExecutionEnvironment {
  private import SAF_Viewpoints::*;
  private import DE4SDV_Stakeholders::*;
  private import Views::*;


  private import DE4SDV_AEBSSimulationDeployment::*;
  private import DE4SDV_ExecutionEnvironments::*;
  private import INCAEBS009AJetsonExecutionEnvironment;

  part def AEBMaintainedJetsonEnvironmentContext
    :> AEBTwoSystemSimulationDeployment {
    doc /*
     * Exact maintained System 2 environment context associated with
     * INC-AEBS-009A.
     *
     * The current maintained host is an NVIDIA Jetson Orin Nano Engineering
     * Reference Developer Kit Super (8 GiB class), running Ubuntu 22.04 with
     * Tegra kernel integration and native linux/arm64 OCI execution.
     *
     * Historical 009A runtime artifacts identify only a Jetson 8 GiB host;
     * they do not identify the exact SKU or prove identity continuity to this
     * post-merge snapshot. The two dependency sets preserve that boundary.
     * INC-AEBS-009C has merged bounded partial evidence. INC-AEBS-009B has
     * executed scenario evidence pending review and retains its own environment
     * and execution-identity trace; neither increment changes the 009A claim
     * boundary.
     */

    part executionEnvironment : INCAEBS009AJetsonExecutionEnvironment;
    bind candidateVehicleSystem1.host = executionEnvironment;

    part runtimeLockEvidence : TestedExecutionEnvironmentEvidence {
      doc /*
       * implementation/aebs-autoware-executable-bench/runtime-lock.yaml
       */
    }

    part containerIdentityEvidence : TestedExecutionEnvironmentEvidence {
      doc /*
       * implementation/aebs-autoware-executable-bench/evidence/container-identity.json
       */
    }

    part readinessEvidence : TestedExecutionEnvironmentEvidence {
      doc /*
       * implementation/aebs-autoware-executable-bench/evidence/readiness.json
       */
    }

    part environmentIdentityEvidence : InspectedExecutionEnvironmentEvidence {
      doc /*
       * implementation/aebs-autoware-executable-bench/evidence/execution-environment-snapshot.json
       * Post-merge host identity supplement; it does not rewrite historical
       * 009A runtime evidence.
       */
    }

    dependency historicalRuntimeEvidence
      from runtimeLockEvidence,
           containerIdentityEvidence,
           readinessEvidence
      to candidateVehicleSystem1;

    dependency maintainedHostIdentity
      from environmentIdentityEvidence
      to executionEnvironment;
  }

  concern physicalStructureConcern : PhysicalStructureConcern {
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder reviewer : OpenSourceReviewer;
  }

  concern argumentationAssuranceConcern : ArgumentationAssuranceConcern {
    doc /* Evidence-based assurance claims and their supporting argumentation. */
  }

  view aebsExecutionEnvironmentAssuranceView {
    viewpoint selectedArgumentationAssuranceViewpoint : ArgumentationAssuranceViewpoint {
      frame argumentationAssuranceConcern;
    }

    expose DE4SDV_AEBSExecutionEnvironment::*;
    render asTreeDiagram;
  }
}
