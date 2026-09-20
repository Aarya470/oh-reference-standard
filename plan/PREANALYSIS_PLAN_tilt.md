# Pre-analysis plan
## Pre-tilt prediction of orthostatic hypotension, and its day-to-day reproducibility

**Written before any label was computed and before any model was fitted.**
Date written: 2026-09-15. Author: Aaryan Roy.

Everything below is fixed in advance. Any departure from this document must be
recorded in a dated amendment section at the bottom, stating what changed and why.
Results obtained after an unrecorded change are to be reported as exploratory.

---

## 1. Why this study exists

Kim et al. (J Clin Neurol 2020;16:448-454) proposed screening for orthostatic
hypotension without a tilt table, using five scalar autonomic-test numbers, and
reported 90.6 percent accuracy with a random forest.

Their cohort was 78 OH cases in 663 patients. A classifier that always answers
"no OH" scores 88.2 percent on that cohort. The reported figure exceeds the
majority-class floor by 2.4 points. Accuracy was the reported metric and the
cohort was imbalanced, so the size of the real effect is not recoverable from
the paper.

This study does three things that the prior work did not.

1. Evaluates pre-tilt OH screening with metrics that survive class imbalance,
   and prints the majority-class floor next to every number.
2. Uses the full pre-tilt waveform rather than five hand-chosen scalars, and
   tests whether the waveform carries information the scalars do not.
3. Measures whether a pre-tilt screening prediction is stable when the same
   person is recorded on two different days. No prior study has done this.
   The clinical premise of "screen instead of tilt" requires the screen to be
   reproducible. That has never been tested.

Item 3 is the primary contribution. A negative answer is a publishable result
and will be reported as such.

---

## 2. Data

PhysioNet, Cerebral Vasoregulation in Diabetes, v1.0.0
(Novak V, Mendez L, 2020). DOI 10.13026/m40k-4758. CC-BY 4.0, open access,
fully de-identified, no IRB required and none sought.

Only the head-up tilt recordings are used: 59 Day 1 records and 57 Day 2
records, 116 total, across approximately 86 subjects.

Channels are not identical between days. Day 1 records carry 7 channels
(marker, ecg, abp, thermst, flow_rate, o2, co2). A subset of records carries
10 channels, adding transcranial Doppler (mcar, mcal) and Radi. **Only the
7 channels common to every record may be used as model input.** Transcranial
Doppler channels are excluded from all modelling, because their availability
is confounded with recording day.

All signals are 1000 Hz, format 16.

---

## 3. Segmentation

Each record contains a `marker` channel carrying short square pulses. Pulse
ordinals map to protocol events via the two per-subject marker tables in
`Data_Description/`, which specify, for each subject, which ordinal corresponds
to: start of 1-minute baseline, deep breathing start and end, Valsalva 1 to 3
start and end, tilt start, tilt end. Several subjects have notes such as
"Ignore marker 3" or fewer than 11 markers. The published tables are
authoritative and override any pulse counting.

Pulses are detected as contiguous runs above 0.5 on the marker channel.

Any record where the published marker table cannot be reconciled with the
detected pulses is **excluded, and listed by name in the paper**. This
exclusion rule is fixed now and may not be relaxed later.

---

## 4. Outcome label, fixed now

**Primary label, `OH`.** Consensus definition (Freeman et al. 2011): a
sustained fall from supine baseline of systolic BP by at least 20 mmHg, or
diastolic BP by at least 10 mmHg, within 3 minutes of tilt onset.

Operationalised on the continuous `abp` channel as follows.

- Baseline: mean beat-to-beat systolic and diastolic pressure over the final
  60 s of supine recording **before** the tilt-start pulse.
- Tilt window: from the tilt-start pulse to min(tilt-end pulse, tilt start +
  180 s). Where the tilt segment is shorter than 180 s, the full available
  segment is used and the record is flagged. **The count and identity of
  short-tilt records will be reported**, and a sensitivity analysis will
  restrict to records with a full 180 s.
