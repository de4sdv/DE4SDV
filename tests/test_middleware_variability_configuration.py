"""INC-MW-009: the configured Autoware + AAOS SDV member (ADR 0022).

The member's PLEML feature configuration selects the application and the
middleware; the receipt derives the adapter, which no configuration selects;
the committed projection regenerates from the receipt byte for byte. The
configured member has one instance and one owner per platform layer (owner
decisions of 2026-10-23 and 2026-10-25): the platform stack owns the derived
adapter, the guest middleware and the guest operating system; the middleware
boundary refers to the adapter and to the AAOS SDV boundary, the AAOS SDV
boundary refers to its platform software, and three bindings make the
references the same things.

The ownership guards are lexical. They scan the files of the five validated
model roots (``scripts/validate_sysml.py``), without their fixtures, with the
reader of ``test_member_product_projections.py``: it blanks comments and
strings, reads every typing form (``:``, ``defined by``, ``typed by``), every
specialization form (``:>``, ``specializes``), short names and redefinitions,
and fails on a part definition header it cannot read. Licensed Syside
validates the model in CI.
"""
import json
import re
import sys
import unittest
from pathlib import Path

import pytest
import yaml

import test_member_product_projections as reader
from scripts.validate_sysml import MODEL_PATHS as VALIDATED_MODEL_ROOTS, model_files
from sysml_shapes import braced_body, strip_comments


REPO_ROOT = Path(__file__).resolve().parents[1]
PLE_ROOT = REPO_ROOT / "model-based-product-line-engineering"
FEATURE_MODEL = PLE_ROOT / "feature-models" / "sdv_product_line.sysml"
CONFIGURATION = PLE_ROOT / "feature-configurations" / "middleware_autoware_aaos_sdv_reference.sysml"
EVIDENCE_RECORD = PLE_ROOT / "feature-configurations" / "evidence" / "middleware-autoware-aaos-sdv-reference.yaml"
RECEIPT = PLE_ROOT / "feature-models" / "receipts" / "sdv_product_line.receipt.json"
PRODUCT_MODEL = PLE_ROOT / "product-models" / "middleware_autoware_aaos_sdv_reference.sysml"
MIDDLEWARE = REPO_ROOT / "textual-notation-of-model" / "packages" / "features" / "middleware"
PHASE9_MODEL = MIDDLEWARE / "middleware_variability_configuration.sysml"
PHYSICAL_MODEL = MIDDLEWARE / "middleware_physical_software_realization.sysml"
EVIDENCE_MODEL = MIDDLEWARE / "middleware_verification_evidence.sysml"
PLATFORM_STACK = REPO_ROOT / "textual-notation-of-model" / "packages" / "architecture" / "sdv_platform_stack.sysml"
AAOS_BOUNDARY_MODEL = REPO_ROOT / "textual-notation-of-model" / "packages" / "architecture" / "aaos_sdv_middleware_boundary.sysml"
#: SDVCoreBoundary models the internal structure of the AAOS SDV middleware layer
#: (the doc of AndroidSDVMiddleware in the platform stack), so it stands for that layer.
AAOS_SDV_MIDDLEWARE_MODEL = "SDVCoreBoundary"
#: SDVPlatformSoftwareBoundary is guest operating-system content (GKI, drivers, HALs, runtime),
#: so it stands for the guest operating-system layer (owner decision of 2026-10-25).
GUEST_OPERATING_SYSTEM_MODEL = "SDVPlatformSoftwareBoundary"
PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "middleware-variability-configuration.yaml"
)
#: The member whose platform stack owns the adapter and the AAOS SDV guest.
MEMBER = "MiddlewareAutowareAAOSSDVConfiguredMember"
#: The SDV Core boundary definitions. Every part usage typed by one of them, or by a
#: specialization of one, is a reference: the platform stack owns the guest.
SDV_CORE_BOUNDARY_DEFINITIONS = frozenset({AAOS_SDV_MIDDLEWARE_MODEL, GUEST_OPERATING_SYSTEM_MODEL})
#: The references that stand for the guest outside the platform stack. A part usage that
#: redefines, subsets or reference-subsets one of them must stay a reference too.
GUEST_REFERENCES = frozenset({"aaosSdvBoundary", "platformSoftware"})
#: Definitions that stand for a layer the member's platform stack owns: the guest operating
#: system, the guest middleware and the adapter (the stack realizations and the boundary
#: models of them), and the display-capable AAOS SDV guest of INC-AEBS-010.
SHARED_LAYER_DEFINITIONS = frozenset({"AndroidHLOS", "AndroidSDVMiddleware", "AutowareToAAOSSDVAdapter",
                                      "SDVCoreBoundary", "SDVPlatformSoftwareBoundary", "SdvIviCfGuestTarget"})
