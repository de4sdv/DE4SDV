"""INC-MW-011 phase 8: the gateway pin, the AAOS SDV broker path, the relay's discard rule and the adapter's abort conditions.

ASM-MW-021 binds every S-CORE statement of the increment to its pins. The other
slices name the same gateway and lifecycle commits, and the bench that builds
the layer builds those commits too. SOME/IP ends at the SOME/IP broker of the
SDV Core VM, and the layer refers to the AAOS SDV elements that it uses
(ADR 0025). The IVI frame relay discards the frames that the AEBS stack produced
before the HMI application's subscription phase (REQ-MW-019), with the clock
bound of ASM-MW-030 and the residual band of GAP-MW-045; the relay's code uses
the same margin and copy window. The criteria of REQ-MW-019 declare that margin
as the bound of ASM-MW-030, and VC-MW-020 checks it. ASM-MW-030 measures the
clock that times the start of the subscription, the IVI VM clock. The
one-process adapter of REQ-MW-018 has two conditions: one ROS 2 environment on
the host (ASM-MW-031 for the processes outside the layer) and no ROS 2 parameter
services. Its fault-injection interface is the trigger of the abort test.
someipd names ASM-MW-031 for the DDS criteria of REQ-MW-016.

These are lexical source guards; licensed Syside validates the model in CI. The
pins live in doc comments, so these tests read the docs on purpose. They check
consistency, not existence. The pin check skips only while the bench is absent and
no workflow declares the pins. The relay check reads only the files that git
tracks, so ignored build output, bags and workspaces never count. It skips while
no tracked non-Markdown file under implementation/ or .github/ names the relay's
service (de4sdv_ivi_frame_relay) or its margin constant (kPhaseStartMarginNs),
and outside a git checkout. Once one does, the relay's headers and its init
file, the one with a `service de4sdv_ivi_frame_relay` line, must carry the
model's margin and copy window.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"
VERIFICATION = MIDDLEWARE / "middleware_score_verification_evidence.sysml"
#: The S-CORE slices of INC-MW-011.
SCORE_SLICES = sorted(MIDDLEWARE.glob("middleware_score_*.sysml"))
WORKFLOWS = ROOT / ".github" / "workflows"
#: The realization trees, and the S-CORE reference interop bench when it is on the revision.
IMPLEMENTATION = ROOT / "implementation"
BENCH = IMPLEMENTATION / "score-reference-interop-bench"
#: The IVI frame relay shows by its service name or by its margin constant, in the realization or in CI.
RELAY_SERVICE = "de4sdv_ivi_frame_relay"
RELAY_MARKERS = (RELAY_SERVICE, "kPhaseStartMarginNs")
#: The pathspecs of the marker and header scans.
MARKER_PATHSPECS = ("implementation", ".github")
#: The relay's init file declares its service on a line of its own; a comment does not count.
_RELAY_SERVICE_LINE = re.compile(rf"^\s*service\s+{RELAY_SERVICE}\b", re.M)
#: The frame assembler of INC-AEBS-010, whose timer sets the frame period.
BRIDGE_NODE = (ROOT / "implementation" / "aebs-aaos-sdv-visualization-bench" / "src" / "de4sdv_aebs_010_bridge"
               / "de4sdv_aebs_010_bridge" / "ros_node.py")

_GATEWAY_PIN = re.compile(r"inc_someip_gateway at commit ([0-9a-f]{40})")
_LIFECYCLE_PIN = re.compile(r"lifecycle v0\.6\.1 \(commit ([0-9a-f]{40})\)")
_WORKFLOW_PIN = re.compile(r"^\s*(GATEWAY_SHA|LIFECYCLE_SHA):\s*[\"']?([0-9a-fA-F]+)[\"']?\s*(?:#.*)?$", re.M)


def _flat(text: str) -> str:
    """The text with comment line prefixes removed and whitespace collapsed."""
    lines = (re.sub(r"^\s*\*\s?", "", line) for line in text.splitlines())
    return " ".join(" ".join(lines).split())


def _part_doc(text: str, short_name: str) -> str:
    """The flattened doc of the one part with ``short_name``."""
    matches = list(re.finditer(rf"\bpart <'{re.escape(short_name)}'> \w+ : \w+ \{{\s*doc /\*(.*?)\*/", text, re.DOTALL))
    assert len(matches) == 1, f"expected one part <'{short_name}'> with a doc, found {len(matches)}"
    return _flat(matches[0][1])


def _named_part_doc(text: str, name: str) -> str:
    """The flattened doc of the one part usage ``name`` without a short name."""
    matches = list(re.finditer(rf"\bpart {re.escape(name)} : \w+ \{{\s*doc /\*(.*?)\*/", text, re.DOTALL))
    assert len(matches) == 1, f"expected one part {name} with a doc, found {len(matches)}"
    return _flat(matches[0][1])


def _comment(text: str, name: str) -> tuple[list[str], str]:
    """The about targets and the flattened body of the one package comment ``name``."""
    matches = list(re.finditer(rf"\bcomment {re.escape(name)}\s+about\s+(.*?)\s*/\*(.*?)\*/", text, re.DOTALL))
    assert len(matches) == 1, f"expected one comment {name}, found {len(matches)}"
    targets = [target.strip() for target in matches[0][1].split(",")]
    return targets, _flat(matches[0][2])


def _adapter_doc(text: str) -> str:
    """The flattened doc of the adapter reference of the physical realization."""
    matches = list(re.finditer(r"\bref part adapter : [\w, ]+ \{\s*doc /\*(.*?)\*/", text, re.DOTALL))
    assert len(matches) == 1, f"expected one ref part adapter with a doc, found {len(matches)}"
    return _flat(matches[0][1])


def _verification_def_doc(name: str) -> str:
    """The flattened doc of the one verification definition ``name`` of the verification slice."""
    text = VERIFICATION.read_text(encoding="utf-8")
    matches = list(re.finditer(rf"\bverification def {re.escape(name)}\s*\{{\s*doc /\*(.*?)\*/", text, re.DOTALL))
    assert len(matches) == 1, f"expected one verification def {name} with a doc, found {len(matches)}"
    return _flat(matches[0][1])


def _asm_mw_021() -> str:
    return _named_part_doc(FRAMING.read_text(encoding="utf-8"), "asmSCOREBaselinePinned")


def _pins() -> tuple[str, str]:
    """The gateway and lifecycle commits of ASM-MW-021."""
    doc = _asm_mw_021()
    (gateway,) = set(_GATEWAY_PIN.findall(doc))
    (lifecycle,) = set(_LIFECYCLE_PIN.findall(doc))
    return gateway, lifecycle


def _workflow_pins(text: str) -> list[tuple[str, str]]:
    """Every GATEWAY_SHA and LIFECYCLE_SHA occurrence of a workflow, in order."""
    return _WORKFLOW_PIN.findall(text)


def _numbers(pattern: str, text: str) -> list[int]:
    return [int(value) for value in re.findall(pattern, text)]


def _tracked(*pathspecs: str) -> list[Path] | None:
    """The files that git tracks under ``pathspecs`` and that exist in the working tree; None outside a checkout.

    Git, not the working tree, decides what belongs to the revision: an ignored file is never read, however large,
    and a tracked file is read wherever it sits.
    """
    try:
        listing = subprocess.run(["git", "ls-files", "-z", "--", *pathspecs], cwd=ROOT,
                                 capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    paths = (ROOT / name for name in listing.decode("utf-8").split("\0") if name)
    return [path for path in paths if path.is_file()]


def _relay_marker_files(tracked: list[Path]) -> list[str]:
    """The tracked non-Markdown files that name the relay's service or its margin constant.

    Markdown is left out, so a README may name the service before the code lands.
    """
    markers = tuple(marker.encode() for marker in RELAY_MARKERS)
    found = []
    for path in tracked:
        if path.suffix == ".md":
            continue
        data = path.read_bytes()
        if any(marker in data for marker in markers):
            found.append(path.relative_to(ROOT).as_posix())
    return found


def test_asm_mw_021_pins_one_gateway_commit_with_its_module_versions() -> None:
    doc = _asm_mw_021()
    assert doc.startswith("ASM-MW-021:"), doc[:40]
    assert len(set(_GATEWAY_PIN.findall(doc))) == 1, "ASM-MW-021 names one gateway commit"
    assert len(_LIFECYCLE_PIN.findall(doc)) == 1, "ASM-MW-021 pins the lifecycle commit"
    assert "communication 0.5.0 with two patches of the gateway and baselibs 0.2.16 with one" in doc
    assert "0.2.15" not in doc, "ASM-MW-021 still names the baselibs of the earlier gateway pin"


def test_every_pin_of_the_s_core_slices_is_the_one_of_asm_mw_021() -> None:
    gateway, lifecycle = _pins()
    for pattern, pin, least in ((_GATEWAY_PIN, gateway, 4), (_LIFECYCLE_PIN, lifecycle, 2)):
        found: dict[str, list[str]] = {}
        for path in SCORE_SLICES:
            for commit in pattern.findall(_flat(path.read_text(encoding="utf-8"))):
                found.setdefault(commit, []).append(path.name)
        assert set(found) == {pin}, f"pins other than ASM-MW-021's {pin}: {found}"
        assert len(found[pin]) >= least, f"expected at least {least} statements of {pin}, found {found[pin]}"


def test_the_workflow_pin_reader_reads_every_occurrence() -> None:
    text = ("env:\n  GATEWAY_REPO: https://example.invalid/gw.git\n"
            f"  GATEWAY_SHA: {'a' * 40}\n  LIFECYCLE_SHA: \"{'b' * 40}\"  # a comment\n"
            f"jobs:\n  build:\n    env:\n      GATEWAY_SHA: {'c' * 40}\n")
    assert _workflow_pins(text) == [("GATEWAY_SHA", "a" * 40), ("LIFECYCLE_SHA", "b" * 40),
                                    ("GATEWAY_SHA", "c" * 40)]


def test_every_workflow_builds_the_commits_that_asm_mw_021_pins() -> None:
    """main never holds a bench pinned to one commit and a model pinned to another."""
    gateway, lifecycle = _pins()
    expected = {"GATEWAY_SHA": gateway, "LIFECYCLE_SHA": lifecycle}
    found = {path.name: _workflow_pins(path.read_text(encoding="utf-8"))
             for path in sorted(WORKFLOWS.glob("*.y*ml"))}
    found = {name: pins for name, pins in found.items() if pins}
    if not found:
        assert not BENCH.exists(), f"{BENCH.relative_to(ROOT)} is on the revision, but no workflow declares its pins"
        pytest.skip("the S-CORE reference interop bench is not on this revision")
    wrong = {name: [(key, value) for key, value in pins if value != expected[key]] for name, pins in found.items()}
    assert not any(wrong.values()), f"workflow pins other than ASM-MW-021's: {wrong}"
    declared = {key for pins in found.values() for key, _ in pins}
    assert declared == set(expected), f"the workflows declare {sorted(declared)}, not both pins"


def test_the_relay_discard_rule_traces_its_requirements_bound_and_residual() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    targets, rule = _comment(text, "relaySubscriptionPhaseDiscardRule")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqDeliverAEBSSignalsInSourceOrder",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqPreserveAEBSSignalProvenance",
        "gapLoLaReturnsStoredSamplesOnSubscription",
        "asmHostAndGuestClocksAgree",
        "gapPhaseStartDiscardBand",
    ]
    assert re.search(r"\bpart <'ASM-MW-030'> asmHostAndGuestClocksAgree : IncrementAssumption \{", text)
    assert re.search(r"\bpart <'GAP-MW-045'> gapPhaseStartDiscardBand : IncrementGap \{", text)
    (margin,) = _numbers(r"not earlier than the phase start less (\d+) ms, the bound of ASM-MW-030", rule)
    assert _numbers(r"The margin is fixed at (\d+) ms\. No option sets it, and the relay stops at start on any "
                    r"margin option", rule) == [margin]
    (bound,) = _numbers(r"differ by less than (\d+) ms", _part_doc(text, "ASM-MW-030"))
    (band_margin,) = _numbers(r"it puts its (\d+) ms margin before the start", _part_doc(text, "GAP-MW-045"))
    assert margin == bound == band_margin, (margin, bound, band_margin)
    for statement in ("the relay holds a subscription, through the SDV Gateway on IVI, to the broker's publication "
                      "of the frame topic",
                      "the ingress is connected to the relay's loopback server",
                      "the notification Disconnected of the gateway client, an event of the API that the "
                      "feasibility runs did not see",
                      "the notification PublicationDestroyed of the subscription",
                      "no message for 3 s, the relay's own timeout",
                      "saw PublicationDestroyed within about 0.1 s after a restart of someipd",
                      # A phase end that the layer causes is a delivery failure for REQ-MW-014, and for REQ-MW-019
                      # the new phase is the current subscription (claims review R1 of phase 8 and of phase 10).
                      "A phase end that the layer causes is a phase end by PublicationDestroyed, by Disconnected or "
                      "by the timeout, while the ingress stays connected. For REQ-MW-014 it is a delivery failure of "
                      "the layer, not an unsubscription of the HMI application. For REQ-MW-019 the new phase is the "
                      "current subscription. So the verification of REQ-MW-014 records every phase end.",
                      "It never lets the run pass.",
                      "A DATA_LOSS status of a read is a gap (GAP-MW-037). It does not end the phase.",
                      "So the timeout is the event that ends the phase then (GAP-MW-048).",
                      "They are older than the new phase, so the first check drops them.",
                      "accepts it as the only client",
                      "The relay takes the phase start from the system clock of the IVI VM.",
                      "It is no copy of a frame that the relay served in this phase",
                      "it clears them at each phase start",
                      "a subscriber with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE reads only the messages published "
                      "after its subscription",
                      "the rule drops no frame that the AEBS stack produced after the phase start"):
        assert statement in rule, statement
    # The SOME/IP events of the parked receiver no longer define the phase: the broker ends SOME/IP. The unscoped
    # sentence that read a phase end as no unsubscription for every requirement is gone.
    for gone in ("SubscribeEventgroupAck", "TCP keepalive", "a reboot of someipd",
                 "It is not an unsubscription of the HMI application."):
        assert gone not in rule, gone


def test_asm_mw_030_holds_the_clock_bound_with_session_controls() -> None:
    """The offset is measured two-way on the clock that times the subscription, and steps of both clocks are logged."""
    assumption = _part_doc(PHYSICAL.read_text(encoding="utf-8"), "ASM-MW-030")
    (bound,) = _numbers(r"differ by less than (\d+) ms", assumption)
    assert _numbers(r"No case starts before the start measurement gives an offset whose size plus that "
                    r"uncertainty is below (\d+) ms", assumption) == [bound]
    for control in ("the system clocks of the Linux host and of the IVI VM of the AAOS SDV guest differ",
                    "the IVI VM clock is set after each boot and before each session",
                    "So the bound holds only after a clock setting",
                    "The relay takes the phase start from the system clock of the IVI VM. So that clock times the "
                    "start of the HMI application's subscription.",
                    "by a two-way time exchange with the chrony of the host",
                    "A setting through adb is not used",
                    "the same two-way time exchange, without a clock setting, measures the offset between the host "
                    "clock and the IVI VM clock",
                    "the host logs each step of its clock",
                    "That minimum bounds the offset from one side only",
                    # The relay's log is no bounding control at the latency of the broker path (claims review R5).
                    "So it cannot detect an offset inside 20 ms, and it is no bounding control",
                    "It is the only control that bounds the offset. It reports its uncertainty, half of its round "
                    "trip.",
                    "A run whose measured offset plus its uncertainty is not below 20 ms is void",
                    # A slewing client, or sessions sized from the drift (technical review R12).
                    "A slew changes CLOCK_REALTIME and CLOCK_MONOTONIC alike, so it is no step under this "
                    "assumption.",
                    "Otherwise each session is sized from the measured drift"):
        assert control in assumption, control
    # The SOME/IP path no longer ends in the IVI VM (owner decision of 2026-10-28, finding D5 of the requirements
    # review).
    assert "the offset comes from SOME/IP packets" not in assumption, "the measurement follows the subscription clock"


def test_the_derived_numbers_follow_the_bound_the_frame_period_and_the_slots() -> None:
    """The band is twice the bound at most, below half of the assembler's frame period; the copy window sums the slots."""
    text = PHYSICAL.read_text(encoding="utf-8")
    assumption = _part_doc(text, "ASM-MW-030")
    (bound,) = _numbers(r"differ by less than (\d+) ms", assumption)
    (band_max,) = _numbers(r"more than 0 ms and less than (\d+) ms while ASM-MW-030 holds", _part_doc(text, "GAP-MW-045"))
    assert band_max == 2 * bound, (band_max, bound)
    (period,) = _numbers(r"below half of the (\d+) ms frame period of the frame assembler", assumption)
    (seconds,) = re.findall(r"self\.create_timer\(([0-9.]+), self\._publish_frame\)",
                            BRIDGE_NODE.read_text(encoding="utf-8"))
    assert round(float(seconds) * 1000) == period, (seconds, period)
    assert band_max < period / 2, (band_max, period)
    _, rule = _comment(text, "relaySubscriptionPhaseDiscardRule")
    (window,) = _numbers(r"of the last (\d+) frames it served", rule)
    slots = re.search(r"the (\d+) slots of the adapter's frame event and the (\d+) of gatewayd's bridged service", rule)
    assert slots, "the rule names the slot counts that its copy window sums"
    assert window == int(slots[1]) + int(slots[2]), (window, slots.groups())
    # Each addend comes from the statement that sets it, not from the rule itself.
    (frame_event_slots,) = _numbers(r"give the frame event no cycle and (\d+) sample slots", text)
    gatewayd = _named_part_doc(text, "gatewayd")
    (bridged_slots,) = _numbers(r"offers the frame service again as a bridged service with (\d+) sample slots", gatewayd)
    assert (int(slots[1]), int(slots[2])) == (frame_event_slots, bridged_slots), (slots.groups(), frame_event_slots,
                                                                                 bridged_slots)
    (max_samples,) = _numbers(r"with a maximum sample count of (\d+)", gatewayd)
    (needed,) = _numbers(r"So the frame event needs at least (\d+) sample slots", gatewayd)
    assert needed == max_samples <= frame_event_slots, (needed, max_samples, frame_event_slots)


