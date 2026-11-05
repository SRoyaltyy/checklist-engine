// ==UserScript==
// @name Venice Bridge Loader
// @namespace venice.local
// @version 1.12
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
var bootSeq = 0, settleTimer = 0;

var mine = document.createElement('div');
mine.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:2147483646;padding:7px 11px;border-radius:8px;font:12px ui-monospace,monospace;color:#fff;background:#9e6a03;cursor:default;box-shadow:0 2px 10px rgba(0,0,0,.45);opacity:.9;';
mine.textContent = 'LOAD v1.12';
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

function healthy(t0) { return lastAct > t0; }

function hash(s) { var h = 5381, i; s = String(s); for (i = 0; i < s.length; i++) { h = ((h << 5) + h + s.charCodeAt(i)) >>> 0; } return h.toString(36) + '.' + s.length.toString(36); }

function badList() { try { var v = GM_getValue(BAD, ''); return v ? String(v).split(',') : []; } catch (e) { return []; } }
function markBad(v) { if (!v) return; try { var l = badList(); if (l.indexOf(v) === -1) { l.push(v); GM_setValue(BAD, l.join(',')); } } catch (e) {} }

function stopOld() { try { if (window.__vrb && window.__vrb.stop) window.__vrb.stop(); } catch (e) {} }
function cancelSettle() { if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; } }

// self-contained one-shot directive filter, injected into the bridge.
// Backslashes are doubled so they survive this string and reach the bridge as
// \n and \s rather than as a real newline and a literal s.
// Wrapped in try/catch: if it ever throws, the plain slice is returned so the
// scan still works and the bridge is not rolled back for a filter bug.
var FILTER = "(function(){var raw=(document.body.innerText||'').slice(-20000);try{var S=window.__vrbSeen||(window.__vrbSeen={});var L=raw.split('\n');var n=0,i,s,t,x,j,k;for(i=0;i<L.length;i++){s=L[i];if(s.indexOf('@@')===-1)continue;t=s.replace(/\s+$/,'');x=5381;for(j=0;j<t.length;j++){x=((x<<5)+x+t.charCodeAt(j))>>>0;}k=x.toString(36)+'.'+t.length;if(S[k]){L[i]='';}else{S[k]=1;n++;}}if(n>500){var c=0;for(k in S){if(++c>500)delete S[k];}}return L.join('\n');}catch(e){return raw;}})()";

function patch(src) {
var out = String(src), n = 0;
// 1.12: force is now false. The bridge short-circuits its 240s cooldown on a
// forced wake, so forcing every heartbeat made every 30s scan submit a wake.
if (out.indexOf("wake(reason || 'heartbeat', false)") !== -1) { out = out.replace("wake(reason || 'heartbeat', false)", "wake(reason || 'heartbeat', false)"); n++; }
if (out.indexOf('@version 5.1') !== -1) { out = out.replace('@version 5.1', '@version 5.4'); n++; }
if (out.indexOf("var text = (document.body.innerText || '').slice(-20000)") !== -1) { out = out.replace("var text = (document.body.innerText || '').slice(-20000)", "var text = " + FILTER); n++; }
else if (out.indexOf("var text = document.body.innerText || ''") !== -1) { out = out.replace("var text = document.body.innerText || ''", "var text = " + FILTER); n++; }
if (n) console.log('[loader] patched ' + n + ' spot(s)');
if (out.indexOf('__vrbSeen') === -1) console.log('[loader] WARN scan filter did not take');
return out;
}

function get(p) {
return new Promise(function (res) {
GM_xmlhttpRequest({
method: 'GET', timeout: 20000,
url: W + 'read&branch=' + BR + '&path=' + encodeURIComponent(p) + '&t=' + Date.now(),
onload: function (r) { res(r.status >= 200 && r.status < 300 ? r.responseText : ''); },
onerror: function () { res(''); },
ontimeout: function () { res(''); }
});
});
}

function unwrap(raw) {
var s = String(raw || '');
try { var o = JSON.parse(s); if (o && typeof o.text === 'string') return o.text; if (o && typeof o.content === 'string') return o.content; } catch (e) {}
return s;
}

function sanitize(src) {
return String(src).replace(/^\sCopy code\s$/gm, '').replace(/^```[a-zA-Z]\s$/gm, '');
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

function refresh() {
get('agent/BRIDGE.user.js').then(function (raw) {
var src = unwrap(raw);
if (!src || src.length < 500) { console.log('[loader] empty bridge fetch'); }
else if (adopt(src, 'init')) return;
var last = GM_getValue(KEY, '');
if (last) { console.log('[loader] using last good'); boot(last, 'cached', ''); return; }
say('NO SOURCE', '#d1242f');
});
}

show();
refresh();
setInterval(refresh, 60000);
})();
