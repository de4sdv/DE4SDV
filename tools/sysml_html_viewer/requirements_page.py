"""Requirements browser page rendering for the DE4SDV static model viewer.

One standalone page (``requirements.html``) listing every need, requirement,
acceptance criterion, evidence contract, claim, argument, counterclaim, and
problem statement extracted from the model (``requirements_data``), with
kind/status filters, an ID/text search, and the ID cross-reference network.

Read-only and model-reflecting: every shown attribute comes from the
``.sysml`` textual notation; nothing is inferred or invented.
"""
from __future__ import annotations

import json

from .requirements_data import RequirementRecord, build_trace_links
from .render import esc

# record kinds shown in the kind filter, display order
_KIND_ORDER = (
    "need",
    "requirement",
    "acceptance criterion",
    "evidence contract",
    "claim",
    "argument",
    "counterclaim",
    "problem statement",
)


def _kind_badge(kind: str) -> str:
    cls = esc(kind.replace(" ", "-"))
    return f'<span class="req-kind req-kind-{cls}">{esc(kind)}</span>'


def _record_card(
    r: RequirementRecord,
    links: dict[str, list[str]],
    page_paths: dict[str, str],
    prefix: str,
) -> str:
    """One record card. ``page_paths`` maps rel_path -> page href prefix so a
    record links to its declaration on the file page."""
    rid = r.rid or r.name
    title = esc(r.rid) if r.rid else esc(r.name)
    status_html = f'<span class="req-status">{esc(r.status)}</span>' if r.status else ""
    subject_html = esc(r.subject) if r.subject else '<span class="muted">no subject</span>'
    stakeholders = (
        " · ".join(esc(s) for s in r.stakeholders) if r.stakeholders else ""
    )
    statement_html = (
        f'<p class="req-statement">{esc(r.statement)}</p>' if r.statement else ""
    )
    doc_html = f'<p class="req-doc muted">{esc(r.doc)}</p>' if r.doc else ""
    file_page = page_paths.get(r.rel_path, "")
    source_link = (
        f'<a href="{esc(file_page)}#{esc(r.anchor)}">{esc(r.rel_path)}:{r.line}</a>'
        if file_page
        else esc(r.rel_path)
    )
    trace_html = ""
    targets = links.get(r.rid, []) if r.rid else []
    if targets:
        items = "".join(
            f'<a class="req-trace-link" href="#req-{esc(t)}">{esc(t)}</a>'
            for t in targets
        )
        trace_html = f'<p class="req-trace"><span class="muted">traces:</span> {items}</p>'
    mentions_html = ""
    unlinked = [m for m in r.mentions if r.rid and m not in targets] if r.rid else r.mentions
    if unlinked:
        items = " · ".join(esc(m) for m in unlinked)
        mentions_html = (
            f'<p class="req-mentions"><span class="muted">references:</span> {items}</p>'
        )
    stakeholders_html = (
        f'<p class="req-stakeholders"><span class="muted">stakeholders:</span> '
        f"{stakeholders}</p>"
        if stakeholders
        else ""
    )
    attrs_html = ""
    if r.rationale or r.source:
        rows = ""
        if r.rationale:
            rows += f'<p class="req-attr"><span class="muted">rationale:</span> {esc(r.rationale)}</p>'
        if r.source:
            rows += f'<p class="req-attr"><span class="muted">source:</span> {esc(r.source)}</p>'
        attrs_html = f'<div class="req-attrs">{rows}</div>'
    return f"""
<article class="req-card card" id="req-{esc(rid)}" data-kind="{esc(r.kind)}" data-id="{esc(rid)}" data-search="{esc((rid + ' ' + r.name + ' ' + r.statement + ' ' + r.doc + ' ' + r.subject + ' ' + ' '.join(r.stakeholders)).lower())}">
  <div class="req-card-head">
    {_kind_badge(r.kind)}
    <h3 class="req-title">{title}</h3>
    {status_html}
  </div>
  <p class="req-subject"><span class="muted">subject:</span> {subject_html}</p>
  {stakeholders_html}
  {statement_html}
  {doc_html}
  {attrs_html}
  {trace_html}
  {mentions_html}
  <p class="req-source muted">{source_link}</p>
</article>
"""


def render_requirements_page(
    records: list[RequirementRecord],
    tree_html: str,
    breadcrumbs: list[tuple[str, str]],
    page_paths: dict[str, str],
    prefix: str,
    picker: str = "",
    filters: str = "",
    asset_stamp: str = "",
) -> str:
    """The standalone needs & requirements browser page."""
    from .render import _page_shell  # local import: render imports this module late

    links = build_trace_links(records)
    page_paths = dict(page_paths)
    cards = "".join(
        _record_card(r, links, page_paths, prefix)
        for r in sorted(
            records,
            key=lambda r: (r.rid == "", r.rid or r.name),
        )
    )
    kinds_seen = {r.kind for r in records}
    kind_chips = "".join(
        f'<button type="button" class="req-filter" data-kind="{esc(kind)}">'
        f"{esc(kind)} <span class='muted'>({sum(1 for r in records if r.kind == kind)})</span>"
        f"</button>"
        for kind in _KIND_ORDER
        if kind in kinds_seen
    )
    n_ids = sum(1 for r in records if r.rid)
    trace_json = json.dumps(links, sort_keys=True).replace("</", "<\\/")
    content = f"""
<div class="card req-header">
  <h1>Needs &amp; Requirements</h1>
  <p class="muted">{len(records)} record(s) · {n_ids} with a controlled ID ·
  extracted from the SysML v2 textual model — read-only, nothing inferred.
  Every record links to its declaration; IDs in text form the trace network.</p>
  <div class="req-controls">
    <input type="search" id="reqSearch" placeholder="Filter by ID, name, text…"
      aria-label="Filter needs and requirements">
    <div class="req-filters">{kind_chips}</div>
  </div>
  <p class="muted" id="reqStatus" hidden></p>
</div>
<div id="reqList">
{cards}
</div>
<script type="application/json" id="reqTraceData">{trace_json}</script>
"""
    return _page_shell(
        "Needs & Requirements",
        tree_html,
        breadcrumbs,
        content,
        f"{prefix}assets/viewer.css",
        f"{prefix}assets/viewer.js",
        picker=picker,
        body_class="requirements-page",
        search_prefix=prefix,
        filters=filters,
        asset_stamp=asset_stamp,
    )
