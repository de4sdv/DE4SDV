"""Live definitions: synthetic sources and independent literal oracles."""
import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import definition_projection as batch1
from de4sdv.semantic import definition_projection_batch2 as batch2


MODEL_FILE = "textual-notation-of-model/fixture_definition.sysml"


def _batch1_source(root: Path) -> None:
    files = {
        MODEL_FILE: "package Fixture {\n  part def Alpha {\n    doc /*Alpha documentation.*/\n  }\n}\n",
        batch1.ADMISSION_PATH: yaml.safe_dump({
            "schema": "de4sdv.o4-definition-admission/v1",
            "status": "admitted",
            "admitted": [{
                "identity": "Alpha", "semantic_kind": "class", "wave": "W2",
                "stage": "synthetic", "declaration": {
                    "file": MODEL_FILE, "declaration": "part def Alpha"},
                "evidence_state": "repository-evidenced",
                "authority_current": "legacy-yaml",
                "required_runtime_support_target": "vocabulary-only",
            }],
        }, sort_keys=False),
    }
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _expected_batch1_pair():
    return {
        "projection": {
            "schema": "de4sdv.o4-definition-projection/v1",
            "status": "admitted",
            "warning": ("vocabulary-only, no traversal, no authority retirement; the runtime "
                        "reads this artifact to build the kernel contract"),
            "scope": {
                "admission": "class-definition admission (class-definition-admission.yaml)",
                "admitted": ["Alpha"],
                "note": "no frozen O3 or gated identity is admitted",
            },
            "rows": [{
                "identity": "Alpha", "semantic_kind": "class", "wave": "W2",
                "definition": {
                    "documentation": "Alpha documentation.",
                    "documentation_witness": {
                        "source_file": MODEL_FILE, "declaration": "part def Alpha", "doc_count": 1},
                    "documentation_observation": "model-owned-documentation",
                },
                "grounding": {"kernel_binding_contract": {
                    "source_file": MODEL_FILE, "declaration": "part def Alpha"}},
                "support": "vocabulary-only", "traversal": False, "api_identity": "unclaimed",
            }],
        },
        "profile": {
            "schema": "de4sdv.o4-definition-profile/v1", "status": "admitted",
            "warning": ("vocabulary-only, no traversal, no authority retirement; the runtime "
                        "reads this artifact to build the kernel contract"),
            "entries": [{
                "profile_identity": "de4sdv.o4-definition-profile/v1#Alpha", "for_concept": "Alpha",
                "representation_class": "part-definition",
                "binding_contract_echo": {
                    "source_file": MODEL_FILE, "declaration": "part def Alpha", "api_metaclass": "PartDefinition"},
                "witness_forms": ["ownedRelationship -> OwningMembership -> Documentation (definition documentation, authored source order)"],
            }],
        },
    }



def test_batch1_construction_needs_only_current_sources_not_git(tmp_path):
    _batch1_source(tmp_path)
    assert batch1.build_artifact_pair(tmp_path) == _expected_batch1_pair()


def _batch2_source(root: Path) -> None:
    files = {
        MODEL_FILE: "package Fixture {\n  part def Alpha {\n    doc /*Alpha documentation.*/\n  }\n}\n",
        batch2.SUCCESSOR_FILE: 'package DE4SDV_RelationshipSuccessor {\n  part version : SuccessorVersionRecord {\n    attribute :>> version = "de4sdv.relationship-successor/v1";\n    attribute :>> supersedes = "synthetic";\n  }\n}\n',
        batch2.ADMISSION_PATH: yaml.safe_dump({
            "schema": "de4sdv.o4-definition-admission-batch2/v1", "status": "admitted", "exceptions": [],
            "admitted": [{
                "identity": "Alpha", "semantic_kind": "class", "admission_class": "definition",
                "register": {"wave": "W2", "accounting": "retained"}, "boundary": "none",
                "home": {"form": "owned-doc", "file": MODEL_FILE, "owner": "part def Alpha", "index": 0},
                "grounding": {"kernel_mapping": {"file": MODEL_FILE, "declaration": "part def Alpha"},
                              "sub_class_of": None, "disjoint_with": []},
                "gates": [], "forward_obligations": [],
            }],
        }, sort_keys=False),
    }
    for relative, text in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _expected_batch2_pair():
    warning = ("no traversal proof, no API element identity, no authority retirement; the "
               "runtime reads this artifact to build the kernel contract; retired names "
               "answer no fact (retired; use the successor)")
    return {
        "projection": {
            "schema": "de4sdv.o4-definition-batch2-projection/v1", "status": "admitted", "warning": warning,
            "scope": {
                "admission": "kernel-vocabulary admission (kernel-vocabulary-admission.yaml)",
                "admitted": ["Alpha"], "exceptions": [],
                "note": ("no frozen O3 identity and no identity of another generated layer "
                         "is admitted; exceptions are owner-visible and never silently fall back"),
            },
            "rows": [{
                "identity": "Alpha", "semantic_kind": "class", "admission_class": "definition",
                "register_wave": "W2", "accounting": "retained", "boundary": "none",
                "definition": {
                    "documentation": "Alpha documentation.",
                    "documentation_witness": {"source_file": MODEL_FILE, "owner": "part def Alpha",
                                              "form": "owned-doc", "documentation_name": None, "documentation_index": 0},
                    "documentation_observation": "model-owned-documentation",
                },
                "grounding": {
                    "kernel_binding_contract": {"source_file": MODEL_FILE, "declaration": "part def Alpha"},
                    "ontology_relations": {"sub_class_of": None, "disjoint_with": []},
                    "contract_source": ("kernel mapping kind and ontology relations: reviewed admission-manifest "
                        "fields (manifest-held; owner decision D9); file mappings are resolved in "
                        "the model by this generator; authored-ontology parity proven before its "
                        "deletion: https://github.com/de4sdv/DE4SDV/blob/release-2026-10-11/"
                        "docs/method-conformance/o4/closure/contract-equivalence.json"),
                },
                "support": "vocabulary-only", "traversal": False, "api_identity": "unclaimed",
            }],
        },
        "profile": {
            "schema": "de4sdv.o4-definition-batch2-profile/v1", "status": "admitted", "warning": warning,
            "entries": [{
                "profile_identity": "de4sdv.o4-definition-batch2-profile/v1#Alpha", "for_concept": "Alpha",
                "representation_class": "part-definition",
                "binding_contract_echo": {"source_file": MODEL_FILE, "owner": "part def Alpha", "api_metaclass": "PartDefinition"},
                "witness_forms": ["ownedRelationship -> OwningMembership -> Documentation (anonymous, owner-selected index)"],
            }],
        },
    }


