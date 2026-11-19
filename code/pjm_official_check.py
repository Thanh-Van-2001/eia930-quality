"""Amendment 2, item 1 (exploratory, after independent review; PLAN.md): which PJM series carries
the one-hour offset?

PJM's official summer coincident peaks (5CP: date, hour ending EPT, MW), 2022 to 2026, transcribed
from PJM's reports "Summer YYYY Peaks and 5CPs" (PJM Resource Adequacy Planning). The reports are not
redistributed here; fetch them from PJM and compare with the SHA-256 below.
  2022 https://www.pjm.com/-/media/planning/res-adeq/load-forecast/summer-2022-peaks-and-5cps.ashx
       f64030d88bb60d8f214bd7a3bc87c3549298810526d886970380183c0cc1f705
  2023 https://www.pjm.com/-/media/planning/res-adeq/load-forecast/summer-2023-peaks-and-5cps.ashx
       45f23453a8bbb029a123b3fed481fa35d7ed2c3a9ceb3c160bc71ab98d6f98dd
  2024 https://www.pjm.com/-/media/planning/res-adeq/load-forecast/summer-2024-peaks-and-5cps.ashx
       9e2ce72ebda415f20453b67e2bebfce84dc9c4daf21e1d16f866c534f183a76e
  2025 https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/summer-2025-peaks-and-5cps.pdf
       07e23468ad97607b8894ce3650e4f8d17f51960975d57455bdaa667a59d8f231
  2026 https://www.pjm.com/-/media/DotCom/planning/res-adeq/load-forecast/summer-2026-peaks-and-5cps.pdf
       f15db6c4c73d8ef4f215bd46ffbee9e2dc5469f49ee6d1c23de1253e1df1cac5

For each official CP day: the hour (EIA-930 "Hour Number", hour ending, local prevailing time) of the
daily maximum of reported demand, of the forecast as published, and of the forecast delayed by one
hour (forecast at t-1 paired with demand at t, the realignment k = -1). Gross errors are removed as in
code/lag_diag.py. From out/lag_monthly.csv: PJM's best monthly shift since February 2019 in
standard-time months (December to February) and daylight-time months (June to August).
Writes out/pjm_official_check.json. Run from the repository root: python -I code/pjm_official_check.py
"""
import json

import numpy as np
import pandas as pd

# (date, hour ending EPT, MW) of the RTO 5CP, as listed in each report's "RTO Coincident Peaks (5CP)" table
OFFICIAL = {
    2022: [("2022-07-20", 18, 147334), ("2022-07-21", 17, 145144), ("2022-07-22", 18, 144246),
           ("2022-08-08", 16, 143101), ("2022-08-03", 18, 142112)],
    2023: [("2023-07-27", 18, 146843), ("2023-09-05", 17, 146167), ("2023-07-28", 18, 144452),
           ("2023-09-06", 17, 141355), ("2023-07-05", 18, 137806)],
    2024: [("2024-07-16", 18, 152307), ("2024-07-15", 18, 151103), ("2024-08-01", 18, 148240),
           ("2024-06-21", 18, 147271), ("2024-08-28", 18, 147249)],
    2025: [("2025-06-23", 18, 160649), ("2025-06-24", 18, 160629), ("2025-07-29", 18, 156035),
           ("2025-06-25", 15, 152903), ("2025-07-28", 18, 151525)],
    2026: [("2026-07-02", 18, 165910), ("2026-07-01", 18, 161118), ("2026-07-15", 18, 158408),
           ("2026-07-16", 18, 153226), ("2026-09-01", 18, 152035)],
}

d = pd.read_parquet("data/eia930_all.parquet", columns=["ba", "date", "hour", "utc_end", "forecast", "demand"])
g = d[d["ba"] == "PJM"].set_index("utc_end").sort_index()
G = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
ref = G["demand"].where(G["demand"] > 0).rolling(168, center=True, min_periods=24).median()
for c in ("demand", "forecast"):
    G.loc[(G[c] <= 0) | (G[c] > 2 * ref) | (G[c] < 0.3 * ref), c] = np.nan
G["forecast_delayed"] = G["forecast"].shift(1)  # forecast at t-1 paired with demand at t (k = -1)


def peak_hour(day, col):
    x = G.loc[G["date"] == day].set_index("hour")[col]
    return int(x.idxmax()) if x.notna().any() else None


rows = []
for yr, lst in OFFICIAL.items():
    for ds, he, mw in lst:
        day = pd.Timestamp(ds)
        x = G.loc[G["date"] == day].set_index("hour")
        rows.append({"year": yr, "date": ds, "official_he": he, "official_mw": mw, "n_hours": int(len(x)),
                     "demand_peak_he": peak_hour(day, "demand"), "forecast_peak_he": peak_hour(day, "forecast"),
                     "forecast_delayed_peak_he": peak_hour(day, "forecast_delayed"),
                     "demand_at_official_he": float(x["demand"].get(he, np.nan))})
R = pd.DataFrame(rows)
res = {"n_days": int(len(R)),
       "demand_at_official": int((R["demand_peak_he"] == R["official_he"]).sum()),
       "demand_within_1h": int(((R["demand_peak_he"] - R["official_he"]).abs() <= 1).sum()),
       "forecast_at_official": int((R["forecast_peak_he"] == R["official_he"]).sum()),
       "forecast_before_official": int((R["forecast_peak_he"] < R["official_he"]).sum()),
       "forecast_delayed_at_official": int((R["forecast_delayed_peak_he"] == R["official_he"]).sum()),
       "forecast_minus_official_mean_h": float((R["forecast_peak_he"] - R["official_he"]).mean()),
       "forecast_delayed_minus_official_mean_h": float((R["forecast_delayed_peak_he"] - R["official_he"]).mean()),
       "demand_minus_official_mean_h": float((R["demand_peak_he"] - R["official_he"]).mean()),
       "demand_over_official_mw_median": float((R["demand_at_official_he"] / R["official_mw"]).median()),
       "demand_over_official_mw_min": float((R["demand_at_official_he"] / R["official_mw"]).min()),
       "demand_over_official_mw_max": float((R["demand_at_official_he"] / R["official_mw"]).max())}
LM = pd.read_csv("out/lag_monthly.csv")
P = LM[(LM["ba"] == "PJM") & (LM["ym"] >= 201902)].copy()
P["flag"] = (P["best"] != 0) & (P["mape_best"] <= 0.9 * P["mape0"])
for lab, months in (("std_DecFeb", (12, 1, 2)), ("dst_JunAug", (6, 7, 8))):
    s = P[P["ym"].mod(100).isin(months)]
    res[f"season_{lab}"] = {"months": int(len(s)), "best_minus1": int((s["best"] == -1).sum()),
                            "flagged_minus1": int(((s["best"] == -1) & s["flag"]).sum())}
res["rows"] = rows
json.dump(res, open("out/pjm_official_check.json", "w"), indent=1)
print({k: v for k, v in res.items() if k != "rows"})
print(R.to_string())
