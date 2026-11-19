"""Content pins for the E/E architecture capability classification (phase 3), not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import strip_comments

ROOT = Path(__file__).resolve().parents[1]
EE = ROOT / "textual-notation-of-model/packages/features/ee"
FRAMING = EE / "ee_architecture_framing.sysml"
CONTEXT = EE / "ee_architecture_operational_context.sysml"
MODEL = EE / "ee_architecture_capability_classification.sysml"
FEATURES = ROOT / "model-based-product-line-engineering/feature-models/sdv_product_line.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
PACKAGE = "DE4SDV_EEArchitectureCapabilityClassification"
FRAMING_PACKAGE = "DE4SDV_EEArchitectureFraming"
SCOPE_GAP = "gapEENetworkInProductLine"
STACK_GAP = "gapEEStackAndNetworkBoundary"

#: The product-line characteristic kinds of the method kernel. Phase 3 records the feature-model delta
#: only (increment-workflow rule 10), and this increment adds none: an empty delta records nothing.
CHARACTERISTIC_KINDS = (
    "ProductLineCharacteristic", "ProductLineFeatureCandidate", "DeferredProductLineScope",
    "CommonProductLineCapability",
)
#: the whole comment-stripped package body: the two named comments, and no declaration of any kind
BODY = (
    f"comment eeNetworkScopeDecisions about {FRAMING_PACKAGE}::{SCOPE_GAP} "
    f"comment eeStackClassification about {FRAMING_PACKAGE}::{STACK_GAP}"
)
#: a dated word: the slice states what holds, not when (one style with the framing)
DATED = re.compile(r"(?i)\b(?:already|still|yet|today|currently|settled?)\b")
#: the field words of the operational-context test, and a field of the command
FIELD = re.compile(r"(?i)\bfields?\b")
#: ADR numbers and decisions are no number of the command either
ADR = re.compile(r"\bADR \d{4}(?: decisions? \d)?\b")

#: one sentence per item without a record, each with its reason, read flat from the header
HEADER_REASONS = (
    "INC-EE-001, phase 3, adds no characteristic that distinguishes member products, so it records no feature "
    "candidate and no deferred scope.",
    "Core elements are common by default and get no record.",
    "The topology of the vehicle network gets none: the increment judges one topology for one configuration, its "
    "framing puts a second topology and any variability of the E/E architecture out of scope, and no member, "
    "configuration or product model of the product line holds a vehicle network.",
    "The zone controllers, the backbone, the CAN buses, the direct link and the actuation ECU get none: they are "
    "parts of that topology.",
    "The two routes of the driving command get none: they are a design alternative inside that one topology, the "
    "increment judges both, and its lifecycle decision names the route of the reference vehicle network; no member "
    "differs by its route.",
    "The driving command gets none: it is the command of the driver-assistance increment.",
    "{source}, the source of the driving command in the operational context, gets none: what gives the command is "
    "the driver-assistance increment's to classify.",
    "The Eclipse S-CORE path ({path}) gets none: Eclipse S-CORE is a feature of the feature model ({score}), and this "
    "increment changes no feature.",
    "The vehicle gets none: this increment varies nothing of it.",
    "The faults of the network get none: phase 5 states what the command path does under them and phase 10 judges "
    "it.",
    "The verdicts get none: they are evidence of phase 10, from a testbed of System 2, which the governed scope "
    "keeps out of product variability.",
    "The medium of the direct link gets none: phases 6 to 8 decide it.",
    "The vehicle-target compute family gets none: the increment selects no compute target for the nodes of the "
    "network, and the family is the deferred vehicle runtime variability of the governed scope.",
    "Vehicle-Target AEBS and the independence of the protected emergency command path get none: they stay common, "
    "and this increment does not carry the AEBS command.",
    "The items that the framing puts out of scope get none: they are out-of-scope items of the framing.",
)
#: the whole text of the comment on the product-line gap
SCOPE_COMMENT = (
    "Phase 3 classifies the vehicle network against the governed scope as it stands and names the scope decisions "
    "that the lifecycle decision of this increment needs. This increment admits nothing; a scope change follows "
    "the change control of ADR 0014. "
    "- The reference vehicle network: no member differs by it, so it is no feature candidate. Whether the governed "
    "scope takes it, with the route that the decision names, as common content of every member is open. "
    "- The common content: Vehicle-Target AEBS and the independence of the protected emergency command path stay "
    "common; ADR 0023 decision 5 keeps them common to the three planned members it names, once its scope pull "
    "request lands. What a common vehicle network "
    "means for that path and for the hand-off to the brake ECU ({handoff}) is open. "
    "- Later topologies: a second topology, or a route that tells members apart, would be variability that the "
    "governed scope does not hold; Integration Mode is the only product variability that the governed scope "
    "admits (ADR 0023 decision 2). Whether such variability enters the scope as deferred variability is open. "
    "- The configuration: no feature of the feature model expresses the vehicle network, so a configuration "
    "selects none for it."
)
#: the whole text of the comment on the stack gap, phase 3's share of it
STACK_COMMENT = (
    "Phase 3's share of the gap, the classification: the platform stack, the vehicle-target execution-environment "
    "family and {boundary} get no feature from this increment, and this increment changes none of them. In the "
    "operational context the driving command enters the vehicle network from the Eclipse S-CORE path "
    "({assumption}), and the context reuses no {boundary} of the AAOS SDV middleware boundary. How the network "
    "side of the central computer relates to the SoC and the hardware layer of the platform stack is open for "
    "phases 6 to 8. Whether phase 8 allocates a node of the network to the vehicle-target family is open for "
    "phase 8."
)


def _raw() -> str:
    assert MODEL.is_file(), "phase 3 of INC-EE-001 needs a capability classification model"
    return MODEL.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _header() -> str:
    match = re.match(r"\s*/\*(.*?)\*/\s*package\b", _raw(), re.S)
    assert match, "the slice opens with a header comment before its package"
    return _flat(match.group(1))


def _comment(about: str) -> str:
    match = re.search(rf"\bcomment\s+(ee\w+)\s+about\s+{re.escape(about)}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, f"a named comment about {about} records what phase 3 classified"
    return _flat(match.group(2))


def _item(text: str, marker: str) -> str:
    items = [item for item in text.split(" - ") if item.startswith(marker)]
    assert len(items) == 1, f"one item of the comment names {marker}"
    return items[0].strip()


def _gaps() -> set[str]:
    return set(re.findall(r"\bpart\s+(\w+)\s*:\s*IncrementGap\b", FRAMING.read_text(encoding="utf-8")))


def _names() -> dict[str, str]:
    """The element names the text cites, read from the models that declare them."""
    context = CONTEXT.read_text(encoding="utf-8")
    source = re.search(r"\bpart\s+def\s+(\w+)\s*:>\s*OperationalEntity\b", context)
    path = re.search(r"\bpart\s+scorePath\s*:\s*(\w+)", context)
    score = re.search(r"<'F-PLATFORM-MIDDLEWARE-ECLIPSE-SCORE'>\s+(\w+)\[", FEATURES.read_text(encoding="utf-8"))
    boundary = re.search(r"\b(?:port|part)\s+def\s+(VehicleNetworkBoundary)\b", (
        ROOT / "textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml").read_text(
        encoding="utf-8"))
    handoff = re.search(r"\bpart\s+(gapEEBrakeHandoff)\s*:\s*IncrementGap\b", FRAMING.read_text(encoding="utf-8"))
    assumption = re.search(r"\bpart\s+(asmEEScoreCommandSource)\s*:\s*IncrementAssumption\b",
                           FRAMING.read_text(encoding="utf-8"))
    assert source and path and score and boundary and handoff and assumption, \
        "the cited elements are declared where they live"
    return {"source": source.group(1), "path": path.group(1), "score": score.group(1),
            "boundary": boundary.group(1), "handoff": handoff.group(1), "assumption": assumption.group(1)}


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
        "the package body is the two named comments and declares nothing else"
    assert re.findall(r"\bcomment\s+(\w+)\s+about\s+(\S+)", code) == [
        ("eeNetworkScopeDecisions", f"{FRAMING_PACKAGE}::{SCOPE_GAP}"),
        ("eeStackClassification", f"{FRAMING_PACKAGE}::{STACK_GAP}"),
    ], "two named comments, one about each framing gap that names phase 3"
    assert "CLS-" not in raw


def test_the_header_gives_each_unrecorded_item_its_reason():
    header = _header()
    assert header.startswith("DE4SDV E/E architecture capability classification model slice. ")
    names = _names()
    sentences = [reason.format(**names) for reason in HEADER_REASONS]
    body = header[len("DE4SDV E/E architecture capability classification model slice. "):]
    assert body == " ".join(sentences), "the header gives every item without a record its reason, and no more"


def test_the_routes_are_judged_in_one_topology_not_a_member_alternative():
    texts = " ".join([_header(), _comment(f"{FRAMING_PACKAGE}::{SCOPE_GAP}"),
                      _comment(f"{FRAMING_PACKAGE}::{STACK_GAP}")])
    assert "they are a design alternative inside that one topology" in texts
    assert "no member differs by its route." in texts
    for banned in ("route as a feature candidate", "distinguishes members by", "variant of",
                   "alternative of Integration Mode", "members differ by their route"):
        assert banned not in texts, banned


def test_the_scope_decisions_are_named_against_the_product_line_gap():
    text = _comment(f"{FRAMING_PACKAGE}::{SCOPE_GAP}")
    assert text == SCOPE_COMMENT.format(**_names()), "the comment on the product-line gap is pinned whole"
    for marker in ("The reference vehicle network:", "The common content:", "Later topologies:"):
        assert re.search(r"\bis open\.$", _item(text, marker)), f"{marker} ends on what is open"
    assert _item(text, "The configuration:").endswith("selects none for it.")
    for banned in ("becomes common", "needs no new", "three accepted members", "is common content of every member"):
        assert banned not in text, banned


def test_the_stack_gap_gets_phase_3s_share():
    assert _comment(f"{FRAMING_PACKAGE}::{STACK_GAP}") == STACK_COMMENT.format(**_names())


def test_each_comment_is_about_a_gap_the_framing_holds():
    gaps = _gaps()
    targets = re.findall(r"\bcomment\s+\w+\s+about\s+(\S+)", _raw())
    assert targets
    for target in targets:
        package, _, name = target.partition("::")
        assert package == FRAMING_PACKAGE and name in gaps, f"{target} is a gap of the framing"


def test_the_charter_names_the_classification_package():
    charter = FRAMING.read_text(encoding="utf-8")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and PACKAGE in re.findall(r'"([^"]+)"', artifacts.group(1))


def test_the_slice_touches_no_phase_9_vocabulary():
    raw = _raw()
    for banned in ("PLEML", "#FeatureBinding", "#DerivationRule", "receiptSha256", "SDVProductLineFeatureTree",
                   "DE4SDV_AEBSProductLineScope"):
        assert banned not in raw, banned


def _sentences() -> dict[str, list[str]]:
    model = _flat(_raw())
    guide = _guide_section()
    split = re.compile(r"(?<=[.;:])\s+")
    return {MODEL.name: split.split(model), "the guide's Phase 3 section": split.split(guide)}


def test_the_slice_carries_no_claim_or_dated_wording():
    from test_ee_architecture_framing import APPROVAL, PAST_BEHAVIOR
    from test_ee_architecture_operational_context import CLAIM
    for name, sentences in _sentences().items():
        for sentence in sentences:
            assert not APPROVAL.search(sentence), f"{name} makes an approval claim: {sentence}"
            assert not PAST_BEHAVIOR.search(sentence), f"{name} reports a run: {sentence}"
            assert not CLAIM.search(sentence), f"{name} makes a timing or safety claim: {sentence}"
            assert not DATED.search(sentence), f"{name} dates its statement: {sentence}"
            for banned in ("complian", "certif", "approv", "owner decided", "owner direction", "CLS-"):
                assert banned not in sentence.lower() if banned.islower() else banned not in sentence, \
                    f"{name}: {banned}: {sentence}"


def test_the_slice_names_no_form_of_the_driving_command():
    from test_ee_architecture_operational_context import FORM, IDENTITY
    for name, sentences in _sentences().items():
        for sentence in sentences:
            bare = re.sub(ADR, "", re.sub(IDENTITY, "", sentence))
            assert not FORM.search(bare), f"{name} names a form, a rate or a number of the command: {sentence}"
            assert not FIELD.search(bare), f"{name} names a field of the command: {sentence}"


#: the guide's Phase 3 section, flat, split on its bullets: the intro, each bullet whole, the last with the closing
GUIDE_PARTS = (
    "The increment adds no characteristic that distinguishes member products. Its [capability classification]"
    "(../../textual-notation-of-model/packages/features/ee/ee_architecture_capability_classification.sysml) "
    "records no feature candidate and no deferred scope. Core elements are common by default and get no record.",
    "The topology:** one topology for one configuration; a second topology and any E/E variability are out of "
    "scope, and no member of the product line holds a vehicle network.",
    "The two routes:** a design alternative inside that topology; the increment judges both, and its lifecycle "
    "decision names the route of the reference vehicle network. No member differs by its route.",
    "The driving command and its source:** the command is that of the driver-assistance increment, and what gives "
    "it is that increment's to classify; Eclipse S-CORE is a feature of the feature model. The command source, the "
    "S-CORE path and the vehicle get no feature from this increment.",
    "Faults, verdicts and the medium of the direct link:** requirements and evidence of Phases 5 and 10 and a "
    "choice of Phases 6 to 8, none of them a feature. **The vehicle-target compute family:** the deferred vehicle "
    "runtime variability of the governed scope; the increment selects no compute target.",
    "Scope decisions** (`gapEENetworkInProductLine`): whether the governed scope takes the reference vehicle "
    "network as common content, what that means for the AEBS emergency path and the brake hand-off, and whether "
    "later topologies enter the scope as deferred variability, are open for the lifecycle decision. This "
    "increment admits nothing.",
    "The platform stack and the network boundary** (`gapEEStackAndNetworkBoundary`): they get no feature from "
    "this increment. How the network side of the central computer relates to the SoC and the hardware layer of "
    "the platform stack is open for Phases 6 to 8, and whether Phase 8 allocates a node of the network to the "
    "vehicle-target family is open for Phase 8. The one blocking check of Phase 3 evaluates the characteristics "
    "recorded, and this phase records none, so the Method Check reports Phase 3 as having nothing to evaluate. "
    "Review judges the classification.",
)


def test_the_guide_states_the_classification_and_admits_nothing():
    section = _guide_section()
    parts = tuple(section.split(" - **"))
    assert len(parts) == len(GUIDE_PARTS), "the intro and one part for each bullet"
    for part, expected in zip(parts, GUIDE_PARTS):
        assert part == expected, "each bullet of the guide's Phase 3 section is pinned whole"
    assert "(../../textual-notation-of-model/packages/features/ee/ee_architecture_capability_classification.sysml)" \
        in section
    assert SCOPE_GAP in section and STACK_GAP in section
    assert "VisionPilot" not in section and "VisionPilot" not in _raw(), \
        "phase 3 says no more about the driver-assistance increment than phase 0 does"
