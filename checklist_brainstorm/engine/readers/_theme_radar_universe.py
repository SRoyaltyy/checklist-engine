"""Read-only point-in-time Finviz universe from theme-radar's own snapshots.

universe(date) -> pandas DataFrame (one row per ticker, every column of the
theme-radar data/snapshots/<D>.raw.csv export as strings, plus snapshot_date and
data_as_of), using only a snapshot known before 09:25 ET on `date`; None if none exists
(callers should answer NOT_READY with reason no_universe_snapshot).

Known-at rule: a snapshot version counts from the first NYSE session whose 09:25 ET is
after its git commit time on origin/main, and a snapshot dated D is never used for date D
(snapshot_date < date, strictly). If a file was rewritten, the newest version known by
the cutoff is used. Data are read from the local clone with `git show` (nothing copied to disk).
"""
import io, re, subprocess, datetime as dt
from functools import lru_cache
import pandas as pd

REPO = "/workspace/theme-radar-repo"
NYSE_HOLIDAYS = {"2026-01-01","2026-01-19","2026-02-16","2026-04-03","2026-05-25","2026-06-19",
                 "2026-07-03","2026-09-07","2026-11-26","2026-12-25"}

def _git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, check=True).stdout

def known_from(ts):
    """Session date of the first NYSE 09:25 ET strictly after commit time ts (aware datetime)."""
    off = -4 if dt.date(2026, 3, 8) <= ts.date() < dt.date(2026, 11, 1) else -5
    e = ts.astimezone(dt.timezone(dt.timedelta(hours=off))); d = e.date()
    if (e.hour, e.minute) >= (9, 25): d += dt.timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in NYSE_HOLIDAYS: d += dt.timedelta(days=1)
    return d.isoformat()

@lru_cache(None)
def snapshot_versions():
    """[(snapshot_date, commit, path, known_from)] for every version of every raw snapshot on origin/main."""
    log = _git("log", "origin/main", "--format=@%h %cI", "--name-status", "--", "data/snapshots/").decode()
    out, cur = [], None
    for line in log.splitlines():
        if line.startswith("@"):
            h, ts = line[1:].split(); cur = (h, known_from(dt.datetime.fromisoformat(ts)))
        elif line.strip():
            st, *paths = line.split("\t")
            m = re.fullmatch(r"data/snapshots/(\d{4}-\d\d-\d\d)\.raw\.csv", paths[-1])
            if m and not st.startswith("D"): out.append((m.group(1), cur[0], paths[-1], cur[1]))
    return out

def usable_versions(date):
    """{snapshot_date: (commit, path, known_from)} usable for `date` (snapshot_date < date, known_from <= date)."""
    best = {}
    for d, c, f, kf in snapshot_versions():
        if d < date and d <= kf <= date and (d not in best or kf > best[d][2]): best[d] = (c, f, kf)
    return best

@lru_cache(None)
def load_version(commit, path, usecols=None):
    raw = _git("show", f"{commit}:{path}")
    if usecols is not None:
        hdr = pd.read_csv(io.BytesIO(raw), nrows=0).columns
        usecols = [c for c in hdr if c in usecols]
    df = pd.read_csv(io.BytesIO(raw), usecols=usecols, dtype=str, keep_default_na=False)
    return df.drop_duplicates("Ticker").set_index("Ticker")

def history(date, usecols=None):
    """All usable snapshots for `date`, oldest first: [(snapshot_date, DataFrame)]; empty placeholder files skipped."""
    out = [(d, load_version(c, f, usecols)) for d, (c, f, _) in sorted(usable_versions(date).items())]
    return [(d, df) for d, df in out if len(df) > 1000]

def universe(date):
    h = history(date)
    if not h: return None
    d, df = h[-1]
    df = df.copy(); df["snapshot_date"] = d; df["data_as_of"] = d
    return df
