// ==UserScript==
// @name         Venice Bridge Loader
// @namespace    venice.local
// @version      1.4
// @match        https://venice.ai/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      venice-doorman.fullscan-relay.workers.dev
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';
  var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
  var BR = 'venice%2Fsec-options-pipelines';
  var KEY = 'vrb.lastgood', VER = 'vrb.version';

  var mine = document.createElement('div');
  mine.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483646;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#9e6a03;cursor:default;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9';
  mine.textContent = 'LOAD v1.4';
  function say(t, bg) { mine.textContent = t; mine.style.background = bg; }
  function show() { if (!mine.parentElement && document.body) document.body.appendChild(mine); }
  function hide() { if (mine.parentElement) mine.remove(); }

  function get(p) {
    return new Promise(function (res) {
      GM_xmlhttpRequest({ method: 'GET', timeout: 20000,
        url: W + 'read&branch=' + BR + '&path=' + encodeURIComponent(p),
        onload: function (r) { res(r.status >= 200 && r.status < 300 ? r.responseText : ''); },
        onerror: function () { res(''); }, ontimeout: function () { res(''); } });
    });
  }

  function unwrap(raw) {
    try { var o = JSON.parse(raw); if (o && typeof o.text === 'string') return o.text; } catch (e) {}
    return raw;
  }

  function sanitize(src) {
    return String(src)
      .replace(/^\s*Copy code\s*$/gm, '')
      .replace(/^\s*Copied\s*$/gm, '')
      .replace(/^\s*```[a-z0-9+#._-]*\s*$/gmi, '');
  }

  function stopOld() {
    try { if (window.__vrb && window.__vrb.stop) window.__vrb.stop(); } catch (e) {}
    window.__vrb = null;
  }

  function boot(rawSrc, tag) {
    var src = sanitize(rawSrc);
    stopOld();
    try {
      new Function('GM_xmlhttpRequest', src)(GM_xmlhttpRequest);
      say('LOADED ' + (tag || ''), '#238636');
      setTimeout(function () {
        if (window.__vrb && window.__vrb.stop) hide();
        else say('NO BRIDGE UI', '#d1242f');
      }, 1500);
      console.log('[loader] bridge started');
      return true;
    } catch (e) {
      say('EVAL FAIL', '#d1242f');
      console.log('[loader] eval failed', e);
      return false;
    }
  }

  function refresh() {
    get('agent/BRIDGE_VERSION.json').then(function (raw) {
      var v = '';
      try { v = JSON.parse(unwrap(raw)).sha || ''; } catch (e) {}
      if (!v || v === GM_getValue(VER, '')) return;
      get('agent/BRIDGE.user.js').then(function (raw) {
        var src = unwrap(raw);
        if (!src || src.length < 500) return;
        if (boot(src, v)) { GM_setValue(KEY, src); GM_setValue(VER, v); }
      });
    });
  }

  show();
  get('agent/BRIDGE.user.js').then(function (raw) {
    var src = unwrap(raw);
    if (src && src.length > 500 && boot(src, 'init')) return;
    var last = GM_getValue(KEY, '');
    if (last) { console.log('[loader] using last good'); boot(last, 'cached'); return; }
    say('NO SOURCE', '#d1242f');
  });

  setInterval(refresh, 60000);
}());
