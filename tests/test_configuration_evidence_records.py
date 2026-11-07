"""The evidence records of the PLEML feature configurations (ADR 0022, step S7).

The evidence block of a Bill-of-Features was not a feature selection. Since
the Bills-of-Features retired at S7, each configuration whose bill carried
one has an evidence record in ``feature-configurations/evidence/``, named by
the configuration's file stem in kebab case. A record keeps the schema of the
block, a status and artifacts with an id and a path, and its integrity rules:
the status vocabulary, retained artifacts for an evidence-bearing status, the
artifact id grammar, no duplicate id, repository-relative paths outside
``.git``, no symbolic link, and an existing, Git-tracked file. The records
select no feature, and no evaluation or receipt reads them.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from de4sdv.semantic import pleml_receipts as receipts
from scripts import run_ple_authority as runner

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "model-based-product-line-engineering/feature-configurations/evidence"
#: The evidence status of each configuration with an evidence record: the status its Bill-of-Features
#: stated until S7.
STATUSES = {
    "apple_silicon_macos_candidate.sysml": "planned",
    "inc_aebs_009a_jetson.sysml": "inspected",
    "middleware_autoware_aaos_sdv_reference.sysml": "planned",
    "nxp_zephyr_vehicle_target_candidate.sysml": "planned",
}


class _UniqueKeyLoader(yaml.SafeLoader):
    """A safe loader that refuses a duplicate mapping key, as the Bill-of-Features reader did."""


def _unique_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError("while constructing a mapping", node.start_mark,
                                                    f"found duplicate key {key!r}", key_node.start_mark)
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _records() -> list[Path]:
    return sorted(EVIDENCE.glob("*.yaml"))


def _configuration_of(record: Path) -> str:
    return record.stem.replace("-", "_") + ".sysml"


def test_each_evidence_record_belongs_to_one_member_configuration() -> None:
    assert sorted(path.name for path in EVIDENCE.iterdir()) == [record.name for record in _records()]
    configurations = {Path(path).name: path for path in runner.CONFIGURATIONS}
    assert {_configuration_of(record) for record in _records()} == set(STATUSES)
    assert set(STATUSES) <= set(configurations)
    for record in _records():
        assert (ROOT / configurations[_configuration_of(record)]).is_file(), record.name


@pytest.mark.parametrize("record", _records(), ids=lambda record: record.stem)
def test_the_evidence_record_keeps_the_evidence_rules(record: Path) -> None:
    data = yaml.load(record.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    assert receipts.evidence_record_errors(data, ROOT) == []
    assert data["status"] == STATUSES[_configuration_of(record)]


def test_a_duplicate_key_is_refused() -> None:
    with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
        yaml.load("status: planned\nstatus: inspected\nartifacts: []\n", Loader=_UniqueKeyLoader)


def test_the_inspected_environment_names_its_retained_artifacts() -> None:
    data = yaml.safe_load((EVIDENCE / "inc-aebs-009a-jetson.yaml").read_text(encoding="utf-8"))
    assert [artifact["id"] for artifact in data["artifacts"]] == [
        "EVID-AEBS-009A-RUNTIME-LOCK", "EVID-AEBS-009A-CONTAINER-IDENTITY", "EVID-AEBS-009A-READINESS",
        "EVID-AEBS-009A-ENVIRONMENT-SNAPSHOT"]


def test_no_feature_configuration_carries_an_evidence_status() -> None:
    """The status lives in the record, never in the model: the configurations select features only."""
    for path in runner.CONFIGURATIONS:
        text = (ROOT / path).read_text(encoding="utf-8").split("package", 1)[1]
        assert "status" not in text.lower(), path
