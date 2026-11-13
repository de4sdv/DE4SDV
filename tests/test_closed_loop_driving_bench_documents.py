"""The documents of the closed-loop driving bench, held to their sources (INC-DRIVING-001).

The documents of the bench (`implementation/closed-loop-driving-bench`; the paths below are relative to it)
restate by hand what the SysML model of the increment and the bench's own code state. Each test here reads both
sides from the repository and fails with the items that disagree. CI runs `python -m pytest tests -q` and none
of the bench's own test folders, so these checks live here:

- the mw::com table of the interface document (`interfaces/ICD.md` section 2) against the connections of the
  software realization of phase 8;
- the two payloads that phase 8 types against the structs of `interfaces/include/de4sdv/driving/payloads.h`;
- the observer's field table (`ivi-observer/codec/icd_table.py`) against the 43 rows of ICD section 3;
- the run record of ICD section 8 against `RetainedDrivingRunEvidence` and against the agent's writer, the
  keys of its "It also holds" list included;
- the table of `case-evaluators/OBSERVABLES.md`: the requirement of each case against the model, and the
  numbers of each pass threshold against the requirement, with the exceptions the document states;
- the scenario column of that table against the scenarios in which the evaluators judge each case
  (`SCENARIO_CASES` of `case-evaluators/cases.py`).

Each check is a function of the texts it reads, so a mutated text can be handed to the same check. The parsing
is a test-side convenience, not a SysML v2 or C++ parser: comments are blanked before structural matching,
names are matched whole, and a pattern that finds nothing fails. Semantic validation of the model stays with
syside (`python scripts/validate_sysml.py`).
"""

from __future__ import annotations

import ast
from collections import Counter
import importlib.util
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
REALIZATION = DRIVING / "closed_loop_driving_physical_software_realization.sysml"
EVIDENCE = DRIVING / "closed_loop_driving_verification_evidence.sysml"
REQUIREMENTS = DRIVING / "closed_loop_driving_needs_requirements.sysml"
BENCH = ROOT / "implementation/closed-loop-driving-bench"
ICD = BENCH / "interfaces/ICD.md"
PAYLOADS = BENCH / "interfaces/include/de4sdv/driving/payloads.h"
FIELD_TABLE = BENCH / "ivi-observer/codec/icd_table.py"
OBSERVABLES = BENCH / "case-evaluators/OBSERVABLES.md"
AGENT_WRITER = BENCH / "agent/cc/agent_ffi.cpp"
PLANNER_WRITER = BENCH / "agent/python/de4sdv_planner/__init__.py"
EVALUATORS = BENCH / "case-evaluators/cases.py"

#: ICD section 2 names the programs by short names, the software realization by its part names
ICD_PART_NAMES = {"agent": "drivingAgent", "actuationAdapter": "actuationAdapter",
                  "statePublisher": "statePublisherApplication", "gatewayd": "gatewayd"}
#: the hop of the model that ICD section 2 holds inside the row of the operational state
GATEWAY_IPC = ("gatewayd", "someipd")
GATEWAY_CONSUMER = "gatewayd → SOME/IP"
EVENT_ROWS = 6
SOFTWARE_CONNECTIONS = 7
#: the payloads phase 8 types as items; payloads.h declares a struct of each name
TYPED_PAYLOADS = ("EgoMotionSamplePayload", "VehicleMotionCommandPayload")
STATE_FIELDS = 43
EVIDENCE_ITEM = "RetainedDrivingRunEvidence"
VERIFICATION_CASES = 35
OBSERVABLES_HEADER = "| VC | Scen. | Req | Observables (ICD v2) | Computation | Pass threshold | Status |"

_SYSML_LEXEMES = re.compile(r'"(?:[^"\\]|\\.)*"|/\*.*?\*/|//[^\n]*', re.S)
_CPP_LEXEMES = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'|/\*.*?\*/|//[^\n]*', re.S)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _blank(text: str) -> str:
    return re.sub(r"[^\n]", " ", text)


def _masked(text: str, lexemes: re.Pattern, *, strings: bool = False) -> str:
    """``text`` with its comments blanked and, unless ``strings``, the contents of its string literals too.

    Blanking keeps every offset, so a span found in the masked text is the same span of ``text``.
    """
    def blank(match: re.Match) -> str:
        found = match.group(0)
        if found[0] in "\"'":
            return found if strings else found[0] + _blank(found[1:-1]) + found[-1]
        return _blank(found)

    return lexemes.sub(blank, text)


def _block(masked: str, opening: int) -> tuple[int, int]:
    """``(start, end)`` of the body of the brace block that opens at ``opening`` of a masked text."""
    assert masked[opening] == "{", f"no block opens at offset {opening}"
    depth = 0
    for index in range(opening, len(masked)):
        if masked[index] == "{":
            depth += 1
        elif masked[index] == "}":
            depth -= 1
            if depth == 0:
                return opening + 1, index
    raise AssertionError(f"unclosed block at offset {opening}")


