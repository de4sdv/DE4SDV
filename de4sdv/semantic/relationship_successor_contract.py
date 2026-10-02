"""Build-time model record extraction, not runtime semantic authority tables.

This bounded extractor is not a SysML validator. Licensed ingestion must validate
model notation and persist exact kernel/carrier bindings before live closure.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from .authority_inventory import declaration_block

MODEL = "textual-notation-of-model/packages/methods/de4sdv/de4sdv_relationship_carriers.sysml"
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


def _comment_free(text: str) -> str:
    """Remove comments while preserving every offset (strings stay intact)."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", lambda match: " " * len(match.group(0)), text, flags=re.S)


def _mask_strings(text: str) -> str:
    """Mask string content without moving offsets."""
    return re.sub(r'"(?:\\.|[^"\\])*"', lambda match: " " * len(match.group(0)), text)


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


def generate_contract(root: Path) -> dict:
    text = (root / MODEL).read_text()
    code = _mask_strings(_comment_free(text))
    records = {}
    for name, kind in re.findall(r"\bpart\s+(\w+)\s*:\s*(Successor\w+Record)\s*\{", code):
        # Reuse the comment/string-aware owned-body scanner for record usages.
        record_text = re.sub(r"(?m)^(\s*)part\s+" + re.escape(name) +
                             r"\s*:\s*" + re.escape(kind) + r"\b",
                             r"\1part def " + name, text)
        block, bodyless = declaration_block(record_text, "part def " + name)
        if not block or bodyless:
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
        records.setdefault(kind, []).append(values)
    versions = records.get("SuccessorVersionRecord", [])
    if len(versions) != 1 or not versions[0].get("version"):
        raise ValueError("one explicit successor version required")
    classes = {}
    inputs = {MODEL, *PROGRAM_INPUTS}
    for row in records.get("SuccessorClassRecord", []):
        name = row["identity"]
        if not name or name in classes:
            raise ValueError("duplicate or blank class identity")
        file = row["sourceFile"]
        if Path(file).is_absolute() or ".." in Path(file).parts:
            raise ValueError("unsafe model pin")
        pin, bodyless = declaration_block((root / file).read_text(), row["declaration"])
        if not pin or bodyless:
            raise ValueError(f"missing complete class declaration {name}")
        inputs.add(file)
        classes[name] = dict(file=file, declaration=row["declaration"])
    relations, carriers = {}, {}
    for row in records.get("SuccessorRelationRecord", []):
        if set(row) != {"predicate", "carrier", "mechanism", "strength", "sourceClass", "targetClass", "sourceUsage", "targetUsage", "inverse"}:
            raise ValueError("incomplete relation profile record")
        if row["mechanism"] not in {"native-allocation", "typed-connection"}:
            raise ValueError("unsupported profile mechanism")
        carrier, bodyless = declaration_block(text, "connection def " + row["carrier"])
        if not carrier or bodyless:
            raise ValueError("missing typed carrier")
        ends, _ = _owned_matches(carrier, r"\bend\s+(\w+)\s*:\s*([A-Za-z_][\w:]*)\s*;")
        declared_ends = {}
        for end in ends:
            if end.group(1) in declared_ends:
                raise ValueError(f"duplicate carrier end: {row['carrier']}.{end.group(1)}")
            declared_ends[end.group(1)] = end.group(2)
        for end, class_key in [("source", "sourceClass"), ("target", "targetClass")]:
            expected = classes[row[class_key]]["declaration"].split()[-1]
            if declared_ends.get(end, "").split("::")[-1] != expected:
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


def verify_contract(contract, root):
    regenerated = generate_contract(root)
    if regenerated != contract:
        changed = sorted(p for p, d in contract.get("bound_inputs", {}).items()
                         if not (root / p).is_file() or digest((root / p).read_bytes()) != d)
        raise ValueError("successor contract/source mismatch: " + ", ".join(changed))
    return regenerated
