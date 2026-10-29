// Paste this scheduled handler into the existing venice-doorman Worker.
// It dispatches the loop workflow on the branch. It cannot wake a chat,
// only start runner work, which is the point.
// The loop exits immediately when the queue has no todo item, so a firing
// cron with nothing to do is harmless.

const REPO = "SRoyaltyy/checklist-engine";
const BRANCH = "venice/calendar-announce-ledger";
const WORKFLOW = "agent-loop.yml";

function dispatch(env) {
  return fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "User-Agent": "venice-doorman",
    },
    body: JSON.stringify({ ref: BRANCH }),
  });
}

// Add alongside the existing export default:
//  async scheduled(event, env, ctx) {
//    ctx.waitUntil(dispatch(env));
//  }

// Wrangler config for a 20-minute beat:
// [triggers]
// crons = ["*/20 * * * *"]

// Turning it off: comment out the scheduled export or clear the crons
// entry and redeploy. Nothing else depends on it.

export { dispatch };