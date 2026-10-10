# Cardiovascular Risk Benchmarking on NHANES (research prototype)

**Not a medical device or diagnostic tool.**

## Research question
Among US adults aged 40-79 with no prior cardiovascular disease at their NHANES exam, do ML survival models predict 10-year mortality better than a Cox model on traditional risk-factor variables, in discrimination, calibration, or across demographic subgroups? Do near-equally accurate models explain their predictions consistently?

## Pre-specified design (committed before any results)
- Data: NHANES 1999-2008 exam/lab/questionnaire files + NCHS public-use Linked Mortality Files (2019), follow-up to 2019-12-31
- Primary outcome: all-cause death within 10 years (MORTSTAT, PERMTH_EXM). Secondary: heart-disease death (UCOD_LEADING=001), noisier because follow-up time/cause were perturbed for select records
- Split: train 1999-2004 cycles, temporal held-out test 2005-2008 cycles
- Baseline: Cox on age, sex, SBP, total cholesterol, HDL, smoking, diabetes, BP-medication status
- Models: Cox, penalised Cox, random survival forest, gradient-boosted survival
- Metrics: C-index, time-dependent AUC, Brier score, calibration curves; subgroup breakdowns
- Meaningful-improvement margin (C-index): 0.01

## Hypotheses
- H1: ML gains in C-index over baseline are smaller than the margin above
- H2: any discrimination gain does not carry over to calibration on the held-out cycles
- H3: performance and calibration differ across age, sex and race/ethnicity subgroups; ML does not close the gaps
- H4: feature-importance rankings differ more across near-equally accurate models than across bootstrap resamples of one model

## Data attribution
National Center for Health Statistics. NHANES public-use linked mortality files (2019) and NHANES data, CDC/NCHS. Analyses and conclusions are the author's, not NCHS's.

## Amendments (after reading NCHS methodology documentation; before any modelling)
- Follow-up is truncated at 120 months from the exam date: deaths after month 120 count as survivors at 10 years.
- Weights: NCHS provides no linkage-eligibility-adjusted weights for NHANES. Ineligible adults are about 0.1% of the sample (30 of 28,852), so no adjustment is applied. Pooled analyses divide the 2-year weights by the number of cycles pooled (NCHS recommendation).
- H3 caveat: mortality ascertainment via NDI linkage may differ by race/ethnicity. NCHS's own 2015-vs-2019 linkage comparison moves the NHANES Mexican American hazard ratio from 1.00 to 0.67. Subgroup over-prediction cannot be separated from missed deaths in that subgroup and will be reported with this limitation.
- The public-use files substitute synthetic follow-up time or cause of death for select records; the share is not published in the documents reviewed. Heart-disease death is secondary only. A horizon sensitivity check at 5, 8 and 10 years will test the stability of the primary outcome.
