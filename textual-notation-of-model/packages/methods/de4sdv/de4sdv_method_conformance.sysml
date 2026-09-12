/* DE4SDV method-conformance kernel vocabulary (Lane B).
 *
 * Typed model-resident vocabulary for method-contract objects and
 * evaluation scopes, per the frozen conformance baseline (Sections 6-7)
 * and the accepted Package A specification (docs/method-conformance/).
 *
 * Representation decision (frozen baseline Section 7: "the first
 * implementation increment must choose and prove its native
 * representation"): the contract schema is materialized as model-resident
 * records — item definitions carrying typed attributes — so the contract
 * and the INC-AEBS-009D pilot scope are real API-queryable objects, not
 * prose. Every declaration here is classified in the ontology/kernel
 * contract (approach/framework/ontology/de4sdv-basic-ontology.yaml).
 *
 * Boundary: this file defines method vocabulary only. The concrete
 * INC-AEBS-009D pilot scope usage lives beside its verification slice in
 * the AEBS package; no phase-specific populations, thresholds, or
 * obligations live here.
 */
package DE4SDV_MethodConformance {

  private import ScalarValues::*;
  private import Metaobjects::SemanticMetadata;
  private import DE4SDV_MethodProcess::*;

  /* Evaluation-source kinds from the frozen baseline Section 7 schema:
     pinned model record | pinned repository artifact | live delivery adapter. */
  enum def EvaluationSourceKind {
    doc /* The kind of input an obligation reads: a pinned model record, a pinned
           repository artifact, or a live delivery adapter (outside deterministic
           V1 evaluation). */
    pinnedModelRecord {
      doc /* The obligation reads a pinned model record at the bound API revision. */
    }
    pinnedRepositoryArtifact {
      doc /* The obligation reads a pinned, digest-identified repository artifact. */
    }
    liveDeliveryAdapter {
      doc /* The obligation reads a live delivery projection; outside deterministic V1 evaluation. */
    }
  }

  /* One typed method-contract obligation. Attributes mirror the frozen
     baseline Section 7 schema exactly; status conditions bind to explicit
     allowed-value vocabularies (no example literals such as 'approved'). */
  item def MethodContractObligation {
    doc /* A typed model-resident method-contract obligation: stable explicit
           identifier, phase reference, typed subject selector, restricted
           applicability, population policy, pinned predicate with declared
           input/output types, target filters, per-subject cardinality bounds,
           requiredness, evaluation source, optional attestation-policy
           reference, and exact claim boundary. Model materialization of the
           frozen baseline Section 7 schema. */
    attribute obligationId : String;
    doc /* Stable explicit identifier; unique in the selected method. */
    attribute phase : MethodPhase;
    doc /* Reference to an existing MethodPhase literal; never a phase-specific Python branch. */
    attribute subjectSelector : String;
    doc /* Typed selection from the declared evaluation scope; no free-text inference. */
    attribute applicability : String;
    doc /* Restricted typed condition over pinned model/configuration data; empty means unconditional. */
    attribute minimumPopulation : Natural;
    attribute permittedEmpty : Boolean;
    doc /* Explicit permitted-empty disposition; an empty population without it is not a pass. */
    attribute predicate : String;
    doc /* Pinned ontology predicate identifier with declared input/output types. */
    attribute targetFilter : String;
    doc /* Typed conditions on returned targets, not implicitly on subjects. */
    attribute cardinalityMinimum : Natural;
    attribute cardinalityMaximum : Natural;
    doc /* Integer bounds over distinct qualifying targets per applicable subject. */
    attribute required : Boolean;
    doc /* Whether failure blocks this declared contract scope. */
    attribute evaluationSource : EvaluationSourceKind;
    attribute attestationPolicyRef : String;
    doc /* Policy identity required when acceptance/approval is part of the obligation; may be empty. */
    attribute claimBoundary : String;
    doc /* Exact claim supported when this obligation passes. */
  }

  /* An evaluation scope binds increment identity, root subjects with
     eligible types, population policy, and explicit exclusions with
     rationale (frozen baseline Section 6). Contribution set and evaluation
     scope are distinct sets. */
  part def MethodEvaluationScope {
    doc /* An evaluation scope binding increment identity, eligible subject types,
           and explicit exclusions. Contribution set and evaluation scope are
           distinct sets; membership in evaluation scope is a reviewed scope
           decision, not an inferred impact claim. */
    attribute incrementId : String;
    doc /* Owning increment identifier, e.g. an INC-<SUBJECT>-<SEQ> record identity. */
    attribute subjectType : String;
    doc /* Eligible subject API metaclass for this scope; subjects of other types are rejected. */
  }

  /* Explicit membership of one subject in an evaluation scope: the
     "contributes" relation of the frozen baseline Section 6. Membership in
     evaluation scope is a reviewed scope decision, not an inferred impact
     claim. */
  item def EvaluationScopeMembership {
    doc /* Explicit membership of one subject in an evaluation scope, carrying the
           contributes flag that separates the contribution set from reused
           evaluation-scope members. */
    attribute scopeId : String;
    doc /* Stable explicit identifier of the owning scope. */
    attribute subjectId : String;
    doc /* Stable explicit identifier (declaredShortName) of the subject element. */
    attribute contributes : Boolean;
    doc /* True when the increment introduces or changes the subject (contribution set); false for reused scope members. */
  }

  /* A candidate evaluation declares the tested scope it compares evidence
     against (provenance fingerprint fields from the retained records). */
  item def TestedScopeDeclaration {
    doc /* A candidate evaluation's declaration of the tested scope it compares
           retained evidence against: execution head and pinned profile
           identities (conservative scope-equality inputs). */
    attribute executionHead : String;
    doc /* Full Git SHA the retained execution records were produced at. */
    attribute profileIdentities : String;
    doc /* Comma-separated pinned profile identities of the declared tested scope. */
  }

  /* Reference to one retained execution record: explicit external identity
     with digest and provenance; bytes stay external. */
  item def RetainedExecutionRecordReference {
    doc /* A model-resident reference to one retained execution record with
           explicit external identity, artifact path, digest, and run identity;
           record bytes stay external. */
    attribute recordId : String;
    attribute artifactPath : String;
    attribute sha256 : String;
    attribute runId : String;
  }

  /* Reference to the authorization policy and, where present, the
     attributable acceptance decision. Policy status (proposed vs approved)
     is carried by the policy document, not by this reference. */
  item def AcceptanceAttestationReference {
    doc /* A model-resident reference to the authorization policy and the
           machine-declared decision-registry location. Policy status (proposed
           vs approved) is carried by the policy document, not by this reference;
           a missing registry and a known-empty registry are different states. */
    attribute policyRef : String;
    doc /* Resolvable policy identity; an unresolvable identity is a contract error downstream. */
    attribute decisionRegistryPath : String;
    doc /* Machine-declared decision-registry location; missing and known-empty registries are different states. */
  }

  doc /* Method-conformance vocabulary: model-resident contract objects so
       obligations, scopes, and evidence references are API-queryable at a
       bound revision. Phase-specific populations and thresholds are model
       data in feature slices, never Python constants. */
}
