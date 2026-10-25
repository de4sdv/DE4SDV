"""INC-MW-009: the configured Autoware + AAOS SDV member (ADR 0022).

The member's PLEML feature configuration selects the application and the
middleware; the receipt derives the adapter, which no configuration selects;
the committed projection regenerates from the receipt byte for byte. The
configured member has one adapter with one owner (owner decisions of 2026-10-23
and 2026-10-25): the platform stack owns the derived adapter, the middleware
boundary refers to it, and a binding makes the reference the same thing. The
second representation of the AAOS SDV guest in the boundary is an open item.
"""
import json
import re
import unittest
from pathlib import Path

import yaml

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
#: SDVCoreBoundary models the internal structure of the AAOS SDV middleware layer
#: (the doc of AndroidSDVMiddleware in the platform stack), so it stands for that layer.
AAOS_SDV_MIDDLEWARE_MODEL = "SDVCoreBoundary"
#: Head of a part definition with its specialization list: ``part def X :> A, P::B {``.
_SPECIALIZATION = re.compile(r"\bpart\s+def\s+(?:<'[^']*'>\s*)?(\w+)\s*(?::>|\bspecializes\b)\s*([^{;]+)")
#: Head of a part usage with its typing list: ``ref part x : A, P::B[1] {`` (not ``:>`` or ``:>>``).
_TYPED_USAGE = re.compile(r"\b(ref\s+)?part\s+(\w+)\s*:(?![>:])\s*([^{;=]+)")


def _names(type_list: str) -> list[str]:
    """Every simple name in a typing or specialization list, multiplicities removed."""
    return [name.strip().rsplit("::", 1)[-1] for name in re.sub(r"\[[^\]]*\]", "", type_list).split(",")
            if name.strip()]
PILOT = (
    REPO_ROOT
    / "methodologies"
    / "sysmod-sysmlv2"
    / "pilots"
    / "middleware-variability-configuration.yaml"
)


def _receipt_model():
    receipt = json.loads(RECEIPT.read_text())
    [model] = receipt["evaluation"]["feature_models"]
    return model


def _platform_layer_definitions() -> set[str]:
    """The layer definitions of the SDV platform stack, their realizations, and every
    specialization of them in the physical slice (lexical, transitive). Every general
    definition of a specialization list counts, not only the first."""
    specializations = []
    for path in (PLATFORM_STACK, PHYSICAL_MODEL):
        specializations += [(name, _names(generals))
                            for name, generals in _SPECIALIZATION.findall(strip_comments(path.read_text()))]
    layers = set(re.findall(r"\bpart\s+def\s+(\w+Layer)\b", strip_comments(PLATFORM_STACK.read_text())))
    assert len(layers) == 6, layers
    grown = True
    while grown:
        grown = False
        for name, generals in specializations:
            if layers.intersection(generals) and name not in layers:
                layers.add(name)
                grown = True
    return layers | {AAOS_SDV_MIDDLEWARE_MODEL}


def _declarations(body: str) -> list[tuple[str, str, list[str]]]:
    """``(ref keyword or '', name, types)`` of the part usages declared directly in ``body``.
    ``types`` holds every definition of the typing list, not only the first."""
    flat, depth = [], 0
    for character in body:
        depth += (character == "{") - (character == "}")
        if depth == 0 and character != "}":
            flat.append(character)
    return [(ref, name, _names(types)) for ref, name, types in _TYPED_USAGE.findall("".join(flat))]


