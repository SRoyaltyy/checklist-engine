// venice-deployer — deploys venice-doorman from the repo so a broken doorman can be replaced.
// Secrets: CF_TOKEN, DEPLOY_KEY, GITHUB_TOKEN. Vars: CF_ACCOUNT, SCRIPT_NAME, GITHUB_REPO.
const json = (d, s = 200) => new Response(JSON.stringify(d, null, 2), { status: s, headers: { "Content-Type": "application/json" } });

export default {
  async fetch(request, env) {
    const p = new URL(request.url).searchParams;
    if (p.get("k") !== env.DEPLOY_KEY) return json({ ok: false, error: "bad key" }, 401);
    if (p.get("op") !== "deploy") return json({ ok: true, ops: ["deploy"] });
    const branch = p.get("branch") || "main";
    const got = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/contents/agent/DOORMAN.worker.js?ref=${encodeURIComponent(branch)}`, { headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: "application/vnd.github.raw" } });
    if (!got.ok) return json({ ok: false, error: "source " + got.status }, 400);
    const src = await got.text();
    const put = await fetch(`https://api.cloudflare.com/client/v4/accounts/${env.CF_ACCOUNT}/workers/scripts/${env.SCRIPT_NAME}`, { method: "PUT", headers: { Authorization: `Bearer ${env.CF_TOKEN}`, "Content-Type": "application/javascript" }, body: src });
    const body = (await put.text()).slice(0, 400);
    return json({ ok: put.ok, status: put.status, body }, put.ok ? 200 : 400);
  },
};
