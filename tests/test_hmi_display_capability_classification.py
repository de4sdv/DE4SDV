"""Content pins for the HMI display capability classification (INC-HMI-001 phase 3), not semantic validation.

Phase 3 of INC-HMI-001 adds no characteristic that distinguishes member products, so the slice records nothing: a
header gives each content item of the display its reason, and one named comment about the framing's product-line gap
names the scope decisions that stay open. These tests pin that text whole, read every name it cites from the model
that declares it, and hold the guide's Phase 3 section to the model. They read the model text; they do not parse SysML.
"""

from pathlib import Path
import re

from sysml_shapes import strip_comments

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "textual-notation-of-model/packages/features"
HMI = FEATURES / "hmi"
FRAMING = HMI / "hmi_display_framing.sysml"
CONTEXT = HMI / "hmi_display_operational_context.sysml"
MODEL = HMI / "hmi_display_capability_classification.sysml"
FEATURE_MODEL = ROOT / "model-based-product-line-engineering/feature-models/sdv_product_line.sysml"
SCOPE = ROOT / "model-based-product-line-engineering/scoping/de4sdv_aebs_product_line_scope.sysml"
MIDDLEWARE = FEATURES / "middleware/middleware_score_feature_classification.sysml"
AEBS = FEATURES / "aebs/aebs_needs_requirements.sysml"
DRIVING = FEATURES / "driving/driver_assistance_capability_classification.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
PACKAGE = "DE4SDV_HmiDisplayCapabilityClassification"
FRAMING_PACKAGE = "DE4SDV_HmiDisplayFraming"
SCOPE_GAP = "gapHmiDisplayInProductLine"
COMMENT = "hmiDisplayContentScopeDecisions"
TITLE = "DE4SDV HMI display capability classification model slice. "

#: The product-line characteristic kinds of the method kernel. Phase 3 records the feature-model delta
#: only (increment-workflow rule 10), and this increment adds none: an empty delta records nothing.
CHARACTERISTIC_KINDS = (
    "ProductLineCharacteristic", "ProductLineFeatureCandidate", "DeferredProductLineScope",
    "CommonProductLineCapability",
)
#: the whole comment-stripped package body: the one named comment, and no declaration of any kind
BODY = f"comment {COMMENT} about {FRAMING_PACKAGE}::{SCOPE_GAP}"
#: a dated word: the slice states what holds, not when (one style with the E/E precedent)
DATED = re.compile(r"(?i)\b(?:already|still|yet|today|currently|settled?)\b")
#: the reading of an accepted ADR two ways, before and after its scope pull request: the scope holds ADR 0026
TWO_WAY = re.compile(r"(?i)scope pull request|takes? effect")

