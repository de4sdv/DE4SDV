#!/usr/bin/env python3
"""DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.

Turns the scenario directories that xdomain.py wrote into facts and verdicts.
Three independent records are compared: what the host publisher sent (its
frame log), what crossed the veth into the guest network domain (the
guest-side packet capture, reassembled from TCP), and what the guest's
vsomeip 3.7.6 client delivered to its application (its payload log).

Usage: analyze.py <results-root> [--json out.json] [--markdown out.md]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import someip_pcap  # noqa: E402

SERVICE = 0x4DEE
EVENT = 0x8001
HOST_IP = "10.250.0.1"
GUEST_IP = "10.250.0.2"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frame_seq(data: bytes) -> int | None:
    if len(data) >= 12 and struct.unpack(">I", data[:4])[0] == len(data) - 4:
        return struct.unpack(">Q", data[4:12])[0]
    return None


def read_publisher_frames(path: Path, tag: str) -> list[dict]:
    frames = []
    raw = path.read_bytes() if path.exists() else b""
    offset = 0
    while offset + 20 <= len(raw):
        seq, t_ns, length = struct.unpack("<QQI", raw[offset:offset + 20])
        data = raw[offset + 20:offset + 20 + length]
        offset += 20 + length
        if len(data) != length:
            break
        frames.append({"seq": seq, "t_ns": t_ns, "len": length, "sha256": sha256(data), "tag": tag,
                       "prefix_ok": frame_seq(data) == seq})
    return frames


def read_client_payloads(path: Path) -> list[dict]:
    payloads = []
    raw = path.read_bytes() if path.exists() else b""
    offset = 0
    while offset + 12 <= len(raw):
        recv_ns, length = struct.unpack("<QI", raw[offset:offset + 12])
        data = raw[offset + 12:offset + 12 + length]
        offset += 12 + length
        if len(data) != length:
            break
        payloads.append({"recv_ns": recv_ns, "len": length, "sha256": sha256(data), "seq": frame_seq(data)})
    return payloads


def read_events(path: Path) -> list[tuple[int, str]]:
    events = []
    if not path.exists():
        return events
    for line in path.read_text(errors="replace").splitlines():
        stamp, _, text = line.partition(" ")
        if stamp.isdigit():
            events.append((int(stamp), text))
    return events


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


class Data:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.meta = json.loads((directory / "scenario.json").read_text()) if (directory / "scenario.json").exists() else {}
        self.published: list[dict] = []
        for path in sorted(directory.glob("*_frames.bin")):
            self.published.extend(read_publisher_frames(path, path.name[: -len("_frames.bin")]))
        self.published.sort(key=lambda f: f["t_ns"])
        self.pub_by_seq: dict[int, dict] = {}
        for frame in self.published:
            self.pub_by_seq.setdefault(frame["seq"], frame)
        self.received = read_client_payloads(directory / "client_payloads.bin")
        self.client_events = read_events(directory / "client_events.log")
        self.timeline = read_events(directory / "orchestrator.log")
        clock = self.meta.get("clock", {})
        self.realtime_minus_mono = clock.get("realtime_ns", 0) - clock.get("monotonic_ns", 0)
        self.wire = None
        self.wire_error = None
        pcap = directory / "guest_wire.pcap"
        if pcap.exists():
            try:
                self.wire = someip_pcap.analyse(pcap)
            except Exception as error:  # a truncated capture is reported, not fatal
                self.wire_error = repr(error)

    def wire_mono(self, ts_ns: int) -> int:
        return ts_ns - self.realtime_minus_mono

    def wire_notifications(self) -> list:
        if not self.wire:
            return []
        return [m for m in self.wire["messages"]
                if m.service == SERVICE and m.method == EVENT and m.message_type == 0x02
                and m.src == HOST_IP and m.dst == GUEST_IP]

    def wire_from_guest(self) -> list:
        if not self.wire:
            return []
        return [m for m in self.wire["messages"] if m.src == GUEST_IP and m.service == SERVICE]

    def sd_timeline(self) -> list[dict]:
        if not self.wire:
            return []
        rows = []
        for entry in self.wire["sd"]:
            if entry["service"] != f"0x{SERVICE:04x}":
                continue
            row = dict(entry)
            row["mono_ns"] = self.wire_mono(entry["ts_ns"])
            rows.append(row)
        return rows

    def availability(self) -> list[tuple[int, int]]:
        rows = []
        for stamp, text in self.client_events:
            match = re.match(r"AVAILABLE value=(\d)", text)
            if match:
                rows.append((stamp, int(match.group(1))))
        return rows

    def subscriptions(self) -> list[tuple[int, str]]:
        return [(stamp, text.split("status=")[1]) for stamp, text in self.client_events
                if text.startswith("SUBSCRIPTION_STATUS")]

    def host_log_lines(self, pattern: str) -> dict[str, list[str]]:
        regex = re.compile(pattern, re.IGNORECASE)
        hits = {}
        for path in sorted(self.dir.glob("*.stdout.log")):
            if path.name.startswith(("client", "tcpdump")):
                continue
            lines = [line for line in path.read_text(errors="replace").splitlines() if regex.search(line)]
            if lines:
                hits[path.name] = lines[:20] + ([f"... {len(lines) - 20} more"] if len(lines) > 20 else [])
        return hits


def identity(data: Data, seqs_expected: list[int] | None = None) -> dict:
    received = data.received
    seqs = [r["seq"] for r in received]
    identical = [r for r in received if r["seq"] in data.pub_by_seq and data.pub_by_seq[r["seq"]]["sha256"] == r["sha256"]]
    corrupted = [r for r in received if r not in identical]
    published_seqs = sorted(data.pub_by_seq)
    expected = seqs_expected if seqs_expected is not None else published_seqs
    counts = Counter(seqs)
    latencies_ms = [(r["recv_ns"] - data.pub_by_seq[r["seq"]]["t_ns"]) / 1e6 for r in identical]
    recv_times = [r["recv_ns"] for r in received]
    gaps_ms = [(b - a) / 1e6 for a, b in zip(recv_times, recv_times[1:])]
    wire = data.wire_notifications()
    wire_digests = [m.sha256 for m in wire]
    client_digests = [r["sha256"] for r in received]
    result = {
        "published": len(data.published),
        "published_seq_range": [published_seqs[0], published_seqs[-1]] if published_seqs else None,
        "received": len(received),
        "byte_identical": len(identical),
        "corrupted_or_unknown": len(corrupted),
        "duplicates": sorted(s for s, c in counts.items() if c > 1),
        "order_violations": sum(1 for a, b in zip(seqs, seqs[1:]) if a is not None and b is not None and b <= a),
        "missing_expected": sorted(set(expected) - set(seqs)),
        "received_sizes": {"min": min((r["len"] for r in received), default=None),
                           "max": max((r["len"] for r in received), default=None),
                           "count_2048": sum(1 for r in received if r["len"] == 2048),
                           "count_20": sum(1 for r in received if r["len"] == 20)},
        "latency_ms": {"p50": percentile(latencies_ms, 0.5), "p95": percentile(latencies_ms, 0.95),
                       "max": max(latencies_ms, default=None)},
        "max_inter_arrival_ms": max(gaps_ms, default=None),
        "wire": {
            "notifications": len(wire),
            "transports": sorted({m.transport for m in wire}),
            "digests_equal_client_in_order": wire_digests == client_digests,
            "wire_identical_to_published": sum(
                1 for m in wire if frame_seq(m.payload) in data.pub_by_seq
                and data.pub_by_seq[frame_seq(m.payload)]["sha256"] == m.sha256),
            "error": data.wire_error,
        },
    }
    if wire:
        result["wire"]["first_notification"] = wire[0].describe()
    return result


def received_in(data: Data, seqs: set[int]) -> list[int]:
    return [r["seq"] for r in data.received if r["seq"] in seqs]


def phase_of(stamp: int, marks: list[tuple[str, int]]) -> str:
    phase = "before"
    for name, mark in marks:
        if mark is not None and stamp >= mark:
            phase = f"after {name}"
    return phase


# --------------------------------------------------------------------------- scenarios


def s01(data: Data) -> dict:
    facts = identity(data)
    ok = (facts["received"] >= 100 and facts["byte_identical"] == facts["received"]
          and facts["corrupted_or_unknown"] == 0 and facts["wire"]["digests_equal_client_in_order"])
    summary = (f"{facts['byte_identical']}/{facts['published']} frames byte-identical at the guest client "
               f"(digest), wire digests equal the client's in order: {facts['wire']['digests_equal_client_in_order']}, "
               f"transport {facts['wire']['transports']}")
    return {"verdict": "PASS" if ok else "FAIL", "summary": summary, "facts": facts}


def s02(data: Data) -> dict:
    stale = received_in(data, set(range(1, 51)))
    facts = identity(data, list(range(51, 101)))
    facts["received_produced_before_subscription"] = stale
    ok = not stale and facts["received"] > 0
    return {"verdict": "PASS" if ok else "FAIL", "facts": facts,
            "summary": f"late subscriber received {len(stale)} of the 50 frames produced before it subscribed; "
                       f"first seq received {data.received[0]['seq'] if data.received else None}"}


def s03(data: Data) -> dict:
    during = received_in(data, set(range(41, 81)))
    facts = identity(data, list(range(1, 41)) + list(range(81, 121)))
    facts["received_produced_while_unsubscribed"] = during
    facts["subscriptions"] = data.subscriptions()
    ok = not during and facts["received"] > 0
    return {"verdict": "PASS" if ok else "FAIL", "facts": facts,
            "summary": f"{len(during)} of the 40 frames produced while unsubscribed reached the guest after "
                       f"resubscription; missing expected {len(facts['missing_expected'])}"}


def byte_correct(data: Data, record: dict) -> bool:
    """True if the received bytes equal the published frame that the record's own header names."""
    frame = data.pub_by_seq.get(record["seq"]) if record["seq"] is not None else None
    return frame is not None and frame["sha256"] == record["sha256"]


