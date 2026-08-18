"""SAF GfSE viewpoint descriptions for viewer tooltips.

Sourced from the System Architecture Framework user documentation:
https://saf.gfse.org/userdoc/ — per-viewpoint "Purpose" sections.
Extracted 2026-08-18 from the `main` branch of saf.gfse.org.

Text is copied verbatim from the SAF userdoc (whitespace collapsed,
markdown list artifacts flattened). Viewpoints without a SAF page
(DE4SDV method-governance viewpoints) are intentionally absent; the
viewer falls back to model-derived information for those.
"""

SAF_VIEWPOINT_INFO: dict[str, str] = {
    "ArgumentationAssuranceViewpoint": (
        "The Argumentation Assurance Viewpoint presents claims backed up by "
        "arguments that are supported by evidence, together with the possibility "
        "to counter such claims in a similar manner."
    ),
    "OperationalCapabilityDefinitionViewpoint": (
        "The Operational Capability Definition Viewpoint defines a taxonomy of "
        "Capabilities from a Stakeholder's perspective including composition, "
        "specialization, and dependency relationships between Operational "
        "Capabilities."
    ),
    "OperationalContextDefinitionViewpoint": (
        "The Operational Context Definition Viewpoint provides the operational "
        "contexts and the involved operational performers necessary to support a "
        "specific set of operational capabilities."
    ),
    "OperationalStoryViewpoint": (
        "The Operational Story Viewpoint captures operational stories within "
        "operational contexts and their relation to operational performers, thus "
        "enables storytelling. It illustrates the operational background from the "
        "Stakeholder perspective, serves as starting point to identify "
        "Stakeholders and/or context elements, and fosters the communication "
        "among different Stakeholders."
    ),
    "PhysicalContextDefinitionViewpoint": (
        "The Physical Context Definition Viewpoint identifies the various "
        "contexts the SOI is used in, along with the associated external entities "
        "sharing a physical interface with the system. For each context, the "
        "applicable environmental conditions shall be defined. The physical "
        "context helps identify the interface requirements needed to integrate a "
        "system into its environment in a given context."
    ),
    "PhysicalContextExchangeViewpoint": (
        "The Physical Context Exchange Viewpoint focuses on the identification of "
        "the physical interfaces with external entities and relevant "
        "documentation. It is used to capture interface design requirements, "
        "applicable standards, protocols and format specifications, that are "
        "agreed upon the interfaces."
    ),
    "PhysicalInterfaceDefinitionViewpoint": (
        "The Physical Interface Definition Viewpoint captures definitions for "
        "physical interfaces. It allows to adopt long-lived standards and to "
        "harmonize physical interface definitions to improve interchangeability, "
        "interoperability, and portability."
    ),
    "PhysicalInternalExchangeViewpoint": (
        "The Physical Internal Exchange Viewpoint serves for the identification "
        "and definition of interfaces of elements of the physical system. also, "
        "the delegation of system element interfaces to the physical system "
        "boundary interfaces is covered."
    ),
    "PhysicalLogicalMappingViewpoint": (
        "The Physical Logical Mapping Viewpoint supports the definition of the "
        "realization of conceptual logical system elements by physical system "
        "elements comprising the SOI. Following the identification of physical "
        "system elements capable of performing the system functions of logical "
        "elements, the Physical Logical Mapping Viewpoint provides feedback to "
        "the System Architecture Definition process to consolidate or confirm the "
        "allocation, partitioning, and alignment of logical elements to physical "
        "elements that comprise the SOI."
    ),
    "PhysicalStructureDefinitionViewpoint": (
        "The Physical Structure Viewpoint is used to model the internal structure "
        "of the SOI and to identify the internal system elements making up the "
        "SOI. The SOI breakdown structure identifies system elements and finally "
        "at the implementation level hardware, software, and mechanics. The SOI "
        "breakdown structure determines items that are reused and make-or-buy "
        "(COTS) items."
    ),
    "StakeholderRequirementDefinitionViewpoint": (
        "The Stakeholder Requirement Definition Viewpoint specifies all "
        "capabilities, functions and properties, that the intended solution shall "
        "possess or expose from the perspective of the Stakeholders. The "
        "Stakeholder Requirement Definition Viewpoint also captures constraints "
        "for the system to be developed from stakeholders perspective."
    ),
    "SystemFunctionalBreakdownStructureViewpoint": (
        "The System Functional Breakdown Structure Viewpoint defines the "
        "structured, modular functional breakdown of the SOI beginning with "
        "System Processes, over identified System Functions further refined down "
        "to System Partial Functions. The reuse of System Functions, and System "
        "Partial Functions over Function Trees of the SOI is facilitated."
    ),
    "SystemFunctionMappingViewpoint": (
        "The System Function Mapping Viewpoint supports the definition of "
        "assignment of system functions (and their sub functions) to conceptual "
        "system elements."
    ),
    "SystemInterfaceDefinitionViewpoint": (
        "The System Interface Definition Viewpoint captures system wide concepts "
        "defining interfaces. It allows to adopt long-lived standards and to "
        "harmonize conceptual interface definitions to improve interchangeability, "
        "interoperability, and portability."
    ),
    "SystemInternalExchangeViewpoint": (
        "The System Internal Exchange Viewpoint serves for the identification "
        "and definition of interfaces of elements of the conceptual system. also, "
        "the delegation of system element interfaces to the conceptual system "
        "boundary interfaces is covered."
    ),
    "SystemRequirementDefinitionViewpoint": (
        "The System Requirement Definition Viewpoint specifies functions, "
        "non-functional properties, or constraints of the System. System "
        "Requirements are captured, the interrelationships between Functional and "
        "Non-Functional Requirements on the same level of abstraction and the "
        "traceability to Stakeholder Requirements are depicted."
    ),
    "SystemRequirementTraceabilityViewpoint": (
        "The System Requirement Traceability Viewpoint specifies for every System "
        "Requirement the traceability to the functional domain level: System Use "
        "Case, System Capability, System Context Definition, System Context "
        "Exchange, System Context Interaction, System Process, System State."
    ),
    "SystemStructureDefinitionViewpoint": (
        "The System Structure Definition Viewpoint describes how the system is "
        "decomposed into a hierarchical structure of conceptual elements. These "
        "conceptual system parts will be used to assign responsibilty to "
        "functions to them (divide & conquer principle). It covers related "
        "concepts and principles that define what the system does and is widely "
        "reusable among similar systems like product families, or product "
        "generations."
    ),
}
