"""Generate the trace-vocabulary contract from the model (build time only).

The runtime serves the trace relations of the method kernel (``allocatedTo``,
``hasValidationScenario`` with its inverse ``validationScenarioFor``,
``hasRegulatorySource``) and refuses the retired relation names from one
generated file, ``de4sdv/semantic/contract-data/trace-vocabulary-contract.json``.
This module writes that file from the trace-vocabulary package of the kernel:
its relation, retirement and version records, and the typed ends of the
connection definitions those records name, checked against the class pins of
the generated projection layers (:func:`model_contract.model_class_pins`). The
runtime reads the generated file (:func:`model_contract.load_trace_contract`)
and never parses SysML text (ADR 0011).

The reader is a bounded token scan of the supported textual subset, not a
SysML parser or validator. Comments and both quoted-token forms (strings and
single-quoted names) are inert, so a commented or quoted decoy can never move
a declaration boundary or supply a record, a field or a carrier end. Every
record and carrier must be one live, directly owned declaration (a duplicate
refuses), and a record field must be a directly owned
``attribute :>> name = "literal";``. Licensed validation of the model stays
separate.

Generation is deterministic: the same sources give the same bytes, and the
file names no Git revision and no input digest.
``scripts/generate_trace_vocabulary_contract.py`` writes it; its ``--check``,
run by ``scripts/check_repo.py``, refuses a missing or stale file. Run it after
the projection generators, whose class pins it reads.

Read-only and offline; never imported by the runtime.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import model_contract as mc

MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_trace_vocabulary.sysml"
PACKAGE = "DE4SDV_TraceVocabulary"
GENERATOR = "scripts/generate_trace_vocabulary_contract.py"
#: The record definitions the package declares, with the fields each record sets.
RECORD_FIELDS = {
    "TraceVocabularyVersionRecord": frozenset({"version", "supersedes"}),
    "TraceRelationRecord": frozenset({"predicate", "carrier", "mechanism", "strength", "sourceClass",
                                      "targetClass", "sourceUsage", "targetUsage", "inverse"}),
    "RetiredRelationRecord": frozenset({"predicate", "reason"}),
}
VERSION_RECORD, RELATION_RECORD, RETIREMENT_RECORD = RECORD_FIELDS
WARNING = (
    "Generated from the trace-vocabulary package of the method kernel by "
    "scripts/generate_trace_vocabulary_contract.py; do not edit. The runtime reads this "
    "file to serve the trace relations and never parses the model."
)


def _lexical_mask(text: str, *, mask_strings: bool) -> str:
    """One bounded token scan: comments are inert only outside quoted tokens.

    Both String literals and unrestricted-name tokens protect their contents.
    Offsets and newlines stay stable; incomplete tokens cannot supply code.
    This does not validate SysML types, imports or language semantics.
    """
    output, index = [], 0
    while index < len(text):
        start = index
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end == -1:
                raise ValueError("unterminated successor source comment")
            index, masked = end + 2, True
        elif text.startswith("//", index):
            end = text.find("\n", index + 2)
            index, masked = (len(text) if end == -1 else end), True
        elif text[index] in ('"', "'"):
            quote = text[index]
            index += 1
            while index < len(text):
                if text[index] == "\\":
                    index += 2
                elif text[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise ValueError("unterminated successor source quoted token")
            masked = mask_strings
        else:
            output.append(text[index])
            index += 1
            continue
        token = text[start:index]
        output.append("".join("\n" if c == "\n" else " " for c in token) if masked else token)
    return "".join(output)


def _comment_free(text: str) -> str:
    return _lexical_mask(text, mask_strings=False)


def _mask_strings(text: str) -> str:
    return _lexical_mask(text, mask_strings=True)


def _owned_matches(block: str, pattern: str):
    """Direct-owned CODE matches of one declaration block, plus its code text.

    ``declaration_block`` returns a block starting at its opening brace, so its
    direct members sit at depth 1. Comments and string content are not code,
    and a member nested in an inner body (or a foreign declaration) belongs to
    that owner: neither can supply a construction input. Offsets are preserved,
    so a match slices the comment-free text.
    """
    code = _comment_free(block)
    structure = _mask_strings(code)
    depths, depth = [], 0
    for char in structure:
        depths.append(depth)
        depth += (char == "{") - (char == "}")
    return [match for match in re.finditer(pattern, structure) if depths[match.start()] == 1], code


def _live_declaration(text: str, header_pattern: str, *, direct_depth: int | None = None) -> str | None:
    """Locate one declaration's owned block through the bounded token scan.

    Comment content and both quoted-token forms are inert while the header is
    found and its braces are matched, so a commented decoy or an unrestricted
    name containing ``{``, ``}`` or ``/*`` cannot move a declaration boundary.
    Offsets are preserved, so the returned block still slices the original text
    and quoted field values remain readable. Zero live declarations return
    ``None``; more than one refuses, because a duplicated declaration cannot
    supply a single construction witness. This is bounded lexical handling for
    the supported subset, not SysML notation or type validation.
    """
    structure = _mask_strings(_comment_free(text))
    matches = list(re.finditer(header_pattern, structure))
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError("ambiguous live declaration: " + header_pattern)
    if direct_depth is not None:
        prefix = structure[:matches[0].start()]
        if prefix.count("{") - prefix.count("}") != direct_depth:
            raise ValueError("declaration is not directly owned: " + header_pattern)
    index = matches[0].end()
    while index < len(structure) and structure[index] not in "{;":
        index += 1
    if index >= len(structure):
        raise ValueError("unterminated declaration header: " + header_pattern)
    if structure[index] == ";":
        raise ValueError("declaration has no owned body: " + header_pattern)
    brace = index
    depth = 0
    while index < len(structure):
        char = structure[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace:index + 1]
        index += 1
    raise ValueError("unterminated declaration body: " + header_pattern)


def _definition_pattern(declaration: str) -> str:
    """Line-anchored, comment/quote-inert pattern for one ``X def Y`` header."""
    kind, _, name = declaration.partition(" def ")
    return (r"(?m)^[ \t]*(?:(?:public|private|protected)\s+)?(?:abstract\s+)?"
            + re.escape(kind.strip()).replace(r"\ ", r"\s+") + r"\s+def\s+"
            + re.escape(name.strip()) + r"\b")


def _definition_owner(text: str, declaration: str) -> str:
    """Prove a pin's direct top-level package owner in the supported subset.

    Arbitrary nested definitions are not package namespace identities. The
    constructor accepts direct package members only, not a general SysML
    name/import resolver. Live homonyms still refuse before ownership checks.
    """
    pattern = _definition_pattern(declaration)
    if not _live_declaration(text, pattern, direct_depth=1):
        raise ValueError("missing complete class declaration: " + declaration)
    structure = _mask_strings(_comment_free(text))
    match = re.search(pattern, structure)
    assert match is not None  # The unique complete declaration was checked above.
    openings = []
    for index, char in enumerate(structure[:match.start()]):
        if char == "{":
            openings.append(index)
        elif char == "}":
            if not openings:
                raise ValueError("unbalanced braces before class declaration: " + declaration)
            openings.pop()
    if not openings:
        raise ValueError("class declaration has no direct package owner: " + declaration)
    packages = list(re.finditer(r"\bpackage\s+([A-Za-z_]\w*)\s*\{", structure))
    owners = [package for package in packages if package.end() - 1 == openings[0]]
    if len(owners) != 1:
        raise ValueError("class declaration has no direct package owner: " + declaration)
    owner = owners[0].group(1)
    _live_declaration(text, r"\bpackage\s+" + re.escape(owner) + r"(?=\s*\{)", direct_depth=0)
    return owner


def _competing_known_homonyms(class_types: dict[str, tuple[str, str]], classes: dict,
                              imports: set[str], identity: str, expected: str,
                              canonical: str) -> set[str]:
    """Known same-name definitions exposed by the supported direct import scope.

    A bare carrier-end type may be admitted only when the class pins and direct
    imports identify exactly the pinned canonical definition. Another pinned
    definition with the same name competes when its exact qualified name or its
    package wildcard is directly imported. Equal qualification in distinct
    pinned files is also ambiguous; aliases of one exact file/declaration are
    not. This bounded uniqueness check reads no imported package and is not a
    general SysML name resolver.
    """
    return {
        other_owner + "::" + other_name
        for other, (other_owner, other_name) in class_types.items()
        if other_name == expected and classes[other] != classes[identity]
        and (other_owner + "::" + other_name == canonical
             or {other_owner + "::" + other_name, other_owner + "::*"} & imports)
    }


def extract_contract(root: Path, *, class_pins: dict) -> dict:
    """The trace-vocabulary contract, read from the model.

    ``class_pins`` supplies the exact file/declaration pin per class from the
    generated projection layers (:func:`model_contract.model_class_pins`). The
    contract carries the version and supersession, the endpoint class pins, the
    carrier pins, the relation rows and the retirements, plus ``id``: the digest
    of exactly that meaning (:func:`model_contract.trace_contract_id`).
    """
    text = (root / MODEL).read_text()
    package = _live_declaration(text, r"\bpackage\s+" + PACKAGE + r"(?=\s*\{)", direct_depth=0)
    if not package:
        raise ValueError("missing governed successor package")
    import_matches, _ = _owned_matches(
        package, r"\bimport\s+([A-Za-z_]\w*(?:::(?:[A-Za-z_]\w*|\*))+)\s*;")
    imports = {match.group(1) for match in import_matches}
    records = {}
    record_pattern = r"\bpart\s+(\w+)\s*:\s*(\w+Record)\s*\{"
    owned_records, _ = _owned_matches(package, record_pattern)
    for record in owned_records:
        name, kind = record.groups()
        if kind not in RECORD_FIELDS:
            raise ValueError(f"incomplete or unsupported successor record {name}: {kind}")
        block = _live_declaration(
            text, r"(?m)^[ \t]*part\s+" + re.escape(name) + r"\s*:\s*" + re.escape(kind) + r"\b",
            direct_depth=1)
        if not block:
            raise ValueError(f"missing complete record {name}")
        values = {}
        fields, field_code = _owned_matches(block, r"attribute\s+:>>\s+\w+\s*=\s*[^;]*;")
        attributes, _ = _owned_matches(block, r"\battribute\b")
        if {attribute.start() for attribute in attributes} != {field.start() for field in fields}:
            raise ValueError(f"unsupported record field in {name}")
        for field in fields:
            parsed = re.fullmatch(r'attribute\s+:>>\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*")\s*;',
                                  field_code[field.start():field.end()])
            if not parsed:
                raise ValueError(f"unsupported record field in {name}")
            key = parsed.group(1)
            if key in values:
                raise ValueError(f"duplicate record field {name}.{key}")
            values[key] = json.loads(parsed.group(2))
        if set(values) != RECORD_FIELDS[kind]:
            raise ValueError(f"incomplete or unsupported successor record {name}: {kind}")
        records.setdefault(kind, []).append(values)
    versions = records.get(VERSION_RECORD, [])
    if len(versions) != 1 or not versions[0].get("version"):
        raise ValueError("one explicit successor version required")
    for name, pin in class_pins.items():
        if (not isinstance(pin, dict) or set(pin) != {"file", "declaration"}
                or not isinstance(pin["file"], str) or not pin["file"].strip()
                or pin["file"] != pin["file"].strip()
                or not isinstance(pin["declaration"], str)
                or not re.fullmatch(r"[a-z]+(?: [a-z]+)* def [A-Za-z_]\w*", pin["declaration"])):
            raise ValueError(f"malformed class pin for {name}: {pin!r}")
    class_pin_map = {name: dict(pin) for name, pin in class_pins.items()}
    profile_classes = sorted({row[key] for row in records.get(RELATION_RECORD, [])
                              for key in ("sourceClass", "targetClass")})
    missing = [name for name in profile_classes if name not in class_pin_map]
    if missing:
        raise ValueError("missing endpoint class pin: " + ", ".join(missing))
    # Known pinned identities: the profile classes plus every class pin that
    # declares the same short name (bounded homonym competition, no resolver).
    wanted = {class_pin_map[name]["declaration"].split()[-1] for name in profile_classes}
    known = {name: pin for name, pin in class_pin_map.items()
             if name in profile_classes or pin["declaration"].split()[-1] in wanted}
    known_pins, known_types = {}, {}
    for name in sorted(known):
        pin = known[name]
        file = pin["file"]
        if Path(file).is_absolute() or ".." in Path(file).parts:
            raise ValueError("unsafe model pin")
        try:
            source = (root / file).read_text()
        except OSError as error:
            raise ValueError(f"unreadable model pin for {name}: {file}") from error
        owner = _definition_owner(source, pin["declaration"])
        if file == MODEL and owner != PACKAGE:
            raise ValueError(f"class pin outside governed successor package: {name}")
        known_pins[name] = dict(file=file, declaration=pin["declaration"])
        known_types[name] = (owner, pin["declaration"].split()[-1])
    classes = {name: known_pins[name] for name in profile_classes}
    class_types = {name: known_types[name] for name in profile_classes}
    relations, carriers = {}, {}
    for row in records.get(RELATION_RECORD, []):
        if set(row) != RECORD_FIELDS[RELATION_RECORD]:
            raise ValueError("incomplete relation profile record")
        if row["mechanism"] not in {"native-allocation", "typed-connection"}:
            raise ValueError("unsupported profile mechanism")
        carrier = _live_declaration(
            text, r"(?m)^[ \t]*connection\s+def\s+" + re.escape(row["carrier"]) + r"\b",
            direct_depth=1)
        if not carrier:
            raise ValueError("missing typed carrier")
        if _definition_owner(text, "connection def " + row["carrier"]) != PACKAGE:
            raise ValueError("carrier outside governed successor package")
        ends, _ = _owned_matches(carrier, r"\bend\s+(\w+)\s*:\s*([A-Za-z_][\w:]*)\s*;")
        declared_ends = {}
        for end in ends:
            if end.group(1) in declared_ends:
                raise ValueError(f"duplicate carrier end: {row['carrier']}.{end.group(1)}")
            declared_ends[end.group(1)] = end.group(2)
        for end, class_key in [("source", "sourceClass"), ("target", "targetClass")]:
            if row[class_key] not in class_types:
                raise ValueError("missing endpoint class pin: " + row[class_key])
            owner, expected = class_types[row[class_key]]
            canonical = owner + "::" + expected
            pin = classes[row[class_key]]
            local_definitions, _ = _owned_matches(package, r"\bdef\s+" + re.escape(expected) + r"\b")
            homonyms = _competing_known_homonyms(known_types, known_pins, imports,
                                                row[class_key], expected, canonical)
            admitted_types = {canonical} if canonical not in homonyms else set()
            if canonical not in homonyms and (pin["file"] == MODEL or
                    (not local_definitions and not homonyms and {canonical, owner + "::*"} & imports)):
                admitted_types.add(expected)
            if declared_ends.get(end, "") not in admitted_types:
                raise ValueError(f"carrier endpoint pin mismatch: {row['carrier']}.{end}")
        name = row["predicate"]
        if name in relations and any(relations[name][0][k] != row[k] for k in ("mechanism", "strength", "inverse")):
            raise ValueError("conflicting relation rows")
        if row in relations.setdefault(name, []):
            raise ValueError("duplicate endpoint combination")
        relations[name].append(row)
        if row["mechanism"] == "typed-connection":
            carriers[name] = dict(file=MODEL, declaration="connection def " + row["carrier"])
    retirements = {}
    for row in records.get(RETIREMENT_RECORD, []):
        if not row.get("reason") or row["predicate"] in retirements:
            raise ValueError("invalid retirement record")
        retirements[row["predicate"]] = row["reason"]
    inverse_names = [rows[0]["inverse"] for rows in relations.values() if rows[0]["inverse"]]
    if len(inverse_names) != len(set(inverse_names)) or set(inverse_names) & (set(relations) | set(retirements)) or set(relations) & set(retirements):
        raise ValueError("overlapping relationship identities")
    contract: dict = dict(schema=versions[0]["version"], supersedes=versions[0]["supersedes"],
                          classes=classes, carriers=carriers, relations=relations, retired=retirements)
    contract["id"] = mc.trace_contract_id(contract)
    return contract


def build_document(root: Path) -> dict:
    """The generated file: the contract read from the model, with the current class pins."""
    _records, provisions = mc.load_model_layers(root)
    contract = extract_contract(root, class_pins=mc.model_class_pins(provisions))
    return {"schema": mc.TRACE_CONTRACT_SCHEMA, "warning": WARNING, "contract": contract}


def run_check_errors(root: Path) -> list[str]:
    """Require the committed file to equal regeneration from the current sources."""
    try:
        document = build_document(root)
    except (ValueError, OSError) as exc:
        return [f"{MODEL}: trace-vocabulary contract cannot be generated: {exc}"]
    path = root / mc.TRACE_CONTRACT_PATH
    if not path.is_file():
        return [f"{mc.TRACE_CONTRACT_PATH}: missing; run {GENERATOR} and commit the output "
                "with the source change"]
    if mc.canonical_json(document).encode("utf-8") != path.read_bytes():
        return [f"{mc.TRACE_CONTRACT_PATH}: differs from regeneration from the current sources; "
                f"run {GENERATOR} and commit the output with the source change "
                "(docs/guides/generated-semantic-assets.md)"]
    return []