def s04(data: Data) -> dict:
    killed = data.meta.get("gatewayd_killed_ns")
    after = [r for r in data.received if killed is not None and r["recv_ns"] >= killed]
    correct_after = [r for r in after if byte_correct(data, r)]
    wrong_after = [r for r in after if not byte_correct(data, r)]
    replayed = [r["seq"] for r in correct_after if r["seq"] <= 50]
    recovered = sorted({r["seq"] for r in correct_after if r["seq"] > 50})
    facts = identity(data)
    facts.update({"received_after_kill": len(after), "byte_correct_after_kill": len(correct_after),
                  "wrong_bytes_after_kill": len(wrong_after), "replayed_after_restart": replayed,
                  "new_frames_after_restart": len(recovered),
                  "gatewayd_2_log_tail": (data.dir / "gatewayd-2.stdout.log").read_text(errors="replace").splitlines()[-15:]
                  if (data.dir / "gatewayd-2.stdout.log").exists() else None})
    recovery = "PASS" if len(recovered) == 50 and not wrong_after else ("PARTIAL" if recovered else "FAIL")
    no_replay = "PASS" if not replayed else "FAIL"
    return {"verdict": f"recovery {recovery}, no-replay {no_replay}", "facts": facts,
            "summary": f"after the gatewayd restart the guest got {len(after)} events: {len(correct_after)} with "
                       f"the published bytes ({len(recovered)} new frames, {len(replayed)} replayed, seq <= 50) and "
                       f"{len(wrong_after)} with wrong bytes"}


