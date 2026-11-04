Copy code
// ==UserScript==
// @name         Venice Repo Bridge
// @namespace    venice.local
// @version      4.9
// @match        https://venice.ai/*
// @grant        GM_xmlhttpRequest
// @connect      venice-doorman.fullscan-relay.workers.dev
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';
  if (load('vrb.v') === null) store('vrb.v', '0');
  var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
  var BR = 'venice%2Fsec-options-pipelines';
  var REPO = 'SRoyaltyy/checklist-engine';
  var FENCE = String.fromCharCode(96, 96, 96);
  var POLL = 30000, COOL = 240000, DEAD_LIMIT = 3, STUCK_MS = 300000, BOOT_MAX = 2, ESC_COOL = 90000, SCRAPE_MAX = 12000;
  var RETRY_MS = 15000, RETRY_MAX = 12;
  var READS = ['agent/CONTEXT.md', 'agent/PROTOCOL.md', 'agent/STATE.md', 'agent/PROGRESS.md', 'agent/MEMORY.md', 'agent/JOURNAL.md', 'agent/FETCH.md', 'agent/WAKE.json'];
  var COMPACT_READS = ['agent/COMPACT.md', 'agent/STATE.md', 'agent/PROGRESS.md', 'agent/QUEUE.jsonl', 'agent/WAKE_PROMPT.md'];
  var BUDGET = 120000;
  var BOOT_READS = ['agent/CONTEXT.md', 'agent/PROTOCOL.md', 'agent/STATE.md', 'agent/PROGRESS.md', 'agent/MEMORY.md', 'agent/COMPACT.md'];
  var busy = false, busyTicks = 0, sent = 0, phase = 'work', bootTries = 0, awaiting = 0, nodesAt = 0, dead = 0, failsAtSubmit = 0;
  var parked = null, parkedTries = 0;

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function num(k) { return Number(load(k) || 0); }
  function str(v) { return v == null ? '' : (typeof v === 'string' ? v : String(v)); }

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
      GM_xmlhttpRequest({ method: 'POST', url: url, data: str(body), timeout: 60000,
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
    return str(raw);
  }

  function readback(path, content, status) {
    content = str(content);
    return gm(readUrl(path)).then(function (back) {
      var got = unwrap(back.text || '');
      var tol = Math.max(40, Math.floor(content.length * 0.01));
      var ok = back.ok && got.length > 0 && Math.abs(got.length - content.length) <= tol;
      console.log('[bridge] put ' + path + ' -> ' + status + ', readback ' + got.length + '/' + content.length + (ok ? ' OK' : ' MISMATCH'));
      return { ok: ok, status: status };
    }).catch(function (e) {
      console.log('[bridge] readback threw for ' + path + ': ' + e);
      return { ok: false, status: status };
    });
  }

  function putFile(path, content) {
    content = str(content);
    if (!content) { console.log('[bridge] empty write to ' + path); return Promise.resolve({ ok: false, status: -1 }); }
    return gmPost(putUrl(path), content).then(function (r) { return readback(path, content, r.status); });
  }

  function tail(s, n) { s = str(s); return s.length <= n ? s : '[...trimmed...]\n' + s.slice(-n); }

  function headTail(s, n) {
    s = str(s);
    if (s.length <= n) return s;
    var half = Math.floor(n / 2);
    return s.slice(0, half) + '\n\n[... ' + (s.length - n) + ' chars trimmed ...]\n\n' + s.slice(-half);
  }

  function labelOf(el) {
    return ((el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + (el.getAttribute('data-testid') || '')).trim();
  }

  function composer() {
    var list = Array.prototype.slice.call(document.querySelectorAll('textarea, [contenteditable="true"], div[role="textbox"]'));
    var i;
    for (i = 0; i < list.length; i++) { if (list[i].offsetParent === null) continue; if (/message|chat|ask/i.test(labelOf(list[i]))) return list[i]; }
    for (i = list.length - 1; i >= 0; i--) { if (list[i].offsetParent !== null) return list[i]; }
    return null;
  }

  function sendButton() {
    var btns = Array.prototype.slice.call(document.querySelectorAll('button, [role
Ask anything privately...

Agent

Sub-agent
wakeg15| 24 v45