- Sustained: the criterion must be met by a 10 s centred rolling mean of
  beat-to-beat systolic or diastolic pressure. Single-beat excursions do not
  count. This guards against cuff artifact and movement.
- Beat detection on `abp` by systolic peak detection with a physiological
  refractory period; every record's beat detection is visually spot-checked
  and the check is logged.

**Secondary label, `OT`.** Sustained heart-rate rise of at least 30 bpm from
supine baseline within the tilt window, from the `ecg` channel. Reported
descriptively only. This cohort is 55 to 75 years old and this label is
expected to be rare.

The clinical `Group` field (Control / DM / DMOH) from the summary table is
**not** the label. It is used only for cohort description and for one
pre-declared agreement check, section 8.

---

## 5. Model input, fixed now

Features are computed **only from signal recorded before the tilt-start pulse**.
No sample at or after the tilt pulse may enter any feature, for any model arm.
This is enforced in code by slicing the record once, at the tilt index, before
feature extraction is called.

Three input arms, declared in advance.

- **Arm S, scalars.** The Kim et al. feature set reconstructed from these
  recordings: age, supine baseline systolic BP, E-I difference, E:I ratio,
  Valsalva ratio. This is the replication arm.
- **Arm W, waveform.** Standard HRV (time, frequency, nonlinear), blood
  pressure variability, baroreflex sensitivity by sequence and spectral
  methods, and Valsalva-phase BP response features, computed over the supine,
  deep-breathing and Valsalva segments.
- **Arm S+W.** Union of the two.

The pre-registered comparison of interest is Arm W versus Arm S. If Arm W does
not beat Arm S, that is the finding.

---

## 6. Evaluation, fixed now

- **Splitting is by subject, never by recording.** A subject's Day 1 and Day 2
  records must fall on the same side of every split. Violating this would leak
  the answer between folds.
- Repeated stratified group k-fold, 5 folds, 20 repeats, fixed seeds recorded.
- Models: logistic regression with L2, and random forest. Both calibrated.
  Hyperparameters tuned inside the training folds only, never on the test fold.
- **Primary metric: AUROC.** Reported with a cluster bootstrap confidence
  interval resampling subjects, not recordings.
- Also reported, always, side by side:
  - PR-AUC, and the positive class prevalence that is its floor
  - Accuracy, and the majority-class accuracy that is its floor
  - Sensitivity and specificity at a pre-declared operating point of 0.90
    sensitivity, since a screening test that misses cases is useless
  - Calibration slope and intercept
- **No metric is reported without its floor printed immediately beside it.**

---

## 7. Reproducibility analysis, the primary contribution

Restricted to subjects having both a Day 1 and a Day 2 tilt record.

- **Label stability.** Cohen's kappa between the Day 1 OH label and the Day 2
  OH label for the same person. Also the raw disagreement count.
- **Prediction stability.** Intraclass correlation, ICC(2,1), of the model's
  predicted probability on Day 1 versus Day 2, with the model trained on
  subjects not in this pair set.
- **Bland-Altman** of predicted probability across days, with limits of
  agreement.

Pre-declared interpretation, fixed now so it cannot be rationalised later:

- kappa below 0.4 means the outcome itself is unstable across days, which
  limits what any screening model can achieve and is the headline finding.
- ICC below 0.5 means the screen is not reproducible at the individual level
  and should not be used as described in the prior literature.

---

## 8. Confound checks, all pre-declared, all reported whether or not they pass

The two most recent failures in this research programme were a class-equals-
generator confound and a prevalence artifact mistaken for a real effect. These
checks exist because of those failures.

1. **Majority-class floor.** Printed beside every accuracy. Done.
2. **Shuffled-label control.** The entire pipeline, including feature
   selection and tuning, re-run with labels permuted within the subject
   grouping, 200 permutations. The real AUROC must exceed the 95th percentile
   of the null distribution.
3. **Recording-day confound.** Is OH prevalence different on Day 1 versus
   Day 2? Is any feature predictive of *day* rather than of OH? A model
   trained to predict day from the same features must perform near chance.
