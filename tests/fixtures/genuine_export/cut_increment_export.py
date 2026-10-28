#!/usr/bin/env python3
"""Cut a small, self-contained export of one increment from a genuine full-model export.

    python tests/fixtures/genuine_export/cut_increment_export.py <export.json> <INC-ID> <out.json.gz> \\
        <declared package kept in full> [...] [--keep-mapping=<qualified name of a signal mapping> ...] \\
        [--keep-package=<top-level package of another increment, kept in full> ...]

Elements are kept unchanged, so every serializer shape is the real one: the
owned subtrees of the named declared packages, of the package declaring the
increment's workflow and of the library definitions whose features kept
content redefines; the other declared packages as package elements; each
top-level package named with ``--keep-package`` (of another increment, such as
INC-MW-011's operational context, for the binding shapes of its story); every
kernel declaration, a kernel enumeration with its literals; every library
declaration a check binds by identity (the VSS signal metadata); each signal
mapping named with ``--keep-mapping``, with the definitions its target's
signals are read through and the VSS metadata annotating them (what
``carried_vss_paths`` walks); and, transitively, what kept elements reference,
with their non-membership relationships and owner chains (owned members of a
referenced element are not followed). Output: canonical JSON (sorted keys, no
spaces), gzip-compressed, with a ``cut_from`` record of the source export and
the sha256 of the cut's own elements and element sources (see README.md).
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
from de4sdv.semantic.relation_checks import (  # noqa: E402
    SIGNAL_CARRIERS,
    VSS_SIGNAL_METADATA,
    allocation_ends,
    member_features,
    type_lineage,
)

OWNED = ("ownedRelationship", "ownedRelatedElement")


def canonical(value) -> bytes:
    """The cut's serialization: sorted keys, no spaces."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode()


def _ids(value) -> list[str]:
    if isinstance(value, dict):
        return [value["@id"]] if "@id" in value else []
    return [found for item in value for found in _ids(item)] if isinstance(value, list) else []


def main(source: Path, increment: str, target: Path, full_packages: set[str], mappings: list[str],
         other_packages: list[str] = ()) -> None:
    raw_bytes = source.read_bytes()
    raw = json.loads(raw_bytes)
    by_id = {element["@id"]: element for element in raw["elements"]}
    snapshot = load_export_snapshot(source, None, root=ROOT)
    view = export_view(snapshot, root=ROOT)
    scope = resolve_increment(view, increment)
    keep: set[str] = set()

    def subtrees(seeds) -> list[str]:
        """Keep the owned subtrees of the seeds; return what was added."""
        added, stack = [], list(seeds)
        while stack:
            current = stack.pop()
            if current in by_id and current not in keep:
                keep.add(current)
                added.append(current)
                stack.extend(found for key in OWNED for found in _ids(by_id[current].get(key)))
        return added

    def close(frontier) -> None:
        """Keep what the frontier references, with non-membership relationships and owner chains."""
        frontier = list(frontier)
        while frontier:
            element = by_id[frontier.pop()]
            following = [found for key, value in element.items() if key not in (*OWNED, "@id", "elementId")
                         for found in _ids(value)]
            following += [found for found in _ids(element.get("ownedRelationship"))
                          if not str(by_id.get(found, {}).get("@type", "")).endswith("Membership")]
            for found in following:
                if found in by_id and found not in keep:
                    keep.add(found)
                    frontier.append(found)

    workflow, _reason = workflow_of(view, scope.charters[0])
    subtrees([p for p in scope.scope_packages if view.index.name_of(p) in full_packages] + [view.top_package(workflow)])
    for name in other_packages:
        (package,) = [element["@id"] for element in view.names.resolve(name)]
        subtrees([package])
    keep.update(scope.scope_packages)
    kernel = [binding.element_id for binding in snapshot.kernel_bindings]
    # A kernel enumeration keeps its literals: remedies name them (SignalMappingDisposition::candidate).
    subtrees([found for found in kernel if by_id.get(found, {}).get("@type") == "EnumerationDefinition"])
    keep.update(kernel)
    subtrees(snapshot.library_bindings.values())
    for qualified in mappings:
        (mapping,) = [element["@id"] for element in view.names.resolve(qualified)]
        subtrees([mapping])
        signal_closure(view, allocation_ends(view)[mapping][0][1], subtrees, raw["element_sources"])
    vss = view.index.specializations(snapshot.library_bindings[VSS_SIGNAL_METADATA]) if mappings else frozenset()
    subtrees([metadata for metadata in view.index.elements_of_type("MetadataUsage")
              if view.index.typed_by(metadata) & vss and {
                  found for relationship in view.index.owned_relationships(metadata, "Annotation")
                  for found in _ids(relationship.get("annotatedElement"))} & keep])
    close(keep)
    redefined = [_ids(by_id[r].get("redefinedFeature")) for r in keep
                 if by_id[r].get("@type") == "Redefinition" and not by_id[r].get("isImplied")]
    bases = {view.index.owner_of(found[0]) for found in redefined if found} - {None}
    bases = [base for base in bases if raw["element_sources"].get(base, "").startswith(".sysand/lib/")]
    keep.difference_update(bases)
    close(subtrees(bases))
    elements = [element for element in raw["elements"] if element["@id"] in keep]
    sources = {element["@id"]: raw["element_sources"][element["@id"]] for element in elements}
    data = canonical({
        "schema": raw["schema"], "git_commit": raw["git_commit"],
        "cut_from": {"export_sha256": hashlib.sha256(raw_bytes).hexdigest(), "increment": increment,
                     "full_packages": sorted(full_packages), "kept_mappings": sorted(mappings),
                     **({"kept_packages": sorted(other_packages)} if other_packages else {}),
                     "elements": len(raw["elements"]),
                     "content_sha256": {"elements": hashlib.sha256(canonical(elements)).hexdigest(),
                                        "element_sources": hashlib.sha256(canonical(sources)).hexdigest()}},
        "elements": elements,
        "element_sources": sources,
        "external_references": [],
        "source_manifest": [entry for entry in raw.get("source_manifest", [])
                            if entry.get("path") in set(sources.values())],
    })
    target.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    print(f"kept {len(elements)} of {len(raw['elements'])} elements; {len(data) // 1024} KB, "
          f"{target.stat().st_size // 1024} KB compressed")


def signal_closure(view, target: str, subtrees, element_sources) -> None:
    """Keep the subtrees of the model definitions the signals at ``target`` are read through: its type
    lineage and that of the ports, items and attributes it carries, as ``carried_vss_paths`` walks them
    (library definitions stay referenced elements only)."""
    frontier, seen = [(target, 0)], set()
    while frontier:
        current, depth = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        subtrees([definition for definition in type_lineage(view, current)
                  if not element_sources.get(definition, "").startswith(".sysand/lib/")])
        if depth < 4:
            frontier.extend((feature, depth + 1) for feature in member_features(view, current)
                            if str(view.index.element(feature).get("@type")) in SIGNAL_CARRIERS)


if __name__ == "__main__":
    options = [argument for argument in sys.argv[4:] if argument.startswith("--keep-mapping=")]
    packages = [argument for argument in sys.argv[4:] if argument.startswith("--keep-package=")]
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), set(sys.argv[4:]) - set(options) - set(packages),
         [option.split("=", 1)[1] for option in options], [option.split("=", 1)[1] for option in packages])
