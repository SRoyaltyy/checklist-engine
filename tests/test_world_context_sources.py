import hashlib
import io
import tarfile

import pandas as pd
import pytest

from ci.shared_context_build import verified_parquet, normalize_index


def test_verified_archive_reads_only_expected_bytes_without_extracting_paths(tmp_path):
    frame = pd.DataFrame({"DATE":pd.to_datetime(["2020-01-02"]),"VVIX":[100.]})
    raw = frame.to_parquet(index=False)
    archive = tmp_path/"source.tar.gz"
    with tarfile.open(archive,"w:gz") as out:
        for name,content in (("unexpected.parquet",b"not parquet"),("../../escape.parquet",raw)):
            info = tarfile.TarInfo(name);info.size = len(content);out.addfile(info,io.BytesIO(content))
    actual,name = verified_parquet(archive,hashlib.sha256(raw).hexdigest())
    pd.testing.assert_frame_equal(actual,frame)
    assert name == "../../escape.parquet"
    assert list(tmp_path.iterdir()) == [archive]
    with pytest.raises(ValueError,match="fingerprint absent"):
        verified_parquet(archive,"0"*64)


def test_close_only_source_normalization_preserves_real_field_and_no_fake_ohlc():
    frame = pd.DataFrame({"DATE":["2020-01-02"],"VVIX":[100.]})
    result = normalize_index(frame,{"source_columns":["DATE","VVIX"],"has_true_ohlc":False})
    assert list(result) == ["DATE","CLOSE"]
    assert result.CLOSE.iloc[0] == 100
    assert "VVIX" in frame


def test_ambiguous_or_unproven_source_schema_fails():
    frame = pd.DataFrame({"DATE":["2020-01-02"],"VVIX":[100.],"OTHER":[9.]})
    with pytest.raises(ValueError,match="ambiguous"):
        normalize_index(frame,{"source_columns":list(frame),"has_true_ohlc":False})
    with pytest.raises(ValueError,match="OHLC not proven"):
        normalize_index(frame,{"source_columns":["DATE","VVIX"],"has_true_ohlc":True})
    with pytest.raises(ValueError,match="schema differs"):
        normalize_index(frame,{"source_columns":["DATE","MISSING"],"has_true_ohlc":False})
