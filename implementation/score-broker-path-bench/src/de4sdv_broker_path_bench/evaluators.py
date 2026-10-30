"""Pure evaluators of the running verification cases, from raw run artifacts.

Each evaluator reads a run directory and returns a CaseResult whose outcome is
of the middleware evidence vocabulary (outcome.py), mapped to a verdict as
INC-MW-010 maps it. It verifies one requirement and checks the success
criteria of its verification case (middleware_score_verification_evidence.sysml), adding no criterion of its own. It
reads the independent captures and the relay's log; it never opens a socket
and never runs on the VM.

Precedence (decision of 2026-10-29, VC-MW-015): only a failure whose
evidence does not depend on an inconclusive condition dominates. A
clock-dependent or capture-dependent failure is downgraded to inconclusive
when its condition is inconclusive (outcome.Finding.depends_on).

Run directory, by convention:
- produced.pcap  host capture of the frame assembler stream (lo:4721);
- received.pcap  guest capture of the relay stream (IVI lo:4731);
- data-tunnel-vlan2.pcap  guest capture of Data Tunnel on VLAN 2 (VC-MW-020's second start);
- relay-logcat.txt  the IVI logcat with the relay's events;
- clock-start.pcap, clock-end.pcap  the NTP exchanges of ASM-MW-030;
- settings.json  the run settings (ports, the relay's logcat tag, condition);
- for VC-MW-016: host-cvd-ebr.pcap (the SD capture) with sd_core_processed.json
  (the core stack's log line about the offer), or residual.json (GAP-MW-012);
- for VC-MW-017: the probe artifacts of probe.py;
- frame_assembler_clients.json  the ss client check of ASM-MW-029 (VC-MW-015).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import clock, dt, frames, probe, relay_log, sd
from .outcome import BLOCKED, ERROR, FAIL, INCONCLUSIVE, PASS, CaseResult
from .pcap import PcapError, datagrams, read_pcap, tcp_streams

#: The relay's phase_end causes where the relay itself closed the ingress stream
#: (its write to the ingress failed, so it closed the socket).
RELAY_CLOSE_CAUSES = ("client_write_failed",)

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
    mid_stream: bool = False
    ended_cleanly: bool = True  # the last stream closed (FIN/RST); False means the capture was cut mid-stream
    # The first close of each connection that carried frames: (connection, time, by the server port).
    closes: list = field(default_factory=list)


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
    mid_stream = False
    last_stream = None
    closes = []
    for index, stream in enumerate(tcp_streams(datagrams(capture), port)):
        # A mid-stream join (the capture started while the ingress was already
        # connected, the documented window) is not a loss: it only means the
        # required window starts at the first captured frame (review R31).
        if stream.mid_stream_start:
            mid_stream = True
        if stream.gaps:
            had_gap = True
        stream_frames, problems = frames.split_frames(stream, index)
        if any("capture gap" in problem or "resync" in problem for problem in problems):
            had_gap = True
        collected.extend(stream_frames)
        last_stream = stream
        # Only a connection that carried frames is the ingress stream; a refused
        # second client carries none, so its close by the relay is no disconnect.
        if stream_frames and stream.first_close_ns is not None:
            closes.append((index, stream.first_close_ns, bool(stream.first_close_by_server)))
    # The capture ended cleanly when its last connection closed (a FIN or RST);
    # a capture cut mid-stream has neither. A truncated end means the guest
    # capture was stopped while the connection was open, so frames the stack
    # produced afterwards are beyond its coverage, not missing (review B1).
    ended_cleanly = bool(last_stream is not None and (last_stream.fin_ns is not None or last_stream.rst_ns is not None))
    collected.sort(key=lambda item: item.delivered_ns)
    return Capture(collected, had_gap, None, present=True, mid_stream=mid_stream, ended_cleanly=ended_cleanly,
                   closes=closes)


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


@dataclass(frozen=True)
class _Accept:
    accept_ns: int | None  # the completed handshake, else the SYN-ACK or the SYN; None when joined mid-stream
    first_ns: int | None   # the first packet of the connection in the capture


def _accept_by_connection(run: RunInputs, port: int) -> dict[int, _Accept]:
    """The loopback accept of the ingress in received.pcap, per connection index.

    The accept is the completed handshake (the client's ACK), else the SYN-ACK
    or the SYN where the ACK is not in the capture; a connection the capture
    joined mid-stream has none, only its first captured packet. The indices
    are those of ``_read_frames`` (the order of ``tcp_streams``), so a frame's
    ``connection`` finds its own.
    """
    path = run.run_dir / "received.pcap"
    if not path.exists():
        return {}
    try:
        capture = read_pcap(path)
    except PcapError:
        return {}
    return {index: _Accept(stream.established_ns or stream.synack_ns or stream.syn_ns, stream.first_ns)
            for index, stream in enumerate(tcp_streams(datagrams(capture), port))}


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


def _sd_from_capture(run: RunInputs):
    """The spoofed SD offer and the provider after it, from the host SD capture (VC-MW-016).

    None when there is no SD capture; "ERROR" when it cannot be read.
    """
    path = run.run_dir / "host-cvd-ebr.pcap"
    if not path.exists():
        return None
    try:
        entries = sd.sd_entries(read_pcap(path))
    except PcapError:
        return "ERROR"
    return sd.offer_and_provider(entries)


def _count_frame_assembler_clients(run: RunInputs, port: int) -> int:
    """How many distinct client connections to the frame assembler port are in produced.pcap (ASM-MW-029).

    The ss check runs only before and after the event, so a client that joins
    and leaves mid-event is invisible to it; the capture shows it (review R35).
    """
    path = run.run_dir / "produced.pcap"
    if not path.exists():
        return 0
    try:
        capture = read_pcap(path)
    except PcapError:
        return 0
    return len({stream.client for stream in tcp_streams(datagrams(capture), port)})


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

    # The AEBS event window, from the produced frames' timestamps (host clock).
    # A phase end or a DATA_LOSS matters only inside it (VC-MW-015, review R32).
    produced_ts = [facts.frame_timestamp_ns for _frame, facts in produced_facts if facts.frame_timestamp_ns is not None]
    event_lo, event_hi = (min(produced_ts), max(produced_ts)) if produced_ts else (None, None)

    def in_event(when: int | None) -> bool:
        return when is not None and event_lo is not None \
            and event_lo - PHASE_SLOP_NS <= when <= event_hi + PHASE_SLOP_NS

    def overlaps_event(phase) -> bool:
        if event_lo is None:
            return False
        end = phase.end_realtime_ns if phase.end_realtime_ns is not None else event_hi
        return phase.start_realtime_ns <= event_hi + PHASE_SLOP_NS and end >= event_lo - PHASE_SLOP_NS

    # Clock-independent, dominating failures in a phase that overlapped the AEBS event.
    if relay_present:
        for phase in all_phases:
            if phase.end_realtime_ns is None or not overlaps_event(phase):
                continue
            if phase.layer_caused_end:
                result.add("phase-end", FAIL, f"the layer ended a subscription phase (pid {phase.pid}, "
                           f"{phase.number}) by {phase.end_cause!r} while the ingress stayed connected; "
                           "a layer-caused phase end in the event is a delivery failure of the layer")
            elif phase.client_connected_at_end is False and phase.end_cause in RELAY_CLOSE_CAUSES:
                # The relay closed the ingress stream itself (VC-MW-015, main
                # 4bcfe628): a delivery failure of the layer, not inconclusive.
                result.add("ingress-disconnect", FAIL, f"the relay closed the ingress stream in phase (pid "
                           f"{phase.pid}, {phase.number}) by {phase.end_cause!r} in the event; an ingress "
                           "disconnect that the relay causes is a delivery failure of the layer")
            elif phase.client_connected_at_end is False:
                result.add("delivery_evidence", INCONCLUSIVE, f"the ingress disconnected in phase (pid {phase.pid}, "
                           f"{phase.number}) in the event; the run cannot show source order")
        # The relay's exit: it ends the process on a lost gateway client
        # (exit code 4), which closes the ingress stream (VC-MW-015).
        for event in events:
            if event.get("event") != "gateway_client_lost":
                continue
            when = event.get("realtime_ns")
            if in_event(when if isinstance(when, int) else event.get("logcat_ns")):
                result.add("relay-exit", FAIL, f"the relay lost its gateway client in the event and exits (exit code "
                           f"{event.get('exit_code', 4)}); the ingress disconnect that its exit causes is a delivery "
                           "failure of the layer")
        for event in relay_log.data_loss_events(events):
            when = event.get("realtime_ns")
            if in_event(when if isinstance(when, int) else event.get("logcat_ns")):
                result.add("data-loss", FAIL, f"the relay read DATA_LOSS in subscription {event.get('subscription')} "
                           "in the event; a DATA_LOSS in the event is a sequence gap")

    # A close of the ingress stream from the relay's port in the loopback
    # capture is a disconnect that the relay causes (VC-MW-015), whatever its
    # log says: it also covers a relay that died without a log line.
    for connection, close_ns, by_server in received.closes:
        if by_server and in_event(close_ns):
            result.add("ingress-disconnect", FAIL, f"the relay closed the ingress stream (connection {connection}) "
                       f"from port {run.received_port} in the loopback capture in the event; an ingress disconnect "
                       "that the relay causes is a delivery failure of the layer")

    # Order: received sequences must strictly increase (clock-independent).
    received_seq = [facts.sequence for _frame, facts in received_facts if facts.sequence is not None]
    if any(b <= a for a, b in zip(received_seq, received_seq[1:])):
        result.add("order", FAIL, "the received frames are not in strictly increasing sequence order")

    # ASM-MW-029 and ASM-MW-030 gate the completeness evidence: a second client
    # of the frame assembler, an ingress disconnect, a bad clock or a capture
    # gap all make a missing frame missing evidence, not a delivery failure
    # (review R6/R7). They share the code the completeness and gap FAILs rest on.
    second_client = _second_client_held_4721(run)
    produced_clients = _count_frame_assembler_clients(run, run.produced_port)
    if second_client is True or produced_clients > 1:
        # A second client breaks ASM-MW-029, so the run never passes; the
        # execution slice records a bench discrepancy before any fail counts
        # against the layer (VC-MW-015, main 4bcfe628).
        result.measurements["bench_discrepancy"] = (
            "a second client of the frame assembler port 4721 (ASM-MW-029 broken); record a bench discrepancy "
            "before any fail counts against the layer")
    if second_client is True:
        result.add("delivery_evidence", INCONCLUSIVE, "another client held the frame assembler stream (ASM-MW-029), "
                   "so a missing frame may be that client's, not a delivery failure")
    elif produced_clients > 1:
        result.add("delivery_evidence", INCONCLUSIVE, f"{produced_clients} clients of the frame assembler are visible "
                   "in produced.pcap (ASM-MW-029); the ss check missed one, so a missing frame may be another "
                   "client's, not a delivery failure")
    elif second_client is None:
        result.add("delivery_evidence", INCONCLUSIVE, "no frame-assembler client check (ASM-MW-029) in the run")

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

    # Required produced frames: those produced unambiguously inside a phase, by
    # the 20 ms clock margin from each edge. A frame within 20 ms of an edge is
    # a band frame: the clocks cannot place it, so it is a measurement, not a
    # required frame (review R14).
    def in_a_phase(host_ts: int) -> bool:
        for phase in all_phases:
            start = phase.start_realtime_ns + PHASE_SLOP_NS
            end = (phase.end_realtime_ns - PHASE_SLOP_NS) if phase.end_realtime_ns is not None else host_ts
            if start <= host_ts <= end:
                return True
        return False

    def in_a_band(host_ts: int) -> bool:
        for phase in all_phases:
            end = phase.end_realtime_ns if phase.end_realtime_ns is not None else host_ts
            if phase.start_realtime_ns - PHASE_SLOP_NS <= host_ts <= phase.start_realtime_ns + PHASE_SLOP_NS \
                    or (phase.end_realtime_ns is not None and end - PHASE_SLOP_NS <= host_ts <= end + PHASE_SLOP_NS):
                return True
        return False

    # When the guest capture joined mid-stream, frames produced before its
    # first complete frame were delivered but not captured, so they are not
    # required (VC-MW-015, review R31).
    received_ts = [facts.frame_timestamp_ns for _frame, facts in received_facts
                   if facts.frame_timestamp_ns is not None]
    capture_floor = (min(received_ts) - PHASE_SLOP_NS) if (received.mid_stream and received_ts) else None
    # A guest capture that was cut mid-stream (no clean close) stops before the
    # stack does: a frame produced after the last captured packet was delivered
    # but not captured, so it is beyond the capture's coverage and not required.
    # The ceiling is the last received packet time less the inter-arrival bound
    # and the 20 ms clock band, mirroring the mid-stream floor (review B1/R31).
    # A capture that closed cleanly is not trimmed: a stack that keeps producing
    # past a cleanly ended stream is a genuine stop, judged below.
    capture_ceiling = (max(frame.delivered_ns for frame in received.frames) - MAX_GAP_NS - PHASE_SLOP_NS) \
        if (received.frames and not received.ended_cleanly) else None

    received_set = set(received_seq)
    required = [facts.sequence for _frame, facts in produced_facts
                if facts.sequence is not None and (not all_phases or in_a_phase(facts.frame_timestamp_ns or 0))
                and (capture_floor is None or (facts.frame_timestamp_ns or 0) >= capture_floor)
                and (capture_ceiling is None or (facts.frame_timestamp_ns or 0) <= capture_ceiling)]
    result.measurements["band_frames"] = sum(1 for _frame, facts in produced_facts
                                             if all_phases and facts.frame_timestamp_ns is not None
                                             and in_a_band(facts.frame_timestamp_ns) and not in_a_phase(facts.frame_timestamp_ns))
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

    # The SD offer: from the host SD capture (the authoritative source,
    # VC-MW-016), else the GAP-MW-012 residual. A written sd_offer.json is data
    # only and gives no pass (review R49); an empty record is missing evidence
    # too (review R34).
    offer_time_ns: int | None = None
    offer = _sd_from_capture(run)
    residual = _load_json(run, "residual.json")
    sd_offer = _load_json(run, "sd_offer.json")
    if offer == "ERROR" or sd_offer == "ERROR" or residual == "ERROR":
        result.add("sd-offer", ERROR, "an SD record is not valid JSON")
        return result
    if offer is not None:
        capture_offer_time = offer.get("offer_time_ns")
        offer_src_port = offer.get("offer_src_port")
        processed = _load_json(run, "sd_core_processed.json")
        if processed == "ERROR":
            result.add("sd-offer", ERROR, "sd_core_processed.json is not valid JSON")
            return result
        providers = offer.get("providers_after") or []
        redirected = [p for p in providers if p != "192.168.98.1"]
        # The stack's own record (send_sd_offer.sh, review R43): processed only
        # with status "processed" and the matched line; else ignored or unknown.
        processed_ok = isinstance(processed, dict) and processed.get("processed") is True \
            and processed.get("status") == "processed" \
            and isinstance(processed.get("matched_line"), str) and processed["matched_line"].strip() != ""
        status = processed.get("status") if isinstance(processed, dict) else None
        if capture_offer_time is None:
            result.add("sd-offer", INCONCLUSIVE, "no spoofed SD offer from a non-host sender in the SD capture")
        elif redirected:
            # The core subscribing to another provider after the spoofed offer
            # shows by itself that the stack took the offer; no log line is
            # needed, and none may hide this failure.
            offer_time_ns = capture_offer_time
            result.add("sd-redirect", FAIL, f"after the SD offer from the IVI VM the stack subscribed to "
                       f"{redirected}, not 192.168.98.1")
        elif offer_src_port != sd.SD_PORT:
            # A SOME/IP stack ignores an SD message whose source port is not the
            # SD port, so an offer from an ephemeral port is not a valid
            # stimulus and shows nothing (review R43).
            result.add("sd-offer", INCONCLUSIVE, f"the spoofed SD offer came from source port {offer_src_port}, not "
                       f"{sd.SD_PORT}; a SOME/IP stack ignores an SD message from another port, so it is not a valid "
                       "stimulus")
        elif not processed_ok:
            # The offer is from the SD port, but nothing shows the core stack
            # read it; the no-redirect property is not demonstrated (review R43).
            if status == "ignored":
                why = (f"the core stack's log shows it ignored the offer before service discovery "
                       f"({processed.get('matched_line')!r})")
            elif status == "unknown":
                why = "the core stack's log around the offer has no matching line (status unknown)"
            else:
                why = "no record (sd_core_processed.json with the matched line) shows the core stack processed it"
            result.add("sd-offer", INCONCLUSIVE, f"the SD capture holds a spoofed offer from the SD source port, but "
                       f"{why}; the no-redirect property is not shown")
        else:
            offer_time_ns = capture_offer_time
            result.measurements["sd_core_processed"] = {"result": processed.get("result"),
                                                        "matched_line": processed.get("matched_line")}
            if not providers:
                result.add("sd-offer", INCONCLUSIVE, "an SD offer was seen and processed but no later subscription of "
                           "the stack, so the provider after the offer is unknown")
    elif isinstance(sd_offer, dict):
        # A written sd_offer.json is data only (review R49): the case takes the
        # provider after the offer from the SD capture, and neither R43
        # condition (an offer from the SD source port, a stack-processed record)
        # can be shown by a written record. Alone it gives no pass.
        result.measurements["sd_offer_record"] = {key: sd_offer.get(key)
                                                  for key in ("provider_after_offer", "offer_time_ns")}
        result.add("sd-offer", INCONCLUSIVE, "sd_offer.json is data only: the provider after the offer must come from "
                   "the SD capture (host-cvd-ebr.pcap) with the core stack's record (sd_core_processed.json); a "
                   "written record alone shows nothing")
    elif isinstance(residual, dict) and residual.get("gap") == "GAP-MW-012":
        result.measurements["residual"] = "GAP-MW-012 recorded (no pin or filter)"
    else:
        result.add("sd-offer", INCONCLUSIVE, "no SD capture with a spoofed offer and no GAP-MW-012 residual record")
    offer_recorded = offer_time_ns is not None

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

    # Frames must keep arriving after the offer (no silent redirect or stop).
    if offer_recorded and received.frames:
        received_facts = [(frame, _facts(frame)) for frame in received.frames]
        last_received_ts = max((facts.frame_timestamp_ns for _frame, facts in received_facts
                                if facts and facts.frame_timestamp_ns is not None), default=None)
        received_seqs = {facts.sequence for _frame, facts in received_facts if facts and facts.sequence is not None}
        # A guest capture cut mid-stream (no clean close) does not cover frames
        # the stack produced after its last packet, so those are not a stop
        # after the offer (review B1). A cleanly closed stream has no ceiling, so
        # frames produced past it are a genuine stop.
        capture_ceiling = (max(frame.delivered_ns for frame in received.frames) - MAX_GAP_NS - PHASE_SLOP_NS) \
            if not received.ended_cleanly else None
        # The stream stopped: the stack produced frames after the last received
        # frame (so after the offer, which fell in the event) that never arrived,
        # within the capture's coverage.
        if last_received_ts is not None and not (received.had_gap or produced.had_gap):
            stopped = [facts.sequence for frame in produced.frames
                       if (facts := _facts(frame)) and facts.sequence is not None
                       and facts.frame_timestamp_ns is not None and facts.frame_timestamp_ns > last_received_ts
                       and (capture_ceiling is None or facts.frame_timestamp_ns <= capture_ceiling)
                       and facts.sequence not in received_seqs]
            if stopped:
                result.add("sd-stop", FAIL, f"after the SD offer the received frames stopped: {len(stopped)} frames "
                           f"the stack produced later never arrived (first {sorted(stopped)[:5]})")
        # A long inter-arrival gap: a definite stop when the offer time places it
        # after the offer; without an offer time, it is missing evidence (R34).
        gaps = [(received.frames[i - 1].delivered_ns, received.frames[i].delivered_ns - received.frames[i - 1].delivered_ns)
                for i in range(1, len(received.frames))]
        long_gaps = [start for start, gap in gaps if gap >= MAX_GAP_NS]
        if long_gaps and offer_time_ns is not None:
            if any(start >= offer_time_ns - PHASE_SLOP_NS for start in long_gaps):
                result.add("sd-stop", FAIL, "the received frames stop for the inter-arrival bound or longer after the "
                           "SD offer")
        elif long_gaps:
            result.add("sd-gap", INCONCLUSIVE, "the received frames have an inter-arrival gap of 500 ms or longer, "
                       "but the record has no offer time, so whether it follows the offer is unknown")

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
    result.measurements["isolated_probes"] = verdict.isolated_probes
    result.measurements["asm_mw_031_holds"] = verdict.asm_mw_031_holds
    result.measurements["required_dds_ports"] = verdict.required_dds_ports
    result.measurements["dds_range"] = verdict.dds_range
    result.measurements["probed_pairs"] = sum(len(pairs) for pairs in verdict.probed_pairs.values())

    # A reachable DDS port of a layer element fails, whatever the control or ASM-MW-031 show.
    for reached in verdict.reached_layer:
        result.add("layer-reachable", FAIL, f"a guest domain reached layer DDS port {reached.get('port')} "
                   f"from {reached.get('guest')} over {reached.get('interface')}")
    # A reachable DDS port of a process outside the layer: fail only while ASM-MW-031 holds.
    for reached in verdict.reached_other:
        if verdict.asm_mw_031_holds:
            result.add("other-reachable", FAIL, f"a guest reached host DDS port {reached.get('port')} of a process "
                       "outside the layer, and ASM-MW-031 holds")
        else:
            result.add("other-reachable", INCONCLUSIVE, f"a guest reached host DDS port {reached.get('port')} of a "
                       "process outside the layer, but ASM-MW-031 is not shown")
    # Port 4721 is an ASM-MW-029 finding, not a REQ-MW-016 failure.
    for reached in verdict.reached_frame_assembler:
        result.measurements.setdefault("asm_mw_029_findings", []).append(
            f"port 4721 reachable from {reached.get('guest')} over {reached.get('interface')}")

    if not verdict.control_ok:
        result.add("control", INCONCLUSIVE, f"the positive control did not reach its host socket ({verdict.control_detail}); "
                   "an unreachable probe shows nothing")
    for gap in verdict.coverage_gaps:
        result.add("coverage", INCONCLUSIVE, gap)
    if not verdict.reached_layer and not verdict.reached_other and verdict.asm_mw_031_holds is not True:
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

#: The relay notices a clock step at its next event, at most this long after it.
RELAY_STEP_DETECTION_NS = 100_000_000
#: How far before the judged start the bound looks for the frames on Data Tunnel.
DT_BOUND_LOOKBACK_NS = 3_000_000_000


def _dt_start(tunnel, first_frame, judged_start_ns: int, produced: "Capture") -> tuple[str, int | None, str]:
    """(kind, start, detail) of the Data Tunnel subscription that carried a phase's first frame.

    kind "stream_open": the capture holds the opening HEADERS of the HTTP/2
    stream that carried the frame; that time is the start. kind
    "before_judged_start": the capture joined the connection after it opened
    (so the open time is not in it), but the produced frames flowed on the same
    carrier with no gap of 500 ms or more from before the judged start to the
    phase's first frame, so the subscription started before the judged start.
    The caller must also judge every later delivery and reject deliveries
    outside a relay phase before that start. kind "unknown":
    neither, so the second check cannot run.
    """
    located = tunnel.locate(first_frame.payload)
    if not located:
        return "unknown", None, "the Data Tunnel capture does not carry the phase's first frame"
    carrier = located[0]
    opened = tunnel.stream_open_ns(carrier)
    if opened is not None:
        return "stream_open", opened, "the opening HEADERS of the stream that carried the phase's first frame"
    first_facts = _facts(first_frame)
    last_ts = first_facts.frame_timestamp_ns if first_facts is not None else None
    since = judged_start_ns - DT_BOUND_LOOKBACK_NS
    window = [frame.payload for frame in produced.frames
              if (facts := _facts(frame)) is not None and facts.frame_timestamp_ns is not None and last_ts is not None
              and since <= facts.frame_timestamp_ns <= last_ts]
    times = [when for when in tunnel.arrivals(carrier, window + [first_frame.payload], since_ns=since - MAX_GAP_NS)
             if when <= carrier.arrival_ns]
    gaps = [b - a for a, b in zip(times, times[1:])]
    if times and times[0] < judged_start_ns and times[-1] == carrier.arrival_ns and all(g < MAX_GAP_NS for g in gaps):
        return "before_judged_start", None, (f"the capture joined the connection after its start; the frames flowed on "
                                             f"it from {(judged_start_ns - times[0]) / 1e6:.0f} ms before the judged "
                                             "start to the phase's first frame with no gap of 500 ms or more")
    return "unknown", None, ("the capture does not hold the opening of the stream that carried the phase's first "
                             "frame, and does not show the frames flowing on it through the judged start")



def _clock_step_between(events: list[dict], all_phases: list, start_ns: int, end_ns: int) -> bool:
    """Whether the relay logged a clock step between the two offset measurements (guest clock).

    The relay stamps a step with the realtime after it. A forward step after the
    start measurement is stamped later than it; a backward step after it can be
    stamped up to its own size earlier. So the window widens by the step size
    on the low side for a backward step (or one of unknown size, without
    limit), and by the relay's detection delay on both sides. A step the
    times cannot place counts as between: it disables the wide limit, which
    only removes a fail. A phase whose phase_end counts a clock step and that
    overlaps the window counts too.
    """
    for step in relay_log.clock_steps(events):
        when = step.get("realtime_ns")
        when = when if isinstance(when, int) else step.get("logcat_ns")
        if not isinstance(when, int):
            return True
        size = step.get("step_ns")
        if isinstance(size, bool) or not isinstance(size, int):
            low = None
        elif size < 0:
            low = start_ns - (-size) - RELAY_STEP_DETECTION_NS
        else:
            low = start_ns - RELAY_STEP_DETECTION_NS
        if (low is None or when >= low) and when <= end_ns + RELAY_STEP_DETECTION_NS:
            return True
    for phase in all_phases:
        if (phase.clock_steps_in_phase or 0) > 0:
            phase_end = phase.end_realtime_ns if phase.end_realtime_ns is not None else end_ns
            if phase.start_realtime_ns <= end_ns and phase_end >= start_ns:
                return True
    return False


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
    if received.had_gap:
        # A frame lost in the gap may be one produced before the new
        # subscription, so the captured frames cannot show a clean phase; a
        # captured violation still fails.
        result.add("capture-gap", INCONCLUSIVE, "received.pcap has a capture gap, so a frame produced before the "
                   "new subscription may have reached the HMI unseen")

    # The judged phases. In the IVI-VM-down condition, the clock is set after
    # the reboot and the ingress is started again; the case judges the phase
    # that starts then, and records the first phase after the reboot as data,
    # outside the judged scope (VC-MW-020, review R18/R30).
    judged = list(all_phases)
    if run.condition == "ivi_vm_down" and len(all_phases) >= 2:
        # The out-of-scope phase is the first the relay logged, by log order and
        # (pid, phase), not the earliest realtime: a clock step in the first
        # phase can move realtime back past the next phase start (review R46).
        first_key = relay_log.first_phase_key(events)
        first = next((phase for phase in all_phases if phase.key == first_key), None) if first_key else None
        if first is None:  # no readable phase_start order: fall back to the earliest realtime
            first = min(all_phases, key=lambda phase: phase.start_realtime_ns)
        judged = [phase for phase in all_phases if phase.key != first.key]
        result.measurements["first_phase_recorded_as_data"] = {"pid": first.pid, "phase": first.number}
    judged_keys = {phase.key for phase in judged}

    # The judged start of a phase is the later of two times: the relay's phase
    # start and the loopback accept of the ingress (received.pcap) on the
    # connection that carries the frame (VC-MW-020, decision on review R33). A later
    # start only makes the check stricter: a relay that claims a start before
    # the ingress connected is judged against the accept; in the normal order
    # (accept, then the relay's log line) the later time is the relay's own.
    # Both times and their difference are recorded. The VLAN 2 Data Tunnel
    # capture supplies the independent second check below.
    accepts = _accept_by_connection(run, run.received_port)
    phase_starts: dict[tuple, dict] = {}

    def judged_start(phase, connection: int) -> tuple[int, bool]:
        """The judged start, and whether it is known (else the relay's start is only a lower bound)."""
        relay = phase.start_realtime_ns
        entry = accepts.get(connection)
        accept = entry.accept_ns if entry is not None else None
        if accept is not None:
            start, known = max(relay, accept), True
        elif entry is not None and entry.first_ns is not None and entry.first_ns <= relay:
            # Joined mid-stream, but the capture saw this connection before the
            # relay's start: the accept is earlier still, so the later time is the relay's.
            start, known = relay, True
        else:
            # Joined mid-stream after the relay's start: the accept is not in the
            # capture, and the capture may have missed the start of the phase.
            start, known = relay, False
        phase_starts.setdefault((phase.key, connection), {
            "pid": phase.pid, "phase": phase.number, "connection": connection,
            "relay_start_ns": relay, "accept_ns": accept,
            "accept_minus_relay_ns": None if accept is None else accept - relay,
            "judged_start_ns": start, "judged_start_known": known})
        return start, known

    # ASM-MW-030: start and end offsets hold; a clock step in a JUDGED phase
    # voids only that phase (review R30).
    measurements = _clock(run)
    both = "start" in measurements and "end" in measurements
    clock_ok = both and measurements["start"].holds() and measurements["end"].holds()
    if "start" in measurements:
        result.measurements["offset_start_ns"] = measurements["start"].offset_ns
    if "end" in measurements:
        result.measurements["offset_end_ns"] = measurements["end"].offset_ns
    if not clock_ok:
        result.add("asm_mw_030", INCONCLUSIVE, "ASM-MW-030 does not hold in the run (offset plus uncertainty not "
                   "below 20 ms at start and end)")
    steps = relay_log.clock_steps(events)

    def step_in(phase) -> bool:
        if (phase.clock_steps_in_phase or 0) > 0:
            return True
        end = phase.end_realtime_ns
        for step in steps:
            when = step.get("realtime_ns")
            if isinstance(when, int) and phase.start_realtime_ns <= when and (end is None or when <= end):
                return True
        return False

    if any(step_in(phase) for phase in judged):
        result.add("asm_mw_030", INCONCLUSIVE, "a clock step fell inside a judged phase; that phase is void")

    # The clock-independent threshold: a frame earlier than the phase start by
    # more than 20 ms plus the larger absolute offset plus its uncertainty is a
    # violation whatever ASM-MW-030 shows (review R19). It applies only if the
    # relay logged no clock step between the two offset measurements (VC-MW-020,
    # main 4bcfe628): a step there makes the measured offsets no bound.
    ci_threshold = None
    wide_limit_applied = False
    if both and not _clock_step_between(events, all_phases, measurements["start"].measured_at_ns,
                                        measurements["end"].measured_at_ns):
        larger = max((measurements["start"], measurements["end"]), key=lambda m: abs(m.offset_ns))
        ci_threshold = PHASE_SLOP_NS + abs(larger.offset_ns) + larger.uncertainty_ns
        wide_limit_applied = True
    result.measurements["wide_limit_applied"] = wide_limit_applied

    # Judge each frame against the phase it arrived in, raw (no offset correction, VC-MW-020 and the rule).
    judged_frames = 0
    seen_phases: set = set()
    phase_frames: dict = {}
    violations = 0
    clock_independent = 0
    unknown_start = 0
    for frame in received.frames:
        facts = _facts(frame)
        if facts is None:
            result.add("frame", ERROR, "a received frame did not decode")
            return result
        phase = relay_log.phase_at(all_phases, frame.delivered_ns)
        if phase is None or phase.key not in judged_keys:
            continue  # outside any phase, or in the unjudged first phase: not judged here
        seen_phases.add(phase.key)
        phase_frames.setdefault(phase.key, []).append(frame)
        if facts.frame_timestamp_ns is None:
            result.add("timestamp", INCONCLUSIVE, f"a frame in phase {phase.key} has no frame timestamp")
            continue
        judged_frames += 1
        start, known = judged_start(phase, frame.connection)
        # Raw comparison: production time (host clock) vs the judged start less
        # the 20 ms margin. Where the start is only a lower bound, a frame
        # earlier than it is still a violation; a later frame is not shown clean.
        violation = facts.frame_timestamp_ns < start - PHASE_SLOP_NS
        if violation:
            violations += 1
        elif not known:
            unknown_start += 1
        # Clock-independent: earlier than the judged start by more than the
        # offset plus its uncertainty plus 20 ms fails whatever the clock shows (R19).
        if ci_threshold is not None and facts.frame_timestamp_ns < start - ci_threshold:
            clock_independent += 1
    result.measurements["judged_frames"] = judged_frames
    result.measurements["judged_phases"] = len(seen_phases)
    result.measurements["phase_starts"] = list(phase_starts.values())

    # The second check (VC-MW-020, main 4bcfe628): the same check with the time
    # of the subscription in the Data Tunnel capture as the start. If it fails
    # and the first passes, the run is inconclusive. Without a readable time the
    # second check cannot run, so the run gives no pass (coordinator decision).
    dt_starts, dt_violations = [], 0
    # Keep the explicit post-reboot data-only phase outside both checks. No
    # other phase boundary may remove a received frame from the second check.
    dt_frames = [frame for frame in received.frames
                 if (phase := relay_log.phase_at(all_phases, frame.delivered_ns)) is None or phase.key in judged_keys]
    dt_path = run.run_dir / "data-tunnel-vlan2.pcap"
    tunnel = None
    if not dt_path.exists():
        result.add("dt-start", INCONCLUSIVE, "no Data Tunnel capture (data-tunnel-vlan2.pcap), so the second check "
                   "with the Data Tunnel subscription time cannot run; the run gives no pass")
    else:
        try:
            tunnel = dt.read(read_pcap(dt_path))
        except PcapError as error:
            result.add("dt-start", ERROR, f"data-tunnel-vlan2.pcap is unreadable: {error}")
    if tunnel is not None:
        produced = _read_frames(run, "produced.pcap", run.produced_port)
        for key in sorted(seen_phases):
            in_phase = [frame for frame in phase_frames[key] if _facts(frame) is not None]
            if not in_phase:
                continue
            first = min(in_phase, key=lambda frame: frame.delivered_ns)
            phase = next(item for item in all_phases if item.key == key)
            start1, _known = judged_start(phase, first.connection)
            kind, start2, detail = _dt_start(tunnel, first, start1, produced)
            record = {"pid": phase.pid, "phase": phase.number, "judged_start_ns": start1, "dt_start_kind": kind,
                      "dt_start_ns": start2, "dt_minus_judged_ns": None if start2 is None else start2 - start1,
                      "detail": detail}
            dt_starts.append(record)
            # The bound's guard starts at the previous relay phase end, or the
            # capture start when there is no previous end.
            previous_end = max((other.end_realtime_ns for other in all_phases
                                if other.key != phase.key and other.end_realtime_ns is not None
                                and other.end_realtime_ns <= phase.start_realtime_ns), default=None)
            if kind == "unknown":
                result.add("dt-start", INCONCLUSIVE, f"phase (pid {phase.pid}, {phase.number}): {detail}; the second "
                           "check cannot run, so the run gives no pass")
            elif kind == "stream_open":
                # Every received frame delivered at or after the second start, not
                # only those inside the relay's phase: a frame delivered between the
                # relay's phases after the subscription is judged too (R48).
                late = [frame for frame in dt_frames
                        if frame.delivered_ns >= start2
                        and (facts := _facts(frame)) is not None and facts.frame_timestamp_ns is not None
                        and facts.frame_timestamp_ns < start2 - PHASE_SLOP_NS]
                dt_violations += len(late)
            else:
                # The bound shows the subscription started before the judged start,
                # not when. A frame delivered outside every relay phase between the
                # previous phase end and the judged start might follow it, and the
                # bound cannot judge that frame (R48).
                stray = [frame for frame in received.frames
                         if (previous_end is None or frame.delivered_ns >= previous_end)
                         and frame.delivered_ns < start1 and relay_log.phase_at(all_phases, frame.delivered_ns) is None]
                record["frames_outside_a_phase_before_the_judged_start"] = len(stray)
                if stray:
                    result.add("dt-bound", INCONCLUSIVE, f"phase (pid {phase.pid}, {phase.number}): {len(stray)} frames "
                               "were delivered outside the relay's phases before the judged start; the Data Tunnel "
                               "bound cannot judge them, so the run shows nothing")
                # The stricter judged start can prove the second check only for
                # frames within its margin. Apply it after the start without
                # trusting a relay phase end to hide later deliveries.
                unproven = [frame for frame in dt_frames if frame.delivered_ns >= start1
                            and (facts := _facts(frame)) is not None and facts.frame_timestamp_ns is not None
                            and facts.frame_timestamp_ns < start1 - PHASE_SLOP_NS]
                if unproven:
                    result.add("dt-bound", INCONCLUSIVE, f"phase (pid {phase.pid}, {phase.number}): {len(unproven)} frames "
                               "delivered at or after the judged start were produced before its margin; the Data "
                               "Tunnel bound alone cannot judge them")
            if kind != "unknown":
                check_start = start2 if kind == "stream_open" else start1
                if any(frame.delivered_ns >= check_start
                       and ((facts := _facts(frame)) is None or facts.frame_timestamp_ns is None)
                       for frame in dt_frames):
                    result.add("dt-timestamp", INCONCLUSIVE, "a frame delivered after the second check's start has "
                               "no frame timestamp, so the Data Tunnel check gives no pass")
        if dt_violations:
            result.add("dt-check", INCONCLUSIVE, f"{dt_violations} frames were produced more than 20 ms before the "
                       "subscription time in the Data Tunnel capture; with that start the check fails, so the run "
                       "shows nothing (the relay's record and the Data Tunnel capture disagree)")
    result.measurements["dt_starts"] = dt_starts
    if judged_frames == 0:
        result.add("frames", INCONCLUSIVE, "no frame with a timestamp arrived in a judged phase")
    if unknown_start:
        result.add("phase-start", INCONCLUSIVE, f"{unknown_start} frames are on a connection that received.pcap "
                   "joined after the relay's phase start, with no loopback accept; their judged start is not known")
    if clock_independent:
        result.add("discard", FAIL, f"{clock_independent} frames were produced earlier than the new subscription by "
                   "more than the clock offset plus its uncertainty plus 20 ms; a clock-independent violation")
    elif violations:
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
