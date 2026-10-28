"""INC-MW-011 phase 8: the gateway pin, the receiver's discard rule and the adapter's abort conditions.

ASM-MW-021 binds every S-CORE statement of the increment to its pins. The other
slices name the same gateway and lifecycle commits, and the bench that builds
the layer builds those commits too. The SOME/IP receiver discards the frames that
the AEBS stack produced before the HMI application's subscription phase
(REQ-MW-019), with the clock bound of ASM-MW-030 and the residual band of
GAP-MW-045; the receiver's code uses the same margin and copy window. The
criteria of REQ-MW-019 declare that margin as the bound of ASM-MW-030, and
VC-MW-020 checks it. The one-process adapter of REQ-MW-018 has two conditions:
one ROS 2 environment on the host (ASM-MW-031 for the processes outside the
layer) and no ROS 2 parameter services. Its fault-injection interface is the
trigger of the abort test. someipd names ASM-MW-031 for the DDS criteria of
REQ-MW-016.

These are lexical source guards; licensed Syside validates the model in CI. The
pins live in doc comments, so these tests read the docs on purpose. They check
consistency, not existence. The pin check skips only while the bench is absent and
no workflow declares the pins. The receiver check reads only the files that git
tracks, so ignored build output, bags and workspaces never count. It skips while
no tracked non-Markdown file under implementation/ or .github/ names the
receiver's service (de4sdv_someip_receiver) or its margin constant
(kPhaseStartMarginNs), and outside a git checkout. Once one does, the receiver's
headers and its init file, the one with a `service de4sdv_someip_receiver` line,
must carry the model's margin and copy window.
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
#: The SOME/IP receiver shows by its service name or by its margin constant, in the realization or in CI.
RECEIVER_SERVICE = "de4sdv_someip_receiver"
RECEIVER_MARKERS = (RECEIVER_SERVICE, "kPhaseStartMarginNs")
#: The pathspecs of the marker and header scans.
MARKER_PATHSPECS = ("implementation", ".github")
#: The receiver's init file declares its service on a line of its own; a comment does not count.
_RECEIVER_SERVICE_LINE = re.compile(rf"^\s*service\s+{RECEIVER_SERVICE}\b", re.M)
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


def _receiver_marker_files(tracked: list[Path]) -> list[str]:
    """The tracked non-Markdown files that name the receiver's service or its margin constant.

    Markdown is left out, so a README may name the service before the code lands.
    """
    markers = tuple(marker.encode() for marker in RECEIVER_MARKERS)
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


def test_the_receiver_discard_rule_traces_its_requirements_bound_and_residual() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    targets, rule = _comment(text, "receiverSubscriptionPhaseDiscardRule")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver",
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
    assert _numbers(r"The margin is fixed at (\d+) ms\. No option sets it, and the receiver stops at start on any "
                    r"margin option", rule) == [margin]
    (bound,) = _numbers(r"differ by less than (\d+) ms", _part_doc(text, "ASM-MW-030"))
    (band_margin,) = _numbers(r"it puts its (\d+) ms margin before the start", _part_doc(text, "GAP-MW-045"))
    assert margin == bound == band_margin, (margin, bound, band_margin)
    for statement in ("SubscribeEventgroupAck", "accepts it as the only client", "a reboot of someipd",
                      "a loss of the SOME/IP framing of the TCP stream", "The receiver sets no TCP keepalive",
                      "a link loss that lasts longer than the TTL",
                      "only if it no longer holds the TCP connection",
                      "It is no copy of a frame that the receiver served in this phase",
                      "it clears them at each phase start",
                      "the rule drops no frame that the AEBS stack produced after the phase start"):
        assert statement in rule, statement


def test_asm_mw_030_holds_the_clock_bound_with_session_controls() -> None:
    """The offset is measured two-way and gates the session; steps of both clocks are logged."""
    assumption = _part_doc(PHYSICAL.read_text(encoding="utf-8"), "ASM-MW-030")
    (bound,) = _numbers(r"differ by less than (\d+) ms", assumption)
    assert _numbers(r"No case starts before the start capture gives an offset below (\d+) ms", assumption) == [bound]
    for control in ("by a two-way time exchange with the chrony of the host",
                    "A setting through adb is not used",
                    "This two-way capture measures the offset.",
                    "the host logs each step of its clock",
                    "That minimum bounds the offset from one side only"):
        assert control in assumption, control


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
    _, rule = _comment(text, "receiverSubscriptionPhaseDiscardRule")
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


def test_the_receiver_code_uses_the_margin_and_the_copy_window_of_the_model() -> None:
    """Once a tracked file names the SOME/IP receiver, its code and its init file carry the model's margin and window.

    The check holds the realization to the model; it does not need the receiver to exist. It reads only the files
    that git tracks. It skips only while no tracked non-Markdown file under implementation/ or .github/ names the
    receiver's service or its margin constant, so a silent skip needs both names gone from all of them. Outside a
    git checkout it skips, because it cannot tell tracked files from build output there.
    """
    tracked = _tracked(*MARKER_PATHSPECS)
    init_files = _tracked("*.rc")
    if tracked is None or init_files is None:
        pytest.skip("not a git checkout: the receiver check reads only the files that git tracks")
    found = _receiver_marker_files(tracked)
    if not found:
        pytest.skip("no file under implementation/ or .github/ names the SOME/IP receiver (tracked, non-Markdown)")
    _, rule = _comment(PHYSICAL.read_text(encoding="utf-8"), "receiverSubscriptionPhaseDiscardRule")
    (margin,) = _numbers(r"not earlier than the phase start less (\d+) ms", rule)
    (window,) = _numbers(r"of the last (\d+) frames it served", rule)
    named = f"{found[0]} names the receiver"
    headers = [path for path in tracked if path.suffix == ".hpp" and path.is_relative_to(IMPLEMENTATION)]
    code = "\n".join(path.read_text(encoding="utf-8") for path in headers)
    margins = [int(value.replace("'", "")) for value in re.findall(r"\bkPhaseStartMarginNs\s*=\s*([0-9']+)", code)]
    windows = [int(value) for value in re.findall(r"\bkCopyMemoryFrames\s*=\s*(\d+)", code)]
    assert margins, f"{named}, but no header under implementation/ defines kPhaseStartMarginNs"
    assert margins == [margin * 1_000_000], f"the receiver's margin is {margins} ns, the model's {margin} ms"
    assert windows == [window], f"the receiver keeps {windows} frames, the model {window}"
    # The ingress of INC-AEBS-010 has an init file too, so the receiver's own one must declare its service.
    receiver_init = [rc for rc in init_files if _RECEIVER_SERVICE_LINE.search(rc.read_text(encoding="utf-8"))]
    assert receiver_init, f"{named}, but no tracked init file (*.rc) declares the service {RECEIVER_SERVICE}"
    for rc in init_files:
        lines = [line for line in rc.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")]
        options = re.findall(r"--[\w-]*(?:margin|bound)[\w-]*", "\n".join(lines))
        assert not options, f"{rc.name} passes {options}; no option sets the margin, fixed at {margin} ms"


def test_the_receiver_repeats_the_ingress_trigger_only_until_its_first_client() -> None:
    doc = _named_part_doc(PHYSICAL.read_text(encoding="utf-8"), "someipReceiver")
    for statement in ("It does so at each of its own starts, once its loopback server listens.",
                      "So until the first client of the current receiver process connects, the receiver repeats "
                      "the trigger at a fixed interval, a fixed number of times at most.",
                      "After that first client, it never triggers the ingress again."):
        assert statement in doc, statement
    for removed in ("while no client is connected", "harmless"):
        assert removed not in doc, removed


def test_the_guest_side_guard_rail_names_the_clock_assumption() -> None:
    targets, _ = _comment(PHYSICAL.read_text(encoding="utf-8"), "guestStaleFrameDropGuardRail")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver",
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
    """The criteria of REQ-MW-019 declare the margin, so only the stored-frame gap holds a pass back."""
    case = _verification_def_doc("UnsubscribedFrameDiscardVerification")
    assert case.endswith("While GAP-MW-039 is open, a pass does not close REQ-MW-019."), case[-200:]
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


def test_someipd_names_the_assumption_that_the_dds_criteria_of_req_mw_016_need() -> None:
    """REQ-MW-016 also covers the host's ROS 2 processes outside the layer; ASM-MW-031 assumes their environment."""
    doc = _named_part_doc(PHYSICAL.read_text(encoding="utf-8"), "someipd")
    assert ("While ASM-MW-031 holds, the criteria of REQ-MW-016 also cover the ROS 2 processes of the host outside "
            "the layer. ASM-MW-031 assumes that they run in the ROS 2 environment of "
            "adapterAbortConditions.") in doc, doc
