"""Discover and verify the NHANES 1999-2008 files/variables needed for the CV-risk benchmark.

File names are read from CDC's own listing pages (not guessed). Only matched .xpt files
are downloaded; variable names/labels are read from the XPT headers themselves.
"""
import html
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import pyreadstat
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nhanes"
REPORTS = ROOT / "reports"
CYCLE_YEARS = {"1999_2000": 1999, "2001_2002": 2001, "2003_2004": 2003, "2005_2006": 2005, "2007_2008": 2007}
LISTING = "https://wwwn.cdc.gov/nchs/nhanes/search/datapage.aspx?Component={component}&CycleBeginYear={year}"
HEADERS = {"User-Agent": "Mozilla/5.0 (research script; nhanes-cv-risk-benchmark)"}

# component -> lowercase title keywords; a file is downloaded if its title contains any of them
WANTED_TITLES = {
    "Demographics": ["demographic"],
    "Examination": ["blood pressure", "body measures"],
    "Laboratory": ["cholesterol", "hdl", "glycohemoglobin", "glycated", "biochemistry", "c-reactive"],
    "Questionnaire": ["medical conditions", "smoking - cigarette", "diabetes", "blood pressure & cholesterol"],
}

# analysis key -> acceptable variable names (first one found wins)
WANTED_VARS = {
    "SEQN": ["SEQN"],
    "age_years": ["RIDAGEYR"],
    "sex": ["RIAGENDR"],
    "race_ethnicity": ["RIDRETH1"],
    "exam_weight_2yr": ["WTMEC2YR"],
    "psu": ["SDMVPSU"],
    "strata": ["SDMVSTRA"],
    "education_adult": ["DMDEDUC2"],
    "income_poverty_ratio": ["INDFMPIR"],
    "sbp_1": ["BPXSY1"], "sbp_2": ["BPXSY2"], "sbp_3": ["BPXSY3"], "sbp_4": ["BPXSY4"],
    "dbp_1": ["BPXDI1"], "dbp_2": ["BPXDI2"], "dbp_3": ["BPXDI3"], "dbp_4": ["BPXDI4"],
    "bmi": ["BMXBMI"],
    "waist_cm": ["BMXWAIST"],
    "total_cholesterol": ["LBXTC"],
    "hdl": ["LBDHDD", "LBDHDL", "LBXHDD"],
    "hba1c": ["LBXGH"],
    "creatinine": ["LBXSCR", "LBDSCR"],
    "crp": ["LBXCRP"],
    "chf": ["MCQ160B"],
    "chd": ["MCQ160C"],
    "angina": ["MCQ160D"],
    "heart_attack": ["MCQ160E"],
    "stroke": ["MCQ160F"],
    "smoked_100_cigs": ["SMQ020"],
    "current_smoker": ["SMQ040"],
    "diabetes_told": ["DIQ010"],
    "told_high_bp": ["BPQ020"],
    "bp_med_ever": ["BPQ040A"],
    "bp_med_now": ["BPQ050A"],
}


def parse_listing(component: str, year: int) -> dict[str, str]:
    """Return {file title: .xpt url} from CDC's listing page."""
    url = LISTING.format(component=component, year=year)
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    files: dict[str, str] = {}
    for block in re.findall(r"<tr[^>]*>(.*?)</tr>", resp.text, flags=re.S | re.I):
        link = re.search(r'href="([^"]+\.xpt)"', block, flags=re.I)
        cell = re.search(r"<td[^>]*>(.*?)</td>", block, flags=re.S | re.I)
        if link and cell:
            title = html.unescape(re.sub(r"<[^>]+>", "", cell.group(1))).strip()
            files[title] = urljoin(url, link.group(1))
    if not files:
        sys.exit(f"No .xpt links parsed from {url}")
    return files


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    if not resp.content.startswith(b"HEADER RECORD"):
        sys.exit(f"{url} did not return an XPT file (got {resp.content[:40]!r})")
    dest.write_bytes(resp.content)
    time.sleep(0.3)  # be polite to CDC's servers


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    file_rows: list[dict] = []
    var_rows: list[dict] = []

    for cycle, year in CYCLE_YEARS.items():
        found_in: dict[str, list[tuple[str, str]]] = {}
        for component, keywords in WANTED_TITLES.items():
            for title, url in parse_listing(component, year).items():
                if not any(k in title.lower() for k in keywords):
                    continue
                dest = RAW / cycle / Path(url).name
                download(url, dest)
                _, meta = pyreadstat.read_xport(str(dest), metadataonly=True, encoding="ISO-8859-1")
                file_rows.append({"cycle": cycle, "component": component, "title": title,
                                  "file": dest.name, "url": url})
                for name, label in zip(meta.column_names, meta.column_labels):
                    found_in.setdefault(name.upper(), []).append((dest.stem, label or ""))
        for key, alternatives in WANTED_VARS.items():
            hit = next((a for a in alternatives if a in found_in), None)
            if hit is None:
                var_rows.append({"cycle": cycle, "key": key, "variable": "", "files": "", "label": ""})
            else:
                stems = sorted({s for s, _ in found_in[hit]})
                var_rows.append({"cycle": cycle, "key": key, "variable": hit,
                                 "files": "|".join(stems), "label": found_in[hit][0][1]})

    files_df = pd.DataFrame(file_rows)
    vars_df = pd.DataFrame(var_rows)
    files_df.to_csv(REPORTS / "nhanes_files_selected.csv", index=False)
    vars_df.to_csv(REPORTS / "nhanes_variable_map.csv", index=False)

    vars_df["cell"] = vars_df.apply(
        lambda r: "MISSING" if not r["variable"] else f'{r["files"]}:{r["variable"]}', axis=1)
    pivot = vars_df.pivot(index="key", columns="cycle", values="cell").reindex(list(WANTED_VARS))

    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 60)
    print("\nFiles downloaded per cycle:")
    print(files_df.groupby("cycle")["file"].apply(lambda s: ", ".join(s)).to_string())
    print("\nWhere each wanted variable lives (file:VARIABLE) in each cycle:")
    print(pivot.to_string())
    labels = vars_df[vars_df["variable"] != ""].drop_duplicates(["key", "variable"])[["key", "variable", "label"]]
    print("\nLabels (as written in the files):")
    print(labels.to_string(index=False))
    missing = vars_df[vars_df["variable"] == ""]
    print(f"\nMISSING variable-cycle pairs: {len(missing)}")


if __name__ == "__main__":
    main()
