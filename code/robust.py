"""Amendment 2, items 2 to 6 (exploratory, after independent review; PLAN.md). Not pre-specified.
(2) threshold grid for H1 and H2: SPIKE bounds x FLAT run x COPY run, 27 configurations;
(3) H2 without the SHIFT class, and absolute (percentage-point) MAPE changes;
(4) BA-cluster bootstrap intervals for the H2 and H3 shares;
(5) H1 with the forecast's own reference median, and with forecast flags at anomalous-demand hours dropped;
(6) flagged hours during Winter Storms Uri and Elliott.
The screen is the one of code/quality.py with the COPY run length and the forecast's reference made
parameters; the pre-specified configuration must reproduce out/results.json (checked below).
Reads data/eia930_all.parquet, out/ba_quality_table.csv, out/ba_year.csv, out/results.json.
Writes out/amendment2.json and out/ba_year_a2.csv. Run from the repository root: python -I code/robust.py
"""
import itertools
import json
import time

import numpy as np
import pandas as pd
from scipy import stats

START, END = "2016-01-01", "2026-09-30"
SHARED = ["NONPOS", "OVER", "SPIKE", "FLAT"]
CLASSES = SHARED + ["COPY", "SHIFT"]
SPIKES, FLATS, COPIES = [(1.5, 0.5), (2.0, 0.3), (3.0, 0.2)], [4, 6, 12], [12, 24, 48]
MAIN = (2.0, 0.3, 6, 24)
EVENTS = {"Uri": ("2021-02-13", "2021-02-20", ["ERCO", "SWPP", "MISO"]),
          "Elliott": ("2022-12-23", "2022-12-26", ["PJM", "TVA", "DUK"])}
B, SEED = 10000, 20261119

d = pd.read_parquet("data/eia930_all.parquet",
                    columns=["ba", "date", "hour", "utc_end", "forecast", "demand", "demand_adj"])
d = d[(d["date"] >= START) & (d["date"] <= END)]
T0 = pd.read_csv("out/ba_quality_table.csv", index_col=0)
Y0 = pd.read_csv("out/ba_year.csv")
R0 = json.load(open("out/results.json"))


def runs(x, minlen):
    v = x.values
    same = np.r_[False, (v[1:] == v[:-1]) & ~np.isnan(v[1:]) & ~np.isnan(v[:-1])]
    grp = np.cumsum(~same)
    n = pd.Series(grp).map(pd.Series(grp).value_counts()).values
    return (n >= minlen) & ~np.isnan(v)


def classify(g, hi, lo, flat, copy, own_ref=False):
    """code/quality.py classify(), with the COPY run length and the forecast's reference as parameters."""
    ref_d = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    ref_f = g["forecast"].where(g["forecast"] > 0).rolling(168, center=True, min_periods=24).median() if own_ref else ref_d
    lab = {}
    for c, ref in (("demand", ref_d), ("forecast", ref_f)):
        x = g[c]
        L = pd.Series("", index=g.index, dtype=object)
        L[x.isna()] = "MISS"
        L[(L == "") & (x <= 0)] = "NONPOS"
        L[(L == "") & (x > 10 * ref)] = "OVER"
        L[(L == "") & (((x > hi * ref) & (x <= 10 * ref)) | ((x > 0) & (x < lo * ref)))] = "SPIKE"
        L[(L == "") & runs(x, flat)] = "FLAT"
        lab[c] = L
    f, dm = g["forecast"], g["demand"]
    e = ((f == dm) & f.notna()).values.astype(int)
    grp = np.cumsum(np.r_[1, (e[1:] != e[:-1]).astype(int)])
    n = pd.Series(grp).map(pd.Series(grp).value_counts()).values
    L = lab["forecast"]
    L[(L == "") & (e == 1) & (n >= copy)] = "COPY"
    clean = (lab["demand"] == "") & (L == "")
    month = g.index.to_period("M")
    shift = np.zeros(len(g), dtype=bool)
    fv, dv, cv = f.values, dm.values, clean.values
    for mth in np.unique(month):
        j = np.where(month == mth)[0]
        maes = {}
        for k in range(-3, 4):
            jj = j[(j + k >= 0) & (j + k < len(g))]
            ok = cv[jj] & cv[jj + k]
            if ok.sum() >= 100:
                maes[k] = np.mean(np.abs(fv[jj + k][ok] - dv[jj][ok]))
        if 0 in maes:
            kb = min(maes, key=maes.get)
            if kb != 0 and maes[kb] <= 0.8 * maes[0]:
                shift[j] = True
    L[(L == "") & shift & f.notna()] = "SHIFT"
    lab["forecast"] = L
    return lab


