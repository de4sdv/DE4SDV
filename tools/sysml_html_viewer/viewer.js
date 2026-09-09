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

  /* ---- DE4SDV Guide inline renderer (link-aware) ----
   * Same inline subset as appendAskInline plus markdown links. Model
   * output is untrusted and must never reach innerHTML: link URLs are
   * whitelisted (http(s), mailto, relative repository paths), and text
   * always enters as text nodes. Relative targets pointing at a
   * repository path are rewritten to GitHub blob URLs pinned to the
   * deployed SHA so in-text citations land on the exact revision, and a
   * bare path with no markdown link is auto-linked the same way. */
  var GUIDE_LINK_RE =
    /\[([^\]\n]+)\]\(([^)\s]+)\)/g;
  var GUIDE_BARE_PATH_RE =
    /(^|[\s(])([A-Za-z0-9][A-Za-z0-9_./-]*(?:\.md|\.py|\.sysml|\.ya?ml|\.toml))(?=$|[\s.,;:!?)])/g;
  var GUIDE_SAFE_URL_RE = /^(https?:\/\/|mailto:)/;
  var GUIDE_REL_PATH_RE = /^[A-Za-z0-9][A-Za-z0-9_./-]+$/;

  function guideIsRepoPath(candidate) {
    if (!GUIDE_REL_PATH_RE.test(candidate)) return false;
    if (candidate.indexOf('//') !== -1) return false;
    return candidate.indexOf('/') !== -1 || candidate.indexOf('.') !== -1;
  }

  function guideRewriteHref(href, gitSha) {
    if (GUIDE_SAFE_URL_RE.test(href)) return href;
    if (!guideIsRepoPath(href)) return '';
    if (!gitSha) return '';
    var base = window.GUIDE_REPO_BLOB_BASE || '';
    if (!base) return '';
    return base.replace(/\/+$/, '') + '/blob/' + gitSha + '/' + href;
  }

  function appendGuideInline(parent, text, gitSha) {
    var pos = 0;
    var match;
    GUIDE_LINK_RE.lastIndex = 0;
    while ((match = GUIDE_LINK_RE.exec(text)) !== null) {
      if (match.index > pos) {
        appendAskInline(parent, text.slice(pos, match.index));
      }
      var label = match[1];
      var target = match[2];
      var href = guideRewriteHref(target, gitSha);
      if (href) {
        var a = document.createElement('a');
        a.href = href;
        a.textContent = label;
        if (GUIDE_SAFE_URL_RE.test(href)) {
          a.target = '_blank';
          a.rel = 'noopener';
        }
        parent.appendChild(a);
      } else {
        appendAskInline(parent, label);
      }
      pos = match.index + match[0].length;
    }
    if (pos < text.length) {
      var rest = text.slice(pos);
      var barePos = 0;
      var bare;
      GUIDE_BARE_PATH_RE.lastIndex = 0;
      while ((bare = GUIDE_BARE_PATH_RE.exec(rest)) !== null) {
        if (bare.index > barePos) {
          appendAskInline(parent, rest.slice(barePos, bare.index));
        }
        var pathCandidate = bare[2];
        var bareHref = guideRewriteHref(pathCandidate, gitSha);
        if (bareHref) {
          var bareA = document.createElement('a');
          bareA.href = bareHref;
          bareA.textContent = pathCandidate;
          bareA.className = 'guide-inline-src';
          parent.appendChild(bareA);
        } else {
          appendAskInline(parent, pathCandidate);
        }
        barePos = bare.index + bare[0].length;
      }
      if (barePos < rest.length) {
        appendAskInline(parent, rest.slice(barePos));
      }
    }
  }

  /* Render the small Markdown subset commonly returned by the model.  Build
   * nodes explicitly: model output is untrusted and must never reach
   * innerHTML. */
  function appendAskInline(parent, text) {
    var pos = 0;
    while (pos < text.length) {
      var emphasisAt = text.indexOf('***', pos);
      var strongAt = text.indexOf('**', pos);
      var doubleCodeAt = text.indexOf('``', pos);
      var codeAt = text.indexOf('`', pos);
      var next = -1;
      var marker = '';
      [
        [emphasisAt, '***'],
        [strongAt, '**'],
        [doubleCodeAt, '``'],
        [codeAt, '`']
      ].forEach(function (candidate) {
        if (candidate[0] !== -1
            && (next === -1 || candidate[0] < next
                || (candidate[0] === next
                    && candidate[1].length > marker.length))) {
          next = candidate[0];
          marker = candidate[1];
        }
      });
      if (marker === '**' && emphasisAt === next) {
        marker = '***';
      }
      if (marker === '`' && doubleCodeAt === next) {
        marker = '``';
      }
      if (next === -1) {
        parent.appendChild(document.createTextNode(text.slice(pos)));
        return;
      }
      if (next > pos) {
        parent.appendChild(document.createTextNode(text.slice(pos, next)));
      }
      var end = text.indexOf(marker, next + marker.length);
      if (end === -1) {
        parent.appendChild(document.createTextNode(
          text.slice(next + marker.length)
        ));
        return;
      }
      var content = text.slice(next + marker.length, end);
      if (!content) {
        pos = end + marker.length;
        continue;
      }
      var node;
      if (marker === '***') {
        node = document.createElement('strong');
        var em = document.createElement('em');
        appendAskInline(em, content);
        node.appendChild(em);
      } else if (marker === '**') {
        node = document.createElement('strong');
        appendAskInline(node, content);
      } else {
        node = document.createElement('code');
        node.textContent = content;
      }
      parent.appendChild(node);
      pos = end + marker.length;
    }
  }

  function renderAskAnswer(container, text, inlineRenderer) {
    /* inlineRenderer defaults to appendAskInline; DE4SDV Guide passes a
     * link-aware variant. Ask-the-model rendering is unchanged. */
    var inline = inlineRenderer || appendAskInline;
    container.textContent = '';
    var lines = String(text || '').replace(/\r\n?/g, '\n').split('\n');
    var i = 0;
    while (i < lines.length) {
      if (!lines[i].trim()) {
        i += 1;
        continue;
      }

      var fence = lines[i].match(/^\s*`{3,}[^`]*$/);
      if (fence) {
        i += 1;
        var codeLines = [];
        while (i < lines.length && !/^\s*`{3,}\s*$/.test(lines[i])) {
          codeLines.push(lines[i]);
          i += 1;
        }
        if (i < lines.length) i += 1;
        var pre = document.createElement('pre');
        var blockCode = document.createElement('code');
        blockCode.textContent = codeLines.join('\n');
        pre.appendChild(blockCode);
        container.appendChild(pre);
        continue;
      }

      var heading = lines[i].match(/^\s{0,3}(#{1,6})\s+(.+)$/);
      if (heading) {
        var h = document.createElement(
          'h' + Math.min(6, heading[1].length + 2)
        );
        inline(h, heading[2].trim());
        container.appendChild(h);
        i += 1;
        continue;
      }

      var bullet = lines[i].match(/^\s*[-*+]\s+(.+)$/);
      var numbered = lines[i].match(/^\s*(\d+)[.)]\s+(.+)$/);
      if (bullet || numbered) {
        var list = document.createElement(bullet ? 'ul' : 'ol');
        while (i < lines.length) {
          var item = bullet
            ? lines[i].match(/^\s*[-*+]\s+(.+)$/)
            : lines[i].match(/^\s*(\d+)[.)]\s+(.+)$/);
          if (!item) break;
          var li = document.createElement('li');
          inline(li, item[bullet ? 1 : 2].trim());
          list.appendChild(li);
          i += 1;
          var nextItem = i;
          while (nextItem < lines.length && !lines[nextItem].trim()) {
            nextItem += 1;
          }
          var continues = nextItem < lines.length && (bullet
            ? /^\s*[-*+]\s+/.test(lines[nextItem])
            : /^\s*\d+[.)]\s+/.test(lines[nextItem]));
          if (continues) i = nextItem;
        }
        container.appendChild(list);
        continue;
      }

      var paragraphLines = [];
      while (i < lines.length && lines[i].trim()
             && !/^\s*`{3,}[^`]*$/.test(lines[i])
             && !/^\s{0,3}#{1,6}\s+/.test(lines[i])
             && !/^\s*[-*+]\s+/.test(lines[i])
             && !/^\s*\d+[.)]\s+/.test(lines[i])) {
        paragraphLines.push(lines[i].trim());
        i += 1;
      }
      var p = document.createElement('p');
      inline(p, paragraphLines.join(' '));
      container.appendChild(p);
    }
  }

  /* ---- DE4SDV Guide: floating repository chatbot (all viewer pages) ----
   * Separate from "Ask the model": repository/documentation assistant,
   * grounded in the checked-out Git repository via /api/repo-chat.
   * Never routes through the Systems Modeling API, never falls back to
   * Ask the model, and states that boundary in its intro. Conversation
   * and collapsed/expanded state persist client-side (localStorage). */
  var GUIDE_STORAGE_KEY = 'de4sdv-guide-state';

  function guideLoadState() {
    try {
      var st = JSON.parse(
        window.localStorage.getItem(GUIDE_STORAGE_KEY) || 'null'
      );
      if (st && typeof st === 'object' && Array.isArray(st.messages)) {
        return st;
      }
    } catch (err) {}
    return { open: false, messages: [] };
  }

  function guideSaveState(state) {
    try {
      window.localStorage.setItem(
        GUIDE_STORAGE_KEY, JSON.stringify(state)
      );
    } catch (err) { /* file:// or private mode: no persistence */ }
  }

  function initRepoGuide() {
    if (document.getElementById('guideFab')) return;

    var state = guideLoadState();

    /* floating action button (the collapsed form, bottom-right) */
    var fab = document.createElement('button');
    fab.type = 'button';
    fab.id = 'guideFab';
    fab.className = 'guide-fab';
    fab.setAttribute('aria-label', 'Open the DE4SDV Guide chat');
    fab.title = 'DE4SDV Guide \u2014 repository & documentation assistant';
    var fabIcon = document.createElement('span');
    fabIcon.className = 'guide-fab-icon';
    fabIcon.textContent = '\u{1F4AC}';
    fabIcon.setAttribute('aria-hidden', 'true');
    var fabLabel = document.createElement('span');
    fabLabel.textContent = 'Guide';
    fab.appendChild(fabIcon);
    fab.appendChild(fabLabel);

    /* panel (the expanded form) */
    var panel = document.createElement('div');
    panel.className = 'guide-panel';
    panel.id = 'guidePanel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'DE4SDV Guide');

    var head = document.createElement('div');
    head.className = 'guide-head';
    var title = document.createElement('span');
    title.className = 'guide-title';
    title.textContent = 'DE4SDV Guide';
    var cap = document.createElement('span');
    cap.className = 'guide-cap';
    cap.textContent = 'repo assistant';
    cap.title = 'Generated answers grounded in the checked-out Git '
      + 'repository. Not an engineering or model authority; no '
      + 'Systems Modeling API queries. For a model element, '
      + 'right-click it and use Ask the model.';
    var clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.className = 'guide-clear';
    clearBtn.textContent = 'New chat';
    clearBtn.title = 'Clear the conversation';
    var minBtn = document.createElement('button');
    minBtn.type = 'button';
    minBtn.className = 'guide-min';
    minBtn.textContent = '\u2212';
    minBtn.setAttribute('aria-label', 'Minimize the DE4SDV Guide');
    minBtn.title = 'Minimize';
    head.appendChild(title);
    head.appendChild(cap);
    head.appendChild(clearBtn);
    head.appendChild(minBtn);

    var body = document.createElement('div');
    body.className = 'guide-body';
    body.id = 'guideBody';

    var foot = document.createElement('div');
    foot.className = 'guide-foot';
    var input = document.createElement('textarea');
    input.className = 'guide-input';
    input.id = 'guideInput';
    input.placeholder = 'Ask about the repository, docs, workflow\u2026';
    input.rows = 2;
    input.setAttribute('aria-label', 'Ask the DE4SDV Guide');
    var sendBtn = document.createElement('button');
    sendBtn.type = 'button';
    sendBtn.className = 'guide-send';
    sendBtn.textContent = 'Send';
    foot.appendChild(input);
    foot.appendChild(sendBtn);

    panel.appendChild(head);
    panel.appendChild(body);
    panel.appendChild(foot);

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    var els = { body: body, input: input };

    /* --- rendering (untrusted model output never reaches innerHTML) --- */
    function guideSourcesBlock(answer, sources, sha) {
      var wrap = document.createElement('div');
      wrap.className = 'guide-sources';
      var label = document.createElement('span');
      label.className = 'guide-sources-label';
      label.textContent = 'sources';
      wrap.appendChild(label);
      (sources || []).forEach(function (s) {
        var a = document.createElement('a');
        a.className = 'guide-source';
        var ref = s.path + ':' + s.start + '-' + s.end;
        if (s.github_url) {
          a.href = s.github_url;
          a.target = '_blank';
          a.rel = 'noopener';
          a.title = 'Open ' + ref + ' on GitHub at the deployed revision';
        } else {
          a.title = 'Repository source ' + ref;
        }
        a.textContent = ref;
        wrap.appendChild(a);
      });
      if (sha) {
        var pinned = document.createElement('span');
        pinned.className = 'guide-sha';
        pinned.title = 'Source links are pinned to the deployed '
          + 'application revision';
        pinned.textContent = '@ ' + sha.slice(0, 7);
        wrap.appendChild(pinned);
      }
      return wrap;
    }

    function guideAppendUser(text) {
      var b = document.createElement('div');
      b.className = 'guide-msg guide-msg-user';
      b.textContent = text;
      els.body.appendChild(b);
      els.body.scrollTop = els.body.scrollHeight;
    }

    function guideAppendStarter(text) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'guide-starter';
      b.textContent = text;
      b.addEventListener('click', function () {
        b.remove();
        guideSubmit(text);
      });
      els.body.appendChild(b);
    }

    function guidePendingBubble() {
      var b = document.createElement('div');
      b.className = 'guide-msg guide-msg-guide';
      var st = document.createElement('span');
      st.className = 'guide-status';
      st.textContent = 'Searching the repository\u2026';
      b.appendChild(st);
      els.body.appendChild(b);
      els.body.scrollTop = els.body.scrollHeight;
      return b;
    }

    function guideRemoveStarterButtons() {
      Array.prototype.slice.call(
        els.body.querySelectorAll('.guide-starter')
      ).forEach(function (b) { b.remove(); });
    }

    function guideSubmit(text) {
      var q = String(text || '').trim();
      if (!q) return;
      guideRemoveStarterButtons();
      guideAppendUser(q);
      state.messages.push({ role: 'user', text: q });
      guideSaveState(state);
      var bubble = guidePendingBubble();
      input.value = '';
      var answerSha = null;
      fetch('/api/repo-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      }).then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, data: data };
        });
      }).then(function (res) {
        bubble.remove();
        answerSha = res.data.git_sha || null;
        window.GUIDE_REPO_BLOB_BASE = res.data.repo_blob_base
          || window.GUIDE_REPO_BLOB_BASE || '';
        var b = document.createElement('div');
        b.className = 'guide-msg guide-msg-guide';
        renderAskAnswer(b, res.data.error
          ? res.data.error
          : (res.data.answer || '(empty answer)'),
          function (parent, text) {
            appendGuideInline(parent, text, answerSha);
          });
        if (res.data.sources && res.data.sources.length) {
          b.appendChild(guideSourcesBlock(
            res.data.answer, res.data.sources, res.data.git_sha
          ));
        }
        els.body.appendChild(b);
        state.messages.push({
          role: 'guide',
          text: res.data.answer || res.data.error || '',
          sources: res.data.sources || [],
          sha: res.data.git_sha || '',
          repoBlobBase: res.data.repo_blob_base || ''
        });
        guideSaveState(state);
        els.body.scrollTop = els.body.scrollHeight;
      }).catch(function (err) {
        bubble.remove();
        var b = document.createElement('div');
        b.className = 'guide-msg guide-msg-guide';
        renderAskAnswer(b, 'DE4SDV Guide request failed: ' + err);
        els.body.appendChild(b);
        els.body.scrollTop = els.body.scrollHeight;
      });
    }

    function guideReplay() {
      els.body.textContent = '';
      if (state.messages.length) {
        state.messages.forEach(function (m) {
          if (m.role === 'user') {
            guideAppendUser(m.text);
            return;
          }
          var b = document.createElement('div');
          b.className = 'guide-msg guide-msg-guide';
          window.GUIDE_REPO_BLOB_BASE = m.repoBlobBase
            || window.GUIDE_REPO_BLOB_BASE || '';
          renderAskAnswer(b, m.text || '', function (parent, text) {
            appendGuideInline(parent, text, m.sha || null);
          });
          if (m.sources && m.sources.length) {
            b.appendChild(guideSourcesBlock(
              m.text, m.sources, m.sha
            ));
          }
          els.body.appendChild(b);
        });
      } else {
        var intro = document.createElement('div');
        intro.className = 'guide-msg guide-msg-guide guide-intro';
        renderAskAnswer(intro,
          'I can help you understand the DE4SDV repository, '
          + 'architecture, documentation and contribution workflow. '
          + 'Answers are generated from the checked-out Git repository '
          + '\u2014 not from the Systems Modeling API. For a specific '
          + 'model element, right-click it and use Ask the model.');
        els.body.appendChild(intro);
        ['What is DE4SDV and where do I start?',
         'How do I contribute to the repository?',
         'Where are the architecture decision records (ADRs)?',
         'How is the SysML v2 model organized?',
         'What does the public deployment stack look like?'
        ].forEach(guideAppendStarter);
      }
      els.body.scrollTop = els.body.scrollHeight;
    }

    function applyOpen(open) {
      state.open = !!open;
      panel.classList.toggle('open', state.open);
      guideSaveState(state);
      chatSyncLayout();
      if (state.open) input.focus();
    }

    fab.addEventListener('click', function () { applyOpen(true); });
    minBtn.addEventListener('click', function () {
      applyOpen(false);
    });
    clearBtn.addEventListener('click', function () {
      state.messages = [];
      guideSaveState(state);
      guideReplay();
    });
    sendBtn.addEventListener('click', function () {
      guideSubmit(input.value);
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' && !ev.shiftKey) {
        ev.preventDefault();
        guideSubmit(input.value);
      }
    });

    guideReplay();
    applyOpen(state.open);
    chatSyncLayout();
  }

    /* Open the DE4SDV Guide panel with a prefilled question (context-menu
     * entry point). The question goes into the input so the user can adjust
     * before sending; the panel expands and keeps its persisted
     * conversation. */
    function openGuideWith(question) {
      var panel = document.getElementById('guidePanel');
      var input = document.getElementById('guideInput');
      if (!panel || !input) {
        initRepoGuide();
        panel = document.getElementById('guidePanel');
        input = document.getElementById('guideInput');
        if (!panel || !input) return;
      }
      input.value = question;
      panel.classList.add('open');
      try {
        window.localStorage.setItem(CHAT_GUIDE_CHIP_KEY, '0');
      } catch (err) {}
      chatSyncLayout();
      try {
        var st = JSON.parse(
          window.localStorage.getItem(GUIDE_STORAGE_KEY) || '{}'
        );
        st.open = true;
        window.localStorage.setItem(
          GUIDE_STORAGE_KEY, JSON.stringify(st)
        );
      } catch (err) {}
      input.focus();
    }

  /* ---- chat panel layout coordinator ----
   * Two floating panels share the bottom-right corner: Ask the model
   * (.ask-panel) and DE4SDV Guide (.guide-panel). When both are open they
   * sit side by side (Ask keeps the corner, Guide shifts left); when only
   * one is open it takes the corner; the Guide FAB is visible only when
   * neither is open. Minimized panels reappear as small chips. */
  var CHAT_ASK_OPEN_KEY = 'de4sdv-ask-open';
  var CHAT_GUIDE_CHIP_KEY = 'de4sdv-guide-minimized';

  function chatAskMinimized() {
    try { return window.localStorage.getItem(CHAT_ASK_OPEN_KEY) === '0'; }
    catch (err) { return false; }
  }

  function chatSetAskMinimized(min) {
    try {
      window.localStorage.setItem(CHAT_ASK_OPEN_KEY, min ? '0' : '1');
    } catch (err) {}
  }

  function chatGuidePanelOpen() {
    var panel = document.getElementById('guidePanel');
    return !!(panel && panel.classList.contains('open'));
  }

  function chatAskPanelOpen() {
    var panel = document.getElementById('askPanel');
    return !!(panel && panel.classList.contains('open'));
  }

  function chatSyncLayout() {
    var askOpen = chatAskPanelOpen();
    var guideOpen = chatGuidePanelOpen();
    var both = askOpen && guideOpen;

    document.body.classList.toggle('chat-ask-open', askOpen);
    document.body.classList.toggle('chat-guide-open', guideOpen);
    document.body.classList.toggle('chat-both-open', both);

    // Fixed order, left to right: [Ask panel/chip] [Guide panel]
    // Guide always owns the corner slot; Ask shifts left when both open.
    var askPanel = document.getElementById('askPanel');
    if (askPanel) askPanel.classList.toggle('shifted', both);

    var guidePanel = document.getElementById('guidePanel');
    if (guidePanel) guidePanel.classList.remove('shifted');

    var fab = document.getElementById('guideFab');
    if (fab) {
      // The FAB is the single Guide entry point: hidden only while the
      // Guide panel itself is open.
      fab.style.display = guideOpen ? 'none' : '';
      // When Ask is open (or minimized to its chip), the FAB must not sit
      // under the Ask panel/chip: shift it left of Ask's footprint.
      fab.classList.toggle('shifted', askOpen || chatAskMinimized());
    }
    var askChip = document.getElementById('askMinChip');
    if (askChip) {
      askChip.style.display =
        (!askOpen && chatAskMinimized()) ? 'inline-flex' : 'none';
      askChip.classList.toggle('shifted', guideOpen);
    }
  }


  function hasContextMenuItems(uses, ask, serverEnabled) {
    return Boolean((uses && uses.length) || (ask && serverEnabled));
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
      // stash for the ask-model context menu (any hovered askable element)
      t.__askInfo = info;
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
      /* ask-model: element identity for the context menu. Source refs and
       * viewpoint spans carry data-tip-* attrs; SVG texts, connectors, and
       * boxes stash the tooltip info on hover (show()). */
      function askInfoFor(target, a) {
        if (a && a.getAttribute) {
          var name = a.getAttribute('data-tip-name');
          if (name) {
            return {
              kind: a.getAttribute('data-tip-kind') || 'element',
              name: name,
              doc: a.getAttribute('data-tip-doc') || '',
              file: a.getAttribute('data-tip-file') || '',
              line: a.getAttribute('data-tip-line') || ''
            };
          }
        }
        var el = target || null;
        while (el) {
          if (el.__askInfo) return el.__askInfo;
          // tree element nodes carry the identity on the .tree-node
          // container, not on the matched anchor/label
          if (el.getAttribute && el.getAttribute('data-tip-name')) {
            return {
              kind: el.getAttribute('data-tip-kind') || 'element',
              name: el.getAttribute('data-tip-name'),
              doc: el.getAttribute('data-tip-doc') || '',
              file: el.getAttribute('data-tip-file') || '',
              line: el.getAttribute('data-tip-line') || ''
            };
          }
          el = el.parentElement;
        }
        return null;
      }

      document.addEventListener('contextmenu', function (ev) {
        var a = ev.target && ev.target.closest
          ? ev.target.closest('a.src-ref, span.src-sym, span.vp-tip, '
            + '.tree-node[data-tip-name] > summary > a, '
            + '.tree-node[data-tip-name] > a, '
            + '.tree-node[data-tip-name] > summary > .tree-label') : null;
        var uses = a ? usesFor(a) : null;
        var ask = askInfoFor(ev.target, a);
        var canAsk = ask && window.__DE4SDV_VIEWER_SERVER__;
        if (!hasContextMenuItems(uses, ask,
                                 window.__DE4SDV_VIEWER_SERVER__)
            && !canAsk) return;
        ev.preventDefault();
        closeMenu();
        if (uses && uses.length) {
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
        }
        if (canAsk) {
          var divider = document.createElement('div');
          divider.className = 'uses-menu-divider';
          menu.appendChild(divider);
          var repoItem = document.createElement('button');
          repoItem.type = 'button';
          repoItem.className = 'uses-menu-item';
          var repoIcon = document.createElement('span');
          repoIcon.className = 'uses-menu-icon';
          repoIcon.textContent = '\u{1F4AC}';
          repoItem.appendChild(repoIcon);
          var repoLabel = document.createElement('span');
          repoLabel.textContent = 'Ask repo assistant\u2026';
          repoItem.appendChild(repoLabel);
          repoItem.title = 'Open the DE4SDV Guide with this element ' +
            'named in the question — repository and documentation ' +
            'context, generated answer (not model authority)';
          repoItem.addEventListener('click', function (e) {
            e.stopPropagation();
            closeMenu();
            openGuideWith('What is the ' + (ask.kind || 'element')
              + ' ' + ask.name + ' and where is it documented?');
          });
          menu.appendChild(repoItem);
          var askItem = document.createElement('button');
          askItem.type = 'button';
          askItem.className = 'uses-menu-item';
          var askIcon = document.createElement('span');
          askIcon.className = 'uses-menu-icon';
          askIcon.textContent = '\u2753';
          askItem.appendChild(askIcon);
          var askLabel = document.createElement('span');
          askLabel.textContent = 'Ask the model\u2026 (authoritative query)';
          askItem.appendChild(askLabel);
          askItem.title = 'Ask a question about ' + ask.name +
            ' — answered from the model element itself';
          askItem.addEventListener('click', function (e) {
            e.stopPropagation();
            closeMenu();
            openAskPanel(ask);
          });
          menu.appendChild(askItem);
        }
        menu.style.left = Math.min(ev.clientX, window.innerWidth - 240) + 'px';
        menu.style.top = Math.min(ev.clientY, window.innerHeight - menu.offsetHeight - 8) + 'px';
        menu.style.display = 'block';
      });

      /* ---- ask-model panel (server mode only) ---- */
      var askPanel = null;
      function ensureAskPanel() {
        if (askPanel) return;
        askPanel = document.createElement('div');
        askPanel.className = 'ask-panel';
        askPanel.id = 'askPanel';

        var head = document.createElement('div');
        head.className = 'ask-head';
        var askTitle = document.createElement('span');
        askTitle.className = 'ask-title';
        var askKind = document.createElement('span');
        askKind.className = 'ask-kind';
        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'ask-close';
        closeBtn.textContent = '\u2715';
        closeBtn.title = 'Close (Esc)';
        closeBtn.addEventListener('click', function () { hideAskPanel(); });
        head.appendChild(askTitle);
        head.appendChild(askKind);
        head.appendChild(closeBtn);

        var meta = document.createElement('a');
        meta.className = 'ask-meta';

        var body = document.createElement('div');
        body.className = 'ask-body';
        var input = document.createElement('textarea');
        input.className = 'ask-input';
        input.placeholder = 'Ask about this element\u2026 (Enter to ask, Shift+Enter for a new line)';
        input.rows = 3;
        var status = document.createElement('div');
        status.className = 'ask-status';
        var answer = document.createElement('div');
        answer.className = 'ask-answer';
        var footer = document.createElement('div');
        footer.className = 'ask-footer';
        var grounded = document.createElement('a');
        grounded.className = 'ask-grounded';
        var modelLine = document.createElement('span');
        modelLine.className = 'ask-model-line';
        var altsLine = document.createElement('div');
        altsLine.className = 'ask-alts';
        footer.appendChild(grounded);
        footer.appendChild(modelLine);
        footer.appendChild(altsLine);
        body.appendChild(input);
        body.appendChild(status);
        body.appendChild(answer);
        body.appendChild(footer);

        askPanel.appendChild(head);
        askPanel.appendChild(meta);
        askPanel.appendChild(body);
        var askChip = document.createElement('button');
        askChip.type = 'button';
        askChip.id = 'askMinChip';
        askChip.className = 'chat-chip chat-chip-ask';
        askChip.setAttribute('aria-label',
          'Reopen the Ask the model panel');
        askChip.title = 'Ask the model — minimized';
        askChip.textContent = '\u2753';
        askChip.addEventListener('click', function () {
          showAskPanel();
        });
        document.body.appendChild(askChip);
        document.body.appendChild(askPanel);
        chatSyncLayout();

        input.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' && !ev.shiftKey) {
            ev.preventDefault();
            submitAsk();
          }
        });
        document.addEventListener('keydown', function (ev) {
          if (ev.key === 'Escape' && askPanel.classList.contains('open')) {
            hideAskPanel();
          }
        });
        var askMin = document.createElement('button');
        askMin.type = 'button';
        askMin.className = 'ask-min';
        askMin.textContent = '\u2212';
        askMin.setAttribute('aria-label', 'Minimize the Ask the model panel');
        askMin.title = 'Minimize (keeps this answer)';
        askMin.addEventListener('click', function (e) {
          e.stopPropagation();
          hideAskPanel();
        });
        head.appendChild(askMin);

        askPanel.__els = {
          title: askTitle, kind: askKind, meta: meta, input: input,
          status: status, answer: answer, grounded: grounded,
          modelLine: modelLine, altsLine: altsLine
        };
      }

      function hideAskPanel() {
        if (askPanel) {
          askPanel.classList.remove('open');
          chatSetAskMinimized(true);
          chatSyncLayout();
        }
      }

      function showAskPanel() {
        if (!askPanel) return;
        askPanel.classList.add('open');
        chatSetAskMinimized(false);
        chatSyncLayout();
        if (askPanel.__els && askPanel.__els.input) askPanel.__els.input.focus();
      }

      function openAskPanel(info) {
        ensureAskPanel();
        var els = askPanel.__els;
        askPanel.__info = info;
        askPanel.classList.add('open');
        chatSetAskMinimized(false);
        chatSyncLayout();
        els.title.textContent = info.name;
        els.kind.textContent =
          (info.kind || 'element') + ' (authoritative query)';
        els.meta.textContent = info.file ? info.file + ':' + info.line : '';
        els.meta.href = info.file
          ? (window.VIEWER_PREFIX || '') + 'pages/' + info.file + '.html#src-' + info.line
          : '';
        els.input.value = '';
        els.status.textContent = '';
        els.answer.textContent = '';
        els.grounded.textContent = '';
        els.grounded.removeAttribute('href');
        els.modelLine.textContent = '';
        els.altsLine.textContent = '';
        els.input.focus();
      }

      function submitAsk() {
        if (!askPanel) return;
        var els = askPanel.__els;
        var info = askPanel.__info;
        var q = els.input.value.trim();
        if (!info || !q || els.status.textContent) return;
        els.status.textContent = 'Asking the model\u2026';
        els.answer.textContent = '';
        els.grounded.textContent = '';
        els.modelLine.textContent = '';
        els.altsLine.textContent = '';
        fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            element: info.name,
            question: q,
            file: info.file || '',
            line: info.line || '',
            ref: currentRefFromPath()
          })
        }).then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, data: data };
          });
        }).then(function (res) {
          els.status.textContent = '';
          if (!res.ok || res.data.error) {
            renderAskAnswer(els.answer, res.data.error ||
              'request failed (HTTP ' + (res.ok ? 200 : '?') + ')');
            return;
          }
          renderAskAnswer(els.answer, res.data.answer || '(empty answer)');
          var el = res.data.element || {};
          if (el.href) {
            els.grounded.href = (window.VIEWER_PREFIX || '') + el.href;
            els.grounded.textContent =
              'grounded on ' + el.name + ' \u00b7 ' + el.file + ':' + el.line;
          }
          els.modelLine.textContent = 'model: ' + (res.data.model || '?')
            + (res.data.method_context_source
              ? ' \u00b7 method context: ' + res.data.method_context_source
              : '');
          var alts = res.data.ambiguous_alternatives || [];
          if (alts.length) {
            els.altsLine.textContent =
              'same-name elements exist (' + alts.length + ' more) \u2014 ' +
              alts.map(function (x) { return x.file + ':' + x.line; }).join(', ');
          }
        }).catch(function (err) {
          els.status.textContent = '';
          renderAskAnswer(els.answer, 'ask-model request failed: ' + err);
        });
      }
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
      document.addEventListener('click', function (ev) {
        var a = ev.target && ev.target.closest ? ev.target.closest(sel) : null;
        if (!a) return;
        var href = a.getAttribute('data-tip-href');
        if (!href) return;
        // the span itself is clickable (viewpoint type -> SAF page);
        // anchors with data-tip-href would be handled here too
        ev.preventDefault();
        ev.stopPropagation();
        if (/^https?:/i.test(href)) {
          window.open(href, '_blank', 'noopener');
        } else {
          window.location.href = href;
        }
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
    initRequirements();
    initRepoGuide();
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


  /* ---- needs & requirements browser (requirements.html) ---- */

  function initRequirements() {
    var list = document.getElementById('reqList');
    if (!list) return; // not on the requirements page
    var input = document.getElementById('reqSearch');
    var status = document.getElementById('reqStatus');
    var cards = Array.prototype.slice.call(list.querySelectorAll('.req-card'));
    var chips = Array.prototype.slice.call(document.querySelectorAll('.req-filter'));
    var activeKinds = [];

    function apply() {
      var q = input ? input.value.trim().toLowerCase() : '';
      var shown = 0;
      cards.forEach(function (card) {
        var kindOk = !activeKinds.length ||
          activeKinds.indexOf(card.getAttribute('data-kind')) !== -1;
        var textOk = !q ||
          (card.getAttribute('data-search') || '').indexOf(q) !== -1;
        var show = kindOk && textOk;
        card.classList.toggle('filtered-out', !show);
        if (show) shown += 1;
      });
      if (status) {
        var filtered = activeKinds.length || q;
        status.hidden = !filtered;
        if (filtered) {
          status.textContent = shown + ' of ' + cards.length + ' records shown';
        }
      }
    }

    if (input) {
      input.addEventListener('input', apply);
    }
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var kind = chip.getAttribute('data-kind');
        var idx = activeKinds.indexOf(kind);
        if (idx === -1) {
          activeKinds.push(kind);
          chip.classList.add('active');
        } else {
          activeKinds.splice(idx, 1);
          chip.classList.remove('active');
        }
        apply();
      });
    });

    // hash navigation: flash the target record and scroll past the header
    function flashFromHash() {
      if (!location.hash) return;
      var target = document.getElementById(location.hash.slice(1));
      if (!target || !target.classList.contains('req-card')) return;
      target.classList.remove('flash');
      void target.offsetWidth;
      target.classList.add('flash');
    }
    window.addEventListener('hashchange', flashFromHash);
    flashFromHash();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
