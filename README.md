# Reference-standard instability in orthostatic hypotension

Code, derived data and pre-analysis plan for the study
**"What Are We Predicting? Reference-Standard Instability in Machine Learning
for Orthostatic Hypotension."**

The short version: the orthostatic hypotension label that machine learning
studies are trained and scored against is not a single quantity. Reading the
same continuous blood pressure recordings three defensible ways moves prevalence
roughly four-fold, and the reading that agrees with the clinical reference
depends on how that reference was recorded.

## What is here

```
plan/      the pre-analysis plan, released unedited, with every dated amendment
code/      every analysis script, in the order they run
derived/   per-recording labels, features, model output, permutation nulls
download/  scripts that fetch the two public datasets from PhysioNet
```

No raw waveforms are redistributed. Both source datasets are open access on
PhysioNet and should be obtained from there.

## Data

| Cohort | Dataset | DOI | Records used |
|---|---|---|---|
| 1 | Cerebral Vasoregulation in Diabetes v1.0.0 | 10.13026/m40k-4758 | 71 of 110 available |
| 2 | Cerebral Vasoregulation in Elderly with Stroke v1.0.0 | 10.13026/C2DW96 | 54 of 68 |

Run `download/download_tilt_data.ps1` and `download/download_cves.ps1` to fetch
only the head-up tilt recordings, about 1.7 GB and 1.5 GB, rather than the full
archives.

## Two defects in the published data

Both have been reported to the dataset maintainers. Anyone reusing these
resources should apply the corrections below.

**1. Cohort 1 declares the wrong sampling rate.** Every header says 1000 Hz.
The true rate is 500 Hz. Eight independent confirmations are in the manuscript
and in `plan/PREANALYSIS_PLAN_tilt.md`, Amendment 1. The most direct: the
protocol paces deep breathing at 0.1 Hz, and at the declared rate the measured
frequency is 0.200 Hz in 13 of 14 records, a ratio of exactly 2.00. The most
conclusive: the laboratory's own protocol, distributed with cohort 2, states
that all analog signals were recorded at 500 Hz on the Labview NIDAQ system.

Uncorrected, every frequency-domain HRV measure is displaced by one octave,
baroreflex sensitivity in ms/mmHg is wrong by a factor of two, and the
three-minute window the consensus definition requires is in fact 90 seconds.

Set `TRUE_FS = 500` and ignore the header. See `code/tilt_labels.py`.

**2. Cohort 2's index file double-lists the tilt folder.** `RECORDS` contains
136 lines for 68 head-up tilt files, every record listed exactly twice. The
dataset's five other data folders are each listed once. Any pipeline that
iterates `RECORDS` will process every tilt recording twice and report double the
true sample size. Deduplicate before use.

## Running the analysis

Requires Python 3 with numpy, scipy, pandas, scikit-learn and wfdb.

```bash
python code/tilt_labels.py        # cohort 1 segmentation and labels
python code/outcomes.py           # cohort 1 continuous outcome
python code/pretilt_features.py   # cohort 1 features, pre-tilt signal only
python code/cves_labels.py        # cohort 2 segmentation and labels
python code/cves_features.py      # cohort 2 features
python code/observed.py           # single-cohort regression
python code/pooled_observed.py    # pooled two-cohort regression
python code/null_chunk.py 0 1000 ridge   # permutation null
python code/finalize.py           # verdict against the pre-declared conditions
```

Feature extraction asserts at runtime that no sample at or after tilt onset
enters any feature. The assertion halts the run rather than warning.

## Headline numbers

Prevalence of orthostatic hypotension, same recordings, three readings:

| Reading | Cohort 1 | Cohort 2 |
|---|---|---|
| minimum across the tilt | 38.0 % | 46.3 % |
| clinical timepoints, 1 and 3 min | 9.9 % | 18.5 % |
| mean of the final 60 s | 8.0 % | 11.1 % |

Day-to-day agreement in 20 participants recorded twice: kappa 0.608 under the
clinical-timepoint reading, 0.200 under the minimum reading, on identical data.
ICC(2,1) of the continuous fall is 0.586, with a within-subject standard
deviation of 12.6 mmHg against a 20 mmHg diagnostic threshold.

The pre-registered prediction study is **negative**. Pooled across cohorts it
gave Spearman rho 0.250, p = 0.003, CI 0.111 to 0.421, which is an artifact: a
model predicting cohort membership from the same features reaches AUROC 0.788,
model error exceeds that of predicting the cohort mean in every configuration,
and the effect vanishes within cohort 2 (rho -0.015).

## On the pre-analysis plan

`plan/PREANALYSIS_PLAN_tilt.md` is released unedited. It records four dated
amendments, including two that document our own errors:

- **Amendment 1** the sampling-rate correction.
- **Amendment 2** our original primary reading was biased, inflating the
  systolic fall by 17.2 mmHg against a 20 mmHg threshold. It also records a
  withdrawn finding: a day-to-day kappa of 0.200 that looked like evidence the
  tilt reference standard barely reproduces, and was instead a property of our
  own statistic.
- **Amendment 3** re-scope after a pre-declared falsification condition fired.
- **Amendment 4** the second cohort, declared before any of its data was read.

The amendments are the point. They are what the agreement checks caught.

## Exclusions

`derived/EXCLUSIONS.csv` lists all 53 excluded recordings by name with the
reason for each: 39 in cohort 1, 14 in cohort 2. No recording was recovered by
inference. A physiological tilt-onset detector was built, failed its
pre-declared accuracy gate, and was discarded; the code is kept in
`code/tilt_onset.py` and its failure mode is described in Amendment 3.5.

## License

Code released under the MIT License. Derived data released under CC BY 4.0.
The source datasets carry their own licenses on PhysioNet and are not
redistributed here.

## Citation

Roy A. What Are We Predicting? Reference-Standard Instability in Machine
Learning for Orthostatic Hypotension. Manuscript in preparation, 2026.
