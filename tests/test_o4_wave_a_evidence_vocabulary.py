"""O4 Wave A evidence/assurance vocabulary roles: lexical source checks only.

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
ASSURANCE = KERNEL + "de4sdv_scoped_assurance.sysml"
CONTEXT = KERNEL + "de4sdv_method_context.sysml"
OPERATIONAL = KERNEL + "de4sdv_operational_context.sysml"

# role name -> (file, annotated elements, required phrases)
ROLES = {
    "EvidenceArtifactVocabularyRole": (
        ASSURANCE, "EvidenceArtifactOntologyDefinition",
        ("content is external", "no authority", "de4sdv.evidence-reference/v1", "No artifact bytes")),
    # Annotates the EvidenceArtifact home, not the whole package (PR #328 escape class).
    "hasEvidenceVocabularyRole": (
        ASSURANCE, "EvidenceArtifactOntologyDefinition",
        ("artifact association only", "content external, no authority", "no traversal",
         "not supportedByEvidence")),
    "supportedByEvidenceVocabularyRole": (
        ASSURANCE, "EvidenceSupportCitation, ScopedEvidenceAdequacyAssessment",
        ("cited support", "distinct from hasEvidence", "rationale", "known limits",
         "ScopedEvidenceAdequacyAssessment of the evidence set", "AcceptanceAttestationReference",
         "never imply each other", "Vocabulary only")),
    "hasEvidenceStatusVocabularyRole": (
        ASSURANCE, "ScopedVVActivityRecord",
        ("unchanged adopted VVStatus", "No new universal status enum", "Completed never means passed",
         "Retirement", "no new model usage")),
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


def _direct_body(text, header):
    """Direct members of the one ``header {`` block: nested bodies are blanked."""
    starts = [m.end() - 1 for m in re.finditer(header + r"\s*\{", text)]
    assert len(starts) == 1, header
    out, depth = [], 0
    for char in text[starts[0]:]:
        if char == "}":
            depth -= 1
            if depth == 0:
                return "".join(out)
        out.append(char if depth <= 1 else " ")
        if char == "{":
            depth += 1
    raise AssertionError("unclosed block")


def test_supported_by_evidence_adequacy_reuses_typed_citations():
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", (ROOT / ASSURANCE).read_text(), flags=re.S)
    direct = _direct_body(text, r"\bitem\s+def\s+ScopedEvidenceAdequacyAssessment\b")
    # Directly owned by the assessment, exactly once; never nested or relocated.
    assert len(re.findall(r"\bref\s+item\s+citations\s*:\s*EvidenceSupportCitation\[\*\]\s*;", direct)) == 1
    assert len(re.findall(r"\bcitations\b", text)) == 1, "citations must have exactly one owner"


def test_status_successor_adds_no_universal_status_enum_and_keeps_legacy_name():
    # The kernel enum population is pinned: a status successor must reuse VVStatus.
    enums = set()
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        enums |= set(re.findall(r"\benum\s+def\s+(\w+)", active))
    assert enums == {"MethodPhase", "SignalMappingDisposition", "IncrementSize", "EvaluationSourceKind",
                     "TraceCompletionClaim", "PriorityKind", "StakeholderCategoryKind"}, enums
    # No status vocabulary under another definition kind or name either.
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        assert not re.search(r"\bdef\s+\w*(?:Status|Verdict)\w*", active), path.name
        assert not re.search(r"\battribute\s+def\b", active), (path.name, "attribute def outside the pinned kernel")
    active = re.sub(r"/\*.*?\*/", " ", (ROOT / ASSURANCE).read_text(), flags=re.S)
    assert re.search(r"attribute\s+status\s*:\s*VVStatus\s*;", active)
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
    profile = yaml.safe_load((ROOT / "docs/method-conformance/o4/external-reference-profile.yaml").read_text())
    entries = {row["identity"]: row for row in profile["profile_entries"]}
    for identity in ("EvidenceArtifact", "hasEvidence", "capturedInBaseline"):
        assert entries[identity]["declaration"] is None
    for path in sorted((ROOT / KERNEL).glob("*.sysml")):
        active = re.sub(r"/\*.*?\*/|//[^\n]*", " ", path.read_text(), flags=re.S)
        assert not re.search(r"\bdef\s+(?:EvidenceArtifact|Baseline|BaselineManifest)\w*\b", active), path.name


def test_scoped_assurance_native_population_still_matches_supplied_record_adapter(monkeypatch):
    from de4sdv.semantic import scoped_assurance

    monkeypatch.setattr(scoped_assurance, "_installed_adopted_statuses", lambda root: {
        "NotStarted", "InProgress", "Completed", "CompletedUnsuccessful", "CompletedFailed", "CompletedPassed"})
    monkeypatch.setattr(scoped_assurance, "_adopted_library_pin",
                        lambda root: ({}, {"kpar_digest": "x", "kpar_size": 0}))
    report = scoped_assurance.verify_native_sources()
    assert report["model_declarations"] == [
        "EvidenceSupportCitation", "ScopedVVActivityRecord", "ScopedEvidenceAdequacyAssessment"]
    assert report["native_semantic_validation"] is False
