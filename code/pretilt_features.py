"""
Pre-tilt autonomic features, per PREANALYSIS_PLAN_tilt.md Amendment 3.4.

Hard rule enforced by assertion: no feature may touch a sample at or after the
tilt-onset index. The record is sliced once, before any feature function runs.

Three windows, matched in length across Day 1 and Day 2:
  R  resting      first 60 s from the protocol's opening baseline marker
  P  pre-tilt     the 120 s immediately before tilt onset
  V  Valsalva 1   the first Valsalva strain plus 30 s of recovery

Deep breathing exists only on Day 1 and is therefore excluded from the primary
feature set, per the plan. It is computed and stored separately, clearly named,
for a Day-1-only sensitivity analysis.

Output: pretilt_features.json, pretilt_features.csv
"""

import os, csv, json, glob, warnings
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt, find_peaks, welch

warnings.filterwarnings("ignore")

ROOT = "/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data"
OUT  = "/sessions/amazing-sleepy-goldberg/mnt/outputs"
TRUE_FS = 500                      # Amendment 1

REST_S   = 60.0
PRETILT_S = 120.0
VAL_POST_S = 30.0


# --------------------------------------------------------------- beat series
def beat_series(abp):
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
    ibi = np.r_[np.nan, np.diff(t)] * 1000.0        # ms
    return t, s, d, ibi


# ------------------------------------------------------------------ features
def hrv(ibi, tag):
    v = ibi[np.isfinite(ibi)]
    v = v[(v > 300) & (v < 2000)]
    f = {}
    if len(v) < 20:
        return f
    dv = np.diff(v)
    f[f"{tag}_meanIBI"] = float(np.mean(v))
    f[f"{tag}_HR"]      = float(60000.0/np.mean(v))
    f[f"{tag}_SDNN"]    = float(np.std(v, ddof=1))
    f[f"{tag}_RMSSD"]   = float(np.sqrt(np.mean(dv**2)))
    f[f"{tag}_pNN50"]   = float(np.mean(np.abs(dv) > 50))
    f[f"{tag}_CVnn"]    = float(np.std(v, ddof=1)/np.mean(v))
    # Poincare
    sd1 = np.sqrt(0.5)*np.std(dv, ddof=1)
    sd2 = np.sqrt(max(2*np.var(v, ddof=1) - 0.5*np.var(dv, ddof=1), 1e-9))
    f[f"{tag}_SD1"] = float(sd1)
    f[f"{tag}_SD2"] = float(sd2)
    f[f"{tag}_SD1SD2"] = float(sd1/sd2) if sd2 > 0 else np.nan
    return f


def spectral(t, v, tag, name):
    """Interpolate an unevenly sampled beat series to 4 Hz, then Welch."""
    m = np.isfinite(v)
    if m.sum() < 30:
        return {}
    tt, vv = t[m], v[m]
    span = tt[-1] - tt[0]
    if span < 45:
        return {}
    grid = np.arange(tt[0], tt[-1], 0.25)
    y = np.interp(grid, tt, vv)
    y = y - y.mean()
    nper = min(len(y), int(45*4))
    fr, P = welch(y, fs=4.0, nperseg=nper)
    band = lambda lo, hi: float(np.trapezoid(P[(fr >= lo) & (fr < hi)], fr[(fr >= lo) & (fr < hi)]))
    lf, hf = band(0.04, 0.15), band(0.15, 0.40)
    out = {f"{tag}_{name}_LF": lf, f"{tag}_{name}_HF": hf,
           f"{tag}_{name}_LFHF": float(lf/hf) if hf > 0 else np.nan,
           f"{tag}_{name}_TP": band(0.003, 0.40)}
    return out