4. **Duration confound.** Record duration varies from 411 s to 1885 s. Test
   whether duration alone predicts the label. If it does, duration is
   residualised out of all features and the analysis is repeated.
5. **Channel-count confound.** Records differ in channel count. Verify channel
   count does not predict the label.
6. **Diabetes-status confound.** The label will correlate with diabetes.
   Report model performance separately within the diabetic subgroup and within
   the control subgroup. If the model only separates diabetics from controls
   and does nothing within either group, say so plainly.
7. **Group-field agreement.** Compare the waveform-derived OH label against the
   clinical DMOH grouping. Disagreements are reported, not reconciled away.
8. **Leakage audit.** Assert in code that no feature array shares any sample
   index with the tilt window. Assertion failure halts the run.

---

## 9. Falsification conditions

The study is reported as negative, and framed as negative, if any of these hold.

- Fewer than 15 positive OH cases are found. Below that, no modelling is
  attempted and the paper becomes a reproducibility and feasibility report.
- Real AUROC does not exceed the 95th percentile of the shuffled-label null.
- A model predicting recording day from the same features reaches AUROC above
  0.70, indicating day-driven signal.
- Record duration predicts the label with AUROC above 0.65 and performance
  collapses after residualisation.
- Arm W does not beat Arm S. This does not kill the paper but the claim
  "waveforms add information" is then withdrawn, not softened.

---

## 10. What will be released

- All feature-extraction and analysis code.
- The derived per-record label table with the beat-detection spot-check log.
- The exclusion list with a stated reason per excluded record.
- This plan, unedited, with any amendments dated and appended below.
- No raw waveforms are redistributed. The source is already public under CC-BY.

---

## Amendments

### Amendment 1, 2026-09-15. Sampling rate in the published headers is wrong.

Discovered during segmentation, before any model was fitted.

Every `.hea` file in this dataset declares `1000` Hz. The true effective rate is
**500 Hz**. Six independent checks, each against a value documented in the
dataset's own protocol files:

| Check | At declared 1000 Hz | At 500 Hz | Documented / physiological value |
|---|---|---|---|
| Paced deep-breathing frequency, 13 of 14 records | 0.200 Hz | **0.100 Hz** | protocol states 0.1 Hz |
| Head-up tilt duration, Day 1 median | 156 s | **312 s** | protocol states a 5-minute tilt |
| Valsalva strain duration, n=53 | 6.6 s | **13.1 s** | standard strain is 15 s |
| Heart rate, all 59 Day 1 records | median 130, max 182 | **median 65, range 47 to 91** | plausible for ages 55 to 75 |
| Respiratory rate from capnography | 34 to 39 /min | **17 to 19 /min** | plausible at rest |
| Whole-record duration, s0030DA | 480 s | **960 s** | fits the full documented protocol |

The deep-breathing check is decisive on its own: the protocol paces breathing at
0.1 Hz, and the measured ratio is exactly 2.00.

**Consequences of not catching this.** Every frequency-domain HRV feature would
have been displaced by one octave, placing the LF and HF bands on the wrong
physiology. Baroreflex sensitivity, in ms/mmHg, would have been wrong by a
factor of two. The consensus 3-minute OH window would in fact have been
90 seconds. The first label run, made before this was found, reported 52.9
percent OH prevalence, which is implausible for this cohort and is now
understood to be partly an artifact of the truncated window.

**Change adopted.** All timing uses `fs = 500` Hz. The published header value is
overridden in code by a single constant, `TRUE_FS = 500`, with the override
logged in every output file. Section 2 of this plan is amended accordingly.

**Also adopted, same amendment.** Consensus OH describes a *sustained* fall and
is distinct from initial orthostatic hypotension, which is a transient in the
first seconds of standing and occurs in healthy people. The first **30 s** after
tilt onset is therefore excluded from the OH determination. The 30 s figure is
fixed now, before the label is recomputed. The initial transient will be
reported separately as a descriptive measure, not as the primary label.

**Disclosure.** The 52.9 percent figure from the pre-amendment run is recorded
here so that the change is auditable. It was not used for any inference and no
model was fitted to it.