class TestLayerGuardReadsWholeLists(unittest.TestCase):
    """The guard helpers read every name of a typing or specialization list (form review R3)."""

    def test_typing_lists(self):
        body = "part a : SignalAccessClient, AutowareToAAOSSDVAdapterPhysical; ref part b : P::X[1] { part c : Y; }"
        self.assertEqual(_declarations(body), [("", "a", ["SignalAccessClient", "AutowareToAAOSSDVAdapterPhysical"]),
                                               ("ref ", "b", ["X"])])
        self.assertEqual(_declarations("part :>> a = b; part x :> y; part z :>> w;"), [])

    def test_specialization_lists(self):
        self.assertEqual(_SPECIALIZATION.findall("part def X :> PhysicalAllocationElement, AutowareToAAOSSDVAdapter { }"),
                         [("X", "PhysicalAllocationElement, AutowareToAAOSSDVAdapter ")])
        self.assertEqual(_names("PhysicalAllocationElement, DE4SDV_SDVPlatformStack::AutowareToAAOSSDVAdapter "),
                         ["PhysicalAllocationElement", "AutowareToAAOSSDVAdapter"])


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
        self.assertFalse({"platformStack.noMiddleware", "platformStack.android", "platformStack.noGuestOS",
                          "platformStack.noGuestMiddleware", "capabilities.hmiDisplay", "sensingBoundary.radar"}
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

    def test_the_boundary_refers_to_the_adapter_layer(self):
        """The middleware boundary refers to the adapter and does not own it (owner decisions of
        2026-10-23 and 2026-10-25, narrowed to the adapter).

        aaosSdvBoundary still stands for the AAOS SDV guest middleware and stays composite: the
        open item of 2026-10-25. Every other part of the boundary is typed by no platform layer."""
        layers = _platform_layer_definitions()
        self.assertIn("AutowareToAAOSSDVAdapterPhysical", layers)
        boundary = braced_body(strip_comments(PHYSICAL_MODEL.read_text()), "part def MiddlewarePhysicalSoftwareBoundary")
        declared = _declarations(boundary)
        self.assertEqual(len(declared), 9)
        layered = [(ref.strip(), name) for ref, name, types in declared if layers.intersection(types)]
        self.assertEqual(layered, [("ref", "adapter"), ("", "aaosSdvBoundary")])
        self.assertEqual([name for ref, name, _ in declared if ref], ["adapter"])

    def test_the_configured_member_has_one_adapter_with_one_owner(self):
        """The platform stack owns the derived adapter; one binding makes the adapter reference of
        the boundary the same thing. The body declares exactly the two parts and this binding."""
        code = strip_comments(PHASE9_MODEL.read_text())
        member = braced_body(code, "part def MiddlewareAutowareAAOSSDVConfiguredMember")
        self.assertEqual(
            [(ref.strip(), name, types) for ref, name, types in _declarations(member)],
            [("", "platformStack", ["MiddlewareAutowareAAOSSDVReference"]),
             ("", "middlewareBoundary", ["MiddlewarePhysicalSoftwareBoundary"])],
        )
        own = " ".join(member.split())
        self.assertEqual(re.findall(r"\bbinding\s+(\w+)\s+bind\b", own), ["adapterBoundToDerivedAdapter"])
        self.assertIn("binding adapterBoundToDerivedAdapter bind middlewareBoundary.adapter = "
                      "platformStack.applicationMiddlewareAdapter;", own)
        self.assertNotIn(":>>", member, "the member redefines no feature of its parts")

    def test_the_configuration_identity_keeps_its_evidence_and_records_the_structure_change(self):
        """MW-CONFIG-001 is not renumbered; the retained records still bind it. The configured
        member records the change, the records that inherit it, and the open AAOS SDV guest item."""
        evidence = EVIDENCE_MODEL.read_text()
        self.assertEqual(evidence.count('attribute :>> configurationIdentity = "MW-CONFIG-001";'), 4)
        self.assertIn("subject claimSubject : MiddlewareIntegrationVandVBench;", evidence)
        self.assertIn("part system1MemberProduct : MiddlewareAutowareAAOSSDVConfiguredMember;", evidence)
        member = PHASE9_MODEL.read_text()
        usage = member[member.index("part configuredMember : MiddlewareAutowareAAOSSDVConfiguredMember"):]
        usage = " ".join(usage[:usage.index("\n  }\n")].replace("*", " ").split())
        for text in ("Configuration management note: on 2026-10-23 the owner decided one owner per layer",
                     "on 2026-10-25 the owner narrowed the change to the adapter.",
                     "The identity MW-CONFIG-001 is not renumbered, and no variant selection changed.",
                     "E-MW-011 to E-MW-014 bind this identity, and BL-MW-010-P12 rests on them.",
                     "CLM-MW-010-01 and the other INC-MW-010 records take MiddlewareIntegrationVandVBench as "
                     "subject, whose System 1 part is typed by MiddlewareAutowareAAOSSDVConfiguredMember, so "
                     "they inherit the change.",
                     "So do the INC-AEBS-010 test article and its verification bench.",
                     "baseline revision b8170f6953567b07164b8c02be05be137f8047f0. No record is edited.",
                     "Open item (owner decision of 2026-10-25): the middleware boundary still represents the "
                     "AAOS SDV guest a second time (aaosSdvBoundary)",
                     "platformSoftware: GKI, drivers, HALs",
                     "headless sdv_core_cf image, while the INC-AEBS-010 evidence ran the display-capable "
                     "sdv_ivi_cf image.",
                     "is a later owner decision."):
            with self.subTest(text=text):
                self.assertIn(text, usage)

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
