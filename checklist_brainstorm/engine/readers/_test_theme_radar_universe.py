import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _theme_radar_universe import universe, usable_versions
u = universe("2026-10-21")
assert u is not None
assert (u["snapshot_date"] < "2026-10-21").all(), "snapshot dated D used for D"
assert "2026-10-21" not in usable_versions("2026-10-21")
assert all(d < "2026-10-21" for d in usable_versions("2026-10-21"))
assert universe("2026-08-06") is None  # first snapshot is dated 08-06
print("ok", u["snapshot_date"].iloc[0], len(u))
