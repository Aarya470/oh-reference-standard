"""
cves segmentation and labelling, per PREANALYSIS_PLAN_tilt.md Amendment 4.3-4.5.

Anchoring rule fixed in advance from the laboratory's own protocol:
the head-up tilt is the final event, so tilt onset is the second-to-last marker
pulse and tilt end is the last. Acceptance window 240 to 900 s.

Three readings computed, exactly as in Amendment 2:
  A  minimum of a 10 s rolling mean across the tilt
  B  clinical timepoints, 1 min and 3 min, +/-15 s means   [primary]
  C  mean of the final 60 s of the first 180 s of tilt
"""
import glob, json, os, csv, warnings, numpy as np, wfdb
warnings.filterwarnings("ignore")
from scipy.signal import butter, filtfilt, find_peaks

ROOT="/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data/cves"
OUT="/sessions/amazing-sleepy-goldberg/mnt/outputs"
BASELINE_S=60.0; HALF=15.0; TIMEPOINTS=(60.0,180.0)
INITIAL_SKIP=30.0; SUSTAIN_S=10.0; TILT_MAX_S=180.0
MIN_TILT=240.0; MAX_TILT=900.0; ABORT_BELOW=540.0

def pulses(path, fs):
    r=wfdb.rdrecord(path, channel_names=["marker"]); m=r.p_signal[:,0]
    hi=m>0.5; d=np.diff(hi.astype(int)); s=np.where(d==1)[0]+1
    if hi[0]: s=np.r_[0,s]
    out=[]
    for x in s:
        if not out or x-out[-1]>0.3*fs: out.append(int(x))
    return np.array(out,dtype=int), len(m)

def beats(path):
    rec=wfdb.rdrecord(path, channel_names=["abp"]); abp=rec.p_signal[:,0]; fs=rec.fs
    x=np.nan_to_num(abp)
    b,a=butter(2,[0.5/(fs/2),10/(fs/2)],btype="band")
    y=filtfilt(b,a,x-x.mean())
    pk,_=find_peaks(y,distance=int(0.35*fs),prominence=np.std(y)*0.5)
    t,s,d=[],[],[]
    for p,q in zip(pk[:-1],pk[1:]):
        if not (0.35*fs<=(q-p)<=2.0*fs): continue
        seg=abp[p:q]; hi,lo=float(np.nanmax(seg)),float(np.nanmin(seg))
        if not (40<=lo<=150 and 60<=hi<=260 and hi-lo>=10): continue
        t.append(p/fs); s.append(hi); d.append(lo)
    return np.array(t),np.array(s),np.array(d),fs

def rolling(t,v,win):
    o=np.full(len(v),np.nan)
    for i,ti in enumerate(t):
        m=(t>=ti-win/2)&(t<=ti+win/2)
        if m.sum()>=3: o[i]=np.nanmean(v[m])
    return o