#: one sentence per item without a record, each with its reason, read flat from the header; {names} are read from
#: the models that declare them
HEADER_REASONS = (
    "INC-HMI-001, phase 3, adds no characteristic that distinguishes member products, so it records no feature "
    "candidate and no deferred scope.",
    "Core elements are common by default and get no record.",
    "The HMI display gets none: by ADR 0026, which the owner decided on 2026-11-13, it is common content of every "
    "member of the governed scope ({common}) and no selectable feature for members.",
    "In the feature model {display} is optional, so that configurations which are not members can leave it out "
    "(validity), and it corresponds to that common content (admission).",
    "Where the display runs gets none: each integration-mode alternative derives it as part of its execution-domain "
    "topology, the AAOS SDV guest of an integrated member or a Linux-side display on the standalone member (ADR 0026 "
    "decision 2).",
    "The guest itself is the feature candidate {guest} of the Eclipse S-CORE middleware increment, whose counterpart "
    "is both integrated alternatives by the owner's decision of 2026-11-21.",
    "The scene gets none: the owner decided on 2026-11-17 that it is the scene that VisionPilot builds from its own "
    "perception, so it comes with the vehicle application, and VisionPilot is a feature of the feature model "
    "({visionpilot}) that corresponds to the deferred driving-stack variability of the governed scope ({stack}).",
    "The display of this increment belongs to the VisionPilot configuration, which is not a member product.",
    "The vehicle speed on the display gets none: no member differs by it, and neither the feature model nor the "
    "governed scope holds a display of the speed.",
    "Its source is the vehicle, and its carrier goes to the architecture phases ({speed}).",
    "The collision warning on the display gets none: REQ-AEBS-002 asks every member product for a collision warning "
    "to the driver, and whether the display carries it belongs to the AEBS requirements and architecture, which ADR "
    "0026 leaves open.",
    "The warning as a sound gets none: neither the feature model nor the governed scope holds a warning mode, and no "
    "member differs by one; phase 3 of the driver-assistance increment identified the same.",
    "The indication that the warning is unavailable gets none: it rests on N-AEBS-008 and REQ-AEBS-013, the product "
    "line's need and requirement on the status of the AEBS, and how the display learns of it is open "
    "({availability}).",
    "Showing no element as current when it is not gets none: it is behavior, which phase 5 states as requirements "
    "and phase 6 as states ({currency}).",
    "Which renderer draws what gets none: it is a realization that phase 8 maps ({allocation}), which the owner "
    "decided on 2026-11-17 for this configuration; either renderer of this configuration needs the AAOS SDV guest, "
    "which follows the integration mode.",
    "The third VM of the guest gets none: the VM layout of a guest is realization content (ADR 0026, after ADR "
    "0025), and the gap leaves it to a decision outside this increment ({layout}).",
    "The outages of Android in the IVI VM get none: they are events inside the black box of the operational context, "
    "whose detection phases 6 to 8 decide ({outage}).",
    "The verdicts and the verification environment get none: they are System 2, which the governed scope keeps out "
    "of product variability ({system2}).",
    "The candidate application and the Eclipse S-CORE path, outside the boundary, get none: VisionPilot and Eclipse "
    "S-CORE are features of the feature model ({visionpilot}, {score}), and this increment changes no feature.",
    "Adaptive cruise control and lane-keep assist of the candidate get none: the feature model holds them as {acc} "
    "and {lka}, which the governed scope does not hold, and this increment does not judge them.",
    "The Linux-side display of the standalone member gets none: its place derives from the standalone integration "
    "mode, this increment leaves it out of its scope ({standalone_out}), and its design is open ({standalone}).",
    "The display in the headless guest of the AAOS-integrated member gets none: which VM of the guest holds it is "
    "realization content ({headless}).",
    "The owner decided on 2026-11-21 that this increment records these two gaps.",
    "The items that the framing puts out of scope get none: they are out-of-scope items of the framing.",
)
#: the opening of the comment on the product-line gap, and each of its items whole
SCOPE_INTRO = (
    "Phase 3 classifies the content of the HMI display against the governed scope as it stands and names the scope "
    "decisions that the lifecycle decision of this increment needs. This increment admits nothing; a scope change "
    "follows the change control of ADR 0014."
)
SCOPE_ITEMS = (
    "The scene: whether the scene of a member's driving application becomes common content of the display, each "
    "member showing the scene of its own application, or tells the members apart, as a feature candidate of a later "
    "increment, is open.",
    "The vehicle speed: whether the speed becomes common content of the display is open.",
    "The collision warning: whether the warning and the indication that it is unavailable become content of the "
    "display of every member belongs to the AEBS requirements and architecture, and is open.",
    "The sound: phase 3 of the driver-assistance increment identified the same item; whether the acoustic warning "
    "becomes common content of the driver warning is open.",
    "The renderers: whether the high availability renderer or an app in the IVI VM draws the common content where a "
    "member has an AAOS SDV guest is open.",
    "The members: the Linux-side display of the standalone member ({standalone}) and the display in the guest of the "
    "AAOS-integrated member ({headless}) are realization content, and both are open.",
)
#: the guide's Phase 3 section, flat, split on its bullets: the intro, each bullet whole, the last with the closing
GUIDE_PARTS = (
    "The increment adds no characteristic that distinguishes member products. Its [capability classification]"
    "(../../textual-notation-of-model/packages/features/hmi/hmi_display_capability_classification.sysml) "
    "records no feature candidate and no deferred scope. Core elements are common by default and get no record.",
    "The display itself:** common content of every member (ADR 0026) and no selectable feature for members. In the "
    "feature model `hmiDisplay` is optional, so that configurations which are not members can leave it out "
    "(validity), and it corresponds to that common content (admission).",
    "Where it runs:** derived from the integration mode, in the AAOS SDV guest of an integrated member or on the "
    "Linux side of the standalone member. The guest is the feature candidate `hmiGuestExecutionDomain` of the "
    "Eclipse S-CORE middleware increment.",
    "The scene:** VisionPilot's own, so it comes with the vehicle application, a feature of the feature model. The "
    "display of this increment belongs to the VisionPilot configuration, which is not a member product.",
    "The speed, the warning and its sound:** no member differs by them. The collision warning and the indication "
    "that it is unavailable rest on REQ-AEBS-002, N-AEBS-008 and REQ-AEBS-013 of the product line, and neither the "
    "feature model nor the governed scope holds a warning mode.",
    "Behavior, realization and evidence:** late content and the outages of Android are behavior for Phases 5 and "
    "6; which renderer draws what, the VMs of the guest and the displays of the members are realization; the "
    "verdicts are System 2. None of them is a feature.",
    "Scope decisions** (`gapHmiDisplayInProductLine`): whether the scene of each member's driving application and "
    "the speed become common content of the display; whether the warning and the indication that it is unavailable "
    "become content of the display of every member, a question that belongs to the AEBS requirements and "
    "architecture; whether the acoustic warning becomes common content of the driver warning; and whether the high "
    "availability renderer or an app in the IVI VM draws the common content where a member has an AAOS SDV guest, "
    "are open for the lifecycle decision. This increment admits nothing. The one blocking check of "
    "Phase 3 evaluates the characteristics recorded, and this phase records none, so the Method Check reports Phase "
    "3 as having nothing to evaluate. Review judges the classification.",
)


