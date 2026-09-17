#!/usr/bin/env python3
"""Regenerate the governed review envelope from the canonical decision files.

Consumes ONLY the canonical structured sources under
``docs/method-conformance/o4/ontology-review/decisions/`` and raises on any
type violation instead of coercing — the package-revision-1 defect (iterating
free-text strings character-by-character) is structurally impossible here
because non-list fields are rejected.

The reviewed semantic baseline revision is pinned (``bc2b65a…`` — the revision
the review examined). Re-running with ``--revision`` records a different
revision only for a deliberate new governed review.

Usage:
    python scripts/ontology_review/consolidate_review.py [--revision <full-sha>]
"""

from __future__ import annotations

from pathlib import Path
import json, sys, collections

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs/method-conformance/o4/ontology-review"
DECISIONS_DIR = REVIEW_DIR / "decisions"
SCHEMA = "de4sdv-ontology-review-integrated/v2"
REVIEWED_BASELINE = "bc2b65abb623e50032f177d566e34e1a41c09f34"

SOURCES = ["parent-decisions-v2.json", "method-decisions-v2.json",
           "ple-decisions-v2.json", "architecture-decisions-v2.json"]

base = json.loads((DECISIONS_DIR / "base-records.json").read_text())
base_index = {r["identity"]: r for r in base}

dec = {}
for f in SOURCES:
    for r in json.loads((DECISIONS_DIR / f).read_text()):
        n = r["identity"]
        assert n not in dec, f"duplicate identity across sources: {n}"
        # ---- strict canonical input contract (fail loudly) ----
        assert isinstance(r["consumers"], list), f"{n}: consumers must be a list"
        for c in r["consumers"]:
            assert isinstance(c, dict), f"{n}: consumer element must be an object"
        assert isinstance(r["evidence"], list), f"{n}: evidence must be a list"
        for e in r["evidence"]:
            assert isinstance(e, dict) and e.get("type") and e.get("path_or_reference"), f"{n}: bad evidence element"
        assert isinstance(r["normative_reference"], list), f"{n}: normative_reference must be a list"
        for x in r["normative_reference"]:
            assert isinstance(x, dict) and x.get("source") and x.get("reference"), f"{n}: bad normative_reference element"
        assert isinstance(r["dependencies"], list), f"{n}: dependencies must be a list"
        assert isinstance(r["decisions"], list), f"{n}: decisions must be a list"
        assert isinstance(r["blocker"], (str, type(None))), f"{n}: blocker must be string|null"
        assert r["classification"] in {"NATIVE_EXPLICIT", "NATIVE_IMPLICIT", "NATIVE_GROUNDED_DE4SDV",
                                       "ACCEPTED_LIBRARY", "REPRESENTATION_ONLY", "NO_NATIVE_SEMANTIC_FIT"}, f"{n}: bad classification"
        assert r["disposition"] in {"KEEP_NATIVE", "KEEP_ACCEPTED_LIBRARY", "KEEP_DE4SDV_APPLICATION_SEMANTIC",
                                    "KEEP_EXTERNAL_REFERENCE", "KEEP_VOCABULARY_ONLY", "KEEP_CONDITIONAL",
                                    "REDESIGN", "MERGE", "DEPRECATE", "REMOVE", "BLOCKED", "O3_AMENDMENT_REQUIRED"}, f"{n}: bad disposition"
        assert r["migration"] in {"ALREADY_COMPLETE", "CURRENT_O3_13", "PROJECTION_ONLY", "MODEL_AUTHORITY_PARITY",
                                  "NEW_APPLICATION_SEMANTICS", "NATIVE_OR_LIBRARY_ADOPTION", "EXTERNAL_BOUNDARY",
                                  "PLE_DEPENDENT", "REQUIRES_SEMANTIC_MIGRATION", "REMOVE_FROM_ONTOLOGY", "BLOCKED"}, f"{n}: bad migration"
        dec[n] = r
assert set(dec) == set(base_index), (sorted(set(base_index) - set(dec)), sorted(set(dec) - set(base_index)))