def test_batch2_construction_needs_only_current_sources_not_git(tmp_path):
    _batch2_source(tmp_path)
    assert batch2.build_artifact_pair(tmp_path) == _expected_batch2_pair()


@pytest.mark.parametrize("module,source,expected", [
    (batch1, _batch1_source, _expected_batch1_pair),
    (batch2, _batch2_source, _expected_batch2_pair),
], ids=["batch1", "batch2"])
def test_gate_accepts_independent_literal_pair_without_any_binding(tmp_path, module, source, expected):
    source(tmp_path)
    pair = expected()
    for key, relative in (("projection", module.PROJECTION_PATH), ("profile", module.PROFILE_PATH)):
        (tmp_path / relative).write_text(json.dumps(pair[key], indent=2) + "\n", encoding="utf-8")
    assert module.run_check_errors(tmp_path) == []


@pytest.mark.parametrize("module,source", [(batch1, _batch1_source), (batch2, _batch2_source)], ids=["batch1", "batch2"])
def test_missing_artifacts_fail_without_a_commit_first_prerequisite(tmp_path, module, source):
    source(tmp_path)
    errors = module.run_check_errors(tmp_path)
    assert len(errors) == 2
    for relative in (module.PROJECTION_PATH, module.PROFILE_PATH):
        assert any(relative in error for error in errors)
    assert not any("commit the admission" in error or "two-commit" in error for error in errors)


@pytest.mark.parametrize("module,source,expected", [
    (batch1, _batch1_source, _expected_batch1_pair),
    (batch2, _batch2_source, _expected_batch2_pair),
], ids=["batch1", "batch2"])
def test_model_documentation_edit_needs_no_second_text_authority(tmp_path, module, source, expected):
    source(tmp_path)
    admission = tmp_path / module.ADMISSION_PATH
    document = yaml.safe_load(admission.read_text(encoding="utf-8"))
    for row in document["admitted"]:
        for key in ("reviewed_definition", "expected_documentation_observation", "semantic_text_equivalence"):
            row.pop(key, None)
    admission.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    path = tmp_path / MODEL_FILE
    path.write_text(path.read_text(encoding="utf-8").replace("Alpha documentation.", "Edited model meaning."), encoding="utf-8")
    pair = expected()
    definition = pair["projection"]["rows"][0]["definition"]
    definition["documentation"] = "Edited model meaning."
    definition["documentation_observation"] = "model-owned-documentation"
    definition.pop("semantic_text_equivalence", None)
    assert module.build_artifact_pair(tmp_path) == pair
    for key, relative in (("projection", module.PROJECTION_PATH), ("profile", module.PROFILE_PATH)):
        (tmp_path / relative).write_text(json.dumps(pair[key], indent=2) + "\n", encoding="utf-8")
    assert module.run_check_errors(tmp_path) == []


@pytest.mark.parametrize("module,source", [(batch1, _batch1_source), (batch2, _batch2_source)], ids=["batch1", "batch2"])
def test_empty_model_documentation_is_refused(tmp_path, module, source):
    source(tmp_path)
    path = tmp_path / MODEL_FILE
    path.write_text(path.read_text(encoding="utf-8").replace("Alpha documentation.", "   "), encoding="utf-8")
    error = batch1.DefinitionAdmissionError if module is batch1 else batch2.DefinitionBatch2Error
    with pytest.raises(error, match="empty documentation"):
        module.build_artifact_pair(tmp_path)
    assert module.run_check_errors(tmp_path)


