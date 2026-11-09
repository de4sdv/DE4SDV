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


def icd_max_samples(bench=BENCH):
    """The per-proxy max sample count that ICD.md section 2 fixes ("max sample count of N")."""
    text = (bench / "interfaces" / "ICD.md").read_text(encoding="utf-8")
    section = text.split("## 2.", 1)[1].split("\n## ", 1)[0]
    found = re.search(r"max sample count of (\d+)", section)
    assert found, "ICD.md section 2 states no per-proxy max sample count"
    return int(found.group(1))


def event_deployments(path):
    """[(specifier, event, numberOfSampleSlots, maxSubscribers)] of one manifest."""
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for inst in cfg.get("serviceInstances", []):
        for i in inst.get("instances", []):
            for e in i.get("events", []):
                out.append((inst["instanceSpecifier"], e.get("eventName"),
                            e.get("numberOfSampleSlots"), e.get("maxSubscribers")))
    return out


def check_sizing(path, per_proxy):
    """LoLa (enforceMaxSamples, the default) rejects a Subscribe once the subscribers' max sample
    counts would sum to more than the event's numberOfSampleSlots, and the producer needs one slot no
    subscriber holds. So every allowed subscriber fits only when slots >= maxSubscribers x N + 1."""
    problems = []
    for spec, event, slots, subs in event_deployments(path):
        if not isinstance(slots, int) or not isinstance(subs, int) or subs < 1:
            problems.append(f"{spec}/{event}: numberOfSampleSlots {slots}, maxSubscribers {subs}")
        elif slots < subs * per_proxy + 1:
            problems.append(f"{spec}/{event}: {slots} slots cannot hold {subs} subscribers x {per_proxy}"
                            f" samples + 1 producer slot (needs {subs * per_proxy + 1})")
    return problems


SOURCE_SKIP = {".venv", ".build", ".upstream", "tests", "__pycache__"}


def subscribe_calls(bench=BENCH):
    """[(file, line, count or None)] for every mw::com Subscribe call in the bench's C++ sources;
    a named count is resolved from a constant of the same file, None when it cannot be."""
    calls = []
    for path in sorted(bench.rglob("*")):
        if path.suffix not in (".cpp", ".cc", ".h") or SOURCE_SKIP & set(path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?:\.|->)\s*Subscribe\(\s*([A-Za-z_]\w*|\d+)\s*\)", text):
            arg = m.group(1)
            if arg.isdigit():
                count = int(arg)
            else:
                const = re.search(rf"\b{arg}\s*=\s*(\d+)", text)
                count = int(const.group(1)) if const else None
            calls.append((str(path.relative_to(bench)), text.count("\n", 0, m.start()) + 1, count))
    return calls


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


def test_every_event_has_a_slot_for_each_subscriber_and_the_producer():
    # On the simulator host the bench tap and the actuation adapter each subscribed to the command
    # event with 8 samples while it had 8 slots: whichever came second was rejected (slot overflow).
    per_proxy = icd_max_samples()
    problems = {str(p.relative_to(BENCH)): check_sizing(p, per_proxy) for p in manifests()}
    assert not any(problems.values()), problems


def test_every_copy_of_an_event_deployment_agrees():
    seen = {}
    for p in manifests():
        for spec, event, slots, subs in event_deployments(p):
            seen.setdefault((spec, event), set()).add((slots, subs, str(p.relative_to(BENCH))))
    disagree = {f"{s}/{e}": sorted(v) for (s, e), v in seen.items() if len({(a, b) for a, b, _ in v}) > 1}
    assert not disagree, disagree


def test_every_proxy_subscribes_within_the_icd_count():
    per_proxy = icd_max_samples()
    calls = subscribe_calls()
    files = {f for f, _, _ in calls}
    for consumer in ("agent/tools/agent_tap.cpp", "actuation-adapter/actuation_adapter_main.cpp",
                     "state-publisher/state_publisher_main.cpp"):
        assert consumer in files, f"no Subscribe call found in {consumer}: the scan is blind"
    bad = [(f, line, n) for f, line, n in calls if n is None or n > per_proxy]
    assert not bad, bad


if __name__ == "__main__":
    bench = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else BENCH
    table = icd_table(bench)
    bad = 0
    for p in manifests(bench):
        probs = check_manifest(p, table)
        bad += len(probs)
        print(("OK  " if not probs else "BAD ") + str(p.relative_to(bench)) + "".join("\n     " + q for q in probs))
    sys.exit(1 if bad else 0)
