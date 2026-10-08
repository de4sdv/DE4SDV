"""Build-time model record extraction, not runtime semantic authority tables.

This bounded extractor is not a SysML validator. Licensed ingestion must validate
model notation and persist exact kernel/carrier bindings before live closure.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml"
PACKAGE = "DE4SDV_RelationshipSuccessor"
# Class identities are pinned by the authored ontology's kernel mappings, not by
# file-path records inside the SysML model: the model carries engineering
# semantics, the ontology carries the class-to-declaration mapping.
ONTOLOGY = "approach/framework/ontology/de4sdv-basic-ontology.yaml"
PROGRAM_INPUTS = (
    "de4sdv/semantic/relationship_successor_contract.py",
    "de4sdv/semantic/relationship_successor.py",
    "de4sdv/semantic/composition_construction.py",
    "de4sdv/semantic/authority_inventory.py",
    "de4sdv/semantic/traversal.py",
    "de4sdv/semantic/query.py",
    "de4sdv/semantic/api_binding.py",
    "de4sdv/semantic/kernel_binding_index.py",
    "de4sdv/semantic/kernel_contract.py",
    "de4sdv/semantic/model_edges.py",
    "de4sdv/semantic/relationships.py",
    "de4sdv/semantic/impact.py",
    "de4sdv/sysml_api/revisions.py",
    "de4sdv/sysml_api/repository.py",
    "de4sdv/sysml_api/client.py",
    "scripts/relationship_successor.py",
    "textual-notation-of-model/packages/features/aebs/aebs_functional_architecture.sysml",
    "textual-notation-of-model/packages/features/aebs/aebs_logical_architecture.sysml",
    "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml",
    "methodologies/sysmod-sysmlv2/pilots/aebs-needs-requirements.yaml",
    "methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml",
)


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


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


def _ontology_class_pins(root: Path) -> dict[str, dict[str, str]]:
    """Exact file/declaration pin per ontology class, from kernel mappings only.

    A class with its own ``kernel: {file, declaration}`` mapping pins that
    declaration. A natively represented class (e.g. ``Function``) is pinned by
    its unique directly specializing ontology class that has a file mapping
    (e.g. ``AllocatableFunction``). Two such specializations are ambiguous and
    pin nothing. No name lookup in model source; no record inside the model.
    """
    import yaml

    try:
        document = yaml.safe_load((root / ONTOLOGY).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ValueError("unreadable ontology for successor class pins") from error
    classes = document.get("classes") if isinstance(document, dict) else None
    if not isinstance(classes, dict):
        raise ValueError("ontology classes mapping missing")

    def file_pin(row):
        kernel = row.get("kernel") if isinstance(row, dict) else None
        if isinstance(kernel, dict) and set(kernel) == {"file", "declaration"}:
            file, declaration = kernel["file"], kernel["declaration"]
            # Malformed pins are a controlled refusal, never a raw exception.
            if (not isinstance(file, str) or not file.strip() or file != file.strip()
                    or not isinstance(declaration, str)
                    or not re.fullmatch(r"[a-z]+(?: [a-z]+)* def [A-Za-z_]\w*", declaration)):
                raise ValueError(f"malformed ontology kernel pin: {kernel!r}")
            return {"file": file, "declaration": declaration}
        return None

    pins = {}
    for name, row in classes.items():
        own = file_pin(row)
        if own:
            pins[name] = own
            continue
        specializations = [file_pin(child) for child in classes.values()
                           if isinstance(child, dict) and child.get("subClassOf") == name
                           and file_pin(child)]
        if len(specializations) == 1:
            pins[name] = specializations[0]
    return pins


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


def generate_contract(root: Path, *, class_pins: dict | None = None,
                      pin_inputs: tuple[str, ...] = ()) -> dict:
    """Generate the successor contract from the model.

    ``class_pins`` supplies the exact file/declaration pin per class from the
    model-generated projection layers (``model_contract.model_class_pins``);
    ``pin_inputs`` names the layer files those pins were read from, so they
    are bound inputs of the contract.
    """
    text = (root / MODEL).read_text()
    package = _live_declaration(text, r"\bpackage\s+" + PACKAGE + r"(?=\s*\{)", direct_depth=0)
    if not package:
        raise ValueError("missing governed successor package")
    import_matches, _ = _owned_matches(
        package, r"\bimport\s+([A-Za-z_]\w*(?:::(?:[A-Za-z_]\w*|\*))+)\s*;")
    imports = {match.group(1) for match in import_matches}
    records = {}
    record_pattern = r"\bpart\s+(\w+)\s*:\s*(Successor\w+Record)\s*\{"
    owned_records, _ = _owned_matches(package, record_pattern)
    for record in owned_records:
        name, kind = record.groups()
        block = _live_declaration(
            text, r"(?m)^[ \t]*part\s+" + re.escape(name) + r"\s*:\s*" + re.escape(kind) + r"\b",
            direct_depth=1)
        if not block:
            raise ValueError(f"missing complete record {name}")
        values = {}
        fields, field_code = _owned_matches(block, r"attribute\s+:>>\s+\w+\s*=\s*[^;]*;")
        for field in fields:
            parsed = re.fullmatch(r'attribute\s+:>>\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*")\s*;',
                                  field_code[field.start():field.end()])
            if not parsed:
                raise ValueError(f"unsupported record field in {name}")
            key = parsed.group(1)
            if key in values:
                raise ValueError(f"duplicate record field {name}.{key}")
            values[key] = json.loads(parsed.group(2))
        required_fields = {
            "SuccessorVersionRecord": {"version", "supersedes"},
            "SuccessorRelationRecord": {"predicate", "carrier", "mechanism", "strength", "sourceClass",
                                        "targetClass", "sourceUsage", "targetUsage", "inverse"},
            "SuccessorRetirementRecord": {"predicate", "reason"},
        }
        if kind not in required_fields or set(values) != required_fields[kind]:
            raise ValueError(f"incomplete or unsupported successor record {name}: {kind}")
        records.setdefault(kind, []).append(values)
    versions = records.get("SuccessorVersionRecord", [])
    if len(versions) != 1 or not versions[0].get("version"):
        raise ValueError("one explicit successor version required")
    classes, class_types = {}, {}
    if class_pins is None:
        inputs = {MODEL, ONTOLOGY, *PROGRAM_INPUTS}
        ontology_pins = _ontology_class_pins(root)
    else:
        inputs = {MODEL, *pin_inputs, *PROGRAM_INPUTS}
        ontology_pins = {name: dict(pin) for name, pin in class_pins.items()}
    profile_classes = sorted({row[key] for row in records.get("SuccessorRelationRecord", [])
                              for key in ("sourceClass", "targetClass")})
    missing = [name for name in profile_classes if name not in ontology_pins]
    if missing:
        raise ValueError("missing endpoint class pin: " + ", ".join(missing))
    # Known pinned identities: the profile classes plus every ontology pin that
    # declares the same short name (bounded homonym competition, no resolver).
    wanted = {ontology_pins[name]["declaration"].split()[-1] for name in profile_classes}
    known = {name: pin for name, pin in ontology_pins.items()
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
        inputs.add(file)
        known_pins[name] = dict(file=file, declaration=pin["declaration"])
        known_types[name] = (owner, pin["declaration"].split()[-1])
    classes = {name: known_pins[name] for name in profile_classes}
    class_types = {name: known_types[name] for name in profile_classes}
    relations, carriers = {}, {}
    for row in records.get("SuccessorRelationRecord", []):
        if set(row) != {"predicate", "carrier", "mechanism", "strength", "sourceClass", "targetClass", "sourceUsage", "targetUsage", "inverse"}:
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
    for row in records.get("SuccessorRetirementRecord", []):
        if not row.get("reason") or row["predicate"] in retirements:
            raise ValueError("invalid retirement record")
        retirements[row["predicate"]] = row["reason"]
    inverse_names = [rows[0]["inverse"] for rows in relations.values() if rows[0]["inverse"]]
    if len(inverse_names) != len(set(inverse_names)) or set(inverse_names) & (set(relations) | set(retirements)) or set(relations) & set(retirements):
        raise ValueError("overlapping relationship identities")
    payload = dict(schema=versions[0]["version"], supersedes=versions[0]["supersedes"],
                   classes=classes, carriers=carriers, relations=relations, retired=retirements,
                   bound_inputs={p: digest((root / p).read_bytes()) for p in sorted(inputs)})
    payload["id"] = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return payload


def verify_contract(contract, root, *, class_pins=None, pin_inputs=()):
    regenerated = generate_contract(root, class_pins=class_pins, pin_inputs=pin_inputs)
    if regenerated != contract:
        changed = sorted(p for p, d in contract.get("bound_inputs", {}).items()
                         if not (root / p).is_file() or digest((root / p).read_bytes()) != d)
        raise ValueError("successor contract/source mismatch: " + ", ".join(changed))
    return regenerated
