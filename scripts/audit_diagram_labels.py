"""Audit: which diagram labels fail hover resolution, and why."""
import re
import sys
from pathlib import Path

sys.path.insert(0, '.')
from tools.sysml_html_viewer.model_parse import load_model, build_member_index
from tools.sysml_html_viewer.svg_info import extract_text_labels, _normalize, resolve_labels

REPO = Path('.')

# 1. current index (same roots as the viewer)
from tools.sysml_html_viewer.generate import DEFAULT_ROOTS
files = load_model(REPO, DEFAULT_ROOTS)
index = build_member_index(files)

# 2. every declared name in the whole repo (any .sysml)
all_names = set()
for p in REPO.rglob('*.sysml'):
    if '.git' in p.parts or 'workspace' in p.parts:
        continue
    text = p.read_text(encoding='utf-8', errors='replace')
    all_names.update(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))

# 3. audit every diagram svg under the model
diagrams = sorted(REPO.rglob('diagrams/diagram-*.svg'))
unresolved_total = {}
diagram_stats = []
for svg in diagrams:
    labels = extract_text_labels(svg.read_text(encoding='utf-8', errors='replace'))
    resolved = resolve_labels(labels, index, view_file=svg.as_posix(), view_folder=svg.parent.as_posix())
    resolved_set = {r.label for r in resolved}
    unresolved = [l for l in labels if l not in resolved_set]
    diagram_stats.append((svg, len(labels), len(resolved), unresolved))
    for l in unresolved:
        unresolved_total.setdefault(l, 0)
        unresolved_total[l] += 1

print(f"diagrams: {len(diagrams)}")
resolved_all = sum(s[2] for s in diagram_stats)
labels_all = sum(s[1] for s in diagram_stats)
print(f"labels total: {labels_all}, resolved: {resolved_all}, unresolved: {labels_all - resolved_all}")
print(f"unique unresolved labels: {len(unresolved_total)}\n")

# classify unresolved
classified = {}
for label, count in sorted(unresolved_total.items(), key=lambda x: -x[1]):
    cands = _normalize(label)
    name = cands[0] if cands else ''
    base = name.split('::')[0].strip("'") if '::' in name else name.strip("'")
    if not base:
        cls = 'empty'
    elif base in index:
        cls = 'IN-INDEX-BUT-FAILED'  # should not happen; resolution bug
    elif base in all_names:
        cls = 'declared-elsewhere'
    else:
        cls = 'not-in-model'
    classified.setdefault(cls, []).append((label, count))

for cls, items in classified.items():
    print(f"--- {cls}: {len(items)}")
    for label, count in items[:12]:
        print(f"   x{count:<3} {label[:90]!r}")

print("\n--- per-diagram unresolved (top 8) ---")
for svg, n, r, un in sorted(diagram_stats, key=lambda s: -len(s[3]))[:8]:
    print(f"{svg.as_posix()}  labels={n} resolved={r} unresolved={len(un)}")
    for l in un[:6]:
        print(f"    - {l[:80]!r}")
