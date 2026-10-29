"""Pure evaluators of the running verification cases, from raw run artifacts.

Each evaluator reads a run directory and returns a CaseResult whose outcome is
of the middleware evidence vocabulary (outcome.py). It checks only the success
criteria of the requirement its case verifies, and it adds no criterion. It
reads the independent captures, not the relay's or the ingress's own logs; it
reads the relay log only as supporting data. No evaluator opens a socket or
runs on the bench; it is replayed off the VM.

The run directory holds, by convention:

- produced.pcap: host capture of the frame assembler stream (lo:4721);
- received.pcap: guest capture of the relay stream (IVI lo:4731);
- relay-logcat.txt: the IVI logcat with the relay's events;
- clock-start.pcap, clock-end.pcap: the NTP exchanges of ASM-MW-030;
- settings.json: the run settings (ports, the relay's logcat tag, the SNTP
  server, the stage the event must reach);
- for VC-MW-017 only, the isolation-probe artifacts of probe.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import clock, frames, probe
from .outcome import BLOCKED, FAIL, INCONCLUSIVE, PASS, CaseResult
from .pcap import PcapError, read_pcap, tcp_streams
from .relay_log import phases, phase_at, relay_events

DEFAULT_PRODUCED_PORT = 4721
DEFAULT_RECEIVED_PORT = 4731
#: The inter-arrival bound of REQ-MW-014.
MAX_GAP_NS = 500_000_000


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
    def relay_tag(self) -> str:
        # The relay's liblog tag belongs to the relay lane; a run names it in its
        # settings.json. The neutral default keeps that lane's service name out
        # of this bench's committed code (the model guard scans for it).
        return str(self.settings.get("relay_logcat_tag", "frame_relay"))


def load_run(run_dir: str | Path) -> RunInputs:
    run_dir = Path(run_dir)
    settings_path = run_dir / "settings.json"
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}
    return RunInputs(run_dir, settings)


def _frames_of(run: RunInputs, name: str, port: int):
    """The frames of one capture, as one list across every connection, in delivery order."""
    path = run.run_dir / name
    if not path.exists():
        return None, [f"{name} is missing"]
    try:
        capture = read_pcap(path)
    except PcapError as error:
        return None, [str(error)]
    collected = []
    problems: list[str] = []
    if capture.truncated:
        problems.append(f"{name}: the capture was cut off mid-record (the capture stopped mid-write)")
    for index, stream in enumerate(tcp_streams(_datagrams(capture), port)):
        stream_frames, stream_problems = frames.split_frames(stream, index)
        collected.extend(stream_frames)
        problems.extend(f"{name} connection {index}: {problem}" for problem in stream_problems)
    collected.sort(key=lambda item: item.delivered_ns)
    return collected, problems


def _datagrams(capture):
    from .pcap import datagrams
    return datagrams(capture)


def _relay_phases(run: RunInputs):
    path = run.run_dir / "relay-logcat.txt"
    if not path.exists():
        return [], ["relay-logcat.txt is missing"]
    events = relay_events(path.read_text(errors="replace").splitlines(), run.relay_tag)
    return phases(events)


def _clock_measurements(run: RunInputs):
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


def evaluate_source_order(run: RunInputs) -> CaseResult:
    """VC-MW-015, REQ-MW-014: every produced frame reaches the HMI, in order, gaps below 500 ms."""
    result = CaseResult("VC-MW-015", run.run_dir.name)
    produced, produced_problems = _frames_of(run, "produced.pcap", run.produced_port)
    received, received_problems = _frames_of(run, "received.pcap", run.received_port)
    for problem in produced_problems + received_problems:
        result.add("capture", INCONCLUSIVE, problem)
    if produced is None or received is None:
        return result
    produced_facts = [frames.frame_facts(frame.payload) for frame in produced]
    stages = {frames.stage(facts) for facts in produced_facts}
    missing = [stage for stage in frames.STAGES if stage not in stages]
    if missing:
        result.add("event", INCONCLUSIVE, f"the produced frames do not show every stage; missing {missing}")
        return result
    received_facts = [frames.frame_facts(frame.payload) for frame in received]
    produced_seq = [facts.sequence for facts in produced_facts]
    received_seq = [facts.sequence for facts in received_facts]
    result.measurements["produced_frames"] = len(produced)
    result.measurements["received_frames"] = len(received)
    missing_seq = [seq for seq in produced_seq if seq not in set(received_seq)]
    if missing_seq:
        result.add("completeness", FAIL, f"{len(missing_seq)} produced frames never reached the HMI; "
                   f"first missing sequences {missing_seq[:5]}")
    ordered = received_seq == sorted(received_seq)
    if not ordered:
        result.add("order", FAIL, "the received frames are out of order against their own sequence numbers")
    gaps = [(received[i].delivered_ns - received[i - 1].delivered_ns) for i in range(1, len(received))]
    over = [gap for gap in gaps if gap > MAX_GAP_NS]
    if gaps:
        result.measurements["max_gap_ns"] = max(gaps)
    if over:
        result.add("gap", FAIL, f"{len(over)} inter-arrival gaps exceed 500 ms; the largest is {max(gaps)} ns")
    # The relay log corroborates: a phase end during the event is a delivery
    # failure of the layer. The independent captures stay authoritative, so a
    # missing relay log is a note, not a missing-evidence verdict; its absence
    # would still show as missing or late frames above.
    if (run.run_dir / "relay-logcat.txt").exists():
        all_phases, phase_problems = _relay_phases(run)
        result.measurements["relay_phases"] = len(all_phases)
        if phase_problems:
            result.measurements["relay_log_problems"] = phase_problems
        if received:
            window = (received[0].delivered_ns, received[-1].delivered_ns)
            ended = [phase for phase in all_phases if phase.end_realtime_ns is not None
                     and window[0] <= phase.end_realtime_ns <= window[1]]
            if ended:
                result.add("phase", FAIL, f"the relay ended {len(ended)} subscription phase(s) during the event; "
                           "a phase end while the ingress stays connected is a delivery failure of the layer")
    else:
        result.measurements["relay_log"] = "absent"
    if not any(finding.outcome in (FAIL, BLOCKED) for finding in result.findings):
        result.add("source-order", PASS, f"{len(produced)} produced frames all reached the HMI, in order, "
                   f"with the largest gap {max(gaps) if gaps else 0} ns")
    return result


def evaluate_provenance(run: RunInputs) -> CaseResult:
    """VC-MW-016, REQ-MW-015: each received frame equals its produced frame, field by field with the source kind."""
    result = CaseResult("VC-MW-016", run.run_dir.name)
    produced, produced_problems = _frames_of(run, "produced.pcap", run.produced_port)
    received, received_problems = _frames_of(run, "received.pcap", run.received_port)
    for problem in produced_problems + received_problems:
        result.add("capture", INCONCLUSIVE, problem)
    if produced is None or received is None:
        return result
    produced_by_seq = {}
    for frame in produced:
        facts = frames.frame_facts(frame.payload)
        if facts.sequence is not None:
            produced_by_seq[facts.sequence] = frame.payload
    stages = {frames.stage(frames.frame_facts(frame.payload)) for frame in produced}
    if any(stage not in stages for stage in frames.STAGES):
        result.add("event", INCONCLUSIVE, "the produced frames do not show every stage of the event")
        return result
    compared = 0
    for frame in received:
        facts = frames.frame_facts(frame.payload)
        seq = facts.sequence
        produced_payload = produced_by_seq.get(seq)
        if produced_payload is None:
            result.add("pairing", INCONCLUSIVE, f"received frame sequence {seq} has no produced frame to compare")
            continue
        compared += 1
        if frame.payload != produced_payload:
            differences = frames.diff_trees(frames.field_tree(produced_payload), frames.field_tree(frame.payload))
            result.add("bytes", FAIL, f"frame sequence {seq} differs: {differences[:3]}")
            continue
        for number, kind in facts.source_kinds.items():
            if number in frames.NOT_NATIVE_FIELDS and kind == frames.NATIVE:
                result.add("source-kind", FAIL, f"frame sequence {seq}: field {frames.FIELD_NAMES.get(number)} "
                           "carries coordinator or display-derived output but is marked native Autoware AEB")
        expected = frames.ASSEMBLER_SOURCE_KIND
        for number, kind in facts.source_kinds.items():
            if number in expected and kind != expected[number]:
                result.add("source-kind", FAIL, f"frame sequence {seq}: field {frames.FIELD_NAMES.get(number)} "
                           f"has source kind {frames.SOURCE_KINDS.get(kind)}, not {frames.SOURCE_KINDS[expected[number]]}")
    result.measurements["frames_compared"] = compared
    if compared == 0:
        result.add("pairing", INCONCLUSIVE, "no received frame paired with a produced frame")
    elif not any(finding.outcome == FAIL for finding in result.findings):
        result.add("provenance", PASS, f"{compared} received frames equal their produced frames, byte for byte, "
                   "with their source kinds")
    return result


def evaluate_isolation(run: RunInputs) -> CaseResult:
    """VC-MW-017, REQ-MW-016 second finding: no isolated host port is reachable from a guest domain."""
    result = CaseResult("VC-MW-017", run.run_dir.name)
    verdict = probe.evaluate_isolation(run.run_dir)
    for problem in verdict.problems:
        result.add("probe", INCONCLUSIVE, problem)
    result.measurements["probe_attempts"] = verdict.attempts
    result.measurements["layer_dds_ports"] = verdict.layer_dds_ports
    if not verdict.control_ok:
        return result  # an unreachable result shows nothing without a working control
    for reached in verdict.reachable:
        result.add("reachable", FAIL, f"a guest domain reached host port {reached.get('port')} "
                   f"from {reached.get('guest')} over {reached.get('interface')}")
    if verdict.attempts and verdict.control_ok and not verdict.reachable:
        result.add("isolation", PASS, f"no isolated host port was reachable in {verdict.attempts} probes, "
                   "and the positive control reached its reachable port")
    return result


def evaluate_unsubscribed_discard(run: RunInputs) -> CaseResult:
    """VC-MW-020, REQ-MW-019: after a new subscription, no frame produced more than the margin before it arrives."""
    result = CaseResult("VC-MW-020", run.run_dir.name)
    measurements = _clock_measurements(run)
    start = measurements.get("start")
    end = measurements.get("end")
    if start is None or end is None:
        result.add("clock", INCONCLUSIVE, "ASM-MW-030 needs a start and an end offset measurement; one is missing")
        return result
    result.measurements["offset_start_ns"] = start.offset_ns
    result.measurements["offset_end_ns"] = end.offset_ns
    if not (start.holds() and end.holds()):
        result.add("clock", INCONCLUSIVE, "ASM-MW-030 does not hold in the run: the offset plus its uncertainty "
                   f"is not below 20 ms (start {start.bound_term_ns:.0f} ns, end {end.bound_term_ns:.0f} ns)")
        return result
    received, received_problems = _frames_of(run, "received.pcap", run.received_port)
    for problem in received_problems:
        result.add("capture", INCONCLUSIVE, problem)
    if received is None:
        return result
    subscription_starts = run.settings.get("new_subscription_realtime_ns")
    if not subscription_starts:
        result.add("timeline", INCONCLUSIVE, "the run settings name no new-subscription time on the IVI VM clock")
        return result
    margin_ns = clock.CLOCK_BOUND_NS
    offset = start.offset_ns  # guest - host
    violations = 0
    for frame in received:
        facts = frames.frame_facts(frame.payload)
        if facts.frame_timestamp_ns is None:
            continue
        # The start comes from the guest clock; the production time from the host clock.
        start_on_host = min(subscription_starts) - offset
        if facts.frame_timestamp_ns < start_on_host - margin_ns:
            violations += 1
    result.measurements["frames_after_subscription"] = len(received)
    result.measurements["violations"] = violations
    if violations:
        result.add("discard", FAIL, f"{violations} frames produced more than 20 ms before the new subscription "
                   "reached the HMI")
    else:
        result.add("discard", PASS, "no frame produced before the new subscription (less the 20 ms margin) reached "
                   "the HMI")
    return result


EVALUATORS = {
    "VC-MW-015": evaluate_source_order,
    "VC-MW-016": evaluate_provenance,
    "VC-MW-017": evaluate_isolation,
    "VC-MW-020": evaluate_unsubscribed_discard,
}
