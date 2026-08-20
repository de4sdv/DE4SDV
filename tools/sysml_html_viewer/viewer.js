/* DE4SDV model viewer — diagram hover enrichment.
 * Reads the label -> element-info JSON embedded next to each inlined
 * diagram and shows a tooltip with model knowledge (kind, doc, source,
 * viewer link) when the pointer rests on a known element label.
 * Vanilla JS, works from file:// — no dependencies. */
(function () {
  'use strict';

  function norm(s) {
    return s.replace(/\s+/g, ' ').trim();
  }

  function init() {
    measureHeader();
    // webfonts (IBM Plex) load late and change the header height; when they
    // settle, re-measure and re-scroll any hash target so it stays clear of
    // the sticky header
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(function () {
        measureHeader();
        if (location.hash) {
          var el = document.getElementById(location.hash.slice(1));
          if (el) el.scrollIntoView({ block: 'start' });
        }
      });
    }

    var tip = document.createElement('div');
    tip.className = 'viewer-tooltip';
    tip.style.display = 'none';
    document.body.appendChild(tip);

    var active = null;
    function clearActive() {
      if (active) {
        active.classList.remove('tip-hit');
        active = null;
      }
    }

    function hide() {
      tip.style.display = 'none';
      clearActive();
    }

    function move(ev) {
      if (tip.style.display === 'none') return;
      var pad = 14;
      var x = ev.clientX + pad;
      var y = ev.clientY + pad;
      var r = tip.getBoundingClientRect();
      if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - pad;
      if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - pad;
      tip.style.left = x + 'px';
      tip.style.top = y + 'px';
    }

    function show(t, info, ev) {
      clearActive();
      active = t;
      t.classList.add('tip-hit');
      tip.textContent = '';

      var badge = document.createElement('span');
      badge.className = 'tip-badge';
      badge.textContent = info.kind || 'element';
      tip.appendChild(badge);

      var name = document.createElement('span');
      name.className = 'tip-name';
      name.textContent = info.name;
      tip.appendChild(name);

      if (info.doc) {
        var doc = document.createElement('div');
        doc.className = 'tip-doc';
        doc.textContent = info.doc;
        tip.appendChild(doc);
      }
      if (info.file) {
        var src = document.createElement('div');
        src.className = 'tip-src';
        src.textContent = info.file + ':' + info.line;
        tip.appendChild(src);
      }
      if (info.href) {
        var hint = document.createElement('div');
        hint.className = 'tip-hint';
        // external SAF page links open in a new tab; in-viewer jumps stay
        if (/^https?:/i.test(info.href)) {
          var ext = document.createElement('a');
          ext.className = 'tip-link';
          ext.href = info.href;
          ext.target = '_blank';
          ext.rel = 'noopener';
          ext.textContent = info.hint || 'open SAF viewpoint page';
          hint.appendChild(ext);
        } else {
          hint.textContent = info.hint || 'click to open in viewer';
        }
        tip.appendChild(hint);
      }
      if (info.uses && info.uses.length) {
        var usesLine = document.createElement('div');
        usesLine.className = 'tip-uses';
        usesLine.textContent =
          'used in ' + info.uses.length +
          (info.uses.length === 1 ? ' diagram' : ' diagrams') +
          ' — right-click to open';
        tip.appendChild(usesLine);
      }
      tip.style.display = 'block';
      move(ev);
    }

    /* ---- source references & viewpoint tips (hover tooltip) ---- */
    /* ---- "used in diagrams": source ref -> diagram chooser ---- */
    var USES = window.USES_INDEX || {};

    function usesFor(a) {
      if (!a || !a.getAttribute) return null;
      var f = a.getAttribute('data-tip-file');
      var l = a.getAttribute('data-tip-line');
      if (!f || !l) return null;
      return USES[f + ':' + l] || null;
    }

    function initUsesMenu() {
      // visual indication: source refs that appear in diagrams
      var refs = document.querySelectorAll('a.src-ref');
      Array.prototype.forEach.call(refs, function (a) {
        if (usesFor(a)) a.classList.add('has-uses');
      });

      var menu = document.createElement('div');
      menu.className = 'uses-menu';
      menu.style.display = 'none';
      document.body.appendChild(menu);

      function closeMenu() {
        menu.style.display = 'none';
        menu.textContent = '';
      }
      document.addEventListener('click', closeMenu);
      document.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') closeMenu();
      });
      document.addEventListener('contextmenu', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest('a.src-ref') : null;
        var uses = a ? usesFor(a) : null;
        if (!uses || !uses.length) return;
        ev.preventDefault();
        closeMenu();
        var title = document.createElement('div');
        title.className = 'uses-menu-title';
        title.textContent =
          'Used in ' + uses.length + (uses.length === 1 ? ' diagram' : ' diagrams');
        menu.appendChild(title);
        uses.forEach(function (u) {
          var item = document.createElement('button');
          item.type = 'button';
          item.className = 'uses-menu-item';
          var icon = document.createElement('span');
          icon.className = 'uses-menu-icon';
          icon.textContent = '\u25C8';
          item.appendChild(icon);
          var name = document.createElement('span');
          name.textContent = u.v;
          item.appendChild(name);
          item.title = u.f;
          item.addEventListener('click', function (e) {
            e.stopPropagation();
            closeMenu();
            try {
              sessionStorage.setItem(
                'de4sdv-hl',
                JSON.stringify({
                  f: a.getAttribute('data-tip-file'),
                  l: parseInt(a.getAttribute('data-tip-line'), 10),
                  h: a.getAttribute('href') || ''
                })
              );
            } catch (err) {}
            window.location.href =
              (window.VIEWER_PREFIX || '') + 'pages/' + u.f + '.html#' + u.a;
          });
          menu.appendChild(item);
        });
        menu.style.left = Math.min(ev.clientX, window.innerWidth - 240) + 'px';
        menu.style.top = Math.min(ev.clientY, window.innerHeight - menu.offsetHeight - 8) + 'px';
        menu.style.display = 'block';
      });
    }

    /* when landing on a view with a pending highlight, flash the labels of
     * the element inside the diagram (the reverse of the source flash) */
    function flashSvgText(t) {
      try {
        var b = t.getBBox();
        var ns = 'http://www.w3.org/2000/svg';
        var rect = document.createElementNS(ns, 'rect');
        rect.setAttribute('x', b.x - 3);
        rect.setAttribute('y', b.y - 1);
        rect.setAttribute('width', b.width + 6);
        rect.setAttribute('height', b.height + 2);
        rect.setAttribute('rx', 2);
        rect.setAttribute('class', 'svg-flash');
        rect.setAttribute('pointer-events', 'none');
        t.parentNode.insertBefore(rect, t);
        setTimeout(function () {
          if (rect.parentNode) rect.parentNode.removeChild(rect);
        }, 3200);
      } catch (err) {}
    }

    function highlightFromUses() {
      var id = location.hash ? location.hash.slice(1) : '';
      if (id.indexOf('view-') !== 0) return;
      var pending = null;
      try {
        pending = JSON.parse(sessionStorage.getItem('de4sdv-hl') || 'null');
      } catch (err) {}
      if (!pending) return;
      try { sessionStorage.removeItem('de4sdv-hl'); } catch (err) {}
      var section = document.getElementById(id);
      if (!section) return;
      var script = section.querySelector('script.diagram-info');
      var frame = section.querySelector('.diagram-frame.interactive');
      if (!script || !frame) return;
      var map;
      try { map = JSON.parse(script.textContent); } catch (err) { return; }
      var labels = [];
      var flashPos = {};
      Object.keys(map).forEach(function (k) {
        if (k === 'connectors' || k === 'boxes' || k === 'positions') return;
        var info = map[k];
        if (info && info.file === pending.f && info.line === pending.l) {
          labels.push(k);
        }
      });
      var posMap = map.positions || {};
      Object.keys(posMap).forEach(function (pk) {
        var info = posMap[pk];
        if (info && info.file === pending.f && info.line === pending.l) {
          flashPos[pk] = true;
        }
      });
      if (!labels.length && !Object.keys(flashPos).length) return;
      var texts = frame.querySelectorAll('svg text');
      Array.prototype.forEach.call(texts, function (t) {
        var key = norm(t.textContent);
        var x = t.getAttribute('x');
        var y = t.getAttribute('y');
        var pk = (parseFloat(x) || 0) + ',' + (parseFloat(y) || 0);
        if (labels.indexOf(key) !== -1 || flashPos[pk]) flashSvgText(t);
      });
      // visible return path: "arrived from src-N" note in the toolbar
      if (pending.h) {
        var toolbar = section.querySelector('.diagram-toolbar');
        if (toolbar) {
          var note = document.createElement('a');
          note.className = 'origin-note';
          note.href = pending.h;
          note.textContent = '↩ from src-' + pending.l;
          note.title = 'Back to the source line you came from';
          toolbar.appendChild(note);
          setTimeout(function () {
            if (note.parentNode) note.parentNode.removeChild(note);
          }, 8000);
        }
      }
    }

    function initSourceRefs() {
      var sel = 'a.src-ref, span.src-sym, span.vp-tip';
      document.addEventListener('mouseover', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest(sel) : null;
        if (!a) return;
        show(a, {
          kind: a.getAttribute('data-tip-kind') || 'element',
          name: a.getAttribute('data-tip-name') || norm(a.textContent),
          doc: a.getAttribute('data-tip-doc') || '',
          file: a.getAttribute('data-tip-file') || '',
          line: a.getAttribute('data-tip-line') || '',
          href: a.getAttribute('data-tip-href') || a.getAttribute('href') || '',
          hint: a.getAttribute('data-tip-hint') || '',
          uses: usesFor(a)
        }, ev);
      });
      document.addEventListener('mouseout', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest(sel) : null;
        if (!a) return;
        var rt = ev.relatedTarget;
        if (rt && rt.closest && rt.closest(sel) === a) return; // still inside
        hide();
      });
    }

    var scripts = document.querySelectorAll('script.diagram-info');
    Array.prototype.forEach.call(scripts, function (sc) {
      var viewName = sc.getAttribute('data-for');
      var section = document.getElementById('view-' + viewName);
      if (!section) return;
      var frame = section.querySelector('.diagram-frame.interactive');
      if (!frame) return;
      var map;
      try {
        map = JSON.parse(sc.textContent);
      } catch (e) {
        return;
      }
      var posMap = map.positions || {};
      function infoFor(t) {
        var x = t.getAttribute('x');
        var y = t.getAttribute('y');
        if (x !== null && y !== null) {
          var pk = (parseFloat(x) || 0) + ',' + (parseFloat(y) || 0);
          if (posMap[pk]) return posMap[pk];
        }
        return map[norm(t.textContent)];
      }
      var texts = frame.querySelectorAll('svg text');
      Array.prototype.forEach.call(texts, function (t) {
        t.addEventListener('mouseover', function (ev) {
          var info = infoFor(t);
          if (!info) {
            hide();
            return;
          }
          show(t, info, ev);
        });
        t.addEventListener('mousemove', move);
        t.addEventListener('mouseout', hide);
        t.addEventListener('click', function (ev) {
          var info = infoFor(t);
          if (info && info.href) {
            ev.stopPropagation();
            if (/^https?:/i.test(info.href)) {
              window.open(info.href, '_blank', 'noopener');
            } else {
              window.location.href = info.href;
            }
          }
        });
      });
      // connections: the polyline itself carries the tooltip of the label
      // that lies on it (flow/connection usage), so hovering the line names
      // the connection
      var conns = map.connectors || {};
      var connectorShapes = frame.querySelectorAll('svg polyline, svg line, svg path');
      Array.prototype.forEach.call(connectorShapes, function (p) {
        if (p.classList.contains('conn-hit-overlay')) return;
        var key = p.hasAttribute('points')
          ? p.getAttribute('points')
          : (p.tagName.toLowerCase() === 'line'
            ? 'line:' + p.getAttribute('x1') + ',' + p.getAttribute('y1') + ','
              + p.getAttribute('x2') + ',' + p.getAttribute('y2')
            : 'path:' + p.getAttribute('d'));
        var info = conns[key];
        if (!info) return;
        function bindConnector(target) {
          target.classList.add('conn-hit');
          target.addEventListener('mouseover', function (ev) { show(target, info, ev); });
          target.addEventListener('mousemove', move);
          target.addEventListener('mouseout', hide);
          target.addEventListener('click', function (ev) {
            if (info.href) {
              ev.stopPropagation();
              window.location.href = info.href;
            }
          });
        }
        bindConnector(p);
        // SysIDE connectors are often only 0.5px wide. Keep the committed
        // diagram visually unchanged, but add a transparent, wider SVG hit
        // target so a reviewer can actually hover the relationship.
        var hit = p.cloneNode(false);
        hit.classList.add('conn-hit-overlay');
        hit.setAttribute('fill', 'none');
        hit.setAttribute('stroke', 'transparent');
        hit.setAttribute('stroke-width', '12');
        hit.setAttribute('stroke-opacity', '0');
        hit.setAttribute('pointer-events', 'stroke');
        p.parentNode.appendChild(hit);
        bindConnector(hit);
      });
      // element boxes: the white rounded-rect body of a part carries the
      // tooltip of the element it belongs to (same pattern as connectors)
      var boxes = map.boxes || {};
      var paths = frame.querySelectorAll('svg path');
      Array.prototype.forEach.call(paths, function (p) {
        if (p.classList.contains('conn-hit-overlay')) return;
        var info = boxes[p.getAttribute('d')];
        if (!info) return;
        p.classList.add('box-hit');
        p.addEventListener('mouseover', function (ev) { show(p, info, ev); });
        p.addEventListener('mousemove', move);
        p.addEventListener('mouseout', hide);
        p.addEventListener('click', function (ev) {
          if (info.href) {
            ev.stopPropagation();
            window.location.href = info.href;
          }
        });
      });
    });

    initTreeResizer();
    initRefPicker();
    initDiagramFullscreen();
    initSourceRefs();
    initUsesMenu();
    initTreeSearch();
    flashTarget();
    highlightFromUses();
    window.addEventListener('hashchange', function () {
      flashTarget();
      highlightFromUses();
    });
  }

  /* brief fade on the element the page was just jumped to (diagram click,
   * tree member link, source reference); keeps the sticky header from
   * hiding the target via scroll-margin-top, and makes it obvious */
  function flashTarget() {
    var id = location.hash ? location.hash.slice(1) : '';
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    var target = el.classList.contains('src-line') ? el
      : (el.classList.contains('view-section') ? el.querySelector(':scope > h2') : null);
    if (!target) return;
    target.classList.remove('flash');
    void target.offsetWidth; // restart the animation on repeated jumps
    target.classList.add('flash');
    setTimeout(function () { target.classList.remove('flash'); }, 3200);
  }

  // the header height drives the sidebar geometry and scroll offsets
  // (--header-h); measured, never hardcoded
  function measureHeader() {
    var header = document.querySelector('.site-header');
    if (!header) return;
    var h = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--header-h', h + 'px');
  }

  /* ---- model search & filters (filter the tree in place, same layout) ---- */
  function initTreeSearch() {
    var input = document.getElementById('treeSearch');
    var status = document.getElementById('treeSearchStatus');
    var nav = document.getElementById('treeNav');
    var kindFilter = document.getElementById('kindFilter');
    var domainFilter = document.getElementById('domainFilter');
    var aspectFilter = document.getElementById('aspectFilter');
    var vpFilter = document.getElementById('viewpointFilter');
    var clearBtn = document.getElementById('clearFilters');
    if (!input || !status || !nav) return;
    var timer = null;
    var firstMatchEl = null;
    var matchCount = 0;
    var query = '';

    function snapshotOpenState() {
      // capture the current tree shape so clearing the query restores
      // exactly what the user had before typing
      var details = nav.querySelectorAll('details.tree-node');
      for (var i = 0; i < details.length; i++) {
        details[i]._openOrig = details[i].open;
      }
    }

    function labelElement(node) {
      if (node.tagName === 'DETAILS') {
        return node.querySelector('summary > a, summary > .tree-label');
      }
      return node.querySelector(':scope > a, :scope > .tree-label');
    }

    function highlightLabel(labelEl, q) {
      // rebuild the label from its concatenated text: a previous highlight
      // may have split the text into several nodes, so per-node matching
      // would miss queries spanning the split
      var t = labelEl.textContent;
      var idx = t.toLowerCase().indexOf(q);
      if (idx === -1) return;
      var frag = document.createDocumentFragment();
      if (idx > 0) frag.appendChild(document.createTextNode(t.slice(0, idx)));
      var mark = document.createElement('mark');
      mark.className = 'tree-hl';
      mark.textContent = t.slice(idx, idx + q.length);
      frag.appendChild(mark);
      if (idx + q.length < t.length) {
        frag.appendChild(document.createTextNode(t.slice(idx + q.length)));
      }
      labelEl.textContent = '';
      labelEl.appendChild(frag);
    }

    function clearHighlights() {
      var marks = nav.querySelectorAll('mark.tree-hl');
      for (var i = marks.length - 1; i >= 0; i--) {
        var m = marks[i];
        m.parentNode.replaceChild(document.createTextNode(m.textContent), m);
      }
    }

    function passesFilters(node) {
      if (kindFilter && kindFilter.value &&
          node.dataset.kind !== kindFilter.value) return false;
      if (domainFilter && domainFilter.value &&
          node.dataset.domain !== domainFilter.value) return false;
      if (aspectFilter && aspectFilter.value &&
          node.dataset.aspect !== aspectFilter.value) return false;
      if (vpFilter && vpFilter.value &&
          node.dataset.vp !== vpFilter.value) return false;
      return true;
    }

    function anyFilterActive() {
      return (kindFilter && kindFilter.value) || (domainFilter && domainFilter.value) ||
        (aspectFilter && aspectFilter.value) || (vpFilter && vpFilter.value);
    }

    // returns true when the node (or any descendant) matches
    function filterNode(node) {
      // containers (the tree may be wrapped in <ul>s depending on the
      // page) are not tree nodes: recurse through them without marking
      var isNode = node.classList.contains('tree-node');
      var labelEl = isNode ? labelElement(node) : null;
      var nameOk = !query || (labelEl &&
        labelEl.textContent.toLowerCase().indexOf(query) !== -1);
      var own = isNode && nameOk && passesFilters(node);
      var anyChild = false;
      var kids = node.children;
      for (var i = 0; i < kids.length; i++) {
        if (kids[i].tagName === 'SUMMARY') continue; // label row, not a branch
        if (filterNode(kids[i])) anyChild = true;
      }
      if (!isNode) return anyChild;
      var shown = own || anyChild;
      node.classList.toggle('tree-filtered-out', !shown);
      if (own) {
        matchCount++;
        if (!firstMatchEl) firstMatchEl = node;
        if (query) highlightLabel(labelEl, query);
      }
      if (shown && node.tagName === 'DETAILS') node.open = true;
      return shown;
    }

    function restoreTree() {
      clearHighlights();
      var nodes = nav.querySelectorAll('.tree-node');
      for (var i = 0; i < nodes.length; i++) {
        nodes[i].classList.remove('tree-filtered-out');
      }
      var details = nav.querySelectorAll('details.tree-node');
      for (var j = 0; j < details.length; j++) {
        details[j].open = !!details[j]._openOrig;
      }
      status.hidden = true;
    }

    function render() {
      query = input.value.trim().toLowerCase();
      if (!query && !anyFilterActive()) {
        restoreTree();
        updateClearBtn();
        return;
      }
      clearHighlights();
      snapshotOpenState();
      matchCount = 0;
      firstMatchEl = null;
      var tops = nav.children;
      for (var i = 0; i < tops.length; i++) {
        filterNode(tops[i]);
      }
      if (query) {
        status.textContent = matchCount === 0
          ? 'No matches'
          : matchCount + (matchCount === 1 ? ' match' : ' matches');
      } else {
        status.textContent = matchCount === 0
          ? 'No elements'
          : matchCount + (matchCount === 1 ? ' element' : ' elements');
      }
      status.hidden = false;
      updateClearBtn();
    }

    function updateClearBtn() {
      if (!clearBtn) return;
      var active = !!(input.value.trim() || anyFilterActive());
      clearBtn.hidden = !active;
    }

    function resetAll() {
      input.value = '';
      if (kindFilter) kindFilter.value = '';
      if (domainFilter) domainFilter.value = '';
      if (aspectFilter) aspectFilter.value = '';
      if (vpFilter) vpFilter.value = '';
      restoreTree();
      updateClearBtn();
      input.focus();
    }

    input.addEventListener('input', function () {
      clearTimeout(timer);
      timer = setTimeout(render, 120);
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        clearTimeout(timer);
        render();
        if (firstMatchEl) {
          var a = firstMatchEl.tagName === 'DETAILS'
            ? firstMatchEl.querySelector('summary > a')
            : firstMatchEl.querySelector(':scope > a');
          if (a) a.scrollIntoView({ block: 'nearest' });
        }
      } else if (ev.key === 'Escape') {
        if (input.value) {
          input.value = '';
          render();
        }
      }
    });
    if (kindFilter) kindFilter.addEventListener('change', render);
    if (domainFilter) domainFilter.addEventListener('change', render);
    if (aspectFilter) aspectFilter.addEventListener('change', render);
    if (vpFilter) vpFilter.addEventListener('change', render);
    if (clearBtn) clearBtn.addEventListener('click', resetAll);
  }

  /* ---- revision picker ---- */
  function currentRefFromPath() {
    var m = location.pathname.match(/^\/refs\/([^\/]+)\//);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /* Switching to a ref that is not built yet takes a few seconds (the
   * server generates it on first request). Show a progress overlay and
   * pre-fetch the target page so the user sees the generation happen
   * instead of a blank tab; navigate when the server answers. */
  function buildThenGo(url, label) {
    var overlay = document.createElement('div');
    overlay.className = 'viewer-busy';
    var box = document.createElement('div');
    box.className = 'viewer-busy-box';
    var spin = document.createElement('span');
    spin.className = 'viewer-busy-spin';
    var text = document.createElement('span');
    text.className = 'viewer-busy-text';
    text.textContent = 'Building revision ' + label + ' …';
    box.appendChild(spin);
    box.appendChild(text);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    fetch(url, { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('build failed');
        window.location.href = url;
      })
      .catch(function () {
        overlay.remove();
        window.location.href = url; // let the browser try anyway
      });
  }

  function serverNote(picker, text) {
    var wrap = picker.closest ? picker.closest('.ref-picker-wrap') : null;
    if (!wrap) return;
    var note = document.createElement('span');
    note.className = 'ref-picker-note';
    note.textContent = text;
    wrap.appendChild(note);
  }

  /* Server mode: the page is served by tools/sysml_html_viewer/serve.py
   * (it stamps every HTML page with __DE4SDV_VIEWER_SERVER__), which lists
   * every branch and PR of the repository in /_refs and builds unbuilt refs
   * on demand. Upgrade the static picker (which only lists refs built at
   * generation time) to the full dynamic list. Pages without the marker
   * (file:// or a plain static host) keep the static picker. */
  function upgradeRefPicker(picker) {
    if (typeof fetch !== 'function') {
      serverNote(picker, 'revision list unavailable (fetch unsupported)');
      return;
    }
    fetch('/_refs', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (data) {
        if (data && data.refs) {
          var current = currentRefFromPath();
          picker.innerHTML = '';
          data.refs.forEach(function (ref) {
            var o = document.createElement('option');
            o.value = ref.url;
            o.textContent = ref.label;
            o.setAttribute('data-built', ref.built ? 'true' : 'false');
            if (ref.id === current) o.selected = true;
            if (!ref.buildable) {
              o.disabled = true;
              o.title = ref.hint || 'no model content under the validated roots';
            }
            picker.appendChild(o);
          });
          return;
        }
        serverNote(picker, 'revision list unavailable — is --repo correct?');
      });
  }

  function initRefPicker() {
    var picker = document.getElementById('refPicker');
    if (!picker) return;
    picker.addEventListener('change', function () {
      var url = picker.value;
      if (!url) return;
      if (window.__DE4SDV_VIEWER_SERVER__ && url.indexOf('/refs/') === 0) {
        var opt = picker.selectedOptions.length ? picker.selectedOptions[0] : null;
        var unbuilt = opt ? opt.getAttribute('data-built') !== 'true' : true;
        if (unbuilt) {
          buildThenGo(url, opt ? opt.textContent.trim() : url);
          return;
        }
      }
      window.location.href = url;
    });
    if (window.__DE4SDV_VIEWER_SERVER__) upgradeRefPicker(picker);
  }

  /* ---- fullscreen diagrams ---- */
  function setFullscreen(frame, btn, on) {
    frame.classList.toggle('fullscreen', on);
    if (btn) btn.textContent = on ? '\u2715 Close' : '\u26F6 Fullscreen';
    if (on) {
      var scroll = frame.querySelector('.diagram-scroll');
      if (scroll) scroll.scrollTop = 0;
    } else if (frame.getBoundingClientRect().top < 0) {
      frame.scrollIntoView({ block: 'start' });
    }
  }

  function initDiagramFullscreen() {
    var frames = document.querySelectorAll('.diagram-frame');
    Array.prototype.forEach.call(frames, function (frame) {
      var btn = frame.querySelector('.diagram-fs-btn');
      if (!btn) return;
      btn.addEventListener('click', function (ev) {
        ev.stopPropagation();
        setFullscreen(frame, btn, !frame.classList.contains('fullscreen'));
      });
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key !== 'Escape') return;
      var open = document.querySelector('.diagram-frame.fullscreen');
      if (open) setFullscreen(open, open.querySelector('.diagram-fs-btn'), false);
    });
  }

  /* ---- resizable navigation tree ---- */
  function initTreeResizer() {
    var resizer = document.getElementById('treeResizer');
    var layout = document.querySelector('.layout');
    if (!resizer || !layout) return;

    var STORAGE_KEY = 'de4sdvViewerTreeWidth';
    var MIN = 200;
    var MAX = 640;

    function apply(width) {
      if (!width) return;
      width = Math.max(MIN, Math.min(MAX, width));
      layout.style.gridTemplateColumns = width + 'px 6px 1fr';
    }

    try {
      apply(parseInt(window.localStorage.getItem(STORAGE_KEY), 10));
    } catch (e) { /* file:// or private mode: no persistence */ }

    function onMove(ev) {
      var rect = layout.getBoundingClientRect();
      apply(ev.clientX - rect.left);
      try {
        window.localStorage.setItem(STORAGE_KEY, String(ev.clientX - rect.left));
      } catch (e) { /* ignore */ }
    }

    function onUp() {
      resizer.classList.remove('dragging');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }

    resizer.addEventListener('mousedown', function (ev) {
      ev.preventDefault();
      resizer.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