def test_the_relay_code_uses_the_margin_and_the_copy_window_of_the_model() -> None:
    """Once a tracked file names the IVI frame relay, its code and its init file carry the model's margin and window.

    The check holds the realization to the model; it does not need the relay to exist. It reads only the files
    that git tracks. It skips only while no tracked non-Markdown file under implementation/ or .github/ names the
    relay's service or its margin constant, so a silent skip needs both names gone from all of them. Outside a
    git checkout it skips, because it cannot tell tracked files from build output there.
    """
    tracked = _tracked(*MARKER_PATHSPECS)
    init_files = _tracked("*.rc")
    if tracked is None or init_files is None:
        pytest.skip("not a git checkout: the relay check reads only the files that git tracks")
    found = _relay_marker_files(tracked)
    if not found:
        pytest.skip("no file under implementation/ or .github/ names the IVI frame relay (tracked, non-Markdown)")
    _, rule = _comment(PHYSICAL.read_text(encoding="utf-8"), "relaySubscriptionPhaseDiscardRule")
    (margin,) = _numbers(r"not earlier than the phase start less (\d+) ms", rule)
    (window,) = _numbers(r"of the last (\d+) frames it served", rule)
    named = f"{found[0]} names the relay's service or its margin constant"
    headers = [path for path in tracked if path.suffix == ".hpp" and path.is_relative_to(IMPLEMENTATION)]
    code = "\n".join(path.read_text(encoding="utf-8") for path in headers)
    margins = [int(value.replace("'", "")) for value in re.findall(r"\bkPhaseStartMarginNs\s*=\s*([0-9']+)", code)]
    windows = [int(value) for value in re.findall(r"\bkCopyMemoryFrames\s*=\s*(\d+)", code)]
    assert margins, f"{named}, but no header under implementation/ defines kPhaseStartMarginNs"
    assert margins == [margin * 1_000_000], f"the relay's margin is {margins} ns, the model's {margin} ms"
    assert windows == [window], f"the relay keeps {windows} frames, the model {window}"
    # The ingress of INC-AEBS-010 has an init file too, so the relay's own one must declare its service.
    relay_init = [rc for rc in init_files if _RELAY_SERVICE_LINE.search(rc.read_text(encoding="utf-8"))]
    assert relay_init, f"{named}, but no tracked init file (*.rc) declares the service {RELAY_SERVICE}"
    for rc in init_files:
        lines = [line for line in rc.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]
        options = re.findall(r"--[\w-]*(?:margin|bound)[\w-]*", "\n".join(lines))
        assert not options, f"{rc.name} passes {options}; no option sets the margin, fixed at {margin} ms"