#: Named exception, tied to the open owner decision on headless or display (2026-10-25). The
#: INC-AEBS-010 test article inherits the headless guest of the member and also composes the
#: display-capable sdv_ivi_cf guest of its System 2 instrument, whose doc says that it replaces
#: the headless target. Remove the exception when the owner decides. Any other composite
#: representation of a shared layer in the member or its specializations fails.
KNOWN_SECOND_GUEST = frozenset({
    ("AEBSAutowareAAOSSDVVisualizationTestArticle", "visualizationChain.instrument.iviGuest", "SdvIviCfGuestTarget"),
})
#: A part, item or occurrence usage keyword, and the ``ref`` keyword, in a declaration head.
_KIND = re.compile(r"\b(?:part|item|occurrence)\b")
_PART = re.compile(r"\bpart\b")
_REF = re.compile(r"\bref\b")
#: A feature relation in a declaration: a redefinition (``:>>``, ``redefines``), a subsetting
#: (``:>``, ``subsets``) or a reference subsetting (``::>``, ``references``) of ``target``.
_FEATURE_RELATION = re.compile(
    rf"(?::>>|\bredefines\b|::>|\breferences\b|:>(?!>)|\bsubsets\b)\s*(?P<target>{reader._QUALIFIED})")
_PART_DEF = re.compile(r"\bpart\s+def\b")
#: The start of a usage declaration that owns a body: ``part <'id'> name : T {``, ``part name {``.
_USAGE_BODY = re.compile(
    rf"\b(?:part|item|occurrence)\s+{reader._SHORT_NAME}(?:(?::>>|\bredefines\b)\s*)?(?P<name>{reader._NAME})"
    r"[^;{}]*\{")


def _simple(names: str | None) -> list[str]:
    """The simple names of a typing or specialization list, in order."""
    return [name.rsplit("::", 1)[-1] for name in reader._names(names)]


def _head(code: str, position: int) -> str:
    """The declaration head before ``position``: the text after the last ``;``, ``{`` or ``}``."""
    return code[max(code.rfind(mark, 0, position) for mark in ";{}") + 1:position]


def _typed_usages(code: str) -> list[tuple[int, str, str, list[str]]]:
    """(position, declaration head, usage name, simple types) of every typed usage of active ``code``."""
    return [(match.start(), _head(code, match.start()), reader._bare(match["usage"]), _simple(match["types"]))
            for match in reader._TYPED_USAGE.finditer(code)]


def _is_composite(head: str) -> bool:
    """A usage with a part, item or occurrence keyword and no ``ref`` is composite."""
    return bool(_KIND.search(head)) and not _REF.search(head)


def _definition_index(code: dict[str, str]) -> dict[str, list[tuple[set[str], str]]]:
    """Part definition name -> (simple supertypes, braced body) of each declaration of it."""
    index: dict[str, list[tuple[set[str], str]]] = {}
    for text in code.values():
        for name, generals, start, end in reader._definitions(text):
            index.setdefault(name, []).append(({general.rsplit("::", 1)[-1] for general in generals},
                                               text[start:end + 1] if end > start else ""))
    return index


def _with_specializations(roots, index) -> set[str]:
    """``roots`` and every part definition that specializes one of them, directly or not."""
    family = set(roots)
    while True:
        grown = family | {name for name, declarations in index.items()
                          if any(generals & family for generals, _ in declarations)}
        if grown == family:
            return family
        family = grown


def _guest_model_code() -> dict[str, str]:
    """Active code of every file of the five validated model roots, without their fixtures, as
    ``scripts/validate_sysml.py`` and the licensed check select them."""
    return {path.relative_to(REPO_ROOT).as_posix(): reader._active(path.read_text(encoding="utf-8"))
            for model_path in VALIDATED_MODEL_ROOTS for path in model_files(REPO_ROOT, model_path)}


def _sdv_core_boundary_usages(code: dict[str, str]) -> set[tuple[str, str, bool]]:
    """(file, usage, composite) of every part usage typed by an SDV Core boundary definition or a
    specialization of one, and of every part usage that redefines, subsets or reference-subsets a
    guest reference."""
    family = _with_specializations(SDV_CORE_BOUNDARY_DEFINITIONS, _definition_index(code))
    found = set()
    for path, text in code.items():
        for _, head, usage, types in _typed_usages(text):
            if family.intersection(types) and _PART.search(head):
                found.add((path, usage, _is_composite(head)))
        for match in _FEATURE_RELATION.finditer(text):
            target = reader._qualified(match["target"]).rsplit("::", 1)[-1]
            head = _head(text, match.start())
            if target in GUEST_REFERENCES and _PART.search(head) and not _PART_DEF.search(head):
                found.add((path, target, _is_composite(head)))
    return found


