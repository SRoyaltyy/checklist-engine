#!/usr/bin/env python3
"""Chain-based option features (per ticker per DoltHub date), from raw option_chain rows
(date, act_symbol, expiration, strike, call_put, vol, delta). Keeps only aggregates, never raw contracts.
near = first expiry with DTE>=7; far = expiry with DTE closest to 90 and DTE >= near+20.
Forward F per expiry from put-call parity on mids (strike minimising |C-P|, F=K+C-P); DoltHub has no underlying price and
its deltas are noisy on stale strikes, so moneyness is K/F, not delta.
skew10 = put IV at K~0.90F minus call IV at K~1.10F (near expiry, +-3% moneyness, bid>0) -> SKEW-HI >=0.05, SKEW-LO <=0
atm = mean call+put IV at the 2 strikes nearest F; term = atm_near/atm_far
exp_move = ATM straddle mid / F (implied move to near expiry); exp_move_iv = atm*sqrt(dte/365) kept as a cross-check.
Questions (same PIT/stale rules as build_opt.py): GK-OPX-SKEW-HI skew25>=0.05, GK-OPX-SKEW-LO skew25<=0,
GK-OPX-TERM-INV term>=1.10, GK-OPX-TERM-CTG term<=0.90, GK-OPX-MOVE-HI exp_move>=0.10, GK-OPX-MOVE-LO exp_move<=0.04."""
import numpy as np, pandas as pd
def fwd_atm(g):
    """Forward F = strike where |call_mid - put_mid| is smallest (put-call parity), F ~= K + (C-P). Returns F, ATM IV, straddle/F."""
    c = g[g.call_put == "Call"].set_index("strike"); p = g[g.call_put == "Put"].set_index("strike")
    k = c.index.intersection(p.index)
    if len(k) < 3: return np.nan, np.nan, np.nan, None, None
    cm = ((c.bid + c.ask) / 2)[k]; pm = ((p.bid + p.ask) / 2)[k]; ok = (c.bid[k] > 0) & (p.bid[k] > 0)
    if ok.sum() < 2: return np.nan, np.nan, np.nan, None, None
    d = (cm - pm)[ok]; k0 = d.abs().idxmin(); F = k0 + d[k0]
    if F <= 0: return np.nan, np.nan, np.nan, None, None
    kk = sorted(k[ok], key=lambda x: abs(x - F))[:2]
    iv = np.nanmean(np.r_[c.vol[kk].values, p.vol[kk].values]); strad = (cm[k0] + pm[k0]) / F
    return F, iv, strad, c, p
def iv_at(side, F, m):
    if side is None or side.empty: return np.nan
    x = (side.index.to_series() / F - m).abs(); i = x.idxmin()
    return side.vol[i] if x[i] <= 0.03 and side.bid[i] > 0 else np.nan
def one(g):
    d = g.name[0]; dte = (g.expiration - d).dt.days; ex = sorted(pd.to_datetime(g.expiration[dte >= 7].unique()))
    if not len(ex): return pd.Series(dtype=float)
    nr = ex[0]; dn = (nr - d).days
    F, atm, strad, C, P = fwd_atm(g[g.expiration == nr])
    far = [e for e in ex if (e - d).days >= dn + 20]
    fe = min(far, key=lambda e: abs((e - d).days - 90)) if far else None
    atf = fwd_atm(g[g.expiration == fe])[1] if fe is not None else np.nan
    return pd.Series(dict(fwd=F, skew10=iv_at(P, F, .90) - iv_at(C, F, 1.10), atm_near=atm, atm_far=atf,
                          term=atm / atf if atf > 0 else np.nan, dte_near=dn, exp_move=strad, exp_move_iv=atm * np.sqrt(dn / 365)))
def features(raw):
    raw = raw.copy(); raw["date"] = pd.to_datetime(raw.date); raw["expiration"] = pd.to_datetime(raw.expiration)
    for c in ("vol", "delta", "strike", "bid", "ask"): raw[c] = pd.to_numeric(raw[c], errors="coerce")
    import warnings; warnings.simplefilter("ignore")
    return raw.groupby(["date", "act_symbol"]).apply(one).reset_index()
QS = {"GK-OPX-SKEW-HI": ("skew10", lambda x: x >= .05), "GK-OPX-SKEW-LO": ("skew10", lambda x: x <= 0),
      "GK-OPX-TERM-INV": ("term", lambda x: x >= 1.10), "GK-OPX-TERM-CTG": ("term", lambda x: x <= .90),
      "GK-OPX-MOVE-HI": ("exp_move", lambda x: x >= .10), "GK-OPX-MOVE-LO": ("exp_move", lambda x: x <= .04)}
def codes(F):
    return np.stack([np.where(F[c].notna(), np.where(f(F[c]), 2, 1), 0) for c, f in QS.values()], 1).astype(np.uint8)