def test_the_relay_repeats_the_ingress_trigger_only_until_its_first_client() -> None:
    doc = _named_part_doc(PHYSICAL.read_text(encoding="utf-8"), "iviFrameRelay")
    for statement in ("It does so at each of its own starts, once its loopback server listens.",
                      "So until the first client of the current relay process connects, the relay repeats the "
                      "trigger at a fixed interval, a fixed number of times at most.",
                      "After that first client, it never triggers the ingress again."):
        assert statement in doc, statement
    for removed in ("while no client is connected", "harmless"):
        assert removed not in doc, removed


def test_the_relay_subscribes_through_the_gateway_and_removes_the_broker_wrapper() -> None:
    """The relay reads no message from before its subscription and checks the framing after the wrapper (S1, S2)."""
    doc = _named_part_doc(PHYSICAL.read_text(encoding="utf-8"), "iviFrameRelay")
    for statement in ("with the subscriber flag ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE",
                      "Each message holds the SOME/IP payload of one frame event in the broker's wrapper for "
                      "INTERPRET_AS_BYTES: a protobuf message with one bytes field "
                      "(some_ip/broker_agent_comms/src/translator/broker_translator.rs:248-262).",
                      # The strict parse of the wrapper (technical review R10).
                      "The relay parses the wrapper strictly. The outer varint must equal the size that remains. "
                      "Exactly one field must follow: field 1 of wire type 2 (0x0A), whose length equals the rest, "
                      "with no other byte.",
                      "Then it forwards a payload only when the payload's own length prefix matches the payload length",
                      "The broker subscribes to someipd whether an IVI subscriber exists or not "
                      "(some_ip/broker_agent_comms/src/pubsub/pubsub_handler.rs:764-923).",
                      "from the bench's synthetic frame source",
                      "This rule is the discard that REQ-MW-019 relies on in the guest.",
                      "on 127.0.0.1:4731 of the IVI VM loopback",
                      # The resubscription (owner decision of 2026-10-29), with the conditions of both reviews.
                      "Subscription (owner decision of 2026-10-29):",
                      "The relay keeps one subscription for its lifetime, with or without a client.",
                      "It runs the gateway client (init, subscribe and read) on a thread of its own, with bounded "
                      "waits. The loopback server and the ingress connection do not depend on that thread.",
                      "On PublicationDestroyed, it ends the old subscription and subscribes again: every 100 ms for "
                      "the first 5 s, then every second.",
                      "PublicationDestroyed came within about 0.1 s after a restart of someipd",
                      "On Disconnected, it creates the gateway client again, with a bounded retry, and it logs each "
                      "attempt. Disconnected is an event of the API. The feasibility runs did not see it.",
                      "When no message comes for 3 s, it ends the subscription and subscribes again.",
                      "After three subscriptions in a row that bring no message, it waits 5 s between them.",
                      "It counts each failed subscription and logs it with its status text.",
                      "if no subscription succeeds within 30 s of its start, the relay reports a likely fault of the "
                      "ACL or of the mapping. After that, it tries every 10 s.",
                      "It counts a DATA_LOSS status of a read as a gap (GAP-MW-037), not as the end of a phase.",
                      "which someipd (no receiver for guest data) and the host configuration of GAP-MW-046 (DDS "
                      "ports) enforce.",
                      "(init/service.cpp:620-642 and 328-329 of platform/system/core at android17-release).",
                      "The publication was instance1:com.android.sdv.someip.SomeIpBroker/default, unit "
                      "de4sdv-score-aebs-signal-frame."):
        assert statement in doc, statement
    assert "FLAG_FETCHLASTMESSAGE" not in doc, "the relay never asks for the last message before its subscription"
    for gone in ("about 0.5 s", "no message comes for 1 s", "android14-release", "which someipd enforces"):
        assert gone not in doc, gone
    # The relay's input carries the wrapped topic; its behavior unwraps it (technical review R11).
    relay = _braced(PHYSICAL.read_text(encoding="utf-8"), r"\bpart iviFrameRelay : PhysicalAllocationElement \{")
    assert re.search(r"\bport frameTopicIn : DataTunnelPort \{", relay)
    assert re.search(r"\bport aebsSignalFrameOut : AEBSSignalFrameOut \{", relay)


