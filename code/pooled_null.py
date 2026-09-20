import sys, json, numpy as np
sys.path.insert(0,'/sessions/amazing-sleepy-goldberg/mnt/outputs')
from pooled_data import pooled
from scipy import stats
rows,keep,X,y,g,coh,age,sex,base,rr=pooled()
def nullrun(mat,yy,gg,fn,n,seed):
    rng=np.random.default_rng(seed); uniq=np.unique(gg)
    sub={s:np.where(gg==s)[0] for s in uniq}; out=[]
    for _ in range(n):
        order=rng.permutation(len(uniq)); yp=yy.copy()
        for a,b in zip(uniq,uniq[order]):
            ia,ib=sub[a],sub[b]; k=min(len(ia),len(ib)); yp[ia[:k]]=yy[ib[:k]]
        p=rr.oof_predict(mat,yp,gg,fn,0); m=np.isfinite(p)
        r=stats.spearmanr(yp[m],p[m]).statistic
        if np.isfinite(r): out.append(float(r))
    return np.array(out)

obs=json.load(open("pooled_observed.json"))
res={}
for lab,mat,yy,gg,o in [("pooled ridge",X,y,g,obs["waveform ridge, pooled"]["rho"]),
                        ("diabetes only",X[coh==0],y[coh==0],g[coh==0],obs["diabetes only"]["rho"]),
                        ("stroke only",  X[coh==1],y[coh==1],g[coh==1],obs["stroke cves only"]["rho"])]:
    nl=nullrun(mat,yy,gg,rr.ridge,400,777)
    thr=float(np.percentile(nl,97.5)); p=float((nl>=o).mean())
    res[lab]=dict(n_perm=len(nl),null_mean=float(nl.mean()),thr97_5=thr,observed=float(o),p=p)
    print(f"  {lab:<15s} null mean {nl.mean():+.3f}  97.5pct {thr:+.3f}  observed {o:+.3f}  p={p:.3f}  "
          f"{'EXCEEDS' if o>thr else 'does NOT exceed'}")
json.dump(res, open("pooled_null.json","w"), indent=1)
