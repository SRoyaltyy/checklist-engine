import csv
import hashlib
import json

import pytest

from ci.binary_master_storage import CSV_NAME, MANIFEST, pack_csv, unpack_csv


def test_roundtrip_preserves_utf8_multiline_quoted_csv_across_byte_boundaries(tmp_path):
    source = tmp_path / CSV_NAME
    raw = 'question_id,formula\nq1,"上升, \'quoted\'\nsecond line"\nq2,"x > 0"\n'.encode('utf-8')
    source.write_bytes(raw)
    first = pack_csv(source, chunk_bytes=7)
    second = pack_csv(source, chunk_bytes=7)
    assert first == second
    assert first['csv_sha256'] == hashlib.sha256(raw).hexdigest()
    assert all(c['raw_bytes'] <= 7 for c in first['chunks'])
    source.unlink()
    restored = unpack_csv(tmp_path)
    assert restored.read_bytes() == raw
    with restored.open(encoding='utf-8', newline='') as stream:
        assert list(csv.DictReader(stream)) == [
            {'question_id': 'q1', 'formula': "上升, 'quoted'\nsecond line"},
            {'question_id': 'q2', 'formula': 'x > 0'}]


def test_corrupt_part_cannot_replace_existing_csv(tmp_path):
    source = tmp_path / CSV_NAME
    source.write_bytes(b'question_id\nq1\n')
    manifest = pack_csv(source, chunk_bytes=5)
    part = tmp_path / manifest['chunks'][0]['path']
    raw = bytearray(part.read_bytes())
    raw[-1] ^= 1
    part.write_bytes(raw)
    source.write_bytes(b'keep existing bytes')
    with pytest.raises(ValueError, match='hash differs'):
        unpack_csv(tmp_path)
    assert source.read_bytes() == b'keep existing bytes'


def test_manifest_cannot_read_outside_package_and_repeated_chunks_are_valid(tmp_path):
    source = tmp_path / CSV_NAME
    source.write_bytes(b'abcdabcd')
    manifest = pack_csv(source, chunk_bytes=4)
    assert manifest['chunks'][0] == manifest['chunks'][1]
    assert unpack_csv(tmp_path).read_bytes() == b'abcdabcd'
    manifest['chunks'][0]['path'] = '../outside.gz'
    (tmp_path / MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='invalid part path'):
        unpack_csv(tmp_path)


def test_regeneration_removes_only_obsolete_manifest_parts(tmp_path):
    source = tmp_path / CSV_NAME
    source.write_bytes(b'first generation')
    previous = pack_csv(source, chunk_bytes=6)
    unrelated = tmp_path / 'BINARY_MASTER_V1.parts' / 'notes.txt'
    unrelated.write_text('keep this')
    source.write_bytes(b'new generation')
    current = pack_csv(source, chunk_bytes=6)
    live = {c['path'] for c in current['chunks']}
    assert all(not (tmp_path / c['path']).exists() for c in previous['chunks'] if c['path'] not in live)
    assert unrelated.read_text() == 'keep this'
    assert unpack_csv(tmp_path).read_bytes() == b'new generation'
