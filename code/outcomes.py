"""
Primary outcome per PREANALYSIS_PLAN_tilt.md Amendment 3.2.

delta_SBP = supine baseline systolic minus the mean systolic in a +/-15 s window
centred on the 1-minute and 3-minute tilt timepoints, taking whichever timepoint
gives the larger fall. Definition B of Amendment 2, kept continuous.
Positive means the pressure fell.
"""
import json, numpy as np, wfdb, warnings
warnings.filterwarnings("ignore")
from scipy.signal import butter, filtfilt, find_peaks

ROOT="/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data"; TRUE_FS=500
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
BASELINE_S=60.0; HALF=15.0; TIMEPOINTS=(60.0,180.0)

def beats(path):
    rec=wfdb.rdrecord(path, channel_names=["abp"]); abp=rec.p_signal[:,0]
    x=np.nan_to_num(abp)
    b,a=butter(2,[0.5/(TRUE_FS/2),10/(TRUE_FS/2)],btype="band")
    y=filtfilt(b,a,x-x.mean())
    pk,_=find_peaks(y,distance=int(0.35*TRUE_FS),prominence=np.std(y)*0.5)
    t,s,d=[],[],[]
    for p,q in zip(pk[:-1],pk[1:]):
        if not (0.35*TRUE_FS<=(q-p)<=2.0*TRUE_FS): continue
        seg=abp[p:q]; hi,lo=float(np.nanmax(seg)),float(np.nanmin(seg))
        if not (40<=lo<=150 and 60<=hi<=260 and hi-lo>=10): continue
        t.append(p/TRUE_FS); s.append(hi); d.append(lo)
    return map(np.array,(t,s,d))

lab=[r for r in json.load(open(f"{OUT}/tilt_labels.json")) if r["status"]=="OK"]
res={}
for r in lab:
    fold="Head-up-tilt_Day1" if r["day"]==1 else "Head-up-tilt_Day2"
    p=f"{ROOT}/Data/Labview/Converted/{fold}/{r['record']}"
    t,s,d=beats(p)
    t0=r["tilt_start_s"]; t1=t0+r["tilt_window_s"]
    bm=(t>=t0-BASELINE_S)&(t<t0)
    if bm.sum()<20: continue
    s0,d0=float(np.nanmean(s[bm])),float(np.nanmean(d[bm]))
    ds,dd,used=[],[],[]
    for tp in TIMEPOINTS:
        if t0+tp-HALF > t1: continue
        m=(t>=t0+tp-HALF)&(t<=t0+tp+HALF)
        if m.sum()<8: continue
        ds.append(s0-float(np.nanmean(s[m]))); dd.append(d0-float(np.nanmean(d[m])))
        used.append(tp)
    if not ds: continue
    k=int(np.argmax(ds))
    res[r["record"]]=dict(delta_SBP=round(ds[k],2), delta_DBP=round(dd[k],2),
                          at_timepoint=used[k], baseline_SBP=round(s0,1),
                          baseline_DBP=round(d0,1),
                          delta_SBP_pct=round(100*ds[k]/s0,2),
                          timepoints_available=len(ds))

feats=json.load(open(f"{OUT}/pretilt_features.json"))
n=0
for f in feats:
    o=res.get(f["record"])
    if o: f.update(o); n+=1
json.dump(feats, open(f"{OUT}/pretilt_features.json","w"), indent=1)
json.dump(res, open(f"{OUT}/outcomes.json","w"), indent=1)

v=np.array([f["delta_SBP"] for f in feats if f.get("delta_SBP") is not None])
print(f"records with outcome : {n} of {len(feats)}")
print(f"delta_SBP  mean {v.mean():6.2f}  sd {v.std(ddof=1):6.2f}  "
      f"min {v.min():6.1f}  median {np.median(v):6.1f}  max {v.max():6.1f} mmHg")
print(f"  >= 20 mmHg (would be OH by SBP): {int((v>=20).sum())} of {len(v)}")
tp=[f["at_timepoint"] for f in feats if f.get("at_timepoint")]
print(f"  larger fall at 1 min: {tp.count(60.0)}   at 3 min: {tp.count(180.0)}")
