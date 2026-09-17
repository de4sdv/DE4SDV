#!/usr/bin/env python3
"""Hardened validator for the governed O4 ontology-review package.

Validates ``docs/method-conformance/o4/ontology-review/integrated-review.json``
(schema ``de4sdv-ontology-review-integrated/v2``) against the pinned source
inventory (``decisions/base-records.json``) so that the package-revision-1
corruption class (free-text fields iterated into character fragments;
string-typed arrays) can never pass again:

  1. inventory integrity   : 93 rows / 59 classes / 34 relationships; exact identity set; no duplicates
  2. enum integrity        : classification / disposition / migration / evidence type
  3. type integrity        : arrays are arrays; objects are objects; strings rejected for array fields
  4. path sanity           : no one-character fragments or implausible references (type-aware)
  5. O3 integrity          : exactly the frozen 13 marked; no substantive change without an amendment record
  6. completeness          : classification, rationale, disposition, migration, evidence, blockers, open_decisions
  7. accepted-target pins  : retained target == 90 (1 removal + 2 merges, exact identities); zero O3 amendments
  8. mutation self-test    : 9 planted defects must all be rejected
  9. regression proof      : where the pre-repair audit artifact is present, it must fail this validator

Usage:
    python scripts/ontology_review/validate_review.py            # validate + (re)write validation-report.json
    python scripts/ontology_review/validate_review.py --check    # validate only, no writes

This is a governance validator; it never grants runtime semantic authority.
"""

from __future__ import annotations

from pathlib import Path
import json, copy, re

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs/method-conformance/o4/ontology-review"
SCHEMA = "de4sdv-ontology-review-integrated/v2"

CLASSIFICATIONS = {"NATIVE_EXPLICIT", "NATIVE_IMPLICIT", "NATIVE_GROUNDED_DE4SDV", "ACCEPTED_LIBRARY", "REPRESENTATION_ONLY", "NO_NATIVE_SEMANTIC_FIT"}
DISPOSITIONS = {"KEEP_NATIVE", "KEEP_ACCEPTED_LIBRARY", "KEEP_DE4SDV_APPLICATION_SEMANTIC", "KEEP_EXTERNAL_REFERENCE", "KEEP_VOCABULARY_ONLY", "KEEP_CONDITIONAL", "REDESIGN", "MERGE", "DEPRECATE", "REMOVE", "BLOCKED", "O3_AMENDMENT_REQUIRED"}
MIGRATIONS = {"ALREADY_COMPLETE", "CURRENT_O3_13", "PROJECTION_ONLY", "MODEL_AUTHORITY_PARITY", "NEW_APPLICATION_SEMANTICS", "NATIVE_OR_LIBRARY_ADOPTION", "EXTERNAL_BOUNDARY", "PLE_DEPENDENT", "REQUIRES_SEMANTIC_MIGRATION", "REMOVE_FROM_ONTOLOGY", "BLOCKED"}
EVIDENCE_TYPES = {"repository", "model", "test", "runtime", "normative-spec", "ADR", "review", "evidence-artifact"}
O3_13 = {"MethodPhase", "MethodContractObligation", "EvaluationScopeMembership", "EvaluationSourceKind",
         "TestedScopeDeclaration", "RetainedExecutionRecordReference", "AcceptanceAttestationReference",
         "VerificationCase", "hasSubject", "verifiedBy", "derivesRequirementFromNeed",
         "derivedRequirementsOfNeed", "hasRelevantArchitecture"}
O3_ALLOWED_DISPOSITIONS = {"KEEP_NATIVE", "KEEP_DE4SDV_APPLICATION_SEMANTIC", "KEEP_ACCEPTED_LIBRARY"}
ARRAY_FIELDS = ["semantic_consumers", "evidence", "dependencies", "blockers", "open_decisions", "normative_reference"]
REPO_PATH_TYPES = {"repository", "model", "test", "runtime", "ADR", "review"}

# Accepted review conclusions (package revision 2, independently rechecked).
EXPECTED_REMOVED = {"derivesNeedFromConcern"}
EXPECTED_MERGED = {"IncrementTraceabilityShell", "validatesFitnessForUse"}
EXPECTED_RETAINED = 90


def _load_base(root: Path) -> dict:
    base = json.loads((root / "docs/method-conformance/o4/ontology-review/decisions/base-records.json").read_text())
    return {r["identity"]: r for r in base}