def _declared_body(masked: str, header: str) -> tuple[int, int]:
    """The body of the one declaration whose header (a pattern that ends at its opening brace) matches."""
    found = list(re.finditer(header, masked))
    assert len(found) == 1, f"{header}: {len(found)} declarations, not 1"
    return _block(masked, found[0].end() - 1)


def _direct(body: str) -> str:
    """Blank nested bodies, keeping their braces, so only direct members remain visible."""
    out, depth = [], 0
    for char in body:
        if char == "}":
            depth -= 1
        out.append(char if depth == 0 or char == "\n" else " ")
        if char == "{":
            depth += 1
    assert depth == 0, "unbalanced body"
    return "".join(out)


def _section(markdown: str, heading: str) -> str:
    """The text below the one level-2 heading that starts with ``heading``, up to the next level-2 heading."""
    found = list(re.finditer(rf"^{re.escape(heading)}.*\n", markdown, re.M))
    assert len(found) == 1, f"{heading!r}: {len(found)} headings, not 1"
    rest = markdown[found[0].end():]
    following = re.search(r"^## ", rest, re.M)
    return rest[:following.start()] if following else rest


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def _table(text: str, header: str) -> list[list[str]]:
    """The rows of the one Markdown table whose header line starts with ``header``; each row is as wide."""
    lines = text.splitlines()
    found = [index for index, line in enumerate(lines) if line.startswith(header)]
    assert len(found) == 1, f"{header!r}: {len(found)} tables, not 1"
    width = len(_cells(lines[found[0]]))
    separator = _cells(lines[found[0] + 1]) if found[0] + 1 < len(lines) else []
    assert len(separator) == width and all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator), \
        f"{header!r}: no separator line under the header"
    rows = []
    for line in lines[found[0] + 2:]:
        if not line.startswith("|"):
            break
        cells = _cells(line)
        assert len(cells) == width, f"{header!r}: a row of {len(cells)} cells, not {width}: {line[:72]}"
        rows.append(cells)
    assert rows, f"{header!r}: no rows"
    return rows


# ---------------------------------------------------------------- 1. ICD section 2 and the connections


def _event_rows(icd: str) -> list[tuple[str, str, str]]:
    """``(event, producer, consumers)`` of each row of the table of ICD section 2."""
    section = _section(icd, "## 2. mw::com events")
    return [(cells[0], cells[1], cells[2]) for cells in _table(section, "| Event | Producer | Consumers |")]


def _realization(model: str) -> tuple[str, str]:
    """The masked model, and the direct members of the body of the software realization."""
    masked = _masked(model, _SYSML_LEXEMES)
    start, end = _declared_body(masked, r"\bpart\s+def\s+ClosedLoopDrivingSoftwareRealization\b[^{;]*\{")
    return masked, _direct(masked[start:end])


def _software_connections(model: str) -> list[tuple[str, str, str]]:
    """``(name, source, target)`` of each connection the software realization owns."""
    _, members = _realization(model)
    return re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", members)


def _agent_activities(model: str) -> list[str]:
    """The part usages of the definition that types the realization's ``drivingAgent``."""
    masked, members = _realization(model)
    typed = re.findall(r"\bpart\s+drivingAgent\s*:\s*(\w+)\s*;", members)
    assert len(typed) == 1, f"drivingAgent: {len(typed)} typed usages in the realization, not 1"
    start, end = _declared_body(masked, rf"\bpart\s+def\s+{typed[0]}\b[^{{;]*\{{")
    activities = re.findall(r"\bpart\s+(\w+)\s*:", _direct(masked[start:end]))
    assert activities, f"part def {typed[0]}: no part usage"
    return activities


