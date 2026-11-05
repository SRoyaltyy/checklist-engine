Update to DIAG_DOUBLE_INSTANCE_1640. 2026-11-05T16:50Z

Instance count is now three, not two. Console at 16:50Z shows wake go three times per wake and bail: generating three times per scan. "resend stranded" repeats between them, so the stranded pending flag is now feeding all three and each one resends.

Badge finding, and the end of the badge gate

Badge reads wakeg15 v51 and stays visible. v51 is the bridge header version, which the loader deliberately does not patch, so the badge cannot display a loader version and the "badge must read LOADER v1.11" condition was never achievable as written. The loader is pasted and working: put agent/LOADER4.user.js 200 with readback 7113/7113 OK, filter line intact, boots with no eval failure. Gate satisfied in substance. Badge demoted to cosmetic.

All five record PUTs landed with matching readbacks this wake, so the earlier "unconfirmed write" caveats in STATE and PROGRESS are now stale and can be cleared next rewrite.

New delivery defect

Scrape of the loader reported 200 and delivered 5778 bytes from the raw URL. The loader on disk is 7113 bytes. Difference 1335. Either the delivery caps content or the raw read was partial. Do not patch from the delivered text until the tail is confirmed present, or the loader loses its last section.

Guard spec stands as written in PATCH_SINGLE_INSTANCE_1640.md. With three instances the filter cannot be trusted at all, so the guard is the only item.
