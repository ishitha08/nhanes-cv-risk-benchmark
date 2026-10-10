"""Stage 4a: recode survey codes, derive baseline predictors, sanity-check. Fits nothing."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
c = pd.read_csv(ROOT / "data" / "interim" / "cohort_stage3.csv")

# 7 = refused, 9 = don't know -> missing
for col in ["smoked_100_cigs", "current_smoker", "diabetes_told", "told_high_bp",
            "bp_med_ever", "bp_med_now"]:
    c[col] = c[col].where(~c[col].isin([7, 9]))

c["sbp"] = c[[f"sbp_{i}" for i in range(1, 5)]].mean(axis=1)
c["dbp"] = c[[f"dbp_{i}" for i in range(1, 5)]].mean(axis=1)
c["male"] = (c.sex == 1).astype(int)

# current smoker: SMQ040 is only asked of people who smoked >= 100 cigarettes
c["smoker_current"] = np.select(
    [c.current_smoker.isin([1, 2]), (c.smoked_100_cigs == 2) | (c.current_smoker == 3)],
    [1, 0], default=np.nan)
# diabetes (self-report): yes=1; no or borderline=0
c["diabetes"] = np.select([c.diabetes_told == 1, c.diabetes_told.isin([2, 3])],
                          [1, 0], default=np.nan)
# BP medication: BPQ050A is only asked of people who reported taking a prescription
c["bp_med"] = np.select(
    [c.bp_med_now == 1, (c.told_high_bp == 2) | (c.bp_med_ever == 2) | (c.bp_med_now == 2)],
    [1, 0], default=np.nan)
# HDL method differs by cycle (LBDHDL 1999-2002; direct HDL from 2003)
c["hdl_direct_era"] = (~c.cycle.isin(["1999_2000", "2001_2002"])).astype(int)

base = ["age_years", "male", "sbp", "total_cholesterol", "hdl",
        "smoker_current", "diabetes", "bp_med"]
print("MISSING % after derivation:")
print((c[base].isna().mean() * 100).round(1).to_string())

cc = c[base].notna().all(axis=1)
print("\nComplete cases on baseline predictors:")
print(c.assign(cc=cc).groupby("split").agg(n=("SEQN", "size"), complete=("cc", "sum")).to_string())
print("Deaths among complete cases:", c[cc].groupby("split").death_10y.sum().to_dict())

print("\nRANGES:")
print(c[["age_years", "sbp", "dbp", "total_cholesterol", "hdl", "bmi", "hba1c"]]
      .describe().loc[["min", "50%", "max"]].round(1).to_string())
print("\nMEANS by cycle (look for step changes, esp. HDL):")
print(c.groupby("cycle")[["hdl", "sbp", "total_cholesterol", "hba1c"]].mean().round(1).to_string())
print("\nPREVALENCE by cycle:")
print(c.groupby("cycle")[["smoker_current", "diabetes", "bp_med"]].mean().round(3).to_string())

c.to_csv(ROOT / "data" / "interim" / "cohort_features.csv", index=False)
print(f"\nSaved cohort_features.csv ({len(c)} rows)")