def _event_table_problems(icd: str, model: str) -> list[str]:
    rows = _event_rows(icd)
    connections = _software_connections(model)
    activities = _agent_activities(model)
    problems = []
    if len(rows) != EVENT_ROWS:
        problems.append(f"ICD section 2 has {len(rows)} rows, not {EVENT_ROWS}: {[row[0] for row in rows]}")
    if len(connections) != SOFTWARE_CONNECTIONS:
        problems.append(f"the software realization owns {len(connections)} connections, not "
                        f"{SOFTWARE_CONNECTIONS}: {[connection[0] for connection in connections]}")
    table = Counter()
    for event, producer, consumers in rows:
        producer_name, _, activity = (part.strip() for part in producer.partition(" / "))
        pair = (ICD_PART_NAMES.get(producer_name), ICD_PART_NAMES.get(consumers.split(" →")[0].strip()))
        if None in pair:
            problems.append(f"row {event!r}: producer {producer!r} or consumer {consumers!r} names no program "
                            f"of the realization (known: {sorted(ICD_PART_NAMES)})")
            continue
        table[pair] += 1
        if producer_name == "agent" and activity not in activities:
            problems.append(f"row {event!r}: {activity!r} is no activity of the agent {activities}")
        if producer_name != "agent" and activity:
            problems.append(f"row {event!r}: {producer!r} names an activity of a program that has none")
    model_pairs = Counter()
    for name, source, target in connections:
        ends = (source.split("."), target.split("."))
        if min(len(end) for end in ends) < 2:
            problems.append(f"connection {name}: an end names no part ({source} to {target})")
            continue
        model_pairs[(ends[0][-2], ends[1][-2])] += 1
    if model_pairs[GATEWAY_IPC] != 1:
        problems.append(f"the model has {model_pairs[GATEWAY_IPC]} connections {GATEWAY_IPC}, not 1")
    covered = model_pairs - Counter({GATEWAY_IPC: 1})
    if table != covered:
        problems.append(f"(producer, consumer) in the table, not in the model: {sorted((table - covered).elements())}; "
                        f"in the model, not in the table: {sorted((covered - table).elements())}")
    gateway_rows = [event for event, _, consumers in rows if consumers == GATEWAY_CONSUMER]
    if len(gateway_rows) != 1:
        problems.append(f"{len(gateway_rows)} rows name the consumer {GATEWAY_CONSUMER!r}, not 1; that row holds "
                        f"the hop {GATEWAY_IPC}")
    return problems


def test_the_interface_table_names_the_connections_of_the_software_realization():
    """ICD section 2 against the connections of `ClosedLoopDrivingSoftwareRealization` (phase 8).

    Every row maps its producer and consumer to parts of the realization (`agent` is `drivingAgent`,
    `statePublisher` is `statePublisherApplication`); the (producer, consumer) pairs of the six rows, counted,
    are those of the seven connections without gatewayd to someipd, which the row of the operational state holds
    as "gatewayd → SOME/IP"; and the activity a row names after "agent / " is a part of the agent's definition.

    Not seen: which row belongs to which connection (two rows of the agent that swap their events pass), and the
    columns after the consumers (specifier, service id, payload, when, requirements).
    """
    problems = _event_table_problems(_read(ICD), _read(REALIZATION))
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- 2. the typed payloads and payloads.h


def _item_attributes(model: str, item: str) -> list[str]:
    """The names of the attributes an item definition owns, in order."""
    masked = _masked(model, _SYSML_LEXEMES)
    start, end = _declared_body(masked, rf"\bitem\s+def\s+{item}\b[^{{;]*\{{")
    names = re.findall(r"\battribute\s+(\w+)\s*:", _direct(masked[start:end]))
    assert names, f"item def {item}: no attribute"
    return names


def _struct_members(header: str, struct: str) -> list[str]:
    """The member names of a C++ struct, in order, without the members named ``reserved``."""
    masked = _masked(header, _CPP_LEXEMES)
    start, end = _declared_body(masked, rf"\bstruct\s+{struct}\s*\{{")
    names = [name for name in re.findall(r"\b(\w+)\s*(?:\[[^\]]*\])?\s*;", _direct(masked[start:end]))
             if name != "reserved"]
    assert names, f"struct {struct}: no member"
    return names


def _payload_problems(model: str, header: str) -> list[str]:
    problems = []
    for payload in TYPED_PAYLOADS:
        attributes, members = _item_attributes(model, payload), _struct_members(header, payload)
        if attributes != members:
            problems.append(f"{payload}: the model's attributes {attributes}, the struct's members {members}")
    return problems


def test_the_two_typed_payloads_equal_the_structs_of_the_bench():
    """`EgoMotionSamplePayload` and `VehicleMotionCommandPayload`: the attribute names of the item definitions,
    in order, equal the member names of the structs of the same names in `payloads.h`.

    Not seen: types and units (the model types VSS signals and DE4SDV extension candidates, the struct C++
    types), and the other structs of `payloads.h`, which the model does not type.
    """
    problems = _payload_problems(_read(REALIZATION), _read(PAYLOADS))
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- 3. the observer's field table and ICD section 3


def _state_rows(icd: str) -> list[tuple[int, str, str]]:
    """``(number, field, type)`` of each row of the field table of ICD section 3, in order."""
    section = _section(icd, "## 3. The operational state")
    rows = []
    for cells in _table(section, "| # | Field | Type | Meaning |"):
        assert re.fullmatch(r"\d+", cells[0]), f"ICD section 3: {cells[0]!r} is no row number"
        rows.append((int(cells[0]), cells[1], cells[2]))
    return rows


def _observer_fields(path: Path = FIELD_TABLE) -> list[tuple[int, str, str]]:
    """``(number, name, kind)`` of each entry of ``FIELDS`` of the observer's field table module."""
    spec = importlib.util.spec_from_file_location("_bench_documents_icd_table", path)
    assert spec and spec.loader, f"{path}: not loadable"
    module = importlib.util.module_from_spec(spec)
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    fields = [(field.number, field.name, field.kind) for field in module.FIELDS]
    assert fields, f"{path}: FIELDS is empty"
    return fields


