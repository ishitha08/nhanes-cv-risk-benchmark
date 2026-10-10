"""Load and inspect the NCHS public-use Linked Mortality Files (NHANES 1999-2008).

Column positions come from NCHS's own R_ReadInProgramAllSurveys.R
(1-based inclusive there; converted here to 0-based half-open for pandas).
Only fields needed for outcome construction are read. DIABETES / HYPERTEN are
death-certificate-derived and must never be used as model features.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
CYCLES = ["1999_2000", "2001_2002", "2003_2004", "2005_2006", "2007_2008"]
COLSPECS = {
    "seqn": (0, 6),
    "eligstat": (14, 15),
    "mortstat": (15, 16),
    "ucod_leading": (16, 19),
    "permth_int": (42, 45),
    "permth_exm": (45, 48),
}
HEART_DISEASE = "001"  # UCOD_LEADING code for "Diseases of heart (054-068)"
TEN_YEARS_MONTHS = 120


def load_cycle(cycle: str) -> pd.DataFrame:
    path = RAW / f"NHANES_{cycle}_MORT_2019_PUBLIC.dat"
    df = pd.read_fwf(
        path,
        colspecs=list(COLSPECS.values()),
        names=list(COLSPECS),
        dtype=str,  # keeps "001" intact; numeric conversion is explicit below
        na_values=["."],
    )
    for col in ["seqn", "eligstat", "mortstat", "permth_int", "permth_exm"]:
        df[col] = pd.to_numeric(df[col], errors="raise")  # raise on unexpected text
    df["ucod_leading"] = df["ucod_leading"].str.strip()
    df.insert(0, "cycle", cycle)

    assert df["seqn"].is_unique, f"{cycle}: duplicate SEQN"
    assert df["eligstat"].isin([1, 2, 3]).all(), f"{cycle}: unexpected ELIGSTAT"
    assert df["mortstat"].dropna().isin([0, 1]).all(), f"{cycle}: unexpected MORTSTAT"
    return df


def load_all() -> pd.DataFrame:
    return pd.concat([load_cycle(c) for c in CYCLES], ignore_index=True)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    e = df[df["eligstat"] == 1].copy()
    e["death"] = e["mortstat"] == 1
    e["death_10y"] = e["death"] & (e["permth_exm"] <= TEN_YEARS_MONTHS)
    e["heart_death"] = e["death"] & (e["ucod_leading"].fillna("") == HEART_DISEASE)
    e["cause_missing"] = e["death"] & e["ucod_leading"].isna()
    e["no_exam_followup"] = e["permth_exm"].isna()
    e["alive_short_followup"] = (~e["death"]) & (e["permth_exm"] < TEN_YEARS_MONTHS)

    summary = e.groupby("cycle").agg(
        adults_eligible=("seqn", "size"),
        deaths=("death", "sum"),
        deaths_within_120m=("death_10y", "sum"),
        heart_disease_deaths=("heart_death", "sum"),
        deaths_cause_missing=("cause_missing", "sum"),
        no_exam_followup=("no_exam_followup", "sum"),
        alive_followup_lt_120m=("alive_short_followup", "sum"),
        median_followup_exm_months=("permth_exm", "median"),
    )
    total = summary.drop(columns="median_followup_exm_months").sum()
    total["median_followup_exm_months"] = e["permth_exm"].median()
    summary.loc["TOTAL"] = total
    return summary


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)
    data = load_all()

    print("\nLinkage eligibility by cycle (1=eligible, 2=under 18, 3=ineligible):")
    print(data.groupby("cycle")["eligstat"].value_counts().unstack(fill_value=0))

    # Sanity: alive participants should carry no cause of death
    alive_with_cause = ((data["mortstat"] == 0) & data["ucod_leading"].notna()).sum()
    print(f"\nAlive participants with a cause-of-death code (expect 0): {alive_with_cause}")

    table = summarise(data)
    print("\nEvent counts (all eligible adults, before any age/exam/baseline-disease filters):")
    print(table.to_string())

    REPORTS.mkdir(exist_ok=True)
    table.to_csv(REPORTS / "lmf_event_counts.csv")
    print(f"\nSaved {REPORTS / 'lmf_event_counts.csv'}")
