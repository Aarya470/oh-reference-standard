const d = require('docx');
const {Document,Packer,Paragraph,TextRun,HeadingLevel,AlignmentType,Table,TableRow,TableCell,
       WidthType,ShadingType,BorderStyle,PageOrientation,convertInchesToTwip} = d;
const fs = require('fs');

const FONT="Times New Roman";
const P = (text,o={}) => new Paragraph({
  spacing:{after:o.after??120, line:o.line??276},
  alignment:o.align??AlignmentType.JUSTIFIED,
  indent:o.indent,
  children:[new TextRun({text,font:FONT,size:o.size??22,bold:o.bold,italics:o.italics})]});
const RUNS = (runs,o={}) => new Paragraph({
  spacing:{after:o.after??120, line:o.line??276},
  alignment:o.align??AlignmentType.JUSTIFIED,
  children:runs.map(r=>new TextRun({text:r.t,font:FONT,size:o.size??22,bold:r.b,italics:r.i}))});
const H1 = t => new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:260,after:120},
  children:[new TextRun({text:t,font:FONT,size:22,bold:true,allCaps:true,color:"000000"})]});
const H2 = t => new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:180,after:100},
  children:[new TextRun({text:t,font:FONT,size:22,bold:false,italics:true,color:"000000"})]});
const GAP = () => new Paragraph({spacing:{after:80},children:[]});

const TW = 9360; // 6.5in
function table(headers, rows, widths, caption){
  const cell = (txt,{b=false,shade=false,al=AlignmentType.LEFT}={},w) => new TableCell({
    width:{size:w,type:WidthType.DXA},
    shading: shade?{type:ShadingType.CLEAR,fill:"E8E8E8"}:undefined,
    margins:{top:60,bottom:60,left:90,right:90},
    children:[new Paragraph({alignment:al,spacing:{after:0,line:240},
      children:[new TextRun({text:txt,font:FONT,size:19,bold:b})]})]});
  const trs=[new TableRow({tableHeader:true,children:headers.map((h,i)=>
    cell(h,{b:true,shade:true,al:i?AlignmentType.CENTER:AlignmentType.LEFT},widths[i]))})];
  rows.forEach(r=>trs.push(new TableRow({children:r.map((c,i)=>
    cell(String(c),{al:i?AlignmentType.CENTER:AlignmentType.LEFT},widths[i]))})));
  const out=[];
  if(caption) out.push(new Paragraph({spacing:{before:160,after:80},
    children:[new TextRun({text:caption,font:FONT,size:19,bold:true})]}));
  out.push(new Table({columnWidths:widths,width:{size:TW,type:WidthType.DXA},rows:trs}));
  out.push(new Paragraph({spacing:{after:140},children:[]}));
  return out;
}

const body = [];
const push = (...x)=>x.forEach(e=>Array.isArray(e)?body.push(...e):body.push(e));

// ---------------------------------------------------------------- title
push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:140},
  children:[new TextRun({text:"What Are We Predicting? Reference-Standard Instability in Machine Learning for Orthostatic Hypotension",font:FONT,size:30,bold:true})]}));
push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:40},
  children:[new TextRun({text:"Aaryan Roy",font:FONT,size:23})]}));
push(new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:260},
  children:[new TextRun({text:"aaryan10cityzen@gmail.com",font:FONT,size:20,italics:true})]}));

