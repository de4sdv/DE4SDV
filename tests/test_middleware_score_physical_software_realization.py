"""INC-MW-011 phase 8: the gateway pin, the receiver's discard rule and the adapter's abort conditions.

ASM-MW-021 binds every S-CORE statement of the increment to its pins. The other
slices name the same gateway and lifecycle commits, and the bench that builds
the layer builds those commits too. The SOME/IP receiver discards the frames that
the AEBS stack produced before the HMI application's subscription phase
(REQ-MW-019), with the clock bound of ASM-MW-030 and the residual band of
GAP-MW-045; the receiver's code uses the same margin and copy window. The
one-process adapter of REQ-MW-018 has two conditions: one ROS 2 environment on the
host (ASM-MW-031 for the processes outside the layer) and no ROS 2 parameter
services.

These are lexical source guards; licensed Syside validates the model in CI. The
pins live in doc comments, so these tests read the docs on purpose. The bench and
receiver checks skip only while the bench is not on the revision.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIDDLEWARE = ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
PHYSICAL = MIDDLEWARE / "middleware_score_physical_software_realization.sysml"
FRAMING = MIDDLEWARE / "middleware_score_framing.sysml"
#: The S-CORE slices of INC-MW-011.
SCORE_SLICES = sorted(MIDDLEWARE.glob("middleware_score_*.sysml"))
WORKFLOWS = ROOT / ".github" / "workflows"
#: The S-CORE reference interop bench and its SOME/IP receiver, when they are on the revision.
BENCH = ROOT / "implementation" / "score-reference-interop-bench"
RECEIVER = BENCH / "someip-receiver"
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
                      "It is no copy of a frame that the receiver served in this phase",
                      "it clears them at each phase start",
                      "the rule drops no frame that the AEBS stack produced after the phase start"):
        assert statement in rule, statement


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


def test_the_receiver_code_uses_the_margin_and_the_copy_window_of_the_model() -> None:
    if not RECEIVER.exists():
        pytest.skip("the SOME/IP receiver is not on this revision")
    _, rule = _comment(PHYSICAL.read_text(encoding="utf-8"), "receiverSubscriptionPhaseDiscardRule")
    (margin,) = _numbers(r"not earlier than the phase start less (\d+) ms", rule)
    (window,) = _numbers(r"of the last (\d+) frames it served", rule)
    code = "\n".join(path.read_text(encoding="utf-8") for path in sorted(RECEIVER.rglob("*.hpp")))
    margins = [int(value.replace("'", "")) for value in re.findall(r"\bkPhaseStartMarginNs\s*=\s*([0-9']+)", code)]
    windows = [int(value) for value in re.findall(r"\bkCopyMemoryFrames\s*=\s*(\d+)", code)]
    assert margins == [margin * 1_000_000], f"the receiver's margin is {margins} ns, the model's {margin} ms"
    assert windows == [window], f"the receiver keeps {windows} frames, the model {window}"
    for rc in sorted(RECEIVER.glob("*.rc")):
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
    assert re.search(r"\bpart <'ASM-MW-031'> asmOneROS2EnvironmentOnHost : IncrementAssumption \{", text)