rows=[]
for h in sorted(glob.glob(f"{ROOT}/data/head-up-tilt/*.hea")):
    base=h[:-4]; name=os.path.basename(base); sid="S"+name[1:5]
    R={"record":name,"subject":sid,"cohort":"cves"}
    hdr=open(h).readline().split(); fs=float(hdr[2])
    R["fs_in_header"]=fs
    try:
        pk,nsamp=pulses(base,fs)
    except Exception as e:
        R["status"]=f"ERROR_{type(e).__name__}"; rows.append(R); continue
    R["duration_s"]=round(nsamp/fs,1); R["n_pulses"]=len(pk)
    if len(pk)<4:
        R["status"]=f"EXCLUDED_only_{len(pk)}_pulses"; rows.append(R); continue
    t0,t1 = pk[-2]/fs, pk[-1]/fs
    span=t1-t0
    R["tilt_start_s"]=round(t0,1); R["tilt_span_s"]=round(span,1)
    if not (MIN_TILT<=span<=MAX_TILT):
        R["status"]=f"EXCLUDED_final_interval_{span:.0f}s"; rows.append(R); continue
    R["possibly_aborted"]=bool(span<ABORT_BELOW)
    if t0 < BASELINE_S+10:
        R["status"]="EXCLUDED_insufficient_baseline"; rows.append(R); continue
    try:
        bt,bs,bd,_=beats(base)
    except Exception as e:
        R["status"]=f"ERROR_{type(e).__name__}"; rows.append(R); continue
    if len(bt)<200:
        R["status"]=f"EXCLUDED_beats_{len(bt)}"; rows.append(R); continue
    R["n_beats"]=len(bt)
    hr=np.r_[np.nan,60.0/np.diff(bt)]
    R["mean_hr_record"]=round(float(np.nanmean(hr)),1)
    bm=(bt>=t0-BASELINE_S)&(bt<t0)
    if bm.sum()<20:
        R["status"]="EXCLUDED_baseline_beats"; rows.append(R); continue
    s0,d0=float(np.nanmean(bs[bm])),float(np.nanmean(bd[bm]))
    R["baseline_SBP"]=round(s0,1); R["baseline_DBP"]=round(d0,1)
    R["baseline_HR"]=round(float(np.nanmean(hr[bm])),1)
    tend=min(t1,t0+TILT_MAX_S)
    # reading A
    sm=(bt>=t0+INITIAL_SKIP)&(bt<=tend)
    if sm.sum()>=20:
        ra=rolling(bt[sm],bs[sm],SUSTAIN_S); rb=rolling(bt[sm],bd[sm],SUSTAIN_S)
        R["A_dSBP"]=round(float(s0-np.nanmin(ra)),2); R["A_dDBP"]=round(float(d0-np.nanmin(rb)),2)
        R["A_OH"]=int((R["A_dSBP"]>=20) or (R["A_dDBP"]>=10))
    # reading B, primary
    ds,dd,used=[],[],[]
    for tp in TIMEPOINTS:
        if t0+tp-HALF>t1: continue
        m=(bt>=t0+tp-HALF)&(bt<=t0+tp+HALF)
        if m.sum()<8: continue
        ds.append(s0-float(np.nanmean(bs[m]))); dd.append(d0-float(np.nanmean(bd[m]))); used.append(tp)
    if ds:
        k=int(np.argmax(ds))
        R["delta_SBP"]=round(ds[k],2); R["delta_DBP"]=round(dd[k],2); R["at_timepoint"]=used[k]
        R["delta_SBP_pct"]=round(100*ds[k]/s0,2)
        R["B_OH"]=int((ds[k]>=20) or (dd[k]>=10))
    # reading C
    m=(bt>=tend-60)&(bt<=tend)
    if m.sum()>=20:
        R["C_dSBP"]=round(float(s0-np.nanmean(bs[m])),2)
        R["C_dDBP"]=round(float(d0-np.nanmean(bd[m])),2)
        R["C_OH"]=int((R["C_dSBP"]>=20) or (R["C_dDBP"]>=10))
    R["status"]="OK" if "B_OH" in R else "EXCLUDED_no_timepoint_window"
    rows.append(R)

json.dump(rows, open(f"{OUT}/cves_labels.json","w"), indent=1)
ok=[r for r in rows if r["status"]=="OK"]
from collections import Counter
print("="*64); print("cves, Amendment 4.3 anchoring"); print("="*64)
print(f"records {len(rows)}   usable {len(ok)}   excluded {len(rows)-len(ok)}")
for k,v in Counter(r["status"] for r in rows if r["status"]!="OK").most_common():
    print(f"   {v:3d}  {k}")
if ok:
    print(f"\nheader fs: {set(r['fs_in_header'] for r in ok)}")
    print(f"mean HR median {np.median([r['mean_hr_record'] for r in ok]):.0f} bpm "
          f"(range {min(r['mean_hr_record'] for r in ok):.0f} to {max(r['mean_hr_record'] for r in ok):.0f})")
    print(f"tilt span median {np.median([r['tilt_span_s'] for r in ok]):.0f} s "
          f"(protocol says 600 s)   possibly aborted: {sum(r.get('possibly_aborted',False) for r in ok)}")
    print("\nTHREE READINGS, same recordings:")
    for k,lab in [("A_OH","A minimum across tilt"),("B_OH","B clinical timepoints"),("C_OH","C final 60 s")]:
        v=[r[k] for r in ok if k in r]
        print(f"   {lab:<24s} n={len(v):3d}   OH in {100*np.mean(v):5.1f} %")
