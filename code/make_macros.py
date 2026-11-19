"""Every number in the paper. Reads out/results.json, out/ba_quality_table.csv, out/ba_year.csv,
out/lag_diag.json; writes paper/macros.tex, paper/tab_classes.tex, paper/tab_lag.tex, out/macros.json.
Run from the repository root: python -I code/make_macros.py"""
import json

import numpy as np
import pandas as pd

R = json.load(open("out/results.json"))
T = pd.read_csv("out/ba_quality_table.csv", index_col=0)
Y = pd.read_csv("out/ba_year.csv")
L = json.load(open("out/lag_diag.json"))
H, S = R["hypotheses"], R["secondary"]
M = {}


def f(x, d=2):
    return f"{x:.{d}f}"


def pct(x, d=1):
    return f"{100 * x:.{d}f}"


def pvt(p):
    return "$<$0.001" if p < 0.001 else f"{p:.3f}" if p < 0.01 else f"{p:.2f}"


def pv(p):
    """Relation form for use as $p\res{key}$."""
    return "<0.001" if p < 0.001 else "=" + (f"{p:.3f}" if p < 0.01 else f"{p:.2f}")


M["nBa"], M["nHoursM"] = str(len(T)), f(T["hours"].sum() / 1e6, 2)
for k, v in T["size"].value_counts().items():
    M["nSize" + k.capitalize()] = str(v)
M["medDemShared"], M["medFcShared"] = pct(T["demand_shared"].median(), 3), pct(T["forecast_shared"].median(), 3)
M["medDemRate"], M["medFcRate"] = pct(T["demand_rate"].median(), 3), pct(T["forecast_rate"].median(), 3)
M["baAnyDem"], M["baAnyFc"] = str(int((T["demand_rate"] > 0).sum())), str(int((T["forecast_rate"] > 0).sum()))
for s, tag in (("demand", "Dem"), ("forecast", "Fc")):
    M[f"medMiss{tag}"] = pct(T[f"{s}_miss"].median(), 2)
    for c, n in S["bas_with_class"][s].items():
        M[f"ba{tag}{c.capitalize()}"] = str(n)
for sz in ("small", "mid", "large"):
    M[f"size{sz.capitalize()}Dem"] = pct(S["by_size"]["demand_shared"][sz], 3)
    M[f"size{sz.capitalize()}Fc"] = pct(S["by_size"]["forecast_shared"][sz], 3)
# H1, H4
h1, h4 = H["H1"], H["H4"]
M["hOnePos"], M["hOneN"], M["hOneP"], M["hOneHolm"] = str(h1["pos"]), str(h1["n"]), pv(h1["p"]), pv(h1["p_holm"])
M["hFourUp"], M["hFourN"], M["hFourDown"] = str(h4["pos"]), str(h4["n"]), str(h4["n"] - h4["pos"])
M["hFourP"], M["hFourHolm"] = pv(h4["p"]), pv(h4["p_holm"])
# H2
h2 = H["H2"]
M["hTwoK"], M["hTwoN"], M["hTwoShare"], M["hTwoLo"], M["hTwoHi"] = (str(h2["k"]), str(h2["n"]), pct(h2["share"]),
                                                                    pct(h2["lo"]), pct(h2["hi"]))
v = Y.dropna(subset=["rel_change"])
M["hTwoFifty"], M["hTwoHundred"] = str(int((v["rel_change"] > 0.5).sum())), str(int((v["rel_change"] > 1).sum()))
M["hTwoBas"] = str(v.loc[v["rel_change"] > 0.1, "ba"].nunique())
M["hTwoBasOf"] = str(v["ba"].nunique())
for sz in ("small", "mid", "large"):
    vv = v[v["size"] == sz]
    M["hTwoShare" + sz.capitalize()] = pct((vv["rel_change"] > 0.1).mean(), 0)
top = v.sort_values("rel_change", ascending=False).iloc[0]
M["worstMapeBa"], M["worstMapeYear"] = top["ba"], str(int(top["year"]))
M["worstMapeRaw"], M["worstMapeScr"] = f(top["mape_raw"], 0), f(top["mape_scr"], 1)
tau = S["kendall_by_year"]
M["tauMin"], M["tauMax"] = f(min(tau.values())), f(max(tau.values()))
M["tauMinYear"] = min(tau, key=tau.get)
# H3
h3 = H["H3"]
M["hThreeK"], M["hThreeN"], M["hThreeShare"], M["hThreeLo"], M["hThreeHi"] = (str(h3["k"]), str(h3["n"]), pct(h3["share"]),
                                                                              pct(h3["lo"]), pct(h3["hi"]))