**External corroboration, added 2026-09-16.** The same laboratory (Novak, Beth
Israel Deaconess) has published a second open dataset, *Cerebral Vasoregulation
in Elderly with Stroke* (cves v1.0.0), recorded on the same rig under the same
head-up tilt protocol. Its channel list is identical in name and order:
`marker, ecg, abp, mcar, mcal, radi, thermst, flow_rate, o2, co2`.

**Every cves header declares 500 Hz.**

Read at its declared 500 Hz, cves is physiological, and it matches the diabetes
dataset only when the diabetes dataset is also read at 500 Hz:

| | cves at declared 500 Hz | diabetes at declared 1000 Hz | diabetes at 500 Hz |
|---|---|---|---|
| heart rate, median | **64.4 bpm** (48 to 78) | 130 bpm (94 to 182) | **65 bpm** (47 to 91) |
| respiratory rate | **14.0 /min** (8 to 22) | 34 to 39 /min | **17 to 19 /min** |

This is the seventh independent line of evidence and the only one that is
external to the diabetes recordings themselves. The correcting value is
published by the same group that released the defective file.

**Documentary evidence, added 2026-09-16.** The cves release includes the
laboratory's own written protocol, `full-study-protocol.docx`. It states, of the
Day 2 head-up tilt instrumentation:

> "All analog signals will be recorded at 500 Hz using Labview NIDAQ (National
> Instruments Data Acquisition System 64 Channel/100 Ks/s, Labview 6i, Austin,
> TX)."

and separately:

> "Cardiovascular, respiratory and TCD signals during the tilt were recorded on
> Labview at 500Hz"

The diabetes recordings come from the same Labview NIDAQ rig, in the same
laboratory, under the same head-up tilt protocol, and are stored in a directory
the dataset itself names `Data/Labview/`. The acquisition rate is therefore not
inferred, it is documented by the investigators. This is the eighth line of
evidence and it is the decisive one.

**Action outside this study.** The sampling-rate discrepancy will be reported to
the PhysioNet dataset maintainers, citing the cves headers and the laboratory's
own protocol document as the references.

---

### Amendment 2, 2026-09-16. The primary label definition was wrong, and the error was mine.

Section 4 operationalised the sustained fall as
`baseline mean − minimum of a 10 s rolling mean across the tilt window`.

That statistic is biased. The expected minimum of a series falls as the window
lengthens and as variability rises, so a person with noisy blood pressure and no
true orthostatic fall scores as though they had one. Measured on these 71
records, it inflates the systolic drop by **+17.2 mmHg on average**, against a
diagnostic threshold of 20 mmHg. The statistic was, in effect, manufacturing the
diagnosis.

Three readings of the **same** recordings:

| Reading | OH prevalence |
|---|---|
| A. minimum of a 10 s rolling mean across the tilt | **38 %** |
| B. clinical timepoints, 1 min and 3 min, ±15 s means | **10 %** |
| C. mean of the final 60 s of tilt | **8 %** |

A and B agree on only 72 percent of records, kappa 0.303.

**Which reading is right was decided by external validation, not by preference.**
The dataset's summary table contains the original study clinicians' own cuff
readings during tilt, at baseline, 1, 3 and 5 minutes. Against that reference,
on the 35 Day 1 records where both exist:

| Reading | Agreement | Kappa | False positives | False negatives |
|---|---|---|---|---|
| A. minimum | 69 % | 0.304 | 8 | 3 |
| B. clinical timepoints | **83 %** | **0.426** | **0** | 6 |

Reading B is adopted as the primary definition. It matches consensus criteria,
which specify measurement within 3 minutes of tilt, it matches how a clinician
actually reads a tilt table, and it produces no false positives against the
original clinicians. It remains conservative, under-calling relative to the
clinicians, and that direction is stated in the paper.

