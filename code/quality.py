"""Recording errors in EIA-930 demand and forecast series (PLAN.md). Writes out/results.json,
out/ba_quality_table.csv, out/ba_year.csv. Run from the repository root:
    python -I code/quality.py            full run
    python -I code/quality.py --check    pipeline check (CISO and PJM, 2018 only) -> out_check/
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

CHECK = "--check" in sys.argv
OUT = "out_check" if CHECK else "out"
os.makedirs(OUT, exist_ok=True)
START, END = "2016-01-01", "2026-09-30"
CLASSES = ["NONPOS", "OVER", "SPIKE", "FLAT", "COPY", "SHIFT"]
SHARED = ["NONPOS", "OVER", "SPIKE", "FLAT"]
VARIANTS = {"main": (2.0, 0.3, 6), "spike_loose": (1.5, 0.5, 6), "spike_tight": (3.0, 0.2, 6),
            "flat4": (2.0, 0.3, 4), "flat12": (2.0, 0.3, 12)}

d = pd.read_parquet("data/eia930_all.parquet",
                    columns=["ba", "date", "hour", "utc_end", "forecast", "demand", "demand_adj"])
d = d[(d["date"] >= START) & (d["date"] <= END)]
if CHECK:
    d = d[d["ba"].isin(["CISO", "PJM"]) & (d["date"].dt.year == 2018)]
both = d["demand"].notna() & d["forecast"].notna()
cov = both.groupby([d["ba"], d["date"].dt.year]).mean()
yrs80 = (cov >= 0.8).groupby(level=0).sum()
med = d["demand"].where(d["demand"] > 0).groupby(d["ba"]).median()
sample = sorted(yrs80[yrs80 >= (1 if CHECK else 8)].index)


def size_group(mw):
    return "small" if mw < 500 else ("mid" if mw <= 5000 else "large")


def runs(x, minlen):
    """Boolean: hour belongs to a run of >= minlen identical consecutive non-missing values."""
    v = x.values
    same = np.r_[False, (v[1:] == v[:-1]) & ~np.isnan(v[1:]) & ~np.isnan(v[:-1])]
    grp = np.cumsum(~same)
    n = pd.Series(grp).map(pd.Series(grp).value_counts()).values
    return (n >= minlen) & ~np.isnan(v)


def classify(g, hi, lo, flat):
    """Return a frame of class labels ('' = clean, 'MISS', ...) for demand and forecast."""
    ref = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    lab = {}
    for c in ("demand", "forecast"):
        x = g[c]
        L = pd.Series("", index=g.index, dtype=object)
        L[x.isna()] = "MISS"
        L[(L == "") & (x <= 0)] = "NONPOS"
        L[(L == "") & (x > 10 * ref)] = "OVER"
        L[(L == "") & (((x > hi * ref) & (x <= 10 * ref)) | ((x > 0) & (x < lo * ref)))] = "SPIKE"
        L[(L == "") & runs(x, flat)] = "FLAT"
        lab[c] = L
    f, dm = g["forecast"], g["demand"]
    eq = (f == dm) & f.notna()
    # COPY: run of >= 24 consecutive hours with forecast == demand
    e = eq.values.astype(int)
    grp = np.cumsum(np.r_[1, (e[1:] != e[:-1]).astype(int)])
    n = pd.Series(grp).map(pd.Series(grp).value_counts()).values
    copy = (e == 1) & (n >= 24)
    L = lab["forecast"]
    L[(L == "") & copy] = "COPY"
    # SHIFT per month: best lag in -3..3 on hours clean in both series
    clean = (lab["demand"] == "") & (L == "")
    month = g.index.to_period("M")
    shift = np.zeros(len(g), dtype=bool)
    shift_k = np.zeros(len(g), dtype=int)
    fv, dv, cv = f.values, dm.values, clean.values
    for mth in np.unique(month):
        j = np.where(month == mth)[0]
        maes = {}
        for k in range(-3, 4):
            jj = j[(j + k >= 0) & (j + k < len(g))]
            ok = cv[jj] & cv[jj + k]
            if ok.sum() >= 100:
                maes[k] = np.mean(np.abs(fv[jj + k][ok] - dv[jj][ok]))
        if 0 in maes and maes:
            kb = min(maes, key=maes.get)
            if kb != 0 and maes[kb] <= 0.8 * maes[0]:
                shift[j] = True
                shift_k[j] = kb
    L[(L == "") & shift & f.notna()] = "SHIFT"
    lab["forecast"] = L
    lab["_k"] = pd.Series(shift_k, index=g.index)
    return lab


def changed_by_eia(g):
    a, r = g["demand_adj"], g["demand"]
    return (a.notna() & r.notna() & ((a - r).abs() > 0.5)) | (a.notna() & r.isna())


def mape(f, y, m):
    m = m & f.notna() & y.notna() & (y > 0)
    return float((100 * (f[m] - y[m]).abs() / y[m]).mean()) if m.sum() else np.nan


rows, by, var_rates = [], [], {k: {} for k in VARIANTS}
for ba in sample:
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    G = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    keep = G["date"].notna()
    g = G[keep]
    for vk, (hi, lo, fl) in VARIANTS.items():
        lab = classify(G, hi, lo, fl)
        lab = {k: v[keep] for k, v in lab.items()}
        if vk != "main":
            var_rates[vk][ba] = {s: float(lab[s].isin(SHARED).sum() / (lab[s] != "MISS").sum()) for s in ("demand", "forecast")}
            continue
        Ld, Lf, K = lab["demand"], lab["forecast"], lab["_k"]
    # realigned forecast for SHIFT months (amendment 1): forecast at t+k paired with demand at t
    pos = np.arange(len(G))[keep.values]
    fG = G["forecast"].values
    src = pos + K.values
    okp = (src >= 0) & (src < len(G))
    f_al = pd.Series(np.where(okp, fG[np.clip(src, 0, len(G) - 1)], np.nan), index=g.index)
    eia = changed_by_eia(g)
    yr = g["date"].dt.year
    r = {"ba": ba, "median_mw": float(med[ba]), "size": size_group(med[ba]), "hours": int(len(g))}
    for s, L in (("demand", Ld), ("forecast", Lf)):
        pres = (L != "MISS").sum()
        r[f"{s}_miss"] = float((L == "MISS").mean())
        for c in CLASSES:
            r[f"{s}_{c}"] = float((L == c).sum() / pres) if pres else np.nan
        r[f"{s}_rate"] = float(L.isin(CLASSES).sum() / pres) if pres else np.nan
        r[f"{s}_shared"] = float(L.isin(SHARED).sum() / pres) if pres else np.nan
        for per, m in (("early", yr <= 2019), ("late", yr >= 2023)):
            pm = m & (L != "MISS")
            r[f"{s}_shared_{per}"] = float((L[m].isin(SHARED)).sum() / pm.sum()) if pm.sum() else np.nan
    flagged = Ld.isin(SHARED)
    a_, r_ = g["demand_adj"], g["demand"]
    eia_val = a_.notna() & r_.notna() & ((a_ - r_).abs() > 0.5)
    r["n_eia_val"], r["n_eia_fill"] = int(eia_val.sum()), int((a_.notna() & r_.isna()).sum())
    r["k_eia_val_flagged"] = int((eia_val & flagged).sum())
    for c in SHARED:
        r[f"eia_n_{c}"], r[f"eia_k_{c}"] = int((Ld == c).sum()), int(((Ld == c) & eia).sum())
    r["eia_changed"] = float(eia.mean())
    r["screen_in_eia"] = float((flagged & eia).sum() / flagged.sum()) if flagged.sum() else np.nan
    r["eia_in_screen"] = float((flagged & eia).sum() / eia.sum()) if eia.sum() else np.nan
    r["n_flagged_demand"], r["n_eia_changed"] = int(flagged.sum()), int(eia.sum())
    clean = (Ld == "") & (Lf == "")
    raw_ok = pd.Series(True, index=g.index)
    for y in sorted(yr.unique()):
        m = yr == y
        q = {"ba": ba, "year": int(y), "size": r["size"]}
        q["mape_raw"] = mape(g["forecast"], g["demand"], m & raw_ok)
        q["mape_scr"] = mape(g["forecast"], g["demand"], m & clean)
        q["rel_change"] = abs(q["mape_raw"] / q["mape_scr"] - 1) if q["mape_scr"] else np.nan
        q["abs_change"] = abs(q["mape_raw"] - q["mape_scr"])
        clean2 = Ld.isin(["", "MISS"]) & Lf.isin(["", "MISS", "SHIFT"])
        q["mape_scr2"] = mape(f_al, g["demand"], m & clean2)
        q["rel_change2"] = abs(q["mape_raw"] / q["mape_scr2"] - 1) if q["mape_scr2"] else np.nan
        q["abs_change2"] = abs(q["mape_raw"] - q["mape_scr2"])
        q["n_shift_hours"] = int((Lf[m] == "SHIFT").sum())
        rep, adj = g.loc[m, "demand"], g.loc[m, "demand_adj"]
        scr = g.loc[m, "demand"].where(Ld[m] == "")
        q["peak_rep"], q["peak_adj"], q["peak_scr"] = float(rep.max()), float(adj.max()), float(scr.max())
        q["peak_rel_diff"] = abs(q["peak_rep"] / q["peak_adj"] - 1) if q["peak_adj"] > 0 else np.nan
        q["peak_date_differs"] = bool(g.loc[rep.idxmax(), "date"] != g.loc[adj.idxmax(), "date"]) if rep.notna().any() and adj.notna().any() else None
        q["scr_peak_rel_diff"] = abs(q["peak_rep"] / q["peak_scr"] - 1) if q["peak_scr"] > 0 else np.nan
        # top 5% days by reported daily max: any anomalous hour (either series) on those days
        gm = g[m]
        dmax = gm.groupby("date")["demand"].max()
        top = dmax.index[dmax >= dmax.quantile(0.95)]
        bad = Ld[m].isin(CLASSES) | Lf[m].isin(CLASSES)
        q["top_days_contaminated"] = bool(bad[gm["date"].isin(top)].any())
        amax = gm.groupby("date")["demand_adj"].max()
        top2 = amax.index[amax >= amax.quantile(0.95)]
        bad2 = Ld[m].isin(CLASSES) | Lf[m].isin(["NONPOS", "OVER", "SPIKE", "FLAT", "COPY"])
        q["top_days_contaminated2"] = bool(bad2[gm["date"].isin(top2)].any())
        q["forecast_shared"] = float(Lf[m].isin(SHARED).sum() / max((Lf[m] != "MISS").sum(), 1))
        q["demand_shared"] = float(Ld[m].isin(SHARED).sum() / max((Ld[m] != "MISS").sum(), 1))
        by.append(q)
    rows.append(r)

T = pd.DataFrame(rows).set_index("ba")
Y = pd.DataFrame(by)
T.to_csv(f"{OUT}/ba_quality_table.csv")
Y.to_csv(f"{OUT}/ba_year.csv", index=False)


def sign(x, alt):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    k = int((x > 0).sum())
    if len(x) == 0:
        return {"pos": 0, "n": 0, "p": float("nan")}
    return {"pos": k, "n": int(len(x)), "p": float(stats.binomtest(k, len(x), 0.5, alternative=alt).pvalue)}


def share_ci(b):
    b = np.asarray(b, dtype=bool)
    k, n = int(b.sum()), int(len(b))
    ci = stats.binomtest(k, n).proportion_ci(method="exact") if n else None
    return {"k": k, "n": n, "share": k / n if n else np.nan, "lo": ci.low if ci else np.nan, "hi": ci.high if ci else np.nan}


H = {"H1": sign(T["forecast_shared"] - T["demand_shared"], "greater"),
     "H4": sign(T["demand_shared_late"] - T["demand_shared_early"], "two-sided")}
order = sorted(H, key=lambda k: H[k]["p"])
prev = 0.0
for i, k in enumerate(order):
    prev = min(1.0, max(prev, (len(order) - i) * H[k]["p"]))
    H[k]["p_holm"] = prev
H["H1"]["supported"] = bool(H["H1"]["p_holm"] < 0.05 and H["H1"]["pos"] > H["H1"]["n"] / 2)
H["H4"]["supported"] = bool(H["H4"]["p_holm"] < 0.05)
yv = Y.dropna(subset=["rel_change"])
H["H2"] = share_ci(yv["rel_change"] > 0.10)
H["H2"]["supported"] = bool(H["H2"]["share"] >= 0.10)
yp = Y.dropna(subset=["peak_rel_diff"])
H["H3"] = share_ci(yp["peak_rel_diff"] > 0.01)
H["H3"]["supported"] = bool(H["H3"]["share"] >= 0.05)
H["H3"]["date_differs"] = share_ci(yp["peak_date_differs"].fillna(False))

tau = {}
for y, g in Y.dropna(subset=["mape_raw", "mape_scr"]).groupby("year"):
    if len(g) >= 5:
        tau[int(y)] = float(stats.kendalltau(g["mape_raw"], g["mape_scr"]).statistic)
sec = {"kendall_by_year": tau,
       "variants": {k: sign(pd.Series({b: v["forecast"] - v["demand"] for b, v in vv.items()}), "greater")
                    for k, vv in var_rates.items() if vv},
       "by_size": T.groupby("size")[["demand_shared", "forecast_shared", "demand_rate", "forecast_rate",
                                     "demand_miss", "forecast_miss"]].median().to_dict(),
       "rate_by_year": Y.groupby("year")[["demand_shared", "forecast_shared"]].median().to_dict(),
       "top_days_contaminated": share_ci(Y["top_days_contaminated"]),
       "eia": {"median_changed": float(T["eia_changed"].median()),
               "pooled_screen_in_eia": float((T["screen_in_eia"] * T["n_flagged_demand"]).sum() / T["n_flagged_demand"].sum()),
               "pooled_eia_in_screen": float((T["eia_in_screen"] * T["n_eia_changed"]).sum() / max(T["n_eia_changed"].sum(), 1))},
       "class_totals": {s: {c: float(T[f"{s}_{c}"].median()) for c in CLASSES} for s in ("demand", "forecast")},
       "bas_with_class": {s: {c: int((T[f"{s}_{c}"] > 0).sum()) for c in CLASSES} for s in ("demand", "forecast")}}
v2 = Y.dropna(subset=["rel_change2"])
noSEC = T.drop(index="SEC", errors="ignore")
am1 = {"H2_realigned": share_ci(v2["rel_change2"] > 0.10),
       "H2_dropped": [f"{a} {b}" for a, b in Y.loc[Y["rel_change"].isna(), ["ba", "year"]].values],
       "H2_hits_below_1pp": int(((yv["rel_change"] > 0.10) & (yv["abs_change"] < 1)).sum()),
       "H2_realigned_hits_below_1pp": int(((v2["rel_change2"] > 0.10) & (v2["abs_change2"] < 1)).sum()),
       "H2_abs_over_1pp": share_ci(yv["abs_change"] >= 1), "H2_realigned_abs_over_1pp": share_ci(v2["abs_change2"] >= 1),
       "top_days2": share_ci(Y["top_days_contaminated2"]),
       "eia_by_class": {c: {"n": int(T[f"eia_n_{c}"].sum()), "k": int(T[f"eia_k_{c}"].sum()),
                            "n_noSEC": int(noSEC[f"eia_n_{c}"].sum()), "k_noSEC": int(noSEC[f"eia_k_{c}"].sum())} for c in SHARED},
       "eia_screen_in_noSEC": float(noSEC[[f"eia_k_{c}" for c in SHARED]].values.sum() / max(noSEC[[f"eia_n_{c}" for c in SHARED]].values.sum(), 1)),
       "eia_screen_in_median_ba": float((T["screen_in_eia"]).median()),
       "eia_val_flagged_share": float(T["k_eia_val_flagged"].sum() / max(T["n_eia_val"].sum(), 1)),
       "eia_val_total": int(T["n_eia_val"].sum()), "eia_fill_total": int(T["n_eia_fill"].sum())}
desc = {"n_ba": len(T), "n_ba_year": len(Y), "median_demand_shared": float(T["demand_shared"].median()),
        "median_forecast_shared": float(T["forecast_shared"].median()),
        "max_rel_change": float(yv["rel_change"].max()) if len(yv) else np.nan}
json.dump({"hypotheses": H, "secondary": sec, "descriptive": desc, "amendment1": am1}, open(f"{OUT}/results.json", "w"), indent=1, default=float)
print(json.dumps({"hypotheses": H, "descriptive": desc}, indent=1, default=float))