def _usage_bodies(body: str) -> list[tuple[str, int, int]]:
    """(usage name, opening brace, closing brace) of every usage declaration of ``body`` that owns a body."""
    spans = []
    for match in _USAGE_BODY.finditer(body):
        opening = match.end() - 1
        depth = 0
        for closing in range(opening, len(body)):
            depth += {"{": 1, "}": -1}.get(body[closing], 0)
            if depth == 0:
                break
        spans.append((reader._bare(match["name"]), opening, closing))
    return spans


def _composed_shared_layers(code: dict[str, str]) -> set[tuple[str, str, str]]:
    """(definition, usage path, type) of every composite usage typed by a shared layer definition, or a
    specialization of one, that the member or a specialization of it composes outside ``platformStack``.

    The walk starts at the bodies of each such definition and of its supertypes. It follows composite
    usages at any depth of a body, and the definitions (with their supertypes) of every composite
    usage it passes, a hit included. So the path names each composite owner on the way, and a shared
    layer inside the definition of a hit is reported too.
    """
    index = _definition_index(code)
    family = _with_specializations(SHARED_LAYER_DEFINITIONS, index)
    lineage = _with_specializations({MEMBER}, index)
    hits = set()

    def bodies(name: str, seen: set[str]):
        for generals, text in index.get(name, []):
            yield text
            for general in sorted(generals - seen):
                seen.add(general)
                yield from bodies(general, seen)

    def walk(owner: str, text: str, path: tuple[str, ...], visited: frozenset, top: bool) -> None:
        spans = _usage_bodies(text)
        excluded = [(opening, closing) for name, opening, closing in spans
                    if top and name == "platformStack" and text.count("{", 0, opening) - text.count("}", 0, opening) == 1]
        for position, head, usage, types in _typed_usages(text):
            if not _is_composite(head) or any(opening < position < closing for opening, closing in excluded):
                continue
            if top and usage == "platformStack" and text.count("{", 0, position) - text.count("}", 0, position) == 1:
                continue
            nesting = tuple(name for name, opening, closing in spans if opening < position < closing)
            full = path + nesting + (usage,)
            shared = family.intersection(types)
            if shared:
                hits.add((owner, ".".join(full), sorted(shared)[0]))
            for name in types:
                if name not in visited:
                    for inner in bodies(name, {name}):
                        walk(owner, inner, full, visited | {name}, False)

    for member in sorted(lineage):
        for text in bodies(member, {member}):
            walk(member, text, (), frozenset({member}), True)
    return hits


def _receipt_model():
    receipt = json.loads(RECEIPT.read_text())
    [model] = receipt["evaluation"]["feature_models"]
    return model


def _platform_layer_definitions() -> set[str]:
    """The layer definitions of the SDV platform stack, their realizations, and every
    specialization of them in the physical slice (lexical, transitive). Every general
    definition of a specialization list counts, not only the first."""
    code = {path.name: reader._active(path.read_text(encoding="utf-8")) for path in (PLATFORM_STACK, PHYSICAL_MODEL)}
    layers = set(re.findall(r"\bpart\s+def\s+(\w+Layer)\b", code[PLATFORM_STACK.name]))
    assert len(layers) == 6, layers
    return _with_specializations(layers, _definition_index(code)) | SDV_CORE_BOUNDARY_DEFINITIONS


def _declarations(body: str) -> list[tuple[str, str, list[str]]]:
    """(``'ref'`` or ``''``, name, simple types) of the part usages that ``body`` declares itself,
    at depth 0, in every typing form, with short names and redefinitions."""
    code = reader._active(body)
    return [("ref" if _REF.search(head) else "", usage, types)
            for position, head, usage, types in _typed_usages(code)
            if _PART.search(head) and code.count("{", 0, position) == code.count("}", 0, position)]


class TestLayerGuardReadsWholeLists(unittest.TestCase):
    """The guard helpers read every typing and specialization form and every name of a list."""

    def test_typing_lists(self):
        body = "part a : SignalAccessClient, AutowareToAAOSSDVAdapterPhysical; ref part b : P::X { part c : Y; }"
        self.assertEqual(_declarations(body), [("", "a", ["SignalAccessClient", "AutowareToAAOSSDVAdapterPhysical"]),
                                               ("ref", "b", ["X"])])
        self.assertEqual(_declarations("part :>> a = b; part x :> y; part z :>> w;"), [])

    def test_typing_forms(self):
        body = ("part a defined by X; part <'S-1'> b typed by Y; part :>> c : Z; ref part <d> e[0..1] : P::W;"
                " /* part f : V; */ attribute g : U;")
        self.assertEqual(_declarations(body), [("", "a", ["X"]), ("", "b", ["Y"]), ("", "c", ["Z"]),
                                               ("ref", "e", ["W"])])

    def test_specialization_lists(self):
        code = reader._active("part def X :> PhysicalAllocationElement, DE4SDV_SDVPlatformStack::AutowareToAAOSSDVAdapter"
                              " { } part def <'Y-1'> Y specializes X;")
        index = _definition_index({"probe": code})
        self.assertEqual(index["X"][0][0], {"PhysicalAllocationElement", "AutowareToAAOSSDVAdapter"})
        self.assertEqual(_with_specializations({"AutowareToAAOSSDVAdapter"}, index),
                         {"AutowareToAAOSSDVAdapter", "X", "Y"})


