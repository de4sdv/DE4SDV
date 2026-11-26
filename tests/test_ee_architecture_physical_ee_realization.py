"""Content pins for the E/E architecture physical E/E realization (phase 8, its first package), not semantic validation.

INC-EE-001 phase 8 realizes the vehicle network in two packages (owner decisions of 2026-11-26); this one is the E/E
realization: the nodes, the links and the frame on them, System 1 only. Method Check holds the
DefinePhysicalRealization rule (each logical element allocated to a physical allocation element; advisories, each
physical element carries a logical element, each crossing has a signal mapping with its semantic source). These pins
hold what the design settled on top of it:

- the topology of REQ-EE-001: the central computer, declared here as a vehicle compute node whose network side alone
  is an element of the vehicle network, two zone controllers, the Ethernet backbone, a CAN FD bus in each zone, the
  direct link, which is a CAN FD link, and the actuation ECU, with the vehicle as context;
- the placement: the network side carries the identity recorder and the command carrier, the zone controller of the
  actuation ECU's zone carries the command carrier, the actuation ECU carries the actuation end; these three are the
  only physical allocation elements, so the links, the other zone controller and its bus receive no allocation and
  the advisory reads the three alone;
- one CAN FD frame per driving command, which specializes the boundary item of phase 6 and adds the two
  DE4SDV_VSS_Extensions signals beside the inherited quantities; on the backbone it rides in an IEEE 1722 packet that
  holds it whole;
- the routes as connections from an out port to an in port of one item, and the other zone attached by ports that
  carry no item;
- no software element, no platform layer, no bench host and no relation of software to a node;
- seven signal mappings with complete records, REQ-EE-001 and REQ-EE-003 carried by two dependencies from the
  physical system, four comments on the framing's records and three gaps;
- three views, each framed by a concern of the Physical domain, three of them the phase 1 concerns;
- the texts of record of the design whole, and the guide's Phase 8 section block by block.
"""

from itertools import zip_longest
from pathlib import Path
import hashlib
import re

import pytest

from sysml_shapes import braced_body, strip_comments
from test_ee_architecture_framing import APPROVAL
from test_ee_architecture_functional_architecture import CLAUSE_NUMBER, PAST_BEHAVIOR

ROOT = Path(__file__).resolve().parents[1]
EE = ROOT / "textual-notation-of-model/packages/features/ee"
MODEL = EE / "ee_architecture_physical_ee_realization.sysml"
LOGICAL = EE / "ee_architecture_logical_architecture.sysml"
FRAMING = EE / "ee_architecture_framing.sysml"
NEEDS = EE / "ee_architecture_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_EEArchitecturePhysicalEERealization"
LOGICAL_PACKAGE = "DE4SDV_EEArchitectureLogicalArchitecture"
LOGICAL_SYSTEM = "EEVehicleNetworkLogicalSystem"
SYSTEM = "EEVehicleNetworkPhysicalSystem"
SYSTEM_USAGE = "eeVehicleNetworkPhysicalSystem"
CENTRAL = "EECentralComputer"

#: The three nodes that carry a logical element, the only physical allocation elements of the package, in order.
ELEMENT_DEFINITIONS = ['EECentralComputerNetworkSide', 'EEActuationZoneController', 'EEActuationECU']
#: The other part definitions: the central computer, the other zone controller, the links, the vehicle, the system.
NOT_ELEMENTS = ['EECentralComputer',
                'EEOtherZoneController',
                'EEEthernetBackbone',
                'EEActuationZoneCANFDBus',
                'EEOtherZoneCANFDBus',
                'EEDirectCANFDLink',
                'EEActuatedVehicle',
                'EEVehicleNetworkPhysicalSystem']
#: Each part definition -> what it specializes, as written (None: nothing), in the order of the file.
BASES = {'EECentralComputerNetworkSide': 'PhysicalAllocationElement',
          'EEActuationZoneController': 'PhysicalAllocationElement, VehicleComputeNode',
          'EEActuationECU': 'PhysicalAllocationElement, VehicleComputeNode',
          'EECentralComputer': 'VehicleComputeNode',
          'EEOtherZoneController': 'VehicleComputeNode',
          'EEEthernetBackbone': None,
          'EEActuationZoneCANFDBus': None,
          'EEOtherZoneCANFDBus': None,
          'EEDirectCANFDLink': None,
          'EEActuatedVehicle': None,
          'EEVehicleNetworkPhysicalSystem': None}
#: The nodes that software runs on, typed by the execution environments' VehicleComputeNode (lead default C9).
NODES = ["EEActuationZoneController", "EEActuationECU", "EECentralComputer", "EEOtherZoneController"]
TYPING = ("Its typing as a vehicle compute node of the execution environments claims no board, no operating system "
          "and no qualification.")
#: The links of the topology (the term Element of phase 5): they receive no allocation.
LINKS = ["EEEthernetBackbone", "EEActuationZoneCANFDBus", "EEOtherZoneCANFDBus", "EEDirectCANFDLink"]

#: Each part definition -> its own ports (name, port definition), in order.
PORTS = {'EECentralComputerNetworkSide': [('eeDrivingCommandIn', 'EEBoundaryCommandIn'),
                                          ('eeBackbonePacketOut', 'EECommandPacketOut'),
                                          ('eeDirectLinkFrameOut', 'EECommandFrameOut')],
         'EEActuationZoneController': [('eePacketIn', 'EECommandPacketIn'), ('eeFrameOut', 'EECommandFrameOut')],
         'EEActuationECU': [('eeZoneBusFrameIn', 'EECommandFrameIn'),
                            ('eeDirectLinkFrameIn', 'EECommandFrameIn'),
                            ('eeAppliedCommandOut', 'EEAppliedCommandOut')],
         'EECentralComputer': [('eeBackbonePacketOut', 'EECommandPacketOut'),
                               ('eeDirectLinkFrameOut', 'EECommandFrameOut')],
         'EEOtherZoneController': [('eeBackboneAttachment', 'EENetworkAttachment'),
                                   ('eeZoneBusAttachment', 'EENetworkAttachment')],
         'EEEthernetBackbone': [('eePacketIn', 'EECommandPacketIn'),
                                ('eePacketOut', 'EECommandPacketOut'),
                                ('eeOtherZoneAttachment', 'EENetworkAttachment')],
         'EEActuationZoneCANFDBus': [('eeFrameIn', 'EECommandFrameIn'), ('eeFrameOut', 'EECommandFrameOut')],
         'EEOtherZoneCANFDBus': [('eeZoneControllerAttachment', 'EENetworkAttachment')],
         'EEDirectCANFDLink': [('eeFrameIn', 'EECommandFrameIn'), ('eeFrameOut', 'EECommandFrameOut')],
         'EEActuatedVehicle': [('eeAppliedCommandIn', 'EEAppliedCommandIn')]}
#: Each container -> its parts (kind, name, type), in order.
PARTS = {'EECentralComputer': [('part', 'eeNetworkSide', 'EECentralComputerNetworkSide')],
         'EEVehicleNetworkPhysicalSystem': [('part', 'eeCentralComputer', 'EECentralComputer'),
                                            ('part', 'eeEthernetBackbone', 'EEEthernetBackbone'),
                                            ('part', 'eeActuationZoneController', 'EEActuationZoneController'),
                                            ('part', 'eeOtherZoneController', 'EEOtherZoneController'),
                                            ('part', 'eeActuationZoneCANFDBus', 'EEActuationZoneCANFDBus'),
                                            ('part', 'eeOtherZoneCANFDBus', 'EEOtherZoneCANFDBus'),
                                            ('part', 'eeDirectCANFDLink', 'EEDirectCANFDLink'),
                                            ('part', 'eeActuationECU', 'EEActuationECU'),
                                            ('part', 'eeActuatedVehicle', 'EEActuatedVehicle')]}
BINDS = {'EECentralComputer': [('eeBackbonePacketOut', 'eeNetworkSide.eeBackbonePacketOut'),
                               ('eeDirectLinkFrameOut', 'eeNetworkSide.eeDirectLinkFrameOut')],
         'EEVehicleNetworkPhysicalSystem': []}
CONNECTIONS = {'EECentralComputer': [],
               'EEVehicleNetworkPhysicalSystem': [('eeBackbonePacketFromCentralComputer',
                                                   'eeCentralComputer.eeBackbonePacketOut',
                                                   'eeEthernetBackbone.eePacketIn'),
                                                  ('eeBackbonePacketToActuationZone',
                                                   'eeEthernetBackbone.eePacketOut',
                                                   'eeActuationZoneController.eePacketIn'),
                                                  ('eeZoneBusFrameFromZoneController',
                                                   'eeActuationZoneController.eeFrameOut',
                                                   'eeActuationZoneCANFDBus.eeFrameIn'),
                                                  ('eeZoneBusFrameToActuationECU',
                                                   'eeActuationZoneCANFDBus.eeFrameOut',
                                                   'eeActuationECU.eeZoneBusFrameIn'),
                                                  ('eeDirectLinkFrameFromCentralComputer',
                                                   'eeCentralComputer.eeDirectLinkFrameOut',
                                                   'eeDirectCANFDLink.eeFrameIn'),
                                                  ('eeDirectLinkFrameToActuationECU',
                                                   'eeDirectCANFDLink.eeFrameOut',
                                                   'eeActuationECU.eeDirectLinkFrameIn'),
                                                  ('eeAppliedCommandToVehicle',
                                                   'eeActuationECU.eeAppliedCommandOut',
                                                   'eeActuatedVehicle.eeAppliedCommandIn'),
                                                  ('eeOtherZoneOnBackbone',
                                                   'eeEthernetBackbone.eeOtherZoneAttachment',
                                                   'eeOtherZoneController.eeBackboneAttachment'),
                                                  ('eeOtherZoneBusOnZoneController',
                                                   'eeOtherZoneController.eeZoneBusAttachment',
                                                   'eeOtherZoneCANFDBus.eeZoneControllerAttachment')]}
#: The item definitions -> (what each specializes, its own attributes (name, type)), and the packet's one item.
ITEMS = {"EECommandFrame": ("EEDrivingCommandInput",
                            [("eeSteeringAngleSignal", "Vehicle_ADAS_Driving_Command_SteeringAngle"),
                             ("eeAccelerationSignal", "Vehicle_ADAS_Driving_Command_Acceleration")]),
         "EECommandPacket": (None, [])}
PACKET_ITEM = ("eeCarriedFrame", "EECommandFrame")
#: Each port definition with an item -> (direction, item, type); the attachment carries none.
PORT_ITEMS = {'EEBoundaryCommandIn': ('in', 'eeDrivingCommand', 'DrivingCommandEventPayload'),
              'EECommandPacketOut': ('out', 'eeCommandPacket', 'EECommandPacket'),
              'EECommandPacketIn': ('in', 'eeCommandPacket', 'EECommandPacket'),
              'EECommandFrameOut': ('out', 'eeCommandFrame', 'EECommandFrame'),
              'EECommandFrameIn': ('in', 'eeCommandFrame', 'EECommandFrame'),
              'EEAppliedCommandOut': ('out', 'eeAppliedCommand', 'EEActuationOutput'),
              'EEAppliedCommandIn': ('in', 'eeAppliedCommand', 'EEActuationOutput')}
ATTACHMENT = "EENetworkAttachment"
#: (allocation, logical element, physical element under the usage)
ALLOCATIONS = [('eeRecorderToNetworkSide', 'eeIdentityRecorder', 'eeCentralComputer::eeNetworkSide'),
               ('eeCarrierToNetworkSide', 'eeCommandCarrier', 'eeCentralComputer::eeNetworkSide'),
               ('eeCarrierToActuationZoneController', 'eeCommandCarrier', 'eeActuationZoneController'),
               ('eeActuationEndToActuationECU', 'eeActuationEnd', 'eeActuationECU')]
#: (allocation, short name, record, logical element, target chain under the usage)
MAPPINGS = [('eeScoreCommandMapping',
             'MAP-EE-SCORE-COMMAND',
             'eeScoreCommandMappingRecord',
             'eeCommandCarrier',
             'eeCentralComputer.eeNetworkSide.eeDrivingCommandIn'),
            ('eeZoneRoutePacketMapping',
             'MAP-EE-ZONE-ROUTE-PACKET',
             'eeZoneRoutePacketMappingRecord',
             'eeCommandCarrier',
             'eeCentralComputer.eeNetworkSide.eeBackbonePacketOut'),
            ('eeZoneBusFrameMapping',
             'MAP-EE-ZONE-BUS-FRAME',
             'eeZoneBusFrameMappingRecord',
             'eeCommandCarrier',
             'eeActuationZoneController.eeFrameOut'),
            ('eeDirectLinkFrameMapping',
             'MAP-EE-DIRECT-LINK-FRAME',
             'eeDirectLinkFrameMappingRecord',
             'eeCommandCarrier',
             'eeCentralComputer.eeNetworkSide.eeDirectLinkFrameOut'),
            ('eeActuationFrameMapping',
             'MAP-EE-ACTUATION-FRAME',
             'eeActuationFrameMappingRecord',
             'eeActuationEnd',
             'eeActuationECU'),
            ('eeAppliedCommandMapping',
             'MAP-EE-APPLIED-COMMAND',
             'eeAppliedCommandMappingRecord',
             'eeActuationEnd',
             'eeActuationECU.eeAppliedCommandOut'),
            ('eeIdentityRecordMapping',
             'MAP-EE-IDENTITY-RECORD',
             'eeIdentityRecordMappingRecord',
             'eeIdentityRecorder',
             'eeCentralComputer.eeNetworkSide')]
RECORD_ATTRIBUTES = ('semanticSource',
                     'softwareContractArtifact',
                     'softwareContractMessage',
                     'softwareContractField',
                     'dataTypeAndUnit',
                     'timingQualityAndState',
                     'transformationRule',
                     'disposition',
                     'owner',
                     'nextAction',
                     'evidenceOrGap')
DEPENDENCIES = [('eePhysicalSystemCarriesBothRoutesInOneTopology', 'reqBothRoutesInOneTopology'),
                ('eePhysicalSystemCarriesCommandsOnlyOnTheirRoute', 'reqCommandsOnlyOnTheirRoute')]
COMMENTS = {'eePhase8ActuationEndPlaced': 'gapEEActuationEnd',
            'eePhase8StackBoundaryPartlySettled': 'gapEEStackAndNetworkBoundary',
            'eePhase8BoundaryInterfacePlaced': 'asmEEScoreCommandSource',
            'eePhase8TestbedQuestionsAsked': 'gapEEBenchPlatform'}
GAPS = ['gapEECentralComputerHandover', 'gapEEConfigurationNamedByRole', 'gapEENodeSoftwareOpen']
NOTES = ['The route through a zone controller.',
         'The direct route.',
         'The applied command, to the vehicle.',
         'The other zone, on neither route: attachments that carry no item.']
HEADINGS = ['─── The items on the links ───',
            '─── The ports: one item each, and the attachment that carries none ───',
            '─── The nodes that carry the logical elements ───',
            '─── The central computer and the other zone controller ───',
            '─── The links: they carry the frame and compute nothing ───',
            '─── The vehicle, as context ───',
            '─── The vehicle network ───',
            '─── Logical-to-physical allocations (allocatedTo) ───',
            '─── The topology and route requirements, carried by the realization that places the routes ───',
            '─── Signal mappings: one per crossing, each with its record ───',
            "─── What phase 8 settled on the framing's records ───",
            '─── The gaps of the realization ───',
            '─── Concerns and views of the phase ───']

