"""
Tilt-onset detector, per PREANALYSIS_PLAN_tilt.md Amendment 3.5.

Developed and validated ONLY on records whose published markers reconcile.
Acceptance gate, fixed in advance: median absolute error < 5 s and
90th-percentile absolute error < 15 s. Applied to unindexable records only if
the gate is passed.
"""
import json, glob, os, warnings, numpy as np, wfdb
warnings.filterwarnings("ignore")
from scipy.signal import butter, filtfilt, find_peaks

ROOT = "/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data"
TRUE_FS = 500
W = 90.0          # comparison half-window, seconds
STEP = 1.0        # search resolution, seconds
GUARD = 100.0     # tilt must be sustainable this long after onset


def beats(path):
    rec = wfdb.rdrecord(path, channel_names=["abp"])
    abp = rec.p_signal[:, 0]
    x = np.nan_to_num(abp)
    b, a = butter(2, [0.5/(TRUE_FS/2), 10/(TRUE_FS/2)], btype="band")
    y = filtfilt(b, a, x - x.mean())
    pk, _ = find_peaks(y, distance=int(0.35*TRUE_FS), prominence=np.std(y)*0.5)
    t, s, d = [], [], []
    for p, q in zip(pk[:-1], pk[1:]):
        if not (0.35*TRUE_FS <= (q-p) <= 2.0*TRUE_FS):
            continue
        seg = abp[p:q]
        hi, lo = float(np.nanmax(seg)), float(np.nanmin(seg))
        if not (40 <= lo <= 150 and 60 <= hi <= 260 and hi-lo >= 10):
            continue
        t.append(p/TRUE_FS); s.append(hi); d.append(lo)
    t, s, d = map(np.array, (t, s, d))
    hr = np.r_[np.nan, 60.0/np.diff(t)]
    return t, s, d, hr


def detect(t, s, d, hr, dur):
    """Largest sustained step in heart rate and diastolic pressure."""
    cand = np.arange(W + 10, dur - GUARD, STEP)
    best, best_score = None, -np.inf
    for c in cand:
        pre = (t >= c - W) & (t < c)
        post = (t >= c) & (t < c + W)
        if pre.sum() < 30 or post.sum() < 30:
            continue
        # tilt raises heart rate and diastolic pressure, and narrows pulse pressure
        dhr = np.nanmean(hr[post]) - np.nanmean(hr[pre])
        ddia = np.nanmean(d[post]) - np.nanmean(d[pre])
        dpp = np.nanmean((s-d)[pre]) - np.nanmean((s-d)[post])
        sd_hr = np.nanstd(hr[pre]) + 1e-6
        sd_d = np.nanstd(d[pre]) + 1e-6
        sd_p = np.nanstd((s-d)[pre]) + 1e-6
        score = dhr/sd_hr + ddia/sd_d + dpp/sd_p
        if score > best_score:
            best_score, best = score, c
    return best, best_score


def main():
    labels = json.load(open("tilt_labels.json"))
    truth = {r["record"]: r["tilt_start_s"] for r in labels
             if r["status"] == "OK" and "tilt_start_s" in r}

    rows = []
    for f in sorted(glob.glob(f"{ROOT}/Data/Labview/Converted/Head-up-tilt_Day*/*.dat")):
        base = f[:-4]; name = os.path.basename(base)
        try:
            t, s, d, hr = beats(base)
            if len(t) < 200:
                continue
            dur = t[-1]
            est, sc = detect(t, s, d, hr, dur)
            if est is None:
                continue
            rows.append(dict(record=name, est=round(float(est), 1),
                             score=round(float(sc), 2),
                             truth=truth.get(name),
                             day=1 if name.endswith("DA") else 2))
        except Exception as e:
            rows.append(dict(record=name, err=str(e)[:60]))

    val = [r for r in rows if r.get("truth") is not None]
    err = np.array([abs(r["est"] - r["truth"]) for r in val])
    print("=" * 60)
    print("TILT-ONSET DETECTOR, validated against reconciled markers")
    print("=" * 60)
    print(f"validation records : {len(val)}")
    print(f"median abs error   : {np.median(err):6.1f} s   gate < 5 s")
    print(f"90th pct abs error : {np.percentile(err,90):6.1f} s   gate < 15 s")
    print(f"mean abs error     : {err.mean():6.1f} s")
    print(f"within  5 s        : {100*(err<5).mean():5.1f} %")
    print(f"within 15 s        : {100*(err<15).mean():5.1f} %")
    print(f"within 30 s        : {100*(err<30).mean():5.1f} %")
    for day in (1, 2):
        e = np.array([abs(r["est"]-r["truth"]) for r in val if r["day"] == day])
        if len(e):
            print(f"   day {day}: n={len(e):3d}  median {np.median(e):5.1f} s  "
                  f"within15 {100*(e<15).mean():4.0f} %")
    gate = (np.median(err) < 5) and (np.percentile(err, 90) < 15)
    print(f"\nGATE: {'PASSED, detector may be applied to unindexable records' if gate else 'FAILED, detector NOT used'}")
    worst = sorted(val, key=lambda r: -abs(r["est"]-r["truth"]))[:8]
    print("\nworst cases (record, estimated, marker, error):")
    for r in worst:
        print(f"   {r['record']:>9s} {r['est']:8.1f} {r['truth']:8.1f} {abs(r['est']-r['truth']):7.1f}")
    json.dump(rows, open("tilt_onset.json", "w"), indent=1)


if __name__ == "__main__":
    main()