def s05(data: Data) -> dict:
    stale = received_in(data, set(range(1, 21)))
    facts = identity(data, list(range(21, 61)))
    facts["received_produced_before_subscription"] = stale
    ok = not stale and facts["received"] > 0
    order = ("after gatewayd connected (someipd offers only then)" if data.meta.get("ipc_binding") == "mw_com"
             else "before gatewayd started")
    return {"verdict": "PASS" if ok else "FAIL", "facts": facts,
            "summary": f"guest subscribed {order}; it received {len(stale)} of the 20 frames "
                       f"produced before it subscribed ({stale[:10]})"}


def s06(data: Data) -> dict:
    exited = data.meta.get("publisher_a_exited_ns")
    b_frames = {f["seq"] for f in data.published if f["tag"] == "publisher-b"}
    got_b = received_in(data, b_frames)
    replay = [r["seq"] for r in data.received
              if exited is not None and r["recv_ns"] >= exited and r["seq"] is not None and r["seq"] <= 50]
    facts = identity(data)
    facts.update({"publisher_b_published": len(b_frames), "publisher_b_received": len(got_b),
                  "replayed_after_restart": replay, "availability": data.availability()})
    recovery = "PASS" if b_frames and len(got_b) == len(b_frames) else ("PARTIAL" if got_b else "FAIL")
    return {"verdict": f"recovery {recovery}, no-replay {'PASS' if not replay else 'FAIL'}", "facts": facts,
            "summary": f"after the publisher restart, without restarting gatewayd or someipd, the guest got "
                       f"{len(got_b)}/{len(b_frames)} frames of the new publisher instance"}


