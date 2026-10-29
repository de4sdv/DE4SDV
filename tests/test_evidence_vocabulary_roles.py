"""Evidence and assurance vocabulary roles: lexical source checks only.

These pin model-resident documentation of approved semantic direction
(topics 3 and 4, W5 external-reference rows). They are not licensed Syside
evidence, runtime admission, traversal or acceptance.
"""
from pathlib import Path
import re

import pytest
import yaml

from de4sdv.semantic.authority_inventory import normalize_text

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "textual-notation-of-model/packages/methods/de4sdv/"
CONTEXT = KERNEL + "de4sdv_method_context.sysml"
OPERATIONAL = KERNEL + "de4sdv_operational_context.sysml"

# role name -> (file, annotated elements, required phrases)
ROLES = {
    "EvidenceArtifactVocabularyRole": (
        CONTEXT, "EvidenceArtifactOntologyDefinition",
        ("content is external", "no authority", "de4sdv.evidence-reference/v1", "No artifact bytes")),
    # Annotates the EvidenceArtifact home, not the whole package (PR #328 escape class).
    "hasEvidenceVocabularyRole": (
        CONTEXT, "EvidenceArtifactOntologyDefinition",
        ("artifact association only", "content external, no authority", "no traversal",
         "not supportedByEvidence")),
    "supportedByEvidenceVocabularyRole": (
        CONTEXT, "AssuranceClaimOntologyDefinition",
        ("cited support", "distinct from hasEvidence", "rationale", "known limits",
         "adequacy assessment of the evidence set", "coverage, confidence and rigor bases",
         "an adequate set can establish a negative conclusion",
         "the assessor's scoped conclusion, not checker truth", "AcceptanceAttestationReference",
         "never imply each other", "Vocabulary only")),
    "hasEvidenceStatusVocabularyRole": (
        CONTEXT, "EvidenceStatusOntologyDefinition",
        ("unchanged adopted VVStatus", "exactly one verification or one validation",
         "needs, requirements, designs, production outputs",
         "CompletedUnsuccessful could not complete", "CompletedFailed completed with technical failure",
         "CompletedPassed completed successfully against the activity basis only, not a broader scoped claim",
         "No new universal status enum", "Completed never means passed", "Retirement", "no new model usage")),
    "BaselineVocabularyRole": (
        OPERATIONAL, "DE4SDVEvidenceBaseline",
        ("content is external", "no authority", "no second mutable baseline list")),
    "capturedInBaselineVocabularyRole": (
        OPERATIONAL, "DE4SDVEvidenceBaseline",
        ("content external, no authority", "de4sdv.baseline-manifest-reference/v1",
         "never approves evidence", "no traversal")),
    "ArchitectureDecisionRecordVocabularyRole": (
        CONTEXT, "ArchitectureDecisionRecord",
        ("content is external", "no authority", "does not mirror")),
}


def _role(path, name):
    text = (ROOT / path).read_text()
    found = re.findall(r"\bcomment\s+" + name + r"\b\s*(?:about\s+([\w\s,:]+?))?\s*/\*(.*?)\*/", text, re.S)
    return found


@pytest.mark.parametrize("name", sorted(ROLES))
def test_evidence_vocabulary_role_is_unique_and_states_its_boundary(name):
    path, about, phrases = ROLES[name]
    assert about, (name, "every role must name its annotated element")
    homes = [p for p in sorted((ROOT / KERNEL).glob("*.sysml")) if re.search(r"\bcomment\s+" + name + r"\b", p.read_text())]
    assert [p.relative_to(ROOT).as_posix() for p in homes] == [path], name
    found = _role(path, name)
    assert len(found) == 1, name
    target, body = found[0]
    assert target and normalize_text(target) == normalize_text(about), (name, target)
    body = normalize_text(body.replace("*", " "))
    for phrase in phrases:
        assert normalize_text(phrase) in body, (name, phrase)