STRUCTURE_VIEW = "eeVehicleNetworkPhysicalStructureView"
MATRIX_VIEW = "eeVehicleNetworkPhysicalLogicalMappingView"
PATH_VIEW = "eeVehicleNetworkRouteExchangeView"
#: view -> (type, render, exposes, viewpoint definition, frames)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;", ['eeVehicleNetworkPhysicalSystem',
                      'eeVehicleNetworkPhysicalSystem::eeCentralComputer',
                      'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide',
                      'eeVehicleNetworkPhysicalSystem::eeEthernetBackbone',
                      'eeVehicleNetworkPhysicalSystem::eeActuationZoneController',
                      'eeVehicleNetworkPhysicalSystem::eeOtherZoneController',
                      'eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus',
                      'eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus',
                      'eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink',
                      'eeVehicleNetworkPhysicalSystem::eeActuationECU',
                      'eeVehicleNetworkPhysicalSystem::eeActuatedVehicle'], "PhysicalStructureDefinitionViewpoint",
                     ["eeTopologyStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{LOGICAL_SYSTEM}::{e}" for e in ("eeIdentityRecorder", "eeCommandCarrier", "eeActuationEnd")]
                  + [f"{SYSTEM_USAGE}::{e}" for e in ("eeCentralComputer::eeNetworkSide", "eeActuationZoneController",
                                                        "eeActuationECU")] + [f"{PACKAGE}::*"],
                  "PhysicalLogicalMappingViewpoint", ["eeVehicleNetworkPhysicalAllocationConcern"]),
    PATH_VIEW: (None, "render asInterconnectionDiagram;", ['eeVehicleNetworkPhysicalSystem',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeBackbonePacketOut',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeDirectLinkFrameOut',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDrivingCommandIn',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeBackbonePacketOut',
                 'eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDirectLinkFrameOut',
                 'eeVehicleNetworkPhysicalSystem::eeEthernetBackbone',
                 'eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketIn',
                 'eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketOut',
                 'eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eeOtherZoneAttachment',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneController',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eePacketIn',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eeFrameOut',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneController',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeBackboneAttachment',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeZoneBusAttachment',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameIn',
                 'eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameOut',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus::eeZoneControllerAttachment',
                 'eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink',
                 'eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameIn',
                 'eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameOut',
                 'eeVehicleNetworkPhysicalSystem::eeActuationECU',
                 'eeVehicleNetworkPhysicalSystem::eeActuationECU::eeZoneBusFrameIn',
                 'eeVehicleNetworkPhysicalSystem::eeActuationECU::eeDirectLinkFrameIn',
                 'eeVehicleNetworkPhysicalSystem::eeActuationECU::eeAppliedCommandOut',
                 'eeVehicleNetworkPhysicalSystem::eeActuatedVehicle',
                 'eeVehicleNetworkPhysicalSystem::eeActuatedVehicle::eeAppliedCommandIn',
                 'eeVehicleNetworkPhysicalSystem::eeBackbonePacketFromCentralComputer',
                 'eeVehicleNetworkPhysicalSystem::eeBackbonePacketToActuationZone',
                 'eeVehicleNetworkPhysicalSystem::eeZoneBusFrameFromZoneController',
                 'eeVehicleNetworkPhysicalSystem::eeZoneBusFrameToActuationECU',
                 'eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameFromCentralComputer',
                 'eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameToActuationECU',
                 'eeVehicleNetworkPhysicalSystem::eeAppliedCommandToVehicle',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneOnBackbone',
                 'eeVehicleNetworkPhysicalSystem::eeOtherZoneBusOnZoneController'],
                "PhysicalInternalExchangeViewpoint", ["eeCommandRouteExchangeConcern", "eeCommandItemConcern"]),
}
VIEW_FILTERS = {STRUCTURE_VIEW: ["not (@ SysML::AllocationUsage)", "not (@ SysML::BindingConnectorAsUsage)"],
                MATRIX_VIEW: [],
                PATH_VIEW: ["not (@ SysML::AllocationUsage)", "not (@ SysML::InterfaceUsage)"]}
#: the Phase 1 concerns of the Physical domain, framed here and never redeclared
FRAMING_CONCERNS = {"eeTopologyStructureConcern": "PhysicalStructureConcern",
                    "eeCommandItemConcern": "PhysicalLogicalItemMappingConcern",
                    "eeCommandRouteExchangeConcern": "PhysicalInternalExchangeConcern"}
CATALOGUE_CONCERNS = {"eeVehicleNetworkPhysicalAllocationConcern": ("PhysicalLogicalMappingConcern",
                                                                    ["SystemArchitect", "VerificationEngineer"])}
GRID = ("Vehicle network logical-to-physical mapping",
        "Maps the three logical elements of the vehicle network to the three nodes that carry them.",
        "logical elements (part usages)", "nodes (part usages)")
IMPORTS = ['DE4SDV_MethodContext::*',
           'DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate',
           'DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord',
           'DE4SDV_MethodProcess::SignalMappingDisposition',
           'DE4SDV_TraceVocabulary::PhysicalAllocationElement',
           'DE4SDV_ExecutionEnvironments::VehicleComputeNode',
           'DE4SDV_DriverAssistancePhysicalSoftwareRealization::DrivingCommandEventPayload',
           'DE4SDV_EEArchitectureFraming::gapEEActuationEnd',
           'DE4SDV_EEArchitectureFraming::gapEEStackAndNetworkBoundary',
           'DE4SDV_EEArchitectureFraming::gapEEBenchPlatform',
           'DE4SDV_EEArchitectureFraming::asmEEScoreCommandSource',
           'DE4SDV_EEArchitectureFraming::eeTopologyStructureConcern',
           'DE4SDV_EEArchitectureFraming::eeCommandItemConcern',
           'DE4SDV_EEArchitectureFraming::eeCommandRouteExchangeConcern',
           'DE4SDV_EEArchitectureFunctionalArchitecture::EEDrivingCommandInput',
           'DE4SDV_EEArchitectureFunctionalArchitecture::EEActuationOutput',
           'DE4SDV_EEArchitectureLogicalArchitecture::EEVehicleNetworkLogicalSystem',
           'DE4SDV_EEArchitectureNeedsRequirements::reqBothRoutesInOneTopology',
           'DE4SDV_EEArchitectureNeedsRequirements::reqCommandsOnlyOnTheirRoute',
           'DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_Acceleration',
           'DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_SteeringAngle',
           'DE4SDV_Stakeholders::*',
           'SAF_Viewpoints::*',
           'SysideViews::**',
           'Views::*']
#: the private findings and the banned words, by digest only (none appears in a text of record or here)
PRIVATE_SHA256 = ['00a6009aac697f11c40fb11836ef5cb762f766b2604b66ad25dfafeba3251497',
                  '06a8d99fc6930dbf638ca0330c53a435b63c9541957cf9b7a237c336916c5f81',
                  '076caf869ac583da990536f15abd486cc2a38fc164800596f22c59aabe80fd82',
                  '14394147eaee8ab3a925d48241041396a890182d7a1a954faa496107141c45c8',
                  '24a4d4ed69b194c6641bd327c35a3a27542fd479e3ef2de2c99d9e4582e47773',
                  '407b9ca1039b3dda2c236a8df223d24524fdd44bc59f17da04c73bb211592291',
                  '47575d8bac2a4c68259173c8c0431bdcf58a6677c006b68f75a3f7834dea7b49',
                  '4992854f5d6b980444860d82aed38cbd3f5bfa4c1e0fb73d68c502f1a3e97f43',
                  '647d177cca8601046a3cb39e12f55bec5790bfcbc42199dd5fcf063200fac1d0',
                  '7346bd6ba3cd8945fbea3fac13ec248664f92505340c74dbb934a6774db02f13',
                  '899095c9adf5fcf0432c83e56f45279eafdd842fb3972028f5ff0c455d2f37c6',
                  '8ee529e32615c5ffbc12292550b2ef0f062dcb96e6b57b8f317dc8e6b8cbe8e1',
                  '925733dafd743699fa17409329abdb2728da89ba5736e44ad0fd4a67836e9f9c',
                  '9fb01f36a0018f5dbb083dc6794bb43ad56051c7255381ebdb14c78808eb68cc',
                  'aa7dbb5867d7c5769df8c27559cb3130cc0fd8cb4380c9d85ca1aa31c636e988',
                  'ac203c9843b5bd8c883e07039ff82820c94422010be6108bb82403ca25376a22',
                  'ae94da4c1a6fabab4512e07bd7f597adec85b16c801a4b69251f9c4165010495',
                  'b4b33d2441645d4dd0a0694b5989a0a14a5cc22fe9865e6b7b7eae966e0de36c',
                  'c9a19b5ab6a7f7dbc870c590582418898b6107e6f1e1844aef5647c70f27c98d',
                  'd5c685f25c91f309b6af96c14cd1dc55139184d1153ae51b18c8593a0d69d8c0',
                  'e6b063ad39251eea5286e279d019dee4020e9e99345158198d58d1a6923461de',
                  'ecb53f367b3541da3a14236d9a091f9bcc7a9903953f36577c2664fdd2a68a55',
                  'ed7aa50d187fda240b52d794e3fb9fea08dc8b2c45ba3aeeae7e9c4ea3aefd5a',
                  'ee0877bfa744df6fc391102c3d018c7969f799d31bbc28d83d18a60cb1cd00ed']
#: the bench and System 2 appear only in sentences of these forms
STAND_IN = ("stands in", "stand in for", "the testbed stays to be chosen", "This realization asks of it",
            "System 2 only reads", "that the bench has shown anything",
            "No part here stands for an element of the bench", "is System 2", "is a question for Phase 10",
            "the testbed with its readiness probe")

HEADER_PARAGRAPHS = ['DE4SDV E/E architecture physical E/E realization.',
                     'INC-EE-001, phase 8: the E/E realization of the vehicle network. Which nodes and links of the '
                     'vehicle network realize the three logical elements of phase 7, and what carries each driving '
                     'command on each route from the network side of the central computer to the actuation ECU?',
                     'The realization (owner decisions of 2026-11-26):',
                     '- Phase 8 realizes the vehicle network in two packages: this E/E realization of its nodes, its '
                     'links and the frame on them, and a software realization of the software of each node, which '
                     'follows a change to the method that relates software to a node. This package places no '
                     'software. - The network side of the central computer takes each driving command from the '
                     'Eclipse S-CORE path and puts it, with its three detection parts, into one CAN FD frame. No '
                     'vehicle signal broker and no other element sits between the take and the frame. - Each driving '
                     'command is one CAN FD frame, which the network side builds. On the route through a zone '
                     'controller the frame goes over the Ethernet backbone inside an IEEE 1722 packet, and the zone '
                     "controller of the actuation ECU's zone unpacks it onto the CAN FD bus of its zone and repacks "
                     'nothing. On the direct route the same frame goes over a CAN FD link to the actuation ECU. The '
                     'actuation ECU gets the same bytes on both routes, so the design keeps each part unchanged '
                     '(REQ-EE-004) and has each element pass the detection parts on as it received them '
                     '(REQ-EE-007).',
                     'What follows from the phase 7 elements and the defaults of this phase:',
                     '- Topology: the one topology of REQ-EE-001, with the central computer, two zone controllers, '
                     'the Ethernet backbone between the central computer and the zone controllers, a CAN FD bus in '
                     'each zone, and the direct link, which passes no zone controller, to the actuation ECU. Of the '
                     'central computer only its network side is an element of the vehicle network; the command '
                     'source and the Eclipse S-CORE path on it are outside. The central computer, the two zone '
                     'controllers and the actuation ECU are typed as vehicle compute nodes, a typing that claims no '
                     'board, no operating system and no qualification; the links are not. The central computer is '
                     'declared here, and the realization of the HMI display keeps its own declaration of it until '
                     'software can be placed on a node (gapEECentralComputerHandover). - Placement: the network side '
                     'carries the identity recorder and the command carrier, the zone controller of the actuation '
                     "ECU's zone carries the command carrier, and the actuation ECU carries the actuation end. The "
                     'links carry the frame, compute nothing and receive no allocation; the signal mappings name '
                     'them. The other zone controller and its CAN FD bus lie on neither route and carry no logical '
                     "element. - Time: the network side reads the vehicle's clock when it takes a driving command, "
                     'and the actuation ECU reads it when one arrives; no other element of the vehicle network reads '
                     "a clock for the command. The vehicle's clock is one time base that the central computer and "
                     'the actuation ECU share; the source sets the issue time on it too, so the check of the issue '
                     'time and the 50 ms of REQ-EE-005 rest on the two nodes reading the same time. How the nodes '
                     'share it, time synchronisation between them, stays out of scope (eeTimingOutOfScope). On the '
                     "bench the testbed's simulation clock, one clock for every element, stands in for the vehicle's "
                     'clock. - VSS at the frame: the steering angle and the acceleration of the frame are typed by '
                     'the two DE4SDV_VSS_Extensions command signals of the driving increments, beside the quantities '
                     'of phase 6 that the frame inherits. The issue time, the sequence count and the check value are '
                     'protocol fields, no vehicle signal. No VSS extension is added. - Configuration: the files that '
                     'REQ-EE-010 reads are named by role: the frame layout, the routing entry of the zone controller '
                     'and the route setting; their paths come with the implementation '
                     '(gapEEConfigurationNamedByRole).',
                     'Alternatives recorded and not selected:',
                     '- ALT-EE-VSSBROKER-001: the driving command through a vehicle signal broker on the central '
                     'computer, from which a provider builds the frame. The three detection parts are no vehicle '
                     'signal, so they would cross the broker as signals that they are not, or be computed anew after '
                     'it, which REQ-EE-007 does not allow; and no requirement of this increment asks for what a '
                     'broker adds. - ALT-EE-SIGNALGATEWAY-001: the backbone carries the driving command as an '
                     'Ethernet service message, and the zone controller builds a new CAN FD frame from it. The zone '
                     'controller would encode each part anew, its check value with them, which REQ-EE-007 does not '
                     'allow. - ALT-EE-CLASSICALCAN-001: classical CAN, more than one frame per driving command, '
                     'which the actuation ECU joins again. The sequence count and the check value alone fill the '
                     'data of one classical CAN frame.',
                     'The network side of the central computer, the Ethernet backbone, the two zone controllers, the '
                     'CAN FD bus of each zone, the direct link and the actuation ECU are inside the vehicle network; '
                     'the rest of the central computer and the vehicle are outside it, and the testbed that stands '
                     'in for them is System 2. An allocation here is a responsibility assignment, no deployment, '
                     'execution or runtime claim; a signal mapping is no interoperability claim. Nothing in this '
                     'package claims that a requirement is met, that a case ran or that the bench has shown '
                     'anything.']
