import sys, json, numpy as np
sys.path.insert(0,'/sessions/amazing-sleepy-goldberg/mnt/outputs')
from pooled_data import pooled
from scipy import stats
from sklearn.metrics import mean_absolute_error, roc_auc_score
rows,keep,X,y,g,coh,age,sex,base,rr=pooled()
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
res={}
def run(name, fn, mat, yy=y, gg=g):
    rh,ma,ps=[],[],[]
    for sd in rr.SEEDS:
        p=rr.oof_predict(mat,yy,gg,fn,sd); m=np.isfinite(p)
        rh.append(stats.spearmanr(yy[m],p[m]).statistic); ma.append(mean_absolute_error(yy[m],p[m])); ps.append(p)
    pm=np.nanmean(np.array(ps),axis=0)
    lo,hi=rr.cluster_bootstrap_rho(yy,pm,gg)
    res[name]=dict(rho=float(np.mean(rh)),rho_sd=float(np.std(rh)),mae=float(np.mean(ma)),
                   ci=[float(lo),float(hi)],n=int(len(yy)),pred=pm.tolist())
    print(f"  {name:<34s} n={len(yy):3d}  rho {np.mean(rh):+.3f} (sd {np.std(rh):.3f})  "
          f"CI [{lo:+.3f},{hi:+.3f}]  MAE {np.mean(ma):5.2f}")
    return pm

print("="*74); print("POOLED TWO-COHORT ANALYSIS, Amendment 4.5"); print("="*74)
print(f"125 records, 105 subjects, {len(keep)} features shared by both cohorts\n")
run("waveform ridge, pooled", rr.ridge, X)
run("waveform GBT, pooled",   rr.gbt,   X)
run("waveform+cohort GBT",    rr.gbt,   np.c_[X,coh])
run("FLOOR age+sex+baseSBP",  rr.ridge, np.c_[age,sex,base])
run("FLOOR + cohort",         rr.ridge, np.c_[age,sex,base,coh])
mm=mean_absolute_error(y,np.full_like(y,y.mean()))
print(f"  {'BASELINE predict the mean':<34s} {'':41s}MAE {mm:5.2f}")
res["mae_predict_mean"]=float(mm)

print("\n  within cohort:")
for nm,sel in [("diabetes only",coh==0),("stroke cves only",coh==1)]:
    run(nm, rr.gbt, X[sel], y[sel], g[sel])
    print(f"    {'':32s}   predict-the-mean MAE "
          f"{mean_absolute_error(y[sel],np.full(sel.sum(),y[sel].mean())):5.2f}")

print("\n  CONFOUND CHECK 10 extended: is COHORT predictable from the features?")
p=rr.oof_predict(X,coh,g,rr.gbt,0); m=np.isfinite(p)
auc=roc_auc_score(coh[m].astype(int),p[m])
print(f"    AUROC predicting cohort = {auc:.3f}   {'FAIL >0.70, report within-cohort only' if auc>0.70 else 'ok'}")
res["auc_cohort"]=float(auc)
res["better"]=max(["waveform ridge, pooled","waveform GBT, pooled","waveform+cohort GBT"],
                  key=lambda k:res[k]["rho"])
print(f"\n  better waveform model: {res['better']}  (rho {res[res['better']]['rho']:+.3f})")
json.dump(res, open(f"{OUT}/pooled_observed.json","w"), indent=1)
