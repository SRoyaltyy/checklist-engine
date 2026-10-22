#!/usr/bin/env python3
"""Convert runner CSVs (out/answers_<T>_<D>.csv) to viewer/data/<T>_<D>.json + viewer/data/index.json."""
import csv, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; OUT = HERE / "viewer" / "data"; OUT.mkdir(parents=True, exist_ok=True)
files = [Path(p) for p in sys.argv[1:]] or sorted((HERE / "out").glob("answers_*.csv"))
for p in files:
    rows = list(csv.DictReader(open(p, newline="")))
    if not rows: continue
    t, d = rows[0]["ticker"], rows[0]["date"]
    json.dump({"ticker": t, "date": d, "rows": [[r["row_id"], r["owner"], r["answer"], r["reason"], r["data_as_of"]] for r in rows]},
              open(OUT / f"{t}_{d}.json", "w"), separators=(",", ":"))
idx = sorted({tuple(f.stem.rsplit("_", 1)) for f in OUT.glob("*_*.json")})
json.dump([{"ticker": t, "date": d, "file": f"{t}_{d}.json"} for t, d in idx], open(OUT / "index.json", "w"), indent=0)
print(len(idx), "runs in index")
