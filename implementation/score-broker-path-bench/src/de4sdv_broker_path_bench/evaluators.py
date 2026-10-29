"""Pure evaluators of the running verification cases, from raw run artifacts.

Each evaluator reads a run directory and returns a CaseResult whose outcome is
of the middleware evidence vocabulary (outcome.py), mapped to a verdict as
INC-MW-010 maps it. It verifies one requirement and checks the success
criteria of the verification case of #448, adding no criterion of its own. It
reads the independent captures and the relay's log; it never opens a socket
and never runs on the VM.

Precedence (decision of 2026-10-29, #448 VC-MW-015): only a failure whose
evidence does not depend on an inconclusive condition dominates. A
clock-dependent or capture-dependent failure is downgraded to inconclusive
when its condition is inconclusive (outcome.Finding.depends_on).

Run directory, by convention:
- produced.pcap  host capture of the frame assembler stream (lo:4721);
- received.pcap  guest capture of the relay stream (IVI lo:4731);
- relay-logcat.txt  the IVI logcat with the relay's events;
- clock-start.pcap, clock-end.pcap  the NTP exchanges of ASM-MW-030;
- settings.json  the run settings (ports, the relay's logcat tag, condition);
- for VC-MW-016: sd_offer.json or residual.json;
- for VC-MW-017: the probe artifacts of probe.py;
- frame_assembler_clients.json  the ss client check of ASM-MW-029 (VC-MW-015).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import clock, frames, probe, relay_log
from .outcome import BLOCKED, ERROR, FAIL, INCONCLUSIVE, PASS, CaseResult
from .pcap import PcapError, datagrams, read_pcap, tcp_streams

DEFAULT_PRODUCED_PORT = 4721
DEFAULT_RECEIVED_PORT = 4731
MAX_GAP_NS = 500_000_000            # the inter-arrival bound of REQ-MW-014
PHASE_SLOP_NS = clock.CLOCK_BOUND_NS  # 20 ms: a produced frame counts as in a phase within this of its edges


@dataclass
class RunInputs:
    run_dir: Path
    settings: dict

    @property
    def produced_port(self) -> int:
        return int(self.settings.get("produced_port", DEFAULT_PRODUCED_PORT))

    @property
    def received_port(self) -> int:
        return int(self.settings.get("received_port", DEFAULT_RECEIVED_PORT))

    @property
    def relay_tag(self) -> str | None:
        tag = self.settings.get("relay_logcat_tag")
        return str(tag) if tag else None

    @property
    def condition(self) -> str | None:
        condition = self.settings.get("condition")
        return str(condition) if condition else None


def load_run(run_dir: str | Path) -> RunInputs:
    run_dir = Path(run_dir)
    settings_path = run_dir / "settings.json"
    settings = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            settings = {"_settings_error": True}
    return RunInputs(run_dir, settings)


# --- raw-artifact readers -------------------------------------------------

@dataclass
class Capture:
    frames: list  # frames.StreamFrame
    had_gap: bool
    error: str | None
    present: bool


def _read_frames(run: RunInputs, name: str, port: int) -> Capture:
    path = run.run_dir / name
    if not path.exists():
        return Capture([], False, None, present=False)
    try:
        capture = read_pcap(path)
    except PcapError as error:
        return Capture([], True, str(error), present=True)
    collected = []
    had_gap = capture.truncated
    for index, stream in enumerate(tcp_streams(datagrams(capture), port)):
        if stream.gaps or stream.mid_stream_start:
            had_gap = True
        stream_frames, problems = frames.split_frames(stream, index)
        if any("capture gap" in problem or "resync" in problem for problem in problems):
            had_gap = True
        collected.extend(stream_frames)
    collected.sort(key=lambda item: item.delivered_ns)
    return Capture(collected, had_gap, None, present=True)


def _facts(frame) -> "frames.FrameFacts | None":
    try:
        return frames.frame_facts(frame.payload)
    except frames.WireError:
        return None


def _relay(run: RunInputs) -> tuple[list[dict], list, list[str], bool]:
    """(events, phases, phase_problems, present). An unreadable or absent log is not present."""
    path = run.run_dir / "relay-logcat.txt"
    if not path.exists() or run.relay_tag is None:
        return [], [], [], False
    events = relay_log.relay_events(path.read_text(errors="replace").splitlines(), run.relay_tag)
    all_phases, problems = relay_log.phases(events)
    return events, all_phases, problems, True


def _clock(run: RunInputs) -> dict:
    out = {}
    for name, key in (("clock-start.pcap", "start"), ("clock-end.pcap", "end")):
        path = run.run_dir / name
        if not path.exists():
            continue
        try:
            capture = read_pcap(path)
        except PcapError:
            continue
        found, _problems = clock.exchanges(capture, run.settings.get("sntp_server"))
        measurement = clock.best(found)
        if measurement is not None:
            out[key] = measurement
    return out


def _load_json(run: RunInputs, name: str):
    path = run.run_dir / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return "ERROR"


def _second_client_held_4721(run: RunInputs) -> bool | None:
    """ASM-MW-029: whether a client other than the adapter held the frame assembler.

    The record is the ss check (frame_assembler_clients.json): {adapter_only: bool}.
    None when the record is absent.
    """
    record = _load_json(run, "frame_assembler_clients.json")
    if not isinstance(record, dict):
        return None
    return record.get("adapter_only") is not True


# --- VC-MW-015: REQ-MW-014, source order ----------------------------------

def evaluate_source_order(run: RunInputs) -> CaseResult:
    result = CaseResult("VC-MW-015", run.run_dir.name)
    produced = _read_frames(run, "produced.pcap", run.produced_port)
    received = _read_frames(run, "received.pcap", run.received_port)
    if not produced.present or not received.present:
        result.add("capture", INCONCLUSIVE, "produced.pcap or received.pcap is missing")
        return result
    if produced.error or received.error:
        result.add("capture", ERROR, f"a capture is unreadable: {produced.error or received.error}")
        return result

    produced_facts = [(frame, _facts(frame)) for frame in produced.frames]
    received_facts = [(frame, _facts(frame)) for frame in received.frames]
    if any(facts is None for _frame, facts in produced_facts + received_facts):
        result.add("frame", ERROR, "a frame on the path did not decode as a VisualizationFrame")
        return result

    # The AEBS event must show all four stages among the produced frames.
    stages = {frames.stage(facts) for _frame, facts in produced_facts}
    if any(stage not in stages for stage in frames.STAGES):
        result.add("event", INCONCLUSIVE, f"the produced frames do not show every stage; have {sorted(stages)}")

    events, all_phases, phase_problems, relay_present = _relay(run)
    if not relay_present:
        result.add("relay-log", INCONCLUSIVE, "no relay logcat (with the tag) to read the subscription phases")
    elif not events:
        result.add("relay-log", INCONCLUSIVE, "the relay logcat has no events with the relay tag")
    for problem in phase_problems:
        result.add("relay-log", INCONCLUSIVE, f"relay phase record: {problem}")
    result.measurements["relay_phases"] = len(all_phases)

    # Clock-independent, dominating failures in the event.
    if relay_present:
        for phase in all_phases:
            if phase.end_realtime_ns is None:
                continue
            if phase.layer_caused_end:
                result.add("phase-end", FAIL, f"the layer ended a subscription phase (pid {phase.pid}, "
                           f"{phase.number}) by {phase.end_cause!r} while the ingress stayed connected; "
                           "a layer-caused phase end is a delivery failure of the layer")
            elif phase.client_connected_at_end is False:
                result.add("ingress", INCONCLUSIVE, f"the ingress disconnected in phase (pid {phase.pid}, "
                           f"{phase.number}); the run cannot show source order")
        for event in relay_log.data_loss_events(events):
            result.add("data-loss", FAIL, f"the relay read DATA_LOSS in subscription {event.get('subscription')}; "
                       "a DATA_LOSS in the event is a sequence gap")

    # Order: received sequences must strictly increase.
    received_seq = [facts.sequence for _frame, facts in received_facts if facts.sequence is not None]
    if any(b <= a for a, b in zip(received_seq, received_seq[1:])):
        result.add("order", FAIL, "the received frames are not in strictly increasing sequence order")

    # ASM-MW-029 and ASM-MW-030 gate the completeness evidence.
    second_client = _second_client_held_4721(run)
    if second_client is True:
        result.add("asm-mw-029", INCONCLUSIVE, "another client held the frame assembler stream (ASM-MW-029)")
    elif second_client is None:
        result.add("asm-mw-029", INCONCLUSIVE, "no frame-assembler client check (ASM-MW-029) in the run")

    measurements = _clock(run)
    clock_ok = "start" in measurements and "end" in measurements and measurements["start"].holds() \
        and measurements["end"].holds()
    stepped = relay_present and any(step.get("in_phase") is True for step in relay_log.clock_steps(events))
    if not clock_ok or stepped:
        result.add("delivery_evidence", INCONCLUSIVE, "ASM-MW-030 does not hold in the run, so the phase mapping "
                   "of the produced frames is not reliable")
    if received.had_gap:
        result.add("delivery_evidence", INCONCLUSIVE, "the guest capture has a gap, so a missing frame may be a "
                   "capture loss, not a delivery failure")

    # Required produced frames: those produced while a phase held (HMI subscribed).
    def in_a_phase(host_ts: int) -> bool:
        for phase in all_phases:
            end = phase.end_realtime_ns if phase.end_realtime_ns is not None else host_ts + 1
            if phase.start_realtime_ns - PHASE_SLOP_NS <= host_ts < end + PHASE_SLOP_NS:
                return True
        return False

    received_set = set(received_seq)
    required = [facts.sequence for _frame, facts in produced_facts
                if facts.sequence is not None and (not all_phases or in_a_phase(facts.frame_timestamp_ns or 0))]
    result.measurements["produced_frames"] = len(produced.frames)
    result.measurements["received_frames"] = len(received.frames)
    result.measurements["required_frames"] = len(required)
    missing = [seq for seq in required if seq not in received_set]
    if missing:
        result.add("completeness", FAIL, f"{len(missing)} frames produced while the HMI was subscribed never "
                   f"reached it; first {missing[:5]}", depends_on="delivery_evidence")

    gaps = [received.frames[i].delivered_ns - received.frames[i - 1].delivered_ns
            for i in range(1, len(received.frames))]
    if gaps:
        result.measurements["max_gap_ns"] = max(gaps)
    if any(gap > MAX_GAP_NS for gap in gaps):
        result.add("gap", FAIL, f"an inter-arrival gap exceeds 500 ms (largest {max(gaps)} ns)",
                   depends_on="delivery_evidence")

    if not any(f.outcome in (FAIL, INCONCLUSIVE, BLOCKED, ERROR) for f in result.findings):
        result.add("source-order", PASS, f"every required frame reached the HMI, in order, largest gap "
                   f"{max(gaps) if gaps else 0} ns")
    return result


# --- VC-MW-016: REQ-MW-015, provenance ------------------------------------

def evaluate_provenance(run: RunInputs) -> CaseResult:
    result = CaseResult("VC-MW-016", run.run_dir.name)
    produced = _read_frames(run, "produced.pcap", run.produced_port)
    received = _read_frames(run, "received.pcap", run.received_port)
    if not produced.present or not received.present:
        result.add("capture", INCONCLUSIVE, "produced.pcap or received.pcap is missing")
        return result
    if produced.error or received.error:
        result.add("capture", ERROR, f"a capture is unreadable: {produced.error or received.error}")
        return result

    produced_by_seq: dict[int, bytes] = {}
    for frame in produced.frames:
        facts = _facts(frame)
        if facts is None:
            result.add("frame", ERROR, "a produced frame did not decode")
            return result
        if facts.sequence is not None:
            produced_by_seq[facts.sequence] = frame.payload
    stages = {frames.stage(frames.frame_facts(p)) for p in produced_by_seq.values()}
    if any(stage not in stages for stage in frames.STAGES):
        result.add("event", INCONCLUSIVE, "the produced frames do not show every stage of the event")

    # The SD offer record (the IVI VM must not redirect the stack), or the
    # GAP-MW-012 residual record.
    sd_offer = _load_json(run, "sd_offer.json")
    residual = _load_json(run, "residual.json")
    if sd_offer == "ERROR" or residual == "ERROR":
        result.add("sd-offer", ERROR, "sd_offer.json or residual.json is not valid JSON")
        return result
    if isinstance(sd_offer, dict):
        provider = sd_offer.get("provider_after_offer")
        if provider not in (None, "192.168.98.1"):
            result.add("sd-redirect", FAIL, f"after the SD offer from the IVI VM the stack subscribed to "
                       f"{provider!r}, not 192.168.98.1")
    elif isinstance(residual, dict) and residual.get("gap") == "GAP-MW-012":
        result.measurements["residual"] = "GAP-MW-012 recorded (no pin or filter)"
    else:
        result.add("sd-offer", INCONCLUSIVE, "no SD-offer record and no GAP-MW-012 residual record")

    compared = 0
    for frame in received.frames:
        facts = _facts(frame)
        if facts is None:
            result.add("frame", ERROR, "a received frame did not decode")
            return result
        seq = facts.sequence
        produced_payload = produced_by_seq.get(seq)
        if produced_payload is None:
            if received.had_gap or produced.had_gap:
                result.add("pairing", INCONCLUSIVE, f"received frame {seq} has no produced frame, and a capture "
                           "has a gap")
            else:
                result.add("unproduced", FAIL, f"received frame {seq} was never produced by the AEBS stack")
            continue
        compared += 1
        if frame.payload != produced_payload:
            differences = frames.diff_trees(frames.field_tree(produced_payload), frames.field_tree(frame.payload))
            result.add("bytes", FAIL, f"frame {seq} differs from its produced frame: {differences[:3]}")
            continue
        for number, kind in facts.source_kinds.items():
            if number in frames.NOT_NATIVE_FIELDS and kind == frames.NATIVE:
                result.add("source-kind", FAIL, f"frame {seq}: field {frames.FIELD_NAMES.get(number)} carries "
                           "coordinator or display-derived output but arrived marked native Autoware AEB")

    # Frames must keep arriving after the offer (no silent redirect/stop).
    if isinstance(sd_offer, dict) and received.frames:
        gaps = [received.frames[i].delivered_ns - received.frames[i - 1].delivered_ns
                for i in range(1, len(received.frames))]
        if any(gap >= MAX_GAP_NS for gap in gaps):
            result.add("sd-stop", FAIL, "the received frames stop for the inter-arrival bound or longer after the "
                       "SD offer")

    result.measurements["frames_compared"] = compared
    if compared == 0:
        result.add("pairing", INCONCLUSIVE, "no received frame paired with a produced frame")
    if not any(f.outcome in (FAIL, INCONCLUSIVE, ERROR, BLOCKED) for f in result.findings):
        result.add("provenance", PASS, f"{compared} received frames equal their produced frames, byte for byte, "
                   "with their source kinds")
    return result


# --- VC-MW-017: REQ-MW-016, no application data from the guest -------------

def evaluate_isolation(run: RunInputs) -> CaseResult:
    result = CaseResult("VC-MW-017", run.run_dir.name)
    verdict = probe.evaluate_isolation(run.run_dir)
    for error in verdict.errors:
        result.add("probe", ERROR, error)
    if verdict.errors:
        return result
    result.measurements["probe_attempts"] = verdict.attempts
    result.measurements["asm_mw_031_holds"] = verdict.asm_mw_031_holds

    # A reachable DDS port of a layer element fails, whatever the control or ASM-MW-031 show.
    for reached in verdict.layer_reachable:
        result.add("layer-reachable", FAIL, f"a guest domain reached layer DDS port {reached.get('port')} "
                   f"from {reached.get('guest')} over {reached.get('interface')}")
    # A reachable DDS port of a process outside the layer: fail only while ASM-MW-031 holds.
    for reached in verdict.other_reachable:
        if verdict.asm_mw_031_holds:
            result.add("other-reachable", FAIL, f"a guest reached host DDS port {reached.get('port')} of a process "
                       "outside the layer, and ASM-MW-031 holds")
        else:
            result.add("other-reachable", INCONCLUSIVE, f"a guest reached host DDS port {reached.get('port')} of a "
                       "process outside the layer, but ASM-MW-031 is not shown")
    # Port 4721 is an ASM-MW-029 finding, not a REQ-MW-016 failure.
    for reached in verdict.frame_assembler_reachable:
        result.measurements.setdefault("asm_mw_029_findings", []).append(
            f"port 4721 reachable from {reached.get('guest')} over {reached.get('interface')}")

    if not verdict.control_ok:
        result.add("control", INCONCLUSIVE, f"the positive control did not reach its host socket ({verdict.control_detail}); "
                   "an unreachable probe shows nothing")
    for gap in verdict.coverage_gaps:
        result.add("coverage", INCONCLUSIVE, gap)
    if not verdict.layer_reachable and not verdict.other_reachable and verdict.asm_mw_031_holds is not True:
        result.add("asm-mw-031", INCONCLUSIVE, "no layer DDS port was reachable, but ASM-MW-031 is not shown for the "
                   "other host processes")

    # The first finding (inspection of the interface and configuration).
    if not verdict.inspection_present:
        result.add("first-finding", INCONCLUSIVE, "no inspection record for the first finding (no host endpoint for "
                   "guest application data)")
    elif verdict.inspection_no_host_endpoint is not True:
        result.add("first-finding", FAIL, "the inspection found a host endpoint for guest application data")

    if not any(f.outcome in (FAIL, INCONCLUSIVE, ERROR, BLOCKED) for f in result.findings):
        result.add("isolation", PASS, f"no host DDS port of the layer was reachable in {verdict.attempts} probes, "
                   "the control reached its socket, and the inspection found no host endpoint")
    return result


# --- VC-MW-020: REQ-MW-019, discard while unsubscribed --------------------

def evaluate_unsubscribed_discard(run: RunInputs) -> CaseResult:
    result = CaseResult("VC-MW-020", run.run_dir.name)
    result.measurements["condition"] = run.condition or "unnamed"
    if run.condition is None:
        result.add("condition", INCONCLUSIVE, "the run names no condition; a case pass needs all four conditions")

    events, all_phases, phase_problems, relay_present = _relay(run)
    if not relay_present or not events:
        result.add("relay-log", INCONCLUSIVE, "no relay logcat (with the tag) to read the new subscription phases")
        return result
    for problem in phase_problems:
        result.add("relay-log", INCONCLUSIVE, f"relay phase record: {problem}")

    received = _read_frames(run, "received.pcap", run.received_port)
    if not received.present:
        result.add("capture", INCONCLUSIVE, "received.pcap is missing")
        return result
    if received.error:
        result.add("capture", ERROR, f"received.pcap is unreadable: {received.error}")
        return result

    # ASM-MW-030 gate: start and end offsets hold; no clock step in a judged phase.
    measurements = _clock(run)
    clock_ok = "start" in measurements and "end" in measurements and measurements["start"].holds() \
        and measurements["end"].holds()
    if "start" in measurements:
        result.measurements["offset_start_ns"] = measurements["start"].offset_ns
    if "end" in measurements:
        result.measurements["offset_end_ns"] = measurements["end"].offset_ns
    if not clock_ok:
        result.add("asm_mw_030", INCONCLUSIVE, "ASM-MW-030 does not hold in the run (offset plus uncertainty not "
                   "below 20 ms at start and end)")
    if any(step.get("in_phase") is True for step in relay_log.clock_steps(events)):
        result.add("asm_mw_030", INCONCLUSIVE, "a clock step fell inside a judged phase; the run is void")

    # Judge each frame against the phase it arrived in, raw (no offset correction, #448 and the rule).
    judged_frames = 0
    judged_phases: set = set()
    violations = 0
    for frame in received.frames:
        facts = _facts(frame)
        if facts is None:
            result.add("frame", ERROR, "a received frame did not decode")
            return result
        phase = relay_log.phase_at(all_phases, frame.delivered_ns)
        if phase is None:
            continue  # delivered outside any phase: not judged here
        judged_phases.add(phase.key)
        if facts.frame_timestamp_ns is None:
            result.add("timestamp", INCONCLUSIVE, f"a frame in phase {phase.key} has no frame timestamp")
            continue
        judged_frames += 1
        # Raw comparison: production time (host clock) vs phase start (guest clock) less the 20 ms margin.
        if facts.frame_timestamp_ns < phase.start_realtime_ns - PHASE_SLOP_NS:
            violations += 1
    result.measurements["judged_frames"] = judged_frames
    result.measurements["judged_phases"] = len(judged_phases)
    if judged_frames == 0:
        result.add("frames", INCONCLUSIVE, "no frame with a timestamp arrived in a judged phase")
    if violations:
        result.add("discard", FAIL, f"{violations} frames produced more than 20 ms before the new subscription "
                   "reached the HMI", depends_on="asm_mw_030")
    if not any(f.outcome in (FAIL, INCONCLUSIVE, ERROR, BLOCKED) for f in result.findings):
        result.add("discard", PASS, f"in condition {run.condition!r}, no frame produced before the new subscription "
                   "(less the 20 ms margin) reached the HMI")
    return result


EVALUATORS = {
    "VC-MW-015": evaluate_source_order,
    "VC-MW-016": evaluate_provenance,
    "VC-MW-017": evaluate_isolation,
    "VC-MW-020": evaluate_unsubscribed_discard,
}