def test_the_guest_side_guard_rail_names_the_clock_assumption() -> None:
    targets, _ = _comment(PHYSICAL.read_text(encoding="utf-8"), "guestStaleFrameDropGuardRail")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay",
        "asmFrameAssemblerAndIngressReusedUnchanged",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed",
        "gapLoLaReturnsStoredSamplesOnSubscription",
        "asmHostAndGuestClocksAgree",
    ]

def test_the_adapter_abort_conditions_name_the_ros2_environment_and_the_parameter_services() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    targets, conditions = _comment(text, "adapterAbortConditions")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::adapter",
        "scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqTerminateAdapterOnException",
        "gapROS2AndSCOREInOneProcessUnproven",
        "asmOneROS2EnvironmentOnHost",
    ]
    for setting in ("RMW_IMPLEMENTATION=rmw_cyclonedds_cpp", "ROS_DOMAIN_ID", "CYCLONEDDS_URI",
                    "MaxAutoParticipantIndex to at least the number of ROS 2 processes",
                    "At most MaxAutoParticipantIndex processes get a participant, 9 by default",
                    "ROS_LOCALHOST_ONLY stays unset",
                    "start_parameter_services set to false", "triggers each throw with a signal to the adapter",
                    "No robustness against malformed DDS input is claimed"):
        assert setting in conditions, setting
    # A loopback binding alone keeps no DDS port off the guest network (owner decision of 2026-10-28, REQ-MW-016).
    for statement in ("That alone does not keep the DDS ports off the guest network: CycloneDDS 0.10.5 binds its "
                      "receive sockets to INADDR_ANY (ddsi_udp.c:453-456, 479-480). So the host must also keep these "
                      "ports off the guest network, as REQ-MW-016 asks (someipd).",
                      "Only while the host keeps the DDS ports off the guest network (REQ-MW-016) are the senders "
                      "processes on the host."):
        assert statement in conditions, statement
    for overclaim in ("and so keeps DDS off the guest network", "DDS on the loopback interface limits the senders"):
        assert overclaim not in conditions, overclaim
    assert re.search(r"\bpart <'ASM-MW-031'> asmOneROS2EnvironmentOnHost : IncrementAssumption \{", text)