def _field_table_problems(rows: list[tuple[int, str, str]], fields: list[tuple[int, str, str]]) -> list[str]:
    problems = []
    if len(rows) != STATE_FIELDS:
        problems.append(f"ICD section 3 has {len(rows)} rows, not {STATE_FIELDS}")
    numbers = [row[0] for row in rows]
    if numbers != list(range(1, len(rows) + 1)):
        problems.append(f"ICD section 3 numbers its rows {numbers}")
    for index in range(max(len(rows), len(fields))):
        document = rows[index] if index < len(rows) else None
        copy = fields[index] if index < len(fields) else None
        if document != copy:
            problems.append(f"position {index + 1}: ICD section 3 {document}, icd_table.py {copy}")
    return problems


def test_the_observer_field_table_equals_section_3_of_the_interface_document():
    """`FIELDS` of `ivi-observer/codec/icd_table.py` against the 43 rows of ICD section 3: number, name and type
    of every row, in order.

    Not seen: the Meaning column (the module copies none of it), the module's other tables, and the copy in
    `ivi-observer/fallback-a/tests/test_contract_and_framing.py`, which copies the protobuf message of ICD v1
    (`ICD-v1.md` section 3), not this table.
    """
    problems = _field_table_problems(_state_rows(_read(ICD)), _observer_fields())
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- 4. ICD section 8 and RetainedDrivingRunEvidence


def _listed_fields(section: str, lead: str, *, required: bool = True) -> list[str]:
    """The field names of the list right after the one line of ``section`` that opens with ``lead``.

    An item names fields before its first ``:`` or ``=``, separated by commas or "and"; text in backticks or in
    parentheses is not read.
    """
    lines = section.splitlines()
    found = [index for index, line in enumerate(lines) if line.startswith(lead)]
    if not found and not required:
        return []
    assert len(found) == 1, f"ICD section 8: {len(found)} lines open with {lead!r}, not 1"
    items, index = [], found[0] + 1
    while index < len(lines) and lines[index].startswith("- "):
        item, index = lines[index][2:], index + 1
        while index < len(lines) and lines[index].startswith("  ") and lines[index].strip():
            item, index = f"{item} {lines[index].strip()}", index + 1
        items.append(item)
    assert items, f"ICD section 8: no list after {lead!r}"
    names = []
    for item in items:
        head = re.split(r"[:=]", re.sub(r"`[^`]*`|\([^)]*\)", " ", item), maxsplit=1)[0]
        for name in (part.strip() for part in re.split(r",|\band\b", head.strip().rstrip(";."))):
            assert re.fullmatch(r"[a-z][A-Za-z0-9]*", name), f"ICD section 8: {name!r} of {item!r} is no field name"
            names.append(name)
    return names


def _run_record_lists(icd: str) -> tuple[list[str], list[str]]:
    """The fields ICD section 8 lists as held by the run record, and the fields it lists as not held."""
    section = _section(icd, "## 8. Run record")
    return _listed_fields(section, "It holds "), _listed_fields(section, "It does not hold ", required=False)


def _writer_statement(agent_cpp: str) -> str:
    """The one `fields << ...;` statement of `WriteRunRecordNow`, comments blanked, string literals kept."""
    code = _masked(agent_cpp, _CPP_LEXEMES, strings=True)
    masked = _masked(agent_cpp, _CPP_LEXEMES)
    start, end = _declared_body(masked, r"\bbool\s+WriteRunRecordNow\s*\([^)]*\)\s*\{")
    statements = [start + match.start() for match in re.finditer(r"\bfields\s*<<", masked[start:end])]
    assert len(statements) == 1, f"WriteRunRecordNow: {len(statements)} statements 'fields << ...', not 1"
    return code[statements[0]:masked.index(";", statements[0])]


def _planner_keys(planner_py: str) -> dict[str, set[str]]:
    """Variable -> the keys that the planner's `write_run_record` assigns to it: `fields["key"] = ...` for a key
    of the record, `value["key"] = ...` for a key of each of its `{"path": ...}` objects."""
    writers = [node for node in ast.walk(ast.parse(planner_py))
               if isinstance(node, ast.FunctionDef) and node.name == "write_run_record"]
    assert len(writers) == 1, f"the planner package: {len(writers)} functions write_run_record, not 1"
    assigned: dict[str, set[str]] = {}
    for node in ast.walk(writers[0]):
        for target in node.targets if isinstance(node, ast.Assign) else []:
            if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                    and isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str)):
                assigned.setdefault(target.value.id, set()).add(target.slice.value)
    assert assigned.get("fields"), "write_run_record: adds no key"
    return assigned


