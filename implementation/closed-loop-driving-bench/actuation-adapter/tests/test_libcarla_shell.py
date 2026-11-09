"""The actuation adapter's LibCarla shell keeps every CARLA list alive while it iterates it.

`for (const auto& a : *list->Filter("vehicle.*"))` binds the loop to the list the temporary
SharedPtr points at, and C++17 destroys that SharedPtr before the first iteration. CARLA's actor
iterator then builds actors into freed memory. On the simulator host this aborted the adapter with
"double free detected in tcache 2" as soon as it looked for the hero. The shell runs only against a
live CARLA server, so this static check stands in for a unit test: a range-based for may not iterate
a dereferenced call result; name the result first.

Run: python3 tests/test_libcarla_shell.py      (from actuation-adapter/)
or:  python3 -m pytest -q tests/test_libcarla_shell.py
"""
import re
import sys
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]


def strip_comments_and_strings(src):
    src = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)


def range_over_dereferenced_call(src):
    """[(line, range expression)] of range-based for loops whose range dereferences a call result."""
    code = strip_comments_and_strings(src)
    found = []
    for m in re.finditer(r"\bfor\s*\(", code):
        depth, j = 1, m.end()
        while j < len(code) and depth:
            depth += {"(": 1, ")": -1}.get(code[j], 0)
            j += 1
        header = code[m.end():j - 1]
        depth, colon = 0, None
        for k, c in enumerate(header):
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif c == ":" and depth == 0 and header[k - 1:k] != ":" and header[k + 1:k + 2] != ":":
                colon = k
                break
        if colon is None:
            continue
        rng = header[colon + 1:].strip()
        if rng.startswith("*") and "(" in rng:
            found.append((code.count("\n", 0, m.start()) + 1, rng))
    return found


def test_the_checker_flags_only_dereferenced_temporaries():
    assert range_over_dereferenced_call('for (const auto& a : *actors->Filter("vehicle.*")) {}')
    assert range_over_dereferenced_call("for (auto& a : *world.GetActors()) {}")
    assert not range_over_dereferenced_call("for (const auto& a : *vehicles) {}")
    assert not range_over_dereferenced_call("for (auto it = l->begin(); it != l->end(); ++it) {}")
    assert not range_over_dereferenced_call("for (const std::pair<int, int>& p : m) {}")
    assert not range_over_dereferenced_call("for (std::map<int, int>::iterator it = m.begin(); ;) {}")
    assert not range_over_dereferenced_call('// for (auto& a : *x->Filter("v")) {}')


def test_no_shell_loop_iterates_a_dereferenced_temporary():
    sources = sorted(ADAPTER.glob("*.cpp"))
    assert any(p.name == "actuation_adapter_main.cpp" for p in sources)
    bad = {p.name: hits for p in sources if (hits := range_over_dereferenced_call(p.read_text(encoding="utf-8")))}
    assert not bad, bad


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except AssertionError as error:
                failures += 1
                print("FAIL", name, error)
    sys.exit(1 if failures else 0)
