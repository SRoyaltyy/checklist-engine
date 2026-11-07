// Fixed-target maintenance deployer. Existing token permissions are not widened.
const REPO='SRoyaltyy/checklist-engine', BRANCH='venice/sec-options-pipelines', SCRIPT='venice-doorman';
const json=(d,s=200)=>new Response(JSON.stringify({v:10,...d}),{status:s,headers:{'Content-Type':'application/json'}});
export default {
 async fetch(request,env){
  if(!env.DEPLOY_KEY||request.headers.get('Authorization')!=='Bearer '+env.DEPLOY_KEY)return json({ok:false,error:'Unauthorized'},401);
  const p=new URL(request.url).searchParams;
  if(p.get('op')!=='deploy')return json({ok:true,target:SCRIPT,branch:BRANCH});
  if(request.method!=='POST')return json({ok:false,error:'POST required'},405);
  if(env.SCRIPT_NAME!==SCRIPT||env.GITHUB_REPO!==REPO)return json({ok:false,error:'Unexpected target configuration'},400);
  const commit=p.get('commit');if(!/^[0-9a-f]{40}$/.test(commit||''))return json({ok:false,error:'Immutable 40-character commit required'},400);
  const got=await fetch('https://raw.githubusercontent.com/'+REPO+'/'+commit+'/agent/DOORMAN.worker.js');
  if(!got.ok)return json({ok:false,error:'Source unavailable'},400);const source=await got.text();
  const current=await fetch('https://raw.githubusercontent.com/'+REPO+'/'+BRANCH+'/agent/DOORMAN.worker.js?t='+Date.now());
  if(!current.ok||(await current.text())!==source)return json({ok:false,error:'Source must exactly match the fixed maintenance branch'},409);
  if(source.length<500||source.length>150000)return json({ok:false,error:'Invalid source size'},400);
  const api='https://api.cloudflare.com/client/v4/accounts/'+String(env.CF_ACCOUNT||'').trim()+'/workers/scripts/'+SCRIPT;
  const auth={Authorization:'Bearer '+env.CF_TOKEN};
  const cur=await fetch(api+'/settings',{headers:auth});const cb=await cur.json();
  if(!cur.ok||!cb.success||!Array.isArray(cb.result?.bindings))return json({ok:false,error:'Cannot read settings; deployment aborted'},400);
  const bindings=cb.result.bindings, names=bindings.map(x=>x.name);
  const required=['GITHUB_TOKEN','DOORMAN_KEY','DEPLOY_KEY','GITHUB_REPO','WAKE_BRANCH','DEPLOYER'];
  if(required.some(x=>!names.includes(x)))return json({ok:false,error:'Required existing bindings missing; deployment aborted'},400);
  const flags=[...new Set([...(cb.result.compatibility_flags||[]).filter(x=>x!=='global_fetch_private_origin'),'global_fetch_strictly_public'])];
  const metadata={main_module:'worker.js',keep_bindings:[...new Set(bindings.map(x=>x.type))],compatibility_date:cb.result.compatibility_date||'2026-11-01',compatibility_flags:flags,observability:cb.result.observability};
  const form=new FormData();form.set('metadata',JSON.stringify(metadata));form.set('worker.js',new File([source],'worker.js',{type:'application/javascript+module'}));
  const put=await fetch(api,{method:'PUT',headers:auth,body:form});const result=await put.json();
  if(!put.ok||!result.success)return json({ok:false,error:'Upload rejected',status:put.status,errors:result.errors},400);
  const after=await fetch(api+'/settings',{headers:auth});const ab=await after.json();
  const afterBindings=ab.result?.bindings||[];
  const intact=bindings.every(x=>afterBindings.some(y=>y.name===x.name&&y.type===x.type));
  return json({ok:after.ok&&intact,target:SCRIPT,commit,bindings_preserved:intact,version:result.result?.id},after.ok&&intact?200:500);
 }
};