def path_problem(p, strict_repo=False):
    if not isinstance(p, str) or not p.strip():
        return "empty/non-string path"
    s = p.strip()
    if s != p or "\n" in s:
        return f"path has leading/trailing whitespace: {p!r}"
    if len(s) <= 2:
        return f"one/two-character fragment: {s!r}"
    if strict_repo:
        core = re.sub(r"[:#]\d+([,\-–]\d+)?\+?$", "", s)  # strip trailing line references
        if " " in core:
            return f"path contains whitespace: {p!r}"
        if "/" not in core and not re.search(r"\.(md|py|sysml|json|yaml|toml)", core):
            return f"not a plausible repository reference: {p!r}"
    return None


def validate_rows(rows, base_index) -> list[str]:
    errors: list[str] = []
    ids = [r.get("identity") for r in rows]
    if len(rows) != 93:
        errors.append(f"inventory: expected 93 rows, got {len(rows)}")
    if len(set(ids)) != len(ids):
        errors.append("inventory: duplicate identity")
    missing = sorted(set(base_index) - set(ids))
    extra = sorted(set(ids) - set(base_index))
    if missing:
        errors.append(f"inventory: missing identities {missing}")
    if extra:
        errors.append(f"inventory: unknown identities {extra}")
    kinds = {r.get("kind") for r in rows}
    if kinds - {"class", "relationship"}:
        errors.append(f"inventory: bad kind values {kinds}")
    n_classes = sum(1 for r in rows if r.get("kind") == "class")
    n_rel = sum(1 for r in rows if r.get("kind") == "relationship")
    if n_classes != 59:
        errors.append(f"inventory: expected 59 classes, got {n_classes}")
    if n_rel != 34:
        errors.append(f"inventory: expected 34 relationships, got {n_rel}")

    for r in rows:
        n = r.get("identity", "<no-identity>")
        if n not in base_index:
            continue
        b = base_index[n]
        if r.get("kind") != b["kind"]:
            errors.append(f"{n}: kind changed vs inventory oracle")
        if bool(r.get("o3_protected")) != bool(b["o3_13"]):
            errors.append(f"{n}: row o3_protected mismatch")
        # --- enums ---
        cls = (r.get("classification") or {}).get("sysml_semantic_classification")
        if cls not in CLASSIFICATIONS:
            errors.append(f"{n}: invalid semantic classification {cls!r}")
        disp = (r.get("target") or {}).get("disposition")
        if disp not in DISPOSITIONS:
            errors.append(f"{n}: invalid target disposition {disp!r}")
        mig = r.get("migration_class")
        if mig not in MIGRATIONS:
            errors.append(f"{n}: invalid migration class {mig!r}")
        # --- O3 integrity ---
        if b["o3_13"]:
            if mig not in ("CURRENT_O3_13", "ALREADY_COMPLETE"):
                errors.append(f"{n}: O3-protected identity has migration {mig!r} (must be CURRENT_O3_13)")
            if disp == "O3_AMENDMENT_REQUIRED":
                am = r.get("o3_amendment")
                if not isinstance(am, dict) or not all(k in am for k in ("current_accepted_meaning", "proposed_meaning", "reason", "compatibility_impact", "equivalence_evidence")):
                    errors.append(f"{n}: O3_AMENDMENT_REQUIRED without a complete amendment record")
            elif disp not in O3_ALLOWED_DISPOSITIONS:
                errors.append(f"{n}: O3-protected identity disposition {disp!r} requires O3_AMENDMENT_REQUIRED")
        else:
            if r.get("o3_amendment") is not None:
                errors.append(f"{n}: non-O3 row carries an o3_amendment record")
        # --- type integrity ---
        cur = r.get("current") or {}
        for f in ARRAY_FIELDS:
            if f == "semantic_consumers":
                v = cur.get(f)
            elif f == "normative_reference":
                v = (r.get("classification") or {}).get(f)
            else:
                v = r.get(f)
            if not isinstance(v, list):
                errors.append(f"{n}: {f} must be an array, got {type(v).__name__}")
        cons = cur.get("semantic_consumers")
        if isinstance(cons, list):
            for c in cons:
                if not isinstance(c, dict):
                    errors.append(f"{n}: semantic_consumers element is {type(c).__name__}, not object")
                    continue
                p = c.get("path")
                sym = c.get("symbol_or_surface")
                if p is None and not (isinstance(sym, str) and sym.strip()):
                    errors.append(f"{n}: consumer has neither path nor symbol_or_surface")
                if p is not None:
                    prob = path_problem(p, strict_repo=True)
                    if prob:
                        errors.append(f"{n}: consumer {prob}")
        ev = r.get("evidence")
        if isinstance(ev, list):
            if not ev:
                errors.append(f"{n}: evidence is empty (no anchors and no explicit evidence-gap statement)")
            for e in ev:
                if not isinstance(e, dict):
                    errors.append(f"{n}: evidence element is {type(e).__name__}, not object")
                    continue
                if e.get("type") not in EVIDENCE_TYPES:
                    errors.append(f"{n}: evidence type {e.get('type')!r} not in enum")
                pref = e.get("path_or_reference")
                if e.get("type") in REPO_PATH_TYPES:
                    prob = path_problem(pref, strict_repo=True)
                else:
                    prob = None if (isinstance(pref, str) and len(pref.strip()) >= 4) else f"implausible reference {pref!r}"
                if prob:
                    errors.append(f"{n}: evidence {prob}")
                if not (isinstance(e.get("finding"), str) and e["finding"].strip()):
                    errors.append(f"{n}: evidence element missing finding text")
        nr = (r.get("classification") or {}).get("normative_reference")
        if isinstance(nr, list):
            for x in nr:
                if not isinstance(x, dict):
                    errors.append(f"{n}: normative_reference element is {type(x).__name__}, not object")
                elif not (isinstance(x.get("source"), str) and isinstance(x.get("reference"), str)):
                    errors.append(f"{n}: normative_reference element missing source/reference")
        # --- completeness ---
        if not (isinstance((r.get("classification") or {}).get("semantic_fit_rationale"), str)
                and (r.get("classification") or {}).get("semantic_fit_rationale", "").strip()):
            errors.append(f"{n}: missing semantic_fit_rationale")
        if not (isinstance(r.get("change_summary"), str) and r["change_summary"].strip()):
            errors.append(f"{n}: missing change_summary")
        if not isinstance(r.get("blockers"), list):
            errors.append(f"{n}: blockers must be an array")
        if not isinstance(r.get("open_decisions"), list):
            errors.append(f"{n}: open_decisions must be an array")
        if not isinstance(r.get("dependencies"), list):
            errors.append(f"{n}: dependencies must be an array")

    # --- accepted-target pins ---
    removed = {r["identity"] for r in rows if (r.get("target") or {}).get("disposition") == "REMOVE"}
    merged = {r["identity"] for r in rows if (r.get("target") or {}).get("disposition") == "MERGE"}
    if removed != EXPECTED_REMOVED:
        errors.append(f"accepted target: REMOVE set {sorted(removed)} != expected {sorted(EXPECTED_REMOVED)}")
    if merged != EXPECTED_MERGED:
        errors.append(f"accepted target: MERGE set {sorted(merged)} != expected {sorted(EXPECTED_MERGED)}")
    retained = len(rows) - len(removed) - len(merged)
    if retained != EXPECTED_RETAINED:
        errors.append(f"accepted target: retained {retained} != expected {EXPECTED_RETAINED}")
    amendments = [r["identity"] for r in rows if (r.get("target") or {}).get("disposition") == "O3_AMENDMENT_REQUIRED"]
    if amendments:
        errors.append(f"accepted state: O3 amendment records present {sorted(amendments)}; the accepted package requires none (regenerate deliberately if that changes)")
    return errors


