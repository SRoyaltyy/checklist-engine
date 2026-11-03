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
@@MORE@@