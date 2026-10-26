"""SEC fair-access requests with durable public failure evidence."""
import gzip,json,os,re,time,urllib.error,urllib.request
SEC_HEADERS={'User-Agent':os.environ.get('SEC_USER_AGENT','checklist-engine research cyrus-checklist@users.noreply.github.com'),'Accept-Encoding':'gzip'}
REQUEST_SPACING=1.0  # eight source shards stay below 10 requests per second


class SECSourceError(urllib.error.HTTPError):
    def __init__(self,original,evidence):
        super().__init__(original.url,original.code,original.reason,original.headers,None)
        self.evidence=evidence


def error_evidence(exc,url,attempts):
    try:
        raw=exc.read(16384)
        if raw[:2]==bytes([31,139]):raw=gzip.decompress(raw)
        excerpt=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',raw.decode('utf-8',errors='replace'))).strip()[:800]
    except Exception:excerpt=str(exc.reason)
    return dict(url=url,http_status=exc.code,response_excerpt=excerpt or str(exc.reason),attempts=attempts,
                user_agent=SEC_HEADERS['User-Agent'],request_spacing_seconds=REQUEST_SPACING,accept_encoding=SEC_HEADERS['Accept-Encoding'])


def get_json(url,retries=4,allow_404=False):
    for attempt in range(retries):
        time.sleep(REQUEST_SPACING)
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=SEC_HEADERS),timeout=120) as response:
                raw=response.read()
                if raw[:2]==bytes([31,139]):raw=gzip.decompress(raw)
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            evidence=error_evidence(exc,url,attempt+1)
            if exc.code==404 and allow_404:
                print('SKIP_404',json.dumps(evidence),flush=True);return None
            if exc.code not in (403,429,500,502,503,504) or attempt==retries-1:
                raise SECSourceError(exc,evidence) from None
        except (OSError,TimeoutError):
            if attempt==retries-1:raise
        time.sleep(2**attempt)
    raise RuntimeError('SEC retry loop exhausted')
