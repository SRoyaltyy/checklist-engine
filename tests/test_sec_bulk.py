import io,zipfile
import pytest
from fetch.sec_bulk import source_links,inspect_zip


def test_bulk_index_uses_only_official_https_zip_links_in_requested_years():
    html='<a href="/files/2020q1_form345.zip">data</a><a href="https://www.sec.gov/files/01dec2025-28feb2026_form13f.zip">13f</a><a href="/files/2010q1.zip">old</a><a href="https://other.test/2020q1.zip">other</a>'
    urls=source_links(html,"https://www.sec.gov/page")
    assert urls==['https://www.sec.gov/files/01dec2025-28feb2026_form13f.zip','https://www.sec.gov/files/2020q1_form345.zip']
    with pytest.raises(ValueError,match="no bulk ZIP"):source_links("<html>blocked</html>","https://www.sec.gov/page")
    assert source_links('{"downloadURL":"https://www.sec.gov/files/2020q1.zip"}',"https://catalog.data.gov/dataset/test")==['https://www.sec.gov/files/2020q1.zip']


def zip_data(name,content):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w",compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr(name,content)
    return stream.getvalue()


def test_structured_archive_is_crc_checked_and_reports_schema_without_text_features():
    raw=zip_data('SUBMISSION.tsv','ACCESSION_NUMBER\tFILING_DATE\tISSUERCIK\nA\t2020-01-02\t123\n')
    result=inspect_zip(raw)
    assert result[0]['columns']==['ACCESSION_NUMBER','FILING_DATE','ISSUERCIK'] and result[0]['rows_after_header']==1
    with pytest.raises(ValueError,match="no populated"):inspect_zip(zip_data('README.txt','no tabular data'))
    with pytest.raises(ValueError,match="unsafe"):inspect_zip(zip_data('../SUBMISSION.tsv','A\tB\n1\t2\n'))
    with pytest.raises((ValueError,zipfile.BadZipFile)):inspect_zip(b'<!doctype html>blocked')


def test_blocked_sec_index_can_use_sec_published_government_catalog_without_direct_sec(monkeypatch):
    from urllib.error import HTTPError
    from fetch import sec_bulk
    calls=[]
    def blocked(url):
        calls.append(url);raise HTTPError(url,403,'Forbidden',{},None)
    monkeypatch.setattr(sec_bulk,'get_bytes',blocked)
    class Response(io.BytesIO):
        def __enter__(self):return self
        def __exit__(self,*args):self.close()
    def public(request,timeout):
        assert request.full_url=='https://catalog.data.gov/dataset/form-13f-data-sets'
        return Response(b'{"downloadURL":"https://www.sec.gov/files/2020q1_form13f.zip"}')
    monkeypatch.setattr(sec_bulk.urllib.request,'urlopen',public)
    report={};urls=sec_bulk.discover('13f',report)
    assert urls==['https://www.sec.gov/files/2020q1_form13f.zip'] and len(calls)==1
    assert report['landing_page_failure']['http_status']==403 and 'distribution_catalog' in report