def test_asm_mw_031_names_one_distribution_and_depends_on_the_three_context_processes() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    assumption = _part_doc(text, "ASM-MW-031")
    assert "one ROS 2 distribution (Humble)" in assumption
    assert assumption.endswith("Phase 10 records the environment of each ROS 2 process of a run, "
                               "the observers of the bench among them."), assumption[-160:]
    assert "the observers of the bench, and" not in assumption, "the bench observers are not member processes"
    dependencies = re.findall(r"\bdependency (\w+)\s+from asmOneROS2EnvironmentOnHost\s+to ([\w:]+);", text)
    assert dependencies == [
        ("ros2EnvironmentAssumedForAEBSStack", "scoreTwoDomainPhysicalSystem::linuxHost::aebsStack"),
        ("ros2EnvironmentAssumedForVelocityConverter", "scoreTwoDomainPhysicalSystem::linuxHost::velocityConverter"),
        ("ros2EnvironmentAssumedForFrameAssembler",
         "scoreTwoDomainPhysicalSystem::linuxHost::aebsSignalFrameAssembler"),
    ], dependencies


def test_the_adapter_declares_the_fault_injection_interface_that_the_abort_test_uses() -> None:
    doc = _adapter_doc(PHYSICAL.read_text(encoding="utf-8"))
    for statement in ("Fault-injection interface of the realization, for the test of REQ-MW-018",
                      "in every start configuration, the adapter takes three real-time signals",
                      "SIGRTMIN+1 makes a throw inside librclcpp.so", "SIGRTMIN+2 makes a throw in adapter code",
                      "SIGRTMIN+3 makes std::vector::at throw inside the shared libstdc++",
                      "Such a signal aborts the adapter outside the test too",
                      "nothing beyond what a kill already does"):
        assert statement in doc, statement
    case = _verification_def_doc("AdapterAbortOnExceptionVerification")
    assert "through the fault-injection interface of the adapter (phase 8)" in case, case[:400]


def test_vc_mw_020_does_not_close_req_mw_019_while_the_stored_frame_gap_is_open() -> None:
    """The criteria of REQ-MW-019 declare the margin, so only the stored-frame gap holds a pass back. The case runs
    the pair restart, so the closure names the two host-half events that it leaves to the preflight checks."""
    case = _verification_def_doc("UnsubscribedFrameDiscardVerification")
    assert case.endswith("While GAP-MW-039 is open for a restart of gatewayd alone and for a late start of gatewayd, "
                         "a pass does not close REQ-MW-019."), case[-200:]
    assert "GAP-MW-045 is open" not in case, "the declared margin no longer holds a pass back"


def test_vc_mw_020_checks_the_margin_and_the_condition_of_asm_mw_030() -> None:
    """VC-MW-020 checks the criteria of REQ-MW-019: the bound of ASM-MW-030 as the margin, on the two clocks."""
    case = _verification_def_doc("UnsubscribedFrameDiscardVerification")
    for statement in ("processData checks each frame that arrives after the new subscription. The AEBS stack must "
                      "not have produced it more than the bound of ASM-MW-030 before the new subscription.",
                      "processData takes the production time from the frame timestamp, on the host clock. It takes "
                      "the start of the new subscription from the guest clock.",
                      "If ASM-MW-030 does not hold in the run, the run does not show the criteria met. In that case, "
                      "the outcome is inconclusiveMissingEvidence.",
                      "It records the times of the stop and of the new subscription, and the offset between the host "
                      "clock and the guest clock."):
        assert statement in case, statement
    assert "from the time without a subscription" not in case, "the literal criteria of REQ-MW-019 are gone"


def test_gap_mw_045_records_that_the_criteria_of_req_mw_019_declare_the_margin() -> None:
    """The gap leads with what stays open; the band itself now meets the criteria while ASM-MW-030 holds."""
    gap = _part_doc(PHYSICAL.read_text(encoding="utf-8"), "GAP-MW-045")
    assert gap.startswith("Open: the member has no time synchronization between the Linux host and the AAOS SDV "
                          "guest. So ASM-MW-030 holds only where the bench keeps the clocks together and measures "
                          "them, and the band below rests on it."), gap[:200]
    assert gap.count("Open:") == 1, "one open item, stated first"
    assert ("The success criteria of REQ-MW-019 declare this margin as the bound of ASM-MW-030 (owner decision of "
            "2026-10-28). So such a frame meets them while ASM-MW-030 holds.") in gap
    assert "does not meet the success criteria" not in gap, gap