def _mutation_selftest(rows, base_index) -> list[dict]:
    mutants: list[dict] = []

    def check_mutant(name, mutate):
        m = copy.deepcopy(rows)
        mutate(m)
        errs = validate_rows(m, base_index)
        mutants.append({"mutant": name, "rejected": bool(errs), "example_error": errs[0] if errs else None})

    check_mutant("m1 consumer path single-char fragment", lambda m: m[0]["current"]["semantic_consumers"].append({"path": "t", "symbol_or_surface": None, "role": None}))
    check_mutant("m2 consumers replaced by a string", lambda m: m[0]["current"].__setitem__("semantic_consumers", "de4sdv/semantic/x.py"))
    check_mutant("m3 unknown semantic classification", lambda m: m[0]["classification"].__setitem__("sysml_semantic_classification", "NATIVE_MAYBE"))
    check_mutant("m4 evidence emptied", lambda m: m[0].__setitem__("evidence", []))
    check_mutant("m5 duplicate identity row", lambda m: m.append(copy.deepcopy(m[0])))
    check_mutant("m6 O3 disposition changed without amendment", lambda m: [r for r in m if r["identity"] == "verifiedBy"][0]["target"].__setitem__("disposition", "REMOVE"))
    check_mutant("m7 normative_reference as bare string", lambda m: m[0]["classification"].__setitem__("normative_reference", "SysML 2.0 §x"))
    check_mutant("m8 blockers as string", lambda m: m[0].__setitem__("blockers", "some blocker"))
    check_mutant("m9 evidence single-char fragment", lambda m: m[0]["evidence"].append({"type": "repository", "path_or_reference": "e", "finding": "x"}))
    return mutants


