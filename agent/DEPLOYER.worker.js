const V = 7;
const json = (d, s = 200) => new Response(JSON.stringify({ v: V, ...d }, null, 2), { status: s, headers: { "Content-Type": "application/json" } });
export default {
async fetch(request, env) {
const p = new URL(request.url).searchParams;
if (p.get("k") !== env.DEPLOY_KEY) return json({ ok: false, error: "bad key" }, 401);
const op = p.get("op") || "ops";
const acct = String(env.CF_ACCOUNT || "").trim();
const script = String(env.SCRIPT_NAME || "").trim();
const tok = String(env.CF_TOKEN || "");
const auth = { Authorization: "Bearer " + tok };
const base = "https://api.cloudflare.com/client/v4/accounts/" + acct + "/workers/scripts";
const api = base + "/" + encodeURIComponent(script);
if (op === "bindings") {
const r = await fetch(api + "/settings", { headers: auth });
const b = await r.json();
const list = (b.result && b.result.bindings) || [];
return json({ status: r.status, names: list.map(function (x) { return x.type + ":" + x.name; }) });
}
if (op !== "deploy") return json({ ok: true, ops: ["bindings", "deploy"] });
const branch = p.get("branch") || "main";
const safe = branch.split("/").map(encodeURIComponent).join("/");
const got = await fetch("https://raw.githubusercontent.com/" + env.GITHUB_REPO + "/" + safe + "/agent/DOORMAN.worker.js");
if (!got.ok) return json({ ok: false, error: "source " + got.status }, 400);
const src = await got.text();
if (!src || src.length < 500) return json({ ok: false, error: "source too short" }, 400);
const cur = await fetch(api + "/settings", { headers: auth });
const cb = await cur.json();
const keep = ((cb.result && cb.result.bindings) || []).filter(function (x) {
return x.type === "plain_text" || x.type === "json";
}).map(function (x) {
return x.type === "json" ? { type: "json", name: x.name, json: x.json } : { type: "plain_text", name: x.name, text: x.text };
});
const form = new FormData();
form.set("metadata", JSON.stringify({ main_module: "worker.js", bindings: keep }));
form.set("worker.js", new File([src], "worker.js", { type: "application/javascript+module" }));
const put = await fetch(api + "?keep_bindings=plain_text,secret_text", { method: "PUT", headers: auth, body: form });
const body = (await put.text()).slice(0, 300);
const after = await fetch(api + "/settings", { headers: auth });
const ab = await after.json();
const names = ((ab.result && ab.result.bindings) || []).map(function (x) { return x.name; });
return json({ ok: put.ok, status: put.status, kept: keep.length, bindings_after: names, body }, put.ok ? 200 : 400);
},
};
