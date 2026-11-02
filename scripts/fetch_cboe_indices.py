#!/usr/bin/env python3
"""Fetch CBOE daily index histories (VIX family, SKEW, OVX, GVZ).
PIT: date D's close usable from next session only.
Usage: fetch_cboe_indices.py [--out data/cboe_indices]
Idempotent overwrite of CSVs (source is full history each time).
"""
import argparse, hashlib, os, urllib.request
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SERIES = ["VIX", "VIX9D", "VIX3M", "VVIX", "SKEW", "OVX", "GVZ"]
URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{s}_History.csv"

def fetch(out):
    os.makedirs(out, exist_ok=True)
    sums = []
    for s in SERIES:
        url = URL.format(s=s)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=60) as r:
            b = r.read()
        path = os.path.join(out, f"{s}_History.csv")
        open(path, "wb").write(b)
        h = hashlib.sha256(b).hexdigest()
        sums.append(f"{h}  {s}_History.csv")
        lines = b.count(b"\n")
        last = b.rstrip().split(b"\n")[-1].decode("utf-8", "replace")
        print(s, "bytes", len(b), "lines", lines, "last", last)
    open(os.path.join(out, "SHA256SUMS.txt"), "w").write("\n".join(sums) + "\n")
    print("wrote", out)

if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--out", default="data/cboe_indices")
    fetch(a.parse_args().out)