def _run_record_writer_keys(agent_cpp: str, planner_py: str) -> set[str]:
    """The keys the agent writes into `run_record.json`, nested ones included.

    Those of the JSON text that `WriteRunRecordNow` builds in its one `fields << ...;` statement
    (`\\"key\\":` in its string literals, and `path_field("key", ...)`), and those that the planner's
    `write_run_record` adds (`fields["key"] = ...`, and `value["key"] = ...` in a `{"path": ...}` object).
    """
    statement = _writer_statement(agent_cpp)
    keys = set(re.findall(r'\\"([A-Za-z]\w*)\\":', statement))
    keys |= set(re.findall(r'\bpath_field\(\s*"(\w+)"', statement))
    assert keys, "WriteRunRecordNow: no key"
    return keys.union(*_planner_keys(planner_py).values())


def _run_record_top_level_keys(agent_cpp: str, planner_py: str) -> set[str]:
    """The keys the agent writes at the top level of `run_record.json`: the keys at brace depth 1 of the JSON
    text in the string literals of the `fields << ...;` statement, the `path_field("key", ...)` keys, and the
    keys that the planner's `write_run_record` assigns to `fields[...]`."""
    statement = _writer_statement(agent_cpp)
    keys, depth = set(), 0
    for literal in re.findall(r'"((?:[^"\\\n]|\\.)*)"', statement):
        for token in re.finditer(r'\\"([A-Za-z]\w*)\\":|[{}]', literal):
            if token.group(0) == "{":
                depth += 1
            elif token.group(0) == "}":
                depth -= 1
            elif depth == 1:
                keys.add(token.group(1))
    assert depth == 0 and keys, f"WriteRunRecordNow: the JSON text of the statement ends at brace depth {depth}"
    keys |= set(re.findall(r'\bpath_field\(\s*"(\w+)"', statement))
    return keys | _planner_keys(planner_py)["fields"]


def _also_held(icd: str) -> list[tuple[str, list[str]]]:
    """The keys of the list after the line that opens with "It also holds" in ICD section 8: each name in
    backticks, with the names in its braces (`scenarioVariant {fault, aaosMode}`). In an item, the names end at
    the first "`:"; what follows describes them and is not read."""
    lines = _section(icd, "## 8. Run record").splitlines()
    found = [index for index, line in enumerate(lines) if line.startswith("It also holds")]
    assert len(found) == 1, f"ICD section 8: {len(found)} lines open with 'It also holds', not 1"
    keys, index = [], found[0] + 1
    while index < len(lines) and lines[index].startswith("- "):
        item, index = lines[index][2:], index + 1
        while index < len(lines) and lines[index].startswith("  ") and lines[index].strip():
            item, index = f"{item} {lines[index].strip()}", index + 1
        names = item.split("`:", 1)[0] + "`" if "`:" in item else item
        for span in re.findall(r"`([^`]*)`", names):
            match = re.fullmatch(r"([a-z][A-Za-z0-9]*)(?: \{([A-Za-z0-9, ]+)\})?", span)
            assert match, f"ICD section 8, 'It also holds': `{span}` is no key"
            keys.append((match.group(1), [name.strip() for name in (match.group(2) or "").split(",") if name.strip()]))
    assert keys, "ICD section 8: no key in backticks in the list after 'It also holds'"
    return keys


def _run_record_problems(icd: str, evidence_model: str, agent_cpp: str, planner_py: str) -> list[str]:
    attributes = _item_attributes(evidence_model, EVIDENCE_ITEM)
    held, not_held = _run_record_lists(icd)
    written = _run_record_writer_keys(agent_cpp, planner_py)
    problems = []
    for label, names in (("held", held), ("not held", not_held)):
        unknown = [name for name in names if name not in attributes]
        if unknown:
            problems.append(f"listed as {label}, no attribute of {EVIDENCE_ITEM}: {unknown}")
        twice = sorted(name for name, count in Counter(names).items() if count > 1)
        if twice:
            problems.append(f"listed as {label} twice: {twice}")
    both = sorted(set(held) & set(not_held))
    if both:
        problems.append(f"listed as held and as not held: {both}")
    should_hold = {name for name in attributes if name in written}
    if set(held) != should_hold:
        problems.append(f"listed as held, not written by the agent: {sorted(set(held) - should_hold)}; "
                        f"written by the agent, not listed as held: {sorted(should_hold - set(held))}")
    unsaid = [name for name in attributes if name not in held and name not in not_held]
    if unsaid:
        problems.append(f"attributes of {EVIDENCE_ITEM} that the section lists neither as held nor as not held: "
                        f"{unsaid}")
    also = _also_held(icd)
    top_level = _run_record_top_level_keys(agent_cpp, planner_py)
    named = [name for name, _ in also]
    twice = sorted(name for name, count in Counter(named).items() if count > 1)
    if twice:
        problems.append(f"listed as also held twice: {twice}")
    fields = [name for name in named if name in attributes]
    if fields:
        problems.append(f"listed as also held, but an attribute of {EVIDENCE_ITEM}: {fields}")
    absent = [name for name in named if name not in top_level]
    if absent:
        problems.append(f"listed as also held, not a key the agent writes at the top level of the record: {absent}")
    for name, nested in also:
        unwritten = [key for key in nested if key not in written]
        if unwritten:
            problems.append(f"listed as also held, {name}: the agent writes no key {unwritten}")
    unnamed = sorted(top_level - set(held) - set(named))
    if unnamed:
        problems.append(f"written by the agent at the top level of the record, named nowhere in the section: "
                        f"{unnamed}")
    return problems


