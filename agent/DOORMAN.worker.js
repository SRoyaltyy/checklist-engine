// @ts-nocheck
// venice-doorman — transport for repo actions plus a cron half that sets a wake flag.
// Secrets: GITHUB_TOKEN, DOORMAN_KEY, DEPLOY_KEY. Vars: GITHUB_REPO, WAKE_BRANCH, DEPLOYER.
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET,POST,OPTIONS", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Max-Age": "86400" };
const WAKE_PATH = "agent/WAKE.json";
const WAKE_HEARTBEAT_MIN = 15, WAKE_FRESH_COMMIT_MIN = 20, WAKE_FRESH_FAIL_MIN = 30;
const enc = (s) => { const b = new TextEncoder().encode(s); let o = ""; for (let i = 0; i < b.length; i += 8192) o += String.fromCharCode.apply(null, b.subarray(i, i + 8192)); return btoa(o); };
@@MORE@@