**A finding that was withdrawn.** Under reading A, day-to-day agreement in the
20 subjects with two recordings was kappa **0.200**, which looked like evidence
that the OH reference standard is barely reproducible. That was a striking
result and it was wrong. Under reading B the same 20 subjects give agreement of
90 percent and kappa **0.608**. The instability was a property of my statistic,
not of the patients. The kappa 0.200 figure is recorded here, and will be
reported in the paper as a demonstration of the sensitivity to operationalisation,
but it is **not** claimed as evidence that tilt testing is unreliable.

**Why this is written down rather than quietly fixed.** The error was found only
because the derived label was checked against the original clinicians' readings.
That check was not in the original plan. It is now mandatory, and is added to
section 8 as confound check 9:

> **9. External label validation.** Any derived label must be compared against
> the original study clinicians' own recorded measurements before it is used for
> anything. Agreement, kappa, and the direction of disagreement are reported.

**Consequence for the study design.** Under reading B there are **7** OH
positive records out of 71. Section 9 of this plan states that fewer than 15
positives means no modelling is attempted and the study becomes a reproducibility
and feasibility report. **That falsification condition has fired, and it is
honoured.** The prediction model described in sections 5 and 6 is not built.

The study is re-scoped to what the data actually supports, described in
Amendment 3.

---

### Amendment 3, 2026-09-16. Re-scope. Written before any feature was computed and before any model was fitted.

The binary label cannot support a prediction study at 7 positives. The
underlying physiological quantity can. This amendment fixes the new design in
advance so that it cannot be tuned after the fact.

#### 3.1 What the paper is

A measurement-validity study of the orthostatic hypotension reference standard,
with one constructive contribution. Four components, in order of priority.

**C1. The reference standard is not a single quantity.** Reading the same
continuous recordings three defensible ways gives OH prevalence of 8, 10 and 38
percent. Only one reading agrees with the clinicians who ran the original study.
Already established, Amendment 2.

**C2. Dichotomising destroys the reliability that the underlying measurement
has.** On 20 subjects recorded twice, the continuous orthostatic fall has
ICC(2,1) 0.586 and a within-subject SD of 12.6 mmHg, against a diagnostic
threshold of 20 mmHg. The binary label derived from it has kappa 0.608 under the
clinical reading and 0.200 under the minimum reading. Already established.

**C3. Silent data defects propagate.** The published sampling rate is wrong by a
factor of two, confirmed six ways. Already established, Amendment 1.

**C4, the new work.** If the binary label is unstable but the continuous
quantity is not, then the continuous quantity is what a model should target.
This amendment pre-registers that analysis.

#### 3.2 Primary outcome, fixed now

`delta_SBP` = supine baseline systolic pressure minus the mean systolic pressure
in a ±15 s window centred on the later of the 1-minute and 3-minute tilt
timepoints, whichever gives the larger fall. That is definition B of Amendment 2,
kept continuous instead of thresholded. Units mmHg. Sign convention: positive
means the pressure fell.

Secondary outcome, `delta_DBP`, same construction.

The binary label is retained only for description and for the C1 and C2 analyses.
**No binary classifier is fitted.**

#### 3.3 Primary hypothesis and the number that decides it

Pre-tilt signal predicts `delta_SBP` better than chance.

- Primary metric: **out-of-fold Spearman correlation** between predicted and
  observed `delta_SBP`, subject-level grouping.
- Declared **null comparison**: the same pipeline with `delta_SBP` permuted
  within subject groups, 1000 permutations. The observed rho must exceed the
  97.5th percentile of that null.
- Declared **floor comparison**: a model using only age, sex and supine baseline
  SBP. The waveform model must beat this floor, or the waveform claim is
  withdrawn rather than softened.
- Also reported: MAE in mmHg, and the SD of `delta_SBP`, so the reader can see
  whether the model beats simply predicting the mean.

#### 3.4 Prediction is from pre-tilt signal only

Features come only from samples strictly before the tilt-onset index. Enforced by
slicing the record once at that index before any feature function is called, plus
a runtime assertion. Assertion failure halts the run.

