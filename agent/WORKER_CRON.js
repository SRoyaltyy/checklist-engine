// Venice wake - Cloudflare cron half. Drop-in addition to the existing venice-doorman Worker.
// It checks repo state itself and sets agent/WAKE.json, so no Actions queue sits in the path.
// The userscript reads that file and types into the chat. Nothing here reaches the chat directly.
//
// Install:
//   1. Paste everything below the existing constants, above the export default.
//   2. Add the scheduled method shown at the bottom INSIDE the existing export default object.
//   3. Deploy, then Settings -> Triggers -> Cron Triggers -> add */2 * * * *
//
// A wake fires on a fixed interval whether or not anything moved, plus sooner on a real event.
// The interval is the throttle: one wake per WAKE_HEARTBEAT_MIN. No KV, no stored sha.

const WAKE_REPO = "SRoyaltyy/checklist-engine";
const WAKE_BRANCH = "venice/calendar-announce-ledger";
const WAKE_PATH = "agent/WAKE.json";
const WAKE_HEARTBEAT_MIN = 15;
const WAKE_FRESH_COMMIT_MIN = 20;
const WAKE_FRESH_FAIL_MIN = 30;

function wakeGh(env, path, init = {}) {
  return fetch(`https://api.github.com${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "venice-doorman",
      ...(init.headers || {}),
    },
  });
}

async function wakeRead(env) {
  const res = await wakeGh(env, `/repos/${WAKE_REPO}/contents/${WAKE_PATH}?ref=${WAKE_BRANCH}`);
  if (!res.ok) return { pending: false, sha: null };
  const body = await res.json();
  let parsed = {};
  try {
    parsed = JSON.parse(atob(String(body.content || "").replace(/\n/g, "")));
  } catch (err) {
    parsed = {};
  }
  return { ...parsed, sha: body.sha };
}

async function wakeWrite(env, payload, sha) {
  const body = {
    message: "agent: wake flag",
    content: btoa(unescape(encodeURIComponent(JSON.stringify(payload, null, 2)))),
    branch: WAKE_BRANCH,
  };
  if (sha) body.sha = sha;
  return wakeGh(env, `/repos/${WAKE_REPO}/contents/${WAKE_PATH}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

async function wakeDecide(env) {
  const now = Date.now();
  const wake = await wakeRead(env);

  if (wake.pending && wake.set_at) {
    const age = (now - Date.parse(wake.set_at)) / 60000;
    if (age < WAKE_HEARTBEAT_MIN) return;
  }

  const reasons = [];

  let head = wake.last_main_sha || null;
  const commits = await wakeGh(env, `/repos/${WAKE_REPO}/commits?sha=main&per_page=1`);
  if (commits.ok) {
    const rows = await commits.json();
    const sha = rows[0] && rows[0].sha;
    if (sha && sha !== wake.last_main_sha) {
      head = sha;
      reasons.push(`main moved ${sha.slice(0, 8)}`);
    }
  }

  const runs = await wakeGh(env, `/repos/${WAKE_REPO}/actions/runs?branch=${WAKE_BRANCH}&per_page=5`);
  if (runs.ok) {
    const list = (await runs.json()).workflow_runs || [];
    for (const run of list) {
      if (run.conclusion === "failure") {
        if ((now - Date.parse(run.created_at)) / 60000 < WAKE_FRESH_FAIL_MIN) {
          reasons.push(`run ${run.id} failed (${run.name})`);
        }
        break;
      }
    }
  }

  if (!reasons.length) reasons.push("heartbeat: interval elapsed");

  const stamp = new Date(now).toISOString();
  await wakeWrite(env, { pending: true, id: stamp, set_at: stamp, reason: reasons.join("; "), last_main_sha: head }, wake.sha);
}

// Add this method INSIDE the existing export default object:
//
//  async scheduled(event, env, ctx) {
//    ctx.waitUntil(wakeDecide(env));
//  }

export { wakeDecide };
