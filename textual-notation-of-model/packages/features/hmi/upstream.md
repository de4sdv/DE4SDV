# HMI display: upstream provenance

These are inspection anchors of the HMI display increment, INC-HMI-001, not an
adopted dependency set or an execution manifest. No upstream implementation is
vendored. For this increment DE4SDV has built and run nothing of these
projects.

## High availability renderer

Read for the framing of INC-HMI-001 on 2026-11-17: the display safety service
of AAOS SDV,
[`platform/packages/services/display_safety`](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3),
commit `951af0fd68b691a69bab68542c981291ad4cf1c3` of the branch
`android17-release`, and its device configuration
[`device/google/sdv_display_safety`](https://android.googlesource.com/device/google/sdv_display_safety/+/0971a46741bd2931c8c506e0afe950348af7c1d4),
commit `0971a46741bd2931c8c506e0afe950348af7c1d4` of the same branch, with
the documentation pages
[Display Safety](https://source.android.com/docs/automotive/sdv/display-safety)
and [DriverUI](https://source.android.com/docs/automotive/sdv/display-safety/driverui).
The pages carry no revision; they were read on the same day. Which revision a
bench runs is a decision of phase 8.

The design, as the documentation states it:

- DriverUI is an Android system app that renders the whole cluster display
  except the safety and regulatory elements, which the high availability
  renderer (HAR) renders. The AAOS SDV runs HAR in SDV Media, a guest VM that
  the documentation also calls the rapid boot VM, and DriverUI in the IVI VM.
- HAR renders the display elements that must be present quickly after a cold
  boot, and placeholder elements when Android is unavailable. The
  documentation calls it a quality management process.
- HAR's display plane sits on top of the Android IVI display plane. HAR keeps
  the areas of DriverUI transparent while heartbeat messages from DriverUI
  arrive, and makes them opaque with placeholders when the heartbeats stop.
- Google's reference implementation of the safety monitor carries no ASIL
  certification.

What the framing's gaps rest on, at the inspected commits:

- [Vehicle data catalog](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/vehicledata/sdv_vehicledata_catalog_v1/vehicledata.proto):
  a speed message (`VehicleSpeed`) and a generic boolean telltale message;
  the [topics](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/vehicledata/sdv_vehicledata_catalog_v1/vehicledata_system.vsidl)
  include `adas` and no collision warning, forward-collision warning or
  emergency braking signal.
- [Subscriptions of the HAR service](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/har-sdv-service/src/observe.rs):
  speed and gear switch to the topics `vehicle-speed-ext` and
  `current-gear-ext` when the property `use_ext_variants` is set; the
  telltales have no such variant.
- [UI model of the reference app](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/reference/harry-app-core/src/ui/model.rs)
  and its [presenter](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/reference/harry-app-core/src/ui/presenter.rs):
  the brake telltale is bound to the display; the `adas` telltale has no
  field, so the app stores it and draws it nowhere. The
  [chime configuration](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/harry-prebuilt/data/assets/sdv/config/harry-chimes-config.json)
  holds no collision chime.
- [Display designs](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/harry-prebuilt/data/assets/common/figma/):
  compiled design files named by the identity of their design document. A
  search of the names in the cluster's compiled file finds no `adas` telltale
  and no collision symbol. Design documents of the reference app, in the
  design tool's own format, are in
  [`reference/harry-app/data`](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/reference/harry-app/data/).
- [Driver-assistance scene of the reference code](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/reference/har-adas-viz/src/logic.rs):
  a demonstration whose vehicle state, with lanes, a lead car and a passing
  car, it computes from the time alone. Between 25 s and 30 s of its loop it
  draws a front-collision mark on the lead car. Whether the app on the SDV
  Media VM runs that scene is not traced.
- [Launch template of the two guest VMs](https://android.googlesource.com/platform/packages/services/display_safety/+/951af0fd68b691a69bab68542c981291ad4cf1c3/service/ds-toolkit/res/ds-multi-cvd-config-template.json):
  it sets the graphics mode of the SDV Media guest to
  `gfxstream_guest_angle_host_swiftshader`, which renders on the host's
  processor.

DE4SDV has not run HAR. Whether it renders on the DE4SDV guest host beside the
SDV Core and IVI VMs, how a producer in the SDV Core VM reaches HAR's topics,
and which IVI image or app sends the heartbeats are open (the framing's
assumption `asmHmiRendererWithoutGraphicsCard` and gap
`gapHmiRendererIntegration`).

## VisionPilot scene

Read for the framing of INC-HMI-001 on 2026-11-17: Autoware Foundation
VisionPilot at the commit that the
[driving upstream record](../driving/upstream.md#visionpilot) names for
INC-DRIVING-002, `014e0e7a56ee8e597c2cab8175233f74edd9b856`. That record holds
the project's licence and its general provenance.

What the framing's gaps rest on, at that commit:

- [Build options of the visualization](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/CMakeLists.txt):
  the top-down panel, which the file calls a heuristic occupancy view, is
  built only when the option `ENABLE_OCCUPANCY` is on, and the option is off
  by default.
- [Scene of the panel](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/occupancy_bridge.cpp):
  the lane points, the path that the candidate's lateral fusion fits to them,
  the vehicle's offset and heading in its lane, the detections, and the fused
  distance of the closest object in the path. The bridge takes the plan as an
  argument and does not read it. The lane points are placed on the road
  through the camera's homography, and the
  [panel](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/occupancy_view.cpp)
  places each detection on the road through the same homography. The panel
  also guesses a truck from a detection's projected width, gives each box a
  fixed size, and labels the closest object with its projected position. The
  [visualization](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp)
  hands the scene to the panel inside the application's process.
- [Detection levels](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp):
  a detection's class is a level relative to the path, not a type of object.
  The fusion reads level 1 as the same lane and level 2 as the adjacent lane;
  the [visualization's colours](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp)
  also name a level 3 and draw any other class as other.
- [Estimate of the closest object in the path](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp):
  a fused distance and a fused speed.

What the requirements of Phase 5 cite, at the same commit:

- [VisionPilot/app/vision_pilot.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/app/vision_pilot.cpp#L149-L150):
  the system plans on the closest object only when the fusion gives it as valid
  and nearer than 150 m.
- [VisionPilot/app/vision_pilot.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/app/vision_pilot.cpp#L177):
  the system hands its results to the visualization only when the setting
  `visualization_on` is on.
- [VisionPilot/modules/models/include/models/inference.hpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/models/include/models/inference.hpp#L38-L52):
  the inference result carries a frame identity and times of the host, and no
  capture time.
- [VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp#L17-L18):
  the fused distance in metres and the fused speed in metres per second, which
  the file's comment gives as negative when the object approaches.
- [VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp#L56-L73):
  the fixed distance of 150 m at which the fusion gives a valid closest object
  where neither network confirms one.
- [VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp#L181-L210):
  the levels 1 and 2, and the cut-in.
- [VisionPilot/modules/visualization/include/visualization/occupancy_view.hpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/include/visualization/occupancy_view.hpp#L23-L48):
  the scene of the panel, with no speed of the closest object and no time.
- [VisionPilot/modules/visualization/src/occupancy_bridge.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/occupancy_bridge.cpp#L32-L84):
  how the bridge fills that scene, and the mark from AutoDrive alone.
- [VisionPilot/modules/visualization/src/visual_interface.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp#L304-L323):
  the label of the distance in whole metres.
- [VisionPilot/modules/visualization/src/visual_interface.cpp](https://github.com/autowarefoundation/vision_pilot/blob/014e0e7a56ee8e597c2cab8175233f74edd9b856/VisionPilot/modules/visualization/src/visual_interface.cpp#L645-L648):
  the one place where the visualization hands the scene to the panel, in a
  build with `ENABLE_OCCUPANCY`.

## Questions requiring upstream engagement

Display safety of AAOS SDV:

- Is a collision warning planned in the vehicle data, and how should a
  producer outside the SDV Media VM add a signal that HAR draws?
- Which design document is the source of the compiled cluster, and how should
  a project outside Google author and review a new telltale and chime in it?
- Is the driver-assistance scene of the reference code meant to be driven by
  an application's perception, and through which vehicle data?
- Is HAR supported on a guest host without a graphics card with three guest
  VMs, and which IVI image or app is meant to send the heartbeats of DriverUI?

VisionPilot:

- Is an output of the scene planned apart from the visualization: the lane,
  the path and the detections, with their positions on the road?

## Upstream contact

DE4SDV has posted nothing about this increment in the display safety project
or in the VisionPilot repository. Each message to maintainers remains an
owner-authorized action. No compatibility endorsement, adoption approval or
rights clearance is asserted.