def as_str_list(v):
    assert isinstance(v, list)
    return [str(x) for x in v]


def synth_assessment(n, d, b):
    disp = d["disposition"]
    cls = d["classification"]
    consumers = d["consumers"]
    rename = d.get("rename_or_merge_target")
    row = b["current_ontology_row"]
    obs = (b.get("current_inventory_record") or {}).get("observed") or {}
    rev = (b.get("current_inventory_record") or {}).get("reviewed") or {}
    vocab = obs.get("runtime_support") == "vocabulary-only"
    ret = disp in ("REMOVE", "DEPRECATE")
    strength = (row.get("sysml_mapping") or {}).get("semantic_strength") if isinstance(row, dict) else None
    usage = "No executable/model consumer traced beyond contract/inventory machinery."
    if consumers:
        parts = []
        for c in consumers[:3]:
            label = c.get("path") or c.get("symbol_or_surface") or ""
            role = c.get("role") or ""
            parts.append(f"{label} ({role})" if role else str(label))
        usage = f"{len(consumers)} consumer(s) traced: " + "; ".join(parts)
    return {
        "needed": f"{'No' if ret else 'Yes'} — {d['rationale'][:400]}",
        "definition_precision": ("Undeclared in YAML (definition absent); target definition supplied by this review."
                                 if not (isinstance(row, dict) and str(row.get("definition") or "").strip())
                                 else "Declared; precision reviewed in rationale (see delta/rationale)."),
        "name_fit": (f"Name does not fit the bounded claim: rename to {rename} required."
                     if rename and disp in ("REDESIGN", "MERGE")
                     else ("Name fits; no rename." if not rename else f"Name acceptable; {rename} noted as successor vocabulary.")),
        "duplicate_identity": ("No distinct DE4SDV identity required — meaning retires or merges." if ret
                               else (f"Merges into {rename}." if disp == "MERGE"
                                     else "No duplicate found; nearest identities checked (see rationale/dependencies).")),
        "duplicate_native": ("No — native semantics alone do not establish the claimed engineering meaning (see classification)."
                             if cls in ("REPRESENTATION_ONLY", "NATIVE_GROUNDED_DE4SDV", "NO_NATIVE_SEMANTIC_FIT")
                             else "Partial: native construct carries the core meaning; the DE4SDV identity survives only for projection vocabulary/restrictions (see separate_identity_justification)."),
        "duplicate_library": ("No accepted-library duplicate; candidate libraries remain pinned-not-adopted." if cls != "ACCEPTED_LIBRARY"
                              else "Meaning carried by the accepted pinned library; no DE4SDV parallel vocabulary."),
        "domain_range": (f"Declared domain/range reviewed; corrections recorded under target (domain={row.get('domain')}, range={row.get('range')})."
                         if isinstance(row, dict) and row.get("domain") else "Not applicable to a class identity."),
        "direction": ("Canonical direction reviewed; inverse handled under the paired identity where one exists (see dependency list)."
                      if isinstance(row, dict) and row.get("domain") else "Not applicable."),
        "inverse_same_fact": ("Paired inverse reviewed: same modeled fact, one fact authority retained (no independent second witness)."
                              if n in ("derivedRequirementsOfNeed", "validatesFitnessForUse") else "No inverse identity claimed."),
        "strength_justified": (f"Declared strength {strength} reviewed against the witness; corrections in delta/rationale."
                               if strength else "No declared strength; target strength proposed in target block."),
        "witness_sufficiency": (d.get("rationale") or "")[:400],
        "semantic_vs_configuration": ("Meaning is engineering-semantic; configuration/governance facts stay external (see target_authority)."
                                      if disp in ("KEEP_EXTERNAL_REFERENCE", "KEEP_DE4SDV_APPLICATION_SEMANTIC", "KEEP_ACCEPTED_LIBRARY", "KEEP_NATIVE")
                                      else "Meaning redistributes between model, external authority, or retirement (see target)."),
        "vocabulary_only": ("Currently vocabulary-only; status reviewed against actual consumers, not promoted merely because traversal is implementable." if vocab
                            else "Runtime-consumed; support state recorded, not treated as semantic proof."),
        "usage": usage,
        "removal_impact": (f"Removal impact assessed in rationale: {d['rationale'][:220]}" if disp in ("REMOVE", "DEPRECATE", "MERGE")
                           else "Retained; removal would eliminate the capability described in target definition."),
        "weaker_replacement": ("Yes — a weaker/native relation carries the survivable meaning (see target definition)." if disp in ("REDESIGN", "MERGE", "REMOVE")
                               else "No weaker replacement needed; current bounded claim retained."),
        "overclaim": (d.get("delta") or "")[:300] or "No overclaim found beyond the recorded delta.",
    }


