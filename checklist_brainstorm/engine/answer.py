#!/usr/bin/env python3
"""Single runner: python3 answer.py --ticker X --date YYYY-MM-DD [--out file.csv]
Scans engine/readers/ (primary) then /workspace/tf/engine/readers/ (fallback), dedup by real path.
Joins every reader's output to every row id in merged_draft_v8.2.csv; one deterministic CSV."""
import argparse, csv, importlib.util, os, sys
from collections import Counter, defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
SHEET = HERE.parent / "merged_draft_v8.2.csv"
READER_DIRS = [HERE / "readers", Path("/workspace/tf/engine/readers")]
VALID = {"YES", "NO", "NOT_READY"}
ALIAS = {"grok": "grok-bot", "theme_radar": "theme-radar", "james": "james", "trading-bot-taskforce": "taskforce", "newbot": "new-bot", "themeradar": "theme-radar"}

def load_sheet():
    with open(SHEET, newline="") as f: rows = list(csv.DictReader(f))
    owner, dup = {}, []
    for r in rows:
        i = r["id"].strip()
        if i in owner: dup.append(i)
        owner[i] = (r.get("merge_owner") or "").strip()
    return owner, dup

def find_readers():
    seen, out = set(), []
    for d in READER_DIRS:
        if not d.is_dir(): continue
        for p in sorted(d.glob("*.py")):
            if p.name.startswith("_"): continue
            rp = os.path.realpath(p)
            if rp in seen: continue
            seen.add(rp); out.append((p.stem, rp))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True); ap.add_argument("--date", required=True); ap.add_argument("--out")
    a = ap.parse_args(); t = a.ticker.upper()
    owner, sheet_dup = load_sheet()
    owners = set(owner.values())
    warn = [f"DUPLICATE_ID_IN_SHEET {d}" for d in sorted(set(sheet_dup))]
    claims = defaultdict(list)   # rid -> [(reader, ans, reason, asof)]
    crashed = {}
    for name, path in find_readers():
        try:
            spec = importlib.util.spec_from_file_location(f"reader_{len(crashed)}_{abs(hash(path))}", path)
            m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            res = list(m.answer(t, a.date) or [])
        except Exception as e:
            crashed[name] = f"{type(e).__name__}: {e}".replace("\n", " ")[:200]
            warn.append(f"READER_ERROR {name}: {crashed[name]}"); continue
        for r in res:
            rid = str(r.get("row_id", "")).strip()
            if rid not in owner: warn.append(f"UNKNOWN_ID {name} {rid}"); continue
            ans = r.get("answer"); why = str(r.get("reason") or "").strip()
            if ans not in VALID:
                warn.append(f"CONTRACT_ERROR {name} {rid} answer={ans!r}")
                ans, why = "NOT_READY", f"contract_error: answer={ans!r} from {name}"
            elif ans == "NOT_READY" and not why:
                warn.append(f"CONTRACT_ERROR {name} {rid} NOT_READY without reason")
                why = f"contract_error: no reason from {name}"
            claims[rid].append((name, ans, why, str(r.get("data_as_of") or "")))
    def crash_reason(rid):
        for name, msg in crashed.items():
            o = ALIAS.get(name, name)
            if o == owner[rid] or (o not in owners and owner[rid].replace("-", "") == name.replace("-", "")):
                return f"reader_error: {msg}"
    out = a.out or str(HERE / "out" / f"answers_{t}_{a.date}.csv")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    cnt = Counter()
    with open(out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["row_id", "owner", "ticker", "date", "answer", "reason", "data_as_of"])
        for rid in sorted(owner):
            c = claims.get(rid)
            if not c:
                ans, why, asof = "NOT_READY", crash_reason(rid) or "no_reader", ""
            elif len(c) > 1:
                names = ",".join(x[0] for x in c); warn.append(f"CONFLICT {rid} readers={names}")
                ans, why, asof = "NOT_READY", f"conflict: {names}", ""
            else:
                _, ans, why, asof = c[0]
            cnt[ans if ans != "NOT_READY" else "NOT_READY:" + why.split(":")[0]] += 1
            w.writerow([rid, owner[rid], t, a.date, ans, why, asof])
    for x in warn: print("WARN", x, file=sys.stderr)
    print(out); print(dict(sorted(cnt.items())))
if __name__ == "__main__": main()