def test_the_run_record_section_lists_the_evidence_fields_the_agent_writes_and_those_it_does_not():
    """ICD section 8 lists the fields of `RetainedDrivingRunEvidence` the run record holds and those it does
    not hold. Every name is an attribute of the item definition (`closed_loop_driving_verification_evidence.sysml`),
    no name is in both lists, every attribute is in one of them, and the held ones are exactly the attributes the
    agent's writer writes as keys (`agent/cc/agent_ffi.cpp` `WriteRunRecordNow`, and the keys the planner's
    `write_run_record` adds).

    The section's "It also holds" list names the other keys of the record. Each is a key the writer writes at the
    top level of the record and no attribute of the item definition, each name in its braces is a key the writer
    writes, and every top-level key of the writer is in the held list or in this one.

    Not seen: what a key's value is and what the section says about a key (only its name), a key written in
    another way than the forms the reader knows, keys written on some runs only (they count as written), nested
    keys spelled like a field (they count as written for the held list), the keys inside `setup` (the planner's
    set-up builds them), and the records of real runs.
    """
    problems = _run_record_problems(_read(ICD), _read(EVIDENCE), _read(AGENT_WRITER), _read(PLANNER_WRITER))
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- 5. OBSERVABLES.md and the requirements

#: not numbers of a criterion: case, requirement, scenario, gap and mapping ids; amendment, change-list and
#: scenario codes (A16, C2, S1); "ICD v2"; text in backticks; dates; the short form of a requirement id ("-029")
_NOT_NUMBERS = re.compile(r"\b(?:VC|REQ|SC|GAP|MAP|NEED)-DRIVING-\d+|\b[ACS]\d+\b|\bICD v\d+\b|`[^`]*`"
                          r"|\b\d{4}-\d{2}-\d{2}\b|-0\d\d\b")
_NUMBER = re.compile(r"(?<![A-Za-z\d.])\d+(?:\.\d+)?(?:e[-+]?\d+)?")
#: one line per exception in the introduction of OBSERVABLES.md: "- <case>, <numbers>: <what they are>"
_EXCEPTION = re.compile(r"^- (VC-DRIVING-\d{3}), ([^:\n]+): \S", re.M)


def _numbers(text: str) -> set[str]:
    """The numbers of a text, each in its shortest float form (3.0 and 3 are "3", 1e-3 is "0.001")."""
    return {format(float(token), ".15g") for token in _NUMBER.findall(_NOT_NUMBERS.sub(" ", text))}


def _observables_rows(observables: str) -> list[tuple[str, str, str]]:
    """``(case, requirement, pass threshold)`` of each row of the table of OBSERVABLES.md."""
    rows = []
    for cells in _table(observables, OBSERVABLES_HEADER):
        assert re.fullmatch(r"\d{3}", cells[0]) and re.fullmatch(r"\d{3}", cells[2]), \
            f"OBSERVABLES.md: a row whose case or requirement is no number: {cells[:3]}"
        rows.append((f"VC-DRIVING-{cells[0]}", f"REQ-DRIVING-{cells[2]}", cells[5]))
    return rows


def _stated_exceptions(observables: str) -> dict[str, set[str]]:
    """Case -> the numbers of its pass threshold that the introduction of OBSERVABLES.md states as not the
    requirement's."""
    assert "\n## 1. The table" in observables, "OBSERVABLES.md: no section '1. The table'"
    stated = {}
    for match in _EXCEPTION.finditer(observables[:observables.index("\n## 1. The table")]):
        assert match.group(1) not in stated, f"OBSERVABLES.md: two exception lines for {match.group(1)}"
        stated[match.group(1)] = _numbers(match.group(2))
        assert stated[match.group(1)], f"OBSERVABLES.md: the exception line of {match.group(1)} states no number"
    return stated


