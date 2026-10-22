"""Thin CLI for testing the Taskforce reader.
python3 readers/_tf_cli.py --ticker AAPL --date 2024-05-15 [--out f.csv]
python3 readers/_tf_cli.py --tickers file.txt --dates 2024-05-15,2021-01-27 (or START:END for every SPY session)"""
import sys,os,csv,argparse,importlib.util,collections
H=os.path.dirname(os.path.abspath(__file__)); sp=importlib.util.spec_from_file_location('tbt',os.path.join(H,'trading-bot-taskforce.py')); R=importlib.util.module_from_spec(sp); sp.loader.exec_module(R)
COLS=['row_id','ticker','date','answer','reason','data_as_of']
def run(t,d,out,trunc=None):
    rows=R.answer(t,d,_trunc=trunc)
    with open(out,'w',newline='') as fh: w=csv.DictWriter(fh,COLS); w.writeheader(); w.writerows(rows)
    c=collections.Counter(r['answer'] for r in rows); print(t,d,dict(c),'twins',R.TWIN_STATS,flush=True); return rows
if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--ticker'); a.add_argument('--tickers'); a.add_argument('--date'); a.add_argument('--dates'); a.add_argument('--out'); a.add_argument('--outdir',default=os.path.join(H,'..','out','taskforce')); a.add_argument('--trunc')
    o=a.parse_args(); ts=[o.ticker] if o.ticker else [x.strip() for x in open(o.tickers) if x.strip()]
    ds=[o.date] if o.date else None
    if ds is None:
        if ':' in o.dates:
            s,e=o.dates.split(':'); b,_=R.bars_at('SPY',e); ds=[str(x.date()) for x in b.index if str(x.date())>=s]+[e]
        else: ds=o.dates.split(',')
    os.makedirs(o.outdir,exist_ok=True)
    for t in ts:
        for d in ds: run(t,d,o.out if (o.out and len(ts)*len(ds)==1) else os.path.join(o.outdir,f'tf_{t}_{d}.csv'),o.trunc)
