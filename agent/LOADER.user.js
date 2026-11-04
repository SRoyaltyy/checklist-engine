// ==UserScript==
// @name         Venice Bridge Loader
// @namespace    venice.local
// @version      1.6
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
  var KEY = 'vrb.lastgood', VER = 'vrb.version', BAD = 'vrb.bad';
  var SETTLE_MS = 120000;

  var mine = document.createElement('div');
  mine.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483646;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#9e6a03;cursor:default;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9;';
  mine.textContent = 'LOAD v1.6';
  function say(t, bg) { mine.textContent = t; mine.style.background = bg; }
  function show() { if (!mine.parentElement && document.body) document.body.appendChild(mine); }
  function hide() { if (mine.parentElement) mine.remove(); }

  function hash(s) {
    var h = 5381, i;
    s = String(s);
    for (i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0;
    return h.toString(36) + '.' + s.length.toString(36);
  }

  function get(p) {
    return new Promise(function (res) {
      GM_xmlhttpRequest({ method: 'GET', timeout: 20000,
        url: W + 'read&branch=' + BR + '&path=' + encodeURIComponent(p) + '&t=' + Date.now(),
        onload: function (r) { res(r.status >= 200 && r.status < 300 ? r.responseText : ''); },
        onerror: function () { res(''); },
        ontimeout: function () { res(''); } });
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

  function badList() {
    try { return JSON.parse(GM_getValue(BAD, '[]')) || []; } catch (e) { return []; }
  }
  function markBad(v) {
    if (!v) return;
    var l = badList();
    if (l.indexOf(v) === -1) l.push(v);
    GM_setValue(BAD, JSON.stringify(l.slice(-20)));
  }

  var settleTimer = null;
  function cancelSettle() { if (settleTimer) { clearTimeout(settleTimer); settleTimer = null; } }

  function healthy() {
    return !!(window.__vrb && window.__vrb.stop);
  }

  function boot(rawSrc, tag, version, retry) {
    var src = sanitize(rawSrc);
    if (version && badList().indexOf(version) !== -1) {
      say('SKIP BAD ' + version, '#9e6a03');
      return false;
    }
    stopOld();
    cancelSettle();
    try {
      new Function('GM_xmlhttpRequest', src)(GM_xmlhttpRequest);
    } catch (e) {
      say('EVAL FAIL', '#d1242f');
      console.log('[loader] eval failed', e);
      markBad(version);
      return false;
    }
    say('LOADED ' + (tag || ''), '#238636');
    settleTimer = setTimeout(function () {
      if (healthy()) { hide(); return; }
      if (!retry) {
        say('UNHEALTHY, RETRY', '#9e6a03');
        console.log('[loader] build ' + (version || tag) + ' unhealthy, one retry');
        boot(src, tag, version, true);
        return;
      }
      say('UNHEALTHY, ROLLBACK', '#d1242f');
      console.log('[loader] build ' + (version || tag) + ' unhealthy twice, rolling back');
      markBad(version);
      var last = GM_getValue(KEY, '');
      if (last) boot(last, 'lastgood', '');
      else say('NO FALLBACK', '#d1242f');
    }, SETTLE_MS);
    console.log('[loader] bridge started');
    return true;
  }

  function adopt(src, tag) {
    var v = hash(src);
    if (v === GM_getValue(VER, '')) return false;
    if (badList().indexOf(v) !== -1) { say('SKIP BAD', '#9e6a03'); return false; }
    if (boot(src, tag, v)) { GM_setValue(KEY, src); GM_setValue(VER, v); return true; }
    return false;
  }

  function refresh() {
    get('agent/BRIDGE.user.js').then(function (raw) {
      var src = unwrap(raw);
      if (!src || src.length < 500) return;
      adopt(src, hash(src));
    });
  }

  show();
  get('agent/BRIDGE.user.js').then(function (raw) {
    var src = unwrap(raw);
    if (src && src.length > 500 && adopt(src, 'init')) return;
    var last = GM_getValue(KEY, '');
    if (last) { console.log('[loader] using last good'); boot(last, 'cached', ''); return; }
    say('NO SOURCE', '#d1242f');
  });

  setInterval(refresh, 60000);
}());