DOCS = {'item def EECommandFrame :> EEDrivingCommandInput': 'The driving command as the realization types it on the '
                                                            'links: one CAN FD frame per driving command, which the '
                                                            'network side of the central computer builds from the '
                                                            'parts as it takes them, and which reaches the actuation '
                                                            'ECU with the same bytes on both routes. It keeps the '
                                                            'five parts of the boundary item of phase 6 as it '
                                                            'inherits them: the steering angle, the acceleration, '
                                                            'and the issue time, the sequence count and the check '
                                                            'value, the detection parts. Beside the inherited '
                                                            'steering angle and acceleration it carries their values '
                                                            'typed by the two DE4SDV_VSS_Extensions command signals: '
                                                            'eeSteeringAngleSignal, the value in degrees of the '
                                                            'inherited steeringAngle, positive to the left, and '
                                                            'eeAccelerationSignal, the value in m/s² of the '
                                                            'inherited acceleration, negative to decelerate. The '
                                                            "issue time counts in seconds on the vehicle's clock, "
                                                            'the sequence count is an unsigned 32-bit count from 1 '
                                                            'in each run, and the check value is the CRC-32 over the '
                                                            'other parts; these three are protocol fields, no '
                                                            'vehicle signal. The five parts fit the data of one CAN '
                                                            "FD frame; the frame's identifier and the layout of its "
                                                            'bytes are set by the frame layout of the configuration '
                                                            '(gapEEConfigurationNamedByRole).',
        'item def EECommandPacket': 'The packet in which the Ethernet backbone carries the command frame from the '
                                    'network side of the central computer to the zone controller of the actuation '
                                    "ECU's zone: an IEEE 1722 packet, which carries a CAN frame over Ethernet as one "
                                    'encapsulated bus frame (upstream.md). It holds the one CAN FD frame as the '
                                    'network side built it. Nothing in the packet changes or adds a part of the '
                                    'driving command. Its stream and its address are set by the frame layout of the '
                                    'configuration (gapEEConfigurationNamedByRole). A frame of the vehicle network, '
                                    'no vehicle signal (MAP-EE-ZONE-ROUTE-PACKET).',
        'port def EEBoundaryCommandIn': 'The boundary interface of the vehicle network: each driving command as the '
                                        'mw::com event of the driver-assistance increment gives it to the network '
                                        'side of the central computer.',
        'port def EECommandPacketOut': 'The command packet leaving an element onto the Ethernet backbone, or the '
                                       'backbone towards a zone controller.',
        'port def EECommandPacketIn': 'The command packet entering the Ethernet backbone or the zone controller of '
                                      "the actuation ECU's zone.",
        'port def EECommandFrameOut': 'The command frame leaving an element onto a CAN FD bus or the direct link, or '
                                      'such a link towards a node.',
        'port def EECommandFrameIn': 'The command frame entering a CAN FD bus, the direct link or the actuation ECU.',
        'port def EEAppliedCommandOut': 'The applied steering angle and acceleration leaving the actuation ECU for '
                                        'the vehicle.',
        'port def EEAppliedCommandIn': "The applied steering angle and acceleration entering the vehicle's steering, "
                                       'drive and brakes.',
        'port def EENetworkAttachment': 'The attachment of the other zone controller to a link, which carries no '
                                        'item of the vehicle network: neither route passes it.',
        'part def EECentralComputerNetworkSide :> PhysicalAllocationElement': 'Carries the identity recorder and the '
                                                                              'command carrier of phase 7: the '
                                                                              'network side of the central computer, '
                                                                              'the element of the vehicle network on '
                                                                              'that computer. Its boundary interface '
                                                                              'is the port at which it takes each '
                                                                              'driving command from the Eclipse '
                                                                              'S-CORE path on the central computer '
                                                                              '(asmEEScoreCommandSource), as the '
                                                                              'mw::com event of the '
                                                                              'driver-assistance increment gives it; '
                                                                              'it takes driving commands from '
                                                                              'nowhere else (REQ-EE-002). When it '
                                                                              'takes a driving command it reads the '
                                                                              "vehicle's clock. It puts the five "
                                                                              'parts, as it takes them, into one CAN '
                                                                              'FD frame and computes none of the '
                                                                              'detection parts anew (REQ-EE-007); no '
                                                                              'element sits between the take and the '
                                                                              'frame (owner decision of 2026-11-26). '
                                                                              'By the route of the run, which the '
                                                                              'route setting of the configuration '
                                                                              'sets, it sends the frame on the '
                                                                              'direct link, or inside an IEEE 1722 '
                                                                              'packet on the Ethernet backbone. '
                                                                              'Before it takes the first driving '
                                                                              'command of each run, it records the '
                                                                              'network identity as the term of phase '
                                                                              '5 names it (REQ-EE-010): the route of '
                                                                              'the run, the commit with its '
                                                                              'difference, the SHA-256 of each file '
                                                                              'of the configuration and each setting '
                                                                              'read from outside a file. The record '
                                                                              'is a self-report of System 1, a file '
                                                                              'of the run that System 2 only reads. '
                                                                              'Its software comes with the software '
                                                                              'realization (gapEENodeSoftwareOpen). '
                                                                              'On the bench a node of the testbed '
                                                                              'stands in for it.',
        'part def EEActuationZoneController :> PhysicalAllocationElement, VehicleComputeNode': 'Carries the command '
                                                                                               'carrier of phase 7 '
                                                                                               'on the route through '
                                                                                               'a zone controller: '
                                                                                               'the zone controller '
                                                                                               'of the actuation '
                                                                                               "ECU's zone, a "
                                                                                               'gateway between the '
                                                                                               'Ethernet backbone '
                                                                                               'and the CAN FD bus '
                                                                                               'of its zone. It '
                                                                                               'takes each IEEE 1722 '
                                                                                               'packet of the '
                                                                                               "command's stream "
                                                                                               'from the backbone '
                                                                                               'and puts the frame '
                                                                                               'that the packet '
                                                                                               'holds onto the CAN '
                                                                                               'FD bus of its zone '
                                                                                               'as it is, by its '
                                                                                               'routing entry of the '
                                                                                               'configuration. It '
                                                                                               'unpacks the frame '
                                                                                               'and repacks nothing, '
                                                                                               'so it gives the '
                                                                                               'actuation ECU the '
                                                                                               'bytes that the '
                                                                                               'network side built '
                                                                                               'and computes no '
                                                                                               'detection part anew '
                                                                                               '(REQ-EE-007). It '
                                                                                               'reads no clock for '
                                                                                               'the driving command. '
                                                                                               'Its typing as a '
                                                                                               'vehicle compute node '
                                                                                               'of the execution '
                                                                                               'environments claims '
                                                                                               'no board, no '
                                                                                               'operating system and '
                                                                                               'no qualification. '
                                                                                               'Its software comes '
                                                                                               'with the software '
                                                                                               'realization '
                                                                                               '(gapEENodeSoftwareOpe'
                                                                                               'n). '
                                                                                               'On the bench a node '
                                                                                               'of the testbed '
                                                                                               'stands in for it.',
        'part def EEActuationECU :> PhysicalAllocationElement, VehicleComputeNode': 'Carries the actuation end of '
                                                                                    'phase 7: the actuation ECU on '
                                                                                    'the CAN FD bus of its zone and '
                                                                                    'at the end of the direct link, '
                                                                                    'the last element that a driving '
                                                                                    'command reaches on both routes. '
                                                                                    'It takes each command frame '
                                                                                    'from the CAN FD bus of its zone '
                                                                                    'or from the direct link, by the '
                                                                                    'route of the run, and reads the '
                                                                                    "vehicle's clock when one "
                                                                                    'arrives. It judges each by the '
                                                                                    'term valid driving command: its '
                                                                                    'check value over the other '
                                                                                    'parts as they arrive, its '
                                                                                    'sequence count against the '
                                                                                    'reference count, and its issue '
                                                                                    'time against the time of its '
                                                                                    'arrival. It applies each valid '
                                                                                    'one and nothing in place of an '
                                                                                    'invalid one, gives the vehicle '
                                                                                    'the steering angle and the '
                                                                                    'acceleration of the last valid '
                                                                                    'driving command that it '
                                                                                    'applied, and gives the stop '
                                                                                    'response once more than 200 ms '
                                                                                    'pass on that clock with no '
                                                                                    'valid driving command reaching '
                                                                                    'it (REQ-EE-006, REQ-EE-008, '
                                                                                    'REQ-EE-009). The stop response '
                                                                                    'needs no vehicle speed. How it '
                                                                                    'turns the steering angle and '
                                                                                    'the acceleration into the '
                                                                                    "set-points of the vehicle's "
                                                                                    'actuators is set with its '
                                                                                    'software '
                                                                                    '(gapEENodeSoftwareOpen). Its '
                                                                                    'typing as a vehicle compute '
                                                                                    'node of the execution '
                                                                                    'environments claims no board, '
                                                                                    'no operating system and no '
                                                                                    'qualification. On the bench a '
                                                                                    'node of the testbed stands in '
                                                                                    'for it.',
        'part def EECentralComputer :> VehicleComputeNode': 'The central computer of the vehicle, declared here as a '
                                                            'node of the vehicle network. Its typing as a vehicle '
                                                            'compute node of the execution environments claims no '
                                                            'board, no operating system and no qualification. No '
                                                            'platform layer is claimed either. Of it only its '
                                                            'network side is an element of the vehicle network; the '
                                                            'rest of the computer, where the command source and the '
                                                            'Eclipse S-CORE path run, lies outside the boundary and '
                                                            'holds no part here. Its two ports, to the Ethernet '
                                                            'backbone and to the direct link, are those of its '
                                                            'network side, to which they are bound. The software '
                                                            'that it runs and the layers that it runs on come with '
                                                            'the software realization (gapEENodeSoftwareOpen). The '
                                                            'realization of the HMI display declares the same '
                                                            'computer for its own needs '
                                                            '(gapEECentralComputerHandover). On the bench a host of '
                                                            'the testbed stands in for it.',
        'part def EEOtherZoneController :> VehicleComputeNode': 'The zone controller of the other zone: a gateway '
                                                                'between the Ethernet backbone and the CAN FD bus of '
                                                                'its zone, as the topology of REQ-EE-001 holds it. '
                                                                'Neither route passes it, so it carries no logical '
                                                                'element: the backbone gives it no command packet, '
                                                                'and its attachments to the backbone and to the CAN '
                                                                'FD bus of its zone carry no item of the vehicle '
                                                                'network (REQ-EE-003). Its typing as a vehicle '
                                                                'compute node of the execution environments claims '
                                                                'no board, no operating system and no qualification. '
                                                                'On the bench a node of the testbed stands in for '
                                                                'it.',
        'part def EEEthernetBackbone': 'The Ethernet backbone between the central computer and the two zone '
                                       'controllers, a link of the vehicle network on the route through a zone '
                                       "controller. It carries each IEEE 1722 packet of the command's stream from "
                                       'the network side of the central computer to the zone controller of the '
                                       "actuation ECU's zone, as the network side sent it, and computes nothing: it "
                                       'changes no part of the driving command and computes none (REQ-EE-007). To '
                                       'the other zone controller it carries no command packet: the destination '
                                       "address of the command's stream, which the frame layout of the configuration "
                                       "sets, names only the zone controller of the actuation ECU's zone. It "
                                       'receives no allocation; the mapping of the route through a zone controller '
                                       'names it (MAP-EE-ZONE-ROUTE-PACKET). On the bench a virtual link of the '
                                       'testbed stands in for it.',
        'part def EEActuationZoneCANFDBus': "The CAN FD bus of the actuation ECU's zone, a link of the vehicle "
                                            'network on the route through a zone controller. It carries each command '
                                            'frame from the zone controller of its zone to the actuation ECU as the '
                                            'zone controller put it on the bus, and computes nothing (REQ-EE-007). '
                                            "It receives no allocation; the mapping of the zone's bus names it "
                                            '(MAP-EE-ZONE-BUS-FRAME). On the bench a virtual CAN FD bus of the '
                                            'testbed stands in for it.',
        'part def EEOtherZoneCANFDBus': 'The CAN FD bus of the other zone, a link of the topology that REQ-EE-001 '
                                        'holds. Neither route passes it: it carries no item of the vehicle network '
                                        'and receives no allocation. On the bench a virtual CAN FD bus of the '
                                        'testbed stands in for it.',
        'part def EEDirectCANFDLink': 'The direct link from the central computer to the actuation ECU, which passes '
                                      'no zone controller: a CAN FD link, the medium that phase 8 decides for it '
                                      '(owner decision of 2026-11-26). It carries each command frame from the '
                                      'network side of the central computer to the actuation ECU as the network side '
                                      'sent it, and computes nothing (REQ-EE-007). It receives no allocation; the '
                                      'mapping of the direct route names it (MAP-EE-DIRECT-LINK-FRAME). On the bench '
                                      'a virtual CAN FD link of the testbed stands in for it.',
        'part def EEActuatedVehicle': 'The vehicle that the actuation ECU drives, as context: its steering, drive '
                                      'and brakes take the steering angle and the acceleration that the actuation '
                                      "ECU applies, and send nothing back. It realizes the context's vehicle so that "
                                      'the applied command has an end; it is no element of the vehicle network and '
                                      'carries no logical element. On the bench the vehicle model of the testbed '
                                      'stands in for it.',
        'part def EEVehicleNetworkPhysicalSystem': 'The physical realization of the vehicle network in the vehicle: '
                                                   'the central computer with its network side, the Ethernet '
                                                   'backbone, the two zone controllers, the CAN FD bus of each zone, '
                                                   'the direct link and the actuation ECU, in the one topology of '
                                                   'REQ-EE-001, with the vehicle that the actuation ECU drives as '
                                                   'context. Of the central computer only its network side is an '
                                                   'element of the vehicle network. Each driving command is one CAN '
                                                   'FD frame: on the route through a zone controller it goes from '
                                                   'the network side over the Ethernet backbone inside an IEEE 1722 '
                                                   "packet to the zone controller of the actuation ECU's zone, which "
                                                   'puts it on the CAN FD bus of its zone; on the direct route it '
                                                   'goes over the direct link. The actuation ECU gets the same bytes '
                                                   'on both routes and gives the vehicle the applied command. '
                                                   'Nothing crosses back to the network side, and no item of the '
                                                   'vehicle network reaches the other zone controller or its CAN FD '
                                                   'bus. It carries REQ-EE-001 and REQ-EE-003 by the elements that '
                                                   'it places on the routes. No part here stands for an element of '
                                                   'the bench.',
        'part eeVehicleNetworkPhysicalSystem : EEVehicleNetworkPhysicalSystem': 'The vehicle network as the views '
                                                                                'draw it: the one usage of the '
                                                                                'physical definition. It depicts the '
                                                                                "realization of the context's "
                                                                                'vehicleNetwork and is bound to '
                                                                                'nothing.',
        'concern eeVehicleNetworkPhysicalAllocationConcern : PhysicalLogicalMappingConcern': 'System architects and '
                                                                                             'verification engineers '
                                                                                             'need each logical '
                                                                                             'element of phase 7 '
                                                                                             'allocated to the nodes '
                                                                                             'of the vehicle network '
                                                                                             'that carry it, and '
                                                                                             'each node that carries '
                                                                                             'one: the network side '
                                                                                             'of the central '
                                                                                             'computer, which '
                                                                                             'carries the identity '
                                                                                             'recorder and the '
                                                                                             'command carrier, the '
                                                                                             'zone controller of the '
                                                                                             "actuation ECU's zone, "
                                                                                             'which carries the '
                                                                                             'command carrier, and '
                                                                                             'the actuation ECU, '
                                                                                             'which carries the '
                                                                                             'actuation end. The '
                                                                                             'links, the other zone '
                                                                                             'controller and its CAN '
                                                                                             'FD bus carry no '
                                                                                             'logical element. An '
                                                                                             'allocation is a '
                                                                                             'responsibility '
                                                                                             'assignment, no '
                                                                                             'deployment or runtime '
                                                                                             'claim.',
        'view eeVehicleNetworkRouteExchangeView': 'The two routes of a driving command inside the vehicle network '
                                                  '(eeCommandRouteExchangeConcern) and the item on each part of its '
                                                  'way (eeCommandItemConcern): from the network side of the central '
                                                  'computer, the command frame inside an IEEE 1722 packet over the '
                                                  "Ethernet backbone to the zone controller of the actuation ECU's "
                                                  'zone, and as the frame on the CAN FD bus of that zone to the '
                                                  'actuation ECU; or the frame over the direct link to the actuation '
                                                  'ECU; and the applied command from the actuation ECU to the '
                                                  'vehicle. The other zone controller and its CAN FD bus are drawn '
                                                  'with their attachments, which carry no item. Each edge joins two '
                                                  'ports, and each port definition on a route carries the one item '
                                                  'that its exchange moves; the attachments carry none. The boundary '
                                                  'interface of the network side takes the payload of the '
                                                  'driver-assistance increment; nothing is drawn into it here, since '
                                                  'the Eclipse S-CORE path on the central computer is placed with '
                                                  'the software realization.'}
RECORD_DOCS = {'eeScoreCommandMappingRecord': 'The driving command from the mw::com event of the driver-assistance '
                                              'increment into the network side of the central computer, at the '
                                              "boundary interface. The item is that increment's payload, unchanged.",
               'eeZoneRoutePacketMappingRecord': 'The command frame inside an IEEE 1722 packet, from the network '
                                                 'side of the central computer over the Ethernet backbone to the '
                                                 "zone controller of the actuation ECU's zone, on the route through "
                                                 'a zone controller. A frame of the vehicle network, no vehicle '
                                                 'signal.',
               'eeZoneBusFrameMappingRecord': "The command frame from the zone controller of the actuation ECU's "
                                              'zone onto the CAN FD bus of its zone, as the packet held it. A frame '
                                              'of the vehicle network; the steering angle and the acceleration in it '
                                              'are typed by the two signals of the frame.',
               'eeDirectLinkFrameMappingRecord': 'The command frame from the network side of the central computer '
                                                 'over the direct link to the actuation ECU, on the direct route. A '
                                                 'frame of the vehicle network; the steering angle and the '
                                                 'acceleration in it are typed by the two signals of the frame.',
               'eeActuationFrameMappingRecord': 'The command frame as the actuation ECU takes it, from the CAN FD '
                                                'bus of its zone or from the direct link, by the route of the run, '
                                                'with the same bytes on both routes. The owning allocation targets '
                                                'the element, which the frame enters at two ports.',
               'eeAppliedCommandMappingRecord': "The applied command from the actuation ECU to the vehicle's "
                                                'steering, drive and brakes: the steering angle and the acceleration '
                                                'of the last valid driving command that it applied, or those of the '
                                                'stop response. It carries no detection part.',
               'eeIdentityRecordMappingRecord': 'The record of the network identity that the network side of the '
                                                'central computer writes before it takes the first driving command '
                                                'of each run, a file of the run that System 2 only reads. A record '
                                                'of files and settings, no vehicle signal. The owning allocation '
                                                'targets the element: the record crosses no port.'}