def s07(data: Data) -> dict:
    marks = [("publisher stop", data.meta.get("stop_publisher_ns")), ("gatewayd stop", data.meta.get("stop_gatewayd_ns")),
             ("someipd stop", data.meta.get("stop_someipd_ns"))]
    availability = [{"ns": s, "value": v, "phase": phase_of(s, marks)} for s, v in data.availability()]
    host_offers = [row for row in data.sd_timeline() if row["type"] == "OfferService" and row["src"].startswith(HOST_IP)]
    offer_phases = Counter((phase_of(row["mono_ns"], marks), "StopOffer" if row["stop"] else "Offer") for row in host_offers)
    last_frame = max((r["recv_ns"] for r in data.received), default=None)
    facts = {"marks_ns": dict(marks), "client_availability": availability,
             "host_sd_offers_by_phase": {f"{p} / {k}": n for (p, k), n in sorted(offer_phases.items())},
             "frames_received": len(data.received),
             "last_frame_phase": phase_of(last_frame, marks) if last_frame else None,
             "tcp_streams": data.wire["streams"] if data.wire else None}
    first_up = next((a["ns"] for a in availability if a["value"] == 1), None)
    went_away = [a for a in availability if a["value"] == 0 and first_up is not None and a["ns"] > first_up]
    summary = ("after the guest saw the service, it first saw it unavailable "
               + (f"in phase '{went_away[0]['phase']}'" if went_away else "never")
               + f"; host SD offers by phase: {facts['host_sd_offers_by_phase']}")
    return {"verdict": "INFO", "facts": facts, "summary": summary}


def s08(data: Data) -> dict:
    killed = data.meta.get("kill_someipd_ns")
    went_away = [s for s, v in data.availability() if v == 0 and killed is not None and s >= killed]
    delay_s = (went_away[0] - killed) / 1e9 if went_away else None
    facts = {"kill_ns": killed, "first_unavailable_after_kill_s": delay_s, "availability": data.availability(),
             "tcp_streams": data.wire["streams"] if data.wire else None,
             "gatewayd_log_after_kill": data.host_log_lines(r"error|fail|lost|disconnect|abort|terminate")}
    return {"verdict": "INFO", "facts": facts,
            "summary": f"guest saw the service unavailable {delay_s} s after someipd was killed"}


def s09(data: Data) -> dict:
    start, end = data.meta.get("stall_start_ns"), data.meta.get("stall_end_ns")
    during = {f["seq"] for f in data.published if start is not None and end is not None and start <= f["t_ns"] < end}
    received = {r["seq"]: r for r in data.received}
    backlog = sorted(seq for seq in during if seq in received)
    ages = [(received[s]["recv_ns"] - data.pub_by_seq[s]["t_ns"]) / 1e9 for s in backlog]
    after_resume = [r for r in data.received if end is not None and r["recv_ns"] >= end]
    facts = {"stall_s": (end - start) / 1e9 if start and end else None,
             "published_during_stall": len(during),
             "delivered_after_resume_that_were_published_during_stall": len(backlog),
             "dropped_from_stall_window": len(during) - len(backlog),
             "max_age_on_delivery_s": max(ages, default=None),
             "received_after_resume_total": len(after_resume),
             "rss_kib": data.meta.get("rss"),
             "host_queue_log_lines": data.host_log_lines(r"queue|limit|full|drop|overflow")}
    return {"verdict": "INFO", "facts": facts,
            "summary": f"{len(backlog)} of {len(during)} frames published during a {facts['stall_s']} s stall were "
                       f"delivered after the guest resumed, the oldest {facts['max_age_on_delivery_s']} s old"}


def s10(data: Data) -> dict:
    from_guest = data.wire_from_guest()
    requests = [m.describe() for m in from_guest if m.message_type in (0x00, 0x01)]
    to_guest_replies = [m.describe() for m in (data.wire["messages"] if data.wire else [])
                        if m.src == HOST_IP and m.message_type in (0x80, 0x81)]
    other = [text for _, text in data.client_events if text.startswith("OTHER_MESSAGE")]
    facts = identity(data)
    facts.update({"probe_requests_on_wire": requests, "host_replies_on_wire": to_guest_replies,
                  "client_other_messages": other,
                  "host_logs_mentioning_probe": data.host_log_lines(r"probe|0x0001|unknown method|no handler")})
    return {"verdict": "INFO", "facts": facts,
            "summary": f"{len(requests)} guest requests on the wire, {len(to_guest_replies)} host replies; frames "
                       f"still byte-identical: {facts['byte_identical']}/{facts['received']}"}