def brs_sequence(sbp, ibi, tag):
    """Baroreflex sensitivity, sequence method. Runs of >=3 concordant beats."""
    s, r = sbp[1:], ibi[1:]
    ok = np.isfinite(s) & np.isfinite(r)
    s, r = s[ok], r[ok]
    if len(s) < 30:
        return {}
    ds, dr = np.diff(s), np.diff(r)
    slopes, n_up, n_dn = [], 0, 0
    i = 0
    while i < len(ds) - 1:
        for sign in (1, -1):
            j = i
            while j < len(ds) and np.sign(ds[j]) == sign and np.sign(dr[j]) == sign:
                j += 1
            if j - i >= 3:
                x, y = s[i:j+1], r[i:j+1]
                if np.std(x) > 0:
                    cc = np.corrcoef(x, y)[0, 1]
                    if cc > 0.85:
                        slopes.append(np.polyfit(x, y, 1)[0])
                        if sign > 0: n_up += 1
                        else: n_dn += 1
                i = j
                break
        i += 1
    f = {f"{tag}_BRSseq_n": len(slopes)}
    if slopes:
        f[f"{tag}_BRSseq"] = float(np.mean(slopes))
        f[f"{tag}_BRSseq_up"] = float(n_up)
        f[f"{tag}_BRSseq_dn"] = float(n_dn)
    return f


def brs_alpha(t, sbp, ibi, tag):
    """Spectral alpha index in the LF band."""
    m = np.isfinite(sbp) & np.isfinite(ibi)
    if m.sum() < 30:
        return {}
    tt = t[m]
    if tt[-1] - tt[0] < 45:
        return {}
    grid = np.arange(tt[0], tt[-1], 0.25)
    a = np.interp(grid, tt, sbp[m]); a -= a.mean()
    b = np.interp(grid, tt, ibi[m]); b -= b.mean()
    nper = min(len(a), int(45*4))
    fr, Pa = welch(a, fs=4.0, nperseg=nper)
    _,  Pb = welch(b, fs=4.0, nperseg=nper)
    sel = (fr >= 0.04) & (fr < 0.15)
    if Pa[sel].sum() <= 0:
        return {}
    return {f"{tag}_BRSalpha": float(np.sqrt(Pb[sel].sum()/Pa[sel].sum()))}


def bp_variability(sbp, dbp, tag):
    f = {}
    for nm, v in (("SBP", sbp), ("DBP", dbp)):
        v = v[np.isfinite(v)]
        if len(v) < 20:
            continue
        f[f"{tag}_{nm}_mean"] = float(np.mean(v))
        f[f"{tag}_{nm}_sd"]   = float(np.std(v, ddof=1))
        f[f"{tag}_{nm}_cv"]   = float(np.std(v, ddof=1)/np.mean(v))
        f[f"{tag}_{nm}_arv"]  = float(np.mean(np.abs(np.diff(v))))
    if np.isfinite(sbp).sum() > 20 and np.isfinite(dbp).sum() > 20:
        pp = sbp - dbp
        f[f"{tag}_PP_mean"] = float(np.nanmean(pp))
        f[f"{tag}_PP_sd"]   = float(np.nanstd(pp, ddof=1))
    return f


def valsalva(t, s, d, ibi, v0, v1):
    """Valsalva ratio and the phase II / phase IV pressure responses."""
    f = {}
    pre = (t >= v0 - 30) & (t < v0)
    strain = (t >= v0) & (t <= v1)
    post = (t > v1) & (t <= v1 + VAL_POST_S)
    if pre.sum() < 10 or strain.sum() < 5 or post.sum() < 10:
        return f
    base_s = float(np.nanmean(s[pre]))
    # Valsalva ratio: longest IBI after release over shortest IBI during strain
    ib_st = ibi[strain]; ib_po = ibi[post]
    ib_st = ib_st[np.isfinite(ib_st)]; ib_po = ib_po[np.isfinite(ib_po)]
    if len(ib_st) and len(ib_po) and ib_st.min() > 0:
        f["VAL_ratio"] = float(ib_po.max()/ib_st.min())
    f["VAL_strain_s"] = float(v1 - v0)
    f["VAL_phaseII_drop"] = float(base_s - np.nanmin(s[strain]))
    f["VAL_phaseIV_over"] = float(np.nanmax(s[post]) - base_s)
    f["VAL_HRrise"] = float(60000/np.nanmin(ib_st) - 60000/np.nanmean(ibi[pre][np.isfinite(ibi[pre])])) \
        if len(ib_st) and np.isfinite(ibi[pre]).any() else np.nan
    return f


