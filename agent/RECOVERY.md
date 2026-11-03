RECOVERY

Read only when something is broken.

Badge gone, or no badge ever

Loader not running. Check Tampermonkey: loader present, enabled, site access allowed. Console for [loader].

[loader] eval failed means the bridge does not parse. Get the offset with acorn from jsDelivr, fix, parse, write. Never write unparsed.

Badge idle, wake g0, nothing happens

Look for [bridge] bail: in the console. The message names the blocker.

bail: busy — a wake died mid-run and never cleared the flag. Reload the page.
bail: composer not empty — clear the message box. Attachments do not block, text does.
bail: cooldown — double click, which forces past it.
nothing at all — vrb.sha matches the current reason. Clear it: localStorage.removeItem('vrb.sha').
HALT

Two bootstraps failed. agent/HALT.json holds the reason.

Copy code
localStorage.removeItem('vrb.halt'); localStorage.removeItem('vrb.paused'); location.reload();
A binding went missing

GITHUB_REPO unset, DEPLOYER unset, or bad key. Re-add per agent/PREREQS.md. Deploy only through the deployer, which preserves bindings.

Everything 400s

Read the error body. bad key is a wrong DOORMAN_KEY. unset is a missing variable. Anything else is a code fault — diff against venice/calendar-announce-ledger and parse before writing.

The doorman is a stub

op=putprobe overwrites the script with a one-line worker. Restore by calling the deployer directly, never through the doorman, since a stub serves no ops.

This chat is dead and the rollover never came

Read agent/STATE.md and agent/PROGRESS.md, open a new agentic chat, paste both, plus TODO.md Venice section. Branch venice/*, PR to main, no markers. Do not reconcile old history.
