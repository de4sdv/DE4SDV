/* DE4SDV diagram layout editor.
 * Client side of the layout sidecar workflow: lets a maintainer move and
 * resize the elements of an inlined committed SysIDE diagram and save the
 * result as a reviewable layout sidecar (never touching the model or the
 * committed SVG).
 *
 * The drag preview mutates the inlined SVG in the DOM only; after save the
 * page reloads with the server-applied sidecar (authoritative). The JS
 * geometry mirrors tools/sysml_html_viewer/layout_apply.py.
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
    this.svgOps = [];       /* [{op}] (max 1) */
    this.text = [];         /* [{find, op}] */
    this.boxes = [];
    this.connectors = [];
    this.undoStack = [];
    this.dirty = false;
  }

  EditorState.prototype.layout = function () {
    var ops = [];
    var self = this;
    this.svgOps.forEach(function (s) { ops.push({ kind: 'svg', op: s.op }); });
    ['text', 'boxes', 'connectors'].forEach(function (k) {
      self[k].forEach(function (s) { ops.push({ kind: k, find: s.find, op: s.op }); });
    });
    return { ops: ops };
  };

  EditorState.prototype.opCount = function () {
    return this.svgOps.length + this.text.length + this.boxes.length +
      this.connectors.length;
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
      'by an edge to resize (their labels and separators follow). Drag lines to move them whole. ' +
      'Drag the canvas to pan, Ctrl+wheel to zoom. Ctrl/Cmd+Z undo.</div>';
    frame.insertBefore(ed, frame.firstChild);

    var statusEl = ed.querySelector('.layout-editor-status');
    var undoBtn = ed.querySelector('.le-undo');
    var snapBox = ed.querySelector('.le-snap');
    frame.classList.add('layout-editing');

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

    /* ---------------- live SVG mutation (preview; server reapplies) ------ */

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

    /* move companions (labels/separators/port glyphs) of a box from its
     * current geometry `oldR` into `newR` — mirrors _move_companions in
     * layout_apply.py. Labels/glyphs keep their relative position. */
    function liveCompanions(oldR, newR) {
      var sx = oldR[2] !== oldR[0] ? (newR[2] - newR[0]) / (oldR[2] - oldR[0]) : 1;
      var sy = oldR[3] !== oldR[1] ? (newR[3] - newR[1]) / (oldR[3] - oldR[1]) : 1;
      function inBox(x, y) {
        return x >= oldR[0] && x <= oldR[2] && y >= oldR[1] && y <= oldR[3];
      }
      function mapPt(x, y) {
        return [newR[0] + (x - oldR[0]) * sx, newR[1] + (y - oldR[1]) * sy];
      }
      /* separators + any other polylines fully inside the old box */
      Array.prototype.forEach.call(svg.querySelectorAll('polyline'), function (pl) {
        var raw = pl.getAttribute('points') || '';
        var pts = parsePoints(raw);
        if (!pts.length) return;
        if (pts.every(function (q) { return inBox(q[0], q[1]); })) {
          pl.setAttribute('points', ptsAttr(pts.map(function (q) { return mapPt(q[0], q[1]); })));
        }
      });
      /* port glyphs + nested white sub-paths fully inside */
      Array.prototype.forEach.call(svg.querySelectorAll('path'), function (pth) {
        if (pth.getAttribute('fill') !== '#FFFFFF') return;
        if (pth === this) return;
        var d = pth.getAttribute('d') || '';
        var pts = pathPoints(d);
        if (!pts || !pts.length) return;
        if (pts.every(function (q) { return inBox(q[0], q[1]); })) {
          pth.setAttribute('d', rebuildPath(d, mapPt));
        }
      }, null);
      /* labels whose anchor sits inside */
      Array.prototype.forEach.call(svg.querySelectorAll('text'), function (t) {
        var x = parseFloat(t.getAttribute('x'));
        var y = parseFloat(t.getAttribute('y'));
        if (!inBox(x, y)) return;
        var np = mapPt(x, y);
        liveTextNode(t, np[0], np[1]);
      });
    }

    /* ---------------- op recording (undo captures the live node) --------- */

    function pushUndo(kind, find, prev, node) {
      state.undoStack.push({ kind: kind, find: find, prev: prev, node: node });
      if (state.undoStack.length > 200) state.undoStack.shift();
    }

    function recordText(node, key, nx, ny, prevOp) {
      pushUndo('text', key, prevOp, node);
      state.text = state.text.filter(function (s) { return s.find !== key; });
      state.text.push({ find: key, op: { x: nx, y: ny } });
      state.dirty = true;
      refreshButtons();
    }

    function recordBox(node, key, to, prevOp) {
      pushUndo('boxes', key, prevOp, node);
      state.boxes = state.boxes.filter(function (s) { return s.find !== key; });
      state.boxes.push({
        find: key, op: { x1: to[0], y1: to[1], x2: to[2], y2: to[3] }
      });
      state.dirty = true;
      refreshButtons();
    }

    function recordConnector(node, key, pts, prevOp) {
      pushUndo('connectors', key, prevOp, node);
      state.connectors = state.connectors.filter(function (s) { return s.find !== key; });
      state.connectors.push({ find: key, op: { points: pts } });
      state.dirty = true;
      refreshButtons();
    }

    /* ---------------- drag handling -------------------------------------- */

    function dragEnd(mv) {
      function up() {
        document.removeEventListener('mousemove', mv);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', mv);
      document.addEventListener('mouseup', up);
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
        var p = svgPoint(e);
        var nx = snap(orig[0] + (p[0] - start[0]));
        var ny = snap(orig[1] + (p[1] - start[1]));
        liveTextNode(t, nx, ny);
        recordText(t, key, nx, ny, prevOp);
      }
      dragEnd(mv);
    });

    /* boxes: body = move, edges = resize; companions follow */
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
      /* edge hit: NEAR the edge line (both sides) AND inside the perpendicular
       * extent — a click far away never grabs an edge */
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
        /* live preview: move the box node + companions from orig to n */
        p.setAttribute('d', rounded ? buildRoundedBox(n[0], n[1], n[2], n[3], 6) : rectPathD(n));
        liveCompanions(orig, n);
        recordBox(p, key, n, prevOp);
      }
      dragEnd(mv);
    });

    /* connectors (polylines): move whole route */
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
      function mv(e) {
        var q = svgPoint(e);
        var dx = q[0] - start[0], dy = q[1] - start[1];
        var n = orig.map(function (pt) { return [snap(pt[0] + dx), snap(pt[1] + dy)]; });
        p.setAttribute('points', ptsAttr(n));
        recordConnector(p, key, n, prevOp);
      }
      dragEnd(mv);
    });

    /* pan + zoom on the empty canvas */
    scroller.addEventListener('mousedown', function (ev) {
      if (ev.button !== 0) return;
      /* only when the click did NOT hit an editable element */
      if (ev.target.closest && (ev.target.closest('text') ||
          (ev.target.closest('path') && ev.target.closest('path').getAttribute('fill') === '#FFFFFF') ||
          ev.target.closest('polyline'))) return;
      var sx = ev.clientX, sy = ev.clientY, px = panX, py = panY;
      function mv(e) {
        panX = px + (e.clientX - sx);
        panY = py + (e.clientY - sy);
        applyView();
      }
      function up() {
        document.removeEventListener('mousemove', mv);
        document.removeEventListener('mouseup', up);
      }
      document.addEventListener('mousemove', mv);
      document.addEventListener('mouseup', up);
    });
    scroller.addEventListener('wheel', function (ev) {
      if (!ev.ctrlKey && !ev.metaKey) return;
      ev.preventDefault();
      var factor = ev.deltaY < 0 ? 1.1 : 1 / 1.1;
      var sr = svg.getBoundingClientRect();
      var mx = ev.clientX - sr.left, my = ev.clientY - sr.top;
      panX = mx - (mx - panX) * factor;
      panY = my - (my - panY) * factor;
      zoom = Math.max(0.2, Math.min(5, zoom * factor));
      applyView();
    }, { passive: false });

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
        var from = state.curBox(last.find);   /* where companions sit now */
        state.boxes = state.boxes.filter(function (s) { return s.find !== last.find; });
        if (last.prev) state.boxes.push({ find: last.find, op: last.prev });
        var to = state.curBox(last.find);     /* restored geometry */
        if (from && to && last.node) {
          if (from[0] !== to[0] || from[1] !== to[1] || from[2] !== to[2] || from[3] !== to[3]) {
            liveCompanions(from, to);
            var rounded = /A\s/.test(last.node.getAttribute('d') || '');
            last.node.setAttribute('d', rounded
              ? buildRoundedBox(to[0], to[1], to[2], to[3], 6)
              : rectPathD(to));
          }
        }
      } else if (last.kind === 'connectors') {
        state.connectors = state.connectors.filter(function (s) { return s.find !== last.find; });
        var pts = last.prev ? last.prev.points : meta.orig.connectors[last.find];
        if (last.prev) state.connectors.push({ find: last.find, op: last.prev });
        if (pts && last.node) last.node.setAttribute('points', ptsAttr(pts));
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
