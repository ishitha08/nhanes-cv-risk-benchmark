"""Parse NCHS public-use linked mortality files (2019 follow-up), NHANES 1999-2008.
Column positions are 0-indexed [start, end). VERIFY against NCHS's official read-in program."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mortality"
OUT = ROOT / "data" / "interim"
CYCLES = ["1999_2000", "2001_2002", "2003_2004", "2005_2006", "2007_2008"]
SPECS = {"SEQN": (0, 6), "ELIGSTAT": (14, 15), "MORTSTAT": (15, 16),
         "UCOD_LEADING": (16, 19), "DIABETES": (19, 20), "HYPERTEN": (20, 21),
         "PERMTH_INT": (42, 45), "PERMTH_EXM": (45, 48)}

frames = []
for c in CYCLES:
    df = pd.read_fwf(RAW / f"NHANES_{c}_MORT_2019_PUBLIC.dat", colspecs=list(SPECS.values()),
                     names=list(SPECS), header=None, dtype=str)
    df = df.apply(pd.to_numeric, errors="coerce")
    df["cycle"] = c
    frames.append(df)
    elig = df[df.ELIGSTAT == 1]
    print(f"{c}: rows={len(df)}, eligible={len(elig)}, deaths={int((elig.MORTSTAT == 1).sum())}, "
          f"heart-disease deaths (UCOD 1)={int((elig.UCOD_LEADING == 1).sum())}, "
          f"median exam follow-up (months)={elig.PERMTH_EXM.median()}")

all_df = pd.concat(frames, ignore_index=True)
all_df.to_csv(OUT / "mortality_1999_2008.csv", index=False)
print("\nELIGSTAT counts:\n", all_df.ELIGSTAT.value_counts(dropna=False))
print("\nMORTSTAT among eligible:\n", all_df[all_df.ELIGSTAT == 1].MORTSTAT.value_counts(dropna=False))