@pytest.mark.parametrize("selected", ["1", "2", "all"])
def test_generator_cli_writes_and_checks_current_sources_without_git(tmp_path, monkeypatch, selected):
    from scripts import generate_definition_projection as generator

    _batch1_source(tmp_path)
    _batch2_source(tmp_path)
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    assert generator.main(["--batch", selected]) == 0
    pairs = [(batch1, _expected_batch1_pair)] if selected == "1" else [(batch2, _expected_batch2_pair)]
    if selected == "all":
        pairs = [(batch1, _expected_batch1_pair), (batch2, _expected_batch2_pair)]
    for module, expected in pairs:
        pair = expected()
        for key, relative in (("projection", module.PROJECTION_PATH), ("profile", module.PROFILE_PATH)):
            assert (tmp_path / relative).read_bytes() == (json.dumps(pair[key], indent=2) + "\n").encode("utf-8")
    assert generator.main(["--batch", selected, "--check"]) == 0
    (tmp_path / pairs[0][0].PROFILE_PATH).unlink()
    assert generator.main(["--batch", selected, "--check"]) == 1


def test_generator_rejects_retired_source_revision_option(tmp_path, monkeypatch):
    from scripts import generate_definition_projection as generator

    monkeypatch.setattr(generator, "ROOT", tmp_path)
    with pytest.raises(SystemExit) as exc:
        generator.main(["--source-revision", "0" * 40])
    assert exc.value.code == 2
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("module,source,expected", [
    (batch1, _batch1_source, _expected_batch1_pair),
    (batch2, _batch2_source, _expected_batch2_pair),
], ids=["batch1", "batch2"])
@pytest.mark.parametrize("target,mutation", [
    ("projection", "semantic"), ("profile", "mechanics"),
    ("projection", "binding"), ("profile", "binding"),
    ("projection", "whitespace"), ("profile", "invalid-json"),
    ("projection", "crlf"), ("profile", "missing"),
])
def test_gate_rejects_missing_or_nonexact_artifact_bytes(tmp_path, module, source, expected, target, mutation):
    source(tmp_path)
    pair = expected()
    if mutation == "semantic":
        pair[target]["rows"][0]["grounding"]["kernel_binding_contract"]["declaration"] = "part def Other"
    elif mutation == "mechanics":
        pair[target]["entries"][0]["representation_class"] = "item-definition"
    elif mutation == "binding":
        pair[target]["binding"] = {"source_revision": "0" * 40}
    paths = {"projection": module.PROJECTION_PATH, "profile": module.PROFILE_PATH}
    for key, relative in paths.items():
        data = json.dumps(pair[key], indent=2) + "\n"
        if key == target:
            if mutation == "whitespace":
                data += "\n"
            elif mutation == "invalid-json":
                data = "{not JSON"
            elif mutation == "crlf":
                data = data.replace("\n", "\r\n")
            elif mutation == "missing":
                continue
        (tmp_path / relative).write_bytes(data.encode("utf-8"))
    errors = module.run_check_errors(tmp_path)
    assert len(errors) == 1, errors
    assert paths[target] in errors[0]
    assert ("artifact missing" if mutation == "missing" else "differs from regeneration") in errors[0]


@pytest.mark.parametrize("module,source,expected", [
    (batch1, _batch1_source, _expected_batch1_pair),
    (batch2, _batch2_source, _expected_batch2_pair),
], ids=["batch1", "batch2"])
def test_model_edit_is_stale_until_independently_expected_regeneration(tmp_path, module, source, expected):
    source(tmp_path)
    pair = expected()
    for key, relative in (("projection", module.PROJECTION_PATH), ("profile", module.PROFILE_PATH)):
        (tmp_path / relative).write_text(json.dumps(pair[key], indent=2) + "\n", encoding="utf-8")
    model = tmp_path / MODEL_FILE
    model.write_text(model.read_text(encoding="utf-8").replace("Alpha documentation.", "Current model text."), encoding="utf-8")
    errors = module.run_check_errors(tmp_path)
    assert len(errors) == 1 and module.PROJECTION_PATH in errors[0]
    pair["projection"]["rows"][0]["definition"]["documentation"] = "Current model text."
    (tmp_path / module.PROJECTION_PATH).write_text(json.dumps(pair["projection"], indent=2) + "\n", encoding="utf-8")
    assert module.run_check_errors(tmp_path) == []


@pytest.mark.parametrize("module,source", [(batch1, _batch1_source), (batch2, _batch2_source)], ids=["batch1", "batch2"])
def test_empty_admission_population_cannot_pass_when_artifacts_are_absent(tmp_path, module, source):
    source(tmp_path)
    path = tmp_path / module.ADMISSION_PATH
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    document["admitted"] = []
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    errors = module.run_check_errors(tmp_path)
    assert errors and any("non-empty list" in error for error in errors)