M["hThreeDateK"], M["hThreeDateShare"] = str(h3["date_differs"]["k"]), pct(h3["date_differs"]["share"])
y = Y.dropna(subset=["peak_rel_diff"])
big = y[y["peak_rel_diff"] > 0.01]
M["hThreeRepHigher"] = str(int((big["peak_rep"] > big["peak_adj"]).sum()))
M["hThreeMedRatio"] = f(float((big["peak_rep"] / big["peak_adj"]).median()), 1)
M["hThreeBas"] = str(big["ba"].nunique())
for sz in ("small", "mid", "large"):
    yy = y[y["size"] == sz]
    M["hThreeShare" + sz.capitalize()] = pct((yy["peak_rel_diff"] > 0.01).mean(), 0)
yy = y.assign(r=(y["peak_scr"] / y["peak_adj"] - 1).abs())
M["scrVsAdjK"] = str(int((yy["r"] > 0.01).sum()))
pj = y[(y["ba"] == "PJM") & (y["peak_rep"] > 1e9)]
M["pjmSentinelYear"] = str(int(pj["year"].iloc[0])) if len(pj) else "--"
M["pjmSentinelGw"] = f(pj["peak_rep"].iloc[0] / 1e9, 2) if len(pj) else "--"
M["pjmTrueGw"] = f(pj["peak_adj"].iloc[0] / 1e3, 1) if len(pj) else "--"
# top days, EIA
td = S["top_days_contaminated"]
M["topK"], M["topN"], M["topShare"], M["topLo"], M["topHi"] = str(td["k"]), str(td["n"]), pct(td["share"]), pct(td["lo"]), pct(td["hi"])
E = S["eia"]
M["eiaMedChanged"], M["eiaScreenIn"], M["eiaInScreen"] = pct(E["median_changed"], 2), pct(E["pooled_screen_in_eia"], 0), pct(E["pooled_eia_in_screen"], 0)
M["eiaMaxBa"], M["eiaMax"] = T["eia_changed"].idxmax(), pct(T["eia_changed"].max(), 1)
# sensitivity of H1
V = S["variants"]
M["varPmin"], M["varPmax"] = pv(min(x["p"] for x in V.values())), pv(max(x["p"] for x in V.values()))
# highest forecast rates
fr = T.sort_values("forecast_rate", ascending=False)
for i, tag in enumerate(("One", "Two", "Three")):
    M[f"fcTop{tag}Ba"], M[f"fcTop{tag}Rate"] = fr.index[i], pct(fr["forecast_rate"].iloc[i], 0)
M["pjmShiftShare"] = pct(T.loc["PJM", "forecast_SHIFT"], 0)
M["chpdSpikeShare"] = pct(T.loc["CHPD", "forecast_SPIKE"], 0)
# lag diagnostic
off = {b: sorted(int(yr) for yr, q in r.items() if q["best"] != 0 and q["mape_best"] <= 0.9 * q["mape0"]) for b, r in L.items()}
off = {b: v for b, v in off.items() if v}
M["nOffsetBa"] = str(len(off))
pjm = [L["PJM"][str(yr)] for yr in off.get("PJM", [])]
M["pjmOffFirst"], M["pjmOffLast"] = str(min(off["PJM"])), str(max(off["PJM"]))
M["pjmMapeZero"] = f(np.mean([q["mape0"] for q in pjm]), 1)
M["pjmMapeBest"] = f(np.mean([q["mape_best"] for q in pjm]), 1)
M["pjmMapePre"] = f(np.mean([L["PJM"][str(yr)]["mape0"] for yr in (2016, 2017, 2018)]), 1)
M["pjmBestLag"] = str(pjm[0]["best"]).replace("-", "$-$")
rows = []
for b, yrs in sorted(off.items()):
    q = [L[b][str(yr)] for yr in yrs]
    lags = sorted({x["best"] for x in q})
    span = f"{yrs[0]}" if len(yrs) == 1 else (f"{yrs[0]}--{yrs[-1]}" if yrs == list(range(yrs[0], yrs[-1] + 1)) else ", ".join(map(str, yrs)))
    rows.append(f"{b} & {span} & {', '.join(str(k).replace('-', '$-$') for k in lags)} & "
                f"{np.mean([x['mape0'] for x in q]):.1f} & {np.mean([x['mape_best'] for x in q]):.1f} \\\\")
