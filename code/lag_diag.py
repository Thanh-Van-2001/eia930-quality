"""Exploratory characterisation of the SHIFT class (not a pre-specified hypothesis).

For every BA and calendar year: MAPE of the forecast against reported demand when the
forecast is shifted by k hours, k in -3..3 (forecast at t+k paired with demand at t), on
hours where both values are present and demand > 0, after the main screen (classes 2-5
removed from both series). Writes out/lag_diag.json.
Run from the repository root: python -I code/lag_diag.py
"""
import json

import numpy as np
import pandas as pd

d = pd.read_parquet("data/eia930_all.parquet", columns=["ba", "date", "utc_end", "forecast", "demand"])
d = d[(d["date"] >= "2016-01-01") & (d["date"] <= "2026-09-30")]
T = pd.read_csv("out/ba_quality_table.csv", index_col=0)
res = {}
for ba in T.index:
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    f, y = g["forecast"].copy(), g["demand"].copy()
    for x in (f, y):
        x[(x <= 0) | (x > 2 * ref) | (x < 0.3 * ref)] = np.nan
    f, y, yr = f.values, y.values, g.index.year
    res[ba] = {}
    for Y in range(2016, 2027):
        j = np.where(yr == Y)[0]
        m = {}
        for k in range(-3, 4):
            jj = j[(j + k >= 0) & (j + k < len(g))]
            ok = np.isfinite(f[jj + k]) & np.isfinite(y[jj])
            if ok.sum() >= 1000:
                m[k] = float(np.mean(np.abs(f[jj + k][ok] - y[jj][ok]) / y[jj][ok]) * 100)
        if 0 in m:
            kb = min(m, key=m.get)
            res[ba][Y] = {"best": kb, "mape0": m[0], "mape_best": m[kb], "mape": m}
json.dump(res, open("out/lag_diag.json", "w"), indent=1)
off = {b: [y for y, v in r.items() if v["best"] != 0 and v["mape_best"] <= 0.9 * v["mape0"]] for b, r in res.items()}
print({b: v for b, v in off.items() if v})
