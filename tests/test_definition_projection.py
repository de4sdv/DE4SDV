"""O4 definition-admission batch 1 — governed, fail-closed, separated outputs.

The machinery admits exactly the 21 pinned rows of
``docs/method-conformance/o4/definition-admission.yaml`` (retained, ungated
W2 definitions-parity rows requiring both a generated projection row and an
API-representation-profile entry). Each admitted identity is backed by a
model-resident declaration whose owned documentation carries — or is
bounded-review-equivalent to — the reviewed definition.

Boundaries machine-locked here: the admitted set equals the register-derived
family; every anchor resolves and the recomputed documentation observation
matches the manifest; ``differs`` requires a recorded ``reviewed-equivalent``
review; generated rows carry no O1 governance fields and stay
``vocabulary-only`` with traversal false and no API identity claim; the
generator never reads O1 artifacts; the runtime never imports this machinery.
The committed-artifact test is the Commit-B gate (red between the A1 input
commit and the A2 artifact commit by design).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = "docs/method-conformance/o4/definition-admission.yaml"
DESIGN_PATH = "docs/method-conformance/o4/definition-admission-design.md"
MODULE_PATH = "de4sdv/semantic/definition_projection.py"
GENERATOR_PATH = "scripts/generate_definition_projection.py"
#: The two shared modules the generation path EXECUTES (proved by the
#: executed-path audit) and therefore must bind as generation software.
AUTHORITY_INVENTORY_PATH = "de4sdv/semantic/authority_inventory.py"
PROJECTION_O2P_PATH = "de4sdv/semantic/projection_o2p.py"
BOUND_PROGRAM_INPUTS = (
    MODULE_PATH,
    GENERATOR_PATH,
    AUTHORITY_INVENTORY_PATH,
    PROJECTION_O2P_PATH,
)
_MODEL_FILE = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml"
)
#: The governed model files carrying the admitted declarations of the real
#: manifest (all four participate in the real bound-input set).
_MODEL_FILES = (
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_context.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_process.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_operational_context.sysml",
    "textual-notation-of-model/packages/methods/de4sdv/de4sdv_product_line.sysml",
)

ADMITTED_ROWS = (
    "Assumption",
    "BlockedRealizationBranchRecord",
    "DeferredProductLineScope",
    "EngineeringIncrement",
    "FeatureIncrement",
    "Gap",
    "IncrementEngineeringQuestion",
    "IncrementLifecycleDecision",
    "LogicalToSoftwareSignalMappingRecord",
    "MemberProduct",
    "MissingRealizationRecord",
    "Need",
    "NeedsRequirementsIncrement",
    "ProblemStatement",
    "ProductLine",
    "ProductLineCharacteristic",
    "RegulatoryConstraint",
    "Requirement",
    "Scenario",
    "SignalMappingDisposition",
    "SystemLayer",
    "SystemToSoftwareSignalMappingCandidate",
)

TREATED_STAGE = "o4 definition admission batch 1 (projection + profile)"

#: Layer-B reviewed-decision field names that must never leak into generated
#: semantic rows (identical to the O1 governance guard used by the other
#: projection suites).
O1_GOVERNANCE_FIELDS = (
    "authority_current",
    "authority_target",
    "evidence_state",
    "adoption_status",
    "transition_gate",
    "conditional_target",
    "disposition",
    "confidence",
    "stage",
    "unknowns",
    "required_evidence",
    "exact_fit_decision",
)

_FIXTURE_MANIFEST = {
    "schema": "de4sdv.o4-definition-admission/v1",
    "status": "admitted",
    "warning": "fixture",
    "admitted": [
        {
            "identity": "FixtureAlpha",
            "semantic_kind": "class",
            "wave": "W2",
            "stage": "fixture",
            "declaration": {"file": _MODEL_FILE, "declaration": "part def FixtureAlpha"},
            "evidence_state": "repository-evidenced",
            "authority_current": "legacy-yaml",
            "reviewed_definition": "An exact fixture definition for alpha.",
            "expected_documentation_observation": "normalized-exact",
            "semantic_text_equivalence": None,
            "required_runtime_support_target": (
                "runtime-queryable (post-migration, exact-revision evidence required)"
            ),
        },
        {
            "identity": "FixtureBeta",
            "semantic_kind": "class",
            "wave": "W2",
            "stage": "fixture",
            "declaration": {"file": _MODEL_FILE, "declaration": "part def FixtureBeta"},
            "evidence_state": "repository-evidenced",
            "authority_current": "legacy-yaml",
            "reviewed_definition": "A differing fixture definition for beta.",
            "expected_documentation_observation": "differs",
            "semantic_text_equivalence": "reviewed-equivalent",
            "required_runtime_support_target": (
                "runtime-queryable (post-migration, exact-revision evidence required)"
            ),
        },
    ],
}

_FIXTURE_SYSML = """package FixtureDefinitions {
  part def FixtureAlpha {
    doc /* An exact fixture definition for alpha. */
  }
  part def FixtureBeta {
    doc /* A differing fixture definition for beta that carries extra words. */
  }
}
"""


# ---------------------------------------------------------------------------
# 1. The real committed admission
# ---------------------------------------------------------------------------


def test_manifest_scope_is_exactly_the_admitted_family():
    from de4sdv.semantic.definition_projection import load_document

    document = load_document(REPO_ROOT)
    admitted = [row["identity"] for row in document["admitted"]]
    assert sorted(admitted) == list(ADMITTED_ROWS)
    assert len(admitted) == 22


def test_family_invariant_from_canonical_governance():
    """admitted == structural register family ∩ parity stage − other admissions."""
    from de4sdv.semantic.definition_projection import load_document
    from de4sdv.semantic.o3_bundle import MIGRATED_IDENTITIES

    register = json.loads(
        (
            REPO_ROOT / "docs/method-conformance/o4/o4-execution-register.json"
        ).read_text(encoding="utf-8")
    )
    decisions = yaml.safe_load(
        (
            REPO_ROOT / "docs/method-conformance/o1/authority-review-decisions.yaml"
        ).read_text(encoding="utf-8")
    )["entries"]

    other = set()
    v1 = json.loads(
        (REPO_ROOT / "docs/method-conformance/o2/semantic-projection-v1.json").read_text()
    )
    other |= {row["identity"] for row in v1["concepts"]}
    v11 = json.loads(
        (REPO_ROOT / "docs/method-conformance/o2/semantic-projection-v1.1.json").read_text()
    )
    other |= {row["identity"] for row in v11["concepts"] + v11["predicates"]}
    v12 = json.loads(
        (REPO_ROOT / "docs/method-conformance/o2/semantic-projection-v1.2.json").read_text()
    )
    other |= {row["identity"] for row in v12["predicates"]}
    o2p = json.loads(
        (
            REPO_ROOT / "docs/method-conformance/o2plus/semantic-projection-o2plus.json"
        ).read_text()
    )
    other |= {row["identity"] for row in o2p["rows"]}
    carriers = json.loads(
        (
            REPO_ROOT / "docs/method-conformance/o4/vocabulary-carriers-projection.json"
        ).read_text()
    )
    other |= {row["identity"] for row in carriers["rows"]}

    family = set()
    for row in register["rows"]:
        if row["membership"] != "o4-target" or row["o3_complete"] is not False:
            continue
        if row["base_wave"] not in {"W2", "W5"}:
            continue
        if row["gate_decisions"] or row["gate_wave"] is not None:
            continue
        if not (
            row["required_semantic_projection_change"]
            and row["required_api_representation_profile_change"]
        ):
            continue
        stage = str((decisions[row["identity"]] or {}).get("stage") or "")
        if "definitions parity" not in stage and stage != TREATED_STAGE:
            continue
        family.add(row["identity"])

    expected = family - other - set(MIGRATED_IDENTITIES)
    document = load_document(REPO_ROOT)
    assert sorted(expected) == sorted(row["identity"] for row in document["admitted"])
    # The frozen O3 thirteen are structurally excluded from this layer.
    assert not (set(ADMITTED_ROWS) & set(MIGRATED_IDENTITIES))


def test_every_admitted_row_resolves_and_recomputes_expected_observation():
    from de4sdv.semantic.authority_inventory import doc_text_observation

    from de4sdv.semantic.definition_projection import build_outputs, load_document

    document = load_document(REPO_ROOT)
    outputs = build_outputs(REPO_ROOT, document)
    for row in outputs["projection_rows"]:
        witness = row["definition"]["documentation_witness"]
        file_text = (REPO_ROOT / witness["source_file"]).read_text(encoding="utf-8")
        assert witness["doc_count"] >= 1, row["identity"]
        assert row["definition"]["documentation"].strip(), row["identity"]
        if row["definition"]["documentation_observation"] == "differs":
            assert row["definition"]["semantic_text_equivalence"] == "reviewed-equivalent"

    # Independent recomputation against the manifest oracle.
    manifest = yaml.safe_load((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    for admitted in manifest["admitted"]:
        file_text = (REPO_ROOT / admitted["declaration"]["file"]).read_text(encoding="utf-8")
        observation = doc_text_observation(
            file_text, admitted["declaration"]["declaration"], admitted["reviewed_definition"]
        )
        assert observation == admitted["expected_documentation_observation"], admitted["identity"]


def test_generated_rows_stay_vocabulary_only_and_free_of_governance_fields():
    from de4sdv.semantic.definition_projection import (
        API_METACLASSES,
        PROFILE_SCHEMA,
        build_outputs,
        load_document,
    )

    outputs = build_outputs(REPO_ROOT, load_document(REPO_ROOT))
    assert len(outputs["projection_rows"]) == 22
    assert len(outputs["profile_entries"]) == 22
    for row in outputs["projection_rows"]:
        assert row["support"] == "vocabulary-only"
        assert row["traversal"] is False
        assert row["api_identity"] == "unclaimed"
        serialized = json.dumps(row)
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in serialized, (row["identity"], field)
    for entry in outputs["profile_entries"]:
        assert entry["profile_identity"] == f"{PROFILE_SCHEMA}#{entry['for_concept']}"
        assert entry["binding_contract_echo"]["api_metaclass"] in set(API_METACLASSES.values())
        serialized = json.dumps(entry)
        for field in O1_GOVERNANCE_FIELDS:
            assert f'"{field}"' not in serialized, (entry["for_concept"], field)
    assert [row["identity"] for row in outputs["projection_rows"]] == sorted(
        entry["for_concept"] for entry in outputs["profile_entries"]
    )


def test_excluded_section_records_the_non_admitted_rows():
    manifest = yaml.safe_load((REPO_ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    excluded = {entry["identity"]: entry["reason"] for entry in manifest["excluded"]}
    # Scenario joined the admitted set (batch-1 amendment) and is no longer an
    # exclusion; the remaining considered-not-admitted rows keep their reasons.
    assert "Scenario" not in excluded
    for identity in ("ArchitectureDecisionRecord", "Baseline", "IncrementSize"):
        assert identity in excluded, identity
        assert excluded[identity].strip(), identity


# ---------------------------------------------------------------------------
# 2. Manifest fail-closed negatives
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "definition-admission.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _mutated(**changes) -> dict:
    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"][0].update(changes)
    return document


def test_unknown_row_key_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = _mutated(syaml_mapping={"file": "x"})
    with pytest.raises(DefinitionAdmissionError, match="unknown keys"):
        load_admission(_write_manifest(tmp_path, document))


def test_differs_without_reviewed_equivalence_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"][1]["semantic_text_equivalence"] = None
    with pytest.raises(DefinitionAdmissionError, match="bounded review"):
        load_admission(_write_manifest(tmp_path, document))


def test_exact_observation_with_equivalence_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = _mutated(semantic_text_equivalence="reviewed-equivalent")
    with pytest.raises(DefinitionAdmissionError, match="null"):
        load_admission(_write_manifest(tmp_path, document))


def test_duplicate_identity_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"].append(dict(document["admitted"][0]))
    with pytest.raises(DefinitionAdmissionError, match="duplicate"):
        load_admission(_write_manifest(tmp_path, document))


def test_empty_admitted_list_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    document["admitted"] = []
    with pytest.raises(DefinitionAdmissionError, match="non-empty"):
        load_admission(_write_manifest(tmp_path, document))


def test_missing_required_key_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import DefinitionAdmissionError, load_admission

    document = json.loads(json.dumps(_FIXTURE_MANIFEST))
    del document["admitted"][0]["required_runtime_support_target"]
    with pytest.raises(DefinitionAdmissionError, match="missing keys"):
        load_admission(_write_manifest(tmp_path, document))


# ---------------------------------------------------------------------------
# 3. Fixture generation, binding, and refusal behaviour
# ---------------------------------------------------------------------------


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _fixture_repo(tmp_path: Path, *, commit: bool = True) -> Path:
    root = tmp_path / "repo"
    model = root / _MODEL_FILE
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text(_FIXTURE_SYSML, encoding="utf-8")
    manifest = root / MANIFEST_PATH
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(yaml.safe_dump(_FIXTURE_MANIFEST), encoding="utf-8")
    design = root / DESIGN_PATH
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text("# fixture design\n", encoding="utf-8")
    module = root / MODULE_PATH
    module.parent.mkdir(parents=True, exist_ok=True)
    module.write_text("# bound module stand-in\n", encoding="utf-8")
    generator = root / GENERATOR_PATH
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_text("# bound generator stand-in\n", encoding="utf-8")
    # Both shared modules are executed by the generation path, so the fixture
    # carries their real repository bytes (read at fixture creation) and the
    # same content contract applies to them as to the module/generator.
    for relative in (AUTHORITY_INVENTORY_PATH, PROJECTION_O2P_PATH):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / relative).read_bytes())
    if commit:
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "review@example.invalid")
        _git(root, "config", "user.name", "review")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "admission inputs")
    return root


def test_generation_binds_to_committed_inputs_and_check_passes(tmp_path):
    from de4sdv.semantic.definition_projection import (
        PROFILE_PATH,
        PROJECTION_PATH,
        build_artifact_pair,
        run_check_errors,
    )
    from de4sdv.semantic.projection_o2p import canonical_json

    root = _fixture_repo(tmp_path)
    revision = _git(root, "rev-parse", "HEAD")
    artifacts = build_artifact_pair(root, source_revision=revision)
    binding = artifacts["projection"]["binding"]
    assert binding["source_revision"] == revision
    assert binding["artifact_commit"] is None
    assert binding["api_binding"]["status"] == "unclaimed"
    # The executed shared modules are generation software and are bound.
    assert binding["generation_software"]["program_inputs"] == list(
        BOUND_PROGRAM_INPUTS
    )
    for relative in (AUTHORITY_INVENTORY_PATH, PROJECTION_O2P_PATH):
        assert relative in binding["generation_software"]["program_inputs"]
        assert relative in binding["bound_inputs"]
    assert set(binding["bound_inputs"]) == {
        MANIFEST_PATH,
        DESIGN_PATH,
        MODULE_PATH,
        GENERATOR_PATH,
        AUTHORITY_INVENTORY_PATH,
        PROJECTION_O2P_PATH,
        _MODEL_FILE,
    }
    assert artifacts["projection"]["rows"][0]["traversal"] is False
    assert artifacts["profile"]["entries"][0]["for_concept"] == "FixtureAlpha"
    (root / PROJECTION_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (root / PROFILE_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    assert run_check_errors(root) == []


def test_generation_refuses_uncommitted_inputs(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_artifact_pair,
    )

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(model.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(DefinitionAdmissionError):
        build_artifact_pair(root, source_revision=_git(root, "rev-parse", "HEAD"))


def test_module_declares_the_executed_shared_modules_as_bound_inputs():
    """The real bound-input set is the four executed program inputs + models."""
    from de4sdv.semantic import definition_projection

    assert definition_projection.AUTHORITY_INVENTORY_PATH == AUTHORITY_INVENTORY_PATH
    assert definition_projection.PROJECTION_O2P_PATH == PROJECTION_O2P_PATH
    outputs = definition_projection.build_outputs(
        REPO_ROOT, definition_projection.load_document(REPO_ROOT)
    )
    bound = definition_projection.collect_bound_inputs(REPO_ROOT, outputs)
    assert set(bound) == {
        MANIFEST_PATH,
        DESIGN_PATH,
        MODULE_PATH,
        GENERATOR_PATH,
        AUTHORITY_INVENTORY_PATH,
        PROJECTION_O2P_PATH,
        *_MODEL_FILES,
    }
    for relative in (AUTHORITY_INVENTORY_PATH, PROJECTION_O2P_PATH):
        assert (REPO_ROOT / relative).is_file(), relative
        assert bound[relative].startswith("sha256:")


#: One unique in-body mutation per executed shared module (the executed-path
#: audit named both of them; changing either body must break generation when
#: the bound revision does not contain the change).
_SHARED_MODULE_MUTATIONS = {
    AUTHORITY_INVENTORY_PATH: (
        '    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()',
        '    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip() + "."',
    ),
    PROJECTION_O2P_PATH: (
        '    return json.dumps(document, indent=2, sort_keys=False) + "\\n"',
        '    return json.dumps(document, indent=2, sort_keys=True) + "\\n"',
    ),
}


@pytest.mark.parametrize("relative", [AUTHORITY_INVENTORY_PATH, PROJECTION_O2P_PATH])
def test_uncommitted_shared_module_edit_is_refused_naming_that_file(tmp_path, relative):
    from de4sdv.semantic.authority_inventory import file_digest

    from de4sdv.semantic.definition_projection import (
        PROFILE_PATH,
        PROJECTION_PATH,
        DefinitionAdmissionError,
        build_artifact_pair,
        run_check_errors,
    )
    from de4sdv.semantic.projection_o2p import canonical_json

    root = _fixture_repo(tmp_path)
    revision = _git(root, "rev-parse", "HEAD")
    module = root / relative
    original = module.read_text(encoding="utf-8")
    before, after = _SHARED_MODULE_MUTATIONS[relative]
    assert original.count(before) == 1, relative
    baseline_digest = file_digest(root, relative)

    # (a) mutation WITHOUT committing: the recorded revision no longer
    # contains this bound input byte-for-byte, so generation refuses and the
    # refusal names the mutated shared module.
    module.write_text(original.replace(before, after), encoding="utf-8")
    assert file_digest(root, relative) != baseline_digest
    with pytest.raises(DefinitionAdmissionError, match=re.escape(relative)):
        build_artifact_pair(root, source_revision=revision)

    # (b) commit the edit and rebind to the new revision: generation passes
    # again and the digest moves with the mutation.
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", f"mutate {relative}")
    new_revision = _git(root, "rev-parse", "HEAD")
    artifacts = build_artifact_pair(root, source_revision=new_revision)
    binding = artifacts["projection"]["binding"]
    assert binding["bound_inputs"][relative] == file_digest(root, relative)
    assert binding["bound_inputs"][relative] != baseline_digest

    # The committed artifacts are valid at the new revision ...
    (root / PROJECTION_PATH).write_text(
        canonical_json(artifacts["projection"]), encoding="utf-8"
    )
    (root / PROFILE_PATH).write_text(
        canonical_json(artifacts["profile"]), encoding="utf-8"
    )
    assert run_check_errors(root) == []

    # ... and a further uncommitted edit to that same shared module makes the
    # repository gate refuse, naming the file.
    module.write_text(
        module.read_text(encoding="utf-8") + "# uncommitted probe\n",
        encoding="utf-8",
    )
    errors = run_check_errors(root)
    assert errors, "an uncommitted shared-module edit must fail the gate"
    assert any(relative in error for error in errors), errors


def test_observation_mismatch_after_committed_edit_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_artifact_pair,
    )

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(
        model.read_text(encoding="utf-8").replace(
            "An exact fixture definition for alpha.",
            "A substantially reworded fixture definition for alpha.",
        ),
        encoding="utf-8",
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "reworded doc")
    with pytest.raises(DefinitionAdmissionError, match="observation"):
        build_artifact_pair(root, source_revision=_git(root, "rev-parse", "HEAD"))


def test_missing_declaration_file_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_artifact_pair,
    )

    root = _fixture_repo(tmp_path)
    (root / _MODEL_FILE).unlink()
    with pytest.raises(DefinitionAdmissionError):
        build_artifact_pair(root, source_revision=_git(root, "rev-parse", "HEAD"))


def test_declaration_without_documentation_is_refused(tmp_path):
    from de4sdv.semantic.definition_projection import (
        DefinitionAdmissionError,
        build_outputs,
        load_document,
    )

    root = _fixture_repo(tmp_path)
    model = root / _MODEL_FILE
    model.write_text(
        "package FixtureDefinitions {\n"
        "  part def FixtureAlpha;\n"
        "  part def FixtureBeta {\n"
        "    doc /* A differing fixture definition for beta that carries extra words. */\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )
    with pytest.raises(DefinitionAdmissionError):
        build_outputs(root, load_document(root))


def test_decoy_o1_artifacts_cannot_change_the_output(tmp_path):
    from de4sdv.semantic.definition_projection import build_outputs, load_document
    from de4sdv.semantic.projection_o2p import canonical_json

    root = _fixture_repo(tmp_path, commit=False)
    baseline = canonical_json(build_outputs(root, load_document(root)))
    decoy = root / "docs/method-conformance/o1/semantic-authority-inventory.json"
    decoy.parent.mkdir(parents=True, exist_ok=True)
    decoy.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "identity": "FixtureGamma",
                        "observed": {},
                        "reviewed": {"stage": "o2+ safe-set 1 (grounding + projection)"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert canonical_json(build_outputs(root, load_document(root))) == baseline


# ---------------------------------------------------------------------------
# 4. Commit-B gate: committed artifacts equal regeneration (red until A2)
# ---------------------------------------------------------------------------


def test_committed_artifacts_match_regeneration():
    from de4sdv.semantic.authority_inventory import validate_source_binding

    from de4sdv.semantic.definition_projection import (
        PROFILE_PATH,
        PROJECTION_PATH,
        build_artifact_pair,
        run_check_errors,
    )
    from de4sdv.semantic.projection_o2p import canonical_json

    projection_path = REPO_ROOT / PROJECTION_PATH
    profile_path = REPO_ROOT / PROFILE_PATH
    assert projection_path.is_file(), (
        "Commit-B gate: definition-projection.json is published in the artifact "
        "commit (A2); expected red between A1 and A2 by design"
    )
    assert profile_path.is_file()
    committed = json.loads(projection_path.read_text(encoding="utf-8"))
    assert validate_source_binding(REPO_ROOT, committed["binding"]) == []
    artifacts = build_artifact_pair(
        REPO_ROOT, source_revision=committed["binding"]["source_revision"]
    )
    assert canonical_json(artifacts["projection"]) == projection_path.read_text(
        encoding="utf-8"
    )
    assert canonical_json(artifacts["profile"]) == profile_path.read_text(
        encoding="utf-8"
    )
    assert run_check_errors(REPO_ROOT) == []


# ---------------------------------------------------------------------------
# 5. Runtime independence and repository wiring
# ---------------------------------------------------------------------------


def test_definition_projection_is_never_imported_by_the_runtime_path():
    runtime_modules = (
        "de4sdv/semantic/query.py",
        "de4sdv/semantic/runtime.py",
        "de4sdv/semantic/traversal.py",
        "de4sdv/semantic/impact.py",
        "de4sdv/semantic/mcp_server.py",
        "de4sdv/semantic/api_binding.py",
        "de4sdv/semantic/kernel_binding_index.py",
    )
    for relative in runtime_modules:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "definition_projection" not in text, relative
        assert "definition-projection" not in text, relative
        assert "definition-admission" not in text, relative


def _passing_gate_mocks():
    """All other check_repo gates mocked passing (shared with the ledger suite)."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_o4_consumer_ledger import _passing_gate_mocks as shared

    return shared()


def test_check_repo_actually_invokes_the_definition_admission_gate():
    from unittest import mock

    from de4sdv.semantic import definition_projection
    from scripts import check_repo

    calls: list[int] = []

    def spy(root):
        calls.append(1)
        return []

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(definition_projection, "run_check_errors", side_effect=spy):
            result = check_repo.main()
    finally:
        for m in mocks:
            m.stop()
    assert calls, "check_repo did not invoke the definition-admission gate"
    assert result == 0


def test_check_repo_fails_when_the_definition_admission_gate_fails():
    from unittest import mock

    from de4sdv.semantic import definition_projection
    from scripts import check_repo

    mocks = _passing_gate_mocks()
    for m in mocks:
        m.start()
    try:
        with mock.patch.object(
            definition_projection,
            "run_check_errors",
            return_value=["sentinel definition-admission error"],
        ):
            assert check_repo.main() == 1
    finally:
        for m in mocks:
            m.stop()