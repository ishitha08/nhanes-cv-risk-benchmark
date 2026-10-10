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
