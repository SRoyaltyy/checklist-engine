"""Master coverage v1.4: add-only successor to coverage_v1_3 (06490a8). Rows unchanged;
records combo v2 FAIL (model over many answers, not a master id). Reads no 2025+ data."""
import csv, collections, pathlib
here = pathlib.Path(__file__).parent
src = here.parent / "coverage_v1_3" / "master_coverage_v1_3.csv"
rows = list(csv.DictReader(open(src)))
for r in rows:
    r["status_v1_3"] = r["status"]
    r["source_v1_4"] = "v1.3 unchanged"
out = here / "master_coverage_v1_4.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(len(rows), dict(collections.Counter(r["status"] for r in rows)))