DIAGNOSTIC_PATTERN = (r"subscri|rollback|outdated|max_sample|maxsample|reject|error|warn|fatal|terminat|abort|"
                      r"restart|stale|notif|connect")


def debug_excerpts(data: Data, names: list[str], limit: int = 60) -> dict[str, list[str]]:
    regex = re.compile(DIAGNOSTIC_PATTERN, re.IGNORECASE)
    excerpts = {}
    for name in names:
        path = data.dir / f"{name}.stdout.log"
        if not path.exists():
            continue
        lines = [line[:300] for line in path.read_text(errors="replace").splitlines()
                 if regex.search(line) and " SENT seq=" not in line]
        excerpts[name] = lines[:limit] + ([f"... {len(lines) - limit} more"] if len(lines) > limit else [])
    return excerpts


def backtrace(data: Data, process: str) -> dict:
    """The aborting thread of a core dump of `process`, if the workflow produced one."""
    pid = data.meta.get("processes", {}).get(process, {}).get("pid")
    root = data.dir.parent / "backtraces"
    files = sorted(root.glob(f"core.*.{pid}.*bt.txt")) if pid and root.exists() else []
    if not files:
        return {"core": None, "pid": pid}
    text = files[0].read_text(errors="replace")
    threads = re.split(r"\n(?=Thread \d+ )", text)
    aborting = next((t for t in threads if re.search(r"\babort\b|raise|terminate", t)), threads[0] if threads else "")
    frames = [line for line in aborting.splitlines() if line.startswith("#")]
    return {"core": files[0].name, "pid": pid, "aborting_thread_frames": frames[:30],
            "threads": len([t for t in threads if t.startswith("Thread ")])}


def s11(data: Data) -> dict:
    code = data.meta.get("processes", {}).get("gatewayd", {}).get("exit_code")
    facts = {"gatewayd_exit_code": code, "backtrace": backtrace(data, "gatewayd"),
             "gatewayd_log": debug_excerpts(data, ["gatewayd"]),
             "frames_received_before_stop": len(data.received)}
    return {"verdict": "INFO", "facts": facts,
            "summary": f"gatewayd exit code {code} on SIGTERM; core {facts['backtrace'].get('core')}"}


def s13(data: Data) -> dict:
    result = s04(data)
    result["facts"]["debug_log_excerpts"] = debug_excerpts(data, ["gatewayd", "gatewayd-2", "publisher", "someipd"])
    return result


def s15(data: Data) -> dict:
    killed = data.meta.get("gatewayd_killed_ns")
    b_frames = {f["seq"] for f in data.published if f["tag"] == "publisher-b"}
    got_b = received_in(data, b_frames)
    facts = identity(data)
    facts.update({"publisher_b_published": len(b_frames), "publisher_b_received": len(got_b),
                  "received_after_kill": len([r for r in data.received if killed and r["recv_ns"] >= killed]),
                  "debug_log_excerpts": debug_excerpts(data, ["gatewayd-2", "publisher-b"])})
    recovery = "PASS" if b_frames and len(got_b) == len(b_frames) else ("PARTIAL" if got_b else "FAIL")
    return {"verdict": f"recovery {recovery}", "facts": facts,
            "summary": f"after restarting gatewayd and then the publisher, the guest got {len(got_b)}/{len(b_frames)} "
                       f"frames of the new publisher instance"}


