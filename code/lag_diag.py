"""Exploratory characterisation of the SHIFT class (not a pre-specified hypothesis).

For every BA, per local calendar year and per local calendar month: MAPE of the forecast
against reported demand when the forecast is shifted by k hours, k in -3..3 (forecast at
t+k paired with demand at t; k = -1 means the forecast row one hour earlier matches the
demand, i.e. the forecast is stamped one hour early). Hours with a non-positive value or a
value outside [0.3, 2] x the 168-hour rolling median of demand are removed from both series
(the NONPOS, OVER and SPIKE classes). Writes out/lag_diag.json and out/lag_monthly.csv.
Run from the repository root: python -I code/lag_diag.py
"""
import json

import numpy as np
import pandas as pd

d = pd.read_parquet("data/eia930_all.parquet", columns=["ba", "date", "utc_end", "forecast", "demand"])
d = d[(d["date"] >= "2016-01-01") & (d["date"] <= "2026-09-30")]
T = pd.read_csv("out/ba_quality_table.csv", index_col=0)


def curve(f, y, j, n):
    m = {}
    for k in range(-3, 4):
        jj = j[(j + k >= 0) & (j + k < n)]
        ok = np.isfinite(f[jj + k]) & np.isfinite(y[jj])
        if ok.sum() >= (1000 if len(j) > 2000 else 200):
            m[k] = float(np.mean(np.abs(f[jj + k][ok] - y[jj][ok]) / y[jj][ok]) * 100)
    return m


res, monthly = {}, []
for ba in T.index:
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    f, y = g["forecast"].copy(), g["demand"].copy()
    for x in (f, y):
        x[(x <= 0) | (x > 2 * ref) | (x < 0.3 * ref)] = np.nan
    f, y = f.values, y.values
    ld = g["date"]
    yr = ld.dt.year.values
    ym = (ld.dt.year * 100 + ld.dt.month).values
    res[ba] = {}
    for Y in range(2016, 2027):
        m = curve(f, y, np.where(yr == Y)[0], len(g))
        if 0 in m:
            kb = min(m, key=m.get)
            res[ba][Y] = {"best": kb, "mape0": m[0], "mape_best": m[kb], "mape": m}
    for M in np.unique(ym[np.isfinite(ym)]):
        m = curve(f, y, np.where(ym == M)[0], len(g))
        if 0 in m:
            kb = min(m, key=m.get)
            monthly.append({"ba": ba, "ym": int(M), "best": kb, "mape0": m[0], "mape_best": m[kb],
                            "mape_m1": m.get(-1, np.nan), "mape_p1": m.get(1, np.nan)})
json.dump(res, open("out/lag_diag.json", "w"), indent=1)
pd.DataFrame(monthly).to_csv("out/lag_monthly.csv", index=False)
off = {b: [y for y, v in r.items() if v["best"] != 0 and v["mape_best"] <= 0.9 * v["mape0"]] for b, r in res.items()}
print({b: v for b, v in off.items() if v})
