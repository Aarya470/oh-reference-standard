"""
The pre-registered analysis, PREANALYSIS_PLAN_tilt.md Amendment 3.3 and 3.6.

Primary   : out-of-fold Spearman rho, predicted vs observed delta_SBP
Null      : 1000 subject-level permutations, rho must exceed the 97.5th pct
Floor     : age, sex, supine baseline SBP only; waveform model must beat it
Also      : MAE vs predicting the cohort mean, cluster-bootstrap CIs
Confounds : day, pre-tilt duration, baseline pressure, diabetes, repeat subjects

Nothing is tuned after seeing the result. Falsification conditions are in 3.7.
"""
import json, csv, warnings, numpy as np
warnings.filterwarnings("ignore")
from scipy import stats
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, roc_auc_score

ROOT = "/sessions/amazing-sleepy-goldberg/mnt/dysautonomia_data"
OUT  = "/sessions/amazing-sleepy-goldberg/mnt/outputs"
SEEDS = [0, 1, 2, 3, 4]
NPERM = 1000
MIN_COMPLETE = 0.90        # keep features present on >=90% of records

META = {"record", "subject", "day", "tilt_start_s", "delta_SBP", "delta_DBP",
        "n_features", "at_timepoint", "baseline_SBP", "baseline_DBP",
        "delta_SBP_pct", "timepoints_available"}


# --------------------------------------------------------------- clinical
def parse_csv(text):
    out, f, row, q = [], "", [], False
    for i, c in enumerate(text):
        if q:
            if c == '"':
                if i+1 < len(text) and text[i+1] == '"': f += '"'
                else: q = False
            else: f += c
        else:
            if c == '"': q = True
            elif c == ',': row.append(f); f = ""
            elif c == '\n': row.append(f); out.append(row); row = []; f = ""
            elif c != '\r': f += c
    if f or row: row.append(f); out.append(row)
    return out


def load_clinical():
    T = parse_csv(open(f"{ROOT}/Data_Description/GE-71_Data_Summary_Table.csv").read())
    H = T[0]
    gi, ai, si = H.index("Group"), H.index("Age"), H.index("Gender")
    out = {}
    for r in T[1:]:
        if not r or not r[0].startswith("S"):
            continue
        try: age = float(r[ai])
        except Exception: age = np.nan
        out[r[0]] = dict(age=age,
                         sex=1.0 if r[si].strip().upper().startswith("F") else 0.0,
                         group=r[gi].strip())
    return out


# ------------------------------------------------------------ evaluation
def oof_predict(X, y, groups, model_fn, seed):
    """Out-of-fold predictions, folds grouped by subject."""
    pred = np.full(len(y), np.nan)
    n_groups = len(np.unique(groups))
    k = min(5, n_groups)
    # shuffle group order deterministically per seed
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    perm = rng.permutation(len(uniq))
    remap = {g: perm[i] for i, g in enumerate(uniq)}
    gshuf = np.array([remap[g] for g in groups])
    for tr, te in GroupKFold(n_splits=k).split(X, y, gshuf):
        m = model_fn()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred


def cluster_bootstrap_rho(y, p, groups, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in uniq}
    out = []
    for _ in range(n):
        pick = rng.choice(uniq, len(uniq), replace=True)
        sel = np.concatenate([idx[g] for g in pick])
        if len(np.unique(y[sel])) < 3:
            continue
        out.append(stats.spearmanr(y[sel], p[sel]).statistic)
    out = np.array([o for o in out if np.isfinite(o)])
    return np.percentile(out, [2.5, 97.5])


def ridge():
    return Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("sc", StandardScaler()),
                     ("m", RidgeCV(alphas=np.logspace(-2, 4, 40)))])


def gbt():
    return Pipeline([("m", HistGradientBoostingRegressor(
        max_depth=3, max_iter=250, learning_rate=0.05,
        min_samples_leaf=8, l2_regularization=1.0, random_state=0))])


