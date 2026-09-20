"""
Derive the orthostatic-hypotension label for every head-up tilt recording in the
PhysioNet cerebral-vasoreg-diabetes dataset, per PREANALYSIS_PLAN_tilt.md
sections 3 and 4 as amended by Amendment 1.

AMENDMENT 1 IS IN FORCE HERE:
  * the published header rate of 1000 Hz is wrong, the true rate is 500 Hz
  * the first 30 s after tilt onset is excluded, because consensus OH is a
    sustained fall and the first seconds are initial orthostatic hypotension,
    which healthy people also show

No model is fitted in this file. Labels and audit information only.

Output: tilt_labels.json, tilt_labels.csv
"""

import os, csv, json, glob, warnings
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt, find_peaks

warnings.filterwarnings("ignore")

ROOT = "/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data"
OUT  = "/sessions/amazing-sleepy-goldberg/mnt/outputs"

# ------------------------------------------------- Amendment 1, sampling rate
TRUE_FS = 500          # headers claim 1000; six independent checks say 500
HEADER_FS = 1000

# ------------------------------------------------------------- label constants
SUSTAIN_S    = 10      # rolling window defining "sustained"
BASELINE_S   = 60      # supine baseline immediately before tilt
INITIAL_SKIP = 30      # Amendment 1: exclude initial orthostatic hypotension
OH_SBP_DROP  = 20.0
OH_DBP_DROP  = 10.0
OT_HR_RISE   = 30.0
TILT_MAX_S   = 180     # consensus window


def sec(n_samples):
    """Samples to seconds at the true rate."""
    return n_samples / TRUE_FS


def smp(seconds):
    """Seconds to samples at the true rate."""
    return int(round(seconds * TRUE_FS))


# ------------------------------------------------------------------- markers
def marker_pulses(path):
    r = wfdb.rdrecord(path, channel_names=["marker"])
    m = r.p_signal[:, 0]
    hi = m > 0.5
    d = np.diff(hi.astype(int))
    s = np.where(d == 1)[0] + 1
    if hi[0]:
        s = np.r_[0, s]
    merged = []
    for x in s:
        if not merged or x - merged[-1] > smp(0.3):
            merged.append(int(x))
    return np.array(merged, dtype=int), len(m)


def load_marker_table(path):
    rows = list(csv.reader(open(path)))
    return rows[0], {r[0]: r for r in rows[1:] if r and r[0].startswith("S")}


# --------------------------------------------------------------------- beats
def abp_beats(abp):
    """
    Beat locations from the arterial pressure wave itself.

    The ecg channel in this dataset is not used for beat location. Standard
    R-peak detectors (including neurokit2) return roughly twice the true rate
    on it, and the arterial wave gives an unambiguous one-peak-per-beat count
    that agrees with the spectral dominant frequency.
    """
    x = np.nan_to_num(abp)
    b, a = butter(2, [0.5 / (TRUE_FS / 2), 10 / (TRUE_FS / 2)], btype="band")
    y = filtfilt(b, a, x - np.mean(x))
    pk, _ = find_peaks(y, distance=smp(0.35), prominence=np.std(y) * 0.5)
    return pk


def beatwise_bp(abp, pk):
    """Systolic and diastolic per beat, bounded by consecutive systolic peaks."""
    t, sys, dia = [], [], []
    for a, b in zip(pk[:-1], pk[1:]):
        if not (smp(0.35) <= (b - a) <= smp(2.0)):
            continue
        seg = abp[a:b]
        if np.all(np.isnan(seg)):
            continue
        s, d = float(np.nanmax(seg)), float(np.nanmin(seg))
        if not (40 <= d <= 150 and 60 <= s <= 260 and (s - d) >= 10):
            continue
        t.append(sec(a))
        sys.append(s)
        dia.append(d)
    return np.array(t), np.array(sys), np.array(dia)


def rolling(t, v, win):
    out = np.full(len(v), np.nan)
    for i, ti in enumerate(t):
        m = (t >= ti - win / 2) & (t <= ti + win / 2)
        if m.sum() >= 3:
            out[i] = np.nanmean(v[m])
    return out


