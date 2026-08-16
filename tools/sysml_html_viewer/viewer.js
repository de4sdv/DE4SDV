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
        hint.textContent = 'click to open in viewer';
        tip.appendChild(hint);
      }
      tip.style.display = 'block';
      move(ev);
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
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