def _raw() -> str:
    assert MODEL.is_file(), "phase 3 of INC-HMI-001 needs a capability classification model"
    return MODEL.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _header() -> str:
    match = re.match(r"\s*/\*(.*?)\*/\s*package\b", _raw(), re.S)
    assert match, "the slice opens with a header comment before its package"
    return _flat(match.group(1))


def _comment() -> str:
    match = re.search(rf"\bcomment\s+{COMMENT}\s+about\s+{FRAMING_PACKAGE}::{SCOPE_GAP}\s*/\*(.*?)\*/", _raw(),
                      re.S)
    assert match, f"a named comment about {SCOPE_GAP} records what phase 3 classified"
    return _flat(match.group(1))


def _items(text: str) -> list[str]:
    return [item.strip() for item in text.split(" - ")]


def _one(pattern: str, path: Path) -> str:
    """The one name that the pattern finds in the comment-stripped model file."""
    found = re.findall(pattern, strip_comments(path.read_text(encoding="utf-8")))
    assert len(found) == 1, f"{path.name}: {pattern} finds {found}"
    return found[0]


def _names() -> dict[str, str]:
    """The element names the text cites, each read from the model that declares it."""
    gap = r"\bpart\s+({})\s*:\s*IncrementGap\b"
    return {
        "common": _one(r"\bpart\s+(driverHMIDisplay)\s*:\s*CommonCurrentScopeEngineeringContent\b", SCOPE),
        "stack": _one(r"\bpart\s+(drivingStackVariability)\s*:\s*DeferredCurrentScopeVariability\b", SCOPE),
        "system2": _one(r"\bpart\s+(excludedSystem2ConcernSet)\s*:\s*ExcludedSystem2ConcernSet\b", SCOPE),
        "display": _one(r"<'F-CAPABILITY-HMI-DISPLAY'>\s+(hmiDisplay)\[0\.\.1\]", FEATURE_MODEL),
        "visionpilot": _one(r"<'F-PLATFORM-VEHICLE-APPLICATION-VISIONPILOT'>\s+(visionPilot)\[", FEATURE_MODEL),
        "score": _one(r"<'F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE'>\s+(eclipseSCORE)\[", FEATURE_MODEL),
        "acc": _one(r"<'F-CAPABILITY-ADAPTIVE-CRUISE-CONTROL'>\s+(adaptiveCruiseControl)\[", FEATURE_MODEL),
        "lka": _one(r"<'F-CAPABILITY-LANE-KEEP-ASSIST'>\s+(laneKeepAssist)\[", FEATURE_MODEL),
        "guest": _one(r"\bpart\s+(hmiGuestExecutionDomain)\s*:\s*ProductLineFeatureCandidate\b", MIDDLEWARE),
        "speed": _one(r"\bcomment\s+(vehicleSpeedSourceComment)\s+about\s+\S+::hmiSpeedInScope\b", CONTEXT),
        "outage": _one(r"\bcomment\s+(guestAcrossBoundaryComment)\s+about\s+\S+::gapHmiMemberGuestLayout\b",
                       CONTEXT),
        "currency": _one(r"\bconcern\s+(hmiContentCurrencyConcern)\s*:\s*SystemStateConcern\b", FRAMING),
        "allocation": _one(r"\bconcern\s+(hmiRendererAllocationConcern)\s*:\s*PhysicalFunctionalMappingConcern\b",
                           FRAMING),
        "availability": _one(gap.format("gapHmiWarningAvailability"), FRAMING),
        "layout": _one(gap.format("gapHmiMemberGuestLayout"), FRAMING),
        "standalone": _one(gap.format("gapHmiStandaloneLinuxDisplay"), FRAMING),
        "headless": _one(gap.format("gapHmiAAOSIntegratedGuestDisplay"), FRAMING),
        "standalone_out": _one(r"\bpart\s+(hmiStandaloneDisplayOutOfScope)\s*:\s*OutOfScopeItem\b", FRAMING),
    }


