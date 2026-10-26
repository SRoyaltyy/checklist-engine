"""Accept already-downloaded prices after explicit exclusions; fetch no market data."""
import csv
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

EXPECTED_HASHES={
"prices/FULL_PRICE_RECONCILIATION_AUDIT.json":"caf24f83b656e3f9125be79f4cf0b51e1e65bd466df99dd2572e3d06104d3505",
"listings/CURRENT_LISTING_CLASSIFICATION.csv":"e2ffbe14fbb2fa19ea032e7267771be2187071ea057332bdd80c8c5670280a5f",
"EXCLUDED.csv":"555c4af64f6b25b86e0d1cf9d721bd14fc097edf5b9fb0dc167f08e1cbb84c98",
}

def validate(results,excluded,classification,cutoff):
    universe=set(results)
    if set(classification)!=universe:raise ValueError("classification universe differs")
    names=[r["ticker"] for r in excluded]
    if len(set(names))!=len(names):raise ValueError("duplicate exclusion ticker")
    if not set(names)<=universe:raise ValueError("exclusion outside canonical universe")
    if any(not r.get("reason","").strip() for r in excluded):raise ValueError("blank exclusion reason")
    accepted=[]
    for ticker in sorted(universe-set(names)):
        r=results[ticker]
        if r.get("status")!="PASS":raise ValueError("unlogged failed source: "+ticker)
        if r.get("short_history_all_sessions_exact") or r.get("overlap_rows",0)<60:
            raise ValueError("short history not excluded: "+ticker)
        if r.get("all_overlap_volumes_zero"):raise ValueError("zero-volume basis not excluded: "+ticker)
        if r.get("supplemental_end")!=cutoff:raise ValueError("stale or unknown end: "+ticker)
        if r.get("frozen_values_unchanged") is not True:raise ValueError("frozen values not proved unchanged: "+ticker)
        if r.get("supplemental_basis")!="vendor_split_adjusted_quote_matching_frozen":
            raise ValueError("unexpected quote basis: "+ticker)
        for key,low,high in (("median_return_difference",0,.002),("p99_return_difference",0,.02),("median_volume_ratio",.8,1.25)):
            value=r.get(key)
            if not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
                raise ValueError("bridge metric fails: "+ticker+" "+key)
        accepted.append({"ticker":ticker,"current_listing_classification":classification[ticker],
            "overlap_rows":r["overlap_rows"],"last_price_session":r["supplemental_end"],
            "source_basis":r["supplemental_basis"],"status":"SOURCE_ACCEPTED_NOT_WORLD_GATE"})
    return accepted

def main():
    root=Path("source-acceptance-input")
    for name,wanted in EXPECTED_HASHES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=wanted:
            raise ValueError("source evidence changed: "+name)
    audit=json.loads((root/"prices/FULL_PRICE_RECONCILIATION_AUDIT.json").read_text())
    if (audit["source_commit"]!="1a822a1b1b96886bba5621f2be1e25709f67a6db" or
        audit["source_tag"]!="world-prices-v3-40259691137-1" or len(audit["results"])!=8727 or
        not audit.get("all_archives_verified") or audit.get("missing") or audit.get("duplicate_source_names")):
        raise ValueError("incomplete or unexpected immutable archive audit")
    with (root/"EXCLUDED.csv").open(newline="") as fh:excluded=list(csv.DictReader(fh))
    with (root/"listings/CURRENT_LISTING_CLASSIFICATION.csv").open(newline="") as fh:
        listing=list(csv.DictReader(fh))
    if len({r["ticker"] for r in listing})!=len(listing):raise ValueError("duplicate listing ticker")
    classification={r["ticker"]:r["classification"] for r in listing}
    accepted=validate(audit["results"],excluded,classification,"2026-10-23")
    original_counts=Counter(classification.values())
    accepted_counts=Counter(r["current_listing_classification"] for r in accepted)
    out=Path("price-source-acceptance");out.mkdir(exist_ok=True)
    target=out/"ACCEPTED_PRICE_INVENTORY_V6.csv"
    with target.open("w",newline="",encoding="utf-8") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(accepted[0]));writer.writeheader();writer.writerows(accepted)
    summary={"status":"SOURCE_ACCEPTANCE_PASS_WITH_EXCLUSIONS",
        "as_of_completed_session":"2026-10-23","source_tag":audit["source_tag"],
        "source_collection_run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/40259691137",
        "archive_and_member_hash_proof_run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/40281068048",
        "acceptance_run":"https://github.com/SRoyaltyy/checklist-engine/actions/runs/"+os.environ["GITHUB_RUN_ID"],
        "source_commit":os.environ["GITHUB_SHA"],"input_hashes":EXPECTED_HASHES,
        "original_universe":len(audit["results"]),"explicit_exclusions":len(excluded),"accepted_source_tickers":len(accepted),
        "original_listing_classification":dict(original_counts),"accepted_listing_classification":dict(accepted_counts),
        "current_non_etf_clean_inventory_pct":100*accepted_counts["NON_ETF"]/original_counts["NON_ETF"],
        "strict_minimum_overlap":60,"all_accepted_sources_current":True,"all_frozen_values_unchanged":True,
        "inventory_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_fetched_gate":"PASS_WITH_EXPLICIT_EXCLUSIONS",
        "historical_tradeable_97pct_gate":"NOT_RUN: PIT liquidity and nominal market-cap eligibility remain",
        "world_coverage_gate":"NOT_RUN: all required context/feature blocks still needed",
        "notes":["No new market-data download and no excluded edge-case repairs.",
          "Only existing immutable source evidence was read.",
          "The 242 diagnostic short matches are excluded, never used to waive the 60-session bridge minimum.",
          "Current listing inventory is not historical tradeability; 12 accepted UNKNOWN classifications require explicit later policy.",
          "Source acceptance does not establish point-in-time nominal prices or dividend/split liquidity/size inputs."]}
    (out/"PRICE_SOURCE_ACCEPTANCE_V6.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
