# Frozen matching recipe (written before reading any forward outcome of match2.py run)
Frozen: 2026-10-22 17:38 HKT. Data: 2020-24 survivors only; no 2025-26 aggregates.
Reference: ARQT 2026-10-07. Code: match2.py, feats.py, feats2.py (shas below).
Universe: close>=5, dollar vol>1M/day.
A) Tight feature match: tolerances in match2.py `tol` (17 features).
B) Shape kNN: 25-day window; per-day body/upper wick/lower wick in ATR14 units, close path z-scored, %B path, log(vol/50d avg) path; RMS distance; 1 per ticker per month.
   Common-sense gate CS: body g:r20>=0.9, BB-mid slope up, dip<=4.2 ATR, %B>=0.12, dd_vs_run>=0.5, 5<=days since 20d high<=18.
Knee rule (similarity/n only, no returns): k* = largest k in {200,300,400,500} with dist_cutoff(k) <= 0.6 x median prefilter distance (typical random pair) AND dist_cutoff(k) <= 1.15 x dist_cutoff(100). If none, k*=200 and flag "few true twins".
Eyeball check judges chart resemblance only.
bea4bf150b64d9789c6713f18d3a3b435fb99e04b9b6cee0daafb0b0ac9169f9  match2.py
687db55fbcc3174be32ca18c5e825e26283e7eca4d393b0690f2fa2ab369c5bf  feats.py
d54ce7219c6c5bb7ff30e02e0538f93d06d3f5710ec72a2626cb74dfe0c6f2f5  feats2.py
Knee applied: k*=200 (cutoff 0.486 <= 0.488=0.6x0.814; k=300 cutoff 0.495 fails).
