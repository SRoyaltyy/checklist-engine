"""Lossless, bounded Git assets for the complete generated master CSV."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

CSV_NAME = 'BINARY_MASTER_V1.csv'
MANIFEST = 'BINARY_MASTER_V1_STORAGE.json'
PARTS = 'BINARY_MASTER_V1.parts'
FORMAT = 'BINARY_MASTER_CSV_GZIP_PARTS_V1'
CHUNK_BYTES = 8 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def part_path(root, entry):
    require(re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None, 'invalid part hash')
    require(entry['path'] == PARTS + '/' + entry['sha256'] + '.gz', 'invalid part path')
    path = root / entry['path']
    require(path.resolve().is_relative_to(root.resolve()), 'part escapes storage root')
    return path


def pack_csv(csv_path, chunk_bytes=CHUNK_BYTES):
    csv_path = Path(csv_path)
    require(csv_path.name == CSV_NAME and type(chunk_bytes) is int and 0 < chunk_bytes <= CHUNK_BYTES, 'invalid master packaging request')
    root = csv_path.parent
    manifest_path = root / MANIFEST
    previous = json.loads(manifest_path.read_bytes()) if manifest_path.exists() else None
    stale = [part_path(root, p) for p in previous['chunks']] if previous else []
    (root / PARTS).mkdir(exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    chunks = []
    with csv_path.open('rb') as source:
        while raw := source.read(chunk_bytes):
            digest.update(raw)
            size += len(raw)
            target = io.BytesIO()
            with gzip.GzipFile(filename='', mode='wb', fileobj=target, compresslevel=6, mtime=0) as stream:
                stream.write(raw)
            packed = target.getvalue()
            require(len(packed) < 100_000_000, 'Git asset exceeds file limit')
            checksum = sha(packed)
            entry = dict(path=PARTS + '/' + checksum + '.gz', sha256=checksum,
                         compressed_bytes=len(packed), raw_bytes=len(raw))
            path = part_path(root, entry)
            if path.exists():
                require(path.read_bytes() == packed, 'existing content-addressed part differs')
            else:
                path.write_bytes(packed)
            chunks.append(entry)
    require(size > 0, 'empty CSV cannot be packaged')
    manifest = dict(format=FORMAT, csv_name=CSV_NAME, csv_sha256=digest.hexdigest(), csv_bytes=size,
                    max_chunk_bytes=chunk_bytes, gzip_level=6, gzip_mtime=0, chunks=chunks)
    temporary = root / (MANIFEST + '.tmp')
    temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    temporary.replace(manifest_path)
    current = {part_path(root, c).resolve() for c in chunks}
    # Remove only obsolete generated assets named by the previous manifest.
    for path in set(stale):
        require(path.resolve().is_relative_to(root.resolve()), 'stale part escapes storage root')
        if path.resolve() not in current:
            if path.exists():
                require(sha(path.read_bytes()) == path.stem, 'obsolete generated part was edited; preserve it')
            path.unlink(missing_ok=True)
    return manifest


def unpack_csv(root):
    root = Path(root)
    manifest = json.loads((root / MANIFEST).read_bytes())
    require(manifest['format'] == FORMAT and manifest['csv_name'] == CSV_NAME, 'invalid storage manifest')
    require(type(manifest['max_chunk_bytes']) is int and 0 < manifest['max_chunk_bytes'] <= CHUNK_BYTES, 'invalid chunk bound')
    require(manifest['chunks'] and re.fullmatch('[0-9a-f]{64}', manifest['csv_sha256']) is not None, 'missing CSV binding')
    temporary = root / (CSV_NAME + '.unpacking')
    digest = hashlib.sha256()
    size = 0
    with temporary.open('wb') as target:
        for entry in manifest['chunks']:
            path = part_path(root, entry)
            require(type(entry['raw_bytes']) is int and 0 < entry['raw_bytes'] <= manifest['max_chunk_bytes'], 'invalid raw chunk size')
            require(type(entry['compressed_bytes']) is int and 0 < entry['compressed_bytes'] < 100_000_000, 'invalid compressed size')
            require(path.stat().st_size == entry['compressed_bytes'], 'compressed part size differs')
            packed = path.read_bytes()
            require(sha(packed) == entry['sha256'], 'compressed part hash differs')
            with gzip.GzipFile(fileobj=io.BytesIO(packed), mode='rb') as stream:
                raw = stream.read(entry['raw_bytes'] + 1)
            require(len(raw) == entry['raw_bytes'], 'decompressed chunk exceeds or misses bound')
            digest.update(raw)
            size += len(raw)
            target.write(raw)
    require(size == manifest['csv_bytes'] and digest.hexdigest() == manifest['csv_sha256'], 'reconstructed CSV differs')
    output = root / CSV_NAME
    temporary.replace(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('pack', 'unpack'))
    parser.add_argument('--root', type=Path, default=Path('docs'))
    args = parser.parse_args()
    result = pack_csv(args.root / CSV_NAME) if args.operation == 'pack' else str(unpack_csv(args.root))
    print(json.dumps(result, indent=2))
