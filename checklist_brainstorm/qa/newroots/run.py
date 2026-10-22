import requests,re,json,urllib.parse as u,pandas as pd,csv,io,time,datetime as D,os
H={'User-Agent':'cyrus-research/1.0 (cyrus)'};P=[];R='raw/'
now=lambda:D.datetime.now().strftime('%Y-%m-%d %H:%M HKT')
for t in 'SPY XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC'.split():
  url=f'https://www.ssga.com/us/en/intermediary/etfs/library-content/products/fund-data/etfs/us/navhist-us-en-{t.lower()}.xlsx'
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'});open(R+f'ssga_{t}.xlsx','wb').write(r.content)
  try:
    d=pd.read_excel(io.BytesIO(r.content),header=3);d['dt']=pd.to_datetime(d['Date'],errors='coerce',format='%d-%b-%Y');d=d.dropna(subset=['dt','Shares Outstanding'])
    P.append(['ssga_navhist',t,url,r.status_code,d.dt.min().date(),d.dt.max().date(),len(d),f"{d.dt.max().date()} SO={d['Shares Outstanding'].iloc[0]}",'T-1 value posted overnight; usable T',now()])
  except Exception as e: P.append(['ssga_navhist',t,url,r.status_code,'','',0,repr(e)[:60],'',now()])
# Nasdaq cross-check (today's SO only)
for t in ['SPY','XLK','QQQ','IWM']:
  url=f'https://api.nasdaq.com/api/quote/{t}/info?assetclass=etf'
  try: r=requests.get(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'},timeout=20);open(R+f'nasdaq_{t}.json','w').write(r.text);P.append(['nasdaq_quote',t,url,r.status_code,'','','',r.text[:80].replace(',',';'),'snapshot only',now()])
  except Exception as e: P.append(['nasdaq_quote',t,url,'ERR','','','',repr(e)[:60],'',now()])
for t,url in [('QQQ','https://www.invesco.com/us/financial-products/etfs/holdings/main/holdings/0?audienceType=Investor&action=download&ticker=QQQ'),('IWM','https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=xls&fileName=iShares-Russell-2000-ETF_fund&dataType=fund')]:
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'});open(R+f'issuer_{t}.out','wb').write(r.content);P.append(['issuer',t,url,r.status_code,'','',0,('html page, not data' if r.text.lstrip().startswith('<!') else 'data'),'',now()])
for s in ['VIX','VIX9D','VIX3M','VIX6M']:
  os.replace(f'y_{s}.out',R+f'yahoo_{s}.json') if os.path.exists(f'y_{s}.out') else None
  r=json.load(open(R+f'yahoo_{s}.json'))['chart']['result'][0];ts=r['timestamp'];c=r['indicators']['quote'][0]['close'];f=lambda x:D.datetime.fromtimestamp(x,D.UTC).date()
  P.append(['yahoo_chart','^'+s,f'https://query1.finance.yahoo.com/v8/finance/chart/%5E{s}',200,f(ts[0]),f(ts[-1]),len(ts),f'{f(ts[-1])} close={c[-1]:.2f}','16:15 ET close T-1; usable T','2026-10-22 03:0x HKT'])
  os.replace(f'cb_{s}.csv',R+f'cboe_{s}_History.csv') if os.path.exists(f'cb_{s}.csv') else None
  l=open(R+f'cboe_{s}_History.csv').read().splitlines()
  P.append(['cboe_official_csv',s,f'https://cdn.cboe.com/api/global/us_indices/daily_prices/{s}_History.csv',200,l[1].split(',')[0],l[-1].split(',')[0],len(l)-1,l[-1].replace(',',' '),'16:15 ET close T-1; usable T','2026-10-22 03:1x HKT'])
h=open('sp.html').read();tb=h.split('id="constituents"')[1].split('</table>')[0];rows=[]
for tr in tb.split('<tr')[2:]:
  tds=re.findall(r'<td.*?</td>',tr,re.S)
  if len(tds)<2: continue
  tk=re.sub('<[^>]+>','',tds[0]).strip();a=re.search(r'href="https://en.wikipedia.org/wiki/([^"]+)"',tds[1])
  if a: rows.append((tk,u.unquote(a.group(1)).replace('_',' ')))
red={}
for i in range(0,len(rows),50):
  r=requests.get('https://en.wikipedia.org/w/api.php',params={'action':'query','titles':'|'.join(x[1] for x in rows[i:i+50]),'redirects':1,'format':'json'},headers=H).json()
  for x in r['query'].get('redirects',[]): red[x['from']]=x['to']
os.makedirs(R+'wiki',exist_ok=True);ok=late=fail=0;out=[]
for tk,ti in rows:
  rs=red.get(ti,ti);url='https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/'+u.quote(rs.replace(' ','_'),safe='')+'/daily/20150701/20261021'
  try: r=requests.get(url,headers=H,timeout=30);st=r.status_code
  except Exception: st='ERR'
  f0=l0=n=v=''
  if st==200:
    open(R+f'wiki/{tk}.json','w').write(r.text);it=r.json()['items'];f0,l0,n,v=it[0]['timestamp'][:8],it[-1]['timestamp'][:8],len(it),it[-1]['views'];ok+=1;late+=f0>'20150701'
  else: fail+=1
  out.append([tk,ti,rs,ti!=rs,st,f0,l0,n,v]);time.sleep(0.03)
with open('sp500_wiki_map.csv','w') as fh: w=csv.writer(fh);w.writerow(['ticker','list_title','resolved_title','was_redirect','http','first','last','days','last_views']);w.writerows(out)
P.append(['wikimedia_pageviews',f'{len(rows)} S&P500 articles','https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/...',f'200:{ok} fail:{fail}','20150701','see map','',f'redirects={len(red)} late_start={late}','UTC day D; ready ~D+1 morning UTC -> D-1 usable at 09:25 ET',now()])
# second endpoint: aggregate for Apple + news spike check
r=requests.get('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Apple_Inc./daily/20150701/20261021',headers=H);open(R+'wiki_AAPL_allagents.json','w').write(r.text)
r2=requests.get('https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/2024/06/10',headers=H);open(R+'wiki_top_20240610.json','w').write(r2.text)
P.append(['wikimedia_top_endpoint','top 2024-06-10',r2.url,r2.status_code,'','','','see raw','',now()])
with open('../src/fetch_proof_grok-bot-newroots.csv','w') as fh:
  w=csv.writer(fh);w.writerow(['source','series','url','http_status','first_date','last_date','rows','sample','known_when','pulled_at']);w.writerows(P)
print('done',len(rows),ok,fail,late,len(red))
