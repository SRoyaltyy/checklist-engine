Repairs for gm, readback, putFile. 2026-11-05T18:00Z

gm survives as onload: function (r) { res({ ok: r.status >= 200 && r.status and then the delivery jumps into readback, so the status test and the failure arms are gone. Restore:

onload: function (r) { res({ ok: r.status >= 200 && r.status < 300, status: r.status, text: r.responseText }); },
onerror: function () { res({ ok: false, status: -1, text: '' }); },
ontimeout: function () { res({ ok: false, status: -2, text: '' }); }

readback survives as ... Math.abs(got.length - content.length) and then the log line with (ok ? ' OK' : ' MISMATCH'). The comparison is a length equality plus a small tolerance, so restore:

var ok = got.length === content.length;

immediately after got is obtained, and keep the existing log and return shape unchanged.

putFile is intact apart from the call into readback; leave it.

Three cautions, because these are the ones that fail quietly:

A readback that always returns ok is worse than none, so do not simplify the length check away. A missing onerror arm leaves a promise that never settles and hangs the wake loop, so both arms matter more than the status message. -1 and -2 are distinct on purpose so a transport failure is distinguishable from an HTTP failure in the console.

Also note: r.responseText is what the rest of the file expects from gm, so any rewrite must keep that field name or every caller breaks.
