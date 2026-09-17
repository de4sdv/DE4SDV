#!/usr/bin/env python3
"""Regenerate REVIEW-matrix.md from the validated v2 integrated-review.json envelope.

Usage:
    python scripts/ontology_review/generate_review_matrix.py
"""

from __future__ import annotations

from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = REPO_ROOT / "docs/method-conformance/o4/ontology-review"

envelope = json.loads((REVIEW_DIR / "integrated-review.json").read_text())
rows = envelope["rows"]
assert envelope["schema"] == "de4sdv-ontology-review-integrated/v2"
assert len(rows) == 93
out = ["# Deliverable 2 — Complete 93-entry matrix", "",
       f"Snapshot: DE4SDV `main` @ `{envelope['source_revision']}` (read-only review; package revision 2, validated).",
       "Classification: primary SysML/KerML semantic-source classification. RT = runtime support (observed).",
       "O3 = one of the 13 protected identities. Blocker \"—\" = none.", "",
       "| # | Identity | Kind | Current authority | Classification | Normative semantic source | DE4SDV semantic delta | RT | O3 | Target disposition | Target authority | Migration class | Blocker |",
       "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for i, r in enumerate(rows, 1):
    c = r["classification"]
    t = r["target"]
    src = c["sysml_semantic_source"] or ""
    if len(src) > 60:
        src = src[:57] + "..."
    delta = (c["de4sdv_semantic_delta"] or "")
    delta = delta.replace("|", "/")
    if len(delta) > 90:
        delta = delta[:87] + "..."
    auth = r["current"].get("authority") or "?"
    tgt_auth = t.get("authority") or "?"
    if len(tgt_auth) > 55:
        tgt_auth = tgt_auth[:52] + "..."
    blocker = r.get("blockers") or []
    blocker_txt = "; ".join(blocker) if blocker else "—"
    if len(blocker_txt) > 70:
        blocker_txt = blocker_txt[:67] + "..."
    out.append(f"| {i} | {r['identity']} | {r['kind']} | {auth} | {c['sysml_semantic_classification']} | {src} | {delta} | {r['current'].get('runtime_support') or '—'} | {'Y' if r['o3_protected'] else ''} | {t['disposition']} | {tgt_auth} | {r['migration_class']} | {blocker_txt} |")
(REVIEW_DIR / "REVIEW-matrix.md").write_text("\n".join(out) + "\n")
print("wrote REVIEW-matrix.md rows:", len(rows))