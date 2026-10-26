"""SEC fair-access requests and optional reuse of the existing official-source relay."""
import gzip,json,os,re,time,urllib.error,urllib.parse,urllib.request
SEC_HEADERS={'User-Agent':os.environ.get('SEC_USER_AGENT','checklist-engine research cyrus-checklist@users.noreply.github.com'),'Accept-Encoding':'gzip'}
REQUEST_SPACING=1.0


def _redact(value):
    text=str(value);relay=os.environ.get('PRIMARY_ACTION_RELAY_URL','').strip()
    if relay:
        text=text.replace(relay,'[RELAY REDACTED]')
        parsed=urllib.parse.urlsplit(relay)
        if parsed.netloc:text=text.replace(parsed.netloc,'[RELAY HOST REDACTED]')
        for values in urllib.parse.parse_qs(parsed.query).values():
            for token in values:
                if len(token)>3:text=text.replace(token,'[REDACTED]')
    return text


def relay_target(relay,url):
    target=urllib.parse.urlsplit(url);base=urllib.parse.urlsplit(relay)
    if target.hostname not in ('data.sec.gov','www.sec.gov','sec.gov'):raise ValueError('relay accepts only SEC source URLs')
    if base.scheme!='https' or not base.hostname or base.username or base.password:
        raise ValueError('SEC relay must be HTTPS without embedded credentials')
    query=[(k,v) for k,v in urllib.parse.parse_qsl(base.query,keep_blank_values=True) if k!='url']
    query.append(('url',url))
    return urllib.parse.urlunsplit((base.scheme,base.netloc,base.path or '/',urllib.parse.urlencode(query),''))


class SECSourceError(urllib.error.HTTPError):
    def __init__(self,original,evidence):
        super().__init__(evidence['url'],original.code,_redact(original.reason),original.headers,None)
        self.evidence=evidence


def error_evidence(exc,url,attempts,route):
    try:
        raw=exc.read(16384)
        if raw[:2]==bytes([31,139]):raw=gzip.decompress(raw)
        excerpt=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',raw.decode('utf-8',errors='replace'))).strip()[:800]
    except Exception:excerpt=str(exc.reason)
    return dict(url=url,http_status=exc.code,response_excerpt=_redact(excerpt or str(exc.reason)),attempts=attempts,
        user_agent=SEC_HEADERS['User-Agent'],request_spacing_seconds=REQUEST_SPACING,
        accept_encoding=SEC_HEADERS['Accept-Encoding'],route=route)


def _request_json(request_url,source_url,retries,allow_404,route):
    for attempt in range(retries):
        time.sleep(REQUEST_SPACING)
        try:
            with urllib.request.urlopen(urllib.request.Request(request_url,headers=SEC_HEADERS),timeout=120) as response:
                raw=response.read()
                if raw[:2]==bytes([31,139]):raw=gzip.decompress(raw)
                result=json.loads(raw)
                print('SEC_SOURCE_OK',source_url,'route='+route,'bytes='+str(len(raw)),flush=True)
                return result
        except urllib.error.HTTPError as exc:
            evidence=error_evidence(exc,source_url,attempt+1,route)
            if exc.code==404 and allow_404:
                print('SKIP_404',json.dumps(evidence),flush=True);return None
            if exc.code not in (403,429,500,502,503,504) or attempt==retries-1:
                raise SECSourceError(exc,evidence) from None
        except (OSError,TimeoutError) as exc:
            if attempt==retries-1:raise RuntimeError('SEC transport failure via '+route+': '+_redact(exc)) from None
        time.sleep(2**attempt)
    raise RuntimeError('SEC retry loop exhausted')


def get_json(url,retries=4,allow_404=False):
    relay=os.environ.get('PRIMARY_ACTION_RELAY_URL','').strip()
    request_url=relay_target(relay,url) if relay else url
    return _request_json(request_url,url,retries,allow_404,'relay' if relay else 'direct')
