/* DE4SDV diagram layout editor.
 * Client side of the layout sidecar workflow: lets a maintainer move and
 * resize the elements of an inlined committed SysIDE diagram and save the
 * result as a reviewable layout sidecar (never touching the model or the
 * committed SVG).
 *
 * The drag preview mutates the inlined SVG in the DOM only; the SAVE sends
 * every moved element as its own explicit op (boxes, labels, separators,
 * port glyphs, connector re-routes with stretched endpoints, arrowheads) —
 * the server's applier is the single source of truth and replays exactly
 * those ops on the committed SVG. Nothing is inferred at apply time, so a
 * saved layout can never visually detach a relationship from its element.
 *
 * While the editor is open, the viewer's hover/click enrichment is
 * suppressed inside this diagram (capture-phase listener) — clicks never
 * jump to the source view in edit mode.
 *
 * Activates only on pages served by the local editor server
 * (window.__DE4SDV_EDITOR__ + .diagram-layout payloads). Vanilla JS. */
(function () {
  'use strict';

  function fmtNum(v) {
    if (Math.abs(v - Math.round(v)) < 1e-9) return String(Math.round(v));
    return String(Math.round(v * 100) / 100);
  }

  function textKey(x, y) { return fmtNum(x) + ',' + fmtNum(y); }
  function boxKey(x1, y1, x2, y2) {
    return textKey(x1, y1) + ',' + textKey(x2, y2);
  }
  function ptsKey(pts) {
    return pts.map(function (p) { return fmtNum(p[0]) + ',' + fmtNum(p[1]); }).join(' ');
  }

  /* --- SVG geometry (mirrors layout_apply.py) ---------------------------- */

  function buildRoundedBox(x1, y1, x2, y2, r) {
    var f = fmtNum;
    return 'M ' + f(x1 + r) + ',' + f(y1) + ' H ' + f(x2 - r) +
      ' A ' + f(r) + ',' + f(r) + ' 0 0 1 ' + f(x2) + ',' + f(y1 + r) +
      ' V ' + f(y2 - r) +
      ' A ' + f(r) + ',' + f(r) + ' 0 0 1 ' + f(x2 - r) + ',' + f(y2) +
      ' H ' + f(x1 + r) +
      ' A ' + f(r) + ',' + f(r) + ' 0 0 1 ' + f(x1) + ',' + f(y2 - r) +
      ' V ' + f(y1 + r) +
      ' A ' + f(r) + ',' + f(r) + ' 0 0 1 ' + f(x1 + r) + ',' + f(y1) + ' Z';
  }

  function rectPathD(n) {
    return 'M ' + fmtNum(n[0]) + ',' + fmtNum(n[1]) + ' H ' + fmtNum(n[2]) +
      ' V ' + fmtNum(n[3]) + ' H ' + fmtNum(n[0]) + ' V ' + fmtNum(n[1]) + ' Z';
  }

  function pathPoints(d) {
    /* M/H/V/A/Z absolute-only parser; null when unsupported commands appear */
    var pts = [], cur = [0, 0], re = /([A-Z])\s*((?:-?[\d.]+[\s,]*)*)/g, m;
    while ((m = re.exec(d)) !== null) {
      var cmd = m[1];
      if ('MHVAZ'.indexOf(cmd) === -1) return null;
      var nums = (m[2].match(/-?[\d.]+/g) || []).map(parseFloat);
      if (cmd === 'M' && nums.length >= 2) { cur = [nums[0], nums[1]]; pts.push(cur); }
      else if (cmd === 'H' && nums.length) { cur = [nums[0], cur[1]]; pts.push(cur); }
      else if (cmd === 'V' && nums.length) { cur = [cur[0], nums[0]]; pts.push(cur); }
      else if (cmd === 'A') {
        if (nums.length % 7) return null;
        for (var i = 0; i < nums.length; i += 7) {
          cur = [nums[i + 5], nums[i + 6]]; pts.push(cur);
        }
      }
    }
    return pts;
  }

  function pathBBox(d) {
    var pts = pathPoints(d);
    if (!pts || pts.length < 2) return null;
    var xs = pts.map(function (q) { return q[0]; });
    var ys = pts.map(function (q) { return q[1]; });
    return [Math.min.apply(null, xs), Math.min.apply(null, ys),
            Math.max.apply(null, xs), Math.max.apply(null, ys)];
  }

  function parsePoints(raw) {
    var c = raw.trim().split(/[,\s]+/).filter(Boolean).map(parseFloat);
    var out = [];
    for (var i = 0; i + 1 < c.length; i += 2) out.push([c[i], c[i + 1]]);
    return out;
  }

  function ptsAttr(pts) {
    return pts.map(function (p) { return fmtNum(p[0]) + ',' + fmtNum(p[1]); }).join(' ');
  }

  function rebuildPath(d, mapPt) {
    var out = [], cur = [0, 0];
    var re = /([A-Z])\s*((?:-?[\d.]+[\s,]*)*)/g, m;
    while ((m = re.exec(d)) !== null) {
      var cmd = m[1];
      var nums = (m[2].match(/-?[\d.]+/g) || []).map(parseFloat);
      if (cmd === 'Z') { out.push('Z'); continue; }
      if (cmd === 'M' && nums.length >= 2) {
        var p = mapPt(nums[0], nums[1]); cur = p;
        out.push('M ' + fmtNum(p[0]) + ',' + fmtNum(p[1]));
      } else if (cmd === 'H' && nums.length) {
        var q = mapPt(nums[0], cur[1]); cur = q;
        out.push('H ' + fmtNum(q[0]));
      } else if (cmd === 'V' && nums.length) {
        var r2 = mapPt(cur[0], nums[0]); cur = r2;
        out.push('V ' + fmtNum(r2[1]));
      } else if (cmd === 'A' && nums.length % 7 === 0) {
        for (var i = 0; i < nums.length; i += 7) {
          var a = mapPt(nums[i + 5], nums[i + 6]); cur = a;
          out.push('A ' + fmtNum(nums[i]) + ',' + fmtNum(nums[i + 1]) +
            ' 0 ' + Math.round(nums[i + 3]) + ' ' + Math.round(nums[i + 4]) +
            ' ' + fmtNum(a[0]) + ',' + fmtNum(a[1]));
        }
      } else return d;
    }
    return out.join(' ');
  }

  /* ------------------------------------------------------------------ state */

  function EditorState(meta) {
    this.meta = meta;
    this.text = [];        /* [{find, op}] */
    this.boxes = [];
    this.connectors = [];
    this.arrows = [];
    this.undoStack = [];
    this.dirty = false;
  }

  EditorState.prototype.layout = function () {
    var ops = [];
    var self = this;
    ['text', 'boxes', 'connectors', 'arrows'].forEach(function (k) {
      self[k].forEach(function (s) { ops.push({ kind: k, find: s.find, op: s.op }); });
    });
    return { ops: ops };
  };

  EditorState.prototype.opCount = function () {
    return this.text.length + this.boxes.length + this.connectors.length +
      this.arrows.length;
  };

  /* current geometry of an element (committed + working ops) */
  EditorState.prototype.curText = function (key) {
    var found = null;
    this.text.forEach(function (s) { if (s.find === key) found = s.op; });
    if (found) return [found.x, found.y];
    var o = this.meta.orig.text[key];
    return o ? [o[0], o[1]] : null;
  };

  EditorState.prototype.curBox = function (key) {
    var found = null;
    this.boxes.forEach(function (s) { if (s.find === key) found = s.op; });
    if (found) return [found.x1, found.y1, found.x2, found.y2];
    var o = this.meta.orig.boxes[key];
    return o ? o.slice() : null;
  };

  EditorState.prototype.curConnector = function (key) {
    var found = null;
    this.connectors.forEach(function (s) { if (s.find === key) found = s.op.points; });
    if (found) return found;
    var o = this.meta.orig.connectors[key];
    return o ? o.map(function (p) { return p.slice(); }) : null;
  };

  /* current geometry of EVERY box: stable find key -> [x1,y1,x2,y2] */
  EditorState.prototype.curBoxMap = function () {
    var out = {}, self = this;
    Object.keys(this.meta.orig.boxes).forEach(function (k) {
      var g = self.curBox(k);
      if (g) out[k] = g;
    });
    return out;
  };

  /* --- stable identity: the geometry an element had when it was FIRST
   * edited is its find key forever. A mousedown sees the element's CURRENT
   * geometry; resolve it back to the stable find key. ------------------- */
  EditorState.prototype.resolveTextKey = function (curKey) {
    if (this.meta.orig.text[curKey]) return curKey;
    for (var i = 0; i < this.text.length; i++) {
      if (textKey(this.text[i].op.x, this.text[i].op.y) === curKey) {
        return this.text[i].find;
      }
    }
    return null;
  };

  EditorState.prototype.resolveBoxKey = function (curKey) {
    if (this.meta.orig.boxes[curKey]) return curKey;
    for (var i = 0; i < this.boxes.length; i++) {
      var o = this.boxes[i].op;
      if (boxKey(o.x1, o.y1, o.x2, o.y2) === curKey) return this.boxes[i].find;
    }
    return null;
  };

  EditorState.prototype.resolveConnectorKey = function (curKey) {
    if (this.meta.orig.connectors[curKey]) return curKey;
    for (var i = 0; i < this.connectors.length; i++) {
      if (ptsKey(this.connectors[i].op.points) === curKey) {
        return this.connectors[i].find;
      }
    }
    return null;
  };

  EditorState.prototype.resolveArrowKey = function (curKey) {
    if (this.meta.orig.arrows[curKey]) return curKey;
    for (var i = 0; i < this.arrows.length; i++) {
      if (textKey(this.arrows[i].op.x, this.arrows[i].op.y) === curKey) {
        return this.arrows[i].find;
      }
    }
    return null;
  };

  /* ------------------------------------------------------------------ boot */

  function initEditor() {
    if (!window.__DE4SDV_EDITOR__) return;
    var scripts = document.querySelectorAll('script.diagram-layout');
    Array.prototype.forEach.call(scripts, function (sc) {
      var viewName = sc.getAttribute('data-for');
      var section = document.getElementById('view-' + viewName);
      if (!section) return;
      var frame = section.querySelector('.diagram-frame.interactive');
      if (!frame) return;
      var meta;
      try { meta = JSON.parse(sc.textContent); } catch (e) { return; }
      var btn = section.querySelector('.diagram-edit-btn');
      if (!btn) return;
      btn.hidden = false;
      btn.addEventListener('click', function () { openEditor(frame, meta); });
    });
  }

  /* ---------------------------------------------------------------- editor */

  function openEditor(frame, meta) {
    if (frame.__layoutEditor) return;
    var svg = frame.querySelector('svg');
    var scroller = frame.querySelector('.diagram-scroll');
    if (!svg || !scroller) return;

    var state = new EditorState(meta);
    var zoom = 1, panX = 0, panY = 0;

    /* editor chrome */
    var ed = document.createElement('div');
    ed.className = 'layout-editor';
    ed.innerHTML =
      '<div class="layout-editor-bar">' +
      '<span class="layout-editor-title">Layout editor</span>' +
      '<label class="layout-editor-ctl"><input type="checkbox" class="le-snap" checked>snap</label>' +
      '<span class="layout-editor-status"></span>' +
      '<span class="layout-editor-flex"></span>' +
      '<button type="button" class="le-btn le-undo" disabled>Undo</button>' +
      '<button type="button" class="le-btn le-reset" title="Delete the saved layout sidecar">Reset saved</button>' +
      '<button type="button" class="le-btn le-cancel">Close</button>' +
      '<button type="button" class="le-btn le-save le-primary">Save layout</button>' +
      '</div>' +
      '<div class="layout-editor-hint">Drag labels to move them. Drag boxes by the body to move, ' +
      'by an edge to resize \u2014 their labels, separators, ports and attached connector ' +
      'ends follow. Drag a line to move it whole (endpoints stay glued to their boxes). ' +
      'Drag the canvas to pan, Ctrl+wheel to zoom. Ctrl/Cmd+Z undo.</div>';
    frame.insertBefore(ed, frame.firstChild);

    var statusEl = ed.querySelector('.layout-editor-status');
    var undoBtn = ed.querySelector('.le-undo');
    var snapBox = ed.querySelector('.le-snap');
    frame.classList.add('layout-editing');

    /* suppress the viewer's own hover/click enrichment inside this diagram
     * while editing: stop click/hover in the capture phase before it
     * reaches the viewer's element-level handlers (tooltips + source jumps
     * are dead in edit mode). mousemove is NOT suppressed: the tooltip
     * never shows anyway (its mouseover is stopped) and the editor's own
     * document-level drag handlers must keep receiving it. */
    function swallow(ev) {
      ev.stopPropagation();
      ev.preventDefault();
    }
    var suppressed = ['click', 'mouseover', 'mouseout', 'contextmenu'];
    suppressed.forEach(function (t) {
      svg.addEventListener(t, swallow, true);
    });

    /* neutralize the responsive downscale so screen px == user units at zoom 1 */
    var canvas = meta.canvas && meta.canvas.cur ? meta.canvas.cur : null;
    var unitW = canvas ? canvas[0] : parseFloat(svg.getAttribute('width')) || 800;
    var unitH = canvas ? canvas[1] : parseFloat(svg.getAttribute('height')) || 600;
    svg.style.maxWidth = 'none';
    svg.style.width = unitW + 'px';
    svg.style.height = unitH + 'px';
    svg.style.transformOrigin = '0 0';

    function applyView() {
      svg.style.transform = 'translate(' + panX + 'px,' + panY + 'px) scale(' + zoom + ')';
    }

    function svgPoint(ev) {
      var r = svg.getBoundingClientRect();
      return [(ev.clientX - r.left) / zoom, (ev.clientY - r.top) / zoom];
    }

    function setStatus(t) { statusEl.textContent = t; }

    function refreshButtons() {
      undoBtn.disabled = !state.undoStack.length;
      var n = state.opCount();
      statusEl.textContent = n
        ? n + ' layout change' + (n === 1 ? '' : 's') + ' (unsaved)'
        : '';
    }

    function snap(v) {
      return snapBox.checked ? Math.round(v / 2) * 2 : Math.round(v * 100) / 100;
    }

    /* ---------------- live SVG mutation (preview; server replays ops) ---- */

    function liveTextNode(t, nx, ny) {
      var x0 = parseFloat(t.getAttribute('x'));
      var y0 = parseFloat(t.getAttribute('y'));
      t.setAttribute('x', fmtNum(nx));
      t.setAttribute('y', fmtNum(ny));
      var dx = nx - x0, dy = ny - y0;
      Array.prototype.forEach.call(t.querySelectorAll('tspan'), function (ts) {
        if (ts.getAttribute('x') !== null) {
          ts.setAttribute('x', fmtNum(parseFloat(ts.getAttribute('x')) + dx));
        }
        if (ts.getAttribute('y') !== null) {
          ts.setAttribute('y', fmtNum(parseFloat(ts.getAttribute('y')) + dy));
        }
      });
    }

    function livePolyline(pl, pts) {
      pl.setAttribute('points', ptsAttr(pts));
    }

    function livePath(pth, d) {
      pth.setAttribute('d', d);
    }

    /* arrowheads: <g transform="translate(x,y) rotate…"> groups */
    function liveArrow(g, nx, ny) {
      var m = g.getAttribute('transform') || '';
      var cur = /translate\((-?[\d.]+),(-?[\d.]+)\)/.exec(m);
      if (!cur) return;
      g.setAttribute('transform', m.replace(
        'translate(' + cur[1] + ',' + cur[2] + ')',
        'translate(' + fmtNum(nx) + ',' + fmtNum(ny) + ')'
      ));
    }

    /* ---------------- op recording (undo captures the live node) --------- */

    function pushUndo(kind, find, prev, node) {
      state.undoStack.push({ kind: kind, find: find, prev: prev, node: node });
      if (state.undoStack.length > 200) state.undoStack.shift();
    }

    function record(kind, node, key, op, prevOp) {
      pushUndo(kind, key, prevOp, node);
      var list = state[kind];
      for (var i = 0; i < list.length; i++) {
        if (list[i].find === key) { list.splice(i, 1); break; }
      }
      list.push({ find: key, op: op });
      state.dirty = true;
      refreshButtons();
    }

    /* ---------------- geometric helpers ---------------------------------- */

    function rectContains(r, x, y, pad) {
      pad = pad || 0;
      return x >= r[0] - pad && x <= r[2] + pad && y >= r[1] - pad && y <= r[3] + pad;
    }

    function bboxOf(pts) {
      var xs = pts.map(function (q) { return q[0]; });
      var ys = pts.map(function (q) { return q[1]; });
      return [Math.min.apply(null, xs), Math.min.apply(null, ys),
              Math.max.apply(null, xs), Math.max.apply(null, ys)];
    }

    /* ---- companion snapshot + apply (box drags) --------------------------
     * Companions are captured ONCE at drag start (positions as they are at
     * that moment) and every frame maps THOSE positions into the new box
     * geometry — never the live DOM (which would compound each frame).
     *
     * Attachment rule (matches SysIDE rendering): a connector endpoint
     * stretches with the boundary when the endpoint itself sits on it OR
     * when an arrowhead that sits on the boundary is within GAP_TOL of the
     * endpoint (SysIDE draws the glyph on the edge and the line a few px
     * short). Arrowheads keep rotate/scale; endpoints keep their gap. */
    var GAP_TOL = 24;

    function collectCompanions(from) {
      function onBoundary(x, y) {
        return rectContains(from, x, y, 0.5);
      }
      /* arrows that will move (inside / on the old boundary) */
      var arrows = [];
      Array.prototype.forEach.call(svg.querySelectorAll('g'), function (g) {
        if (!g.getAttribute || !g.getAttribute('transform')) return;
        var mm = /translate\((-?[\d.]+),(-?[\d.]+)\)/.exec(g.getAttribute('transform'));
        if (!mm || g.getAttribute('fill') !== '#1A1A1A') return;
        var ax = parseFloat(mm[1]), ay = parseFloat(mm[2]);
        if (!onBoundary(ax, ay)) return;
        var key = state.resolveArrowKey(textKey(ax, ay));
        if (!key) return;
        arrows.push({
          node: g, key: key, start: [ax, ay],
          prevOp: (state.arrows.filter(function (s) { return s.find === key; })[0] || {}).op || null
        });
      });
      var items = [];
      /* labels anchored inside the old box */
      Array.prototype.forEach.call(svg.querySelectorAll('text'), function (t) {
        var x = parseFloat(t.getAttribute('x'));
        var y = parseFloat(t.getAttribute('y'));
        if (!onBoundary(x, y)) return;
        var key = state.resolveTextKey(textKey(x, y));
        if (!key) return;
        items.push({
          kind: 'text', node: t, key: key, start: [x, y],
          prevOp: (state.text.filter(function (s) { return s.find === key; })[0] || {}).op || null
        });
      });
      /* polylines: fully inside move; an endpoint near the boundary or near
       * a moving arrowhead stretches */
      Array.prototype.forEach.call(svg.querySelectorAll('polyline'), function (pl) {
        var raw = pl.getAttribute('points') || '';
        var pts = parsePoints(raw);
        if (!pts.length) return;
        var key = state.resolveConnectorKey(raw);
        if (!key) return;
        var anyMoves = pts.some(function (q) {
          return onBoundary(q[0], q[1]) ||
            arrows.some(function (a) {
              return Math.hypot(a.start[0] - q[0], a.start[1] - q[1]) < GAP_TOL;
            });
        });
        if (!anyMoves) return;
        items.push({
          kind: 'connectors', node: pl, key: key, start: pts,
          prevOp: (state.connectors.filter(function (s) { return s.find === key; })[0] || {}).op || null
        });
      });
      /* port glyphs (white sub-paths) fully inside */
      Array.prototype.forEach.call(svg.querySelectorAll('path'), function (pth) {
        if (pth.getAttribute('fill') !== '#FFFFFF') return;
        var d = pth.getAttribute('d') || '';
        var pts = pathPoints(d);
        if (!pts || !pts.length) return;
        if (!pts.every(function (q) { return onBoundary(q[0], q[1]); })) return;
        var key = state.resolveBoxKey(boxKey.apply(null, bboxOf(pts)));
        if (!key) return;
        items.push({
          kind: 'boxes', node: pth, key: key, start: d,
          prevOp: (state.boxes.filter(function (s) { return s.find === key; })[0] || {}).op || null
        });
      });
      arrows.forEach(function (a) {
        items.push({ kind: 'arrows', node: a.node, key: a.key, start: a.start, prevOp: a.prevOp });
      });
      return items;
    }

    /* map snapshot companions from the start box geometry into the new one */
    function applyCompanions(items, from, to) {
      var sx = from[2] !== from[0] ? (to[2] - to[0]) / (from[2] - from[0]) : 1;
      var sy = from[3] !== from[1] ? (to[3] - to[1]) / (from[3] - from[1]) : 1;
      function mapPt(x, y) {
        return [to[0] + (x - from[0]) * sx, to[1] + (y - from[1]) * sy];
      }
      function onBoundary(x, y) {
        return rectContains(from, x, y, 0.5);
      }
      var movingArrows = items.filter(function (it) { return it.kind === 'arrows'; });
      items.forEach(function (it) {
        if (it.kind === 'text') {
          var np = mapPt(it.start[0], it.start[1]);
          liveTextNode(it.node, np[0], np[1]);
          record('text', it.node, it.key, { x: np[0], y: np[1] }, it.prevOp);
        } else if (it.kind === 'connectors') {
          var npts = it.start.map(function (q) {
            if (onBoundary(q[0], q[1]) ||
                movingArrows.some(function (a) {
                  return Math.hypot(a.start[0] - q[0], a.start[1] - q[1]) < GAP_TOL;
                })) {
              return mapPt(q[0], q[1]);
            }
            return q;
          });
          livePolyline(it.node, npts);
          record('connectors', it.node, it.key, { points: npts }, it.prevOp);
        } else if (it.kind === 'boxes') {
          var nd = rebuildPath(it.start, mapPt);
          var npts2 = pathPoints(nd);
          var bb = bboxOf(npts2);
          livePath(it.node, nd);
          record('boxes', it.node, it.key, {
            x1: bb[0], y1: bb[1], x2: bb[2], y2: bb[3]
          }, it.prevOp);
        } else if (it.kind === 'arrows') {
          var na = mapPt(it.start[0], it.start[1]);
          liveArrow(it.node, na[0], na[1]);
          record('arrows', it.node, it.key, { x: na[0], y: na[1] }, it.prevOp);
        }
      });
    }

    /* ---- connector drag: arrowheads glued to the ends --------------------
     * At mousedown, attach the arrowhead glyph nearest each end (within
     * GAP_TOL; SysIDE offsets it a few px). Per frame each attached arrow
     * translates by the SAME delta its end moved, preserving the gap. */
    function attachArrows(orig) {
      var out = [];
      Array.prototype.forEach.call(svg.querySelectorAll('g'), function (g) {
        if (!g.getAttribute || !g.getAttribute('transform')) return;
        var mm = /translate\((-?[\d.]+),(-?[\d.]+)\)/.exec(g.getAttribute('transform'));
        if (!mm || g.getAttribute('fill') !== '#1A1A1A') return;
        var ax = parseFloat(mm[1]), ay = parseFloat(mm[2]);
        var near = null;
        [0, orig.length - 1].forEach(function (idx) {
          var end = orig[idx];
          var d = Math.hypot(ax - end[0], ay - end[1]);
          if (d < GAP_TOL && (!near || d < near.d)) near = { d: d, endIdx: idx };
        });
        if (!near) return;
        var key = state.resolveArrowKey(textKey(ax, ay));
        if (!key) return;
        out.push({
          node: g, key: key, start: [ax, ay], endIdx: near.endIdx,
          prevOp: (state.arrows.filter(function (s) { return s.find === key; })[0] || {}).op || null
        });
      });
      return out;
    }

    /* ---------------- drag dispatch -------------------------------------- */

    function bboxOf(pts) {
      var xs = pts.map(function (q) { return q[0]; });
      var ys = pts.map(function (q) { return q[1]; });
      return [Math.min.apply(null, xs), Math.min.apply(null, ys),
              Math.max.apply(null, xs), Math.max.apply(null, ys)];
    }

    /* labels */
    svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      var t = ev.target.closest ? ev.target.closest('text') : null;
      if (!t) return;
      ev.preventDefault();
      var curKey = textKey(parseFloat(t.getAttribute('x')), parseFloat(t.getAttribute('y')));
      var key = state.resolveTextKey(curKey);
      if (!key) return;
      var cur = state.curText(key);
      var orig = cur.slice();
      var start = svgPoint(ev);
      var selfState = state.text.filter(function (s) { return s.find === key; })[0];
      var prevOp = selfState ? selfState.op : null;
      function mv(e) {
        var q = svgPoint(e);
        var nx = snap(orig[0] + (q[0] - start[0]));
        var ny = snap(orig[1] + (q[1] - start[1]));
        liveTextNode(t, nx, ny);
        record('text', t, key, { x: nx, y: ny }, prevOp);
      }
      dragEnd(mv);
    });

    /* boxes: body = move, edges = resize; companions + endpoints follow */
    svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      var p = ev.target.closest ? ev.target.closest('path') : null;
      if (!p || p.getAttribute('fill') !== '#FFFFFF') return;
      ev.preventDefault();
      var d = p.getAttribute('d') || '';
      var bb = pathBBox(d);
      if (!bb) return;
      var curKey = boxKey(bb[0], bb[1], bb[2], bb[3]);
      var key = state.resolveBoxKey(curKey);
      if (!key) return;
      var cur = state.curBox(key);
      var rounded = /A\s/.test(d);
      var sr = svg.getBoundingClientRect();
      var mx = ev.clientX - sr.left, my = ev.clientY - sr.top;
      var m = 8;
      var nearL = Math.abs(mx - cur[0] * zoom) < m && my > cur[1] * zoom - m && my < cur[3] * zoom + m;
      var nearR = Math.abs(mx - cur[2] * zoom) < m && my > cur[1] * zoom - m && my < cur[3] * zoom + m;
      var nearT = Math.abs(my - cur[1] * zoom) < m && mx > cur[0] * zoom - m && mx < cur[2] * zoom + m;
      var nearB = Math.abs(my - cur[3] * zoom) < m && mx > cur[0] * zoom - m && mx < cur[2] * zoom + m;
      var edge = { w: nearL, e: nearR, n: nearT, s: nearB };
      var isMove = !edge.n && !edge.s && !edge.w && !edge.e;
      /* tiny boxes (port glyphs) are never resize targets */
      if (cur[2] - cur[0] < 40 && cur[3] - cur[1] < 40) isMove = true;
      var start = svgPoint(ev);
      var orig = cur.slice();
      var selfState = state.boxes.filter(function (s) { return s.find === key; })[0];
      var prevOp = selfState ? selfState.op : null;
      /* companions captured ONCE: labels/separators/glyphs inside, connector
       * ends on (or near, via arrowheads) the boundary */
      var companions = collectCompanions(orig);
      function mv(e) {
        var q = svgPoint(e);
        var dx = q[0] - start[0], dy = q[1] - start[1];
        var n = orig.slice();
        if (isMove) {
          n[0] = orig[0] + dx; n[2] = orig[2] + dx;
          n[1] = orig[1] + dy; n[3] = orig[3] + dy;
        } else {
          if (edge.e) n[2] = orig[2] + dx;
          if (edge.w) n[0] = orig[0] + dx;
          if (edge.s) n[3] = orig[3] + dy;
          if (edge.n) n[1] = orig[1] + dy;
          if (n[2] - n[0] < 20) { if (edge.e) n[2] = n[0] + 20; else n[0] = n[2] - 20; }
          if (n[3] - n[1] < 12) { if (edge.s) n[3] = n[1] + 12; else n[1] = n[3] - 12; }
        }
        n = [snap(n[0]), snap(n[1]), snap(n[2]), snap(n[3])];
        livePath(p, rounded ? buildRoundedBox(n[0], n[1], n[2], n[3], 6) : rectPathD(n));
        record('boxes', p, key, { x1: n[0], y1: n[1], x2: n[2], y2: n[3] }, prevOp);
        applyCompanions(companions, orig, n);
      }
      function up() {
        document.removeEventListener('mousemove', mv);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', mv);
      document.addEventListener('mouseup', up);
    });

    /* connectors: move whole route, endpoints glued, arrows follow */
    svg.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      var p = ev.target.closest ? ev.target.closest('polyline') : null;
      if (!p) return;
      ev.preventDefault();
      var curKey = p.getAttribute('points') || '';
      var key = state.resolveConnectorKey(curKey);
      if (!key) return;
      var cur = state.curConnector(key);
      var start = svgPoint(ev);
      var orig = cur.map(function (q) { return q.slice(); });
      var selfState = state.connectors.filter(function (s) { return s.find === key; })[0];
      var prevOp = selfState ? selfState.op : null;

      /* arrowheads attached at mousedown: each glyph nearest an end (within
       * GAP_TOL) moves with that end, preserving the SysIDE gap */
      var i_end = { 0: 0, 1: orig.length - 1 };
      var dragArrows = attachArrows(orig);

      function mv(e) {
        var q = svgPoint(e);
        var dx = q[0] - start[0], dy = q[1] - start[1];
        var n = orig.map(function (pt) { return [snap(pt[0] + dx), snap(pt[1] + dy)]; });
        p.setAttribute('points', ptsAttr(n));
        record('connectors', p, key, { points: n }, prevOp);
        /* arrowheads attached at mousedown follow their end, keeping the
         * SysIDE gap (same delta as the end itself) */
        dragArrows.forEach(function (a) {
          var ei = i_end[a.endIdx];
          var na = [a.start[0] + (n[ei][0] - orig[ei][0]),
                    a.start[1] + (n[ei][1] - orig[ei][1])];
          liveArrow(a.node, na[0], na[1]);
          record('arrows', a.node, a.key, { x: na[0], y: na[1] }, a.prevOp);
        });
      }
      function up() {
        document.removeEventListener('mousemove', mv);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', mv);
      document.addEventListener('mouseup', up);
    });

    /* ---------------- undo ------------------------------------------------ */

    function undo() {
      var last = state.undoStack.pop();
      if (!last) return;
      if (last.kind === 'text') {
        state.text = state.text.filter(function (s) { return s.find !== last.find; });
        var target = last.prev
          ? [last.prev.x, last.prev.y]
          : (meta.orig.text[last.find] || null);
        if (last.prev) state.text.push({ find: last.find, op: last.prev });
        if (target && last.node) liveTextNode(last.node, target[0], target[1]);
      } else if (last.kind === 'boxes') {
        state.boxes = state.boxes.filter(function (s) { return s.find !== last.find; });
        if (last.prev) state.boxes.push({ find: last.find, op: last.prev });
        var to = state.curBox(last.find);
        if (to && last.node) {
          var rounded = /A\s/.test(last.node.getAttribute('d') || '');
          last.node.setAttribute('d', rounded
            ? buildRoundedBox(to[0], to[1], to[2], to[3], 6)
            : rectPathD(to));
        }
      } else if (last.kind === 'connectors') {
        state.connectors = state.connectors.filter(function (s) { return s.find !== last.find; });
        var pts = last.prev ? last.prev.points : meta.orig.connectors[last.find];
        if (last.prev) state.connectors.push({ find: last.find, op: last.prev });
        if (pts && last.node) last.node.setAttribute('points', ptsAttr(pts));
      } else if (last.kind === 'arrows') {
        state.arrows = state.arrows.filter(function (s) { return s.find !== last.find; });
        var target = last.prev
          ? [last.prev.x, last.prev.y]
          : (meta.orig.arrows[last.find] || null);
        if (last.prev) state.arrows.push({ find: last.find, op: last.prev });
        if (target && last.node) liveArrow(last.node, target[0], target[1]);
      }
      state.dirty = state.opCount() > 0;
      refreshButtons();
    }
    undoBtn.addEventListener('click', undo);
    document.addEventListener('keydown', function (ev) {
      if (!frame.classList.contains('layout-editing')) return;
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z') {
        ev.preventDefault();
        undo();
      }
    });

    /* ---------------- save / reset / close -------------------------------- */

    ed.querySelector('.le-cancel').addEventListener('click', function () {
      if (state.dirty && !confirm('Discard unsaved layout changes?')) return;
      close();
    });

    ed.querySelector('.le-reset').addEventListener('click', function () {
      if (!confirm('Delete the saved layout sidecar for this diagram?\nThe committed diagram will render unchanged.')) return;
      fetch('/diagram-layout/' + meta.svg, { method: 'DELETE' })
        .then(function () { window.location.reload(); })
        .catch(function () { setStatus('reset failed — server unreachable'); });
    });

    ed.querySelector('.le-save').addEventListener('click', function () {
      var layout = state.layout();
      if (!layout.ops.length) { setStatus('nothing to save — drag something first'); return; }
      setStatus('saving…');
      fetch('/diagram-layout/' + meta.svg, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base: meta.base, layout: layout, original: { svg: meta.svg } })
      }).then(function (r) {
        if (r.status === 409) {
          return r.json().then(function (j) {
            alert('The committed diagram changed since you loaded this page.\n' +
              (j.message || '') + '\n\nReload the page, then redo your layout changes.');
            return null;
          });
        }
        return r.json();
      }).then(function (j) {
        if (!j) return;
        if (j.ok) {
          state.dirty = false;
          window.location.reload();
        } else {
          setStatus('save failed: ' + (j.message || j.error || 'unknown error'));
        }
      }).catch(function () { setStatus('save failed — server unreachable'); });
    });

    function close() {
      suppressed.forEach(function (t) {
        svg.removeEventListener(t, swallow, true);
      });
      ed.parentNode.removeChild(ed);
      frame.classList.remove('layout-editing');
      svg.style.transform = '';
      svg.style.maxWidth = '';
      svg.style.width = '';
      svg.style.height = '';
      frame.__layoutEditor = null;
    }

    frame.__layoutEditor = true;
    refreshButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initEditor);
  } else {
    initEditor();
  }
})();
