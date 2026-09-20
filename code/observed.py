import sys, json, numpy as np
sys.path.insert(0,'/sessions/amazing-sleepy-goldberg/mnt/outputs')
from _shared import data
from scipy import stats
from sklearn.metrics import mean_absolute_error
rows,keep,X,y,g,rr=data()
clin=rr.load_clinical()
base=np.array([r["baseline_SBP"] for r in rows],float)
age=np.array([clin.get(s,{}).get("age",np.nan) for s in g],float)
sex=np.array([clin.get(s,{}).get("sex",np.nan) for s in g],float)
print(f"records {len(rows)}  subjects {len(np.unique(g))}  features {len(keep)}")
print(f"delta_SBP mean {y.mean():.2f} sd {y.std(ddof=1):.2f}")
res={}
for name,fn,mat in [("waveform_ridge",rr.ridge,X),("waveform_gbt",rr.gbt,X),
                    ("floor_age_sex_baseSBP",rr.ridge,np.c_[age,sex,base])]:
    rh,ma,ps=[],[],[]
    for sd in rr.SEEDS:
        p=rr.oof_predict(mat,y,g,fn,sd); m=np.isfinite(p)
        rh.append(stats.spearmanr(y[m],p[m]).statistic); ma.append(mean_absolute_error(y[m],p[m])); ps.append(p)
    pm=np.nanmean(np.array(ps),axis=0)
    lo,hi=rr.cluster_bootstrap_rho(y,pm,g)
    res[name]=dict(rho=float(np.mean(rh)),rho_sd=float(np.std(rh)),mae=float(np.mean(ma)),ci=[float(lo),float(hi)],pred=pm.tolist())
    print(f"  {name:<24s} rho {np.mean(rh):+.3f} (sd {np.std(rh):.3f})  CI [{lo:+.3f},{hi:+.3f}]  MAE {np.mean(ma):5.2f}")
mm=mean_absolute_error(y,np.full_like(y,y.mean()))
print(f"  {'predict_the_mean':<24s} {'':38s} MAE {mm:5.2f}")
res["mae_predict_mean"]=float(mm)
res["better"]="waveform_gbt" if res["waveform_gbt"]["rho"]>res["waveform_ridge"]["rho"] else "waveform_ridge"
print(f"  better waveform model: {res['better']}")
json.dump(res,open("/sessions/amazing-sleepy-goldberg/mnt/outputs/observed.json","w"),indent=1)
