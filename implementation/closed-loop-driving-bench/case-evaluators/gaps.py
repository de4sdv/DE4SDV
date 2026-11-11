"""The observable records of ICD v2, as data.

One entry per change adopted into ICD v2 (section 3/6/7/8/10). `cases.py`
cites these ids in each evaluator's `needs`, and the tests strip the records
of one change at a time to prove that the case really needs it.

`unblocks` is derived from `cases.CASES[vc]["needs"]` (tests assert the two
agree); `campaign_unblocks` names the cases that need the change only to group
the runs of a campaign.

`V2_GAPS` is the other direction: the cases ICD v2 still cannot decide, and
the exact field + producer each one misses; `change`, where given, is the label
of the record change the case names in `icd_changes`, a label ICD v2 has not
adopted (not in ICD_CHANGES). OBSERVABLES.md's "Against ICD v2" section is the
prose half and the tests keep the two in step.

`AMENDMENT_CHANGES` records the rulings of ICD amendments 1 and 2 (A11, A16,
A17, ..., A34) that closed the earlier gaps; its entries have the same shape as
ICD_CHANGES and name the cases each ruling makes decidable.

Nothing here edits the ICD or the model.
"""

from __future__ import annotations

ICD_CHANGES: dict[str, dict] = {
    "C1": {
        "title": "World-side record: sensors and ego kinematics",
        "adds": (
            "simulator/world.jsonl, one record per tick: frame, sim_ms; egoPose "
            "{x, y, yaw}; velocity {speed_mps, heading_rad}; acceleration "
            "{longitudinal_mps2, lateral_mps2}; angular_velocity {roll, pitch, "
            "yaw_rad_s}; lane {road, lane, lat_m, junction}; sensors[] "
            "{name, actor_id, alive, attached} (no image digest: the pacer does "
            "not receive images); controlSource; autopilotEnabled; "
            "trafficManagerEnabled; collisions; laneInvasions."
        ),
        "where": "simulator host, pacer (world.jsonl)",
        "unblocks": ["VC-DRIVING-008", "VC-DRIVING-009", "VC-DRIVING-010", "VC-DRIVING-011", "VC-DRIVING-013", "VC-DRIVING-020", "VC-DRIVING-022", "VC-DRIVING-035"],
    },
    "C2": {
        "title": "Scaled checkpoint input record",
        "adds": (
            "score/checkpointInputs.jsonl, one record per step: frame, sim_ms; "
            "per camera {name, image_frame, capture_sim_ms, arrival_mono_ns, "
            "width, height, valid, status, history[] frame refs}; the ego-motion "
            "history rows (64 x 4); the projection operators once per run (and "
            "on change); map_context_render_sim_ms; corridor_cell_count; "
            "destination_cell_count; input_conditions. Full input bundles "
            "score/bundles/<frame>.npz for every 50th step and every step "
            "within +/-0.5 s of an injected fault."
        ),
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-001", "VC-DRIVING-002", "VC-DRIVING-003", "VC-DRIVING-004", "VC-DRIVING-005", "VC-DRIVING-006", "VC-DRIVING-007", "VC-DRIVING-008", "VC-DRIVING-009", "VC-DRIVING-010", "VC-DRIVING-013", "VC-DRIVING-023", "VC-DRIVING-030", "VC-DRIVING-032"],
    },
    "C3": {
        "title": "Command simulation-time stamps in the log record",
        "adds": (
            "commandVehicle's out.command (and the adapter's in.command) record "
            "carries step_capture_sim_ms and plan_capture_sim_ms. The command "
            "payload stays exact and gains no simulation field."
        ),
        "where": "S-CORE host, drivingAgent/commandVehicle (run log)",
        "unblocks": ["VC-DRIVING-026"],
    },
    "C4": {
        "title": "Campaign and variant identity in the run record",
        "adds": (
            "run_record.json: campaignId, runRole, scenarioVariant {fault, "
            "entrySpeedMps, aaosMode, checkpointCase}, inputReplay {sourceRun, "
            "digest}."
        ),
        "where": "S-CORE host, inference activity (run_record.json)",
        "unblocks": [],
        "campaign_unblocks": ["VC-DRIVING-018", "VC-DRIVING-019", "VC-DRIVING-020",
                              "VC-DRIVING-021", "VC-DRIVING-022", "VC-DRIVING-035"],
    },
    "C5": {
        "title": "Plan age in HEALTH",
        "adds": (
            "HEALTH fields 36-39: last_plan_capture_ms, step_capture_ms, "
            "last_plan_production_mono_s/_ns."
        ),
        "where": "S-CORE host, statePublisher (SOME/IP HEALTH event)",
        "unblocks": ["VC-DRIVING-017"],
    },
    "C6": {
        "title": "Checkpoint-refusal detail",
        "adds": (
            "HEALTH fields 41-43: checkpoint_expected_sha256, "
            "checkpoint_actual_sha256, refusal_reason (mismatch|no_pin); and the "
            "drivingAgent `error` record {code: checkpoint_refused, "
            "expectedSha256, actualSha256, reason} before any plan."
        ),
        "where": "S-CORE host, drivingAgent + statePublisher",
        "unblocks": ["VC-DRIVING-035"],
    },
    "C7": {
        "title": "Run-record provenance",
        "adds": (
            "run_record.json: checkpointPath, configurationPath, "
            "vehicleConfiguration {path, sha256}, navigationMap {path, sha256}, "
            "route {path, sha256}, writtenAtMonoNs, writtenAtRealNs. The "
            "checkpoint itself is retained once per campaign, not per run."
        ),
        "where": "S-CORE host, inference activity + Launch Manager",
        "unblocks": ["VC-DRIVING-012", "VC-DRIVING-033"],
    },
    "C8": {
        "title": "Bench injection and control record",
        "adds": (
            "bench/injection.jsonl {action: plan_inject|comm_stop|fault_begin|"
            "fault_end|camera_stop, t_sim_ms, t_mono_ns, t_real_ns, detail}."
        ),
        "where": "bench controller process",
        "unblocks": ["VC-DRIVING-011", "VC-DRIVING-012", "VC-DRIVING-014", "VC-DRIVING-027"],
    },
    "C9": {
        "title": "Clock suffixes on every stamp",
        "adds": (
            "ICD section 6: every time field in data names its clock with "
            "_sim_ms/_sim_s, _mono_ns/_mono_s or _real_ns; a payload crossing "
            "keeps its model field names and carries a sibling `clocks` object "
            "mapping each payload time field to its clock."
        ),
        "where": "all record producers",
        "unblocks": ["VC-DRIVING-001", "VC-DRIVING-009", "VC-DRIVING-012", "VC-DRIVING-013", "VC-DRIVING-014", "VC-DRIVING-016", "VC-DRIVING-020", "VC-DRIVING-021", "VC-DRIVING-022", "VC-DRIVING-024", "VC-DRIVING-025", "VC-DRIVING-026", "VC-DRIVING-028", "VC-DRIVING-030", "VC-DRIVING-031", "VC-DRIVING-032"],
    },
    "C10": {
        "title": "Priming-complete marker",
        "adds": (
            "score/drivingAgent.jsonl event priming.complete {frame, sim_ms, "
            "historiesReady}."
        ),
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-001", "VC-DRIVING-013", "VC-DRIVING-023", "VC-DRIVING-024",
                     "VC-DRIVING-025"],
    },
    "C11": {
        "title": "Reference-inference artifact",
        "adds": (
            "score/referenceInference.jsonl {frameIndex, checkpointSha256, "
            "sourceRevision, acceleration[64], curvature[64]} produced by the "
            "pinned checkpoint's Python reference on the retained bundles."
        ),
        "where": "S-CORE host, offline (after the run)",
        "unblocks": ["VC-DRIVING-002"],
    },
    "C12": {
        "title": "Plan producer and completeness on the PLAN publication",
        "adds": (
            "PLAN fields 16-18: plan_producer (drivingAgent/inferPlan), "
            "plan_sample_count, plan_horizon_s."
        ),
        "where": "S-CORE host, statePublisher",
        "unblocks": ["VC-DRIVING-015"],
    },
}