RECORD_VALUES = {'eeScoreCommandMappingRecord': {'semanticSource': 'the driving command of the driver-assistance '
                                                                   'increment, typed at the port by its payload '
                                                                   'DrivingCommandEventPayload, whose steering angle '
                                                                   'and acceleration are the DE4SDV_VSS_Extensions '
                                                                   'signals '
                                                                   'Vehicle_ADAS_Driving_Command_SteeringAngle and '
                                                                   'Vehicle_ADAS_Driving_Command_Acceleration; the '
                                                                   'issue time, the sequence count and the check '
                                                                   'value are protocol fields, no vehicle signal',
                                                 'softwareContractArtifact': 'the mw::com event of the driving '
                                                                             'command that the vehicle interface of '
                                                                             'the driver-assistance increment '
                                                                             'publishes on the Eclipse S-CORE path, '
                                                                             'taken by the network side of the '
                                                                             'central computer at the boundary '
                                                                             'interface, candidate',
                                                 'softwareContractMessage': 'DrivingCommandEventPayload, one event '
                                                                            'per driving command, candidate',
                                                 'softwareContractField': 'steeringAngle, acceleration, issueTime, '
                                                                          'sequenceCount, checkValue, exact',
                                                 'dataTypeAndUnit': 'steeringAngle in degrees, positive to the left; '
                                                                    'acceleration in m/s², negative to decelerate; '
                                                                    "issueTime in seconds on the vehicle's clock; "
                                                                    'sequenceCount an unsigned 32-bit count from 1 '
                                                                    'in each run; checkValue the CRC-32 over the '
                                                                    'other parts',
                                                 'timingQualityAndState': 'the driving commands at the rate the '
                                                                          'source gives them; the network side reads '
                                                                          "the vehicle's clock when it takes each "
                                                                          'one, the time from which the 50 ms of '
                                                                          'REQ-EE-005 count; on the bench the '
                                                                          "testbed's simulation clock stands in",
                                                 'transformationRule': 'none: the network side takes each part as '
                                                                       'the event gives it and puts it into the '
                                                                       'command frame unchanged',
                                                 'disposition': 'SignalMappingDisposition::candidate',
                                                 'owner': 'DE4SDV maintainers',
                                                 'nextAction': 'realize the take of the event on the network side '
                                                               'with the software realization, then bring the '
                                                               'verification cases of REQ-EE-002 and REQ-EE-005 to '
                                                               'evidence of record; none is started',
                                                 'evidenceOrGap': 'no runtime evidence of record; gap '
                                                                  'gapEENodeSoftwareOpen and framing assumption '
                                                                  'asmEEScoreCommandSource'},
                 'eeZoneRoutePacketMappingRecord': {'semanticSource': 'the command frame as the network side built '
                                                                      'it, held unchanged in a packet of the '
                                                                      'backbone: a frame of the vehicle network, no '
                                                                      'vehicle signal; the steering angle and the '
                                                                      'acceleration in it keep their typing by the '
                                                                      'two DE4SDV_VSS_Extensions signals of the '
                                                                      'frame',
                                                    'softwareContractArtifact': 'the communication matrix of the '
                                                                                'vehicle network, by role: the frame '
                                                                                'layout of the command frame and the '
                                                                                'IEEE 1722 stream that carries it on '
                                                                                'the backbone to the zone controller '
                                                                                "of the actuation ECU's zone, "
                                                                                'candidate',
                                                    'softwareContractMessage': 'EECommandPacket, one per driving '
                                                                               'command on the route through a zone '
                                                                               'controller, holding one '
                                                                               'EECommandFrame, candidate',
                                                    'softwareContractField': 'eeCarriedFrame, the whole frame with '
                                                                             'its five parts and the two signal '
                                                                             'values, exact; the fields of the '
                                                                             'packet around it are set by the stream '
                                                                             'of the configuration',
                                                    'dataTypeAndUnit': 'the bytes of the frame as the network side '
                                                                       'built them; the units of the parts as at the '
                                                                       'boundary interface',
                                                    'timingQualityAndState': 'one packet per driving command on the '
                                                                             'route through a zone controller; no '
                                                                             'element reads a clock on the backbone; '
                                                                             'the 50 ms of REQ-EE-005 count from the '
                                                                             'take to the arrival at the actuation '
                                                                             'ECU',
                                                    'transformationRule': 'the packet holds the frame as the network '
                                                                          'side built it; nothing on the backbone '
                                                                          'changes or computes a part (REQ-EE-007)',
                                                    'disposition': 'SignalMappingDisposition::candidate',
                                                    'owner': 'DE4SDV maintainers',
                                                    'nextAction': 'set the frame layout and the stream in the '
                                                                  'configuration, then bring the verification cases '
                                                                  'of REQ-EE-003, REQ-EE-004 and REQ-EE-007 to '
                                                                  'evidence of record; none is started',
                                                    'evidenceOrGap': 'no runtime evidence of record; gap '
                                                                     'gapEEConfigurationNamedByRole'},
                 'eeZoneBusFrameMappingRecord': {'semanticSource': 'the command frame as the network side built it, '
                                                                   'typed at the port by EECommandFrame, whose '
                                                                   'eeSteeringAngleSignal and eeAccelerationSignal '
                                                                   'are the DE4SDV_VSS_Extensions signals '
                                                                   'Vehicle_ADAS_Driving_Command_SteeringAngle and '
                                                                   'Vehicle_ADAS_Driving_Command_Acceleration; the '
                                                                   'issue time, the sequence count and the check '
                                                                   'value are protocol fields, no vehicle signal',
                                                 'softwareContractArtifact': 'the communication matrix of the '
                                                                             'vehicle network, by role: the frame '
                                                                             'layout of the command frame on the CAN '
                                                                             "FD bus of the actuation ECU's zone, "
                                                                             'and the routing entry by which the '
                                                                             'zone controller puts the frames of the '
                                                                             'stream on that bus, candidate',
                                                 'softwareContractMessage': 'EECommandFrame, one CAN FD frame per '
                                                                            'driving command, candidate',
                                                 'softwareContractField': 'the five parts and the two signal values '
                                                                          'as the network side built them, exact',
                                                 'dataTypeAndUnit': 'eeSteeringAngleSignal in degrees, the value of '
                                                                    'steeringAngle; eeAccelerationSignal in m/s², '
                                                                    'the value of acceleration; the issue time, the '
                                                                    'sequence count and the check value as at the '
                                                                    'boundary interface',
                                                 'timingQualityAndState': 'one frame per packet that reaches the '
                                                                          'zone controller; the zone controller '
                                                                          'reads no clock for the driving command',
                                                 'transformationRule': 'the zone controller unpacks: the frame '
                                                                       'leaves it with the bytes that the packet '
                                                                       'held, no part repacked and none computed '
                                                                       'anew (REQ-EE-007)',
                                                 'disposition': 'SignalMappingDisposition::candidate',
                                                 'owner': 'DE4SDV maintainers',
                                                 'nextAction': 'set the routing entry of the zone controller in the '
                                                               'configuration, then bring the verification cases of '
                                                               'REQ-EE-004 and REQ-EE-007 to evidence of record; '
                                                               'none is started',
                                                 'evidenceOrGap': 'no runtime evidence of record; gaps '
                                                                  'gapEEConfigurationNamedByRole and '
                                                                  'gapEENodeSoftwareOpen'},
                 'eeDirectLinkFrameMappingRecord': {'semanticSource': 'the command frame as the network side built '
                                                                      'it, typed at the port by EECommandFrame, '
                                                                      'whose eeSteeringAngleSignal and '
                                                                      'eeAccelerationSignal are the '
                                                                      'DE4SDV_VSS_Extensions signals '
                                                                      'Vehicle_ADAS_Driving_Command_SteeringAngle '
                                                                      'and '
                                                                      'Vehicle_ADAS_Driving_Command_Acceleration; '
                                                                      'the issue time, the sequence count and the '
                                                                      'check value are protocol fields, no vehicle '
                                                                      'signal',
                                                    'softwareContractArtifact': 'the communication matrix of the '
                                                                                'vehicle network, by role: the frame '
                                                                                'layout of the command frame on the '
                                                                                'direct link, candidate',
                                                    'softwareContractMessage': 'EECommandFrame, one CAN FD frame per '
                                                                               'driving command, candidate',
                                                    'softwareContractField': 'steeringAngle, acceleration, '
                                                                             'issueTime, sequenceCount, checkValue, '
                                                                             'eeSteeringAngleSignal, '
                                                                             'eeAccelerationSignal, exact; the '
                                                                             'layout of their bytes is set by the '
                                                                             'frame layout',
                                                    'dataTypeAndUnit': 'eeSteeringAngleSignal in degrees, the value '
                                                                       'of steeringAngle; eeAccelerationSignal in '
                                                                       'm/s², the value of acceleration; the issue '
                                                                       'time, the sequence count and the check value '
                                                                       'as at the boundary interface',
                                                    'timingQualityAndState': 'one frame per driving command on the '
                                                                             'direct route; no element reads a clock '
                                                                             'on the direct link',
                                                    'transformationRule': 'eeSteeringAngleSignal = steeringAngle in '
                                                                          'degrees and eeAccelerationSignal = '
                                                                          'acceleration in m/s², each as taken; the '
                                                                          'other parts as taken; nothing on the '
                                                                          'direct link changes or computes a part '
                                                                          '(REQ-EE-007)',
                                                    'disposition': 'SignalMappingDisposition::candidate',
                                                    'owner': 'DE4SDV maintainers',
                                                    'nextAction': 'set the frame layout in the configuration, then '
                                                                  'bring the verification cases of REQ-EE-003, '
                                                                  'REQ-EE-004 and REQ-EE-007 to evidence of record; '
                                                                  'none is started',
                                                    'evidenceOrGap': 'no runtime evidence of record; gap '
                                                                     'gapEEConfigurationNamedByRole'},
                 'eeActuationFrameMappingRecord': {'semanticSource': 'the command frame of the vehicle network, '
                                                                     'typed at the two ports of the actuation ECU by '
                                                                     'EECommandFrame, whose two signal values are '
                                                                     'the DE4SDV_VSS_Extensions command signals; the '
                                                                     'issue time, the sequence count and the check '
                                                                     'value are protocol fields, no vehicle signal',
                                                   'softwareContractArtifact': 'the communication matrix of the '
                                                                               'vehicle network, by role: the frame '
                                                                               'layout of the command frame as the '
                                                                               'actuation ECU reads it, candidate',
                                                   'softwareContractMessage': 'EECommandFrame, one CAN FD frame per '
                                                                              'driving command, candidate',
                                                   'softwareContractField': 'the five parts and the two signal '
                                                                            'values, exact',
                                                   'dataTypeAndUnit': 'eeSteeringAngleSignal in degrees, the value '
                                                                      'of steeringAngle; eeAccelerationSignal in '
                                                                      'm/s², the value of acceleration; the issue '
                                                                      'time, the sequence count and the check value '
                                                                      'as at the boundary interface',
                                                   'timingQualityAndState': "the actuation ECU reads the vehicle's "
                                                                            'clock when a frame arrives; a frame is '
                                                                            'valid only with an issue time no more '
                                                                            'than 100 ms before that time, and the '
                                                                            'stop response starts once more than 200 '
                                                                            'ms pass with no valid driving command; '
                                                                            "on the bench the testbed's simulation "
                                                                            'clock stands in',
                                                   'transformationRule': 'the actuation ECU judges each frame by the '
                                                                         'term valid driving command: the check '
                                                                         'value over the other parts as they arrive, '
                                                                         'the sequence count against the reference '
                                                                         'count, the issue time against the time of '
                                                                         'arrival; it computes no part anew',
                                                   'disposition': 'SignalMappingDisposition::candidate',
                                                   'owner': 'DE4SDV maintainers',
                                                   'nextAction': 'realize the check in the software of the actuation '
                                                                 'ECU, then bring the verification cases of '
                                                                 'REQ-EE-004, REQ-EE-006, REQ-EE-008 and REQ-EE-009 '
                                                                 'to evidence of record; none is started',
                                                   'evidenceOrGap': 'no runtime evidence of record; gap '
                                                                    'gapEENodeSoftwareOpen'},
                 'eeAppliedCommandMappingRecord': {'semanticSource': 'the steering angle and the acceleration that '
                                                                     'the actuation ECU gives the vehicle, typed by '
                                                                     'the item of phase 6, EEActuationOutput, with '
                                                                     'its quantities; they are the values that the '
                                                                     'frame carries as '
                                                                     'Vehicle_ADAS_Driving_Command_SteeringAngle and '
                                                                     'Vehicle_ADAS_Driving_Command_Acceleration, or '
                                                                     'those of the stop response',
                                                   'softwareContractArtifact': 'the actuator interfaces of the '
                                                                               "vehicle's steering, drive and "
                                                                               'brakes, by role, set with the design '
                                                                               'of the actuation ECU; on the bench '
                                                                               'the vehicle model of the testbed '
                                                                               'stands in for them, candidate',
                                                   'softwareContractMessage': 'EEActuationOutput, the applied '
                                                                              'command, candidate',
                                                   'softwareContractField': 'steeringAngle, acceleration, exact; the '
                                                                            'set-points of the actuators are set '
                                                                            'with the software of the actuation ECU',
                                                   'dataTypeAndUnit': 'steeringAngle in degrees, positive to the '
                                                                      'left; acceleration in m/s², negative to '
                                                                      'decelerate',
                                                   'timingQualityAndState': 'the actuation ECU applies each valid '
                                                                            'driving command at the time at which it '
                                                                            'arrives, and gives the stop response '
                                                                            'from later than 200 ms and no later '
                                                                            'than 300 ms after the last valid '
                                                                            'driving command reached it, or after '
                                                                            'the run started when none did, until '
                                                                            'the run ends',
                                                   'transformationRule': 'the steering angle and the acceleration of '
                                                                         'the last valid driving command, as it '
                                                                         'carried them; in the stop response a '
                                                                         'deceleration of 4 m/s² and the steering '
                                                                         'angle of the last valid driving command, '
                                                                         'or 0° when it applied none',
                                                   'disposition': 'SignalMappingDisposition::candidate',
                                                   'owner': 'DE4SDV maintainers',
                                                   'nextAction': 'set the actuator interfaces with the design of the '
                                                                 'actuation ECU, then bring the verification cases '
                                                                 'of REQ-EE-006, REQ-EE-008 and REQ-EE-009 to '
                                                                 'evidence of record; none is started',
                                                   'evidenceOrGap': 'no runtime evidence of record; gap '
                                                                    'gapEENodeSoftwareOpen and framing gap '
                                                                    'gapEEBenchPlatform'},
                 'eeIdentityRecordMappingRecord': {'semanticSource': 'the network identity of the run as the term of '
                                                                     'phase 5 names it: a record of files and '
                                                                     'settings, no vehicle signal',
                                                   'softwareContractArtifact': 'the record file of the network '
                                                                               'identity of each run, written on the '
                                                                               'central computer, candidate',
                                                   'softwareContractMessage': 'one record per run, written before '
                                                                              'the first driving command of the run '
                                                                              'is taken, candidate',
                                                   'softwareContractField': 'the route of the run, the commit of the '
                                                                            'DE4SDV repository with the difference, '
                                                                            'the SHA-256 of each file of the '
                                                                            'configuration, and each setting that '
                                                                            'the vehicle network reads from outside '
                                                                            'a file, as read; the files are named by '
                                                                            'role until the implementation names '
                                                                            'them',
                                                   'dataTypeAndUnit': 'strings; each SHA-256 in hexadecimal',
                                                   'timingQualityAndState': 'once per run, before the network side '
                                                                            'takes the first driving command of the '
                                                                            'run',
                                                   'transformationRule': 'none: each value as read or hashed',
                                                   'disposition': 'SignalMappingDisposition::candidate',
                                                   'owner': 'DE4SDV maintainers',
                                                   'nextAction': 'name the files of the configuration with the '
                                                                 'implementation, then bring the verification cases '
                                                                 'of REQ-EE-010 to evidence of record; none is '
                                                                 'started',
                                                   'evidenceOrGap': 'no runtime evidence of record; gaps '
                                                                    'gapEEConfigurationNamedByRole and '
                                                                    'gapEENodeSoftwareOpen'}}
