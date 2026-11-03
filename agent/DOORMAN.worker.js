// @ts-nocheck
// venice-doorman — transport for repo actions plus a cron half that sets a wake flag.
// Secrets: GITHUB_TOKEN, DOORMAN_KEY, DEPLOY_KEY. Vars: GITHUB_REPO, WAKE_BRANCH, DEPLOYER.
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" };
const WAKE_PATH = "agent/WAKE.json";
const WAKE_HEARTBEAT_MIN = 15, WAKE_FRESH_COMMIT_MIN = 20, WAKE_FRESH_FAIL_MIN = 30;
const enc = (s) => { const b = new TextEncoder().encode(s); let o = ""; for (let i = 0; i < b.length; i += 8192) o += String.fromCharCode.apply(null, b.subarray(i, i + 8192)); return btoa(o); };
const dec = (b64) => { const r = atob(String(b64 || "").replace(/\n/g, "")); const u = new Uint8Array(r.length); for (let i = 0; i < r.length; i += 1) u[i] = r.charCodeAt(i); return new TextDecoder().decode(u); };
const reply = (d, s = 200) => new Response(JSON.stringify(d, null, 2), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
function repo(env) { if (!env.GITHUB_REPO) throw new Error("GITHUB_REPO unset"); return env.GITHUB_REPO; }
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
async function wakeRead(env) {
  const got = await gh(env, `/contents/${WAKE_PATH}?ref=${encodeURIComponent(env.WAKE_BRANCH)}`);
  if (!got.ok) return { pending: false, sha: null };
  let parsed = /** @type {any} */ ({});
  try { parsed = JSON.parse(dec(got.body.content)); } catch { parsed = {}; }
  return /** @type {any} */ ({ ...parsed, sha: got.body.sha });
}

async function wakeWrite(env, payload, sha) {
  const body = { message: "agent: wake flag", content: enc(JSON.stringify(payload, null, 2)), branch: env.WAKE_BRANCH };
  if (sha) body.sha = sha;
  const put = await gh(env, `/contents/${WAKE_PATH}`, { method: "PUT", body: JSON.stringify(body) });
  if (!put.ok) throw new Error(`wake write failed: ${put.status}`);
}
async function wakeDecide(env) {
  const now = Date.now();
  const wake = await wakeRead(env);
  if (wake.pending && wake.set_at) {
    const age = (now - Date.parse(wake.set_at)) / 60000;
    if (age < WAKE_HEARTBEAT_MIN) return;
  }
  const reasons = [];
  const commits = await gh(env, `/commits?sha=main&per_page=1`);
  if (commits.ok && Array.isArray(commits.body) && commits.body[0]) {
    const when = commits.body[0].commit?.committer?.date;
    if (when && (now - Date.parse(when)) / 60000 < WAKE_FRESH_COMMIT_MIN) reasons.push(`main moved ${commits.body[0].sha.slice(0, 8)}`);
  }
  const runs = await gh(env, `/actions/runs?branch=${encodeURIComponent(env.WAKE_BRANCH)}&per_page=5`);
  if (runs.ok && runs.body.workflow_runs) {
    for (const run of runs.body.workflow_runs) {
      if (run.conclusion === "failure") {
        if ((now - Date.parse(run.created_at)) / 60000 < WAKE_FRESH_FAIL_MIN) reasons.push(`run ${run.id} failed (${run.name})`);
        break;
      }
    }
  }
  if (!reasons.length) reasons.push("heartbeat: interval elapsed");
  const stamp = new Date(now).toISOString();
  await wakeWrite(env, { pending: true, id: stamp, set_at: stamp, reason: reasons.join("; ") }, wake.sha);
}
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    const p = new URL(request.url).searchParams;
    const op = p.get("op") || "ops";
    if (env.DOORMAN_KEY && p.get("k") !== env.DOORMAN_KEY) return reply({ ok: false, error: "bad key" }, 401);
    let bodyText = "", bodyJson = null;
    if (request.method === "POST") {
      bodyText = await request.text();
      const type = request.headers.get("content-type") || "";
      if (type.includes("application/json")) { try { bodyJson = JSON.parse(bodyText); } catch { bodyJson = null; } }
    }
    const pick = (name) => {
      const q = p.get(name);
      if (q !== null && q !== undefined) return q;
      if (bodyJson && bodyJson[name] !== undefined) return bodyJson[name];
      if (bodyText) return bodyText;
      return undefined;
    };
    const branch = p.get("branch") || (bodyJson && bodyJson.branch) || "main";
    const path = p.get("path") || (bodyJson && bodyJson.path);
    const message = p.get("message") || p.get("msg") || (bodyJson && bodyJson.message) || undefined;
    try {
      switch (op) {
        case "ops":
          return reply({ ok: true, ops: ["branch", "ref", "read", "list", "commits", "diff", "search", "grep", "put", "edit", "pr", "pr-edit", "runs", "dispatch", "merge", "deploy"] });
        case "branch": {
          const got = await gh(env, `/git/ref/heads/${encodeURIComponent(branch)}`);
          if (!got.ok) throw new Error(`branch failed: ${got.status}`);
          return reply({ ok: true, sha: got.body.object.sha });
        }
        case "ref": {
          const base = p.get("base") || "main";
          const got = await gh(env, `/git/ref/heads/${encodeURIComponent(base)}`);
          if (!got.ok) throw new Error(`base ref failed: ${got.status}`);
          const made = await gh(env, `/git/refs`, { method: "POST", body: JSON.stringify({ ref: `refs/heads/${branch}`, sha: got.body.object.sha }) });
          if (!made.ok) throw new Error(`ref failed: ${made.status}`);
          return reply({ ok: true, sha: made.body.object.sha });
        }
        case "read": {
          if (!path) throw new Error("path is required");
          const file = await readFile(env, branch, path);
          if (p.get("b64") === "1") return reply({ ok: true, base64: file.base64, sha: file.sha });
          return reply({ ok: true, text: file.text, sha: file.sha });
        }
        case "list": {
          const dir = path || p.get("dir") || "";
          const got = await gh(env, `/contents/${dir}?ref=${encodeURIComponent(branch)}`);
          if (!got.ok) throw new Error(`list ${dir} failed: ${got.status}`);
          const items = Array.isArray(got.body) ? got.body : [got.body];
          return reply({ ok: true, entries: items.map((i) => ({ name: i.name, path: i.path, type: i.type, size: i.size })) });
        }
        case "commits": {
          const limit = Math.min(Number(p.get("limit") || 20), 100);
          const got = await gh(env, `/commits?sha=${encodeURIComponent(branch)}&per_page=${limit}`);
          if (!got.ok) throw new Error(`commits failed: ${got.status}`);
          return reply({ ok: true, commits: (Array.isArray(got.body) ? got.body : []).map((c) => ({ sha: c.sha, short: String(c.sha).slice(0, 8), message: (c.commit.message || "").split("\n")[0], date: c.commit.author.date })) });
        }
        case "diff": {
          const sha = p.get("sha") || (bodyJson && bodyJson.sha);
          const base = p.get("base") || (bodyJson && bodyJson.base);
          if (!sha) throw new Error("sha is required");
          const target = base ? `/compare/${encodeURIComponent(base)}...${encodeURIComponent(sha)}` : `/commits/${encodeURIComponent(sha)}`;
          const got = await gh(env, target, { headers: { Accept: "application/vnd.github.diff" } });
          if (!got.ok) throw new Error(`diff failed: ${got.status}`);
          return reply({ ok: true, diff: String(got.text).slice(0, 200000) });
        }
        case "search": {
          const q = p.get("q") || (bodyJson && bodyJson.q);
          if (!q) throw new Error("q is required");
          const got = await ghRoot(env, `/search/code?q=${encodeURIComponent(q  " repo:"  repo(env))}&per_page=${Math.min(Number(p.get("limit") || 20), 100)}`);
          if (!got.ok) throw new Error(`search failed: ${got.status}`);
          return reply({ ok: true, total: got.body.total_count, hits: (got.body.items || []).map((i) => ({ path: i.path, name: i.name })) });
        }
        case "grep": {
          const q = p.get("q") || (bodyJson && bodyJson.q);
          if (!q) throw new Error("q is required");
          const limit = Math.min(Number(p.get("limit") || 40), 200);
          const scope = p.get("path") || (bodyJson && bodyJson.path) || "";
          const ref = await gh(env, `/git/ref/heads/${encodeURIComponent(branch)}`);
          if (!ref.ok) throw new Error(`grep ref failed: ${ref.status}`);
          const tree = await gh(env, `/git/trees/${ref.body.object.sha}?recursive=1`);
          if (!tree.ok) throw new Error(`grep tree failed: ${tree.status}`);
          const textish = /\.(py|md|json|jsonl|yml|yaml|txt|csv|ts|js|cfg|toml|ini)$/i;
          const all = (tree.body.tree || []).filter((n) => n.type === "blob" && textish.test(n.path) && (scope ? n.path === scope || n.path.startsWith(scope.replace(/\/$/, "") + "/") : true));
          const blobs = all.slice(0, 40);
          const needle = q.toLowerCase();
          const hits = [];
          for (const n of blobs) {
            if (hits.length >= limit) break;
            const r = await gh(env, `/git/blobs/${n.sha}`);
            if (!r.ok) continue;
            const lines = dec(r.body.content).split("\n");
            for (let k = 0; k < lines.length; k += 1) {
              if (lines[k].toLowerCase().includes(needle)) {
                hits.push({ path: n.path, line: k + 1, text: lines[k].trim().slice(0, 200) });
                if (hits.length >= limit) break;
              }
            }
          }
          return reply({ ok: true, candidates: all.length, scanned: blobs.length, truncated: all.length > blobs.length, hits });
        }
        case "put": {
          if (!path) throw new Error("path is required");
          const text = pick("text");
          if (text === undefined || text === null) throw new Error("text is required");
          const sha = await writeFile(env, branch, path, text, message, p.get("b64") === "1");
          return reply({ ok: true, sha });
        }
        case "edit": {
          if (!path) throw new Error("path is required");
          const find = pick("find");
          const replace = p.get("replace") ?? p.get("repl") ?? (bodyJson && bodyJson.replace) ?? bodyText;
          const sha = await editFile(env, branch, path, find, String(replace ?? ""), message);
          return reply({ ok: true, sha });
        }
@@MORE@@