# ------------------------------------------------------------------- main
def main():
    rows = [r for r in json.load(open(f"{OUT}/pretilt_features.json"))
            if r.get("delta_SBP") is not None]
    clin = load_clinical()

    feat_names = sorted({k for r in rows for k in r
                         if k not in META and not k.startswith("DB1ONLY")})
    keep = []
    for k in feat_names:
        v = [r.get(k) for r in rows]
        ok = sum(1 for x in v if isinstance(x, (int, float)) and np.isfinite(x))
        if ok >= MIN_COMPLETE*len(rows):
            keep.append(k)

    X = np.array([[float(r.get(k)) if isinstance(r.get(k), (int, float))
                   and np.isfinite(r.get(k)) else np.nan for k in keep] for r in rows])
    y = np.array([r["delta_SBP"] for r in rows], float)
    groups = np.array([r["subject"] for r in rows])
    day = np.array([r["day"] for r in rows], float)
    base_sbp = np.array([r["baseline_SBP"] for r in rows], float)
    age = np.array([clin.get(s, {}).get("age", np.nan) for s in groups], float)
    sex = np.array([clin.get(s, {}).get("sex", np.nan) for s in groups], float)
    grp = np.array([clin.get(s, {}).get("group", "?") for s in groups])

    print("="*66)
    print("PRE-REGISTERED ANALYSIS, Amendment 3.3")
    print("="*66)
    print(f"records {len(rows)}   subjects {len(np.unique(groups))}   "
          f"features {len(keep)} of {len(feat_names)} kept at >={int(MIN_COMPLETE*100)}% complete")
    print(f"outcome delta_SBP: mean {y.mean():.2f}  sd {y.std(ddof=1):.2f} mmHg")
    print(f"clinical data available for {int(np.isfinite(age).sum())} of {len(rows)} records\n")

    # ------------------------------------------------ primary and floor
    results = {}
    for name, fn, mat in [("waveform ridge", ridge, X),
                          ("waveform GBT",   gbt,   X),
                          ("FLOOR age+sex+baselineSBP", ridge,
                           np.c_[age, sex, base_sbp])]:
        rhos, maes, preds = [], [], []
        for sd in SEEDS:
            p = oof_predict(mat, y, groups, fn, sd)
            m = np.isfinite(p)
            rhos.append(stats.spearmanr(y[m], p[m]).statistic)
            maes.append(mean_absolute_error(y[m], p[m]))
            preds.append(p)
        pm = np.nanmean(np.array(preds), axis=0)
        lo, hi = cluster_bootstrap_rho(y, pm, groups)
        results[name] = dict(rho=float(np.mean(rhos)), rho_sd=float(np.std(rhos)),
                             mae=float(np.mean(maes)), ci=(float(lo), float(hi)),
                             pred=pm)
        print(f"  {name:<28s} rho {np.mean(rhos):+.3f} (sd {np.std(rhos):.3f}) "
              f"95% CI [{lo:+.3f}, {hi:+.3f}]   MAE {np.mean(maes):5.2f} mmHg")

    mae_mean = mean_absolute_error(y, np.full_like(y, y.mean()))
    print(f"  {'BASELINE predict the mean':<28s} {'':21s}"
          f"                MAE {mae_mean:5.2f} mmHg")

    # ------------------------------------------------ permutation null
    best = max(("waveform ridge", "waveform GBT"), key=lambda k: results[k]["rho"])
    fn = ridge if best == "waveform ridge" else gbt
    print(f"\n  permutation null on the better waveform model ({best}), "
          f"{NPERM} subject-level permutations ...")
    rng = np.random.default_rng(12345)
    uniq = np.unique(groups)
    sub_of = {g: np.where(groups == g)[0] for g in uniq}
    null = []
    for i in range(NPERM):
        order = rng.permutation(len(uniq))
        yp = y.copy()
        for a, b in zip(uniq, uniq[order]):
            # swap whole subject blocks, keeping within-subject structure
            ia, ib = sub_of[a], sub_of[b]
            n = min(len(ia), len(ib))
            yp[ia[:n]] = y[ib[:n]]
        p = oof_predict(X, yp, groups, fn, 0)
        m = np.isfinite(p)
        null.append(stats.spearmanr(yp[m], p[m]).statistic)
    null = np.array([v for v in null if np.isfinite(v)])
    thr = np.percentile(null, 97.5)
    obs = results[best]["rho"]
    pval = float((null >= obs).mean())
    print(f"    null rho: mean {null.mean():+.3f}  97.5th pct {thr:+.3f}")
    print(f"    observed : {obs:+.3f}   permutation p = {pval:.4f}")

    # ------------------------------------------------ confound checks
    print("\n  CONFOUND CHECKS, Amendment 3.6")
    p_day = oof_predict(X, day, groups, gbt, 0)
    m = np.isfinite(p_day)
    auc_day = roc_auc_score((day[m] == 2).astype(int), p_day[m])
    print(f"    10 recording day: AUROC predicting day from features = {auc_day:.3f}"
          f"   {'FAIL >0.70' if auc_day > 0.70 else 'ok'}")

    pre_dur = np.array([r["tilt_start_s"] for r in rows], float)
    r_dur = stats.spearmanr(pre_dur, y)
    print(f"    11 pre-tilt duration vs outcome: rho {r_dur.statistic:+.3f}"
          f" p={r_dur.pvalue:.3f}")

    r_base = stats.spearmanr(base_sbp, y)
    print(f"    12 baseline SBP vs outcome     : rho {r_base.statistic:+.3f}"
          f" p={r_base.pvalue:.3f}")
    ypct = np.array([r["delta_SBP_pct"] for r in rows], float)
    p_pct = oof_predict(X, ypct, groups, fn, 0)
    mm = np.isfinite(p_pct)
    print(f"       relative fall (% of baseline) as outcome: rho "
          f"{stats.spearmanr(ypct[mm], p_pct[mm]).statistic:+.3f}")

    print("    13 by clinical group:")
    pm = results[best]["pred"]
    for g in ["Control", "DM", "DMOH"]:
        sel = (grp == g) & np.isfinite(pm)
        if sel.sum() >= 8:
            print(f"       {g:<8s} n={sel.sum():3d}  rho "
                  f"{stats.spearmanr(y[sel], pm[sel]).statistic:+.3f}")
    dm = np.isin(grp, ["DM", "DMOH"]) & np.isfinite(pm)
    ct = (grp == "Control") & np.isfinite(pm)
    if dm.sum() >= 8 and ct.sum() >= 8:
        print(f"       diabetic  n={dm.sum():3d}  rho {stats.spearmanr(y[dm], pm[dm]).statistic:+.3f}")
        print(f"       control   n={ct.sum():3d}  rho {stats.spearmanr(y[ct], pm[ct]).statistic:+.3f}")

    n_rep = sum(1 for g in uniq if (groups == g).sum() > 1)
    print(f"    14 subjects contributing two records: {n_rep} "
          f"(all CIs are cluster bootstrapped over subjects)")

    # ------------------------------------------------ verdict
    print("\n" + "="*66)
    print("FALSIFICATION CONDITIONS, Amendment 3.7")
    print("="*66)
    c1 = obs <= thr
    c2 = results[best]["rho"] <= results["FLOOR age+sex+baselineSBP"]["rho"]
    c3 = results[best]["mae"] >= mae_mean
    c4 = auc_day > 0.70
    for lab, fired in [("rho does not exceed the permutation null", c1),
                       ("waveform model does not beat the age/sex/baseline floor", c2),
                       ("MAE not better than predicting the mean", c3),
                       ("day is predictable from the features, AUROC > 0.70", c4)]:
        print(f"  [{'X FIRED' if fired else '  ok   '}] {lab}")
    verdict = "NEGATIVE" if (c1 or c2 or c3 or c4) else "POSITIVE"
    print(f"\n  C4 VERDICT: {verdict}")
    print("  C1 to C3 stand regardless, they rest on measurements already made.")

    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "pred"}
               for k, v in results.items()} |
              {"permutation": {"null_mean": float(null.mean()),
                               "null_97_5": float(thr), "observed": float(obs),
                               "p": pval},
               "confounds": {"auc_day": float(auc_day),
                             "rho_duration": float(r_dur.statistic),
                             "rho_baseline": float(r_base.statistic)},
               "mae_predict_mean": float(mae_mean),
               "verdict": verdict},
              open(f"{OUT}/regression_results.json", "w"), indent=1)


if __name__ == "__main__":
    main()
