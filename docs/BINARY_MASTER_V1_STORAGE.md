# Master CSV storage

The complete `BINARY_MASTER_V1.csv` remains the generated CSV, with the same
columns, row order and decoded `csv_sha256` in `BINARY_MASTER_V1_REPORT.json`.
The repository stores its lossless gzip byteparts and ordered
`BINARY_MASTER_V1_STORAGE.json` manifest. No columns or definitions are removed.

Restore the exact CSV after checkout, using only Python's standard library:

```text
python -m ci.binary_master_storage unpack
```

The unpacker checks every compressed asset's size/SHA, bounded decoded size,
and the complete CSV size/SHA before replacing the generated file. Byteparts
may divide UTF8 characters or quoted multiline CSV cells; concatenate decoded
bytes through this command before reading CSV records. Individual byteparts
are not separate CSV tables.

`python -m ci.binary_master_build` regenerates both the complete CSV and its
storage package. The generated plaintext CSV is ignored by Git. Commit the
report, storage manifest and parts together. Each raw chunk is at most 8 MiB;
even incompressible content fits well below GitHub's per-file limit. Repeated
chunks share content-addressed files, and regeneration removes only obsolete
generated files referenced by the previous manifest.

Gzip uses level 6, zero modification time and an empty original filename.
The canonical identity is the decoded CSV hash; compressed assets also carry
their own hashes. CI restores the committed package, checks its declared CSV
hash, regenerates all bound definitions, verifies the exact same CSV hash, and
uploads the complete storage package and report.

This changes physical storage. Definition readiness, aliases, pending semantic
deduplication, chart/derive/mining gates and numeric indicator policies retain
their existing status.