COMMENT_TEXTS = {'eePhase8ActuationEndPlaced': 'Placed, not observed: the actuation ECU holds the check, the '
                                               'application and the stop response of the actuation end. Each driving '
                                               'command with its issue time, sequence count and check value is one '
                                               'CAN FD frame (owner decision of 2026-11-26), and the zone controller '
                                               "of the actuation ECU's zone unpacks the frame from its packet and "
                                               'repacks nothing, so the detection reaches from the network side of '
                                               'the central computer to the actuation ECU on both routes. The stop '
                                               'response needs no vehicle speed. Still open: how the actuation ECU '
                                               'turns the steering angle and the acceleration into the set-points of '
                                               "the vehicle's actuators, and whether that needs a vehicle speed "
                                               '(gapEENodeSoftwareOpen). The adapters of the driving benches stay as '
                                               'they are.',
                 'eePhase8StackBoundaryPartlySettled': 'Settled in part: the central computer, the two zone '
                                                       'controllers and the actuation ECU are typed as vehicle '
                                                       'compute nodes of the execution environments of the product '
                                                       'line, a typing that claims no board, no operating system, no '
                                                       'qualification and no candidate of that family; the links are '
                                                       'not. The Ethernet backbone of this realization is its own '
                                                       'and reuses no port of VehicleNetworkBoundary of the AAOS SDV '
                                                       'middleware boundary. How the network side relates to the SoC '
                                                       'and the hardware layer of the platform stack, and the layers '
                                                       'that each node runs on, stay open for the software '
                                                       'realization of this phase (gapEENodeSoftwareOpen).',
                 'eePhase8BoundaryInterfacePlaced': 'Placed, not observed: the boundary interface is the port of the '
                                                    'network side of the central computer at which it takes the '
                                                    'mw::com event of the driving command of the driver-assistance '
                                                    'increment. What on the central computer gives that event to the '
                                                    'network side is placed with the software realization of this '
                                                    'phase. The readiness probe still tests first that the Eclipse '
                                                    'S-CORE path hands the driving command to the network side.',
                 'eePhase8TestbedQuestionsAsked': 'Not settled here: the testbed stays to be chosen. This '
                                                  'realization asks of it, before phase 10, whether its buses and '
                                                  'its direct link carry CAN FD frames; whether it gives every '
                                                  'element the one clock of the virtual vehicle and records each '
                                                  'driving command at each element with its simulation time; and '
                                                  'whether it makes one fault on one link of a route at a time. On '
                                                  'the testbed a node, a virtual link or a virtual CAN FD bus stands '
                                                  'in for each element of this realization.'}
GAP_DOCS = {'gapEECentralComputerHandover': 'The realization of the HMI display, '
                                            'DE4SDV_HmiDisplayPhysicalSoftwareRealization, declares the central '
                                            'computer too, as HmiDisplayCentralComputer with the VMs that it hosts, '
                                            'and its doc says that it imports the declaration of an E/E realization '
                                            'once one exists. This realization declares the central computer as a '
                                            'node, the declaration that the realization of the HMI display is to '
                                            'import. The realization of the HMI display keeps its own declaration '
                                            'until the method can place software on a node, and its file is changed '
                                            'in its own increment, not here. Until then the model holds two '
                                            'declarations of one computer.',
            'gapEEConfigurationNamedByRole': 'REQ-EE-010 reads the network identity over the files of the '
                                             'configuration that phase 8 names. This realization names them by role '
                                             'only: the frame layout of the command frame, with the IEEE 1722 stream '
                                             'of its packet; the routing entry of the zone controller of the '
                                             "actuation ECU's zone; the route setting of the network side; and the "
                                             'files that set the software of each element. Their paths come with the '
                                             'implementation, so phase 8 does not name the files yet, and REQ-EE-010 '
                                             'cannot be verified as worded until they are named, which is due before '
                                             'phase 10.',
            'gapEENodeSoftwareOpen': 'This realization places the logical elements on the nodes and the command '
                                     'frame on the links; it places no software. The software of the network side of '
                                     'the central computer, which takes the event and builds the frame, of the zone '
                                     'controller, which unpacks it, and of the actuation ECU, which checks and '
                                     'applies it, the layers that each node runs on, and the typing by VSS at their '
                                     'software ports come with the software realization of this phase, after the '
                                     'change to the method that relates software to a node. How the identity '
                                     'recorder reads the software and the configuration of the zone controller and '
                                     'of the actuation ECU is set there too. If the recorder reads them over the '
                                     'vehicle network, that reading is an exchange between logical elements, which '
                                     'phase 7 lacks: there the identity recorder exchanges nothing. The owner then '
                                     'decides between an amendment of phase 7 and a narrower REQ-EE-010.'}

GUIDE_HEADING = "## E/E realization (Phase 8)"
GUIDE_LINK = "../../textual-notation-of-model/packages/features/ee/ee_architecture_physical_ee_realization.sysml"
GUIDE_STATUS = ('**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability '
                'classification, Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, '
                'Phase 7 logical architecture and the E/E realization of Phase 8, proposal.**')
GUIDE_NEXT = ('The next model obligation is the software realization of **Phase 8**, after the change to the method '
              'that relates software to a node: the software of each node, the layers that it runs on and VSS at its '
              'software ports. Once the E/E realization holds the gate of Phase 8, the Method Check names Phase 9 '
              "next, with its first gate `incrementHasConfiguredProduct`; by the owner's decision Phase 9 waits for "
              'the software realization.')
GUIDE_BLOCKS = ['Phase 8 realizes the vehicle network in two packages. The first is the [E/E '
                'realization](../../textual-notation-of-model/packages/features/ee/ee_architecture_physical_ee_realiz'
                'ation.sysml), '
                'DE4SDV_EEArchitecturePhysicalEERealization: the nodes, the links and the frame on them. The '
                'software realization, with the software of each node, follows a change to the method that relates '
                'software to a node. On 2026-11-26 the owner decided this split, that the network side of the '
                'central computer puts each driving command straight into one CAN FD frame, and that this frame '
                'reaches the actuation ECU unchanged on either route.',
                '- The central computer, the two zone controllers and the actuation ECU are typed as vehicle compute '
                'nodes, a typing that claims no board, no operating system and no qualification. Of the central '
                'computer only its network side is an element of the vehicle network, and it carries the identity '
                'recorder and the command carrier. It takes each driving command from the Eclipse S-CORE path at the '
                "boundary interface, reads the vehicle's clock and builds the frame. Before the first driving "
                "command of each run it records the network identity. - The zone controller of the actuation ECU's "
                'zone carries the command carrier on the route through a zone controller. It takes the frame out of '
                'its IEEE 1722 packet from the Ethernet backbone and puts it on the CAN FD bus of its zone. It '
                "repacks nothing. - The actuation ECU carries the actuation end. It reads the vehicle's clock when a "
                'frame arrives, checks the frame, applies each valid driving command and gives the stop response. - '
                'The Ethernet backbone, the CAN FD bus of that zone and the direct link, a CAN FD link, carry the '
                'frame and compute nothing. The other zone controller and its CAN FD bus lie on neither route and '
                'carry no logical element.',
                'The frame keeps the five parts of the command of Phase 6. Its steering angle and acceleration are '
                'typed by the two DE4SDV_VSS_Extensions command signals of the driving increments; the issue time, '
                'the sequence count and the check value are protocol fields, no vehicle signal. Seven signal '
                'mappings record the items at the crossings, and two dependencies from the physical system carry '
                'REQ-EE-001 and REQ-EE-003. Three gaps state what is not settled: the second declaration of the '
                'central computer, in the realization of the HMI display (`gapEECentralComputerHandover`); the files '
                'of the configuration, named by role only (`gapEEConfigurationNamedByRole`); and the software of the '
                'nodes (`gapEENodeSoftwareOpen`). On the bench the testbed stands in for each element; whether it '
                'carries CAN FD is a question for Phase 10.',
                'Three views show it: the structure as a tree, the logical elements by node as a matrix, and the two '
                'routes as an interconnection, which also shows the item on each part of the way.',
                '`tests/test_ee_architecture_physical_ee_realization.py` pins the elements, their ports and routes, '
                'the allocations, the mappings, the views and this section.']

