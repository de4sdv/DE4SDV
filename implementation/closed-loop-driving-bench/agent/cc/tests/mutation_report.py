"""The table the agent's mutation probes print (agent_logic.md, frame_store.md).

One row per mutation: what it changes, the rule it breaks, the result, and the
tests that killed it. A test binary prints one line per failing check,
"FAIL <file>:<line>: <expression>"; the test that holds the check is the last
top-level function definition above that line in <file>. A failing check that
prints a label instead of a file and line (the frame store's accounting
identities) is named by its label. The table names functions, never lines: the
probes find each mutation by its text, so the table does not change when
unrelated lines move.
"""
from __future__ import annotations

import re
from pathlib import Path

_FAIL_AT = re.compile(r"^FAIL (?P<file>[^:\s]+):(?P<line>\d+): ")
_FAIL_LABEL = re.compile(r"^FAIL (?P<label>[^:\s]+): ")
# A top-level definition: return type tokens, the name, an opening parenthesis,
# and no semicolon on the line (a declaration ends with one).
_DEFINITION = re.compile(r"^(?:[A-Za-z_][\w:<>,]*[\s*&]+)+([A-Za-z_]\w*)\s*\([^;]*$")
_definitions: dict[str, list[tuple[int, str]]] = {}


def _functions(path: str) -> list[tuple[int, str]]:
    if path not in _definitions:
        found: list[tuple[int, str]] = []
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for number, text in enumerate(lines, start=1):
            match = _DEFINITION.match(text)
            if match:
                found.append((number, match.group(1)))
        _definitions[path] = found
    return _definitions[path]


def enclosing_function(path: str, line: int) -> str:
    """The function of `path` whose definition is the last one at or above `line`."""
    name = "?"
    for number, function in _functions(path):
        if number > line:
            break
        name = function
    return name


def failing_tests(output: str) -> tuple[list[str], int]:
    """The tests holding failing checks, in the order of their first failure, and
    the number of failing checks."""
    names: list[str] = []
    count = 0
    for text in output.splitlines():
        at = _FAIL_AT.match(text)
        label = None if at else _FAIL_LABEL.match(text)
        if at:
            name = enclosing_function(at.group("file"), int(at.group("line")))
        elif label:
            name = label.group("label")
        else:
            continue
        count += 1
        if name not in names:
            names.append(name)
    return names, count


def killed_by(output: str, returncode: int) -> str:
    """The "killed by" cell for one failed test run."""
    names, count = failing_tests(output)
    if names:
        shown = ", ".join(f"`{name}`" for name in names[:3])
        if len(names) > 3:
            shown += f" and {len(names) - 3} more"
        return f"{shown} ({count} failing check{'' if count == 1 else 's'})"
    if returncode == 124:
        return "timed out"
    return f"exit status {returncode}, no failing check printed"


def print_table(rows: list[tuple[str, str, str, str]]) -> None:
    """Rows of (mutation, rule, result, killed by), as a Markdown table."""
    print("| mutation | rule | result | killed by |")
    print("|---|---|---|---|")
    for mutation, rule, result, by in rows:
        print(f"| {mutation} | {rule} | {result} | {by} |")