def test_the_host_isolation_is_an_obligation_with_an_open_gap() -> None:
    """The DDS ports and port 4721 must be kept off the guest network; the bench does not do it yet (GAP-MW-046)."""
    text = PHYSICAL.read_text(encoding="utf-8")
    someipd = _named_part_doc(text, "someipd")
    assert ("if the host also keeps the DDS ports of the adapter and the health proxy node off the guest network, as "
            "it must keep port 4721 of the frame assembler (ASM-MW-029).") in someipd, someipd
    assert ("The bench does not have the configuration that keeps these ports off the guest network yet "
            "(GAP-MW-046).") in someipd, someipd
    assert "(DDS) traffic" not in someipd, "the isolation is about ports"
    (assembler,) = (_flat(doc) for doc in re.findall(r"\bpart aebsSignalFrameAssembler \{\s*doc /\*(.*?)\*/", text,
                                                       re.DOTALL))
    assert "so the host must keep the guest network off that port (ASM-MW-029)." in assembler, assembler
    assert "so the host keeps the guest network off that port" not in assembler, assembler
    assumption = _part_doc(text, "ASM-MW-029")
    for statement in ("The frame assembler binds 0.0.0.0 (de4sdv_aebs_010_bridge/ros_node.py:34-35), so port 4721 "
                      "is open on every address of the host.",
                      "So the host must keep the guest network off port 4721.",
                      "The reachability probe of the case that verifies REQ-MW-016 records whether a guest domain "
                      "reaches it. The bench does not keep it off yet (GAP-MW-046)."):
        assert statement in assumption, statement
    gap = _part_doc(text, "GAP-MW-046")
    assert gap.startswith("Open: the host configuration that keeps each guest domain of the layer off the DDS ports "
                          "of the host and off port 4721 of the frame assembler is not authored."), gap[:200]
    assert ("The loopback binding of the ROS 2 environment does not close this gap: CycloneDDS 0.10.5 binds its "
            "receive sockets to INADDR_ANY (ddsi_udp.c:453-456, 479-480).") in gap, gap
    assert re.search(r"\bpart <'GAP-MW-046'> gapHostPortIsolationNotAuthored : IncrementGap \{", text)
    assert re.findall(r"\bdependency (\w+)\s+from gapHostPortIsolationNotAuthored to ([\w:]+);", text) == [
        ("hostPortIsolationGapOnLinuxHost", "scoreTwoDomainPhysicalSystem::linuxHost")]
    (action,) = re.findall(r'attribute :>> nextAction = "phase 10, in this order: ([^"]*)";', text)
    last = ("(11) author the host configuration of GAP-MW-046, written by interface, that makes the DDS ports of "
            "every host ROS 2 process, and port 4721, unreachable from each guest domain (a host firewall on the "
            "bench), and run the reachability probe of the case that verifies REQ-MW-016 from each VM, over each of "
            "its interfaces (eth1, buried_eth0, the VLAN interfaces, wlan if present), to each address of the host "
            "(192.168.98.1, the host end of the buried network of each VM, any other cvd-* bridge address) "
            "(ASM-MW-029, GAP-MW-046)")
    assert action.endswith(last), action[-300:]
    assert re.findall(r"\((\d+)\) ", action) == [str(step) for step in range(1, 12)], "the steps are numbered in order"
    # The steps that the technical review asked for (R3, R4 and items 4 and 6 of its list S1).
    for step in ("(2) set up the SD network of the host: the unicast address 192.168.98.1/24 of someipd on the "
                 "bridge cvd-ebr, a route for the SD group on cvd-ebr",
                 "with the remote endpoint of the frame service pinned to 192.168.98.1, so that an SD message from "
                 "the IVI VM cannot redirect the subscription",
                 "(5) provision the relay for the IVI VM:",
                 "install exactly one ACL file for the relay's subject before the IVI VM boots",
                 "(7) check on the host with ss -H -t -n -p state established '( sport = :4721 )'",
                 "and record every phase end of the relay"):
        assert step in action, step
    assert ("the frame assembler binds 0.0.0.0:4721 (de4sdv_aebs_010_bridge/ros_node.py:34-35), and the adapter "
            "connects to 127.0.0.1:4721 on the host loopback") in text
    assert "on the host loopback, 127.0.0.1:4721 (de4sdv_aebs_010_bridge/ros_node.py:34-35)" not in text, "citation"
    assert ("GAP-MW-043, GAP-MW-045, GAP-MW-046, GAP-MW-047, GAP-MW-048; ASM-MW-032; design data only from the "
            "feasibility runs of 2026-10-28 (GAP-MW-038)\";") in text, (
        "the frame mapping record lists the isolation gap, the version skew, the restart gap and the AAOS SDV path "
        "assumption")
    # The host configuration is written by interface (technical review R1), and the SOME/IP rule is hardening
    # bound to the bridge port of the SDV Core VM (technical review R2); the owner decided both on 2026-10-29.
    for statement in ("Host configuration (owner decision of 2026-10-29): rules by interface, not by source "
                      "address.",
                      "drops UDP 30150-30151 and 30160-30401, and TCP 4721, on every interface except lo.",
                      "the bench's ROS_DOMAIN_ID 91 with MaxAutoParticipantIndex 120",
                      "The reachability probe runs from each VM, over each of its interfaces (eth1, buried_eth0, the "
                      "VLAN interfaces, and wlan if present), to each address of the host (192.168.98.1, the host end "
                      "of the buried network of each VM, and any other cvd-* bridge address).",
                      "The IVI VM can reach the SOME/IP ports of someipd: one routing rule in the guest is enough, so "
                      "the host must not rely on the routing of the guest.",
                      "Hardening (owner decision of 2026-10-29), for REQ-MW-019 and REQ-MW-015, not for "
                      "REQ-MW-016:",
                      "accepts UDP 30490 and TCP 30509 to the host only from that bridge port. It also matches ip "
                      "saddr 192.168.98.3 and the MAC address of that VM.",
                      "a static neighbour entry pins that MAC address"):
        assert statement in gap, statement
    assert "admits SOME/IP to someipd from the SDV Core VM only" not in gap, "the IP-only rule is replaced"


def test_someipd_names_the_assumption_that_the_dds_criteria_of_req_mw_016_need() -> None:
    """REQ-MW-016 also covers the host's ROS 2 processes outside the layer; ASM-MW-031 assumes their environment."""
    doc = _named_part_doc(PHYSICAL.read_text(encoding="utf-8"), "someipd")
    assert ("While ASM-MW-031 holds, the criteria of REQ-MW-016 also cover the ROS 2 processes of the host outside "
            "the layer. ASM-MW-031 assumes that they run in the ROS 2 environment of "
            "adapterAbortConditions.") in doc, doc


def _braced(text: str, header: str) -> str:
    """The text of the one braced body after the regex ``header``, which ends with its opening brace."""
    matches = list(re.finditer(header, text))
    assert len(matches) == 1, f"expected one {header!r}, found {len(matches)}"
    start = matches[0].end() - 1
    depth = 0
    for end in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[end], 0)
        if depth == 0:
            return text[start:end + 1]
    raise AssertionError(f"{header!r} has an unbalanced body")