open("paper/tab_lag.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
# class table
CL = ["NONPOS", "OVER", "SPIKE", "FLAT", "COPY", "SHIFT"]
rows = []
for c in CL:
    cells = []
    for s in ("demand", "forecast"):
        if c in ("COPY", "SHIFT") and s == "demand":
            cells += ["--", "--"]
            continue
        col = T[f"{s}_{c}"]
        n = int((col > 0).sum())
        cells += [str(n), (f"{100 * col.max():.2f} ({col.idxmax()})" if n else "0")]
    rows.append(f"{c} & " + " & ".join(cells) + " \\\\")
open("paper/tab_classes.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")

# ---- amendment 1 (after the results and an internal review; see PLAN.md) ----
A1 = R["amendment1"]
q = A1["H2_realigned"]
M["hTwoRealShare"], M["hTwoRealLo"], M["hTwoRealHi"], M["hTwoRealK"], M["hTwoRealN"] = pct(q["share"]), pct(q["lo"]), pct(q["hi"]), str(q["k"]), str(q["n"])
M["hTwoBelowPp"], M["hTwoRealBelowPp"] = str(A1["H2_hits_below_1pp"]), str(A1["H2_realigned_hits_below_1pp"])
M["hTwoAbsShare"], M["hTwoRealAbsShare"] = pct(A1["H2_abs_over_1pp"]["share"]), pct(A1["H2_realigned_abs_over_1pp"]["share"])
drop = A1["H2_dropped"]
pj = sorted(int(x.split()[1]) for x in drop if x.startswith("PJM"))
other = [x for x in drop if not x.startswith("PJM")]
M["hTwoDropped"] = ", ".join(other + ([f"PJM {pj[0]}--{pj[-1]}"] if pj else []))
M["nDropped"] = str(len(drop))
s_ = Y.sort_values(["ba", "year"]).dropna(subset=["mape_scr2"]).copy()
s_["yy"] = s_.groupby("ba")["mape_scr2"].transform(lambda v: (v / v.shift(1) - 1).abs())
M["yoyMed"], M["yoyLo"], M["yoyHi"] = pct(s_["yy"].median(), 0), pct(s_["yy"].quantile(0.25), 0), pct(s_["yy"].quantile(0.75), 0)
q = A1["top_days2"]
M["topTwoShare"], M["topTwoLo"], M["topTwoHi"] = pct(q["share"]), pct(q["lo"]), pct(q["hi"])
E1 = A1["eia_by_class"]
for c, v in E1.items():
    t = c.capitalize()
    M[f"eiaN{t}"], M[f"eiaK{t}"] = f"{v['n']:,}".replace(",", "{,}"), f"{v['k']:,}".replace(",", "{,}")
    M[f"eiaPct{t}"] = pct(v["k"] / v["n"], 0) if v["n"] else "--"
    M[f"eiaPctNoSec{t}"] = pct(v["k_noSEC"] / v["n_noSEC"], 0) if v["n_noSEC"] else "--"
M["eiaNoSec"], M["eiaMedBa"] = pct(A1["eia_screen_in_noSEC"], 0), pct(A1["eia_screen_in_median_ba"], 0)
M["eiaValFlagged"] = pct(A1["eia_val_flagged_share"], 1)
M["eiaValTotal"], M["eiaFillTotal"] = f"{A1['eia_val_total']:,}".replace(",", "{,}"), f"{A1['eia_fill_total']:,}".replace(",", "{,}")
yr_ = Y.dropna(subset=["peak_rel_diff"])
ratio = yr_["peak_rep"] / yr_["peak_adj"]
M["ratioOverTwo"] = str(int((ratio > 2).sum()))
M["ratioMid"] = str(int(((ratio > 1.5) & (ratio <= 2)).sum()))
M["ratioSmall"] = str(int(((ratio > 1.01) & (ratio <= 1.5)).sum()))
M["ratioBelow"] = str(int((ratio < 0.99).sum()))
aa = yr_["peak_adj"] / yr_["peak_scr"]
M["adjAboveScr"], M["adjAboveScrTen"] = str(int((aa > 1.01).sum())), str(int((aa > 1.1).sum()))
pj20 = yr_[(yr_["ba"] == "PJM") & (yr_["year"] == 2020)].iloc[0]
M["pjmAdjTwenty"], M["pjmScrTwenty"] = f"{pj20['peak_adj']:,.0f}".replace(",", "{,}"), f"{pj20['peak_scr']:,.0f}".replace(",", "{,}")
LM = pd.read_csv("out/lag_monthly.csv")
LM["flag"] = (LM["best"] != 0) & (LM["mape_best"] <= 0.9 * LM["mape0"])
for b in ("PJM", "CISO", "AZPS", "SC"):
    x = LM[(LM["ba"] == b) & LM["flag"]]
    M[f"months{b.capitalize()}"] = str(len(x))
    if len(x):
        first = int(x["ym"].min())
        M[f"first{b.capitalize()}"] = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
                                      "October", "November", "December"][first % 100 - 1] + f" {first // 100}"
        M[f"calMonths{b.capitalize()}"] = str(x["ym"].mod(100).nunique())
