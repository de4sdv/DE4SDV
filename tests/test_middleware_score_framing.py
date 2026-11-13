"""Content pins for the INC-MW-011 framing concerns, not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "textual-notation-of-model/packages/features/middleware/middleware_score_framing.sysml"


def test_the_hmi_domain_concern_asks_a_physical_context_exchange_question():
    """The HMI path names concrete platforms: S-CORE on the Linux host, the AAOS SDV guest and the
    hypervisor boundary between them. Which items cross the system boundary to the guest, one way, is the
    SAF Physical-domain context-exchange question, not the Conceptual functional-interface one, whose
    definition is about candidate VSS extension signals."""
    code = strip_comments(MODEL.read_text(encoding="utf-8"))
    assert re.search(r"\bconcern\s+hmiDomainBoundaryConcern\s*:\s*PhysicalContextExchangeConcern\s*\{", code)
    body = braced_body(code, "concern hmiDomainBoundaryConcern : PhysicalContextExchangeConcern")
    assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == [
        ("occupant", "VehicleOccupant"), ("systemArchitect", "SystemArchitect"),
        ("safetyExpert", "SafetyExpert"), ("verificationEngineer", "VerificationEngineer")]
    assert "frame hmiDomainBoundaryConcern;" in code