# Rulings of ICD amendments 1 and 2 the evaluators rely on. Same entry shape
# as ICD_CHANGES; kept apart because they extend records ICD v2 already has
# instead of adding a record, so no evaluator gains a `needs` id and the
# strip rules stay one per ICD_CHANGES key. evaluate_run.py names them per
# case (amendments_for).
AMENDMENT_CHANGES: dict[str, dict] = {
    "A11": {
        "title": "C2 per-step metadata (amendment 1)",
        "adds": (
            "score/checkpointInputs.jsonl, per step: cameras[front].front_hi_res "
            "{width, height}; marker {image_px, operator_coverage}; mapContext "
            "{channels, width, height, geometry}; routeMask {corridorCells, "
            "geometry, routeSha256}."
        ),
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-003", "VC-DRIVING-006", "VC-DRIVING-007"],
    },
    "A16": {
        "title": "C2 route coverage and raster pose (amendment 2)",
        "adds": (
            "routeMask adds waypointsInWindow and waypointsOnCorridor; the step "
            "adds rasterPose {x_map_m, y_map_m, yaw_map_rad}, the REF pose both "
            "rasters were rendered at. The in-window count is re-derivable from "
            "the route file and that pose."
        ),
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-007"],
    },
    "A17": {
        "title": "C2 image sizes (amendment 2)",
        "adds": (
            "A camera's width/height is the size of the image handed to the "
            "checkpoint (the 512x512 tile for the checkpoint engine); "
            "source_width/source_height is the simulator image, and "
            "cameras[front].front_hi_res is the 1024x1024 front image."
        ),
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-002", "VC-DRIVING-003"],
    },
    "A18": {
        "title": "Route provider log (amendment 2)",
        "adds": "Each route datagram is logged as out.route_announcement with "
                "clocks {issueTime: simulation}.",
        "where": "route provider (score/route_provider.jsonl)",
        "unblocks": ["VC-DRIVING-007", "VC-DRIVING-025"],
    },
    "A23": {
        "title": "Merged frames (amendment 2)",
        "adds": "C2's step record lists the older frames merged into it, "
                "{frame, conditioned, why, condition_ms, readyByDeadline}.",
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-001", "VC-DRIVING-023"],
    },
    "A24": {
        "title": "Adapter command timeout (amendment 2)",
        "adds": "The adapter's stop begins once more than 200 ms of simulation time "
                "have passed since the last valid command; it reaches the actuation "
                "300 ms after the last applied command.",
        "where": "simulator host, actuation adapter",
        "unblocks": ["VC-DRIVING-014", "VC-DRIVING-028"],
    },
    "A25": {
        "title": "C2 camera names (amendment 2)",
        "adds": "C2 names each camera by the checkpoint's slot, in the slot order; "
                "before, the CARLA role names cam_<slot>.",
        "where": "S-CORE host, drivingAgent/conditionInputs",
        "unblocks": ["VC-DRIVING-003"],
    },
    "A26": {
        "title": "primed and priming.complete (amendment 2)",
        "adds": "C2 primed and C10 priming.complete come from the planner's engine; "
                "a step the engine did not condition is not primed.",
        "where": "S-CORE host, drivingAgent",
        "unblocks": ["VC-DRIVING-001", "VC-DRIVING-009", "VC-DRIVING-013",
                     "VC-DRIVING-023", "VC-DRIVING-024", "VC-DRIVING-025"],
    },
    "A29": {
        "title": "Ego-motion history against the poses (amendment 2)",
        "adds": "No record is added. VC-DRIVING-008 works speed and acceleration out "
                "of the C1 egoPose of the 66 frames that end at the step, moved to "
                "the origin in drivingAgent's `rig` record (result.origin), and no "
                "longer reads C1 velocity or acceleration.",
        "where": "simulator host, world side (world.jsonl); S-CORE host, drivingAgent",
        "unblocks": ["VC-DRIVING-008"],
    },
    "A34": {
        "title": "Observation records (amendment 2)",
        "adds": "No record is added. The evaluators read the observation records as "
                "their producers write them: the observer's in.operational_state "
                "(guest/observer.jsonl: the 43 section 3 fields for every kind; kind, "
                "mode and cause as u32 values) and the publisher's "
                "out.operational_state (score/statePublisher.jsonl: kind, mode and "
                "cause by name, its own stamps as whole nanosecond counts and "
                "_sim_ms). The publisher writes its record after the send, so the "
                "record's t_mono_ns is the publication time of VC-DRIVING-015, -016 "
                "and -029. A run that holds only rx.plan, rx.vehicle_state, rx.health "
                "or out.health is missing evidence.",
        "where": "S-CORE host, statePublisher; IVI guest, observer app",
        "unblocks": ["VC-DRIVING-015", "VC-DRIVING-016", "VC-DRIVING-017",
                     "VC-DRIVING-029", "VC-DRIVING-035"],
    },
}