pjm_all = LM[(LM["ba"] == "PJM") & (LM["ym"] >= int(LM.loc[(LM["ba"] == "PJM") & LM["flag"], "ym"].min()))]
M["pjmMonthsSince"] = str(len(pjm_all))
ch = Y[Y["ba"] == "CHPD"].set_index("year")["mape_scr2"]
bad_ = ch[ch > 20]
M["chpdBadFirst"], M["chpdBadLast"] = str(int(bad_.index.min())), str(int(bad_.index.max()))
M["chpdBadMin"], M["chpdBadMax"] = f(bad_.min(), 0), f(bad_.max(), 0)
M["chpdGood"] = f(ch[ch.index >= 2022].mean(), 1)
M["varPminT"], M["varPmaxT"] = pvt(min(x["p"] for x in V.values())), pvt(max(x["p"] for x in V.values()))

# ---- amendment 2 (exploratory, after independent review; see PLAN.md) ----
# PJM 2020 peaks (clarification)
pj = yr_[yr_["ba"] == "PJM"].set_index("year")
M["pjmRepTwenty"] = f"{pj.loc[2020, 'peak_rep']:,.0f}".replace(",", "{,}")
M["pjmAdjNineteen"] = f"{pj.loc[2019, 'peak_adj']:,.0f}".replace(",", "{,}")
M["pjmAdjTwentyOne"] = f"{pj.loc[2021, 'peak_adj']:,.0f}".replace(",", "{,}")
M["pjmScrAboveNbr"] = pct(pj.loc[2020, "peak_scr"] / max(pj.loc[2019, "peak_adj"], pj.loc[2021, "peak_adj"]) - 1, 0)
M["hThreeMinDiff"] = f"{np.floor(1000 * yr_.loc[yr_['peak_rel_diff'] > 0, 'peak_rel_diff'].min()) / 10:.1f}"  # rounded down: "exceeded"
# PJM official coincident-peak hours
P = json.load(open("out/pjm_official_check.json"))
M["cpN"], M["cpDem"], M["cpDemWithin"] = str(P["n_days"]), str(P["demand_at_official"]), str(P["demand_within_1h"])
M["cpFc"], M["cpFcBefore"], M["cpFcDel"] = str(P["forecast_at_official"]), str(P["forecast_before_official"]), str(P["forecast_delayed_at_official"])
M["cpFcMean"] = f(P["forecast_minus_official_mean_h"], 1).replace("-", "$-$")
M["cpFcDelMean"] = f(P["forecast_delayed_minus_official_mean_h"], 1).replace("-", "$-$")
M["cpDemMwDev"] = pct(max(abs(P["demand_over_official_mw_min"] - 1), abs(P["demand_over_official_mw_max"] - 1)), 0)
for lab, tag in (("std_DecFeb", "Std"), ("dst_JunAug", "Dst")):
    M[f"pjm{tag}Months"], M[f"pjm{tag}Minus"] = str(P[f"season_{lab}"]["months"]), str(P[f"season_{lab}"]["flagged_minus1"])
# robustness
A2 = json.load(open("out/amendment2.json"))
assert A2["reproduces_prespecified"], "robust.py does not reproduce the pre-specified H1/H2"
gr = A2["grid_range"]
M["gridN"] = str(gr["n_cfg"])
M["gridHTwoLo"], M["gridHTwoHi"] = pct(gr["H2"][0]), pct(gr["H2"][1])
M["gridNsLo"], M["gridNsHi"] = pct(gr["H2_noshift"][0]), pct(gr["H2_noshift"][1])
M["gridAbsLo"], M["gridAbsHi"] = pct(gr["H2_abs1pp"][0]), pct(gr["H2_abs1pp"][1])
M["gridHOnePosLo"], M["gridHOnePosHi"] = str(gr["H1_pos"][0]), str(gr["H1_pos"][1])
M["gridHOnePLo"], M["gridHOnePHi"] = pvt(gr["H1_p"][0]), pvt(gr["H1_p"][1])
# the COPY run length must not change any grid result (H1 cannot depend on it: COPY is not a shared class)
sig = {}
for tag, x in A2["grid"].items():
    hi_, lo_, fl_, cp_ = tag.split("_")
    sig.setdefault((hi_, lo_, fl_), set()).add((x["H1"]["pos"], x["H1"]["n"], x["H2"]["k"], x["H2_noshift"]["k"], x["H2_abs1pp"]["k"]))