Feature families, fixed now:
supine heart-rate variability in time, frequency and nonlinear domains; systolic
and diastolic variability; baroreflex sensitivity by the sequence method and by
spectral alpha; deep-breathing E:I ratio and E-I difference where the segment
exists; Valsalva ratio and Valsalva phase II and IV pressure responses; end-tidal
CO2 level and respiratory rate.

Day 2 records have a longer pre-tilt period and no deep-breathing segment.
**All features are computed on windows matched in length across days**, and any
feature that cannot be computed on both days is excluded from the primary model.

#### 3.5 Record recovery, and why it is legitimate

71 of 110 records currently pass. Most exclusions are because the published
marker tables cannot be indexed against the detected pulses, not because the
recording is bad.

A tilt-onset detector will be built from the pressure and heart-rate step change.
It is **developed and validated only on the records whose markers do reconcile**,
where the marker-derived onset is the reference. It is accepted only if median
absolute error is under 5 s and 90th percentile error is under 15 s. Only then is
it applied to the unindexable records.

This is declared now, before the detector exists. Records recovered this way are
flagged in every table, and the entire primary analysis is repeated without them
as a sensitivity analysis. If the conclusion changes, both are reported.

#### 3.5a Outcome of the record-recovery attempt, 2026-09-16

The detector was built and tested as specified. **It failed the pre-declared
gate and is not used.**

| | median abs error | 90th pct | within 15 s |
|---|---|---|---|
| gate | < 5 s | < 15 s | — |
| all records, n=71 | 113.2 s | 685.5 s | 32 % |
| day 1 only, n=48 | 18.8 s | — | 44 % |
| day 2 only, n=23 | 552.2 s | — | 9 % |

The day 2 failure mode is informative and is reported in the paper: the detector
locks onto the **hypocapnic** tilt, which produces a larger haemodynamic step
than the normocapnic one that precedes it. A generic "find the biggest
orthostatic transition" heuristic therefore selects the wrong event in a
protocol containing more than one tilt.

A second approach, anchoring the tilt ordinal from the end of the pulse train
rather than the start, recovered 55 of 59 day 1 records but mis-anchored 8
percent of them by more than 5 s. That trades 7 extra records for label noise on
an unknown subset, and was rejected.

**Decision.** The analysis proceeds on the 71 cleanly indexed records from 51
subjects. All exclusions are listed by name with their reason. No record is
recovered by inference.

#### 3.6 Confound checks, in addition to section 8

10. **Recording day.** Day is included as a covariate and a model predicting day
    from the features must be near chance.
11. **Pre-tilt duration.** Day 2 pre-tilt periods are roughly three times longer.
    Duration must not predict `delta_SBP`, and features are computed on matched
    windows.
12. **Baseline pressure.** A higher supine pressure permits a larger absolute
    fall. Report the model with and without baseline SBP, and report results for
    the relative fall as a percentage of baseline.
13. **Diabetes status.** Report performance within the diabetic and control
    subgroups separately. If the model only separates the two groups, say so.
14. **Repeated subjects.** 20 subjects contribute two records. All confidence
    intervals use a cluster bootstrap over subjects.

#### 3.7 Falsification conditions for C4, fixed now

C4 is reported as negative, in the abstract, if any of these hold.

- Out-of-fold Spearman rho does not exceed the 97.5th percentile of the
  permutation null.
- The waveform model does not beat the age, sex and baseline-SBP floor.
- Model MAE is not lower than the MAE of predicting the cohort mean.
- A model predicting recording day from the same features reaches AUROC above
  0.70.

A negative C4 does not weaken C1, C2 and C3, which stand on measurements already
made. The paper is viable either way, and this is stated here so that a negative
result creates no incentive to keep searching.

#### 3.8 What will not be done

No further changes to the outcome definition. No additional model families beyond
regularised linear regression and gradient-boosted trees. No threshold tuning.
If C4 fails, it is reported as failed and the paper leads with C1 to C3.


---

### Amendment 4, 2026-09-16. Second cohort added. Written before any cves label or feature was computed.

#### 4.1 Why