def mape(f, y, m):
    m = m & f.notna() & y.notna() & (y > 0)
    return float((100 * (f[m] - y[m]).abs() / y[m]).mean()) if m.sum() else np.nan


def sign(x):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    k = int((x > 0).sum())
    return {"pos": k, "n": int(len(x)), "p": float(stats.binomtest(k, len(x), 0.5, alternative="greater").pvalue)}


def share(b):
    b = np.asarray(b, dtype=bool)
    return {"k": int(b.sum()), "n": int(len(b)), "share": float(b.mean())}


def rate(L, m=None):
    m = (L != "MISS") if m is None else (m & (L != "MISS"))
    return float((L[m].isin(SHARED)).sum() / m.sum()) if m.sum() else np.nan


grid = [(hi, lo, fl, cp) for (hi, lo), fl, cp in itertools.product(SPIKES, FLATS, COPIES)]
rate_rows, year_rows, events = [], [], []
t0 = time.time()
for ba in T0.index:
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    G = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    keep = G["date"].notna()
    g = G[keep]
    yr = g["date"].dt.year
    raw = {int(y): mape(g["forecast"], g["demand"], yr == y) for y in sorted(yr.unique())}
    for cfg in grid + [MAIN + ("own_ref",)]:
        own = len(cfg) == 5
        lab = classify(G, *cfg[:4], own_ref=own)
        Ld, Lf = lab["demand"][keep], lab["forecast"][keep]
        tag = "own_ref" if own else "%g_%g_%d_%d" % cfg
        rr = {"ba": ba, "cfg": tag, "demand": rate(Ld), "forecast": rate(Lf)}
        if cfg == MAIN:
            rr["forecast_no_dem_anom"] = rate(Lf.where(~(Ld.isin(SHARED) & Lf.isin(SHARED)), ""))
            for ev, (a, b_, bas) in EVENTS.items():
                if ba in bas:
                    m = (g["date"] >= a) & (g["date"] <= b_)
                    events.append({"event": ev, "ba": ba, "hours": int(m.sum()),
                                   "demand_flagged": int(Ld[m].isin(SHARED).sum()),
                                   "forecast_flagged": int(Lf[m].isin(CLASSES).sum()),
                                   "demand_classes": Ld[m][Ld[m].isin(SHARED)].value_counts().to_dict(),
                                   "forecast_classes": Lf[m][Lf[m].isin(CLASSES)].value_counts().to_dict()})
        rate_rows.append(rr)
        if own:
            continue
        clean = (Ld == "") & (Lf == "")
        clean_ns = (Ld == "") & Lf.isin(["", "SHIFT"])
        for y in sorted(yr.unique()):
            m = yr == y
            s, sn = mape(g["forecast"], g["demand"], m & clean), mape(g["forecast"], g["demand"], m & clean_ns)
            year_rows.append({"ba": ba, "year": int(y), "cfg": tag, "mape_raw": raw[int(y)], "mape_scr": s, "mape_scr_ns": sn})
    print(ba, f"{time.time() - t0:.0f}s", flush=True)

RR, YY = pd.DataFrame(rate_rows), pd.DataFrame(year_rows)
YY["rel"] = (YY["mape_raw"] / YY["mape_scr"] - 1).abs()
YY["rel_ns"] = (YY["mape_raw"] / YY["mape_scr_ns"] - 1).abs()
YY["abs"] = (YY["mape_raw"] - YY["mape_scr"]).abs()
YY["abs_ns"] = (YY["mape_raw"] - YY["mape_scr_ns"]).abs()
main_tag = "%g_%g_%d_%d" % MAIN

out = {"grid": {}}
for tag, q in YY.groupby("cfg"):
    v, vn = q.dropna(subset=["rel"]), q.dropna(subset=["rel_ns"])
    r = RR[RR["cfg"] == tag]
    out["grid"][tag] = {"H1": sign(r["forecast"] - r["demand"]),
                        "H2": share(v["rel"] > 0.10), "H2_noshift": share(vn["rel_ns"] > 0.10),
                        "H2_abs1pp": share(v["abs"] >= 1), "H2_hits_below_1pp": int(((v["rel"] > 0.10) & (v["abs"] < 1)).sum()),
                        "H2_noshift_abs1pp": share(vn["abs_ns"] >= 1)}