// ---------------------------------------------------------------- abstract
push(new Paragraph({spacing:{after:100},children:[new TextRun({text:"Abstract",font:FONT,size:22,bold:true,italics:true})]}));
push(P("Machine learning models for orthostatic hypotension are trained against a label derived from a tilt-table test. That label is treated as fixed. We show it is not. Using two open cardiovascular autonomic datasets from the same laboratory, 71 tilt recordings from 51 adults with and without type 2 diabetes and 54 recordings from 54 adults with and without ischemic stroke, we read the same continuous arterial pressure signals three ways, each defensible and each used in the literature. Orthostatic hypotension prevalence moved from 8 to 38 percent in the first cohort and from 11 to 46 percent in the second. Only one reading agreed well with the clinicians who originally ran each study, and it was a different reading in each cohort because the two studies recorded their reference measurements differently. Day-to-day agreement in 20 adults recorded twice was kappa 0.61 under the best reading and 0.20 under the worst, on identical data. The orthostatic change is a small difference between two large, strongly correlated pressures, so it is unreliable per patient by construction. We also report two silent defects in the published data: a sampling rate declared at twice its true value, confirmed eight ways including the laboratory's own protocol, and an index file that lists every tilt recording twice. Finally, we pre-registered and ran a prediction study. Pooled across cohorts it produced a rank correlation of 0.250, p equal to 0.003, with a confidence interval excluding zero. It was an artifact: the model predicted which cohort a recording came from at an area under the curve of 0.788, its error exceeded that of predicting the cohort mean, and the effect vanished in the second cohort. We argue that reported accuracies for orthostatic hypotension prediction are not comparable across studies, and we specify what a paper must report for them to become so.",{size:21}));
push(GAP());
push(RUNS([{t:"Index Terms",b:true,i:true},{t:" — orthostatic hypotension, head-up tilt, reference standard, measurement reliability, reproducibility, open data, autonomic nervous system."}],{size:21}));

// ---------------------------------------------------------------- I
push(H1("I. Introduction"));
push(P("Orthostatic hypotension is defined by consensus as a sustained fall in systolic blood pressure of at least 20 mmHg, or in diastolic pressure of at least 10 mmHg, within three minutes of standing or head-up tilt. The definition is a threshold applied to a measurement. It says nothing about how the measurement should be taken from a continuous recording, and continuous beat-to-beat pressure is what modern tilt laboratories actually acquire."));
push(P("This gap is not academic. A clinician reading a tilt table takes discrete pressures at fixed minutes. An analyst with a waveform can take the minimum across the tilt, a rolling mean, a mean over the final segment, or values at the same fixed minutes. Each is a reasonable reading of the same consensus sentence. Each produces a different label for the same patient."));
push(P("Machine learning studies inherit whichever label their source used, and then report accuracy against it as though the target were fixed. Kim et al. proposed screening for orthostatic hypotension without a tilt table, using five scalar autonomic-test measures, and reported 90.6 percent accuracy with a random forest [1]. Their cohort contained 78 cases among 663 patients. A classifier that always answers negative scores 88.2 percent on that cohort. The reported figure exceeds the majority-class floor by 2.4 points, and because accuracy was the reported metric on an imbalanced sample, the size of the underlying effect is not recoverable from the paper."));
push(P("We do not single that study out. It is a careful paper and it is representative. Our point is that the field lacks the information needed to compare such results at all, because the label they are measured against is not one quantity."));
push(P("This paper makes four contributions."));
push(P("1) We quantify how far orthostatic hypotension prevalence moves when the same recordings are read in three defensible ways, and we replicate that in an independent cohort with a different disease.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("2) We validate each reading against the measurements recorded by the clinicians who ran the original studies, and show that the best-agreeing reading differs between cohorts because the two studies recorded their reference differently.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("3) We report two data defects in the published resources that would silently corrupt downstream analysis, and we document how each was detected.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("4) We pre-register a prediction study, report it as negative, and show in detail how a pooled analysis of the same data produces a significant-looking result that is an artifact of cohort structure.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("The full pre-analysis plan, including every amendment with its date and reason, is released with the code."));

