"""Approved direction is reproducible governance, never runtime activation."""
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import rename_transition as transition

ROOT = Path(__file__).resolve().parents[1]
APPROVALS = "docs/method-conformance/o4/approved-semantic-decisions.yaml"


@pytest.fixture
def approved_root(tmp_path):
    for relative in (APPROVALS, transition.PLAN_PATH):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    return tmp_path


def _raw(root):
    return yaml.safe_load((root / transition.PLAN_PATH).read_text())


def test_committed_approved_direction_is_not_activation():
    document = transition.load_plan(ROOT)
    assert document["schema"] == "de4sdv.o4-w6-transition-plan/v2"
    assert document["status"] == "approved-implementation"
    assert document["runtime_activation"] is False
    assert document["automatic_aliases"] is False
    assert len(document["entries"]) == 8
    assert len(transition.authorized_entries(document)) == 8
    assert all(transition.transition_state(row["identity"], document) == "approved"
               for row in document["entries"])
    assert transition.transition_state("realizedBy") == "approved"


@pytest.mark.parametrize("key,value", [
    ("runtime_activation", True), ("runtime_activation", 0),
    ("automatic_aliases", True), ("automatic_aliases", "false"),
    ("status", "active"), ("approval_record", "../outside.yaml"),
])
def test_approved_plan_refuses_activation_and_foreign_record(approved_root, key, value):
    document = _raw(approved_root)
    document[key] = value
    with pytest.raises(transition.RenameTransitionError):
        transition.validate_plan(document, root=approved_root)


@pytest.mark.parametrize("mutation", ["missing-topic", "wrong-decision", "blank-approval", "activation"])
def test_missing_or_contradictory_owner_record_refuses(approved_root, mutation):
    path = approved_root / APPROVALS
    approvals = yaml.safe_load(path.read_text())
    if mutation == "missing-topic":
        del approvals["topics"]["topic1"]
    elif mutation == "wrong-decision":
        approvals["topics"]["topic1"]["decisions"] = ["decision-99"]
    elif mutation == "blank-approval":
        approvals["topics"]["topic1"]["approval"] = " "
    else:
        approvals["production_activation"] = True
    path.write_text(yaml.safe_dump(approvals))
    with pytest.raises(transition.RenameTransitionError):
        transition.load_plan(approved_root)


def test_missing_record_file_refuses(approved_root):
    (approved_root / APPROVALS).unlink()
    with pytest.raises(transition.RenameTransitionError):
        transition.load_plan(approved_root)


@pytest.mark.parametrize("identity,successor", [
    ("realizedBy", "allocatedToArchitecture"),
    ("deployedTo", "logicalAllocatedToPhysical"),
    ("specifiesFunction", "hasRelevantFunction"),
    ("validatedBy", "validatedBy"),
])
def test_superseded_advisory_successors_cannot_reenter(approved_root, identity, successor):
    document = _raw(approved_root)
    row = next(row for row in document["entries"] if row["identity"] == identity)
    row["successor"] = successor
    with pytest.raises(transition.RenameTransitionError):
        transition.validate_plan(document, root=approved_root)


def test_authorization_must_resolve_all_applicable_topics(approved_root):
    document = _raw(approved_root)
    row = next(row for row in document["entries"] if row["identity"] == "constrainedBy")
    row["authorization"]["record"] = APPROVALS + "#topic1"
    with pytest.raises(transition.RenameTransitionError):
        transition.validate_plan(document, root=approved_root)


@pytest.mark.parametrize("mutation", ["unknown-key", "missing-key", "duplicate", "missing-entry", "null-authorization"])
def test_incomplete_or_ambiguous_transition_refuses(approved_root, mutation):
    document = _raw(approved_root)
    if mutation == "unknown-key":
        document["entries"][0]["activated"] = True
    elif mutation == "missing-key":
        del document["entries"][0]["disposition"]
    elif mutation == "duplicate":
        document["entries"].append(deepcopy(document["entries"][0]))
    elif mutation == "missing-entry":
        document["entries"].pop()
    else:
        document["entries"][0]["authorization"] = None
    with pytest.raises(transition.RenameTransitionError):
        transition.validate_plan(document, root=approved_root)


def test_duplicate_approval_yaml_keys_refuse(approved_root):
    path = approved_root / APPROVALS
    path.write_text(path.read_text() + "\nscope: reviewed-semantic-direction-only\n")
    with pytest.raises(transition.RenameTransitionError, match="duplicate YAML key"):
        transition.load_plan(approved_root)
