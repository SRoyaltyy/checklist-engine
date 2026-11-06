// ==UserScript==
// @name Venice Bridge Loader
// @namespace venice.local
// @version 2.0.0
// @match https://venice.ai/*
// @grant GM_xmlhttpRequest
// @grant GM_getValue
// @grant GM_setValue
// @grant GM_registerMenuCommand
// @connect venice-doorman.fullscan-relay.workers.dev
// @updateURL https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice/sec-options-pipelines/agent/LOADER6.user.js
// @downloadURL https://raw.githubusercontent.com/SRoyaltyy/checklist-engine/venice/sec-options-pipelines/agent/LOADER6.user.js
// @run-at document-idle
// ==/UserScript==
(function(){
  'use strict';
  const CONFIG={worker:'https://venice-doorman.fullscan-relay.workers.dev/',branch:'venice/sec-options-pipelines',key:GM_getValue('vrb6.key','')};
  const SOURCE='agent/BRIDGE6.js';
  let current=null,currentSha='',candidate=null,refreshing=false,bootedAt=0;
  const badge=document.createElement('div');badge.style.cssText='position:fixed;right:12px;bottom:52px;z-index:2147483647;background:#574615;color:white;padding:6px 9px;border-radius:6px;font:12px monospace';document.body.appendChild(badge);
  function status(t){badge.textContent='Loader 2 | '+t;console.log('[venice-loader2] '+t);}
  GM_registerMenuCommand('Configure Venice bridge key',()=>{const k=prompt('Doorman key (stored locally in Tampermonkey):',CONFIG.key);if(k){GM_setValue('vrb6.key',k.trim());location.reload();}});
  if(!CONFIG.key){status('configure key in Tampermonkey menu');return;}
  function getSource(){return new Promise((resolve,reject)=>{
    const u=new URL(CONFIG.worker);u.searchParams.set('k',CONFIG.key);u.searchParams.set('op','read');u.searchParams.set('branch',CONFIG.branch);u.searchParams.set('path',SOURCE);u.searchParams.set('_',String(Date.now()));
    GM_xmlhttpRequest({method:'GET',url:u.href,timeout:30000,onload:r=>{try{const o=JSON.parse(r.responseText);if(r.status<200||r.status>=300||o.ok!==true||typeof o.text!=='string'||!o.sha)throw new Error(o.error||'bad source');resolve({source:o.text,sha:o.sha});}catch(e){reject(e);}},onerror:()=>reject(new Error('source offline')),ontimeout:()=>reject(new Error('source timeout'))});
  });}
  function compile(source){return new Function('GM_xmlhttpRequest','GM_getValue','GM_setValue','window','document','CONFIG',source);}
  function boot(build){
    const factory=compile(build.source); // Parse candidate before stopping the healthy runtime.
    current?.stop();current=null;
    const handle=factory(GM_xmlhttpRequest,GM_getValue,GM_setValue,window,document,CONFIG);
    if(!handle||typeof handle.stop!=='function'||typeof handle.health!=='function')throw new Error('runtime returned no lifecycle handle');
    current=handle;currentSha=build.sha;candidate=build;bootedAt=Date.now();status('testing '+handle.version);
  }
  async function refresh(){
    if(refreshing)return;
    refreshing=true;
    try{
      const build=await getSource();if(build.sha===currentSha)return;
      if(build.sha===GM_getValue('vrb6.badSha',''))return;
      if(current&&!current.health().canUpgrade){status('update waiting for turn checkpoint');return;}
      try{boot(build);}catch(e){GM_setValue('vrb6.badSha',build.sha);status('update rejected: '+e.message);if(!current){const cached=GM_getValue('vrb6.lastgood',null);if(cached)boot(cached);}}
    }catch(e){status(e.message);if(!current){const cached=GM_getValue('vrb6.lastgood',null);if(cached)try{boot(cached);}catch(e){status('cached build failed: '+e.message);}}}
    finally{refreshing=false;}
  }
  setInterval(()=>{
    if(!current)return;
    const h=current.health();
    if(candidate&&h.ready&&Date.now()-bootedAt>30000&&Date.now()-h.lastTick<20000){GM_setValue('vrb6.lastgood',candidate);candidate=null;status('healthy '+current.version);}
    if(Date.now()-h.lastTick>90000){const bad=currentSha;current.stop();current=null;currentSha='';GM_setValue('vrb6.badSha',bad);status('stalled; restoring last healthy build');const cached=GM_getValue('vrb6.lastgood',null);if(cached&&cached.sha!==bad)try{boot(cached);}catch(e){status(e.message);}}
  },10000);
  setInterval(refresh,60000);refresh();
})();

