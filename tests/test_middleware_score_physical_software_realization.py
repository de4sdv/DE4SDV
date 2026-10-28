"""INC-MW-011 phase 8: the gateway pin, the receiver's discard rule and the adapter's abort conditions.

ASM-MW-021 binds every S-CORE statement of the increment to its pins. The other
slices name the same gateway commit, and the bench that builds the layer builds
that commit too. The SOME/IP receiver discards the frames that the AEBS stack
produced before the HMI application's subscription phase (REQ-MW-019), with the
clock bound of ASM-MW-030 and the residual band of GAP-MW-045. The one-process
adapter of REQ-MW-018 has two conditions: one ROS 2 environment on the host and
no ROS 2 parameter services.

These are lexical source guards; licensed Syside validates the model in CI. The
pins live in doc comments, so these tests read the docs on purpose.
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
#: The workflow of the S-CORE reference interop bench, when it is on the revision.
BENCH_WORKFLOW = ROOT / ".github" / "workflows" / "score-reference-interop-bench.yml"

_GATEWAY_PIN = re.compile(r"inc_someip_gateway at commit ([0-9a-f]{40})")
_LIFECYCLE_PIN = re.compile(r"lifecycle v0\.6\.1 \(commit ([0-9a-f]{40})\)")


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


def _workflow_pins(text: str) -> dict[str, str]:
    """The GATEWAY_SHA and LIFECYCLE_SHA values of a workflow's env block."""
    return dict(re.findall(r"^\s+(GATEWAY_SHA|LIFECYCLE_SHA):\s*([0-9a-f]{40})\s*$", text, re.M))


def test_asm_mw_021_pins_one_gateway_commit_with_its_module_versions() -> None:
    doc = _asm_mw_021()
    assert doc.startswith("ASM-MW-021:"), doc[:40]
    assert len(set(_GATEWAY_PIN.findall(doc))) == 1, "ASM-MW-021 names one gateway commit"
    assert len(_LIFECYCLE_PIN.findall(doc)) == 1, "ASM-MW-021 pins the lifecycle commit"
    assert "communication 0.5.0 with two patches of the gateway and baselibs 0.2.16 with one" in doc
    assert "0.2.15" not in doc, "ASM-MW-021 still names the baselibs of the earlier gateway pin"


def test_every_gateway_pin_of_the_s_core_slices_is_the_one_of_asm_mw_021() -> None:
    (pin,) = set(_GATEWAY_PIN.findall(_asm_mw_021()))
    found = {}
    for path in SCORE_SLICES:
        for commit in _GATEWAY_PIN.findall(_flat(path.read_text(encoding="utf-8"))):
            found.setdefault(commit, []).append(path.name)
    assert set(found) == {pin}, f"gateway pins other than ASM-MW-021's {pin}: {found}"
    assert len(found[pin]) >= 4, "phase 8 names the pin for the S-CORE services, gatewayd and the transport"


def test_the_workflow_pin_reader_reads_both_pins() -> None:
    text = ("env:\n  GATEWAY_REPO: https://example.invalid/gw.git\n"
            f"  GATEWAY_SHA: {'a' * 40}\n  LIFECYCLE_SHA: {'b' * 40}\n")
    assert _workflow_pins(text) == {"GATEWAY_SHA": "a" * 40, "LIFECYCLE_SHA": "b" * 40}


def test_the_bench_builds_the_commits_that_asm_mw_021_pins() -> None:
    """main never holds a bench pinned to one gateway commit and a model pinned to another."""
    if not BENCH_WORKFLOW.exists():
        pytest.skip("the S-CORE reference interop bench is not on this revision")
    doc = _asm_mw_021()
    (gateway,) = set(_GATEWAY_PIN.findall(doc))
    (lifecycle,) = _LIFECYCLE_PIN.findall(doc)
    assert _workflow_pins(BENCH_WORKFLOW.read_text(encoding="utf-8")) == {
        "GATEWAY_SHA": gateway, "LIFECYCLE_SHA": lifecycle}


def test_the_receiver_discard_rule_traces_its_requirements_bound_and_residual() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    targets, rule = _comment(text, "receiverSubscriptionPhaseDiscardRule")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::someipReceiver",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqDiscardFramesWhileHMIUnsubscribed",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqDeliverAEBSSignalsInSourceOrder",
        "gapLoLaReturnsStoredSamplesOnSubscription",
        "asmHostAndGuestClocksAgree",
        "gapPhaseStartDiscardBand",
    ]
    assert re.search(r"\bpart <'ASM-MW-030'> asmHostAndGuestClocksAgree : IncrementAssumption \{", text)
    assert re.search(r"\bpart <'GAP-MW-045'> gapPhaseStartDiscardBand : IncrementGap \{", text)
    (margin,) = re.findall(r"not earlier than the phase start less (\d+) ms, the bound of ASM-MW-030", rule)
    (bound,) = re.findall(r"differ by less than (\d+) ms", _part_doc(text, "ASM-MW-030"))
    (band_margin,) = re.findall(r"it puts its (\d+) ms margin before the start", _part_doc(text, "GAP-MW-045"))
    assert margin == bound == band_margin, (margin, bound, band_margin)
    for statement in ("SubscribeEventgroupAck", "accepts it as the only client",
                      "It is no copy of a frame that the receiver served in this phase",
                      "the rule drops no frame that the AEBS stack produced after the phase start"):
        assert statement in rule, statement


def test_the_adapter_abort_conditions_name_the_ros2_environment_and_the_parameter_services() -> None:
    text = PHYSICAL.read_text(encoding="utf-8")
    targets, conditions = _comment(text, "adapterAbortConditions")
    assert targets == [
        "scoreTwoDomainPhysicalSystem::integrationLayer::adapter",
        "scoreTwoDomainPhysicalSystem::integrationLayer::scoreServices::launchManager",
        "DE4SDV_MiddlewareSCORENeedsRequirements::reqTerminateAdapterOnException",
        "gapROS2AndSCOREInOneProcessUnproven",
    ]
    for setting in ("RMW_IMPLEMENTATION=rmw_cyclonedds_cpp", "ROS_DOMAIN_ID", "CYCLONEDDS_URI",
                    "MaxAutoParticipantIndex", "start_parameter_services set to false"):
        assert setting in conditions, setting
