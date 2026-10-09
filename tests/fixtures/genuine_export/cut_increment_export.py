#!/usr/bin/env python3
"""Cut a small, self-contained export of one increment from a genuine full-model export.

    python tests/fixtures/genuine_export/cut_increment_export.py <export.json> <INC-ID> <out.json.gz> \\
        <declared package kept in full> [...]

The cut keeps the export's own elements unchanged, so every serializer shape
is the real one:

- the full owned subtree of the named declared packages of the increment and
  of the package that declares its workflow; its other declared packages are
  kept as their package elements;
- every kernel declaration the contract binds, and the full owned subtree of
  the library definitions whose features kept content redefines;
- every element the kept content references, with its non-membership
  relationships (typing, specialization, redefinition, subsetting) and its
  owner chain, closed transitively; owned members of a referenced element
  are not followed.

The output is gzip-compressed JSON with a ``cut_from`` provenance record.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from de4sdv.semantic.export_evaluation import export_view, load_export_snapshot  # noqa: E402
from de4sdv.semantic.increment_scope import resolve_increment  # noqa: E402
from de4sdv.semantic.increment_workflow import workflow_of  # noqa: E402

OWNED = ("ownedRelationship", "ownedRelatedElement")


def _ids(value) -> list[str]:
    if isinstance(value, dict):
        return [value["@id"]] if "@id" in value else []
    if isinstance(value, list):
        return [found for item in value for found in _ids(item)]
    return []


def main(source: Path, increment: str, target: Path, full_packages: set[str]) -> None:
    raw_bytes = source.read_bytes()
    raw = json.loads(raw_bytes)
    by_id = {element["@id"]: element for element in raw["elements"]}
    snapshot = load_export_snapshot(source, None, root=ROOT)
    view = export_view(snapshot, root=ROOT)
    scope = resolve_increment(view, increment)
    workflow, _reason = workflow_of(view, scope.charters[0])
    keep: set[str] = set()

    def subtrees(seeds) -> None:
        stack = list(seeds)
        while stack:
            current = stack.pop()
            if current not in keep and current in by_id:
                keep.add(current)
                stack.extend(found for key in OWNED for found in _ids(by_id[current].get(key)))

    def close(frontier) -> None:
        frontier = list(frontier)
        while frontier:
            element = by_id[frontier.pop()]
            references = [found for key, value in element.items()
                          if key not in (*OWNED, "@id", "elementId") for found in _ids(value)]
            references += [found for found in _ids(element.get("ownedRelationship"))
                           if not str(by_id.get(found, {}).get("@type", "")).endswith("Membership")]
            for found in references:
                if found in by_id and found not in keep:
                    keep.add(found)
                    frontier.append(found)

    full = [p for p in scope.scope_packages if view.index.name_of(p) in full_packages]
    subtrees([*full, view.top_package(workflow)])
    keep.update(scope.scope_packages)
    keep.update(binding.element_id for binding in snapshot.kernel_bindings)
    close(keep)
    redefined = {_ids(by_id[r]["redefinedFeature"])[0] for r in keep if by_id[r].get("@type") == "Redefinition"
                 and not by_id[r].get("isImplied") and _ids(by_id[r].get("redefinedFeature"))}
    bases = {view.index.owner_of(feature) for feature in redefined} - {None}
    bases = [base for base in bases if raw["element_sources"].get(base, "").startswith(".sysand/lib/")]
    before = set(keep)
    keep.difference_update(bases)
    subtrees(bases)
    close(keep - before)
    elements = [element for element in raw["elements"] if element["@id"] in keep]
    files = {raw["element_sources"][element["@id"]] for element in elements}
    cut = {
        "schema": raw["schema"],
        "git_commit": raw["git_commit"],
        "cut_from": {"export_sha256": hashlib.sha256(raw_bytes).hexdigest(), "increment": increment,
                     "full_packages": sorted(full_packages), "elements": len(raw["elements"])},
        "elements": elements,
        "element_sources": {element["@id"]: raw["element_sources"][element["@id"]] for element in elements},
        "external_references": [],
        "source_manifest": [entry for entry in raw.get("source_manifest", []) if entry.get("path") in files],
    }
    data = json.dumps(cut, separators=(",", ":"), sort_keys=True).encode()
    target.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    print(f"kept {len(elements)} of {len(raw['elements'])} elements; {len(data) // 1024} KB, "
          f"{target.stat().st_size // 1024} KB compressed")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), set(sys.argv[4:]))