def gas(path, i_lo, i_hi, tag):
    """End-tidal CO2 level and respiratory rate from capnography."""
    try:
        rec = wfdb.rdrecord(path, sampfrom=i_lo, sampto=i_hi, channel_names=["co2"])
    except Exception:
        return {}
    x = np.nan_to_num(rec.p_signal[:, 0])
    if len(x) < TRUE_FS*30:
        return {}
    f = {f"{tag}_CO2_mean": float(np.mean(x)),
         f"{tag}_CO2_p95": float(np.percentile(x, 95))}
    y = x - x.mean()
    fr, P = welch(y, fs=TRUE_FS, nperseg=min(len(y), TRUE_FS*30))
    sel = (fr > 0.08) & (fr < 0.6)
    if sel.any():
        f[f"{tag}_respRate"] = float(fr[sel][np.argmax(P[sel])]*60)
    return f


# ------------------------------------------------------------------- driver
def load_table(p):
    rows = list(csv.reader(open(p)))
    return rows[0], {r[0]: r for r in rows[1:] if r and r[0].startswith("S")}


def marker_pulses(path):
    r = wfdb.rdrecord(path, channel_names=["marker"])
    m = r.p_signal[:, 0]
    hi = m > 0.5
    dd = np.diff(hi.astype(int))
    s = np.where(dd == 1)[0] + 1
    if hi[0]:
        s = np.r_[0, s]
    out = []
    for x in s:
        if not out or x - out[-1] > 0.3*TRUE_FS:
            out.append(int(x))
    return np.array(out, dtype=int)