def _guide_section() -> str:
    section = re.search(r"(?ms)^## Capability classification \(Phase 3\)\n(.*?)(?=^## )",
                        GUIDE.read_text(encoding="utf-8"))
    assert section, "the guide has a Phase 3 section"
    return " ".join(section.group(1).split())


def test_the_classification_records_no_characteristic():
    raw = _raw()
    assert len(re.findall(rf"^package {PACKAGE} \{{", raw, re.M)) == 1
    code = strip_comments(raw)
    kinds = "|".join(CHARACTERISTIC_KINDS)
    assert re.findall(rf"\bpart\s+\w+\s*:\s*(?:\w+::)*(?:{kinds})\b", code) == [], \
        "an empty delta records nothing (increment-workflow rule 10)"
    assert not re.search(rf"\b(?:{kinds})\b", code), "no product-line characteristic kind is named at all"
    body = re.search(rf"^package {PACKAGE} \{{(.*)\}}\s*$", code, re.M | re.S)
    assert body and " ".join(body.group(1).split()) == BODY, \
        "the package body is the one named comment and declares nothing else: no import, part, concern or view"
    assert "CLS-" not in raw


def test_the_header_gives_each_unrecorded_item_its_reason():
    header = _header()
    assert header.startswith(TITLE)
    sentences = [reason.format(**_names()) for reason in HEADER_REASONS]
    assert header[len(TITLE):] == " ".join(sentences), "the header gives every item without a record its reason"


def test_the_header_names_each_layer_where_it_calls_the_display_optional():
    # validity and admission are two layers: an optional feature beside common content reads as a contradiction
    # unless the same sentence says why it is optional
    for name, text in (("the header", _header()), ("the guide", _guide_section())):
        optional = [sentence for sentence in re.split(r"(?<=\.)\s+", text) if re.search(r"\boptional\b", sentence)]
        assert optional, f"{name} speaks of the feature hmiDisplay"
        for sentence in optional:
            assert "configurations which are not members" in sentence, f"{name}: {sentence}"
            assert "(validity)" in sentence and "(admission)" in sentence, f"{name}: {sentence}"


def test_the_sound_is_carried_over_from_the_driver_assistance_increment_not_decided_again():
    sound = [sentence for sentence in HEADER_REASONS if sentence.startswith("The warning as a sound")]
    assert len(sound) == 1 and sound[0].endswith("phase 3 of the driver-assistance increment identified the same.")
    item = next(item for item in _items(_comment()) if item.startswith("The sound:"))
    assert "phase 3 of the driver-assistance increment identified the same item" in item
    for text in (sound[0], item):
        assert "owner" not in text and not re.search(r"\d{4}-\d{2}-\d{2}", text), \
            "the sound is a reading of the driver-assistance increment, not a decision of the owner"
    # the reading it carries over is in that increment's classification
    driving = _flat(DRIVING.read_text(encoding="utf-8"))
    assert ("neither the feature model nor the governed scope holds a warning mode, and no member differs by one, "
            "so the sound is no feature candidate.") in driving


def test_the_cited_requirements_are_those_of_the_aebs_model():
    aebs = AEBS.read_text(encoding="utf-8")
    for identity in ("REQ-AEBS-002", "REQ-AEBS-013", "N-AEBS-008"):
        assert len(re.findall(rf"doc\s*/\*\s*{identity}\b", aebs)) == 1, f"{identity} is declared once"
        assert identity in _header()


def test_the_scope_decisions_are_named_against_the_product_line_gap():
    names = _names()
    items = _items(_comment())
    assert items[0] == SCOPE_INTRO
    assert tuple(items[1:]) == tuple(item.format(**names) for item in SCOPE_ITEMS), "each item is pinned whole"
    for item in items[1:]:
        assert re.search(r"\b(?:is|are) open\.$", item), f"each item ends on what is open: {item}"
    for banned in ("becomes common.", "needs no new", "is common content of every member", "decided that"):
        assert banned not in _comment(), banned


