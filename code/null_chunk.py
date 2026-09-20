import sys, json, numpy as np
from scipy import stats
sys.path.insert(0,'/sessions/amazing-sleepy-goldberg/mnt/outputs')
from _shared import data
chunk=int(sys.argv[1]); nper=int(sys.argv[2]); model=sys.argv[3]
rows,keep,X,y,g,rr=data()
fn = rr.gbt if model=="gbt" else rr.ridge
rng=np.random.default_rng(12345+chunk*1000)
uniq=np.unique(g); sub={s:np.where(g==s)[0] for s in uniq}
out=[]
for i in range(nper):
    order=rng.permutation(len(uniq)); yp=y.copy()
    for a,b in zip(uniq,uniq[order]):
        ia,ib=sub[a],sub[b]; n=min(len(ia),len(ib)); yp[ia[:n]]=y[ib[:n]]
    p=rr.oof_predict(X,yp,g,fn,0); m=np.isfinite(p)
    r=stats.spearmanr(yp[m],p[m]).statistic
    if np.isfinite(r): out.append(float(r))
json.dump(out, open(f"/sessions/amazing-sleepy-goldberg/mnt/outputs/null_{model}_{chunk}.json","w"))
print(f"chunk {chunk} model {model}: {len(out)} perms, mean {np.mean(out):+.3f}, 97.5pct {np.percentile(out,97.5):+.3f}")
