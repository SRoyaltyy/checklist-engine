const CORS={'Access-Control-Allow-Origin':'https://venice.ai','Access-Control-Allow-Methods':'GET,POST,OPTIONS','Access-Control-Allow-Headers':'Content-Type,Authorization','Vary':'Origin'};
const enc = (s) => { const b = new TextEncoder().encode(s); let o = ""; for (let i = 0; i < b.length; i += 8192) o += String.fromCharCode.apply(null, b.subarray(i, i + 8192)); return btoa(o); };
const dec = (b64) => { const r = atob(String(b64 || "").replace(/\n/g, "")); const u = new Uint8Array(r.length); for (let i = 0; i < r.length; i += 1) u[i] = r.charCodeAt(i); return new TextDecoder().decode(u); };
const reply = (d, s = 200) => new Response(JSON.stringify(d, null, 2), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
function repo(env) { if (env.GITHUB_REPO !== "SRoyaltyy/checklist-engine") throw new Error("Worker is pinned to SRoyaltyy/checklist-engine"); return "SRoyaltyy/checklist-engine"; }
async function gh(env, path, init = {}) {
  const res = await fetch(`https://api.github.com/repos/${repo(env)}${path}`, { ...init, headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json", "Content-Type": "application/json", "User-Agent": "venice-doorman", ...(init.headers || {}) } });
  const text = await res.text();
  let body; try { body = JSON.parse(text); } catch { body = text; }
  return { ok: res.ok, status: res.status, body, text };
}
async function ghRoot(env, path, init = {}) {
  const res = await fetch(`https://api.github.com${path}`, { ...init, headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github+json", "User-Agent": "venice-doorman", ...(init.headers || {}) } });
  const text = await res.text();
  let body; try { body = JSON.parse(text); } catch { body = text; }
  return { ok: res.ok, status: res.status, body, text };
}

async function readFile(env, branch, path) {
  const got = await gh(env, `/contents/${path}?ref=${encodeURIComponent(branch)}`);
  if (!got.ok) throw new Error(`read ${path} failed: ${got.status}`);
  if (typeof got.body.content === "string" && got.body.encoding === "base64") {
    return { text: dec(got.body.content), base64: got.body.content, sha: got.body.sha };
  }
  const blob = await gh(env, `/git/blobs/${got.body.sha}`);
  if (!blob.ok) throw new Error(`read ${path} failed: ${blob.status}`);
  return { text: dec(blob.body.content), base64: blob.body.content, sha: got.body.sha };
}

async function writeFile(env, branch, path, text, message, isBase64) {
  const body = { message: message || `doorman: ${path}`, content: isBase64 ? String(text).replace(/\n/g, "") : enc(text), branch };
  const head = await gh(env, `/contents/${path}?ref=${encodeURIComponent(branch)}`);
  if (head.ok) body.sha = head.body.sha;
  const put = await gh(env, `/contents/${path}`, { method: "PUT", body: JSON.stringify(body) });
  if (!put.ok) throw new Error(`write ${path} failed: ${put.status} ${JSON.stringify(put.body).slice(0, 300)}`);
  return put.body.commit.sha;
}

async function editFile(env, branch, path, find, replace, message) {
  if (!find) throw new Error("find is empty");
  const current = await readFile(env, branch, path);
  const hits = current.text.split(find).length - 1;
  if (hits !== 1) throw new Error(`find matched ${hits} times, need exactly 1`);
  return writeFile(env, branch, path, current.text.replace(find, replace), message, false);
}

// Optional owner-assigned task mode. No active task means legacy monitoring remains available.
const ACTIVE_TASK_PATH='agent/ACTIVE_TASK.json',TASK_LEASE_MS=1800000;
function taskId(value){if(!/^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$/.test(value||''))throw new Error('Valid task_id required');return value;}
function actorId(value){if(!/^[A-Za-z0-9._-]{8,120}$/.test(value||''))throw new Error('Valid owner_id required');return value;}
function taskRoot(task){return RUNTIME_ROOT+'/tasks/'+task.id;}
async function activeTask(env){
 const f=await maybeRead(env,'main',ACTIVE_TASK_PATH);if(!f)return null;
 const t=JSON.parse(f.text);if(t.status!=='active')return null;
 taskId(t.id);writableBranch(t.branch);
 if(!t.goal||!Array.isArray(t.allowed_paths)||!t.allowed_paths.length)throw new Error('Active task needs goal and allowed_paths');
 for(const p of t.allowed_paths)safePath(p.endsWith('/**')?p.slice(0,-3):p);
 return {...t,assignment_sha:f.sha};
}
function taskPathAllowed(task,path){safePath(path);if(path===ACTIVE_TASK_PATH)return false;const matches=p=>p==='**'||(p.endsWith('/**')?(path===p.slice(0,-3)||path.startsWith(p.slice(0,-2))):path===p);if((task.protected_paths||[]).some(matches))return false;return task.allowed_paths.some(matches);}
async function claimTask(env,command){
 const task=await activeTask(env);if(!task||command.task_id!==task.id||command.assignment_sha!==task.assignment_sha)throw new Error('Refresh the active task assignment before claiming it');
 const owner=actorId(command.owner_id),path=taskRoot(task)+'/LEASE.json',f=await maybeRead(env,runtimeBranch(env),path);
 const prior=f?JSON.parse(f.text):null,now=Date.now();
 if(prior&&prior.assignment_sha===task.assignment_sha&&prior.owner_id!==owner&&prior.expires_at>now)throw new Error('Task is leased to another owner until '+new Date(prior.expires_at).toISOString());
 if(prior?.owner_id===owner&&prior.assignment_sha===task.assignment_sha&&prior.expires_at-now>300000)return {ok:true,task_id:task.id,owner_id:owner,expires_at:prior.expires_at,unchanged:true};
 const lease={task_id:task.id,branch:task.branch,assignment_sha:task.assignment_sha,owner_id:owner,at:now,expires_at:now+TASK_LEASE_MS};
 const result=await verifiedWrite(env,runtimeBranch(env),path,JSON.stringify(lease,null,2),'venice: claim task ownership',f?f.sha:null);
 return {ok:true,...lease,commit:result.commit};
}
async function requireTask(env,command,action,args={}){
 const task=await activeTask(env);if(!task){if(command.task_id)throw new Error('No active task; refresh assignment');return null;}
 if(command.task_id!==task.id||command.assignment_sha!==task.assignment_sha)throw new Error('Task assignment changed; refresh context before mutation');
 const owner=actorId(command.owner_id),f=await maybeRead(env,runtimeBranch(env),taskRoot(task)+'/LEASE.json'),lease=f?JSON.parse(f.text):null;
 if(!lease||lease.owner_id!==owner||lease.assignment_sha!==task.assignment_sha||lease.expires_at<=Date.now())throw new Error('Claim or renew task ownership before mutation');
 const maintenance=['agent/BRIDGE6.js','agent/LOADER6.user.js','agent/DOORMAN.worker.js','agent/DEPLOYER.worker.js'];
 if(action==='write_file'||action==='edit_file'){
  const infrastructure=task.allow_infrastructure===true&&(args.branch||runtimeBranch(env))===runtimeBranch(env)&&maintenance.includes(args.path);
  if(!infrastructure&&((args.branch||runtimeBranch(env))!==task.branch||!taskPathAllowed(task,args.path)))throw new Error('Write is outside the assigned task branch/paths');
  if(action==='write_file'&&!Object.prototype.hasOwnProperty.call(args,'expected_sha'))throw new Error('Task writes require expected_sha from the prior read, or null for a new file');
 }
 if(action==='create_branch'&&args.branch!==task.branch)throw new Error('Create only the assigned work branch');
 if(action==='create_pr'&&(args.branch||runtimeBranch(env))!==task.branch)throw new Error('PR must use the assigned branch');
 if(action==='dispatch'&&(args.branch||runtimeBranch(env))!==task.branch)throw new Error('Dispatch must use the assigned branch');
 if(action==='deploy_worker'&&task.allow_infrastructure!==true)throw new Error('Infrastructure maintenance is not enabled for this task');
 return task;
}
async function taskReadTool(env,action,args){
 const number=Number(args.issue||args.pr);const page=Math.max(1,Math.min(100,Number(args.page)||1));
 if(!Number.isSafeInteger(number)||number<1)throw new Error('Positive issue/pr number required');
 if(action==='read_issue'||action==='read_pr'){
  const r=await gh(env,(action==='read_issue'?'/issues/':'/pulls/')+number);if(!r.ok)throw new Error(action+': '+r.status);
  const b=r.body,offset=Math.max(0,Number(args.offset)||0),body=String(b.body||''),text=body.slice(offset,offset+12000);
  return {ok:true,number:b.number,title:b.title,state:b.state,url:b.html_url,body:text,next_offset:offset+text.length<body.length?offset+text.length:null,head:b.head?{branch:b.head.ref,sha:b.head.sha,repo:b.head.repo?.full_name}:undefined,base:b.base?{branch:b.base.ref,sha:b.base.sha}:undefined,mergeable:b.mergeable,draft:b.draft,merged:b.merged};
 }
 const api=action==='issue_comments'?'/issues/'+number+'/comments':'/pulls/'+number+'/files';
 const r=await gh(env,api+'?per_page=30&page='+page);if(!r.ok)throw new Error(action+': '+r.status);
 return {ok:true,page,possibly_more:r.body.length===30,...(action==='issue_comments'?{comments:r.body.map(x=>({id:x.id,url:x.html_url,body:String(x.body||'').slice(0,12000)}))}:{files:r.body.map(x=>({path:x.filename,status:x.status,sha:x.sha,additions:x.additions,deletions:x.deletions,patch:String(x.patch||'').slice(0,2500)}))})};
}
async function mergeTaskPr(env,command,args){
 if(env.VENICE_PUBLISH_ENABLED!=='true')throw new Error('Autonomous publication is not enabled; operator must rotate legacy credentials and enable VENICE_PUBLISH_ENABLED');
 if(env.VENICE_REQUIRE_ROTATED_KEYS==='true')await requireRotatedPublicationKeys(env);
 const task=await requireTask(env,command,'merge_pr',args);if(!task||task.allow_merge!==true)throw new Error('The active assignment does not permit merging');
 if(!/^[0-9a-f]{40}$/.test(args.expected_head_sha||'')||!/^\d+$/.test(String(args.pr)))throw new Error('PR number and exact expected_head_sha required');
 const r=await gh(env,'/pulls/'+args.pr);if(!r.ok)throw new Error('PR: '+r.status);const p=r.body;
 if(p.state!=='open'||p.draft||p.head?.repo?.full_name!==repo(env)||p.head.ref!==task.branch||p.base.ref!=='main'||p.head.sha!==args.expected_head_sha||p.mergeable!==true)throw new Error('PR/head/base/mergeability does not match the assigned tested change');
 const files=await gh(env,'/pulls/'+args.pr+'/files?per_page=100');if(!files.ok||files.body.length!==p.changed_files||files.body.some(f=>!taskPathAllowed(task,f.filename)))throw new Error('PR contains paths outside the assignment or its full diff was not inspected');
 const base=await gh(env,'/git/ref/heads/main');if(!base.ok)throw new Error('Cannot resolve current main');
 const ancestry=await gh(env,'/compare/'+base.body.object.sha+'...'+p.head.sha);
 if(!ancestry.ok||ancestry.body.merge_base_commit?.sha!==base.body.object.sha)throw new Error('Sync current main into the task branch and rerun tests before merging');
 const [checks,status]=await Promise.all([gh(env,'/commits/'+p.head.sha+'/check-runs?per_page=100'),gh(env,'/commits/'+p.head.sha+'/status')]);
 if(!checks.ok||!status.ok||checks.body.total_count>100)throw new Error('Cannot verify all checks');
 const cs=checks.body.check_runs||[],ss=status.body.statuses||[];
 if(!cs.some(c=>c.conclusion==='success')||cs.some(c=>c.status!=='completed'||!['success','neutral','skipped'].includes(c.conclusion))||ss.some(s=>s.state!=='success'))throw new Error('Wait for successful checks on the exact head before merging');
 const merged=await gh(env,'/pulls/'+args.pr+'/merge',{method:'PUT',body:JSON.stringify({sha:p.head.sha,merge_method:'merge'})});
 if(!merged.ok||!merged.body.merged)throw new Error('Merge: '+merged.status+' '+JSON.stringify(merged.body));
 return {ok:true,merged:true,commit:merged.body.sha,head_sha:p.head.sha,url:p.html_url};
}
async function syncTaskBranch(env,command,args){
 const task=await requireTask(env,command,'sync_branch',args);if(!task)throw new Error('An active task is required');
 if(!/^[0-9a-f]{40}$/.test(args.expected_head_sha||''))throw new Error('Exact expected_head_sha required');
 const [head,base]=await Promise.all([gh(env,'/git/ref/heads/'+encodeURIComponent(task.branch)),gh(env,'/git/ref/heads/main')]);
 if(!head.ok||!base.ok||head.body.object.sha!==args.expected_head_sha)throw new Error('Branch changed; read branch_head again before sync');
 const r=await gh(env,'/merges',{method:'POST',body:JSON.stringify({base:task.branch,head:base.body.object.sha,commit_message:'venice: synchronize assigned branch with current main'})});
 if(!r.ok)throw new Error('Sync conflict or failure: '+r.status+' '+JSON.stringify(r.body));
 return {ok:true,branch:task.branch,commit:r.body?.sha||head.body.object.sha,base_sha:base.body.object.sha,unchanged:r.status===204};
}
async function publicationStatus(env){
 if(env.VENICE_PUBLISH_ENABLED!=='true')return {enabled:false,reason:'operator_flag_disabled'};
 try{if(env.VENICE_REQUIRE_ROTATED_KEYS==='true')await requireRotatedPublicationKeys(env);return {enabled:true,credential_rotation_required:env.VENICE_REQUIRE_ROTATED_KEYS==='true'};}catch(e){return {enabled:false,reason:e.message};}
}
async function requireRotatedPublicationKeys(env){
 const exposed=['8cc827e62aae83f112867a6438511e849da19821d3f7751f696bca60cb6bce60','c11226fbc8e36d50d599429cc35f216d139f340b9a225890d6c9f5e3c35d6371'];
 for(const name of ['DOORMAN_KEY','DEPLOY_KEY']){
  const value=String(env[name]||'');if(value.length<32)throw new Error('Credential rotation required before publication: '+name);
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(x=>x.toString(16).padStart(2,'0')).join('');
  if(exposed.includes(hash))throw new Error('Exposed legacy credential is forbidden for publication: '+name);
 }
}
async function taskCapsule(env,data,known){
 const task=await requireTask(env,data,'checkpoint');if(!task)return null;
 if(!/^[A-Za-z0-9._-]{8,120}$/.test(data.turn_id||''))throw new Error('Valid turn_id required for task session');
 const c=data.contribution;
 if(!c||!['implementation','verification','finding','blocker','completion'].includes(c.kind)||!String(c.description||'').trim())throw new Error('Each work session needs a tangible contribution, not a repeated status');
 const proof=(Array.isArray(c.evidence)?c.evidence:[]).filter(x=>known.includes(x));
 if(!proof.length||!String(data.next||'').trim())throw new Error('Contribution needs returned evidence and an exact next step');
 if(data.done&&task.deliverable==='merged_pr'){
  const link=[...known].reverse().find(x=>String(x).includes('/pull/')),number=link?.match(/\/pull\/(\d+)/)?.[1];
  const result=number?await gh(env,'/pulls/'+number):null;
  if(!result?.ok||!result.body.merged||result.body.head?.ref!==task.branch)throw new Error('This goal is not complete until its task PR is actually merged');
 }
 const branch=runtimeBranch(env),root=taskRoot(task),path=root+'/sessions/'+data.turn_id+'.json';
 const input={task_id:task.id,assignment_sha:task.assignment_sha,owner_id:data.owner_id,turn_id:data.turn_id,branch:task.branch,goal:task.goal,summary:data.summary,next:data.next,contribution:{kind:c.kind,description:String(c.description).slice(0,3000),evidence:proof},plan:data.plan,notes:data.notes,pitfalls:data.pitfalls||[]};
 const prior=await maybeRead(env,branch,path);
 if(prior){const record=JSON.parse(prior.text);if(JSON.stringify(record.input)!==JSON.stringify(input))throw new Error('A completed session id cannot be reused for a different handoff');await persistTaskPitfalls(env,task,record.pitfalls);return {task,record,pitfalls:record.pitfalls};}
 const pf=await maybeRead(env,branch,root+'/PITFALLS.json'),pitfalls=pf?JSON.parse(pf.text):[];
 if(!Array.isArray(input.pitfalls)||input.pitfalls.length>50)throw new Error('At most 50 pitfall updates per session');
 for(const p of input.pitfalls){
  if(!/^[A-Za-z0-9._-]{3,100}$/.test(p.id||'')||!p.problem||!p.lesson)throw new Error('Pitfall needs stable id, problem and lesson');
  const evidence=(Array.isArray(p.evidence)?p.evidence:[]).filter(x=>known.includes(x));if(!evidence.length)throw new Error('Pitfall requires returned evidence');
  const old=pitfalls.find(x=>x.id===p.id);
  const update={...p,problem:String(p.problem).slice(0,2000),lesson:String(p.lesson).slice(0,2000),failed_approach:String(p.failed_approach||'').slice(0,2000),evidence,first_seen:old?.first_seen||data.turn_id,last_seen:data.turn_id,seen_at_ms:Date.now()};
  if(old)Object.assign(old,update,{evidence:[...new Set([...(old.evidence||[]),...evidence])]});else pitfalls.push(update);
 }
 if(pitfalls.length>200)throw new Error('Archive task pitfalls explicitly before adding more than 200 entries');
 const record={version:1,at:new Date().toISOString(),input,pitfalls};
 await verifiedWrite(env,branch,path,JSON.stringify(record,null,2),'venice: immutable work-session handoff',null);
 if(input.pitfalls.length)await persistTaskPitfalls(env,task,pitfalls);
 return {task,record,pitfalls};
}
async function persistTaskPitfalls(env,task,entries){
 if(!entries.length)return;
 const path=taskRoot(task)+'/PITFALLS.json',f=await maybeRead(env,runtimeBranch(env),path),merged=f?JSON.parse(f.text):[];
 for(const entry of entries){const old=merged.find(x=>x.id===entry.id);if(!old)merged.push(entry);else if((entry.seen_at_ms||0)>=(old.seen_at_ms||0))Object.assign(old,entry,{evidence:[...new Set([...(old.evidence||[]),...(entry.evidence||[])])]});}
 await verifiedWrite(env,runtimeBranch(env),path,JSON.stringify(merged,null,2),'venice: retain accumulated task pitfalls',f?f.sha:null);
}

// Runtime v6: durable, acknowledged tools for the Venice web bridge.
const RUNTIME_BRANCH = 'venice/sec-options-pipelines';
const RUNTIME_ROOT = 'agent/runtime';
function runtimeBranch(env) { return env.WAKE_BRANCH || RUNTIME_BRANCH; }
function writableBranch(branch) {
  if (!/^venice\/[A-Za-z0-9._/-]+$/.test(branch) || branch.includes('..')) throw new Error('Writes must use a venice/* branch; main is read-only');
  return branch;
}
function safePath(path) {
  if (typeof path !== 'string' || !path || path.startsWith('/') || /[?#\\\x00-\x1f]/.test(path) || path.split('/').some(x => x === '..' || x === '.')) throw new Error('Invalid repository path');
  return path;
}
async function maybeRead(env, branch, path) {
  const r = await gh(env, `/contents/${safePath(path)}?ref=${encodeURIComponent(branch)}`);
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`read ${path}: ${r.status}`);
  if (typeof r.body.content === 'string') return { text: dec(r.body.content), sha: r.body.sha };
  return readFile(env, branch, path);
}
async function verifiedWrite(env, branch, path, text, message, expectedSha) {
  writableBranch(branch); safePath(path);
  if (typeof text !== 'string' || text.length > 250000) throw new Error('text must be a string under 250000 characters');
  const prior = await maybeRead(env, branch, path);
  if (expectedSha !== undefined && expectedSha !== (prior ? prior.sha : null)) throw new Error('File changed since read; read it again before editing');
  if (prior && prior.text === text) return { ok: true, unchanged: true, path, blob_sha: prior.sha };
  const body = { branch, message: message || `venice: ${path}`, content: enc(text) };
  if (prior) body.sha = prior.sha;
  const r = await gh(env, `/contents/${path}`, { method: 'PUT', body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`write ${path}: ${r.status} ${JSON.stringify(r.body).slice(0,250)}`);
  const back = await readFile(env, branch, path);
  if (back.text !== text) throw new Error(`readback mismatch: ${path}`);
  return { ok: true, path, commit: r.body.commit.sha, blob_sha: back.sha, verified: true };
}
async function runtimeContext(env) {
  const branch = runtimeBranch(env);
  const [todo, method, progress, state, runs, notes] = await Promise.all([
    readFile(env, 'main', 'TODO.md'), readFile(env, 'main', 'METHODOLOGY.md'),
    maybeRead(env, branch, `${RUNTIME_ROOT}/PROGRESS.md`), maybeRead(env, branch, `${RUNTIME_ROOT}/STATE.json`),
    gh(env, '/actions/runs?branch=main&per_page=50'), maybeRead(env,branch,`${RUNTIME_ROOT}/NOTES.md`)
  ]);
  const section = todo.text.match(/^##\s+Venice\b[^\n]*\n[\s\S]*?(?=^##\s|$(?![\s\S]))/m);
  if (!section) throw new Error('No Venice section in main/TODO.md; refusing to invent a task');
  const ml = method.text.split('\n');
  const instructions = ml.slice(0,22).join('\n').slice(0,6000);
  const specific = 'Historical lane assignments are omitted to prevent stale work. Use grep/read_file on main/METHODOLOGY.md for task-specific rules. The active task list is the current main/TODO.md Venice section.';
  const task=await activeTask(env);
  let task_notes=null,pitfalls=[],lease=null,task_runs=null;
  if(task){
    const root=taskRoot(task),[n,p,l,r]=await Promise.all([maybeRead(env,branch,root+'/NOTES.md'),maybeRead(env,branch,root+'/PITFALLS.json'),maybeRead(env,branch,root+'/LEASE.json'),gh(env,'/actions/runs?branch='+encodeURIComponent(task.branch)+'&per_page=30')]);
    task_notes=n?.text||'';pitfalls=p?JSON.parse(p.text):[];lease=l?JSON.parse(l.text):null;
    task_runs=r.ok?(r.body.workflow_runs||[]).map(x=>({id:x.id,name:x.name,title:x.display_title,status:x.status,conclusion:x.conclusion,sha:x.head_sha,url:x.html_url})):null;
  }
  const saved=state?JSON.parse(state.text):null;
  const publication=await publicationStatus(env);
  let task_pr=null;
  if(task&&saved?.task_id===task.id){const link=[...(saved.evidence||[])].reverse().find(x=>String(x).includes('/pull/'));const n=link?.match(/\/pull\/(\d+)/)?.[1];if(n){const p=await gh(env,'/pulls/'+n);if(p.ok)task_pr={number:p.body.number,state:p.body.state,merged:p.body.merged,head_sha:p.body.head?.sha,updated_at:p.body.updated_at};}}
  return { ok:true, version:6, at:new Date().toISOString(), branch,
    assignment:task,lease,pitfalls,task_runs,task_pr,publishing_enabled:publication.enabled,publication,
    instructions:{todo_sha:todo.sha,venice_lane:section[0],methodology_sha:method.sha,methodology_start:instructions,methodology_venice_matches:specific},
    available_evidence:[`TODO.md@${todo.sha}`,`METHODOLOGY.md@${method.sha}`],
    progress:progress?.text || 'No v6 progress recorded yet. Begin with the current Venice lane; old SEC collector work was reassigned.',
    state:task&&saved?.task_id!==task.id?null:saved,
    notes:task?task_notes:(notes?.text || 'No durable notes yet. Record file locations, decisions, failed approaches and unresolved questions here; keep them concise.'),
    runs:runs.ok ? (runs.body.workflow_runs||[]).filter(r=>/nai[-_]sec[-_]|nai[-_]occ[-_]oi[-_]daily/.test(r.path||r.name||'')).slice(0,15).map(r=>({id:r.id,path:r.path,name:r.name,status:r.status,conclusion:r.conclusion,sha:r.head_sha,url:r.html_url,created_at:r.created_at})) : {error:runs.status}
  };
}
async function runtimeSave(env, data) {
  const branch=runtimeBranch(env);
  const summary=String(data.summary||'').slice(0,10000), next=String(data.next||'').slice(0,4000);
  const before=await maybeRead(env,branch,`${RUNTIME_ROOT}/STATE.json`);let previous={};try{previous=JSON.parse(before?.text||'{}');}catch{}
  const known=[...new Set([...(previous.evidence||[]),...(data.evidence||[])])].slice(-100);
  const capsule=await taskCapsule(env,data,known);
  const rawPlan=data.plan||previous.plan||{goal:'Follow current main/TODO.md Venice lane',why:'Advance James\' assigned work',current_task:'lane',tasks:[{id:'lane',title:'Inspect the current lane and break it into provable subtasks',status:'doing',weight:1,evidence:[]}]};
  const tasks=(Array.isArray(rawPlan.tasks)?rawPlan.tasks:[]).slice(0,25).map((t,i)=>{
    const evidence=(Array.isArray(t.evidence)?t.evidence:[]).filter(x=>known.includes(x));
    const status=['todo','doing','done','blocked'].includes(t.status)?t.status:'todo';
    return {id:String(t.id||i+1),title:String(t.title||'').slice(0,300),acceptance:String(t.acceptance||'').slice(0,500),weight:Math.max(1,Math.min(20,Number(t.weight)||1)),status:status==='done'&&!evidence.length?'doing':status,evidence,blocker:String(t.blocker||'').slice(0,500)};
  });
  const total=tasks.reduce((n,t)=>n+t.weight,0),complete=tasks.filter(t=>t.status==='done').reduce((n,t)=>n+t.weight,0);
  const plan={goal:String(rawPlan.goal||'').slice(0,2000),why:String(rawPlan.why||'').slice(0,2000),gantt_row:String(rawPlan.gantt_row||'Venice assigned lane').slice(0,300),current_task:String(rawPlan.current_task||''),tasks,progress_percent:total?Math.floor(100*complete/total):0};
  const state={version:6,at:capsule?.record.at||new Date().toISOString(),turn_id:data.turn_id||null,summary,next,plan,tool_results:data.tool_results||[],blockers:data.blockers||[],evidence:known,done:!!data.done,...(capsule?{task_id:capsule.task.id,assignment_sha:capsule.task.assignment_sha,owner_id:data.owner_id,work_branch:capsule.task.branch,contribution:capsule.record.input.contribution,pitfalls:capsule.pitfalls}: {})};
  const rows=tasks.map(t=>`| ${t.id} | ${t.title.replace(/\|/g,'/')} | ${t.status} | ${t.evidence.join(', ')} |`).join('\n');
  const text=`# Venice progress\n\nUpdated ${state.at} UTC\n\n## Goal\n${plan.goal}\n\n## Why this advances the repo\n${plan.why}\n\nGantt row: ${plan.gantt_row}\nVerified progress: **${plan.progress_percent}%**\nCurrent subtask: ${plan.current_task}\n\n| ID | Subtask | Status | Evidence |\n|---|---|---|---|\n${rows}\n\n## Last completed work\n${summary}\n\n## Exact next step\n${next}\n\n## Blockers\n${JSON.stringify(state.blockers)}\n\n## Evidence\n${JSON.stringify(state.evidence)}\n\nTurn: ${state.turn_id}\n`;
  await verifiedWrite(env,branch,`${RUNTIME_ROOT}/PLAN.json`,JSON.stringify(plan,null,2)+'\n','venice: checkpoint verified task plan');
  await verifiedWrite(env,branch,`${RUNTIME_ROOT}/PROGRESS.md`,text,'venice: checkpoint progress');
  if(typeof data.notes==='string'&&data.notes.trim())await verifiedWrite(env,branch,`${capsule?taskRoot(capsule.task):RUNTIME_ROOT}/NOTES.md`,data.notes.slice(0,10000),'venice: checkpoint durable notes');
  if(capsule)await verifiedWrite(env,branch,taskRoot(capsule.task)+'/STATE.json',JSON.stringify(state,null,2)+'\n','venice: checkpoint task state');
  return verifiedWrite(env,branch,`${RUNTIME_ROOT}/STATE.json`,JSON.stringify(state,null,2)+'\n','venice: checkpoint state');
}
async function jobLog(env,jobId,runId) {
  if(!/^\d+$/.test(String(jobId)))throw new Error('job_id required');
  let r=await fetch(`https://api.github.com/repos/${repo(env)}/actions/jobs/${jobId}/logs`,{redirect:'manual',headers:{Authorization:`Bearer ${env.GITHUB_TOKEN}`,'User-Agent':'venice-doorman'}});
  if(r.status===302){const u=new URL(r.headers.get('location'));if(u.protocol!=='https:'||!/(\.blob\.core\.windows\.net|\.actions\.githubusercontent\.com|\.githubusercontent\.com)$/.test(u.hostname))throw new Error('Unexpected log download host');r=await fetch(u,{redirect:'manual'});}
  if(!r.ok)throw new Error(`job log: ${r.status}`);
  const text=await r.text();
  const error_lines=text.split('\n').filter(x=>/Traceback|(?:Error|Exception):|##\[error\]/.test(x)).slice(-15);
  return {ok:true,job_id:jobId,url:`https://github.com/${repo(env)}/actions/runs/${runId||''}/job/${jobId}`,error_lines,total_characters:text.length,text:text.slice(-9000),truncated:text.length>9000};
}
async function reportFailure(env,runId) {
  if(!/^\d+$/.test(String(runId)))throw new Error('run_id required');
  const branch=runtimeBranch(env), proofPath=`${RUNTIME_ROOT}/reports/${runId}.json`;
  const saved=await maybeRead(env,branch,proofPath);if(saved)return {...JSON.parse(saved.text),replayed:true};
  const run=await gh(env,`/actions/runs/${runId}`);if(!run.ok)throw new Error(`run: ${run.status}`);
  if(run.body.conclusion!=='failure'||!/nai[-_]sec[-_]|nai[-_]occ[-_]oi[-_]daily/.test(run.body.path||run.body.name||''))throw new Error('Only failed SEC/OI lane runs may be reported by this tool');
  const jobs=await gh(env,`/actions/runs/${runId}/jobs?per_page=30`);if(!jobs.ok)throw new Error(`jobs: ${jobs.status}`);
  const failed=(jobs.body.jobs||[]).filter(j=>j.conclusion==='failure');
  const facts=[];
  for(const j of failed.slice(0,3)){
    let log;try{log=await jobLog(env,j.id,runId);}catch(e){log={error_lines:[],unavailable:String(e.message||e)};}
    facts.push({job_id:j.id,url:j.html_url,failed_steps:(j.steps||[]).filter(s=>s.conclusion==='failure').map(s=>s.name),skipped_steps:(j.steps||[]).filter(s=>s.conclusion==='skipped').map(s=>s.name),error_lines:log.error_lines,log_unavailable:log.unavailable||null});
  }
  const marker=`<!-- venice-dedupe:run-${runId} -->`, verifiedMarker=`<!-- venice-verified-log:${runId} -->`;
  const lines=[`Verified failure report — GitHub API/job-log facts only. GPT owns the fix.`,``,`Run: ${runId} — ${run.body.html_url}`,`Workflow: ${run.body.name}; branch: ${run.body.head_branch}; commit: ${run.body.head_sha}`,`Conclusion: ${run.body.conclusion}`];
  for(const f of facts){lines.push('',`Job ${f.job_id}: ${f.url}`,`Failed steps: ${f.failed_steps.join('; ')||'not supplied'}`,`Skipped steps: ${f.skipped_steps.join('; ')||'none'}`,'','Exact error lines:',...f.error_lines.map(x=>'> '+x));if(f.log_unavailable)lines.push(`Log unavailable: ${f.log_unavailable}. No root cause is inferred.`);}
  lines.push('','This verified record supersedes any earlier inferred diagnosis or guessed step status. No pipeline code was changed.',marker,verifiedMarker);
  const body=lines.join('\n');
  const list=await gh(env,'/issues?state=all&per_page=100');if(!list.ok)throw new Error('Cannot check existing failure reports');
  let issue=(list.body||[]).find(x=>!x.pull_request&&(x.body||'').includes(marker))||(list.body||[]).find(x=>!x.pull_request&&(x.body||'').includes(`/actions/runs/${runId}`));let result;
  if(issue){
    const comments=await gh(env,`/issues/${issue.number}/comments?per_page=100`);if(!comments.ok)throw new Error('Cannot check prior verified comments');
    const prior=(comments.body||[]).find(x=>(x.body||'').includes(verifiedMarker));
    if(prior)result={ok:true,url:prior.html_url,issue:issue.number,already_reported:true};
    else {const posted=await gh(env,`/issues/${issue.number}/comments`,{method:'POST',body:JSON.stringify({body})});if(!posted.ok)throw new Error(`comment: ${posted.status}`);result={ok:true,url:posted.body.html_url,issue:issue.number};}
  }else{
    const posted=await gh(env,'/issues',{method:'POST',body:JSON.stringify({title:`Failed scheduled run ${runId} — ${run.body.name}`,body})});if(!posted.ok)throw new Error(`issue: ${posted.status}`);result={ok:true,url:posted.body.html_url,issue:posted.body.number};
  }
  result={...result,run_id:runId,facts,verified:true};
  await verifiedWrite(env,branch,proofPath,JSON.stringify(result,null,2)+'\n','venice: retain verified failure report');
  return result;
}
async function runtimeTool(env, command) {
  const {id,action,args={}}=command||{};
  if (!/^[A-Za-z0-9._-]{8,120}$/.test(id||'')) throw new Error('Each tool requires a stable unique id (8-120 letters, digits, dot, dash, underscore)');
  if(action==='claim_task')return claimTask(env,command);
  if(['read_issue','read_pr','issue_comments','pr_files'].includes(action))return taskReadTool(env,action,args);
  const branch=runtimeBranch(env), receiptPath=`${RUNTIME_ROOT}/receipts/${id}.json`;
  const old=await maybeRead(env,branch,receiptPath);
  if (old) {
    const receipt=JSON.parse(old.text);
    if (receipt.action!==action || JSON.stringify(receipt.args)!==JSON.stringify(args)) throw new Error('Action id reused with different arguments');
    if (receipt.status==='done') return {...receipt.result,replayed:true};
    return {ok:false,uncertain:true,error:'The previous execution did not save its final receipt. Inspect repository state/run history before issuing a new mutation.',id};
  }
  const mutations=new Set(['write_file','edit_file','create_branch','create_pr','create_issue','comment_issue','report_failure','dispatch','deploy_worker','merge_pr','sync_branch']);
  const mutation=mutations.has(action);
  if (mutation) await verifiedWrite(env,branch,receiptPath,JSON.stringify({id,action,args,status:'running',at:new Date().toISOString()}),'venice: claim tool action');
  let result;
  try {
    if(mutation)await requireTask(env,command,action,args);
    const target=args.branch||branch;
    switch(action) {
      case 'branch_head': {const b=args.branch||'main',r=await gh(env,'/git/ref/heads/'+encodeURIComponent(b));if(!r.ok)throw new Error('branch_head: '+r.status);result={ok:true,branch:b,sha:r.body.object.sha,url:'https://github.com/'+repo(env)+'/tree/'+r.body.object.sha};break;}
      case 'read_file': {
        const b=args.branch||'main', file=await readFile(env,b,safePath(args.path));
        const lines=file.text.split('\n'), start=Math.max(1,Number(args.start_line)||1), end=Math.min(lines.length,Number(args.end_line)||start+249);
        const offset=args.offset===undefined?lines.slice(0,start-1).join('\n').length+(start>1?1:0):Math.max(0,Number(args.offset)||0);
        const selected=args.offset===undefined?lines.slice(start-1,end).join('\n'):file.text.slice(offset);
        const text=selected.slice(0,12000),next=offset+text.length;
        result={ok:true,branch:b,path:args.path,sha:file.sha,total_lines:lines.length,total_characters:file.text.length,start_line:start,end_line:end,offset,next_offset:next<file.text.length?next:null,truncated:text.length<selected.length,text};break;
      }
      case 'list_files': {
        const p=args.path?safePath(args.path):'';
        const r=await gh(env,`/contents/${p}?ref=${encodeURIComponent(args.branch||'main')}`);
        if(!r.ok)throw new Error(`list: ${r.status}`);
        result={ok:true,entries:(Array.isArray(r.body)?r.body:[r.body]).slice(0,150).map(x=>({path:x.path,type:x.type,size:x.size,sha:x.sha}))};break;
      }
      case 'grep': {
        const file=await readFile(env,args.branch||'main',safePath(args.path));
        const q=String(args.query||'').toLowerCase();if(!q)throw new Error('query is required');
        result={ok:true,path:args.path,sha:file.sha,hits:file.text.split('\n').map((text,i)=>({line:i+1,text})).filter(x=>x.text.toLowerCase().includes(q)).slice(0,30)};break;
      }
      case 'write_file': result=await verifiedWrite(env,target,safePath(args.path),args.text,args.message,args.expected_sha);break;
      case 'edit_file': {
        const prior=await readFile(env,writableBranch(target),safePath(args.path));
        if(!args.find || prior.text.split(args.find).length!==2)throw new Error('find must match exactly once');
        result=await verifiedWrite(env,target,args.path,prior.text.replace(args.find,String(args.replace||'')),args.message,prior.sha);break;
      }
      case 'create_branch': {
        writableBranch(args.branch); const r=await gh(env,`/git/ref/heads/${encodeURIComponent(args.base||'main')}`);
        if(!r.ok)throw new Error(`base ref: ${r.status}`);
        const made=await gh(env,'/git/refs',{method:'POST',body:JSON.stringify({ref:`refs/heads/${args.branch}`,sha:r.body.object.sha})});
        if(!made.ok)throw new Error(`create branch: ${made.status}`);result={ok:true,branch:args.branch,sha:made.body.object.sha};break;
      }
      case 'runs': {
        const r=await gh(env,`/actions/runs?branch=${encodeURIComponent(args.branch||'main')}&per_page=30`);if(!r.ok)throw new Error(`runs: ${r.status}`);
        result={ok:true,runs:(r.body.workflow_runs||[]).map(x=>({id:x.id,path:x.path,name:x.name,status:x.status,conclusion:x.conclusion,url:x.html_url,sha:x.head_sha}))};break;
      }
      case 'run_jobs': {
        if(!/^\d+$/.test(String(args.run_id)))throw new Error('run_id required');
        const r=await gh(env,`/actions/runs/${args.run_id}/jobs?per_page=30`);if(!r.ok)throw new Error(`jobs: ${r.status}`);
        result={ok:true,jobs:(r.body.jobs||[]).map(x=>({id:x.id,name:x.name,conclusion:x.conclusion,url:x.html_url,check_run_url:x.check_run_url,steps:x.steps?.map(s=>({name:s.name,conclusion:s.conclusion}))}))};break;
      }
      case 'run_status': {
        if(!/^\d+$/.test(String(args.run_id)))throw new Error('run_id required');
        const r=await gh(env,`/actions/runs/${args.run_id}`);if(!r.ok)throw new Error(`run: ${r.status}`);
        result={ok:true,id:r.body.id,status:r.body.status,conclusion:r.body.conclusion,url:r.body.html_url,sha:r.body.head_sha,branch:r.body.head_branch};break;
      }
      case 'annotations': {
        if(!/^\d+$/.test(String(args.check_run_id)))throw new Error('check_run_id required');
        const r=await gh(env,`/check-runs/${args.check_run_id}/annotations?per_page=30`);if(!r.ok)throw new Error(`annotations: ${r.status}`);
        result={ok:true,annotations:r.body};break;
      }
      case 'job_log': {
        result=await jobLog(env,args.job_id,args.run_id);break;
      }
      case 'report_failure': result=await reportFailure(env,args.run_id);break;
      case 'create_issue': case 'comment_issue': case 'create_pr': {
        const dedupe=String(args.dedupe_key||'').replace(/[^A-Za-z0-9._-]/g,'').slice(0,100);
        const marker=`<!-- venice-action:${id} -->`, dedupeMarker=dedupe?`<!-- venice-dedupe:${dedupe} -->`:'';
        const body=String(args.body||'')+'\n\n'+marker+'\n'+dedupeMarker;
        let api,payload;
        if(action==='create_pr'){writableBranch(target);api='/pulls';payload={title:args.title,body,head:target,base:'main'};}
        else if(action==='create_issue'){
          if(dedupe){const listed=await gh(env,'/issues?state=all&creator=@me&per_page=100');if(!listed.ok)throw new Error('Cannot check prior reports');const existing=(listed.body||[]).find(x=>(x.body||'').includes(dedupeMarker));if(existing){result={ok:true,number:existing.number,url:existing.html_url,deduplicated:true};break;}}
          api='/issues';payload={title:args.title,body};
        }
        else {if(!/^\d+$/.test(String(args.issue)))throw new Error('issue number required');api=`/issues/${args.issue}/comments`;payload={body};}
        const r=await gh(env,api,{method:'POST',body:JSON.stringify(payload)});if(!r.ok)throw new Error(`${action}: ${r.status} ${JSON.stringify(r.body).slice(0,200)}`);
        result={ok:true,number:r.body.number,url:r.body.html_url};break;
      }
      case 'dispatch': {
        writableBranch(target);if(!/^[A-Za-z0-9_.-]+\.ya?ml$/.test(args.workflow||''))throw new Error('workflow filename required');
        const r=await gh(env,`/actions/workflows/${args.workflow}/dispatches`,{method:'POST',body:JSON.stringify({ref:target,inputs:args.inputs||{}})});if(!r.ok)throw new Error(`dispatch: ${r.status}`);
        result={ok:true,workflow:args.workflow,branch:target};break;
      }
      case 'deploy_worker': {
        writableBranch(target);if(target!==runtimeBranch(env))throw new Error('Worker deployment is pinned to the runtime maintenance branch');
        if(!env.DEPLOYER)throw new Error('DEPLOYER unset');
        const head=await gh(env,`/git/ref/heads/${encodeURIComponent(target)}`);if(!head.ok)throw new Error('Cannot resolve deployment commit');
        const u=new URL(/^https?:/.test(env.DEPLOYER)?env.DEPLOYER:'https://'+env.DEPLOYER);if(u.origin!=='https://venice-deployer.fullscan-relay.workers.dev')throw new Error('Unexpected deployer target');u.searchParams.set('op','deploy');u.searchParams.set('commit',head.body.object.sha);
        const r=await fetch(u,{method:'POST',headers:{Authorization:'Bearer '+String(env.DEPLOY_KEY||'').trim()}});const body=await r.json();if(!r.ok||body.ok!==true)throw new Error(`deploy failed: ${JSON.stringify(body).slice(0,500)}`);
        result={ok:true,commit:head.body.object.sha,deployment:body};break;
      }
      case 'merge_pr': result=await mergeTaskPr(env,command,args);break;
      case 'sync_branch': result=await syncTaskBranch(env,command,args);break;
      default: throw new Error('Unknown tool: '+action);
    }
  } catch(e) {result={ok:false,error:String(e.message||e),action};}
  if(mutation){const receipt=await verifiedWrite(env,branch,receiptPath,JSON.stringify({id,action,args,status:'done',at:new Date().toISOString(),result}),'venice: acknowledge tool action');result={...result,receipt_path:receiptPath,receipt_sha:receipt.blob_sha};}
  return result;
}

export default {
 async fetch(request,env){
  if(request.method==='OPTIONS')return new Response(null,{headers:CORS});
  if(!env.DOORMAN_KEY || request.headers.get('Authorization')!=='Bearer '+env.DOORMAN_KEY)return reply({ok:false,error:'Unauthorized'},401);
  const op=new URL(request.url).searchParams.get('op')||'ops';
  try{
   if(env.GITHUB_REPO!=='SRoyaltyy/checklist-engine')throw new Error('Unexpected repository configuration');
   if(op==='ops'){const publication=await publicationStatus(env);return reply({ok:true,version:6,revision:'6.4.1',ops:['source','context','tool','checkpoint'],repository:'SRoyaltyy/checklist-engine',writes:'venice/* only',merge:publication.enabled,publication,task_leases:true,session_capsules:true});}
   if(op==='source'&&request.method==='GET'){const f=await readFile(env,runtimeBranch(env),'agent/BRIDGE6.js');return reply({ok:true,...f});}
   if(op==='context'&&request.method==='GET')return reply(await runtimeContext(env));
   if(request.method!=='POST')return reply({ok:false,error:'JSON POST required for mutations'},405);
   const raw=await request.text();if(raw.length>300000)throw new Error('Request too large');
   const data=JSON.parse(raw);
   if(op==='tool')return reply(await runtimeTool(env,data));
   if(op==='checkpoint')return reply(await runtimeSave(env,data));
   return reply({ok:false,error:'Unknown operation'},400);
  }catch(e){return reply({ok:false,error:String(e.message||e)},400);}
 },
 async scheduled(event,env,ctx){ctx.waitUntil((async()=>{
  if(env.LEGACY_WAKE_ENABLED!=='true')return;
  const branch=runtimeBranch(env),old=await maybeRead(env,branch,'agent/WAKE.json');let prior={};try{prior=JSON.parse(old?.text||'{}');}catch{}
  if(prior.set_at&&Date.now()-Date.parse(prior.set_at)<840000)return;
  const stamp=new Date().toISOString();await verifiedWrite(env,branch,'agent/WAKE.json',JSON.stringify({pending:true,id:stamp,set_at:stamp,reason:'scheduled heartbeat'},null,2),'venice: scheduled wake');
 })());}
};