def _code(text: str) -> str:
    """``text`` with block and line comments blanked, so declarations are matched in code only."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.DOTALL)


def test_the_layer_refers_to_the_aaos_sdv_elements_and_owns_the_relay() -> None:
    """ADR 0025, decision 6: the layer refers to the SDV Core and the SDV Gateway on IVI, and owns the relay."""
    layer = " ".join(_code(_braced(PHYSICAL.read_text(encoding="utf-8"),
                                   r"\bpart def SCOREMiddlewareIntegrationLayerRealization\b[^{;]*\{")).split())
    for declaration in ("ref part sdvCore : SDVCoreBoundary {", "ref part sdvGateway : SDVGatewayOnIVIBoundary {",
                        "part iviFrameRelay : PhysicalAllocationElement {"):
        assert declaration in layer, declaration
    assert not re.search(r"(?<!ref )\bpart (?:sdvCore|sdvGateway)\b", layer), "the AAOS SDV elements are references"
    assert len(re.findall(r"\bconnect\b", layer)) == 7, "a further connection in the layer"
    assert re.findall(r"\bconnection (\w+) connect ([\w.]+) to ([\w.]+);", layer) == [
        ("speedTopicToHealthProxy", "adapter.middlewareVelocityStatusOut", "healthProxyNode.middlewareVelocityStatusIn"),
        ("frameEventOverSCORECommunication", "adapter.aebsSignalFrameOut", "scoreServices.gatewayd.aebsSignalFrameIn"),
        ("frameEventOverGatewayIPC", "scoreServices.gatewayd.aebsSignalFrameOut",
         "scoreServices.someipd.aebsSignalFrameIn"),
        ("frameEventOverSOMEIPAcrossHypervisor", "scoreServices.someipd.aebsSignalFrameOut", "sdvCore.someIp.someIpPort"),
        ("frameTopicPublishedByBroker", "sdvCore.someIp.topicPublishOut", "sdvCore.dataTunnel.topicPublishPort"),
        ("frameTopicOverDataTunnelAcrossVMs", "sdvCore.dataTunnel.topicSubscribePort", "sdvGateway.dataTunnelPort"),
        ("frameTopicThroughSDVGatewayToRelay", "sdvGateway.clientPort", "iviFrameRelay.frameTopicIn"),
    ]


def test_the_physical_context_has_two_vms_and_binds_the_aaos_sdv_references() -> None:
    """One side, two VMs, three operating-system instances (ADR 0025); five bindings, one owner each."""
    context = _braced(PHYSICAL.read_text(encoding="utf-8"), r"\bpart def SCORETwoDomainPhysicalSystem\s*\{")
    core = " ".join(_code(_braced(context, r"\bpart sdvCoreGuest\s*\{")).split())
    ivi = " ".join(_code(_braced(context, r"\bpart hmiGuest\s*\{")).split())
    for declaration in ("part os : AndroidHLOS;", "part sdvMiddleware : AndroidSDVMiddleware;"):
        assert declaration in core and declaration in ivi, declaration
    assert "part sdvGateway : SDVGatewayOnIVIBoundary {" in ivi
    assert "SDVGatewayOnIVIBoundary" not in core and "SDVCoreBoundary" not in core + ivi, "one owner per element"
    own = " ".join(_code(context).split())
    assert len(re.findall(r"\bbind\b", own)) == 5, "a further binding in the physical context"
    assert re.findall(r"\bbinding (\w+) bind ([\w.]+) = ([\w.]+);", own) == [
        ("scoreServicesBoundToLinuxHost", "integrationLayer.scoreServices", "linuxHost.scoreServices"),
        ("adapterBoundToLinuxHost", "integrationLayer.adapter", "linuxHost.adapter"),
        ("sdvCoreBoundToSDVCoreVM", "integrationLayer.sdvCore", "sdvCoreGuest.sdvMiddleware"),
        ("platformSoftwareBoundToSDVCoreVM", "integrationLayer.sdvCore.platformSoftware", "sdvCoreGuest.os"),
        ("sdvGatewayBoundToIVIVM", "integrationLayer.sdvGateway", "hmiGuest.sdvGateway"),
    ]
    assert re.findall(r"\binterface (\w+) : OSHypervisorInterface connect ([\w.]+) to ([\w.]+);", own) == [
        ("sdvCoreGuestUnderKVM", "sdvCoreGuest.os.hypervisorPort", "linuxHost.hypervisor.guestPort"),
        ("hmiGuestUnderKVM", "hmiGuest.os.hypervisorPort", "linuxHost.hypervisor.guestPort"),
    ]
    assert ("connection framesToHMIOverGuestLoopback connect integrationLayer.iviFrameRelay.aebsSignalFrameOut to "
            "hmiGuest.hmiApplication.aebsSignalFrameIn;") in own


def test_the_parked_receiver_is_out_of_the_model() -> None:
    """ADR 0025, decision 7: the SOME/IP receiver leaves the product path; the relay keeps its discard core."""
    for path in sorted(MIDDLEWARE.glob("*.sysml")):
        code = _code(path.read_text(encoding="utf-8"))
        for name in ("someipReceiver", "receiverSubscriptionPhaseDiscardRule", "hmiFrameRelayToSomeipReceiver"):
            assert name not in code, (path.name, name)
    text = PHYSICAL.read_text(encoding="utf-8")
    assert re.search(r"\ballocation hmiFrameRelayToIviFrameRelay allocate "
                     r"DE4SDV_MiddlewareSCORELogicalArchitecture::hmiFrameRelay to "
                     r"scoreTwoDomainPhysicalSystem::integrationLayer::iviFrameRelay;", text)


def test_the_claim_boundary_is_stated_in_the_layer_and_in_gap_mw_038() -> None:
    """ADR 0025, decision 9: a non-production reference sample, no endorsement, no conformance claim."""
    text = PHYSICAL.read_text(encoding="utf-8")
    layer = _flat(re.search(r"\bpart def SCOREMiddlewareIntegrationLayerRealization\b[^{;]*\{\s*doc /\*(.*?)\*/",
                            text, re.DOTALL)[1])
    for statement in ("Unless the fallback of ADR 0025, decision 4, applies, the member uses Google's reference "
                      "stack, a non-production reference sample.",
                      "Google has not confirmed or endorsed this chain.",
                      "No SOME/IP conformance or AAOS SDV compatibility claim is made."):
        assert statement in layer, statement
    gap = _part_doc(text, "GAP-MW-038")
    assert ("Claim boundary: Google's reference stack is a non-production reference sample. This member uses it as "
            "AAOS SDV deploys it, in the SDV Core VM. No SOME/IP conformance or AAOS SDV compatibility claim is "
            "made.") in gap, gap


def test_gap_mw_038_carries_the_corrected_premise() -> None:
    """AOSP ships vsomeip with Boost under Soong, so the Boost port applies only to upstream vsomeip."""
    gap = _part_doc(PHYSICAL.read_text(encoding="utf-8"), "GAP-MW-038")
    assert gap.startswith("DE4SDV has no evidence of record of the AAOS SDV SOME/IP path of this member "
                          "(ADR 0025)."), gap[:120]
    for statement in ("AOSP android17-release ships vsomeip 3.1.37.1 with Boost 1.76.0 in external/sdv/vsomeip, "
                      "built with Soong. So an in-tree consumer needs no Boost port.",
                      "applies only to upstream vsomeip, not to this copy.",
                      "Design data, not evidence of record: unreviewed DE4SDV feasibility runs on the bench VM "
                      "(2026-10-28) ran the whole chain.",
                      "Both VMs must use the same boot mode: a mismatch failed at the handshake.",
                      "The host bridge passed the tagged frames",
                      "Google's documentation states that cross-VM communication is denied by default. The bench "
                      "used the allow-all VM-level policy of the sample targets, and a subject without a "
                      "service-level ACL was denied.",
                      # The AOSP citations are pinned once (form review R5).
                      "The AOSP citations of this slice refer to the android17-release tree of manifest ad156f32 "
                      "(platform/manifest), with these project commits: some_ip 27bff3fe, sdv_gateway c918480a, "
                      "middleware 7ab87b58 and samples e8cc5f41 of platform/system/software_defined_vehicle; "
                      "device/google/sdv f4bfa128; platform/external/sdv/vsomeip 906331c2; platform/system/core "
                      "545d2487.",
                      "In the UNLOCKED mode of the bench, the SD mesh and Data Tunnel run as cleartext HTTP/2.",
                      "exactly one ACL file for its subject on the IVI side, before the IVI VM boots",
                      "It needs a rebuilt SDV Core image",
                      "Still open: evidence of record, the build of the relay and its start as a native init service",
                      "This is design data, not evidence of record."):
        assert statement in gap, statement
    assert "It would need Boost 1.75 or later" not in gap, "the premise of a Boost port is corrected"


def test_gap_mw_047_records_the_version_skew_and_the_fallback() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    assert re.search(r"\bpart <'GAP-MW-047'> gapReferenceStackVsomeipSkewUntested : IncrementGap \{", text)
    holders = [path.name for path in SCORE_SLICES if "<'GAP-MW-047'>" in path.read_text(encoding="utf-8")]
    assert holders == [PHYSICAL.name], holders
    gap = _part_doc(text, "GAP-MW-047")
    for statement in ("links the vsomeip 3.1.37.1 of AOSP", "vsomeip 3.6.1",
                      "The stack sent the subscription with an IPv4 endpoint option for TCP",
                      "showed that the two interoperate on this path",
                      "With multicast blocked, the stack used no unicast SD.",
                      "the fallback of ADR 0025, decision 4, applies"):
        assert statement in gap, statement
    assert re.findall(r"\bdependency (\w+)\s+from gapReferenceStackVsomeipSkewUntested to ([\w:]+);", text) == [
        ("referenceStackSkewGapOnSDVCoreVM", "scoreTwoDomainPhysicalSystem::sdvCoreGuest")]


def test_asm_mw_032_assumes_order_and_bytes_on_the_aaos_sdv_hops() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    assert re.search(r"\bpart <'ASM-MW-032'> asmAAOSSDVPathKeepsOrderAndBytes : IncrementAssumption \{", text)
    assumption = _part_doc(text, "ASM-MW-032")
    assert "REQ-MW-014 and REQ-MW-015 rely on this on the AAOS SDV hops." in assumption
    assert "check this assumption end to end" in assumption
    assert re.findall(r"\bdependency (\w+)\s+from asmAAOSSDVPathKeepsOrderAndBytes\s+to ([\w:]+);", text) == [
        ("aaosSdvPathAssumedForSDVCore", "scoreTwoDomainPhysicalSystem::integrationLayer::sdvCore"),
        ("aaosSdvPathAssumedForSDVGateway", "scoreTwoDomainPhysicalSystem::integrationLayer::sdvGateway"),
    ]


def test_gap_mw_048_records_that_nothing_restarts_the_broker_and_its_stack() -> None:
    """The broker and the stack are oneshot; the bench recovery is an owner decision, the ways out are later ones."""
    text = PHYSICAL.read_text(encoding="utf-8")
    assert re.search(r"\bpart <'GAP-MW-048'> gapSOMEIPBrokerAndStackNotRestarted : IncrementGap \{", text)
    holders = [path.name for path in SCORE_SLICES if "<'GAP-MW-048'>" in path.read_text(encoding="utf-8")]
    assert holders == [PHYSICAL.name], holders
    gap = _part_doc(text, "GAP-MW-048")
    assert gap.startswith("Open: nothing restarts the SOME/IP broker or its stack in the SDV Core VM."), gap[:100]
    for statement in ('"Critical agent has died"', "all_service_bundles_alive as false within about 90 ms",
                      # The two deaths, each on its own (claims review R2).
                      "showed two different deaths:",
                      "A start of the stack alone gave no message. A restart of the broker after it gave the frames "
                      "again, and so did a reboot of the SDV Core VM;",
                      "A start of the broker alone gave no publication. The frames came back after a toggle of the "
                      "service availability on the host",
                      "A reboot of the SDV Core VM was not tried after this death.",
                      # Detection, the launch configuration and the preferred recovery (technical review R7).
                      "Detection: for either death, the logcat of the SDV Core VM shows",
                      "So the reboot keeps the launch configuration",
                      "it gives no burst of GAP-MW-039, and one procedure covers both deaths.",
                      "Bench recovery (owner decision of 2026-10-29): a manual recovery by the operator, for the bench "
                      "only.",
                      "No availability claim is made. Phase 10 measures how long the HMI shows stale",
                      "A failure of the SD agent or of sdv_gateway in the IVI VM needs a reboot of the IVI VM",
                      "it needs a new clock setting (ASM-MW-030)",
                      "Ways out, each a later decision:",
                      "so it needs a test after a death of the broker first;",
                      "it needs a requirement of its own."):
        assert statement in gap, statement
    assert re.findall(r"\bdependency (\w+)\s+from gapSOMEIPBrokerAndStackNotRestarted to ([\w:]+);", text) == [
        ("brokerRestartGapOnSDVCoreVM", "scoreTwoDomainPhysicalSystem::sdvCoreGuest")]


def test_the_owner_decisions_of_2026_10_29_replace_the_proposals() -> None:
    """The owner decided the relay's subscription, the host rules and the bench recovery; no proposal is left."""
    text = PHYSICAL.read_text(encoding="utf-8")
    assert "(proposed; the owner decides)" not in _flat(text), "a proposal marker is left"
    assert "Subscription (owner decision of 2026-10-29):" in _named_part_doc(text, "iviFrameRelay")
    gap = _part_doc(text, "GAP-MW-046")
    assert "Host configuration (owner decision of 2026-10-29): rules by interface" in gap, gap
    assert "Hardening (owner decision of 2026-10-29), for REQ-MW-019 and REQ-MW-015" in gap, gap
    assert "Bench recovery (owner decision of 2026-10-29):" in _part_doc(text, "GAP-MW-048")