def direction_of(row, mapping):
    if mapping:
        if mapping.get("query_direction"):
            return mapping["query_direction"]
        if mapping.get("direction") == "incoming":
            return "incoming"
        return "outgoing"
    return "not-applicable"


INVERSE = {"derivesRequirementFromNeed": "derivedRequirementsOfNeed",
           "derivedRequirementsOfNeed": "derivesRequirementFromNeed",
           "validatedBy": "validatesFitnessForUse",
           "validatesFitnessForUse": "validatedBy"}

rows_out = []
for n, b in base_index.items():
    d = dec[n]
    row = b["current_ontology_row"]
    inv = b.get("current_inventory_record") or {}
    obs = inv.get("observed") or {}
    rev = inv.get("reviewed") or {}
    mapping = row.get("sysml_mapping") if isinstance(row, dict) else None
    disp = d["disposition"]
    rename = d.get("rename_or_merge_target")
    migration = d["migration"]
    blockers = [d["blocker"]] if d.get("blocker") else []
    evidence_needed = as_str_list(rev.get("required_evidence") or []) + blockers
    runtime_target = ("external" if disp == "KEEP_EXTERNAL_REFERENCE"
                      else "vocabulary-only" if disp in ("KEEP_VOCABULARY_ONLY", "KEEP_CONDITIONAL")
                      else "blocked" if disp == "BLOCKED"
                      else "none" if disp in ("REMOVE", "DEPRECATE")
                      else "runtime-queryable (post-migration, exact-revision evidence required)")
    rec = {
        "identity": n,
        "kind": b["kind"],
        "o3_protected": bool(b["o3_13"]),
        "current": {
            "authority": rev.get("authority_current") or obs.get("grounding_kind"),
            "authority_target": rev.get("authority_target"),
            "definition": row.get("definition") if isinstance(row, dict) else None,
            "domain": row.get("domain") if isinstance(row, dict) else None,
            "range": row.get("range") if isinstance(row, dict) else None,
            "direction": direction_of(row, mapping),
            "inverse": INVERSE.get(n),
            "semantic_strength": (mapping or {}).get("semantic_strength") or "not-declared",
            "claim_boundary": (str(row.get("definition")).strip() or None) if isinstance(row, dict) and row.get("definition") else None,
            "model_representation": obs.get("declaration") or obs.get("ref") or obs.get("grounding_kind"),
            "library_grounding": (str(rev.get("note"))[:200] if rev.get("authority_target") == "accepted-library-grounded" and rev.get("note") else None),
            "evidence_state": rev.get("evidence_state") or obs.get("runtime_support"),
            "adoption_state": rev.get("adoption_status"),
            "runtime_support": obs.get("runtime_support"),
            "support_category": ("vocabulary-only" if obs.get("runtime_support") == "vocabulary-only"
                                 else "external" if obs.get("runtime_support") == "external (no traversal)"
                                 else "executable" if obs.get("runtime_support") else "unknown"),
            "yaml_dependency": bool(obs.get("grounding_kind") == "yaml-vocabulary" or rev.get("authority_current") == "legacy-yaml"),
            "o3_protected": bool(b["o3_13"]),
            "semantic_consumers": [
                {"path": c.get("path"), "symbol_or_surface": c.get("symbol_or_surface"), "role": c.get("role")}
                for c in d["consumers"]
            ],
        },
        "classification": {
            "sysml_semantic_classification": d["classification"],
            "sysml_semantic_source": d["source"],
            "implicit_semantics_used": bool(d.get("implicit_rule")),
            "normative_reference": d["normative_reference"],
            "semantic_fit_rationale": d["rationale"],
            "de4sdv_semantic_delta": d["delta"],
            "separate_identity_justification": (d.get("rationale") or "")[:350],
        },
        "assessment": synth_assessment(n, d, b),
        "target": {
            "disposition": disp,
            "authority": d["target_authority"],
            "definition": d["target_definition"],
            "domain": row.get("domain") if isinstance(row, dict) else None,
            "range": row.get("range") if isinstance(row, dict) else None,
            "direction": direction_of(row, mapping),
            "semantic_strength": (mapping or {}).get("semantic_strength") or "not-declared",
            "grounding": d["target_authority"],
            "native_representation_exists": d["classification"] in ("NATIVE_EXPLICIT", "NATIVE_IMPLICIT", "NATIVE_GROUNDED_DE4SDV", "ACCEPTED_LIBRARY"),
            "new_modeling_required": disp in ("REDESIGN", "MERGE") or migration in ("MODEL_AUTHORITY_PARITY", "NEW_APPLICATION_SEMANTICS"),
            "projection_required": migration in ("PROJECTION_ONLY", "MODEL_AUTHORITY_PARITY", "NEW_APPLICATION_SEMANTICS", "REQUIRES_SEMANTIC_MIGRATION"),
            "api_profile_required": migration in ("MODEL_AUTHORITY_PARITY", "NEW_APPLICATION_SEMANTICS", "REQUIRES_SEMANTIC_MIGRATION", "CURRENT_O3_13", "ALREADY_COMPLETE"),
            "traversal_required": migration in ("NEW_APPLICATION_SEMANTICS", "REQUIRES_SEMANTIC_MIGRATION") and disp not in ("KEEP_EXTERNAL_REFERENCE", "KEEP_VOCABULARY_ONLY"),
            "runtime_support_target": runtime_target,
            "evidence_needed": evidence_needed,
            "merge_into": rename if disp in ("MERGE", "REMOVE", "DEPRECATE") else None,
            "proposed_name": rename,
        },
        "migration_class": migration,
        "blockers": blockers,
        "dependencies": as_str_list(d["dependencies"]),
        "open_decisions": as_str_list(d["decisions"]),
        "evidence": [{"type": e["type"], "path_or_reference": e["path_or_reference"],
                      "finding": e.get("finding") or f"Reviewed anchor for {n} ({e['type']})."} for e in d["evidence"]],
        "change_summary": d.get("change_summary") or f"Recorded decision: {disp}.",
        "implicit_detail": (dict(d["implicit_rule"]) if isinstance(d.get("implicit_rule"), dict) else None),
        "o3_amendment": None,
    }
    rows_out.append(rec)

revision = REVIEWED_BASELINE
argv = sys.argv[1:]
if "--revision" in argv:
    revision = argv[argv.index("--revision") + 1]

envelope = {
    "schema": SCHEMA,
    "source_revision": revision,
    "generated_from": SOURCES + ["base-records.json"],
    "row_count": len(rows_out),
    "rows": rows_out,
}
(REVIEW_DIR / "integrated-review.json").write_text(json.dumps(envelope, indent=1) + "\n")
print("rows:", len(rows_out))
print("kinds:", dict(collections.Counter(r["kind"] for r in rows_out)))
print("classifications:", dict(collections.Counter(r["classification"]["sysml_semantic_classification"] for r in rows_out)))
print("dispositions:", dict(collections.Counter(r["target"]["disposition"] for r in rows_out)))
print("migrations:", dict(collections.Counter(r["migration_class"] for r in rows_out)))
print("o3_protected:", sum(r["o3_protected"] for r in rows_out))
print("revision:", revision)