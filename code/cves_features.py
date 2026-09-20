"""
Pre-tilt features for the cves stroke cohort.

Same feature functions as pretilt_features.py (Amendment 3.4), same leakage
assertion. Windows chosen to be comparable across cohorts:
  R  resting   first 60 s of the record's opening baseline
  P  pre-tilt  the 120 s immediately before tilt onset
Valsalva is not used here: cves has no per-subject marker table, so individual
Valsalva pulses cannot be identified without inference. Excluding it keeps the
pooled feature set honest rather than guessed.
"""
import glob, json, os, csv, warnings, numpy as np, wfdb
warnings.filterwarnings("ignore")
import importlib.util
spec=importlib.util.spec_from_file_location("pf","/sessions/amazing-sleepy-goldberg/mnt/outputs/pretilt_features.py")
pf=importlib.util.module_from_spec(spec); spec.loader.exec_module(pf)

ROOT="/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data/cves"
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
REST_S=60.0; PRETILT_S=120.0

# cves is natively 500 Hz, which is also the corrected rate for the diabetes set,
# so the shared feature code needs no rate override here.
assert pf.TRUE_FS == 500

labels=[r for r in json.load(open(f"{OUT}/cves_labels.json")) if r["status"]=="OK"]
rows=[]
for lab in labels:
    path=f"{ROOT}/data/head-up-tilt/{lab['record']}"
    t_tilt=lab["tilt_start_s"]; i_tilt=int(round(t_tilt*pf.TRUE_FS))
    rec=wfdb.rdrecord(path, sampto=i_tilt, channel_names=["abp"])
    assert rec.p_signal.shape[0] <= i_tilt, "pre-tilt slice reached the tilt window"
    abp=rec.p_signal[:,0]
    t,s,d,ibi=pf.beat_series(abp)
    assert len(t)==0 or t[-1] < t_tilt, "beat at or after tilt onset"

    F={"record":lab["record"],"subject":lab["subject"],"cohort":"cves","day":2,
       "tilt_start_s":t_tilt,
       "delta_SBP":lab.get("delta_SBP"),"delta_DBP":lab.get("delta_DBP"),
       "delta_SBP_pct":lab.get("delta_SBP_pct"),
       "baseline_SBP":lab.get("baseline_SBP"),"baseline_DBP":lab.get("baseline_DBP"),
       "at_timepoint":lab.get("at_timepoint")}

    m=(t>=t[0])&(t< t[0]+REST_S) if len(t) else np.array([],bool)
    if m.sum()>=30:
        F.update(pf.hrv(ibi[m],"R")); F.update(pf.bp_variability(s[m],d[m],"R"))
        F.update(pf.gas(path,int(t[0]*pf.TRUE_FS),int((t[0]+REST_S)*pf.TRUE_FS),"R"))
    m=(t>=t_tilt-PRETILT_S)&(t<t_tilt)
    if m.sum()>=60:
        F.update(pf.hrv(ibi[m],"P")); F.update(pf.bp_variability(s[m],d[m],"P"))
        F.update(pf.spectral(t[m],ibi[m],"P","IBI")); F.update(pf.spectral(t[m],s[m],"P","SBP"))
        F.update(pf.brs_sequence(s[m],ibi[m],"P")); F.update(pf.brs_alpha(t[m],s[m],ibi[m],"P"))
        F.update(pf.gas(path,int((t_tilt-PRETILT_S)*pf.TRUE_FS),i_tilt,"P"))
    rows.append(F)

# clinical covariates
R=list(csv.reader(open(f"{ROOT}/subjects.csv")))
clin={r[0].strip():r for r in R[1:] if r and r[0].strip().startswith("S")}
num=lambda x:(float(x) if str(x).strip() not in ("","na","n/a","n",".") else np.nan)
for F in rows:
    c=clin.get(F["subject"])
    if c:
        F["age"]=num(c[5]); F["sex"]=1.0 if c[9].strip().upper().startswith("F") else 0.0
        F["group"]=c[3].strip()

json.dump(rows, open(f"{OUT}/cves_features.json","w"), indent=1)
keys=sorted({k for r in rows for k in r})
print(f"records {len(rows)}  feature columns {len(keys)}")
feat=[k for k in keys if k not in ("record","subject","cohort","day","tilt_start_s",
     "delta_SBP","delta_DBP","delta_SBP_pct","baseline_SBP","baseline_DBP",
     "at_timepoint","age","sex","group")]
comp={k:sum(1 for r in rows if isinstance(r.get(k),(int,float)) and np.isfinite(r[k])) for k in feat}
print(f"complete on every record: {sum(1 for v in comp.values() if v==len(rows))} of {len(feat)}")
print("with outcome:", sum(1 for r in rows if r.get("delta_SBP") is not None))
print("with age    :", sum(1 for r in rows if np.isfinite(r.get("age",np.nan))))