#: The package's code, every declaration at its own depth (two spaces a level), as `_skeleton` reads it: generated
#: from the model, never written by hand. A line ending in a backslash continues on the next.
SKELETON = """\
/*…*/
package DE4SDV_EEArchitecturePhysicalEERealization {
  private import DE4SDV_MethodContext::*;
  private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;
  private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;
  private import DE4SDV_MethodProcess::SignalMappingDisposition;
  private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;
  private import DE4SDV_ExecutionEnvironments::VehicleComputeNode;
  private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::DrivingCommandEventPayload;
  private import DE4SDV_EEArchitectureFraming::gapEEActuationEnd;
  private import DE4SDV_EEArchitectureFraming::gapEEStackAndNetworkBoundary;
  private import DE4SDV_EEArchitectureFraming::gapEEBenchPlatform;
  private import DE4SDV_EEArchitectureFraming::asmEEScoreCommandSource;
  private import DE4SDV_EEArchitectureFraming::eeTopologyStructureConcern;
  private import DE4SDV_EEArchitectureFraming::eeCommandItemConcern;
  private import DE4SDV_EEArchitectureFraming::eeCommandRouteExchangeConcern;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEDrivingCommandInput;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEActuationOutput;
  private import DE4SDV_EEArchitectureLogicalArchitecture::EEVehicleNetworkLogicalSystem;
  private import DE4SDV_EEArchitectureNeedsRequirements::reqBothRoutesInOneTopology;
  private import DE4SDV_EEArchitectureNeedsRequirements::reqCommandsOnlyOnTheirRoute;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_Acceleration;
  private import DE4SDV_VSS_Extensions::Vehicle_ADAS_Driving_Command_SteeringAngle;
  private import DE4SDV_Stakeholders::*;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;
  /* ─── The items on the links ─── */
  item def EECommandFrame :> EEDrivingCommandInput {
    doc /*…*/
    attribute eeSteeringAngleSignal : Vehicle_ADAS_Driving_Command_SteeringAngle;
    attribute eeAccelerationSignal : Vehicle_ADAS_Driving_Command_Acceleration;
  item def EECommandPacket {
    doc /*…*/
    item eeCarriedFrame : EECommandFrame;
  /* ─── The ports: one item each, and the attachment that carries none ─── */
  port def EEBoundaryCommandIn {
    doc /*…*/
    in item eeDrivingCommand : DrivingCommandEventPayload;
  port def EECommandPacketOut {
    doc /*…*/
    out item eeCommandPacket : EECommandPacket;
  port def EECommandPacketIn {
    doc /*…*/
    in item eeCommandPacket : EECommandPacket;
  port def EECommandFrameOut {
    doc /*…*/
    out item eeCommandFrame : EECommandFrame;
  port def EECommandFrameIn {
    doc /*…*/
    in item eeCommandFrame : EECommandFrame;
  port def EEAppliedCommandOut {
    doc /*…*/
    out item eeAppliedCommand : EEActuationOutput;
  port def EEAppliedCommandIn {
    doc /*…*/
    in item eeAppliedCommand : EEActuationOutput;
  port def EENetworkAttachment {
    doc /*…*/
  /* ─── The nodes that carry the logical elements ─── */
  part def EECentralComputerNetworkSide :> PhysicalAllocationElement {
    doc /*…*/
    port eeDrivingCommandIn : EEBoundaryCommandIn;
    port eeBackbonePacketOut : EECommandPacketOut;
    port eeDirectLinkFrameOut : EECommandFrameOut;
  part def EEActuationZoneController :> PhysicalAllocationElement, VehicleComputeNode {
    doc /*…*/
    port eePacketIn : EECommandPacketIn;
    port eeFrameOut : EECommandFrameOut;
  part def EEActuationECU :> PhysicalAllocationElement, VehicleComputeNode {
    doc /*…*/
    port eeZoneBusFrameIn : EECommandFrameIn;
    port eeDirectLinkFrameIn : EECommandFrameIn;
    port eeAppliedCommandOut : EEAppliedCommandOut;
  /* ─── The central computer and the other zone controller ─── */
  part def EECentralComputer :> VehicleComputeNode {
    doc /*…*/
    port eeBackbonePacketOut : EECommandPacketOut;
    port eeDirectLinkFrameOut : EECommandFrameOut;
    part eeNetworkSide : EECentralComputerNetworkSide;
    bind eeBackbonePacketOut = eeNetworkSide.eeBackbonePacketOut;
    bind eeDirectLinkFrameOut = eeNetworkSide.eeDirectLinkFrameOut;
  part def EEOtherZoneController :> VehicleComputeNode {
    doc /*…*/
    port eeBackboneAttachment : EENetworkAttachment;
    port eeZoneBusAttachment : EENetworkAttachment;
  /* ─── The links: they carry the frame and compute nothing ─── */
  part def EEEthernetBackbone {
    doc /*…*/
    port eePacketIn : EECommandPacketIn;
    port eePacketOut : EECommandPacketOut;
    port eeOtherZoneAttachment : EENetworkAttachment;
  part def EEActuationZoneCANFDBus {
    doc /*…*/
    port eeFrameIn : EECommandFrameIn;
    port eeFrameOut : EECommandFrameOut;
  part def EEOtherZoneCANFDBus {
    doc /*…*/
    port eeZoneControllerAttachment : EENetworkAttachment;
  part def EEDirectCANFDLink {
    doc /*…*/
    port eeFrameIn : EECommandFrameIn;
    port eeFrameOut : EECommandFrameOut;
  /* ─── The vehicle, as context ─── */
  part def EEActuatedVehicle {
    doc /*…*/
    port eeAppliedCommandIn : EEAppliedCommandIn;
  /* ─── The vehicle network ─── */
  part def EEVehicleNetworkPhysicalSystem {
    doc /*…*/
    part eeCentralComputer : EECentralComputer;
    part eeEthernetBackbone : EEEthernetBackbone;
    part eeActuationZoneController : EEActuationZoneController;
    part eeOtherZoneController : EEOtherZoneController;
    part eeActuationZoneCANFDBus : EEActuationZoneCANFDBus;
    part eeOtherZoneCANFDBus : EEOtherZoneCANFDBus;
    part eeDirectCANFDLink : EEDirectCANFDLink;
    part eeActuationECU : EEActuationECU;
    part eeActuatedVehicle : EEActuatedVehicle;
    connection eeBackbonePacketFromCentralComputer connect eeCentralComputer.eeBackbonePacketOut to\
 eeEthernetBackbone.eePacketIn;
    connection eeBackbonePacketToActuationZone connect eeEthernetBackbone.eePacketOut to\
 eeActuationZoneController.eePacketIn;
    connection eeZoneBusFrameFromZoneController connect eeActuationZoneController.eeFrameOut to\
 eeActuationZoneCANFDBus.eeFrameIn;
    connection eeZoneBusFrameToActuationECU connect eeActuationZoneCANFDBus.eeFrameOut to\
 eeActuationECU.eeZoneBusFrameIn;
    connection eeDirectLinkFrameFromCentralComputer connect eeCentralComputer.eeDirectLinkFrameOut to\
 eeDirectCANFDLink.eeFrameIn;
    connection eeDirectLinkFrameToActuationECU connect eeDirectCANFDLink.eeFrameOut to\
 eeActuationECU.eeDirectLinkFrameIn;
    connection eeAppliedCommandToVehicle connect eeActuationECU.eeAppliedCommandOut to\
 eeActuatedVehicle.eeAppliedCommandIn;
    connection eeOtherZoneOnBackbone connect eeEthernetBackbone.eeOtherZoneAttachment to\
 eeOtherZoneController.eeBackboneAttachment;
    connection eeOtherZoneBusOnZoneController connect eeOtherZoneController.eeZoneBusAttachment to\
 eeOtherZoneCANFDBus.eeZoneControllerAttachment;
  part eeVehicleNetworkPhysicalSystem : EEVehicleNetworkPhysicalSystem {
    doc /*…*/
  /* ─── Logical-to-physical allocations (allocatedTo) ─── */
  allocation eeRecorderToNetworkSide allocate EEVehicleNetworkLogicalSystem::eeIdentityRecorder to\
 eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
  allocation eeCarrierToNetworkSide allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
  allocation eeCarrierToActuationZoneController allocate EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
  allocation eeActuationEndToActuationECU allocate EEVehicleNetworkLogicalSystem::eeActuationEnd to\
 eeVehicleNetworkPhysicalSystem::eeActuationECU;
  /* ─── The topology and route requirements, carried by the realization that places the routes ─── */
  dependency eePhysicalSystemCarriesBothRoutesInOneTopology from EEVehicleNetworkPhysicalSystem to\
 reqBothRoutesInOneTopology;
  dependency eePhysicalSystemCarriesCommandsOnlyOnTheirRoute from EEVehicleNetworkPhysicalSystem to\
 reqCommandsOnlyOnTheirRoute;
  /* ─── Signal mappings: one per crossing, each with its record ─── */
  allocation eeScoreCommandMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeDrivingCommandIn {
    item <'MAP-EE-SCORE-COMMAND'> eeScoreCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the driving command of the driver-assistance increment, typed at the port by its\
 payload DrivingCommandEventPayload, whose steering angle and acceleration are the DE4SDV_VSS_Extensions signals\
 Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the\
 sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the mw::com event of the driving command that the vehicle interface of\
 the driver-assistance increment publishes on the Eclipse S-CORE path, taken by the network side of the central\
 computer at the boundary interface, candidate";
      attribute :>> softwareContractMessage = "DrivingCommandEventPayload, one event per driving command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, issueTime, sequenceCount, checkValue, exact";
      attribute :>> dataTypeAndUnit = "steeringAngle in degrees, positive to the left; acceleration in m/s², negative\
 to decelerate; issueTime in seconds on the vehicle's clock; sequenceCount an unsigned 32-bit count from 1 in each\
 run; checkValue the CRC-32 over the other parts";
      attribute :>> timingQualityAndState = "the driving commands at the rate the source gives them; the network side\
 reads the vehicle's clock when it takes each one, the time from which the 50 ms of REQ-EE-005 count; on the bench the\
 testbed's simulation clock stands in";
      attribute :>> transformationRule = "none: the network side takes each part as the event gives it and puts it\
 into the command frame unchanged";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "realize the take of the event on the network side with the software realization,\
 then bring the verification cases of REQ-EE-002 and REQ-EE-005 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen and framing assumption\
 asmEEScoreCommandSource";
  allocation eeZoneRoutePacketMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeBackbonePacketOut {
    item <'MAP-EE-ZONE-ROUTE-PACKET'> eeZoneRoutePacketMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the command frame as the network side built it, held unchanged in a packet of\
 the backbone: a frame of the vehicle network, no vehicle signal; the steering angle and the acceleration in it keep\
 their typing by the two DE4SDV_VSS_Extensions signals of the frame";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame\
 layout of the command frame and the IEEE 1722 stream that carries it on the backbone to the zone controller of the\
 actuation ECU's zone, candidate";
      attribute :>> softwareContractMessage = "EECommandPacket, one per driving command on the route through a zone\
 controller, holding one EECommandFrame, candidate";
      attribute :>> softwareContractField = "eeCarriedFrame, the whole frame with its five parts and the two signal\
 values, exact; the fields of the packet around it are set by the stream of the configuration";
      attribute :>> dataTypeAndUnit = "the bytes of the frame as the network side built them; the units of the parts\
 as at the boundary interface";
      attribute :>> timingQualityAndState = "one packet per driving command on the route through a zone controller; no\
 element reads a clock on the backbone; the 50 ms of REQ-EE-005 count from the take to the arrival at the actuation\
 ECU";
      attribute :>> transformationRule = "the packet holds the frame as the network side built it; nothing on the\
 backbone changes or computes a part (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the frame layout and the stream in the configuration, then bring the\
 verification cases of REQ-EE-003, REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEEConfigurationNamedByRole";
  allocation eeZoneBusFrameMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem.eeActuationZoneController.eeFrameOut {
    item <'MAP-EE-ZONE-BUS-FRAME'> eeZoneBusFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the command frame as the network side built it, typed at the port by\
 EECommandFrame, whose eeSteeringAngleSignal and eeAccelerationSignal are the DE4SDV_VSS_Extensions signals\
 Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the\
 sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame\
 layout of the command frame on the CAN FD bus of the actuation ECU's zone, and the routing entry by which the zone\
 controller puts the frames of the stream on that bus, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "the five parts and the two signal values as the network side built them,\
 exact";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle;\
 eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at\
 the boundary interface";
      attribute :>> timingQualityAndState = "one frame per packet that reaches the zone controller; the zone\
 controller reads no clock for the driving command";
      attribute :>> transformationRule = "the zone controller unpacks: the frame leaves it with the bytes that the\
 packet held, no part repacked and none computed anew (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the routing entry of the zone controller in the configuration, then bring the\
 verification cases of REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gaps gapEEConfigurationNamedByRole and\
 gapEENodeSoftwareOpen";
  allocation eeDirectLinkFrameMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeCommandCarrier to\
 eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide.eeDirectLinkFrameOut {
    item <'MAP-EE-DIRECT-LINK-FRAME'> eeDirectLinkFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the command frame as the network side built it, typed at the port by\
 EECommandFrame, whose eeSteeringAngleSignal and eeAccelerationSignal are the DE4SDV_VSS_Extensions signals\
 Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration; the issue time, the\
 sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame\
 layout of the command frame on the direct link, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, issueTime, sequenceCount, checkValue,\
 eeSteeringAngleSignal, eeAccelerationSignal, exact; the layout of their bytes is set by the frame layout";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle;\
 eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at\
 the boundary interface";
      attribute :>> timingQualityAndState = "one frame per driving command on the direct route; no element reads a\
 clock on the direct link";
      attribute :>> transformationRule = "eeSteeringAngleSignal = steeringAngle in degrees and eeAccelerationSignal =\
 acceleration in m/s², each as taken; the other parts as taken; nothing on the direct link changes or computes a part\
 (REQ-EE-007)";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the frame layout in the configuration, then bring the verification cases of\
 REQ-EE-003, REQ-EE-004 and REQ-EE-007 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEEConfigurationNamedByRole";
  allocation eeActuationFrameMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeActuationEnd to eeVehicleNetworkPhysicalSystem.eeActuationECU {
    item <'MAP-EE-ACTUATION-FRAME'> eeActuationFrameMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the command frame of the vehicle network, typed at the two ports of the\
 actuation ECU by EECommandFrame, whose two signal values are the DE4SDV_VSS_Extensions command signals; the issue\
 time, the sequence count and the check value are protocol fields, no vehicle signal";
      attribute :>> softwareContractArtifact = "the communication matrix of the vehicle network, by role: the frame\
 layout of the command frame as the actuation ECU reads it, candidate";
      attribute :>> softwareContractMessage = "EECommandFrame, one CAN FD frame per driving command, candidate";
      attribute :>> softwareContractField = "the five parts and the two signal values, exact";
      attribute :>> dataTypeAndUnit = "eeSteeringAngleSignal in degrees, the value of steeringAngle;\
 eeAccelerationSignal in m/s², the value of acceleration; the issue time, the sequence count and the check value as at\
 the boundary interface";
      attribute :>> timingQualityAndState = "the actuation ECU reads the vehicle's clock when a frame arrives; a frame\
 is valid only with an issue time no more than 100 ms before that time, and the stop response starts once more than\
 200 ms pass with no valid driving command; on the bench the testbed's simulation clock stands in";
      attribute :>> transformationRule = "the actuation ECU judges each frame by the term valid driving command: the\
 check value over the other parts as they arrive, the sequence count against the reference count, the issue time\
 against the time of arrival; it computes no part anew";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "realize the check in the software of the actuation ECU, then bring the verification\
 cases of REQ-EE-004, REQ-EE-006, REQ-EE-008 and REQ-EE-009 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen";
  allocation eeAppliedCommandMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeActuationEnd to eeVehicleNetworkPhysicalSystem.eeActuationECU.eeAppliedCommandOut {
    item <'MAP-EE-APPLIED-COMMAND'> eeAppliedCommandMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the steering angle and the acceleration that the actuation ECU gives the\
 vehicle, typed by the item of phase 6, EEActuationOutput, with its quantities; they are the values that the frame\
 carries as Vehicle_ADAS_Driving_Command_SteeringAngle and Vehicle_ADAS_Driving_Command_Acceleration, or those of the\
 stop response";
      attribute :>> softwareContractArtifact = "the actuator interfaces of the vehicle's steering, drive and brakes,\
 by role, set with the design of the actuation ECU; on the bench the vehicle model of the testbed stands in for them,\
 candidate";
      attribute :>> softwareContractMessage = "EEActuationOutput, the applied command, candidate";
      attribute :>> softwareContractField = "steeringAngle, acceleration, exact; the set-points of the actuators are\
 set with the software of the actuation ECU";
      attribute :>> dataTypeAndUnit = "steeringAngle in degrees, positive to the left; acceleration in m/s², negative\
 to decelerate";
      attribute :>> timingQualityAndState = "the actuation ECU applies each valid driving command at the time at which\
 it arrives, and gives the stop response from later than 200 ms and no later than 300 ms after the last valid driving\
 command reached it, or after the run started when none did, until the run ends";
      attribute :>> transformationRule = "the steering angle and the acceleration of the last valid driving command,\
 as it carried them; in the stop response a deceleration of 4 m/s² and the steering angle of the last valid driving\
 command, or 0° when it applied none";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "set the actuator interfaces with the design of the actuation ECU, then bring the\
 verification cases of REQ-EE-006, REQ-EE-008 and REQ-EE-009 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gap gapEENodeSoftwareOpen and framing gap\
 gapEEBenchPlatform";
  allocation eeIdentityRecordMapping : SystemToSoftwareSignalMappingCandidate allocate\
 EEVehicleNetworkLogicalSystem::eeIdentityRecorder to eeVehicleNetworkPhysicalSystem.eeCentralComputer.eeNetworkSide {
    item <'MAP-EE-IDENTITY-RECORD'> eeIdentityRecordMappingRecord : LogicalToSoftwareSignalMappingRecord {
      doc /*…*/
      attribute :>> semanticSource = "the network identity of the run as the term of phase 5 names it: a record of\
 files and settings, no vehicle signal";
      attribute :>> softwareContractArtifact = "the record file of the network identity of each run, written on the\
 central computer, candidate";
      attribute :>> softwareContractMessage = "one record per run, written before the first driving command of the run\
 is taken, candidate";
      attribute :>> softwareContractField = "the route of the run, the commit of the DE4SDV repository with the\
 difference, the SHA-256 of each file of the configuration, and each setting that the vehicle network reads from\
 outside a file, as read; the files are named by role until the implementation names them";
      attribute :>> dataTypeAndUnit = "strings; each SHA-256 in hexadecimal";
      attribute :>> timingQualityAndState = "once per run, before the network side takes the first driving command of\
 the run";
      attribute :>> transformationRule = "none: each value as read or hashed";
      attribute :>> disposition = SignalMappingDisposition::candidate;
      attribute :>> owner = "DE4SDV maintainers";
      attribute :>> nextAction = "name the files of the configuration with the implementation, then bring the\
 verification cases of REQ-EE-010 to evidence of record; none is started";
      attribute :>> evidenceOrGap = "no runtime evidence of record; gaps gapEEConfigurationNamedByRole and\
 gapEENodeSoftwareOpen";
  /* ─── What phase 8 settled on the framing's records ─── */
  comment eePhase8ActuationEndPlaced about gapEEActuationEnd /*…*/
  comment eePhase8StackBoundaryPartlySettled about gapEEStackAndNetworkBoundary /*…*/
  comment eePhase8BoundaryInterfacePlaced about asmEEScoreCommandSource /*…*/
  comment eePhase8TestbedQuestionsAsked about gapEEBenchPlatform /*…*/
  /* ─── The gaps of the realization ─── */
  part gapEECentralComputerHandover : IncrementGap {
    doc /*…*/
  part gapEEConfigurationNamedByRole : IncrementGap {
    doc /*…*/
  part gapEENodeSoftwareOpen : IncrementGap {
    doc /*…*/
  /* ─── Concerns and views of the phase ─── */
  view eeVehicleNetworkPhysicalStructureView {
    viewpoint eePhysicalStructureViewpoint : PhysicalStructureDefinitionViewpoint {
      frame eeTopologyStructureConcern;
    expose eeVehicleNetworkPhysicalSystem;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::BindingConnectorAsUsage);
    render asTreeDiagram;
  concern eeVehicleNetworkPhysicalAllocationConcern : PhysicalLogicalMappingConcern {
    doc /*…*/
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  view eeVehicleNetworkPhysicalLogicalMappingView : MVD::MatrixView {
    viewpoint eePhysicalLogicalMappingViewpoint : PhysicalLogicalMappingViewpoint {
      frame eeVehicleNetworkPhysicalAllocationConcern;
    view :>> rowView {
      expose EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
      expose EEVehicleNetworkLogicalSystem::eeCommandCarrier;
      expose EEVehicleNetworkLogicalSystem::eeActuationEnd;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> columnView {
      expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
      expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
      expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> cellView {
      expose DE4SDV_EEArchitecturePhysicalEERealization::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
  view eeVehicleNetworkRouteExchangeView {
    doc /*…*/
    viewpoint eeRouteExchangeViewpoint : PhysicalInternalExchangeViewpoint {
      frame eeCommandRouteExchangeConcern;
      frame eeCommandItemConcern;
    expose eeVehicleNetworkPhysicalSystem;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeBackbonePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeDirectLinkFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDrivingCommandIn;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeBackbonePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeCentralComputer::eeNetworkSide::eeDirectLinkFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketIn;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eePacketOut;
    expose eeVehicleNetworkPhysicalSystem::eeEthernetBackbone::eeOtherZoneAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eePacketIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneController::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeBackboneAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneController::eeZoneBusAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationZoneCANFDBus::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneCANFDBus::eeZoneControllerAttachment;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeDirectCANFDLink::eeFrameOut;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeZoneBusFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeDirectLinkFrameIn;
    expose eeVehicleNetworkPhysicalSystem::eeActuationECU::eeAppliedCommandOut;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle;
    expose eeVehicleNetworkPhysicalSystem::eeActuatedVehicle::eeAppliedCommandIn;
    expose eeVehicleNetworkPhysicalSystem::eeBackbonePacketFromCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeBackbonePacketToActuationZone;
    expose eeVehicleNetworkPhysicalSystem::eeZoneBusFrameFromZoneController;
    expose eeVehicleNetworkPhysicalSystem::eeZoneBusFrameToActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameFromCentralComputer;
    expose eeVehicleNetworkPhysicalSystem::eeDirectLinkFrameToActuationECU;
    expose eeVehicleNetworkPhysicalSystem::eeAppliedCommandToVehicle;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneOnBackbone;
    expose eeVehicleNetworkPhysicalSystem::eeOtherZoneBusOnZoneController;
    filter not (@ SysML::AllocationUsage);
    filter not (@ SysML::InterfaceUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
"""


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _doc(declaration: str) -> str:
    """The doc text of the element whose body follows ``declaration`` in the raw model."""
    assert _raw().count(declaration + " {") == 1, declaration
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _comment(name: str) -> str:
    match = re.search(rf"\bcomment\s+{name}\s+about\s+\w+\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, name
    return _flat(match.group(1))


def _header_paragraphs() -> list[str]:
    head = _raw().split(f"package {PACKAGE}", 1)[0]
    assert head.startswith("/*") and head.rstrip().endswith("*/")
    lines = [re.sub(r"^\s*\*?\s?", "", line) for line in head.strip()[2:-2].splitlines()]
    return [" ".join(part.split()) for part in "\n".join(lines).split("\n\n") if part.strip()]


def _direct(body: str) -> str:
    """Blank nested bodies, so only the direct members of ``body`` remain visible."""
    out, depth = [], 0
    for char in body:
        if char == "}":
            depth -= 1
        out.append(char if depth == 0 else " ")
        if char == "{":
            depth += 1
    return "".join(out)


def _definition(name: str) -> str:
    header = re.search(rf"\bpart\s+def\s+{name}\b[^{{;]*\{{", _code())
    assert header, name
    return braced_body(_code(), header.group(0)[:-1].rstrip())


def _connections(name: str) -> list[tuple[str, str, str]]:
    return re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*[;{]", _direct(_definition(name)))


def _binds(name: str) -> list[tuple[str, str]]:
    return re.findall(r"\bbind\s+([\w.]+)\s*=\s*([\w.]+)\s*;", _direct(_definition(name)))


def _strings_blanked(code: str) -> str:
    return re.sub(r'"[^"\n]*"', '""', code)


def _end(container: str, end: str) -> str:
    """The port definition at a connection end inside ``container``, read through the part definitions."""
    part, port = end.split(".")
    definition = {name: typ for _, name, typ in PARTS[container]}[part]
    return dict(PORTS[definition])[port]


def _records() -> dict[str, dict[str, str]]:
    records = {}
    for _, short, record, _, _ in MAPPINGS:
        body = braced_body(_raw(), f"item <'{short}'> {record} : LogicalToSoftwareSignalMappingRecord")
        body = re.sub(r"doc\s*/\*.*?\*/", "", body, flags=re.S)
        values = re.findall(r'^\s*attribute\s+:>>\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|[\w:]+)\s*;\s*$', body, re.M)
        records[record] = {name: value[1:-1] if value.startswith('"') else value for name, value in values}
    return records


def _texts() -> list[str]:
    """Every text of record of the model: each block comment and each record value."""
    raw = _raw()
    return [_flat(t) for t in re.findall(r"/\*(.*?)\*/", raw, re.S)] + re.findall(r'=\s*"((?:[^"\\]|\\.)*)"', raw)


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING + "\n", 1)[1].split("\n## ", 1)[0]


def _skeleton() -> list[str]:
    """The raw model as one line per declaration, the whole declaration up to its own `{` or `;` (whitespace
    collapsed), indented two spaces per brace depth, each body's members after it one level deeper. The `//` and
    `//* */` notes are left out; the header, each `doc` and each `comment` keep only `/*…*/` (the texts of record pin
    their words); every other `/* */` comment, a section comment, keeps its text."""
    raw = _raw()
    lines: list[str] = []
    pending, depth, at = "", 0, 0

    def emit(text: str) -> None:
        lines.append("  " * depth + " ".join(text.split()))

    while at < len(raw):
        if raw.startswith("//*", at):
            at = raw.index("*/", at + 3) + 2
        elif raw.startswith("//", at):
            end = raw.find("\n", at)
            at = len(raw) if end < 0 else end
        elif raw.startswith("/*", at):
            end = raw.index("*/", at + 2) + 2
            if re.fullmatch(r"\s*(?:doc|comment)\b[\w\s:,]*", pending) or not (lines or pending.strip()):
                emit(pending + " /*…*/")
                pending = ""
            elif pending.strip():
                pending += " /* " + " ".join(raw[at + 2:end - 2].split()) + " */ "
            else:
                emit("/* " + " ".join(raw[at + 2:end - 2].split()) + " */")
            at = end
        elif raw[at] in "\"'":
            end = raw.index(raw[at], at + 1) + 1
            pending += raw[at:end]
            at = end
        elif raw[at] == "{":
            emit(pending + " {")
            pending, depth, at = "", depth + 1, at + 1
        elif raw[at] == ";":
            emit(pending + ";")
            pending, at = "", at + 1
        elif raw[at] == "}":
            if pending.strip():
                emit(pending)
            assert depth > 0, "a } that closes no body"
            pending, depth, at = "", depth - 1, at + 1
        else:
            pending += raw[at]
            at += 1
    if pending.strip():
        emit(pending)
    assert depth == 0, "a body that is never closed"
    return lines


# -- the package and its elements ----------------------------------------------------------------------------------


def test_the_charter_names_the_package_after_the_logical_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part eeArchitectureCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(LOGICAL_PACKAGE) + 1 == len(names) - 1
    assert names.count(PACKAGE) == 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_header_states_its_text_of_record():
    assert _header_paragraphs() == HEADER_PARAGRAPHS


def test_the_header_records_the_three_decisions_in_order():
    paragraphs = _header_paragraphs()
    index = paragraphs.index("The realization (owner decisions of 2026-11-26):")
    bullets = [b for b in re.split(r"(?:^|\s)- (?=[A-Z])", paragraphs[index + 1]) if b]
    assert [b[:40] for b in bullets] == ["Phase 8 realizes the vehicle network in ",
                                         "The network side of the central computer",
                                         "Each driving command is one CAN FD frame"]
    assert "This package places no software." in bullets[0]
    assert "No vehicle signal broker and no other element sits between the take and the frame." in bullets[1]
    assert "inside an IEEE 1722 packet" in bullets[2] and "repacks nothing" in bullets[2]
    assert "so the design keeps each part unchanged (REQ-EE-004) and has each element pass the detection parts on" \
        in bullets[2]
    assert " ".join(paragraphs).count("owner decisions of 2026-11-26") == 1
    alternatives = paragraphs[paragraphs.index("Alternatives recorded and not selected:") + 1]
    assert "classical CAN, more than one frame per driving command, which the actuation ECU joins again." in \
        alternatives
    assert not re.search(r"\b(?:two|three|four|\d+) frames\b", alternatives), "no frame count the model cannot hold"


def test_the_package_imports_one_by_one():
    imports = re.findall(r"^\s*private\s+import\s+([\w:*]+)\s*;", _code(), re.M)
    assert sorted(imports) == sorted(IMPORTS), "the imports, each once; their order is free"
    assert len(re.findall(r"\bimport\b", _code())) == len(IMPORTS)
    assert not re.search(r"\bpublic\s+import\b", _code())


def _declaration(definition: str) -> str:
    return f"part def {definition}" + (f" :> {BASES[definition]}" if BASES[definition] else "")


def test_the_three_nodes_that_carry_logical_elements_are_the_physical_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*(?::>\s*([\w,\s]+?))?\s*\{", code)
    assert [(name, " ".join(bases.split()) or None) for name, bases in declared] == list(BASES.items())
    assert [name for name, bases in BASES.items() if bases and "PhysicalAllocationElement" in bases] == \
        ELEMENT_DEFINITIONS
    assert len(re.findall(r"\bPhysicalAllocationElement\b", code)) == len(ELEMENT_DEFINITIONS) + 1, "the import too"
    for definition in ELEMENT_DEFINITIONS:
        assert _doc(_declaration(definition)).startswith("Carries "), definition
    for definition in LINKS + ["EEOtherZoneController"]:
        doc = _doc(_declaration(definition))
        assert "receives no allocation" in doc or "carries no logical element" in doc, definition


@pytest.mark.parametrize("definition", list(PORTS), ids=list(PORTS))
def test_each_definition_declares_exactly_its_ports(definition):
    body = _direct(_definition(definition))
    assert re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M) == [tuple(p) for p in PORTS[definition]]
    assert len(re.findall(r"\bport\b", body)) == len(PORTS[definition])


@pytest.mark.parametrize("definition", list(PARTS), ids=list(PARTS))
def test_each_container_holds_exactly_its_parts_binds_and_connections(definition):
    body = _direct(_definition(definition))
    parts = re.findall(r"^\s*(ref\s+part|part)\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert [(" ".join(kind.split()), name, typ) for kind, name, typ in parts] == [tuple(p) for p in PARTS[definition]]
    assert len(re.findall(r"\bpart\b", body)) == len(PARTS[definition])
    assert _binds(definition) == [tuple(b) for b in BINDS[definition]]
    assert _connections(definition) == [tuple(c) for c in CONNECTIONS[definition]]
    assert len(re.findall(r"\bconnection\b", body)) == len(CONNECTIONS[definition])


def test_the_nodes_and_links_hold_ports_and_nothing_else():
    for definition in PORTS:
        if definition == CENTRAL:
            continue
        body = _definition(definition)
        assert not re.search(r"\b(part|action|perform|flow|item|attribute|connection|bind|interface)\b", body), \
            definition


def test_the_items_and_the_port_definitions_carry_one_item_each_in_one_direction():
    code = _code()
    declared = re.findall(r"\bitem\s+def\s+(\w+)\s*(?::>\s*(\w+)\s*)?\{", code)
    assert [(name, parent or None) for name, parent in declared] == [(n, p) for n, (p, _) in ITEMS.items()]
    for name, (_, attributes) in ITEMS.items():
        body = braced_body(code, f"item def {name}")
        assert re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body) == attributes, name
    assert re.findall(r"\bitem\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(code, "item def EECommandPacket")) == [PACKET_ITEM]
    assert re.findall(r"\bport\s+def\s+(\w+)", code) == list(PORT_ITEMS) + [ATTACHMENT]
    for port_def, (direction, item, item_type) in PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)]
    assert braced_body(code, f"port def {ATTACHMENT}").split() == ["doc"], "an attachment carries no item"
    used = {port_def for ports in PORTS.values() for _, port_def in ports}
    assert used == set(PORT_ITEMS) | {ATTACHMENT}, "every port definition is used, and only these"


