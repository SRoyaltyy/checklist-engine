// ==UserScript==
// @name         Venice Repo Bridge
// @namespace    venice.local
// @version     4.1
// @match       https://venice.ai/*
// @grant       GM_xmlhttpRequest
// @connect     venice-doorman.fullscan-relay.workers.dev
// @run-at      document-idle
// ==/UserScript==

(function () {
  'use strict';
  var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
  var BR = 'venice%2Fcalendar-announce-ledger';
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
      console.log('[bridge] put ' + path + ' -> ' + status + ', readback ' + got.length + '/' + content.length + (ok ? ' OK' : ' MISMATCH'));
      return { ok: ok, status: status };
    });
  }

  function putFile(path, content) {
    if (!content) { console.log('[bridge] empty write to ' + path); return Promise.resolve({ ok: false, status: -1 }); }
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
    } else { el.textContent = text; }
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
    badge.textContent = (paused ? 'PAUSED' : (phase === 'boot' ? 'BOOTSTRAP' : 'wake')) + ' g' + num('vrb.gen') + (sent ? ' | ' + sent : '') + (num('vrb.fail') ? ' | f' + num('vrb.fail') : '');
    badge.style.background = paused ? '#8b949e' : phase === 'boot' ? '#9e6a03' : '#238636';
  }

  badge.addEventListener('click', function () { store('vrb.paused', load('vrb.paused') === '1' ? '0' : '1'); paint(); });
  badge.addEventListener('dblclick', function () { store('vrb.fail', '0'); wake('manual', true); });

  function halt(reason) {
    store('vrb.halt', '1'); store('vrb.paused', '1'); paint();
    putFile('agent/HALT.json', JSON.stringify({ at: new Date().toISOString(), gen: num('vrb.gen'), reason: reason }, null, 2));
    console.log('[bridge] HALT ' + reason);
  }

  function wake(reason, force) {
    if (busy) return;
    if (load('vrb.paused') === '1') return;
    if (!force && Date.now() - num('vrb.cool') < COOL) return;
    var el = composer();
    if (!el) return;
    if (valueOf(el).trim().length > 0) return;
    busy = true; paint();
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
        } else { body = '[unavailable ' + r.status + ']'; }
        chunks.push('## ' + p + '\n```\n' + body + '\n```');
        step();
      });
    }
    function finish() {
      var stamp = new Date().toISOString();
      gm(W + 'read&branch=main&path=TODO.md').then(function (todo) {
        var t = todo.ok ? unwrap(todo.text) : '';
        var hit = t.match(/##\s*Venice[\s\S]*?(?=\n##\s|$)/);
        var lane = hit ? hit[0] : '[TODO.md Venice section unavailable ' + todo.status + ']';
        gm(readUrl('agent/WAKE_PROMPT.md')).then(function (pr) {
          var tpl = pr.ok ? unwrap(pr.text) : '';
          var body = tpl.trim() ? tpl.replace('{{TIME}}', stamp).replace('{{REASON}}', reason) : '[wake ' + stamp + '] ' + reason + '\n\n[WAKE_PROMPT.md unavailable]';
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

  function waitFor(fn, ms) {
    return new Promise(function (res) {
      var t0 = Date.now();
      (function poll() {
        if (fn()) return res(true);
        if (Date.now() - t0 > ms) return res(false);
        setTimeout(poll, 500);
      }());
    });
  }

  function clickNewChat() {
    var els = Array.prototype.slice.call(document.querySelectorAll('button, [role="button"], a'));
    var i;
    for (i = 0; i < els.length; i++) {
      if (els[i].offsetParent === null) continue;
      if (/new chat|new conversation|start new/i.test(labelOf(els[i]))) { els[i].click(); return true; }
    }
    location.href = location.origin + '/';
    return false;
  }

  function ensureAgentic() {
    var els = Array.prototype.slice.call(document.querySelectorAll('[aria-label], [title], [data-testid]'));
    var i, e;
    for (i = 0; i < els.length; i++) {
      e = els[i];
      if (e.offsetParent === null) continue;
      if (!/agent/i.test(labelOf(e))) continue;
      if (e.getAttribute('aria-checked') === 'true' || e.getAttribute('aria-pressed') === 'true') return 'on';
      if (e.getAttribute('aria-checked') === 'false' || e.getAttribute('aria-pressed') === 'false') { e.click(); return 'toggled'; }
    }
    return 'unknown';
  }

  function composeBootstrap(gen) {
    var chunks = [], i = 0;
    function step() {
      if (i >= BOOT_READS.length) return finish();
      var p = BOOT_READS[i]; i++;
      gm(readUrl(p)).then(function (r) {
        var body = r.ok ? unwrap(r.text) : '[unavailable ' + r.status + ']';
        if (r.ok && body.trim() === '') body = '[EMPTY FILE]';
        chunks.push('## ' + p + '\n```\n' + body + '\n```');
        step();
      });
    }
    function finish() {
      var links = [
        '[bootstrap gen ' + gen + ' ' + new Date().toISOString() + ']',
        'The previous chat hit the context ceiling. This chat continues it. Do not reconcile; state below is authoritative.',
        '',
        'Repo: https://github.com/' + REPO,
        'Lane: https://github.com/' + REPO + '/blob/main/TODO.md',
        'Progress: https://github.com/' + REPO + '/blob/' + decodeURIComponent(BR) + '/agent/PROGRESS.md',
        '',
        chunks.join('\n\n'),
        '',
        'Read TODO.md Venice section from main, then PROGRESS.md. Do the first unticked item. Branch venice/*, PR to main, no markers. Journal and rewrite PROGRESS.md before stopping.'
      ];
      var el = composer();
      if (!el) { halt('no composer after new chat'); return; }
      fill(el, links.join('\n'));
      setTimeout(function () {
        nodesAt = msgNodes(); awaiting = Date.now();
        submit(el);
        console.log('[bridge] bootstrap submitted, gen ' + gen);
      }, 400);
    }
    step();
  }

  function escalate(reason) {
    if (phase === 'boot') {
      bootTries++;
      if (bootTries > BOOT_MAX) { halt('bootstrap failed ' + bootTries + 'x: ' + reason); return; }
    }
    phase = 'boot';
    busy = true;
    store('vrb.fail', '0');
    store('vrb.halt', '0');
    lastFailSeen = 0;
    var gen = num('vrb.gen') + 1;
    store('vrb.gen', String(gen));
    store('vrb.bootPending', String(gen));
    paint();
    console.log('[bridge] escalate -> gen ' + gen + ' (' + reason + ')');
    clickNewChat();
    waitFor(function () { return composer() !== null; }, 45000).then(function (ok) {
      if (!ok) { halt('composer never appeared'); return; }
      console.log('[bridge] agentic mode: ' + ensureAgentic());
      setTimeout(function () {
        var el = composer();
        if (!el) { halt('composer vanished'); return; }
        if (valueOf(el).trim().length > 0) { el.textContent = ''; }
        composeBootstrap(gen);
      }, 2500);
    });
  }

  var lastFailSeen = 0, failPrimed = false;

  function healthTick() {
    if (load('vrb.halt') === '1') return;
    var text = document.body.innerText || '';
    var hits = (text.match(/Response failed/gi) || []).length;
    if (!failPrimed) { lastFailSeen = hits; failPrimed = true; }
    if (hits > lastFailSeen) {
      store('vrb.fail', String(num('vrb.fail') + (hits - lastFailSeen)));
      lastFailSeen = hits;
      awaiting = 0;
      paint();
    }
    if (num('vrb.fail') >= FAIL_LIMIT && !busy) { escalate('response failed x' + num('vrb.fail')); return; }
    if (awaiting && Date.now() - awaiting > STUCK_MS) {
      if (msgNodes() <= nodesAt) {
        store('vrb.fail', String(num('vrb.fail') + 1));
        awaiting = 0; paint();
        if (num('vrb.fail') >= FAIL_LIMIT) escalate('stuck, no reply');
      } else { awaiting = 0; }
    }
    if (awaiting && msgNodes() > nodesAt) {
      awaiting = 0;
      if (phase === 'boot') {
        phase = 'work'; bootTries = 0; store('vrb.fail', '0'); paint();
        console.log('[bridge] bootstrap answered, resuming');
        setTimeout(function () { wake('post-bootstrap resume', true); }, 3000);
      } else if (num('vrb.fail')) { store('vrb.fail', '0'); paint(); }
    }
  }

  var fired = {};
  try { fired = JSON.parse(load('vrb.fired') || '{}'); } catch (e) { fired = {}; }

  function hash(s) {
    var h = 5381, i;
    for (i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
    return h.toString(36);
  }

  function mark(h) {
    fired[h] = 1;
    var keys = Object.keys(fired), i;
    if (keys.length > 2000) {
      var trimmed = {};
      for (i = keys.length - 2000; i < keys.length; i++) trimmed[keys[i]] = 1;
      fired = trimmed;
    }
    store('vrb.fired', JSON.stringify(fired));
  }

  var CHROME = /^(?:```[a-z0-9+#._-]*|yaml|yml|json|python|py|bash|sh|js|javascript|md|markdown|text|txt|Copy code|Copy|Copied)$/;

  function cleanBody(raw) {
    var lines = raw.replace(/\r/g, '').split('\n');
    var guard = 0;
    while (lines.length && guard++ < 12) {
      var head = lines[0].trim();
      if (head === '' || head.indexOf('@@BODY') === 0 || CHROME.test(head)) { lines.shift(); continue; }
      break;
    }
    guard = 0;
    while (lines.length && guard++ < 12) {
      var foot = lines[lines.length - 1].trim();
      if (foot === '' || CHROME.test(foot)) { lines.pop(); continue; }
      break;
    }
    return lines.join('\n').replace(/\s+$/, '') + '\n';
  }

  function doPut(path, raw) {
    var body = cleanBody(raw);
    var h = hash(path + body);
    if (fired[h]) return;
    mark(h);
    putFile(path, body).then(function () { sent++; paint(); });
  }

  function scan() {
    var text = document.body.innerText || '';
    var m;
    var strict = /@@PUT[ \t]+(\S+)[ \t]*\r?\n([\s\S]*?)\r?\n?@@END\b/g;
    var covered = {};
    while ((m = strict.exec(text)) !== null) {
      covered[hash(m[1] + cleanBody(m[2]))] = 1;
      doPut(m[1], m[2]);
    }
    var loose = /@@PUT[ \t]+(\S+)[ \t]*\r?\n([\s\S]*?)(?=\r?\n@@END|\r?\n@@PUT|\r?\n@@DISPATCH|\r?\n@@RUNS|\r?\n@@MERGE|\r?\n@@DEPLOY|$)/g;
    while ((m = loose.exec(text)) !== null) {
      var b2 = cleanBody(m[2]);
      if (covered[hash(m[1] + b2)]) continue;
      console.log('[bridge] UNTERMINATED @@PUT ' + m[1]);
      doPut(m[1], m[2]);
    }
    var dispRe = /@@DISPATCH[ \t]+(\S+)/g;
    while ((m = dispRe.exec(text)) !== null) {
      var hd = hash('d' + m[1] + m.index);
      if (fired[hd]) continue;
      mark(hd);
      (function (wf) {
        gm(W + 'dispatch&branch=' + BR + '&workflow=' + encodeURIComponent(wf)).then(function (r) {
          sent++; paint(); console.log('[bridge] dispatch ' + r.status);
        });
      }(m[1]));
    }
    var runsRe = /@@RUNS/g;
    while ((m = runsRe.exec(text)) !== null) {
      var hr = hash('r' + m.index);
      if (fired[hr]) continue;
      mark(hr);
      gm(W + 'runs&branch=' + BR).then(function (r) { sent++; paint(); console.log('[bridge] runs ' + r.status); });
    }
    var mergeRe = /@@MERGE[ \t]+(\d+)/g;
    while ((m = mergeRe.exec(text)) !== null) {
      var hm = hash('m' + m[1]);
      if (fired[hm]) continue;
      mark(hm);
      (function (n) {
        gm(W + 'merge&pr=' + n).then(function (r) { sent++; paint(); console.log('[bridge] merge ' + r.status); });
      }(m[1]));
    }
  }

  function tick() {
    if (load('vrb.paused') === '1' || load('vrb.halt') === '1' || phase === 'boot') return;
    gm(readUrl('agent/WAKE.json')).then(function (r) {
      if (!r.ok) return;
      var flag;
      try { flag = JSON.parse(unwrap(r.text)); } catch (e) { return; }
      var reason = (flag && flag.reason) || '';
      var sha = (reason.match(/[0-9a-f]{7,40}/) || [''])[0];
      if (sha && sha === load('vrb.sha')) return;
      wake(reason || 'heartbeat', false);
      if (sha) store('vrb.sha', sha);
    });
  }

  var timer = null;
  var observer = new MutationObserver(function () {
    clearTimeout(timer);
    timer = setTimeout(scan, 900);
  });
  observer.observe(document.body, { childList: true, subtree: true, characterData: true });

  var tickTimer = setInterval(tick, POLL);
  var healthTimer = setInterval(healthTick, 5000);

  window.__vrb = { stop: function () {
    clearInterval(tickTimer); clearInterval(healthTimer);
    clearTimeout(timer); observer.disconnect();
    if (badge.parentElement) badge.remove();
  } };

  gm(readUrl('agent/BRIDGE_GEN.json')).then(function (r) {
    if (!r.ok) return;
    try {
      var g = JSON.parse(unwrap(r.text)).gen;
      if (g && g > num('vrb.gen')) { store('vrb.gen', String(g)); paint(); }
    } catch (e) {}
  });

  document.body.appendChild(badge);
  paint();
  setTimeout(tick, 4000);
}());
