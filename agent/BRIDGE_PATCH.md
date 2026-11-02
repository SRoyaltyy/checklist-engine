# Bridge patch v4.0 -> v4.1

The wake prompt lives in agent/WAKE_PROMPT.md now, so it can change without touching the script.

## READS
Add PROGRESS.md, shrink the tails.

Replace the JOURNAL and TEST_LOG entries with:
`agent/PROGRESS.md`, `agent/JOURNAL.md`, `agent/TEST_LOG.txt`

In wake(), change `tail(t, 7000)` to `tail(t, 3000)` and `tail(t, 4000)` to `tail(t, 2500)`.

## finish()
Replace the whole function with:

```js
    function finish() {
      gm(readUrl('agent/WAKE_PROMPT.md')).then(function (r) {
        var tpl = r.ok ? unwrap(r.text) : '';
        var lines = tpl.split('\n');
        var head = (lines.shift() || '[wake {{TIME}}] {{REASON}}')
          .replace('{{TIME}}', new Date().toISOString())
          .replace('{{REASON}}', reason);
        var text = head + '\n\n' + chunks.join('\n\n') + '\n\n' + lines.join('\n');
        if (!tpl.trim()) text = head + '\n\n' + chunks.join('\n\n') + '\n\n[WAKE_PROMPT.md unavailable]';
        fill(el, text);
        setTimeout(function () {
          nodesAtSubmit = msgNodes();
          awaitingSince = Date.now();
          submit(el);
          store('vrb.cool', String(Date.now()));
          busy = false; paint();
        }, 250);
      });
    }
```

The fallback keeps a wake working if the prompt file is ever missing.