def test_the_frame_keeps_the_inherited_quantities_and_types_two_values_by_vss_beside_them():
    code = _strings_blanked(_code())
    assert re.findall(r"(?<!:):(?!:)\s*(Vehicle_\w+)", code) == ["Vehicle_ADAS_Driving_Command_SteeringAngle",
                                                                 "Vehicle_ADAS_Driving_Command_Acceleration"]
    assert "COVESA_VSS" not in code and "SteerAngleTarget" not in code and "VssSignalMetadata" not in code
    frame = braced_body(code, "item def EECommandFrame :> EEDrivingCommandInput")
    assert ":>>" not in frame, "the inherited parts are never redefined"
    doc = _doc("item def EECommandFrame :> EEDrivingCommandInput")
    for phrase in ("eeSteeringAngleSignal, the value in degrees of the inherited steeringAngle",
                   "eeAccelerationSignal, the value in m/s² of the inherited acceleration",
                   "these three are protocol fields, no vehicle signal",
                   "The five parts fit the data of one CAN FD frame"):
        assert phrase in doc, phrase
    assert not re.search(r"\b\d+\s*bytes?\b", doc), "no byte layout that the model cannot hold"


def test_every_node_that_software_runs_on_is_a_vehicle_compute_node_and_no_link_is():
    nodes = [name for name, bases in BASES.items() if bases and "VehicleComputeNode" in bases]
    assert nodes == NODES
    assert not set(LINKS) & set(nodes) and BASES["EECentralComputerNetworkSide"] == "PhysicalAllocationElement"
    for node in NODES:
        assert TYPING in _doc(_declaration(node)), node
    assert len(re.findall(r"\bVehicleComputeNode\b", _code())) == len(NODES) + 1, "the import too"


def test_the_central_computer_is_a_vehicle_compute_node_with_its_network_side_alone():
    body = _direct(_definition(CENTRAL))
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M) == [("eeNetworkSide",
                                                                         "EECentralComputerNetworkSide")]
    assert not re.search(r"\bref\s+part\b", _code()), "no layer is referenced in the E/E realization"
    assert "private import DE4SDV_ExecutionEnvironments::VehicleComputeNode;" in _code()
    assert re.findall(r"\b(\w+)\s*:(?![:>])\s*EECentralComputer\b", _code()) == ["eeCentralComputer"]
    doc = _doc(_declaration(CENTRAL))
    assert "Of it only its network side is an element of the vehicle network" in doc
    assert "No platform layer is claimed either." in doc


def test_no_part_is_a_bench_host_a_platform_layer_or_software():
    code = _code()
    assert not re.search(r"\b(?:AAOSGuestHost|DriverAssistanceSCOREHost|ClosedLoopDrivingLinuxHost|\w*GuestHost|"
                         r"LinuxPlatform|KVMHypervisor|OSPlatformLayer|HypervisorLayer|HardwareLayer|EclipseSCORE|"
                         r"VehicleNetworkBoundary|EngineeringComputeNode|NXPVehicleComputeCandidate|"
                         r"HmiDisplayCentralComputer)\b", code)
    assert not re.search(r"\b(?:Application|Service|Adapter|Process|Software)\w*\s*[;{]", _strings_blanked(code))
    assert not re.search(r"\b(?:deployedTo|interface|perform|action|flow|exhibit|succession|ref)\b",
                         _strings_blanked(code))
    assert "DE4SDV_SDVPlatformStack" not in code and "DE4SDV_HmiDisplay" not in code


def test_the_bench_appears_only_where_something_stands_in_or_is_asked():
    for text in _texts():
        for sentence in re.split(r"(?<=[.;])\s+", text):
            if re.search(r"(?i)\b(?:bench|testbed|System 2)\b", sentence):
                assert any(form in sentence for form in STAND_IN), sentence


def test_the_system_its_usage_and_its_structure_describe_the_vehicle():
    system = _doc(f"part def {SYSTEM}")
    assert system.startswith("The physical realization of the vehicle network in the vehicle: the central computer")
    allowed = "No part here stands for an element of the bench."
    assert system.count(allowed) == 1 and "bench" not in system.replace(allowed, "")
    assert "bench" not in _doc(f"part {SYSTEM_USAGE} : {SYSTEM}")
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", _code(), re.M) == [SYSTEM_USAGE]
    assert braced_body(_code(), f"part {SYSTEM_USAGE} : {SYSTEM}").split() == ["doc"]
    package = _direct(braced_body(_code(), f"package {PACKAGE}"))
    assert re.findall(r"^\s*part\s+(?!def\b)(\w+)\s*:(?!\s*IncrementGap\b)", package, re.M) == [SYSTEM_USAGE], \
        "the one usage of the system, beside the gaps"


# -- the routes ----------------------------------------------------------------------------------------------------


def test_each_connection_runs_from_an_out_port_to_an_in_port_of_one_item():
    for name, source, target in CONNECTIONS[SYSTEM]:
        ends = _end(SYSTEM, source), _end(SYSTEM, target)
        if ATTACHMENT in ends:
            assert ends == (ATTACHMENT, ATTACHMENT), name
            continue
        assert PORT_ITEMS[ends[0]][0] == "out" and PORT_ITEMS[ends[1]][0] == "in", name
        assert PORT_ITEMS[ends[0]][2] == PORT_ITEMS[ends[1]][2], name
    for own, inner in BINDS[CENTRAL]:
        assert dict(PORTS[CENTRAL])[own] == dict(PORTS["EECentralComputerNetworkSide"])[inner.split(".")[1]]
    assert len(re.findall(r"\bconnect\b", _code())) == len(CONNECTIONS[SYSTEM])


def test_the_routes_pass_the_elements_of_phase_5_and_nothing_reaches_the_other_zone():
    connections = _connections(SYSTEM)
    hops = [(source.split(".")[0], target.split(".")[0]) for _, source, target in connections
            if ATTACHMENT not in (_end(SYSTEM, source), _end(SYSTEM, target))]
    # the zone route of REQ-EE-003, the direct route, and the applied command
    assert hops == [("eeCentralComputer", "eeEthernetBackbone"), ("eeEthernetBackbone", "eeActuationZoneController"),
                    ("eeActuationZoneController", "eeActuationZoneCANFDBus"),
                    ("eeActuationZoneCANFDBus", "eeActuationECU"), ("eeCentralComputer", "eeDirectCANFDLink"),
                    ("eeDirectCANFDLink", "eeActuationECU"), ("eeActuationECU", "eeActuatedVehicle")], hops
    sources = [source.split(".")[0] for _, source, _ in connections]
    assert sources.count("eeCentralComputer") == 2, "the backbone and the direct link"
    other = [(s, t) for _, s, t in connections if "Other" in s or "Other" in t]
    assert all(ATTACHMENT in (_end(SYSTEM, s), _end(SYSTEM, t)) for s, t in other) and len(other) == 2
    assert not [t for _, _, t in connections if t.startswith("eeCentralComputer.")], "nothing leads back"
    assert [t for _, _, t in connections if t.startswith("eeActuationECU.")] == [
        "eeActuationECU.eeZoneBusFrameIn", "eeActuationECU.eeDirectLinkFrameIn"]


def test_the_boundary_interface_is_typed_by_the_driving_increments_payload_and_left_open_inward():
    assert PORT_ITEMS["EEBoundaryCommandIn"] == ("in", "eeDrivingCommand", "DrivingCommandEventPayload")
    assert ("eeDrivingCommandIn", "EEBoundaryCommandIn") in PORTS["EECentralComputerNetworkSide"]
    assert "eeDrivingCommandIn" not in _strings_blanked(braced_body(_code(), f"part def {SYSTEM}"))
    assert not re.search(r"\b(?:item|port)\s+def\s+DrivingCommandEvent", _code()), "imported, never redeclared"
    assert "placed with the software realization" in _doc(f"view {PATH_VIEW}")


def test_the_frame_crosses_unchanged_and_the_clock_is_read_at_the_take_and_at_the_arrival():
    zone = _doc(_declaration("EEActuationZoneController"))
    assert "It unpacks the frame and repacks nothing" in zone and "It reads no clock for the driving command." in zone
    side = _doc(_declaration("EECentralComputerNetworkSide"))
    assert "When it takes a driving command it reads the vehicle's clock." in side
    assert "computes none of the detection parts anew (REQ-EE-007)" in side
    ecu = _doc(_declaration("EEActuationECU"))
    assert "reads the vehicle's clock when one arrives" in ecu and "The stop response needs no vehicle speed." in ecu
    for link in ("EEEthernetBackbone", "EEActuationZoneCANFDBus", "EEDirectCANFDLink"):
        assert "computes nothing" in _doc(_declaration(link)), link
    assert "How the nodes share it, time synchronisation between them, stays out of scope (eeTimingOutOfScope)." in \
        " ".join(_header_paragraphs())


# -- allocations, mappings and the topology and route requirements --------------------------------------------------