def test_status_successor_adds_no_universal_status_enum_and_keeps_legacy_name():
    # The kernel enum population is pinned: a status successor must reuse VVStatus.
    # LifecycleDisposition (owner decision of 2026-10-28, Q2) is a decision outcome
    # of phase 12 (accepted, deferred, invalidated), not a status or a verdict.
    enums = set()
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        enums |= set(re.findall(r"\benum\s+def\s+(\w+)", active))
    assert enums == {"MethodPhase", "SignalMappingDisposition", "IncrementSize", "EvaluationSourceKind",
                     "PriorityKind", "StakeholderCategoryKind", "LifecycleDisposition"}, enums
    # No status vocabulary under another definition kind or name either.
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        assert not re.search(r"\bdef\s+\w*(?:Status|Verdict)\w*", active), path.name
        assert not re.search(r"\battribute\s+def\b", active), (path.name, "attribute def outside the pinned kernel")
    # The old names stay vocabulary of the model-built contract (O4 Wave C2:
    # the authored YAML is deleted; the batch-2 projection rows carry them).
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from model_contract_fixtures import model_contract

    contract = model_contract()
    for name, (domain, range_) in {"hasEvidenceStatus": ("EvidenceArtifact", "EvidenceStatus"),
                                   "supportedByEvidence": ("AssuranceClaim", "EvidenceArtifact")}.items():
        spec = contract.relationships[name]
        assert (spec["domain"], spec["range"]) == (domain, range_), name
        assert "sysml_mapping" not in spec, name
    assert contract.relationship_mapping("hasEvidence").strategy == "external"


def test_external_boundary_rows_gain_no_model_content_mirror():
    """W5 rows stay external-reference contracts: no new definition mirrors
    artifact, baseline or ADR content, and the accepted profile keeps its
    declaration-free reference records."""
    profile = yaml.safe_load((ROOT / "de4sdv/semantic/contract-data/external-reference-profile.yaml").read_text())
    entries = {row["identity"]: row for row in profile["profile_entries"]}
    for identity in ("EvidenceArtifact", "hasEvidence", "capturedInBaseline"):
        assert entries[identity]["declaration"] is None
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        assert not re.search(r"\bdef\s+(?:EvidenceArtifact|Baseline|BaselineManifest)\w*\b", active), path.name


#: The VVStatus literals of the exact-pinned ODE4HERA library that the served
#: hasEvidenceStatus text and the glossary rely on.
ADOPTED_VV_STATUSES = {"NotStarted", "InProgress", "Completed", "CompletedUnsuccessful",
                       "CompletedFailed", "CompletedPassed"}
ODE4HERA = "pkg:sysand/ode4hera/requirements-management"


def _installed_requirements_management() -> Path:
    """The synced ODE4HERA library (``sysand sync``), matched to the lock's exact pin.

    Read here, in a test, only: the runtime never reads a library source."""
    import tomllib

    lock = tomllib.loads((ROOT / "sysand-lock.toml").read_text(encoding="utf-8"))
    (pin,) = [p for p in lock["project"] if ODE4HERA in p.get("identifiers", [])]
    env = tomllib.loads((ROOT / ".sysand/env.toml").read_text(encoding="utf-8"))
    (installed,) = [p for p in env["project"] if ODE4HERA in p.get("identifiers", [])]
    assert installed["version"] == pin["version"]
    assert installed["kpar_cksum"] == pin["sources"][0]["kpar_digest"]
    return ROOT / ".sysand" / installed["path"] / "RequirementsManagement.sysml"


def _enum_literals(source: str, name: str) -> list[str]:
    """Direct literals of one enum definition, read lexically with comments removed."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", " ", source, flags=re.S)
    (start,) = [m.end() for m in re.finditer(r"\benum\s+def\s+" + name + r"\s*\{", code)]
    tokens = re.findall(r"[{};]|[A-Za-z_]\w*", code[start:])
    literals, depth = [], 1
    for token, following in zip(tokens, tokens[1:] + [""]):
        if token == "{":
            depth += 1
        elif token == "}":
            depth -= 1
            if depth == 0:
                return literals
        elif depth == 1 and token not in (";", "doc") and following in ("{", ";"):
            literals.append(token)
    raise AssertionError(f"enum def {name} is not closed")


def test_the_served_status_text_names_only_the_pinned_vvstatus_literals():
    literals = _enum_literals(_installed_requirements_management().read_text(encoding="utf-8"), "VVStatus")
    assert len(literals) == len(set(literals)) and set(literals) == ADOPTED_VV_STATUSES, literals
    (found,) = _role(CONTEXT, "hasEvidenceStatusVocabularyRole")
    named = set(re.findall(r"\b(?:NotStarted|InProgress|Completed\w*)\b", found[1]))
    assert {"Completed", "CompletedUnsuccessful", "CompletedFailed", "CompletedPassed"} <= named
    assert named <= ADOPTED_VV_STATUSES, named - ADOPTED_VV_STATUSES


def test_a_changed_vvstatus_population_would_be_noticed():
    library = _installed_requirements_management().read_text(encoding="utf-8")
    grown = library.replace("enum def VVStatus {", "enum def VVStatus {\n        SignedOff { doc /* synthetic */ }", 1)
    assert set(_enum_literals(grown, "VVStatus")) == ADOPTED_VV_STATUSES | {"SignedOff"}