def _requirement_texts(model: str) -> dict[str, tuple[str, str, str]]:
    """Requirement id -> ``(usage name, statement, success criterion)``."""
    code = _masked(model, _SYSML_LEXEMES, strings=True)
    masked = _masked(model, _SYSML_LEXEMES)
    found = {}
    for match in re.finditer(r"\brequirement\s+<'(REQ-DRIVING-\d{3})'>\s+(\w+)\s*:\s*\w+\s*\{", masked):
        requirement = match.group(1)
        start, end = _block(masked, match.end() - 1)
        statements = list(re.finditer(r"\brequire\s+constraint\s+statement\s*\{", masked[start:end]))
        criteria = re.findall(r'\battribute\s*:>>\s*successCriteria\s*=\s*"((?:[^"\\]|\\.)*)"\s*;',
                              code[start:end])
        assert len(statements) == 1 and len(criteria) == 1, \
            f"{requirement}: {len(statements)} statements and {len(criteria)} success criteria, not 1 and 1"
        statement_start, statement_end = _block(masked, start + statements[0].end() - 1)
        statement = re.findall(r"/\*(.*?)\*/", model[statement_start:statement_end], re.S)
        assert len(statement) == 1, f"{requirement}: the statement is not one textual body"
        assert requirement not in found, f"{requirement}: declared twice"
        found[requirement] = (match.group(2), statement[0], criteria[0])
    assert found, "no requirement <'REQ-DRIVING-NNN'> in the model"
    return found


def _case_requirements(evidence_model: str) -> dict[str, list[str]]:
    """Case id -> the names of the requirement usages its verification definition verifies."""
    masked = _masked(evidence_model, _SYSML_LEXEMES)
    verified = {}
    for match in re.finditer(r"\bverification\s+def\s+(\w+)\b[^{;]*\{", masked):
        start, end = _block(masked, match.end() - 1)
        verified[match.group(1)] = [name.split("::")[-1]
                                    for name in re.findall(r"\bverify\s+([\w:]+)", masked[start:end])]
    cases = {}
    for match in re.finditer(r"\bverification\s+<'(VC-DRIVING-\d{3})'>\s+\w+\s*:\s*(\w+)\s*\{", masked):
        assert match.group(1) not in cases, f"{match.group(1)}: declared twice"
        assert match.group(2) in verified, f"{match.group(1)}: no verification def {match.group(2)}"
        cases[match.group(1)] = verified[match.group(2)]
    assert cases, "no verification <'VC-DRIVING-NNN'> in the model"
    return cases


def _by_value(numbers: set[str]) -> list[str]:
    return sorted(numbers, key=float)


def _observables_problems(observables: str, requirements_model: str, evidence_model: str) -> list[str]:
    rows = _observables_rows(observables)
    stated = _stated_exceptions(observables)
    requirements = _requirement_texts(requirements_model)
    requirement_of = {name: requirement for requirement, (name, _, _) in requirements.items()}
    cases = _case_requirements(evidence_model)
    problems = []
    if len(rows) != VERIFICATION_CASES:
        problems.append(f"OBSERVABLES.md has {len(rows)} rows, not {VERIFICATION_CASES}")
    in_table = [case for case, _, _ in rows]
    twice = sorted(case for case, count in Counter(in_table).items() if count > 1)
    if twice:
        problems.append(f"cases with two rows: {twice}")
    if set(in_table) != set(cases):
        problems.append(f"cases in the table, not in the model: {sorted(set(in_table) - set(cases))}; "
                        f"in the model, not in the table: {sorted(set(cases) - set(in_table))}")
    read = 0
    for case, requirement, threshold in rows:
        verified = [requirement_of.get(name, f"?{name}") for name in cases.get(case, [])]
        if case in cases and verified != [requirement]:
            problems.append(f"{case}: the table names {requirement}, the model's case verifies {verified}")
        if requirement not in requirements:
            problems.append(f"{case}: {requirement} is no requirement of the model")
            continue
        _, statement, criterion = requirements[requirement]
        wanted = _numbers(threshold)
        read += len(wanted)
        unexplained = wanted - _numbers(statement) - _numbers(criterion)
        if unexplained != stated.get(case, set()):
            problems.append(f"{case} ({requirement}): numbers of the pass threshold in neither the statement nor "
                            f"the success criterion {_by_value(unexplained)}, stated as exceptions "
                            f"{_by_value(stated.get(case, set()))}")
    stale = sorted(set(stated) - set(in_table))
    if stale:
        problems.append(f"exception lines for cases without a row: {stale}")
    assert read, "no number in any pass threshold: the tokenizer read nothing"
    return problems


def test_the_evaluators_table_takes_its_requirements_and_numbers_from_the_model_with_stated_exceptions():
    """`case-evaluators/OBSERVABLES.md` against the model: 35 rows, one per verification case of
    `closed_loop_driving_verification_evidence.sysml`; the requirement of each row is the one the case's
    definition verifies; and the numbers of each "Pass threshold" cell that are in neither the statement nor the
    success criterion of that requirement (`closed_loop_driving_needs_requirements.sysml`) are exactly the numbers
    the document's introduction states as exceptions for that case ("- <case>, <numbers>: <what they are>").

    The tokenizer compares sets of numbers. Not seen: a number that is in the requirement for another reason
    (it passes), dates (skipped), units and relations (100 ms and 100 m, <= and >=), numbers written as words,
    the other columns (a tolerance written in the Computation cell), what an exception line says its numbers are,
    and the "Scen." column.
    """
    problems = _observables_problems(_read(OBSERVABLES), _read(REQUIREMENTS), _read(EVIDENCE))
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- 6. OBSERVABLES.md and the evaluators' scenarios

