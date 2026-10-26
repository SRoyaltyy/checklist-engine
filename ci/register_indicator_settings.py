"""Explicit research configurations approved by the 2026-10-26 owner review.

This registers configurations; registration is not a measured feature-coverage claim.
Short/long are research choices. They are not alleged TradingView defaults.
"""
import csv
import json
from pathlib import Path

# id: parameter names, short/default/long tuples. Non-length parameters keep
# their own units; they are never blindly rounded or scaled as periods.
GRIDS = {
"I028": ("fastk,slowk,slowd", [(5,3,3),(14,3,3),(21,5,5)]),
"I029": ("period", [(7,),(14,),(28,)]),
"I030": ("fast,slow,signal", [(5,35,5),(12,26,9),(8,17,9)]),
"I034": ("period", [(7,),(14,),(28,)]),
"I036": ("period", [(10,),(20,),(40,)]),
"I037": ("period", [(7,),(14,),(28,)]),
"I038": ("fast,slow", [(3,17),(5,34),(10,68)]),
"I039": ("mean_period", [(7,),(14,),(28,)]),
"I040": ("ema_period", [(7,),(13,),(26,)]),
"I041": ("period", [(7,),(14,),(28,)]),
"I042": ("period", [(11,),(21,),(42,)]),
"I043": ("period", [(5,),(9,),(18,)]),
"I044": ("roc1,roc2,roc3,roc4,sma1,sma2,sma3,sma4,signal",
          [(5,8,10,15,5,5,5,8,5),(10,15,20,30,10,10,10,15,9),(20,30,40,60,20,20,20,30,18)]),
"I045": ("wma,roc1,roc2", [(5,7,6),(10,14,11),(20,28,22)]),
"I046": ("fast,slow,signal", [(6,13,5),(12,26,9),(24,52,18)]),
"I047": ("period", [(5,),(10,),(20,)]),
"I048": ("period", [(5,),(10,),(20,)]),
"I049": ("std_period,rma_period", [(5,7),(10,14),(20,28)]),
"I050": ("short,long,signal", [(3,10,3),(5,20,5),(10,40,10)]),
"I051": ("range_period,smooth1,smooth2", [(5,2,2),(10,3,3),(20,6,6)]),
"I052": ("rsi,stoch,k,d", [(7,7,2,2),(14,14,3,3),(28,28,6,6)]),
"I053": ("period", [(9,),(18,),(36,)]),
"I054": ("long,short", [(13,7),(25,13),(50,26)]),
"I055": ("period1,period2,period3", [(4,7,14),(7,14,28),(14,28,56)]),
"I056": ("price_rsi,streak_rsi,rank", [(2,2,50),(3,2,100),(6,4,200)]),
"I057": ("atr_period,multiplier,stop_period", [(5,1,5),(10,1,9),(20,1,18)]),
"I058": ("period", [(7,),(14,),(28,)]),
"I059": ("ema_period,sum_period", [(5,13),(9,25),(18,50)]),
"I060": ("period", [(7,),(14,),(28,)]),
"I061": ("acceleration,maximum", [(.01,.1),(.02,.2),(.04,.4)]),
"I062": ("atr_period,multiplier", [(5,3),(10,3),(20,3)]),
"I063": ("period,multiplier", [(11,3),(22,3),(44,3)]),
"I064": ("period,multiplier", [(10,2),(20,2),(40,2)]),
"I065": ("jaw,teeth,lips,jaw_shift,teeth_shift,lips_shift",
          [(7,4,3,4,3,2),(13,8,5,8,5,3),(26,16,10,16,10,6)]),
"I066": ("left,right", [(1,1),(2,2),(4,4)]),
"I067": ("reversal_percent", [(2.5,),(5,),(10,)]),
"I068": ("period", [(50,),(100,),(200,)]),
"I069": ("period", [(10,),(20,),(60,),(120,)]),
"I071": ("period", [(7,),(14,),(28,)]),
"I072": ("period", [(7,),(14,),(28,)]),
"I073": ("period", [(5,),(21,),(63,),(126,),(252,)]),
# Pivot anchors are completed calendar blocks, not fake numerical lengths.
"I074": ("anchor", [("week",),("month",),("quarter",)]),
"I075": ("left,right", [(5,5),(10,10),(20,20)]),
"I076": ("atr_period,reversal_atr", [(14,2),(14,3),(14,5)]),
"I077": ("last_pivots,pivot_left,pivot_right", [(2,2,2),(3,2,2),(5,2,2)]),
"I080": ("period", [(5,),(20,),(50,)]),
"I084": ("period", [(7,),(14,),(28,)]),
"I088": ("period", [(10,),(20,),(40,)]),
"I089": ("fast,slow", [(2,5),(3,10),(6,20)]),
"I090": ("period", [(7,),(14,),(28,)]),
"I091": ("ema_period", [(7,),(13,),(26,)]),
"I092": ("fast,slow,signal", [(17,28,7),(34,55,13),(68,110,26)]),
"I095": ("fast,slow,signal", [(6,13,5),(12,26,9),(24,52,18)]),
"I098": ("period,deviation", [(10,1.5),(20,2),(50,2.5)]),
"I099": ("ema_period,atr_period,multiplier", [(20,14,1),(20,14,1.5),(20,14,2)]),
"I101": ("period", [(10,),(20,),(55,)]),
}
RAW_DERIVED = {
"I093": ("ema_period", (10,20,40), "EMA of the raw NVI and PVI; raw cumulative base 1000 retained"),
"I094": ("sum_period", (5,20,60), "rolling sum of raw V*sign(close change); raw series retained"),
"I096": ("ema_period", (10,20,40), "EMA of the raw cumulative PVT; raw series retained"),
}
NOTES = {
"I039": "Raw BOP is also retained; mean_period smooths raw BOP as in the registered dictionary definition.",
"I066": "Publish a pivot only after right bars have closed; never write it back onto its unconfirmed pivot date.",
"I067": "Only confirmed percentage-reversal pivots; live extremes are not confirmed pivots.",
"I073": "All five explicit horizons plus calendar YTD from the prior year-end close.",
"I074": "Traditional pivots from prior completed week/month/quarter; current partial block is never used.",
"I075": "Strict pivots; ties disqualify. Availability is after the right-hand confirmation bars close.",
"I076": "Last two confirmed ATR-reversal pivots, ATR frozen at each running extreme; levels 0.236/0.382/0.5/0.618/0.786.",
"I077": "Arithmetic mean of last K confirmed strict highs/lows. Unknown when fewer than K pivots exist.",
"I069": "Pearson correlation of stock and SPY native-candle returns; pairwise identical candle boundaries required.",
"I070": "Annualized log-return sample volatility; daily sqrt(252), k-day sqrt(252/k), monthly sqrt(12).",
}
def registry():
    items = {}
    for ident, (names, values) in GRIDS.items():
        keys = names.split(",")
        labels = ["short","default","long"] if len(values)==3 else [
            "default" if (ident in ("I069","I070") and v==(20,)) or
                         (ident=="I073" and v==(21,)) else "window_" + str(v[0])
            for v in values]
        items[ident] = {"settings": [
            {"name": label, "kind": "native", "parameters": dict(zip(keys, row))}
            for label,row in zip(labels,values)], "note": NOTES.get(ident,"")}
    for ident,(key,values,note) in RAW_DERIVED.items():
        items[ident] = {"settings": [{"name":"default","kind":"raw","parameters":{}}] + [
            {"name":name,"kind":"derived","parameters":{key:v}}
            for name,v in zip(("short","medium","long"),values)], "note":note}
    items["I070"]={"settings":[{"name":"default","kind":"native","parameters":{"period":20}}]+[
        {"name":name,"kind":"derived","parameters":{"period":20,"ema_period":n}}
        for name,n in zip(("short","medium","long"),(10,20,40))],
        "note":"I070 retains HV(20) only. The extra HV(10/60/120) windows belong to I209. Derived variants smooth HV(20); annualization follows native candle duration."}
    return {"version":"phase1-settings-v1","status":"REGISTERED_NOT_MEASURED_COVERAGE",
            "units":"Periods count native completed candles, unless explicitly calendar anchors.",
            "timeframes":[f"{k}d" for k in range(1,22)]+["monthly"],
            "items": dict(sorted(items.items()))}

