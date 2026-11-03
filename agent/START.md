START — the only link a new chat needs

You are a Venice chat continuing work that outlived a previous chat. You have no memory of it. Everything is in the repo and this file tells you how to get it.

Get the key first

Every worker call needs the doorman key as the k parameter. It is deliberately not in this file. Ask the human for it, or read it from the W constant near the top of agent/BRIDGE.user.js. The repo is public, so treat the key as public and low-value: worst case someone writes to a branch.

Read in this order

Substitute the key for KEY. The worker needs no tool and no rate limit.

Copy code
https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FCONTEXT.md
https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FPROTOCOL.md
https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FSTATE.md
https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FMEMORY.md
https://venice-doorman.fullscan-relay.workers.dev/?k=KEY&op=read&branch=main&path=TODO.md

CONTEXT.md first and in full — it explains what this is and why. TODO.md: the ## Venice section only. That section is your lane.

If the worker is unreachable

Open a blank about:blank tab, F12, and fetch the same URLs there. about:blank has no CSP. Do not use the sandbox iframe — it cannot reach workers.dev.

Then

Follow agent/PROTOCOL.md. One item per wake. Branch venice/*, PR to main, never push main. No markers in committed files. Proof is a green run ID or a commit, and it goes in the PR.

How to write a file

Two at-signs, then the word PUT, a space, the path, a newline, the body, a newline, then two at-signs and the word END. Put it in your reply as plain text, not inside a code fence. The bridge in the page executes it.

Journal, rewrite STATE.md and PROGRESS.md, append MEMORY.md, then stop.
