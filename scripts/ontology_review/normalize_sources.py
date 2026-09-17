"""Canonical source normalization for the 93-entry review (integration-repair stage; provenance tool).

Root cause of the v1 corruption: the v1 integrator iterated free-text string
fields (consumers/decisions/evidence) character-by-character. This stage
converted every legacy decision file into the canonical machine-readable
schema BEFORE integration, so the integrator can consume strictly typed data
and fail loudly on anything unexpected.

This tool operated on the review working archive (pre-repair sources are
audit-only and are NOT committed to the governed tree). It is retained here to
document the exact v1 -> v2 canonicalization transform; the canonical outputs
it produced live under docs/method-conformance/o4/ontology-review/decisions/.

Usage:
    python scripts/ontology_review/normalize_sources.py <review-working-archive-dir>

Inputs (in the given working-archive dir): parent-decisions.json,
method-decisions.json, ple-decisions.json, base-records.json
Outputs: parent-decisions-v2.json, method-decisions-v2.json, ple-decisions-v2.json
(architecture is handled by arch_recheck.py -> architecture-decisions-v2.json)
"""
from pathlib import Path
import json, re, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: normalize_sources.py <review-working-archive-dir>")
WORK = Path(sys.argv[1])
BASE = {r['identity']: r for r in json.loads((WORK / 'base-records.json').read_text())}

def classify_path(p):
    if p.startswith('docs/architecture-decisions'):
        return 'ADR'
    if 'docs/method-conformance' in p:
        return 'review'
    if p.startswith('tests/') or '/test_' in p or p.startswith('scripts/'):
        return 'test'
    if p.startswith('evidence/'):
        return 'evidence-artifact'
    if p.startswith('textual-notation-of-model') or p.startswith('model-based-product-line-engineering'):
        return 'model'
    if p.startswith('de4sdv/') or p.startswith('tools/'):
        return 'runtime'
    return 'repository'

def parse_consumers(v):
    """Accept str (semicolon-joined free text), list[str], or list[dict]; emit structured objects."""
    out = []
    if isinstance(v, str):
        items = v.split(';')
    elif isinstance(v, list):
        items = v
    else:
        items = [v]
    for it in items:
        if isinstance(it, dict):
            path = it.get('path')
            sym = it.get('symbol') or it.get('symbol_or_surface')
            role = it.get('role')
            entry = {'path': path, 'symbol_or_surface': sym, 'role': role}
            if it.get('evidence'):
                entry['evidence'] = str(it['evidence'])
            out.append(entry)
            continue
        s = str(it).strip().rstrip('.')
        if not s:
            continue
        head, sep, tail = s.partition(' ')
        if sep and ('/' in head or head.endswith(('.sysml', '.py', '.md', '.json', '.yaml', '.toml'))):
            out.append({'path': head, 'symbol_or_surface': tail or None, 'role': None})
        elif '/' in s and ' ' not in s:
            out.append({'path': s, 'symbol_or_surface': None, 'role': None})
        else:
            out.append({'path': None, 'symbol_or_surface': s, 'role': None})
    return out

def parse_norm_ref(v):
    if v is None:
        return []
    if isinstance(v, list):
        items = [str(x) for x in v]
    else:
        items = str(v).split(';')
    out = []
    for seg in items:
        s = seg.strip()
        if not s:
            continue
        if s.startswith('KerML'):
            src = 'KerML 1.0'
        elif s.startswith('SysML'):
            src = 'SysML 2.0' if ' 2.0' in s else 'SysML v2'
        elif 'PDF' in s or 'PDF page' in s:
            src = 'SysML v2'
        else:
            src = 'DE4SDV review basis'
        out.append({'source': src, 'reference': s})
    return out

def parse_evidence(v, identity):
    items = v if isinstance(v, list) else ([v] if v else [])
    out = []
    for it in items:
        s = str(it).strip().rstrip('.')
        if not s:
            continue
        note = None
        if ' (' in s:
            s, _, rest = s.partition(' (')
            note = '(' + rest
        elif '; ' in s:
            s, _, rest = s.partition('; ')
            note = rest
        head, _, tail = s.partition(' ')
        if tail and ('/' in head or re.search(r'\.(md|py|sysml|json|yaml|toml)', head)):
            s = head
            note = (tail + (' ' + note if note else '')).strip()
        s = s.strip()
        t = classify_path(s) if ('/' in s) else ('normative-spec' if ('§' in s or s.startswith(('SysML', 'KerML'))) else 'review')
        finding = f"Reviewed anchor for {identity} ({t})."
        if note:
            finding += ' ' + note.strip()
        out.append({'type': t, 'path_or_reference': s, 'finding': finding})
    return out

def parse_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    return [str(x) for x in v]

def build(src_file, out_file):
    rows = json.loads((WORK / src_file).read_text())
    out = []
    for r in rows:
        n = r['identity']
        base = BASE[n]
        implicit = r.get('implicit_rule') or r.get('implicit_rule_and_api_handling')
        if isinstance(implicit, dict):
            implicit = dict(implicit)
            if r.get('api_handling') and not implicit.get('current_handling'):
                implicit['current_handling'] = r['api_handling']
        elif implicit is None:
            implicit = None
        elif r.get('api_handling'):
            implicit = {'rule': str(implicit), 'source': None, 'api_observable': None,
                        'current_handling': str(r['api_handling'])}
        else:
            implicit = {'rule': str(implicit), 'source': None, 'api_observable': None,
                        'current_handling': None}
        row = {
            'identity': n,
            'kind': base['kind'],
            'o3_protected': bool(base['o3_13']),
            'classification': r['classification'],
            'source': r['source'],
            'normative_reference': parse_norm_ref(r.get('normative_reference')),
            'delta': r['delta'],
            'disposition': r['disposition'],
            'target_authority': r['target_authority'],
            'target_definition': r['target_definition'],
            'migration': r['migration'],
            'rationale': r['rationale'],
            'consumers': parse_consumers(r.get('consumers')),
            'evidence': parse_evidence(r.get('evidence'), n),
            'dependencies': parse_list(r.get('dependencies')),
            'decisions': parse_list(r.get('decisions')),
            'blocker': r.get('blocker'),
            'change_summary': r.get('change_summary') or f"Decision recorded in v1 review; canonicalized in repair stage ({r['disposition']}).",
            'implicit_rule': implicit,
            'rename_or_merge_target': r.get('rename_or_merge_target'),
        }
        out.append(row)
    assert len(out) == len(rows)
    assert {r['identity'] for r in out} == {r['identity'] for r in rows}
    (WORK / out_file).write_text(json.dumps(out, indent=2) + '\n')
    return out

par = build('parent-decisions.json', 'parent-decisions-v2.json')
met = build('method-decisions.json', 'method-decisions-v2.json')
ple = build('ple-decisions.json', 'ple-decisions-v2.json')
print('parent:', len(par), '| method:', len(met), '| ple:', len(ple))
# shape assertions
for group in (par, met, ple):
    for r in group:
        assert isinstance(r['consumers'], list) and all(isinstance(c, dict) for c in r['consumers'])
        assert all((c.get('path') is None) or (len(c['path']) != 1) for c in r['consumers'])
        assert isinstance(r['evidence'], list) and all(isinstance(e, dict) and e.get('type') and e.get('path_or_reference') for e in r['evidence'])
        assert isinstance(r['normative_reference'], list) and all(isinstance(x, dict) for x in r['normative_reference'])
        assert isinstance(r['dependencies'], list) and isinstance(r['decisions'], list)
print('canonical shape assertions passed for all three groups')