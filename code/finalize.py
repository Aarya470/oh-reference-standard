import sys, json, glob, numpy as np
sys.path.insert(0,'/sessions/amazing-sleepy-goldberg/mnt/outputs')
from _shared import data
from scipy import stats
from sklearn.metrics import roc_auc_score
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
rows,keep,X,y,g,rr=data()
obs=json.load(open(f"{OUT}/observed.json"))
clin=rr.load_clinical()
base=np.array([r["baseline_SBP"] for r in rows],float)
day=np.array([r["day"] for r in rows],float)
grp=np.array([clin.get(s,{}).get("group","?") for s in g])

null_r=json.load(open(f"{OUT}/null_ridge_0.json"))
null_g=sum((json.load(open(f)) for f in sorted(glob.glob(f"{OUT}/null_gbt_*.json"))),[])
print("="*68); print("PRE-REGISTERED RESULTS, Amendment 3.3 and 3.7"); print("="*68)
print(f"records {len(rows)}  subjects {len(np.unique(g))}  features {len(keep)}")
print(f"outcome delta_SBP: mean {y.mean():+.2f}  sd {y.std(ddof=1):.2f} mmHg\n")
for k in ["waveform_ridge","waveform_gbt","floor_age_sex_baseSBP"]:
    v=obs[k]; print(f"  {k:<24s} rho {v['rho']:+.3f}  95% CI [{v['ci'][0]:+.3f},{v['ci'][1]:+.3f}]  MAE {v['mae']:5.2f} mmHg")
print(f"  {'predict_the_mean':<24s} {'':38s}MAE {obs['mae_predict_mean']:5.2f} mmHg")

print("\n  PERMUTATION NULL, subject-level block permutation")
for nm,nl,obsrho in [("ridge",null_r,obs["waveform_ridge"]["rho"]),
                     ("GBT",  null_g,obs["waveform_gbt"]["rho"])]:
    nl=np.array(nl); thr=np.percentile(nl,97.5); p=float((nl>=obsrho).mean())
    print(f"    {nm:<6s} n={len(nl):4d}  null mean {nl.mean():+.3f}  97.5th pct {thr:+.3f}"
          f"  observed {obsrho:+.3f}  p={p:.3f}  {'EXCEEDS' if obsrho>thr else 'does NOT exceed'}")
    if nm=="GBT": gthr,gp=thr,p

print("\n  CONFOUND CHECKS, Amendment 3.6")
p_day=rr.oof_predict(X,day,g,rr.ridge,0); m=np.isfinite(p_day)
auc=roc_auc_score((day[m]==2).astype(int),p_day[m])
print(f"    10 day predictable from features: AUROC {auc:.3f}  {'FAIL' if auc>0.70 else 'ok'}")
pre=np.array([r['tilt_start_s'] for r in rows],float)
rd=stats.spearmanr(pre,y); rb=stats.spearmanr(base,y)
print(f"    11 pre-tilt duration vs outcome : rho {rd.statistic:+.3f} p={rd.pvalue:.3f}")
print(f"    12 baseline SBP vs outcome      : rho {rb.statistic:+.3f} p={rb.pvalue:.3f}")
pm=np.array(obs[obs["better"]]["pred"],float)
print("    13 by clinical group:")
for gg in ["Control","DM","DMOH"]:
    s=(grp==gg)&np.isfinite(pm)
    if s.sum()>=8: print(f"       {gg:<8s} n={s.sum():3d} rho {stats.spearmanr(y[s],pm[s]).statistic:+.3f}")
print(f"    14 subjects with two records: {sum(1 for s in np.unique(g) if (g==s).sum()>1)}")

print("\n"+"="*68); print("FALSIFICATION CONDITIONS, Amendment 3.7"); print("="*68)
b=obs[obs["better"]]
c=[("rho does not exceed the permutation null", b["rho"]<=gthr),
   ("waveform model does not beat the age/sex/baselineSBP floor", b["rho"]<=obs["floor_age_sex_baseSBP"]["rho"]),
   ("MAE not better than predicting the cohort mean", b["mae"]>=obs["mae_predict_mean"]),
   ("day predictable from features, AUROC > 0.70", auc>0.70)]
for lab,fired in c: print(f"  [{'X FIRED ' if fired else '   ok   '}] {lab}")
verdict="NEGATIVE" if any(f for _,f in c) else "POSITIVE"
print(f"\n  C4 VERDICT: {verdict}")
json.dump(dict(observed=obs,null_ridge_n=len(null_r),null_gbt_n=len(null_g),
               null_gbt_97_5=float(gthr),null_gbt_p=float(gp),auc_day=float(auc),
               rho_duration=float(rd.statistic),rho_baseline=float(rb.statistic),
               verdict=verdict,
               fired=[l for l,f in c if f]),
          open(f"{OUT}/regression_results.json","w"),indent=1)