// ---------------------------------------------------------------- II
push(H1("II. Materials"));
push(H2("A. Cohorts"));
push(P("Both datasets are open access on PhysioNet, fully de-identified, and were collected at the Syncope and Falls in the Elderly Laboratory, Beth Israel Deaconess Medical Center. No institutional review board approval was required for this secondary analysis and none was sought."));
push(P("Cohort 1, Cerebral Vasoregulation in Diabetes [2], contains head-up tilt recordings from adults aged 55 to 75 with type 2 diabetes and age-matched controls. Of the 116 published tilt recordings, 110 were available at the time of analysis. Each carries a marker channel, electrocardiogram, continuous finger arterial pressure, respiration and capnography at 1000 Hz as declared. A subset adds transcranial Doppler."));
push(P("Cohort 2, Cerebral Vasoregulation in Elderly with Stroke [3], contains 68 head-up tilt recordings from adults aged 60 to 80, recruited as 60 stroke and 60 non-stroke, of whom 48 controls and 43 stroke participants completed the protocol. Diabetes is an explicit exclusion criterion, so the two cohorts do not overlap in population. Channels are identical in name and order to cohort 1, declared at 500 Hz."));
push(H2("B. Two defects in the published data"));
push(P("Sampling rate. Every header in cohort 1 declares 1000 Hz. The true rate is 500 Hz. Table I lists eight independent confirmations. The most direct is that cohort 1's own protocol paces deep breathing at 0.1 Hz; measured at the declared rate the paced frequency is 0.200 Hz in 13 of 14 records, a ratio of exactly 2.00. The most conclusive is documentary: the protocol distributed with cohort 2 states that all analog signals were recorded at 500 Hz on the Labview NIDAQ system, and cohort 1's recordings are stored in a directory the dataset itself names Data/Labview."));
push(P("Read at 1000 Hz, cohort 1 implies a median resting heart rate of 130 beats per minute and a respiratory rate of 34 to 39 per minute in adults aged 55 to 75. At 500 Hz those become 65 and 17 to 19. Uncorrected, every frequency-domain heart-rate-variability measure is displaced by one octave, placing the low- and high-frequency bands on the wrong physiology; baroreflex sensitivity in ms/mmHg is wrong by a factor of two; and the three-minute window the consensus definition requires is in fact 90 seconds."));
push(P("Index duplication. In cohort 2 the published RECORDS index lists every head-up tilt recording exactly twice, 136 lines for 68 files. The dataset's five other data folders are each listed once. RECORDS is the file an automated pipeline iterates, so any such pipeline processes every tilt recording twice and reports double the true sample size."));
push(P("Both defects have been reported to the dataset maintainers."));

push(table(["Check","At declared rate","At 500 Hz","Expected"],
[["Paced deep breathing, 13 of 14 records","0.200 Hz","0.100 Hz","0.1 Hz per protocol"],
 ["Head-up tilt duration, cohort 1 day 1","156 s","312 s","5 min per protocol"],
 ["Valsalva strain duration, n = 53","6.6 s","13.1 s","15 s standard"],
 ["Heart rate, 59 day-1 records","median 130","median 65","50 to 90, ages 55 to 75"],
 ["Respiratory rate, capnography","34 to 39 /min","17 to 19 /min","12 to 20 /min at rest"],
 ["Whole-record duration, s0030DA","480 s","960 s","fits full protocol"],
 ["Cohort 2 headers, same rig and channels","—","declares 500 Hz","external reference"],
 ["Laboratory protocol document","—","\"recorded at 500 Hz\"","documentary"]],
[3300,1900,1900,2260],
"TABLE I. Eight independent confirmations that the declared sampling rate of cohort 1 is wrong by a factor of two."));

