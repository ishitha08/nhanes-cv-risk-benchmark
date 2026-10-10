"""Stage 3: merge NHANES 1999-2008 with linked mortality, apply pre-specified exclusions,
report cohort flow, 10-year event counts and missingness. No feature engineering yet."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nhanes"
vm = pd.read_csv(ROOT / "reports" / "nhanes_variable_map.csv").fillna("")
mort = pd.read_csv(ROOT / "data" / "interim" / "mortality_1999_2008.csv")

frames = []
for cycle, g in vm[vm.key != "SEQN"].groupby("cycle"):
    by_file = {}
    for _, r in g.iterrows():
        by_file.setdefault(r.files.split("|")[0], []).append((r.variable, r.key))
    df = None
    for stem, pairs in by_file.items():
        path = next(p for p in (RAW / cycle).iterdir() if p.stem == stem)
        d, _ = pyreadstat.read_xport(str(path), usecols=["SEQN"] + [v for v, _ in pairs],
                                     encoding="ISO-8859-1")
        d = d.rename(columns={v: k for v, k in pairs}).drop_duplicates("SEQN")
        df = d if df is None else df.merge(d, on="SEQN", how="outer")
    df["cycle"] = cycle
    frames.append(df)

d = pd.concat(frames, ignore_index=True)
d["SEQN"] = d["SEQN"].astype(int)
d = d.merge(mort, on=["SEQN", "cycle"], how="left")

for c in ["chf", "chd", "angina", "heart_attack", "stroke"]:
    d[c] = d[c].where(d[c].isin([1, 2]))          # 7 = refused, 9 = don't know -> missing

steps = [("All NHANES 1999-2008 participants", d.SEQN.notna())]
steps.append(("Eligible for mortality linkage (ELIGSTAT=1)", d.ELIGSTAT == 1))
steps.append(("Examined (exam weight > 0)", d.exam_weight_2yr > 0))
steps.append(("Age 40-79", d.age_years.between(40, 79)))
steps.append(("No self-reported prior CHF/CHD/angina/MI/stroke",
              ~(d[["chf", "chd", "angina", "heart_attack", "stroke"]] == 1).any(axis=1)))

mask = pd.Series(True, index=d.index)
print("COHORT FLOW")
for label, m in steps:
    mask &= m
    print(f"  {label}: {int(mask.sum())}")
c = d[mask].copy()

c["death_10y"] = ((c.MORTSTAT == 1) & (c.PERMTH_EXM <= 120)).astype(int)
c["hd_death_10y"] = ((c.MORTSTAT == 1) & (c.UCOD_LEADING == 1) & (c.PERMTH_EXM <= 120)).astype(int)
c["censored_before_10y"] = ((c.MORTSTAT == 0) & (c.PERMTH_EXM < 120)).astype(int)
c["split"] = np.where(c.cycle.isin(["1999_2000", "2001_2002", "2003_2004"]), "train", "test")

print("\nEVENTS (10-year, from exam date)")
print(c.groupby("split").agg(n=("SEQN", "size"), deaths_10y=("death_10y", "sum"),
                             hd_deaths_10y=("hd_death_10y", "sum"),
                             censored_early=("censored_before_10y", "sum")).to_string())
print("\nBy cycle:")
print(c.groupby("cycle").agg(n=("SEQN", "size"), deaths_10y=("death_10y", "sum"),
                             hd_deaths_10y=("hd_death_10y", "sum")).to_string())

core = ["sbp_1", "total_cholesterol", "hdl", "smoked_100_cigs", "current_smoker",
        "diabetes_told", "told_high_bp", "bp_med_now", "bmi", "hba1c", "creatinine", "crp"]
print("\nMISSING % among cohort:")
print((c[core].isna().mean() * 100).round(1).to_string())

c.to_csv(ROOT / "data" / "interim" / "cohort_stage3.csv", index=False)
print(f"\nSaved cohort_stage3.csv ({len(c)} rows)")
