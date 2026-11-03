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

  function putFile(path, content) {
    if (!content) { console.log('[bridge] empty write to ' path); return Promise.resolve({ ok: false, status: -1 }); }
    return gmPost(putUrl(path), content).then(function (r) { return readback(path, content, r.status); });
  }

  function tail(s, n) { return s.length <= n ? s : '[...trimmed...]\n' + s.slice(-n); }

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
    var btns = Array.prototype.slice.call(document.querySelectorAll('button, [role="button"]'));
    var i, b;
    for (i = 0; i < btns.length; i++) { if (/send|submit/i.test(labelOf(btns[i]))) return btns[i]; }
    var attach = null;
    for (i = 0; i < btns.length; i++) { if (/attach/i.test(labelOf(btns[i]))) attach = btns[i]; }
    if (!attach || !attach.parentElement) return null;
    var sibs = Array.prototype.slice.call(attach.parentElement.querySelectorAll('button, [role="button"]'));
    var silent = [];
    for (i = 0; i < sibs.length; i++) { b = sibs[i]; if (b === attach || b.disabled) continue; if (labelOf(b) === '') silent.push(b); }
    if (silent.length) return silent[silent.length - 1];
    for (i = sibs.length - 1; i >= 0; i--) { b = sibs[i]; if (b !== attach && !b.disabled && !/attach|dictate|close/i.test(labelOf(b))) return b; }
    return null;
  }

  function valueOf(el) { return el.tagName === 'TEXTAREA' ? el.value : el.textContent; }

  function fill(el, text) {
    el.focus();
    if (el.tagName === 'TEXTAREA') {
      var setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
      setter.call(el, text);
    } else {
      var done = false;
      try {
        document.execCommand('selectAll', false, null);
        done = document.execCommand('insertText', false, text);
      } catch (e) { done = false; }
      if (!done || valueOf(el).length < text.length * 0.8) el.textContent = text;
    }
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }
@@MORE@@