class TestMWVariabilityConfiguration(unittest.TestCase):
    def test_configuration_selects_member_features_but_not_the_derived_adapter(self):
        model = _receipt_model()
        [configuration] = [item for item in model["configurations"]
                           if item["source"] == CONFIGURATION.relative_to(REPO_ROOT).as_posix()]
        self.assertTrue(configuration["valid"])
        # One SoC (owner decision D3, INC-MW-011 phase 9): Autoware on Linux on the main side, the KVM host,
        # and the AAOS SDV middleware in the Android guest. No HMI display (owner decisions D3 and D2 V3).
        self.assertEqual(
            {"platformStack.autoware", "platformStack.androidSDV", "platformStack.linux", "platformStack.kvm",
             "platformStack.guestAndroid", "platformStack.guestAndroidSDV",
             "sensingBoundary.lidar", "sensingBoundary.camera"} - set(configuration["selected"]),
            set(),
        )
        self.assertFalse({"platformStack.noMiddleware", "platformStack.android",
                          "platformStack.noGuestOperatingSystem", "platformStack.noGuestMiddleware",
                          "capabilities.hmiDisplay", "sensingBoundary.radar"}
                         & set(configuration["selected"]))
        exempted = [item["asset"] for item in configuration["admission"]["common_content"] if item["exempted"]]
        self.assertEqual(exempted, [], "the member needs no exemption")
        self.assertFalse(any("adapter" in path.lower() for path in configuration["selected"]))
        derived = {item["variation"]: item for item in configuration["derived_variants"]}
        self.assertEqual(derived["applicationMiddlewareAdapter"]["variant"], "autowareToAAOSSDV")
        self.assertNotIn("binding", derived["applicationMiddlewareAdapter"])
        self.assertEqual(configuration["admission"]["alternative"], "aaosIntegrated")
        evidence = yaml.safe_load(EVIDENCE_RECORD.read_text())
        self.assertEqual(evidence, {"status": "planned", "artifacts": []})

    def test_feature_model_derives_the_complete_supported_pair_table(self):
        [derivation] = _receipt_model()["derivations"]
        self.assertEqual(derivation["derived_variation"], "applicationMiddlewareAdapter")
        resolved = {tuple(rule["premises"]): rule["result"] for rule in derivation["rules"]}
        self.assertEqual(
            resolved,
            {
                ("platformStack.autoware", "platformStack.eclipseSCORE"): "autowareToSCORE",
                ("platformStack.autoware", "platformStack.androidSDV"): "autowareToAAOSSDV",
                ("platformStack.autoware", "platformStack.autosarAdaptive"): "autowareToAUTOSAR",
                ("platformStack.openpilot", "platformStack.eclipseSCORE"): "openpilotToSCORE",
                ("platformStack.apollo", "platformStack.eclipseSCORE"): "apolloToSCORE",
                ("platformStack.autoware", "platformStack.noMiddleware"): "none",
                ("platformStack.openpilot", "platformStack.noMiddleware"): "none",
                ("platformStack.apollo", "platformStack.noMiddleware"): "none",
            },
        )

    def test_committed_product_projection_is_reproducible(self):
        """From the receipt, byte for byte."""
        import projection_sources as sources

        committed = PRODUCT_MODEL.read_text()
        self.assertEqual(sources.receipt_projection(CONFIGURATION.relative_to(REPO_ROOT).as_posix()), committed)

        product = PRODUCT_MODEL.read_text()
        self.assertIn(
            "part :>> applicationMiddlewareAdapter = "
            "applicationMiddlewareAdapter::autowareToAAOSSDV;",
            product,
        )
        self.assertIn("derived by D-ASSET-APPLICATION-MIDDLEWARE-ADAPTER", product)
        self.assertIn("do not prove provider", product)
        self.assertNotIn("kuksa", product.lower())

    def test_phase9_model_records_source_roles_realization_choice_and_nonclaims(self):
        model = PHASE9_MODEL.read_text()
        normalized = " ".join(model.replace("*", " ").split())
        required = [
            "package DE4SDV_MiddlewareVariabilityConfiguration",
            "part incMW009 : FeatureIncrement",
            "part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember",
            "part ifexInterfaceDesignSource : SourceContributionRecord",
            "part vehicleSpeedPropertyClassification : SourceContributionRecord",
            "part directVSIDLToROS2Realization : MissingRealizationRecord",
            "part kuksaBrokeredAlternative : DeferredProductLineScope",
            "dependency configuredPhysicalBoundaryTrace",
            "dependency vssVehicleSpeedSemanticTrace",
            "dependency exactReferenceContractTrace",
            "ProductLineConfigurationViewpoint",
            "ProductModelAssemblyViewpoint",
            "GAP-MW-024",
        ]
        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, model)
        self.assertIn("Property", model)
        self.assertIn("not selected", model)
        self.assertIn("not implemented", normalized)
        self.assertIn("not deployed", normalized)
        self.assertIn("not empirically verified", normalized)
        self.assertNotIn("part kuksaDatabroker", model)

    def test_the_boundary_refers_to_the_platform_layers_it_needs(self):
        """The middleware boundary owns no platform layer (owner decisions of 2026-10-23 and
        2026-10-25). It refers to the adapter and to the AAOS SDV boundary; every other part it
        declares is typed by no platform layer, so it keeps owning them."""
        layers = _platform_layer_definitions()
        self.assertIn("AutowareToAAOSSDVAdapterPhysical", layers)
        boundary = braced_body(strip_comments(PHYSICAL_MODEL.read_text()), "part def MiddlewarePhysicalSoftwareBoundary")
        declared = _declarations(boundary)
        self.assertEqual(len(declared), 9)
        layered = [(ref.strip(), name) for ref, name, types in declared if layers.intersection(types)]
        self.assertEqual(layered, [("ref", "adapter"), ("ref", "aaosSdvBoundary")])
        self.assertEqual([name for ref, name, _ in declared if ref], ["adapter", "aaosSdvBoundary"])

    def test_the_sdv_core_boundary_refers_to_its_platform_software(self):
        """SDVCoreBoundary owns the AAOS SDV services and refers to its platform software, the
        guest operating-system content (owner decision of 2026-10-25)."""
        layers = _platform_layer_definitions()
        core = braced_body(strip_comments(AAOS_BOUNDARY_MODEL.read_text()), "part def SDVCoreBoundary")
        declared = _declarations(core)
        self.assertEqual(len(declared), 16)
        self.assertEqual([(ref.strip(), name) for ref, name, types in declared if layers.intersection(types)],
                         [("ref", "platformSoftware")])
        self.assertEqual([name for ref, name, _ in declared if ref], ["platformSoftware"])

    def test_the_configured_member_has_one_instance_and_one_owner_per_platform_layer(self):
        """The platform stack owns the derived adapter, the guest middleware and the guest operating
        system; three bindings make the references the same things. The body declares exactly the
        two parts and exactly these three bindings."""
        code = strip_comments(PHASE9_MODEL.read_text())
        member = braced_body(code, "part def MiddlewareAutowareAAOSSDVConfiguredMember")
        self.assertEqual(
            [(ref.strip(), name, types) for ref, name, types in _declarations(member)],
            [("", "platformStack", ["MiddlewareAutowareAAOSSDVReference"]),
             ("", "middlewareBoundary", ["MiddlewarePhysicalSoftwareBoundary"])],
        )
        own = " ".join(member.split())
        self.assertEqual(re.findall(r"\bbinding\s+(\w+)\s+bind\b", own),
                         ["adapterBoundToDerivedAdapter", "aaosSdvBoundaryBoundToGuestMiddleware",
                          "platformSoftwareBoundToGuestOperatingSystem"])
        for binding in ("binding adapterBoundToDerivedAdapter bind middlewareBoundary.adapter = "
                        "platformStack.applicationMiddlewareAdapter;",
                        "binding aaosSdvBoundaryBoundToGuestMiddleware bind middlewareBoundary.aaosSdvBoundary = "
                        "platformStack.guestMiddleware;",
                        "binding platformSoftwareBoundToGuestOperatingSystem bind "
                        "middlewareBoundary.aaosSdvBoundary.platformSoftware = platformStack.guestOSPlatform;"):
            with self.subTest(binding=binding):
                self.assertIn(binding, own)
        self.assertNotIn(":>>", member, "the member redefines no feature of its parts")
        # The platform stack owns the guest side once: the projection selects the guest operating
        # system and the guest middleware, and the middleware variant androidSDV refers to the
        # guest middleware (constraint C009).
        stack = " ".join(strip_comments(PLATFORM_STACK.read_text()).split())
        self.assertIn("variant ref part androidSDV : AndroidSDVMiddleware references guestMiddleware::androidSDV;",
                      stack)
        projection = PRODUCT_MODEL.read_text()
        self.assertIn("part :>> guestOSPlatform = guestOSPlatform::android;", projection)
        self.assertIn("part :>> guestMiddleware = guestMiddleware::androidSDV;", projection)

    def test_the_configuration_identity_keeps_its_evidence_and_records_the_structure_change(self):
        """MW-CONFIG-001 is not renumbered; the retained records still bind it. The configured
        member records both structure changes, the records that inherit them, and that the
        binding sharpens the headless-or-display discrepancy of INC-AEBS-010."""
        evidence = EVIDENCE_MODEL.read_text()
        self.assertEqual(evidence.count('attribute :>> configurationIdentity = "MW-CONFIG-001";'), 4)
        self.assertIn("subject claimSubject : MiddlewareIntegrationVandVBench;", evidence)
        self.assertIn("part system1MemberProduct : MiddlewareAutowareAAOSSDVConfiguredMember;", evidence)
        member = PHASE9_MODEL.read_text()
        usage = member[member.index("part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember"):]
        usage = " ".join(usage[:usage.index("\n  }\n")].replace("*", " ").split())
        for text in ("Configuration management note: under the owner decision of one owner per layer (2026-10-23), "
                     "the structure of this configured member changed twice.",
                     "The first change, narrowed to the adapter on 2026-10-25, removed the second adapter",
                     "Later on 2026-10-25 the owner decided to give the AAOS SDV guest one owner too.",
                     "So the open item about the duplicate guest in this member is closed.",
                     "Its platform stack also changed in INC-MW-011 phase 9",
                     "The identity MW-CONFIG-001 is not renumbered, and no variant selection changed in these two "
                     "changes.",
                     "E-MW-011 to E-MW-014 bind this identity, and BL-MW-010-P12 rests on them.",
                     "CLM-MW-010-01 and the other INC-MW-010 records take MiddlewareIntegrationVandVBench as "
                     "subject, whose System 1 part is typed by MiddlewareAutowareAAOSSDVConfiguredMember, so "
                     "they inherit the change.",
                     "So do the INC-AEBS-010 test article and its verification bench, and with them "
                     "EVID-AEBS-S2-001 to EVID-AEBS-S2-006, which bind AEBS-CONFIG-010-001.",
                     "baseline revision b8170f6953567b07164b8c02be05be137f8047f0. No record is edited.",
                     "the binding makes the guest middleware of this member a headless SDV Core boundary",
                     "It also composes a second AAOS SDV guest: the display-capable sdv_ivi_cf guest of its System 2 "
                     "instrument (iviGuest : SdvIviCfGuestTarget). Its evidence ran that image.",
                     "the binding now contradicts that statement.",
                     "So the binding sharpens the discrepancy that INC-AEBS-010 records.",
                     "stays a later owner decision."):
            with self.subTest(text=text):
                self.assertIn(text, usage)
        self.assertNotIn("Open item", usage)

    def test_pilot_is_framing_metadata_not_a_second_configuration_model(self):
        data = yaml.safe_load(PILOT.read_text())
        self.assertEqual(data["id"], "INC-MW-009")
        self.assertEqual(data["parent_increment"], "INC-MW-008")
        artifacts = data["model_artifacts"]
        self.assertEqual(artifacts["feature_model"], FEATURE_MODEL.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(artifacts["feature_configuration"], CONFIGURATION.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(artifacts["evidence_record"], EVIDENCE_RECORD.relative_to(REPO_ROOT).as_posix())
        for key in ("sysml", "feature_model", "feature_configuration", "evidence_record", "generated_projection"):
            self.assertTrue((REPO_ROOT / artifacts[key]).is_file(), key)
        self.assertNotIn("selections", data)
        self.assertNotIn("derived_adapter", data)
        self.assertIn("INC-MW-010", data["next_increments"])


if __name__ == "__main__":
    unittest.main()


# Ownership guards over the five validated model roots, with self-tests on synthetic inputs
# (never copies of model files).

KNOWN_GUEST_REFERENCES = {
    ("textual-notation-of-model/packages/architecture/aaos_sdv_middleware_boundary.sysml", "platformSoftware", False),
    ("textual-notation-of-model/packages/features/middleware/middleware_physical_software_realization.sysml",
     "aaosSdvBoundary", False),
}


def test_only_references_are_typed_by_the_aaos_sdv_boundary_definitions() -> None:
    """Every part usage typed by SDVCoreBoundary, SDVPlatformSoftwareBoundary or a specialization
    of one, and every part usage that redefines, subsets or reference-subsets aaosSdvBoundary or
    platformSoftware by name, is a reference: the platform stack owns the guest (owner decision of
    2026-10-25). The scan does not read feature-chain targets."""
    found = _sdv_core_boundary_usages(_guest_model_code())
    assert KNOWN_GUEST_REFERENCES <= found, "the scan must see the two guest references"
    assert sorted(usage for usage in found if usage[2]) == []


def test_the_member_and_its_specializations_compose_no_shared_layer_outside_the_platform_stack() -> None:
    """In typed part usages, the member (with its supertypes) and its specializations compose the
    shared layers only through platformStack, at any depth: AndroidHLOS, AndroidSDVMiddleware,
    AutowareToAAOSSDVAdapter, SDVCoreBoundary, SDVPlatformSoftwareBoundary, SdvIviCfGuestTarget and
    their specializations.
    The one named exception is the display guest of the INC-AEBS-010 test article (open owner
    decision on headless or display); shared layers inside its definition are still reported."""
    assert _composed_shared_layers(_guest_model_code()) == KNOWN_SECOND_GUEST


def test_the_guest_guards_scan_the_five_validated_model_roots() -> None:
    """The guards read every file that the licensed check validates: the five model roots of
    scripts/validate_sysml.py (AGENTS.md), feature models and configurations included, and no fixture."""
    scanned = set(_guest_model_code())
    roots = [model_path.as_posix() for model_path in VALIDATED_MODEL_ROOTS]
    assert roots == ["textual-notation-of-model", "model-based-product-line-engineering/product-models",
                     "model-based-product-line-engineering/scoping",
                     "model-based-product-line-engineering/feature-models",
                     "model-based-product-line-engineering/feature-configurations"]
    for root in roots:
        assert any(path.startswith(root + "/") for path in scanned), root
    assert FEATURE_MODEL.relative_to(REPO_ROOT).as_posix() in scanned
    assert CONFIGURATION.relative_to(REPO_ROOT).as_posix() in scanned
    assert not [path for path in scanned if "/fixtures/" in path]
    assert (PLE_ROOT / "feature-configurations" / "fixtures").is_dir(), "the fixture exclusion must be exercised"


_PROBE = "textual-notation-of-model/packages/probe/probe.sysml"


def _with_probe(monkeypatch, text: str, path: str = _PROBE) -> None:
    original = _guest_model_code
    monkeypatch.setattr(sys.modules[__name__], "_guest_model_code",
                        lambda: {**original(), path: reader._active(text)})


_COMPOSED_GUESTS = {
    "colon": "part def Probe { part extraGuest : SDVCoreBoundary; }",
    "defined-by": "part def Probe { part extraGuest defined by SDVCoreBoundary; }",
    "typed-by": "part def Probe { part extraGuest typed by Pkg::SDVPlatformSoftwareBoundary; }",
    "short-name": "part def Probe { part <'G-1'> extraGuest : SDVCoreBoundary; }",
    "typing-list": "part def Probe { part extraGuest : PhysicalAllocationElement, SDVCoreBoundary; }",
    "typed-redefinition": "part def Probe :> MiddlewarePhysicalSoftwareBoundary { part :>> aaosSdvBoundary : SDVCoreBoundary; }",
    "redefinition": "part def Probe :> MiddlewarePhysicalSoftwareBoundary { part :>> aaosSdvBoundary; }",
    "named-redefinition": "part def Probe :> SDVCoreBoundary { part os redefines platformSoftware; }",
    "subsetting": "part def Probe :> MiddlewarePhysicalSoftwareBoundary { part guestCopy :> aaosSdvBoundary; }",
    "subsets": "part def Probe :> MiddlewarePhysicalSoftwareBoundary { part guestCopy subsets aaosSdvBoundary; }",
    "reference-subsetting": "part def Probe :> SDVCoreBoundary { part os ::> platformSoftware; }",
    "references": "part def Probe :> SDVCoreBoundary { part os references platformSoftware; }",
    "specialization": "part def ExtraSDVCore :> DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary;"
                      " part extraCoreOwner { part extraCore : ExtraSDVCore; }",
    "package-level": "part extraCore : SDVCoreBoundary;",
}


@pytest.mark.parametrize("text", list(_COMPOSED_GUESTS.values()), ids=list(_COMPOSED_GUESTS))
def test_guest_reference_guard_refuses_a_composite_guest_in_every_form(monkeypatch, text: str) -> None:
    _with_probe(monkeypatch, text)
    with pytest.raises(AssertionError):
        test_only_references_are_typed_by_the_aaos_sdv_boundary_definitions()


@pytest.mark.parametrize("root", [model_path.as_posix() for model_path in VALIDATED_MODEL_ROOTS])
def test_guest_reference_guard_refuses_a_composite_guest_in_every_validated_root(monkeypatch, root: str) -> None:
    """A composite guest in a file of any validated root fails; feature models and configurations included."""
    _with_probe(monkeypatch, "part def Probe { part extraGuest : SDVCoreBoundary; }", f"{root}/probe.sysml")
    with pytest.raises(AssertionError):
        test_only_references_are_typed_by_the_aaos_sdv_boundary_definitions()


@pytest.mark.parametrize("text", [
    "part def Probe { ref part extraGuest : SDVCoreBoundary; }",
    "part def Probe { extraGuest : SDVCoreBoundary; }",
    "part def Probe :> MiddlewarePhysicalSoftwareBoundary { ref part :>> aaosSdvBoundary; }",
    "part def Probe :> MiddlewarePhysicalSoftwareBoundary { ref part guestCopy :> aaosSdvBoundary; }",
    "part def Probe { /* part extraGuest : SDVCoreBoundary; */ }",
    'part def Probe { attribute note = "part extraGuest : SDVCoreBoundary;"; }',
], ids=["ref-part", "reference-usage", "ref-redefinition", "ref-subsetting", "comment", "string"])
def test_guest_reference_guard_accepts_references(monkeypatch, text: str) -> None:
    """Positive controls: references, comments and strings are no composite guest."""
    _with_probe(monkeypatch, text)
    test_only_references_are_typed_by_the_aaos_sdv_boundary_definitions()


_SECOND_LAYERS = {
    "guest-middleware": "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part secondGuest : AndroidSDVMiddleware; }",
    "guest-os": "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part secondOS : DE4SDV_SDVPlatformStack::AndroidHLOS; }",
    "adapter": "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part secondAdapter : AutowareToAAOSSDVAdapterPhysical; }",
    "display-guest": "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part secondDisplay : SdvIviCfGuestTarget; }",
    "nested-in-a-part": "part def Holder { part inner { part guest : AndroidHLOS; } }"
                        " part def Probe :> AEBSAutowareAAOSSDVVisualizationTestArticle { part holder : Holder; }",
    "through-a-supertype": "part def Base { part guest : SDVCoreBoundary; } part def Holder :> Base;"
                           " part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part holder : Holder; }",
    "specialized-guest": "part def ExtraGuest :> AndroidSDVMiddleware;"
                         " part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part guest defined by ExtraGuest; }",
    # A second declaration of a definition adds its body to the walk, as a model edit would.
    "inside-the-excepted-guest-definition": "part def SdvIviCfGuestTarget { part guestMiddleware : AndroidSDVMiddleware; }",
    "in-a-supertype-of-the-member": "part def AAOSIntegratedAutowareAEBSReferenceMember { part extraGuest : AndroidSDVMiddleware; }",
}


@pytest.mark.parametrize("text", list(_SECOND_LAYERS.values()), ids=list(_SECOND_LAYERS))
def test_member_guard_refuses_a_second_composite_layer(monkeypatch, text: str) -> None:
    _with_probe(monkeypatch, text)
    with pytest.raises(AssertionError):
        test_the_member_and_its_specializations_compose_no_shared_layer_outside_the_platform_stack()


def test_member_walk_reports_shared_layers_inside_the_definition_of_a_hit() -> None:
    """On a hit the walk still reads the hit's definitions, so an exception never hides what its
    definition composes."""
    code = {_PROBE: reader._active(
        "part def MiddlewareAutowareAAOSSDVConfiguredMember { part display : Guest; }"
        " part def Guest :> SdvIviCfGuestTarget { part os : AndroidHLOS; }")}
    assert _composed_shared_layers(code) == {
        ("MiddlewareAutowareAAOSSDVConfiguredMember", "display", "Guest"),
        ("MiddlewareAutowareAAOSSDVConfiguredMember", "display.os", "AndroidHLOS"),
    }


@pytest.mark.parametrize("text", [
    "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { ref part guest : AndroidSDVMiddleware; }",
    "part def Probe :> MiddlewareAutowareAAOSSDVConfiguredMember { part :>> platformStack : MiddlewareAutowareAAOSSDVReference; }",
    "part def Bench { part guest : AndroidHLOS; }",
], ids=["reference", "platform-stack", "outside-the-member-lineage"])
def test_member_guard_accepts_what_is_no_second_owner(monkeypatch, text: str) -> None:
    """Positive controls: a reference, the platform stack itself, and a context outside the member lineage."""
    _with_probe(monkeypatch, text)
    test_the_member_and_its_specializations_compose_no_shared_layer_outside_the_platform_stack()
