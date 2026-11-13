#!/usr/bin/env python3
"""Generate the case catalogue of the closed-loop driving bench from the SysML model.

The bench's case evaluators judge the verification cases of INC-DRIVING-001.
What the model declares about those cases as typed elements is taken from the
model, not copied by hand: the literals of ``enum def DrivingEvidenceOutcome``,
the verdict of each by ``calc def MapDrivingEvidenceOutcomeToVerdict`` with its
``else`` branch, the literals of ``enum def DrivingScenarioIdentity``, and the
``verification <'VC-DRIVING-NNN'>`` usages with the requirement each verifies.
The generator reads the verification-evidence file of the driving model and,
for the requirement ids, its needs-and-requirements file, and writes
``implementation/closed-loop-driving-bench/case-evaluators/driving_case_catalogue.json``
beside the evaluators, which read it at import.

The reading is lexical and fails closed. Comments, notes, ``doc`` bodies and
string literals are blanked before any structural match, so a commented-out
declaration is no declaration and no comment or doc text reaches the
catalogue. A declaration found zero or two times, a form the generator does not
read, and each inconsistency ``catalogue_from_text`` names are errors, never
skips. This is no SysML validation: Syside remains the authority on the model.

USAGE::

    python3 scripts/generate_driving_case_catalogue.py                  # print to stdout
    python3 scripts/generate_driving_case_catalogue.py --output PATH    # write to file
    python3 scripts/generate_driving_case_catalogue.py --check          # diff vs tracked catalogue
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = "textual-notation-of-model/packages/features/driving"
EVIDENCE_MODEL = f"{MODEL_DIR}/closed_loop_driving_verification_evidence.sysml"
REQUIREMENTS_MODEL = f"{MODEL_DIR}/closed_loop_driving_needs_requirements.sysml"
CATALOGUE_PATH = "implementation/closed-loop-driving-bench/case-evaluators/driving_case_catalogue.json"
SCHEMA = "de4sdv.driving.case-catalogue.v1"
REGENERATE = f"python3 scripts/generate_driving_case_catalogue.py --output {CATALOGUE_PATH}"

OUTCOME_ENUM = "DrivingEvidenceOutcome"
SCENARIO_ENUM = "DrivingScenarioIdentity"
VERDICT_CALC = "MapDrivingEvidenceOutcomeToVerdict"
VERDICT_KIND = "VerdictKind"
#: The literals of the standard library's VerificationCases::VerdictKind.
VERDICT_KINDS = ("pass", "fail", "inconclusive", "error")
CASE_ID = re.compile(r"VC-DRIVING-\d{3}")
REQUIREMENT_ID = re.compile(r"REQ-DRIVING-\d{3}")

NAME = r"[A-Za-z_]\w*"
SHORT_NAME = r"<'((?:[^'\\]|\\.)*)'>"
#: Tokens of a blanked body: unrestricted names, names, the operators the calc reads, any other character.
TOKEN = re.compile(r"'(?:[^'\\]|\\.)*'|[A-Za-z_]\w*|::|==|!=|:>>|:>|\S")
USAGE_HEADER = re.compile(rf"verification\s+{SHORT_NAME}\s*({NAME})\s*:\s*({NAME})\s*[{{;]")
VERIFY_FORM = re.compile(rf"verify\s+({NAME})\s*[{{;]")
REQUIREMENT_USAGE = re.compile(rf"\brequirement\s+(?!def\b)(?:{SHORT_NAME}\s*)?({NAME})\b")


class CatalogueError(ValueError):
    """The model is not in the form the generator reads; the message names the rule."""


# ---------------------------------------------------------------------------
# SysML text helpers
# ---------------------------------------------------------------------------

def _line(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _closing(text: str, start: int, quote: str) -> int:
    """Index of the quote that closes the string or name opened at ``start``; -1 if none."""
    index = start + 1
    while index < len(text):
        if text[index] == "\\":
            index += 2
        elif text[index] == quote:
            return index
        else:
            index += 1
    return -1


def _blank(text: str, relative: str) -> str:
    """``text`` with every comment, note, ``doc`` body and string literal blanked.

    Each blanked character becomes a space and newlines stay, so positions and
    line numbers hold. A ``//`` note runs to the end of its line; a ``//*`` note
    and a ``/* */`` comment run to the next ``*/``; the keyword ``doc`` right
    before a comment is blanked with it. Unrestricted names
    (``'VC-DRIVING-001'``) are code and stay.
    """
    out = list(text)

    def blank(start: int, end: int) -> None:
        for position in range(start, end):
            if out[position] != "\n":
                out[position] = " "

    index = 0
    while index < len(text):
        if text.startswith("//*", index) or text.startswith("/*", index):
            opener = 3 if text.startswith("//*", index) else 2
            end = text.find("*/", index + opener)
            if end == -1:
                raise CatalogueError(f"{relative} has an unterminated comment from line {_line(text, index)}")
            blank(index, end + 2)
            _blank_doc_keyword(out, index)
            index = end + 2
        elif text.startswith("//", index):
            end = text.find("\n", index)
            end = len(text) if end == -1 else end
            blank(index, end)
            index = end
        elif text[index] in "\"'":
            end = _closing(text, index, text[index])
            if end == -1:
                what = "string literal" if text[index] == '"' else "unrestricted name"
                raise CatalogueError(f"{relative} has an unterminated {what} from line {_line(text, index)}")
            if text[index] == '"':
                blank(index + 1, end)
            index = end + 1
        else:
            index += 1
    return "".join(out)


def _blank_doc_keyword(out: list[str], comment: int) -> None:
    """Blank the keyword ``doc`` when it is the code right before the comment at ``comment``."""
    index = comment - 1
    while index >= 0 and out[index].isspace():
        index -= 1
    start = index - 2
    if start >= 0 and "".join(out[start:index + 1]) == "doc" and (start == 0 or not (
            out[start - 1].isalnum() or out[start - 1] == "_")):
        out[start:index + 1] = [" ", " ", " "]


def _body(code: str, after: int, what: str, empty_allowed: bool = False) -> str:
    """The text between the braces of the body that follows ``after``; only whitespace may come between.

    With ``empty_allowed`` a declaration that ends in ``;`` has the empty body.
    """
    index = after
    while index < len(code) and code[index].isspace():
        index += 1
    if empty_allowed and code.startswith(";", index):
        return ""
    if not code.startswith("{", index):
        raise CatalogueError(f"{what} is not followed by its body")
    depth = 0
    for end in range(index, len(code)):
        if code[end] == "{":
            depth += 1
        elif code[end] == "}":
            depth -= 1
            if depth == 0:
                return code[index + 1:end]
    raise CatalogueError(f"{what} has no closing brace")


def _definitions(code: str, keyword: str, name: str) -> list[int]:
    """The index just past each ``<keyword> def [<'short name'>] <name>`` of ``code``."""
    pattern = re.compile(rf"\b{keyword}\s+def\s+(?:{SHORT_NAME}\s*)?{re.escape(name)}\b")
    return [match.end() for match in pattern.finditer(code)]


def _one_body(code: str, keyword: str, name: str, relative: str) -> str:
    """The body of the one ``<keyword> def <name>`` of ``code``; zero or two of them are an error."""
    ends = _definitions(code, keyword, name)
    declaration = f"{keyword} def {name}"
    if len(ends) != 1:
        raise CatalogueError(f"`{declaration}` is declared {len(ends)} times in {relative}; "
                             "the catalogue needs it exactly once")
    return _body(code, ends[0], f"`{declaration}` in {relative}")


def _snippet(code: str, start: int) -> str:
    """The text of a header from ``start`` up to its body or end, whitespace collapsed."""
    end = min([position for position in (code.find("{", start), code.find(";", start)) if position != -1]
              + [start + 160])
    return " ".join(code[start:end + 1].split())


# ---------------------------------------------------------------------------
# The parts of the catalogue
# ---------------------------------------------------------------------------

def _enum_literals(code: str, name: str, relative: str) -> list[str]:
    """The literals of ``enum def <name>`` in declaration order: ``<literal>;`` or ``enum <literal>;`` only."""
    statements, current = [], []
    for token in TOKEN.findall(_one_body(code, "enum", name, relative)):
        if token == ";":
            statements.append(current)
            current = []
        else:
            current.append(token)
    if current:
        raise CatalogueError(f"`enum def {name}` holds a member the generator does not read: `{' '.join(current)}`")
    literals: list[str] = []
    for statement in statements:
        words = statement[1:] if statement[:1] == ["enum"] and len(statement) > 1 else statement
        if len(words) != 1 or not re.fullmatch(NAME, words[0]):
            raise CatalogueError(f"`enum def {name}` holds a member the generator does not read: "
                                 f"`{' '.join(statement)};`")
        if words[0] in literals:
            raise CatalogueError(f"`enum def {name}` declares the literal {words[0]} twice")
        literals.append(words[0])
    if not literals:
        raise CatalogueError(f"`enum def {name}` declares no literal")
    return literals


def _verdict_rule(code: str, outcomes: list[str], relative: str) -> tuple[dict[str, str], str]:
    """The verdict of each outcome by the calc definition's explicit branches, the ``else`` branch for the rest.

    The body must be exactly ``in <p> : DrivingEvidenceOutcome; return <r> : VerdictKind =`` followed by one or
    more ``if <p> == DrivingEvidenceOutcome::<literal>? VerdictKind::<verdict> else`` and a final
    ``VerdictKind::<verdict>;``.
    """
    tokens = TOKEN.findall(_one_body(code, "calc", VERDICT_CALC, relative))

    def other_form() -> CatalogueError:
        return CatalogueError(
            f"the body of `calc def {VERDICT_CALC}` is not the conditional chain the generator reads "
            f"(in <p> : {OUTCOME_ENUM}; return <r> : {VERDICT_KIND} = if <p> == {OUTCOME_ENUM}::<literal>? "
            f"{VERDICT_KIND}::<verdict> else ... else {VERDICT_KIND}::<verdict>;): it reads `{' '.join(tokens)}`")

    if (len(tokens) < 11 or tokens[0] != "in" or not re.fullmatch(NAME, tokens[1])
            or tokens[2:5] != [":", OUTCOME_ENUM, ";"] or tokens[5] != "return" or not re.fullmatch(NAME, tokens[6])
            or tokens[7:10] != [":", VERDICT_KIND, "="] or tokens[-1] != ";"):
        raise other_form()
    parameter, chain = tokens[1], tokens[10:-1]
    branches: list[tuple[str, str]] = []
    while chain[:1] == ["if"]:
        branch, chain = chain[:11], chain[11:]
        if (len(branch) != 11 or branch[1:3] != [parameter, "=="] or branch[3:5] != [OUTCOME_ENUM, "::"]
                or not re.fullmatch(NAME, branch[5]) or branch[6:9] != ["?", VERDICT_KIND, "::"]
                or not re.fullmatch(NAME, branch[9]) or branch[10] != "else"):
            raise other_form()
        branches.append((branch[5], branch[9]))
    if not branches or len(chain) != 3 or chain[:2] != [VERDICT_KIND, "::"] or not re.fullmatch(NAME, chain[2]):
        raise other_form()
    otherwise = chain[2]

    def known(verdict: str) -> str:
        if verdict not in VERDICT_KINDS:
            raise CatalogueError(f"`calc def {VERDICT_CALC}` gives the verdict {VERDICT_KIND}::{verdict}, "
                                 f"which is none of {', '.join(VERDICT_KINDS)}")
        return verdict

    rule: dict[str, str] = {}
    for literal, verdict in branches:
        if literal not in outcomes:
            raise CatalogueError(f"`calc def {VERDICT_CALC}` compares {OUTCOME_ENUM}::{literal}, which is no "
                                 f"literal of `enum def {OUTCOME_ENUM}`")
        if literal in rule:
            raise CatalogueError(f"`calc def {VERDICT_CALC}` gives the literal {literal} two branches")
        rule[literal] = known(verdict)
    otherwise = known(otherwise)
    return {outcome: rule.get(outcome, otherwise) for outcome in outcomes}, otherwise


def _requirement_index(code: str) -> dict[str, list[str | None]]:
    """Name -> the short names of the ``requirement`` usages declared with that name."""
    index: dict[str, list[str | None]] = {}
    for match in REQUIREMENT_USAGE.finditer(code):
        index.setdefault(match.group(2), []).append(match.group(1))
    return index


def _cases(code: str, requirements_code: str) -> list[dict[str, str]]:
    """The ``verification <'VC-DRIVING-NNN'>`` usages, each with its definition and the requirement it verifies."""
    usages: dict[str, list[tuple[str, str]]] = {}
    for match in re.finditer(r"\bverification\b(?!\s+def\b)", code):
        header = USAGE_HEADER.match(code, match.start())
        if header is None:
            raise CatalogueError(f"a verification usage in {EVIDENCE_MODEL} is in a form the generator does not "
                                 f"read: `{_snippet(code, match.start())}`")
        short, usage, definition = header.groups()
        if not CASE_ID.fullmatch(short):
            raise CatalogueError(f"the verification usage {usage} in {EVIDENCE_MODEL} has the short name {short!r}, "
                                 "which is no VC-DRIVING-NNN case id")
        usages.setdefault(short, []).append((usage, definition))
    requirements = _requirement_index(requirements_code)
    cases = []
    for case_id in sorted(usages):
        if len(usages[case_id]) != 1:
            raise CatalogueError(f"the case id {case_id} is used by {len(usages[case_id])} verification usages: "
                                 + ", ".join(usage for usage, _ in usages[case_id]))
        ((usage, definition),) = usages[case_id]
        ends = _definitions(code, "verification", definition)
        if len(ends) != 1:
            raise CatalogueError(f"the definition {definition} of case {case_id} ({usage}) is declared {len(ends)} "
                                 f"times in {EVIDENCE_MODEL}; it must be declared exactly once")
        body = _body(code, ends[0], f"`verification def {definition}` in {EVIDENCE_MODEL}", empty_allowed=True)
        targets = []
        for verify in re.finditer(r"\bverify\b", body):
            form = VERIFY_FORM.match(body, verify.start())
            if form is None:
                raise CatalogueError(f"a verify of `verification def {definition}` is in a form the generator does "
                                     f"not read: `{_snippet(body, verify.start())}`")
            targets.append(form.group(1))
        if len(targets) != 1:
            raise CatalogueError(f"`verification def {definition}` (case {case_id}) has {len(targets)} verify "
                                 "targets; a case verifies exactly one requirement")
        target = targets[0]
        shorts = requirements.get(target, [])
        where = f"the verify target {target} of `verification def {definition}` (case {case_id})"
        if len(shorts) != 1:
            raise CatalogueError(f"{where} resolves to {len(shorts)} requirement declarations in "
                                 f"{REQUIREMENTS_MODEL}; it must resolve to exactly one "
                                 "`requirement <'REQ-DRIVING-NNN'>` declaration")
        (short,) = shorts
        if short is None:
            raise CatalogueError(f"{where} resolves to a requirement without a short name; it needs a "
                                 "REQ-DRIVING-NNN id")
        if not REQUIREMENT_ID.fullmatch(short):
            raise CatalogueError(f"{where} resolves to a requirement whose short name {short!r} is no "
                                 "REQ-DRIVING-NNN id")
        cases.append({"id": case_id, "usage": usage, "definition": definition, "requirement": short})
    return cases


# ---------------------------------------------------------------------------
# The catalogue
# ---------------------------------------------------------------------------

def catalogue_from_text(evidence: str, requirements: str) -> dict:
    """The catalogue of the two model texts; raises CatalogueError on any form or rule the generator refuses."""
    code = _blank(evidence, EVIDENCE_MODEL)
    requirements_code = _blank(requirements, REQUIREMENTS_MODEL)
    outcomes = _enum_literals(code, OUTCOME_ENUM, EVIDENCE_MODEL)
    scenarios = _enum_literals(code, SCENARIO_ENUM, EVIDENCE_MODEL)
    verdicts, otherwise = _verdict_rule(code, outcomes, EVIDENCE_MODEL)
    return {
        "schema": SCHEMA,
        "generated_from": [EVIDENCE_MODEL, REQUIREMENTS_MODEL],
        "outcomes": outcomes,
        "verdicts": verdicts,
        "verdict_otherwise": otherwise,
        "scenarios": scenarios,
        "cases": _cases(code, requirements_code),
    }


def generate_catalogue(root: Path | None = None) -> dict:
    """The catalogue of the model files under ``root`` (default: this checkout)."""
    root = ROOT if root is None else Path(root)
    return catalogue_from_text((root / EVIDENCE_MODEL).read_text(encoding="utf-8"),
                               (root / REQUIREMENTS_MODEL).read_text(encoding="utf-8"))


def serialize(catalogue: dict) -> str:
    return json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------

def run_check_errors(root: Path | None = None) -> list[str]:
    """Error strings for a catalogue that cannot be generated, is missing or differs from the tracked bytes.

    Designed for ``scripts/check_repo.py``, like the other validators: an empty list is a pass.
    """
    root = ROOT if root is None else Path(root)
    try:
        regenerated = serialize(generate_catalogue(root))
    except CatalogueError as error:
        return [f"Driving case catalogue cannot be generated from the SysML model: {error}"]
    tracked = root / CATALOGUE_PATH
    if not tracked.is_file():
        return [f"Driving case catalogue not found: regenerate with `{REGENERATE}`"]
    if tracked.read_bytes() != regenerated.encode("utf-8"):
        return [f"Driving case catalogue has drifted from the SysML model: regenerate with `{REGENERATE}`"]
    return []


def run_check(root: Path | None = None) -> int:
    """Regenerate and compare with the tracked catalogue: 0 on a match, 1 otherwise."""
    errors = run_check_errors(root)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Driving case catalogue check passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the case catalogue of the closed-loop driving bench from the SysML model.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the catalogue to this path (default: print to stdout).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Regenerate and compare with the tracked catalogue; exit 1 when they differ.",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_check()

    try:
        text = serialize(generate_catalogue())
    except CatalogueError as error:
        print(f"Driving case catalogue generation failed: {error}", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(text.encode("utf-8"))
        print(f"Wrote catalogue to {args.output}")
        return 0

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
