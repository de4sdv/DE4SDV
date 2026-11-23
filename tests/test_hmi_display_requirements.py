"""Content pins for the HMI display requirements (INC-HMI-001, phase 5), not semantic validation.

Phase 5 derives the requirements of the HMI display, the system of interest the charter declares, from the six
needs of phase 4; they rest on REQ-AEBS-002 and REQ-AEBS-013. The SpecifyRequirements rules of the increment workflow
are checked by Method Check; these pins hold what review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method, within the charter's scope
  cap of at most ten requirements, each derived from its need by a DerivesFromNeed connection;
- each statement, source, rationale and success criteria whole, as review settled them;
- requirement-writing rules: one obligation per statement (one `shall`, at most 60 words), the positive form, the HMI
  display as the subject of each, and the terms the statements use defined once in the package, exactly these terms;
- each time limit in its time domain, with no timing claim for a vehicle, and the presentation time on each change of
  what the display shows;
- the count of runs that each criteria states, so that no criteria passes on an empty set of runs;
- the three comments that record what phase 5 fixes of two gaps and what the criteria ask of System 2;
- the two comments of phase 4 on the input contracts replaced by the requirements and their rationales;
- one requirement definition table, the one view the method names for phase 5, framing the requirement trace concern;
- the guide's phase 5 section, its bullets, its decisions and the next obligation, phase 6;
- the upstream record's permalink for each line range that a rationale cites;
- no claim the charter excludes, the word patterns of the tests that read the same files, no satisfy link, and no
  feature link of the HMI display or of a requirement in any model file before phase 9.

The tests read the model text; they do not parse SysML. They state their own constants.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sysml_shapes import braced_body, short_name_declarations, strip_comments

ROOT = Path(__file__).resolve().parents[1]
NOTATION = ROOT / "textual-notation-of-model"
HMI = NOTATION / "packages/features/hmi"
MODEL = HMI / "hmi_display_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
RECORD = HMI / "upstream.md"
MODEL_ROOTS = (NOTATION, ROOT / "model-based-product-line-engineering")
SUBJECT_LINE = "subject hmiDisplay :> DE4SDV_HmiDisplayFraming::hmiDisplaySystem;"
GUIDE_LINK = "../../textual-notation-of-model/packages/features/hmi/hmi_display_needs_requirements.sysml"

#: the needs of phase 4 -> their short names
NEED_SHORT = {
    "needPerceivedSceneOnTheDisplay": "NEED-HMI-001",
    "needVehicleSpeedOnTheDisplay": "NEED-HMI-002",
    "needCollisionWarningOnRequest": "NEED-HMI-003",
    "needSpeedAndWarningThroughOutages": "NEED-HMI-004",
    "needNoElementShownAsCurrentWhenItIsNot": "NEED-HMI-005",
    "needRunsIdentifyTheDisplay": "NEED-HMI-006",
}

F = "FunctionalRequirementCandidate"
R = "RequirementCandidate"

#: The charter's scope: at most ten requirements.
SCOPE_CAP = 10

#: requirement -> (short name, the need it derives from, its definition, its verification method)
REQUIREMENTS = {
    "reqShowTheSceneAsGiven": ("REQ-HMI-001", "needPerceivedSceneOnTheDisplay", F, "test"),
    "reqMarkTheObjectTheSystemActsOn": ("REQ-HMI-002", "needPerceivedSceneOnTheDisplay", F, "test"),
    "reqShowTheVehicleSpeed": ("REQ-HMI-003", "needVehicleSpeedOnTheDisplay", F, "test"),
    "reqCollisionWarningWhileRequested": ("REQ-HMI-004", "needCollisionWarningOnRequest", F, "test"),
    "reqStartEachWarningModeWithinLimit": ("REQ-HMI-005", "needCollisionWarningOnRequest", R, "test"),
    "reqShowOutdatedElementsAsOutdated": ("REQ-HMI-006", "needNoElementShownAsCurrentWhenItIsNot", F, "test"),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "REQ-HMI-007", "needNoElementShownAsCurrentWhenItIsNot", F, "test"),
    "reqSpeedAndWarningThroughOutages": ("REQ-HMI-008", "needSpeedAndWarningThroughOutages", F, "test"),
    "reqRendererSplitAndInputPaths": ("REQ-HMI-009", "needSpeedAndWarningThroughOutages", R, "inspect"),
    "reqRecordDisplayIdentity": ("REQ-HMI-010", "needRunsIdentifyTheDisplay", F, "test"),
}
#: requirement -> the kind word its rationale opens with (functional: none)
KIND_WORDS = {
    "reqShowTheSceneAsGiven": "functional",
    "reqMarkTheObjectTheSystemActsOn": "functional",
    "reqShowTheVehicleSpeed": "functional",
    "reqCollisionWarningWhileRequested": "functional",
    "reqStartEachWarningModeWithinLimit": "performance",
    "reqShowOutdatedElementsAsOutdated": "functional",
    "reqShowWarningUnavailableWhileRequestOutdated": "functional",
    "reqSpeedAndWarningThroughOutages": "functional",
    "reqRendererSplitAndInputPaths": "design constraint",
    "reqRecordDisplayIdentity": "functional",
}
#: requirement -> its statement, pinned whole
STATEMENTS = {
    "reqShowTheSceneAsGiven": (
        "The HMI display shall show, within the presentation time, each scene that reaches it outside an outage in "
        "the IVI VM, or a newer scene, as the driver-assistance system gives it."),
    "reqMarkTheObjectTheSystemActsOn": (
        "With each scene that it shows, the HMI display shall show the object that the system acts on, when the scene "
        "has one, and no other object, as an element of its own apart from the objects of the scene, with its "
        "distance to the whole metre and the speed of the closest object to the whole km/h."),
    "reqShowTheVehicleSpeed": (
        "The HMI display shall show, within the presentation time, each vehicle speed that reaches it, or a newer "
        "one, to the whole km/h."),
    "reqCollisionWarningWhileRequested": (
        "The HMI display shall give the collision warning on the display and as a sound while, and only while, the "
        "warning request asks for it, each mode following each change of the asking within the presentation time."),
    "reqStartEachWarningModeWithinLimit": (
        "When the start of a request reaches the HMI display, the HMI display shall start each mode of the collision "
        "warning within 0.1 s of wall-clock time."),
    "reqShowOutdatedElementsAsOutdated": (
        "The HMI display shall show each element as outdated while, and only while, the element is outdated, "
        "following each change of its state within the presentation time."),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "The HMI display shall show that the collision warning is unavailable while, and only while, the warning "
        "request is outdated, following each change of the state of the warning request within the presentation time."),
    "reqSpeedAndWarningThroughOutages": (
        "Throughout each outage in the IVI VM, the HMI display shall show the vehicle speed, give the collision "
        "warning while the warning request asks for it, and show that the warning is unavailable while the warning "
        "request is outdated."),
    "reqRendererSplitAndInputPaths": (
        "The HMI display shall draw the vehicle speed and the collision warning and give its sound by the high "
        "availability renderer in an SDV Media VM, and draw the scene by an app in the IVI VM, each taking its inputs "
        "from the SDV Core VM over paths inside the boundary of the HMI display."),
    "reqRecordDisplayIdentity": (
        "The HMI display shall record its display identity before its first frame on the display in each run."),
}
#: requirement -> its source, pinned whole
SOURCES = {
    "reqShowTheSceneAsGiven": (
        "NEED-HMI-001; hmiDisplayInputsConcern; hmiContentVarianceConcern; scope item hmiSceneInScope; gaps "
        "gapHmiSceneOutput and gapHmiSceneContent; scenarios SC-HMI-001 to SC-HMI-007"),
    "reqMarkTheObjectTheSystemActsOn": (
        "NEED-HMI-001; scope item hmiSceneInScope; gap gapHmiSceneContent; scenarios SC-HMI-001 and SC-HMI-002"),
    "reqShowTheVehicleSpeed": (
        "NEED-HMI-002; scope item hmiSpeedInScope; scenarios SC-HMI-001, SC-HMI-002 and SC-HMI-007"),
    "reqCollisionWarningWhileRequested": (
        "NEED-HMI-003; REQ-AEBS-002; hmiWarningSequenceConcern; scope item hmiCollisionWarningInScope; gap "
        "gapHmiRendererCollisionWarning; scenarios SC-HMI-001, SC-HMI-002 and SC-HMI-007"),
    "reqStartEachWarningModeWithinLimit": (
        "NEED-HMI-003; REQ-AEBS-002; hmiWarningSequenceConcern; gap gapHmiWarningPresentation; scenarios SC-HMI-001 "
        "and SC-HMI-002"),
    "reqShowOutdatedElementsAsOutdated": (
        "NEED-HMI-005; hmiContentCurrencyConcern; scope item hmiStaleContentInScope; scenarios SC-HMI-001 to "
        "SC-HMI-007"),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "NEED-HMI-005; REQ-AEBS-013; hmiContentCurrencyConcern; gap gapHmiWarningAvailability; scenarios SC-HMI-001 "
        "to SC-HMI-007"),
    "reqSpeedAndWarningThroughOutages": (
        "NEED-HMI-004; REQ-AEBS-013; hmiAndroidOutageConcern; scope item hmiAndroidOutageInScope; scenarios "
        "SC-HMI-003 to SC-HMI-006"),
    "reqRendererSplitAndInputPaths": (
        "NEED-HMI-004; hmiRendererAllocationConcern; hmiRendererPathConcern; scope item hmiRendererSplitInScope; gaps "
        "gapHmiRendererIntegration and gapHmiMemberGuestLayout"),
    "reqRecordDisplayIdentity": (
        "NEED-HMI-006; hmiDisplayVerdictConcern; scope item hmiVerdictEvidenceInScope; assumption "
        "asmHmiSimulationStandsIn; scenarios SC-HMI-001 to SC-HMI-007"),
}
#: requirement -> its rationale, pinned whole
RATIONALES = {
    "reqShowTheSceneAsGiven": (
        "The driver supervises the driver-assistance system with what it perceives, right or wrong, so the display "
        "shows the scene that the system gives and no other. At 014e0e7a the system builds a scene only inside its "
        "own visualization, in a build with the option ENABLE_OCCUPANCY and with the visualization switched on "
        "(visual_interface.cpp:645-648; vision_pilot.cpp:177). The bridge of its panel builds it from the lane points "
        "of AutoSteer placed on the road through the homography that the system loads, the path that the lateral "
        "fusion fits, the offset and the heading of the vehicle in its lane, the detections of AutoSpeed as boxes "
        "with a score and a class, and the validity and the distance of the closest object, and it does not read the "
        "plan (occupancy_bridge.cpp:20-77). That scene carries no speed of the closest object and no time, and the "
        "inference result carries a frame identity and no capture time (occupancy_view.hpp:23-48; "
        "inference.hpp:38-52). So the scene that the display takes is an output that the system does not give yet "
        "(gapHmiSceneOutput), and what it carries bounds what the display can show of it (gapHmiSceneContent). The "
        "scene is the one input whose form follows the driving application, so this requirement and REQ-HMI-002 "
        "follow it. The display may skip a scene only for a newer one. The presentation time bounds the delay, so "
        "that a display that shows each scene late cannot hide behind REQ-HMI-006. During an outage in the IVI VM the "
        "app that draws the scene cannot show it; REQ-HMI-006 then shows the scene as outdated, and once the app "
        "gives its first frame again this requirement holds again. A display that shows the simulator's record of the "
        "scene or an estimate of its own shows another scene (hmiSimulatorTruthOutOfScope)."),
    "reqMarkTheObjectTheSystemActsOn": (
        "NEED-HMI-001 asks for the closest object in the path, which the system acts on, marked apart from the other "
        "objects. At 014e0e7a the fusion takes as the closest object the nearest detection of the first level, or of "
        "the second when that one is nearer, a cut-in (longitudinal_fusion.cpp:181-182, 207-210), and fuses its "
        "distance with the distance that AutoDrive gives where AutoDrive flags an object in the path. Where AutoSpeed "
        "gives no detection of the first level and AutoDrive flags no object in the path, the fusion still gives a "
        "valid closest object at a fixed distance of 150 m (longitudinal_fusion.cpp:56, 63-73), and the system plans "
        "on the closest object only when it is valid and nearer than 150 m (vision_pilot.cpp:147-150). So the object "
        "that the system acts on is that one, and no object is marked at the fixed distance. The value of 150 m is "
        "compared when the pin moves, and a change revises the term. The scene names no detection as the closest "
        "object, so the display shows that object as an element of its own and marks no detection as it: choosing a "
        "box would be an estimate of the display's own. The fusion gives the distance in m and the speed in m/s, "
        "negative when the object approaches, as its own declaration states (longitudinal_fusion.hpp:17-18); the "
        "display shows that speed with its sign, in km/h. The whole metre is the resolution of the system's own label "
        "of the distance (visual_interface.cpp:304-323), and the whole km/h is set here for each speed on the "
        "display. The scene of the panel gives no speed of the closest object, so the scene that the display takes "
        "carries it (REQ-HMI-001). The mark that the visualization draws from AutoDrive alone "
        "(occupancy_bridge.cpp:79-84) is no closest object of the fusion, and the display shows no such mark as that "
        "object."),
    "reqShowTheVehicleSpeed": (
        "The driver supervises the driver-assistance system with the same speed that the system acts on "
        "(NEED-HMI-002). In the realization of the driver-assistance increment the vehicle speed enters the system "
        "with its sample time in simulation time, typed by COVESA VSS in km/h (VehicleSpeedSamplePayload and "
        "MAP-DRIVING-DA-VEHICLE-SPEED), and the system reads it once in each result pass. The display takes the speed "
        "of each world snapshot that reaches the input of the system, not the copy that the system reads in each "
        "result pass (MAP-DRIVING-DA-VEHICLE-SPEED): the signal is the same, and the snapshots go on when the system "
        "gives no result. The vehicle gives the speed, and which element brings it to the display is for the "
        "architecture phases (vehicleSpeedSourceComment). The display may skip a sample only for a newer one, and the "
        "presentation time bounds the delay. Before the first vehicle speed of a run reaches the display there is no "
        "speed to show, and REQ-HMI-006 shows the element as outdated. In the runs of SC-HMI-003 to SC-HMI-006, "
        "REQ-HMI-008 judges this obligation through each outage."),
    "reqCollisionWarningWhileRequested": (
        "The display gives the warning so that the driver can act on an imminent collision, and none without a "
        "request (NEED-HMI-003). The warning request is the output that the driver-assistance increment realizes from "
        "the warnings of each plan: one event for each plan, which asks for the collision warning when the plan holds "
        "the forward-collision warning or the emergency braking and carries the capture time in simulation time of "
        "the frame that the plan came from, with no value changed on its path (CollisionWarningRequestOutput and "
        "MAP-DRIVING-DA-WARNING-REQUEST). The request does not tell the two apart, so the display gives one collision "
        "warning for both. The request carries no end, so the warning lasts while the request asks: a continuing "
        "request continues the warning, and the warning ends once the request asks for none or is outdated, when "
        "REQ-HMI-007 shows that it is unavailable. Each mode follows each change within the presentation time that "
        "REQ-HMI-005 sets, at the start and at the end alike. The term takes only the form of the request, so the "
        "requirement names no variant. It rests on REQ-AEBS-002, the collision warning that the product line asks "
        "for; whether a warning is due is the decision of the driver-assistance system, which that increment judges. "
        "The vehicle data of the renderer holds no collision warning yet (gapHmiRendererCollisionWarning). In the "
        "runs of SC-HMI-003 to SC-HMI-006, REQ-HMI-008 judges this obligation through each outage. No safety claim is "
        "made."),
    "reqStartEachWarningModeWithinLimit": (
        "This is a performance requirement on the share of the HMI display in the time that the driver-assistance "
        "increment allots from the warning request to each mode. REQ-DRIVING-042 allots 0.2 s of wall-clock time to "
        "the Eclipse S-CORE path and the AAOS SDV together, and the realization of that increment divides it, on its "
        "path to its own app on the IVI VM, into 0.1 s for the path and 0.1 s for the presentation, from the receipt "
        "to the first frame with the warning and to the start of the sound (MAP-DRIVING-DA-WARNING-REQUEST). The "
        "boundary of the HMI display lies at the SDV Core VM, with the Eclipse S-CORE path outside it and the paths "
        "from the SDV Core VM inside it, so the share of the display starts when the start of a request reaches it. "
        "Unlike that division, whose path share runs to the receipt on the IVI VM, the share of the display also "
        "holds the paths from the SDV Core VM to the renderer and to the app. The 0.1 s is chosen here by analogy "
        "with that division and leaves the other 0.1 s to the part before the boundary. It is unmeasured for the high "
        "availability renderer and for the sound, and it is revisited when a readiness probe measures them "
        "(gapHmiWarningPresentation). Within is strict, so a mode that starts exactly at the limit is late. A mode "
        "starts at its start of a mode; a recording or an overlay in place of a mode is no start. The limit counts in "
        "wall-clock time while the simulation runs no faster than wall-clock time, which is the obligation of System "
        "2, and makes no timing claim for a vehicle."),
    "reqShowOutdatedElementsAsOutdated": (
        "The display shows no element as current when it is not, so that the driver supervises the driver-assistance "
        "system on what it perceives now (NEED-HMI-005). The scene and the warning request share one period of 0.1 s "
        "of simulation time in the realization of the driver-assistance increment: one camera image, one result pass, "
        "one plan and one event of the warning request each 0.1 s; the vehicle speed comes with each world snapshot "
        "at the input of the system, every step of 0.05 s. The limits of the term current take two periods, so that "
        "one late value is tolerated. The vehicle speed brings the newest time to the display with each world "
        "snapshot, so the limit in simulation time also counts the time from the capture of a frame to the arrival of "
        "its scene and its event at the display, and the time that the display takes to show the scene. While those "
        "times stay within one period together, a scene stays current until the next one is shown, and the warning "
        "request until its next event; with longer times an element can turn outdated before its next value comes, "
        "and the limit is revisited once a readiness probe measures them (warningPresentationFixedInPhase5). The "
        "limit in simulation time counts against the newest time that has reached the display, so it catches a delay "
        "before the display, which an age taken from the arrival would hide, and a value whose time the display "
        "changes. The limit in wall-clock time counts from the arrival of the newest value of the input, so it "
        "catches every input stopping, when the newest time stops as well. Late and missing values give one state, "
        "outdated, and phase 8 states how an outdated element looks; the visual design stays out of scope "
        "(hmiHumanFactorsOutOfScope). An element is shown as current again once it is current, which is the validity "
        "rule of the display; the converse, current while it is current, keeps a display from showing everything as "
        "outdated. The state of each element counts on its own, so a late scene leaves the vehicle speed current. No "
        "safety claim is made."),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "The display shows when the warning is unavailable, so that the driver can tell a warning that cannot come "
        "from one that is not due (NEED-HMI-005); it rests on N-AEBS-008, that the availability of the AEBS be "
        "apparent, and on the status indication of REQ-AEBS-013. This is the one degraded response of the set. The "
        "warning request carries no indication of its own availability (gapHmiWarningAvailability), and one of its "
        "events comes for each plan, telling whether it asks, so the display learns from their age that the warning "
        "cannot come: the warning is unavailable while the warning request is outdated. A signal of its own would "
        "need a change of the driver-assistance system (hmiCandidateChangeOutOfScope). The warning shows as available "
        "again once the warning request is current, which is the validity rule; the converse keeps a display from "
        "showing the warning as unavailable at all times. In SC-HMI-007 the Eclipse S-CORE path ends carrying the "
        "request, and the display shows the warning as unavailable while the driver still sees the vehicle speed. A "
        "renderer that cannot give the warning, such as a sound output that is out, is left for a later increment "
        "(warningAvailabilityFixedInPhase5). No safety claim is made."),
    "reqSpeedAndWarningThroughOutages": (
        "While the drawing of the scene or Android in the IVI VM is out, the driver-assistance system goes on driving "
        "the vehicle, and the driver still needs the speed and the warning, or to know that the warning cannot come "
        "(NEED-HMI-004). The outages are those of the story: the app that draws the scene ends or hangs (SC-HMI-003), "
        "and Android in the IVI VM boots (SC-HMI-004), hangs (SC-HMI-005) or restarts (SC-HMI-006). REQ-HMI-003, "
        "REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 state the speed and the warning in every run; this requirement "
        "carries them through each outage, and its criteria judge them there. It rests on N-AEBS-008 and on the "
        "status indication of REQ-AEBS-013. Each outage is an event inside the boundary of the display, whose "
        "detection phases 6 to 8 decide (guestAcrossBoundaryComment). The speed and the warning hold throughout, the "
        "scene returns under REQ-HMI-001 once the app gives frames again, and until then REQ-HMI-006 shows it as "
        "outdated, within the limits of the term current and the presentation time from the last scene that the app "
        "has shown. No time from a restart to the scene is set here; that limit, and whether the HMI display meets "
        "those of REQ-HMI-006 through a hang of the app or of Android in the IVI VM, stay open with the owner until a "
        "probe measures them. No safety claim is made."),
    "reqRendererSplitAndInputPaths": (
        "This is a design constraint on the realization of the HMI display, from the owner's decision of 2026-11-17: "
        "the high availability renderer in an SDV Media VM draws the speed and the collision warning and gives its "
        "sound, and an app in the IVI VM draws the scene, so that the speed and the warning do not depend on Android "
        "in the IVI VM (hmiRendererSplitInScope). The boundary puts the paths from the SDV Core VM inside the display "
        "and the Eclipse S-CORE path outside it. How a collision warning and its sound reach the renderer is open "
        "(gapHmiRendererCollisionWarning), and so is how the renderer and the guest fit a bench "
        "(gapHmiRendererIntegration). Phases 6 to 8 decide the elements on each path and how the app tells the "
        "renderer that Android is alive; this requirement fixes only the split and that the paths stay inside the "
        "boundary. It names the AAOS SDV guest, and phase 9 links it."),
    "reqRecordDisplayIdentity": (
        "A verdict holds only for the display that ran, and the configuration of the display is every setting that it "
        "reads at its start (NEED-HMI-006). The parts of the identity are pinned each on its own, because none of "
        "them fixes the others: the build of each of the two drawing elements, the image of each guest VM, the sound "
        "of the warning, the files of the configuration and the settings of the start. Each part is the SHA-256 of "
        "named files or a setting written out, so that another engineer can check it. The candidate revision is bound "
        "by the run of the driver-assistance system (NEED-DRIVING-011 and REQ-DRIVING-044), and the record of what "
        "that system gives, the captures and the evaluators belong to System 2 and are bound there. Like "
        "REQ-DRIVING-044, the record is a behaviour of the display in each run, which phase 6 allocates to a "
        "function. A verdict holds for the simulated configuration only (asmHmiSimulationStandsIn)."),
}
#: requirement -> its success criteria, pinned whole
CRITERIA = {
    "reqShowTheSceneAsGiven": (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-004 and SC-HMI-006 has "
        "the end of its outage in the IVI VM before its own end, and in each run every scene that reaches the HMI "
        "display outside an outage in the IVI VM, or a newer scene, is on the display less than 0.1 s of wall-clock "
        "time after it arrives, with its lane points, its path and each of its objects with its level, as many "
        "objects as the scene gives and at the positions that it gives, read within the drawing tolerance that phase "
        "8 states; and when no frame on the display shows a lane, a path or an object that no scene of the run gives, "
        "from the simulator's record of the scene or from an estimate of the display's own."),
    "reqMarkTheObjectTheSystemActsOn": (
        "Met when each of SC-HMI-001 and SC-HMI-002 has at least one run whose scenes give an object that the system "
        "acts on, and in each run of SC-HMI-001 to SC-HMI-007 each frame on the display that shows a scene shows, as "
        "an element of its own, the object that the system acts on of that scene when it has one and no such element "
        "when it has none, the fixed distance of 150 m included; marks no box of the objects and no mark of AutoDrive "
        "alone as that object; and shows its distance as the distance of the scene rounded to the whole metre and its "
        "speed as the speed of the closest object of the scene times 3.6, rounded to the whole km/h, with its sign."),
    "reqShowTheVehicleSpeed": (
        "Met when each of SC-HMI-001, SC-HMI-002 and SC-HMI-007 has at least one run, and in each of their runs each "
        "speed on a frame on the display is the value of a vehicle speed of the run that has reached the HMI display, "
        "rounded to the whole km/h; each vehicle speed that reaches the HMI display, or a newer one, is on the "
        "display less than 0.1 s of wall-clock time after it arrives; and no frame shows a speed from another source, "
        "a fixed value of the display's own, or a speed before the first vehicle speed of the run reaches the HMI "
        "display."),
    "reqCollisionWarningWhileRequested": (
        "Met when each run of SC-HMI-001 has at least one start of a request that reaches the HMI display, and in "
        "each run of SC-HMI-001, SC-HMI-002 and SC-HMI-007 each mode of the collision warning is on from less than "
        "0.1 s of wall-clock time after each start of a request reaches the HMI display until less than 0.1 s of "
        "wall-clock time after the warning request ends its asking, and at no other time, with no recording or "
        "overlay in place of either mode."),
    "reqStartEachWarningModeWithinLimit": (
        "Met when each run of SC-HMI-001 has at least one start of a request that reaches the HMI display, and for "
        "each start of a request that reaches the HMI display in a run of SC-HMI-001 or SC-HMI-002, the first frame "
        "on the display with the warning and the start of the sound each come less than 0.1 s of wall-clock time "
        "after it arrives, with no recording or overlay in place of either mode."),
    "reqShowOutdatedElementsAsOutdated": (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-003 to SC-HMI-006 has its "
        "outage in the IVI VM and each run of SC-HMI-007 the stop of the Eclipse S-CORE path, and in each run each "
        "frame on the display shows each element as outdated, in the form that phase 8 states for it, from less than "
        "0.1 s of wall-clock time after the element turns outdated until less than 0.1 s of wall-clock time after it "
        "turns current again, and as current at every other time; an element is outdated from the start of the run "
        "until a first current value of its input reaches the HMI display."),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "Met when each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-007 has the stop of the "
        "Eclipse S-CORE path at least 0.3 s of wall-clock time before its end, and in each run the display shows that "
        "the collision warning is unavailable from less than 0.1 s of wall-clock time after the warning request turns "
        "outdated until less than 0.1 s of wall-clock time after it turns current again, and at no other time, so "
        "that the warning shows as available again only once an event of the warning request is current."),
    "reqSpeedAndWarningThroughOutages": (
        "Met when each of SC-HMI-003 to SC-HMI-006 has at least one run, each run has its outage in the IVI VM with "
        "at least one start of a request reaching the HMI display during it, and throughout the outage of each run "
        "each frame on the display and each mode of the collision warning meet what the criteria of REQ-HMI-003, "
        "REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 ask of them."),
    "reqRendererSplitAndInputPaths": (
        "Met when the inspection of the realization that phase 8 records shows the vehicle speed, the collision "
        "warning on the display and its sound in the high availability renderer in an SDV Media VM, the scene in an "
        "app in the IVI VM, and for each input the elements that carry it from the SDV Core VM to the renderer or to "
        "the app, all inside the boundary of the HMI display, with no other element drawing the vehicle speed or the "
        "collision warning."),
    "reqRecordDisplayIdentity": (
        "Met when every run of SC-HMI-001 to SC-HMI-007 has the record of its display identity before its first frame "
        "on the display; when another engineer who hashes the named files obtains the recorded values; and when a "
        "display with one changed build, image, sound file, configuration file or start setting records a different "
        "display identity."),
}

#: requirement -> the count of runs that its criteria state first, so that no criteria passes on an empty set of
#: runs; the inspection of REQ-HMI-009 judges no run
NON_VACUITY = {
    "reqShowTheSceneAsGiven": (
        "each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-004 and SC-HMI-006 has the end of "
        "its outage in the IVI VM before its own end"),
    "reqMarkTheObjectTheSystemActsOn": (
        "each of SC-HMI-001 and SC-HMI-002 has at least one run whose scenes give an object that the system acts on"),
    "reqShowTheVehicleSpeed": "each of SC-HMI-001, SC-HMI-002 and SC-HMI-007 has at least one run",
    "reqCollisionWarningWhileRequested": (
        "each run of SC-HMI-001 has at least one start of a request that reaches the HMI display"),
    "reqStartEachWarningModeWithinLimit": (
        "each run of SC-HMI-001 has at least one start of a request that reaches the HMI display"),
    "reqShowOutdatedElementsAsOutdated": (
        "each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-003 to SC-HMI-006 has its outage "
        "in the IVI VM and each run of SC-HMI-007 the stop of the Eclipse S-CORE path"),
    "reqShowWarningUnavailableWhileRequestOutdated": (
        "each of SC-HMI-001 to SC-HMI-007 has at least one run, each run of SC-HMI-007 has the stop of the Eclipse "
        "S-CORE path at least 0.3 s of wall-clock time before its end"),
    "reqSpeedAndWarningThroughOutages": (
        "each of SC-HMI-003 to SC-HMI-006 has at least one run, each run has its outage in the IVI VM with at least "
        "one start of a request reaching the HMI display during it"),
    "reqRendererSplitAndInputPaths": None,
    "reqRecordDisplayIdentity": (
        "every run of SC-HMI-001 to SC-HMI-007 has the record of its display identity before its first frame on the "
        "display"),
}

#: the intro sentence of the terms comment
TERMS_INTRO = "Terms of the requirements of the HMI display below, which the needs above use in the same sense."
#: Every term the requirements use in a sense of their own, in its order, with its definition, pinned whole.
TERM_DEFINITIONS = {
    "Driver-assistance system": (
        "the candidate application that drives the vehicle in the configuration that the HMI display serves. It gives "
        "the scene and the warning request, and the vehicle gives it the vehicle speed."),
    "Result pass": (
        "a pass of the loop of the driver-assistance system in which it gives an inference result. At 014e0e7a "
        "VisionPilot makes one pass for each camera image that it takes, and the bench of the driver-assistance "
        "increment gives it one each 0.1 s of simulation time."),
    "Scene": (
        "the output of the driver-assistance system for one result pass, in the form of the scene of the panel of "
        "VisionPilot at 014e0e7a, with the speed of the closest object and the time of the scene, which that scene "
        "lacks: the lane points, the path that the system fits to its lane, the objects it detects, each with its "
        "level, and the closest object in its path that its fusion gives, with its validity, its distance and its "
        "speed."),
    "Level": (
        "the class that the driver-assistance system gives an object it detects, relative to its path: 1 for the same "
        "lane, 2 for the adjacent lane, and any other class as the system gives it."),
    "Object that the system acts on": (
        "the closest object of a scene when the fusion of the driver-assistance system gives it as valid at a "
        "distance below 150 m. A scene whose closest object lies at 150 m or more, the fixed distance of 150 m "
        "included, has none."),
    "Distance": (
        "the distance of the closest object of a scene, in m, as the fusion of the driver-assistance system gives it."),
    "Speed of the closest object": (
        "the speed of the closest object of a scene, in m/s, as the fusion of the driver-assistance system gives it, "
        "negative when the object approaches."),
    "Vehicle speed": (
        "the speed of the vehicle in km/h, with its sample time in simulation time, as the vehicle gives it to the "
        "driver-assistance system at its input. Each sample is one vehicle speed."),
    "Warning request": (
        "the input by which the HMI display is asked for the collision warning, in the form that the "
        "driver-assistance increment gives it at its boundary: one event for each plan of the driver-assistance "
        "system, telling whether it requests the collision warning, with its issue time in simulation time."),
    "Ask": (
        "the warning request asks while its newest event that has reached the HMI display is current and requests the "
        "collision warning."),
    "Start of a request": (
        "the event of the warning request with which the asking begins: the first event that makes the warning "
        "request ask after an instant at which it asks for no collision warning."),
    "Collision warning": (
        "the warning to the driver of an imminent collision, which the HMI display gives in two modes, on the display "
        "and as a sound."),
    "Mode": "one of the two forms of the collision warning: the warning on the display, or the warning as a sound.",
    "Start of a mode": (
        "for the mode on the display, the first frame on the display with the warning; for the sound, the start of "
        "the sound, as the realization of the driver-assistance increment takes the start of each mode."),
    "Presentation time": (
        "the 0.1 s of wall-clock time that REQ-HMI-005 sets from the start of a request reaching the HMI display to "
        "the start of each mode, which the other requirements take for each change of what the HMI display shows."),
    "Within": "a time within a span after an instant is less than that span after it.",
    "Input": (
        "the scene, the vehicle speed or the warning request, each a series of values that reach the HMI display: "
        "scenes, vehicle speeds or events of the warning request."),
    "Time of a value": (
        "the time in simulation time that a value of an input carries as its source gives it: for a scene, the "
        "capture time of the camera image of its result pass; for a vehicle speed, its sample time; for an event of "
        "the warning request, its issue time. The newest value of an input is the one with the latest time."),
    "Element": (
        "each thing that the HMI display shows from an input: the scene, which holds the object that the system acts "
        "on, and the vehicle speed."),
    "Current": (
        "a value of an input is current while the time of the value is at most 0.2 s of simulation time older than "
        "the newest time of a value that has reached the HMI display, and the newest value of the same input reached "
        "it at most 0.2 s of wall-clock time before. An element is current while it shows a current value, and the "
        "warning request is current while its newest event is current."),
    "Outdated": (
        "an element or the warning request is outdated at each instant at which it is other than current: a value "
        "that comes late and a value that never comes count alike, and so does the time before the first value of its "
        "input reaches the HMI display."),
    "Reach": (
        "a value reaches the HMI display when it arrives at the boundary of the display from the path that carries it "
        "there."),
    "Outage in the IVI VM": (
        "the time from the start of a hang or the end of the app in the IVI VM that draws the scene, or of a hang, a "
        "boot or a restart of Android in the IVI VM, until that app gives its first frame on the display after it."),
    "Display identity": (
        "the SHA-256 of the files of the build of the high availability renderer in the SDV Media VM, of the files of "
        "the build of the app in the IVI VM that draws the scene, of the image of the IVI VM and of the SDV Media VM, "
        "and of the sound file of the collision warning; the SHA-256 of each configuration file that the HMI display "
        "reads at its start; and the settings of its start, verbatim."),
    "Run": "one execution of the HMI display on one scenario of SC-HMI-001 to SC-HMI-007, from its start to its end.",
    "Simulation time": "the time of the simulated world.",
    "Wall-clock time": "the time of the host.",
}
TERMS_COMMENT = "termsHmiDisplayRequirements"

#: the inflected forms that a statement may use in place of a term, beyond the head and its plural
TERM_INFLECTIONS = {
    "Ask": ("asking",),
    "Start of a mode": ("start of each mode", "start each mode"),
    "Time of a value": ("time of the value",),
    "Reach": ("reaches", "reached", "reaching"),
}
#: requirement -> exactly the defined terms its statement uses (as the rule checks of phase 5 list them)
STATEMENT_TERMS = {
    "REQ-HMI-001": ["Presentation time", "Within", "Scene", "Reach", "Outage in the IVI VM",
        "Driver-assistance system"],
    "REQ-HMI-002": ["Scene", "Object that the system acts on", "Element", "Distance", "Speed of the closest object"],
    "REQ-HMI-003": ["Presentation time", "Within", "Vehicle speed", "Reach"],
    "REQ-HMI-004": ["Collision warning", "Warning request", "Ask", "Mode", "Within", "Presentation time"],
    "REQ-HMI-005": ["Start of a request", "Reach", "Start of a mode", "Collision warning", "Within", "Wall-clock time"],
    "REQ-HMI-006": ["Element", "Outdated", "Within", "Presentation time"],
    "REQ-HMI-007": ["Collision warning", "Warning request", "Outdated", "Within", "Presentation time"],
    "REQ-HMI-008": ["Outage in the IVI VM", "Vehicle speed", "Collision warning", "Warning request", "Ask", "Outdated"],
    "REQ-HMI-009": ["Vehicle speed", "Collision warning", "Scene", "Input"],
    "REQ-HMI-010": ["Display identity", "Run"],
}
#: the requirements whose statements set a time limit with its value
TIMED_REQUIREMENTS = ["REQ-HMI-005"]
#: the requirements whose statements take the presentation time that REQ-HMI-005 sets, for each change of what the
#: display shows (the lead's decision of 2026-11-22 on the presentation time)
PRESENTATION_TIME_REQUIREMENTS = ["REQ-HMI-001", "REQ-HMI-003", "REQ-HMI-004", "REQ-HMI-006", "REQ-HMI-007"]
#: kind word -> how the rationale of a requirement that is not functional opens
KIND_OPENING = {"design constraint": "This is a design constraint", "performance": "This is a performance requirement"}

#: comment name -> (the elements it is about, its text), pinned whole
GAP_COMMENTS = {
    "warningPresentationFixedInPhase5": (
        ("DE4SDV_HmiDisplayFraming::gapHmiWarningPresentation",),
        (
            "What phase 5 fixes of this gap, and what stays open. Fixed: the HMI display starts each mode of the "
            "collision warning within 0.1 s of wall-clock time after the start of a request reaches it (REQ-HMI-005), "
            "its share of the 0.2 s of wall-clock time that the driver-assistance increment allots from the warning "
            "request to each mode, and each change of what it shows takes the same 0.1 s (the term presentation "
            "time). Open: the 0.1 s is chosen by analogy with the division on the path to the app of the "
            "driver-assistance increment and is unmeasured for the high availability renderer, for the app that draws "
            "the scene and for the sound; the owner revisits it when a readiness probe measures them. Whether the "
            "time from the capture of a frame to the arrival of its scene and its event at the HMI display, with the "
            "time to show the scene, stays within one period of 0.1 s, as the limit in simulation time of the term "
            "current needs, is open until a readiness probe measures it; a longer time revises that limit. Which part "
            "of System 1 holds the other 0.1 s, before the boundary of the display on the Eclipse S-CORE path, is for "
            "the architecture phases of both increments. Whether a build of this display replaces the app of the "
            "driver-assistance increment stays open; the realization and the verdicts of that increment stay as they "
            "are.")),
    "warningAvailabilityFixedInPhase5": (
        ("DE4SDV_HmiDisplayFraming::gapHmiWarningAvailability",),
        (
            "What phase 5 fixes of this gap, and what stays open. Fixed: the HMI display learns that the collision "
            "warning is unavailable from the age of the events of the warning request, with no signal of its own: the "
            "warning is unavailable while the warning request is outdated, and available again once it is current "
            "(REQ-HMI-007 and the term current). Open, for a later increment: a renderer that cannot give the "
            "warning, such as a sound output that is out or a high availability renderer that cannot draw it, makes "
            "the warning unavailable as well, and no requirement of this increment states what the display shows "
            "then. A signal of the driver-assistance system of its own stays a change of that system, out of scope "
            "here.")),
    "hmiTestbedObligationsOfPhase5": (
        ("DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration",),
        (
            "What the criteria of phase 5 ask of System 2: each is an obligation of the verification environment and "
            "none a criterion of the HMI display. The bench runs the simulation no faster than wall-clock time. The "
            "records hold each value of each input as its source gives it, with its simulation time, and where it "
            "reaches the HMI display, with the wall-clock time of its arrival; each frame on the display and the "
            "start of each sound, with their wall-clock times; and the files and the settings that the display "
            "identity names. The fault injection makes the outage of each run of SC-HMI-003 to SC-HMI-006 after the "
            "first value of each input reaches the display and while at least one start of a request reaches it, and "
            "the stop of the Eclipse S-CORE path in each run of SC-HMI-007. It leaves at least 0.3 s of wall-clock "
            "time before the end of the run, the longest response that the criteria judge: 0.2 s to turn outdated and "
            "0.1 s to show it. Each run of SC-HMI-004 and SC-HMI-006 has a length that System 2 states before the "
            "run, so that the scene has to return within it; a limit on that time stays open with the owner until a "
            "probe measures the boot of Android in the IVI VM. How a frame on the display is read against the scene "
            "that it shows, with the tolerance of a drawn position, is set with the drawing in phase 8. Open: the "
            "bench of the renderer and of the guest, and its readiness probe (gapHmiRendererIntegration).")),
}
#: the comments of phase 4 on the input contracts, which phase 5 states as requirements and rationales
REMOVED_COMMENTS = ("perceivedSceneContract", "warningRequestContract")

#: the two header paragraphs of phase 5, pinned whole
HEADER_PHASE_FIVE_SET = (
    "Phase 5: the requirements derived from these needs, each with one subject, the HMI display, one verification "
    "method and its success criteria. They derive from the needs and rest on REQ-AEBS-002 and REQ-AEBS-013, and the "
    "scope of the increment caps them at ten. From the driver-assistance increment the terms take the form of the "
    "warning request and the start of each mode; from the files of VisionPilot at 014e0e7a they take the levels, the "
    "fixed distance of 150 m and the sign that the fusion declares for the speed of the closest object. The "
    "rationales name those files by their file names, and upstream.md gives each with its path. Set here, each with "
    "its reason in a rationale: the speed of the closest object as its fusion gives it; the object that the system "
    "acts on; distances to the whole metre and speeds to the whole km/h; the vehicle speed at the input of the "
    "driver-assistance system; the share of the HMI display in the time that the driver-assistance increment allots "
    "from the warning request to each mode, 0.1 s of wall-clock time, which every change of what the display shows "
    "takes as its presentation time; the limits of 0.2 s of simulation time and of 0.2 s of wall-clock time beyond "
    "which an element is outdated; the warning unavailable while the warning request is outdated; and the split of "
    "the renderers, by the owner's decision of 2026-11-17. The comments on gapHmiWarningPresentation and "
    "gapHmiWarningAvailability give what phase 5 fixes of those gaps and what stays open, and the comment on "
    "gapHmiRendererIntegration gives what the criteria ask of System 2.")
HEADER_PHASE_FIVE_VARIABILITY = (
    "Rule 5 of the increment workflow makes a requirement core when its subject has no link and it has none of its "
    "own. No requirement carries a link at this revision, so all ten read as core. Phase 3 classes the HMI display as "
    "content of every member of the governed scope and leaves open which of its content is common, so phase 9 decides "
    "on a link of its system of interest and claims no member. Beyond the subject, REQ-HMI-001 and REQ-HMI-002 follow "
    "the driving application through the scene, whose form is that of VisionPilot (visionPilot), and REQ-HMI-001, "
    "REQ-HMI-008, REQ-HMI-009 and REQ-HMI-010 name the AAOS SDV guest through the IVI VM or the SDV Media VM "
    "(guestAndroidSDV); phase 9 links them. The terms take only the form of the warning request, so REQ-HMI-003 to "
    "REQ-HMI-007 name no variant.")
#: the header sentence that phase 5 replaces
HEADER_OLD = "Phase 5 adds to this package the requirements derived from these needs."
#: the non-claim sentence of the header
HEADER_NON_CLAIM = (
    "No safety, timing, on-road or production-readiness claim is made, and no member product is claimed.")

CONCERN = "hmiDisplayRequirementTraceConcern"
CONCERN_DOC = (
    "Verification engineers and open-source reviewers need each requirement of the HMI display traced to the need it "
    "derives from, with its source, its rationale, its verification method and its success criteria, to judge whether "
    "the requirements answer the needs and can be verified. No concern of the framing names this table: "
    "hmiDisplayVerdictConcern asks a verdict for each requirement and scenario, and the table gives those "
    "requirements.")
CONCERN_HOLDERS = [("reviewer", "OpenSourceReviewer"), ("verificationEngineer", "VerificationEngineer")]
#: Owner decision of 2026-11-04 (the workflow's views per phase): phase 5 has one table, typed by
#: SystemRequirementDefinitionViewpoint.
VIEW = "hmiDisplayRequirementsView"
VIEWPOINT_USAGE = "selectedHmiRequirementDefinitionViewpoint"
VIEWPOINT = "SystemRequirementDefinitionViewpoint"
MAX_ROW_HEIGHT = 500
#: the columns in order: (name, what it renders); the renderer reads no column width, so no column sets one
COLUMNS = [
    ("ID", "CT::reqId"),
    ("Requirement", "CT::declaredName"),
    ("Statement", "constraintLanguage"),
    ("Source", "source"),
    ("Rationale", "rationale"),
    ("Method", "verificationMethod"),
    ("Criteria", "successCriteria"),
]

GUIDE_STATUS_OLD = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification and "
    "Phase 4 stakeholder needs, proposal.**")
GUIDE_STATUS_NEW = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs and Phase 5 requirements, proposal.**")
GUIDE_FRAME_LINE = f"- [SysML requirements]({GUIDE_LINK}): the Phase 5 requirements of the HMI display."
GUIDE_PHASE_FOUR_OLD = (
    "No need states a number or names a drawing: Phase 5 derives the requirements and their limits, how the app in "
    "the IVI VM draws the scene is a choice of Phase 8, and no need asks for gear, set speed, speed limit or another "
    "telltale. Comments about `NEED-HMI-001` and `NEED-HMI-003` keep for Phase 5 what the pinned driver-assistance "
    "system builds and what the driver-assistance increment realizes from it: what the scene of its visualization "
    "carries, and what the warning request asks for and carries.")
GUIDE_PHASE_FOUR_NEW = (
    "No need states a number or names a drawing: Phase 5 derives the requirements and their limits, how the app in "
    "the IVI VM draws the scene is a choice of Phase 8, and no need asks for gear, set speed, speed limit or another "
    "telltale. Phase 5 states in its requirements what the scene of the pinned driver-assistance system carries and "
    "what the warning request asks for and carries.")
GUIDE_NEXT_OLD = "The next model obligation is **Phase 5**, the requirements."
GUIDE_NEXT_NEW = "The next model obligation is **Phase 6**, the functional architecture."
GUIDE_HEADING = "## Requirements (Phase 5)"
#: the blocks of the guide's Phase 5 section, in order; BULLETS and DECISIONS stand for the two lists
GUIDE_BLOCKS = (
    (
        "The [requirements](" + GUIDE_LINK + ") state what the HMI display shall do and how each is verified. There "
        "are ten, the cap of the scope. Each has one subject, the HMI display, derives from one need, and has one "
        "verification method and its success criteria. They derive from the Phase 4 needs and rest on `REQ-AEBS-002` "
        "and `REQ-AEBS-013`. Eight are functional; Phase 6 allocates each of those to a function."),
    "BULLETS",
    (
        "A comment of terms defines each word that a statement uses, among them the scene, the object that the system "
        "acts on, the warning request, the presentation time, current and outdated, the outage in the IVI VM and the "
        "display identity. Each time limit names simulation time or wall-clock time and makes no timing claim for a "
        "vehicle."),
    "The Phase 5 decisions, each with its reason in the rationale of the requirement that it shapes:",
    "DECISIONS",
    (
        "The rationales cite the files of VisionPilot by file name and line, and the upstream record gives each with "
        "its path at the pinned commit."),
    (
        "Comments about `gapHmiWarningPresentation` and `gapHmiWarningAvailability` record what Phase 5 fixes of "
        "those gaps and what stays open, a renderer that cannot give the warning among them, and a comment about "
        "`gapHmiRendererIntegration` records what the criteria ask of System 2. The table of the requirements frames "
        "`hmiDisplayRequirementTraceConcern`. `tests/test_hmi_display_requirements.py` pins the requirements, their "
        "derivations, the terms, the comments and the table. The Phase 5 gates check that each requirement has a "
        "statement, one subject, a derivation from a need and one verification method. Review judges whether the "
        "requirements are the right ones."),
)
#: requirement -> the guide's Phase 5 bullet after its id, pinned whole
GUIDE_BULLETS = {
    "REQ-HMI-001": (
        "`reqShowTheSceneAsGiven`, from `NEED-HMI-001`, functional, test: shows each scene that reaches it, or a "
        "newer one, within the presentation time and as the driver-assistance system gives it, apart from the outages "
        "in the IVI VM."),
    "REQ-HMI-002": (
        "`reqMarkTheObjectTheSystemActsOn`, from `NEED-HMI-001`, functional, test: shows the object that the system "
        "acts on, and no other, apart from the objects of the scene, with its distance to the whole metre and its "
        "speed to the whole km/h."),
    "REQ-HMI-003": (
        "`reqShowTheVehicleSpeed`, from `NEED-HMI-002`, functional, test: shows each vehicle speed, or a newer one, "
        "within the presentation time, to the whole km/h."),
    "REQ-HMI-004": (
        "`reqCollisionWarningWhileRequested`, from `NEED-HMI-003`, functional, test: gives the collision warning on "
        "the display and as a sound while, and only while, the warning request asks for it."),
    "REQ-HMI-005": (
        "`reqStartEachWarningModeWithinLimit`, from `NEED-HMI-003`, a performance requirement, test: starts each mode "
        "within 0.1 s of wall-clock time after the start of a request reaches the display."),
    "REQ-HMI-006": (
        "`reqShowOutdatedElementsAsOutdated`, from `NEED-HMI-005`, functional, test: shows each element as outdated "
        "while, and only while, it is outdated."),
    "REQ-HMI-007": (
        "`reqShowWarningUnavailableWhileRequestOutdated`, from `NEED-HMI-005`, functional, test: shows that the "
        "collision warning is unavailable while, and only while, the warning request is outdated; the one degraded "
        "response of the set."),
    "REQ-HMI-008": (
        "`reqSpeedAndWarningThroughOutages`, from `NEED-HMI-004`, functional, test: keeps the speed, the warning and "
        "its unavailability throughout each outage in the IVI VM."),
    "REQ-HMI-009": (
        "`reqRendererSplitAndInputPaths`, from `NEED-HMI-004`, a design constraint, inspect: the speed, the warning "
        "and its sound by the high availability renderer in an SDV Media VM, the scene by an app in the IVI VM, and "
        "their paths from the SDV Core VM inside the display."),
    "REQ-HMI-010": (
        "`reqRecordDisplayIdentity`, from `NEED-HMI-006`, functional, test: records the display identity before its "
        "first frame on the display in each run."),
}
#: the Phase 5 decisions that the guide lists, in order, pinned whole
GUIDE_DECISIONS = (
    (
        "The speed of the closest object is shown as the fusion of the driver-assistance system gives it, with the "
        "sign that the fusion declares, in km/h: a speed that the display works out itself would be an estimate of "
        "its own."),
    (
        "The object that the system acts on is the closest object that the fusion gives as valid below 150 m; at the "
        "fixed distance of 150 m none is marked. The value is compared when the pin moves."),
    (
        "The display shows that object as an element of its own and marks none of the objects of the scene as it, "
        "since the scene names none."),
    (
        "Distances are shown to the whole metre and speeds to the whole km/h; the rest of the scene is shown as the "
        "system gives it."),
    (
        "The vehicle speed is the speed that the vehicle gives the driver-assistance system at its input, with its "
        "sample time, and not the copy that the system reads in each pass."),
    (
        "The collision warning lasts while, and only while, the warning request asks for it; a continuing request "
        "continues it."),
    (
        "The share of the display in the time that the driver-assistance increment allots from the warning request to "
        "each mode is 0.1 s of wall-clock time from the boundary of the display, chosen by analogy with the division "
        "on the path to the app of that increment and unmeasured for the renderer, for the app that draws the scene "
        "and for the sound. Every change of what the display shows takes the same 0.1 s as its presentation time."),
    (
        "An element is outdated once its time is more than 0.2 s of simulation time older than the newest time at the "
        "display, or once 0.2 s of wall-clock time pass with no new value of its input: two periods of 0.1 s. Late "
        "and missing values count alike."),
    (
        "The warning is unavailable while the warning request is outdated and available again once it is current. A "
        "renderer that cannot give the warning is left for a later increment."),
    (
        "The speed and the warning hold throughout each outage in the IVI VM. While the app that draws the scene "
        "gives no frame, the scene is shown as outdated within the limits of the term current and the presentation "
        "time, which no probe has measured for an outage; no limit on the return of the scene is set before a probe "
        "measures it."),
    (
        "The speed, the warning and its sound go to the high availability renderer in an SDV Media VM and the scene "
        "to an app in the IVI VM, by the owner's decision of 2026-11-17."),
    (
        "The display identity hashes the builds of the renderer and of the app that draws the scene, the images of "
        "both guest VMs, the sound file and each configuration file, and records the settings of its start, before "
        "the first frame of each run."),
    (
        "No requirement carries a feature link yet: phase 9 links `REQ-HMI-001` and `REQ-HMI-002` to the driving "
        "application and `REQ-HMI-001`, `REQ-HMI-008`, `REQ-HMI-009` and `REQ-HMI-010` to the AAOS SDV guest."),
)

VISIONPILOT_PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
VISIONPILOT_BLOB = f"https://github.com/autowarefoundation/vision_pilot/blob/{VISIONPILOT_PIN}/"
#: the line that opens the record's list of what the rationales cite
UPSTREAM_LEAD = "What the requirements of Phase 5 cite, at the same commit:"
#: one permalink per line range that a rationale cites: (path at the pin, anchor, what the lines hold)
UPSTREAM_LINKS = [
    ("VisionPilot/app/vision_pilot.cpp", "L147-L150",
     "the system plans on the closest object only when the fusion gives it as valid and nearer than 150 m."),
    ("VisionPilot/app/vision_pilot.cpp", "L177",
     "the system hands its results to the visualization only when the setting `visualization_on` is on."),
    ("VisionPilot/modules/models/include/models/inference.hpp", "L38-L52",
     "the inference result carries a frame identity and durations measured on the host, and no capture time."),
    ("VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp", "L17-L18",
     (
         "the fused distance in metres and the fused speed in metres per second, which the file's comment gives as "
         "negative when the object approaches.")),
    ("VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp", "L56-L73",
     (
         "the fixed distance of 150 m at which the fusion gives a valid closest object where neither network confirms "
         "one.")),
    ("VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp", "L181-L210",
     "the levels 1 and 2, and the cut-in."),
    ("VisionPilot/modules/visualization/include/visualization/occupancy_view.hpp", "L23-L48",
     "the scene of the panel, with no speed of the closest object and no time."),
    ("VisionPilot/modules/visualization/src/occupancy_bridge.cpp", "L20-L84",
     "how the bridge fills that scene, and the mark from AutoDrive alone."),
    ("VisionPilot/modules/visualization/src/visual_interface.cpp", "L304-L323",
     "the label of the distance in whole metres."),
    ("VisionPilot/modules/visualization/src/visual_interface.cpp", "L645-L648",
     "the one place where the visualization hands the scene to the panel, in a build with `ENABLE_OCCUPANCY`."),
]

#: Claims the charter excludes.
EXCLUDED = re.compile(r"(?i)certif\w*|homologat\w*|complian\w*|type approval|on-road|production-ready|member product")
#: Wording that belongs to the review of the answer, carried by a statement of none.
STATEMENT_REVIEW_WORDING = re.compile(r"(?i)\b(?:autopilot|replay\w*|overlay\w*|recording)\b")
#: a positive safety claim; "no safety claim" is the non-claim
SAFETY_CLAIM = re.compile(r"(?i)(?<!no )\bsaf(?:e|ety|ely)\b")
#: a positive timing claim; "no timing claim" is the non-claim
TIMING_CLAIM = re.compile(r"(?i)(?<!no )\b(?:timing|latency|jitter|in time|real[- ]time|deadline)\b")
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")
#: a time limit with its unit
TIMED = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|s)\b")
#: wording that phase 5 replaced
OLD_TEXTS = (HEADER_OLD, GUIDE_NEXT_OLD, "displayed frame", "detected objects", *REMOVED_COMMENTS)
#: a file and lines of the pinned source, as a rationale cites them
CITATION = re.compile(r"\b(\w+\.(?:cpp|hpp)):(\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*)")

#: The word patterns of the tests that read the files phase 5 changes, copied from those modules, and the rules of
#: the increment's texts. Each must find nothing in the phase 5 texts: (name, the texts it reads, pattern); "all" reads
#: every phase 5 text, "doc" all but the requirement attributes, whose rationales cite files and lines.
GUARDS = [
    ("needs EXCLUDED", "all", re.compile(
        r"(?i)\b(?:certif\w*|homologat\w*|complian\w*|complies|approv\w*|type.approv\w*|admi(?:t|ss)\w*|on-road|"
        r"member products?|passe[sd]|fail(?:s|ed))\b")),
    ("needs SAFETY_CLAIM", "all", SAFETY_CLAIM),
    ("needs TIMING_CLAIM", "all", TIMING_CLAIM),
    ("needs DISPLAY_RULE, no third mention", "all", re.compile(r"(?i)display-rule decision")),
    ("needs amend or correct of 2026-11-22", "all", re.compile(r"(?i)\b(?:amend\w*|correct\w*) (?:on|of) 2026-11-22")),
    ("framing PAST_BEHAVIOR", "all", re.compile(
        r"(?i)\b(?:braked|warned|stopped|collided|avoided|detected|passed|failed|displayed|rendered|showed|crashed|"
        r"hung)\b")),
    ("framing APPROVAL", "all",
     re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")),
    ("framing instrument", "all", re.compile(r"(?i)instrument")),
    ("framing exchange", "all", re.compile(
        r"(?i)\bDE4SDV (?:has )?(?:confirmed|agreed|asked|contacted|told|informed|reported|discussed|opened|sent)\b")),
    ("context WRONG_WARNING_TIME", "all", re.compile(r"time from the (?:warning )?request to each mode")),
    ("context warning time without the increment that allots it", "all",
     re.compile(r"(?i)(?<!increment allots )\bfrom the (?:warning )?request to each mode\b")),
    ("no translation label", "all", re.compile(r"(?i)\btranslat\w*")),
    ("no upstream line outside a rationale", "doc", re.compile(r"\.(?:cpp|hpp|rs|conf|yaml|txt):\d")),
    ("no timing word of a claim", "all", re.compile(r"(?i)\b(?:latency|deadline|real-time|in time)\b")),
]
#: a word that no text of the increment carries, held as its SHA-256 so that this file does not carry it either
EXCLUDED_WORD_SHA256 = "647d177cca8601046a3cb39e12f55bec5790bfcbc42199dd5fcf063200fac1d0"

REQUIREMENT_PATTERN = re.compile(
    r"\brequirement\s+<'(REQ-HMI-[^']+)'>\s+(\w+)\s*:\s*(FunctionalRequirementCandidate|RequirementCandidate)\b")


def _raw() -> str:
    assert MODEL.is_file(), "phase 5 of INC-HMI-001 adds its requirements to the needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _short(name: str) -> str:
    return REQUIREMENTS[name][0]


def _requirement(name: str) -> str:
    short, _need, kind, _method = REQUIREMENTS[name]
    return braced_body(_raw(), f"requirement <'{short}'> {name} : {kind}")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def _texts(name: str) -> dict[str, str]:
    body = _requirement(name)
    return {"statement": _statement(body), "source": _attribute(body, "source"),
            "rationale": _attribute(body, "rationale"), "criteria": _attribute(body, "successCriteria")}


def _terms_comment() -> str:
    matches = re.findall(rf"\bcomment\s+{TERMS_COMMENT}\s*/\*(.*?)\*/", _raw(), re.S)
    assert len(matches) == 1, "one comment defines the terms of the requirements"
    return matches[0]


def _header_paragraphs() -> list[str]:
    return [_flat(part) for part in re.split(r"\n\s*\*\s*\n", _raw().split("\npackage ", 1)[0])]


def _gap_comment(name: str) -> str:
    targets, _text = GAP_COMMENTS[name]
    match = re.search(rf"\bcomment\s+{name}\s+about\s+{re.escape(', '.join(targets))}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, name
    return _flat(match.group(1))


def _concern_doc() -> str:
    raw_concern = braced_body(_raw(), f"concern {CONCERN} : RequirementTraceConcern")
    doc = re.search(r"\bdoc\s*/\*(.*?)\*/", raw_concern, re.S)
    assert doc, "the concern has its doc"
    return _flat(doc.group(1))


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING, 1)[1].split("\n## ", 1)[0]


def _record_block() -> str:
    record = RECORD.read_text(encoding="utf-8")
    section = record.split("\n## VisionPilot scene\n", 1)[1].split("\n## ", 1)[0]
    assert section.count(UPSTREAM_LEAD) == 1, "the record lists what the rationales cite once, in its scene section"
    return section.split(UPSTREAM_LEAD, 1)[1]


def test_the_requirements_are_exactly_the_ten_of_phase_5_in_order():
    declared = REQUIREMENT_PATTERN.findall(_code())
    assert declared == [(short, name, kind) for name, (short, _need, kind, _method) in REQUIREMENTS.items()]
    assert len(declared) <= SCOPE_CAP, "the charter's scope cap: at most ten requirements"
    assert [short for short, _name, _kind in declared] == [f"REQ-HMI-{n:03d}" for n in range(1, len(declared) + 1)], \
        "REQ-HMI-001 onward, without a gap, in order"


def test_each_requirement_has_its_subject_one_statement_and_its_attributes():
    # SpecifyRequirements: requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
    # and the advisories requirementSubjectIsSystemOfInterest and requirementStatesSuccessCriteria.
    member = re.compile(r"subject\b|require constraint statement\b|attribute :>> (?:source|rationale|"
                        r"verificationMethod|successCriteria|verificationStatus)\b")
    for name, (_short, _need, _kind, method) in REQUIREMENTS.items():
        body = _requirement(name)
        code = strip_comments(body)
        subjects = re.findall(r"(?m)^\s*(subject\b[^\n]*)$", code)
        assert subjects == [SUBJECT_LINE], (name, subjects)
        statements = re.findall(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*', body)
        assert len(statements) == 1, (name, "one English statement")
        assert len(re.findall(r"\brequire\b", code)) == 1, (name, "one require constraint")
        assert _attribute(body, "verificationMethod") == method, name
        assert _attribute(body, "successCriteria").startswith("Met when"), name
        assert body.count("attribute :>> verificationStatus = VVStatus::NotStarted;") == 1, name
        assert len(re.findall(r"\bverificationStatus\b", code)) == 1, name
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        kinds = [member.match(line) for line in lines]
        assert all(kinds), (name, "a requirement body holds only its subject, statement and attributes", lines)
        assert [kind.group(0) for kind in kinds] == [
            "subject", "require constraint statement", "attribute :>> source", "attribute :>> rationale",
            "attribute :>> verificationMethod", "attribute :>> successCriteria",
            "attribute :>> verificationStatus"], name


def test_each_text_of_the_requirements_is_pinned_whole():
    for name in REQUIREMENTS:
        texts = _texts(name)
        assert texts["statement"] == STATEMENTS[name], (name, "statement")
        assert texts["source"] == SOURCES[name], (name, "source")
        assert texts["rationale"] == RATIONALES[name], (name, "rationale")
        assert texts["criteria"] == CRITERIA[name], (name, "criteria")


def test_each_statement_holds_one_obligation_in_the_positive_form():
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name))
        assert statement.count(" shall ") == 1, (name, "one obligation per statement")
        assert len(statement.split()) <= 60, (name, len(statement.split()))
        assert not re.search(r"\bnot\b", statement), (name, "the positive form")
        assert "n't" not in statement, (name, "the positive form")
        assert not STATEMENT_REVIEW_WORDING.findall(statement), (name, STATEMENT_REVIEW_WORDING.findall(statement))
        assert re.search(r"(?i)(?:^|, )the HMI display$", statement.split(" shall ", 1)[0]), \
            (name, "the HMI display is the subject of the statement")


def test_each_source_leads_with_its_need_and_wraps_in_its_column():
    for name, (_short, need, _kind, _method) in REQUIREMENTS.items():
        source = _attribute(_requirement(name), "source")
        assert source.startswith(NEED_SHORT[need] + ";"), (name, source)
        longest = max(source.split(), key=len)
        assert len(longest) <= 40, (name, longest)
        assert not re.search(r"\bconcern\s+\w+", source), (name, "a model-wide test reads 'concern <name>'")


def test_rationales_and_criteria_wrap_in_their_columns():
    for name in REQUIREMENTS:
        texts = _texts(name)
        for field in ("rationale", "criteria"):
            longest = max(texts[field].split(), key=len)
            assert len(longest) <= 40, (name, field, longest)


def test_no_requirement_text_makes_an_excluded_claim():
    for name in REQUIREMENTS:
        texts = _texts(name)
        for field in ("statement", "rationale", "criteria"):
            text = texts[field]
            for pattern in (EXCLUDED, SAFETY_CLAIM, TIMING_CLAIM):
                assert not pattern.findall(text), (name, field, pattern.findall(text))
            for old in OLD_TEXTS:
                assert old not in text, (name, field, old)
    raw = _raw()
    assert not CLAUSE_NUMBER.findall(raw), CLAUSE_NUMBER.findall(raw)


def test_each_timed_requirement_names_its_time_domain_and_its_non_claim():
    timed = []
    for name in REQUIREMENTS:
        texts = _texts(name)
        if TIMED.search(texts["statement"]):
            timed.append(_short(name))
            assert "within 0.1 s of wall-clock time" in texts["statement"], name
            assert "runs no faster than wall-clock time, which is the obligation of System 2" in texts["rationale"]
            assert "makes no timing claim for a vehicle." in texts["rationale"], name
    assert timed == TIMED_REQUIREMENTS
    # every limit of a criteria names its time domain
    for name in REQUIREMENTS:
        for match in TIMED.finditer(_texts(name)["criteria"]):
            rest = _texts(name)["criteria"][match.end():]
            assert rest.startswith(" of wall-clock time"), (name, match.group(0))


def test_the_presentation_time_bounds_each_change_of_what_the_display_shows():
    # REQ-HMI-005 sets 0.1 s of wall-clock time from the start of a request to each mode; the term presentation time
    # takes it for each change of what the display shows, so a display that shows each value late fails.
    taking = [_short(name) for name in REQUIREMENTS if "within the presentation time" in _statement(_requirement(name))]
    assert taking == PRESENTATION_TIME_REQUIREMENTS
    assert TERM_DEFINITIONS["Presentation time"].startswith("the 0.1 s of wall-clock time that REQ-HMI-005 sets ")
    for name in REQUIREMENTS:
        if _short(name) in PRESENTATION_TIME_REQUIREMENTS:
            assert "less than 0.1 s of wall-clock time after" in _texts(name)["criteria"], name
    assert TERM_DEFINITIONS["Within"] == "a time within a span after an instant is less than that span after it."
    assert "for the app that draws the scene and for the sound" in GAP_COMMENTS["warningPresentationFixedInPhase5"][1]


def test_each_criteria_states_its_count_of_runs_first():
    # a criteria over a filtered set of runs passes when the filter leaves nothing, so each states first how
    # many runs it judges, and the outage runs whose ends the subject controls end their outage within the run.
    assert sorted(NON_VACUITY) == sorted(REQUIREMENTS)
    for name, clause in NON_VACUITY.items():
        criteria = _texts(name)["criteria"]
        if clause is None:
            assert REQUIREMENTS[name][3] == "inspect" and "has at least one run" not in criteria, name
            continue
        assert criteria.startswith(f"Met when {clause}"), (name, criteria[:120])
    speed = _texts("reqShowTheVehicleSpeed")["criteria"]
    # a vehicle that holds its speed shows a constant speed rightly: only a value of the display's own fails
    assert "a fixed value of the display's own" in speed and "a constant speed" not in speed


def test_each_kind_opens_its_rationale():
    for name, (_short, _need, kind, _method) in REQUIREMENTS.items():
        rationale = _attribute(_requirement(name), "rationale")
        if kind == R:
            assert rationale.startswith(KIND_OPENING[KIND_WORDS[name]]), (name, KIND_WORDS[name])
        else:
            assert KIND_WORDS[name] == "functional", name
            assert not rationale.startswith(tuple(KIND_OPENING.values())), name


def test_each_requirement_derives_from_its_need_through_derives_from_need_only():
    # requirementDerivesFromNeed counts DerivesFromNeed only; a plain dependency to a need does not count
    # and is not declared.
    code = _code()
    derivations = re.findall(
        r"\bconnection\s+(\w+)\s*:\s*DerivesFromNeed\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert len(derivations) == 10
    expected = [(f"{name[3].lower()}{name[4:]}Derivation", need, name)
                for name, (_short, need, _kind, _method) in REQUIREMENTS.items()]
    assert derivations == expected
    assert len(re.findall(r"\bDerivesFromNeed\b", code)) == 10
    assert {need for _derivation, need, _name in derivations} == set(NEED_SHORT), "every need of phase 4 has one"
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    assert not [pair for pair in plain if pair[0] in REQUIREMENTS and pair[1].split("::")[-1] in NEED_SHORT]


def test_the_terms_are_defined_once_and_exactly():
    comment = _terms_comment()
    heads = tuple(re.findall(r"(?m)^\s*\*\s+- ([^:\n]+):", comment))
    assert heads == tuple(TERM_DEFINITIONS), heads
    expected = " ".join([TERMS_INTRO, *(f"- {head}: {definition}" for head, definition in TERM_DEFINITIONS.items())])
    assert _flat(comment) == expected, "the terms comment, whole"
    assert re.findall(rf"(?m)^\s*comment\s+{TERMS_COMMENT}\s*$", _raw()), "the comment annotates its package"


def _used_terms(text: str) -> set[str]:
    """The defined terms that a text uses: each occurrence of a head, its plural or a listed inflection, read as the
    longest defined term that covers it, so that "start of a request" uses Start of a request and never Request."""
    low = text.lower()
    found = []
    for head in TERM_DEFINITIONS:
        for form in (head.lower(), head.lower() + "s") + TERM_INFLECTIONS.get(head, ()):
            found += [(m.start(), m.end(), head) for m in re.finditer(rf"\b{re.escape(form)}\b", low)]
    taken, used = [], set()
    for start, end, head in sorted(found, key=lambda item: item[0] - item[1]):
        if all(end <= first or start >= last for first, last in taken):
            taken.append((start, end))
            used.add(head)
    return used


def test_each_statement_uses_defined_terms():
    by_short = {short: name for name, (short, _need, _kind, _method) in REQUIREMENTS.items()}
    assert sorted(STATEMENT_TERMS) == sorted(by_short)
    for short, heads in STATEMENT_TERMS.items():
        assert set(heads) <= set(TERM_DEFINITIONS), (short, sorted(set(heads) - set(TERM_DEFINITIONS)))
        # the list is exact: each listed term is used, and each defined term that the statement uses is listed
        assert _used_terms(_statement(_requirement(by_short[short]))) == set(heads), short


def test_the_gap_comments_record_what_phase_5_fixes_and_asks():
    raw = _raw()
    for name, (targets, text) in GAP_COMMENTS.items():
        declaration = f"comment {name} about {', '.join(targets)}"
        assert raw.count(declaration) == 1, declaration
        assert len(re.findall(rf"\bcomment\s+{name}\b", raw)) == 1, name
        assert _gap_comment(name) == text, name
    named = re.findall(r"(?m)^\s*comment\s+(\w+)", _code())
    assert named == [TERMS_COMMENT, *GAP_COMMENTS], "the terms and the three comments of phase 5, no other"


def test_the_header_states_phase_5():
    paragraphs = _header_paragraphs()
    assert len(paragraphs) == 8, "the header has its eight paragraphs"
    assert paragraphs[5:7] == [HEADER_PHASE_FIVE_SET, HEADER_PHASE_FIVE_VARIABILITY], \
        "the two paragraphs of phase 5, pinned whole, before the non-claims"
    assert HEADER_OLD not in _flat(_raw().split("\npackage ", 1)[0])
    assert paragraphs[-1].removesuffix("/").strip() == HEADER_NON_CLAIM, "the header keeps its non-claims"


def test_the_phase_4_contract_comments_are_now_stated_in_the_rationales():
    # Phase 4 kept two input contracts as comments about NEED-HMI-001 and NEED-HMI-003 for phase 5. Phase 5 states
    # them in the requirements and their rationales, so the comments no longer earn their place.
    raw = _raw()
    for name in REMOVED_COMMENTS:
        assert name not in raw, name
    assert not re.findall(r"\bcomment\s+\w+\s+about\s+(?:need\w+|DE4SDV_HmiDisplayNeedsRequirements::\w+)\b", raw)
    assert ("the system plans on the closest object only when it is valid and nearer than 150 m "
            "(vision_pilot.cpp:147-150)") in RATIONALES["reqMarkTheObjectTheSystemActsOn"]
    assert "and it does not read the plan (occupancy_bridge.cpp:20-77)" in RATIONALES["reqShowTheSceneAsGiven"]
    assert "The request does not tell the two apart" in RATIONALES["reqCollisionWarningWhileRequested"]
    assert "One plan holds" not in RATIONALES["reqCollisionWarningWhileRequested"], "a fact with no source of record"


def test_no_feature_link_before_phase_9():
    # Phase 3 classes the HMI display as content of every member; phase 9 decides on a link.
    raw = _raw()
    assert "DE4SDV_SDVProductLineFeatureModel" not in raw
    assert not re.search(r"\bimport\s+DE4SDV_ProductLine", raw)
    assert "#FeatureBinding" not in raw
    # rule 5 reads a dependency of a requirement on a feature, a variant or its definition as a link: no client of any
    # dependency is one of the ten, by declared name, qualified name or short name, in any place of the client list
    names = "|".join(REQUIREMENTS)
    shorts = "|".join(re.escape(short) for short, _need, _kind, _method in REQUIREMENTS.values())
    client = re.compile(rf"(?:^|[\s,:])(?:'?(?:{names})'?|'(?:{shorts})')(?![\w'])")
    for dependency in re.findall(r"\bdependency\b[^;{]*", _code()):
        clients = re.search(r"\bfrom\b(.*?)\bto\b", dependency, re.S)
        assert not (clients and client.search(clients.group(1))), f"a requirement has a dependency: {dependency}"
    # the method declares no satisfy link in phase 5
    assert not re.search(r"\bsatisfy\b", _code()), "phase 5 declares no satisfy link"
    # a link may also be declared in another file: no dependency of any model file has the HMI display or one of
    # the ten among its clients, by its plain or its qualified name
    subject = (r"(?:DE4SDV_HmiDisplayFraming::)?hmiDisplaySystem|"
               rf"(?:DE4SDV_HmiDisplayNeedsRequirements::)?(?:{names})")
    for path in sorted(p for root in MODEL_ROOTS for p in root.rglob("*.sysml")):
        for dependency in re.findall(r"\bdependency\b[^;{]*", strip_comments(path.read_text(encoding="utf-8"))):
            clients = re.search(r"\bfrom\b(.*?)\bto\b", dependency, re.S)
            assert not (clients and re.search(rf"(?<![\w:])(?:{subject})(?!\w)", clients.group(1))), \
                (path.name, "a link of the HMI display or a requirement before phase 9", dependency)


def _columns(body: str) -> list[str]:
    return re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews\s*\{", body)


def _column(body: str, column: str) -> str:
    return braced_body(body, f"view {column} :> columnViews")


def test_one_table_defines_each_requirement_with_its_verification_and_frames_the_trace_concern():
    code = _code()
    assert re.findall(r"\bconcern\s+(\w+)\s*:\s*RequirementTraceConcern\b", code) == [CONCERN]
    concern = braced_body(code, f"concern {CONCERN} : RequirementTraceConcern")
    lines = [line.strip() for line in concern.splitlines() if line.strip() and line.strip() != "doc"]
    assert lines[0] == "subject;", "the subject is the first parameter"
    holders = sorted(re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", concern))
    assert holders == CONCERN_HOLDERS
    rest = re.sub(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;|\bsubject\s*;|\bdoc\b", "", concern)
    assert not rest.strip(), ("the concern holds its doc, its subject and its stakeholders, nothing else", rest)
    assert _concern_doc() == CONCERN_DOC

    framing = []
    for view, kind in re.findall(r"\bview\s+(\w+)\s*:\s*([\w:]+)\s*\{", code):
        if re.search(rf"\bframe\s+{CONCERN}\s*;", braced_body(code, f"view {view} : {kind}")):
            framing.append((view, kind))
    assert framing == [(VIEW, "TVD::TableView")], "one table for phase 5, not two forms of the same requirements"
    body = braced_body(code, f"view {VIEW} : TVD::TableView")
    assert re.search(rf"\bviewpoint\s+{VIEWPOINT_USAGE}\s*:\s*{VIEWPOINT}\s*\{{\s*frame\s+{CONCERN}\s*;\s*\}}", body)
    assert re.findall(r"\bexpose\s+([^;]+);", body) == list(REQUIREMENTS)
    assert re.findall(r"\bfilter\b[^;]*;", body) == ["filter @ SysML::RequirementUsage;"]
    assert "attribute :>> includeReferenceElements = true;" in body
    assert f"attribute :>> maxRowHeight = {MAX_ROW_HEIGHT};" in body
    assert len(re.findall(r"\battribute\s+:>>", body)) == 2 + len(COLUMNS), "no attribute beyond the columns"
    assert "columnWidth" not in body, "the renderer reads no column width"
    assert not re.search(r"\bdoc\s*/\*", braced_body(_raw(), f"view {VIEW} : TVD::TableView")), "the table has no doc"
    assert _columns(body) == [column for column, _render in COLUMNS]
    for column, render in COLUMNS:
        text = _column(body, column)
        if render.startswith("CT::"):
            assert re.search(rf"featureToRender\s*=\s*{re.escape(render)}\s*;", text), column
        elif render == "constraintLanguage":
            assert re.search(r'CT::constraintLanguage\s*\{\s*attribute\s+constraintName\s*=\s*"statement"\s*;', text)
            assert re.search(r"attribute\s+constraintType\s*=\s*CL::ConT::required\s*;", text)
            assert re.search(r'attribute\s+constraintLanguage\s*=\s*"English"\s*;', text)
        else:
            assert re.search(rf'CT::attributeValue\s*\{{\s*attribute\s+attributeName\s*=\s*"{render}"\s*;\s*\}}',
                             text), column


def test_each_identity_and_declared_name_is_declared_once_in_the_model():
    declared = short_name_declarations(r"REQ-HMI-\d{3}", MODEL_ROOTS)
    assert sorted(declared) == sorted(short for short, _need, _kind, _method in REQUIREMENTS.values())
    for short, paths in declared.items():
        assert paths == [MODEL], (short, paths)
    names = [*REQUIREMENTS, *(f"{name[3].lower()}{name[4:]}Derivation" for name in REQUIREMENTS), TERMS_COMMENT,
             *GAP_COMMENTS, CONCERN, VIEW, VIEWPOINT_USAGE]
    counts = dict.fromkeys(names, 0)
    pattern = re.compile(r"\b(?:requirement|connection|comment|concern|view|part|attribute|item|action|dependency|"
                         r"port|interface|allocation|constraint|state|use\s+case|verification|analysis|viewpoint|"
                         r"rendering|occurrence|calc|enum|package)(?:\s+|(?=<))(?:def\b\s*)?(?:<'[^']*'>\s*)?"
                         r"(?!def\b)'?(\w+)\b")
    for path in sorted(path for root in MODEL_ROOTS for path in root.rglob("*.sysml")):
        for name in pattern.findall(strip_comments(path.read_text(encoding="utf-8"))):
            if name in counts:
                counts[name] += 1
    assert counts == dict.fromkeys(names, 1), {name: count for name, count in counts.items() if count != 1}


def test_the_guide_states_phase_5_and_the_next_obligation():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Stakeholder needs (Phase 4)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    blocks = re.split(r"\n\s*\n", raw_section.strip())
    shown = []
    for block in blocks:
        if block.startswith("- `REQ-HMI-"):
            shown.append("BULLETS")
        elif re.match(r"\d+\. ", block):
            shown.append("DECISIONS")
        else:
            shown.append(" ".join(block.split()))
    assert shown == list(GUIDE_BLOCKS), "the guide's Phase 5 section, block by block, whole"
    bullets = [(match[1], " ".join(match[2].split()))
               for match in re.finditer(r"(?ms)^- `(REQ-HMI-\d{3})` (.*?)(?=^- `|^\s*$)", raw_section)]
    assert bullets == list(GUIDE_BULLETS.items()), "the guide's Phase 5 bullets, pinned whole, in order"
    decisions = [(match[1], " ".join(match[2].split()))
                 for match in re.finditer(r"(?ms)^(\d+)\. (.*?)(?=^\d+\. |^\s*$)", raw_section)]
    assert decisions == [(str(n), text) for n, text in enumerate(GUIDE_DECISIONS, 1)], "the decisions, in order"
    for name, (short, need, _kind, method) in REQUIREMENTS.items():
        kind = {"functional": "functional", "performance": "a performance requirement",
                "design constraint": "a design constraint"}[KIND_WORDS[name]]
        assert GUIDE_BULLETS[short].startswith(f"`{name}`, from `{NEED_SHORT[need]}`, {kind}, {method}: "), short
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS_NEW) == 1 and GUIDE_STATUS_OLD not in flat
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert frame.count(GUIDE_FRAME_LINE) == 1
    phase_four = " ".join(guide.split("## Stakeholder needs (Phase 4)", 1)[1].split("\n## ", 1)[0].split())
    assert GUIDE_PHASE_FOUR_NEW in phase_four and GUIDE_PHASE_FOUR_OLD not in flat
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT_NEW) == 1 and GUIDE_NEXT_OLD not in flat
    assert guide.endswith("\n") and not guide.endswith("\n\n"), "the guide ends with exactly one newline"


def test_the_upstream_record_links_each_cited_line_range_at_the_pin():
    block = _record_block()
    items = re.findall(r"(?ms)^- \[([^\]]+)\]\(([^)]+)\):\n(.*?)(?=^- \[|\Z)", block)
    found = [(text, url, " ".join(what.split())) for text, url, what in items]
    assert found == [(path, f"{VISIONPILOT_BLOB}{path}#{anchor}", what) for path, anchor, what in UPSTREAM_LINKS], \
        "the record's Phase 5 links, whole, in order"
    # each line that a rationale cites lies inside a link to its file, and each link is cited
    ranges = []
    for path, anchor, _what in UPSTREAM_LINKS:
        first, _, last = anchor.removeprefix("L").partition("-L")
        ranges.append((path.rsplit("/", 1)[1], int(first), int(last or first)))
    used = set()
    cited = 0
    for name in REQUIREMENTS:
        for file, lines in CITATION.findall(_texts(name)["rationale"]):
            for part in lines.split(", "):
                start, _, end = part.partition("-")
                start, end = int(start), int(end or start)
                cited += 1
                holders = [r for r in ranges if r[0] == file and r[1] <= start and end <= r[2]]
                assert len(holders) == 1, (name, file, part)
                used.add(holders[0])
    assert cited >= len(UPSTREAM_LINKS), "the population of the check must not be vacuous"
    assert used == set(ranges), sorted(set(ranges) - used)


def _phase_five_texts() -> dict[str, tuple[str, str]]:
    """label -> (the scope it belongs to, its text): every text that phase 5 writes, as it stands in the files."""
    texts = {}
    for name in REQUIREMENTS:
        for field, text in _texts(name).items():
            texts[f"{name} {field}"] = ("all", text)
    texts["terms comment"] = ("doc", _flat(_terms_comment()))
    for name in GAP_COMMENTS:
        texts[f"comment {name}"] = ("doc", _gap_comment(name))
    paragraphs = _header_paragraphs()
    texts["header of phase 5"] = ("doc", " ".join(paragraphs[5:7]))
    texts["concern doc"] = ("doc", _concern_doc())
    guide = _guide()
    texts["guide Phase 5 section"] = ("doc", " ".join(_guide_section(guide).split()))
    for label, phrase in (("guide status", GUIDE_STATUS_NEW), ("guide frame line", GUIDE_FRAME_LINE),
                          ("guide Phase 4 paragraph", GUIDE_PHASE_FOUR_NEW), ("guide next", GUIDE_NEXT_NEW)):
        assert phrase in " ".join(guide.split()), label
        texts[label] = ("doc", phrase)
    texts["upstream record"] = ("doc", " ".join(_record_block().split()))
    return texts


def test_the_phase_5_texts_pass_the_word_patterns_of_the_files_they_land_in():
    texts = _phase_five_texts()
    assert len(texts) >= 50, "the population of the check must not be vacuous"
    for name, scope, pattern in GUARDS:
        for label, (kind, text) in texts.items():
            if scope == "all" or kind == "doc":
                assert not pattern.findall(text), (name, label, pattern.findall(text))


def test_no_text_of_the_increment_carries_the_excluded_word():
    for path in (MODEL, GUIDE, RECORD, HMI / "VIEWS.md", *sorted((ROOT / "tests").glob("test_hmi_display_*.py"))):
        words = set(re.findall(r"[a-z0-9]+", path.read_text(encoding="utf-8").lower()))
        assert len(words) >= 100, path.name
        digests = {hashlib.sha256(word.encode()).hexdigest() for word in words}
        assert EXCLUDED_WORD_SHA256 not in digests, path.name
