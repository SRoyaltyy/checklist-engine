// ==UserScript==
// @name         Venice Bridge Loader
// @namespace    venice.local
// @version      1.2
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

  function stopOld() {
    try { if (window.__vrb && window.__vrb.stop) window.__vrb.stop(); } catch (e) {}
    window.__vrb = null;
  }

  function boot(src) {
    stopOld();
    try {
      new Function('GM_xmlhttpRequest', src)(GM_xmlhttpRequest);
      console.log('[loader] bridge started');
      return true;
    } catch (e) { console.log('[loader] eval failed', e); return false; }
  }

  function refresh() {
    get('agent/BRIDGE_VERSION.json').then(function (raw) {
      var v = '';
      try { v = JSON.parse(unwrap(raw)).sha || ''; } catch (e) {}
      if (!v || v === GM_getValue(VER, '')) return;
      get('agent/BRIDGE.user.js').then(function (raw) {
        var src = unwrap(raw);
        if (!src || src.length < 500) return;
        if (boot(src)) { GM_setValue(KEY, src); GM_setValue(VER, v); }
      });
    });
  }

  get('agent/BRIDGE.user.js').then(function (raw) {
    var src = unwrap(raw);
    if (src && src.length > 500 && boot(src)) return;
    var last = GM_getValue(KEY, '');
    if (last) { console.log('[loader] using last good'); boot(last); }
  });

  setInterval(refresh, 60000);
}());
