"""Live freshness is exact regeneration, never a Git binding.

Use synthetic declarations, not mirrors of the authoritative model. The
legacy source_revision arguments remain accepted but supply no authority.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import projection_o2p as native
from scripts import generate_semantic_projection_o2p as native_cli


def _native_inputs(root: Path) -> None:
    """A synthetic safe-set input tree without Git or generator stand-ins."""
    witness_file = "textual-notation-of-model/synthetic.sysml"
    admitted = []
    declarations = []
    for identity, flags in native.ADMITTED_SPEC.items():
        declaration = f"part def Synthetic{identity};"
        declarations.append(declaration)
        admitted.append({
            "identity": identity,
            **flags,
            "support": "vocabulary-only",
            "witness": {"file": witness_file, "contains": declaration},
            "construct": f"synthetic construct for {identity}",
            "exact_fit": "synthetic exact-fit witness",
            "standard_construct": "synthetic standard construct",
            "claim_boundary": "Vocabulary-only; no traversal or API UUID claim.",
        })
    manifest = {
        "schema": "de4sdv.o2plus-admission/v1",
        "admitted": admitted,
        "excluded": [
            {"identity": identity, "reason": "synthetically excluded"}
            for identity in (
                "allocatedTo", "EvidenceStatus", "variesAt",
                "FeatureConfiguration", "instantiatesCanonicalArchitecture",
            )
        ],
    }
    inputs = {
        native.ADMISSION_O2P_PATH: yaml.safe_dump(manifest),
        witness_file: "package Synthetic {\n" + "\n".join(declarations) + "\n}\n",
        native.SYSIDE_WORKFLOW_PATH: 'SYSIDE_VERSION="synthetic-pin"\n',
    }
    for relative, text in inputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _refuse_git(*args, **kwargs):
    pytest.fail("live construction/check must not invoke Git")


def test_native_cli_constructs_and_checks_without_git(tmp_path, monkeypatch):
    """One vertical slice: current inputs -> CLI write -> exact CLI check."""
    _native_inputs(tmp_path)
    monkeypatch.setattr(native_cli, "ROOT", tmp_path)
    monkeypatch.setattr(native.subprocess, "run", _refuse_git)

    assert native_cli.main([]) == 0
    paths = (native.PROJECTION_O2P_PATH, native.PROFILE_O2P_PATH)
    emitted = [(tmp_path / path).read_bytes() for path in paths]
    documents = [json.loads(payload) for payload in emitted]
    assert all("binding" not in document for document in documents)
    assert all("bound_revision" not in row["review_ref"] for row in documents[0]["rows"])
    assert documents[0]["scope"]["projection_outputs"] == [
        "Concern", "IncrementSize", "View", "Viewpoint",
    ]
    assert documents[0]["scope"]["api_profile_outputs"] == ["Variant", "VariationPoint"]
    assert native_cli.main(["--check"]) == 0
    assert native_cli.main([]) == 0
    assert emitted == [(tmp_path / path).read_bytes() for path in paths]


@pytest.mark.parametrize("relative", [native.PROJECTION_O2P_PATH, native.PROFILE_O2P_PATH])
@pytest.mark.parametrize("mutation", ["payload", "malformed", "retired-binding", "crlf"])
def test_native_check_refuses_noncanonical_bytes(tmp_path, monkeypatch, relative, mutation):
    _native_inputs(tmp_path)
    monkeypatch.setattr(native_cli, "ROOT", tmp_path)
    monkeypatch.setattr(native.subprocess, "run", _refuse_git)
    assert native_cli.main([]) == 0
    path = tmp_path / relative
    payload = path.read_bytes()
    document = json.loads(payload)
    if mutation == "payload":
        if "rows" in document:
            document["rows"][0]["support"] = "runtime-queryable"
        else:
            document["entries"][0]["representation"]["mechanics"] = "unreviewed mechanics"
        changed = native.canonical_json(document).encode("utf-8")
    elif mutation == "malformed":
        changed = b"\xff not JSON"
    elif mutation == "retired-binding":
        document["binding"] = {"source_revision": "0" * 40}
        changed = native.canonical_json(document).encode("utf-8")
    else:
        changed = payload.replace(b"\n", b"\r\n")
    path.write_bytes(changed)
    before = [(tmp_path / name).read_bytes() for name in (
        native.PROJECTION_O2P_PATH, native.PROFILE_O2P_PATH,
    )]
    errors = native.run_check_errors_o2p(tmp_path)
    assert len(errors) == 1 and relative in errors[0]
    assert "differs from" in errors[0]
    assert native_cli.main(["--check"]) == 1
    assert before == [(tmp_path / name).read_bytes() for name in (
        native.PROJECTION_O2P_PATH, native.PROFILE_O2P_PATH,
    )]


@pytest.mark.parametrize("relative", [native.PROJECTION_O2P_PATH, native.PROFILE_O2P_PATH])
def test_native_missing_artifact_fails_closed(tmp_path, monkeypatch, relative):
    _native_inputs(tmp_path)
    monkeypatch.setattr(native_cli, "ROOT", tmp_path)
    assert native_cli.main([]) == 0
    (tmp_path / relative).unlink()
    errors = native.run_check_errors_o2p(tmp_path)
    assert len(errors) == 1 and relative in errors[0] and "missing" in errors[0]
    assert native_cli.main(["--check"]) == 1
    assert not (tmp_path / relative).exists()


def test_native_current_input_edit_requires_regeneration_not_a_commit(tmp_path, monkeypatch):
    _native_inputs(tmp_path)
    monkeypatch.setattr(native_cli, "ROOT", tmp_path)
    monkeypatch.setattr(native.subprocess, "run", _refuse_git)
    assert native_cli.main([]) == 0
    path = tmp_path / native.ADMISSION_O2P_PATH
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["admitted"][0]["claim_boundary"] = "Edited synthetic boundary; still vocabulary-only."
    path.write_text(yaml.safe_dump(manifest), encoding="utf-8")
    assert native_cli.main(["--check"]) == 1
    assert native_cli.main(["--source-revision", "0" * 40]) == 0
    assert native_cli.main(["--check"]) == 0
    first = native.build_pair_o2p(tmp_path)
    assert first == native.build_pair_o2p(tmp_path, source_revision="1" * 40)
    assert first["projection"]["rows"][0]["claim_boundary"] == manifest["admitted"][0]["claim_boundary"]
