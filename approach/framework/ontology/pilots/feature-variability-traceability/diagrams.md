# Ontology Pilot Diagrams

These Mermaid diagrams are intentionally lightweight. They are review artifacts,
not generated ontology output.

## Basic ontology modules

```mermaid
flowchart TD
    CORE[de4sdv-core]
    METHOD[de4sdv-sysmod-method]
    PL[de4sdv-product-line]
    REQ[de4sdv-requirements]
    ARCH[de4sdv-architecture]
    ASSURE[de4sdv-assurance]

    CORE --> METHOD
    CORE --> PL
    CORE --> REQ
    CORE --> ARCH
    CORE --> ASSURE
    METHOD --> PL
    METHOD --> REQ
    METHOD --> ARCH
    METHOD --> ASSURE
    PL --> REQ
    REQ --> ARCH
    ARCH --> ASSURE
```

## SYSMOD-style modeling chain

```mermaid
flowchart LR
    P[ProblemStatement]
    I[SystemIdea]
    O[SystemObjective]
    S[Stakeholder / Concern]
    R[Requirement / Constraint]
    C[ContextBoundary / ExternalActor]
    U[UseCase / Scenario]
    B[Process / Function]
    A[ArchitectureElement]
    E[VerificationCase / EvidenceArtifact]

    P --> I --> O --> S --> R --> C --> U --> B --> A --> E
```

## Feature vs common capability

```mermaid
flowchart TD
    PL[DE4SDV product line]
    BASE[BaseSDV member product]
    PREMIUM[PremiumSDV member product]
    CAP[OTAUpdateSupport
CommonCapability]
    FEAT[AutomaticRollbackForOTAUpdate
Feature]

    PL --> BASE
    PL --> PREMIUM
    BASE --> CAP
    PREMIUM --> CAP
    PREMIUM --> FEAT
    FEAT -. distinguishes from .-> BASE
```

## OTA rollback traceability slice

```mermaid
flowchart LR
    NEED[NEED-OTA-RECOVERABLE]
    FEAT[FEAT-OTA-ROLLBACK]
    REQ[REQ-OTA-ROLLBACK-001]
    ARCH[ARCH-ROLLBACK-MANAGER]
    EVID[EVID-ROLLBACK-FAILURE-INJECTION]
    CERT[CERT-OTA-RELEASE-EVIDENCE]

    NEED -->|derived feature| FEAT
    FEAT -->|specified by| REQ
    REQ -->|realized by| ARCH
    REQ -->|verified by| EVID
    FEAT -->|impacts| CERT
    EVID -->|supports| CERT
```

## Feature catalogue and bills-of-features

```mermaid
flowchart TD
    FC[Feature catalogue]
    F1[FEAT-OTA-ROLLBACK]
    C1[CONSTRAINT-ROLLBACK-REQUIRES-OTA]
    BOF_BASE[BOF-BASE-SDV]
    BOF_PREM[BOF-PREMIUM-SDV]
    BASE[BaseSDV]
    PREMIUM[PremiumSDV]

    FC --> F1
    FC --> C1
    BOF_BASE --> BASE
    BOF_PREM --> PREMIUM
    BOF_PREM --> F1
    C1 -->|requires| CAP[CAP-OTA-UPDATE]
```

## Shared asset superset and variation point

```mermaid
flowchart LR
    BOF[Bill of features]
    VP[VP-OTA-RECOVERY-BEHAVIOR]
    SAS_REQ[OTA requirements superset]
    SAS_ARCH[OTA architecture superset]
    PRODUCT[Product asset instances]

    BOF -->|feature selections| VP
    SAS_REQ --> VP
    SAS_ARCH --> VP
    VP -->|configured content| PRODUCT
```

## Future SysML v2 semantic stack

```mermaid
flowchart TD
    K[KerML semantic libraries]
    S[SysML v2 semantic libraries]
    D[DE4SDV product-line domain library]
    M[Semantic metadata / user-defined keywords]
    U[Concrete DE4SDV model usage]

    K --> S
    S --> D
    D --> M
    M --> U
    D --> U
```

Metadata and user-defined keywords are shown as shorthand over the domain
library, not as the source of semantics.

## Pilot quality gates

```mermaid
flowchart TD
    A[Candidate characteristic]
    B{Included in all member products?}
    C[Model as CommonCapability]
    D{Distinguishes at least one member product?}
    E[Model as Feature]
    F[Do not model as product-line feature yet]
    G{Has requirement / constraint?}
    H{Has planned or actual evidence?}
    I[Feature traceability acceptable for pilot]

    A --> B
    B -- yes --> C
    B -- no --> D
    D -- no --> F
    D -- yes --> E
    E --> G
    G -- no --> F
    G -- yes --> H
    H -- no --> F
    H -- yes --> I
```