SCENARIO_ENUM = "DrivingScenarioIdentity"
NO_SCENARIO_CELL = "Ref."


def _scenario_cells(evidence_model: str) -> dict[str, str]:
    """Token of the "Scen." column -> scenario identity. "S<n>" is the identity that the case usages of the model
    pair with SC-DRIVING-00<n> ("SC-DRIVING-003 (DrivingScenarioIdentity::degradedInputOrPlan)"); "Ref." is the
    one literal of `enum def DrivingScenarioIdentity` that is paired with no scenario."""
    pairs = set(re.findall(rf"\bSC-DRIVING-00(\d)\s*(?:\*\s*)?\({SCENARIO_ENUM}::(\w+)\)", evidence_model))
    assert pairs, f"no 'SC-DRIVING-00<n> ({SCENARIO_ENUM}::<name>)' in the model"
    by_number, by_name = {}, {}
    for number, name in sorted(pairs):
        assert by_number.setdefault(number, name) == name, f"SC-DRIVING-00{number} is paired with two identities"
        assert by_name.setdefault(name, number) == number, f"{name} is paired with two scenarios"
    masked = _masked(evidence_model, _SYSML_LEXEMES)
    start, end = _declared_body(masked, rf"\benum\s+def\s+{SCENARIO_ENUM}\s*\{{")
    literals = re.findall(r"\b(\w+)\s*;", masked[start:end])
    extra = sorted(set(by_name) - set(literals))
    assert not extra, f"paired identities that are no literal of {SCENARIO_ENUM}: {extra}"
    unpaired = [literal for literal in literals if literal not in by_name]
    assert len(unpaired) == 1, f"{SCENARIO_ENUM}: {unpaired} are paired with no scenario, not one literal"
    return {**{f"S{number}": name for number, name in by_number.items()}, NO_SCENARIO_CELL: unpaired[0]}


def _evaluator_scenarios(evaluators_py: str) -> dict[str, set[str]]:
    """Case id -> the scenarios in which the evaluators judge it: `SCENARIO_CASES` of `case-evaluators/cases.py`,
    evaluated from its source without importing the module (it needs numpy, which CI does not install)."""
    tables = [node.value for node in ast.parse(evaluators_py).body if isinstance(node, ast.Assign)
              and [getattr(target, "id", None) for target in node.targets] == ["SCENARIO_CASES"]]
    assert len(tables) == 1, f"cases.py: {len(tables)} assignments of SCENARIO_CASES, not 1"
    table = eval(compile(ast.Expression(tables[0]), "SCENARIO_CASES", "eval"), {"__builtins__": {}, "range": range})
    judged: dict[str, set[str]] = {}
    for scenario, cases in table.items():
        for case in cases:
            judged.setdefault(case, set()).add(scenario)
    assert judged, "cases.py: SCENARIO_CASES names no case"
    return judged


def _scenario_column_problems(observables: str, evidence_model: str, evaluators_py: str) -> list[str]:
    cells = _scenario_cells(evidence_model)
    judged = _evaluator_scenarios(evaluators_py)
    rows = _table(observables, OBSERVABLES_HEADER)
    problems = []
    for row in rows:
        case = f"VC-DRIVING-{row[0]}"
        tokens = [token.strip() for token in re.split(r"[,/]", row[1])]
        unknown = [token for token in tokens if token not in cells]
        if unknown or len(set(tokens)) != len(tokens):
            problems.append(f"{case}: the Scen. cell {row[1]!r} is not a list of {sorted(cells)} without repeats")
            continue
        named = {cells[token] for token in tokens}
        if named != judged.get(case, set()):
            problems.append(f"{case}: the table names {sorted(named)}, the evaluators judge it in "
                            f"{sorted(judged.get(case, set()))}")
    without_row = sorted(set(judged) - {f"VC-DRIVING-{row[0]}" for row in rows})
    if without_row:
        problems.append(f"cases the evaluators judge, without a row in the table: {without_row}")
    return problems


def test_the_evaluators_table_names_the_scenarios_in_which_the_evaluators_judge_each_case():
    """The "Scen." column of `case-evaluators/OBSERVABLES.md` against `SCENARIO_CASES` of the evaluators
    (`case-evaluators/cases.py`): each row names exactly the scenarios in which the evaluators judge its case, and
    every case the evaluators judge has a row. The tokens of the column are read through the model: "S<n>" is the
    identity that the case usages pair with SC-DRIVING-00<n>, "Ref." the one identity paired with no scenario.

    Not seen: the scenario sentence of each case usage of the model (this test reads the pairs of scenario and
    identity only, not which case names which), the order of the tokens in a cell, and which run of a scenario a
    case needs.
    """
    problems = _scenario_column_problems(_read(OBSERVABLES), _read(EVIDENCE), _read(EVALUATORS))
    assert not problems, "\n".join(problems)