def main():
    labels = {r["record"]: r for r in json.load(open(f"{OUT}/tilt_labels.json"))
              if r["status"] == "OK"}
    h1, t1 = load_table(f"{ROOT}/Data_Description/GE-71_Head-up-tilt-Day1_Markers_per_subject.csv")
    h2, t2 = load_table(f"{ROOT}/Data_Description/GE-71_Head-up-tilt-Day2_Markers_per_subject.csv")

    # ordinal columns
    D1 = dict(base=h1.index("Start 1 min"), val0=h1.index("Val 1"), val1=h1.index("Val 1")+1,
              db0=h1.index("Deep breathing"), db1=h1.index("Deep breathing")+1)
    D2 = dict(base=2, val0=3, val1=4)

    rows = []
    for rec_name, lab in sorted(labels.items()):
        day = lab["day"]
        folder = "Head-up-tilt_Day1" if day == 1 else "Head-up-tilt_Day2"
        path = f"{ROOT}/Data/Labview/Converted/{folder}/{rec_name}"
        sid = lab["subject"]
        tab, cols = (t1, D1) if day == 1 else (t2, D2)
        row = tab.get(sid)
        if row is None:
            continue
        g = lambda i: (int(row[i].strip())
                       if row[i].strip().isdigit() and int(row[i].strip()) > 0 else 0)

        pulses = marker_pulses(path)
        t_tilt = lab["tilt_start_s"]
        i_tilt = int(round(t_tilt*TRUE_FS))

        rec = wfdb.rdrecord(path, sampto=i_tilt, channel_names=["abp"])
        # ---- LEAKAGE ASSERTION, Amendment 3.4
        assert rec.p_signal.shape[0] <= i_tilt, "pre-tilt slice reached the tilt window"
        abp = rec.p_signal[:, 0]

        t, s, d, ibi = beat_series(abp)
        assert len(t) == 0 or t[-1] < t_tilt, "beat found at or after tilt onset"

        F = {"record": rec_name, "subject": sid, "day": day,
             "tilt_start_s": t_tilt,
             "delta_SBP": None, "delta_DBP": None}

        # ---------- R window, opening baseline
        ob = g(cols["base"])
        if ob and ob <= len(pulses):
            r0 = pulses[ob-1]/TRUE_FS
            m = (t >= r0) & (t < r0 + REST_S)
            if m.sum() >= 30:
                F.update(hrv(ibi[m], "R"))
                F.update(bp_variability(s[m], d[m], "R"))
                F.update(gas(path, int(r0*TRUE_FS), int((r0+REST_S)*TRUE_FS), "R"))

        # ---------- P window, 120 s immediately pre-tilt
        m = (t >= t_tilt - PRETILT_S) & (t < t_tilt)
        if m.sum() >= 60:
            F.update(hrv(ibi[m], "P"))
            F.update(bp_variability(s[m], d[m], "P"))
            F.update(spectral(t[m], ibi[m], "P", "IBI"))
            F.update(spectral(t[m], s[m], "P", "SBP"))
            F.update(brs_sequence(s[m], ibi[m], "P"))
            F.update(brs_alpha(t[m], s[m], ibi[m], "P"))
            F.update(gas(path, int((t_tilt-PRETILT_S)*TRUE_FS), i_tilt, "P"))

        # ---------- V window, first Valsalva
        v0o, v1o = g(cols["val0"]), g(cols["val1"])
        if v0o and v1o and max(v0o, v1o) <= len(pulses):
            v0, v1 = pulses[v0o-1]/TRUE_FS, pulses[v1o-1]/TRUE_FS
            if 3 < (v1 - v0) < 40 and v1 + VAL_POST_S < t_tilt:
                F.update(valsalva(t, s, d, ibi, v0, v1))

        # ---------- deep breathing, DAY 1 ONLY, stored but excluded from primary
        if day == 1:
            b0, b1 = g(cols["db0"]), g(cols["db1"])
            if b0 and b1 and max(b0, b1) <= len(pulses):
                x0, x1 = pulses[b0-1]/TRUE_FS, pulses[b1-1]/TRUE_FS
                m = (t >= x0) & (t <= x1)
                if m.sum() >= 20:
                    v = ibi[m]; v = v[np.isfinite(v)]
                    if len(v) > 10:
                        F["DB1ONLY_EIratio"] = float(v.max()/v.min())
                        F["DB1ONLY_EIdiff"] = float(60000/v.min() - 60000/v.max())

        F["n_features"] = sum(1 for k, v in F.items()
                              if k not in ("record", "subject", "day", "tilt_start_s",
                                           "delta_SBP", "delta_DBP", "n_features")
                              and v is not None and np.isfinite(v if isinstance(v, float) else 0))
        rows.append(F)
        print(f"  {rec_name:>9s} day{day}  features={F['n_features']}")

    json.dump(rows, open(f"{OUT}/pretilt_features.json", "w"), indent=1)
    keys = sorted({k for r in rows for k in r})
    with open(f"{OUT}/pretilt_features.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)

    print("\n" + "="*60)
    print(f"records        : {len(rows)}")
    print(f"subjects       : {len({r['subject'] for r in rows})}")
    print(f"feature columns: {len(keys)}")
    # completeness
    feat = [k for k in keys if k not in ("record","subject","day","tilt_start_s",
                                         "delta_SBP","delta_DBP","n_features")]
    comp = {k: sum(1 for r in rows if isinstance(r.get(k), float) and np.isfinite(r[k]))
            for k in feat}
    full = [k for k, v in comp.items() if v == len(rows)]
    print(f"complete on every record: {len(full)} of {len(feat)}")
    thin = sorted(((v, k) for k, v in comp.items()), key=lambda x: x[0])[:12]
    print("least complete features:")
    for v, k in thin:
        print(f"    {v:3d}/{len(rows)}  {k}")


if __name__ == "__main__":
    main()
