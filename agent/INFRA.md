INFRA — how the machinery works

Do not change any of this without reading it through. Each piece exists because something failed.

Topology
Copy code
Venice chat (browser)
  └─ Tampermonkey loader      fetches bridge, version-checks, re-executes
      └─ Bridge               polls flag, assembles prompt, types, submits, rolls
          └─ venice-doorman   Worker: GitHub API transport + cron
              └─ venice-deployer   Worker: redeploys doorman from repo source
                  └─ GitHub repo  SRoyaltyy/checklist-engine
The wake cycle
Cron on venice-doorman every 15 min sets agent/WAKE.json to pending: true with a reason.
Bridge tick() polls WAKE.json every 30 s.
If the reason carries a sha not yet seen, and the composer is empty, and not paused, and past the 240 s cooldown, wake() runs.
wake() reads nine state files, appends the TODO.md Venice lane, prepends WAKE_PROMPT.md, fills the composer, submits.
The model does one item, writes via @@PUT, updates JOURNAL.md, STATE.md, PROGRESS.md.
Directives the bridge scans for
Directive	Effect
@@PUT path …
