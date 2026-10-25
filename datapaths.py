"""One data-folder setting. Unset CHECKLIST_DATA_DIR = original box paths.
Set it to the folder holding the release data-2020-24-v1 files and every input is read from there."""
import os
_DIR = os.environ.get('CHECKLIST_DATA_DIR')
_RENAME = {'universe_2020_survivors.parquet': 'universe_2020_survivors_le2024.parquet',
           'bars_all.parquet': 'bars_all_le2024.parquet',
           'etf_2015.parquet': 'etf_2015_le2024.parquet',
           'VIXCLS.parquet': 'VIXCLS_le2024.parquet'}
def D(default):
    if not _DIR: return default
    b = os.path.basename(default); return os.path.join(_DIR, _RENAME.get(b, b))
