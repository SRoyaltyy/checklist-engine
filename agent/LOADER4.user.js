// ==UserScript==
// @name Venice Bridge Loader
// @namespace venice.local
// @version 1.11
// @match https://venice.ai/*
// @grant GM_xmlhttpRequest
// @grant GM_setValue
// @grant GM_getValue
// @connect venice-doorman.fullscan-relay.workers.dev
// @updateURL https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice/sec-options-pipelines/agent/LOADER4.user.js
// @downloadURL https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice/sec-options-pipelines/agent/LOADER4.user.js
// @run-at document-idle
// ==/UserScript==

(function () {
'use strict';
var W = 'https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=';
var BR = 'venice%2Fsec-options-pipelines';
var KEY = 'vrb.lastgood', VER = 'vrb.version', BAD = 'vrb.bad';
var SETTLE_MS = 120000;

var mine = document.createElement('div');
mine.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483646;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#9e6a03;cursor:default;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9;';
mine.textContent = 'LOAD v1.11';
function say(t, bg) { mine.textContent = t; mine.style.background = bg; }
function show() { if (!mine.parentElement && document.body) document.body.appendChild(mine); }
function hide() { if (mine.parentElement) mine.remove(); }

// liveness probe: the bridge announces itself on the console. A build that
// says nothing for a full settle window is dead. A build that talks is alive
// whether or not it ever publishes window.__vrb.
var lastAct = 0;
function probe(name) {
var orig = console[name];
console[name] = function () {
try { var a = arguments[0]; if (typeof a === 'string' && a.indexOf('[bridge]') === 0) lastAct = Date.now(); } catch (e) {}
return orig.apply(console, arguments);
};
}
probe('log'); probe('warn'); probe('error');

function hash(s) { var h = 5381, i; s = String(s); for (i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h.toString(36) + '.' + s.length.toString(36); }

// self-contained one-shot directive filter, injected into the bridge.
// Backslashes are doubled so they survive this string and reach the bridge as
// \n and \b rather than as a real newline and a backspace character.
// Wrapped in try/catch: if it ever throws, the plain slice is returned so the
// scan still works and the bridge is not rolled back for a filter bug.
var FILTER = "(function(){var raw=(document.body.innerText||'').slice(-20000);try{var S=window.__vrbSeen||(window.__vrbSeen={});var L=raw.split('\n');var n=0,i,s,h,j,k;for(i=0;i<L.length;i++){s=L[i].trim();if(!/^@@(PUT|SCRAPE|RUNS|DISPATCH|MERGE|SELF)\b/.test(s))continue;h=0;for(j=0;j<s.length;j++)h=((h*33)^s.charCodeAt(j))>>>0;k=h+'.'+s.length;if(S[k]){L[i]='';}else{S[k]=1;n++;}}if(n>500){var c=0;for(k in S){if(++c>500)delete S[k];}}return L.join('\n');}catch(e){return raw;}})()";

function patch(src) {
var out = String(src), n = 0;
if (out.indexOf("wake(reason || 'heartbeat', false)") !== -1) { out = out.replace("wake(reason || 'heartbeat', false)", "wake(reason || 'heartbeat', true)"); n++; }
if (out.indexOf('@version 5.1') !== -1) { out = out.replace('@version 5.1', '@version 5.4'); n++; }
if (out.indexOf("var text = (document.body.innerText || '').slice(-20000)") !== -1) { out = out.replace("var text = (document.body.innerText || '').slice(-20000)", "var text = " + FILTER); n++; }
else if (out.indexOf("var text = document.body.innerText || ''") !== -1) { out = out.replace("var text = document.body.innerText || ''", "var text = " + FILTER); n++; }
if (n) console.log('[loader] patched ' + n + ' spot(s)');
if (out.indexOf('__vrbSeen') === -1) console.log('[loader] WARN scan filter did not take');
return out;
}

function get(p) { return new Promise(function (res) { GM_xmlhttpRequest({ method: 'GET', timeout: 20000, url: W + 'read&branch=' + BR + '&path=' + encodeURIComponent(p) + '&t=' + Date.now(), onload: function (r) { res(r.status >= 200 && r.status < 300 ? r.responseText : ''); }, onerror: function () { res(''); }, ontimeout: function () { res(''); } }); }); }
function unwrap(raw) { try { var o = JSON.parse(raw); if (o && typeof o.text === 'string') return o.text; } catch (e) {} return raw; }
function sanitize(src) { return String(src).replace(/^\sCopy code\s$/gm, '').replace(/^\sCopied\s$/gm, '').replace(/^\s*```[a-z0-9+#._-]\s$/gmi, ''); }

function stopOld() { try { if (window.__vrb && window.__vrb.stop) window.__vrb.stop(); } catch (e) {} window.__vrb = null; }
function badList() { try { return JSON.parse(GM_getValue(BAD, '[]')) || []; } catch (e) { return []; } }
function markBad(v) { if (!v) return; var l = badList(); if (l.indexOf(v) === -1) l.push(v); GM_setValue(BAD, JSON.stringify(l.slice(-20))); }

var settleTimer = null, bootSeq = 0;
function cancelSettle() { if (settleTimer) { clearTimeout(settleTimer); settleTimer = null; } }

// healthy = the bridge published a real stop handle, OR it has said something
// since this boot started. A sentinel we install ourselves does not count.
function healthy(t0) {
if (window.__vrb && window.__vrb.stop && !window.__vrb.sentinel) return true;
return lastAct > t0;
}

function boot(rawSrc, tag, version, retry) {
var src = patch(sanitize(rawSrc));
if (version && badList().indexOf(version) !== -1) { say('SKIP BAD ' + version, '#9e6a03'); return false; }
stopOld();
cancelSettle();
var seq = ++bootSeq, t0 = Date.now();
try { new Function('GM_xmlhttpRequest', src)(GM_xmlhttpRequest); }
catch (e) { say('EVAL FAIL', '#d1242f'); console.log('[loader] eval failed', e); markBad(version); return false; }
if (!window.__vrb || !window.__vrb.stop) window.__vrb = { stop: function () {}, sentinel: true };
say('LOADED ' + (tag || ''), '#238636');
settleTimer = setTimeout(function () {
if (seq !== bootSeq) return;
if (healthy(t0)) { hide(); return; }
if (!retry) { say('UNHEALTHY, RETRY', '#9e6a03'); console.log('[loader] build ' + (version || tag) + ' silent, one retry'); boot(rawSrc, tag, version, true); return; }
say('UNHEALTHY, ROLLBACK', '#d1242f');
console.log('[loader] build ' + (version || tag) + ' silent twice, rolling back');
markBad(version);
var last = GM_getValue(KEY, '');
if (last) boot(last, 'lastgood', ''); else say('NO FALLBACK', '#d1242f');
}, SETTLE_MS);
console.log('[loader] bridge started');
return true;
}

function adopt(src, tag) {
var v = hash(patch(src));
if (v === GM_getValue(VER, '')) return false;
if (badList().indexOf(v) !== -1) { say('SKIP BAD', '#9e6a03'); return false; }
if (boot(src, tag, v)) { GM_setValue(KEY, src); GM_setValue(VER, v); return true; }
return false;
}

function refresh() { get('agent/BRIDGE.user.js').then(function (raw) { var src = unwrap(raw); if (!src || src.length < 500) return; adopt(src, hash(patch(src))); }); }

show();
get('agent/BRIDGE.user.js').then(function (raw) {
var src = unwrap(raw);
if (src && src.length > 500 && adopt(src, 'init')) return;
var last = GM_getValue(KEY, '');
if (last) { console.log('[loader] using last good'); boot(last, 'cached', ''); return; }
say('NO SOURCE', '#d1242f');
});

setInterval(refresh, 60000);
})();
