/*
 * DE4SDV E/E architecture capability classification model slice.
 *
 * INC-EE-001, phase 3, adds no characteristic that distinguishes member
 * products, so it records no feature candidate and no deferred scope.
 * Core elements are common by default and get no record. The topology of
 * the vehicle network gets none: the increment judges one topology for
 * one configuration, its framing puts a second topology and any
 * variability of the E/E architecture out of scope, and no member,
 * configuration or product model of the product line holds a vehicle
 * network. The zone controllers, the backbone, the CAN buses, the direct
 * link and the actuation ECU get none: they are parts of that topology.
 * The two routes of the driving command get none: they are a design
 * alternative inside that one topology, the increment judges both, and
 * its lifecycle decision names the route of the reference vehicle
 * network; no member differs by its route. The driving command gets none:
 * it is the command of the driver-assistance increment.
 * DrivingCommandSource, the source of the driving command in the
 * operational context, gets none: what gives the command is the
 * driver-assistance increment's to classify. The Eclipse S-CORE path
 * (SCORECommandAndWarningPath) gets none: Eclipse S-CORE is a feature of
 * the feature model (eclipseSCORE), and this increment changes no
 * feature. The vehicle gets none: this increment varies nothing of it.
 * The faults of the network get none: phase 5 states what the command
 * path does under them and phase 10 judges it. The verdicts get none:
 * they are evidence of phase 10, from a testbed of System 2, which the
 * governed scope keeps out of product variability. The medium of the
 * direct link gets none: phases 6 to 8 decide it. The vehicle-target
 * compute family gets none: the increment selects no compute target for
 * the nodes of the network, and the family is the deferred vehicle
 * runtime variability of the governed scope. Vehicle-Target AEBS and the
 * independence of the protected emergency command path get none: they
 * stay common, and this increment does not carry the AEBS command. The
 * items that the framing puts out of scope get none: they are
 * out-of-scope items of the framing.
 */

package DE4SDV_EEArchitectureCapabilityClassification {
  comment eeNetworkScopeDecisions about DE4SDV_EEArchitectureFraming::gapEENetworkInProductLine
  /*
   * Phase 3 classifies the vehicle network against the governed scope as it
   * stands and names the scope decisions that the lifecycle decision of
   * this increment needs. This increment admits nothing; a scope change
   * follows the change control of ADR 0014.
   * - The reference vehicle network: no member differs by it, so it is no
   *   feature candidate. Whether the governed scope takes it, with the
   *   route that the decision names, as common content of every member is
   *   open.
   * - The common content: Vehicle-Target AEBS and the independence of the
   *   protected emergency command path stay common; ADR 0023 decision 5
   *   keeps them common to the three planned members it names, once its
   *   scope pull request lands. What a common vehicle network means for
   *   that path and for the hand-off to the brake ECU (gapEEBrakeHandoff)
   *   is open.
   * - Later topologies: a second topology, or a route that tells members
   *   apart, would be variability that the governed scope does not hold;
   *   Integration Mode is the only product variability that the governed
   *   scope admits (ADR 0023 decision 2). Whether such variability enters
   *   the scope as deferred variability is open.
   * - The configuration: no feature of the feature model expresses the
   *   vehicle network, so a configuration selects none for it.
   */

  comment eeStackClassification about DE4SDV_EEArchitectureFraming::gapEEStackAndNetworkBoundary
  /*
   * Phase 3's share of the gap, the classification: the platform stack, the
   * vehicle-target execution-environment family and VehicleNetworkBoundary
   * get no feature from this increment, and this increment changes none of
   * them. In the operational context the driving command enters the vehicle
   * network from the Eclipse S-CORE path (asmEEScoreCommandSource), and the
   * context reuses no VehicleNetworkBoundary of the AAOS SDV middleware
   * boundary. How the network side of the central computer relates to the
   * SoC and the hardware layer of the platform stack is open for phases 6
   * to 8. Whether phase 8 allocates a node of the network to the
   * vehicle-target family is open for phase 8.
   */
}
