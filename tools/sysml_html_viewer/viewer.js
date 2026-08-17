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
        hint.textContent = info.hint || 'click to open in viewer';
        tip.appendChild(hint);
      }
      tip.style.display = 'block';
      move(ev);
    }

    /* ---- source references (hover tooltip, click to jump) ---- */
    function initSourceRefs() {
      document.addEventListener('mouseover', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest('a.src-ref') : null;
        if (!a) return;
        show(a, {
          kind: a.getAttribute('data-tip-kind') || 'element',
          name: a.getAttribute('data-tip-name') || norm(a.textContent),
          doc: a.getAttribute('data-tip-doc') || '',
          file: a.getAttribute('data-tip-file') || '',
          line: a.getAttribute('data-tip-line') || '',
          href: a.getAttribute('href') || '',
          hint: a.getAttribute('data-tip-hint') || ''
        }, ev);
      });
      document.addEventListener('mouseout', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest('a.src-ref') : null;
        if (!a) return;
        var rt = ev.relatedTarget;
        if (rt && rt.closest && rt.closest('a.src-ref') === a) return; // still inside
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
      var texts = frame.querySelectorAll('svg text');
      Array.prototype.forEach.call(texts, function (t) {
        t.addEventListener('mouseover', function (ev) {
          var info = map[norm(t.textContent)];
          if (!info) {
            hide();
            return;
          }
          show(t, info, ev);
        });
        t.addEventListener('mousemove', move);
        t.addEventListener('mouseout', hide);
        t.addEventListener('click', function (ev) {
          var info = map[norm(t.textContent)];
          if (info && info.href) {
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