# ---------------------------------------------------------------- per record
def process(path, sid, day, tilt_ord, end_ord, table_maxord):
    res = {"subject": sid, "day": day, "record": os.path.basename(path),
           "fs_used": TRUE_FS, "fs_in_header": HEADER_FS}

    pk_idx, n_samp = marker_pulses(path)
    dur = sec(n_samp)
    res["duration_s"] = round(dur, 1)
    res["n_pulses"] = len(pk_idx)
    res["table_max_ordinal"] = table_maxord

    if table_maxord > len(pk_idx):
        res["status"] = f"EXCLUDED_marker_mismatch_need{table_maxord}_have{len(pk_idx)}"
        return res
    if not tilt_ord or tilt_ord > len(pk_idx):
        res["status"] = "EXCLUDED_no_tilt_marker"
        return res

    i0 = int(pk_idx[tilt_ord - 1])
    i1 = int(pk_idx[end_ord - 1]) if (end_ord and end_ord <= len(pk_idx)) else i0 + smp(TILT_MAX_S)
    if sec(i1 - i0) < 60:
        res["status"] = f"EXCLUDED_tilt_window_{sec(i1-i0):.0f}s"
        return res
    i1 = min(i1, i0 + smp(TILT_MAX_S), n_samp)

    res["tilt_start_s"] = round(sec(i0), 1)
    res["tilt_window_s"] = round(sec(i1 - i0), 1)
    res["tilt_truncated"] = bool(sec(i1 - i0) < TILT_MAX_S)

    if sec(i0) < BASELINE_S + 10:
        res["status"] = "EXCLUDED_insufficient_supine_baseline"
        return res

    rec = wfdb.rdrecord(path, channel_names=["abp"])
    abp = rec.p_signal[:, 0]

    pk = abp_beats(abp)
    if len(pk) < 100:
        res["status"] = f"EXCLUDED_abp_peaks_{len(pk)}"
        return res

    bt, bs, bd = beatwise_bp(abp, pk)
    if len(bt) < 100:
        res["status"] = f"EXCLUDED_clean_beats_{len(bt)}"
        return res
    res["n_beats_total"] = len(bt)
    res["beat_yield"] = round(len(bt) / max(1, len(pk) - 1), 3)

    hr = np.r_[np.nan, 60.0 / np.diff(bt)]
    res["mean_hr_record"] = round(float(np.nanmean(hr)), 1)

    t0, t1 = sec(i0), sec(i1)
    base = (bt >= t0 - BASELINE_S) & (bt < t0)
    # Amendment 1: sustained window starts 30 s after tilt onset
    sust = (bt >= t0 + INITIAL_SKIP) & (bt <= t1)
    init = (bt >= t0) & (bt < t0 + INITIAL_SKIP)

    res["n_beats_baseline"] = int(base.sum())
    res["n_beats_sustained"] = int(sust.sum())
    if base.sum() < 30 or sust.sum() < 30:
        res["status"] = "EXCLUDED_too_few_clean_beats"
        return res

    sbp0, dbp0 = float(np.nanmean(bs[base])), float(np.nanmean(bd[base]))
    hr0 = float(np.nanmean(hr[base]))
    res.update(baseline_sbp=round(sbp0, 1), baseline_dbp=round(dbp0, 1),
               baseline_hr=round(hr0, 1))

    rs = rolling(bt[sust], bs[sust], SUSTAIN_S)
    rd = rolling(bt[sust], bd[sust], SUSTAIN_S)
    rh = rolling(bt[sust], hr[sust], SUSTAIN_S)

    drop_s = sbp0 - np.nanmin(rs) if np.isfinite(rs).any() else np.nan
    drop_d = dbp0 - np.nanmin(rd) if np.isfinite(rd).any() else np.nan
    rise_h = np.nanmax(rh) - hr0 if np.isfinite(rh).any() else np.nan

    res.update(max_sbp_drop=round(float(drop_s), 1),
               max_dbp_drop=round(float(drop_d), 1),
               max_hr_rise=round(float(rise_h), 1))

    # descriptive only, reported separately, never the primary label
    if init.sum() >= 5:
        res["initial_sbp_drop"] = round(float(sbp0 - np.nanmin(bs[init])), 1)

    res["OH"] = int((drop_s >= OH_SBP_DROP) or (drop_d >= OH_DBP_DROP))
    res["OH_by_sbp"] = int(drop_s >= OH_SBP_DROP)
    res["OH_by_dbp"] = int(drop_d >= OH_DBP_DROP)
    res["OT"] = int(rise_h >= OT_HR_RISE)
    res["status"] = "OK"
    return res