The Amendment 3 analysis rested on 71 records from 51 subjects in a single
cohort. Two weaknesses follow. The C1 operationalisation finding was shown in
one dataset and could be a quirk of it. The C4 null was underpowered, so
"no signal" and "not enough data to see signal" are not separable.

A second, independent cohort addresses both.

#### 4.2 The cohort

PhysioNet, *Cerebral Vasoregulation in Elderly with Stroke*, cves v1.0.0
(Novak V, 2018). DOI 10.13026/C2DW96. Open Data Commons Attribution License,
open access, de-identified, no IRB required and none sought.

68 head-up tilt recordings, one per subject, no repeat days. Ages 60 to 80.
Recruitment targeted 60 stroke and 60 non-stroke; 48 controls and 43 stroke
participants completed. **Diabetes is an explicit exclusion criterion**, so the
two cohorts do not overlap in population: diabetics in one, stroke patients with
diabetes excluded in the other.

Same laboratory, same Labview NIDAQ rig, same Portapres finger pressure device,
same ten channels in the same order. Declared 500 Hz, which matches the protocol.

**Defect noted now, before analysis.** The published `RECORDS` index lists every
head-up-tilt record exactly twice, 136 lines for 68 files. The other five data
folders are listed once each. Any pipeline that iterates `RECORDS` will process
each tilt record twice and report double the true sample size. This is reported
in the paper and to the maintainers.

#### 4.3 Segmentation, fixed now

cves has no per-subject marker table. The protocol document fixes the Day 2
order: 10 min supine, two Valsalva maneuvers at 15 s strain, hyperventilation to
CO2 25 mmHg for 3 min, CO2 rebreathing to 45 mmHg for 3 min, 5 min equilibration,
10 min supine, then **head-up tilt to 80 degrees for 10 minutes**.

The tilt is the final event of the protocol. Tilt onset is therefore defined as
**the second-to-last marker pulse**, and tilt end as the last, subject to these
acceptance rules fixed now:

- the final inter-pulse interval must be between 240 and 900 s. The protocol
  specifies 10 minutes; the window allows for tilts terminated early
- the protocol states the tilt was interrupted on pre-syncope or blurred vision,
  so records with a final interval between 240 and 540 s are flagged as
  **possibly aborted** and a sensitivity analysis excludes them
- records with fewer than 4 marker pulses are excluded outright
- every excluded record is listed by name with its reason

This anchoring rule is declared before any cves outcome is computed. It is not
tuned against the result.

#### 4.4 External label validation is mandatory here too

`subjects.csv` contains the original clinicians' own tilt measurements, including
`SBP BASELINE`, `SBP TILT`, `SBP change tilt`, `DBP change tilt`, and a clinical
`OH` symptom field. Confound check 9 of Amendment 2 applies without exception:
the waveform-derived label is compared against these before it is used for
anything, and agreement, kappa and the direction of disagreement are reported.

If the segmentation rule in 4.3 is wrong, this check will expose it. That is its
purpose.

#### 4.5 What is tested in cves, and what is not

**Replicated, C1.** The three readings of Amendment 2, A minimum, B clinical
timepoints, C final-60 s mean, are applied to cves. The pre-declared prediction
is that prevalence again differs several-fold across readings, and that reading B
again agrees best with the clinicians. If prevalence does **not** move materially
across readings in cves, C1 is reported as not replicating, and the diabetes
result is reported as cohort-specific.

**Replicated with more power, C4.** The Amendment 3.3 regression is re-run on the
pooled cohorts with cohort as a covariate, and separately within cves alone. All
falsification conditions of 3.7 carry over unchanged. Cohort is added to confound
check 10: a model predicting cohort from the features must be near chance, and if
it is not, pooled results are reported only alongside within-cohort results.

**Not tested in cves.** Day-to-day reproducibility. cves has one recording per
subject. C2 remains based on the 20 diabetes pairs and its sample size is stated
plainly as a limitation.

#### 4.6 No further datasets

Two cohorts is the analysis. If C4 is null in both, it is reported as null. This
clause exists so that a second null does not become a reason to go looking for a
third cohort.