// ---------------------------------------------------------------- III
push(H1("III. Methods"));
push(H2("A. Segmentation"));
push(P("Cohort 1 ships per-subject marker tables mapping marker-pulse ordinals to protocol events. These tables are authoritative. Any recording whose table could not be reconciled against the detected pulses was excluded and is listed by name in the released materials. This rule was fixed before analysis and was not relaxed."));
push(P("Cohort 2 ships no marker table. Its protocol fixes the day-2 order and places head-up tilt last, at 80 degrees for 10 minutes. Tilt onset was therefore defined as the second-to-last marker pulse, accepted only when the final inter-pulse interval fell between 240 and 900 s. The rule was declared before any cohort-2 outcome was computed. It is supported after the fact by three independent checks: the resulting median tilt duration is 612 s against a protocol specifying 600 s; mean tilt systolic pressure correlates 0.899 with the clinicians' recorded tilt pressure; and baseline heart rate correlates 0.919 with theirs."));
push(P("We also built a purely physiological tilt-onset detector, intended to recover recordings whose marker tables could not be indexed. It was required in advance to reach a median absolute error below 5 s. It reached 113 s and was discarded. Its failure mode is instructive and we report it: in a protocol containing more than one orthostatic challenge the detector locks onto the hypocapnic tilt, which produces a larger haemodynamic step than the normocapnic tilt preceding it."));
push(H2("B. Beat detection"));
push(P("Beats were located from the arterial pressure wave rather than the electrocardiogram. Standard R-peak detectors, including a widely used open implementation, returned approximately twice the true rate on the electrocardiogram channel of these recordings, while the pressure wave gives one peak per beat in agreement with the spectral dominant frequency. Systolic and diastolic values were taken per beat between consecutive systolic peaks, with beats outside physiological bounds discarded. Median beat yield exceeded 0.99."));
push(H2("C. Three readings of the consensus definition"));
push(P("From an identical supine baseline, the mean of the final 60 s before tilt onset, we computed three readings of the orthostatic fall:"));
push(P("A. the minimum of a 10 s centred rolling mean across the tilt window, excluding the first 30 s so that initial orthostatic hypotension is not counted;",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("B. the fall at the clinical timepoints, the mean over ±15 s windows centred at 1 and 3 minutes, taking the larger;",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("C. the fall at the mean of the final 60 s of the analysis window.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("Each was thresholded at the consensus criterion. Reading A was our own first choice and we report below why it was wrong."));
push(H2("D. External label validation"));
push(P("Both datasets include the original investigators' own tilt measurements: discrete cuff pressures at baseline, 1, 3 and 5 minutes in cohort 1, and baseline and tilt-mean pressures in cohort 2. Every derived label was compared against these before being used for anything. This check is the reason the analysis in this paper is not the analysis we set out to do."));
push(H2("E. Pre-registered prediction study"));
push(P("Features were computed only from signal recorded strictly before tilt onset, enforced by slicing each record once at the tilt index before any feature function ran, with a runtime assertion. Feature families were heart-rate variability in time, frequency and nonlinear domains, systolic and diastolic variability, baroreflex sensitivity by the sequence method and by spectral alpha, and end-tidal CO2 and respiratory rate. Fifty-four features were computable in both cohorts."));
push(P("The outcome was the continuous orthostatic systolic fall under reading B. Models were ridge regression and gradient-boosted trees. Splits were grouped by subject so that a participant's two recordings never straddled a fold. The primary metric was out-of-fold Spearman correlation with cluster-bootstrap intervals over subjects. Declared in advance were a subject-level block permutation null, a floor model using only age, sex and baseline systolic pressure, a comparison against the error of predicting the cohort mean, and a check that recording day and cohort were not themselves predictable from the features. Four falsification conditions were fixed before the data were seen; any one firing makes the result negative."));

// ---------------------------------------------------------------- IV
push(H1("IV. Results"));
push(H2("A. Cohorts analysed"));
push(P("In cohort 1, 71 of 110 recordings from 51 subjects passed segmentation, 48 from day 1 and 23 from day 2; 26 lacked a tilt marker, 11 could not be reconciled against the published table, and 2 had an unusable tilt window. Median analysis window was 180 s, with one truncated recording. In cohort 2, 54 of 68 recordings passed; median tilt span was 612 s and 4 recordings were flagged as possibly terminated early, consistent with the protocol's provision for stopping on pre-syncope. Median resting heart rate was 68 and 69 beats per minute respectively, both physiological at the corrected rate."));
push(H2("B. The reading determines the prevalence"));
push(P("Table II gives the result that motivates this paper. On identical recordings, prevalence moves roughly four-fold across three defensible readings, and the pattern replicates in an independent cohort with a different disease, a different segmentation procedure and no shared subjects."));
push(table(["Reading of the same recordings","Cohort 1, diabetes (n = 71)","Cohort 2, stroke (n = 54)"],
[["A. minimum across the tilt","38.0 %","46.3 %"],
 ["B. clinical timepoints, 1 and 3 min","9.9 %","18.5 %"],
 ["C. mean of the final 60 s","8.0 %","11.1 %"],
 ["ratio, highest to lowest","4.8×","4.2×"]],
[4160,2600,2600],
"TABLE II. Orthostatic hypotension prevalence by reading. Same signals, same consensus threshold, same baseline definition."));
push(H2("C. Reading A was ours, and it was wrong"));
push(P("Our pre-registered primary reading was A. It is biased. The expected minimum of a series falls as the observation window lengthens and as variability rises, so a participant with labile pressure and no true orthostatic fall scores as though they had one. Measured on cohort 1, reading A inflates the systolic fall by 17.2 mmHg on average against a diagnostic threshold of 20 mmHg."));
push(P("We discovered this only by comparing against the original clinicians. Table III gives that comparison. In cohort 1, reading B agrees best and produces no false positives against the clinicians. In cohort 2, the best agreement comes from a reading matched to how that study recorded its reference, a tilt-mean rather than discrete timepoints."));
push(table(["Reading","Cohort 1 agreement","Cohort 1 kappa","Cohort 2 agreement","Cohort 2 kappa"],
[["A. minimum","69 %","0.304","55 %","0.008"],
 ["B. clinical timepoints","83 %","0.426","83 %","0.128"],
 ["C. final 60 s","—","—","91 %","0.245"],
 ["matched to each study's own reference","83 %","0.426","96 %","0.480"]],
[3000,1590,1590,1590,1590],
"TABLE III. Agreement of each reading with the measurements recorded by the clinicians who ran each original study."));
push(P("The last row is the finding. There is no single reading that is correct in both cohorts. The reading that agrees with the reference depends on how the reference itself was recorded, and that is a property of the study, not of the patient."));
push(H2("D. A withdrawn result, reported because it is instructive"));
push(P("Under reading A, day-to-day agreement in the 20 cohort-1 participants recorded twice was kappa 0.200, with 8 of 20 discordant. Taken at face value this says the tilt-table reference standard barely reproduces, which would undercut every accuracy figure in the screening literature. It is a striking claim and it is not supported. Under reading B the same 20 participants give 90 percent agreement and kappa 0.608. The instability was a property of our statistic, not of the patients. We withdraw the claim and report the numbers here so the sensitivity to operationalisation is visible."));
push(H2("E. Why the change is unreliable even when the pressures are not"));
push(P("Reproducibility of the underlying continuous quantity is moderate, not poor: ICC(2,1) of 0.586 across days, with a within-subject standard deviation of 12.6 mmHg against a 20 mmHg diagnostic threshold and 95 percent limits of agreement from -32.7 to +37.1 mmHg. Dichotomising a moderately reliable continuous measure at a threshold that sits inside its own measurement error is what produces the unstable binary label."));
push(P("Cohort 2 shows the mechanism directly. Our measurements and the clinicians' agree well on levels: baseline heart rate correlates 0.919, tilt systolic pressure 0.899, baseline systolic pressure 0.670. They agree on the population summary, both giving orthostatic hypotension in 2 of 53, 96 percent agreement, kappa 0.480. Yet the per-participant systolic change correlates at only -0.162. The reason is arithmetic: baseline and tilt systolic pressures have standard deviations of 16.4 and 18.6 mmHg and correlate at 0.797, so their difference has a standard deviation of only 11.3 mmHg and carries mostly noise. The orthostatic change is a small difference between two large, strongly correlated numbers. In cohort 1 the same correlation is +0.635, because diabetic autonomic neuropathy creates genuine between-subject spread; cohort 2 excludes diabetes by design."));
push(H2("F. The prediction study, and how it nearly fooled us"));
push(P("Table IV gives the pre-registered analysis on 125 recordings from 105 subjects."));
push(table(["Configuration","n","Spearman rho","Null 97.5th pct","p","Model MAE","Cohort-mean MAE"],
[["Pooled, ridge","125","+0.250","+0.116","0.003","12.68","12.45"],
 ["Cohort 1 only","71","+0.145","+0.138","0.015","13.81","12.24"],
 ["Cohort 2 only","54","−0.015","+0.213","0.165","14.32","12.66"],
 ["Floor: age, sex, baseline SBP","125","+0.196","—","—","12.00","12.45"]],
[2500,620,1350,1400,780,1300,1410],
"TABLE IV. Pre-registered prediction of the continuous orthostatic systolic fall from pre-tilt signal only. MAE in mmHg."));
push(P("Read the first columns alone and the pooled result looks convincing: rho 0.250, confidence interval 0.111 to 0.421, p equal to 0.003 against a subject-level permutation null. Read the last two columns and it is useless. In every configuration the model's mean absolute error exceeds that of ignoring the patient and predicting the cohort average. The model ranks participants slightly better than chance while predicting their actual pressure fall worse than a constant."));
push(P("It also fails to replicate. In cohort 2 the correlation is -0.015, interval -0.293 to +0.274."));
push(P("The source of the pooled effect is identifiable. A model trained on the same features to predict only which cohort a recording came from reaches an area under the curve of 0.788, and the two cohorts differ in mean outcome, 5.63 against 7.13 mmHg. Part of the pooled rank correlation is the model recognising diabetics from stroke patients. Our pre-declared rule barred the pooled figure from standing alone once that check exceeded 0.70, which it did."));
push(P("Two of the four falsification conditions fired. The prediction result is negative."));

// ---------------------------------------------------------------- V
push(H1("V. Discussion"));
push(P("The central claim of this paper is narrow and, we think, hard to avoid. Reported accuracies for orthostatic hypotension prediction are not comparable across studies, because the target is not a fixed quantity. A four-fold difference in prevalence is available to any analyst working from the same recordings without departing from the consensus definition, and prevalence is what sets the majority-class floor that accuracy must be judged against."));
push(P("This compounds an existing problem. A study reporting 90.6 percent accuracy against a label with 11.8 percent prevalence is reporting 2.4 points above a constant predictor [1]. If a different but equally defensible reading of the same recordings would have produced 38 percent prevalence, the floor moves to 62 percent and the same model would be described very differently. Neither number is wrong. They are answers to different questions, and the papers do not currently contain the information needed to tell which question was asked."));
push(P("Our own near-miss is the clearest illustration we can offer. A pooled analysis of two real cohorts, using a pre-registered pipeline with subject-grouped cross-validation and a permutation null, produced a result with p equal to 0.003 and a confidence interval excluding zero, that was an artifact of cohort structure. It was caught by two checks written down before the data were seen: compare the model's error against predicting the mean, and verify that the model cannot identify the dataset a record came from. Neither is standard practice. Both are cheap."));
push(H2("A. What a paper should report"));
push(P("We propose four requirements, each of which we would have failed at some point in this work."));
push(P("1) State the reading. Specify exactly how the pressure fall was extracted from the recording, including the baseline window, the analysis window, whether an extremum or a mean was taken, and whether the initial transient was excluded. \"Consensus criteria\" is not sufficient.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("2) Print the floor beside every metric. Accuracy without the majority-class rate, and area under the precision-recall curve without the prevalence, are not interpretable.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("3) Validate the derived label against the original clinical measurements where they exist, and report the direction of disagreement, not only the agreement rate.",{indent:{left:convertInchesToTwip(0.25)}}));
push(P("4) When pooling cohorts, report the area under the curve for predicting cohort membership from the same features, and report within-cohort results alongside pooled ones.",{indent:{left:convertInchesToTwip(0.25)}}));
push(H2("B. Implications for the screening question"));
push(P("Our negative prediction result should be read with care. It does not show that pre-tilt autonomic signal is uninformative about orthostatic tolerance. It shows that in 125 recordings from two elderly cohorts, with 54 features and a pre-registered pipeline, the signal was not strong enough to beat a constant predictor and did not replicate across cohorts. Given the reliability of the target measured here, a within-subject standard deviation of 12.6 mmHg against a mean fall of about 6 mmHg, a large fraction of the variance a model is asked to predict is measurement error. Improving the reference standard may be a precondition for progress on the prediction problem, not a separate concern."));

// ---------------------------------------------------------------- VI
push(H1("VI. Limitations"));
push(P("The cohorts are elderly, 55 to 80 years, and specific: type 2 diabetes with controls, and ischemic stroke with controls, with diabetes excluded from the latter. Nothing here speaks directly to younger patients with postural tachycardia syndrome, where the diagnostic question and the signal are different."));
push(P("The reproducibility analysis rests on 20 participants recorded twice, all from cohort 1, and cohort 2's second-day tilt follows hypercapnic and hypocapnic challenges with roughly 160 s of recovery. We tested for systematic bias from this and found none, paired p equal to 0.588 and exact McNemar p equal to 0.727, but the sample is small and the design is not a clean test-retest."));
push(P("Sample size limits the prediction result. With 125 recordings and 105 subjects the study is powered only for moderate effects, and a small true association cannot be excluded. We report the result as negative under pre-declared conditions rather than as evidence of absence."));
push(P("Thirty-nine recordings in cohort 1 and 14 in cohort 2 were excluded, mostly for marker indexing failures. If those failures correlate with recording quality they could bias the sample. All exclusions are listed by name with reasons in the released materials."));
push(P("Finally, both cohorts come from a single laboratory using one instrument family. The prevalence-by-reading result should be tested on data from other laboratories and other pressure devices."));

// ---------------------------------------------------------------- VII
push(H1("VII. Conclusion"));
push(P("The label that machine learning studies of orthostatic hypotension are trained and scored against varies roughly four-fold depending on how the same recording is read, and the reading that matches the clinical reference depends on how that reference was recorded. Day-to-day agreement of the binary label ranges from kappa 0.20 to 0.61 on identical data according to that choice, because the orthostatic change is a small difference between two large correlated pressures. We report two silent defects in widely available public data and show how a pre-registered prediction study produced a significant-looking pooled result that was an artifact of cohort structure. Until studies state their reading, print their floors, and validate their labels against clinical measurement, reported accuracies in this area cannot be compared."));

// ---------------------------------------------------------------- data
push(H1("Data and Code Availability"));
push(P("Both datasets are open access on PhysioNet and are not redistributed here. All feature-extraction and analysis code, the derived per-recording label tables, the complete exclusion list with reasons, and the pre-analysis plan with every dated amendment are released at [REPOSITORY URL]. The pre-analysis plan is released unedited, including the amendment recording the withdrawn kappa 0.200 result and the reason for it."));

push(H1("References"));
const refs=[
 "J. B. Kim, H. Kim, J. H. Sung, S.-H. Baek, and B.-J. Kim, “Heart-rate-based machine-learning algorithms for screening orthostatic hypotension,” J. Clin. Neurol., vol. 16, no. 3, pp. 448–454, Jul. 2020.",
 "V. Novak and L. Mendez, “Cerebral vasoregulation in diabetes,” PhysioNet, v1.0.0, 2020, doi:10.13026/m40k-4758.",
 "V. Novak, “Cerebral vasoregulation in elderly with stroke,” PhysioNet, v1.0.0, 2018, doi:10.13026/C2DW96.",
 "R. Freeman et al., “Consensus statement on the definition of orthostatic hypotension, neurally mediated syncope and the postural tachycardia syndrome,” Clin. Auton. Res., vol. 21, no. 2, pp. 69–72, 2011.",
 "A. L. Goldberger et al., “PhysioBank, PhysioToolkit, and PhysioNet: components of a new research resource for complex physiologic signals,” Circulation, vol. 101, no. 23, pp. e215–e220, 2000.",
 "V. Novak, K. Hu, L. Desrochers, P. Novak, L. Caplan, L. Lipsitz, and M. Selim, “Cerebral flow velocities during daily activities depend on blood pressure in patients with chronic ischemic infarctions,” Stroke, vol. 41, no. 1, pp. 61–66, 2010.",
 "G. Parati, J. E. Ochoa, C. Lombardi, and G. Bilo, “Assessment and management of blood-pressure variability,” Nat. Rev. Cardiol., vol. 10, no. 3, pp. 143–155, 2013.",
 "J. M. Bland and D. G. Altman, “Statistical methods for assessing agreement between two methods of clinical measurement,” Lancet, vol. 327, no. 8476, pp. 307–310, 1986."];
refs.forEach((r,i)=>push(new Paragraph({spacing:{after:80,line:240},alignment:AlignmentType.JUSTIFIED,
  indent:{left:convertInchesToTwip(0.3),hanging:convertInchesToTwip(0.3)},
  children:[new TextRun({text:`[${i+1}] ${r}`,font:FONT,size:20})]})));

const doc = new Document({styles:{default:{document:{run:{font:FONT,size:22}}}},
  sections:[{properties:{page:{size:{width:12240,height:15840},
    margin:{top:1440,bottom:1440,left:1440,right:1440}}},children:body}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync("/tmp/ms/JBHI_manuscript.docx",b);console.log("written",b.length,"bytes");});
