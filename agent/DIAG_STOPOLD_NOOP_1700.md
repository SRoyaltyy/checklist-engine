Root cause of the instance pile-up. Supersedes the "no guard" framing in PATCH_SINGLE_INSTANCE_1640.md. 2026-11-05T17:00Z

Loader 1.11 does call stopOld() at the top of boot. It looks guarded and is not. The line that follows installs a placeholder:

if (!window.__vrb || !window.__vrb.stop) window.__vrb = { stop: function () {}, sentinel: true };

A live bridge never publishes window.__vrb.stop, so the placeholder is what stopOld() finds, and it is a no-op. Every boot therefore adds an instance and removes none. Three boots visible on the console, three live bridges.

The damage that matters is not the count. It is window.__vrbSeen, one shared mark set for all instances. Instance A marks a directive line, instance B sees it marked and blanks it, and the line is consumed before either instance acts on it, or consumed twice. Either way the one-shot filter is defeated by a second instance even though the filter code is correct.

Fix chosen, loader only

Key the seen store per boot instead of globally. Each boot gets a token; the filter reads its store through that token. Instances stop sharing marks, so a duplicate can no longer erase another instance's directive. Directive will fire once per boot, which is the correct semantics, and the 60s refresh does not re-boot an unchanged body so it does not re-fire on its own.

Not fixed by this: instance count stays at three until the bridge publishes a real stop handle. Follow-up if it matters is a bridge edit, and the bridge body is only reachable through a channel that strips angle brackets, so it needs care.

Channel defect, noted

Delivered text loses angle-bracket runs. hash() arrives as "for (i = 0; i >> 0; return h.toString(36)" and the FILTER loop as "for(i=0;i >>0;k=...". Anything compared against the delivery must be treated as approximate, not exact.