assert all(len(v) == 1 for v in sig.values()), "COPY run length changes a grid result"
M["gridNdistinct"] = str(len(sig))
lowp = sorted(A2["grid"].items(), key=lambda kv: kv[1]["H1"]["p"])[0]
hi_, lo_, fl_, _ = lowp[0].split("_")
M["gridMinPSpikeHi"], M["gridMinPSpikeLo"], M["gridMinPFlat"] = hi_, lo_, fl_
M["gridMinPPos"], M["gridMinPN"], M["gridMinPP"] = str(lowp[1]["H1"]["pos"]), str(lowp[1]["H1"]["n"]), pv(lowp[1]["H1"]["p"])
M["gridSigCombos"] = str(sum(1 for k in sig if A2["grid"]["_".join(k) + "_24"]["H1"]["p"] < 0.05))
SHARED_ = ["NONPOS", "OVER", "SPIKE", "FLAT"]
M["gridHTwoAllAbove"] = "yes" if gr["H2_supported_all"] and gr["H2_noshift_supported_all"] else "no"
main_tag = "2_0.3_6_24"
g0 = A2["grid"][main_tag]
M["hTwoNsK"], M["hTwoNsN"], M["hTwoNsShare"] = str(g0["H2_noshift"]["k"]), str(g0["H2_noshift"]["n"]), pct(g0["H2_noshift"]["share"])
M["hTwoAbsK"] = str(g0["H2_abs1pp"]["k"])
M["hTwoAbsMedHits"] = f(A2["H2_abs"]["median_abs_hits"], 1)
M["hTwoAbsQlo"], M["hTwoAbsQhi"] = f(A2["H2_abs"]["q25_abs_hits"], 1), f(A2["H2_abs"]["q75_abs_hits"], 1)
CL_ = A2["cluster"]
for k, tag in (("H2", "hTwo"), ("H2_noshift", "hTwoNs"), ("H2_realigned", "hTwoReal"), ("H2_abs1pp", "hTwoAbs"), ("H3", "hThree")):
    M[f"{tag}ClLo"], M[f"{tag}ClHi"] = pct(CL_[k]["lo"]), pct(CL_[k]["hi"])
M["bootB"] = f"{CL_['B']:,}".replace(",", "{,}")
for k, tag in (("H1_own_ref", "Own"), ("H1_no_dem_anom", "Nda")):
    M[f"hOne{tag}Pos"], M[f"hOne{tag}N"], M[f"hOne{tag}P"] = str(A2[k]["pos"]), str(A2[k]["n"]), pv(A2[k]["p"])
th = A2["H3_thresholds"]
M["hThreeTwoPct"], M["hThreeFivePct"], M["hThreeTenPct"] = pct(th["0.02"]["share"]), pct(th["0.05"]["share"]), pct(th["0.1"]["share"])
M["hThreeNoGross"], M["hThreeNoGrossK"] = pct(A2["H3_without_gross"]["share"]), str(A2["H3_without_gross"]["k"])
EV = pd.DataFrame(A2["events"])
for ev in ("Uri", "Elliott"):
    e = EV[EV["event"] == ev]
    M[f"ev{ev}Hours"] = f"{int(e['hours'].sum()):,}".replace(",", "{,}")
    M[f"ev{ev}Dem"], M[f"ev{ev}Fc"] = str(int(e["demand_flagged"].sum())), str(int(e["forecast_flagged"].sum()))
    fc_cls = pd.DataFrame(list(e["forecast_classes"])).sum()
    M[f"ev{ev}FcShared"] = str(int(sum(fc_cls.get(c, 0) for c in SHARED_)))
    M[f"ev{ev}FcShift"] = str(int(fc_cls.get("SHIFT", 0)))

with open("paper/macros.tex", "w", encoding="utf-8") as fh:
    fh.write("% generated by code/make_macros.py -- do not edit\n\\makeatletter\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\expandafter\\def\\csname res@{k}\\endcsname{{{v}}}\n")
    fh.write("\\makeatother\n\\newcommand{\\res}[1]{\\ifcsname res@#1\\endcsname\\csname res@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
json.dump(M, open("out/macros.json", "w"), indent=0)
print(len(M), "macros")
print({k: M[k] for k in ("pjmMapeZero", "pjmMapeBest", "pjmMapePre", "hThreeMedRatio", "nOffsetBa", "fcTopOneBa", "pjmSentinelGw")})
