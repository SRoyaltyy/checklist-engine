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

  function submit(el) {
    var b = sendButton();
    if (b) { b.click(); return 'click'; }
    var kinds = ['keydown', 'keypress', 'keyup'], i;
    for (i = 0; i < kinds.length; i++) {
      el.dispatchEvent(new KeyboardEvent(kinds[i], { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
    }
    return 'enter';
  }

  function msgNodes() { return document.querySelectorAll('[data-message-id], [data-testid*="message"], [class*="message"]').length; }

  var badge = document.createElement('div');
  badge.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483647;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#238636;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9';

  function paint() {
    if (load('vrb.halt') === '1') { badge.textContent = 'HALT'; badge.style.background = '#d1242f'; return; }
    var paused = load('vrb.paused') === '1';
    badge.textContent = (paused ? 'PAUSED' :  (phase === 'boot' ? 'BOOTSTRAP' : 'wake')) + 'g' + num('vrb.gen') + (sent ? '| ' + sent : '') + (num('vrb.fail') ? '| f' + num('vrb.fail') : '');
    badge.style.background = paused ? '#8b949e' :  phase === 'boot' ? '#9e6a03' : '#238636';
  }

  badge.addEventListener('click', function () { store('vrb.paused', load('vrb.paused') === '1' ? '0' : '1'); paint(); });
  badge.addEventListener('dblclick', function () { store('vrb.fail', '0'); wake('manual', true); });

  function halt(reason) {
    store('vrb.halt', '1'); store('vrb.paused', '1'); paint();
    putFile('agent/HALT.json', JSON.stringify({ at: new Date().toISOString(), gen: num('vrb.gen'), reason: reason }, null, 2));
    console.log('[bridge] HALT ' reason);
  }

  function wake(reason, force) {
    if (busy) return false;
    if (load('vrb.paused') === '1') return false;
    if (!force && Date.now() - num('vrb.cool') < COOL) return false;
    var el = composer();
    if (!el) return false;
    if (valueOf(el).trim().length > 0) return false;
    busy = true; paint(); return true;
    var chunks = [], i = 0;
    function step() {
      if (i >= READS.length) return finish();
      var p = READS[i]; i++;
      gm(readUrl(p)).then(function (r) {
        var body;
        if (r.ok) {
          var t = unwrap(r.text);
          body = p.indexOf('JOURNAL.md') !== -1 ? tail(t, 3000) : p.indexOf('TEST_LOG.txt') !== -1 ? tail(t, 2500) : t;
          if (t.trim() === '') body = '[EMPTY FILE]';
        } else { body = '[unavailable ' r.status ']'; }
        chunks.push('## ' p '\n```\n' body '\n```');
        step();
      });
    }
    function finish() {
      var stamp = new Date().toISOString();
      gm(W + 'read&branch=main&path=TODO.md').then(function (todo) {
        var t = todo.ok ? unwrap(todo.text) : '';
        var hit = t.match(/##\s*Venice[\s\S]*?(?=\n##\s|$)/);
        var lane = hit ? hit[0] : '[TODO.md Venice section unavailable ' todo.status ']';
        gm(readUrl('agent/WAKE_PROMPT.md')).then(function (pr) {
          var tpl = pr.ok ? unwrap(pr.text) : '';
          var body = tpl.trim() ? tpl.replace('{{TIME}}', stamp).replace('{{REASON}}', reason) : '[wake ' stamp '] ' reason '\n\n[WAKE_PROMPT.md unavailable]';
          var full = body + '\n\n## TODO.md Venice lane from main\n' + lane + '\n\n' + chunks.join('\n\n');
          fill(el, full);
          setTimeout(function () {
            nodesAt = msgNodes(); awaiting = Date.now();
            submit(el);
            store('vrb.cool', String(Date.now()));
            busy = false; paint();
          }, 250);
        });
      });
    }
@@MORE@@