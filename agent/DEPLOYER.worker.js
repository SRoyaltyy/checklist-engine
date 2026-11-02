// venice-deployer — deploys venice-doorman from the public repo so a broken
// doorman can still be replaced. Secrets: CF_TOKEN, DEPLOY_KEY.
// Vars: CF_ACCOUNT, SCRIPT_NAME, GITHUB_REPO.
const json = (d, s = 200) => new Response(JSON.stringify(d, null, 2), { status: s, headers: { "Content-Type": "application/json" } });

export default {
  async fetch(request, env) {
    const p = new URL(request.url).searchParams;
    if (p.get("k") !== env.DEPLOY_KEY) return json({ ok: false, error: "bad key" }, 401);
    if (p.get("op") !== "deploy") return json({ ok: true, ops: ["deploy"] });
    const branch = p.get("branch") || "main";
    const safe = branch.split("/").map(encodeURIComponent).join("/");
    const url = `https://raw.githubusercontent.com/${env.GITHUB_REPO}/${safe}/agent/DOORMAN.worker.js`;
    const got = await fetch(url);
    if (!got.ok) return json({ ok: false, error: "source " + got.status }, 400);
    const src = await got.text();
    if (!src || src.length < 500) return json({ ok: false, error: "source too short" }, 400);
    const put = await fetch(`https://api.cloudflare.com/client/v4/accounts/${env.CF_ACCOUNT}/workers/scripts/${env.SCRIPT_NAME}`, { method: "PUT", headers: { Authorization: `Bearer ${env.CF_TOKEN}`, "Content-Type": "application/javascript" }, body: src });
    const body = (await put.text()).slice(0, 400);
    return json({ ok: put.ok, status: put.status, body }, put.ok ? 200 : 400);
  },
};