# Cases ICD v2 still cannot decide, with the exact missing field and its
# producer. The first token before the em dash is the ledger key.
V2_GAPS: dict[str, dict] = {
    "VC-DRIVING-005": {
        "missing": "marker pixel measured in an image: A11 logs marker.image_px, "
                   "but the case compares the operator with where the marker "
                   "actually appears, which a person must measure in a bundle",
        "producer": "drivingAgent/conditionInputs (marker) + a measured bundle image",
        "bundle": "1 bundle at frame 300 of the nominal run (all six cameras "
                  "valid), the marker measured in each image",
    },
    "VC-DRIVING-016": {
        "missing": "out.ego_motion_sample.arrival_mono_ns: when the world snapshot "
                   "the motion sample comes from arrived at the agent, whole "
                   "nanoseconds of the S-CORE host's monotonic clock, with "
                   "clocks.arrival_mono_ns = monotonic. The criterion counts from "
                   "when the driving system received the sample; the agent's record "
                   "carries no arrival time (ICD A34), and the frame store may hold "
                   "a sample up to 95 ms before the agent hands it on",
        "producer": "drivingAgent (agent/cc/agent_ffi.cpp, out.ego_motion_sample; "
                    "the frame store knows the arrival, FrameView::snapshotArrivalMonoNs)",
        "change": "C13",
    },
}


def changes_for(vc: str) -> list[str]:
    return sorted(cid for cid, c in ICD_CHANGES.items() if vc in c["unblocks"])


def amendments_for(vc: str) -> list[str]:
    return sorted(aid for aid, c in AMENDMENT_CHANGES.items() if vc in c["unblocks"])


def campaign_changes_for(vc: str) -> list[str]:
    return sorted(cid for cid, c in ICD_CHANGES.items()
                  if vc in (c.get("campaign_unblocks") or []))


def by_weight() -> list[tuple[str, int]]:
    """Change ids ordered by the number of single-run cases each unblocks."""
    rows = [(cid, len(c.get("unblocks") or []) + len(c.get("campaign_unblocks") or []))
            for cid, c in ICD_CHANGES.items()]
    return sorted(rows, key=lambda r: (-r[1], r[0]))
