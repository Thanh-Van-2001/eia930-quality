"""Extract every balancing authority from the EIA-930 six-month BALANCE files.

Keeps: authority, local date, hour number, local and UTC end time, Demand
Forecast, Demand, Demand (Imputed), Demand (Adjusted). Values are read as text
and parsed after removing thousands separators; unparseable non-empty cells are
counted, not dropped silently. Writes data/eia930_all.parquet and
data/extract_all_log.json.
Run: python -I extract_all.py <raw_dir> <out_dir>
"""
import glob
import json
import os
import sys

import pandas as pd

RAW, OUT = sys.argv[1], sys.argv[2]
COLS = {"Balancing Authority": "ba", "Data Date": "date", "Hour Number": "hour",
        "Local Time at End of Hour": "local_end", "UTC Time at End of Hour": "utc_end",
        "Demand Forecast (MW)": "forecast", "Demand (MW)": "demand",
        "Demand (MW) (Imputed)": "demand_imp", "Demand (MW) (Adjusted)": "demand_adj"}
NUM = ["forecast", "demand", "demand_imp", "demand_adj"]
parts, log = [], {"files": [], "parse_errors": {c: 0 for c in NUM}}
for f in sorted(glob.glob(os.path.join(RAW, "EIA930_BALANCE_*.csv"))):
    df = pd.read_csv(f, usecols=lambda c: c in COLS, dtype=str, low_memory=False).rename(columns=COLS)
    for c in NUM:
        if c not in df:
            df[c] = None
        s = df[c].str.replace(",", "", regex=False).str.strip()
        v = pd.to_numeric(s, errors="coerce")
        log["parse_errors"][c] += int((s.notna() & (s != "") & v.isna()).sum())
        df[c] = v
    df["hour"] = pd.to_numeric(df["hour"], errors="coerce")
    log["files"].append({"file": os.path.basename(f), "rows": int(len(df)),
                         "missing_cols": [c for c in COLS.values() if df[c].isna().all()]})
    parts.append(df)
d = pd.concat(parts, ignore_index=True)
d["date"] = pd.to_datetime(d["date"], format="%m/%d/%Y", errors="coerce")
for c in ("utc_end", "local_end"):
    d[c] = pd.to_datetime(d[c], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
log["bad_timestamps"] = int(d["utc_end"].isna().sum())
dups = int(d.duplicated(["ba", "utc_end"]).sum())
d = d.dropna(subset=["utc_end"]).drop_duplicates(["ba", "utc_end"], keep="last").sort_values(["ba", "utc_end"])
log["duplicates_dropped"] = dups
log["rows"] = int(len(d))
d.to_parquet(os.path.join(OUT, "eia930_all.parquet"), index=False)
cov = d.groupby(["ba", d["date"].dt.year]).agg(rows=("demand", "size"), demand=("demand", lambda x: x.notna().mean()),
                                                forecast=("forecast", lambda x: x.notna().mean()))
cov.round(3).to_csv(os.path.join(OUT, "coverage_ba_year.csv"))
json.dump(log, open(os.path.join(OUT, "extract_all_log.json"), "w"), indent=1)
print(len(d), "rows;", dups, "duplicates;", log["parse_errors"])
