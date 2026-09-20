import json, numpy as np, warnings
warnings.filterwarnings("ignore")
import importlib.util
spec=importlib.util.spec_from_file_location("rr","/sessions/amazing-sleepy-goldberg/mnt/outputs/run_regression.py")
rr=importlib.util.module_from_spec(spec); spec.loader.exec_module(rr)
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
META=set(rr.META)|{"cohort","age","sex","group"}

def pooled():
    dia=[r for r in json.load(open(f"{OUT}/pretilt_features.json")) if r.get("delta_SBP") is not None]
    clin=rr.load_clinical()
    for r in dia:
        r["cohort"]="diabetes"
        c=clin.get(r["subject"],{})
        r["age"]=c.get("age",np.nan); r["sex"]=c.get("sex",np.nan); r["group"]=c.get("group","?")
        r["subject"]="DIA_"+r["subject"]
    cv=[r for r in json.load(open(f"{OUT}/cves_features.json")) if r.get("delta_SBP") is not None]
    for r in cv:
        r["subject"]="CVE_"+r["subject"]
    rows=dia+cv
    # features usable in BOTH cohorts: >=90% complete within each
    cand=sorted({k for r in rows for k in r if k not in META and not k.startswith("DB1ONLY")})
    keep=[]
    for k in cand:
        ok=True
        for grp in (dia,cv):
            n=sum(1 for r in grp if isinstance(r.get(k),(int,float)) and np.isfinite(r.get(k)))
            if n < 0.9*len(grp): ok=False
        if ok: keep.append(k)
    X=np.array([[float(r.get(k)) if isinstance(r.get(k),(int,float)) and np.isfinite(r.get(k)) else np.nan
                 for k in keep] for r in rows])
    y=np.array([r["delta_SBP"] for r in rows],float)
    g=np.array([r["subject"] for r in rows])
    coh=np.array([1.0 if r["cohort"]=="cves" else 0.0 for r in rows])
    age=np.array([r.get("age",np.nan) for r in rows],float)
    sex=np.array([r.get("sex",np.nan) for r in rows],float)
    base=np.array([r["baseline_SBP"] for r in rows],float)
    return rows,keep,X,y,g,coh,age,sex,base,rr
