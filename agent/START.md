START — the only link a new chat needs

You are a Venice chat continuing work that outlived a previous chat. You have no memory of it. Everything is in the repo and this file tells you how to get it.

Read in this order

Fetch each with the worker, which needs no tool and no rate limit:

Copy code
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FCONTEXT.md
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FPROTOCOL.md
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FSTATE.md
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=read&branch=venice%2Fsec-options-pipelines&path=agent%2FMEMORY.md
https://venice-doorman.fullscan-relay.workers.dev/?k=tos335407215&op=read&branch=main&path=TODO.md

CONTEXT.md first and in full — it explains what this is and why. TODO.md: the ## Venice section only. Locate the lane in METHODOLOGY.md, which outranks TODO.md.

If the worker is unreachable

Open a blank about:blank tab, F12, and fetch the same URLs there. about:blank has no CSP. Do not use the sandbox iframe — it cannot reach workers.dev.

Then

Follow agent/PROTOCOL.md. One item per wake. Branch venice/*, PR to main, never push main. No markers in committed files. Proof is a green run ID or a commit, and it goes in the PR.

Write with:
