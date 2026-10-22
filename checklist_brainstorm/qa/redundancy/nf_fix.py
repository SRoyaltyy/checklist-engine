import sys;sys.path.insert(0,'.');from engine import *;prep()
import pickle
S=pickle.load(open('signals.pkl','rb'));d=pd.read_pickle('tagged.pkl').set_index('id',drop=False)
rows=[]
for k in list(S):
    if k not in d.index: continue
    r=d.loc[k]
    if not (r.merge_owner=='taskforce' and r.variant.startswith('CDL')): continue
    old=S[k].stack().mean(); P=tf_signal(r); S[k]=P.astype(float); new=S[k].stack().mean()
    rows.append((k,r.variant,r.lens,ONE_SIDED.get(r.variant),round(old,4),round(new,4)))
pickle.dump(S,open('signals.pkl','wb'))
o=pd.DataFrame(rows,columns=['id','variant','lens','plus100_only','old_rate','new_rate']);o.to_csv('never_fire_recheck.csv',index=False);print(o.to_string())
R=[(k,P.stack().mean()) for k,P in S.items()];R=[x for x in R if x[1]<=0 or x[1]>=0.999];print('never/always now:',R)
