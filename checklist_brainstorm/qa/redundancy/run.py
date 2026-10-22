import sys;sys.path.insert(0,'.');from engine import *;prep()
import pickle
d=pd.read_pickle('tagged.pkl'); d=d.set_index('id',drop=False)
rng=np.random.default_rng(7)
def pick(df,n,by):
    g=df.groupby(by); k=max(1,n//g.ngroups+1)
    # round-robin over strata in shuffled order -> returns ordered candidate list
    lst=[x.sample(frac=1,random_state=7) for _,x in g]
    out=[];i=0
    while any(i<len(x) for x in lst):
        for x in lst:
            if i<len(x): out.append(x.iloc[i])
        i+=1
    return (pd.DataFrame(out),n)
tf=d[d.merge_owner=='taskforce']; tf=tf[tf.variant.map(lambda v:TFX(v,stockbars()['AAPL'],ctx('AAPL')) is not None)]
tf=tf[tf.lens.str.replace(' (BUT)','',regex=False).isin(['level','extreme','change','div_price','div_volume','div_sector','cross','streak','rank_market'])]
tf=tf[~(tf.variant.str.startswith('CDL')&(tf.lens!='level')&(tf.lens!='level (BUT)'))]
ja=d[d.merge_owner=='james']; ja=ja[ja.strict_definition.str.contains(INST_RE,regex=True)]
tr=d[(d.merge_owner=='theme-radar')&d.root.str.contains('Finviz rest')]; tr=tr[tr.variant.map(lambda v:TRX(v,stockbars()['AAPL'],'AAPL') is not None)&tr.lens.isin(['fixed threshold','extreme vs own history','change since last value','cross','streak','divergence vs price'])]
nb=d[d.variant.isin(['Consecutive gap-ups','Up on SPY down day','SSR triggered','Inside day after big move','Beta breakdown'])|d.variant.str.startswith('beta-residual')]
cand=[('tf',pick(tf,230,'data_type')),('ja',pick(ja,170,['source','lens'])),('tr',pick(tr,60,'variant')),('nb',(nb.drop_duplicates('variant'),40))]
SIG={}
for tag,(df,quota) in cand:
    got=0
    for _,r in df.iterrows():
        if got>=quota: break
        f={'tf':tf_signal,'ja':james_signal,'tr':tr_signal,'nb':nb_signal}[tag]
        try: P=f(r)
        except Exception as e: P=None
        if P is None: continue
        SIG[r.id]=P.astype(float); got+=1
    print(tag,len(SIG),flush=True)
pickle.dump(SIG,open('signals.pkl','wb'))
