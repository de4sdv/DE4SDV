"""Static checks of the identity recorder's parts that the host cannot build, and of its contracts with the other
lanes.

identity_recorder_main.cpp and candidate_record_probe_main.cpp are compiled for syntax against the closed-loop
bench's local mw::com mock (a mock, NOT S-CORE; the real API is checked only by the B2 build), and
lifecycle_reporter_score.cpp against the Lifecycle v0.10.0 API declarations of launch-manager/tests/lifecycle_mock.
The ids come from interfaces/ICD.md and service_ids.json at test time; the values ICD.md leaves open are the
warning-contract lane's (score-path/config/README.md) and the Launch Manager lane's, pinned here as theirs.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RECORDER = Path(__file__).resolve().parents[1]
BENCH = RECORDER.parent
ROOT = BENCH.parents[1]
ICD = BENCH / "interfaces" / "ICD.md"
MWCOM_MOCK = BENCH.parent / "closed-loop-driving-bench" / "state-publisher" / "tests" / "mock"
LIFECYCLE_MOCK = BENCH / "launch-manager" / "tests" / "lifecycle_mock"
MANIFEST = RECORDER / "mw_com_config_identity_recorder.json"
PROBE_MANIFEST = RECORDER / "mw_com_config_candidate_record_probe.json"
LAUNCH = BENCH / "launch-manager" / "config" / "launch_manager_config.json"
CANDIDATE_MANIFEST = BENCH / "score-path" / "config" / "mw_com_config_vision_pilot.json"


def icd_record_row() -> dict[str, str]:
    for line in ICD.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == "MAP-DRIVING-DA-CANDIDATE-RECORD":
            return {"event": cells[1].strip("`"), "specifier": cells[2].strip("`"), "service_id": cells[3],
                    "payload": cells[4]}
    raise AssertionError("ICD.md has no MAP-DRIVING-DA-CANDIDATE-RECORD row")


def compiler() -> str:
    found = shutil.which("g++")
    if found is None:
        pytest.skip("g++ is not installed")
    return found


@pytest.mark.parametrize("unit", ["identity_recorder_main.cpp", "candidate_record_probe_main.cpp"])
def test_the_mains_compile_for_syntax_against_the_mwcom_mock(tmp_path: Path, unit: str) -> None:
    assert (MWCOM_MOCK / "score" / "mw" / "com" / "types.h").is_file()
    subprocess.run([compiler(), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-isystem",
                    str(MWCOM_MOCK), f"-I{RECORDER}", f"-I{BENCH / 'interfaces' / 'include'}",
                    f"-I{BENCH / 'actuation-adapter'}", str(RECORDER / unit)], check=True, cwd=tmp_path)


def test_the_lifecycle_reporter_compiles_against_the_api_declarations(tmp_path: Path) -> None:
    subprocess.run([compiler(), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", "-fsyntax-only",
                    "-isystem", str(LIFECYCLE_MOCK), f"-I{RECORDER}", f"-I{BENCH / 'interfaces' / 'include'}",
                    f"-I{BENCH / 'actuation-adapter'}", str(RECORDER / "lifecycle_reporter_score.cpp")],
                   check=True, cwd=tmp_path)


def test_the_mains_use_the_icd_specifier_and_event() -> None:
    row = icd_record_row()
    for unit in ("identity_recorder_main.cpp", "candidate_record_probe_main.cpp"):
        text = (RECORDER / unit).read_text(encoding="utf-8")
        specifier = re.search(r'kCandidateRecordSpecifier = "([^"]+)";', text)
        assert specifier and specifier.group(1) == row["specifier"], unit
        event = re.search(r'Event<CandidateRecordEventPayload> (\w+)\{\*this, "([^"]+)"\};', text)
        assert event and event.group(1) == row["event"] == event.group(2), unit


def test_the_republish_period_is_the_icds() -> None:
    assert "re-published every 1 s for the whole run" in icd_record_row()["payload"]
    header = (RECORDER / "recorder_shell.h").read_text(encoding="utf-8")
    assert re.search(r"kRepublishPeriodS = 1\.0;", header)


def manifest_ids(path: Path) -> tuple[dict, dict, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    types = [s for s in data["serviceTypes"] if s["serviceTypeName"] == "/de4sdv/driver_assistance/CandidateRecord"]
    instances = [s for s in data["serviceInstances"]
                 if s["serviceTypeName"] == "/de4sdv/driver_assistance/CandidateRecord"]
    assert len(types) == 1 and len(instances) == 1, path.name
    return types[0], instances[0], data["global"]


def test_the_recorders_manifest_is_the_contract() -> None:
    row = icd_record_row()
    service, instance, glob = manifest_ids(MANIFEST)
    assert [b["serviceId"] for b in service["bindings"]] == [int(row["service_id"])]
    assert [(e["eventName"], e["eventId"]) for e in service["bindings"][0]["events"]] == [(row["event"], 1)]
    assert instance["instanceSpecifier"] == row["specifier"]
    # the warning-contract lane's values (score-path/config/README.md) and the Launch Manager lane's id
    assert [(i["instanceId"], i["asil-level"], i["binding"]) for i in instance["instances"]] == [(1, "QM", "SHM")]
    assert [(e["numberOfSampleSlots"], e["maxSubscribers"]) for e in instance["instances"][0]["events"]] == [(2, 1)]
    assert glob["applicationID"] == 3414
    readme = (BENCH / "score-path" / "config" / "README.md").read_text(encoding="utf-8")
    assert "service id 7413, event `candidate_record` with id 1, instance 1, QM, 2 slots, one subscriber" in readme


@pytest.mark.parametrize("consumer", [CANDIDATE_MANIFEST, PROBE_MANIFEST])
def test_the_consumers_find_the_recorders_service(consumer: Path) -> None:
    ours, our_instance, _ = manifest_ids(MANIFEST)
    theirs, their_instance, _ = manifest_ids(consumer)
    assert theirs == ours
    assert their_instance == our_instance


def test_every_application_id_on_the_host_is_unique() -> None:
    manifests = sorted(BENCH.glob("**/mw_com_config_*.json"))
    ids = {}
    for path in manifests:
        app = json.loads(path.read_text(encoding="utf-8"))["global"]["applicationID"]
        assert app not in ids, f"{path.name} and {ids.get(app)} share {app}"
        ids[app] = path.name
    assert ids[3414] == MANIFEST.name and ids[3416] == PROBE_MANIFEST.name


def test_the_launch_manager_starts_the_recorder_as_the_contract_says() -> None:
    config = json.loads(LAUNCH.read_text(encoding="utf-8"))
    component = config["components"]["identity_recorder"]
    assert component["component_properties"]["application_profile"]["application_type"] == "Reporting"
    assert component["component_properties"]["binary_name"] == "identity_recorder"
    args = component["component_properties"]["process_arguments"]
    assert args[0] == "--run-dir" and args[1].endswith("/run")
    env = component["deployment_config"]["environmental_variables"]
    assert env["MW_COM_CONFIG"].endswith("/config/" + MANIFEST.name)
    # the main takes exactly these: --run-dir, and MW_COM_CONFIG from the environment
    main = (RECORDER / "identity_recorder_main.cpp").read_text(encoding="utf-8")
    assert '"--run-dir"' in main and 'std::getenv("MW_COM_CONFIG")' in main
    # the candidate's process and the adapter wait for it
    for name in ("vision_pilot", "actuation_adapter"):
        assert "identity_recorder" in config["components"][name]["component_properties"]["depends_on"]


def test_every_cpp_file_that_names_a_fixed_width_type_includes_cstdint() -> None:
    files = sorted(RECORDER.glob("*.cpp")) + sorted(RECORDER.glob("*.h")) + sorted((RECORDER / "tests").glob("*.cpp")) \
        + sorted((RECORDER / "tests").glob("*.h"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bu?int(8|16|32|64)_t\b", text):
            assert "#include <cstdint>" in text, path.name


def test_bazel_names_every_source() -> None:
    build = (RECORDER / "BUILD.bazel").read_text(encoding="utf-8")
    for path in sorted(RECORDER.glob("*.cpp")) + sorted(RECORDER.glob("*.h")):
        assert f'"{path.name}"' in build, path.name
    for target in ("identity_recorder", "candidate_record_probe"):
        assert re.search(rf'cc_binary\(\s*name = "{target}"', build), target
