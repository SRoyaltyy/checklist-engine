"""Inspect existing New Bot archive schemas before treating it as a price source."""
import csv,hashlib,io,json,tarfile
from pathlib import Path
import pyarrow.parquet as pq
EXPECTED='e0f88aa4fbb884f06c38e19c82cbabd8aa0d38a30d4e5c9b2227ff1819609128'
def main():
    file=Path('nb_nbx_2025_2026_v2.tar')
    if hashlib.sha256(file.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Existing New Bot archive hash mismatch')
    records=[]
    with tarfile.open(file) as tar:
        for member in tar:
            if not member.isfile():continue
            record=dict(name=member.name,bytes=member.size)
            if member.name.endswith('.parquet'):
                raw=tar.extractfile(member).read();parquet=pq.ParquetFile(io.BytesIO(raw))
                record.update(rows=parquet.metadata.num_rows,columns=parquet.schema_arrow.names)
            elif member.name.lower().endswith(('.csv','.tsv')):
                stream=io.TextIOWrapper(tar.extractfile(member),encoding='utf8',errors='replace')
                reader=csv.reader(stream,delimiter='\t' if member.name.endswith('.tsv') else ',')
                record['columns']=next(reader,[])
            records.append(record)
    report=dict(source_release='data-ext-2020-26-v1',asset=file.name,sha256=EXPECTED,members=records,scope='Existing archive schema inspection only; no source approval or historical price substitution')
    Path('NBX_ARCHIVE_SOURCE_AUDIT.json').write_text(json.dumps(report,indent=2))
    print('NBX_ARCHIVE_SOURCE_AUDIT',json.dumps(report),flush=True)
if __name__=='__main__':main()
