"""Stage 4b: baseline Cox model (train 1999-2004) evaluated on test 2005-2008. All-cause death."""
from pathlib import Path
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index

ROOT = Path(__file__).resolve().parents[1]
c = pd.read_csv(ROOT / "data" / "interim" / "cohort_features.csv")
base = ["age_years", "male", "sbp", "total_cholesterol", "hdl",
        "smoker_current", "diabetes", "bp_med"]
c = c.dropna(subset=base).copy()
c["time"] = c.PERMTH_EXM.clip(upper=120)                      # administrative censoring at 10 years
c["event"] = c.death_10y
c["log_age"] = np.log(c.age_years); c["log_tc"] = np.log(c.total_cholesterol)
c["log_hdl"] = np.log(c.hdl);       c["log_sbp"] = np.log(c.sbp)
cols = ["log_age", "male", "log_sbp", "log_tc", "log_hdl", "smoker_current", "diabetes", "bp_med"]

tr, te = c[c.split == "train"], c[c.split == "test"]
cph = CoxPHFitter().fit(tr[cols + ["time", "event"]], "time", "event")
print(cph.summary[["coef", "exp(coef)", "p"]].round(3).to_string())

for name, d in [("train", tr), ("test", te)]:
    risk = cph.predict_partial_hazard(d[cols])
    print(f"C-index {name}: {concordance_index(d.time, -risk, d.event):.3f}")

# test-set 10-year predicted vs observed mortality (calibration-in-the-large)
p10 = 1 - cph.predict_survival_function(te[cols], times=[119.9]).T.iloc[:, 0]
print(f"\nTest 10y mean predicted risk: {p10.mean():.3f}   observed: {te.event.mean():.3f}")

print("\nProportional hazards check:")
cph.check_assumptions(tr[cols + ["time", "event"]], p_value_threshold=0.01, show_plots=False)