def test_the_comment_is_about_the_one_gap_that_names_phase_3():
    framing = FRAMING.read_text(encoding="utf-8")
    gaps = set(re.findall(r"\bpart\s+(\w+)\s*:\s*IncrementGap\b", framing))
    assert SCOPE_GAP in gaps
    targets = re.findall(r"\bcomment\s+(\w+)\s+about\s+(\S+)", strip_comments(_raw()))
    assert targets == [(COMMENT, f"{FRAMING_PACKAGE}::{SCOPE_GAP}")], "one named comment, about the product-line gap"
    # the gap is the one of the framing that names phase 3
    docs = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*IncrementGap\s*\{\s*doc\s*/\*(.*?)\*/", framing, re.S))
    assert set(docs) == gaps, "every gap of the framing has a doc"
    naming = [gap for gap in sorted(gaps) if re.search(r"(?i)\bphase 3\b", _flat(docs[gap]))]
    assert naming == [SCOPE_GAP], naming
    # the speed's placement has its own comment of phase 2, which this slice does not restate
    assert "phase 3 places no element" in _flat(CONTEXT.read_text(encoding="utf-8"))
    assert "hmiSpeedInScope" not in _raw()


def test_the_charter_names_the_classification_package():
    charter = FRAMING.read_text(encoding="utf-8")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    # the framing test pins the whole list; later phases append their packages after this one
    assert artifacts and PACKAGE in re.findall(r'"([^"]+)"', artifacts.group(1))


def test_the_slice_touches_no_phase_9_vocabulary():
    raw = _raw()
    for banned in ("PLEML", "requiresFeatures", "#feature", "featureConfiguration", "Corresponds", "receiptSha256",
                   "SDVProductLineFeatureTree", "DE4SDV_AEBSProductLineScope"):
        assert banned not in raw, banned


def _sentences() -> dict[str, list[str]]:
    split = re.compile(r"(?<=[.;:])\s+")
    return {MODEL.name: split.split(_flat(_raw())), "the guide's Phase 3 section": split.split(_guide_section())}


def test_the_slice_carries_no_claim_dated_or_two_way_wording():
    from test_hmi_display_framing import APPROVAL, PAST_BEHAVIOR
    from test_hmi_display_operational_context import CLAIM
    for name, sentences in _sentences().items():
        for sentence in sentences:
            assert not APPROVAL.search(sentence), f"{name} makes an approval claim: {sentence}"
            assert not PAST_BEHAVIOR.search(sentence), f"{name} reports a run: {sentence}"
            assert not CLAIM.search(sentence), f"{name} makes a timing, safety or obligation claim: {sentence}"
            assert not DATED.search(sentence), f"{name} dates its statement: {sentence}"
            assert not TWO_WAY.search(sentence), f"{name} reads ADR 0026 before its scope revision: {sentence}"
            for banned in ("complian", "certif", "approv", "verified", "accepted as a feature", "instrument",
                           "dashboard", "CLS-"):
                assert banned not in sentence.lower() if banned.islower() else banned not in sentence, \
                    f"{name}: {banned}: {sentence}"


def test_the_guide_states_the_classification_and_admits_nothing():
    section = _guide_section()
    parts = tuple(section.split(" - **"))
    assert len(parts) == len(GUIDE_PARTS), "the intro and one part for each bullet"
    for part, expected in zip(parts, GUIDE_PARTS):
        assert part == expected, "each bullet of the guide's Phase 3 section is pinned whole"
    assert section.endswith("Review judges the classification."), "the section ends on the vacuous sentence"
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## Operational context and story (Phase 2)") < guide.index(
        "## Capability classification (Phase 3)") < guide.index("## What the framing already records as open")
    assert guide.count("## Capability classification (Phase 3)") == 1
    assert "](../../textual-notation-of-model/packages/features/hmi/hmi_display_capability_classification.sysml)" \
        in guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0], "the frame links the slice"
    assert all(len(line) <= 79 or "](" in line or line.startswith("|") for line in guide.splitlines()), \
        "the guide's prose wraps at 79 columns; a link or a table row may run longer"


def test_the_guide_names_the_next_obligation_after_the_classification():
    flat = " ".join(GUIDE.read_text(encoding="utf-8").split("## Next obligation and execution limits", 1)[1]
                    .split("\n## ", 1)[0].split())
    for phrase in ("Phase 3, the capability classification, records no feature-model delta, and review judges it: "
                   "its one blocking check has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, "
                   "with a prompt for review.",
                   "The next model obligation is **Phase 9**: the configuration, which makes the realization of the "
                   "increment a configured product; its first gate is `incrementHasConfiguredProduct`."):
        assert flat.count(phrase) == 1, phrase
    assert "The next model obligation is **Phase 3**" not in flat
    assert "The next model obligation is **Phase 4**" not in flat
    assert "The next model obligation is **Phase 5**" not in flat
    assert "The next model obligation is **Phase 6**" not in flat
    assert "The next model obligation is **Phase 7**" not in flat
    assert "The next model obligation is **Phase 8**" not in flat