def test_each_logical_element_is_allocated_to_the_nodes_that_carry_it():
    code = _code()
    rows = re.findall(r"\ballocation\s+(\w+)\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*;", code)
    assert rows == [(name, f"{LOGICAL_SYSTEM}::{logical}", f"{SYSTEM_USAGE}::{physical}")
                    for name, logical, physical in ALLOCATIONS]
    assert len(re.findall(r"\ballocation\b", code)) == len(ALLOCATIONS) + len(MAPPINGS)
    targets = {}
    for _, logical, physical in ALLOCATIONS:
        targets.setdefault(logical, []).append(physical.split("::")[-1])
    assert targets == {"eeIdentityRecorder": ["eeNetworkSide"],
                       "eeCommandCarrier": ["eeNetworkSide", "eeActuationZoneController"],
                       "eeActuationEnd": ["eeActuationECU"]}
    logical = strip_comments(LOGICAL.read_text(encoding="utf-8"))
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*\w+\s*;", braced_body(logical, f"part def {LOGICAL_SYSTEM}"),
                      re.M) == list(targets)
    ends = re.findall(r"\ballocation\s+\w+(?:\s*:\s*\w+)?\s+allocate\s+\S+\s+to\s+([^\s;{]+)", code)
    assert len(ends) == len(ALLOCATIONS) + len(MAPPINGS)
    placed = {re.split(r"::|\.", end)[1] for end in ends}
    assert placed == {"eeCentralComputer", "eeActuationZoneController", "eeActuationECU"}, \
        "no link, no other zone and not the vehicle is an allocation target"


def test_each_crossing_has_one_signal_mapping_with_a_complete_record():
    code = _code()
    found = re.findall(r"\ballocation\s+(\w+)\s*:\s*SystemToSoftwareSignalMappingCandidate\s+allocate\s+(\S+)\s+to\s+"
                       r"([^\s{;]+)\s*\{\s*item\s+<'([A-Z-]+)'>\s+(\w+)\s*:\s*LogicalToSoftwareSignalMappingRecord",
                       code)
    assert found == [(name, f"{LOGICAL_SYSTEM}::{logical}", f"{SYSTEM_USAGE}.{target}", short, record)
                     for name, short, record, logical, target in MAPPINGS]
    assert len(re.findall(r"\bSystemToSoftwareSignalMappingCandidate\b", code)) == len(MAPPINGS) + 1
    for record, values in _records().items():
        assert tuple(values) == RECORD_ATTRIBUTES, record
        assert values["disposition"] == "SignalMappingDisposition::candidate", record
        assert values["owner"] == "DE4SDV maintainers", record
        assert values["nextAction"].endswith("; none is started"), record
        assert values["evidenceOrGap"].startswith("no runtime evidence of record; "), record
    realized = {logical for _, _, _, logical, _ in MAPPINGS}
    assert realized == {"eeIdentityRecorder", "eeCommandCarrier", "eeActuationEnd"}, "each realized logical element"


@pytest.mark.parametrize("record", [m[2] for m in MAPPINGS], ids=[m[1] for m in MAPPINGS])
def test_each_record_states_its_values_of_record(record):
    assert _records()[record] == RECORD_VALUES[record]
    short = next(m[1] for m in MAPPINGS if m[2] == record)
    assert _doc(f"item <'{short}'> {record} : LogicalToSoftwareSignalMappingRecord") == RECORD_DOCS[record]


def test_every_item_that_is_no_vehicle_signal_says_so_and_the_frame_names_its_vss_types():
    for _, short, record, _, _ in MAPPINGS:
        source = _records()[record]["semanticSource"]
        if short in ("MAP-EE-SCORE-COMMAND", "MAP-EE-ZONE-BUS-FRAME", "MAP-EE-DIRECT-LINK-FRAME"):
            assert "Vehicle_ADAS_Driving_Command_SteeringAngle" in source, short
        if short != "MAP-EE-APPLIED-COMMAND":
            assert "no vehicle signal" in source, short
        else:
            assert "EEActuationOutput" in source and "Vehicle_ADAS_Driving_Command_Acceleration" in source


def test_the_topology_and_route_requirements_are_carried_by_dependencies_from_the_physical_system():
    code = _code()
    assert re.findall(r"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)\s*;", code) == [
        (name, SYSTEM, requirement) for name, requirement in DEPENDENCIES]
    assert len(re.findall(r"\bdependency\b", code)) == len(DEPENDENCIES)
    for _, requirement in DEPENDENCIES:
        assert f"private import DE4SDV_EEArchitectureNeedsRequirements::{requirement};" in code
    assert not re.search(r"\ballocate\s+\w*req[A-Z]", code), "no allocation names a requirement"
    assert len(re.findall(r"\breq[A-Z]\w*", code)) == 2 * len(DEPENDENCIES), "the imports and the dependencies"


# -- comments, gaps and texts of record ----------------------------------------------------------------------------


def test_the_comments_record_what_phase_8_settled_on_the_framing_records():
    code = _code()
    assert dict(re.findall(r"\bcomment\s+(\w+)\s+about\s+(\w+)\s*$", code, re.M)) == COMMENTS
    for name, record in COMMENTS.items():
        assert _comment(name) == COMMENT_TEXTS[name], name
        assert f"private import DE4SDV_EEArchitectureFraming::{record};" in code, record


def test_the_gaps_of_the_realization_are_recorded_without_short_names_and_with_no_disposition():
    code = _code()
    assert re.findall(r"\bpart\s+(\w+)\s*:\s*IncrementGap\s*\{", code) == GAPS, "the increment's form: no short name"
    assert not re.search(r"<'", re.sub(r"\bitem\s+<'MAP-EE-[A-Z-]+'>", "", code)), "short names on the records only"
    assert len(re.findall(r"\bIncrementGap\b", code)) == len(GAPS)
    for name in GAPS:
        body = braced_body(code, f"part {name} : IncrementGap")
        assert body.split() == ["doc"], "open, with no disposition yet"
        assert _doc(f"part {name} : IncrementGap") == GAP_DOCS[name], name
    handover = GAP_DOCS["gapEECentralComputerHandover"]
    assert handover.startswith("The realization of the HMI display, DE4SDV_HmiDisplayPhysicalSoftwareRealization, "
                               "declares the central computer too, as HmiDisplayCentralComputer with the VMs")
    assert "the declaration that the realization of the HMI display is to import" in handover
    assert not re.search(r"\.sysml|:\d", handover), "a model text names the element, never a file or a line"
    configuration = GAP_DOCS["gapEEConfigurationNamedByRole"]
    assert "so phase 8 does not name the files yet" in configuration
    assert "REQ-EE-010 cannot be verified as worded until they are named, which is due before phase 10." in \
        configuration
    term = _flat(re.search(r"- Configuration:(.*?)(?=- Network identity:)", NEEDS.read_text(encoding="utf-8"),
                           re.S).group(1))
    assert "every file" in term, "the term reads files, which the gap says are named by role only"


@pytest.mark.parametrize("declaration", list(DOCS), ids=[[w for w in d.split() if w != "def"][1] for d in DOCS])
def test_each_element_states_its_text_of_record(declaration):
    assert _doc(declaration) == DOCS[declaration]


def test_every_doc_of_the_package_is_pinned_and_the_notes_and_headings_are_these():
    assert len(re.findall(r"\bdoc\s*/\*", _raw())) == len(DOCS) + len(RECORD_DOCS) + len(GAP_DOCS)
    assert re.findall(r"//\s*(.*)", _raw()) == NOTES
    body = _raw().split(f"package {PACKAGE}", 1)[1]
    plain = [_flat(t) for lead, t in re.findall(r"(\bdoc\s*|\bcomment\s+\w+\s+about\s+\w+\s*)?/\*(.*?)\*/", body, re.S)
             if not lead]
    assert plain == HEADINGS


def test_the_element_docs_make_no_assurance_claim():
    head = " ".join(_header_paragraphs())
    disclaimer = ("Nothing in this package claims that a requirement is met, that a case ran or that the bench has "
                  "shown anything.")
    assert head.count(disclaimer) == 1
    for text in _texts():
        assert not APPROVAL.search(text.replace(disclaimer, "")), text[:80]
    assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|constrainedBy|satisfy|verify)\b",
                         _strings_blanked(_code()))


def test_no_text_of_phase_8_quotes_the_owner_or_carries_a_banned_word_or_a_private_finding():
    section = _guide_section(_guide())
    texts = {"model": " ".join(_texts()), "guide section": section,
             "this test": Path(__file__).read_text(encoding="utf-8")}
    for label, text in texts.items():
        flat = " ".join(text.split()).lower()
        assert not PAST_BEHAVIOR.search(flat) and not CLAUSE_NUMBER.search(flat), label
        assert not re.search(r"\b(?:v\d+\.\d+|r\d\d-\d\d|release \d|version \d)", flat), label
        for size in (1, 2, 3, 4, 5):
            words = re.findall(r"[a-z0-9]+", flat)
            grams = {" ".join(words[i:i + size]) for i in range(len(words) - size + 1)}
            assert not {hashlib.sha256(g.encode()).hexdigest() for g in grams} & set(PRIVATE_SHA256), (label, size)
    for label in ("model", "guide section"):
        flat = _flat(texts[label])
        assert not re.search(r"(?i)\b(?:the owner said|owner's words|in his words|he said)\b", flat), label
        assert not re.search(r"(?i)\b(?:issue|pull request|PR)\s*#?\d+|#\d{2,}", flat), label
        assert not re.search(r"\b\d+(?:\.\d+)?\s*ms\b", flat.replace("50 ms", "").replace("100 ms", "")
                             .replace("200 ms", "").replace("300 ms", "")), "a time figure beside the requirements'"
    prose = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", section)
    assert '"' not in prose and "\u201c" not in prose and "\u201d" not in prose, "the section quotes nobody"


def test_the_package_holds_no_connector_kind_beside_its_connections_and_the_two_binds():
    """Read over the whole code with docs, notes and strings removed, so no doc word trips it and no level escapes:
    no flow, binding, interface, message or succession anywhere, and the only binds are the two of the central
    computer."""
    code = _strings_blanked(_code())
    assert not re.search(r"\b(?:flow|binding|interface|message|succession|connector|perform|exhibit)\b", code)
    assert len(re.findall(r"\bbind\b", code)) == len(BINDS[CENTRAL]) == 2
    assert len(re.findall(r"\bconnection\b", code)) == len(CONNECTIONS[SYSTEM])
    assert len(re.findall(r"\ballocation\b", code)) == len(ALLOCATIONS) + len(MAPPINGS)
    assert len(re.findall(r"\bdependency\b", code)) == len(DEPENDENCIES)
    assert not re.search(r"[^\x00-\x7f]", code), "the code is ASCII: only docs, comments and values hold others"


def test_the_package_is_exactly_its_skeleton():
    """The whole code of the package, pinned line by line: every declaration at its own depth, whole, in order.
    Because the skeleton pins the code whole, a change to any declaration of the package fails it: a member added,
    removed, moved or reordered at any depth, a changed keyword, name, type, value or binding, a changed section
    comment, a brace that closes no body or a body never closed. Its limit: the header, the docs and the `//` notes
    are pinned by the texts of record and NOTES, which read the one copy of each declaration in the file (a note
    that copies a declaration fails them)."""
    expected = SKELETON.replace("\\\n", "").splitlines()
    actual = _skeleton()
    assert len(expected) >= 200, "the skeleton must not be vacuous"
    for number, (line, pinned) in enumerate(zip_longest(actual, expected), 1):
        assert line == pinned, f"skeleton line {number}: {line!r}, pinned {pinned!r}"


def test_the_package_declares_no_name_that_another_model_package_declares():
    kinds = r"(?:package|part def|port def|item def|part|port|item|connection|allocation|concern|view|viewpoint|" \
            r"dependency|comment|attribute)"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    # the record values are blanked, so a word after a keyword inside a value is no name; depth and
    # showAnnotationRows are the views' attributes
    declared = set(anywhere.findall(_strings_blanked(_code()))) - {"def", "depth", "showAnnotationRows"}
    assert len(declared) >= 90, "the population of the check must not be vacuous"
    assert all(name.startswith(("ee", "EE", "gapEE")) for name in declared - {PACKAGE}), sorted(
        name for name in declared if not name.startswith(("ee", "EE", "gapEE")))
    definitions = re.compile(r"\b\w+\s+def\s+(\w+)")
    usages = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(?=(\w+))")
    taken: dict[str, list[str]] = {}
    scanned = 0
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            scanned += 1
            code = strip_comments(path.read_text(encoding="utf-8"))
            for name in definitions.findall(code) + usages.findall(code):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert scanned > 100, "the population of the scan must not be vacuous"
    assert not taken, f"declared in another package too: {taken}"


# -- views -----------------------------------------------------------------------------------------------------------


def test_the_package_publishes_exactly_one_view_per_question():
    assert re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M) == list(VIEWS)


@pytest.mark.parametrize("view_name", list(VIEWS), ids=list(VIEWS))
def test_each_view_frames_its_concerns_and_exposes_its_content(view_name):
    view_type, render, exposes, viewpoint_type, frames = VIEWS[view_name]
    view = braced_body(_code(), f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{viewpoint_type}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == exposes
    assert re.findall(r"\bfilter\s+([^;]+);", view) == VIEW_FILTERS[view_name]
    if render:
        assert render in view
    else:
        assert "render as" not in view, "the view type selects the kind"


def test_the_path_view_names_every_part_port_and_connection_and_the_tree_sets_nothing():
    path = braced_body(_code(), f"view {PATH_VIEW}")
    assert re.findall(r"\battribute\s+(\w+)\s*=\s*([^;]+);", path) == [("depth", "-1"),
                                                                       ("showAnnotationRows", "false")]
    assert "::**" not in path and "::*;" not in path, "named exposes only"
    assert "attribute" not in braced_body(_code(), f"view {STRUCTURE_VIEW}")
    named = set(VIEWS[PATH_VIEW][2])
    for _, source, target in CONNECTIONS[SYSTEM]:
        for end in (source, target):
            assert f"{SYSTEM_USAGE}::{end.replace('.', '::')}" in named, end
    doc = _doc(f"view {PATH_VIEW}")
    for phrase in ("(eeCommandRouteExchangeConcern)", "(eeCommandItemConcern)", "which carry no item",
                   "Each edge joins two ports, and each port definition on a route carries the one item that its "
                   "exchange moves; the attachments carry none."):
        assert phrase in doc, phrase


def test_the_matrix_maps_the_logical_elements_to_the_nodes_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows, columns, cells = (braced_body(view, f"view :>> {axis}") for axis in ("rowView", "columnView", "cellView"))
    exposes = VIEWS[MATRIX_VIEW][2]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == exposes[:3]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == exposes[3:6]
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert (metadata.title, metadata.description, metadata.row_label, metadata.column_label) == GRID


@pytest.mark.parametrize("concern_name", list(CATALOGUE_CONCERNS), ids=list(CATALOGUE_CONCERNS))
def test_each_phase_8_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern) == stakeholders
    assert len(re.findall(r"\bconcern\s+\w+\s*:", _code())) == len(CATALOGUE_CONCERNS)


def test_the_phase_1_physical_concerns_are_framed_here_in_their_domain_and_need_no_deviation():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    code = _code()
    for concern, catalogue in FRAMING_CONCERNS.items():
        assert re.search(rf"\bconcern\s+{concern}\s*:\s*{catalogue}\b", framing), concern
        assert f"private import DE4SDV_EEArchitectureFraming::{concern};" in code, concern
        assert not re.search(rf"\bconcern\s+{concern}\b", code), "framed, never redeclared"
    import test_views_per_phase as views

    assert not [key for key in views.KNOWN_DEVIATIONS if key[0] == "INC-EE-001"], "the method's own list"


# -- registrations and the guide -----------------------------------------------------------------------------------


def test_the_allocation_file_is_governed_with_its_three_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.EE_P == MODEL
    assert trace.ALLOCATION_FILES[trace.EE_P] == (
        (trace.EE_P, trace.EE_L), {(trace.LOGICAL, trace.PHYSICAL): len(ALLOCATIONS)},
        {"SystemToSoftwareSignalMappingCandidate": len(MAPPINGS)}, (trace.LOGICAL, trace.PHYSICAL))
    assert trace.GOVERNED[trace.EE_P] == (trace.PHYSICAL, set(ELEMENT_DEFINITIONS))
    assert trace.LINEAGE_FILES.index(trace.EE_P) == trace.LINEAGE_FILES.index(trace.EE_L) + 1
    assert trace.NOT_ENDPOINTS[trace.EE_P] == set(NOT_ELEMENTS)


def test_the_guide_has_a_phase_8_section_and_names_the_next_obligation():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Logical architecture (Phase 7)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    assert f"]({GUIDE_LINK})" in raw_section
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks == GUIDE_BLOCKS, "every block of the section, whole and in order, as it says"
    assert all(len(line) <= 78 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 78"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1
    assert "and Phase 7 logical architecture, proposal.**" not in flat, "the status line moved to phase 8"
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 8**:" not in flat
    assert flat.count("The next model obligation is") == 1
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_ee_architecture_physical_ee_realization.py" in check