G0 = out["grid"][main_tag]
out["reproduces_prespecified"] = bool(G0["H2"]["k"] == R0["hypotheses"]["H2"]["k"] and G0["H2"]["n"] == R0["hypotheses"]["H2"]["n"]
                                      and G0["H1"]["pos"] == R0["hypotheses"]["H1"]["pos"] and G0["H1"]["n"] == R0["hypotheses"]["H1"]["n"])
gv = list(out["grid"].values())
out["grid_range"] = {k: [min(x[k]["share"] for x in gv), max(x[k]["share"] for x in gv)]
                     for k in ("H2", "H2_noshift", "H2_abs1pp")}
out["grid_range"]["H1_pos"] = [min(x["H1"]["pos"] for x in gv), max(x["H1"]["pos"] for x in gv)]
out["grid_range"]["H1_p"] = [min(x["H1"]["p"] for x in gv), max(x["H1"]["p"] for x in gv)]
out["grid_range"]["H2_supported_all"] = bool(all(x["H2"]["share"] >= 0.10 for x in gv))
out["grid_range"]["H2_noshift_supported_all"] = bool(all(x["H2_noshift"]["share"] >= 0.10 for x in gv))
out["grid_range"]["n_cfg"] = len(gv)
# (5) H1 confounding
rm = RR[RR["cfg"] == main_tag].set_index("ba")
ro = RR[RR["cfg"] == "own_ref"].set_index("ba")
out["H1_own_ref"] = sign(ro["forecast"] - ro["demand"])
out["H1_no_dem_anom"] = sign(rm["forecast_no_dem_anom"] - rm["demand"])
# (3) absolute changes, pre-specified configuration
ym = YY[YY["cfg"] == main_tag].copy()
v = ym.dropna(subset=["rel"])
hit = v[v["rel"] > 0.10]
out["H2_abs"] = {"median_abs_all": float(v["abs"].median()), "median_abs_hits": float(hit["abs"].median()),
                 "q25_abs_hits": float(hit["abs"].quantile(0.25)), "q75_abs_hits": float(hit["abs"].quantile(0.75))}
# (4) BA-cluster bootstrap
rng = np.random.default_rng(SEED)
Y0i = Y0.set_index(["ba", "year"])
ym = ym.join(Y0i[["peak_rel_diff", "peak_rep", "peak_adj", "rel_change2"]], on=["ba", "year"])
ym["size"] = ym["ba"].map(T0["size"])
ym.drop(columns="cfg").to_csv("out/ba_year_a2.csv", index=False)
bas = np.array(sorted(ym["ba"].unique()))
idx = rng.integers(0, len(bas), size=(B, len(bas)))


def cluster(col, cond):
    q = ym.dropna(subset=[col])
    k = q.assign(h=cond(q)).groupby("ba")["h"].sum().reindex(bas, fill_value=0).values
    n = q.groupby("ba").size().reindex(bas, fill_value=0).values
    s = k[idx].sum(1) / n[idx].sum(1)
    return {"k": int(k.sum()), "n": int(n.sum()), "share": float(k.sum() / n.sum()),
            "lo": float(np.percentile(s, 2.5)), "hi": float(np.percentile(s, 97.5))}


out["cluster"] = {"H2": cluster("rel", lambda q: q["rel"] > 0.10),
                  "H2_noshift": cluster("rel_ns", lambda q: q["rel_ns"] > 0.10),
                  "H2_realigned": cluster("rel_change2", lambda q: q["rel_change2"] > 0.10),
                  "H2_abs1pp": cluster("rel", lambda q: q["abs"] >= 1),
                  "H3": cluster("peak_rel_diff", lambda q: q["peak_rel_diff"] > 0.01),
                  "B": B, "seed": SEED}
# H3 at other thresholds and without gross errors (reported peak > 2 x adjusted)
yp = Y0.dropna(subset=["peak_rel_diff"])
ratio = yp["peak_rep"] / yp["peak_adj"]
out["H3_thresholds"] = {str(t): share(yp["peak_rel_diff"] > t) for t in (0.005, 0.01, 0.02, 0.05, 0.10)}
out["H3_without_gross"] = share((yp["peak_rel_diff"] > 0.01) & (ratio <= 2))
out["events"] = events
json.dump(out, open("out/amendment2.json", "w"), indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k != "grid"}, indent=1, default=float))