def s18(data: Data) -> dict:
    facts = identity(data)
    subscribed = next((s for s, status in data.subscriptions() if status == "0x0"), None)
    found = data.meta.get("gatewayd_found_ns")  # orchestrator poll, about 50 ms after the log line
    correct = [r for r in data.received if byte_correct(data, r)]
    before_sub = sorted(r["seq"] for r in correct if subscribed is not None and data.pub_by_seq[r["seq"]]["t_ns"] < subscribed)
    before_found = sorted(r["seq"] for r in correct if found is not None and data.pub_by_seq[r["seq"]]["t_ns"] < found)
    ages = [(r["recv_ns"] - data.pub_by_seq[r["seq"]]["t_ns"]) / 1e9 for r in correct]
    facts.update({"client_subscribed_ns": subscribed, "gatewayd_found_ns": found,
                  "delivered_published_before_guest_subscription": before_sub,
                  "delivered_published_before_gatewayd_found": before_found,
                  "first_delivered_seq": data.received[0]["seq"] if data.received else None,
                  "max_delivery_age_s": max(ages, default=None)})
    ok = (facts["corrupted_or_unknown"] == 0 and not before_sub and facts["received"] > 0)
    return {"verdict": "PASS" if ok else "FAIL", "facts": facts,
            "summary": f"spawn-only start order: {facts['byte_identical']}/{facts['received']} received frames "
                       f"byte-identical, {facts['corrupted_or_unknown']} wrong; {len(before_sub)} delivered frames were "
                       f"published before the guest subscribed, {len(before_found)} before gatewayd found the "
                       f"publisher; oldest delivery {facts['max_delivery_age_s']} s"}


def s16(data: Data) -> dict:
    facts = identity(data)
    ok = (facts["received"] >= 100 and facts["byte_identical"] == facts["received"]
          and facts["wire"]["digests_equal_client_in_order"])
    return {"verdict": "PASS" if ok else "FAIL", "facts": facts,
            "summary": f"{facts['byte_identical']}/{facts['published']} byte-identical at 100 Hz; missing "
                       f"{len(facts['missing_expected'])}, max inter-arrival {facts['max_inter_arrival_ms']} ms, "
                       f"latency p95 {facts['latency_ms']['p95']} ms"}


EVALUATORS = {
    "s01-main": s01, "s02-late-subscriber": s02, "s03-resubscribe": s03, "s04-gatewayd-crash-restart": s04,
    "s05-late-gatewayd": s05, "s06-publisher-restart": s06, "s07-host-stop-sequence": s07,
    "s08-someipd-kill": s08, "s09-stalled-guest": s09, "s10-guest-request-probe": s10,
    "s11-gatewayd-sigterm-publisher-alive": s11, "s12-gatewayd-sigterm-without-publisher": s11,
    "s13-gatewayd-crash-restart-debug": s13, "s14-gatewayd-crash-restart-2subs": s13,
    "s15-gatewayd-crash-then-publisher-restart": s15, "s16-main-1000-frames-100hz": s16,
    "s17-gateway-pair-restart": s13,
    "s18-start-order-spawn-only": s18,
}


def common(data: Data) -> dict:
    processes = data.meta.get("processes", {})
    return {
        "description": data.meta.get("description"),
        "orchestrator_error": data.meta.get("orchestrator_error"),
        "wait_timeouts": [w["what"] for w in data.meta.get("waits", []) if not w["ok"]],
        "exit_codes": {name: p.get("exit_code") for name, p in processes.items()},
        "mapped_libraries": {name: p.get("mapped_libraries") for name, p in processes.items() if p.get("mapped_libraries")},
        "publisher_alloc_or_send_failures": sum(1 for path in data.dir.glob("*_events.log")
                                                for _, text in read_events(path)
                                                if text.startswith(("ALLOC_FAIL", "SEND_FAIL"))),
        "sd_entries": len(data.sd_timeline()),
        "wire_packets": data.wire["packets"] if data.wire else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--json")
    parser.add_argument("--markdown")
    args = parser.parse_args()
    root = Path(args.root)
    results = {}
    if not root.is_dir():
        print(f"no results directory {root}: the scenarios did not run")
        return 1
    for directory in sorted(p for p in root.iterdir() if p.is_dir()):
        evaluator = EVALUATORS.get(directory.name)
        if evaluator is None:
            continue
        data = Data(directory)
        try:
            result = evaluator(data)
        except Exception as error:
            result = {"verdict": "BROKEN", "summary": f"analysis error {error!r}", "facts": {}}
        result["common"] = common(data)
        results[directory.name] = result
    text = json.dumps(results, indent=2, default=str)
    if args.json:
        Path(args.json).write_text(text)
    lines = ["| scenario | verdict | summary |", "|---|---|---|"]
    for name, result in results.items():
        lines.append(f"| {name} | {result['verdict']} | {result['summary']} |")
    table = "\n".join(lines)
    if args.markdown:
        Path(args.markdown).write_text(table + "\n")
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