def write(root):
    spec=registry()
    (root/"dictionary/INDICATOR_SETTINGS.json").write_text(json.dumps(spec,indent=2)+"\n",encoding="utf-8")
    target=root/"dictionary/WORLD_SNAPSHOT_DICTIONARY.csv"
    with target.open(encoding="utf-8-sig",newline="") as fh:
        reader=csv.DictReader(fh); fields=reader.fieldnames; rows=list(reader)
    for row in rows:
        ident=row["id"]
        if ident=="C01":
            row.update(setting="world: 1d through 21d plus calendar monthly",
                definition="World candles: non-overlapping k-session OHLCV blocks anchored to a supplied shared market-session calendar for cross-entity builds, otherwise the first supplied entity session; O first, H max, L min, C last, V sum. Calendar monthly uses the prior completed calendar month. A candle becomes available on the next observed session (monthly: next calendar month); incomplete candles are excluded. Legacy engine.kbars rolling-offset composites are a separate feature definition, never silently substituted for native world candles.",
                window="k completed sessions or one completed calendar month",
                rolling_or_fixed="fixed non-overlapping world candles",
                pit_rule="Candle end < query day D; only completed candles with available_from <= D. D open is execution only.",
                warmup="Per indicator native-candle warmup; insufficient history remains blank.",
                parameters="k="+ "|".join(map(str,range(1,22))) + "; calendar=monthly; anchor=shared market-session calendar when supplied, otherwise first entity session",
                in_code="world_timeframes.completed_candles")
        elif ident in spec["items"]:
            item=spec["items"][ident]
            row["setting"]="explicit research grid; default retained"
            row["parameters"]="; ".join(s["name"]+" ["+s["kind"]+"]: "+
                (",".join(f"{k}={v}" for k,v in s["parameters"].items()) or "parameterless raw")
                for s in item["settings"])
            if item["note"]: row["parameters"] += "; " + item["note"]
            row["parameters"] += "; registry=dictionary/INDICATOR_SETTINGS.json; stack with every native timeframe"
    additions=json.loads((root/"dictionary/BAR_STATISTICS_REGISTRY.json").read_text(encoding="utf-8"))["items"]
    existing={row["id"] for row in rows}
    for item in additions:
        record=dict(id=item["id"],group="8 Expanded bar statistics",item=item["item"],
            setting="explicit native-candle grid",definition=item["definition"],
            inputs="completed native OHLCV; explicit PIT eligibility and matching benchmark intervals where required",
            window=item["parameters"],rolling_or_fixed="rolling over completed native candles",
            pit_rule="Only candles completed before buy day D; context and universe eligibility must be point-in-time.",
            warmup="Full registered window; unavailable or zero-denominator estimates remain blank.",
            edge_cases="No forward fill of mismatched candle boundaries; registration does not claim full-world measured coverage.",
            in_code=("world_food_statistics" if 221<=int(item["id"][1:])<=226 else "world_bar_statistics")+"; "+item["columns"],parameters=item["parameters"]+"; stack with all 22 native timeframes")
        if item["id"] in existing:
            rows=[record if r["id"]==item["id"] else r for r in rows]
        else:rows.append(record)
    with target.open("w",encoding="utf-8",newline="") as fh:
        writer=csv.DictWriter(fh,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    audit=root/"docs/INDICATOR_SETTINGS_COUNTS.csv"
    with audit.open("w",encoding="utf-8",newline="") as fh:
        writer=csv.writer(fh);writer.writerow(["id","registered_settings","native_settings","raw_settings","derived_settings","status"])
        for ident,item in spec["items"].items():
            ss=item["settings"]
            writer.writerow([ident,len(ss),*[sum(s["kind"]==k for s in ss) for k in ("native","raw","derived")],
                             "REGISTERED_NOT_MEASURED_COVERAGE"])
    return spec

if __name__=="__main__":
    spec=write(Path(__file__).resolve().parents[1])
    print(json.dumps({"registered_items":len(spec["items"]),
       "settings":sum(len(i["settings"]) for i in spec["items"].values()),
       "timeframes":len(spec["timeframes"])}))
