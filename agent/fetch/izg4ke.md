# FETCH https://github.com/SRoyaltyy/checklist-engine/blob/venice/sec-options-pipelines/agent/MEMORY.md

fetched 2026-11-04T18:24:13.497Z status 200 ua Mozilla/5.0 venice-doorman

checklist-engine/agent/MEMORY.md at venice/sec-options-pipelines · SRoyaltyy/checklist-engine · GitHub 

 
 
 
 

 
 

 

 

 
 

 
 

 

 

 

 

 

 

 

 

 

 

 
 
 

 
 
 

 

 

 
 
 
 

 

 

 

 

 
 

 

 
 

 

 

 
 

 
 
 

 
 

 

 

 
 
 
 

 
 Skip to content 

 
 
 
 
 
 
 

 
 
 
 
 

 

 
 
 

 
 
 
 
 

 

 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 Navigation Menu Sign in Products Platform GitHub Repository hosting, code review, and collaboration Copilot AI coding agent for tasks, projects and automated work Build & Ship Actions CI/CD and automation Code Quality Quality analysis, fixes, and enforcement Codespaces Cloud development environments Secure Code Security Vulnerability detection and remediation Secret Protection Secret scanning and leak prevention All Features Developers Learn Documentation Training Certifications Build Build with Copilot Customize Copilot Integrations Explore Trending repos GitHub Sponsors Developer articles Changelog Changelog Your source for the latest features, improvements, and fixes across GitHub products, all in one place. Businesses By Stage Enterprises Team Startups Nonprofits By Industry Healthcare Financial services Manufacturing Government See all industries Evaluate GitHub Why GitHub Customer Stories Business insights Trust Center Add-ons GitHub Advanced Security Enterprise-grade code security Copilot for business Enterprise-grade AI features Premium Support Enterprise-grade 24/7 support Resources Learn & Connect Documentation Resource center Blog Events & webinars Community Forum Customer Stories Integrations Support Customer support Training GitHub Status Company About Partners Changelog GitHub Universe GitHub Universe The event for developers, by developers — talks, workshops, and what’s next for GitHub. Pricing Search / Sign in Sign up Appearance settings 
 

 
 
 
 
 
 You signed in with another tab or window. Reload to refresh your session. 
 You signed out in another tab or window. Reload to refresh your session. 
 You switched accounts on another tab or window. Reload to refresh your session. 

 
 
 
 Dismiss alert 

 
 
 

 

 

 
 
 
 
 
 
 
 
 
 
 
 {{ message }} 

 
 
 
 
 

 

 
 
 
 
 

 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 
 

 
 
 
 SRoyaltyy checklist-engine Repository navigation Code Issues Pull requests 47  ( 47 ) Actions Projects Security and quality Insights More items 
 

 

 
 
 

 
 
 

 
 
 
 Files Expand file tree venice/sec-options-pipelines Breadcrumbs checklist-engine / agent / MEMORY.md Copy path Blame More file actions Blame More file actions Latest commit   History History History 56 lines (38 loc) · 2.75 KB venice/sec-options-pipelines Breadcrumbs checklist-engine / agent / MEMORY.md Copy path Top File metadata and controls Preview Code Blame 56 lines (38 loc) · 2.75 KB Raw Copy raw file Download raw file Outline Edit and raw actions MEMORY — standing focus 
 Mandate, every wake 
 Open with three answers before any action: what was I doing last run, what is my plan now and
which goal does it serve, and what am I actually working on — harness code, James' lane
instructions, or something else. If the plan serves none of the goals, say so in a line or stop. 
 The goals, in order: 1 composer never blocks, 2 every prompt carries repair instructions,
3 GitHub work to James' instructions to completion with a percentage every turn. 
 Anything not advancing 1, 2 or 3 is a side quest. Name it and drop it. 
 Where they stand 
 
 Installed loader is 1.6 and the gate is live. Next: add @updateURL and @downloadURL so the
loader maintains itself instead of needing a paste. 
 Mechanism is this file plus agent/HANDOFF_1741.md. agent/WAKE_PROMPT.md has refused writes;
if it takes now, it carries the mandate directly and this section is the fallback. 
 No run verdict has ever returned. Fix is .github/workflows/probe_result.yml, which re-runs the
probe and always commits agent/RESULT.json with exit code, run ID and the last 4KB of output.
Read that file, not the actions API. 
 
 Writer rules 
 A body is cut at the first end marker inside it, newline optional. Marker on the closing line only.
A bare END as the closer makes the body swallow what follows. 
 cleanBody strips blank lines and chrome words (fences, Copy code, language tags) from head and
tail, twelve lines each. A short body can strip to nothing; keep real content first and last. 
 Never trust a raw read straight after a write; raw caches minutes. Read blob HTML, which keeps
angle brackets and is not cached the same way. base64 through contents also survives. 
 When a path refuses a second write, use a new path rather than fighting it. 
 scrape and dispatch debounce 60s per URL. A repeat inside that window is dropped and an older
delivery arrives, which looks like cache but is not. Vary the URL or space repeats. Parked items
carry their whole text, so 60KB bodies starve fresh small requests. 
 RUNS and DISPATCH are fire-and-forget: they log a status and deliver nothing. 
 Loader and bridge 
 The loader hashes the body and keys its bad list on the hash; a blacklisted hash is skipped
forever. Change the body, never a version number. It rolls back when the bridge object is absent
120s after boot, after one retry — the bridge sets that object synchronously, so a body that
parses is healthy and a rollback means a broken body. 
 Userscript push: PUT the file. Worker push: deployer with keep_bindings, verify with op=ops. 
 Working rules 
 Branch venice only, PR to main, never push main. No @@CUT or @@BODY markers. Every claim needs a
run ID or a commit; no proof means not done. A blocked item is recorded and abandoned, not
retried forever. 
 
 

 

 

 
 

 

 
 Footer 

 

 
 
 
 
 
 
 
 
 &copy; 2026 GitHub, Inc.
 
 

 
 Footer navigation 

 

 
 Terms 
 

 
 Privacy 
 

 
 Security 
 

 
 Status 
 

 
 Community 
 

 
 Docs 
 

 
 Contact 
 

 
 
 
 
 Manage cookies
 
 
 

 
 
 
 Do not share my personal information
 
 
 

 
 
 
 

 

 
 
 
 
 
 
 
 
 
 You can’t perform that action at this time.