def _design_data_carriers(text: str) -> list[str]:
    """The flattened /* */ blocks that name a run on the bench VM of 2026-10-28."""
    blocks = (_flat(block) for block in re.findall(r"/\*(.*?)\*/", text, re.DOTALL))
    return [block for block in blocks if re.search(r"\bbench VM\b.{0,40}\(2026-10-28\)", block)]


def test_the_feasibility_facts_are_dated_design_data() -> None:
    """Each block that reports a run on the bench VM of 2026-10-28 labels it design data, never evidence.

    A scan, not a hand list: every /* */ block whose text names such a run must carry the label and no word of
    acceptance (form review R1)."""
    carriers = _design_data_carriers(PHYSICAL.read_text(encoding="utf-8"))
    assert len(carriers) >= 11, len(carriers)
    for block in carriers:
        assert "design data, not evidence of record" in block.lower(), block[:160]
        for word in (r"\bverified\b", r"\bproven\b", r"\bcertified\b", r"\bcompliant\b"):
            assert not re.search(word, block, re.IGNORECASE), (word, block[:160])


def test_the_design_data_scan_finds_an_unlabelled_or_overclaimed_carrier() -> None:
    """Negative cases on synthetic text: a carrier without the label, and one with a word of acceptance."""
    unlabelled = "/* An unreviewed DE4SDV feasibility run on the bench VM (2026-10-28) saw it. */"
    overclaimed = ("/* Design data, not evidence of record: a run on the bench VM (2026-10-28) verified the "
                   "chain. */")
    (block,) = _design_data_carriers(unlabelled)
    assert "design data, not evidence of record" not in block.lower()
    (block,) = _design_data_carriers(overclaimed)
    assert re.search(r"\bverified\b", block)
    assert _design_data_carriers("/* A run on another VM (2026-10-28). */") == []
