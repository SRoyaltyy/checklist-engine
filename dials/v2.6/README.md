# Dial table draft 2.6 (frozen)

Lever 5 (history) update from round-3 reads: 12 new ATR-relative descriptors (bull/bear versions) and a phase-list layer (3-ATR leg rule). Totals: 433 dial rows, 810 history rows, 6,599 base + 7,989 history = 14,588 questions.

| File | sha256 | Drive |
|---|---|---|
| HISTORY_LEVER_v2.6.csv | 33c66afb7ce8be6fc2b2f637901110785a3c9bf25ad436e44fd4084aca07d704 | https://drive.google.com/file/d/1PNvsDF9kmLcSFY0HByVkLc1ba68oJv9V/view |
| DIAL_TABLE_v2.6.csv | 7d595fbb8ffca24a43cc63f5453694ab592b726b8b3ec7cc6de4a23c720c423c | https://drive.google.com/file/d/1Sg-MWm3zXISszixeWjG3Xl5rzVW6jQSs/view |
| gen4_v2.6.py | 45d46cecd7c236e637dda959b517e3f094eba04d6fd36bb4fbbb9f6f1feaf0c4 | https://drive.google.com/file/d/1CCEPv1VhX7UihgWcvKeQSP26gqPiyfW5/view |
| counts.json | d09a22a48c53029a1f0aebd80574a8c56d4ed8b9fa489bd6a45b24d16403b6c7 | (box only) |

Regenerate: `python3 gen4_v2.6.py` (writes DIAL_TABLE.csv, HISTORY_LEVER.csv, counts.json).
