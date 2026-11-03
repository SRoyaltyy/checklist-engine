// ==UserScript==
// @name         Venice Repo Bridge
// @namespace    venice.local
// @version      4.1
// @match       https://venice.ai/*
// @grant       GM_xmlhttpRequest
// @connect     venice-doorman.fullscan-relay.workers.dev
// @run-at      document-idle
// ==/UserScript==

(function () {
  'use strict';
  var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
  var BR = 'venice%2Fsec-options-pipelines';
  var REPO = 'SRoyaltyy/checklist-engine';
  var POLL = 30000, COOL = 240000, FAIL_LIMIT = 2, STUCK_MS = 150000, BOOT_MAX = 2;
  var READS = ['agent/BRIEF.md', 'agent/STANDING_ORDERS.md', 'agent/QUEUE.jsonl', 'agent/STATE.md', 'agent/PROGRESS.md', 'agent/JOURNAL.md', 'agent/TEST_LOG.txt', 'agent/GANTT_ROWS.md', 'agent/WAKE.json'];
  var BOOT_READS = ['agent/PROGRESS.md', 'agent/JOURNAL.md', 'agent/STATE.md', 'agent/QUEUE.jsonl', 'agent/GANTT_ROWS.md', 'agent/DOORMAN.worker.js', 'agent/DEPLOYER.worker.js'];
  var busy = false, sent = 0, phase = 'work', bootTries = 0, awaiting = 0, nodesAt = 0;

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function num(k) { return Number(load(k) || 0); }

  function gm(url) {
    return new Promise(function (res) {
      GM_xmlhttpRequest({ method: 'GET', url: url, timeout: 25000,
        onload: function (r) { res({ ok: r.status >= 200 && r.status < 300, status: r.status, text: r.responseText || '' }); },
        onerror: function () { res({ ok: false, status: 0, text: '' }); },
        ontimeout: function () { res({ ok: false, status: 0, text: '' }); } });
    });
  }

  function gmPost(url, body) {
    return new Promise(function (res) {
      GM_xmlhttpRequest({ method: 'POST', url: url, data: body, timeout: 60000,
        headers: { 'Content-Type': 'text/plain' },
        onload: function (r) { res({ ok: r.status >= 200 && r.status < 300, status: r.status, text: r.responseText || '' }); },
        onerror: function () { res({ ok: false, status: 0, text: '' }); },
        ontimeout: function () { res({ ok: false, status: 0, text: '' }); } });
    });
  }

  function readUrl(p) { return W + 'read&branch=' + BR + '&path=' + encodeURIComponent(p); }
  function putUrl(p) { return W + 'put&branch=' + BR + '&path=' + encodeURIComponent(p); }

  function unwrap(raw) {
    try { var o = JSON.parse(raw); if (o && typeof o.text === 'string') return o.text; } catch (e) {} 
    return raw;
  }

  function readback(path, content, status) {
    return gm(readUrl(path)).then(function (back) {
      var got = unwrap(back.text || '');
      var tol = Math.max(40, Math.floor(content.length * 0.01));
      var ok = back.ok && got.length > 0 && Math.abs(got.length - content.length) <= tol;
      console.log('[bridge] put ' path ' -> ' status ', readback ' got.length '/' content.length (ok ? ' OK' : ' MISMATCH'));
      return { ok: ok, status: status };
    });
  }
@@MORE@@