def _load_envelope(root: Path):
    envelope = json.loads((root / "docs/method-conformance/o4/ontology-review/integrated-review.json").read_text())
    return envelope


def run_check_errors(root: Path) -> list[str]:
    """Lightweight check entry point for ``scripts/check_repo.py`` (no writes).

    Validates the governed review package and its accepted-target pins.
    """
    review = root / "docs/method-conformance/o4/ontology-review"
    errors: list[str] = []
    if not (review / "integrated-review.json").exists():
        return [f"missing governed review package: {review / 'integrated-review.json'}"]
    envelope = _load_envelope(root)
    if not isinstance(envelope, dict):
        return ["review envelope is not a JSON object"]
    if envelope.get("schema") != SCHEMA:
        return [f"review envelope schema mismatch: {envelope.get('schema')!r}"]
    base_index = _load_base(root)
    rows = envelope.get("rows")
    if not isinstance(rows, list):
        return ["review envelope rows must be a list"]
    errors.extend(validate_rows(rows, base_index))
    mutants = _mutation_selftest(rows, base_index)
    rejected = sum(1 for x in mutants if x["rejected"])
    if rejected != len(mutants):
        errors.append(f"mutation self-test: only {rejected}/{len(mutants)} mutants rejected")
    return errors


def main(argv=None) -> int:
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    check_only = "--check" in args
    root = REPO_ROOT
    review = root / "docs/method-conformance/o4/ontology-review"
    envelope = _load_envelope(root)
    base_index = _load_base(root)
    rows = envelope["rows"]
    errors = validate_rows(rows, base_index)
    mutants = _mutation_selftest(rows, base_index)
    rejected = sum(1 for x in mutants if x["rejected"])
    if rejected != len(mutants):
        errors.append(f"mutation self-test: only {rejected}/{len(mutants)} mutants rejected")

    import collections
    removed = sorted(r["identity"] for r in rows if r["target"]["disposition"] == "REMOVE")
    merged = sorted(r["identity"] for r in rows if r["target"]["disposition"] == "MERGE")
    report = {
        "schema": envelope.get("schema"),
        "review_package": "docs/method-conformance/o4/ontology-review",
        "source_revision": envelope.get("source_revision"),
        "row_count": len(rows),
        "classes": sum(1 for r in rows if r["kind"] == "class"),
        "relationships": sum(1 for r in rows if r["kind"] == "relationship"),
        "duplicates": len(rows) - len({r["identity"] for r in rows}),
        "classification_counts": dict(collections.Counter(r["classification"]["sysml_semantic_classification"] for r in rows)),
        "disposition_counts": dict(collections.Counter(r["target"]["disposition"] for r in rows)),
        "migration_counts": dict(collections.Counter(r["migration_class"] for r in rows)),
        "o3_protected": sum(1 for r in rows if r["o3_protected"]),
        "o3_amendments_required": sum(1 for r in rows if r["target"]["disposition"] == "O3_AMENDMENT_REQUIRED"),
        "accepted_target": {"retained": len(rows) - len(removed) - len(merged), "removed": removed, "merged": merged},
        "errors": errors,
        "mutation_selftest": mutants,
        "mutation_selftest_passed": rejected == len(mutants),
    }
    pre = review / "integrated-review-v1.json"
    if pre.exists():
        v1 = json.loads(pre.read_text())
        v1_rows = v1.get("rows") if isinstance(v1, dict) else v1
        reasons = []
        if not isinstance(v1, dict) or v1.get("schema") != SCHEMA:
            reasons.append("pre-repair artifact is not a v2 envelope")
        if isinstance(v1_rows, list):
            char_cons = sum(1 for r in v1_rows if isinstance(r, dict)
                            and any(isinstance(c.get("path"), str) and len(c["path"].strip()) <= 2
                                    for c in ((r.get("current") or {}).get("semantic_consumers") or []) if isinstance(c, dict)))
            if char_cons:
                reasons.append(f"{char_cons} rows with character-split semantic_consumers")
            v1_errs = validate_rows(v1_rows, base_index)
            if v1_errs:
                reasons.append(f"row validation fails: {v1_errs[0]}")
        report["pre_repair_artifact_rejected"] = bool(reasons)
        report["pre_repair_rejection_reasons"] = reasons
    else:
        report["pre_repair_artifact_rejected"] = None
        report["pre_repair_rejection_reasons"] = ["pre-repair audit artifact not present in the governed tree (audit-only; see RECHECK-REPORT.md §2)"]
    if not check_only:
        (review / "validation-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("errors", "mutation_selftest")}, indent=2)[:2600])
    print("errors:", len(errors))
    for e in errors[:20]:
        print(" -", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())