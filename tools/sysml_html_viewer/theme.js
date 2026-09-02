/* DE4SDV viewer theme toggle: light (default) / dark (Carbon g100).
 * Choice persists in localStorage; ?theme=dark|light is a per-view URL
 * override that does NOT overwrite the saved choice.
 * The inline <head> script applies 'dark' before first paint; this file
 * only wires the toggle button and keeps body state in sync. */
(function () {
  'use strict';
  var KEY = 'de4sdv-viewer-theme';

  function isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  function apply() {
    // body-level hook for anything CSS cannot express via html attr alone
    document.body.classList.toggle('theme-dark', isDark());
    var btn = document.getElementById('themeToggle');
    if (btn) {
      btn.setAttribute('aria-pressed', isDark() ? 'true' : 'false');
    }
  }

  function toggle() {
    if (isDark()) {
      document.documentElement.removeAttribute('data-theme');
      try { localStorage.setItem(KEY, 'light'); } catch (e) { /* file:// */ }
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
      try { localStorage.setItem(KEY, 'dark'); } catch (e) { /* file:// */ }
    }
    apply();
  }

  function init() {
    var btn = document.getElementById('themeToggle');
    if (!btn || btn.dataset.themeBound) return;   // idempotent re-init
    btn.dataset.themeBound = '1';
    btn.addEventListener('click', toggle);
    apply();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // programmatic/test hook
  window.__de4sdvToggleTheme = toggle;
  window.__de4sdvIsDark = isDark;
})();
