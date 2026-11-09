"""Every mw::com manifest of the bench agrees with the ICD's service table (ICD.md section 2).

LoLa connects a proxy to a skeleton by service id, instance id and event id, not by type name. A
manifest that swaps two ids builds and passes its own component tests, but its process never
receives the other side's samples (or reads the wrong payload type). This test reads the table from
ICD.md and checks every mw_com_config*.json under the bench.

Run: python3 -m pytest -q interfaces/tests/test_mw_com_manifests.py   (from the bench root)
or:  python3 interfaces/tests/test_mw_com_manifests.py [bench_root]
"""
import json
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[2]


def icd_table(bench=BENCH):
    """{specifier: (service_id, event_names)} from the section-2 table of ICD.md."""
    text = (bench / "interfaces" / "ICD.md").read_text(encoding="utf-8")
    section = text.split("## 2.", 1)[1].split("\n## ", 1)[0]
    table = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        spec = re.fullmatch(r"`([^`]+)`", cells[3])
        if not spec or not cells[4].isdigit():
            continue
        specifier = spec.group(1)
        events = re.findall(r"`([a-z_]+)`", cells[5]) if specifier.endswith("operational_state") else []
        if not events:  # "The event name of each of the first five services is the last segment"
            events = [specifier.rsplit("/", 1)[1]]
        table[specifier] = (int(cells[4]), events)
    return table


def manifests(bench=BENCH):
    return sorted(p for p in bench.rglob("mw_com_config*.json") if ".venv" not in p.parts)


def check_manifest(path, table):
    """List of problems of one manifest against the table."""
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    types = {}
    for t in cfg.get("serviceTypes", []):
        binding = t["bindings"][0]
        types[t["serviceTypeName"]] = (binding["serviceId"], [e["eventName"] for e in binding.get("events", [])])
    problems = []
    for inst in cfg.get("serviceInstances", []):
        spec = inst["instanceSpecifier"]
        if spec not in table:
            problems.append(f"{spec}: not in the ICD table")
            continue
        want_id, want_events = table[spec]
        got_id, type_events = types.get(inst["serviceTypeName"], (None, []))
        if got_id != want_id:
            problems.append(f"{spec}: service id {got_id}, ICD {want_id}")
        if sorted(type_events) != sorted(want_events):
            problems.append(f"{spec}: events {type_events}, ICD {want_events}")
        for i in inst.get("instances", []):
            if i.get("instanceId") != 1:
                problems.append(f"{spec}: instance id {i.get('instanceId')}, ICD 1")
    return problems


def test_icd_table_is_complete():
    table = icd_table()
    assert {s: v[0] for s, v in table.items()} == {
        "de4sdv/driving/ego_motion_sample": 7401,
        "de4sdv/driving/plan": 7402,
        "de4sdv/driving/mode": 7403,
        "de4sdv/driving/command": 7404,
        "de4sdv/driving/actuation_state": 7405,
        "de4sdv/driving/operational_state": 7406,
    }
    assert table["de4sdv/driving/operational_state"][1] == ["plan", "vehicle_state", "health"]


def test_every_manifest_matches_the_icd():
    table = icd_table()
    found = manifests()
    assert found, "no mw_com_config*.json found under the bench"
    problems = {str(p.relative_to(BENCH)): check_manifest(p, table) for p in found}
    assert not any(problems.values()), problems


if __name__ == "__main__":
    bench = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BENCH
    table = icd_table(bench)
    bad = 0
    for p in manifests(bench):
        probs = check_manifest(p, table)
        bad += len(probs)
        print(("OK  " if not probs else "BAD ") + str(p.relative_to(bench)) + "".join("\n     " + q for q in probs))
    sys.exit(1 if bad else 0)
