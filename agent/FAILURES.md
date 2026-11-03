FAILURES — every fault hit, and what fixed it

Chronological. Most are one class: characters lost during percent-encoded chunked writes.

1. Context ceiling, original chat

Millions of words, no bound. Diagnosed as pre-generation rejection, model-independent. Fix: bound the history with rollover.

2. No failure detection

Ten consecutive agent: wake flag commits over 2.5 h with zero work. Fix: healthTick() counts Response failed, escalates at 2.

3. lastFailSeen never reset

Escalation repeated forever. Fix: reset in escalate(), prime once with failPrimed.

4. clickNewChat fallback killed the promise chain

Bootstrap never sent. Fix: write vrb.bootPending before navigating, resume on init.

5. busy never cleared after escalate

Every later tick bailed permanently. Fix: clear in escalate().

6. Wake sha stored on a bailed wake

Reason consumed forever. Fix: wake() returns boolean, sha stored only on true.

7. Deployer URL had no scheme and a trailing newline

Invalid URL. Fix: strip whitespace, drop trailing slashes, prepend https://.

8. GITHUB_TOKEN lacked contents read

Source fetch 403. Fix: read raw.githubusercontent.com unauthenticated instead.

9. Cloudflare 1042

Traced to a stale deployer build. Fix: v field in every response plus op=ping to identify the live build.

10. Cloudflare 415 twice

Content type rejected. Fix: multipart with a metadata part declaring main_module.

11. Whole binding set wiped

The deploy probe deployed without bindings, stripping every variable and secret. GITHUB_REPO unset on all ops. Fix: keep_bindings=plain_text,secret_text plus echoing plaintext bindings into metadata.

12. ~30 lost + operators in the bridge

From percent-encoding during chunked writes. Every string concat broke. The file had never once parsed. Fix: acorn parse loop, insert + at the reported offset.

13. wake() never called step()

busy = true; paint(); return true; sat above var chunks and the two function declarations, so everything after was dead code and busy stuck true forever. Fix: hoist the var, call step() before the return.

14. wake() was missing its closing brace

finish() closed, then waitFor began, nesting every later function one level deep. Fix: insert }.

15. Loader ran the bridge in page scope

GM_xmlhttpRequest is not defined. Fix: pass the GM functions into new Function as parameters.

16. Regexes lost their +

[ \t] (\S ) instead of [ \t]+(\S+). Parses fine, matches wrong. Fix: literal replacements.

Lesson

Byte counts prove nothing. Parse before writing, every time. Size checks missed thirty syntax errors and a missing brace.