# ------------------------------------------------------------------- driver
def main():
    h1, tab1 = load_marker_table(f"{ROOT}/Data_Description/GE-71_Head-up-tilt-Day1_Markers_per_subject.csv")
    h2, tab2 = load_marker_table(f"{ROOT}/Data_Description/GE-71_Head-up-tilt-Day2_Markers_per_subject.csv")

    TILT1, END1 = h1.index("Tilt "), h1.index("Tilt ") + 1
    TILT2, END2 = 15, 16       # normocapnic tilt on day 2, before the hypocapnic one

    jobs = []
    for day, tab, ti, ei, folder in [(1, tab1, TILT1, END1, "Head-up-tilt_Day1"),
                                     (2, tab2, TILT2, END2, "Head-up-tilt_Day2")]:
        for f in sorted(glob.glob(f"{ROOT}/Data/Labview/Converted/{folder}/*.dat")):
            base = f[:-4]
            sid = "S" + os.path.basename(base)[1:5]
            row = tab.get(sid)
            if row is None:
                jobs.append((base, sid, day, 0, 0, 0)); continue
            ints = [int(x) for x in row[2:] if x.strip().isdigit()]
            g = lambda i: (int(row[i].strip())
                           if row[i].strip().isdigit() and int(row[i].strip()) > 0 else 0)
            jobs.append((base, sid, day, g(ti), g(ei), max(ints or [0])))

    rows = []
    for base, sid, day, ti, ei, mx in jobs:
        try:
            rows.append(process(base, sid, day, ti, ei, mx))
        except Exception as e:
            rows.append({"subject": sid, "day": day,
                         "record": os.path.basename(base),
                         "status": f"ERROR_{type(e).__name__}_{e}"})

    os.makedirs(OUT, exist_ok=True)
    json.dump(rows, open(f"{OUT}/tilt_labels.json", "w"), indent=1)
    keys = sorted({k for r in rows for k in r})
    with open(f"{OUT}/tilt_labels.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)

    ok = [r for r in rows if r["status"] == "OK"]
    from collections import Counter
    print("=" * 64)
    print("AMENDMENT 1 IN FORCE: fs=500 Hz (header says 1000), "
          f"first {INITIAL_SKIP}s of tilt excluded")
    print("=" * 64)
    print(f"records processed : {len(rows)}")
    print(f"usable            : {len(ok)}")
    print(f"excluded          : {len(rows)-len(ok)}")
    for k, v in Counter(r["status"] for r in rows if r["status"] != "OK").most_common():
        print(f"    {v:3d}  {k}")
    if not ok:
        return
    n = len(ok); pos = sum(r["OH"] for r in ok)
    subs = len({r["subject"] for r in ok})
    print(f"\nsubjects          : {subs}")
    print(f"mean HR, median   : {np.median([r['mean_hr_record'] for r in ok]):.0f} bpm "
          f"(range {min(r['mean_hr_record'] for r in ok):.0f}"
          f" to {max(r['mean_hr_record'] for r in ok):.0f})")
    print(f"tilt window median: {np.median([r['tilt_window_s'] for r in ok]):.0f} s"
          f"   truncated <180s: {sum(r['tilt_truncated'] for r in ok)}")
    print(f"\nOH positive       : {pos} of {n}  ({100*pos/n:.1f} %)")
    print(f"  by SBP          : {sum(r['OH_by_sbp'] for r in ok)}")
    print(f"  by DBP          : {sum(r['OH_by_dbp'] for r in ok)}")
    print(f"OT positive       : {sum(r['OT'] for r in ok)}")
    print(f"majority-class floor: {100*max(pos, n-pos)/n:.1f} %")
    for d in (1, 2):
        s = [r for r in ok if r["day"] == d]
        if s:
            print(f"  day {d}: n={len(s):3d}  OH={sum(x['OH'] for x in s):3d} "
                  f"({100*sum(x['OH'] for x in s)/len(s):.0f} %)")
    print(f"\nFALSIFICATION CHECK: plan requires >= 15 positives -> "
          f"{'PASS' if pos >= 15 else 'FAIL, no modelling'}")


if __name__ == "__main__":
    main()
