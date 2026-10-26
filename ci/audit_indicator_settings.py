"""Validate registration without mistaking it for full-world feature coverage."""
import argparse
import csv
import json
from pathlib import Path
from world_indicator_settings import load_settings,SUPPORTED_IDS
from world_timeframes import TIMEFRAMES

def audit(root):
    spec=load_settings()
    if tuple(spec["timeframes"])!=TIMEFRAMES:raise ValueError("dictionary/runtime timeframe mismatch")
    with (root/"dictionary/WORLD_SNAPSHOT_DICTIONARY.csv").open(encoding="utf-8-sig",newline="") as fh:
        rows={row["id"]:row for row in csv.DictReader(fh)}
    required={f"I{n:03}" for n in [*range(36,78),*range(88,97),28,29,30,34,80,84,98,99,101]}
    if not required<=spec["items"].keys():raise ValueError("missing required settings")
    for ident,item in spec["items"].items():
        settings=item["settings"]
        if len(settings)<3 or sum(s["name"]=="default" for s in settings)!=1:
            raise ValueError("missing explicit grid/default: "+ident)
        if len({json.dumps(s["parameters"],sort_keys=True) for s in settings})!=len(settings):
            raise ValueError("duplicate setting: "+ident)
        if any("50%" in rows[ident][key] or "TV default" in rows[ident][key]
               for key in ("setting","parameters")):raise ValueError("vague setting: "+ident)
        for setting in settings:
            for key,value in setting["parameters"].items():
                if f"{key}={value}" not in rows[ident]["parameters"]:
                    raise ValueError("CSV and registry disagree: "+ident)
    core=rows["C01"]
    if "k="+"|".join(map(str,range(1,22))) not in core["parameters"] or "monthly" not in core["parameters"]:
        raise ValueError("C01 grid differs")
    additions=json.loads((root/"dictionary/BAR_STATISTICS_REGISTRY.json").read_text(encoding="utf-8"))["items"]
    for item in additions:
        if rows[item["id"]]["definition"]!=item["definition"]:
            raise ValueError("new statistic absent or definition differs: "+item["id"])
    result={"new_bar_statistic_items":len(additions),"status":"REGISTRATION_PASS_NOT_WORLD_COVERAGE",
            "registered_items":len(spec["items"]),
            "registered_settings":sum(len(x["settings"]) for x in spec["items"].values()),
            "native_timeframes":list(TIMEFRAMES),
            "implemented_recipe_items":len(SUPPORTED_IDS),
            "pending_recipe_items":sorted(set(spec["items"])-SUPPORTED_IDS),
            "world_coverage_gate":"NOT_RUN"}
    return result

if __name__=="__main__":
    root=Path(__file__).resolve().parents[1]
    print(json.dumps(audit(root),indent=2))
