# E/E architecture: upstream provenance

These are the public sources that the texts of the E/E architecture increment,
INC-EE-001, read: the framing for its gap on the zone controller route, and
phase 8 for the transport of the command frame. They are not an adopted
dependency set or an execution manifest. No upstream implementation is
vendored. For this increment DE4SDV has built and run nothing.

## Zone controller route

Read for the framing of INC-EE-001 on 2026-11-17. The pages carry no revision
unless one is named here. They are the sources of the gap
`gapEEZoneRouteInVehicles` of the [framing model](ee_architecture_framing.sysml),
and each supports it only as far as its entry says.

- [AUMOVIO, zone control units](https://www.aumovio.com/en/solutions/vehicle-e-e-architectures/server-zone-architecture/zone-control-units.html),
  a supplier's product page. It names a zone control unit a "Local gateway
  within a physical zone with Ethernet backbone connection to vehicle server
  (HPC)", and lists suspension, a chassis function, among the real-time
  functions that such units run. It also names the "Ability to host critical
  x-Domain real-time functions" and "safety levels up to ASIL C and in future
  ASIL D". Supports: a zone controller as the gateway between the backbone and
  the sensors and actuators of its zone, and real-time functions with a safety
  level on it. Does not support: a brake command on that route.
- [Texas Instruments, white paper on zone architectures](https://www.ti.com/lit/pdf/spry345),
  revision C (the document carries a copyright of 2024). Zone gateways
  distribute data to the sensors, actuators and ECUs of their zone and
  consolidate data for the central computing modules, and a zonal module has
  peripherals such as CAN FD or LIN to reach smart sensors and actuators. It
  gives powertrain and chassis control stricter latency targets than audio,
  and it states: "Transitioning of ADAS or power train and chassis control
  into the zone architecture may need more time." Supports: the topology of
  the increment. Weighs against: chassis commands on a zone route at the time
  of the paper.
- [Aptiv and Excelfore, wheel sensor data in a zonal architecture](https://standards.ieee.org/wp-content/uploads/import/documents/other/eipatd-presentations/2021/d1-15.pdf),
  slides of an IEEE Standards Association event of November 2021. Of the
  systems of that time the slides say: "Currently ALL wheel speed sensors
  connect DIRECTLY to the ABS/ESP ECU". Their concept wires the wheel speed
  sensors to the zone controllers, sends a packet over time-sensitive Ethernet
  to a central controller for each sensor pulse, and draws the "Brake
  Actuators separate from the Zone Controllers". The slides report a test of
  the concept. Supports: wheel speed pulses on a zone route as a concept, not
  as practice in vehicles. Weighs against: the brake command on a zone route.
- [General Motors engineering, Ethernet backbone](https://engineering.gm.com/home.detail.html/Pages/news/us/en/engineering/2026/jul/0722-ethernet-backbone-reshapes-vehicle-architecture.html),
  a blog post of July 2026. Zonal architectures aggregate input and output by
  location and "use the network backbone to connect that I/O to compute
  resources." The post states a plan for a centralized architecture in 2028,
  first on the Cadillac ESCALADE IQ, not a vehicle in production. It says that
  in that architecture "systems including propulsion, steering, braking,
  infotainment, and safety" are connected through the Ethernet backbone. It
  does not say whether the brake command passes through a zone controller.
  Supports: a central computer that reaches the input and output of its zones
  over the backbone, and braking on the backbone as a plan.

No source read shows a production vehicle whose brake command passes through a
zone controller. The framing therefore takes that route as a candidate beside
a direct link and judges both.

## Frame transport

Read for phase 8 of INC-EE-001 on 2026-11-26. It is the source of the
IEEE 1722 packet of the
[E/E realization](ee_architecture_physical_ee_realization.sysml), and supports
it only as far as this entry says.

- [AUTOSAR, the IEEE 1722 transport layer of the classic platform](https://www.autosar.org/fileadmin/standards/R23-11/CP/AUTOSAR_CP_SWS_IEEE1722TransportLayer.pdf),
  release R23-11. It transports "encapsulated bus frames (ACF_CAN,
  ACF_CAN_BRIEF and ACF_LIN)" over an IEEE 1722 stream, and an ACF_CAN message
  is a "Controller Area Network (CAN)/CAN with Flexible Data-Rate (CAN FD)
  message". Supports: one CAN FD frame carried whole inside an IEEE 1722
  packet on the backbone. Does not support: any claim on the timing of that
  transport or on the detection parts.

## Command source

The source of the driving command on the central computer is the one of the
earlier increments: the driving command that the driver-assistance increment
gives over the Eclipse S-CORE path. Its upstream sources and the revisions
read are in the [driving upstream record](../driving/upstream.md). This
increment reads no further upstream code for it.

## Upstream contact

DE4SDV has contacted no author of these sources and no upstream project about
this increment. No endorsement, review or rights clearance by them is
asserted.
